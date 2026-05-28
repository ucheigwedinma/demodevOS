from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from apps.accounts.emails import send_invitation_email
from apps.accounts.audit import audit_emit
from apps.accounts.models import AccessRequest, AccessReviewCampaign, AccessReviewItem, APIKey, ApplicationToken, Connector, ConnectorInstallation, IdentityProvider, Invitation, Organization, ServiceAccount, UserGroup, UserProfile, UserSecurityEvent, Webhook, WebhookDelivery
from apps.settings.models import Role
from django.db.models import Count
from datetime import timedelta
from apps.settings.data_scopes import scoped_user_profile_queryset_for_user
from apps.settings.permissions import HasRolePermission

from .iam_serializers import (
    AccessPolicyDetailSerializer,
    AccessPolicyListSerializer,
    AccessPolicyWriteSerializer,
    AccessRequestCreateSerializer,
    AccessRequestDecisionSerializer,
    AccessRequestListSerializer,
    AccessReviewCampaignListSerializer,
    AccessReviewCampaignWriteSerializer,
    AccessReviewItemDecisionSerializer,
    AccessReviewItemSerializer,
    APIKeyCreateSerializer,
    APIKeyDirectorySerializer,
    ApplicationTokenSerializer,
    ApplicationTokenWriteSerializer,
    AuditEventSerializer,
    ConnectorInstallationWriteSerializer,
    ConnectorSerializer,
    DataScopeSerializer,
    IdentityProviderSerializer,
    IdentityProviderWriteSerializer,
    InvitationListSerializer,
    LoginMethodsSerializer,
    PasswordPolicySerializer,
    RoleScopeSerializer,
    RoleScopeWriteSerializer,
    ServiceAccountCreateSerializer,
    ServiceAccountDetailSerializer,
    ServiceAccountListSerializer,
    ServiceAccountUpdateSerializer,
    UserAuthSessionSerializer,
    UserDetailSerializer,
    UserDirectorySerializer,
    UserGroupDetailSerializer,
    UserGroupListSerializer,
    UserGroupWriteSerializer,
    UserInviteSerializer,
    UserLinkedEmployeeSerializer,
    UserUpdateSerializer,
    WebhookDeliverySerializer,
    WebhookSerializer,
    WebhookWriteSerializer,
)
from apps.accounts.models import UserAuthSession

User = get_user_model()

PAGE_SIZE = 25


class UserManagementViewSet(ViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "iam.users"
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "create",
        "partial_update": "edit",
        "destroy": "delete",
        "suspend": "edit",
        "activate": "edit",
        "invitations": "view",
        "lifecycle": "view",
    }

    def _get_org(self, request):
        profile = getattr(request.user, "profile", None)
        return profile.organization if profile else None

    def _get_base_qs(self, request):
        org = self._get_org(request)
        if not org:
            return UserProfile.objects.none()
        queryset = (
            UserProfile.objects.filter(organization=org)
            .select_related("user", "department", "assigned_role", "reporting_manager")
        )
        return scoped_user_profile_queryset_for_user(
            queryset,
            request.user,
            sub_module=self.rbac_sub_module,
        )

    def _serializer_context(self, request):
        return {"request": request}

    def list(self, request):
        qs = self._get_base_qs(request)

        # Search
        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
                | Q(user__email__icontains=search)
                | Q(phone__icontains=search)
                | Q(job_title__icontains=search)
            )

        # Filters
        user_status = request.query_params.get("status", "")
        if user_status:
            qs = qs.filter(user_status=user_status)

        department_id = request.query_params.get("department", "")
        if department_id:
            qs = qs.filter(department_id=department_id)

        role_id = request.query_params.get("role", "")
        if role_id:
            qs = qs.filter(assigned_role_id=role_id)

        # Filter by identity_type. Accepts a single value ("partner") or a
        # comma-separated set ("partner,system_account") used by the
        # external-users page to surface non-internal identities.
        identity_type = request.query_params.get("identity_type", "")
        if identity_type:
            values = [v.strip() for v in identity_type.split(",") if v.strip()]
            if values:
                qs = qs.filter(identity_type__in=values)

        qs = qs.order_by("user__first_name", "user__last_name")

        # Overview counts (before pagination)
        total_count = qs.count()
        active_count = qs.filter(user_status="active").count()
        suspended_count = qs.filter(user_status="suspended").count()
        locked_count = qs.filter(user_status="locked").count()

        # Pagination
        try:
            page = int(request.query_params.get("page", 1))
        except (ValueError, TypeError):
            page = 1
        try:
            page_size = int(request.query_params.get("page_size", PAGE_SIZE))
        except (ValueError, TypeError):
            page_size = PAGE_SIZE

        start = (page - 1) * page_size
        end = start + page_size
        page_qs = qs[start:end]

        serializer = UserDirectorySerializer(
            page_qs,
            many=True,
            context=self._serializer_context(request),
        )

        return Response(
            {
                "count": total_count,
                "results": serializer.data,
                "overview": {
                    "total": total_count,
                    "active": active_count,
                    "suspended": suspended_count,
                    "locked": locked_count,
                },
            }
        )

    def retrieve(self, request, pk=None):
        qs = self._get_base_qs(request)
        try:
            profile = qs.get(user_id=pk)
        except UserProfile.DoesNotExist:
            return Response(
                {"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = UserDetailSerializer(
            profile,
            context=self._serializer_context(request),
        )
        return Response(serializer.data)

    def partial_update(self, request, pk=None):
        qs = self._get_base_qs(request)
        try:
            profile = qs.get(user_id=pk)
        except UserProfile.DoesNotExist:
            return Response(
                {"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = UserUpdateSerializer(
            data=request.data, context={"organization": self._get_org(request)}
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Update User fields
        user = profile.user
        if "first_name" in data:
            user.first_name = data["first_name"]
        if "last_name" in data:
            user.last_name = data["last_name"]
        user.save(update_fields=[f for f in ["first_name", "last_name"] if f in data] or None)

        # Update Profile fields
        profile_fields = []
        for field in ["phone", "job_title", "user_status", "mfa_enabled", "identity_type", "partner_type"]:
            if field in data:
                setattr(profile, field, data[field])
                profile_fields.append(field)

        if "department_id" in data:
            profile.department_id = data["department_id"]
            profile_fields.append("department_id")

        prior_role_id = profile.assigned_role_id
        if "assigned_role_id" in data:
            profile.assigned_role_id = data["assigned_role_id"]
            profile_fields.append("assigned_role_id")

        if "reporting_manager_id" in data:
            profile.reporting_manager_id = data["reporting_manager_id"]
            profile_fields.append("reporting_manager_id")

        if profile_fields:
            profile.save(update_fields=profile_fields)
            # Emit audit event when assigned_role changes (assign or unassign)
            if "assigned_role_id" in data and data["assigned_role_id"] != prior_role_id:
                new_role_id = data["assigned_role_id"]
                if new_role_id:
                    audit_emit(
                        event_type=UserSecurityEvent.EventType.ROLE_ASSIGNED,
                        request=request,
                        status=UserSecurityEvent.Status.INFO,
                        severity=UserSecurityEvent.Severity.MEDIUM,
                        target_type="user",
                        target_id=str(profile.user_id),
                        detail=f"Role #{new_role_id} assigned to {profile.user.email}",
                        metadata={"prior_role_id": prior_role_id, "new_role_id": new_role_id},
                    )
                else:
                    audit_emit(
                        event_type=UserSecurityEvent.EventType.ROLE_UNASSIGNED,
                        request=request,
                        status=UserSecurityEvent.Status.INFO,
                        severity=UserSecurityEvent.Severity.MEDIUM,
                        target_type="user",
                        target_id=str(profile.user_id),
                        detail=f"Role #{prior_role_id} removed from {profile.user.email}",
                        metadata={"prior_role_id": prior_role_id},
                    )

        # Sync Django auth user.is_active when user_status changes via PATCH
        if "user_status" in data:
            should_be_active = data["user_status"] == "active"
            if user.is_active != should_be_active:
                user.is_active = should_be_active
                user.save(update_fields=["is_active"])

        # Re-fetch for response
        profile.refresh_from_db()
        return Response(
            UserDetailSerializer(
                profile,
                context=self._serializer_context(request),
            ).data
        )

    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        return self._change_status(request, pk, "suspended")

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        return self._change_status(request, pk, "active")

    def _change_status(self, request, pk, new_status):
        qs = self._get_base_qs(request)
        try:
            profile = qs.get(user_id=pk)
        except UserProfile.DoesNotExist:
            return Response(
                {"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND
            )

        profile.user_status = new_status
        profile.save(update_fields=["user_status"])

        # Sync Django auth user.is_active
        user = profile.user
        should_be_active = new_status == "active"
        if user.is_active != should_be_active:
            user.is_active = should_be_active
            user.save(update_fields=["is_active"])

        return Response(
            UserDetailSerializer(
                profile,
                context=self._serializer_context(request),
            ).data
        )

    def create(self, request):
        org = self._get_org(request)
        if not org:
            return Response(
                {"detail": "No organization."}, status=status.HTTP_400_BAD_REQUEST
            )

        serializer = UserInviteSerializer(
            data=request.data, context={"organization": org}
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        from apps.settings.quotas import check_seat_quota

        check_seat_quota(org)

        inv = Invitation.objects.create(
            email=data["email"],
            organization=org,
            invited_by=request.user,
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            role_id=data.get("role_id"),
            department_id=data.get("department_id"),
            job_title=data.get("job_title", ""),
        )

        inviter_name = request.user.get_full_name() or request.user.email
        send_invitation_email(data["email"], org.name, inviter_name, str(inv.token))

        from apps.notifications.models import Notification

        Notification.objects.create(
            recipient=request.user,
            organization=org,
            title="Invitation sent",
            message=f"An invitation to join {org.name} has been sent to {data['email']}.",
            severity=Notification.Severity.INFO,
            category=Notification.Category.SYSTEM,
            link_url="/iam/users",
        )

        return Response(
            InvitationListSerializer(
                inv,
                context=self._serializer_context(request),
            ).data,
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, pk=None):
        qs = self._get_base_qs(request)
        try:
            profile = qs.get(user_id=pk)
        except UserProfile.DoesNotExist:
            return Response(
                {"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND
            )

        if profile.user_id == request.user.id:
            return Response(
                {"detail": "You cannot delete your own account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = profile.user
        user.is_active = False
        user.save(update_fields=["is_active"])
        profile.user_status = "suspended"
        profile.save(update_fields=["user_status"])
        user.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"])
    def invitations(self, request):
        org = self._get_org(request)
        if not org:
            return Response({"results": []})

        qs = Invitation.objects.filter(organization=org).select_related("invited_by")

        inv_status = request.query_params.get("status", "")
        if inv_status:
            qs = qs.filter(status=inv_status)

        qs = qs.order_by("-created_at")
        serializer = InvitationListSerializer(
            qs,
            many=True,
            context=self._serializer_context(request),
        )
        return Response({"results": serializer.data, "count": qs.count()})

    @action(detail=False, methods=["get"])
    def lifecycle(self, request):
        org = self._get_org(request)
        if not org:
            return Response({"stages": {}, "timeline": []})

        profiles = self._get_base_qs(request).select_related("user")
        invitations_qs = Invitation.objects.filter(organization=org)

        now = timezone.now()

        # Stage counts
        pending_invitations = invitations_qs.filter(status="pending").count()
        pending_onboarding = profiles.filter(
            has_completed_onboarding=False, user__is_active=True
        ).count()
        active = profiles.filter(user_status="active").count()
        suspended = profiles.filter(user_status="suspended").count()
        locked = profiles.filter(user_status="locked").count()

        # Timeline: recent lifecycle events (last 30 days)
        cutoff = now - timezone.timedelta(days=30)
        timeline = []

        # Recent invitations
        recent_invites = (
            invitations_qs.filter(created_at__gte=cutoff)
            .select_related("invited_by")
            .order_by("-created_at")[:20]
        )
        for inv in recent_invites:
            inviter = inv.invited_by.get_full_name() or inv.invited_by.email
            timeline.append({
                "type": "invitation",
                "label": f"{inviter} invited {inv.email}",
                "status": inv.status,
                "timestamp": inv.created_at.isoformat(),
            })

        # Recent joins (date_joined within cutoff)
        recent_joins = (
            profiles.filter(user__date_joined__gte=cutoff)
            .order_by("-user__date_joined")[:20]
        )
        for p in recent_joins:
            timeline.append({
                "type": "joined",
                "label": f"{p.user.get_full_name() or p.user.email} joined",
                "status": p.user_status,
                "timestamp": p.user.date_joined.isoformat(),
            })

        # Never logged in (provisioned but idle)
        never_logged_in = profiles.filter(
            user__last_login__isnull=True, user__is_active=True
        ).count()

        # Sort timeline by timestamp descending
        timeline.sort(key=lambda e: e["timestamp"], reverse=True)

        return Response({
            "stages": {
                "pending_invitations": pending_invitations,
                "pending_onboarding": pending_onboarding,
                "active": active,
                "suspended": suspended,
                "locked": locked,
                "never_logged_in": never_logged_in,
            },
            "timeline": timeline[:30],
        })

    @action(detail=False, methods=["get"], url_path="linked-employees")
    def linked_employees(self, request):
        """List org users joined with their HR EmployeeRecord (if linked)."""
        qs = self._get_base_qs(request).select_related("user", "department")
        # Optional filter: ?linked=true|false to surface only one side
        linked_param = request.query_params.get("linked", "").lower()
        if linked_param == "true":
            qs = qs.filter(user__employee_record__isnull=False)
        elif linked_param == "false":
            qs = qs.filter(user__employee_record__isnull=True)

        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
                | Q(user__email__icontains=search)
            )

        qs = qs.order_by("user__first_name", "user__last_name")

        # Pagination
        try:
            page = int(request.query_params.get("page", 1))
        except (ValueError, TypeError):
            page = 1
        try:
            page_size = int(request.query_params.get("page_size", PAGE_SIZE))
        except (ValueError, TypeError):
            page_size = PAGE_SIZE
        start = (page - 1) * page_size
        end = start + page_size

        total_count = qs.count()
        linked_count = qs.filter(user__employee_record__isnull=False).count()
        unlinked_count = total_count - linked_count

        serializer = UserLinkedEmployeeSerializer(
            qs[start:end],
            many=True,
            context=self._serializer_context(request),
        )
        return Response({
            "count": total_count,
            "results": serializer.data,
            "overview": {
                "total": total_count,
                "linked": linked_count,
                "unlinked": unlinked_count,
            },
        })


PAGE_SIZE_SA = 25


class ServiceAccountViewSet(ViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "iam.service_accounts"
    rbac_action_map = {
        "list": "view",
        "create": "create",
        "retrieve": "view",
        "partial_update": "edit",
        "destroy": "delete",
        "create_key": "create",
        "revoke_key": "delete",
    }

    def _get_org(self, request):
        profile = getattr(request.user, "profile", None)
        return profile.organization if profile else None

    def _get_base_qs(self, request):
        org = self._get_org(request)
        if not org:
            return ServiceAccount.objects.none()
        return ServiceAccount.objects.filter(organization=org).select_related("owner")

    def list(self, request):
        qs = self._get_base_qs(request)

        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))

        sa_status = request.query_params.get("status", "")
        if sa_status:
            qs = qs.filter(status=sa_status)

        qs = qs.order_by("-created_at")

        total_count = qs.count()
        active_count = qs.filter(status="active").count()
        suspended_count = qs.filter(status="suspended").count()
        revoked_count = qs.filter(status="revoked").count()

        try:
            page = int(request.query_params.get("page", 1))
        except (ValueError, TypeError):
            page = 1
        try:
            page_size = int(request.query_params.get("page_size", PAGE_SIZE_SA))
        except (ValueError, TypeError):
            page_size = PAGE_SIZE_SA

        start = (page - 1) * page_size
        page_qs = qs[start : start + page_size]

        serializer = ServiceAccountListSerializer(page_qs, many=True)

        return Response(
            {
                "count": total_count,
                "results": serializer.data,
                "overview": {
                    "total": total_count,
                    "active": active_count,
                    "suspended": suspended_count,
                    "revoked": revoked_count,
                },
            }
        )

    def create(self, request):
        org = self._get_org(request)
        if not org:
            return Response(
                {"detail": "No organization."}, status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ServiceAccountCreateSerializer(
            data=request.data, context={"organization": org}
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        sa = ServiceAccount.objects.create(
            organization=org,
            name=data["name"],
            description=data.get("description", ""),
            owner=request.user,
        )
        return Response(
            ServiceAccountDetailSerializer(sa).data,
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, pk=None):
        qs = self._get_base_qs(request)
        try:
            sa = qs.prefetch_related("api_keys").get(pk=pk)
        except ServiceAccount.DoesNotExist:
            return Response(
                {"detail": "Service account not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(ServiceAccountDetailSerializer(sa).data)

    def partial_update(self, request, pk=None):
        qs = self._get_base_qs(request)
        try:
            sa = qs.get(pk=pk)
        except ServiceAccount.DoesNotExist:
            return Response(
                {"detail": "Service account not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ServiceAccountUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        update_fields = []
        for field in ("name", "description", "status"):
            if field in data:
                setattr(sa, field, data[field])
                update_fields.append(field)

        if update_fields:
            sa.save(update_fields=update_fields)

        return Response(ServiceAccountDetailSerializer(sa).data)

    def destroy(self, request, pk=None):
        qs = self._get_base_qs(request)
        try:
            sa = qs.get(pk=pk)
        except ServiceAccount.DoesNotExist:
            return Response(
                {"detail": "Service account not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        sa.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="keys")
    def create_key(self, request, pk=None):
        qs = self._get_base_qs(request)
        try:
            sa = qs.get(pk=pk)
        except ServiceAccount.DoesNotExist:
            return Response(
                {"detail": "Service account not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if sa.status != "active":
            return Response(
                {"detail": "Cannot create keys for a non-active service account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = APIKeyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        key_instance, raw_key = APIKey.generate(
            service_account=sa,
            label=data.get("label", ""),
            scopes=data.get("scopes", []),
            expires_at=data.get("expires_at"),
        )

        return Response(
            {
                "id": key_instance.id,
                "label": key_instance.label,
                "prefix": key_instance.prefix,
                "key": raw_key,
                "scopes": key_instance.scopes,
                "expires_at": key_instance.expires_at,
                "created_at": key_instance.created_at,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["delete"], url_path="keys/(?P<key_id>[0-9]+)")
    def revoke_key(self, request, pk=None, key_id=None):
        qs = self._get_base_qs(request)
        try:
            sa = qs.get(pk=pk)
        except ServiceAccount.DoesNotExist:
            return Response(
                {"detail": "Service account not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            key = sa.api_keys.get(pk=key_id)
        except APIKey.DoesNotExist:
            return Response(
                {"detail": "API key not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        key.is_active = False
        key.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class APIKeyDirectoryView(ViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "iam.service_accounts"
    rbac_action_map = {"list": "view"}

    def _get_org(self, request):
        profile = getattr(request.user, "profile", None)
        return profile.organization if profile else None

    def list(self, request):
        org = self._get_org(request)
        if not org:
            return Response({"count": 0, "results": [], "overview": {}})

        qs = (
            APIKey.objects
            .filter(service_account__organization=org)
            .select_related("service_account")
            .order_by("-created_at")
        )

        # Search
        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(prefix__icontains=search)
                | Q(label__icontains=search)
                | Q(service_account__name__icontains=search)
            )

        # Status filter
        key_status = request.query_params.get("status", "")
        now = timezone.now()
        if key_status == "active":
            qs = qs.filter(is_active=True).filter(Q(expires_at__isnull=True) | Q(expires_at__gte=now))
        elif key_status == "revoked":
            qs = qs.filter(is_active=False)
        elif key_status == "expired":
            qs = qs.filter(is_active=True, expires_at__lt=now)

        total_count = qs.count()

        # Overview counts (on unfiltered org keys)
        all_keys = APIKey.objects.filter(service_account__organization=org)
        total_all = all_keys.count()
        revoked_count = all_keys.filter(is_active=False).count()
        expired_count = all_keys.filter(is_active=True, expires_at__lt=now).count()
        active_count = total_all - revoked_count - expired_count

        # Pagination
        try:
            page = int(request.query_params.get("page", 1))
        except (ValueError, TypeError):
            page = 1
        try:
            page_size = int(request.query_params.get("page_size", PAGE_SIZE))
        except (ValueError, TypeError):
            page_size = PAGE_SIZE

        start = (page - 1) * page_size
        page_qs = qs[start : start + page_size]

        serializer = APIKeyDirectorySerializer(page_qs, many=True)

        return Response({
            "count": total_count,
            "results": serializer.data,
            "overview": {
                "total": total_all,
                "active": active_count,
                "revoked": revoked_count,
                "expired": expired_count,
            },
        })


class MFASettingsView(ViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "iam.mfa_settings"

    def _get_org(self, request):
        profile = getattr(request.user, "profile", None)
        return profile.organization if profile else None

    def retrieve(self, request):
        org = self._get_org(request)
        if not org:
            return Response(
                {"detail": "No organization."}, status=status.HTTP_400_BAD_REQUEST
            )

        total_users = UserProfile.objects.filter(organization=org).count()
        mfa_enabled_count = UserProfile.objects.filter(
            organization=org, mfa_enabled=True
        ).count()

        return Response(
            {
                "mfa_enforcement": org.mfa_enforcement,
                "mfa_enforcement_display": org.get_mfa_enforcement_display(),
                "enforcement_choices": [
                    {"value": c[0], "label": c[1]}
                    for c in Organization.MFAEnforcement.choices
                ],
                "stats": {
                    "total_users": total_users,
                    "mfa_enabled": mfa_enabled_count,
                    "mfa_disabled": total_users - mfa_enabled_count,
                    "adoption_pct": round(
                        (mfa_enabled_count / total_users * 100) if total_users else 0
                    ),
                },
            }
        )

    def partial_update(self, request):
        org = self._get_org(request)
        if not org:
            return Response(
                {"detail": "No organization."}, status=status.HTTP_400_BAD_REQUEST
            )

        enforcement = request.data.get("mfa_enforcement")
        valid_choices = [c[0] for c in Organization.MFAEnforcement.choices]
        if enforcement not in valid_choices:
            return Response(
                {"detail": f"Invalid choice. Must be one of: {', '.join(valid_choices)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        org.mfa_enforcement = enforcement
        org.save(update_fields=["mfa_enforcement"])

        # Re-fetch to return updated data
        return self.retrieve(request)


# ── User Groups ──────────────────────────────────────────────────────


PAGE_SIZE_GROUPS = 25


class UserGroupViewSet(ViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "iam.user_groups"
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "create",
        "partial_update": "edit",
        "destroy": "delete",
    }

    def _get_org(self, request):
        profile = getattr(request.user, "profile", None)
        return profile.organization if profile else None

    def _get_qs(self, request):
        org = self._get_org(request)
        if not org:
            return UserGroup.objects.none()
        return (
            UserGroup.objects.filter(organization=org)
            .annotate(member_count=Count("members"))
        )

    def list(self, request):
        qs = self._get_qs(request)
        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))

        ordering = request.query_params.get("ordering", "name")
        if ordering not in ("name", "-name", "created_at", "-created_at", "member_count", "-member_count"):
            ordering = "name"
        qs = qs.order_by(ordering)

        try:
            page = int(request.query_params.get("page", 1))
        except (ValueError, TypeError):
            page = 1
        try:
            page_size = int(request.query_params.get("page_size", PAGE_SIZE_GROUPS))
        except (ValueError, TypeError):
            page_size = PAGE_SIZE_GROUPS
        start = (page - 1) * page_size
        end = start + page_size

        total_count = qs.count()
        page_qs = qs[start:end]

        return Response({
            "count": total_count,
            "results": UserGroupListSerializer(page_qs, many=True).data,
        })

    def retrieve(self, request, pk=None):
        try:
            group = self._get_qs(request).get(pk=pk)
        except UserGroup.DoesNotExist:
            return Response({"detail": "Group not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(UserGroupDetailSerializer(group).data)

    def create(self, request):
        org = self._get_org(request)
        if not org:
            return Response({"detail": "No organization context."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = UserGroupWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        member_ids = data.pop("member_ids", []) or []

        if UserGroup.objects.filter(organization=org, name=data["name"]).exists():
            return Response(
                {"detail": "A group with this name already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        group = UserGroup.objects.create(organization=org, **data)
        if member_ids:
            valid_user_ids = list(
                UserProfile.objects.filter(
                    organization=org, user_id__in=member_ids
                ).values_list("user_id", flat=True)
            )
            group.members.set(valid_user_ids)

        # Annotate member_count for response
        group.member_count = group.members.count()
        return Response(UserGroupDetailSerializer(group).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        org = self._get_org(request)
        try:
            group = self._get_qs(request).get(pk=pk)
        except UserGroup.DoesNotExist:
            return Response({"detail": "Group not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = UserGroupWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        update_fields = []
        if "name" in data:
            # Uniqueness check (excluding self)
            if UserGroup.objects.filter(
                organization=org, name=data["name"]
            ).exclude(pk=group.pk).exists():
                return Response(
                    {"detail": "A group with this name already exists."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            group.name = data["name"]
            update_fields.append("name")
        if "description" in data:
            group.description = data["description"]
            update_fields.append("description")
        if update_fields:
            group.save(update_fields=update_fields + ["updated_at"])

        if "member_ids" in data:
            valid_user_ids = list(
                UserProfile.objects.filter(
                    organization=org, user_id__in=data["member_ids"]
                ).values_list("user_id", flat=True)
            )
            group.members.set(valid_user_ids)

        group.member_count = group.members.count()
        return Response(UserGroupDetailSerializer(group).data)

    def destroy(self, request, pk=None):
        try:
            group = self._get_qs(request).get(pk=pk)
        except UserGroup.DoesNotExist:
            return Response({"detail": "Group not found."}, status=status.HTTP_404_NOT_FOUND)
        if group.is_system:
            return Response(
                {"detail": "System groups cannot be deleted."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        group.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Access Requests ──────────────────────────────────────────────────


PAGE_SIZE_AR = 25


class AccessRequestViewSet(ViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "iam.access_requests"
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "create",
        "partial_update": "edit",
        "approve": "approve",
        "reject": "approve",
        "revoke": "edit",
        "cancel": "edit",
        "expiring": "view",
    }

    def _get_org(self, request):
        profile = getattr(request.user, "profile", None)
        return profile.organization if profile else None

    def _base_qs(self, request):
        org = self._get_org(request)
        if not org:
            return AccessRequest.objects.none()
        return AccessRequest.objects.filter(organization=org).select_related(
            "requester", "approver", "requested_role"
        )

    def list(self, request):
        qs = self._base_qs(request)

        # Visibility scope
        scope = request.query_params.get("scope", "").lower()
        if scope == "mine":
            qs = qs.filter(requester=request.user)
        elif scope == "to_approve":
            qs = qs.filter(approver=request.user, status=AccessRequest.Status.PENDING)
        elif scope == "temporary":
            qs = qs.filter(
                kind__in=[AccessRequest.Kind.ROLE_GRANT, AccessRequest.Kind.ROLE_ELEVATION],
                granted_valid_until__isnull=False,
            )
        # default: all org-scoped requests visible to caller (they already pass RBAC)

        status_filter = request.query_params.get("status", "")
        if status_filter:
            qs = qs.filter(status=status_filter)

        kind_filter = request.query_params.get("kind", "")
        if kind_filter:
            qs = qs.filter(kind=kind_filter)

        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(reason__icontains=search)
                | Q(requested_resource__icontains=search)
                | Q(requested_role__name__icontains=search)
                | Q(requester__email__icontains=search)
                | Q(requester__first_name__icontains=search)
                | Q(requester__last_name__icontains=search)
            )

        try:
            page = int(request.query_params.get("page", 1))
        except (ValueError, TypeError):
            page = 1
        try:
            page_size = int(request.query_params.get("page_size", PAGE_SIZE_AR))
        except (ValueError, TypeError):
            page_size = PAGE_SIZE_AR
        start = (page - 1) * page_size
        end = start + page_size

        # Overview counts (current org-wide)
        org_qs = self._base_qs(request)
        overview = {
            "pending": org_qs.filter(status=AccessRequest.Status.PENDING).count(),
            "approved": org_qs.filter(status=AccessRequest.Status.APPROVED).count(),
            "rejected": org_qs.filter(status=AccessRequest.Status.REJECTED).count(),
            "to_approve": org_qs.filter(
                approver=request.user, status=AccessRequest.Status.PENDING
            ).count(),
        }

        total_count = qs.count()
        page_qs = qs[start:end]
        return Response({
            "count": total_count,
            "results": AccessRequestListSerializer(page_qs, many=True).data,
            "overview": overview,
        })

    def retrieve(self, request, pk=None):
        try:
            ar = self._base_qs(request).get(pk=pk)
        except AccessRequest.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(AccessRequestListSerializer(ar).data)

    def create(self, request):
        org = self._get_org(request)
        if not org:
            return Response({"detail": "No organization context."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = AccessRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Validate that requested_role belongs to the same org (or is system)
        requested_role = None
        if data.get("requested_role_id"):
            try:
                requested_role = Role.objects.filter(
                    Q(organization=org) | Q(organization__isnull=True),
                    pk=data["requested_role_id"],
                ).first()
            except Role.DoesNotExist:
                requested_role = None
            if not requested_role:
                return Response(
                    {"requested_role_id": "Role not available in your organization."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Resolve approver — must be in same org if specified
        approver = None
        if data.get("approver_id"):
            from django.contrib.auth import get_user_model as _gum
            ApproverUser = _gum()
            approver = ApproverUser.objects.filter(
                pk=data["approver_id"],
                profile__organization=org,
            ).first()
            if not approver:
                return Response(
                    {"approver_id": "Approver not in your organization."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        ar = AccessRequest.objects.create(
            organization=org,
            requester=request.user,
            kind=data["kind"],
            requested_role=requested_role,
            requested_resource=data.get("requested_resource", "") or "",
            reason=data["reason"],
            approver=approver,
            requested_valid_until=data.get("requested_valid_until"),
            request_expires_at=data.get("request_expires_at"),
        )
        audit_emit(
            event_type=UserSecurityEvent.EventType.ACCESS_REQUEST_SUBMITTED,
            request=request,
            status=UserSecurityEvent.Status.INFO,
            severity=UserSecurityEvent.Severity.LOW,
            target_type="access_request",
            target_id=str(ar.id),
            detail=f"{ar.get_kind_display()} requested by {request.user.email}",
            metadata={
                "kind": ar.kind,
                "requested_role_id": ar.requested_role_id,
                "approver_id": ar.approver_id,
            },
        )
        return Response(AccessRequestListSerializer(ar).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        """Limited PATCH: only the requester can update reason/requested_valid_until while pending."""
        try:
            ar = self._base_qs(request).get(pk=pk)
        except AccessRequest.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        if ar.requester_id != request.user.id:
            return Response({"detail": "Only the requester can edit."}, status=status.HTTP_403_FORBIDDEN)
        if ar.status != AccessRequest.Status.PENDING:
            return Response({"detail": "Only pending requests can be edited."}, status=status.HTTP_400_BAD_REQUEST)

        update_fields = []
        if "reason" in request.data:
            ar.reason = request.data["reason"]
            update_fields.append("reason")
        if "requested_valid_until" in request.data:
            ar.requested_valid_until = request.data["requested_valid_until"]
            update_fields.append("requested_valid_until")
        if update_fields:
            ar.save(update_fields=update_fields + ["updated_at"])
        return Response(AccessRequestListSerializer(ar).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        try:
            ar = self._base_qs(request).get(pk=pk)
        except AccessRequest.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        if ar.status != AccessRequest.Status.PENDING:
            return Response({"detail": f"Cannot approve a {ar.status} request."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = AccessRequestDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        granted_until = data.get("granted_valid_until") or ar.requested_valid_until
        if ar.kind == AccessRequest.Kind.ROLE_ELEVATION and not granted_until:
            return Response(
                {"granted_valid_until": "Elevation approvals must specify an expiry."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Apply role grant for ROLE_GRANT / ROLE_ELEVATION
        audit_emit(
            event_type=UserSecurityEvent.EventType.ACCESS_REQUEST_APPROVED,
            request=request,
            status=UserSecurityEvent.Status.SUCCESS,
            severity=UserSecurityEvent.Severity.MEDIUM if ar.kind == AccessRequest.Kind.ROLE_ELEVATION else UserSecurityEvent.Severity.LOW,
            target_type="access_request",
            target_id=str(ar.id),
            detail=f"Approved {ar.get_kind_display()} for {ar.requester.email}",
            metadata={
                "kind": ar.kind,
                "requested_role_id": ar.requested_role_id,
                "granted_valid_until": granted_until.isoformat() if granted_until else None,
            },
        )
        if ar.kind in (AccessRequest.Kind.ROLE_GRANT, AccessRequest.Kind.ROLE_ELEVATION):
            try:
                profile = ar.requester.profile
            except UserProfile.DoesNotExist:
                profile = None
            if profile and ar.requested_role and profile.organization_id == ar.organization_id:
                profile.assigned_role = ar.requested_role
                profile.assigned_role_valid_until = granted_until
                profile.save(update_fields=[
                    "assigned_role", "assigned_role_valid_until", "updated_at",
                ] if hasattr(profile, "updated_at") else ["assigned_role", "assigned_role_valid_until"])

        ar.status = AccessRequest.Status.APPROVED
        ar.approver = request.user
        ar.approval_decision_at = timezone.now()
        ar.approval_notes = data.get("notes", "") or ""
        ar.granted_valid_until = granted_until
        ar.save(update_fields=[
            "status", "approver", "approval_decision_at", "approval_notes",
            "granted_valid_until", "updated_at",
        ])
        return Response(AccessRequestListSerializer(ar).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        try:
            ar = self._base_qs(request).get(pk=pk)
        except AccessRequest.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        if ar.status != AccessRequest.Status.PENDING:
            return Response({"detail": f"Cannot reject a {ar.status} request."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = AccessRequestDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        audit_emit(
            event_type=UserSecurityEvent.EventType.ACCESS_REQUEST_REJECTED,
            request=request,
            status=UserSecurityEvent.Status.INFO,
            target_type="access_request",
            target_id=str(ar.id),
            detail=f"Rejected {ar.get_kind_display()} from {ar.requester.email}",
        )
        ar.status = AccessRequest.Status.REJECTED
        ar.approver = request.user
        ar.approval_decision_at = timezone.now()
        ar.approval_notes = serializer.validated_data.get("notes", "") or ""
        ar.save(update_fields=[
            "status", "approver", "approval_decision_at", "approval_notes", "updated_at",
        ])
        return Response(AccessRequestListSerializer(ar).data)

    @action(detail=True, methods=["post"])
    def revoke(self, request, pk=None):
        """Revoke a previously-approved request (admin action)."""
        try:
            ar = self._base_qs(request).get(pk=pk)
        except AccessRequest.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        if ar.status != AccessRequest.Status.APPROVED:
            return Response({"detail": f"Can only revoke approved requests; this one is {ar.status}."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = AccessRequestDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # If the grant was a role assignment, clear it from the requester.
        audit_emit(
            event_type=UserSecurityEvent.EventType.ACCESS_REQUEST_REVOKED,
            request=request,
            status=UserSecurityEvent.Status.SUCCESS,
            severity=UserSecurityEvent.Severity.HIGH,
            target_type="access_request",
            target_id=str(ar.id),
            detail=f"Revoked {ar.get_kind_display()} previously granted to {ar.requester.email}",
        )
        if ar.kind in (AccessRequest.Kind.ROLE_GRANT, AccessRequest.Kind.ROLE_ELEVATION):
            try:
                profile = ar.requester.profile
            except UserProfile.DoesNotExist:
                profile = None
            if profile and profile.assigned_role_id == (ar.requested_role_id or 0):
                profile.assigned_role = None
                profile.assigned_role_valid_until = None
                profile.save(update_fields=["assigned_role", "assigned_role_valid_until"])

        ar.status = AccessRequest.Status.REVOKED
        ar.approval_notes = (
            (ar.approval_notes + "\n---\n" if ar.approval_notes else "")
            + f"Revoked by {request.user.email}: " + (serializer.validated_data.get("notes", "") or "")
        )
        ar.save(update_fields=["status", "approval_notes", "updated_at"])
        return Response(AccessRequestListSerializer(ar).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Requester withdraws a pending request."""
        try:
            ar = self._base_qs(request).get(pk=pk)
        except AccessRequest.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        if ar.requester_id != request.user.id:
            return Response({"detail": "Only the requester can cancel."}, status=status.HTTP_403_FORBIDDEN)
        if ar.status != AccessRequest.Status.PENDING:
            return Response({"detail": f"Only pending requests can be cancelled; this one is {ar.status}."}, status=status.HTTP_400_BAD_REQUEST)
        ar.status = AccessRequest.Status.CANCELLED
        ar.save(update_fields=["status", "updated_at"])
        audit_emit(
            event_type=UserSecurityEvent.EventType.ACCESS_REQUEST_CANCELLED,
            request=request,
            status=UserSecurityEvent.Status.INFO,
            target_type="access_request",
            target_id=str(ar.id),
            detail=f"{ar.requester.email} cancelled their {ar.get_kind_display()} request",
        )
        return Response(AccessRequestListSerializer(ar).data)

    @action(detail=False, methods=["get"])
    def expiring(self, request):
        """Approved temporary grants expiring within `?within_days=` (default 7)."""
        try:
            within_days = int(request.query_params.get("within_days", 7))
        except (ValueError, TypeError):
            within_days = 7
        within_days = max(0, min(within_days, 365))

        now = timezone.now()
        soon = now + timedelta(days=within_days)
        qs = self._base_qs(request).filter(
            status=AccessRequest.Status.APPROVED,
            granted_valid_until__isnull=False,
            granted_valid_until__gt=now,
            granted_valid_until__lte=soon,
        ).order_by("granted_valid_until")

        already_expired = self._base_qs(request).filter(
            status=AccessRequest.Status.APPROVED,
            granted_valid_until__isnull=False,
            granted_valid_until__lte=now,
        ).count()

        return Response({
            "count": qs.count(),
            "results": AccessRequestListSerializer(qs, many=True).data,
            "overview": {
                "already_expired": already_expired,
                "within_days": within_days,
            },
        })


# ── Password policy + Login methods (org-level settings) ─────────────


PASSWORD_POLICY_FIELDS = (
    "password_min_length",
    "password_require_uppercase",
    "password_require_digits",
    "password_require_special",
    "password_max_age_days",
    "password_history_count",
)

LOGIN_METHOD_FIELDS = (
    "allow_password_login",
    "allow_oauth_login",
    "allow_passkey_login",
    "allow_sso_login",
)


class PasswordPolicyView(ViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "iam.auth_settings"
    rbac_action_map = {"retrieve": "view", "partial_update": "edit"}

    def _get_org(self, request):
        profile = getattr(request.user, "profile", None)
        return profile.organization if profile else None

    def retrieve(self, request):
        org = self._get_org(request)
        if not org:
            return Response({"detail": "No organization context."}, status=status.HTTP_400_BAD_REQUEST)
        return Response({f: getattr(org, f) for f in PASSWORD_POLICY_FIELDS})

    def partial_update(self, request):
        org = self._get_org(request)
        if not org:
            return Response({"detail": "No organization context."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = PasswordPolicySerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        update_fields = []
        for f in PASSWORD_POLICY_FIELDS:
            if f in serializer.validated_data:
                setattr(org, f, serializer.validated_data[f])
                update_fields.append(f)
        if update_fields:
            org.save(update_fields=update_fields)
            audit_emit(
                event_type=UserSecurityEvent.EventType.PASSWORD_POLICY_CHANGED,
                request=request,
                status=UserSecurityEvent.Status.INFO,
                severity=UserSecurityEvent.Severity.MEDIUM,
                target_type="organization",
                target_id=str(org.id),
                detail=f"Updated fields: {', '.join(update_fields)}",
                metadata={f: getattr(org, f) for f in update_fields},
            )
        return Response({f: getattr(org, f) for f in PASSWORD_POLICY_FIELDS})


class LoginMethodsView(ViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "iam.auth_settings"
    rbac_action_map = {"retrieve": "view", "partial_update": "edit"}

    def _get_org(self, request):
        profile = getattr(request.user, "profile", None)
        return profile.organization if profile else None

    def retrieve(self, request):
        org = self._get_org(request)
        if not org:
            return Response({"detail": "No organization context."}, status=status.HTTP_400_BAD_REQUEST)
        return Response({f: getattr(org, f) for f in LOGIN_METHOD_FIELDS})

    def partial_update(self, request):
        org = self._get_org(request)
        if not org:
            return Response({"detail": "No organization context."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = LoginMethodsSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Safety net: don't let an org disable EVERY login method
        merged = {f: getattr(org, f) for f in LOGIN_METHOD_FIELDS}
        merged.update(data)
        if not any(merged.values()):
            return Response(
                {"detail": "At least one login method must remain enabled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        update_fields = []
        for f in LOGIN_METHOD_FIELDS:
            if f in data:
                setattr(org, f, data[f])
                update_fields.append(f)
        if update_fields:
            org.save(update_fields=update_fields)
            audit_emit(
                event_type=UserSecurityEvent.EventType.LOGIN_METHODS_CHANGED,
                request=request,
                status=UserSecurityEvent.Status.INFO,
                severity=UserSecurityEvent.Severity.HIGH,
                target_type="organization",
                target_id=str(org.id),
                detail=f"Updated fields: {', '.join(update_fields)}",
                metadata={f: getattr(org, f) for f in update_fields},
            )
        return Response({f: getattr(org, f) for f in LOGIN_METHOD_FIELDS})


# ── Active sessions ──────────────────────────────────────────────────


class AuthSessionsView(ViewSet):
    """List and revoke a user's active auth sessions."""
    permission_classes = [IsAuthenticated]

    def _current_sid(self, request):
        """Pull the JWT-issued sid from the validated token (set by
        SessionAwareJWTAuthentication during authenticate())."""
        sid = getattr(request, "_jwt_sid", None)
        if sid:
            return str(sid)
        # Fallback: read from the validated token via Authorization header
        auth = request.successful_authenticator
        if hasattr(auth, "get_validated_token"):
            try:
                header = auth.get_header(request)
                raw = auth.get_raw_token(header) if header else None
                if raw:
                    token = auth.get_validated_token(raw)
                    return str(token.get("sid", ""))
            except Exception:
                pass
        return ""

    def list(self, request):
        current_sid = self._current_sid(request)
        qs = UserAuthSession.objects.filter(
            user=request.user,
            revoked_at__isnull=True,
        ).order_by("-last_seen_at")

        # Annotate is_current per row
        results = []
        for s in qs:
            data = UserAuthSessionSerializer(s, context={"request": request}).data
            data["is_current"] = (str(s.sid) == current_sid) if current_sid else False
            results.append(data)
        return Response({
            "count": len(results),
            "results": results,
            "current_sid": current_sid,
        })

    @action(detail=True, methods=["post"])
    def revoke(self, request, pk=None):
        """Revoke a specific session by sid (UUID, in URL)."""
        try:
            session = UserAuthSession.objects.get(sid=pk, user=request.user)
        except UserAuthSession.DoesNotExist:
            return Response({"detail": "Session not found."}, status=status.HTTP_404_NOT_FOUND)
        if session.revoked_at:
            return Response({"detail": "Already revoked."}, status=status.HTTP_400_BAD_REQUEST)
        audit_emit(
            event_type=UserSecurityEvent.EventType.SESSION_REVOKED,
            request=request,
            status=UserSecurityEvent.Status.SUCCESS,
            target_type="session",
            target_id=str(session.sid),
            detail=f"Revoked session from {session.ip_address or 'unknown IP'}",
        )
        session.revoked_at = timezone.now()
        session.revoke_reason = "user_revoked"
        session.save(update_fields=["revoked_at", "revoke_reason"])
        return Response({"detail": "Session revoked.", "sid": str(session.sid)})


# ── Audit events list (Cluster 6) ────────────────────────────────────


PAGE_SIZE_AUDIT = 50


class AuditEventsView(ViewSet):
    """Org-scoped feed of UserSecurityEvent rows. Backs the
    settings/audit/* sub-pages — each page passes a different
    ``event_type`` filter."""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.audit_compliance"
    rbac_action = "view"
    rbac_action_map = {"list": "view"}

    def _get_org(self, request):
        profile = getattr(request.user, "profile", None)
        return profile.organization if profile else None

    def list(self, request):
        org = self._get_org(request)
        is_super = request.user.is_superuser

        from apps.accounts.models import UserSecurityEvent
        qs = UserSecurityEvent.objects.select_related("user", "organization").order_by("-occurred_at")

        if is_super:
            requested_org = request.query_params.get("organization_id")
            if requested_org:
                try:
                    qs = qs.filter(organization_id=int(requested_org))
                except (ValueError, TypeError):
                    pass
        else:
            if org is None:
                return Response({"count": 0, "results": [], "overview": {}})
            qs = qs.filter(
                Q(organization=org) | Q(user__profile__organization=org)
            )

        event_type = request.query_params.get("event_type", "")
        if event_type:
            values = [v.strip() for v in event_type.split(",") if v.strip()]
            if values:
                qs = qs.filter(event_type__in=values)

        severity = request.query_params.get("severity", "")
        if severity:
            qs = qs.filter(severity__in=[v.strip() for v in severity.split(",") if v.strip()])

        status_filter = request.query_params.get("status", "")
        if status_filter:
            qs = qs.filter(status=status_filter)

        date_from = request.query_params.get("date_from")
        if date_from:
            qs = qs.filter(occurred_at__gte=date_from)
        date_to = request.query_params.get("date_to")
        if date_to:
            qs = qs.filter(occurred_at__lte=date_to)

        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(detail__icontains=search)
                | Q(principal__icontains=search)
                | Q(target_id__icontains=search)
                | Q(user__email__icontains=search)
                | Q(ip_address__icontains=search)
            )

        # Pagination
        try:
            page = int(request.query_params.get("page", 1))
        except (ValueError, TypeError):
            page = 1
        try:
            page_size = int(request.query_params.get("page_size", PAGE_SIZE_AUDIT))
        except (ValueError, TypeError):
            page_size = PAGE_SIZE_AUDIT
        page_size = max(1, min(page_size, 200))
        start = (page - 1) * page_size
        end = start + page_size

        # Overview within current filters
        from django.db.models import Count as _Count
        total_count = qs.count()
        severity_breakdown = dict(
            qs.values("severity").annotate(c=_Count("id")).values_list("severity", "c")
        )
        recent_24h = qs.filter(occurred_at__gte=timezone.now() - timedelta(hours=24)).count()

        return Response({
            "count": total_count,
            "results": AuditEventSerializer(qs[start:end], many=True).data,
            "overview": {
                "total": total_count,
                "recent_24h": recent_24h,
                "by_severity": severity_breakdown,
            },
        })


# ── Compliance: Access Reviews / Role Certification (Cluster 9) ──────


PAGE_SIZE_REVIEWS = 25


class AccessReviewCampaignViewSet(ViewSet):
    """CRUD over AccessReviewCampaign + nested item decisions.

    Backs the iam/compliance/access-reviews and role-certification
    pages — both surfaces use the same model with different ?kind=
    filters."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "iam.compliance"
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "create",
        "partial_update": "edit",
        "destroy": "delete",
        "items": "view",
        "decide_item": "edit",
        "start": "edit",
        "complete": "edit",
        "cancel": "edit",
    }

    def _get_org(self, request):
        profile = getattr(request.user, "profile", None)
        return profile.organization if profile else None

    def _qs(self, request):
        org = self._get_org(request)
        if not org:
            return AccessReviewCampaign.objects.none()
        return (
            AccessReviewCampaign.objects.filter(organization=org)
            .select_related("target_role", "created_by")
            .annotate(
                item_count=Count("items"),
                pending_count=Count("items", filter=Q(items__decision="pending")),
                approved_count=Count("items", filter=Q(items__decision="approved")),
                revoked_count=Count("items", filter=Q(items__decision="revoked")),
            )
        )

    def list(self, request):
        qs = self._qs(request)
        kind = request.query_params.get("kind")
        if kind:
            qs = qs.filter(kind=kind)
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        try:
            page = int(request.query_params.get("page", 1))
        except (ValueError, TypeError):
            page = 1
        page_size = PAGE_SIZE_REVIEWS
        start = (page - 1) * page_size
        end = start + page_size
        total = qs.count()
        qs = qs.order_by("-created_at")
        return Response({
            "count": total,
            "results": AccessReviewCampaignListSerializer(qs[start:end], many=True).data,
        })

    def retrieve(self, request, pk=None):
        try:
            c = self._qs(request).get(pk=pk)
        except AccessReviewCampaign.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(AccessReviewCampaignListSerializer(c).data)

    def create(self, request):
        org = self._get_org(request)
        if not org:
            return Response({"detail": "No org context."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = AccessReviewCampaignWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        target_role = None
        if data.get("target_role_id"):
            target_role = Role.objects.filter(
                Q(organization=org) | Q(organization__isnull=True),
                pk=data["target_role_id"],
            ).first()
            if not target_role:
                return Response(
                    {"target_role_id": "Role not available in your organization."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        campaign = AccessReviewCampaign.objects.create(
            organization=org,
            kind=data["kind"],
            name=data["name"],
            description=data.get("description", "") or "",
            target_role=target_role,
            starts_at=data.get("starts_at"),
            ends_at=data.get("ends_at"),
            created_by=request.user,
        )

        # Auto-populate items from target_role if specified
        if target_role:
            users_with_role = UserProfile.objects.filter(
                organization=org, assigned_role=target_role
            ).select_related("user", "assigned_role")
            AccessReviewItem.objects.bulk_create([
                AccessReviewItem(
                    campaign=campaign,
                    user=p.user,
                    role_at_review=p.assigned_role,
                ) for p in users_with_role
            ])

        # Re-fetch with annotations
        c = self._qs(request).get(pk=campaign.pk)
        return Response(AccessReviewCampaignListSerializer(c).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        try:
            c = self._qs(request).get(pk=pk)
        except AccessReviewCampaign.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = AccessReviewCampaignWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        for f in ("name", "description", "starts_at", "ends_at"):
            if f in data:
                setattr(c, f, data[f])
        c.save()
        c = self._qs(request).get(pk=c.pk)
        return Response(AccessReviewCampaignListSerializer(c).data)

    def destroy(self, request, pk=None):
        try:
            c = self._qs(request).get(pk=pk)
        except AccessReviewCampaign.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        if c.status == AccessReviewCampaign.Status.IN_PROGRESS:
            return Response(
                {"detail": "Cannot delete an in-progress campaign. Cancel it first."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        c.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        try:
            c = self._qs(request).get(pk=pk)
        except AccessReviewCampaign.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        if c.status != AccessReviewCampaign.Status.DRAFT:
            return Response({"detail": f"Campaign is {c.status}, cannot start."}, status=status.HTTP_400_BAD_REQUEST)
        c.status = AccessReviewCampaign.Status.IN_PROGRESS
        if not c.starts_at:
            c.starts_at = timezone.now()
        c.save(update_fields=["status", "starts_at", "updated_at"])
        return Response(AccessReviewCampaignListSerializer(self._qs(request).get(pk=c.pk)).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        try:
            c = self._qs(request).get(pk=pk)
        except AccessReviewCampaign.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        if c.status != AccessReviewCampaign.Status.IN_PROGRESS:
            return Response({"detail": f"Campaign is {c.status}, cannot complete."}, status=status.HTTP_400_BAD_REQUEST)
        c.status = AccessReviewCampaign.Status.COMPLETED
        c.completed_at = timezone.now()
        c.save(update_fields=["status", "completed_at", "updated_at"])
        return Response(AccessReviewCampaignListSerializer(self._qs(request).get(pk=c.pk)).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        try:
            c = self._qs(request).get(pk=pk)
        except AccessReviewCampaign.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        if c.status in (AccessReviewCampaign.Status.COMPLETED, AccessReviewCampaign.Status.CANCELLED):
            return Response({"detail": f"Campaign is already {c.status}."}, status=status.HTTP_400_BAD_REQUEST)
        c.status = AccessReviewCampaign.Status.CANCELLED
        c.save(update_fields=["status", "updated_at"])
        return Response(AccessReviewCampaignListSerializer(self._qs(request).get(pk=c.pk)).data)

    @action(detail=True, methods=["get"])
    def items(self, request, pk=None):
        try:
            c = self._qs(request).get(pk=pk)
        except AccessReviewCampaign.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        item_qs = (
            AccessReviewItem.objects
            .filter(campaign=c)
            .select_related("user", "role_at_review", "decided_by")
            .order_by("user__first_name", "user__last_name")
        )
        decision_filter = request.query_params.get("decision", "")
        if decision_filter:
            item_qs = item_qs.filter(decision=decision_filter)
        return Response({
            "count": item_qs.count(),
            "results": AccessReviewItemSerializer(item_qs, many=True).data,
            "campaign": AccessReviewCampaignListSerializer(c).data,
        })

    @action(detail=True, methods=["post"], url_path=r"items/(?P<item_id>[0-9]+)/decide")
    def decide_item(self, request, pk=None, item_id=None):
        try:
            c = self._qs(request).get(pk=pk)
        except AccessReviewCampaign.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        if c.status != AccessReviewCampaign.Status.IN_PROGRESS:
            return Response({"detail": "Campaign is not in progress."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            item = AccessReviewItem.objects.get(pk=item_id, campaign=c)
        except AccessReviewItem.DoesNotExist:
            return Response({"detail": "Item not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = AccessReviewItemDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        item.decision = d["decision"]
        item.decided_by = request.user
        item.decided_at = timezone.now()
        item.notes = d.get("notes", "") or ""
        item.save(update_fields=["decision", "decided_by", "decided_at", "notes"])

        # If REVOKED, also clear the user's assigned_role on the profile
        if d["decision"] == AccessReviewItem.Decision.REVOKED:
            try:
                profile = item.user.profile
                if profile and item.role_at_review_id == profile.assigned_role_id:
                    profile.assigned_role = None
                    profile.assigned_role_valid_until = None
                    profile.save(update_fields=["assigned_role", "assigned_role_valid_until"])
                    audit_emit(
                        event_type=UserSecurityEvent.EventType.ROLE_UNASSIGNED,
                        request=request,
                        status=UserSecurityEvent.Status.INFO,
                        severity=UserSecurityEvent.Severity.MEDIUM,
                        target_type="user",
                        target_id=str(item.user_id),
                        detail=f"Role removed via access review #{c.id}",
                        metadata={"campaign_id": c.id, "item_id": item.id},
                    )
            except UserProfile.DoesNotExist:
                pass

        return Response(AccessReviewItemSerializer(item).data)


# ── Compliance: Dormant Accounts ─────────────────────────────────────


class DormantAccountsView(ViewSet):
    """List org users with no recent login activity."""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "iam.compliance"
    rbac_action = "view"

    def _get_org(self, request):
        profile = getattr(request.user, "profile", None)
        return profile.organization if profile else None

    def list(self, request):
        org = self._get_org(request)
        if not org:
            return Response({"count": 0, "results": [], "overview": {}})

        try:
            threshold_days = int(request.query_params.get("threshold_days", 60))
        except (ValueError, TypeError):
            threshold_days = 60
        threshold_days = max(7, min(threshold_days, 365))
        cutoff = timezone.now() - timedelta(days=threshold_days)

        from django.contrib.auth import get_user_model as _gum
        Usr = _gum()
        # Org users only (active)
        base = Usr.objects.filter(profile__organization=org, is_active=True)

        dormant = base.filter(
            Q(last_login__isnull=True) | Q(last_login__lt=cutoff)
        ).select_related("profile", "profile__assigned_role").order_by("last_login")

        never_logged_in = base.filter(last_login__isnull=True).count()
        dormant_count = dormant.count()
        active_count = base.filter(last_login__gte=cutoff).count()

        results = []
        for u in dormant[:200]:
            profile = getattr(u, "profile", None)
            results.append({
                "id": u.id,
                "name": u.get_full_name() or u.email,
                "email": u.email,
                "last_login": u.last_login.isoformat() if u.last_login else None,
                "date_joined": u.date_joined.isoformat() if u.date_joined else None,
                "role_name": profile.assigned_role.name if profile and profile.assigned_role else "",
                "user_status": profile.user_status if profile else "",
                "days_since_login": (timezone.now() - u.last_login).days if u.last_login else None,
            })

        return Response({
            "count": dormant_count,
            "results": results,
            "overview": {
                "threshold_days": threshold_days,
                "dormant": dormant_count,
                "active": active_count,
                "never_logged_in": never_logged_in,
            },
        })


# ── Compliance: Privilege Risk Analysis ──────────────────────────────


class PrivilegeRiskView(ViewSet):
    """Risk score per user based on permission breadth + recent activity.

    Score is a simple aggregate (0-100) computed from:
      - Permission breadth: count of granted permissions in the user's role
      - Sensitivity: presence of system roles, or roles with admin/configure actions
      - Stale-ness: last_login age (older = harder to monitor)
      - Recent risky actions: revoked / auto-revoked grants in the last 30 days

    Intentionally simple — production scoring should be calibrated with
    real org data. v1 surfaces the framework; tuning is a follow-up.
    """
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "iam.compliance"
    rbac_action = "view"

    def _get_org(self, request):
        profile = getattr(request.user, "profile", None)
        return profile.organization if profile else None

    def list(self, request):
        org = self._get_org(request)
        if not org:
            return Response({"count": 0, "results": [], "overview": {}})

        from django.contrib.auth import get_user_model as _gum
        from apps.settings.models import RolePermission
        Usr = _gum()

        users = (
            UserProfile.objects
            .filter(organization=org, user__is_active=True)
            .select_related("user", "assigned_role")
        )

        now = timezone.now()
        results = []
        for p in users:
            perm_count = 0
            sensitive = False
            is_system = False
            if p.assigned_role_id:
                perm_count = RolePermission.objects.filter(role_id=p.assigned_role_id).count()
                is_system = bool(p.assigned_role.is_system) if p.assigned_role else False
                sensitive = RolePermission.objects.filter(
                    role_id=p.assigned_role_id,
                    action__in=["admin_override", "configure", "delete"],
                ).exists()

            stale_days = (now - p.user.last_login).days if p.user.last_login else 999

            recent_risky = UserSecurityEvent.objects.filter(
                user=p.user,
                event_type__in=[
                    UserSecurityEvent.EventType.ACCESS_REQUEST_REVOKED,
                    UserSecurityEvent.EventType.ACCESS_GRANT_AUTO_REVOKED,
                    UserSecurityEvent.EventType.LOGIN_FAILED,
                ],
                occurred_at__gte=now - timedelta(days=30),
            ).count()

            # Composite score (0-100)
            score = 0
            score += min(perm_count * 2, 40)            # breadth → 40 max
            score += 20 if sensitive else 0             # sensitivity → 20
            score += 10 if is_system else 0             # system role → 10
            score += min(stale_days // 30, 5) * 4       # stale → 20 max
            score += min(recent_risky, 10)              # recent risky → 10
            score = min(score, 100)

            tier = "critical" if score >= 80 else "high" if score >= 60 else "medium" if score >= 30 else "low"

            results.append({
                "user_id": p.user_id,
                "name": p.user.get_full_name() or p.user.email,
                "email": p.user.email,
                "role_name": p.assigned_role.name if p.assigned_role else "",
                "permission_count": perm_count,
                "is_system_role": is_system,
                "sensitive_permissions": sensitive,
                "days_since_login": stale_days if p.user.last_login else None,
                "recent_risky_events": recent_risky,
                "score": score,
                "tier": tier,
            })

        results.sort(key=lambda r: r["score"], reverse=True)

        # Overview tier counts
        tier_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        for r in results:
            tier_counts[r["tier"]] += 1

        return Response({
            "count": len(results),
            "results": results[:100],
            "overview": tier_counts,
        })


# ── Federation: Identity Providers (Cluster 8) ───────────────────────


class IdentityProviderViewSet(ViewSet):
    """CRUD over per-org IdentityProvider rows.

    Stores configuration only — actual auth-backend integration (OIDC
    discovery, SAML metadata parsing, LDAP bind, Google Directory API
    sync) is the next phase. test and sync_now actions return 501
    until the integration phase lands for the corresponding kind."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "iam.federation"
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "create",
        "partial_update": "edit",
        "destroy": "delete",
        "test": "view",
        "sync_now": "edit",
    }

    # Per-kind whitelist of which provider kinds have live integration.
    # Currently only Google Workspace is on the path to be wired (Phase 1
    # of Cluster 8). Others stay in stub mode until their backend lands.
    LIVE_KINDS: tuple[str, ...] = ()  # none yet — all stubbed

    def _get_org(self, request):
        profile = getattr(request.user, "profile", None)
        return profile.organization if profile else None

    def _qs(self, request):
        org = self._get_org(request)
        if not org:
            return IdentityProvider.objects.none()
        return IdentityProvider.objects.filter(organization=org)

    def _merge_secrets(self, existing: dict, incoming: dict) -> dict:
        """When a client PATCHes secrets, only update keys whose values
        are not the mask sentinel — so editing other fields doesn't
        clobber secrets the user didn't re-enter."""
        from .iam_serializers import SECRET_MASK
        out = dict(existing or {})
        for k, v in (incoming or {}).items():
            if v == SECRET_MASK:
                continue  # client sent back the mask — preserve existing
            if v == "" or v is None:
                # Empty string explicitly clears the secret
                out.pop(k, None)
                continue
            out[k] = v
        return out

    def list(self, request):
        qs = self._qs(request)
        kind = request.query_params.get("kind")
        if kind:
            qs = qs.filter(kind=kind)
        return Response({
            "count": qs.count(),
            "results": IdentityProviderSerializer(qs.order_by("kind", "name"), many=True).data,
        })

    def retrieve(self, request, pk=None):
        try:
            p = self._qs(request).get(pk=pk)
        except IdentityProvider.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(IdentityProviderSerializer(p).data)

    def create(self, request):
        org = self._get_org(request)
        if not org:
            return Response({"detail": "No org context."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = IdentityProviderWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        if "kind" not in d or "name" not in d:
            return Response(
                {"detail": "kind and name are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        provider = IdentityProvider.objects.create(
            organization=org,
            kind=d["kind"],
            name=d["name"],
            is_enabled=d.get("is_enabled", False),
            config=d.get("config", {}) or {},
            secrets=d.get("secrets", {}) or {},
            created_by=request.user,
        )
        return Response(IdentityProviderSerializer(provider).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        try:
            p = self._qs(request).get(pk=pk)
        except IdentityProvider.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = IdentityProviderWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        update_fields = []
        for f in ("name", "is_enabled"):
            if f in d:
                setattr(p, f, d[f])
                update_fields.append(f)
        if "config" in d:
            # Merge to preserve untouched keys
            p.config = {**(p.config or {}), **(d["config"] or {})}
            update_fields.append("config")
        if "secrets" in d:
            p.secrets = self._merge_secrets(p.secrets, d["secrets"])
            update_fields.append("secrets")
        if update_fields:
            p.save(update_fields=update_fields + ["updated_at"])
        return Response(IdentityProviderSerializer(p).data)

    def destroy(self, request, pk=None):
        try:
            p = self._qs(request).get(pk=pk)
        except IdentityProvider.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        p.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def test(self, request, pk=None):
        """Stub: structural validation only. Live connection-test
        requires the kind-specific integration phase."""
        try:
            p = self._qs(request).get(pk=pk)
        except IdentityProvider.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        # Structural validation: required keys per kind
        REQUIRED = {
            IdentityProvider.Kind.ACTIVE_DIRECTORY: {
                "config": ["server_uri", "base_dn", "bind_dn"],
                "secrets": ["bind_password"],
            },
            IdentityProvider.Kind.AZURE_AD: {
                "config": ["tenant_id", "client_id", "redirect_uri"],
                "secrets": ["client_secret"],
            },
            IdentityProvider.Kind.GOOGLE_WORKSPACE: {
                "config": ["domain"],
                "secrets": [],
            },
            IdentityProvider.Kind.LDAP: {
                "config": ["server_uri", "base_dn", "bind_dn"],
                "secrets": ["bind_password"],
            },
            IdentityProvider.Kind.SAML_OIDC: {
                "config": ["entity_id"],
                "secrets": [],
            },
        }.get(p.kind, {"config": [], "secrets": []})

        missing_config = [k for k in REQUIRED["config"] if not (p.config or {}).get(k)]
        missing_secrets = [k for k in REQUIRED["secrets"] if not (p.secrets or {}).get(k)]

        is_live_kind = p.kind in self.LIVE_KINDS

        if missing_config or missing_secrets:
            return Response({
                "ok": False,
                "stage": "structural",
                "message": "Missing required fields.",
                "missing_config": missing_config,
                "missing_secrets": missing_secrets,
                "live_test_available": is_live_kind,
            }, status=status.HTTP_400_BAD_REQUEST)

        if not is_live_kind:
            return Response({
                "ok": True,
                "stage": "structural",
                "message": (
                    "Configuration looks structurally complete. Live "
                    "connection test will be available once the "
                    f"{p.get_kind_display()} integration phase lands."
                ),
                "live_test_available": False,
            }, status=status.HTTP_501_NOT_IMPLEMENTED)

        # Future: dispatch to a per-kind test handler
        return Response({
            "ok": True,
            "stage": "live",
            "message": "Connection succeeded.",
            "live_test_available": True,
        })

    @action(detail=True, methods=["post"], url_path="sync")
    def sync_now(self, request, pk=None):
        """Stub: marks the provider as synced (status=stub) until the
        kind-specific integration phase lands."""
        try:
            p = self._qs(request).get(pk=pk)
        except IdentityProvider.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        is_live_kind = p.kind in self.LIVE_KINDS

        p.last_synced_at = timezone.now()
        p.last_sync_status = (
            IdentityProvider.SyncStatus.STUB if not is_live_kind
            else IdentityProvider.SyncStatus.SUCCESS
        )
        p.last_sync_message = (
            f"Stub sync — real {p.get_kind_display()} sync will be available once the integration phase lands."
            if not is_live_kind
            else "Sync completed."
        )
        p.save(update_fields=["last_synced_at", "last_sync_status", "last_sync_message", "updated_at"])

        if not is_live_kind:
            return Response(IdentityProviderSerializer(p).data, status=status.HTTP_501_NOT_IMPLEMENTED)
        return Response(IdentityProviderSerializer(p).data)


# ── Access Policies (Cluster 4) ──────────────────────────────────────


class AccessPolicyViewSet(ViewSet):
    """CRUD over apps.settings.AccessPolicy + nested PolicyCondition /
    PolicyAction children. Backs the iam/access-policies/* surfaces.

    Real enforcement happens via apps.accounts.policy_middleware
    (which is opt-in — not auto-wired into MIDDLEWARE)."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "iam.access_policies"
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "create",
        "partial_update": "edit",
        "destroy": "delete",
        "test": "view",
    }

    def _get_org(self, request):
        profile = getattr(request.user, "profile", None)
        return profile.organization if profile else None

    def _qs(self, request):
        from apps.settings.models import AccessPolicy
        org = self._get_org(request)
        if not org:
            return AccessPolicy.objects.none()
        return AccessPolicy.objects.filter(organization=org).annotate(
            condition_count=Count("conditions")
        ).prefetch_related("conditions", "policy_actions")

    def list(self, request):
        qs = self._qs(request)
        kind = request.query_params.get("kind")
        if kind:
            qs = qs.filter(kind=kind)
        is_active = request.query_params.get("is_active")
        if is_active in ("true", "false"):
            qs = qs.filter(is_active=(is_active == "true"))
        return Response({
            "count": qs.count(),
            "results": AccessPolicyListSerializer(qs.order_by("priority", "name"), many=True).data,
        })

    def retrieve(self, request, pk=None):
        from apps.settings.models import AccessPolicy
        try:
            p = self._qs(request).get(pk=pk)
        except AccessPolicy.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(AccessPolicyDetailSerializer(p).data)

    def _slug_key(self, name: str, org_id: int) -> str:
        from django.utils.text import slugify
        from apps.settings.models import AccessPolicy
        base = slugify(name)[:100] or "policy"
        candidate = base
        n = 2
        while AccessPolicy.objects.filter(organization_id=org_id, key=candidate).exists():
            candidate = f"{base}-{n}"
            n += 1
        return candidate

    def _replace_children(self, policy, conditions, actions):
        from apps.settings.models import PolicyCondition, PolicyAction
        if conditions is not None:
            PolicyCondition.objects.filter(access_policy=policy).delete()
            PolicyCondition.objects.bulk_create([
                PolicyCondition(
                    access_policy=policy,
                    condition_type=c["condition_type"],
                    operator=c.get("operator", "eq"),
                    value=c.get("value", {}),
                    sort_order=c.get("sort_order", idx),
                    is_active=c.get("is_active", True),
                ) for idx, c in enumerate(conditions)
            ])
        if actions is not None:
            PolicyAction.objects.filter(access_policy=policy).delete()
            PolicyAction.objects.bulk_create([
                PolicyAction(
                    access_policy=policy,
                    action_type=a["action_type"],
                    parameters=a.get("parameters", {}),
                    message=a.get("message", ""),
                    sort_order=a.get("sort_order", idx),
                    is_active=a.get("is_active", True),
                ) for idx, a in enumerate(actions)
            ])

    def create(self, request):
        from apps.settings.models import AccessPolicy
        org = self._get_org(request)
        if not org:
            return Response({"detail": "No org context."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = AccessPolicyWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        if "name" not in d or "kind" not in d:
            return Response(
                {"detail": "name and kind are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        key = d.get("key") or self._slug_key(d["name"], org.id)
        policy = AccessPolicy.objects.create(
            organization=org,
            key=key,
            kind=d["kind"],
            name=d["name"],
            description=d.get("description", "") or "",
            module=d.get("module", "") or "",
            sub_module=d.get("sub_module", "") or "",
            action=d.get("action", "") or "",
            priority=d.get("priority", 100),
            is_active=d.get("is_active", False),
        )
        self._replace_children(policy, d.get("conditions"), d.get("actions"))
        # Re-fetch with prefetch for response
        policy = self._qs(request).get(pk=policy.pk)
        return Response(AccessPolicyDetailSerializer(policy).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        from apps.settings.models import AccessPolicy
        try:
            p = self._qs(request).get(pk=pk)
        except AccessPolicy.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = AccessPolicyWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        update_fields = []
        for f in ("name", "description", "priority", "is_active", "kind", "module", "sub_module", "action"):
            if f in d:
                setattr(p, f, d[f])
                update_fields.append(f)
        if update_fields:
            p.save(update_fields=update_fields + ["updated_at"])
        # Children replacement only if explicitly sent
        self._replace_children(
            p,
            d.get("conditions") if "conditions" in serializer.initial_data else None,
            d.get("actions") if "actions" in serializer.initial_data else None,
        )
        p = self._qs(request).get(pk=p.pk)
        return Response(AccessPolicyDetailSerializer(p).data)

    def destroy(self, request, pk=None):
        from apps.settings.models import AccessPolicy
        try:
            p = self._qs(request).get(pk=pk)
        except AccessPolicy.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        p.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def test(self, request, pk=None):
        """Dry-run: evaluate this single policy against the current
        request context and return what its decision would be. Useful
        for previewing without enabling enforcement."""
        from apps.settings.models import AccessPolicy
        from .policy_engine import (
            _CONDITION_HANDLERS,
            _ACTION_TO_DECISION,
        )
        try:
            p = self._qs(request).get(pk=pk)
        except AccessPolicy.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        condition_results = []
        all_match = True
        for cond in p.conditions.all().order_by("sort_order", "id"):
            handler = _CONDITION_HANDLERS.get(cond.condition_type)
            try:
                matched = handler(cond, request) if handler else None
            except Exception as exc:
                matched = None
                err = str(exc)
            else:
                err = ""
            condition_results.append({
                "condition_type": cond.condition_type,
                "matched": matched,
                "error": err,
                "is_active": cond.is_active,
            })
            if cond.is_active and matched is False:
                all_match = False

        primary_action = next((a for a in p.policy_actions.all() if a.is_active), None)
        decision_action = "allow"
        if all_match and primary_action:
            decision_action = _ACTION_TO_DECISION.get(primary_action.action_type, "allow")

        return Response({
            "policy_id": p.id,
            "policy_name": p.name,
            "all_active_conditions_matched": all_match,
            "would_act": all_match,
            "decision_action": decision_action if all_match else "skipped",
            "conditions": condition_results,
        })


# ── Webhooks (Cluster 2) ─────────────────────────────────────────────


import secrets as _secrets
import hashlib as _hashlib
import hmac as _hmac
import json as _json


def _generate_webhook_secret() -> str:
    return _secrets.token_urlsafe(32)


def _generate_app_token() -> tuple[str, str, str]:
    """Returns (full_token, prefix, sha256_hash)."""
    raw = _secrets.token_urlsafe(32)
    full = f"dvo_{raw}"
    prefix = full[:12]
    h = _hashlib.sha256(full.encode("utf-8")).hexdigest()
    return full, prefix, h


class WebhookViewSet(ViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "iam.webhooks"
    rbac_action_map = {
        "list": "view", "retrieve": "view", "create": "create",
        "partial_update": "edit", "destroy": "delete",
        "test": "edit", "deliveries": "view",
    }

    def _get_org(self, request):
        profile = getattr(request.user, "profile", None)
        return profile.organization if profile else None

    def _qs(self, request):
        org = self._get_org(request)
        if not org:
            return Webhook.objects.none()
        return Webhook.objects.filter(organization=org)

    def list(self, request):
        qs = self._qs(request).order_by("name")
        return Response({
            "count": qs.count(),
            "results": WebhookSerializer(qs, many=True).data,
        })

    def retrieve(self, request, pk=None):
        try:
            w = self._qs(request).get(pk=pk)
        except Webhook.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(WebhookSerializer(w).data)

    def create(self, request):
        org = self._get_org(request)
        if not org:
            return Response({"detail": "No org context."}, status=status.HTTP_400_BAD_REQUEST)
        s = WebhookWriteSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        if "name" not in d or "url" not in d:
            return Response({"detail": "name and url are required."}, status=status.HTTP_400_BAD_REQUEST)
        w = Webhook.objects.create(
            organization=org,
            name=d["name"],
            url=d["url"],
            events=d.get("events", []) or [],
            is_active=d.get("is_active", True),
            secret=_generate_webhook_secret(),
            created_by=request.user,
        )
        # Show the secret ONCE on create. Subsequent fetches mask it.
        out = WebhookSerializer(w).data
        out["secret"] = w.secret
        return Response(out, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        try:
            w = self._qs(request).get(pk=pk)
        except Webhook.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        s = WebhookWriteSerializer(data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        update = []
        for f in ("name", "url", "events", "is_active"):
            if f in d:
                setattr(w, f, d[f])
                update.append(f)
        rotated = bool(d.get("rotate_secret"))
        if rotated:
            w.secret = _generate_webhook_secret()
            update.append("secret")
        if update:
            w.save(update_fields=update + ["updated_at"])
        out = WebhookSerializer(w).data
        if rotated:
            out["secret"] = w.secret  # one-shot return for the rotation
        return Response(out)

    def destroy(self, request, pk=None):
        try:
            w = self._qs(request).get(pk=pk)
        except Webhook.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        w.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def test(self, request, pk=None):
        """Synchronously POST a test payload to the webhook URL.
        Logs the attempt as a WebhookDelivery row."""
        import requests
        try:
            w = self._qs(request).get(pk=pk)
        except Webhook.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        payload = {
            "event": "webhook.test",
            "webhook_id": w.id,
            "test": True,
            "timestamp": timezone.now().isoformat(),
            "message": "Test delivery from DeveloperOS.",
        }
        body = _json.dumps(payload).encode("utf-8")
        signature = _hmac.new(
            w.secret.encode("utf-8") if w.secret else b"",
            body,
            _hashlib.sha256,
        ).hexdigest() if w.secret else ""

        delivery = WebhookDelivery.objects.create(
            webhook=w,
            event_name="webhook.test",
            payload=payload,
            status=WebhookDelivery.Status.PENDING,
            attempt_number=1,
        )

        try:
            resp = requests.post(
                w.url,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "X-DeveloperOS-Event": "webhook.test",
                    "X-DeveloperOS-Signature": f"sha256={signature}",
                    "User-Agent": "DeveloperOS-Webhook/1.0",
                },
                timeout=8,
            )
            ok = 200 <= resp.status_code < 300
            delivery.response_code = resp.status_code
            delivery.response_body = (resp.text or "")[:2000]
            delivery.status = WebhookDelivery.Status.DELIVERED if ok else WebhookDelivery.Status.FAILED
            delivery.delivered_at = timezone.now() if ok else None
            delivery.save()

            w.last_delivery_at = timezone.now()
            w.last_delivery_status = "delivered" if ok else "failed"
            w.last_delivery_message = f"HTTP {resp.status_code}"
            w.delivery_count = (w.delivery_count or 0) + 1
            if not ok:
                w.failure_count = (w.failure_count or 0) + 1
            w.save(update_fields=[
                "last_delivery_at", "last_delivery_status",
                "last_delivery_message", "delivery_count", "failure_count",
                "updated_at",
            ])
            return Response({
                "ok": ok,
                "response_code": resp.status_code,
                "response_body": (resp.text or "")[:500],
                "delivery_id": delivery.id,
            })
        except Exception as exc:
            err = str(exc)[:500]
            delivery.status = WebhookDelivery.Status.FAILED
            delivery.error_message = err
            delivery.save(update_fields=["status", "error_message"])
            w.last_delivery_at = timezone.now()
            w.last_delivery_status = "failed"
            w.last_delivery_message = err[:200]
            w.delivery_count = (w.delivery_count or 0) + 1
            w.failure_count = (w.failure_count or 0) + 1
            w.save(update_fields=[
                "last_delivery_at", "last_delivery_status",
                "last_delivery_message", "delivery_count", "failure_count",
                "updated_at",
            ])
            return Response({"ok": False, "error": err, "delivery_id": delivery.id}, status=status.HTTP_502_BAD_GATEWAY)

    @action(detail=True, methods=["get"])
    def deliveries(self, request, pk=None):
        try:
            w = self._qs(request).get(pk=pk)
        except Webhook.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        qs = WebhookDelivery.objects.filter(webhook=w).order_by("-created_at")[:50]
        return Response({
            "count": qs.count(),
            "results": WebhookDeliverySerializer(qs, many=True).data,
        })


# ── Application Tokens (Cluster 2) ───────────────────────────────────


class ApplicationTokenViewSet(ViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "iam.app_tokens"
    rbac_action_map = {
        "list": "view", "retrieve": "view", "create": "create",
        "partial_update": "edit", "destroy": "delete",
        "regenerate": "edit",
    }

    def _get_org(self, request):
        profile = getattr(request.user, "profile", None)
        return profile.organization if profile else None

    def _qs(self, request):
        org = self._get_org(request)
        if not org:
            return ApplicationToken.objects.none()
        return ApplicationToken.objects.filter(organization=org)

    def list(self, request):
        qs = self._qs(request).order_by("-created_at")
        return Response({
            "count": qs.count(),
            "results": ApplicationTokenSerializer(qs, many=True).data,
        })

    def retrieve(self, request, pk=None):
        try:
            t = self._qs(request).get(pk=pk)
        except ApplicationToken.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(ApplicationTokenSerializer(t).data)

    def create(self, request):
        org = self._get_org(request)
        if not org:
            return Response({"detail": "No org context."}, status=status.HTTP_400_BAD_REQUEST)
        s = ApplicationTokenWriteSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        if "name" not in d:
            return Response({"detail": "name is required."}, status=status.HTTP_400_BAD_REQUEST)
        full, prefix, h = _generate_app_token()
        t = ApplicationToken.objects.create(
            organization=org,
            name=d["name"],
            description=d.get("description", "") or "",
            scopes=d.get("scopes", []) or [],
            expires_at=d.get("expires_at"),
            is_active=d.get("is_active", True),
            token_hash=h,
            prefix=prefix,
            created_by=request.user,
        )
        out = ApplicationTokenSerializer(t).data
        out["token"] = full  # one-shot return
        return Response(out, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        try:
            t = self._qs(request).get(pk=pk)
        except ApplicationToken.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        s = ApplicationTokenWriteSerializer(data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        update = []
        for f in ("name", "description", "scopes", "expires_at", "is_active"):
            if f in d:
                setattr(t, f, d[f])
                update.append(f)
        if update:
            t.save(update_fields=update + ["updated_at"])
        return Response(ApplicationTokenSerializer(t).data)

    def destroy(self, request, pk=None):
        try:
            t = self._qs(request).get(pk=pk)
        except ApplicationToken.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        t.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def regenerate(self, request, pk=None):
        try:
            t = self._qs(request).get(pk=pk)
        except ApplicationToken.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        full, prefix, h = _generate_app_token()
        t.token_hash = h
        t.prefix = prefix
        t.is_active = True
        t.save(update_fields=["token_hash", "prefix", "is_active", "updated_at"])
        out = ApplicationTokenSerializer(t).data
        out["token"] = full
        return Response(out)


# ── Connectors / Integrations (Cluster 2) ────────────────────────────


class ConnectorCatalogueView(ViewSet):
    """List the system-wide Connector catalogue, annotated with each
    org's installation state."""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "iam.integrations"
    rbac_action = "view"

    def _get_org(self, request):
        profile = getattr(request.user, "profile", None)
        return profile.organization if profile else None

    def list(self, request):
        org = self._get_org(request)
        connectors = Connector.objects.filter(is_available=True).order_by("category", "name")
        installations = {}
        if org:
            for inst in ConnectorInstallation.objects.filter(organization=org):
                installations[inst.connector_id] = inst
        ser = ConnectorSerializer(
            connectors,
            many=True,
            context={"installations_by_connector": installations},
        )
        # Group by category for the UI
        by_category = {}
        for row in ser.data:
            by_category.setdefault(row["category"], []).append(row)
        return Response({
            "count": connectors.count(),
            "by_category": by_category,
            "categories": [
                {"value": v, "label": l} for v, l in Connector.Category.choices
            ],
        })


class ConnectorInstallationViewSet(ViewSet):
    """Per-org install / configure / enable for a Connector."""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "iam.integrations"
    rbac_action_map = {
        "list": "view", "retrieve": "view", "create": "create",
        "partial_update": "edit", "destroy": "delete",
    }

    def _get_org(self, request):
        profile = getattr(request.user, "profile", None)
        return profile.organization if profile else None

    def _qs(self, request):
        org = self._get_org(request)
        if not org:
            return ConnectorInstallation.objects.none()
        return ConnectorInstallation.objects.filter(organization=org).select_related("connector")

    def _serialize(self, inst):
        from .iam_serializers import _mask_secrets
        return {
            "id": inst.id,
            "connector": {
                "id": inst.connector.id,
                "slug": inst.connector.slug,
                "name": inst.connector.name,
                "vendor": inst.connector.vendor,
                "category": inst.connector.category,
            },
            "is_enabled": inst.is_enabled,
            "config": inst.config,
            "secrets": _mask_secrets(inst.secrets or {}),
            "last_synced_at": inst.last_synced_at.isoformat() if inst.last_synced_at else None,
            "created_at": inst.created_at.isoformat(),
            "updated_at": inst.updated_at.isoformat(),
        }

    def list(self, request):
        qs = self._qs(request)
        return Response({
            "count": qs.count(),
            "results": [self._serialize(i) for i in qs],
        })

    def create(self, request):
        org = self._get_org(request)
        if not org:
            return Response({"detail": "No org context."}, status=status.HTTP_400_BAD_REQUEST)
        s = ConnectorInstallationWriteSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        if "connector_id" not in d:
            return Response({"detail": "connector_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            connector = Connector.objects.get(pk=d["connector_id"], is_available=True)
        except Connector.DoesNotExist:
            return Response({"detail": "Connector not in catalogue."}, status=status.HTTP_400_BAD_REQUEST)
        inst, created = ConnectorInstallation.objects.get_or_create(
            organization=org, connector=connector,
            defaults={
                "is_enabled": d.get("is_enabled", False),
                "config": d.get("config", {}) or {},
                "secrets": d.get("secrets", {}) or {},
                "created_by": request.user,
            },
        )
        if not created:
            # Already installed — treat as PATCH
            return self._update_install(inst, d)
        return Response(self._serialize(inst), status=status.HTTP_201_CREATED)

    def _update_install(self, inst, d):
        update = []
        if "is_enabled" in d:
            inst.is_enabled = d["is_enabled"]
            update.append("is_enabled")
        if "config" in d:
            inst.config = {**(inst.config or {}), **(d["config"] or {})}
            update.append("config")
        if "secrets" in d:
            from .iam_serializers import SECRET_MASK
            existing = inst.secrets or {}
            incoming = d["secrets"] or {}
            merged = dict(existing)
            for k, v in incoming.items():
                if v == SECRET_MASK:
                    continue
                if v == "" or v is None:
                    merged.pop(k, None)
                    continue
                merged[k] = v
            inst.secrets = merged
            update.append("secrets")
        if update:
            inst.save(update_fields=update + ["updated_at"])
        return Response(self._serialize(inst))

    def partial_update(self, request, pk=None):
        try:
            inst = self._qs(request).get(pk=pk)
        except ConnectorInstallation.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        s = ConnectorInstallationWriteSerializer(data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        return self._update_install(inst, s.validated_data)

    def destroy(self, request, pk=None):
        try:
            inst = self._qs(request).get(pk=pk)
        except ConnectorInstallation.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        inst.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Data-access scope (Cluster 3.4) ──────────────────────────────────


class DataScopeListView(ViewSet):
    """Read-only catalogue of available DataScope keys (system-seeded)."""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "iam.roles"
    rbac_action = "view"

    def list(self, request):
        from apps.settings.models import DataScope
        qs = DataScope.objects.all().order_by("key")
        return Response({
            "count": qs.count(),
            "results": DataScopeSerializer(qs, many=True).data,
        })


class RoleScopeViewSet(ViewSet):
    """CRUD over RoleScope assignments. Org-scoped via the role FK."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "iam.roles"
    rbac_action_map = {
        "list": "view", "retrieve": "view", "create": "create",
        "destroy": "delete",
    }

    def _get_org(self, request):
        profile = getattr(request.user, "profile", None)
        return profile.organization if profile else None

    def _qs(self, request):
        from apps.settings.models import RoleScope
        org = self._get_org(request)
        if not org:
            return RoleScope.objects.none()
        return RoleScope.objects.filter(role__organization=org).select_related("role", "data_scope")

    def list(self, request):
        qs = self._qs(request)
        role_id = request.query_params.get("role_id")
        if role_id:
            qs = qs.filter(role_id=role_id)
        qs = qs.order_by("role_id", "module", "sub_module")
        return Response({
            "count": qs.count(),
            "results": RoleScopeSerializer(qs, many=True).data,
        })

    def create(self, request):
        from apps.settings.models import DataScope, Role, RoleScope
        org = self._get_org(request)
        if not org:
            return Response({"detail": "No org context."}, status=status.HTTP_400_BAD_REQUEST)
        s = RoleScopeWriteSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        try:
            role = Role.objects.get(pk=d["role_id"], organization=org)
        except Role.DoesNotExist:
            return Response({"role_id": "Role not in your organization."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            data_scope = DataScope.objects.get(pk=d["data_scope_id"])
        except DataScope.DoesNotExist:
            return Response({"data_scope_id": "Unknown data scope."}, status=status.HTTP_400_BAD_REQUEST)

        rs, created = RoleScope.objects.get_or_create(
            role=role,
            data_scope=data_scope,
            module=d.get("module", "") or "",
            sub_module=d.get("sub_module", "") or "",
        )
        return Response(
            RoleScopeSerializer(rs).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def destroy(self, request, pk=None):
        from apps.settings.models import RoleScope
        try:
            rs = self._qs(request).get(pk=pk)
        except RoleScope.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        rs.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
