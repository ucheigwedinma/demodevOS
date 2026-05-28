"""
Permission-matrix tests — explicit cells from §8 of the design doc.

The §8 matrix has many cells; the API tests cover the exercise paths.
This file pins down the helper functions (team_role_for, can_*) so they
can be reused safely from other apps.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.accounts.models import Organization
from apps.workspace.models import Team, TeamMembership
from apps.workspace.permissions import (
    can_delete_team,
    can_edit_team,
    can_manage_members,
    can_transfer_team,
    can_view_team,
    team_role_for,
)

User = get_user_model()


class PermissionHelperTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Acme")

        def _mk(email):
            user = User.objects.create_user(username=email, email=email, password="x")
            user.profile.organization = cls.org
            user.profile.save(update_fields=["organization"])
            return user

        cls.owner = _mk("owner@acme.test")
        cls.admin = _mk("admin@acme.test")
        cls.member = _mk("member@acme.test")
        cls.guest = _mk("guest@acme.test")
        cls.outsider = _mk("outsider@acme.test")
        cls.team_public = Team.objects.create(
            organization=cls.org, name="Public", visibility=Team.Visibility.PUBLIC
        )
        cls.team_private = Team.objects.create(
            organization=cls.org, name="Private", visibility=Team.Visibility.PRIVATE
        )
        cls.team_secret = Team.objects.create(
            organization=cls.org, name="Secret", visibility=Team.Visibility.SECRET
        )
        for team in (cls.team_public, cls.team_private, cls.team_secret):
            TeamMembership.objects.create(team=team, user=cls.owner, role=TeamMembership.Role.OWNER)
            TeamMembership.objects.create(team=team, user=cls.admin, role=TeamMembership.Role.ADMIN)
            TeamMembership.objects.create(team=team, user=cls.member, role=TeamMembership.Role.MEMBER)
            TeamMembership.objects.create(team=team, user=cls.guest, role=TeamMembership.Role.GUEST)

    def test_team_role_for_returns_role_when_member(self):
        self.assertEqual(team_role_for(self.owner, self.team_public), "owner")
        self.assertEqual(team_role_for(self.admin, self.team_public), "admin")
        self.assertEqual(team_role_for(self.member, self.team_public), "member")
        self.assertEqual(team_role_for(self.guest, self.team_public), "guest")

    def test_team_role_for_returns_none_when_not_member(self):
        self.assertIsNone(team_role_for(self.outsider, self.team_public))

    def test_can_view_team_visibility_rules(self):
        # Public/private: any authenticated user can see metadata.
        self.assertTrue(can_view_team(self.outsider, self.team_public))
        self.assertTrue(can_view_team(self.outsider, self.team_private))
        # Secret: only members.
        self.assertFalse(can_view_team(self.outsider, self.team_secret))
        self.assertTrue(can_view_team(self.guest, self.team_secret))

    def test_can_edit_owner_admin_yes_member_guest_no(self):
        self.assertTrue(can_edit_team(self.owner, self.team_public))
        self.assertTrue(can_edit_team(self.admin, self.team_public))
        self.assertFalse(can_edit_team(self.member, self.team_public))
        self.assertFalse(can_edit_team(self.guest, self.team_public))
        self.assertFalse(can_edit_team(self.outsider, self.team_public))

    def test_can_manage_members_same_as_edit(self):
        # Per design §8, the gate is the same predicate.
        self.assertTrue(can_manage_members(self.admin, self.team_public))
        self.assertFalse(can_manage_members(self.member, self.team_public))

    def test_can_delete_only_owner(self):
        self.assertTrue(can_delete_team(self.owner, self.team_public))
        self.assertFalse(can_delete_team(self.admin, self.team_public))

    def test_can_transfer_only_owner(self):
        self.assertTrue(can_transfer_team(self.owner, self.team_public))
        self.assertFalse(can_transfer_team(self.admin, self.team_public))
