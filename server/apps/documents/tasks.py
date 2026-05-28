"""Celery tasks for document expiry and compliance automation."""
import logging

from celery import shared_task
from django.utils import timezone

from apps.accounts.rls import iter_organization_ids, rls_context

from .compliance_monitoring import run_expiry_compliance_monitor

logger = logging.getLogger(__name__)


@shared_task(name="documents.run_expiry_compliance_monitor")
def run_expiry_compliance_monitor_task():
    """Run Phase 6 expiry checks and compliance score updates."""
    monitor_date = timezone.now().date()
    combined = {
        "monitor_date": monitor_date.isoformat(),
        "processed": 0,
        "alerts_90_day": 0,
        "alerts_30_day": 0,
        "expired_alerts": 0,
        "escalations": 0,
        "expired_documents": 0,
        "notifications_sent": 0,
        "emails_sent": 0,
        "project_scores_updated": 0,
    }

    for organization_id in iter_organization_ids():
        logger.info(
            "documents.expiry_monitor.start organization_id=%s monitor_date=%s",
            organization_id,
            monitor_date.isoformat(),
        )
        try:
            with rls_context(organization_id, bypass=False):
                summary = run_expiry_compliance_monitor(reference_date=monitor_date)
        except Exception:
            logger.exception(
                "documents.expiry_monitor.failed organization_id=%s",
                organization_id,
            )
            raise

        for key in combined:
            if key == "monitor_date":
                continue
            combined[key] += int(summary.get(key, 0) or 0)
        logger.info(
            "documents.expiry_monitor.success organization_id=%s processed=%s notifications=%s emails=%s escalations=%s",
            organization_id,
            int(summary.get("processed", 0) or 0),
            int(summary.get("notifications_sent", 0) or 0),
            int(summary.get("emails_sent", 0) or 0),
            int(summary.get("escalations", 0) or 0),
        )

    logger.info(
        "documents.expiry_monitor.complete monitor_date=%s processed=%s notifications=%s emails=%s escalations=%s",
        combined["monitor_date"],
        combined["processed"],
        combined["notifications_sent"],
        combined["emails_sent"],
        combined["escalations"],
    )
    return combined
