"""
Notification trigger tests for membership state changes.

Verifies §10 table A:
- Added → 1 notification to the added user.
- Promoted (member→admin) → 1 notification.
- Removed (delete) → 1 notification.
- `notify_realtime=False` suppresses notifications.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.accounts.models import Organization
from apps.notifications.models import Notification
from apps.workspace.models import Team, TeamMembership

User = get_user_model()


class MembershipNotificationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Acme")
        cls.team = Team.objects.create(organization=cls.org, name="Squad")
        cls.user = User.objects.create_user(
            username="u@acme.test", email="u@acme.test", password="x"
        )
        cls.user.profile.organization = cls.org
        cls.user.profile.save(update_fields=["organization"])

    def setUp(self):
        Notification.objects.filter(recipient=self.user).delete()

    def test_added_to_team_creates_one_notification(self):
        TeamMembership.objects.create(
            team=self.team, user=self.user, role=TeamMembership.Role.MEMBER
        )
        notifs = Notification.objects.filter(recipient=self.user)
        self.assertEqual(notifs.count(), 1)
        self.assertIn("added to", notifs.first().title)

    def test_role_change_creates_notification(self):
        m = TeamMembership.objects.create(
            team=self.team, user=self.user, role=TeamMembership.Role.MEMBER
        )
        Notification.objects.filter(recipient=self.user).delete()
        m.role = TeamMembership.Role.ADMIN
        m.save(update_fields=["role", "updated_at"])
        notifs = Notification.objects.filter(recipient=self.user)
        self.assertEqual(notifs.count(), 1)
        self.assertIn("admin", notifs.first().title.lower())

    def test_remove_creates_notification(self):
        m = TeamMembership.objects.create(
            team=self.team, user=self.user, role=TeamMembership.Role.MEMBER
        )
        Notification.objects.filter(recipient=self.user).delete()
        m.delete()
        notifs = Notification.objects.filter(recipient=self.user)
        self.assertEqual(notifs.count(), 1)
        self.assertIn("removed", notifs.first().title.lower())

    def test_notify_realtime_false_suppresses(self):
        m = TeamMembership.objects.create(
            team=self.team,
            user=self.user,
            role=TeamMembership.Role.MEMBER,
            notify_realtime=False,
        )
        # Should have zero notifications because notify_realtime is False.
        self.assertEqual(Notification.objects.filter(recipient=self.user).count(), 0)
        m.role = TeamMembership.Role.ADMIN
        m.save(update_fields=["role", "updated_at"])
        self.assertEqual(Notification.objects.filter(recipient=self.user).count(), 0)
