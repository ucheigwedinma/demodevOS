"""
Due-date reminder Celery task tests.

Per design §10 + §14:
- Reminders fire only at 9am org-local
- Only for tasks due tomorrow or today
- Done tasks skipped (EC11)
- Idempotency: 23h Notification lookback (EC12)
- Goes through dispatch_workflow_notification
"""

from __future__ import annotations

from datetime import date, timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Organization
from apps.internal_tasks.models import Task
from apps.internal_tasks.tasks import (
    REMINDER_LOCAL_HOUR,
    dispatch_due_reminders,
)
from apps.notifications.models import Notification

User = get_user_model()


def _mk_user(email, org):
    user = User.objects.create_user(username=email, email=email, password="x")
    user.profile.organization = org
    user.profile.save(update_fields=["organization"])
    return user


class DueReminderTaskTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Acme")
        cls.user = _mk_user("u@acme.test", cls.org)

    def setUp(self):
        Notification.objects.filter(recipient=self.user).delete()

    def _force_hour(self, hour: int):
        return mock.patch(
            "apps.internal_tasks.tasks._org_local_hour", return_value=hour
        )

    def _force_date(self, d: date):
        return mock.patch(
            "apps.internal_tasks.tasks._org_local_date", return_value=d
        )

    def test_skips_outside_9am_window(self):
        Task.objects.create(
            organization=self.org,
            creator=self.user,
            assignee=self.user,
            title="X",
            due_date=date.today(),
            status="todo",
        )
        with self._force_hour(12):  # not 9am
            with mock.patch(
                "apps.internal_tasks.tasks.dispatch_workflow_notification"
            ) as mock_dispatch:
                summary = dispatch_due_reminders()
        self.assertEqual(mock_dispatch.call_count, 0)
        self.assertEqual(summary["orgs_in_window"], 0)

    def test_fires_for_due_today(self):
        today = date.today()
        Task.objects.create(
            organization=self.org,
            creator=self.user,
            assignee=self.user,
            title="DueToday",
            due_date=today,
            status="todo",
        )
        with self._force_hour(REMINDER_LOCAL_HOUR), self._force_date(today):
            with mock.patch(
                "apps.internal_tasks.tasks.dispatch_workflow_notification"
            ) as mock_dispatch:
                summary = dispatch_due_reminders()
        self.assertEqual(mock_dispatch.call_count, 1)
        self.assertEqual(summary["reminders_sent"], 1)

    def test_fires_for_due_tomorrow(self):
        today = date.today()
        tomorrow = today + timedelta(days=1)
        Task.objects.create(
            organization=self.org,
            creator=self.user,
            assignee=self.user,
            title="DueTomorrow",
            due_date=tomorrow,
            status="todo",
        )
        with self._force_hour(REMINDER_LOCAL_HOUR), self._force_date(today):
            with mock.patch(
                "apps.internal_tasks.tasks.dispatch_workflow_notification"
            ) as mock_dispatch:
                summary = dispatch_due_reminders()
        self.assertEqual(mock_dispatch.call_count, 1)
        self.assertEqual(summary["reminders_sent"], 1)

    def test_done_tasks_skipped(self):
        """EC11 — status=done is excluded from the reminder query."""
        today = date.today()
        Task.objects.create(
            organization=self.org,
            creator=self.user,
            assignee=self.user,
            title="DoneToday",
            due_date=today,
            status="done",
        )
        with self._force_hour(REMINDER_LOCAL_HOUR), self._force_date(today):
            with mock.patch(
                "apps.internal_tasks.tasks.dispatch_workflow_notification"
            ) as mock_dispatch:
                summary = dispatch_due_reminders()
        self.assertEqual(mock_dispatch.call_count, 0)
        self.assertEqual(summary["tasks_scanned"], 0)

    def test_idempotency_via_23h_lookback(self):
        """EC12 — skip if a TASK_REMINDER notification exists for the same user+task in last 23h."""
        today = date.today()
        task = Task.objects.create(
            organization=self.org,
            creator=self.user,
            assignee=self.user,
            title="DueToday",
            due_date=today,
            status="todo",
        )
        # Pre-create a recent notification for this task.
        Notification.objects.create(
            recipient=self.user,
            organization=self.org,
            title="prior",
            message="x",
            category=Notification.Category.TASK_REMINDER,
            link_url=f"/internal-tasks/{task.pk}",
        )
        with self._force_hour(REMINDER_LOCAL_HOUR), self._force_date(today):
            with mock.patch(
                "apps.internal_tasks.tasks.dispatch_workflow_notification"
            ) as mock_dispatch:
                summary = dispatch_due_reminders()
        self.assertEqual(mock_dispatch.call_count, 0)
        self.assertEqual(summary["skipped_idempotent"], 1)

    def test_unassigned_falls_back_to_creator(self):
        """When assignee is null, the creator is the recipient (best-effort)."""
        today = date.today()
        Task.objects.create(
            organization=self.org,
            creator=self.user,
            assignee=None,
            title="Unassigned",
            due_date=today,
            status="todo",
        )
        with self._force_hour(REMINDER_LOCAL_HOUR), self._force_date(today):
            with mock.patch(
                "apps.internal_tasks.tasks.dispatch_workflow_notification"
            ) as mock_dispatch:
                summary = dispatch_due_reminders()
        self.assertEqual(mock_dispatch.call_count, 1)
        call = mock_dispatch.call_args
        self.assertEqual(call.kwargs["recipients"][0], self.user)
