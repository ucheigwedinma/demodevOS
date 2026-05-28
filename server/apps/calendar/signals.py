"""
Calendar signals.

Currently small: iCal feed cache invalidation when a user-relevant event
changes. The auditlog hooks live in apps.py (registry-based) so this module
stays focused on side effects.
"""

from __future__ import annotations

from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import CalendarEvent, CalendarEventAttendee, CalendarEventOccurrence


def _bust_user_feed(user_id: int) -> None:
    """Bump the version stamp for a user's iCal feed cache key."""
    cache.delete(f"calendar.ical_feed.v:{user_id}")


@receiver(post_save, sender=CalendarEvent)
@receiver(post_delete, sender=CalendarEvent)
def _invalidate_feed_on_event_write(sender, instance: CalendarEvent, **kwargs):
    _bust_user_feed(instance.creator_id)
    # Attendees' feeds also change. Iterate over current attendees; on delete
    # the M2M relation is already torn down so this is a no-op there.
    try:
        attendee_ids = list(
            CalendarEventAttendee.objects.filter(event_id=instance.pk).values_list(
                "user_id", flat=True
            )
        )
    except Exception:
        attendee_ids = []
    for uid in attendee_ids:
        _bust_user_feed(uid)


@receiver(post_save, sender=CalendarEventAttendee)
@receiver(post_delete, sender=CalendarEventAttendee)
def _invalidate_feed_on_attendee_write(sender, instance: CalendarEventAttendee, **kwargs):
    _bust_user_feed(instance.user_id)
    try:
        creator_id = CalendarEvent.objects.filter(pk=instance.event_id).values_list(
            "creator_id", flat=True
        ).first()
    except Exception:
        creator_id = None
    if creator_id:
        _bust_user_feed(creator_id)


@receiver(post_save, sender=CalendarEventOccurrence)
@receiver(post_delete, sender=CalendarEventOccurrence)
def _invalidate_feed_on_occurrence_write(sender, instance: CalendarEventOccurrence, **kwargs):
    try:
        creator_id = CalendarEvent.objects.filter(pk=instance.event_id).values_list(
            "creator_id", flat=True
        ).first()
    except Exception:
        creator_id = None
    if creator_id:
        _bust_user_feed(creator_id)
