"""
Meetings overlay endpoint tests.

Per design §13:
- Returns flattened shape with source='meeting'
- Window-bounded query
- Org-scoped (inherits apps.meetings rules)
- Empty when no meetings in window
"""

from __future__ import annotations

from datetime import datetime, timezone as dttz

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import Organization
from apps.meetings.models import Meeting

User = get_user_model()


def _utc(year, month, day, hour=0, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=dttz.utc)


def _iso(dt):
    return dt.isoformat().replace("+00:00", "Z")


class MeetingsOverlayTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Acme")
        cls.other_org = Organization.objects.create(name="Other")
        cls.user = User.objects.create_user(
            username="u@acme.test", email="u@acme.test", password="x"
        )
        cls.user.profile.organization = cls.org
        cls.user.profile.save(update_fields=["organization"])
        cls.outsider = User.objects.create_user(
            username="o@other.test", email="o@other.test", password="x"
        )
        cls.outsider.profile.organization = cls.other_org
        cls.outsider.profile.save(update_fields=["organization"])

    def setUp(self):
        self.client = APIClient()

    def _make_meeting(self, *, org=None, title="Site Progress Mtg", scheduled_start=None):
        org = org or self.org
        scheduled_start = scheduled_start or _utc(2026, 6, 5, 13, 0)
        return Meeting.objects.create(
            organization=org,
            title=title,
            scheduled_start=scheduled_start,
            scheduled_end=scheduled_start.replace(hour=scheduled_start.hour + 1),
        )

    def test_overlay_returns_meeting_rows(self):
        self._make_meeting()
        self.client.force_authenticate(user=self.user)
        resp = self.client.get(
            f"/api/calendar/meetings-overlay/?start={_iso(_utc(2026, 6, 1))}&end={_iso(_utc(2026, 6, 10))}"
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        results = resp.json()["results"]
        self.assertEqual(len(results), 1)
        row = results[0]
        self.assertEqual(row["source"], "meeting")
        self.assertEqual(row["kind"], "meeting")
        self.assertIn("edit_url", row)
        self.assertEqual(row["edit_in_app"], "meetings")

    def test_overlay_window_filters(self):
        # Meeting outside window
        self._make_meeting(scheduled_start=_utc(2026, 1, 1, 13, 0))
        self.client.force_authenticate(user=self.user)
        resp = self.client.get(
            f"/api/calendar/meetings-overlay/?start={_iso(_utc(2026, 6, 1))}&end={_iso(_utc(2026, 6, 10))}"
        )
        self.assertEqual(len(resp.json()["results"]), 0)

    def test_overlay_org_scoped(self):
        """Outsider should not see Acme's meetings."""
        self._make_meeting()
        self.client.force_authenticate(user=self.outsider)
        resp = self.client.get(
            f"/api/calendar/meetings-overlay/?start={_iso(_utc(2026, 6, 1))}&end={_iso(_utc(2026, 6, 10))}"
        )
        # Outsider has no profile.organization set? Let's verify the count = 0
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["results"]), 0)
