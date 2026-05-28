"""
Audit log integration tests.

Per design §11:
- CalendarEvent metadata changes create LogEntry rows
- description changes NOT audited (excluded from include_fields)
- CalendarEventAttendee add creates LogEntry
- CalendarEventOccurrence add creates LogEntry
"""

from __future__ import annotations

from datetime import datetime, timezone as dttz

from auditlog.models import LogEntry
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from apps.accounts.models import Organization
from apps.calendar.models import (
    CalendarEvent,
    CalendarEventAttendee,
    CalendarEventOccurrence,
)

User = get_user_model()


def _utc(year, month, day, hour=0, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=dttz.utc)


class CalendarAuditTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Acme")
        cls.user = User.objects.create_user(
            username="u@acme.test", email="u@acme.test", password="x"
        )
        cls.user.profile.organization = cls.org
        cls.user.profile.save(update_fields=["organization"])

    def test_event_create_logged(self):
        event = CalendarEvent.objects.create(
            organization=self.org,
            creator=self.user,
            title="X",
            starts_at=_utc(2026, 6, 3, 13, 0),
            ends_at=_utc(2026, 6, 3, 14, 0),
        )
        ct = ContentType.objects.get_for_model(CalendarEvent)
        entries = LogEntry.objects.filter(content_type=ct, object_pk=str(event.pk))
        self.assertGreaterEqual(entries.count(), 1)

    def test_event_visibility_change_logged(self):
        event = CalendarEvent.objects.create(
            organization=self.org,
            creator=self.user,
            title="X",
            starts_at=_utc(2026, 6, 3, 13, 0),
            ends_at=_utc(2026, 6, 3, 14, 0),
        )
        event.visibility = CalendarEvent.Visibility.ORG
        event.save()
        ct = ContentType.objects.get_for_model(CalendarEvent)
        entries = LogEntry.objects.filter(
            content_type=ct, object_pk=str(event.pk), action=LogEntry.Action.UPDATE
        )
        self.assertGreaterEqual(entries.count(), 1)
        # The change row should mention 'visibility'
        self.assertTrue(
            any("visibility" in str(e.changes) for e in entries),
            f"Expected visibility in audit changes; got {[e.changes for e in entries]}",
        )

    def test_description_change_NOT_logged(self):
        """description is excluded from auditlog per design §11."""
        event = CalendarEvent.objects.create(
            organization=self.org,
            creator=self.user,
            title="X",
            description="initial",
            starts_at=_utc(2026, 6, 3, 13, 0),
            ends_at=_utc(2026, 6, 3, 14, 0),
        )
        # Mutate description only
        event.description = "changed"
        event.save()
        ct = ContentType.objects.get_for_model(CalendarEvent)
        update_entries = LogEntry.objects.filter(
            content_type=ct, object_pk=str(event.pk), action=LogEntry.Action.UPDATE
        )
        # Either zero update entries (auditlog suppresses) or no 'description' in any change.
        for entry in update_entries:
            self.assertNotIn("description", str(entry.changes).lower())

    def test_attendee_add_logged(self):
        event = CalendarEvent.objects.create(
            organization=self.org,
            creator=self.user,
            title="X",
            starts_at=_utc(2026, 6, 3, 13, 0),
            ends_at=_utc(2026, 6, 3, 14, 0),
        )
        guest = User.objects.create_user(
            username="g@acme.test", email="g@acme.test", password="x"
        )
        attendee = CalendarEventAttendee.objects.create(event=event, user=guest)
        ct = ContentType.objects.get_for_model(CalendarEventAttendee)
        entries = LogEntry.objects.filter(content_type=ct, object_pk=str(attendee.pk))
        self.assertGreaterEqual(entries.count(), 1)
