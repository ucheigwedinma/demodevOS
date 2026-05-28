import hashlib
import secrets
import uuid
from datetime import time as dt_time

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


def user_profile_photo_upload_to(instance, filename):
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
    return f"user-profiles/{instance.user_id}/{uuid.uuid4()}.{extension}"


def org_logo_upload_to(instance, filename):
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "png"
    return f"org-logos/{instance.pk}/{uuid.uuid4()}.{extension}"


WORKSPACE_DASHBOARD_WIDGET_KEYS = [
    "alerts",
    "portfolio_kpis",
    "operational_signals",
    "team_workload",
    "valuation_trend",
    "project_status",
    "active_projects",
    "cash_flow_activity",
]


def default_workspace_widget_order():
    return list(WORKSPACE_DASHBOARD_WIDGET_KEYS)


def default_workspace_widget_visibility():
    return {key: True for key in WORKSPACE_DASHBOARD_WIDGET_KEYS}


def default_calendar_working_days():
    return [1, 2, 3, 4, 5]


def default_data_report_filters():
    return {}


def default_data_column_visibility():
    return {}


def default_data_saved_views():
    return []


class Organization(models.Model):
    SIZE_CHOICES = [
        ("1-10", "1-10"),
        ("11-50", "11-50"),
        ("51-200", "51-200"),
        ("201-500", "201-500"),
        ("500+", "500+"),
    ]

    class SubscriptionTier(models.TextChoices):
        ESSENTIALS = "essentials", "Essentials"
        GROWTH = "growth", "Growth"
        SCALE = "scale", "Scale"
        CUSTOM = "custom", "Custom"

    class MFAEnforcement(models.TextChoices):
        DISABLED = "disabled", "Disabled"
        OPTIONAL = "optional", "Optional"
        REQUIRED_ADMINS = "required_admins", "Required for Admins"
        REQUIRED_ALL = "required_all", "Required for All Users"

    # --- Core ---
    name = models.CharField(max_length=200, unique=True)
    legal_name = models.CharField(max_length=300, blank=True)
    trading_name = models.CharField(max_length=300, blank=True)
    industry = models.CharField(max_length=100, blank=True)
    size = models.CharField(max_length=10, blank=True, choices=SIZE_CHOICES)
    description = models.TextField(blank=True)

    # --- Legal & Tax ---
    registration_number = models.CharField(max_length=100, blank=True)
    tax_id = models.CharField(max_length=100, blank=True)
    fiscal_year_start_month = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(12)],
    )

    # --- Contact ---
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    website = models.URLField(blank=True)

    # --- Address ---
    address_line_1 = models.CharField(max_length=255, blank=True)
    address_line_2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state_province = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True)

    # --- Subscription ---
    subscription_tier = models.CharField(
        max_length=20,
        choices=SubscriptionTier.choices,
        default=SubscriptionTier.SCALE,
    )

    # --- Security ---
    mfa_enforcement = models.CharField(
        max_length=20,
        choices=MFAEnforcement.choices,
        default=MFAEnforcement.REQUIRED_ALL,
    )

    # --- Password policy (consumed by registration / password-change flows) ---
    password_min_length = models.PositiveSmallIntegerField(default=12)
    password_require_uppercase = models.BooleanField(default=True)
    password_require_digits = models.BooleanField(default=True)
    password_require_special = models.BooleanField(default=False)
    password_max_age_days = models.PositiveSmallIntegerField(
        default=0,
        help_text="0 = passwords never expire. >0 = users must rotate every N days.",
    )
    password_history_count = models.PositiveSmallIntegerField(
        default=0,
        help_text="0 = no history check. >0 = block reuse of the last N passwords.",
    )

    # --- Login methods (per-org enable flags consumed by the login flow) ---
    allow_password_login = models.BooleanField(default=True)
    allow_oauth_login = models.BooleanField(default=True)
    allow_passkey_login = models.BooleanField(default=True)
    allow_sso_login = models.BooleanField(
        default=False,
        help_text="Enable SAML/OIDC SSO. Requires per-org IdP config (see iam/federation).",
    )

    # --- Platform ---
    is_platform_org = models.BooleanField(
        default=False,
        help_text="The house organization that owns the platform. Only one should be True.",
    )

    # --- Branding ---
    logo = models.ImageField(upload_to=org_logo_upload_to, blank=True, null=True)
    founded_date = models.DateField(null=True, blank=True)

    # --- Duplicate detection ---
    normalized_name = models.CharField(
        max_length=200, blank=True, db_index=True, editable=False
    )
    email_domain = models.CharField(max_length=255, blank=True, db_index=True)

    # --- Metadata ---
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_organizations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @classmethod
    def get_platform_org(cls):
        """Return the house/platform organization. Creates it if missing."""
        org = cls.objects.filter(is_platform_org=True).first()
        if org:
            return org
        # Fallback: look by legacy name
        org = cls.objects.filter(name="developerOS").first()
        if org:
            org.is_platform_org = True
            org.save(update_fields=["is_platform_org"])
            return org
        return None


class PlatformRole(models.Model):
    """
    Platform-level role for console access.
    Unlike tenant roles (settings.Role), these govern platform-wide
    operations: tenant management, telemetry, billing, deployments.
    """

    class Tier(models.TextChoices):
        OWNER = "owner", "Platform Owner"
        ADMIN = "admin", "Platform Admin"
        SUPPORT = "support", "Support Agent"
        BILLING = "billing", "Billing Manager"
        DEVOPS = "devops", "DevOps / Infrastructure"
        VIEWER = "viewer", "Read-Only Viewer"

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    tier = models.CharField(max_length=20, choices=Tier.choices, default=Tier.VIEWER)
    description = models.TextField(blank=True)
    is_system = models.BooleanField(default=False, help_text="System roles cannot be deleted")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def permission_slugs(self):
        return set(self.platform_permissions.values_list("slug", flat=True))


class PlatformPermission(models.Model):
    """
    Granular permission for platform console features.
    Linked to PlatformRole via M2M through PlatformRolePermission.
    """

    class Module(models.TextChoices):
        IAM = "iam", "Identity & Access"
        TELEMETRY = "telemetry", "Telemetry & Monitoring"
        BILLING = "billing", "Billing & Subscriptions"
        OPERATIONS = "operations", "Platform Operations"
        SETTINGS = "settings", "System Settings"
        TENANTS = "tenants", "Tenant Management"
        AUDIT = "audit", "Audit & Compliance"

    class Action(models.TextChoices):
        VIEW = "view", "View"
        CREATE = "create", "Create"
        EDIT = "edit", "Edit"
        DELETE = "delete", "Delete"
        EXECUTE = "execute", "Execute"
        IMPERSONATE = "impersonate", "Impersonate"

    slug = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    module = models.CharField(max_length=30, choices=Module.choices)
    action = models.CharField(max_length=20, choices=Action.choices)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["module", "slug"]

    def __str__(self):
        return f"{self.module}.{self.slug}"


class PlatformRolePermission(models.Model):
    """M2M link between PlatformRole and PlatformPermission."""
    role = models.ForeignKey(
        PlatformRole,
        on_delete=models.CASCADE,
        related_name="platform_permissions",
    )
    permission = models.ForeignKey(
        PlatformPermission,
        on_delete=models.CASCADE,
        related_name="role_assignments",
    )

    class Meta:
        unique_together = [("role", "permission")]

    def __str__(self):
        return f"{self.role.name} → {self.permission.slug}"


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("member", "Member"),
    ]

    class IdentityType(models.TextChoices):
        USER = "user", "User"
        EMPLOYEE = "employee", "Employee"
        PARTNER = "partner", "Partner"
        SYSTEM_ACCOUNT = "system_account", "System Account"

    class PartnerType(models.TextChoices):
        CONTRACTOR = "contractor", "Contractor"
        VENDOR = "vendor", "Vendor"
        CLIENT = "client", "Client"
        INVESTOR = "investor", "Investor"

    class UserStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"
        LOCKED = "locked", "Locked"
        PENDING = "pending", "Pending"

    class ProfileVisibility(models.TextChoices):
        PRIVATE = "private", "Private"
        TEAM = "team", "Team"
        ORGANIZATION = "organization", "Organization"

    class WorkspaceTheme(models.TextChoices):
        LIGHT = "light", "Light"
        DARK = "dark", "Dark"
        SYSTEM = "system", "System"

    class WorkspaceDensity(models.TextChoices):
        COMPACT = "compact", "Compact"
        COMFORTABLE = "comfortable", "Comfortable"

    class WorkspaceSidebarBehavior(models.TextChoices):
        EXPANDED = "expanded", "Expanded"
        COLLAPSED = "collapsed", "Collapsed"

    class WorkspaceLandingPage(models.TextChoices):
        OVERVIEW = "/", "Overview"
        PROPERTIES = "/properties", "Properties"
        PROJECTS = "/projects", "Projects"
        FINANCE = "/finance", "Finance"
        PROCUREMENT = "/procurement", "Procurement"
        ANALYTICS = "/analytics", "Analytics"

    class WorkspaceDashboard(models.TextChoices):
        PORTFOLIO_ANALYTICS = "portfolio_analytics", "Portfolio Analytics"
        BOARD_METRICS = "board_metrics", "Board Metrics"

    class TaskDefaultView(models.TextChoices):
        LIST = "list", "List"
        KANBAN = "kanban", "Kanban"
        CALENDAR = "calendar", "Calendar"

    class ApprovalDelegationRule(models.TextChoices):
        MANUAL_ONLY = "manual_only", "Manual Only"
        USE_ACTIVE_DELEGATIONS = "use_active_delegations", "Use Active Delegations"
        AUTO_WHEN_OUT_OF_OFFICE = "auto_when_out_of_office", "Auto Delegate When Out of Office"

    class DataExportFormat(models.TextChoices):
        PDF = "pdf", "PDF"
        EXCEL = "excel", "Excel"
        CSV = "csv", "CSV"

    class AccessibilityFontSize(models.TextChoices):
        SMALL = "small", "Small"
        MEDIUM = "medium", "Medium"
        LARGE = "large", "Large"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="members",
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="member")
    platform_role = models.ForeignKey(
        PlatformRole,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        help_text="Platform-level role for console access. Null = no console access.",
    )
    assigned_role = models.ForeignKey(
        "settings.Role",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_users",
    )
    assigned_role_valid_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text=(
            "If set, the assigned_role is temporary and is automatically "
            "cleared by the sweep_expired_access_grants Celery task once "
            "this timestamp passes. NULL means a permanent grant."
        ),
    )
    password_last_changed = models.DateTimeField(
        null=True,
        blank=True,
        help_text=(
            "Timestamp of the most recent successful password change. "
            "Used by the org's password_max_age_days policy to detect "
            "expired passwords. NULL = never changed since user creation."
        ),
    )
    profile_photo = models.ImageField(upload_to=user_profile_photo_upload_to, blank=True, null=True)
    has_completed_tour = models.BooleanField(default=False)
    has_completed_onboarding = models.BooleanField(default=False)
    is_demo_account = models.BooleanField(default=False)

    # --- IAM fields ---
    phone = models.CharField(max_length=50, blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    preferred_display_name = models.CharField(max_length=150, blank=True)
    business_unit = models.CharField(max_length=150, blank=True)
    employee_id = models.CharField(max_length=64, blank=True)
    bio = models.TextField(blank=True)
    department = models.ForeignKey(
        "settings.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )
    secondary_phone = models.CharField(max_length=50, blank=True)
    office_location = models.CharField(max_length=150, blank=True)
    timezone = models.CharField(max_length=64, blank=True)
    profile_visibility = models.CharField(
        max_length=20,
        choices=ProfileVisibility.choices,
        default=ProfileVisibility.ORGANIZATION,
    )
    email_visibility = models.CharField(
        max_length=20,
        choices=ProfileVisibility.choices,
        default=ProfileVisibility.TEAM,
    )
    phone_visibility = models.CharField(
        max_length=20,
        choices=ProfileVisibility.choices,
        default=ProfileVisibility.PRIVATE,
    )
    activity_visibility = models.CharField(
        max_length=20,
        choices=ProfileVisibility.choices,
        default=ProfileVisibility.TEAM,
    )
    online_status_visibility = models.CharField(
        max_length=20,
        choices=ProfileVisibility.choices,
        default=ProfileVisibility.TEAM,
    )
    search_discoverable = models.BooleanField(default=True)
    workspace_theme = models.CharField(
        max_length=10,
        choices=WorkspaceTheme.choices,
        default=WorkspaceTheme.SYSTEM,
    )
    workspace_layout_density = models.CharField(
        max_length=20,
        choices=WorkspaceDensity.choices,
        default=WorkspaceDensity.COMFORTABLE,
    )
    workspace_sidebar_behavior = models.CharField(
        max_length=20,
        choices=WorkspaceSidebarBehavior.choices,
        default=WorkspaceSidebarBehavior.EXPANDED,
    )
    workspace_default_landing_page = models.CharField(
        max_length=64,
        choices=WorkspaceLandingPage.choices,
        default=WorkspaceLandingPage.OVERVIEW,
    )
    workspace_default_dashboard = models.CharField(
        max_length=40,
        choices=WorkspaceDashboard.choices,
        default=WorkspaceDashboard.PORTFOLIO_ANALYTICS,
    )
    workspace_dashboard_widget_order = models.JSONField(
        default=default_workspace_widget_order,
        blank=True,
    )
    workspace_dashboard_widget_visibility = models.JSONField(
        default=default_workspace_widget_visibility,
        blank=True,
    )
    task_default_view = models.CharField(
        max_length=20,
        choices=TaskDefaultView.choices,
        default=TaskDefaultView.LIST,
    )
    task_reminder_minutes_before = models.PositiveIntegerField(default=60)
    task_default_due_date_offset_days = models.PositiveSmallIntegerField(default=3)
    task_auto_follow_assigned_tasks = models.BooleanField(default=True)
    task_auto_subscribe_project_updates = models.BooleanField(default=True)
    task_approval_delegation_rule = models.CharField(
        max_length=40,
        choices=ApprovalDelegationRule.choices,
        default=ApprovalDelegationRule.USE_ACTIVE_DELEGATIONS,
    )
    calendar_working_hours_start = models.TimeField(default=dt_time(9, 0))
    calendar_working_hours_end = models.TimeField(default=dt_time(17, 0))
    calendar_working_days = models.JSONField(
        default=default_calendar_working_days,
        blank=True,
    )
    calendar_default_meeting_duration_minutes = models.PositiveSmallIntegerField(default=30)
    calendar_meeting_buffer_minutes = models.PositiveSmallIntegerField(default=10)
    calendar_default_reminder_minutes = models.PositiveIntegerField(
        default=15,
        help_text=(
            "Default reminder lead-time for new CalendarEvents the user creates. "
            "Per-event overrides live on CalendarEvent.reminder_minutes_before. "
            "Set to 0 to opt out of all reminders by default."
        ),
    )
    calendar_timezone_override = models.CharField(max_length=64, blank=True)
    calendar_sync_google_enabled = models.BooleanField(default=False)
    calendar_sync_outlook_enabled = models.BooleanField(default=False)
    calendar_sync_ical_enabled = models.BooleanField(default=False)
    data_default_export_format = models.CharField(
        max_length=10,
        choices=DataExportFormat.choices,
        default=DataExportFormat.PDF,
    )
    data_default_report_filters = models.JSONField(
        default=default_data_report_filters,
        blank=True,
    )
    data_rows_per_page = models.PositiveSmallIntegerField(default=25)
    data_column_visibility = models.JSONField(
        default=default_data_column_visibility,
        blank=True,
    )
    data_saved_views = models.JSONField(
        default=default_data_saved_views,
        blank=True,
    )
    accessibility_font_size = models.CharField(
        max_length=10,
        choices=AccessibilityFontSize.choices,
        default=AccessibilityFontSize.MEDIUM,
    )
    accessibility_high_contrast_mode = models.BooleanField(default=False)
    accessibility_reduced_motion = models.BooleanField(default=False)
    accessibility_screen_reader_support = models.BooleanField(default=False)
    accessibility_keyboard_navigation = models.BooleanField(default=True)
    approval_signature = models.TextField(blank=True)
    default_language = models.CharField(max_length=16, blank=True, default="en")
    reporting_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="direct_reports",
    )
    user_status = models.CharField(
        max_length=10,
        choices=UserStatus.choices,
        default=UserStatus.ACTIVE,
    )
    mfa_enabled = models.BooleanField(default=False)
    passkey_enabled = models.BooleanField(default=False)
    identity_type = models.CharField(
        max_length=20,
        choices=IdentityType.choices,
        default=IdentityType.USER,
    )
    partner_type = models.CharField(
        max_length=20,
        choices=PartnerType.choices,
        blank=True,
        help_text="Only applicable when identity_type is 'partner'.",
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["organization", "user_status"],
                name="acc_prof_org_status_idx",
            ),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.role})"


class UserGroup(models.Model):
    """A named group of users within an organization.

    Used for bulk permission grants, notification routing, and
    organisational grouping orthogonal to roles or departments.
    Org-scoped — a group lives inside exactly one Organization and
    may only contain users from that same Organization.
    """

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="user_groups",
    )
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="user_groups",
        blank=True,
    )
    is_system = models.BooleanField(
        default=False,
        help_text="System groups cannot be deleted via the API.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["organization", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                name="acc_usergroup_org_name_unique",
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization", "name"],
                name="acc_usergroup_org_name_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.organization.name})"


class AccessRequest(models.Model):
    """A user-initiated request for elevated or temporary access.

    Backs the iam/access-requests/ surface (request access, approval queue,
    temporary grants, expiry tracking, privilege elevation).

    The model is intentionally decoupled from apps.workflows: each request
    has a direct ``approver`` FK. If a request needs to drive a multi-step
    workflow, that workflow runs externally and calls
    ``approve``/``reject`` on the request when it reaches a decision.
    """

    class Kind(models.TextChoices):
        ROLE_GRANT = "role_grant", "Role grant"
        ROLE_ELEVATION = "role_elevation", "Privilege elevation"
        RESOURCE_ACCESS = "resource_access", "Resource access"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        EXPIRED = "expired", "Expired"        # request itself timed out before decision
        CANCELLED = "cancelled", "Cancelled"  # withdrawn by requester
        REVOKED = "revoked", "Revoked"        # admin revoked after approval

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="access_requests",
    )
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="access_requests",
    )
    kind = models.CharField(max_length=24, choices=Kind.choices)

    # Target — one of these is populated depending on kind
    requested_role = models.ForeignKey(
        "settings.Role",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="access_requests",
    )
    requested_resource = models.CharField(
        max_length=200,
        blank=True,
        help_text="Free-text resource identifier for kind=resource_access.",
    )

    reason = models.TextField()

    # Approval state
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.PENDING,
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_access_requests",
        help_text="The user designated to decide on this request.",
    )
    approval_decision_at = models.DateTimeField(null=True, blank=True)
    approval_notes = models.TextField(blank=True)

    # Temporary-access window. Optional: NULL granted_valid_until = permanent grant.
    requested_valid_until = models.DateTimeField(null=True, blank=True)
    granted_valid_until = models.DateTimeField(null=True, blank=True)

    # The request itself can expire if not actioned in time.
    request_expires_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="acc_accreq_org_status_idx",
            ),
            models.Index(
                fields=["organization", "approver", "status"],
                name="acc_accreq_org_appr_st_idx",
            ),
            models.Index(
                fields=["organization", "requester", "-created_at"],
                name="acc_accreq_org_req_dt_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"AccessRequest #{self.pk} ({self.kind}, {self.status})"


class AccessReviewCampaign(models.Model):
    """A scheduled review of who has what access in the org.

    Supports the iam/compliance/access-reviews and role-certification
    surfaces. A campaign defines a window during which designated
    reviewers attest each AccessReviewItem (one per user-in-scope) as
    Approved (access confirmed) or Revoked (access removed).
    """

    class Kind(models.TextChoices):
        ACCESS_REVIEW = "access_review", "Access Review"
        ROLE_CERTIFICATION = "role_certification", "Role Certification"
        DORMANT_REVIEW = "dormant_review", "Dormant Account Review"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="access_review_campaigns",
    )
    kind = models.CharField(max_length=24, choices=Kind.choices)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)

    # Optional scope filters — campaign reviews users matching either
    # of these (typically used singly in practice).
    target_role = models.ForeignKey(
        "settings.Role",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="access_review_campaigns",
        help_text="If set, the campaign reviews all users currently assigned this role.",
    )

    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_access_review_campaigns",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["organization", "kind", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_kind_display()}, {self.status})"


class AccessReviewItem(models.Model):
    """One user's review state within an AccessReviewCampaign."""

    class Decision(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Access Confirmed"
        REVOKED = "revoked", "Access Removed"
        DEFERRED = "deferred", "Deferred"

    campaign = models.ForeignKey(
        AccessReviewCampaign,
        on_delete=models.CASCADE,
        related_name="items",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="access_review_items",
    )
    role_at_review = models.ForeignKey(
        "settings.Role",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Snapshot of the user's role at campaign start; preserved even if reassigned later.",
    )

    decision = models.CharField(max_length=12, choices=Decision.choices, default=Decision.PENDING)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="decided_access_review_items",
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["campaign", "user"],
                name="acc_arit_campaign_user_unique",
            ),
        ]
        indexes = [
            models.Index(fields=["campaign", "decision"]),
        ]

    def __str__(self) -> str:
        return f"AccessReviewItem #{self.pk} ({self.user_id}, {self.decision})"


class IdentityProvider(models.Model):
    """Per-organization identity provider configuration.

    Backs the iam/federation/* surfaces. Stores configuration only —
    actual auth-backend wiring (OIDC discovery, SAML metadata parsing,
    LDAP bind, Google Directory API sync, etc.) is the integration
    phase that follows. The ``test`` and ``sync_now`` viewset actions
    are honest stubs that return 501 with a structural-only response
    until per-kind backend code is written.

    Secrets (passwords, client_secret, signing certs) live in a
    separate ``secrets`` JSONField that is write-only via the API —
    GET responses replace each secret value with the literal sentinel
    ``"********"`` so admins can see *which* keys are populated
    without ever reading values back.

    TODO: encrypt the ``secrets`` field at rest via the same Fernet
    helper used by apps.backup. Until then, the column stores
    plaintext — DB access controls (the secret values never leave the
    DB host) are the only protection. Acceptable for a configuration
    surface that has no live auth path yet.
    """

    class Kind(models.TextChoices):
        ACTIVE_DIRECTORY = "active_directory", "Active Directory"
        AZURE_AD = "azure_ad", "Azure AD / Entra ID"
        GOOGLE_WORKSPACE = "google_workspace", "Google Workspace"
        LDAP = "ldap", "LDAP"
        SAML_OIDC = "saml_oidc", "Generic SAML / OIDC"

    class SyncStatus(models.TextChoices):
        NEVER = "never", "Never run"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        STUB = "stub", "Stub — integration phase pending"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="identity_providers",
    )
    kind = models.CharField(max_length=24, choices=Kind.choices)
    name = models.CharField(
        max_length=120,
        help_text="Admin-facing display name for this provider (e.g. 'Acme Azure tenant').",
    )
    is_enabled = models.BooleanField(
        default=False,
        help_text="When True, this provider appears as a sign-in option (once the integration phase lands for its kind).",
    )

    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Public configuration: server URLs, base DNs, attribute mappings, scopes, etc.",
    )
    secrets = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Secret configuration: bind passwords, client secrets, signing certs. "
            "Write-only via API; GET responses mask values."
        ),
    )

    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_sync_status = models.CharField(
        max_length=10,
        choices=SyncStatus.choices,
        default=SyncStatus.NEVER,
    )
    last_sync_message = models.TextField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["organization", "kind", "name"]
        indexes = [
            models.Index(fields=["organization", "kind"]),
            models.Index(fields=["organization", "is_enabled"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_kind_display()})"


class Webhook(models.Model):
    """Org-scoped outbound webhook subscription.

    Backs iam/webhooks. Stores the URL to POST to + the events it
    subscribes to + an HMAC signing secret. Real delivery happens via
    a Celery task (apps.accounts.tasks.deliver_webhook — to be added);
    for v1 the test action sends synchronously so admins can validate
    config during setup.
    """

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="webhooks",
    )
    name = models.CharField(max_length=160)
    url = models.URLField(max_length=500)
    events = models.JSONField(
        default=list,
        blank=True,
        help_text='Array of event names this webhook subscribes to (e.g. ["user.created", "access_request.approved"]). Empty array = all events.',
    )
    secret = models.CharField(
        max_length=128,
        blank=True,
        help_text="HMAC-SHA256 signing secret. Set on creation; receivers verify the X-DeveloperOS-Signature header.",
    )
    is_active = models.BooleanField(default=True)

    last_delivery_at = models.DateTimeField(null=True, blank=True)
    last_delivery_status = models.CharField(max_length=16, blank=True, default="")
    last_delivery_message = models.TextField(blank=True)
    delivery_count = models.PositiveIntegerField(default=0)
    failure_count = models.PositiveIntegerField(default=0)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["organization", "name"]
        indexes = [
            models.Index(fields=["organization", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} → {self.url}"


class WebhookDelivery(models.Model):
    """Log of webhook delivery attempts."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        DELIVERED = "delivered", "Delivered"
        FAILED = "failed", "Failed"

    webhook = models.ForeignKey(
        Webhook,
        on_delete=models.CASCADE,
        related_name="deliveries",
    )
    event_name = models.CharField(max_length=120)
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    response_code = models.PositiveSmallIntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True, help_text="Truncated to 2000 chars on save.")
    attempt_number = models.PositiveSmallIntegerField(default=1)
    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["webhook", "-created_at"]),
            models.Index(fields=["webhook", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.webhook_id}/{self.event_name} ({self.status})"


class ApplicationToken(models.Model):
    """Long-lived bearer token for non-human / scripted access.

    Distinct from per-user JWTs (which are short-lived) and from
    ServiceAccount API keys (which are scoped to a service account).
    Application tokens are owned by an organisation and identified by
    a name; they're used in headers as ``Authorization: AppToken <token>``.

    The plaintext token is shown ONCE at creation/regeneration and
    never persisted; only its SHA-256 hash + a display prefix are
    stored. Scope-based authz is captured but enforcement is
    out-of-scope for v1 (each scope check would have to be coded into
    the protected endpoints).
    """

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="application_tokens",
    )
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    token_hash = models.CharField(max_length=64, db_index=True, unique=True)
    prefix = models.CharField(max_length=12, help_text="First 8 chars of the token for display, e.g. 'dvo_a1b2c3'.")
    scopes = models.JSONField(
        default=list,
        blank=True,
        help_text='Array of scope strings (e.g. ["read:projects", "write:invoices"]). Empty = full org scope.',
    )
    expires_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["organization", "name"]
        indexes = [
            models.Index(fields=["organization", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} [{self.prefix}…]"


class Connector(models.Model):
    """System-wide catalogue of available third-party integrations.

    Seeded data, not user-editable. Lists Slack, Notion, Zapier, etc.;
    org admins install instances of these via ConnectorInstallation.
    """

    class Category(models.TextChoices):
        COMMUNICATION = "communication", "Communication"
        AUTOMATION = "automation", "Automation"
        STORAGE = "storage", "Storage"
        ANALYTICS = "analytics", "Analytics"
        FINANCE = "finance", "Finance"
        DEVELOPMENT = "development", "Development"
        OTHER = "other", "Other"

    slug = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=120)
    vendor = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=24, choices=Category.choices, default=Category.OTHER)
    icon_url = models.CharField(max_length=300, blank=True)
    docs_url = models.CharField(max_length=300, blank=True)
    is_available = models.BooleanField(
        default=True,
        help_text="Set to False to hide a connector from the catalogue without deleting it.",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["category", "name"]
        indexes = [
            models.Index(fields=["category", "is_available"]),
        ]

    def __str__(self) -> str:
        return self.name


class ConnectorInstallation(models.Model):
    """Per-organisation installation of a Connector.

    Scope is intentionally minimal in v1 — stores config + a masked
    secrets blob (same pattern as IdentityProvider). Real OAuth flows
    + per-connector sync logic land later when specific connectors get
    their integration phase.
    """

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="connector_installations",
    )
    connector = models.ForeignKey(
        Connector,
        on_delete=models.PROTECT,
        related_name="installations",
    )
    is_enabled = models.BooleanField(default=False)
    config = models.JSONField(default=dict, blank=True)
    secrets = models.JSONField(
        default=dict,
        blank=True,
        help_text="Write-only via API. GET responses replace each value with '********'.",
    )
    last_synced_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["organization", "connector"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "connector"],
                name="acc_connector_install_unique",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.organization_id} ↔ {self.connector.name}"


class Invitation(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("expired", "Expired"),
    ]

    email = models.EmailField()
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="invitations",
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_invitations",
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")

    # Pre-provisioned metadata — applied to the profile on acceptance
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    role = models.ForeignKey(
        "settings.Role",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    department = models.ForeignKey(
        "settings.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    job_title = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="acc_inv_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="acc_inv_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.email} → {self.organization.name} ({self.status})"


class OAuthConnection(models.Model):
    PROVIDER_CHOICES = [
        ("google", "Google"),
        ("microsoft", "Microsoft"),
        ("apple", "Apple"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="oauth_connections",
    )
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    provider_user_id = models.CharField(max_length=255)
    email = models.EmailField()
    display_name = models.CharField(max_length=255, blank=True)
    access_token_hash = models.CharField(max_length=64, blank=True)
    connected_at = models.DateTimeField(auto_now_add=True)
    last_login_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("provider", "provider_user_id")]
        indexes = [models.Index(fields=["provider", "email"])]
        ordering = ["-connected_at"]

    def __str__(self):
        return f"{self.user.email} via {self.provider}"


class UserIntegrationConnection(models.Model):
    class Provider(models.TextChoices):
        GOOGLE_DRIVE = "google_drive", "Google Drive"
        DROPBOX = "dropbox", "Dropbox"
        SLACK = "slack", "Slack"
        TEAMS = "teams", "Teams"
        ZAPIER = "zapier", "Zapier"
        WEBHOOKS = "webhooks", "Webhooks"

    class Status(models.TextChoices):
        CONNECTED = "connected", "Connected"
        REVOKED = "revoked", "Revoked"
        ERROR = "error", "Error"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="integration_connections",
    )
    provider = models.CharField(max_length=32, choices=Provider.choices)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.CONNECTED,
    )
    account_label = models.CharField(max_length=200, blank=True)
    external_account_id = models.CharField(max_length=255, blank=True)
    webhook_url = models.URLField(blank=True)
    connected_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    last_token_refresh_at = models.DateTimeField(null=True, blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["provider", "-updated_at"]
        unique_together = [("user", "provider")]
        indexes = [
            models.Index(fields=["user", "provider"]),
            models.Index(fields=["user", "status"]),
        ]

    def __str__(self):
        return f"{self.user.email} integration {self.provider}"


class ServiceAccount(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"
        REVOKED = "revoked", "Revoked"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="service_accounts",
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="owned_service_accounts",
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("organization", "name")]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="acc_sa_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="acc_sa_org_created_idx",
            ),
        ]

    def __str__(self):
        return self.name


class APIKey(models.Model):
    PREFIX_LENGTH = 8
    KEY_LENGTH = 40

    service_account = models.ForeignKey(
        ServiceAccount,
        on_delete=models.CASCADE,
        related_name="api_keys",
    )
    label = models.CharField(max_length=100, blank=True)
    prefix = models.CharField(max_length=8, db_index=True)
    hashed_key = models.CharField(max_length=64)
    scopes = models.JSONField(default=list, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["service_account", "is_active"],
                name="acc_apikey_sa_active_idx",
            ),
            models.Index(
                fields=["service_account", "-created_at"],
                name="acc_apikey_sa_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.prefix}... ({self.service_account.name})"

    @classmethod
    def generate(cls, service_account, label="", scopes=None, expires_at=None):
        raw_key = secrets.token_hex(cls.KEY_LENGTH)
        prefix = raw_key[: cls.PREFIX_LENGTH]
        hashed = hashlib.sha256(raw_key.encode()).hexdigest()
        instance = cls.objects.create(
            service_account=service_account,
            label=label,
            prefix=prefix,
            hashed_key=hashed,
            scopes=scopes or [],
            expires_at=expires_at,
        )
        # Return both the instance and the raw key (only time it's visible)
        return instance, raw_key


class UserAuthSession(models.Model):
    class AuthProvider(models.TextChoices):
        PASSWORD = "password", "Password"
        GOOGLE = "google", "Google"
        MICROSOFT = "microsoft", "Microsoft"
        APPLE = "apple", "Apple"
        SSO_SAML = "sso_saml", "SSO / SAML"
        PASSKEY = "passkey", "Passkey / Biometric"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="auth_sessions",
    )
    sid = models.UUIDField(unique=True, db_index=True, default=uuid.uuid4, editable=False)
    auth_provider = models.CharField(
        max_length=20,
        choices=AuthProvider.choices,
        default=AuthProvider.PASSWORD,
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    device_label = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoke_reason = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-last_seen_at"]
        indexes = [
            models.Index(fields=["user", "revoked_at"]),
            models.Index(fields=["user", "last_seen_at"]),
        ]

    def __str__(self):
        return f"{self.user.email} [{self.sid}]"


class UserPasswordHistory(models.Model):
    """Past password hashes for password-reuse prevention.

    Written by the change-password / set-password flows. The number of
    rows kept per user is bounded by the org's password_history_count
    setting; older rows can be pruned by a periodic task (none yet).
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="password_history",
    )
    password_hash = models.CharField(
        max_length=255,
        help_text="Django-format password hash (algorithm$salt$hash).",
    )
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-changed_at"]
        indexes = [
            models.Index(fields=["user", "-changed_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} @ {self.changed_at.isoformat()}"


class UserSecurityEvent(models.Model):
    class EventType(models.TextChoices):
        # Authentication
        LOGIN_SUCCESS = "login_success", "Login Success"
        LOGIN_FAILED = "login_failed", "Login Failed"
        OTP_CHALLENGE = "otp_challenge", "OTP Challenge"
        OTP_FAILED = "otp_failed", "OTP Failed"
        PASSWORD_CHANGED = "password_changed", "Password Changed"
        SESSION_REVOKED = "session_revoked", "Session Revoked"
        SESSION_REVOKED_OTHERS = "session_revoked_others", "Other Sessions Revoked"
        PROVIDER_LINKED = "provider_linked", "Provider Linked"
        # Auth policy changes
        PASSWORD_POLICY_CHANGED = "password_policy_changed", "Password Policy Changed"
        LOGIN_METHODS_CHANGED = "login_methods_changed", "Login Methods Changed"
        # Roles & permissions
        ROLE_ASSIGNED = "role_assigned", "Role Assigned"
        ROLE_UNASSIGNED = "role_unassigned", "Role Unassigned"
        ROLE_PERMISSIONS_CHANGED = "role_permissions_changed", "Role Permissions Changed"
        # Access requests
        ACCESS_REQUEST_SUBMITTED = "access_request_submitted", "Access Request Submitted"
        ACCESS_REQUEST_APPROVED = "access_request_approved", "Access Request Approved"
        ACCESS_REQUEST_REJECTED = "access_request_rejected", "Access Request Rejected"
        ACCESS_REQUEST_REVOKED = "access_request_revoked", "Access Request Revoked"
        ACCESS_REQUEST_CANCELLED = "access_request_cancelled", "Access Request Cancelled"
        ACCESS_GRANT_AUTO_REVOKED = "access_grant_auto_revoked", "Access Grant Auto-Revoked"

    class Status(models.TextChoices):
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        INFO = "info", "Info"

    class Severity(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="security_events",
        null=True,
        blank=True,
    )
    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="security_events",
        null=True,
        blank=True,
        help_text="Org context for cross-user/system events. May be NULL for unauthenticated login attempts.",
    )
    principal = models.CharField(max_length=254, blank=True)
    event_type = models.CharField(max_length=40, choices=EventType.choices)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.INFO)
    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.LOW)
    provider = models.CharField(max_length=40, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    device_label = models.CharField(max_length=200, blank=True)
    target_type = models.CharField(
        max_length=40,
        blank=True,
        help_text="Resource kind acted on (e.g. 'role', 'user', 'session').",
    )
    target_id = models.CharField(
        max_length=64,
        blank=True,
        help_text="ID of the target resource. String to accommodate UUIDs.",
    )
    detail = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(fields=["user", "occurred_at"]),
            models.Index(fields=["user", "event_type", "occurred_at"]),
            models.Index(fields=["principal", "occurred_at"]),
            models.Index(fields=["organization", "occurred_at"]),
            models.Index(fields=["organization", "event_type", "occurred_at"]),
            models.Index(fields=["organization", "severity", "occurred_at"]),
        ]

    def __str__(self):
        principal = self.principal or (self.user.email if self.user_id else "unknown")
        return f"{self.event_type} ({principal})"


# ---------------------------------------------------------------------------
# Subscription Lifecycle
# ---------------------------------------------------------------------------


class OrganizationSubscription(models.Model):
    """
    One-to-one with Organization — the active subscription state.
    Tracks the current edition, billing cycle, seat usage, and external
    payment provider references.
    """

    class Status(models.TextChoices):
        TRIALING = "trialing", "Trial"
        ACTIVE = "active", "Active"
        PAST_DUE = "past_due", "Past Due"
        SUSPENDED = "suspended", "Suspended"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"

    class BillingCycle(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        ANNUAL = "annual", "Annual"

    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name="subscription",
    )
    edition = models.ForeignKey(
        "settings.PlatformEdition",
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    billing_cycle = models.CharField(
        max_length=10,
        choices=BillingCycle.choices,
        default=BillingCycle.MONTHLY,
    )

    # Billing period
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)

    # Trial
    trial_start = models.DateTimeField(null=True, blank=True)
    trial_end = models.DateTimeField(null=True, blank=True)

    # Seat tracking
    seats_purchased = models.PositiveIntegerField(
        default=0, help_text="0 = use edition default (max_users)"
    )
    seats_used = models.PositiveIntegerField(default=0)

    # Storage tracking
    storage_used_gb = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )

    # Cancellation
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancel_reason = models.TextField(blank=True)

    # External billing provider (e.g. Stripe)
    external_subscription_id = models.CharField(max_length=255, blank=True)
    external_customer_id = models.CharField(max_length=255, blank=True)
    payment_method_summary = models.CharField(
        max_length=100, blank=True, help_text='e.g. "Visa ending 4242"'
    )

    auto_renew = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Organization subscription"
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["current_period_end"]),
        ]

    def __str__(self):
        return f"{self.organization.name} — {self.edition.name} ({self.get_status_display()})"

    @property
    def effective_max_users(self):
        """Seats purchased, or edition default if 0."""
        if self.seats_purchased:
            return self.seats_purchased
        return self.edition.max_users

    @property
    def effective_max_storage_gb(self):
        """Edition base storage + purchased storage add-ons."""
        base = self.edition.max_storage_gb
        if base is None:
            return None  # unlimited
        addon_storage = (
            self.active_add_ons
            .filter(add_on__add_on_type="storage")
            .aggregate(total=models.Sum("add_on__storage_gb"))["total"]
            or 0
        )
        return base + addon_storage


class SubscriptionEvent(models.Model):
    """Immutable audit log of every subscription state change."""

    class EventType(models.TextChoices):
        CREATED = "created", "Created"
        ACTIVATED = "activated", "Activated"
        UPGRADED = "upgraded", "Upgraded"
        DOWNGRADED = "downgraded", "Downgraded"
        RENEWED = "renewed", "Renewed"
        PAYMENT_FAILED = "payment_failed", "Payment Failed"
        PAYMENT_RECOVERED = "payment_recovered", "Payment Recovered"
        SUSPENDED = "suspended", "Suspended"
        CANCELLED = "cancelled", "Cancelled"
        REACTIVATED = "reactivated", "Reactivated"
        EXPIRED = "expired", "Expired"
        TRIAL_STARTED = "trial_started", "Trial Started"
        TRIAL_ENDED = "trial_ended", "Trial Ended"

    subscription = models.ForeignKey(
        OrganizationSubscription,
        on_delete=models.CASCADE,
        related_name="events",
    )
    event_type = models.CharField(max_length=30, choices=EventType.choices)
    from_edition = models.ForeignKey(
        "settings.PlatformEdition",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    to_edition = models.ForeignKey(
        "settings.PlatformEdition",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    metadata = models.JSONField(default=dict, blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-occurred_at"]
        verbose_name = "Subscription event"
        indexes = [
            models.Index(fields=["subscription", "-occurred_at"]),
        ]

    def __str__(self):
        return f"{self.get_event_type_display()} — {self.subscription.organization.name}"


class ActiveSubscriptionAddOn(models.Model):
    """Tracks which add-ons an organization has purchased."""

    subscription = models.ForeignKey(
        OrganizationSubscription,
        on_delete=models.CASCADE,
        related_name="active_add_ons",
    )
    add_on = models.ForeignKey(
        "settings.SubscriptionAddOn",
        on_delete=models.PROTECT,
        related_name="activations",
    )
    activated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("subscription", "add_on")]
        verbose_name = "Active subscription add-on"

    def __str__(self):
        return f"{self.subscription.organization.name} — {self.add_on.name}"


class DemoRequest(models.Model):
    """Tracks demo requests from leads and their provisioning status."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROVISIONING = "provisioning", "Provisioning"
        PROVISIONED = "provisioned", "Provisioned"
        FAILED = "failed", "Failed"

    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    company_name = models.CharField(max_length=200)
    company_size = models.CharField(max_length=50, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    message = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    provisioned_organization = models.ForeignKey(
        Organization,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    provisioned_user = models.ForeignKey(
        "auth.User",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    provisioned_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Demo request"

    def __str__(self):
        return f"{self.full_name} — {self.company_name} ({self.status})"


# ---------------------------------------------------------------------------
# MFA Devices
# ---------------------------------------------------------------------------


class TOTPDevice(models.Model):
    """TOTP authenticator app device (one per user)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="totp_device",
    )
    secret = models.CharField(max_length=64)  # base32 encoded
    confirmed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "TOTP device"

    def __str__(self):
        status = "confirmed" if self.confirmed else "unconfirmed"
        return f"TOTP ({self.user.email}) [{status}]"


class RecoveryCode(models.Model):
    """One-time backup codes for MFA recovery."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recovery_codes",
    )
    code_hash = models.CharField(max_length=128)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "used_at"]),
        ]

    def __str__(self):
        status = "used" if self.used_at else "available"
        return f"Recovery code ({self.user.email}) [{status}]"

    @property
    def is_used(self):
        return self.used_at is not None


class WebAuthnCredential(models.Model):
    """FIDO2/WebAuthn passkey credential."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="webauthn_credentials",
    )
    credential_id = models.BinaryField()
    public_key = models.BinaryField()
    sign_count = models.PositiveIntegerField(default=0)
    name = models.CharField(max_length=100, default="Passkey")
    aaguid = models.CharField(max_length=36, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "WebAuthn credential"
        indexes = [
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.user.email})"
