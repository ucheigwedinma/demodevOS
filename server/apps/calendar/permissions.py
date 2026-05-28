"""
DRF permission classes + role resolver for the Calendar API.

Single source of truth: docs/workspace-calendar-design.md §8.
"""

from __future__ import annotations

from typing import Optional

from rest_framework.permissions import BasePermission, IsAuthenticated

from .models import CalendarEvent, CalendarEventAttendee


def event_role_for(user, event: CalendarEvent) -> Optional[str]:
    """
    Return 'creator' | 'attendee' | 'viewer' | None for the user's role on
    the event. 'viewer' = can see metadata but isn't an attendee.
    """
    if user is None or not user.is_authenticated:
        return None
    if event.creator_id == user.id:
        return "creator"
    is_attendee = CalendarEventAttendee.objects.filter(event=event, user=user).exists()
    if is_attendee:
        return "attendee"
    # Visibility-permitted but non-attendee = viewer
    if can_view_event(user, event):
        return "viewer"
    return None


def can_view_event(user, event: CalendarEvent) -> bool:
    """
    Per §8 visibility rules + secret-team gate.
    """
    if user is None or not user.is_authenticated:
        return False

    # Same-org membership is a precondition for everything except secret-team
    # overrides (handled below).
    same_org = (
        getattr(getattr(user, "profile", None), "organization_id", None)
        == event.organization_id
    )

    # Creator + attendees always see their own events.
    if event.creator_id == user.id:
        return True
    if CalendarEventAttendee.objects.filter(event=event, user=user).exists():
        return True

    if not same_org:
        return False

    # Secret-team gate: if the event's team is visibility="secret", visibility
    # is restricted to team members only — overriding the event's own visibility.
    team = event.team
    if team is not None and team.visibility == "secret":
        # Lazy import to avoid cross-app circularity
        from apps.workspace.models import TeamMembership

        return TeamMembership.objects.filter(team=team, user=user).exists()

    # Standard visibility rules.
    if event.visibility == CalendarEvent.Visibility.ORG:
        return True
    if event.visibility == CalendarEvent.Visibility.TEAM:
        if team is None:
            return False
        from apps.workspace.models import TeamMembership

        return TeamMembership.objects.filter(team=team, user=user).exists()
    # PRIVATE — only creator + attendees (handled above)
    return False


def can_edit_event(user, event: CalendarEvent) -> bool:
    """Creator-only edits per design §8."""
    if user is None or not user.is_authenticated:
        return False
    return event.creator_id == user.id


# ---------------------------------------------------------------------------
# DRF BasePermission classes
# ---------------------------------------------------------------------------


class IsCalendarEventVisible(IsAuthenticated):
    """Read endpoints — object-level visibility check."""

    def has_object_permission(self, request, view, obj: CalendarEvent):
        if not super().has_permission(request, view):
            return False
        return can_view_event(request.user, obj)


class IsCalendarEventCreator(IsAuthenticated):
    """Write endpoints — must be the creator."""

    def has_object_permission(self, request, view, obj: CalendarEvent):
        if not super().has_permission(request, view):
            return False
        return can_edit_event(request.user, obj)
