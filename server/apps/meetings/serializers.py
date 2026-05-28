from rest_framework import serializers

from .models import Meeting, MeetingActionItem, MeetingAttendee, MeetingTemplate


class MeetingTemplateSerializer(serializers.ModelSerializer):
    frequency_display = serializers.CharField(source="get_frequency_display", read_only=True)

    class Meta:
        model = MeetingTemplate
        exclude = ("organization",)
        read_only_fields = ("id", "created_at", "updated_at")


class MeetingAttendeeSerializer(serializers.ModelSerializer):
    attendance_status_display = serializers.CharField(source="get_attendance_status_display", read_only=True)

    class Meta:
        model = MeetingAttendee
        fields = (
            "id", "meeting", "name", "email", "role", "company",
            "attendance_status", "attendance_status_display",
            "user", "is_required", "notes",
        )
        read_only_fields = ("id", "meeting")


class MeetingActionItemSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = MeetingActionItem
        fields = (
            "id", "meeting", "description", "assigned_to", "assigned_to_email",
            "due_date", "status", "status_display", "is_overdue",
            "completed_date", "priority", "linked_task",
            "sort_order", "notes", "created_at",
        )
        read_only_fields = ("id", "meeting", "created_at")


class MeetingListSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True, default=None)
    meeting_type_display = serializers.CharField(source="get_meeting_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    format_display = serializers.CharField(source="get_meeting_format_display", read_only=True)
    template_name = serializers.CharField(source="template.name", read_only=True, default=None)
    attendee_count = serializers.IntegerField(read_only=True, default=0)
    action_item_count = serializers.IntegerField(read_only=True, default=0)
    open_action_count = serializers.IntegerField(read_only=True, default=0)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Meeting
        fields = (
            "id", "meeting_number", "title", "meeting_type", "meeting_type_display",
            "status", "status_display", "meeting_format", "format_display",
            "series_name", "template", "template_name",
            "scheduled_start", "scheduled_end", "duration_mins",
            "location", "meeting_link",
            "project", "project_name",
            "organized_by", "recorded_by",
            "attendee_count", "action_item_count", "open_action_count",
            "is_overdue", "minutes_approved",
            "created_at", "updated_at",
        )


class MeetingDetailSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True, default=None)
    meeting_type_display = serializers.CharField(source="get_meeting_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    format_display = serializers.CharField(source="get_meeting_format_display", read_only=True)
    template_name = serializers.CharField(source="template.name", read_only=True, default=None)
    attendees = MeetingAttendeeSerializer(many=True, read_only=True)
    action_items = MeetingActionItemSerializer(many=True, read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Meeting
        fields = "__all__"
        read_only_fields = ("id", "meeting_number", "organization", "created_by", "created_at", "updated_at")


class MeetingWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Meeting
        fields = (
            "id", "template", "title", "meeting_type", "status", "meeting_format",
            "series_name", "scheduled_start", "scheduled_end", "duration_mins",
            "location", "meeting_link",
            "project", "consultant",
            "agenda", "key_decisions",
            "live_notes",
            "discussion_points", "decisions_made", "issues_raised",
            "minutes_text", "recorded_by", "notes",
        )
        read_only_fields = ("id",)
