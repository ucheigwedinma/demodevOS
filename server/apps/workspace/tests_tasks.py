"""
Tests for the daily-digest Celery task (apps.workspace.tasks.send_team_digests).

Verifies:
- The task only fires for orgs whose local hour matches DIGEST_LOCAL_HOUR.
- Empty digests are suppressed (no notification created).
- Email-send (here: notification creation) failures are logged, not retried.
"""

from __future__ import annotations

from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Organization
from apps.notifications.models import Notification
from apps.support_desk.models import SupportTicket
from apps.workspace.models import Team, TeamMembership
from apps.workspace.tasks import DIGEST_LOCAL_HOUR, send_team_digests

User = get_user_model()


class DigestTaskTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # NOTE: Organization has no timezone field on this codebase (A5
        # was wrong); the digest task falls back to UTC for any org without
        # one — see apps.workspace.tasks._org_local_hour.
        cls.org = Organization.objects.create(name="Acme")
        cls.user = User.objects.create_user(
            username="u@acme.test", email="u@acme.test", password="x"
        )
        cls.user.profile.organization = cls.org
        cls.user.profile.save(update_fields=["organization"])
        cls.team = Team.objects.create(organization=cls.org, name="Squad")
        TeamMembership.objects.create(
            team=cls.team,
            user=cls.user,
            role=TeamMembership.Role.OWNER,
            digest_frequency=TeamMembership.DigestFrequency.DAILY,
        )

    def setUp(self):
        Notification.objects.filter(recipient=self.user).delete()
        SupportTicket.objects.filter(team=self.team).delete()

    def _force_local_hour(self, hour: int):
        """Patch _org_local_hour to return a fixed hour."""
        return mock.patch(
            "apps.workspace.tasks._org_local_hour", return_value=hour
        )

    def test_skips_orgs_outside_window(self):
        with self._force_local_hour(12):  # not 08:00
            summary = send_team_digests()
        self.assertEqual(summary["orgs_in_window"], 0)
        self.assertEqual(summary["digests_sent"], 0)

    def test_empty_digest_suppressed(self):
        # In window, but no ticket activity.
        # Other test classes may have left orgs in the keepdb shared test DB,
        # so we assert >= 1 (our org is in the window) rather than ==.
        with self._force_local_hour(DIGEST_LOCAL_HOUR):
            summary = send_team_digests()
        self.assertGreaterEqual(summary["orgs_in_window"], 1)
        # No tickets at all → every membership processed should be an empty
        # digest, and digests_sent must be 0.
        self.assertEqual(summary["digests_sent"], 0)
        self.assertGreaterEqual(summary["skipped_empty"], 1)

    def test_digest_sent_when_activity_exists(self):
        SupportTicket.objects.create(
            organization=self.org,
            team=self.team,
            subject="A new ticket",
            description="...",
            ticket_id="T-001",
        )
        with self._force_local_hour(DIGEST_LOCAL_HOUR):
            summary = send_team_digests()
        self.assertEqual(summary["digests_sent"], 1)
        notifs = Notification.objects.filter(recipient=self.user, title__icontains="digest")
        self.assertEqual(notifs.count(), 1)

    def test_failure_logged_not_retried(self):
        SupportTicket.objects.create(
            organization=self.org,
            team=self.team,
            subject="boom",
            ticket_id="T-002",
        )
        with self._force_local_hour(DIGEST_LOCAL_HOUR), mock.patch(
            "apps.workspace.tasks._send_digest_notification",
            side_effect=Exception("boom"),
        ), mock.patch("apps.workspace.tasks.logger") as logger_mock:
            summary = send_team_digests()
        # The exception was swallowed (no raise) and logged.
        self.assertEqual(summary["digests_sent"], 0)
        self.assertTrue(logger_mock.exception.called)

    def test_digest_off_skips_membership(self):
        TeamMembership.objects.filter(team=self.team, user=self.user).update(
            digest_frequency=TeamMembership.DigestFrequency.OFF
        )
        SupportTicket.objects.create(
            organization=self.org,
            team=self.team,
            subject="x",
            ticket_id="T-003",
        )
        with self._force_local_hour(DIGEST_LOCAL_HOUR):
            summary = send_team_digests()
        self.assertEqual(summary["digests_sent"], 0)
