from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.notifications.models import Notification
from apps.notifications.services import dispatch_workflow_notification

from .models import ReportRun, ScheduledReportDispatch

logger = logging.getLogger(__name__)


@dataclass
class DispatchSummary:
    considered: int = 0
    dispatched: int = 0
    skipped_not_due: int = 0
    enqueue_failed: int = 0


def dispatch_due_scheduled_reports(
    *,
    now: datetime | None = None,
    limit: int = 500,
    organization_id: int | None = None,
) -> dict[str, int]:
    """Create centralized report-run spool entries for due schedules."""

    now_dt = timezone.localtime(now or timezone.now())
    summary = DispatchSummary()

    schedules = ScheduledReportDispatch.objects.filter(
        is_active=True,
        report_template__is_active=True,
    )
    if organization_id is not None:
        schedules = schedules.filter(organization_id=organization_id)
    schedules = schedules.select_related("organization", "report_template").order_by("id")[:limit]

    for schedule in schedules:
        summary.considered += 1
        if not _is_schedule_due(schedule=schedule, now=now_dt):
            summary.skipped_not_due += 1
            continue

        with transaction.atomic():
            run = ReportRun.objects.create(
                organization=schedule.organization,
                report_template=schedule.report_template,
                requested_by=schedule.report_template.owner,
                scheduled_dispatch=schedule,
                trigger=ReportRun.Trigger.SCHEDULED,
                status=ReportRun.Status.QUEUED,
                output_format=schedule.output_format,
                filters={},
                row_count=0,
                result_summary={
                    "message": "Scheduled dispatch accepted and queued for asynchronous execution.",
                    "dispatch_id": schedule.id,
                    "dispatch_name": schedule.name,
                    "requested_action": "run",
                },
            )
            schedule.last_dispatched_at = now_dt
            schedule.save(update_fields=["last_dispatched_at", "updated_at"])
            task_id = enqueue_report_run_execution(run=run)
            if not task_id:
                summary.enqueue_failed += 1
            summary.dispatched += 1

    return {
        "considered": summary.considered,
        "dispatched": summary.dispatched,
        "skipped_not_due": summary.skipped_not_due,
        "enqueue_failed": summary.enqueue_failed,
    }


def enqueue_report_run_execution(*, run: ReportRun) -> str | None:
    """
    Queue asynchronous execution for a report run.

    Returns task id when enqueue succeeds; otherwise marks the run failed and
    returns ``None``.
    """

    from .tasks import execute_report_run_task

    try:
        async_result = execute_report_run_task.delay(
            run_id=run.id,
            organization_id=run.organization_id,
        )
    except Exception as exc:
        now = timezone.now()
        ReportRun.objects.filter(pk=run.pk).update(
            status=ReportRun.Status.FAILED,
            error_message=f"Failed to enqueue async runner: {exc}",
            completed_at=now,
            result_summary=_merge_summary(
                run.result_summary,
                queue_state="enqueue_failed",
                queue_error=str(exc),
                failed_at=timezone.localtime(now).isoformat(),
            ),
        )
        logger.exception(
            "settings.report_run.enqueue_failed run_id=%s org_id=%s",
            run.id,
            run.organization_id,
        )
        return None

    queued_at = timezone.now()
    ReportRun.objects.filter(pk=run.pk).update(
        result_summary=_merge_summary(
            run.result_summary,
            queue_state="enqueued",
            queue_task_id=async_result.id,
            queued_at=timezone.localtime(queued_at).isoformat(),
        )
    )
    return async_result.id


def dispatch_report_ready_notification(*, run: ReportRun, recipients: Iterable[Any]) -> dict[str, int]:
    """Dispatch report-ready notification via centralized notification templates/fallbacks."""

    report_name = run.report_template.name
    view_url = f"/reports/{run.report_template_id}"
    fallback_message = f'Your report "{report_name}" is ready.'

    return dispatch_workflow_notification(
        organization=run.organization,
        event_key="reports_ready",
        recipients=recipients,
        context={
            "report_name": report_name,
            "report_code": run.report_template.code,
            "run_id": run.id,
            "generated_at": timezone.localtime(run.completed_at or run.created_at),
            "output_format": run.get_output_format_display(),
            "view_url": view_url,
            "download_url": f"{view_url}?notification={run.id}&action=download",
            "action_url": view_url,
        },
        link_url=view_url,
        channels=("in_app", "email"),
        fallback_channels=("in_app", "email"),
        fallback_title="Report ready",
        fallback_message=fallback_message,
        fallback_category=Notification.Category.REPORTS_READY,
        fallback_severity=Notification.Severity.INFO,
    )


def notification_recipients_for_run(*, run: ReportRun) -> list[Any]:
    """Resolve recipients for a completed report run notification."""

    if run.trigger == ReportRun.Trigger.SCHEDULED and run.scheduled_dispatch_id:
        recipients = _scheduled_notification_recipients(
            schedule=run.scheduled_dispatch,
            run=run,
        )
        if recipients:
            return recipients

    if run.trigger == ReportRun.Trigger.SUBSCRIPTION and run.subscription_id:
        recipients = _subscription_notification_recipients(
            subscription=run.subscription,
            run=run,
        )
        if recipients:
            return recipients

    owner = run.requested_by
    if owner and getattr(owner, "is_active", False):
        return [owner]
    return []


def _scheduled_notification_recipients(*, schedule: ScheduledReportDispatch, run: ReportRun) -> list[Any]:
    """Resolve in-app notification recipients from schedule email list within org scope."""

    emails = _normalized_emails(schedule.recipients)
    users: list[Any] = []
    if emails:
        user_model = get_user_model()
        email_set = set(emails)
        candidates = user_model.objects.filter(
            is_active=True,
            profile__organization=schedule.organization,
        )
        users = [
            candidate
            for candidate in candidates
            if (getattr(candidate, "email", "") or "").strip().lower() in email_set
        ]

    if users:
        return users

    owner = run.requested_by
    if owner and getattr(owner, "is_active", False):
        return [owner]

    return []


def _subscription_notification_recipients(*, subscription, run: ReportRun) -> list[Any]:
    emails = _normalized_emails(getattr(subscription, "recipients", []))
    recipients: list[Any] = []
    seen_user_ids: set[int] = set()

    subscription_user = getattr(subscription, "user", None)
    if subscription_user and getattr(subscription_user, "is_active", False):
        recipients.append(subscription_user)
        seen_user_ids.add(subscription_user.id)

    if emails:
        user_model = get_user_model()
        email_set = set(emails)
        candidates = user_model.objects.filter(
            is_active=True,
            profile__organization=run.organization,
        )
        for candidate in candidates:
            if candidate.id in seen_user_ids:
                continue
            if (getattr(candidate, "email", "") or "").strip().lower() in email_set:
                recipients.append(candidate)
                seen_user_ids.add(candidate.id)

    if recipients:
        return recipients

    owner = run.requested_by
    if owner and getattr(owner, "is_active", False):
        return [owner]
    return []


def _normalized_emails(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    normalized: dict[str, None] = {}
    for value in values:
        if not isinstance(value, str):
            continue
        email = value.strip().lower()
        if email:
            normalized[email] = None
    return list(normalized.keys())


def _merge_summary(current: Any, **extra: Any) -> dict[str, Any]:
    merged = dict(current) if isinstance(current, dict) else {}
    merged.update(extra)
    return merged


def _is_schedule_due(*, schedule: ScheduledReportDispatch, now: datetime) -> bool:
    dispatch_time = schedule.dispatch_time
    if now.time() < dispatch_time:
        return False

    last = timezone.localtime(schedule.last_dispatched_at) if schedule.last_dispatched_at else None

    if schedule.frequency == ScheduledReportDispatch.Frequency.DAILY:
        return last is None or last.date() < now.date()

    if schedule.frequency == ScheduledReportDispatch.Frequency.WEEKLY:
        if schedule.dispatch_day_of_week is None or now.weekday() != schedule.dispatch_day_of_week:
            return False
        return not _same_iso_week(last, now)

    if schedule.frequency == ScheduledReportDispatch.Frequency.MONTHLY:
        if schedule.dispatch_day_of_month is None or now.day != schedule.dispatch_day_of_month:
            return False
        return last is None or (last.year, last.month) != (now.year, now.month)

    if schedule.frequency == ScheduledReportDispatch.Frequency.QUARTERLY:
        if schedule.dispatch_day_of_month is None or now.day != schedule.dispatch_day_of_month:
            return False
        quarter = (now.month - 1) // 3
        if last is None:
            return True
        last_quarter = (last.month - 1) // 3
        return (last.year, last_quarter) != (now.year, quarter)

    if schedule.frequency == ScheduledReportDispatch.Frequency.ANNUAL:
        if schedule.dispatch_day_of_month is None:
            return False
        if now.month != 1 or now.day != schedule.dispatch_day_of_month:
            return False
        return last is None or last.year != now.year

    return False


def _same_iso_week(last: datetime | None, now: datetime) -> bool:
    if last is None:
        return False
    return last.isocalendar()[:2] == now.isocalendar()[:2]
