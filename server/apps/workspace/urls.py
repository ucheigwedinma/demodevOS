"""
URL routes for the workspace teams API.

Mounted under `/api/workspace/` from `config/urls.py`.
"""

from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import NotificationPrefsView, TeamMembershipViewSet, TeamViewSet

router = DefaultRouter()
router.register(r"teams", TeamViewSet, basename="workspace-team")

urlpatterns = router.urls + [
    # Member management — nested under teams
    path(
        "teams/<int:team_id>/members/",
        TeamMembershipViewSet.as_view({"get": "list", "post": "create"}),
        name="workspace-team-members",
    ),
    path(
        "teams/<int:team_id>/members/<int:user_id>/",
        TeamMembershipViewSet.as_view(
            {"patch": "partial_update", "delete": "destroy"}
        ),
        name="workspace-team-member-detail",
    ),
    # My notification prefs for a single team
    path(
        "teams/<int:team_id>/notifications/",
        NotificationPrefsView.as_view({"patch": "partial_update"}),
        name="workspace-team-notifications",
    ),
]
