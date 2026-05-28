"""
Reminder dispatch tests for apps.calendar.tasks.dispatch_due_reminders.

Per design §10 + §15:
- Reminders flow through apps.notifications.services.dispatch_workflow_notification
- Per-user default reminder used when event override is null
- 0-minute event override = opt out (no reminder fires)
- Cancelled occurrences are skipped (EC5)
- Cancelled events are skipped
- Single-occurrence event fires at trigger time
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone as dttz
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone as djtimezone

from apps.accounts.models import Organization
from apps.calendar.models import (
    CalendarEvent,
    CalendarEventAttendee,
    CalendarEventOccurrence,
)
from apps.calendar.tasks import dispatch_due_reminders

User = get_user_model()


def _utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=dttz.utc) if dt.tzinfo is None else dt.astimezone(dttz.utc)


class ReminderDispatchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Acme")
        cls.creator = User.objects.create_user(
            username="creator@acme.test", email="creator@acme.test", password="x"
        )
        cls.creator.profile.organization = cls.org
        cls.creator.profile.calendar_default_reminder_minutes = 15
        cls.creator.profile.save(
            update_fields=["organization", "calendar_default_reminder_minutes"]
        )

    def _make_event(self, *, starts_at, reminder_minutes_before=None, **kw):
        defaults = dict(
            organization=self.org,
            creator=self.creator,
            title="X",
            starts_at=starts_at,
            ends_at=starts_at + timedelta(minutes=30),
            visibility=CalendarEvent.Visibility.PRIVATE,
            reminder_minutes_before=reminder_minutes_before,
        )
        defaults.update(kw)
        return CalendarEvent.objects.create(**defaults)

    def test_event_in_reminder_window_fires(self):
        """Event starting in 15 minutes — reminder should fire NOW."""
        now = djtimezone.now()
        event = self._make_event(starts_at=now + timedelta(minutes=15))
        with patch(
            "apps.calendar.tasks.dispatch_workflow_notification"
        ) as mock_dispatch:
            result = dispatch_due_reminders()
        self.assertEqual(mock_dispatch.call_count, 1)
        self.assertEqual(result["reminders_sent"], 1)

    def test_event_override_to_zero_opts_out(self):
        """EC15 — event override = 0 means no reminder."""
        now = djtimezone.now()
        event = self._make_event(
            starts_at=now + timedelta(minutes=15),
            reminder_minutes_before=0,
        )
        with patch(
            "apps.calendar.tasks.dispatch_workflow_notification"
        ) as mock_dispatch:
            result = dispatch_due_reminders()
        self.assertEqual(mock_dispatch.call_count, 0)
        self.assertEqual(result["reminders_sent"], 0)

    def test_event_override_lead_time(self):
        """Override of 60 min — fires when event is 60 min away, not 15."""
        now = djtimezone.now()
        event = self._make_event(
            starts_at=now + timedelta(minutes=60),
            reminder_minutes_before=60,
        )
        with patch(
            "apps.calendar.tasks.dispatch_workflow_notification"
        ) as mock_dispatch:
            result = dispatch_due_reminders()
        self.assertEqual(mock_dispatch.call_count, 1)

    def test_cancelled_event_skipped(self):
        now = djtimezone.now()
        event = self._make_event(starts_at=now + timedelta(minutes=15))
        event.is_cancelled = True
        event.save(update_fields=["is_cancelled"])
        with patch(
            "apps.calendar.tasks.dispatch_workflow_notification"
        ) as mock_dispatch:
            result = dispatch_due_reminders()
        self.assertEqual(mock_dispatch.call_count, 0)

    def test_attendee_also_notified(self):
        now = djtimezone.now()
        event = self._make_event(starts_at=now + timedelta(minutes=15))
        guest = User.objects.create_user(
            username="g@acme.test", email="g@acme.test", password="x"
        )
        guest.profile.organization = self.org
        guest.profile.save(update_fields=["organization"])
        CalendarEventAttendee.objects.create(event=event, user=guest)
        with patch(
            "apps.calendar.tasks.dispatch_workflow_notification"
        ) as mock_dispatch:
            result = dispatch_due_reminders()
        self.assertEqual(mock_dispatch.call_count, 2)  # creator + attendee
        self.assertEqual(result["reminders_sent"], 2)


class RecurringReminderTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Acme")
        cls.creator = User.objects.create_user(
            username="creator@acme.test", email="creator@acme.test", password="x"
        )
        cls.creator.profile.organization = cls.org
        cls.creator.profile.calendar_default_reminder_minutes = 15
        cls.creator.profile.save(
            update_fields=["organization", "calendar_default_reminder_minutes"]
        )

    def test_recurring_cancelled_occurrence_no_fire(self):
        """EC5 — cancelled occurrence's reminder does NOT fire."""
        now = djtimezone.now()
        # Anchor the event 7 days ago so today is a recurring occurrence.
        event = CalendarEvent.objects.create(
            organization=self.org,
            creator=self.creator,
            title="Standup",
            starts_at=now - timedelta(days=7) + timedelta(minutes=15),
            ends_at=now - timedelta(days=7) + timedelta(minutes=45),
            recurrence_rule="FREQ=WEEKLY",
            visibility=CalendarEvent.Visibility.PRIVATE,
            reminder_minutes_before=15,
        )
        # Cancel today's occurrence
        todays_original = event.starts_at + timedelta(days=7)
        CalendarEventOccurrence.objects.create(
            event=event,
            original_start=todays_original,
            is_cancelled=True,
        )
        with patch(
            "apps.calendar.tasks.dispatch_workflow_notification"
        ) as mock_dispatch:
            result = dispatch_due_reminders()
        # The cancelled occurrence should NOT generate a reminder.
        self.assertEqual(mock_dispatch.call_count, 0)
