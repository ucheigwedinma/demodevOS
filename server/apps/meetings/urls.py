from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    MeetingActionItemViewSet,
    MeetingAttendeeViewSet,
    MeetingTemplateViewSet,
    MeetingViewSet,
)

template_router = DefaultRouter()
template_router.register(r"", MeetingTemplateViewSet, basename="meeting-template")

meeting_router = DefaultRouter()
meeting_router.register(r"", MeetingViewSet, basename="meeting")

attendee_router = DefaultRouter()
attendee_router.register(r"", MeetingAttendeeViewSet, basename="meeting-attendee")

action_item_router = DefaultRouter()
action_item_router.register(r"", MeetingActionItemViewSet, basename="meeting-action-item")

urlpatterns = [
    path("templates/", include(template_router.urls)),
    path("", include(meeting_router.urls)),
    path("<int:meeting_pk>/attendees/", include(attendee_router.urls)),
    path("<int:meeting_pk>/action-items/", include(action_item_router.urls)),
]
