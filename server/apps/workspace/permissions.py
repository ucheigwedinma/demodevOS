"""
DRF permission classes for Workspace teams.

Single source of truth: docs/workspace-teams-design.md §8.
"""

from __future__ import annotations

from typing import Optional

from rest_framework.permissions import BasePermission, IsAuthenticated

from .models import Team, TeamMembership


def team_role_for(user, team: Team) -> Optional[str]:
    """Return the user's role on the team, or None if not a member."""
    if user is None or not user.is_authenticated:
        return None
    membership = TeamMembership.objects.filter(team=team, user=user).only("role").first()
    return membership.role if membership else None


def can_view_team(user, team: Team) -> bool:
    """
    True iff the user can see this team's metadata page.
    - public/private: any authenticated org member
    - secret:        only members
    """
    if team.visibility == Team.Visibility.SECRET:
        return team_role_for(user, team) is not None
    return True


def can_edit_team(user, team: Team) -> bool:
    return team_role_for(user, team) in (TeamMembership.Role.OWNER, TeamMembership.Role.ADMIN)


def can_manage_members(user, team: Team) -> bool:
    return can_edit_team(user, team)


def can_delete_team(user, team: Team) -> bool:
    return team_role_for(user, team) == TeamMembership.Role.OWNER


def can_transfer_team(user, team: Team) -> bool:
    return team_role_for(user, team) == TeamMembership.Role.OWNER


# ---------------------------------------------------------------------------
# DRF BasePermission classes
# ---------------------------------------------------------------------------


class IsTeamMemberOrVisible(IsAuthenticated):
    """
    Default for team-scoped endpoints. Object-level: the caller must be able
    to see the team (member, OR non-member with non-secret visibility).
    """

    def has_object_permission(self, request, view, obj: Team):
        if not super().has_permission(request, view):
            return False
        return can_view_team(request.user, obj)


class IsTeamOwnerOrAdmin(IsAuthenticated):
    """For mutate-team-metadata endpoints (PATCH, archive, member CRUD)."""

    def has_object_permission(self, request, view, obj: Team):
        if not super().has_permission(request, view):
            return False
        return can_edit_team(request.user, obj)


class IsTeamOwner(IsAuthenticated):
    """For destructive endpoints (delete, transfer)."""

    def has_object_permission(self, request, view, obj: Team):
        if not super().has_permission(request, view):
            return False
        return can_delete_team(request.user, obj)
