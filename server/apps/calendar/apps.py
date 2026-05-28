from django.apps import AppConfig


class CalendarConfig(AppConfig):
    """
    Calendar domain — loose events that don't fit the operational Meeting
    shape (1:1s, focus blocks, OOO, reminders) plus a read-only overlay
    of apps.meetings.Meeting on the shared canvas.

    See docs/workspace-calendar-design.md.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.calendar"
    label = "calendar"
    verbose_name = "Calendar"

    def ready(self):
        # Wire signals (audit hooks, cache invalidation)
        import apps.calendar.signals  # noqa: F401

        # Register audited models — curated fields per §11.
        from auditlog.registry import auditlog

        from .models import CalendarEvent, CalendarEventAttendee, CalendarEventOccurrence

        auditlog.register(
            CalendarEvent,
            include_fields=[
                "title",
                "kind",
                "visibility",
                "starts_at",
                "ends_at",
                "team",
                "recurrence_rule",
                "is_cancelled",
            ],
        )
        auditlog.register(
            CalendarEventOccurrence,
            include_fields=["original_start", "starts_at", "ends_at", "is_cancelled"],
        )
        auditlog.register(CalendarEventAttendee, include_fields=["user"])
