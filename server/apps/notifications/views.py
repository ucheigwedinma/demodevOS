from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.mixins import OrgScopedMixin
from apps.settings.permissions import HasRolePermission

from .models import Notification
from .serializers import NotificationAdminSerializer, NotificationSerializer


class NotificationViewSet(
    OrgScopedMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    ordering = ["-created_at"]

    def _is_org_admin(self):
        profile = getattr(self.request.user, "profile", None)
        return profile and profile.role == "admin"

    def _requesting_org_scope(self):
        return self.request.query_params.get("scope") == "org" and self._is_org_admin()

    def get_permissions(self):
        """Org-wide scope requires settings.system_preferences.view RBAC."""
        perms = super().get_permissions()
        if self.request.query_params.get("scope") == "org":
            rbac = HasRolePermission()
            perms.append(rbac)
            self.rbac_sub_module = "settings.system_preferences"
            self.rbac_action = "view"
        return perms

    def get_serializer_class(self):
        if self._requesting_org_scope():
            return NotificationAdminSerializer
        return NotificationSerializer

    filterset_fields = ["severity", "category", "is_read"]

    queryset = Notification.objects.select_related("recipient")

    def get_queryset(self):
        if self._requesting_org_scope():
            # Admin org-wide view: use OrgScopedMixin's org filter
            qs = super().get_queryset()
        else:
            # Personal view: filter by recipient only (matches UnreadCountView)
            qs = Notification.objects.select_related("recipient").filter(
                recipient=self.request.user,
            )

        # Manual filtering (fallback if django-filter not wired for this viewset)
        params = self.request.query_params
        if params.get("severity"):
            qs = qs.filter(severity=params["severity"])
        if params.get("category"):
            qs = qs.filter(category=params["category"])
        if params.get("is_read") in ("true", "false"):
            qs = qs.filter(is_read=params["is_read"] == "true")
        return qs

    @action(detail=True, methods=["post"], url_path="read")
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=["is_read", "read_at"])
        return Response(NotificationSerializer(notification).data)

    @action(detail=False, methods=["post"], url_path="mark-all-read")
    def mark_all_read(self, request):
        updated = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).update(is_read=True, read_at=timezone.now())
        return Response({"updated": updated})


class UnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).count()
        return Response({"count": count})
