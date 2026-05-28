"""Celery tasks for workflow SLA enforcement and delegation management."""
import logging

from celery import shared_task

from apps.accounts.rls import iter_organization_ids, rls_context

logger = logging.getLogger(__name__)


def _sla_warning_notifications_for_org(*, organization_id: int) -> int:
    from datetime import timedelta

    from django.utils import timezone

    from apps.notifications.models import Notification

    from .models import WorkflowInstance, WorkflowStep

    now = timezone.now()
    warned_count = 0
    pending_steps = (
        WorkflowStep.objects
        .filter(
            decision=WorkflowStep.Decision.PENDING,
            sla_deadline__isnull=False,
            sla_breached=False,
            workflow_instance__template__organization_id=organization_id,
            workflow_instance__state__in=[
                WorkflowInstance.State.PENDING,
                WorkflowInstance.State.IN_PROGRESS,
            ],
        )
        .select_related("workflow_instance__template__organization", "approver_user")
    )

    for step in pending_steps:
        time_remaining = step.sla_deadline - now
        total_time = step.sla_deadline - step.created_at

        if total_time.total_seconds() <= 0:
            continue

        pct_elapsed = 1 - (time_remaining.total_seconds() / total_time.total_seconds())

        if pct_elapsed < 0.75 or time_remaining <= timedelta(0) or not step.approver_user_id:
            continue

        hours_left = round(time_remaining.total_seconds() / 3600, 1)
        Notification.objects.get_or_create(
            recipient=step.approver_user,
            organization=step.workflow_instance.template.organization,
            category=Notification.Category.WORKFLOW_SLA_WARNING,
            title=f"SLA Warning: {step.name}",
            defaults={
                "message": (
                    f"Step \"{step.name}\" in workflow "
                    f"\"{step.workflow_instance.template.name}\" "
                    f"has {hours_left}h remaining before SLA breach."
                ),
                "severity": Notification.Severity.WARNING,
                "link_url": "/settings/workflows",
            },
        )
        warned_count += 1

    return warned_count


@shared_task(name="workflows.check_sla_breaches")
def check_sla_breaches_task():
    """Detect overdue workflow steps and escalate them."""
    from .engine import check_sla_breaches

    total = 0
    for organization_id in iter_organization_ids():
        logger.info(
            "workflows.check_sla_breaches.start organization_id=%s",
            organization_id,
        )
        try:
            with rls_context(organization_id, bypass=False):
                breached = check_sla_breaches(organization_id=organization_id)
        except Exception:
            logger.exception(
                "workflows.check_sla_breaches.failed organization_id=%s",
                organization_id,
            )
            raise
        total += breached
        logger.info(
            "workflows.check_sla_breaches.success organization_id=%s breached=%s",
            organization_id,
            breached,
        )
    logger.info("workflows.check_sla_breaches.complete total_breached=%s", total)
    return total


@shared_task(name="workflows.expire_delegations")
def expire_delegations_task():
    """Mark expired delegations."""
    from .engine import expire_delegations

    total = 0
    for organization_id in iter_organization_ids():
        logger.info(
            "workflows.expire_delegations.start organization_id=%s",
            organization_id,
        )
        try:
            with rls_context(organization_id, bypass=False):
                expired = expire_delegations(organization_id=organization_id)
        except Exception:
            logger.exception(
                "workflows.expire_delegations.failed organization_id=%s",
                organization_id,
            )
            raise
        total += expired
        logger.info(
            "workflows.expire_delegations.success organization_id=%s expired=%s",
            organization_id,
            expired,
        )
    logger.info("workflows.expire_delegations.complete total_expired=%s", total)
    return total


@shared_task(name="workflows.sla_warning_notifications")
def sla_warning_notifications_task():
    """Send warning notifications for steps approaching their SLA deadline."""
    total = 0
    for organization_id in iter_organization_ids():
        logger.info(
            "workflows.sla_warning_notifications.start organization_id=%s",
            organization_id,
        )
        try:
            with rls_context(organization_id, bypass=False):
                warned = _sla_warning_notifications_for_org(organization_id=organization_id)
        except Exception:
            logger.exception(
                "workflows.sla_warning_notifications.failed organization_id=%s",
                organization_id,
            )
            raise
        total += warned
        logger.info(
            "workflows.sla_warning_notifications.success organization_id=%s warned=%s",
            organization_id,
            warned,
        )
    logger.info("workflows.sla_warning_notifications.complete total_warned=%s", total)
    return total
