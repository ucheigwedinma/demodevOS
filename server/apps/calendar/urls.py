"""URL routes for the Calendar API. Mounted at /api/calendar/."""

from django.urls import path

from .views import (
    AttendeeView,
    CalendarFeedView,
    EventViewSet,
    MeetingsOverlayView,
    OccurrenceView,
    RotateFeedTokenView,
)

# Top-level event routes
urlpatterns = [
    path("events/", EventViewSet.as_view({"get": "list", "post": "create"}), name="calendar-events"),
    path("events/agenda/", EventViewSet.as_view({"get": "agenda"}), name="calendar-events-agenda"),
    path(
        "events/<int:pk>/",
        EventViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}),
        name="calendar-event-detail",
    ),
    path(
        "events/<int:pk>/cancel/",
        EventViewSet.as_view({"post": "cancel"}),
        name="calendar-event-cancel",
    ),
    path(
        "events/<int:event_id>/occurrences/",
        OccurrenceView.as_view({"post": "upsert"}),
        name="calendar-event-occurrences",
    ),
    path(
        "events/<int:event_id>/occurrences/<path:original_start>/",
        OccurrenceView.as_view({"delete": "destroy"}),
        name="calendar-event-occurrence-detail",
    ),
    path(
        "events/<int:event_id>/attendees/",
        AttendeeView.as_view({"get": "list", "post": "create"}),
        name="calendar-event-attendees",
    ),
    path(
        "events/<int:event_id>/attendees/<int:user_id>/",
        AttendeeView.as_view({"delete": "destroy"}),
        name="calendar-event-attendee-detail",
    ),
    path("meetings-overlay/", MeetingsOverlayView.as_view(), name="calendar-meetings-overlay"),
    path("feed/", CalendarFeedView.as_view(), name="calendar-feed"),
    path("feed/rotate-token/", RotateFeedTokenView.as_view(), name="calendar-feed-rotate"),
]
