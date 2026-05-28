from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.accounts.models import AccessRequest, AccessReviewCampaign, AccessReviewItem, ApplicationToken, Connector, ConnectorInstallation, IdentityProvider, Invitation, ServiceAccount, UserGroup, UserProfile, Webhook, WebhookDelivery
from apps.settings.models import Role

User = get_user_model()


class UserDirectorySerializer(serializers.Serializer):
    id = serializers.IntegerField(source="user.id")
    profile_id = serializers.IntegerField(source="id")
    full_name = serializers.SerializerMethodField()
    email = serializers.EmailField(source="user.email")
    phone = serializers.CharField()
    job_title = serializers.CharField()
    department_name = serializers.SerializerMethodField()
    role_name = serializers.SerializerMethodField()
    user_status = serializers.CharField()
    user_status_display = serializers.CharField(source="get_user_status_display")
    last_login = serializers.DateTimeField(source="user.last_login")
    mfa_enabled = serializers.BooleanField()
    identity_type = serializers.CharField()
    identity_type_display = serializers.CharField(source="get_identity_type_display")
    partner_type = serializers.CharField()
    partner_type_display = serializers.SerializerMethodField()
    profile_photo = serializers.ImageField()
    date_joined = serializers.DateTimeField(source="user.date_joined")

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    def get_department_name(self, obj):
        return obj.department.name if obj.department else ""

    def get_role_name(self, obj):
        return obj.assigned_role.name if obj.assigned_role else obj.get_role_display()

    def get_partner_type_display(self, obj):
        return obj.get_partner_type_display() if obj.partner_type else ""


class UserDetailSerializer(serializers.Serializer):
    id = serializers.IntegerField(source="user.id")
    first_name = serializers.CharField(source="user.first_name")
    last_name = serializers.CharField(source="user.last_name")
    full_name = serializers.SerializerMethodField()
    email = serializers.EmailField(source="user.email")
    phone = serializers.CharField()
    job_title = serializers.CharField()
    department_id = serializers.IntegerField(source="department.id", default=None)
    department_name = serializers.SerializerMethodField()
    role_name = serializers.SerializerMethodField()
    assigned_role_id = serializers.IntegerField(source="assigned_role.id", default=None)
    reporting_manager_id = serializers.IntegerField(source="reporting_manager.id", default=None)
    reporting_manager_name = serializers.SerializerMethodField()
    user_status = serializers.CharField()
    user_status_display = serializers.CharField(source="get_user_status_display")
    last_login = serializers.DateTimeField(source="user.last_login")
    date_joined = serializers.DateTimeField(source="user.date_joined")
    mfa_enabled = serializers.BooleanField()
    identity_type = serializers.CharField()
    identity_type_display = serializers.CharField(source="get_identity_type_display")
    partner_type = serializers.CharField()
    partner_type_display = serializers.SerializerMethodField()
    profile_photo = serializers.ImageField()
    authentication_methods = serializers.SerializerMethodField()
    has_completed_onboarding = serializers.BooleanField()

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    def get_department_name(self, obj):
        return obj.department.name if obj.department else ""

    def get_role_name(self, obj):
        return obj.assigned_role.name if obj.assigned_role else obj.get_role_display()

    def get_reporting_manager_name(self, obj):
        if obj.reporting_manager:
            return obj.reporting_manager.get_full_name() or obj.reporting_manager.username
        return ""

    def get_authentication_methods(self, obj):
        providers = list(
            obj.user.oauth_connections.values_list("provider", flat=True)
        )
        methods = ["password"]
        methods.extend(providers)
        return methods

    def get_partner_type_display(self, obj):
        return obj.get_partner_type_display() if obj.partner_type else ""


class UserUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)
    phone = serializers.CharField(required=False, allow_blank=True)
    job_title = serializers.CharField(required=False, allow_blank=True)
    department_id = serializers.IntegerField(required=False, allow_null=True)
    assigned_role_id = serializers.IntegerField(required=False, allow_null=True)
    reporting_manager_id = serializers.IntegerField(required=False, allow_null=True)
    user_status = serializers.ChoiceField(
        required=False,
        choices=["active", "suspended", "locked", "pending"],
    )
    identity_type = serializers.ChoiceField(
        required=False,
        choices=["user", "employee", "partner", "system_account"],
    )
    partner_type = serializers.ChoiceField(
        required=False,
        choices=["contractor", "vendor", "client", "investor", ""],
        allow_blank=True,
    )

    def validate_assigned_role_id(self, value):
        if value is None:
            return value
        org = self.context.get("organization")
        if not org:
            raise serializers.ValidationError("Missing organization context.")
        if not Role.objects.filter(id=value, organization=org).exists():
            raise serializers.ValidationError("Role not found in your organization.")
        return value


class UserInviteSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    role_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    department_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    job_title = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")

    def validate_email(self, value):
        value = value.lower().strip()
        org = self.context.get("organization")
        if User.objects.filter(email=value, profile__organization=org).exists():
            raise serializers.ValidationError("A user with this email already exists in your organization.")
        if org and Invitation.objects.filter(email=value, organization=org, status="pending").exists():
            raise serializers.ValidationError("A pending invitation already exists for this email.")
        return value

    def validate_role_id(self, value):
        if value is None:
            return value
        org = self.context.get("organization")
        if not org:
            raise serializers.ValidationError("Missing organization context.")
        if not Role.objects.filter(id=value, organization=org).exists():
            raise serializers.ValidationError("Role not found in your organization.")
        return value


class InvitationListSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()
    status = serializers.CharField()
    status_display = serializers.CharField(source="get_status_display")
    invited_by_name = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField()
    token = serializers.UUIDField()

    def get_invited_by_name(self, obj):
        return obj.invited_by.get_full_name() or obj.invited_by.username


# ── Service Accounts ──────────────────────────────────


class ServiceAccountListSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    description = serializers.CharField()
    owner_name = serializers.SerializerMethodField()
    owner_id = serializers.IntegerField(source="owner.id", default=None)
    status = serializers.CharField()
    status_display = serializers.CharField(source="get_status_display")
    key_count = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()

    def get_owner_name(self, obj):
        if obj.owner:
            return obj.owner.get_full_name() or obj.owner.username
        return ""

    def get_key_count(self, obj):
        return obj.api_keys.filter(is_active=True).count()


class ServiceAccountDetailSerializer(ServiceAccountListSerializer):
    api_keys = serializers.SerializerMethodField()

    def get_api_keys(self, obj):
        keys = obj.api_keys.order_by("-created_at")
        return [
            {
                "id": k.id,
                "label": k.label,
                "prefix": k.prefix,
                "scopes": k.scopes,
                "is_active": k.is_active,
                "expires_at": k.expires_at,
                "last_used_at": k.last_used_at,
                "created_at": k.created_at,
            }
            for k in keys
        ]


class ServiceAccountCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_name(self, value):
        org = self.context.get("organization")
        if org and ServiceAccount.objects.filter(organization=org, name=value).exists():
            raise serializers.ValidationError("A service account with this name already exists.")
        return value


class ServiceAccountUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(
        required=False,
        choices=["active", "suspended", "revoked"],
    )


class APIKeyDirectorySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    prefix = serializers.CharField()
    label = serializers.CharField()
    service_account_id = serializers.IntegerField(source="service_account.id")
    service_account_name = serializers.CharField(source="service_account.name")
    scopes = serializers.ListField(child=serializers.CharField())
    is_active = serializers.BooleanField()
    status_display = serializers.SerializerMethodField()
    expires_at = serializers.DateTimeField()
    last_used_at = serializers.DateTimeField()
    created_at = serializers.DateTimeField()

    def get_status_display(self, obj):
        if not obj.is_active:
            return "Revoked"
        from django.utils import timezone
        if obj.expires_at and obj.expires_at < timezone.now():
            return "Expired"
        return "Active"


class APIKeyCreateSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    scopes = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
    )
    expires_at = serializers.DateTimeField(required=False, allow_null=True, default=None)


# ── User Groups ──────────────────────────────────────────────────────


class UserGroupListSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField()
    description = serializers.CharField(allow_blank=True, required=False)
    member_count = serializers.IntegerField(read_only=True)
    is_system = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class UserGroupDetailSerializer(UserGroupListSerializer):
    members = serializers.SerializerMethodField()

    def get_members(self, obj):
        profiles = (
            UserProfile.objects
            .filter(user__in=obj.members.all(), organization_id=obj.organization_id)
            .select_related("user")
            .order_by("user__first_name", "user__last_name")
        )
        return [
            {
                "id": p.user_id,
                "name": p.user.get_full_name() or p.user.username,
                "email": p.user.email,
                "job_title": p.job_title,
                "user_status": p.user_status,
            }
            for p in profiles
        ]


class UserGroupWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    description = serializers.CharField(allow_blank=True, required=False, default="")
    member_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        default=list,
    )


# ── Linked Employees ─────────────────────────────────────────────────


class UserLinkedEmployeeSerializer(serializers.Serializer):
    """User profile + the linked HR EmployeeRecord if any."""

    user_id = serializers.IntegerField()
    full_name = serializers.SerializerMethodField()
    email = serializers.EmailField(source="user.email")
    job_title = serializers.CharField()
    department_name = serializers.SerializerMethodField()
    user_status = serializers.CharField()
    has_employee_record = serializers.SerializerMethodField()
    employee_id = serializers.SerializerMethodField()
    employee_code = serializers.SerializerMethodField()
    employee_hire_date = serializers.SerializerMethodField()

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    def get_department_name(self, obj):
        return obj.department.name if obj.department else ""

    def _employee(self, obj):
        return getattr(obj.user, "employee_record", None)

    def get_has_employee_record(self, obj):
        return self._employee(obj) is not None

    def get_employee_id(self, obj):
        emp = self._employee(obj)
        return emp.id if emp else None

    def get_employee_code(self, obj):
        emp = self._employee(obj)
        return getattr(emp, "employee_code", "") if emp else ""

    def get_employee_hire_date(self, obj):
        emp = self._employee(obj)
        return emp.hire_date.isoformat() if emp and emp.hire_date else None


# ── Access Requests ──────────────────────────────────────────────────


class AccessRequestListSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    kind = serializers.CharField()
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)
    status = serializers.CharField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    requester_id = serializers.IntegerField(source="requester.id", read_only=True)
    requester_name = serializers.SerializerMethodField()
    requester_email = serializers.EmailField(source="requester.email", read_only=True)

    approver_id = serializers.IntegerField(source="approver.id", read_only=True, allow_null=True)
    approver_name = serializers.SerializerMethodField()

    requested_role_id = serializers.IntegerField(source="requested_role.id", read_only=True, allow_null=True)
    requested_role_name = serializers.SerializerMethodField()
    requested_resource = serializers.CharField()

    reason = serializers.CharField()
    requested_valid_until = serializers.DateTimeField(allow_null=True)
    granted_valid_until = serializers.DateTimeField(allow_null=True)
    request_expires_at = serializers.DateTimeField(allow_null=True)
    approval_decision_at = serializers.DateTimeField(allow_null=True, read_only=True)
    approval_notes = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    def get_requester_name(self, obj):
        return obj.requester.get_full_name() or obj.requester.username

    def get_approver_name(self, obj):
        if not obj.approver:
            return ""
        return obj.approver.get_full_name() or obj.approver.username

    def get_requested_role_name(self, obj):
        return obj.requested_role.name if obj.requested_role else ""


class AccessRequestCreateSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=AccessRequest.Kind.choices)
    requested_role_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    requested_resource = serializers.CharField(required=False, allow_blank=True, default="")
    reason = serializers.CharField(min_length=4, max_length=4000)
    requested_valid_until = serializers.DateTimeField(required=False, allow_null=True)
    request_expires_at = serializers.DateTimeField(required=False, allow_null=True)
    approver_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)

    def validate(self, data):
        kind = data["kind"]
        if kind in (AccessRequest.Kind.ROLE_GRANT, AccessRequest.Kind.ROLE_ELEVATION):
            if not data.get("requested_role_id"):
                raise serializers.ValidationError({
                    "requested_role_id": "Required for role_grant and role_elevation requests."
                })
        if kind == AccessRequest.Kind.RESOURCE_ACCESS:
            if not (data.get("requested_resource") or "").strip():
                raise serializers.ValidationError({
                    "requested_resource": "Required for resource_access requests."
                })
        if kind == AccessRequest.Kind.ROLE_ELEVATION:
            if not data.get("requested_valid_until"):
                raise serializers.ValidationError({
                    "requested_valid_until": "Elevation must specify when access expires."
                })
        return data


class AccessRequestDecisionSerializer(serializers.Serializer):
    """Used by approve / reject / revoke actions."""
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    granted_valid_until = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text=(
            "Approve actions may override the requested validity window. "
            "Null = permanent grant (only valid for role_grant). For "
            "role_elevation, this is required and must be in the future."
        ),
    )


# ── Password policy + Login methods ──────────────────────────────────


class PasswordPolicySerializer(serializers.Serializer):
    password_min_length = serializers.IntegerField(min_value=8, max_value=128)
    password_require_uppercase = serializers.BooleanField()
    password_require_digits = serializers.BooleanField()
    password_require_special = serializers.BooleanField()
    password_max_age_days = serializers.IntegerField(min_value=0, max_value=3650)
    password_history_count = serializers.IntegerField(min_value=0, max_value=50)


class LoginMethodsSerializer(serializers.Serializer):
    allow_password_login = serializers.BooleanField()
    allow_oauth_login = serializers.BooleanField()
    allow_passkey_login = serializers.BooleanField()
    allow_sso_login = serializers.BooleanField()


# ── Active sessions ──────────────────────────────────────────────────


class UserAuthSessionSerializer(serializers.Serializer):
    sid = serializers.UUIDField(read_only=True)
    auth_provider = serializers.CharField()
    auth_provider_display = serializers.CharField(source="get_auth_provider_display", read_only=True)
    ip_address = serializers.IPAddressField(allow_null=True)
    user_agent = serializers.CharField()
    device_label = serializers.CharField()
    created_at = serializers.DateTimeField()
    last_seen_at = serializers.DateTimeField()
    revoked_at = serializers.DateTimeField(allow_null=True)
    revoke_reason = serializers.CharField()
    is_current = serializers.BooleanField()


# ── Audit events ─────────────────────────────────────────────────────


class AuditEventSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    event_type = serializers.CharField()
    event_type_display = serializers.CharField(source="get_event_type_display", read_only=True)
    status = serializers.CharField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    severity = serializers.CharField()
    severity_display = serializers.CharField(source="get_severity_display", read_only=True)
    actor_id = serializers.IntegerField(source="user.id", read_only=True, allow_null=True)
    actor_email = serializers.SerializerMethodField()
    actor_name = serializers.SerializerMethodField()
    principal = serializers.CharField()
    provider = serializers.CharField()
    ip_address = serializers.IPAddressField(allow_null=True)
    user_agent = serializers.CharField()
    device_label = serializers.CharField()
    target_type = serializers.CharField()
    target_id = serializers.CharField()
    detail = serializers.CharField()
    metadata = serializers.JSONField()
    occurred_at = serializers.DateTimeField()

    def get_actor_email(self, obj):
        return obj.user.email if obj.user_id else (obj.principal or "")

    def get_actor_name(self, obj):
        if obj.user_id and obj.user:
            return obj.user.get_full_name() or obj.user.email
        return obj.principal or "System"


# ── Compliance: Access Review Campaigns ──────────────────────────────


class AccessReviewCampaignListSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField()
    description = serializers.CharField(allow_blank=True, required=False)
    kind = serializers.CharField()
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)
    status = serializers.CharField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    target_role_id = serializers.IntegerField(allow_null=True, required=False)
    target_role_name = serializers.SerializerMethodField()
    starts_at = serializers.DateTimeField(allow_null=True, required=False)
    ends_at = serializers.DateTimeField(allow_null=True, required=False)
    completed_at = serializers.DateTimeField(allow_null=True, required=False)
    created_by_name = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(read_only=True)
    item_count = serializers.IntegerField(read_only=True)
    pending_count = serializers.IntegerField(read_only=True)
    approved_count = serializers.IntegerField(read_only=True)
    revoked_count = serializers.IntegerField(read_only=True)

    def get_target_role_name(self, obj):
        return obj.target_role.name if obj.target_role else ""

    def get_created_by_name(self, obj):
        if not obj.created_by_id:
            return ""
        return obj.created_by.get_full_name() or obj.created_by.email


class AccessReviewCampaignWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(allow_blank=True, required=False, default="")
    kind = serializers.ChoiceField(choices=AccessReviewCampaign.Kind.choices)
    target_role_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    starts_at = serializers.DateTimeField(required=False, allow_null=True)
    ends_at = serializers.DateTimeField(required=False, allow_null=True)


class AccessReviewItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    user_name = serializers.SerializerMethodField()
    user_email = serializers.EmailField(source="user.email", read_only=True)
    role_id = serializers.IntegerField(source="role_at_review.id", read_only=True, allow_null=True)
    role_name = serializers.SerializerMethodField()
    decision = serializers.CharField()
    decision_display = serializers.CharField(source="get_decision_display", read_only=True)
    decided_by_name = serializers.SerializerMethodField()
    decided_at = serializers.DateTimeField(allow_null=True, read_only=True)
    notes = serializers.CharField(allow_blank=True, required=False)
    last_login = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(read_only=True)

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.email

    def get_role_name(self, obj):
        return obj.role_at_review.name if obj.role_at_review else ""

    def get_decided_by_name(self, obj):
        if not obj.decided_by_id:
            return ""
        return obj.decided_by.get_full_name() or obj.decided_by.email

    def get_last_login(self, obj):
        return obj.user.last_login.isoformat() if obj.user.last_login else None


class AccessReviewItemDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=AccessReviewItem.Decision.choices)
    notes = serializers.CharField(required=False, allow_blank=True, default="")


# ── Identity Providers (federation config) ───────────────────────────


SECRET_MASK = "********"


def _mask_secrets(secrets: dict) -> dict:
    """Replace each secret value with the mask sentinel; preserves keys
    so admins can see *which* secrets are populated without reading
    the values back."""
    if not isinstance(secrets, dict):
        return {}
    return {k: SECRET_MASK if v else "" for k, v in secrets.items()}


class IdentityProviderSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    kind = serializers.CharField()
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)
    name = serializers.CharField()
    is_enabled = serializers.BooleanField()
    config = serializers.JSONField()
    secrets = serializers.SerializerMethodField()
    last_synced_at = serializers.DateTimeField(allow_null=True, read_only=True)
    last_sync_status = serializers.CharField(read_only=True)
    last_sync_status_display = serializers.CharField(source="get_last_sync_status_display", read_only=True)
    last_sync_message = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    def get_secrets(self, obj):
        return _mask_secrets(obj.secrets or {})


class IdentityProviderWriteSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=IdentityProvider.Kind.choices, required=False)
    name = serializers.CharField(max_length=120, required=False)
    is_enabled = serializers.BooleanField(required=False)
    config = serializers.JSONField(required=False)
    secrets = serializers.JSONField(required=False)


# ── Access Policies (Cluster 4) ──────────────────────────────────────


class _PolicyConditionSerializer(serializers.Serializer):
    condition_type = serializers.CharField()
    operator = serializers.CharField(required=False, default="eq")
    value = serializers.JSONField(required=False, default=dict)
    sort_order = serializers.IntegerField(required=False, default=0)
    is_active = serializers.BooleanField(required=False, default=True)


class _PolicyActionSerializer(serializers.Serializer):
    action_type = serializers.CharField()
    parameters = serializers.JSONField(required=False, default=dict)
    message = serializers.CharField(required=False, allow_blank=True, default="")
    sort_order = serializers.IntegerField(required=False, default=0)
    is_active = serializers.BooleanField(required=False, default=True)


class AccessPolicyListSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    key = serializers.CharField()
    kind = serializers.CharField()
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)
    name = serializers.CharField()
    description = serializers.CharField(allow_blank=True, required=False)
    priority = serializers.IntegerField()
    is_active = serializers.BooleanField()
    condition_count = serializers.IntegerField(read_only=True)
    action_summary = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    def get_action_summary(self, obj):
        actions = list(obj.policy_actions.all())
        if not actions:
            return ""
        primary = actions[0]
        more = f" +{len(actions) - 1}" if len(actions) > 1 else ""
        return f"{primary.get_action_type_display()}{more}"


class AccessPolicyDetailSerializer(AccessPolicyListSerializer):
    conditions = serializers.SerializerMethodField()
    actions = serializers.SerializerMethodField()
    module = serializers.CharField(allow_blank=True, required=False)
    sub_module = serializers.CharField(allow_blank=True, required=False)
    action = serializers.CharField(allow_blank=True, required=False)

    def get_conditions(self, obj):
        return [
            {
                "id": c.id,
                "condition_type": c.condition_type,
                "operator": c.operator,
                "value": c.value,
                "sort_order": c.sort_order,
                "is_active": c.is_active,
            }
            for c in obj.conditions.all().order_by("sort_order", "id")
        ]

    def get_actions(self, obj):
        return [
            {
                "id": a.id,
                "action_type": a.action_type,
                "parameters": a.parameters,
                "message": a.message,
                "sort_order": a.sort_order,
                "is_active": a.is_active,
            }
            for a in obj.policy_actions.all().order_by("sort_order", "id")
        ]


class AccessPolicyWriteSerializer(serializers.Serializer):
    """Used for both create and partial update.

    Conditions and actions arrays REPLACE existing children when
    provided — partial updates that omit them leave children untouched.
    """
    key = serializers.SlugField(max_length=120, required=False)
    kind = serializers.ChoiceField(required=False, choices=[
        # Imported lazily to avoid circular at module load
    ])
    name = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    priority = serializers.IntegerField(required=False, min_value=0, max_value=10000)
    is_active = serializers.BooleanField(required=False)
    module = serializers.CharField(required=False, allow_blank=True)
    sub_module = serializers.CharField(required=False, allow_blank=True)
    action = serializers.CharField(required=False, allow_blank=True)
    conditions = _PolicyConditionSerializer(many=True, required=False)
    actions = _PolicyActionSerializer(many=True, required=False)

    def __init__(self, *args, **kwargs):
        # Late-bind the kind choices to AccessPolicy.Kind without circular imports
        super().__init__(*args, **kwargs)
        from apps.settings.models import AccessPolicy
        self.fields["kind"].choices = AccessPolicy.Kind.choices


# ── Webhooks (Cluster 2) ─────────────────────────────────────────────


class WebhookSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField()
    url = serializers.URLField()
    events = serializers.ListField(child=serializers.CharField(), required=False)
    is_active = serializers.BooleanField()
    secret_set = serializers.SerializerMethodField()
    last_delivery_at = serializers.DateTimeField(read_only=True, allow_null=True)
    last_delivery_status = serializers.CharField(read_only=True)
    last_delivery_message = serializers.CharField(read_only=True)
    delivery_count = serializers.IntegerField(read_only=True)
    failure_count = serializers.IntegerField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    def get_secret_set(self, obj):
        return bool(obj.secret)


class WebhookWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=160, required=False)
    url = serializers.URLField(required=False)
    events = serializers.ListField(child=serializers.CharField(), required=False)
    is_active = serializers.BooleanField(required=False)
    rotate_secret = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Set to True to generate a new HMAC secret on save.",
    )


class WebhookDeliverySerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    event_name = serializers.CharField()
    status = serializers.CharField()
    response_code = serializers.IntegerField(allow_null=True)
    response_body = serializers.CharField()
    attempt_number = serializers.IntegerField()
    error_message = serializers.CharField()
    created_at = serializers.DateTimeField()
    delivered_at = serializers.DateTimeField(allow_null=True)


# ── Application Tokens (Cluster 2) ───────────────────────────────────


class ApplicationTokenSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField()
    description = serializers.CharField(allow_blank=True, required=False)
    prefix = serializers.CharField(read_only=True)
    scopes = serializers.ListField(child=serializers.CharField(), required=False)
    expires_at = serializers.DateTimeField(allow_null=True, required=False)
    last_used_at = serializers.DateTimeField(read_only=True, allow_null=True)
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField(read_only=True)


class ApplicationTokenWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=160, required=False)
    description = serializers.CharField(allow_blank=True, required=False)
    scopes = serializers.ListField(child=serializers.CharField(), required=False)
    expires_at = serializers.DateTimeField(allow_null=True, required=False)
    is_active = serializers.BooleanField(required=False)


# ── Connectors / Integrations (Cluster 2) ────────────────────────────


class ConnectorSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    slug = serializers.CharField()
    name = serializers.CharField()
    vendor = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    category = serializers.CharField()
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    icon_url = serializers.CharField(allow_blank=True)
    docs_url = serializers.CharField(allow_blank=True)
    is_available = serializers.BooleanField()
    installation = serializers.SerializerMethodField()

    def get_installation(self, obj):
        installations = self.context.get("installations_by_connector", {})
        inst = installations.get(obj.id)
        if not inst:
            return None
        return {
            "id": inst.id,
            "is_enabled": inst.is_enabled,
            "last_synced_at": inst.last_synced_at.isoformat() if inst.last_synced_at else None,
            "config": inst.config,
        }


class ConnectorInstallationWriteSerializer(serializers.Serializer):
    connector_id = serializers.IntegerField(min_value=1, required=False)
    is_enabled = serializers.BooleanField(required=False)
    config = serializers.JSONField(required=False)
    secrets = serializers.JSONField(required=False)


# ── Data-access scope (Cluster 3.4) ──────────────────────────────────


class DataScopeSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    key = serializers.CharField()
    label = serializers.CharField()
    description = serializers.CharField()


class RoleScopeSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    role_id = serializers.IntegerField(source="role.id", read_only=True)
    role_name = serializers.CharField(source="role.name", read_only=True)
    data_scope_id = serializers.IntegerField(source="data_scope.id")
    data_scope_key = serializers.CharField(source="data_scope.key", read_only=True)
    data_scope_label = serializers.CharField(source="data_scope.label", read_only=True)
    module = serializers.CharField(allow_blank=True, required=False)
    sub_module = serializers.CharField(allow_blank=True, required=False)
    created_at = serializers.DateTimeField(read_only=True)


class RoleScopeWriteSerializer(serializers.Serializer):
    role_id = serializers.IntegerField(min_value=1)
    data_scope_id = serializers.IntegerField(min_value=1)
    module = serializers.CharField(allow_blank=True, required=False, default="")
    sub_module = serializers.CharField(allow_blank=True, required=False, default="")
