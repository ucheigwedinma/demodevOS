"""
Permission matrix tests per design §8.

Cells:
- Creator: can_view (yes), can_edit (yes)
- Attendee: can_view (yes), can_edit (no)
- Team member (when event has team): can_view depends on visibility
- Org member: can_view depends on visibility
- Outsider (other org): never can_view
- Secret-team gate: even visibility=org events hidden from non-members
"""

from __future__ import annotations

from datetime import datetime, timezone as dttz

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.accounts.models import Organization
from apps.calendar.models import CalendarEvent, CalendarEventAttendee
from apps.calendar.permissions import (
    can_edit_event,
    can_view_event,
    event_role_for,
)
from apps.workspace.models import Team, TeamMembership

User = get_user_model()


def _utc(year, month, day, hour=0, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=dttz.utc)


class PermissionHelperTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Acme")
        cls.other_org = Organization.objects.create(name="Other Co")

        def _mk(email, org=None):
            org = org or cls.org
            user = User.objects.create_user(username=email, email=email, password="x")
            user.profile.organization = org
            user.profile.save(update_fields=["organization"])
            return user

        cls.creator = _mk("creator@acme.test")
        cls.attendee = _mk("attendee@acme.test")
        cls.team_member = _mk("team@acme.test")
        cls.org_member = _mk("org@acme.test")
        cls.outsider = _mk("outsider@other.test", org=cls.other_org)

        cls.public_team = Team.objects.create(
            organization=cls.org, name="Public", visibility=Team.Visibility.PUBLIC
        )
        cls.secret_team = Team.objects.create(
            organization=cls.org, name="Secret", visibility=Team.Visibility.SECRET
        )
        TeamMembership.objects.create(
            team=cls.public_team, user=cls.team_member, role=TeamMembership.Role.MEMBER
        )
        TeamMembership.objects.create(
            team=cls.secret_team, user=cls.team_member, role=TeamMembership.Role.MEMBER
        )

        # Three events varying by visibility
        cls.private_event = cls._mk_event(
            visibility=CalendarEvent.Visibility.PRIVATE, team=None
        )
        cls.team_event = cls._mk_event(
            visibility=CalendarEvent.Visibility.TEAM, team=cls.public_team
        )
        cls.org_event = cls._mk_event(
            visibility=CalendarEvent.Visibility.ORG, team=None
        )
        cls.secret_team_event_org_visibility = cls._mk_event(
            visibility=CalendarEvent.Visibility.ORG, team=cls.secret_team
        )

        # Attendee row on private event
        CalendarEventAttendee.objects.create(
            event=cls.private_event, user=cls.attendee
        )
        CalendarEventAttendee.objects.create(event=cls.team_event, user=cls.attendee)

    @classmethod
    def _mk_event(cls, *, visibility, team):
        return CalendarEvent.objects.create(
            organization=cls.org,
            creator=cls.creator,
            title="X",
            starts_at=_utc(2026, 6, 3, 13, 0),
            ends_at=_utc(2026, 6, 3, 14, 0),
            visibility=visibility,
            team=team,
        )

    # ----- creator -----

    def test_creator_can_view_and_edit_everything(self):
        for event in [self.private_event, self.team_event, self.org_event]:
            self.assertTrue(can_view_event(self.creator, event))
            self.assertTrue(can_edit_event(self.creator, event))
            self.assertEqual(event_role_for(self.creator, event), "creator")

    # ----- attendee -----

    def test_attendee_can_view_not_edit(self):
        self.assertTrue(can_view_event(self.attendee, self.private_event))
        self.assertFalse(can_edit_event(self.attendee, self.private_event))
        self.assertEqual(
            event_role_for(self.attendee, self.private_event), "attendee"
        )

    # ----- private visibility -----

    def test_non_attendee_cannot_view_private(self):
        self.assertFalse(can_view_event(self.org_member, self.private_event))
        self.assertIsNone(event_role_for(self.org_member, self.private_event))

    # ----- team visibility -----

    def test_team_member_can_view_team_event(self):
        self.assertTrue(can_view_event(self.team_member, self.team_event))
        self.assertEqual(
            event_role_for(self.team_member, self.team_event), "viewer"
        )

    def test_non_team_member_cannot_view_team_event(self):
        self.assertFalse(can_view_event(self.org_member, self.team_event))

    # ----- org visibility -----

    def test_org_member_can_view_org_event(self):
        self.assertTrue(can_view_event(self.org_member, self.org_event))

    def test_outsider_cannot_view_org_event(self):
        self.assertFalse(can_view_event(self.outsider, self.org_event))

    # ----- secret-team gate -----

    def test_secret_team_gate_blocks_org_visibility(self):
        """§8-C: secret team's visibility wins over event's own visibility."""
        # Event has visibility=ORG but team has visibility=SECRET.
        # Org members not in the secret team must NOT see it.
        self.assertFalse(
            can_view_event(self.org_member, self.secret_team_event_org_visibility)
        )

    def test_secret_team_member_can_view(self):
        self.assertTrue(
            can_view_event(self.team_member, self.secret_team_event_org_visibility)
        )

    # ----- outsider -----

    def test_outsider_never_views(self):
        for event in [
            self.private_event,
            self.team_event,
            self.org_event,
            self.secret_team_event_org_visibility,
        ]:
            self.assertFalse(can_view_event(self.outsider, event))
