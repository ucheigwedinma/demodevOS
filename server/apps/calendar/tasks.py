"""
Celery tasks for the Calendar feature.

`dispatch_due_reminders` runs every minute via Celery beat. It scans for
events whose effective reminder time has just elapsed (within the last 60s)
and dispatches in-app + email notifications via the central
`apps.notifications.services.dispatch_workflow_notification` pipeline.

Why central pipeline: per design A1, the notifications app handles user
channel prefs, per-org channel enablement, and falls back gracefully. We
just hand over recipients + context.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Iterable

from celery import shared_task
from django.utils import timezone as djtimezone

# Module-level import so tests can patch this symbol. The notifications service
# is also re-imported lazily in `_send_reminder` for the same reason — keep
# both call sites pointing to the module-level reference here.
from apps.notifications.services import dispatch_workflow_notification

logger = logging.getLogger(__name__)

REMINDER_WINDOW_SECONDS = 60
DEFAULT_REMINDER_MINUTES = 15  # fallback when user has no pref set


@shared_task(name="calendar.dispatch_due_reminders")
def dispatch_due_reminders():
    """
    Find events whose reminder window has just passed and dispatch.

    Returns a summary dict for observability.
    """
    from .models import CalendarEvent, CalendarEventAttendee, CalendarEventOccurrence
    from .recurrence import expand_with_overrides

    now = djtimezone.now()
    window_end = now
    window_start = now - timedelta(seconds=REMINDER_WINDOW_SECONDS)

    summary = {"events_scanned": 0, "reminders_sent": 0, "skipped_opt_out": 0, "errors": 0}

    # Bound the candidate set: events that *could* have a reminder in this
    # window. Conservatively: starts_at within [now, now + 1440min] (one
    # day forward — covers up to 24h-before reminders).
    candidates = (
        CalendarEvent.objects.filter(
            is_cancelled=False,
            starts_at__gte=now,
            starts_at__lte=now + timedelta(minutes=1440),
        )
        .select_related("creator__profile", "team")
        .prefetch_related(
            "attendees__user__profile",
            "occurrences",
        )
    )

    for event in candidates:
        summary["events_scanned"] += 1

        recipients = _resolve_recipients(event)
        if not recipients:
            continue

        # Each recipient can have their own effective reminder lead time —
        # creator-set override on the event applies to everyone, otherwise
        # each user's `default_reminder_minutes` is used.
        event_override = event.reminder_minutes_before  # may be None or 0 or >0

        for recipient in recipients:
            try:
                lead = _effective_lead_minutes(event_override, recipient)
                if lead is None:
                    summary["skipped_opt_out"] += 1
                    continue
                # When the event recurs, check each occurrence in the window
                # whose (occurrence_start - lead) falls inside [window_start, window_end].
                if event.recurrence_rule:
                    target_window_start = window_start + timedelta(minutes=lead)
                    target_window_end = window_end + timedelta(minutes=lead)
                    occurrences = expand_with_overrides(
                        event, target_window_start, target_window_end
                    )
                    for occ in occurrences:
                        if occ.is_cancelled:
                            continue
                        _send_reminder(event, recipient, occ.starts_at, lead)
                        summary["reminders_sent"] += 1
                else:
                    trigger = event.starts_at - timedelta(minutes=lead)
                    if window_start <= trigger <= window_end:
                        _send_reminder(event, recipient, event.starts_at, lead)
                        summary["reminders_sent"] += 1
            except Exception:
                logger.exception(
                    "Failed reminder dispatch for event=%s recipient=%s",
                    event.pk,
                    getattr(recipient, "id", None),
                )
                summary["errors"] += 1
                # Do not re-raise — one bad recipient shouldn't poison the batch.

    return summary


def _resolve_recipients(event) -> list:
    """Creator + active attendee users for the event."""
    recipients = [event.creator] if event.creator and event.creator.is_active else []
    for attendee in event.attendees.all():
        if attendee.user_id == event.creator_id:
            continue  # avoid double-notifying the creator
        if attendee.user and attendee.user.is_active:
            recipients.append(attendee.user)
    return recipients


def _effective_lead_minutes(event_override, recipient) -> int | None:
    """
    Per design Q9: event override > user default > None.
    Returns None to mean "no reminder for this recipient" (opt-out).
    """
    if event_override is not None:
        return event_override if event_override > 0 else None
    profile = getattr(recipient, "profile", None)
    user_default = getattr(profile, "calendar_default_reminder_minutes", None)
    if user_default is None:
        user_default = DEFAULT_REMINDER_MINUTES
    if user_default == 0:
        return None
    return user_default


def _send_reminder(event, recipient, when, lead_minutes: int):
    """Dispatch one reminder via the notifications pipeline."""
    from apps.notifications.models import Notification

    title = f"Reminder: {event.title} starts in {lead_minutes} minute(s)"
    message = (
        f"{event.title}\n"
        f"Starts: {when.strftime('%Y-%m-%d %H:%M %Z')}\n"
        + (f"Location: {event.location}\n" if event.location else "")
        + (f"Link: {event.meeting_link}\n" if event.meeting_link else "")
    )

    dispatch_workflow_notification(
        organization=event.organization,
        event_key="calendar.reminder",
        recipients=[recipient],
        context={
            "event_title": event.title,
            "event_starts_at": when.isoformat(),
            "event_location": event.location or event.meeting_link,
            "lead_minutes": lead_minutes,
        },
        link_url=f"/calendar/events/{event.pk}",
        channels=("in_app", "email"),
        fallback_channels=("in_app", "email"),
        fallback_title=title,
        fallback_message=message,
        fallback_category=Notification.Category.CALENDAR_REMINDER,
        fallback_severity=Notification.Severity.INFO,
    )
