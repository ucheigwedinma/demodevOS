from django.contrib import admin

from .models import CalendarEvent, CalendarEventAttendee, CalendarEventOccurrence, IcalFeedToken


class CalendarEventAttendeeInline(admin.TabularInline):
    model = CalendarEventAttendee
    extra = 0
    raw_id_fields = ("user", "invited_by")
    readonly_fields = ("invited_at",)


class CalendarEventOccurrenceInline(admin.TabularInline):
    model = CalendarEventOccurrence
    extra = 0
    readonly_fields = ("created_at", "updated_at")


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "kind",
        "visibility",
        "organization",
        "creator",
        "starts_at",
        "is_cancelled",
    )
    list_filter = ("kind", "visibility", "is_cancelled", "all_day")
    search_fields = ("title", "description", "location")
    raw_id_fields = ("organization", "creator", "team")
    readonly_fields = ("created_at", "updated_at", "recurrence_end")
    date_hierarchy = "starts_at"
    inlines = [CalendarEventAttendeeInline, CalendarEventOccurrenceInline]


@admin.register(CalendarEventOccurrence)
class CalendarEventOccurrenceAdmin(admin.ModelAdmin):
    list_display = ("event", "original_start", "is_cancelled", "starts_at")
    list_filter = ("is_cancelled",)
    raw_id_fields = ("event",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(CalendarEventAttendee)
class CalendarEventAttendeeAdmin(admin.ModelAdmin):
    list_display = ("event", "user", "invited_at")
    raw_id_fields = ("event", "user", "invited_by")
    readonly_fields = ("invited_at",)


@admin.register(IcalFeedToken)
class IcalFeedTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at", "revoked_at")
    list_filter = ("revoked_at",)
    raw_id_fields = ("user",)
    readonly_fields = ("token_hash", "created_at", "revoked_at")
