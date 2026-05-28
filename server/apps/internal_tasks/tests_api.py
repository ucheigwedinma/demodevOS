"""
End-to-end API tests for /api/internal-tasks/.

Per design §7 + §14:
- Create makes caller creator + assignee defaults to creator
- Visibility filtering on list
- Filters: status, priority, tag, mine, overdue
- EC1: visibility=team with team_id=null → 400
- EC9: > 100 checklist items rejected
- Creator OR assignee can edit; only creator can delete; only creator can change team/visibility
- complete toggle, assign, checklist replace
- Tag autocomplete endpoint
"""

from __future__ import annotations

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import Organization
from apps.internal_tasks.models import Task

User = get_user_model()


def _mk_user(email, org):
    user = User.objects.create_user(username=email, email=email, password="x")
    user.profile.organization = org
    user.profile.save(update_fields=["organization"])
    return user


class InternalTasksAPIBase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Acme")
        cls.other_org = Organization.objects.create(name="Other")
        cls.creator = _mk_user("creator@acme.test", cls.org)
        cls.assignee = _mk_user("assignee@acme.test", cls.org)
        cls.org_member = _mk_user("org@acme.test", cls.org)
        cls.outsider = _mk_user("outsider@other.test", cls.other_org)

    def setUp(self):
        self.client = APIClient()

    def _auth(self, user):
        self.client.force_authenticate(user=user)

    def _mk_task(self, *, creator=None, **kwargs):
        defaults = dict(
            organization=self.org,
            creator=creator or self.creator,
            title="X",
            visibility=Task.Visibility.PRIVATE,
        )
        defaults.update(kwargs)
        return Task.objects.create(**defaults)


class TaskCreateTests(InternalTasksAPIBase):
    def test_create_makes_caller_creator_and_default_assignee(self):
        self._auth(self.org_member)
        resp = self.client.post(
            "/api/internal-tasks/tasks/",
            {"title": "Submit Q3 board pack", "priority": "urgent"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        task = Task.objects.get(pk=resp.json()["id"])
        self.assertEqual(task.creator, self.org_member)
        self.assertEqual(task.assignee, self.org_member)
        self.assertEqual(task.priority, "urgent")

    def test_visibility_team_requires_team_id(self):
        """EC1 — visibility=team without team_id → 400."""
        self._auth(self.creator)
        resp = self.client.post(
            "/api/internal-tasks/tasks/",
            {"title": "X", "visibility": "team"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("team", resp.json())

    def test_create_with_checklist(self):
        self._auth(self.creator)
        resp = self.client.post(
            "/api/internal-tasks/tasks/",
            {
                "title": "Outline",
                "checklist_items": [
                    {"label": "Draft", "checked": False},
                    {"label": "Review", "checked": False},
                ],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        body = resp.json()
        self.assertEqual(len(body["checklist_items"]), 2)

    def test_checklist_hard_limit_rejected(self):
        """EC9 — > 100 items rejected."""
        self._auth(self.creator)
        items = [{"label": f"i{i}", "checked": False} for i in range(101)]
        resp = self.client.post(
            "/api/internal-tasks/tasks/",
            {"title": "X", "checklist_items": items},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_tags_lowercased(self):
        self._auth(self.creator)
        resp = self.client.post(
            "/api/internal-tasks/tasks/",
            {"title": "X", "tags": ["BoarD", "Q3"]},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        body = resp.json()
        self.assertEqual(body["tags"], ["board", "q3"])


class TaskListTests(InternalTasksAPIBase):
    def test_creator_sees_own_task(self):
        self._mk_task(title="My task")
        self._auth(self.creator)
        resp = self.client.get("/api/internal-tasks/tasks/")
        self.assertEqual(resp.status_code, 200)
        titles = [t["title"] for t in resp.json()["results"]]
        self.assertIn("My task", titles)

    def test_non_assignee_does_not_see_private_task(self):
        self._mk_task(title="Private 1:1")
        self._auth(self.org_member)
        resp = self.client.get("/api/internal-tasks/tasks/")
        titles = [t["title"] for t in resp.json()["results"]]
        self.assertNotIn("Private 1:1", titles)

    def test_org_member_sees_org_task(self):
        self._mk_task(title="Org-wide", visibility=Task.Visibility.ORG)
        self._auth(self.org_member)
        resp = self.client.get("/api/internal-tasks/tasks/")
        titles = [t["title"] for t in resp.json()["results"]]
        self.assertIn("Org-wide", titles)

    def test_outsider_never_sees(self):
        self._mk_task(title="Org-wide", visibility=Task.Visibility.ORG)
        self._auth(self.outsider)
        resp = self.client.get("/api/internal-tasks/tasks/")
        titles = [t["title"] for t in resp.json()["results"]]
        self.assertNotIn("Org-wide", titles)

    def test_status_filter(self):
        self._mk_task(title="A", status="todo")
        self._mk_task(title="B", status="done")
        self._auth(self.creator)
        resp = self.client.get("/api/internal-tasks/tasks/?status=todo")
        titles = {t["title"] for t in resp.json()["results"]}
        self.assertIn("A", titles)
        self.assertNotIn("B", titles)

    def test_status_filter_comma_separated(self):
        self._mk_task(title="A", status="todo")
        self._mk_task(title="B", status="in_progress")
        self._mk_task(title="C", status="done")
        self._auth(self.creator)
        resp = self.client.get("/api/internal-tasks/tasks/?status=todo,in_progress")
        titles = {t["title"] for t in resp.json()["results"]}
        self.assertIn("A", titles)
        self.assertIn("B", titles)
        self.assertNotIn("C", titles)

    def test_tag_filter_and_semantics(self):
        self._mk_task(title="A", tags=["board", "q3"])
        self._mk_task(title="B", tags=["board"])
        self._mk_task(title="C", tags=["finance"])
        self._auth(self.creator)
        # ?tag=board → A + B
        resp = self.client.get("/api/internal-tasks/tasks/?tag=board")
        titles = {t["title"] for t in resp.json()["results"]}
        self.assertEqual(titles, {"A", "B"})
        # ?tag=board&tag=q3 → A only
        resp = self.client.get("/api/internal-tasks/tasks/?tag=board&tag=q3")
        titles = {t["title"] for t in resp.json()["results"]}
        self.assertEqual(titles, {"A"})

    def test_overdue_filter(self):
        yesterday = date.today() - timedelta(days=1)
        tomorrow = date.today() + timedelta(days=1)
        self._mk_task(title="Overdue", due_date=yesterday, status="todo")
        self._mk_task(title="Future", due_date=tomorrow, status="todo")
        self._mk_task(title="DoneOverdue", due_date=yesterday, status="done")
        self._auth(self.creator)
        resp = self.client.get("/api/internal-tasks/tasks/?overdue=true")
        titles = {t["title"] for t in resp.json()["results"]}
        self.assertIn("Overdue", titles)
        self.assertNotIn("Future", titles)
        self.assertNotIn("DoneOverdue", titles)

    def test_mine_filter(self):
        self._mk_task(title="MineA", assignee=self.creator)
        self._mk_task(title="TheirsB", assignee=self.assignee)
        self._auth(self.creator)
        resp = self.client.get("/api/internal-tasks/tasks/?mine=true")
        titles = {t["title"] for t in resp.json()["results"]}
        self.assertIn("MineA", titles)
        self.assertNotIn("TheirsB", titles)

    def test_q_search(self):
        self._mk_task(title="Board pack draft")
        self._mk_task(title="Q3 finance review")
        self._auth(self.creator)
        resp = self.client.get("/api/internal-tasks/tasks/?q=board")
        titles = {t["title"] for t in resp.json()["results"]}
        self.assertEqual(titles, {"Board pack draft"})


class TaskMutationTests(InternalTasksAPIBase):
    def test_creator_can_edit(self):
        task = self._mk_task()
        self._auth(self.creator)
        resp = self.client.patch(
            f"/api/internal-tasks/tasks/{task.id}/",
            {"title": "Updated"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        task.refresh_from_db()
        self.assertEqual(task.title, "Updated")

    def test_assignee_can_edit(self):
        task = self._mk_task(assignee=self.assignee)
        self._auth(self.assignee)
        resp = self.client.patch(
            f"/api/internal-tasks/tasks/{task.id}/",
            {"description": "Adding context"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)

    def test_assignee_cannot_change_team(self):
        from apps.workspace.models import Team

        team = Team.objects.create(
            organization=self.org, name="Other", visibility=Team.Visibility.PUBLIC
        )
        task = self._mk_task(assignee=self.assignee)
        self._auth(self.assignee)
        resp = self.client.patch(
            f"/api/internal-tasks/tasks/{task.id}/",
            {"team": team.id, "visibility": "team"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_assignee_cannot_delete(self):
        task = self._mk_task(assignee=self.assignee)
        self._auth(self.assignee)
        resp = self.client.delete(f"/api/internal-tasks/tasks/{task.id}/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_creator_can_delete(self):
        task = self._mk_task()
        self._auth(self.creator)
        resp = self.client.delete(f"/api/internal-tasks/tasks/{task.id}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)


class CompleteAndAssignTests(InternalTasksAPIBase):
    def test_complete_toggle(self):
        task = self._mk_task()
        self._auth(self.creator)
        # Toggle to done
        resp = self.client.post(f"/api/internal-tasks/tasks/{task.id}/complete/")
        self.assertEqual(resp.status_code, 200)
        task.refresh_from_db()
        self.assertEqual(task.status, "done")
        self.assertIsNotNone(task.completed_at)
        # Toggle back to todo
        resp = self.client.post(f"/api/internal-tasks/tasks/{task.id}/complete/")
        task.refresh_from_db()
        self.assertEqual(task.status, "todo")
        self.assertIsNone(task.completed_at)

    def test_assign_to_user(self):
        task = self._mk_task()
        self._auth(self.creator)
        resp = self.client.post(
            f"/api/internal-tasks/tasks/{task.id}/assign/",
            {"user_id": self.assignee.id},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        task.refresh_from_db()
        self.assertEqual(task.assignee, self.assignee)

    def test_assign_null(self):
        task = self._mk_task(assignee=self.creator)
        self._auth(self.creator)
        resp = self.client.post(
            f"/api/internal-tasks/tasks/{task.id}/assign/",
            {"user_id": None},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        task.refresh_from_db()
        self.assertIsNone(task.assignee)

    def test_cross_org_assign_rejected(self):
        task = self._mk_task()
        self._auth(self.creator)
        resp = self.client.post(
            f"/api/internal-tasks/tasks/{task.id}/assign/",
            {"user_id": self.outsider.id},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class MeAndTagsTests(InternalTasksAPIBase):
    def test_me_endpoint_returns_open_assigned_tasks(self):
        self._mk_task(title="MineOpen", assignee=self.creator, status="todo")
        self._mk_task(title="MineDone", assignee=self.creator, status="done")
        self._mk_task(title="Theirs", assignee=self.assignee, status="todo")
        self._auth(self.creator)
        resp = self.client.get("/api/internal-tasks/tasks/me/")
        body = resp.json()
        results = body["results"] if "results" in body else body
        titles = {t["title"] for t in results}
        self.assertIn("MineOpen", titles)
        self.assertNotIn("MineDone", titles)
        self.assertNotIn("Theirs", titles)

    def test_tags_endpoint(self):
        self._mk_task(title="A", tags=["board", "q3"])
        self._mk_task(title="B", tags=["board"])
        self._mk_task(title="C", tags=["finance"])
        self._auth(self.creator)
        resp = self.client.get("/api/internal-tasks/tasks/tags/")
        results = resp.json()["results"]
        # board appears twice, finance/q3 once each.
        by_tag = {r["tag"]: r["count"] for r in results}
        self.assertEqual(by_tag.get("board"), 2)
        self.assertEqual(by_tag.get("q3"), 1)
        self.assertEqual(by_tag.get("finance"), 1)
