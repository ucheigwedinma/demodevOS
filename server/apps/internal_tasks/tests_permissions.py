"""
Permission matrix tests per design §8.

Cells:
- Creator: view + edit + delete
- Assignee: view + edit (not delete, not change visibility/team)
- Team member (visibility=team): view if visible
- Org member (visibility=org): view
- Outsider: never view
- Secret-team gate wins over event visibility
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.accounts.models import Organization
from apps.internal_tasks.models import Task
from apps.internal_tasks.permissions import (
    can_delete_task,
    can_edit_task,
    can_view_task,
    task_role_for,
)
from apps.workspace.models import Team, TeamMembership

User = get_user_model()


def _mk_user(email, org):
    user = User.objects.create_user(username=email, email=email, password="x")
    user.profile.organization = org
    user.profile.save(update_fields=["organization"])
    return user


class PermissionHelperTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Acme")
        cls.other_org = Organization.objects.create(name="Other")

        cls.creator = _mk_user("creator@acme.test", cls.org)
        cls.assignee = _mk_user("assignee@acme.test", cls.org)
        cls.team_member = _mk_user("team@acme.test", cls.org)
        cls.org_member = _mk_user("org@acme.test", cls.org)
        cls.outsider = User.objects.create_user(
            username="o@other.test", email="o@other.test", password="x"
        )
        cls.outsider.profile.organization = cls.other_org
        cls.outsider.profile.save(update_fields=["organization"])

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

    def _mk_task(self, *, visibility=Task.Visibility.PRIVATE, team=None, assignee=None):
        return Task.objects.create(
            organization=self.org,
            creator=self.creator,
            assignee=assignee,
            title="X",
            visibility=visibility,
            team=team,
        )

    # ----- creator -----

    def test_creator_can_view_edit_delete(self):
        task = self._mk_task()
        self.assertTrue(can_view_task(self.creator, task))
        self.assertTrue(can_edit_task(self.creator, task))
        self.assertTrue(can_delete_task(self.creator, task))
        self.assertEqual(task_role_for(self.creator, task), "creator")

    # ----- assignee -----

    def test_assignee_can_view_and_edit_not_delete(self):
        task = self._mk_task(assignee=self.assignee)
        self.assertTrue(can_view_task(self.assignee, task))
        self.assertTrue(can_edit_task(self.assignee, task))
        self.assertFalse(can_delete_task(self.assignee, task))
        self.assertEqual(task_role_for(self.assignee, task), "assignee")

    # ----- private visibility -----

    def test_non_assignee_cannot_view_private(self):
        task = self._mk_task(assignee=self.assignee)
        self.assertFalse(can_view_task(self.org_member, task))
        self.assertIsNone(task_role_for(self.org_member, task))

    # ----- team visibility -----

    def test_team_member_can_view_team_task(self):
        task = self._mk_task(
            visibility=Task.Visibility.TEAM, team=self.public_team
        )
        self.assertTrue(can_view_task(self.team_member, task))
        self.assertEqual(task_role_for(self.team_member, task), "viewer")

    def test_non_team_member_cannot_view_team_task(self):
        task = self._mk_task(
            visibility=Task.Visibility.TEAM, team=self.public_team
        )
        self.assertFalse(can_view_task(self.org_member, task))

    # ----- org visibility -----

    def test_org_member_can_view_org_task(self):
        task = self._mk_task(visibility=Task.Visibility.ORG)
        self.assertTrue(can_view_task(self.org_member, task))

    def test_outsider_never_views(self):
        task = self._mk_task(visibility=Task.Visibility.ORG)
        self.assertFalse(can_view_task(self.outsider, task))

    # ----- secret-team gate -----

    def test_secret_team_gate_wins_over_org_visibility(self):
        """EC3 — secret team's visibility overrides task's own visibility."""
        task = self._mk_task(visibility=Task.Visibility.ORG, team=self.secret_team)
        self.assertFalse(can_view_task(self.org_member, task))
        # The team member is in the secret team, so they can see it.
        self.assertTrue(can_view_task(self.team_member, task))
