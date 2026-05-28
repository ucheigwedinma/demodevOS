"""
Model-level tests for apps.internal_tasks.

Per design §14:
- EC2: status → done auto-populates completed_at; reopening clears it
- EC4: unknown @handle silently dropped
- EC5: duplicate mentions deduped
- EC7: tag "BoarD" stored lowercase
- Mention extraction matches first.last, email local, username
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Organization
from apps.internal_tasks.models import Task, TaskComment

User = get_user_model()


def _mk_user(email: str, org: Organization, **extra) -> User:
    user = User.objects.create_user(username=email, email=email, password="x", **extra)
    user.profile.organization = org
    user.profile.save(update_fields=["organization"])
    return user


class TaskModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Acme")
        cls.user = _mk_user("u@acme.test", cls.org)

    def test_defaults(self):
        task = Task.objects.create(
            organization=self.org,
            creator=self.user,
            title="Submit Q3 board pack",
        )
        self.assertEqual(task.status, Task.Status.TODO)
        self.assertEqual(task.priority, Task.Priority.MEDIUM)
        self.assertEqual(task.visibility, Task.Visibility.PRIVATE)
        self.assertEqual(task.tags, [])
        self.assertEqual(task.checklist_items, [])
        self.assertIsNone(task.completed_at)

    def test_completed_at_auto_set_on_done(self):
        """EC2 — transitioning to done populates completed_at; reopen clears it."""
        task = Task.objects.create(
            organization=self.org,
            creator=self.user,
            title="X",
        )
        self.assertIsNone(task.completed_at)

        task.status = Task.Status.DONE
        task.save()
        self.assertIsNotNone(task.completed_at)

        # Reopen
        task.status = Task.Status.TODO
        task.save()
        self.assertIsNone(task.completed_at)

    def test_tags_lowercased_on_save(self):
        """EC7 — tag 'BoarD' stored as 'board'."""
        task = Task.objects.create(
            organization=self.org,
            creator=self.user,
            title="X",
            tags=["BoarD", "Q3", "FINANCE", "  board  ", ""],
        )
        # Lowercased + trimmed + deduped, empty dropped.
        self.assertEqual(task.tags, ["board", "q3", "finance"])

    def test_tags_dedupe_preserves_order(self):
        task = Task.objects.create(
            organization=self.org,
            creator=self.user,
            title="X",
            tags=["a", "B", "A", "c", "b"],
        )
        self.assertEqual(task.tags, ["a", "b", "c"])


class TaskCommentMentionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Acme")
        cls.alice = _mk_user("alice@acme.test", cls.org, first_name="Alice", last_name="Wong")
        cls.bob = _mk_user("bob@acme.test", cls.org, first_name="Bob", last_name="Smith")
        cls.task = Task.objects.create(
            organization=cls.org,
            creator=cls.alice,
            title="X",
        )

    def test_mention_via_email_local(self):
        comment = TaskComment.objects.create(task=self.task, author=self.alice, body="@bob ping?")
        self.assertEqual(comment.mentions, [self.bob.id])

    def test_mention_via_first_name(self):
        comment = TaskComment.objects.create(task=self.task, author=self.alice, body="hey @alice")
        self.assertEqual(comment.mentions, [self.alice.id])

    def test_unknown_handle_silently_dropped(self):
        """EC4 — unknown @handle produces no mention, no error."""
        comment = TaskComment.objects.create(
            task=self.task, author=self.alice, body="@nonexistent help!"
        )
        self.assertEqual(comment.mentions, [])

    def test_duplicates_deduped(self):
        """EC5 — @joan @marco @joan → mentions has 'joan' once."""
        comment = TaskComment.objects.create(
            task=self.task, author=self.alice, body="@bob @alice @bob ?"
        )
        # Order-preserving: bob first, then alice.
        self.assertEqual(comment.mentions, [self.bob.id, self.alice.id])

    def test_empty_body_no_mentions(self):
        comment = TaskComment.objects.create(task=self.task, author=self.alice, body="")
        self.assertEqual(comment.mentions, [])
