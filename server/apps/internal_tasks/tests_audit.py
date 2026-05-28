"""
Audit log integration tests.

Per design §11:
- Task title/status/priority/visibility/due_date/assignee/team/completed_at/tags audited
- description NOT audited
- checklist_items NOT audited
- TaskComment audited (full record)
"""

from __future__ import annotations

from auditlog.models import LogEntry
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from apps.accounts.models import Organization
from apps.internal_tasks.models import Task, TaskComment

User = get_user_model()


def _mk_user(email, org):
    user = User.objects.create_user(username=email, email=email, password="x")
    user.profile.organization = org
    user.profile.save(update_fields=["organization"])
    return user


class TaskAuditTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Acme")
        cls.user = _mk_user("u@acme.test", cls.org)

    def test_task_create_logged(self):
        task = Task.objects.create(
            organization=self.org,
            creator=self.user,
            title="X",
        )
        ct = ContentType.objects.get_for_model(Task)
        entries = LogEntry.objects.filter(content_type=ct, object_pk=str(task.pk))
        self.assertGreaterEqual(entries.count(), 1)

    def test_status_change_logged(self):
        task = Task.objects.create(
            organization=self.org, creator=self.user, title="X"
        )
        task.status = Task.Status.DONE
        task.save()
        ct = ContentType.objects.get_for_model(Task)
        entries = LogEntry.objects.filter(
            content_type=ct,
            object_pk=str(task.pk),
            action=LogEntry.Action.UPDATE,
        )
        # Should be at least one update entry mentioning status.
        self.assertGreaterEqual(entries.count(), 1)
        self.assertTrue(
            any("status" in str(e.changes) for e in entries),
            f"Expected 'status' in audit changes; got {[e.changes for e in entries]}",
        )

    def test_description_change_NOT_logged(self):
        """Description is excluded from auditlog per design §11."""
        task = Task.objects.create(
            organization=self.org,
            creator=self.user,
            title="X",
            description="initial",
        )
        task.description = "changed"
        task.save()
        ct = ContentType.objects.get_for_model(Task)
        update_entries = LogEntry.objects.filter(
            content_type=ct, object_pk=str(task.pk), action=LogEntry.Action.UPDATE
        )
        for entry in update_entries:
            self.assertNotIn("description", str(entry.changes).lower())

    def test_checklist_change_NOT_logged(self):
        task = Task.objects.create(
            organization=self.org,
            creator=self.user,
            title="X",
            checklist_items=[{"label": "a", "checked": False}],
        )
        task.checklist_items = [
            {"label": "a", "checked": True},
            {"label": "b", "checked": False},
        ]
        task.save()
        ct = ContentType.objects.get_for_model(Task)
        update_entries = LogEntry.objects.filter(
            content_type=ct, object_pk=str(task.pk), action=LogEntry.Action.UPDATE
        )
        for entry in update_entries:
            self.assertNotIn("checklist_items", str(entry.changes).lower())

    def test_comment_create_logged(self):
        task = Task.objects.create(
            organization=self.org, creator=self.user, title="X"
        )
        comment = TaskComment.objects.create(task=task, author=self.user, body="hi")
        ct = ContentType.objects.get_for_model(TaskComment)
        entries = LogEntry.objects.filter(content_type=ct, object_pk=str(comment.pk))
        self.assertGreaterEqual(entries.count(), 1)
