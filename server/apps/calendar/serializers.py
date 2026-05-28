"""
Serializers for the Calendar API.

Three flavors of CalendarEvent serializer:
- CalendarEventListSerializer:   used for the windowed list response (lean).
- CalendarEventDetailSerializer: full payload for detail view.
- CalendarEventWriteSerializer:  validated for create + PATCH.
"""

from __future__ import annotations

from datetime import timedelta

from dateutil.rrule import rrulestr
from django.contrib.auth import get_user_model
from django.db.models import F
from rest_framework import serializers

from .models import (
    CalendarEvent,
    CalendarEventAttendee,
    CalendarEventOccurrence,
)
from .permissions import event_role_for

User = get_user_model()


# ---------------------------------------------------------------------------
# Shared mini serializers
# ---------------------------------------------------------------------------


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
# Event serializers
# ---------------------------------------------------------------------------


class CalendarEventListSerializer(serializers.ModelSerializer):
    """
    Lean serializer for /events/?start=&end= responses.
    NB: this represents the EVENT, not an OCCURRENCE. The list endpoint
    composes its own per-occurrence dicts using recurrence.expand_with_overrides.
    """

    my_role = serializers.SerializerMethodField()

    class Meta:
        model = CalendarEvent
        fields = [
            "id",
            "title",
            "kind",
            "visibility",
            "creator",
            "team",
            "starts_at",
            "ends_at",
            "all_day",
            "timezone",
            "recurrence_rule",
            "is_cancelled",
            "my_role",
        ]

    def get_my_role(self, obj):
        request = self.context.get("request")
        if request is None:
            return None
        return event_role_for(request.user, obj)


class CalendarEventDetailSerializer(serializers.ModelSerializer):
    creator = _UserMiniSerializer(read_only=True)
    my_role = serializers.SerializerMethodField()
    attendees_count = serializers.SerializerMethodField()
    overrides_count = serializers.SerializerMethodField()
    has_external_attendees = serializers.SerializerMethodField()

    class Meta:
        model = CalendarEvent
        fields = [
            "id",
            "title",
            "description",
            "location",
            "meeting_link",
            "external_attendee_emails",
            "kind",
            "visibility",
            "team",
            "starts_at",
            "ends_at",
            "all_day",
            "timezone",
            "recurrence_rule",
            "recurrence_end",
            "reminder_minutes_before",
            "is_cancelled",
            "creator",
            "created_at",
            "updated_at",
            "my_role",
            "attendees_count",
            "overrides_count",
            "has_external_attendees",
        ]

    def get_my_role(self, obj):
        request = self.context.get("request")
        if request is None:
            return None
        return event_role_for(request.user, obj)

    def get_attendees_count(self, obj) -> int:
        return obj.attendees.count()

    def get_overrides_count(self, obj) -> int:
        return obj.occurrences.count()

    def get_has_external_attendees(self, obj) -> bool:
        return bool(obj.external_attendee_emails)


class CalendarEventWriteSerializer(serializers.ModelSerializer):
    """
    Used for create + PATCH. Validates the kind/visibility/team coherence
    rules and that the RRULE parses cleanly. Organization + creator
    are injected by the viewset.
    """

    external_attendee_emails = serializers.ListField(
        child=serializers.EmailField(),
        required=False,
        default=list,
    )

    class Meta:
        model = CalendarEvent
        fields = [
            "title",
            "description",
            "location",
            "meeting_link",
            "external_attendee_emails",
            "kind",
            "visibility",
            "team",
            "starts_at",
            "ends_at",
            "all_day",
            "timezone",
            "recurrence_rule",
            "reminder_minutes_before",
        ]

    def validate_recurrence_rule(self, value: str) -> str:
        if not value:
            return value
        try:
            # Validate it parses; anchor at a dummy dtstart so the parser
            # doesn't reject incomplete rules. Real dtstart is applied at
            # expansion time.
            from datetime import datetime, timezone as dttz

            anchor = self.initial_data.get("starts_at")
            if anchor is None and self.instance is not None:
                anchor = self.instance.starts_at
            if isinstance(anchor, str):
                # Best-effort parse
                from django.utils.dateparse import parse_datetime

                anchor = parse_datetime(anchor) or datetime(2026, 1, 1, tzinfo=dttz.utc)
            if anchor is None:
                anchor = datetime(2026, 1, 1, tzinfo=dttz.utc)
            rrulestr(value, dtstart=anchor)
        except Exception as exc:
            raise serializers.ValidationError(f"Invalid RRULE: {exc}") from exc
        return value

    def validate(self, data):
        # Pull effective values, falling back to instance for PATCH.
        instance = self.instance

        def eff(field):
            if field in data:
                return data[field]
            if instance is not None:
                return getattr(instance, field, None)
            return None

        kind = eff("kind")
        visibility = eff("visibility")
        team = eff("team")
        starts_at = eff("starts_at")
        ends_at = eff("ends_at")

        # Visibility=team requires team_id (per §8-B / EC6).
        if visibility == CalendarEvent.Visibility.TEAM and team is None:
            raise serializers.ValidationError(
                {"team": "Team is required when visibility is 'team'."}
            )

        # ends_at must be >= starts_at unless kind=reminder (per EC1 + EC2).
        if kind != CalendarEvent.Kind.REMINDER:
            if ends_at is None:
                raise serializers.ValidationError(
                    {"ends_at": "ends_at is required for non-reminder events."}
                )
            if starts_at is not None and ends_at < starts_at:
                raise serializers.ValidationError(
                    {"ends_at": "ends_at must be on or after starts_at."}
                )

        return data


# ---------------------------------------------------------------------------
# Occurrence override
# ---------------------------------------------------------------------------


class CalendarEventOccurrenceSerializer(serializers.ModelSerializer):
    is_orphan = serializers.SerializerMethodField()

    class Meta:
        model = CalendarEventOccurrence
        fields = [
            "id",
            "event",
            "original_start",
            "is_cancelled",
            "starts_at",
            "ends_at",
            "title",
            "location",
            "description",
            "is_orphan",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "event", "is_orphan", "created_at", "updated_at"]

    def get_is_orphan(self, obj):
        from .recurrence import is_orphan_override

        return is_orphan_override(obj.event, obj)


class OccurrenceUpsertSerializer(serializers.Serializer):
    """Body for POST /events/{id}/occurrences/."""

    original_start = serializers.DateTimeField()
    is_cancelled = serializers.BooleanField(required=False, default=False)
    starts_at = serializers.DateTimeField(required=False, allow_null=True)
    ends_at = serializers.DateTimeField(required=False, allow_null=True)
    title = serializers.CharField(required=False, allow_blank=True, max_length=200)
    location = serializers.CharField(required=False, allow_blank=True, max_length=200)
    description = serializers.CharField(required=False, allow_blank=True)


# ---------------------------------------------------------------------------
# Attendees
# ---------------------------------------------------------------------------


class CalendarEventAttendeeSerializer(serializers.ModelSerializer):
    user = _UserMiniSerializer(read_only=True)

    class Meta:
        model = CalendarEventAttendee
        fields = ["id", "user", "invited_at"]
        read_only_fields = ["id", "user", "invited_at"]


class AttendeeAddSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
