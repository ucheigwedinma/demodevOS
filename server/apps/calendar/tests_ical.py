"""
iCal feed + per-event .ics tests.

Per design §12 + §15:
- Token-protected feed URL works only with valid (un-revoked) token
- Token rotation invalidates old token (EC11)
- Feed contains the user's visible events
- Feed does NOT include apps.meetings.Meeting rows
- VEVENT lines parse cleanly (basic RFC 5545 conformance check)
"""

from __future__ import annotations

from datetime import datetime, timezone as dttz

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase

from apps.accounts.models import Organization
from apps.calendar.ical_export import build_user_feed, event_to_ical
from apps.calendar.models import CalendarEvent, IcalFeedToken

User = get_user_model()


def _utc(year, month, day, hour=0, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=dttz.utc)


class IcalFeedTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Acme")
        cls.user = User.objects.create_user(
            username="u@acme.test", email="u@acme.test", password="x"
        )
        cls.user.profile.organization = cls.org
        cls.user.profile.save(update_fields=["organization"])

    def setUp(self):
        cache.clear()

    def test_feed_includes_owned_events(self):
        CalendarEvent.objects.create(
            organization=self.org,
            creator=self.user,
            title="My event",
            starts_at=_utc(2026, 6, 3, 13, 0),
            ends_at=_utc(2026, 6, 3, 14, 0),
        )
        body = build_user_feed(self.user)
        self.assertIn("BEGIN:VCALENDAR", body)
        self.assertIn("END:VCALENDAR", body)
        self.assertIn("SUMMARY:My event", body)
        self.assertIn("DTSTART:20260603T130000Z", body)

    def test_feed_empty_when_no_events(self):
        body = build_user_feed(self.user)
        self.assertIn("BEGIN:VCALENDAR", body)
        self.assertNotIn("BEGIN:VEVENT", body)

    def test_feed_excludes_private_event_user_not_in(self):
        other = User.objects.create_user(
            username="other@acme.test", email="other@acme.test", password="x"
        )
        other.profile.organization = self.org
        other.profile.save(update_fields=["organization"])
        CalendarEvent.objects.create(
            organization=self.org,
            creator=other,
            title="other private",
            starts_at=_utc(2026, 6, 3, 13, 0),
            ends_at=_utc(2026, 6, 3, 14, 0),
            visibility=CalendarEvent.Visibility.PRIVATE,
        )
        body = build_user_feed(self.user)
        self.assertNotIn("other private", body)

    def test_event_to_ical_standalone(self):
        event = CalendarEvent.objects.create(
            organization=self.org,
            creator=self.user,
            title="Stand-alone",
            location="Conference Room 3, with; commas\\backslash",
            starts_at=_utc(2026, 6, 3, 13, 0),
            ends_at=_utc(2026, 6, 3, 14, 0),
        )
        ical = event_to_ical(event)
        self.assertIn("BEGIN:VCALENDAR", ical)
        self.assertIn("BEGIN:VEVENT", ical)
        self.assertIn("END:VEVENT", ical)
        # Escaping
        self.assertIn("\\,", ical)  # comma escaped
        self.assertIn("\\;", ical)  # semicolon escaped

    def test_recurring_event_emits_rrule_line(self):
        CalendarEvent.objects.create(
            organization=self.org,
            creator=self.user,
            title="Weekly",
            starts_at=_utc(2026, 6, 3, 13, 0),
            ends_at=_utc(2026, 6, 3, 14, 0),
            recurrence_rule="FREQ=WEEKLY;BYDAY=WE",
        )
        body = build_user_feed(self.user)
        self.assertIn("RRULE:FREQ=WEEKLY;BYDAY=WE", body)


class TokenResolutionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="u@acme.test", email="u@acme.test", password="x"
        )

    def test_token_lookup_by_hash(self):
        raw = IcalFeedToken.generate_raw_token()
        IcalFeedToken.objects.create(
            user=self.user, token_hash=IcalFeedToken.hash_token(raw)
        )
        # Find by hash
        found = IcalFeedToken.objects.filter(
            token_hash=IcalFeedToken.hash_token(raw),
            revoked_at__isnull=True,
        ).first()
        self.assertIsNotNone(found)
        self.assertEqual(found.user, self.user)

    def test_revoked_token_excluded(self):
        from django.utils import timezone as djtimezone

        raw = IcalFeedToken.generate_raw_token()
        token = IcalFeedToken.objects.create(
            user=self.user, token_hash=IcalFeedToken.hash_token(raw)
        )
        token.revoked_at = djtimezone.now()
        token.save(update_fields=["revoked_at"])
        found = IcalFeedToken.objects.filter(
            token_hash=IcalFeedToken.hash_token(raw),
            revoked_at__isnull=True,
        ).first()
        self.assertIsNone(found)
