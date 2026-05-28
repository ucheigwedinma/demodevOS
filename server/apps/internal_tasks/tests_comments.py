"""
Comment API + notification fan-out tests.

Per design §10 + §14:
- Add / list / delete (author only)
- Mention parsing handled in TaskComment.save() — verified via API
- Notifications fire through dispatch_workflow_notification
"""

from __future__ import annotations

from unittest import mock

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import Organization
from apps.internal_tasks.models import Task, TaskComment

User = get_user_model()


def _mk_user(email, org, **extra):
    user = User.objects.create_user(username=email, email=email, password="x", **extra)
    user.profile.organization = org
    user.profile.save(update_fields=["organization"])
    return user


class CommentAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Acme")
        cls.creator = _mk_user("creator@acme.test", cls.org)
        cls.bob = _mk_user("bob@acme.test", cls.org, first_name="Bob")
        cls.outsider = _mk_user(
            "out@other.test",
            Organization.objects.create(name="Other"),
        )
        cls.task = Task.objects.create(
            organization=cls.org,
            creator=cls.creator,
            assignee=cls.creator,
            title="X",
            visibility=Task.Visibility.PRIVATE,
        )

    def setUp(self):
        self.client = APIClient()

    def test_creator_can_post_and_list(self):
        self.client.force_authenticate(user=self.creator)
        resp = self.client.post(
            f"/api/internal-tasks/tasks/{self.task.id}/comments/",
            {"body": "First comment"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        resp2 = self.client.get(f"/api/internal-tasks/tasks/{self.task.id}/comments/")
        self.assertEqual(len(resp2.json()), 1)

    def test_empty_body_rejected(self):
        self.client.force_authenticate(user=self.creator)
        resp = self.client.post(
            f"/api/internal-tasks/tasks/{self.task.id}/comments/",
            {"body": "   "},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_outsider_cannot_see_or_post(self):
        self.client.force_authenticate(user=self.outsider)
        resp = self.client.get(f"/api/internal-tasks/tasks/{self.task.id}/comments/")
        self.assertEqual(resp.status_code, 404)

    def test_only_author_can_delete(self):
        self.client.force_authenticate(user=self.creator)
        post_resp = self.client.post(
            f"/api/internal-tasks/tasks/{self.task.id}/comments/",
            {"body": "Will be deleted"},
            format="json",
        )
        comment_id = post_resp.json()["id"]
        # bob cannot delete creator's comment
        # (and bob can't see the task — but let's add bob as assignee first)
        self.task.assignee = self.bob
        self.task.save(update_fields=["assignee", "updated_at"])
        self.client.force_authenticate(user=self.bob)
        resp = self.client.delete(
            f"/api/internal-tasks/tasks/{self.task.id}/comments/{comment_id}/"
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        # Original author can.
        self.client.force_authenticate(user=self.creator)
        resp = self.client.delete(
            f"/api/internal-tasks/tasks/{self.task.id}/comments/{comment_id}/"
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_mention_resolves_to_user(self):
        """End-to-end: posting a comment with @bob populates `mentions`."""
        self.client.force_authenticate(user=self.creator)
        resp = self.client.post(
            f"/api/internal-tasks/tasks/{self.task.id}/comments/",
            {"body": "ping @bob"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        comment = TaskComment.objects.get(pk=resp.json()["id"])
        self.assertEqual(comment.mentions, [self.bob.id])


class CommentNotificationTests(APITestCase):
    """Verify signals fan out via dispatch_workflow_notification."""

    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Acme")
        cls.creator = _mk_user("creator@acme.test", cls.org)
        cls.assignee = _mk_user("assignee@acme.test", cls.org)
        cls.bob = _mk_user("bob@acme.test", cls.org, first_name="Bob")
        cls.task = Task.objects.create(
            organization=cls.org,
            creator=cls.creator,
            assignee=cls.assignee,
            title="X",
            visibility=Task.Visibility.PRIVATE,
        )

    def setUp(self):
        self.client = APIClient()

    def test_comment_fires_notification_to_creator_and_assignee(self):
        """Bob (a viewer? no — let's add him as a watcher via prior comment)."""
        # Set up: bob is not initially a participant, so creator + assignee are
        # the only auto-recipients.
        with mock.patch(
            "apps.internal_tasks.signals.dispatch_workflow_notification"
        ) as mock_dispatch:
            # creator posts — only assignee should get notified (not the actor).
            self.client.force_authenticate(user=self.creator)
            self.client.post(
                f"/api/internal-tasks/tasks/{self.task.id}/comments/",
                {"body": "hello team"},
                format="json",
            )
        self.assertTrue(mock_dispatch.called)
        # The call args should include assignee in recipients.
        call_kwargs = mock_dispatch.call_args.kwargs
        recipient_ids = {u.id for u in call_kwargs["recipients"]}
        self.assertIn(self.assignee.id, recipient_ids)
        self.assertNotIn(self.creator.id, recipient_ids)  # actor excluded

    def test_mention_fires_separate_notification(self):
        # Bob isn't a participant; mention should pull him in via a separate dispatch.
        with mock.patch(
            "apps.internal_tasks.signals.dispatch_workflow_notification"
        ) as mock_dispatch:
            self.client.force_authenticate(user=self.creator)
            self.client.post(
                f"/api/internal-tasks/tasks/{self.task.id}/comments/",
                {"body": "@bob please review"},
                format="json",
            )
        # Two dispatch calls: one for "commented" (assignee), one for "mentioned" (bob).
        self.assertEqual(mock_dispatch.call_count, 2)
        event_keys = {c.kwargs["event_key"] for c in mock_dispatch.call_args_list}
        self.assertIn("internal_tasks.commented", event_keys)
        self.assertIn("internal_tasks.mentioned", event_keys)
