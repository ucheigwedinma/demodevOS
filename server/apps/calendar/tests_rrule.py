"""
RRULE expansion + override tests.

Covers the high-risk recurrence engine before any API code is exercised.
Per design §15:
- EC3: DST transitions (fall back + spring forward), event stays at local time
- EC4: orphan override detection
- EC10: RRULE COUNT=10 + override at occurrence 11 → orphan
- EC12: open-ended RRULE expansion capped at 1y / 6m
- BYDAY: weekly multi-day (Tu, Th)
- Single-occurrence events
- Overrides whose shifted time falls in-window while original lands outside
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone as dttz

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone as djtimezone

from apps.accounts.models import Organization
from apps.calendar.models import CalendarEvent, CalendarEventOccurrence
from apps.calendar.recurrence import (
    WINDOW_CAP_BACKWARD,
    WINDOW_CAP_FORWARD,
    expand_raw,
    expand_with_overrides,
    is_orphan_override,
)

User = get_user_model()


def _utc(year, month, day, hour=0, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=dttz.utc)


class _Base(TestCase):
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
            starts_at=_utc(2026, 6, 3, 13, 30),  # 9:30 EDT
            ends_at=_utc(2026, 6, 3, 14, 0),
            timezone="America/New_York",
            kind=CalendarEvent.Kind.MEETING,
            visibility=CalendarEvent.Visibility.PRIVATE,
        )
        defaults.update(kwargs)
        return CalendarEvent.objects.create(**defaults)


class SingleOccurrenceTests(_Base):
    def test_single_event_in_window(self):
        event = self._make()
        out = expand_raw(event, _utc(2026, 6, 1), _utc(2026, 6, 30))
        self.assertEqual(out, [_utc(2026, 6, 3, 13, 30)])

    def test_single_event_outside_window(self):
        event = self._make(starts_at=_utc(2026, 1, 1, 12, 0), ends_at=_utc(2026, 1, 1, 13, 0))
        out = expand_raw(event, _utc(2026, 6, 1), _utc(2026, 6, 30))
        self.assertEqual(out, [])


class RecurrenceBasicTests(_Base):
    def test_weekly_byday_two_days(self):
        # Every Tuesday and Thursday at 9:30 ET, starting Tue 2026-06-02
        event = self._make(
            starts_at=_utc(2026, 6, 2, 13, 30),
            ends_at=_utc(2026, 6, 2, 14, 0),
            recurrence_rule="FREQ=WEEKLY;BYDAY=TU,TH",
        )
        out = expand_raw(event, _utc(2026, 6, 2), _utc(2026, 6, 20))
        # 2, 4, 9, 11, 16, 18 → 6 occurrences
        self.assertEqual(len(out), 6)

    def test_daily_with_count(self):
        event = self._make(
            starts_at=_utc(2026, 6, 1, 13, 30),
            ends_at=_utc(2026, 6, 1, 14, 0),
            recurrence_rule="FREQ=DAILY;COUNT=5",
        )
        out = expand_raw(event, _utc(2026, 5, 30), _utc(2026, 7, 1))
        self.assertEqual(len(out), 5)

    def test_until_caps(self):
        event = self._make(
            starts_at=_utc(2026, 6, 1, 13, 30),
            ends_at=_utc(2026, 6, 1, 14, 0),
            recurrence_rule="FREQ=DAILY;UNTIL=20260605T235959Z",
        )
        out = expand_raw(event, _utc(2026, 5, 30), _utc(2026, 12, 1))
        # 1, 2, 3, 4, 5
        self.assertEqual(len(out), 5)


class DSTTests(_Base):
    """
    The single most important property: a 9am-NYC weekly recurring event
    must stay at 9am local time across DST boundaries.
    US DST 2026: forward Mar 8, back Nov 1.
    """

    def test_recurring_stays_at_9am_across_fall_back(self):
        # Anchor on 2026-10-26 (Monday before DST ends Nov 1) at 9am NYC = 13:00 UTC
        event = self._make(
            starts_at=_utc(2026, 10, 26, 13, 0),
            ends_at=_utc(2026, 10, 26, 14, 0),
            recurrence_rule="FREQ=WEEKLY;BYDAY=MO",
            timezone="America/New_York",
        )
        out = expand_raw(event, _utc(2026, 10, 26), _utc(2026, 11, 20))
        # Expect 4 Mondays: 10-26 (DST=EDT, UTC offset -4), 11-02 (EST, -5), 11-09 (EST), 11-16 (EST)
        self.assertEqual(len(out), 4)
        # Pre-DST: UTC 13:00 == 09:00 EDT (UTC-4)
        self.assertEqual(out[0].hour, 13)
        # Post-DST: UTC 14:00 == 09:00 EST (UTC-5)
        for after_dst in out[1:]:
            self.assertEqual(
                after_dst.hour, 14,
                f"After DST fall-back, 9am NYC should be 14:00 UTC; got {after_dst}",
            )

    def test_recurring_stays_at_9am_across_spring_forward(self):
        # Anchor on 2026-03-02 (Monday before DST starts Mar 8) at 9am NYC = 14:00 UTC
        event = self._make(
            starts_at=_utc(2026, 3, 2, 14, 0),
            ends_at=_utc(2026, 3, 2, 15, 0),
            recurrence_rule="FREQ=WEEKLY;BYDAY=MO",
            timezone="America/New_York",
        )
        out = expand_raw(event, _utc(2026, 3, 2), _utc(2026, 3, 25))
        # 4 Mondays: 3-02 (EST), 3-09 (EDT — DST already started Sun Mar 8),
        # 3-16 (EDT), 3-23 (EDT)
        self.assertEqual(len(out), 4)
        # Pre-DST: 14:00 UTC
        self.assertEqual(out[0].hour, 14)
        # Post-DST: 13:00 UTC (9am EDT = UTC-4)
        for after_dst in out[1:]:
            self.assertEqual(
                after_dst.hour, 13,
                f"After DST spring-forward, 9am NYC should be 13:00 UTC; got {after_dst}",
            )


class WindowCapTests(_Base):
    def test_open_ended_rule_capped(self):
        """EC12 — FREQ=YEARLY with no UNTIL/COUNT must still expand bounded."""
        event = self._make(
            starts_at=_utc(2025, 1, 1, 13, 0),
            ends_at=_utc(2025, 1, 1, 14, 0),
            recurrence_rule="FREQ=YEARLY",
            timezone="UTC",
        )
        # Request a 100-year window; the cap should kick in.
        out = expand_raw(event, _utc(2020, 1, 1), _utc(2125, 1, 1))
        # 1y forward + 6m back means we should see at most 1-2 occurrences.
        self.assertLessEqual(len(out), 2)


class OverrideTests(_Base):
    def test_cancelled_override_drops_occurrence(self):
        event = self._make(
            starts_at=_utc(2026, 6, 2, 13, 30),
            ends_at=_utc(2026, 6, 2, 14, 0),
            recurrence_rule="FREQ=WEEKLY;BYDAY=TU",
        )
        # Cancel the Tu 2026-06-09 occurrence.
        CalendarEventOccurrence.objects.create(
            event=event,
            original_start=_utc(2026, 6, 9, 13, 30),
            is_cancelled=True,
        )
        out = expand_with_overrides(event, _utc(2026, 6, 1), _utc(2026, 6, 20))
        # 3 occurrences total (2, 9, 16); cancel 9 → 2 left.
        starts = [o.starts_at for o in out]
        self.assertEqual(len(out), 2)
        self.assertIn(_utc(2026, 6, 2, 13, 30), starts)
        self.assertIn(_utc(2026, 6, 16, 13, 30), starts)

    def test_time_shift_override(self):
        event = self._make(
            starts_at=_utc(2026, 6, 2, 13, 30),
            ends_at=_utc(2026, 6, 2, 14, 0),
            recurrence_rule="FREQ=WEEKLY;BYDAY=TU",
        )
        # Move the Tu 2026-06-09 occurrence to 2026-06-10 10:00 UTC
        CalendarEventOccurrence.objects.create(
            event=event,
            original_start=_utc(2026, 6, 9, 13, 30),
            starts_at=_utc(2026, 6, 10, 10, 0),
            ends_at=_utc(2026, 6, 10, 10, 30),
        )
        out = expand_with_overrides(event, _utc(2026, 6, 8), _utc(2026, 6, 14))
        # Should see the shifted occurrence, not the original Tu slot.
        starts = [o.starts_at for o in out]
        self.assertIn(_utc(2026, 6, 10, 10, 0), starts)
        self.assertNotIn(_utc(2026, 6, 9, 13, 30), starts)


class OrphanOverrideTests(_Base):
    def test_orphan_when_count_reduced(self):
        """EC10 — RRULE COUNT=10, override at occurrence 11 → orphan."""
        event = self._make(
            starts_at=_utc(2026, 6, 1, 13, 30),
            ends_at=_utc(2026, 6, 1, 14, 0),
            recurrence_rule="FREQ=DAILY;COUNT=10",
        )
        override = CalendarEventOccurrence.objects.create(
            event=event,
            # 2026-06-11 is the 11th day → not produced by COUNT=10
            original_start=_utc(2026, 6, 11, 13, 30),
            is_cancelled=False,
        )
        self.assertTrue(is_orphan_override(event, override))

    def test_not_orphan_when_in_series(self):
        event = self._make(
            starts_at=_utc(2026, 6, 1, 13, 30),
            ends_at=_utc(2026, 6, 1, 14, 0),
            recurrence_rule="FREQ=DAILY;COUNT=10",
        )
        override = CalendarEventOccurrence.objects.create(
            event=event,
            original_start=_utc(2026, 6, 5, 13, 30),
            is_cancelled=False,
        )
        self.assertFalse(is_orphan_override(event, override))


class ShiftedOverrideInWindowTests(_Base):
    """
    An override whose ORIGINAL_START is outside the query window but whose
    shifted starts_at falls inside the window should still surface.
    """

    def test_shifted_in_window(self):
        event = self._make(
            starts_at=_utc(2026, 6, 2, 13, 30),
            ends_at=_utc(2026, 6, 2, 14, 0),
            recurrence_rule="FREQ=WEEKLY;BYDAY=TU",
        )
        # Original was 2026-06-09; we shift it forward to 2026-06-23.
        CalendarEventOccurrence.objects.create(
            event=event,
            original_start=_utc(2026, 6, 9, 13, 30),
            starts_at=_utc(2026, 6, 23, 10, 0),
            ends_at=_utc(2026, 6, 23, 10, 30),
        )
        # Query window covers only 2026-06-22..25; original_start NOT in window
        # but shifted starts_at IS.
        out = expand_with_overrides(event, _utc(2026, 6, 22), _utc(2026, 6, 25))
        starts = [o.starts_at for o in out]
        self.assertIn(_utc(2026, 6, 23, 10, 0), starts)
