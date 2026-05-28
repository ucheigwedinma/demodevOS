"""
End-to-end API tests for /api/workspace/teams/.

Covers:
- List filters (mine, archived, purpose, q).
- Visibility scoping: secret teams hidden from non-members on list + detail.
- Create makes the caller the owner.
- Edit / archive / delete gated by role.
- Member CRUD: add (idempotent EC11), role change (with EC6 optimistic lock),
  remove (with EC1 owner-self-leave block, admin-can't-demote-admin).
- Transfer ownership atomic swap.
- /me endpoint returns only my teams.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import Organization
from apps.workspace.models import Team, TeamMembership

User = get_user_model()


class WorkspaceTeamsAPIBase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Acme")
        cls.other_org = Organization.objects.create(name="Other Co")

        def _mk(email, *, org=None):
            org = org or cls.org
            user = User.objects.create_user(username=email, email=email, password="x")
            user.profile.organization = org
            user.profile.save(update_fields=["organization"])
            return user

        cls.owner = _mk("owner@acme.test")
        cls.admin = _mk("admin@acme.test")
        cls.member = _mk("member@acme.test")
        cls.guest = _mk("guest@acme.test")
        cls.outsider = _mk("outsider@acme.test")
        cls.other_org_user = _mk("crossorg@other.test", org=cls.other_org)

    def setUp(self):
        self.client = APIClient()

    def _auth(self, user):
        self.client.force_authenticate(user=user)

    def _create_team(self, *, name="Squad", visibility=Team.Visibility.PUBLIC, owner=None):
        owner = owner or self.owner
        team = Team.objects.create(
            organization=self.org,
            name=name,
            visibility=visibility,
            created_by=owner,
        )
        TeamMembership.objects.create(
            team=team, user=owner, role=TeamMembership.Role.OWNER
        )
        return team


class TeamCreateTests(WorkspaceTeamsAPIBase):
    def test_create_makes_caller_owner(self):
        self._auth(self.member)
        resp = self.client.post(
            "/api/workspace/teams/",
            {"name": "Phoenix", "purpose": "guild", "visibility": "public"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        team = Team.objects.get(slug="phoenix")
        self.assertEqual(team.organization, self.org)
        ownership = TeamMembership.objects.get(team=team, user=self.member)
        self.assertEqual(ownership.role, TeamMembership.Role.OWNER)

    def test_create_project_purpose_requires_project_fk(self):
        self._auth(self.member)
        resp = self.client.post(
            "/api/workspace/teams/",
            {"name": "Phoenix", "purpose": "project"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("project", resp.json())


class TeamListVisibilityTests(WorkspaceTeamsAPIBase):
    def test_secret_team_hidden_from_non_members(self):
        secret = self._create_team(name="MA Squad", visibility=Team.Visibility.SECRET)
        self._auth(self.outsider)
        resp = self.client.get("/api/workspace/teams/")
        self.assertEqual(resp.status_code, 200)
        slugs = [t["slug"] for t in resp.json()["results"]]
        self.assertNotIn(secret.slug, slugs)

    def test_secret_team_visible_to_member(self):
        secret = self._create_team(name="MA Squad", visibility=Team.Visibility.SECRET)
        TeamMembership.objects.create(
            team=secret, user=self.member, role=TeamMembership.Role.MEMBER
        )
        self._auth(self.member)
        resp = self.client.get("/api/workspace/teams/")
        slugs = [t["slug"] for t in resp.json()["results"]]
        self.assertIn(secret.slug, slugs)

    def test_public_and_private_visible_to_all(self):
        self._create_team(name="Pub", visibility=Team.Visibility.PUBLIC)
        self._create_team(name="Priv", visibility=Team.Visibility.PRIVATE)
        self._auth(self.outsider)
        resp = self.client.get("/api/workspace/teams/")
        slugs = [t["slug"] for t in resp.json()["results"]]
        self.assertIn("pub", slugs)
        self.assertIn("priv", slugs)

    def test_archived_filter_default_excludes(self):
        team = self._create_team()
        team.is_archived = True
        team.save()
        self._auth(self.owner)
        resp = self.client.get("/api/workspace/teams/")
        self.assertEqual(len(resp.json()["results"]), 0)
        resp2 = self.client.get("/api/workspace/teams/?archived=true")
        self.assertEqual(len(resp2.json()["results"]), 1)

    def test_mine_filter(self):
        a = self._create_team(name="A")
        b = self._create_team(name="B")
        TeamMembership.objects.create(team=a, user=self.member, role=TeamMembership.Role.MEMBER)
        self._auth(self.member)
        resp = self.client.get("/api/workspace/teams/?mine=true")
        slugs = [t["slug"] for t in resp.json()["results"]]
        self.assertIn(a.slug, slugs)
        self.assertNotIn(b.slug, slugs)

    def test_q_search_by_name(self):
        self._create_team(name="Mobile Squad")
        self._create_team(name="Backend Pod")
        self._auth(self.owner)
        resp = self.client.get("/api/workspace/teams/?q=mobile")
        results = resp.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["slug"], "mobile-squad")

    def test_cross_org_isolation(self):
        self._create_team(name="Acme team")
        self._auth(self.other_org_user)
        resp = self.client.get("/api/workspace/teams/")
        self.assertEqual(len(resp.json()["results"]), 0)


class TeamMutationTests(WorkspaceTeamsAPIBase):
    def test_member_cannot_edit_metadata(self):
        team = self._create_team()
        TeamMembership.objects.create(team=team, user=self.member, role=TeamMembership.Role.MEMBER)
        self._auth(self.member)
        resp = self.client.patch(
            f"/api/workspace/teams/{team.id}/", {"description": "hacked"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_edit_metadata(self):
        team = self._create_team()
        TeamMembership.objects.create(team=team, user=self.admin, role=TeamMembership.Role.ADMIN)
        self._auth(self.admin)
        resp = self.client.patch(
            f"/api/workspace/teams/{team.id}/", {"description": "rebrand"}, format="json"
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        team.refresh_from_db()
        self.assertEqual(team.description, "rebrand")

    def test_only_owner_can_delete(self):
        team = self._create_team()
        TeamMembership.objects.create(team=team, user=self.admin, role=TeamMembership.Role.ADMIN)
        self._auth(self.admin)
        resp = self.client.delete(f"/api/workspace/teams/{team.id}/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self._auth(self.owner)
        resp2 = self.client.delete(f"/api/workspace/teams/{team.id}/")
        self.assertEqual(resp2.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Team.objects.filter(pk=team.id).exists())

    def test_archive_toggle(self):
        team = self._create_team()
        self._auth(self.owner)
        resp = self.client.post(f"/api/workspace/teams/{team.id}/archive/")
        self.assertEqual(resp.status_code, 200)
        team.refresh_from_db()
        self.assertTrue(team.is_archived)
        self.assertIsNotNone(team.archived_at)
        # toggle back
        self.client.post(f"/api/workspace/teams/{team.id}/archive/")
        team.refresh_from_db()
        self.assertFalse(team.is_archived)
        self.assertIsNone(team.archived_at)


class MemberCrudTests(WorkspaceTeamsAPIBase):
    def test_add_member_idempotent_ec11(self):
        team = self._create_team()
        self._auth(self.owner)
        url = f"/api/workspace/teams/{team.id}/members/"
        r1 = self.client.post(url, {"user_id": self.member.id, "role": "member"}, format="json")
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED)
        r2 = self.client.post(url, {"user_id": self.member.id, "role": "member"}, format="json")
        # Idempotent: same user → 200, not 201, no duplicate row.
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        self.assertEqual(
            TeamMembership.objects.filter(team=team, user=self.member).count(), 1
        )

    def test_add_member_cross_org_rejected(self):
        team = self._create_team()
        self._auth(self.owner)
        resp = self.client.post(
            f"/api/workspace/teams/{team.id}/members/",
            {"user_id": self.other_org_user.id, "role": "member"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_owner_self_leave_blocked_ec1(self):
        team = self._create_team()
        self._auth(self.owner)
        resp = self.client.delete(
            f"/api/workspace/teams/{team.id}/members/{self.owner.id}/"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Transfer", resp.json().get("detail", ""))

    def test_member_self_leave(self):
        team = self._create_team()
        TeamMembership.objects.create(team=team, user=self.member, role=TeamMembership.Role.MEMBER)
        self._auth(self.member)
        resp = self.client.delete(
            f"/api/workspace/teams/{team.id}/members/{self.member.id}/"
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            TeamMembership.objects.filter(team=team, user=self.member).exists()
        )

    def test_admin_cannot_demote_owner(self):
        team = self._create_team()
        TeamMembership.objects.create(team=team, user=self.admin, role=TeamMembership.Role.ADMIN)
        self._auth(self.admin)
        resp = self.client.patch(
            f"/api/workspace/teams/{team.id}/members/{self.owner.id}/",
            {"role": "member"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_cannot_demote_other_admin(self):
        team = self._create_team()
        TeamMembership.objects.create(team=team, user=self.admin, role=TeamMembership.Role.ADMIN)
        admin2 = User.objects.create_user(
            username="admin2@acme.test", email="admin2@acme.test", password="x"
        )
        admin2.profile.organization = self.org
        admin2.profile.save(update_fields=["organization"])
        TeamMembership.objects.create(team=team, user=admin2, role=TeamMembership.Role.ADMIN)
        self._auth(self.admin)
        resp = self.client.patch(
            f"/api/workspace/teams/{team.id}/members/{admin2.id}/",
            {"role": "member"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_optimistic_lock_ec6(self):
        team = self._create_team()
        TeamMembership.objects.create(team=team, user=self.member, role=TeamMembership.Role.MEMBER)
        # Capture an "old" updated_at, then bump the membership behind the scenes.
        m = TeamMembership.objects.get(team=team, user=self.member)
        old_updated = m.updated_at
        m.role = TeamMembership.Role.GUEST
        m.save()
        self._auth(self.owner)
        resp = self.client.patch(
            f"/api/workspace/teams/{team.id}/members/{self.member.id}/",
            {"role": "admin", "if_unchanged_since": old_updated.isoformat()},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)


class TransferOwnershipTests(WorkspaceTeamsAPIBase):
    def test_owner_transfers_to_admin(self):
        team = self._create_team()
        TeamMembership.objects.create(team=team, user=self.admin, role=TeamMembership.Role.ADMIN)
        self._auth(self.owner)
        resp = self.client.post(
            f"/api/workspace/teams/{team.id}/transfer/",
            {"new_owner_id": self.admin.id},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        # Old owner is now admin; new owner is owner. Exactly one owner.
        self.assertEqual(
            TeamMembership.objects.get(team=team, user=self.admin).role,
            TeamMembership.Role.OWNER,
        )
        self.assertEqual(
            TeamMembership.objects.get(team=team, user=self.owner).role,
            TeamMembership.Role.ADMIN,
        )
        self.assertEqual(
            TeamMembership.objects.filter(
                team=team, role=TeamMembership.Role.OWNER
            ).count(),
            1,
        )

    def test_transfer_to_non_member_rejected(self):
        team = self._create_team()
        self._auth(self.owner)
        resp = self.client.post(
            f"/api/workspace/teams/{team.id}/transfer/",
            {"new_owner_id": self.outsider.id},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_only_owner_can_transfer(self):
        team = self._create_team()
        TeamMembership.objects.create(team=team, user=self.admin, role=TeamMembership.Role.ADMIN)
        self._auth(self.admin)
        resp = self.client.post(
            f"/api/workspace/teams/{team.id}/transfer/",
            {"new_owner_id": self.owner.id},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class JoinFlowTests(WorkspaceTeamsAPIBase):
    def test_self_join_public(self):
        team = self._create_team(visibility=Team.Visibility.PUBLIC)
        self._auth(self.outsider)
        resp = self.client.post(f"/api/workspace/teams/{team.id}/join/")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            TeamMembership.objects.filter(team=team, user=self.outsider).exists()
        )

    def test_self_join_private_blocked(self):
        team = self._create_team(visibility=Team.Visibility.PRIVATE)
        self._auth(self.outsider)
        resp = self.client.post(f"/api/workspace/teams/{team.id}/join/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class MeEndpointTests(WorkspaceTeamsAPIBase):
    def test_me_returns_only_my_teams(self):
        a = self._create_team(name="A")
        b = self._create_team(name="B")
        TeamMembership.objects.create(team=a, user=self.member, role=TeamMembership.Role.MEMBER)
        self._auth(self.member)
        resp = self.client.get("/api/workspace/teams/me/")
        slugs = [t["slug"] for t in (resp.json().get("results") or resp.json())]
        self.assertIn(a.slug, slugs)
        self.assertNotIn(b.slug, slugs)
