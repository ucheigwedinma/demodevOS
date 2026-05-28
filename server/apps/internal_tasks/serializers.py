"""
Serializers for the Internal Tasks API.

Three flavours of Task serializer:
- TaskListSerializer:   lean payload for list responses
- TaskDetailSerializer: full payload for detail view
- TaskWriteSerializer:  used for create + PATCH (validates team/visibility +
                        checklist limits + lowercases tags)

Comments use simple ModelSerializers — body in, mentions auto-computed.
"""

from __future__ import annotations

from datetime import date as date_cls

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Task, TaskComment
from .permissions import task_role_for

User = get_user_model()


# ---------------------------------------------------------------------------
# Mini user serializer (consistent across the Workspace family)
# ---------------------------------------------------------------------------


class _UserMiniSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    initials = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "name", "email", "initials"]

    def get_name(self, obj):
        if not obj.is_active:
            return "[deactivated user]"
        full = obj.get_full_name().strip()
        return full or obj.email or obj.username

    def get_initials(self, obj):
        full = obj.get_full_name().strip()
        if full:
            parts = full.split()
            return "".join(p[0] for p in parts[:2]).upper()
        return (obj.email or obj.username or "?")[:2].upper()


# ---------------------------------------------------------------------------
# Task serializers
# ---------------------------------------------------------------------------


def _overdue(task: Task) -> bool:
    """Per design §5: overdue = status != done AND due_date < today."""
    if task.due_date is None:
        return False
    if task.status == Task.Status.DONE:
        return False
    return task.due_date < date_cls.today()


class TaskListSerializer(serializers.ModelSerializer):
    """Lean payload for list responses (per UI spec list row)."""

    assignee_id = serializers.IntegerField(read_only=True)
    team_id = serializers.IntegerField(read_only=True)
    comments_count = serializers.SerializerMethodField()
    overdue = serializers.SerializerMethodField()
    my_role = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "status",
            "priority",
            "visibility",
            "assignee_id",
            "team_id",
            "due_date",
            "overdue",
            "tags",
            "comments_count",
            "my_role",
            "created_at",
            "updated_at",
        ]

    def get_comments_count(self, obj) -> int:
        return obj.comments.count()

    def get_overdue(self, obj) -> bool:
        return _overdue(obj)

    def get_my_role(self, obj):
        request = self.context.get("request")
        if request is None:
            return None
        return task_role_for(request.user, obj)


class TaskDetailSerializer(serializers.ModelSerializer):
    creator = _UserMiniSerializer(read_only=True)
    assignee = _UserMiniSerializer(read_only=True)
    overdue = serializers.SerializerMethodField()
    my_role = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "description",
            "status",
            "priority",
            "visibility",
            "creator",
            "assignee",
            "team",
            "due_date",
            "completed_at",
            "overdue",
            "tags",
            "checklist_items",
            "comments_count",
            "my_role",
            "created_at",
            "updated_at",
        ]

    def get_overdue(self, obj) -> bool:
        return _overdue(obj)

    def get_my_role(self, obj):
        request = self.context.get("request")
        if request is None:
            return None
        return task_role_for(request.user, obj)

    def get_comments_count(self, obj) -> int:
        return obj.comments.count()


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------


CHECKLIST_HARD_LIMIT = 100  # serializer 400 above this; UI warns above 50


def _validate_checklist(items) -> list[dict]:
    """
    Validate the JSON checklist:
      [{"label": str, "checked": bool}, ...]
    Per design EC9: > 100 items rejected. Empty labels rejected.
    Returns the validated list (with normalized booleans).
    """
    if items is None:
        return []
    if not isinstance(items, list):
        raise serializers.ValidationError("checklist_items must be a list.")
    if len(items) > CHECKLIST_HARD_LIMIT:
        raise serializers.ValidationError(
            f"Checklist supports up to {CHECKLIST_HARD_LIMIT} items."
        )
    out: list[dict] = []
    for i, raw in enumerate(items):
        if not isinstance(raw, dict):
            raise serializers.ValidationError(
                f"checklist_items[{i}] must be an object."
            )
        label = (raw.get("label") or "").strip()
        if not label:
            raise serializers.ValidationError(
                f"checklist_items[{i}].label is required."
            )
        checked = bool(raw.get("checked", False))
        out.append({"label": label, "checked": checked})
    return out


# ---------------------------------------------------------------------------
# Task write serializer (create + PATCH)
# ---------------------------------------------------------------------------


class TaskWriteSerializer(serializers.ModelSerializer):
    tags = serializers.ListField(
        child=serializers.CharField(max_length=40),
        required=False,
        default=list,
    )
    checklist_items = serializers.JSONField(required=False, default=list)

    class Meta:
        model = Task
        fields = [
            "title",
            "description",
            "status",
            "priority",
            "visibility",
            "assignee",
            "team",
            "due_date",
            "tags",
            "checklist_items",
        ]

    def validate_checklist_items(self, value):
        return _validate_checklist(value)

    def validate(self, data):
        """
        EC1: visibility=team requires team_id.
        """
        instance = self.instance

        def eff(field):
            if field in data:
                return data[field]
            if instance is not None:
                return getattr(instance, field, None)
            return None

        visibility = eff("visibility")
        team = eff("team")

        if visibility == Task.Visibility.TEAM and team is None:
            raise serializers.ValidationError(
                {"team": "Team is required when visibility is 'team'."}
            )

        return data


# ---------------------------------------------------------------------------
# Assignment / status helpers (small body serializers)
# ---------------------------------------------------------------------------


class AssignmentSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(allow_null=True)


class ChecklistReplaceSerializer(serializers.Serializer):
    items = serializers.JSONField()

    def validate_items(self, value):
        return _validate_checklist(value)


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------


class TaskCommentSerializer(serializers.ModelSerializer):
    author = _UserMiniSerializer(read_only=True)

    class Meta:
        model = TaskComment
        fields = ["id", "body", "author", "mentions", "created_at", "updated_at"]
        read_only_fields = ["id", "author", "mentions", "created_at", "updated_at"]


class TaskCommentWriteSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=10_000)

    def validate_body(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Comment body cannot be empty.")
        return value
