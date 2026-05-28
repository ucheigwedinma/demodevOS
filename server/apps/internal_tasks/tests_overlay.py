"""
Operational task overlay tests.

Per design §12 + §14:
- Returns ProjectTask + FollowUpTask rows in flattened shape
- Status mapping (completed→done, pending→todo, etc.)
- Priority mapping (critical→urgent)
- Org-scoping inherited (no extra layer)
- assignee=me filter
- EC13: unknown status mapped to "todo" + unmapped_source_status flag
"""

from __future__ import annotations

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import Organization

User = get_user_model()


def _mk_user(email, org):
    user = User.objects.create_user(username=email, email=email, password="x")
    user.profile.organization = org
    user.profile.save(update_fields=["organization"])
    return user


class OverlayTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Acme")
        cls.other_org = Organization.objects.create(name="Other")
        cls.user = _mk_user("u@acme.test", cls.org)
        cls.outsider = _mk_user("o@other.test", cls.other_org)

    def setUp(self):
        self.client = APIClient()

    # ----- ProjectTask overlay -----

    def _make_project_task(self, *, name="Pour slab", status="in_progress", priority="medium", assignee=None, due_date=None, org=None):
        from apps.projects.models import (
            Project,
            ProjectPhase,
            ProjectTask,
        )

        org = org or self.org
        project, _ = Project.objects.get_or_create(
            organization=org,
            name="Phoenix Tower",
        )
        phase, _ = ProjectPhase.objects.get_or_create(
            organization=org,
            project=project,
            name="Foundation",
            defaults={"sort_order": 1},
        )
        return ProjectTask.objects.create(
            organization=org,
            phase=phase,
            name=name,
            status=status,
            priority=priority,
            assigned_user=assignee,
            due_date=due_date,
        )

    def test_project_task_overlay_returns_rows(self):
        self._make_project_task(name="Pour slab", status="in_progress", priority="critical")
        self.client.force_authenticate(user=self.user)
        resp = self.client.get(
            "/api/internal-tasks/overlay/?source=project_task&assignee=all"
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        rows = resp.json()["results"]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["source"], "project_task")
        self.assertEqual(row["title"], "Pour slab")
        # Status mapping: in_progress → in_progress
        self.assertEqual(row["status"], "in_progress")
        # Priority mapping: critical → urgent
        self.assertEqual(row["priority"], "urgent")
        self.assertEqual(row["edit_in_app"], "projects")

    def test_overlay_status_mapping_completed_to_done(self):
        self._make_project_task(name="Done item", status="completed")
        self.client.force_authenticate(user=self.user)
        resp = self.client.get(
            "/api/internal-tasks/overlay/?source=project_task&assignee=all"
        )
        rows = resp.json()["results"]
        self.assertEqual(rows[0]["status"], "done")

    def test_overlay_org_scoped(self):
        """Outsider with different org sees nothing."""
        self._make_project_task(name="Acme task")
        self.client.force_authenticate(user=self.outsider)
        resp = self.client.get(
            "/api/internal-tasks/overlay/?source=project_task&assignee=all"
        )
        self.assertEqual(len(resp.json()["results"]), 0)

    def test_overlay_assignee_me_filter(self):
        self._make_project_task(name="Mine", assignee=self.user)
        self._make_project_task(name="Theirs", assignee=None)
        self.client.force_authenticate(user=self.user)
        resp = self.client.get(
            "/api/internal-tasks/overlay/?source=project_task&assignee=me"
        )
        rows = resp.json()["results"]
        titles = {r["title"] for r in rows}
        self.assertIn("Mine", titles)
        self.assertNotIn("Theirs", titles)

    def test_overlay_unknown_status_flagged(self):
        """EC13 — unknown source status mapped to todo + unmapped_source_status set."""
        # Force a hand-crafted bad status (bypass ProjectTask's choice validation
        # via .update() to simulate an enum that pre-existed).
        from apps.projects.models import ProjectTask

        task = self._make_project_task(name="Unknown", status="in_progress")
        ProjectTask.objects.filter(pk=task.pk).update(status="awaiting_supplier")

        self.client.force_authenticate(user=self.user)
        resp = self.client.get(
            "/api/internal-tasks/overlay/?source=project_task&assignee=all"
        )
        rows = resp.json()["results"]
        bad = [r for r in rows if r["title"] == "Unknown"][0]
        self.assertEqual(bad["status"], "todo")
        self.assertEqual(bad["unmapped_source_status"], "awaiting_supplier")

    def test_overlay_no_source_returns_default_pair(self):
        """No ?source= → defaults to project_task,crm_follow_up combined."""
        self._make_project_task(name="A")
        self.client.force_authenticate(user=self.user)
        resp = self.client.get("/api/internal-tasks/overlay/?assignee=all")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["results"]), 1)
