"""
Serializers for the workspace teams API.

Three flavors of Team serializer:
- TeamListSerializer:    minimal payload for the directory grid.
- TeamDetailSerializer:  full payload with linked-resource counts and my_role.
- TeamWriteSerializer:   used for create + PATCH; validates project FK requirement.

Membership serializers handle the per-row member display + write.
"""

from __future__ import annotations

from typing import Optional

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from rest_framework import serializers

from .models import Team, TeamMembership

User = get_user_model()


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _user_role_in_team(team: Team, user) -> Optional[str]:
    """Lookup the role for `user` in `team` from prefetched memberships if present."""
    if user is None or not user.is_authenticated:
        return None
    cached = getattr(team, "_my_membership_cache", None)
    if cached is not None:
        return cached.role if cached else None
    membership = next(
        (m for m in getattr(team, "_prefetched_my_memberships", []) if m.user_id == user.id),
        None,
    )
    if membership is None:
        membership = TeamMembership.objects.filter(team=team, user=user).only("role").first()
    return membership.role if membership else None


class _UserMiniSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    initials = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "name", "email", "initials"]

    def get_name(self, obj):
        full = obj.get_full_name().strip()
        return full or obj.email or obj.username

    def get_initials(self, obj):
        full = obj.get_full_name().strip()
        if full:
            parts = full.split()
            return "".join(p[0] for p in parts[:2]).upper()
        return (obj.email or obj.username or "?")[:2].upper()


# ---------------------------------------------------------------------------
# Team serializers
# ---------------------------------------------------------------------------


class TeamListSerializer(serializers.ModelSerializer):
    """Lean payload for the directory list view."""

    members_count = serializers.IntegerField(read_only=True)
    my_role = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "purpose",
            "visibility",
            "emoji",
            "color",
            "is_archived",
            "members_count",
            "my_role",
            "created_at",
        ]

    def get_my_role(self, obj):
        request = self.context.get("request")
        if request is None:
            return None
        return _user_role_in_team(obj, request.user)


class TeamDetailSerializer(serializers.ModelSerializer):
    members_count = serializers.IntegerField(read_only=True)
    open_tickets_count = serializers.SerializerMethodField()
    my_role = serializers.SerializerMethodField()
    is_orphaned = serializers.BooleanField(read_only=True)
    project_name = serializers.SerializerMethodField()
    created_by = _UserMiniSerializer(read_only=True)

    class Meta:
        model = Team
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "purpose",
            "visibility",
            "project",
            "project_name",
            "emoji",
            "color",
            "is_archived",
            "archived_at",
            "members_count",
            "open_tickets_count",
            "my_role",
            "is_orphaned",
            "created_by",
            "created_at",
            "updated_at",
        ]

    def get_my_role(self, obj):
        request = self.context.get("request")
        if request is None:
            return None
        return _user_role_in_team(obj, request.user)

    def get_open_tickets_count(self, obj) -> int:
        # Imported lazily to avoid a circular import at module load.
        try:
            from apps.support_desk.models import SupportTicket
        except Exception:
            return 0
        return SupportTicket.objects.filter(
            team=obj
        ).exclude(
            status__in=[SupportTicket.Status.RESOLVED, SupportTicket.Status.CLOSED]
        ).count()

    def get_project_name(self, obj):
        return obj.project.name if obj.project_id and obj.project else None


class TeamWriteSerializer(serializers.ModelSerializer):
    """Used for create + PATCH. The viewset injects organization + created_by."""

    class Meta:
        model = Team
        fields = [
            "name",
            "description",
            "purpose",
            "visibility",
            "project",
            "emoji",
            "color",
        ]

    def validate(self, data):
        # Validate project FK constraint: required when purpose=project,
        # forbidden otherwise (clean rule rather than silently ignoring).
        purpose = data.get("purpose", getattr(self.instance, "purpose", None))
        project = data.get("project", getattr(self.instance, "project", None))
        if purpose == Team.Purpose.PROJECT and not project:
            raise serializers.ValidationError(
                {"project": "A linked project is required for project-purpose teams."}
            )
        if purpose != Team.Purpose.PROJECT and project is not None:
            raise serializers.ValidationError(
                {"project": "Projects can only be linked to project-purpose teams."}
            )
        return data


# ---------------------------------------------------------------------------
# Membership serializers
# ---------------------------------------------------------------------------


class TeamMembershipSerializer(serializers.ModelSerializer):
    user = _UserMiniSerializer(read_only=True)

    class Meta:
        model = TeamMembership
        fields = [
            "id",
            "user",
            "role",
            "joined_at",
            "notify_realtime",
            "digest_frequency",
            "updated_at",
        ]
        read_only_fields = ["id", "joined_at", "user", "updated_at"]


class TeamMembershipWriteSerializer(serializers.Serializer):
    """Request shape for POST /teams/{id}/members/."""

    user_id = serializers.IntegerField()
    role = serializers.ChoiceField(
        choices=TeamMembership.Role.choices,
        default=TeamMembership.Role.MEMBER,
    )


class TransferOwnershipSerializer(serializers.Serializer):
    """Request shape for POST /teams/{id}/transfer/."""

    new_owner_id = serializers.IntegerField()


class RoleChangeSerializer(serializers.Serializer):
    """Request shape for PATCH /teams/{id}/members/{user_id}/."""

    role = serializers.ChoiceField(choices=TeamMembership.Role.choices)
    if_unchanged_since = serializers.DateTimeField(
        required=False,
        help_text="Optimistic lock: 409 if membership.updated_at has moved past this.",
    )


class NotificationPrefsSerializer(serializers.ModelSerializer):
    """Update my own notification prefs for a team."""

    class Meta:
        model = TeamMembership
        fields = ["notify_realtime", "digest_frequency"]
