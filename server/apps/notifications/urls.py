from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import NotificationViewSet, UnreadCountView

router = DefaultRouter()
router.register(r"", NotificationViewSet, basename="notification")

urlpatterns = [
    path("unread-count/", UnreadCountView.as_view(), name="notification-unread-count"),
    path("", include(router.urls)),
]
