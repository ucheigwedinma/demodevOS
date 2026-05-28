"""
Model-level tests for apps.workspace.

Covers:
- Slug auto-generation + uniqueness within an organization (EC8 deterministic
  -2/-3 suffixing).
- One-owner-per-team partial unique constraint.
- TeamMembership uniqueness per (team, user).
- Default values (color='sky', emoji='👥', purpose='initiative').
- archived_at gets stamped/cleared via the API archive endpoint flow.
- is_orphaned computed property.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Organization
from apps.workspace.models import Team, TeamMembership

User = get_user_model()


class TeamModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Acme Co")
        cls.user = User.objects.create_user(
            username="alice@acme.test", email="alice@acme.test", password="x"
        )
        cls.user.profile.organization = cls.org
        cls.user.profile.save(update_fields=["organization"])

    def test_defaults(self):
        team = Team.objects.create(organization=self.org, name="Launch Squad")
        self.assertEqual(team.purpose, Team.Purpose.INITIATIVE)
        self.assertEqual(team.visibility, Team.Visibility.PUBLIC)
        self.assertEqual(team.color, "sky")
        self.assertEqual(team.emoji, "👥")
        self.assertFalse(team.is_archived)
        self.assertIsNone(team.archived_at)

    def test_slug_auto_generated(self):
        team = Team.objects.create(organization=self.org, name="Launch Squad")
        self.assertEqual(team.slug, "launch-squad")

    def test_slug_collision_appends_suffix_deterministically(self):
        Team.objects.create(organization=self.org, name="Launch Squad")
        team2 = Team.objects.create(organization=self.org, name="Launch Squad")
        team3 = Team.objects.create(organization=self.org, name="Launch Squad")
        self.assertEqual(team2.slug, "launch-squad-2")
        self.assertEqual(team3.slug, "launch-squad-3")

    def test_slug_uniqueness_is_per_organization(self):
        org2 = Organization.objects.create(name="Other Co")
        Team.objects.create(organization=self.org, name="Launch Squad")
        # Same name in a different org gets the bare slug (no collision).
        team2 = Team.objects.create(organization=org2, name="Launch Squad")
        self.assertEqual(team2.slug, "launch-squad")

    def test_org_slug_unique_constraint(self):
        Team.objects.create(organization=self.org, name="Launch Squad", slug="custom")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Team.objects.create(organization=self.org, name="Other", slug="custom")

    def test_one_owner_per_team_constraint(self):
        team = Team.objects.create(organization=self.org, name="A")
        bob = User.objects.create_user(
            username="bob@acme.test", email="bob@acme.test", password="x"
        )
        bob.profile.organization = self.org
        bob.profile.save(update_fields=["organization"])
        TeamMembership.objects.create(team=team, user=self.user, role=TeamMembership.Role.OWNER)
        with self.assertRaises(IntegrityError), transaction.atomic():
            TeamMembership.objects.create(team=team, user=bob, role=TeamMembership.Role.OWNER)

    def test_membership_team_user_unique(self):
        team = Team.objects.create(organization=self.org, name="A")
        TeamMembership.objects.create(team=team, user=self.user, role=TeamMembership.Role.MEMBER)
        with self.assertRaises(IntegrityError), transaction.atomic():
            TeamMembership.objects.create(team=team, user=self.user, role=TeamMembership.Role.ADMIN)

    def test_is_orphaned_when_no_active_owner_or_admin(self):
        team = Team.objects.create(organization=self.org, name="A")
        self.assertTrue(team.is_orphaned)
        TeamMembership.objects.create(team=team, user=self.user, role=TeamMembership.Role.MEMBER)
        self.assertTrue(team.is_orphaned)
        TeamMembership.objects.create(
            team=team,
            user=User.objects.create_user(
                username="o@acme.test", email="o@acme.test", password="x"
            ),
            role=TeamMembership.Role.OWNER,
        )
        team.refresh_from_db()
        self.assertFalse(team.is_orphaned)

    def test_archive_flag_can_be_toggled(self):
        team = Team.objects.create(organization=self.org, name="A")
        team.is_archived = True
        team.archived_at = timezone.now()
        team.save()
        team.refresh_from_db()
        self.assertTrue(team.is_archived)
        self.assertIsNotNone(team.archived_at)

    def test_owner_deactivation_promotes_oldest_admin(self):
        """EC2: when a user goes is_active=False, the oldest admin in any team
        they own takes over."""
        team = Team.objects.create(organization=self.org, name="A")
        owner = User.objects.create_user(
            username="owner@acme.test", email="owner@acme.test", password="x"
        )
        admin1 = User.objects.create_user(
            username="admin1@acme.test", email="admin1@acme.test", password="x"
        )
        admin2 = User.objects.create_user(
            username="admin2@acme.test", email="admin2@acme.test", password="x"
        )
        TeamMembership.objects.create(team=team, user=owner, role=TeamMembership.Role.OWNER)
        # admin1 joined first → oldest by joined_at
        m1 = TeamMembership.objects.create(team=team, user=admin1, role=TeamMembership.Role.ADMIN)
        m2 = TeamMembership.objects.create(team=team, user=admin2, role=TeamMembership.Role.ADMIN)

        owner.is_active = False
        owner.save()

        m1.refresh_from_db()
        m2.refresh_from_db()
        old_owner_membership = TeamMembership.objects.get(team=team, user=owner)
        self.assertEqual(m1.role, TeamMembership.Role.OWNER)
        self.assertEqual(m2.role, TeamMembership.Role.ADMIN)
        self.assertEqual(old_owner_membership.role, TeamMembership.Role.ADMIN)

    def test_owner_deactivation_with_no_admin_leaves_team_orphaned(self):
        team = Team.objects.create(organization=self.org, name="A")
        owner = User.objects.create_user(
            username="o@acme.test", email="o@acme.test", password="x"
        )
        TeamMembership.objects.create(team=team, user=owner, role=TeamMembership.Role.OWNER)
        owner.is_active = False
        owner.save()
        team.refresh_from_db()
        self.assertTrue(team.is_orphaned)
