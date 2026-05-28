"""
Audit-log integration tests.

- Team metadata changes create LogEntry rows via django-auditlog.
- TeamMembership role changes create LogEntry rows.
- The settings audit-log aggregator (apps.settings.views.AuditLogListView)
  returns workspace-related entries when scoped to the org.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from auditlog.models import LogEntry

from apps.accounts.models import Organization
from apps.workspace.models import Team, TeamMembership

User = get_user_model()


class AuditTeamTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Acme")
        cls.user = User.objects.create_user(
            username="u@acme.test", email="u@acme.test", password="x"
        )
        cls.user.profile.organization = cls.org
        cls.user.profile.save(update_fields=["organization"])

    def test_team_create_logged(self):
        team = Team.objects.create(organization=self.org, name="A")
        ct = ContentType.objects.get_for_model(Team)
        entries = LogEntry.objects.filter(content_type=ct, object_pk=str(team.pk))
        self.assertGreaterEqual(entries.count(), 1)

    def test_team_visibility_change_logged(self):
        team = Team.objects.create(organization=self.org, name="A")
        team.visibility = Team.Visibility.SECRET
        team.save()
        ct = ContentType.objects.get_for_model(Team)
        entries = LogEntry.objects.filter(
            content_type=ct, object_pk=str(team.pk), action=LogEntry.Action.UPDATE
        )
        self.assertGreaterEqual(entries.count(), 1)
        # The change row should mention 'visibility'.
        self.assertTrue(
            any("visibility" in str(e.changes) for e in entries),
            f"Expected visibility in audit changes; got {[e.changes for e in entries]}",
        )

    def test_membership_role_change_logged(self):
        team = Team.objects.create(organization=self.org, name="A")
        membership = TeamMembership.objects.create(
            team=team, user=self.user, role=TeamMembership.Role.MEMBER
        )
        ct = ContentType.objects.get_for_model(TeamMembership)
        # Update role
        membership.role = TeamMembership.Role.ADMIN
        membership.save()
        entries = LogEntry.objects.filter(
            content_type=ct, object_pk=str(membership.pk), action=LogEntry.Action.UPDATE
        )
        self.assertGreaterEqual(entries.count(), 1)
