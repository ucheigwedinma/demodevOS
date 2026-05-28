"""
Celery tasks for Internal Tasks.

`dispatch_due_reminders` runs every 15 minutes via Celery beat. It scans
for tasks with `status != done` and a `due_date` set, and sends reminders
at 9am org-local on (due_date - 1 day) and on due_date itself.

Idempotency (per design EC12): we skip if a TASK_REMINDER Notification
exists for the same user + task in the last 23 hours.

All deliveries flow through dispatch_workflow_notification (per A1).
"""

from __future__ import annotations

import logging
from datetime import date as date_cls, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from celery import shared_task
from django.utils import timezone as djtimezone

# Module-level import so unittest.mock.patch can intercept it cleanly.
from apps.notifications.services import dispatch_workflow_notification

logger = logging.getLogger(__name__)

REMINDER_LOCAL_HOUR = 9
REMINDER_LOOKBACK_HOURS = 23  # idempotency window


def _safe_tz(name: str) -> ZoneInfo:
    """Return a ZoneInfo, falling back to UTC on garbage input."""
    try:
        return ZoneInfo((name or "UTC").strip() or "UTC")
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def _org_local_hour(org) -> int:
    """Current hour (0-23) in the org's timezone, or UTC fallback."""
    tz = _safe_tz(getattr(org, "timezone", "") or "UTC")
    return djtimezone.now().astimezone(tz).hour


def _org_local_date(org) -> date_cls:
    """Today's date in the org's timezone."""
    tz = _safe_tz(getattr(org, "timezone", "") or "UTC")
    return djtimezone.now().astimezone(tz).date()


@shared_task(name="internal_tasks.dispatch_due_reminders")
def dispatch_due_reminders():
    """
    Send 9am-local reminders for due-tomorrow and due-today tasks.

    Returns a small summary dict for observability.
    """
    from apps.accounts.models import Organization

    from .models import Task

    summary = {
        "orgs_in_window": 0,
        "tasks_scanned": 0,
        "reminders_sent": 0,
        "skipped_idempotent": 0,
        "skipped_no_recipient": 0,
        "errors": 0,
    }

    for org in Organization.objects.all().iterator():
        local_hour = _org_local_hour(org)
        if local_hour != REMINDER_LOCAL_HOUR:
            continue
        summary["orgs_in_window"] += 1

        today = _org_local_date(org)
        tomorrow = today + timedelta(days=1)

        # Candidates: due today or tomorrow, status != done.
        candidates = (
            Task.objects.filter(
                organization=org,
                due_date__in=[today, tomorrow],
            )
            .exclude(status=Task.Status.DONE)
            .select_related("creator", "assignee")
        )

        for task in candidates.iterator():
            summary["tasks_scanned"] += 1
            try:
                if _dispatch_for_task(task):
                    summary["reminders_sent"] += 1
                else:
                    summary["skipped_no_recipient"] += 1
            except _IdempotentSkip:
                summary["skipped_idempotent"] += 1
            except Exception:
                logger.exception(
                    "Internal task reminder dispatch failed (task=%s)", task.pk
                )
                summary["errors"] += 1

    return summary


class _IdempotentSkip(Exception):
    """Internal — raised to count idempotency skips."""


def _dispatch_for_task(task) -> bool:
    """
    Send the reminder for one task. Returns True if a notification was
    dispatched, False if there was no recipient. Raises _IdempotentSkip
    when the 23h dedupe rule applies.
    """
    from apps.notifications.models import Notification

    # Recipients: assignee primarily; creator only if no assignee.
    recipients = []
    if task.assignee_id and task.assignee and task.assignee.is_active:
        recipients = [task.assignee]
    elif task.creator_id and task.creator and task.creator.is_active:
        recipients = [task.creator]

    if not recipients:
        return False

    cutoff = djtimezone.now() - timedelta(hours=REMINDER_LOOKBACK_HOURS)
    link_url = f"/internal-tasks/{task.pk}"

    # Idempotency check (per EC12): skip if a TASK_REMINDER notification
    # exists for the same user + task in the last 23h.
    for recipient in recipients:
        already = Notification.objects.filter(
            recipient=recipient,
            category=Notification.Category.TASK_REMINDER,
            link_url=link_url,
            created_at__gte=cutoff,
        ).exists()
        if already:
            raise _IdempotentSkip

    # Headline depends on whether it's due today or tomorrow.
    today = _org_local_date(task.organization)
    if task.due_date == today:
        headline = f"Due today: {task.title}"
    else:
        headline = f"Due tomorrow: {task.title}"

    dispatch_workflow_notification(
        organization=task.organization,
        event_key="internal_tasks.due_reminder",
        recipients=recipients,
        context={
            "task_title": task.title,
            "task_due_date": task.due_date.isoformat() if task.due_date else "",
        },
        link_url=link_url,
        channels=("in_app", "email"),
        fallback_channels=("in_app", "email"),
        fallback_title=headline,
        fallback_message=task.description or "",
        fallback_category=Notification.Category.TASK_REMINDER,
        fallback_severity=Notification.Severity.INFO,
    )
    return True
