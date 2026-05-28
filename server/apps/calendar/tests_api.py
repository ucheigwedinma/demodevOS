"""
End-to-end API tests for /api/calendar/.

Per design §7 + §15:
- Window list with occurrence-flat results
- Create (caller becomes creator) + validate purpose-team coherence
- Visibility filtering on list
- Creator-only edit + delete
- Attendee CRUD with self-remove
- Cancel
- Window cap (62 days) enforced
- EC6: visibility=team with team_id=null → 400
- EC7: secret-team gate
- EC11: token rotation invalidates old
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone as dttz

from django.contrib.auth import get_user_model
from django.utils import timezone as djtimezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import Organization
from apps.calendar.models import (
    CalendarEvent,
    CalendarEventAttendee,
    CalendarEventOccurrence,
    IcalFeedToken,
)
from apps.workspace.models import Team, TeamMembership

User = get_user_model()


def _utc(year, month, day, hour=0, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=dttz.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


class CalendarAPIBase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Acme")
        cls.other_org = Organization.objects.create(name="Other")

        def _mk(email, org=None):
            org = org or cls.org
            user = User.objects.create_user(username=email, email=email, password="x")
            user.profile.organization = org
            user.profile.save(update_fields=["organization"])
            return user

        cls.creator = _mk("creator@acme.test")
        cls.attendee = _mk("attendee@acme.test")
        cls.org_member = _mk("org@acme.test")
        cls.outsider = _mk("outsider@other.test", org=cls.other_org)

    def setUp(self):
        self.client = APIClient()

    def _auth(self, user):
        self.client.force_authenticate(user=user)

    def _create_event(self, *, creator=None, **kwargs):
        defaults = dict(
            organization=self.org,
            creator=creator or self.creator,
            title="X",
            starts_at=_utc(2026, 6, 3, 13, 0),
            ends_at=_utc(2026, 6, 3, 14, 0),
            visibility=CalendarEvent.Visibility.PRIVATE,
        )
        defaults.update(kwargs)
        return CalendarEvent.objects.create(**defaults)


class EventCreateTests(CalendarAPIBase):
    def test_create_makes_caller_creator(self):
        self._auth(self.attendee)
        resp = self.client.post(
            "/api/calendar/events/",
            {
                "title": "1:1 with Jo",
                "starts_at": _iso(_utc(2026, 6, 5, 14, 0)),
                "ends_at": _iso(_utc(2026, 6, 5, 14, 30)),
                "kind": "meeting",
                "visibility": "private",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        event = CalendarEvent.objects.get(pk=resp.json()["id"])
        self.assertEqual(event.creator, self.attendee)
        self.assertEqual(event.organization, self.org)

    def test_visibility_team_requires_team_fk(self):
        """EC6."""
        self._auth(self.creator)
        resp = self.client.post(
            "/api/calendar/events/",
            {
                "title": "team thing",
                "starts_at": _iso(_utc(2026, 6, 5, 14, 0)),
                "ends_at": _iso(_utc(2026, 6, 5, 15, 0)),
                "visibility": "team",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("team", resp.json())

    def test_reminder_kind_allows_null_ends_at(self):
        self._auth(self.creator)
        resp = self.client.post(
            "/api/calendar/events/",
            {
                "title": "Submit Q3",
                "starts_at": _iso(_utc(2026, 6, 5, 14, 0)),
                "kind": "reminder",
                "visibility": "private",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)

    def test_invalid_rrule_rejected(self):
        self._auth(self.creator)
        resp = self.client.post(
            "/api/calendar/events/",
            {
                "title": "x",
                "starts_at": _iso(_utc(2026, 6, 5, 14, 0)),
                "ends_at": _iso(_utc(2026, 6, 5, 15, 0)),
                "recurrence_rule": "FREQ=NONSENSE",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class EventListTests(CalendarAPIBase):
    def test_window_required(self):
        self._auth(self.creator)
        resp = self.client.get("/api/calendar/events/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_window_cap_enforced(self):
        self._auth(self.creator)
        resp = self.client.get(
            f"/api/calendar/events/?start={_iso(_utc(2026, 1, 1))}&end={_iso(_utc(2026, 6, 1))}"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_creator_sees_own_event(self):
        self._create_event(title="My event")
        self._auth(self.creator)
        resp = self.client.get(
            f"/api/calendar/events/?start={_iso(_utc(2026, 6, 1))}&end={_iso(_utc(2026, 6, 10))}"
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        titles = [r["title"] for r in resp.json()["results"]]
        self.assertIn("My event", titles)

    def test_non_attendee_does_not_see_private(self):
        self._create_event(title="Private 1:1")
        self._auth(self.org_member)
        resp = self.client.get(
            f"/api/calendar/events/?start={_iso(_utc(2026, 6, 1))}&end={_iso(_utc(2026, 6, 10))}"
        )
        titles = [r["title"] for r in resp.json()["results"]]
        self.assertNotIn("Private 1:1", titles)

    def test_org_member_sees_org_event(self):
        self._create_event(
            title="Town hall",
            visibility=CalendarEvent.Visibility.ORG,
        )
        self._auth(self.org_member)
        resp = self.client.get(
            f"/api/calendar/events/?start={_iso(_utc(2026, 6, 1))}&end={_iso(_utc(2026, 6, 10))}"
        )
        titles = [r["title"] for r in resp.json()["results"]]
        self.assertIn("Town hall", titles)

    def test_outsider_does_not_see_org_event(self):
        self._create_event(
            title="Town hall",
            visibility=CalendarEvent.Visibility.ORG,
        )
        self._auth(self.outsider)
        resp = self.client.get(
            f"/api/calendar/events/?start={_iso(_utc(2026, 6, 1))}&end={_iso(_utc(2026, 6, 10))}"
        )
        titles = [r["title"] for r in resp.json()["results"]]
        self.assertNotIn("Town hall", titles)

    def test_recurring_event_expanded(self):
        self._create_event(
            title="Standup",
            starts_at=_utc(2026, 6, 1, 13, 0),
            ends_at=_utc(2026, 6, 1, 13, 30),
            recurrence_rule="FREQ=DAILY;COUNT=5",
            visibility=CalendarEvent.Visibility.ORG,
        )
        self._auth(self.creator)
        resp = self.client.get(
            f"/api/calendar/events/?start={_iso(_utc(2026, 6, 1))}&end={_iso(_utc(2026, 6, 10))}"
        )
        self.assertEqual(resp.status_code, 200)
        results = resp.json()["results"]
        # 5 occurrences
        standups = [r for r in results if r["title"] == "Standup"]
        self.assertEqual(len(standups), 5)


class EventEditTests(CalendarAPIBase):
    def test_creator_can_patch(self):
        event = self._create_event(title="old")
        self._auth(self.creator)
        resp = self.client.patch(
            f"/api/calendar/events/{event.pk}/",
            {"title": "new"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        event.refresh_from_db()
        self.assertEqual(event.title, "new")

    def test_attendee_cannot_patch(self):
        event = self._create_event(title="x")
        CalendarEventAttendee.objects.create(event=event, user=self.attendee)
        self._auth(self.attendee)
        resp = self.client.patch(
            f"/api/calendar/events/{event.pk}/",
            {"title": "hacked"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_creator_can_delete(self):
        event = self._create_event(title="x", visibility=CalendarEvent.Visibility.ORG)
        self._auth(self.creator)
        resp = self.client.delete(f"/api/calendar/events/{event.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CalendarEvent.objects.filter(pk=event.pk).exists())

    def test_org_member_cannot_delete_org_event(self):
        event = self._create_event(title="x", visibility=CalendarEvent.Visibility.ORG)
        self._auth(self.org_member)
        resp = self.client.delete(f"/api/calendar/events/{event.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_cancel(self):
        event = self._create_event()
        self._auth(self.creator)
        resp = self.client.post(f"/api/calendar/events/{event.pk}/cancel/")
        self.assertEqual(resp.status_code, 200)
        event.refresh_from_db()
        self.assertTrue(event.is_cancelled)


class AttendeeTests(CalendarAPIBase):
    def test_creator_adds_attendee(self):
        event = self._create_event()
        self._auth(self.creator)
        resp = self.client.post(
            f"/api/calendar/events/{event.pk}/attendees/",
            {"user_id": self.attendee.id},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(
            CalendarEventAttendee.objects.filter(event=event, user=self.attendee).exists()
        )

    def test_idempotent_add(self):
        """EC9 — adding same user twice doesn't dupe."""
        event = self._create_event()
        self._auth(self.creator)
        url = f"/api/calendar/events/{event.pk}/attendees/"
        self.client.post(url, {"user_id": self.attendee.id}, format="json")
        resp = self.client.post(url, {"user_id": self.attendee.id}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            CalendarEventAttendee.objects.filter(event=event).count(), 1
        )

    def test_cross_org_attendee_rejected(self):
        event = self._create_event()
        self._auth(self.creator)
        resp = self.client.post(
            f"/api/calendar/events/{event.pk}/attendees/",
            {"user_id": self.outsider.id},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_attendee_self_remove(self):
        event = self._create_event()
        CalendarEventAttendee.objects.create(event=event, user=self.attendee)
        self._auth(self.attendee)
        resp = self.client.delete(
            f"/api/calendar/events/{event.pk}/attendees/{self.attendee.id}/"
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            CalendarEventAttendee.objects.filter(event=event, user=self.attendee).exists()
        )

    def test_non_creator_cannot_remove_others(self):
        event = self._create_event()
        CalendarEventAttendee.objects.create(event=event, user=self.attendee)
        CalendarEventAttendee.objects.create(event=event, user=self.org_member)
        # attendee tries to remove org_member
        self._auth(self.attendee)
        resp = self.client.delete(
            f"/api/calendar/events/{event.pk}/attendees/{self.org_member.id}/"
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class OccurrenceTests(CalendarAPIBase):
    def test_creator_can_cancel_occurrence(self):
        event = self._create_event(
            starts_at=_utc(2026, 6, 1, 13, 0),
            ends_at=_utc(2026, 6, 1, 14, 0),
            recurrence_rule="FREQ=WEEKLY",
        )
        self._auth(self.creator)
        original = _utc(2026, 6, 8, 13, 0)
        resp = self.client.post(
            f"/api/calendar/events/{event.pk}/occurrences/",
            {"original_start": _iso(original), "is_cancelled": True},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        override = CalendarEventOccurrence.objects.get(event=event, original_start=original)
        self.assertTrue(override.is_cancelled)

    def test_non_creator_cannot_override(self):
        event = self._create_event(
            starts_at=_utc(2026, 6, 1, 13, 0),
            ends_at=_utc(2026, 6, 1, 14, 0),
            recurrence_rule="FREQ=WEEKLY",
            visibility=CalendarEvent.Visibility.ORG,
        )
        self._auth(self.org_member)
        resp = self.client.post(
            f"/api/calendar/events/{event.pk}/occurrences/",
            {
                "original_start": _iso(_utc(2026, 6, 8, 13, 0)),
                "is_cancelled": True,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class FeedTokenTests(CalendarAPIBase):
    def test_rotate_token_invalidates_old(self):
        """EC11 — old token immediately stops working after rotation."""
        self._auth(self.creator)
        # First rotation creates a token
        r1 = self.client.post("/api/calendar/feed/rotate-token/")
        self.assertEqual(r1.status_code, 200, r1.content)
        token1 = r1.json()["token"]
        # Confirm token1 hits the feed
        f1 = self.client.get(f"/api/calendar/feed/?token={token1}")
        self.assertEqual(f1.status_code, 200)
        # Rotate again
        r2 = self.client.post("/api/calendar/feed/rotate-token/")
        token2 = r2.json()["token"]
        self.assertNotEqual(token1, token2)
        # Old token no longer works
        f1b = self.client.get(f"/api/calendar/feed/?token={token1}")
        self.assertEqual(f1b.status_code, 404)
        # New one works
        f2 = self.client.get(f"/api/calendar/feed/?token={token2}")
        self.assertEqual(f2.status_code, 200)
