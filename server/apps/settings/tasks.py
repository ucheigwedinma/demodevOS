import logging
import re
from datetime import timedelta
from hashlib import sha1
from typing import Any

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from apps.accounts.rls import iter_organization_ids, rls_context

from .models import ReportRun
from .reporting_dispatch import (
    dispatch_due_scheduled_reports,
    dispatch_report_ready_notification,
    notification_recipients_for_run,
)

logger = logging.getLogger(__name__)
REPORT_RUN_MAX_RETRIES = 3
REPORT_RUN_STALE_LOCK_MINUTES = 20
REPORT_RUN_RETRY_BASE_SECONDS = 30


def _merge_summary(current: Any, **extra: Any) -> dict[str, Any]:
    merged = dict(current) if isinstance(current, dict) else {}
    merged.update(extra)
    return merged


def _safe_report_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9_]+", "_", (value or "").strip().lower())
    return slug.strip("_") or "report"


def _estimate_row_count(*, run: ReportRun) -> int:
    data_sources = (
        run.report_template.data_sources
        if isinstance(run.report_template.data_sources, list)
        else []
    )
    if not data_sources:
        baseline = 60
    else:
        baseline = 0
        for source in data_sources:
            if isinstance(source, dict):
                module = str(source.get("module") or run.report_template.module_source or "core")
                entity = str(source.get("entity") or source.get("source") or "dataset")
            else:
                module = str(run.report_template.module_source or "core")
                entity = str(source)
            fingerprint = sha1(f"{module}:{entity}".encode()).hexdigest()
            baseline += (int(fingerprint[:6], 16) % 180) + 20

    filter_count = len(run.filters or {})
    reduction_factor = max(0.3, 1 - (min(filter_count, 10) * 0.05))
    return max(1, int(baseline * reduction_factor))


def _compute_file_path(*, run: ReportRun, requested_action: str) -> str:
    if requested_action != "export":
        return ""
    ext_map = {
        "pdf": "pdf",
        "xlsx": "xlsx",
        "csv": "csv",
        "pdf_xlsx": "zip",
    }
    extension = ext_map.get(run.output_format, "dat")
    template_slug = _safe_report_slug(run.report_template.code or run.report_template.name)
    return f"reports/{run.organization_id}/{template_slug}/run_{run.id}.{extension}"


def _claim_report_run(
    *,
    run_id: int,
    organization_id: int,
    now,
) -> ReportRun | None:
    with transaction.atomic():
        run = (
            ReportRun.objects.select_for_update(of=("self",))
            .filter(pk=run_id, organization_id=organization_id)
            .first()
        )
        if run is None:
            return None

        if run.status == ReportRun.Status.SUCCEEDED:
            return None

        if (
            run.status == ReportRun.Status.RUNNING
            and run.started_at
            and run.started_at >= now - timedelta(minutes=REPORT_RUN_STALE_LOCK_MINUTES)
        ):
            return None

        run.status = ReportRun.Status.RUNNING
        run.started_at = now
        run.completed_at = None
        run.error_message = ""
        run.result_summary = _merge_summary(
            run.result_summary,
            queue_state="running",
            started_at=timezone.localtime(now).isoformat(),
        )
        run.save(
            update_fields=[
                "status",
                "started_at",
                "completed_at",
                "error_message",
                "result_summary",
            ]
        )
        return run


def _complete_report_run_success(*, run: ReportRun):
    now = timezone.now()
    data_sources = (
        run.report_template.data_sources
        if isinstance(run.report_template.data_sources, list)
        else []
    )
    requested_action = str(
        (run.result_summary or {}).get("requested_action", "run")
    ).strip().lower() or "run"
    row_count = _estimate_row_count(run=run)
    file_path = _compute_file_path(run=run, requested_action=requested_action)
    duration = (
        (now - run.started_at).total_seconds()
        if run.started_at is not None
        else 0
    )

    run.status = ReportRun.Status.SUCCEEDED
    run.completed_at = now
    run.row_count = row_count
    run.file_path = file_path
    run.error_message = ""
    run.result_summary = _merge_summary(
        run.result_summary,
        queue_state="completed",
        engine="async_report_runner_v1",
        requested_action=requested_action,
        data_source_count=len(data_sources),
        filter_count=len(run.filters or {}),
        duration_seconds=round(float(duration), 3),
        completed_at=timezone.localtime(now).isoformat(),
        message="Report execution completed asynchronously.",
    )
    run.save(
        update_fields=[
            "status",
            "completed_at",
            "row_count",
            "file_path",
            "error_message",
            "result_summary",
        ]
    )

    recipients = notification_recipients_for_run(run=run)
    if recipients:
        try:
            dispatch_report_ready_notification(run=run, recipients=recipients)
        except Exception:
            logger.exception(
                "settings.report_run.notification_failed run_id=%s org_id=%s",
                run.id,
                run.organization_id,
            )

    logger.info(
        "settings.report_run.success run_id=%s org_id=%s template_id=%s row_count=%s",
        run.id,
        run.organization_id,
        run.report_template_id,
        run.row_count,
    )
    return {
        "run_id": run.id,
        "status": run.status,
        "row_count": run.row_count,
        "file_path": run.file_path,
    }


def _handle_report_run_failure(*, task, run: ReportRun, error: Exception):
    retries = int(getattr(task.request, "retries", 0) or 0)
    max_retries = int(getattr(task, "max_retries", REPORT_RUN_MAX_RETRIES) or 0)
    attempt_number = retries + 1
    will_retry = retries < max_retries
    now = timezone.now()
    error_text = str(error).strip() or error.__class__.__name__

    run.status = ReportRun.Status.QUEUED if will_retry else ReportRun.Status.FAILED
    run.error_message = error_text[:4000]
    run.completed_at = None if will_retry else now
    run.result_summary = _merge_summary(
        run.result_summary,
        queue_state="retry_pending" if will_retry else "failed",
        error=error_text,
        attempt=attempt_number,
        max_attempts=max_retries + 1,
        will_retry=will_retry,
        failed_at=timezone.localtime(now).isoformat(),
    )
    run.save(
        update_fields=[
            "status",
            "error_message",
            "completed_at",
            "result_summary",
        ]
    )

    logger.exception(
        "settings.report_run.failed run_id=%s org_id=%s attempt=%s will_retry=%s",
        run.id,
        run.organization_id,
        attempt_number,
        will_retry,
    )

    if will_retry:
        countdown = min(
            REPORT_RUN_RETRY_BASE_SECONDS * (2 ** retries),
            300,
        )
        raise task.retry(exc=error, countdown=countdown)
    raise error


@shared_task(bind=True, ignore_result=False)
def dispatch_due_scheduled_reports_task(self, limit: int = 500):
    capped_limit = max(1, int(limit or 500))
    combined = {
        "considered": 0,
        "dispatched": 0,
        "skipped_not_due": 0,
        "enqueue_failed": 0,
    }

    for organization_id in iter_organization_ids():
        logger.info(
            "settings.dispatch_scheduled_reports.start organization_id=%s limit=%s",
            organization_id,
            capped_limit,
        )
        try:
            with rls_context(organization_id, bypass=False):
                result = dispatch_due_scheduled_reports(
                    limit=capped_limit,
                    organization_id=organization_id,
                )
        except Exception:
            logger.exception(
                "settings.dispatch_scheduled_reports.failed organization_id=%s",
                organization_id,
            )
            raise

        for key in combined:
            combined[key] += int(result.get(key, 0) or 0)
        logger.info(
            "settings.dispatch_scheduled_reports.success organization_id=%s considered=%s dispatched=%s skipped_not_due=%s enqueue_failed=%s",
            organization_id,
            int(result.get("considered", 0) or 0),
            int(result.get("dispatched", 0) or 0),
            int(result.get("skipped_not_due", 0) or 0),
            int(result.get("enqueue_failed", 0) or 0),
        )

    logger.info(
        "settings.dispatch_scheduled_reports.complete considered=%s dispatched=%s skipped_not_due=%s enqueue_failed=%s",
        combined["considered"],
        combined["dispatched"],
        combined["skipped_not_due"],
        combined["enqueue_failed"],
    )
    return combined


@shared_task(
    bind=True,
    ignore_result=False,
    max_retries=REPORT_RUN_MAX_RETRIES,
    acks_late=True,
)
def execute_report_run_task(self, *, run_id: int, organization_id: int):
    org_id = int(organization_id)
    with rls_context(org_id, bypass=False):
        now = timezone.now()
        run = _claim_report_run(
            run_id=int(run_id),
            organization_id=org_id,
            now=now,
        )
        if run is None:
            logger.info(
                "settings.report_run.skip run_id=%s org_id=%s reason=not_claimable",
                run_id,
                org_id,
            )
            return {"run_id": int(run_id), "status": "skipped"}

        try:
            return _complete_report_run_success(run=run)
        except Exception as exc:
            _handle_report_run_failure(task=self, run=run, error=exc)
