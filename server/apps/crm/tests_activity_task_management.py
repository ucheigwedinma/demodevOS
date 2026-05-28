from __future__ import annotations

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Organization
from apps.crm.models import FollowUpTask, Lead

User = get_user_model()


class ActivityTaskManagementTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="CRM Activity Task Test Org")

        self.admin = User.objects.create_superuser(
            username="crm-admin@example.com",
            email="crm-admin@example.com",
            password="Pass123!",
        )
        self._configure_profile(self.admin, role="admin", job_title="Sales Manager")
        self.client.force_authenticate(self.admin)

        self.logistics_user = User.objects.create_user(
            username="logistics@example.com",
            email="logistics@example.com",
            password="Pass123!",
        )
        self._configure_profile(
            self.logistics_user,
            role="member",
            job_title="Logistics Coordinator",
        )

        self.lead = Lead.objects.create(
            organization=self.org,
            first_name="Lara",
            last_name="Ifeanyi",
            email="lara.ifeanyi@example.com",
            phone="+1-555-0100",
            assigned_to=self.admin,
            status=Lead.Status.ACTIVE,
            pipeline_stage=Lead.PipelineStage.QUALIFIED,
        )

    def _configure_profile(self, user, *, role: str, job_title: str):
        profile = user.profile
        profile.organization = self.org
        profile.role = role
        profile.job_title = job_title
        profile.user_status = "active"
        profile.mfa_enabled = True
        profile.save(
            update_fields=[
                "organization",
                "role",
                "job_title",
                "user_status",
                "mfa_enabled",
            ]
        )

    @patch("apps.crm.views.send_mail")
    @patch("apps.notifications.services.dispatch_workflow_notification")
    def test_site_visit_activity_logs_and_triggers_automation(self, mock_dispatch, mock_send_mail):
        due_at = timezone.now() + timezone.timedelta(days=1)
        payload = {
            "lead": self.lead.id,
            "activity_type": "site_visit",
            "subject": "Inspection at Oak Ridge Plot 12",
            "description": "Client requested Saturday walkthrough.",
            "scheduled_at": due_at.isoformat(),
        }
        res = self.client.post("/api/crm/activities/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)

        task = FollowUpTask.objects.filter(lead=self.lead).order_by("-id").first()
        self.assertIsNotNone(task)
        self.assertEqual(task.status, FollowUpTask.Status.PENDING)
        self.assertEqual(task.assigned_to_id, self.lead.assigned_to_id)
        self.assertIn("[activity:", task.notes)

        mock_send_mail.assert_called_once()

        event_keys = [kwargs.get("event_key") for _, kwargs in mock_dispatch.call_args_list]
        self.assertIn("crm_site_visit_scheduled", event_keys)
        self.assertIn("crm_activity_task_assigned", event_keys)

    @patch("apps.notifications.services.dispatch_workflow_notification")
    def test_manual_task_creation_assigns_task(self, _mock_dispatch):
        due_at = timezone.now() + timezone.timedelta(hours=4)
        payload = {
            "lead": self.lead.id,
            "assigned_to": self.logistics_user.id,
            "due_at": due_at.isoformat(),
            "notes": "Confirm transport and arrival time with client.",
        }
        res = self.client.post("/api/crm/follow-up-tasks/manual-create/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertEqual(res.data["assigned_to"], self.logistics_user.id)
        self.assertEqual(res.data["lead"], self.lead.id)

        task = FollowUpTask.objects.get(id=res.data["id"])
        self.assertEqual(task.rule.name, "Manual Activity Task")
        self.assertEqual(task.assigned_to_id, self.logistics_user.id)

    def test_overview_endpoint_returns_expected_shape(self):
        FollowUpTask.objects.create(
            rule=self._manual_rule_for_org(),
            lead=self.lead,
            assigned_to=self.admin,
            due_at=timezone.now() + timezone.timedelta(hours=2),
            notes="Prepare deck before client follow-up.",
        )
        res = self.client.get("/api/crm/activities-tasks/overview/")
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.assertIn("calendar_integration", res.data)
        self.assertIn("timeline", res.data)
        self.assertIn("open_task_count", res.data)

    def _manual_rule_for_org(self):
        from apps.crm.models import FollowUpRule

        rule, _created = FollowUpRule.objects.get_or_create(
            organization=self.org,
            name="Manual Activity Task",
            defaults={
                "description": "Manual CRM activity task assignment and reminders.",
                "trigger_stage": Lead.PipelineStage.INQUIRY,
                "follow_up_within_hours": 24,
                "required_activity_type": "follow_up",
                "auto_assign_to_owner": False,
                "is_active": True,
            },
        )
        return rule
