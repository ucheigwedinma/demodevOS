"""
Model-level tests for apps.calendar.

Per design §15:
- EC1: kind=reminder with ends_at=null allowed
- EC2: end < start rejected by CHECK constraint
- Idempotent attendee adds (EC9) via unique constraint
- Override uniqueness (event, original_start)
- IcalFeedToken hash mechanics
"""

from __future__ import annotations

from datetime import datetime, timezone as dttz

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.accounts.models import Organization
from apps.calendar.models import (
    CalendarEvent,
    CalendarEventAttendee,
    CalendarEventOccurrence,
    IcalFeedToken,
)

User = get_user_model()


def _utc(year, month, day, hour=0, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=dttz.utc)


class CalendarEventModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Acme")
        cls.user = User.objects.create_user(
            username="u@acme.test", email="u@acme.test", password="x"
        )
        cls.user.profile.organization = cls.org
        cls.user.profile.save(update_fields=["organization"])

    def _make(self, **kwargs):
        defaults = dict(
            organization=self.org,
            creator=self.user,
            title="Standup",
            starts_at=_utc(2026, 6, 3, 13, 30),
            ends_at=_utc(2026, 6, 3, 14, 0),
            timezone="UTC",
            kind=CalendarEvent.Kind.MEETING,
            visibility=CalendarEvent.Visibility.PRIVATE,
        )
        defaults.update(kwargs)
        return CalendarEvent.objects.create(**defaults)

    def test_defaults(self):
        event = self._make()
        self.assertEqual(event.kind, CalendarEvent.Kind.MEETING)
        self.assertEqual(event.visibility, CalendarEvent.Visibility.PRIVATE)
        self.assertEqual(event.timezone, "UTC")
        self.assertFalse(event.all_day)
        self.assertFalse(event.is_cancelled)
        self.assertFalse(event.is_recurring)

    def test_reminder_kind_allows_null_ends_at(self):
        """EC1 — reminders are moments-in-time."""
        event = self._make(kind=CalendarEvent.Kind.REMINDER, ends_at=None)
        self.assertIsNone(event.ends_at)

    def test_end_before_start_rejected_by_constraint(self):
        """EC2 — CHECK constraint enforces ends_at >= starts_at."""
        with self.assertRaises(IntegrityError), transaction.atomic():
            self._make(ends_at=_utc(2026, 6, 3, 13, 0))  # before starts_at

    def test_recurring_flag(self):
        event = self._make(recurrence_rule="FREQ=DAILY;COUNT=5")
        self.assertTrue(event.is_recurring)


class CalendarEventAttendeeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Acme")
        cls.creator = User.objects.create_user(
            username="creator@acme.test", email="creator@acme.test", password="x"
        )
        cls.creator.profile.organization = cls.org
        cls.creator.profile.save(update_fields=["organization"])
        cls.guest = User.objects.create_user(
            username="g@acme.test", email="g@acme.test", password="x"
        )
        cls.guest.profile.organization = cls.org
        cls.guest.profile.save(update_fields=["organization"])
        cls.event = CalendarEvent.objects.create(
            organization=cls.org,
            creator=cls.creator,
            title="x",
            starts_at=_utc(2026, 6, 3, 13, 0),
            ends_at=_utc(2026, 6, 3, 14, 0),
        )

    def test_unique_event_user(self):
        """EC9 — adding the same user twice is rejected at DB level."""
        CalendarEventAttendee.objects.create(event=self.event, user=self.guest)
        with self.assertRaises(IntegrityError), transaction.atomic():
            CalendarEventAttendee.objects.create(event=self.event, user=self.guest)


class CalendarEventOccurrenceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Acme")
        cls.user = User.objects.create_user(
            username="u@acme.test", email="u@acme.test", password="x"
        )
        cls.user.profile.organization = cls.org
        cls.user.profile.save(update_fields=["organization"])
        cls.event = CalendarEvent.objects.create(
            organization=cls.org,
            creator=cls.user,
            title="weekly",
            starts_at=_utc(2026, 6, 3, 13, 0),
            ends_at=_utc(2026, 6, 3, 14, 0),
            recurrence_rule="FREQ=WEEKLY",
        )

    def test_unique_event_original_start(self):
        """Two overrides for the same occurrence are rejected."""
        CalendarEventOccurrence.objects.create(
            event=self.event, original_start=_utc(2026, 6, 10, 13, 0)
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            CalendarEventOccurrence.objects.create(
                event=self.event, original_start=_utc(2026, 6, 10, 13, 0)
            )


class IcalFeedTokenTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="u@acme.test", email="u@acme.test", password="x"
        )

    def test_raw_token_not_stored(self):
        raw = IcalFeedToken.generate_raw_token()
        hashed = IcalFeedToken.hash_token(raw)
        token = IcalFeedToken.objects.create(user=self.user, token_hash=hashed)
        self.assertNotEqual(token.token_hash, raw)
        self.assertEqual(len(token.token_hash), 64)  # sha256 hex digest

    def test_hash_deterministic(self):
        raw = "test-token"
        self.assertEqual(
            IcalFeedToken.hash_token(raw), IcalFeedToken.hash_token(raw)
        )

    def test_token_hash_unique(self):
        raw = IcalFeedToken.generate_raw_token()
        hashed = IcalFeedToken.hash_token(raw)
        IcalFeedToken.objects.create(user=self.user, token_hash=hashed)
        with self.assertRaises(IntegrityError), transaction.atomic():
            IcalFeedToken.objects.create(user=self.user, token_hash=hashed)
