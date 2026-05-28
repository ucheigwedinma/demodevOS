from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from apps.admin_mixins import OrgScopedAdminMixin

from .models import Meeting, MeetingActionItem, MeetingAttendee, MeetingTemplate


@admin.register(MeetingTemplate)
class MeetingTemplateAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["name", "frequency", "default_duration_mins", "auto_generate_minutes", "is_active"]
    list_filter = ["frequency", "is_active"]
    search_fields = ["name"]


class MeetingAttendeeInline(TabularInline):
    model = MeetingAttendee
    extra = 0
    fields = ["name", "email", "role", "company", "attendance_status", "is_required"]


class MeetingActionItemInline(TabularInline):
    model = MeetingActionItem
    extra = 0
    fields = ["description", "assigned_to", "due_date", "status", "priority", "sort_order"]


@admin.register(Meeting)
class MeetingAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["meeting_number", "title", "meeting_type", "status", "scheduled_start", "project"]
    list_filter = ["meeting_type", "status", "series_name"]
    search_fields = ["meeting_number", "title", "series_name"]
    inlines = [MeetingAttendeeInline, MeetingActionItemInline]
