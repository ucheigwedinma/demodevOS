"""
SupportTicket × Workspace.Team visibility integration tests.

Per design §12 — verifies the queryset filter, not the RBAC layer (which is
tested elsewhere in the support_desk suite). We exercise `_ticket_queryset`
directly so an org member without `support_desk.tickets.view` RBAC permission
doesn't muddy the outcome.

Cases:
- Tickets with `team=null` behave exactly as today (no regression).
- Tickets attached to a secret team are hidden from non-members.
- Members of any visibility see their team's tickets.
- Public/private team tickets visible to all org members (the team filter
  only narrows for secret).
"""

from __future__ import annotations

from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from apps.accounts.models import Organization
from apps.support_desk.models import SupportTicket
from apps.support_desk.views import _ticket_queryset
from apps.workspace.models import Team, TeamMembership

User = get_user_model()


class SupportTicketTeamVisibilityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Acme")

        def _mk(email):
            user = User.objects.create_user(username=email, email=email, password="x")
            user.profile.organization = cls.org
            user.profile.save(update_fields=["organization"])
            return user

        cls.member = _mk("member@acme.test")
        cls.outsider = _mk("outsider@acme.test")

        cls.public_team = Team.objects.create(
            organization=cls.org, name="Pub", visibility=Team.Visibility.PUBLIC
        )
        cls.secret_team = Team.objects.create(
            organization=cls.org, name="Secret", visibility=Team.Visibility.SECRET
        )
        TeamMembership.objects.create(
            team=cls.secret_team, user=cls.member, role=TeamMembership.Role.MEMBER
        )

        cls.t_no_team = SupportTicket.objects.create(
            organization=cls.org, subject="No team", ticket_id="T-001"
        )
        cls.t_pub = SupportTicket.objects.create(
            organization=cls.org, subject="Public team", ticket_id="T-002", team=cls.public_team
        )
        cls.t_secret = SupportTicket.objects.create(
            organization=cls.org, subject="Secret team", ticket_id="T-003", team=cls.secret_team
        )

    def _request_for(self, user):
        request = RequestFactory().get("/api/support-desk/tickets/")
        request.user = user
        request.organization = self.org
        return request

    def _ticket_ids(self, qs):
        return set(qs.values_list("ticket_id", flat=True))

    def test_outsider_does_not_see_secret_team_ticket(self):
        request = self._request_for(self.outsider)
        ids = self._ticket_ids(_ticket_queryset(request))
        self.assertIn("T-001", ids)  # null team — unchanged
        self.assertIn("T-002", ids)  # public — visible
        self.assertNotIn("T-003", ids)  # secret — hidden

    def test_member_of_secret_team_sees_secret_ticket(self):
        request = self._request_for(self.member)
        ids = self._ticket_ids(_ticket_queryset(request))
        self.assertIn("T-003", ids)

    def test_null_team_unchanged_baseline(self):
        request = self._request_for(self.outsider)
        ids = self._ticket_ids(_ticket_queryset(request))
        self.assertIn("T-001", ids)
