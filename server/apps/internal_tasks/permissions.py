"""
DRF permission classes + role resolver for Internal Tasks.

Single source of truth: docs/workspace-internal-tasks-design.md §8.

Three classes:
- IsTaskVisible — read endpoints (object-level visibility check)
- IsTaskWriter  — write endpoints (creator OR assignee)
- IsTaskCreator — destructive endpoints (creator only)

Secret-team gate: inherits from workspace.Team visibility, identical to
the rule applied in apps.calendar.permissions.
"""

from __future__ import annotations

from typing import Optional

from rest_framework.permissions import BasePermission, IsAuthenticated

from .models import Task


def task_role_for(user, task: Task) -> Optional[str]:
    """
    Return 'creator' | 'assignee' | 'viewer' | None for the user's role on
    the task. 'viewer' = can see metadata but is neither creator nor assignee.
    """
    if user is None or not user.is_authenticated:
        return None
    if task.creator_id == user.id:
        return "creator"
    if task.assignee_id == user.id:
        return "assignee"
    if can_view_task(user, task):
        return "viewer"
    return None


def can_view_task(user, task: Task) -> bool:
    """
    Per §8 visibility rules + secret-team gate.
    """
    if user is None or not user.is_authenticated:
        return False

    # Creator + assignee always see the task.
    if task.creator_id == user.id:
        return True
    if task.assignee_id == user.id:
        return True

    # Org membership precondition (anything below requires same org).
    same_org = (
        getattr(getattr(user, "profile", None), "organization_id", None)
        == task.organization_id
    )
    if not same_org:
        return False

    # Secret-team gate: if the task's team is visibility="secret", only
    # team members can see — overriding the task's own visibility.
    team = task.team
    if team is not None and team.visibility == "secret":
        from apps.workspace.models import TeamMembership

        return TeamMembership.objects.filter(team=team, user=user).exists()

    # Standard visibility rules.
    if task.visibility == Task.Visibility.ORG:
        return True
    if task.visibility == Task.Visibility.TEAM:
        if team is None:
            return False
        from apps.workspace.models import TeamMembership

        return TeamMembership.objects.filter(team=team, user=user).exists()
    # PRIVATE — only creator + assignee (handled above)
    return False


def can_edit_task(user, task: Task) -> bool:
    """Creator OR assignee can edit metadata."""
    if user is None or not user.is_authenticated:
        return False
    return task.creator_id == user.id or task.assignee_id == user.id


def can_delete_task(user, task: Task) -> bool:
    """Only the creator can delete (or change team/visibility)."""
    if user is None or not user.is_authenticated:
        return False
    return task.creator_id == user.id


# ---------------------------------------------------------------------------
# DRF BasePermission classes
# ---------------------------------------------------------------------------


class IsTaskVisible(IsAuthenticated):
    """Read endpoints — object-level visibility check."""

    def has_object_permission(self, request, view, obj: Task):
        if not super().has_permission(request, view):
            return False
        return can_view_task(request.user, obj)


class IsTaskWriter(IsAuthenticated):
    """Write endpoints — creator OR assignee."""

    def has_object_permission(self, request, view, obj: Task):
        if not super().has_permission(request, view):
            return False
        return can_edit_task(request.user, obj)


class IsTaskCreator(IsAuthenticated):
    """Destructive endpoints — creator only."""

    def has_object_permission(self, request, view, obj: Task):
        if not super().has_permission(request, view):
            return False
        return can_delete_task(request.user, obj)
