"""URL routes for Internal Tasks. Mounted at /api/internal-tasks/."""

from django.urls import path

from .views import OverlayView, TaskCommentView, TaskViewSet

urlpatterns = [
    # Tasks
    path(
        "tasks/",
        TaskViewSet.as_view({"get": "list", "post": "create"}),
        name="internal-tasks-list",
    ),
    path(
        "tasks/me/",
        TaskViewSet.as_view({"get": "me"}),
        name="internal-tasks-me",
    ),
    path(
        "tasks/tags/",
        TaskViewSet.as_view({"get": "tags"}),
        name="internal-tasks-tags",
    ),
    path(
        "tasks/<int:pk>/",
        TaskViewSet.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
        ),
        name="internal-task-detail",
    ),
    path(
        "tasks/<int:pk>/complete/",
        TaskViewSet.as_view({"post": "complete"}),
        name="internal-task-complete",
    ),
    path(
        "tasks/<int:pk>/assign/",
        TaskViewSet.as_view({"post": "assign"}),
        name="internal-task-assign",
    ),
    path(
        "tasks/<int:pk>/checklist/",
        TaskViewSet.as_view({"post": "replace_checklist"}),
        name="internal-task-checklist",
    ),
    # Comments
    path(
        "tasks/<int:task_id>/comments/",
        TaskCommentView.as_view({"get": "list", "post": "create"}),
        name="internal-task-comments",
    ),
    path(
        "tasks/<int:task_id>/comments/<int:comment_id>/",
        TaskCommentView.as_view({"delete": "destroy"}),
        name="internal-task-comment-detail",
    ),
    # Overlay
    path("overlay/", OverlayView.as_view(), name="internal-tasks-overlay"),
]
