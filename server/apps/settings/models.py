from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.text import slugify

from apps.accounts.models import Organization

from .currency import get_default_currency_code

# ---------------------------------------------------------------------------
# RBAC Enums
# ---------------------------------------------------------------------------


class Module(models.TextChoices):
    PROPERTIES = "properties", "Properties"
    PROJECTS = "projects", "Projects"
    FINANCE = "finance", "Finance"
    PROCUREMENT = "procurement", "Procurement"
    DOCUMENTS = "documents", "Documents"
    ANALYTICS = "analytics", "Analytics"
    CRM = "crm", "CRM"
    TENANTS = "tenants", "Tenants"
    CONTRACTS = "contracts", "Contracts"
    COMPLIANCE = "compliance", "Compliance"
    HR = "hr", "Human Resources"
    IAM = "iam", "Identity & Access"
    SUPPORT_DESK = "support_desk", "Support Desk"
    FACILITY_MANAGEMENT = "facility_management", "Facility Management"
    SETTINGS = "settings", "Settings"
    # Add-on only modules (not included in any tier)
    CONSTRUCTION = "construction", "Construction"
    PAYROLL = "payroll", "Payroll"
    CALENDAR = "calendar", "Calendar"
    MAIL = "mail", "Mail"

# Modules that are NEVER included in any tier — purchasable add-ons only.
ADDON_ONLY_MODULES: set[str] = {
    Module.CONSTRUCTION,
    Module.PAYROLL,
    Module.CALENDAR,
    Module.MAIL,
}


# ---------------------------------------------------------------------------
# Subscription Tier → Module Mapping
# ---------------------------------------------------------------------------

# Scale/Custom get everything except permanent add-on-only modules.
_SCALE_MODULES = {m.value for m in Module} - ADDON_ONLY_MODULES

TIER_MODULE_MAP: dict[str, set[str]] = {
    "essentials": {
        Module.PROPERTIES,
        Module.PROJECTS,
        Module.DOCUMENTS,
        Module.IAM,
        Module.SUPPORT_DESK,
        Module.SETTINGS,
    },
    "growth": {
        Module.PROPERTIES,
        Module.PROJECTS,
        Module.FINANCE,
        Module.PROCUREMENT,
        Module.CONTRACTS,
        Module.DOCUMENTS,
        Module.ANALYTICS,
        Module.COMPLIANCE,
        Module.HR,
        Module.IAM,
        Module.SUPPORT_DESK,
        Module.SETTINGS,
    },
    "scale": _SCALE_MODULES,
    "custom": _SCALE_MODULES,
}


class SubModule(models.TextChoices):
    # properties
    PROPERTIES = "properties.properties", "Properties"
    UNITS = "properties.units", "Units"
    PROPERTY_IMAGES = "properties.images", "Images"
    PROPERTY_DOCUMENTS = "properties.documents", "Documents"
    VALUATIONS = "properties.valuations", "Valuations"
    OWNERSHIPS = "properties.ownerships", "Ownerships"
    ENCUMBRANCES = "properties.encumbrances", "Encumbrances"
    # projects
    PROJECTS = "projects.projects", "Projects"
    PHASES = "projects.phases", "Phases"
    TASKS = "projects.tasks", "Tasks"
    MILESTONES = "projects.milestones", "Milestones"
    COSTS = "projects.costs", "Costs"
    # finance
    BILLS = "finance.bills", "Bills"
    INVOICES = "finance.invoices", "Invoices"
    CUSTOMERS = "finance.customers", "Customers"
    PAYMENTS = "finance.payments", "Payments"
    ACCOUNTS = "finance.accounts", "Chart of Accounts"
    BUDGETS = "finance.budgets", "Budgets"
    FINANCE_REPORTS = "finance.reports", "Finance Reports"
    # procurement
    VENDORS = "procurement.vendors", "Vendors"
    REQUISITIONS = "procurement.requisitions", "Requisitions"
    PURCHASE_ORDERS = "procurement.orders", "Purchase Orders"
    GOODS_RECEIPTS = "procurement.receipts", "Goods Receipts"
    RFQS = "procurement.rfqs", "RFQs"
    TENDERS = "procurement.tenders", "Tender Comparisons"
    # documents
    DOCUMENTS_ALL = "documents.all", "Documents"
    # analytics
    ANALYTICS_ALL = "analytics.all", "Analytics"
    # crm, tenants, contracts, compliance
    CRM_ALL = "crm.all", "CRM"
    TENANTS_ALL = "tenants.all", "Tenants"
    CONTRACTS_ALL = "contracts.all", "Contracts"
    COMPLIANCE_ALL = "compliance.all", "Compliance"
    # hr
    HR_ORG_STRUCTURE = "hr.org_structure", "Organization Structure"
    HR_POSITIONS = "hr.positions", "Positions"
    HR_BUDGETING = "hr.budgeting", "Position Budgeting"
    HR_VACANCIES = "hr.vacancies", "Vacancies"
    HR_EMPLOYEE_DIRECTORY = "hr.employee_directory", "Employee Directory"
    HR_COMPENSATION = "hr.compensation", "Compensation"
    HR_REQUISITIONS = "hr.requisitions", "Job Requisitions"
    HR_JOB_LISTINGS = "hr.job_listings", "Job Listings"
    HR_CANDIDATES = "hr.candidates", "Candidates"
    HR_INTERVIEWS = "hr.interviews", "Interviews"
    HR_OFFERS = "hr.offers", "Job Offers"
    # iam
    IAM_USERS = "iam.users", "User Management"
    IAM_SERVICE_ACCOUNTS = "iam.service_accounts", "Service Accounts"
    IAM_MFA_SETTINGS = "iam.mfa_settings", "MFA Settings"
    # support desk
    SUPPORT_DESK_OVERVIEW = "support_desk.overview", "Support Dashboard"
    SUPPORT_DESK_TICKETS = "support_desk.tickets", "Support Tickets"
    # settings
    COMPANY_PROFILE = "settings.company_profile", "Company Profile"
    SUBSIDIARIES_SM = "settings.subsidiaries", "Subsidiaries"
    HIERARCHY = "settings.hierarchy", "Hierarchy"
    ROLES_SM = "settings.roles", "Roles & Permissions"
    SECURITY = "settings.security", "Security Controls"
    SYSTEM_PREFERENCES = "settings.system_preferences", "System Preferences"
    AUDIT_COMPLIANCE = "settings.audit_compliance", "Audit & Compliance"
    WORKFLOW_TEMPLATES = "settings.workflow_templates", "Workflow Templates"
    APPROVAL_POLICIES = "settings.approval_policies", "Approval Policies"
    DELEGATIONS = "settings.delegations", "Delegations"
    SUBSCRIPTIONS = "settings.subscriptions", "Subscriptions"


class Action(models.TextChoices):
    VIEW = "view", "View"
    COMMENT = "comment", "Comment"
    CREATE = "create", "Create"
    EDIT = "edit", "Edit"
    UPLOAD_VERSION = "upload_version", "Upload Version"
    APPROVE = "approve", "Approve"
    ARCHIVE = "archive", "Archive"
    ADMIN_OVERRIDE = "admin_override", "Admin Override"
    DELETE = "delete", "Delete"
    EXPORT = "export", "Export"
    ASSIGN = "assign", "Assign"
    CONFIGURE = "configure", "Configure"
    MANAGE = "manage", "Manage"


class Subsidiary(models.Model):
    class RelationshipType(models.TextChoices):
        SUBSIDIARY = "subsidiary", "Subsidiary"
        BRANCH = "branch", "Branch Office"
        JOINT_VENTURE = "joint_venture", "Joint Venture"
        ASSOCIATE = "associate", "Associate Company"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        DORMANT = "dormant", "Dormant"
        DISSOLVED = "dissolved", "Dissolved"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="subsidiaries",
    )
    name = models.CharField(max_length=300)
    legal_name = models.CharField(max_length=300, blank=True)
    registration_number = models.CharField(max_length=100, blank=True)
    tax_id = models.CharField(max_length=100, blank=True)
    relationship_type = models.CharField(
        max_length=20,
        choices=RelationshipType.choices,
        default=RelationshipType.SUBSIDIARY,
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "subsidiaries"
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="set_sub_org_created_idx",
            ),
        ]

    def __str__(self):
        return self.name


class Division(models.Model):
    class UnitCategory(models.TextChoices):
        PROFIT_CENTER = "profit_center", "Profit Center"
        COST_CENTER = "cost_center", "Cost Center"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="divisions",
    )
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, blank=True)
    description = models.TextField(blank=True)
    head = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="headed_divisions",
    )
    unit_category = models.CharField(
        max_length=20,
        choices=UnitCategory.choices,
        default=UnitCategory.COST_CENTER,
    )
    location_region = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]
        unique_together = [("organization", "code")]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="set_div_org_created_idx",
            ),
        ]

    def __str__(self):
        return self.name


class Department(models.Model):
    division = models.ForeignKey(
        Division,
        on_delete=models.CASCADE,
        related_name="departments",
    )
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, blank=True)
    description = models.TextField(blank=True)
    head = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="headed_departments",
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]
        unique_together = [("division", "code")]

    def __str__(self):
        return self.name


class CostCenter(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="cost_centers",
    )
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=200)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cost_centers",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]
        unique_together = [("organization", "code")]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="set_cc_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.code} — {self.name}"


class ProfitCenter(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="profit_centers",
    )
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=200)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="profit_centers",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]
        unique_together = [("organization", "code")]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="set_pc_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.code} — {self.name}"


# ---------------------------------------------------------------------------
# RBAC — Roles & Permissions
# ---------------------------------------------------------------------------


class Role(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="roles",
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)
    description = models.TextField(blank=True)
    is_system = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        unique_together = [("organization", "slug")]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="set_role_org_created_idx",
            ),
        ]

    def __str__(self):
        return self.name


class DataScope(models.Model):
    class ScopeKey(models.TextChoices):
        SELF = "self", "Self"
        DEPARTMENT = "department", "Department"
        PROJECT = "project", "Project"
        ORGANIZATION = "organization", "Organization"

    key = models.CharField(max_length=20, choices=ScopeKey.choices, unique=True)
    label = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_system = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "data_scopes"
        ordering = ["key"]

    def __str__(self):
        return self.label


class Permission(models.Model):
    module = models.CharField(max_length=30, choices=Module.choices)
    sub_module = models.CharField(max_length=50, choices=SubModule.choices)
    action = models.CharField(max_length=20, choices=Action.choices)
    key = models.CharField(max_length=80, unique=True, editable=False)

    class Meta:
        unique_together = [("sub_module", "action")]
        ordering = ["module", "sub_module", "action"]

    def save(self, *args, **kwargs):
        self.module = self.sub_module.split(".")[0]
        self.key = f"{self.sub_module}.{self.action}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.key


class RolePermission(models.Model):
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="permissions",
    )
    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name="role_permissions",
    )
    module = models.CharField(max_length=30, choices=Module.choices)
    sub_module = models.CharField(max_length=50, choices=SubModule.choices)
    action = models.CharField(max_length=20, choices=Action.choices)

    class Meta:
        unique_together = [("role", "sub_module", "action"), ("role", "permission")]
        ordering = ["module", "sub_module", "action"]

    def save(self, *args, **kwargs):
        if self.permission_id:
            self.module = self.permission.module
            self.sub_module = self.permission.sub_module
            self.action = self.permission.action
        elif self.sub_module:
            self.module = self.sub_module.split(".")[0]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.role.name}: {self.sub_module}.{self.action}"


class RoleScope(models.Model):
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="scopes",
    )
    data_scope = models.ForeignKey(
        DataScope,
        on_delete=models.CASCADE,
        related_name="role_scopes",
    )
    module = models.CharField(max_length=30, choices=Module.choices, blank=True, default="")
    sub_module = models.CharField(max_length=50, choices=SubModule.choices, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "role_scopes"
        unique_together = [("role", "module", "sub_module", "data_scope")]
        ordering = ["role_id", "module", "sub_module", "data_scope__key"]

    def save(self, *args, **kwargs):
        if self.sub_module:
            self.module = self.sub_module.split(".", 1)[0]
        super().save(*args, **kwargs)

    def __str__(self):
        scope_target = self.sub_module or self.module or "global"
        return f"{self.role.name}: {self.data_scope.key} @ {scope_target}"


class UserScopeAssignment(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="scope_assignments",
    )
    data_scope = models.ForeignKey(
        DataScope,
        on_delete=models.CASCADE,
        related_name="user_scope_assignments",
    )
    module = models.CharField(max_length=30, choices=Module.choices, blank=True, default="")
    sub_module = models.CharField(max_length=50, choices=SubModule.choices, blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_scope_assignments",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_scope_assignments"
        unique_together = [("user", "module", "sub_module", "data_scope")]
        ordering = ["user_id", "module", "sub_module", "data_scope__key"]

    def save(self, *args, **kwargs):
        if self.sub_module:
            self.module = self.sub_module.split(".", 1)[0]
        super().save(*args, **kwargs)

    def __str__(self):
        scope_target = self.sub_module or self.module or "global"
        return f"{self.user_id}: {self.data_scope.key} @ {scope_target}"


# ---------------------------------------------------------------------------
# Contextual Access Layer
# ---------------------------------------------------------------------------


class AccessPolicy(models.Model):
    """Conditional access policy evaluated at request time.

    Companion models PolicyCondition + PolicyAction define the policy's
    predicates and outcome. Evaluation lives in
    apps.accounts.policy_engine; enforcement is provided by
    AccessPolicyMiddleware, which must be wired explicitly into
    MIDDLEWARE (not added by default).
    """

    class Kind(models.TextChoices):
        # UI taxonomy used by the iam/access-policies/* pages. Each
        # kind-specific page creates policies with a matching kind so
        # filtering is trivial; the "conditional" kind is the
        # advanced multi-condition builder.
        CONDITIONAL = "conditional", "Conditional access"
        IP_RESTRICTIONS = "ip_restrictions", "IP restrictions"
        DEVICE_RESTRICTIONS = "device_restrictions", "Device restrictions"
        LOCATION_RESTRICTIONS = "location_restrictions", "Location restrictions"
        TIME_BASED = "time_based", "Time-based access"
        SESSION_DURATION = "session_duration", "Session duration"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="access_policies",
    )
    key = models.SlugField(max_length=120)
    kind = models.CharField(
        max_length=24,
        choices=Kind.choices,
        default=Kind.CONDITIONAL,
        help_text=(
            "UI discriminator. Kind-specific pages filter on this; the "
            "policy engine inspects the underlying PolicyCondition rows "
            "regardless."
        ),
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    module = models.CharField(max_length=40, blank=True, default="")
    sub_module = models.CharField(max_length=80, blank=True, default="")
    action = models.CharField(max_length=40, blank=True, default="")
    priority = models.PositiveIntegerField(
        default=100,
        help_text="Lower numbers are evaluated first.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "access_policies"
        ordering = ["priority", "name"]
        unique_together = [("organization", "key")]
        indexes = [
            models.Index(fields=["organization", "is_active", "priority"]),
            models.Index(fields=["organization", "kind"]),
            models.Index(fields=["module", "sub_module", "action"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.key})"


class PolicyCondition(models.Model):
    """Atomic condition row belonging to an access policy."""

    class ConditionType(models.TextChoices):
        USER_ROLE = "user_role", "User Role"
        ACTION = "action", "Action"
        IP_RESTRICTION = "ip_restriction", "IP Restriction"
        TIME_RESTRICTION = "time_restriction", "Time Restriction"
        DEVICE_RESTRICTION = "device_restriction", "Device Restriction"
        MFA_REQUIREMENT = "mfa_requirement", "MFA Requirement"
        LOCATION = "location", "Location"

    class Operator(models.TextChoices):
        EQ = "eq", "Equals"
        NEQ = "neq", "Not Equals"
        IN = "in", "In"
        NOT_IN = "not_in", "Not In"
        GTE = "gte", "Greater Than or Equal"
        LTE = "lte", "Less Than or Equal"
        BETWEEN = "between", "Between"
        CIDR = "cidr", "CIDR Match"

    access_policy = models.ForeignKey(
        AccessPolicy,
        on_delete=models.CASCADE,
        related_name="conditions",
    )
    condition_type = models.CharField(max_length=30, choices=ConditionType.choices)
    operator = models.CharField(
        max_length=20,
        choices=Operator.choices,
        default=Operator.EQ,
    )
    value = models.JSONField(default=dict, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "policy_conditions"
        ordering = ["access_policy_id", "sort_order", "id"]

    def __str__(self):
        return f"{self.access_policy.key}: {self.condition_type}"


class PolicyAction(models.Model):
    """Resulting action row executed when all policy conditions match."""

    class ActionType(models.TextChoices):
        ALLOW = "allow", "Allow"
        DENY = "deny", "Deny"
        REQUIRE_MFA = "require_mfa", "Require MFA"
        REQUIRE_OFFICE_IP = "require_office_ip", "Require Office IP"
        REQUIRE_CORPORATE_DEVICE = "require_corporate_device", "Require Corporate Device"

    access_policy = models.ForeignKey(
        AccessPolicy,
        on_delete=models.CASCADE,
        related_name="policy_actions",
    )
    action_type = models.CharField(max_length=30, choices=ActionType.choices)
    parameters = models.JSONField(default=dict, blank=True)
    message = models.CharField(max_length=255, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "policy_actions"
        ordering = ["access_policy_id", "sort_order", "id"]

    def __str__(self):
        return f"{self.access_policy.key}: {self.action_type}"


# ---------------------------------------------------------------------------
# Security Settings (singleton per Organization)
# ---------------------------------------------------------------------------


class SecuritySettings(models.Model):
    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name="security_settings",
    )

    # Authentication
    mfa_enforced = models.BooleanField(default=False)
    password_min_length = models.PositiveSmallIntegerField(default=8)
    password_require_uppercase = models.BooleanField(default=True)
    password_require_lowercase = models.BooleanField(default=True)
    password_require_digits = models.BooleanField(default=True)
    password_require_special = models.BooleanField(default=False)
    session_timeout_minutes = models.PositiveIntegerField(default=30)

    # IP Restrictions
    ip_restriction_enabled = models.BooleanField(default=False)
    whitelisted_cidrs = models.JSONField(default=list, blank=True)
    geo_blocking_enabled = models.BooleanField(default=False)
    blocked_countries = models.JSONField(default=list, blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Security Settings"
        verbose_name_plural = "Security Settings"

    def __str__(self):
        return f"Security Settings — {self.organization.name}"


# ---------------------------------------------------------------------------
# System Preferences (singleton per Organization)
# ---------------------------------------------------------------------------


class SystemPreferences(models.Model):
    class ThemeMode(models.TextChoices):
        LIGHT = "light", "Light"
        DARK = "dark", "Dark"
        AUTO = "auto", "Auto"

    class DateFormat(models.TextChoices):
        DMY = "DD/MM/YYYY", "DD/MM/YYYY"
        MDY = "MM/DD/YYYY", "MM/DD/YYYY"
        YMD = "YYYY-MM-DD", "YYYY-MM-DD"

    class NumberFormat(models.TextChoices):
        COMMA_DOT = "1,234.56", "1,234.56"
        DOT_COMMA = "1.234,56", "1.234,56"

    class MeasurementUnit(models.TextChoices):
        SQM = "sqm", "Square Meters"
        SQFT = "sqft", "Square Feet"

    class CurrencyPosition(models.TextChoices):
        PREFIX = "prefix", "Prefix (symbol1,000)"
        SUFFIX = "suffix", "Suffix (1,000symbol)"

    LANDING_PAGE_CHOICES = [
        ("/", "Overview"),
        ("/properties", "Properties"),
        ("/projects", "Projects"),
        ("/finance", "Finance"),
        ("/procurement", "Procurement"),
        ("/analytics", "Analytics"),
    ]

    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name="system_preferences",
    )

    # Dashboard by Role — maps role slug → landing page path
    dashboard_by_role = models.JSONField(default=dict, blank=True)

    # Theme / Branding
    theme_mode = models.CharField(
        max_length=10,
        choices=ThemeMode.choices,
        default=ThemeMode.LIGHT,
    )
    accent_color = models.CharField(max_length=7, default="#171717")

    # Date & Number Format
    date_format = models.CharField(
        max_length=20,
        choices=DateFormat.choices,
        default=DateFormat.DMY,
    )
    number_format = models.CharField(
        max_length=20,
        choices=NumberFormat.choices,
        default=NumberFormat.COMMA_DOT,
    )

    # Measurement Units
    measurement_unit = models.CharField(
        max_length=5,
        choices=MeasurementUnit.choices,
        default=MeasurementUnit.SQM,
    )

    # Currency
    default_currency = models.CharField(
        max_length=3,
        default=get_default_currency_code,
    )
    currency_position = models.CharField(
        max_length=10,
        choices=CurrencyPosition.choices,
        default=CurrencyPosition.PREFIX,
    )
    currency_decimal_places = models.PositiveSmallIntegerField(default=2)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "System Preferences"
        verbose_name_plural = "System Preferences"

    def __str__(self):
        return f"System Preferences — {self.organization.name}"


# ---------------------------------------------------------------------------
# Audit & Compliance Settings (singleton per Organization)
# ---------------------------------------------------------------------------


class AuditComplianceSettings(models.Model):
    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name="audit_compliance_settings",
    )

    # 8.1 Audit Logging
    audit_logging_enabled = models.BooleanField(default=True)
    audit_retention_days = models.PositiveIntegerField(default=365)

    # 8.2 Compliance Controls
    mandatory_fields_enforced = models.BooleanField(default=False)
    financial_period_locking = models.BooleanField(default=False)
    locked_before_date = models.DateField(null=True, blank=True)
    change_approval_required = models.BooleanField(default=False)

    # 8.3 Data Access
    access_log_retention_days = models.PositiveIntegerField(default=90)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Audit & Compliance Settings"
        verbose_name_plural = "Audit & Compliance Settings"

    def __str__(self):
        return f"Audit & Compliance — {self.organization.name}"


# ---------------------------------------------------------------------------
# Notification & SLA Settings
# ---------------------------------------------------------------------------


class NotificationChannel(models.TextChoices):
    EMAIL = "email", "Email"
    IN_APP = "in_app", "In-App"
    SMS = "sms", "SMS"
    PUSH = "push", "Push Notification"


class SlaSeverityLevel(models.TextChoices):
    INFO = "info", "Info"
    REVIEW = "review", "Review"
    ACTION_REQUIRED = "action_required", "Action Required"
    ESCALATION = "escalation", "Escalation"


def default_sla_notification_channels():
    return [NotificationChannel.EMAIL, NotificationChannel.IN_APP]


def default_notification_category_overrides():
    """Default org-level category overrides — all enabled by default."""
    from apps.notifications.models import Notification

    return {
        choice[0]: {"enabled": True, "channels": ["in_app", "email"]}
        for choice in Notification.Category.choices
    }


class NotificationChannelSettings(models.Model):
    """Global channel switches and category overrides per organization."""

    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name="notification_channel_settings",
    )
    email_enabled = models.BooleanField(default=True)
    in_app_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=False)
    push_enabled = models.BooleanField(default=False)
    category_overrides = models.JSONField(
        default=default_notification_category_overrides,
        blank=True,
        help_text="Per-category org-level enable/disable and channel overrides.",
    )
    muted_event_keys = models.JSONField(
        default=list,
        blank=True,
        help_text="List of event_key strings to mute org-wide (e.g. 'project_cost_sync').",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Notification Channel Settings"
        verbose_name_plural = "Notification Channel Settings"

    def __str__(self):
        return f"Notification Channels — {self.organization.name}"


class SlaSeverityTier(models.Model):
    """
    Per-tier SLA controls that define response time, escalation path,
    and channels used for notification.
    """

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="sla_severity_tiers",
    )
    level = models.CharField(max_length=20, choices=SlaSeverityLevel.choices)
    sort_order = models.PositiveSmallIntegerField(default=0)
    response_time_hours = models.PositiveIntegerField(default=24)
    escalation_path = models.JSONField(
        default=list,
        blank=True,
        help_text="Role slugs, team aliases, or emails in escalation order.",
    )
    notification_channels = models.JSONField(
        default=default_sla_notification_channels,
        blank=True,
        help_text="List of channel keys: email, in_app, sms, push.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "level"]
        unique_together = [("organization", "level")]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="set_sla_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.get_level_display()} SLA — {self.organization.name}"


class NotificationTemplate(models.Model):
    """Template builder record for outbound/in-app notifications."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="notification_templates",
    )
    code = models.SlugField(max_length=120, blank=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    channel = models.CharField(max_length=20, choices=NotificationChannel.choices)
    event_key = models.CharField(
        max_length=120,
        help_text="Internal event key, e.g. workflow_pending or permit_expiry_30d.",
    )
    severity_tier = models.CharField(
        max_length=20,
        choices=SlaSeverityLevel.choices,
        default=SlaSeverityLevel.INFO,
    )
    subject = models.CharField(max_length=255, blank=True)
    body_text = models.TextField()
    body_html = models.TextField(blank=True)
    variables = models.JSONField(
        default=list,
        blank=True,
        help_text="Placeholder keys expected in template context.",
    )
    is_active = models.BooleanField(default=True)
    is_system = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["channel", "name"]
        unique_together = [("organization", "code")]
        indexes = [
            models.Index(fields=["organization", "channel", "event_key"]),
            models.Index(fields=["organization", "is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.channel})"

    def save(self, *args, **kwargs):
        if not self.code:
            base = slugify(self.name)[:90] or "template"
            self.code = base
        super().save(*args, **kwargs)


DOCUMENT_SIGNATURE_PROVIDER_CHOICES = [
    ("docusign", "DocuSign"),
    ("adobe_acrobat_sign", "Adobe Acrobat Sign"),
    ("dropbox_sign", "Dropbox Sign"),
    ("signnow", "SignNow"),
]

DOCUMENT_CONFIDENTIALITY_CHOICES = [
    ("public", "Public"),
    ("internal", "Internal"),
    ("confidential", "Confidential"),
    ("restricted", "Restricted"),
]


def default_document_signature_providers():
    return [choice[0] for choice in DOCUMENT_SIGNATURE_PROVIDER_CHOICES]


class DocumentAutomationSettings(models.Model):
    """
    Singleton config for document automation.
    Keep policy choices here so operational pages execute with defaults
    instead of exposing configuration fields to end users.
    """

    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name="document_automation_settings",
    )

    default_signature_provider = models.CharField(
        max_length=40,
        choices=DOCUMENT_SIGNATURE_PROVIDER_CHOICES,
        default="docusign",
    )
    enabled_signature_providers = models.JSONField(
        default=default_document_signature_providers,
        blank=True,
        help_text="Allowed provider keys for e-signature workflows.",
    )

    default_generation_owner_role = models.ForeignKey(
        "documents.DocumentOwnerRole",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="default_for_document_automation_settings",
    )
    default_generation_phase = models.ForeignKey(
        "documents.DocumentWorkflowPhase",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="default_for_document_automation_settings",
    )
    default_generation_retention_policy = models.ForeignKey(
        "documents.DocumentRetentionPolicy",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="default_for_document_automation_settings",
    )
    default_generation_confidentiality_level = models.CharField(
        max_length=20,
        choices=DOCUMENT_CONFIDENTIALITY_CHOICES,
        default="internal",
    )
    default_generation_template_code = models.CharField(max_length=120, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Document Automation Settings"
        verbose_name_plural = "Document Automation Settings"

    def __str__(self):
        return f"Document Automation — {self.organization.name}"


def ensure_default_document_automation_settings(organization):
    """
    Idempotent bootstrap for document automation defaults.
    """
    if organization is None:
        return None

    from django.apps import apps

    document_owner_role_model = apps.get_model("documents", "DocumentOwnerRole")
    document_phase_model = apps.get_model("documents", "DocumentWorkflowPhase")
    document_retention_policy_model = apps.get_model("documents", "DocumentRetentionPolicy")

    default_owner_role = document_owner_role_model.objects.filter(is_active=True).order_by("name").first()
    default_phase = document_phase_model.objects.filter(is_active=True).order_by("sort_order", "name").first()
    default_retention = document_retention_policy_model.objects.filter(is_active=True).order_by("name").first()

    settings_obj, _ = DocumentAutomationSettings.objects.get_or_create(
        organization=organization,
        defaults={
            "default_signature_provider": "docusign",
            "enabled_signature_providers": default_document_signature_providers(),
            "default_generation_owner_role": default_owner_role,
            "default_generation_phase": default_phase,
            "default_generation_retention_policy": default_retention,
            "default_generation_confidentiality_level": "internal",
            "default_generation_template_code": "",
        },
    )

    updated_fields: list[str] = []
    if settings_obj.default_generation_owner_role_id is None and default_owner_role:
        settings_obj.default_generation_owner_role = default_owner_role
        updated_fields.append("default_generation_owner_role")
    if settings_obj.default_generation_phase_id is None and default_phase:
        settings_obj.default_generation_phase = default_phase
        updated_fields.append("default_generation_phase")
    if settings_obj.default_generation_retention_policy_id is None and default_retention:
        settings_obj.default_generation_retention_policy = default_retention
        updated_fields.append("default_generation_retention_policy")
    if not settings_obj.enabled_signature_providers:
        settings_obj.enabled_signature_providers = default_document_signature_providers()
        updated_fields.append("enabled_signature_providers")
    if updated_fields:
        settings_obj.save(update_fields=[*updated_fields, "updated_at"])

    return settings_obj


def ensure_default_notification_settings(organization):
    """
    Idempotent bootstrap for notification channels and SLA tiers.
    Safe to call from views and migrations.
    """
    if organization is None:
        return

    NotificationChannelSettings.objects.get_or_create(
        organization=organization,
        defaults={
            "email_enabled": True,
            "in_app_enabled": True,
            "sms_enabled": False,
            "push_enabled": False,
        },
    )

    defaults = [
        {
            "level": SlaSeverityLevel.INFO,
            "sort_order": 10,
            "response_time_hours": 24,
            "escalation_path": ["team_lead"],
            "notification_channels": [NotificationChannel.IN_APP, NotificationChannel.EMAIL],
        },
        {
            "level": SlaSeverityLevel.REVIEW,
            "sort_order": 20,
            "response_time_hours": 8,
            "escalation_path": ["manager"],
            "notification_channels": [NotificationChannel.IN_APP, NotificationChannel.EMAIL],
        },
        {
            "level": SlaSeverityLevel.ACTION_REQUIRED,
            "sort_order": 30,
            "response_time_hours": 2,
            "escalation_path": ["manager", "operations_head"],
            "notification_channels": [
                NotificationChannel.IN_APP,
                NotificationChannel.EMAIL,
                NotificationChannel.PUSH,
            ],
        },
        {
            "level": SlaSeverityLevel.ESCALATION,
            "sort_order": 40,
            "response_time_hours": 1,
            "escalation_path": ["operations_head", "executive_team"],
            "notification_channels": [
                NotificationChannel.IN_APP,
                NotificationChannel.EMAIL,
                NotificationChannel.PUSH,
                NotificationChannel.SMS,
            ],
        },
    ]

    for tier in defaults:
        SlaSeverityTier.objects.get_or_create(
            organization=organization,
            level=tier["level"],
            defaults=tier,
        )


# ---------------------------------------------------------------------------
# Project Governance Settings
# ---------------------------------------------------------------------------


class ProjectGovernanceSettings(models.Model):
    """Singleton settings for project governance per organization."""

    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name="project_governance_settings",
    )

    # Default stage-gate enforcement
    stage_gate_enforcement_enabled = models.BooleanField(default=True)
    require_template_selection = models.BooleanField(default=True)
    risk_assessment_mandatory = models.BooleanField(default=True)

    # BOQ-driven planning automation
    auto_recalculate_on_boq_change = models.BooleanField(
        default=False,
        help_text="When a BOM is updated, automatically recalculate any linked blueprint's WBS, durations, and costs.",
    )
    allow_multi_boq_merge = models.BooleanField(
        default=False,
        help_text="Allow merging multiple BOMs (Structural + MEP + Architectural) into a single blueprint.",
    )

    # Project initiation automation (Group A)
    auto_create_project_on_approval = models.BooleanField(
        default=False,
        help_text="When a workflow approval for a project setup is completed, auto-create the project with budget shell, document repository, and milestone template.",
    )
    auto_lock_budget_on_approval = models.BooleanField(
        default=False,
        help_text="When a budget is approved, auto-lock it and distribute into construction, procurement, and contingency allocations.",
    )
    auto_provision_consultant_access = models.BooleanField(
        default=False,
        help_text="When a consultant engagement status changes to active, auto-assign roles and grant access to design and submittals.",
    )
    auto_activate_on_land_acquisition = models.BooleanField(
        default=False,
        help_text="When all land acquisitions for a project are marked complete, auto-activate the project status.",
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Project Governance Settings"
        verbose_name_plural = "Project Governance Settings"

    def __str__(self):
        return f"Project Governance — {self.organization.name}"


class ProjectTemplate(models.Model):
    """
    Real estate project templates that pre-define structure, phases,
    milestones, risk categories, and compliance checkpoints.
    """

    class TemplateType(models.TextChoices):
        RESIDENTIAL = "residential", "Residential"
        MIXED_USE = "mixed_use", "Mixed-Use"
        COMMERCIAL = "commercial", "Commercial"
        INFRASTRUCTURE = "infrastructure", "Infrastructure"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="project_templates",
        null=True,
        blank=True,
        help_text="NULL = global system template visible to all organisations.",
    )
    name = models.CharField(max_length=200)
    template_type = models.CharField(
        max_length=20,
        choices=TemplateType.choices,
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    is_system = models.BooleanField(
        default=False,
        help_text="System templates cannot be deleted",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["template_type", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                name="unique_org_template_name",
                condition=models.Q(organization__isnull=False),
            ),
            models.UniqueConstraint(
                fields=["name"],
                name="unique_global_template_name",
                condition=models.Q(organization__isnull=True),
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="set_ptpl_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.get_template_type_display()} — {self.name}"


class TemplatePhase(models.Model):
    """Pre-defined phase in a project template."""

    template = models.ForeignKey(
        ProjectTemplate,
        on_delete=models.CASCADE,
        related_name="phases",
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    duration_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Typical duration in days",
    )
    weight = models.PositiveIntegerField(
        default=1,
        help_text="Relative weight for progress calculation",
    )

    class Meta:
        ordering = ["sort_order"]
        verbose_name_plural = "template phases"

    def __str__(self):
        return f"{self.template.name} — {self.name}"


class TemplateMilestone(models.Model):
    """Pre-defined milestone in a template phase."""

    phase = models.ForeignKey(
        TemplatePhase,
        on_delete=models.CASCADE,
        related_name="milestones",
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    days_from_phase_start = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Typical days from phase start",
    )

    class Meta:
        ordering = ["sort_order"]

    def __str__(self):
        return self.name


class TemplateActivity(models.Model):
    """
    Activity layer in the WBS hierarchy: Phase → Activity → Task.

    Activities group related tasks within a phase (e.g., Phase=Foundation,
    Activity=Excavation contains tasks: Dig Trench, Soil Removal, etc.).
    """

    phase = models.ForeignKey(
        TemplatePhase,
        on_delete=models.CASCADE,
        related_name="activities",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    estimated_duration_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Estimated duration in calendar days",
    )
    estimated_effort_hours = models.DecimalField(
        max_digits=8,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="Total estimated effort in hours",
    )
    wbs_code = models.CharField(
        max_length=50,
        blank=True,
        help_text="WBS numbering (e.g., 1.2, 2.3) — auto-generated if blank",
    )

    class Meta:
        ordering = ["sort_order"]
        verbose_name_plural = "template activities"

    def __str__(self):
        return f"{self.phase.name} — {self.name}"


class TemplateDependency(models.Model):
    """
    Dependency relationship between two template activities or tasks.

    Defines the logical flow for the Dependency Graph Engine:
    FS (Finish-to-Start), SS (Start-to-Start), FF (Finish-to-Finish), SF (Start-to-Finish).
    """

    class DependencyType(models.TextChoices):
        FS = "fs", "Finish-to-Start"
        SS = "ss", "Start-to-Start"
        FF = "ff", "Finish-to-Finish"
        SF = "sf", "Start-to-Finish"

    class Strength(models.TextChoices):
        HARD = "hard", "Hard (Physical constraint)"
        SOFT = "soft", "Soft (Preferred sequence)"

    template = models.ForeignKey(
        ProjectTemplate,
        on_delete=models.CASCADE,
        related_name="dependencies",
    )

    # Source node (predecessor)
    from_activity = models.ForeignKey(
        TemplateActivity,
        on_delete=models.CASCADE,
        related_name="outgoing_dependencies",
        null=True,
        blank=True,
    )
    from_task = models.ForeignKey(
        "settings.TaskTemplate",
        on_delete=models.CASCADE,
        related_name="outgoing_dependencies",
        null=True,
        blank=True,
    )

    # Target node (successor)
    to_activity = models.ForeignKey(
        TemplateActivity,
        on_delete=models.CASCADE,
        related_name="incoming_dependencies",
        null=True,
        blank=True,
    )
    to_task = models.ForeignKey(
        "settings.TaskTemplate",
        on_delete=models.CASCADE,
        related_name="incoming_dependencies",
        null=True,
        blank=True,
    )

    dependency_type = models.CharField(
        max_length=2,
        choices=DependencyType.choices,
        default=DependencyType.FS,
    )
    lag_hours = models.DecimalField(
        max_digits=7,
        decimal_places=1,
        default=0,
        help_text="Positive = lag/delay, Negative = lead time.",
    )
    strength = models.CharField(
        max_length=4,
        choices=Strength.choices,
        default=Strength.HARD,
    )
    risk_impact = models.PositiveSmallIntegerField(
        default=5,
        help_text="1–10 scale of historical delay risk for this dependency.",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name_plural = "template dependencies"
        indexes = [
            models.Index(fields=["template", "from_activity"], name="tmpl_dep_from_act_idx"),
            models.Index(fields=["template", "to_activity"], name="tmpl_dep_to_act_idx"),
        ]

    @property
    def from_node_id(self):
        if self.from_task_id:
            return f"task-{self.from_task_id}"
        return f"act-{self.from_activity_id}"

    @property
    def to_node_id(self):
        if self.to_task_id:
            return f"task-{self.to_task_id}"
        return f"act-{self.to_activity_id}"

    def __str__(self):
        src = self.from_task or self.from_activity
        tgt = self.to_task or self.to_activity
        return f"{src} → {tgt} ({self.get_dependency_type_display()})"


def default_rainy_season_months():
    return [4, 5, 6, 7, 8, 9, 10]


def default_outdoor_task_categories():
    return ["civil", "finishing"]


def default_work_days():
    return {"mon": True, "tue": True, "wed": True, "thu": True, "fri": True, "sat": True, "sun": False}


def default_nigerian_holidays():
    return [
        {"name": "New Year", "month": 1, "day": 1},
        {"name": "Workers' Day", "month": 5, "day": 1},
        {"name": "Democracy Day", "month": 6, "day": 12},
        {"name": "Independence Day", "month": 10, "day": 1},
        {"name": "Christmas Day", "month": 12, "day": 25},
        {"name": "Boxing Day", "month": 12, "day": 26},
    ]


def default_resource_roles():
    return [
        {"role": "Site Engineer", "capacity": 1, "daily_rate": 25000},
        {"role": "Electrician", "capacity": 2, "daily_rate": 15000},
        {"role": "Mason", "capacity": 3, "daily_rate": 12000},
        {"role": "Labourer", "capacity": 5, "daily_rate": 5000},
    ]


class TemplateScheduleSettings(models.Model):
    """
    Calendar rules, work-day configuration, resource capacity, and buffer logic
    for the Scheduling Engine per project template.
    """

    template = models.OneToOneField(
        ProjectTemplate,
        on_delete=models.CASCADE,
        related_name="schedule_settings",
    )

    # Work week & shifts
    work_days = models.JSONField(
        default=default_work_days,
        help_text='{"mon":true,"tue":true,...,"sun":false}',
    )
    shift_start = models.TimeField(default="08:00")
    shift_end = models.TimeField(default="17:00")
    hours_per_day = models.DecimalField(max_digits=4, decimal_places=1, default=9)

    # Holidays
    public_holidays = models.JSONField(
        default=default_nigerian_holidays,
        help_text='[{"name","month","day"}]',
    )
    custom_holidays = models.JSONField(
        default=list,
        blank=True,
        help_text='[{"name","date":"YYYY-MM-DD"}]',
    )

    # Weather buffers
    rainy_season_buffer_enabled = models.BooleanField(default=False)
    rainy_season_buffer_pct = models.DecimalField(
        max_digits=5, decimal_places=1, default=15,
        help_text="% buffer added to outdoor tasks during rainy months.",
    )
    rainy_season_months = models.JSONField(
        default=default_rainy_season_months,
        help_text="Month numbers (1-12) considered rainy season.",
    )
    outdoor_task_categories = models.JSONField(
        default=default_outdoor_task_categories,
        help_text="Task categories affected by weather buffers.",
    )

    # Resource roles & capacity
    resource_roles = models.JSONField(
        default=default_resource_roles,
        help_text='[{"role","capacity","daily_rate"}]',
    )
    travel_buffer_hours = models.DecimalField(
        max_digits=5, decimal_places=1, default=0,
        help_text="Hours added for crew mobilization between sites.",
    )

    # Duration scaling
    duration_scalar_pct = models.DecimalField(
        max_digits=5, decimal_places=1, default=100,
        help_text="100 = normal. 90 = 10%% faster. 110 = 10%% slower.",
    )

    # Milestone anchors
    milestone_anchors = models.JSONField(
        default=list,
        blank=True,
        help_text='[{"task_id","anchor_day","label"}]',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Template Schedule Settings"
        verbose_name_plural = "Template Schedule Settings"

    def __str__(self):
        return f"Schedule Settings — {self.template.name}"

    @property
    def work_days_per_week(self):
        return sum(1 for v in (self.work_days or {}).values() if v)


class TemplatePlanScenario(models.Model):
    """
    A saved scenario snapshot for what-if analysis.
    Each scenario captures a set of assumptions (duration scalar, markup,
    location factor, contingency) and the resulting cost/schedule projections.
    """

    class RiskLevel(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    template = models.ForeignKey(
        ProjectTemplate,
        on_delete=models.CASCADE,
        related_name="plan_scenarios",
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_baseline = models.BooleanField(
        default=False,
        help_text="The officially committed plan baseline.",
    )

    # Assumptions
    duration_scalar_pct = models.DecimalField(max_digits=5, decimal_places=1, default=100)
    material_markup_pct = models.DecimalField(max_digits=5, decimal_places=1, default=10)
    location_factor = models.CharField(max_length=30, default="lagos")
    contingency_pct = models.DecimalField(max_digits=5, decimal_places=1, default=10)
    equipment_daily_rate = models.DecimalField(max_digits=12, decimal_places=2, default=50000)
    fx_rate_usd_ngn = models.DecimalField(max_digits=10, decimal_places=2, default=1550)
    risk_level = models.CharField(max_length=10, choices=RiskLevel.choices, default=RiskLevel.MEDIUM)

    # Projected results (computed on save)
    projected_duration_days = models.PositiveIntegerField(default=0)
    projected_material_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    projected_labor_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    projected_equipment_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    projected_contingency = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    projected_total_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # Sensitivity
    sensitivity_fx_10pct_impact = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text="Cost impact of 10% FX increase.")
    sensitivity_material_10pct_impact = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text="Cost impact of 10% material price increase.")

    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="created_plan_scenarios",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_baseline", "-created_at"]
        indexes = [
            models.Index(fields=["template", "-created_at"], name="tmpl_scenario_tmpl_idx"),
        ]

    def __str__(self):
        baseline = " [BASELINE]" if self.is_baseline else ""
        return f"{self.template.name} — {self.name}{baseline}"


class TemplateRequiredDocument(models.Model):
    """Required document type for a template phase."""

    class DocumentCategory(models.TextChoices):
        PERMIT = "permit", "Permit/Approval"
        CONTRACT = "contract", "Contract"
        PLAN = "plan", "Plan/Drawing"
        REPORT = "report", "Report/Assessment"
        CERTIFICATE = "certificate", "Certificate"
        OTHER = "other", "Other"

    phase = models.ForeignKey(
        TemplatePhase,
        on_delete=models.CASCADE,
        related_name="required_documents",
    )
    name = models.CharField(max_length=200)
    category = models.CharField(
        max_length=20,
        choices=DocumentCategory.choices,
        default=DocumentCategory.OTHER,
    )
    description = models.TextField(blank=True)
    is_mandatory = models.BooleanField(default=True)

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return f"{self.name} ({'Required' if self.is_mandatory else 'Optional'})"


class TemplateComplianceCheckpoint(models.Model):
    """Compliance checkpoint for a template phase."""

    phase = models.ForeignKey(
        TemplatePhase,
        on_delete=models.CASCADE,
        related_name="compliance_checkpoints",
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    regulatory_reference = models.CharField(max_length=200, blank=True)
    is_mandatory = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class StageGateRule(models.Model):
    """
    Stage-gate approval rules for project phases.
    Defines what must be completed before moving to next stage.
    """

    class Stage(models.TextChoices):
        FEASIBILITY = "feasibility", "Feasibility"
        DESIGN = "design", "Design"
        PRE_SALES = "pre_sales", "Pre-Sales"
        CONSTRUCTION_START = "construction_start", "Construction Start"
        HANDOVER = "handover", "Handover"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="stage_gate_rules",
    )
    stage = models.CharField(max_length=30, choices=Stage.choices)
    template = models.ForeignKey(
        ProjectTemplate,
        on_delete=models.CASCADE,
        related_name="stage_gate_rules",
        null=True,
        blank=True,
        help_text="If null, applies to all projects",
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["stage", "name"]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="set_sgr_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.get_stage_display()} — {self.name}"


class StageGateChecklistItem(models.Model):
    """Individual checklist item for a stage gate rule."""

    rule = models.ForeignKey(
        StageGateRule,
        on_delete=models.CASCADE,
        related_name="checklist_items",
    )
    item = models.CharField(max_length=300)
    is_mandatory = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order"]

    def __str__(self):
        return self.item


class RiskCategory(models.Model):
    """Risk categories for project risk assessment."""

    class CategoryType(models.TextChoices):
        FINANCIAL = "financial", "Financial"
        REGULATORY = "regulatory", "Regulatory"
        CONSTRUCTION = "construction", "Construction"
        MARKET = "market", "Market"
        OPERATIONAL = "operational", "Operational"
        ENVIRONMENTAL = "environmental", "Environmental"
        LEGAL = "legal", "Legal"
        TECHNICAL = "technical", "Technical"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="risk_categories",
    )
    name = models.CharField(max_length=200)
    category_type = models.CharField(
        max_length=20,
        choices=CategoryType.choices,
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category_type", "name"]
        verbose_name_plural = "risk categories"
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="set_rcat_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.get_category_type_display()} — {self.name}"


class RiskScoreMatrix(models.Model):
    """
    Risk scoring matrix configuration.
    Defines how likelihood × impact = risk score.
    """

    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name="risk_score_matrix",
    )

    # Matrix configuration (stored as JSON)
    # Example structure:
    # {
    #   "likelihood": {"very_low": 1, "low": 2, "medium": 3, "high": 4, "very_high": 5},
    #   "impact": {"very_low": 1, "low": 2, "medium": 3, "high": 4, "very_high": 5},
    #   "thresholds": {"low": 5, "medium": 10, "high": 15, "critical": 20}
    # }
    matrix_config = models.JSONField(
        default=dict,
        help_text="Likelihood, impact, and threshold configuration",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Risk Score Matrix"
        verbose_name_plural = "Risk Score Matrices"

    def __str__(self):
        return f"Risk Matrix — {self.organization.name}"


class RiskMitigationRule(models.Model):
    """
    Auto-assignment rules for risk mitigation based on risk category
    and severity.
    """

    class Severity(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="risk_mitigation_rules",
    )
    risk_category = models.ForeignKey(
        RiskCategory,
        on_delete=models.CASCADE,
        related_name="mitigation_rules",
    )
    severity = models.CharField(max_length=20, choices=Severity.choices)
    assign_to_role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="risk_mitigation_assignments",
    )
    escalation_required = models.BooleanField(default=False)
    response_time_hours = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Required response time in hours",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["severity", "risk_category"]
        unique_together = [("organization", "risk_category", "severity")]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="set_rmr_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.risk_category.name} ({self.get_severity_display()})"


# ---------------------------------------------------------------------------
# Master Data Management
# ---------------------------------------------------------------------------

class MasterDataEntry(models.Model):
    """Generic lookup / reference data entry for centralized master data management."""

    class Category(models.TextChoices):
        # Identity & Access
        IDENTITY_TYPE = "identity_type", "Identity Type"
        PARTNER_TYPE = "partner_type", "Partner Type"
        # People & Organizations
        VENDOR_TYPE = "vendor_type", "Vendor Type"
        CLIENT_TYPE = "client_type", "Client / Buyer Type"
        CONSULTANT_SPECIALIZATION = "consultant_specialization", "Consultant Specialization"
        CONTRACTOR_CLASSIFICATION = "contractor_classification", "Contractor Classification"
        INVESTOR_TYPE = "investor_type", "Investor Type"
        # Property & Assets
        PROPERTY_TYPE = "property_type", "Property Type"
        PROPERTY_CLASSIFICATION = "property_classification", "Property Classification"
        UNIT_TYPOLOGY = "unit_typology", "Unit Typology"
        ASSET_CATEGORY = "asset_category", "Asset Category"
        OWNERSHIP_STRUCTURE = "ownership_structure", "Ownership Structure"
        # Maintenance & Operations
        MAINTENANCE_CATEGORY = "maintenance_category", "Maintenance Category"
        INSPECTION_TYPE = "inspection_type", "Inspection Type"
        # Finance & Costs
        COST_CODE = "cost_code", "Cost Code"
        MATERIAL_CATEGORY = "material_category", "Material Category"
        PAYMENT_METHOD = "payment_method", "Payment Method"
        CURRENCY = "currency", "Currency"
        # Compliance & Risk
        RISK_CATEGORY = "risk_category", "Risk Category"
        ISSUE_CATEGORY = "issue_category", "Issue Category"
        COMPLIANCE_CATEGORY = "compliance_category", "Compliance Category"
        # Projects
        PROJECT_TYPE = "project_type", "Project Type"
        LAND_STATUS = "land_status", "Land Status"
        # Documents
        DOCUMENT_TYPE = "document_type", "Document Type"
        # CRM & Communications
        LEAD_TYPE = "lead_type", "Lead Type"
        LEAD_ARCHIVED_REASON = "lead_archived_reason", "Lead Archived Reason"
        COMMUNICATION_CHANNEL = "communication_channel", "Communication Channel"
        CAMPAIGN_TYPE = "campaign_type", "Campaign Type"
        CALL_DISPOSITION = "call_disposition", "Call Disposition"
        MEETING_TYPE = "meeting_type", "Meeting Type"
        FOLLOW_UP_REASON = "follow_up_reason", "Follow-Up Reason"
        LEAD_SOURCE_CHANNEL = "lead_source_channel", "Lead Source Channel"
        COMMISSION_TYPE = "commission_type", "Commission Type"
        COMMISSION_TRIGGER = "commission_trigger", "Commission Trigger Stage"
        # Finance — Extended
        SPV_ENTITY_TYPE = "spv_entity_type", "SPV Entity Type"
        PAYMENT_PLAN_TYPE = "payment_plan_type", "Payment Plan Type"
        PAYMENT_FREQUENCY = "payment_frequency", "Payment Frequency"
        BUDGET_PERIOD = "budget_period", "Budget Period"
        # HR
        EMPLOYMENT_TYPE = "employment_type", "Employment Type"
        POSITION_LEVEL = "position_level", "Position Level"
        # HR — Employee Directory
        EMERGENCY_CONTACT_RELATIONSHIP = "emergency_contact_relationship", "Emergency Contact Relationship"
        ID_DOCUMENT_TYPE = "id_document_type", "Identification Document Type"
        HR_DOCUMENT_CATEGORY = "hr_document_category", "HR Document Category"
        COMPENSATION_PAY_FREQUENCY = "compensation_pay_frequency", "Compensation Pay Frequency"
        EMPLOYMENT_STATUS = "employment_status", "Employment Status"
        CONTRACT_TYPE = "contract_type", "Contract Type"
        # HR — Recruitment
        REQUISITION_TYPE = "requisition_type", "Requisition Type"
        CANDIDATE_SOURCE = "candidate_source", "Candidate Source"
        INTERVIEW_TYPE = "interview_type", "Interview Type"
        REJECTION_REASON = "rejection_reason", "Rejection Reason"
        # System
        STATUS_BADGE = "status_badge", "Status Badge"

    category = models.CharField(
        max_length=40, choices=Category.choices, db_index=True
    )
    code = models.CharField(max_length=50)
    label = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_system = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("category", "code")]
        ordering = ["category", "sort_order", "label"]
        verbose_name_plural = "Master data entries"

    def __str__(self):
        return f"[{self.get_category_display()}] {self.code} — {self.label}"


# ---------------------------------------------------------------------------
# Module Activation & Feature Flags
# ---------------------------------------------------------------------------


class ModuleActivationSettings(models.Model):
    """Singleton per organization — controls which platform modules are enabled."""

    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name="module_activation_settings",
    )
    enabled_modules = models.JSONField(
        default=list,
        help_text="List of Module enum values that are currently active.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Module activation settings"
        verbose_name_plural = "Module activation settings"

    def __str__(self):
        return f"Module Activation — {self.organization.name}"

    def get_available_modules(self) -> set[str]:
        """Modules the org's tier allows."""
        tier = self.organization.subscription_tier
        return TIER_MODULE_MAP.get(tier, set())

    def get_enabled_modules(self) -> set[str]:
        """Modules that are both tier-allowed AND admin-enabled, plus settings, plus add-on modules."""
        available = self.get_available_modules()
        enabled = set(self.enabled_modules) & available
        enabled.add(Module.SETTINGS)
        # Include modules from active subscription add-ons
        try:
            sub = self.organization.subscription
            addon_modules = (
                sub.active_add_ons
                .filter(add_on__add_on_type="module")
                .exclude(add_on__module_key="")
                .values_list("add_on__module_key", flat=True)
            )
            enabled.update(addon_modules)
        except Exception:
            pass
        return enabled

    def is_module_enabled(self, module_key: str) -> bool:
        if module_key == Module.SETTINGS:
            return True
        return module_key in self.get_enabled_modules()


class FeatureFlagDefinition(models.Model):
    """
    Platform-wide feature flag definition. Created by developers/ops.
    Not org-scoped — these are global flag definitions.
    """

    class FlagType(models.TextChoices):
        BOOLEAN = "boolean", "Boolean (on/off)"
        PERCENTAGE = "percentage", "Percentage Rollout"

    class FlagScope(models.TextChoices):
        GLOBAL = "global", "Global (all orgs)"
        ORG = "org", "Per Organization"
        PROJECT = "project", "Per Project"
        REGION = "region", "Per Region"

    key = models.SlugField(max_length=120, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    module = models.CharField(
        max_length=30,
        choices=Module.choices,
        blank=True,
        help_text="Module this flag applies to. Blank = platform-wide.",
    )
    flag_type = models.CharField(
        max_length=20,
        choices=FlagType.choices,
        default=FlagType.BOOLEAN,
    )
    scope = models.CharField(
        max_length=20,
        choices=FlagScope.choices,
        default=FlagScope.ORG,
    )
    default_enabled = models.BooleanField(default=False)
    rollout_percentage = models.PositiveSmallIntegerField(
        default=0,
        help_text="For percentage flags: 0-100. Ignored for boolean flags.",
    )
    minimum_tier = models.CharField(
        max_length=20,
        choices=Organization.SubscriptionTier.choices,
        default=Organization.SubscriptionTier.ESSENTIALS,
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Master kill switch. If False, flag is off for everyone.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["module", "key"]
        verbose_name = "Feature flag definition"

    def __str__(self):
        return f"{self.key} ({self.get_scope_display()})"


class FeatureFlagOverride(models.Model):
    """Per-organization override for a feature flag."""

    flag = models.ForeignKey(
        FeatureFlagDefinition,
        on_delete=models.CASCADE,
        related_name="overrides",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="feature_flag_overrides",
    )
    enabled = models.BooleanField(default=True)
    scoped_project_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="List of Project IDs this flag applies to. Empty = all projects.",
    )
    scoped_regions = models.JSONField(
        default=list,
        blank=True,
        help_text="List of region/country codes. Empty = all regions.",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("flag", "organization")]
        ordering = ["flag__module", "flag__key"]

    def __str__(self):
        status = "ON" if self.enabled else "OFF"
        return f"{self.flag.key} → {self.organization.name} [{status}]"


# ---------------------------------------------------------------------------
# Platform Edition — purchasable plan definitions
# ---------------------------------------------------------------------------


class PlatformEdition(models.Model):
    """
    DB-backed plan definition. One row per purchasable edition
    (Essentials, Growth, Scale, Custom).
    """

    class SupportTier(models.TextChoices):
        COMMUNITY = "community", "Community"
        STANDARD = "standard", "Standard"
        PRIORITY = "priority", "Priority"
        DEDICATED = "dedicated", "Dedicated"

    key = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=100)
    tier_level = models.PositiveSmallIntegerField(
        help_text="Ordering: 0 = Essentials, 1 = Growth, 2 = Scale, 3 = Custom",
    )
    is_custom = models.BooleanField(default=False)
    description = models.TextField(blank=True)

    # Module access
    included_modules = models.JSONField(
        default=list,
        help_text="List of Module enum values included in this edition.",
    )

    # Quotas
    max_users = models.PositiveIntegerField(
        null=True, blank=True, help_text="null = unlimited"
    )
    max_storage_gb = models.PositiveIntegerField(
        null=True, blank=True, help_text="null = unlimited"
    )
    api_rate_limit_rpm = models.PositiveIntegerField(
        null=True, blank=True, help_text="Requests per minute; null = unlimited"
    )
    data_retention_days = models.PositiveIntegerField(
        null=True, blank=True, help_text="null = unlimited"
    )
    max_projects = models.PositiveIntegerField(
        null=True, blank=True, help_text="null = unlimited"
    )
    max_properties = models.PositiveIntegerField(
        null=True, blank=True, help_text="null = unlimited"
    )
    max_entity_maps = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Max entities with map views; null = unlimited",
    )

    # Support SLA
    support_tier = models.CharField(
        max_length=20,
        choices=SupportTier.choices,
        default=SupportTier.COMMUNITY,
    )
    support_response_hours = models.PositiveIntegerField(
        null=True, blank=True, help_text="SLA: first response time in hours"
    )
    support_resolution_hours = models.PositiveIntegerField(
        null=True, blank=True, help_text="SLA: resolution target in hours"
    )

    # Pricing (flat rate)
    monthly_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="null for custom (negotiated)",
    )
    annual_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="null for custom (negotiated)",
    )
    currency = models.CharField(max_length=3, default="USD")

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["tier_level"]
        verbose_name = "Platform edition"

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# Subscription Add-Ons (à la carte module / storage purchases)
# ---------------------------------------------------------------------------


class SubscriptionAddOn(models.Model):
    """
    Product catalog entry for purchasable add-ons.
    Two types: module (enables a platform module) and storage (extra GB).
    """

    class AddOnType(models.TextChoices):
        MODULE = "module", "Module"
        STORAGE = "storage", "Storage"

    key = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    add_on_type = models.CharField(max_length=20, choices=AddOnType.choices)
    module_key = models.CharField(
        max_length=50, blank=True,
        help_text="Module enum value to enable (for module add-ons)",
    )
    storage_gb = models.PositiveIntegerField(
        default=0,
        help_text="Extra GB to add (for storage add-ons)",
    )
    monthly_price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "Subscription add-on"

    def __str__(self):
        return f"{self.name} (${self.monthly_price}/mo)"


# ---------------------------------------------------------------------------
# Standalone Entity Templates (for Add Phase / Milestone / Task pickers)
# ---------------------------------------------------------------------------


class PhaseTemplate(models.Model):
    """Reusable phase template shown in the Add Phase form."""

    # --- Existing fields ---
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    weight = models.PositiveIntegerField(default=1)
    budget_pct = models.DecimalField(max_digits=4, decimal_places=2, default=0)

    # --- Section A: Phase Overview & Metadata ---
    objective = models.TextField(blank=True, help_text="Primary objective or goal of this phase.")
    estimated_duration_days = models.PositiveIntegerField(null=True, blank=True, help_text="Typical duration in calendar days.")
    phase_owner_role = models.CharField(max_length=200, blank=True, help_text="Suggested role for the phase owner.")

    # --- Section B: Governance & Stakeholders ---
    raci_matrix = models.JSONField(default=list, blank=True, help_text='[{"task","responsible","accountable","consulted","informed"}]')
    approval_authority = models.TextField(blank=True, help_text="Who has final approval authority for this phase.")

    # --- Section C: Scope & Deliverables ---
    key_tasks = models.JSONField(default=list, blank=True, help_text='[{"name","description"}]')
    deliverables = models.JSONField(default=list, blank=True, help_text='[{"name","description","is_mandatory"}]')
    out_of_scope = models.TextField(blank=True, help_text="Items explicitly excluded from this phase.")

    # --- Section D: Resource & Risk Management ---
    resource_requirements = models.JSONField(default=list, blank=True, help_text='[{"type","description","quantity"}]')
    phase_risks = models.JSONField(default=list, blank=True, help_text='[{"risk","likelihood","impact","mitigation"}]')
    budget_notes = models.TextField(blank=True, help_text="Additional notes on budget allocation.")

    # --- Section E: Quality & Completion Criteria ---
    success_metrics = models.JSONField(default=list, blank=True, help_text='[{"metric","target","measurement_method"}]')
    exit_criteria = models.JSONField(default=list, blank=True, help_text='[{"criterion","verification_method"}]')
    lessons_learned_prompt = models.TextField(blank=True, help_text="Guiding questions for lessons-learned capture.")

    class Meta:
        ordering = ["sort_order"]

    def __str__(self):
        return self.name


class MilestoneTemplate(models.Model):
    """Reusable milestone template shown in the Add Milestone form."""

    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    phase_sort_order = models.PositiveIntegerField(
        default=0,
        help_text="Suggested phase sort_order this milestone belongs to.",
    )

    # --- Section A: Milestone Identification ---
    reference_code = models.CharField(max_length=100, blank=True, help_text="Default milestone ID/code, e.g. MS-001.")

    # --- Section B: Scheduling & Status ---
    typical_offset_days = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Typical number of days from phase start to this milestone.",
    )

    # --- Section C: Completion Requirements ---
    success_criteria = models.JSONField(default=list, blank=True, help_text='[{"criterion","verification_method"}]')
    key_deliverables = models.JSONField(default=list, blank=True, help_text='[{"name","description","is_mandatory"}]')
    predecessors = models.JSONField(default=list, blank=True, help_text='[{"milestone","dependency_type","lag_days"}]')
    successors = models.JSONField(default=list, blank=True, help_text='[{"milestone","dependency_type","lag_days"}]')

    # --- Section D: Accountability & Approval ---
    owner_role = models.CharField(max_length=200, blank=True, help_text="Default role responsible for this milestone.")
    approver_role = models.CharField(max_length=200, blank=True, help_text="Default role that approves this milestone.")
    stakeholders_to_notify = models.JSONField(default=list, blank=True, help_text='[{"role","notification_trigger"}]')

    class Meta:
        ordering = ["sort_order"]

    def __str__(self):
        return self.name


class TaskTemplate(models.Model):
    """Reusable task template shown in the Add Task form."""

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    activity = models.ForeignKey(
        "settings.TemplateActivity",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="task_templates",
        help_text="WBS activity this task belongs to.",
    )
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    assigned_role = models.CharField(max_length=200, blank=True)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    sort_order = models.PositiveIntegerField(default=0)
    phase_sort_order = models.PositiveIntegerField(
        default=0,
        help_text="Suggested phase sort_order this task belongs to.",
    )

    # --- Section A: Task Definition & Context ---
    reference_code = models.CharField(max_length=100, blank=True, help_text="Default task ID, e.g. TASK-101.")

    # --- Section B: Assignment & Ownership ---
    reviewer_role = models.CharField(max_length=200, blank=True, help_text="Role that reviews/approves the task output.")
    collaborators = models.JSONField(default=list, blank=True, help_text='[{"role","responsibility"}]')

    # --- Section C: Scheduling & Effort ---
    standard_duration_hours = models.DecimalField(max_digits=7, decimal_places=1, null=True, blank=True, help_text="Standard duration in hours.")
    estimated_effort_hours = models.DecimalField(max_digits=7, decimal_places=1, null=True, blank=True, help_text="Expected effort in man-hours.")
    complexity = models.CharField(
        max_length=10,
        choices=[("low", "Low"), ("medium", "Medium"), ("high", "High")],
        default="medium",
    )
    category = models.CharField(
        max_length=50,
        blank=True,
        help_text="Task category: electrical, civil, logistics, legal_permits, mechanical, finishing, etc.",
    )
    crew_size = models.PositiveIntegerField(null=True, blank=True, help_text="Recommended crew size.")
    estimated_labor_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Base labor cost estimate.")
    output_unit = models.CharField(max_length=50, blank=True, help_text="Unit of measure for progress: m², m³, linear m, units, kg.")
    production_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Output per day in output_unit. E.g. 10 m³/day for concrete pouring.")
    equipment_type = models.CharField(max_length=255, blank=True, help_text="Required equipment types, comma-separated.")
    is_milestone = models.BooleanField(default=False, help_text="Mark as a project milestone checkpoint.")
    status = models.CharField(
        max_length=10,
        choices=[("draft", "Draft"), ("active", "Active"), ("archived", "Archived")],
        default="active",
    )

    # --- Section D: Execution Details ---
    predecessors = models.JSONField(default=list, blank=True, help_text='[{"task","dependency_type","lag_days"}]')
    successors = models.JSONField(default=list, blank=True, help_text='[{"task","dependency_type","lag_days"}]')
    definition_of_done = models.JSONField(default=list, blank=True, help_text='[{"criterion","is_required"}]')

    # --- Section E: Resources & Attachments ---
    tools_required = models.JSONField(default=list, blank=True, help_text='[{"name","description"}]')
    reference_links = models.JSONField(default=list, blank=True, help_text='[{"title","url"}]')
    required_materials = models.JSONField(default=list, blank=True, help_text='[{"item","quantity","unit","essential"}]')
    required_ppe = models.JSONField(default=list, blank=True, help_text='["Hard Hat","Insulated Gloves",...]')
    quality_gates = models.JSONField(default=list, blank=True, help_text='[{"check","is_required"}]')
    photo_requirements = models.JSONField(default=list, blank=True, help_text='[{"description","is_mandatory"}]')
    sop_markdown = models.TextField(blank=True, help_text="Markdown-supported standard operating procedure.")

    class Meta:
        ordering = ["sort_order"]

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# Backup & Disaster Recovery Settings (singleton per Organization)
# ---------------------------------------------------------------------------


class BackupDisasterRecoverySettings(models.Model):
    """Backup configuration, recovery objectives, failover triggers, and restore testing."""

    class BackupFrequency(models.TextChoices):
        HOURLY = "hourly", "Hourly"
        EVERY_6H = "every_6h", "Every 6 Hours"
        EVERY_12H = "every_12h", "Every 12 Hours"
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"

    class BackupRegion(models.TextChoices):
        US_EAST = "us-east-1", "US East (N. Virginia)"
        US_WEST = "us-west-2", "US West (Oregon)"
        EU_WEST = "eu-west-1", "EU West (Ireland)"
        EU_CENTRAL = "eu-central-1", "EU Central (Frankfurt)"
        AP_SOUTHEAST = "ap-southeast-1", "Asia Pacific (Singapore)"
        AF_SOUTH = "af-south-1", "Africa (Cape Town)"
        ME_SOUTH = "me-south-1", "Middle East (Bahrain)"

    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name="backup_dr_settings",
    )

    # Backup configuration
    backup_frequency = models.CharField(
        max_length=20,
        choices=BackupFrequency.choices,
        default=BackupFrequency.DAILY,
    )
    backup_region = models.CharField(
        max_length=30,
        choices=BackupRegion.choices,
        default=BackupRegion.US_EAST,
    )

    # Recovery objectives (stored in minutes)
    rto_minutes = models.PositiveIntegerField(
        default=240,
        help_text="Recovery Time Objective in minutes",
    )
    rpo_minutes = models.PositiveIntegerField(
        default=60,
        help_text="Recovery Point Objective in minutes",
    )

    # Failover trigger conditions
    failover_on_db_failure = models.BooleanField(default=True)
    failover_on_network_outage = models.BooleanField(default=True)
    failover_on_storage_failure = models.BooleanField(default=True)
    failover_on_app_crash = models.BooleanField(default=False)
    failover_on_manual_trigger = models.BooleanField(default=True)

    # Restore testing logs (structured JSON array)
    restore_test_logs = models.JSONField(
        default=list,
        blank=True,
        help_text="Array of restore test entries: [{date, status, duration_seconds, notes}]",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Backup & Disaster Recovery Settings"
        verbose_name_plural = "Backup & Disaster Recovery Settings"

    def __str__(self):
        return f"Backup & DR — {self.organization.name}"


# ---------------------------------------------------------------------------
# Integration Governance Settings (singleton per Organization)
# ---------------------------------------------------------------------------


class IntegrationGovernanceSettings(models.Model):
    """Data sync, conflict resolution, source-of-truth, error routing, SLA monitoring, and version compatibility."""

    class SyncFrequency(models.TextChoices):
        REAL_TIME = "real_time", "Real-Time"
        EVERY_5M = "every_5m", "Every 5 Minutes"
        EVERY_15M = "every_15m", "Every 15 Minutes"
        EVERY_30M = "every_30m", "Every 30 Minutes"
        HOURLY = "hourly", "Hourly"
        EVERY_6H = "every_6h", "Every 6 Hours"
        DAILY = "daily", "Daily"

    class ConflictResolution(models.TextChoices):
        SOURCE_WINS = "source_wins", "Source System Wins"
        TARGET_WINS = "target_wins", "Target System Wins"
        MOST_RECENT = "most_recent", "Most Recent Timestamp Wins"
        MANUAL_REVIEW = "manual_review", "Queue for Manual Review"

    class SourceOfTruth(models.TextChoices):
        ERP = "erp", "ERP System"
        CRM = "crm", "CRM Platform"
        PROPERTY_MGMT = "property_management", "Property Management System"
        FINANCE = "finance_system", "Finance & Accounting"
        PROJECT_MGMT = "project_management", "Project Management"
        CUSTOM = "custom", "Custom / External"

    class ErrorSeverity(models.TextChoices):
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        ERROR = "error", "Error"
        CRITICAL = "critical", "Critical"

    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name="integration_governance_settings",
    )

    # Data Sync Configuration
    default_sync_frequency = models.CharField(
        max_length=20,
        choices=SyncFrequency.choices,
        default=SyncFrequency.HOURLY,
    )
    sync_retry_attempts = models.PositiveIntegerField(
        default=3,
        help_text="Number of retry attempts on sync failure",
    )
    sync_retry_delay_seconds = models.PositiveIntegerField(
        default=60,
        help_text="Delay between retry attempts in seconds",
    )
    sync_enabled = models.BooleanField(default=True)

    # Conflict Resolution
    conflict_resolution_strategy = models.CharField(
        max_length=20,
        choices=ConflictResolution.choices,
        default=ConflictResolution.SOURCE_WINS,
    )
    conflict_auto_resolve = models.BooleanField(
        default=True,
        help_text="Automatically resolve conflicts using the selected strategy",
    )
    conflict_notify_on_resolution = models.BooleanField(
        default=True,
        help_text="Send notifications when conflicts are resolved",
    )
    conflict_escalation_after_hours = models.PositiveIntegerField(
        default=24,
        help_text="Escalate unresolved conflicts after this many hours",
    )

    # Source of Truth Designation
    primary_source_of_truth = models.CharField(
        max_length=30,
        choices=SourceOfTruth.choices,
        default=SourceOfTruth.ERP,
    )
    source_override_allowed = models.BooleanField(
        default=False,
        help_text="Allow downstream systems to override source-of-truth data",
    )

    # Error Log Routing
    error_routing_email = models.BooleanField(default=True)
    error_routing_webhook = models.BooleanField(default=False)
    error_routing_in_app = models.BooleanField(default=True)
    error_routing_syslog = models.BooleanField(default=False)
    error_webhook_url = models.CharField(max_length=500, blank=True)
    error_email_recipients = models.JSONField(
        default=list,
        blank=True,
        help_text="List of email addresses for error notifications",
    )
    error_severity_threshold = models.CharField(
        max_length=10,
        choices=ErrorSeverity.choices,
        default=ErrorSeverity.WARNING,
    )

    # Integration SLA Monitoring
    sla_target_uptime_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=99.9,
        help_text="Target uptime percentage (e.g. 99.9)",
    )
    sla_max_response_time_ms = models.PositiveIntegerField(
        default=5000,
        help_text="Maximum acceptable API response time in milliseconds",
    )
    sla_max_sync_latency_seconds = models.PositiveIntegerField(
        default=300,
        help_text="Maximum acceptable sync latency in seconds",
    )
    sla_alert_on_breach = models.BooleanField(
        default=True,
        help_text="Send alerts when SLA thresholds are breached",
    )

    # Version Compatibility Tracking (read-only, populated by system)
    version_compatibility_log = models.JSONField(
        default=list,
        blank=True,
        help_text="Array of integration version entries: [{integration_name, current_version, min_compatible_version, status, last_checked}]",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Integration Governance Settings"
        verbose_name_plural = "Integration Governance Settings"

    def __str__(self):
        return f"Integration Governance — {self.organization.name}"


# ---------------------------------------------------------------------------
# KPI & Performance Configuration
# ---------------------------------------------------------------------------


class KpiDefinition(models.Model):
    """A single KPI in the organizational KPI library."""

    class Category(models.TextChoices):
        CONSTRUCTION = "construction", "Construction"
        SALES = "sales", "Sales"
        FINANCE = "finance", "Finance"
        OPERATIONS = "operations", "Operations"
        COMPLIANCE = "compliance", "Compliance"
        HR = "hr", "Human Resources"
        PROCUREMENT = "procurement", "Procurement"
        PROJECT_MGMT = "project_management", "Project Management"
        PROPERTY = "property", "Property"
        SAFETY = "safety", "Safety"
        QUALITY = "quality", "Quality"

    class Unit(models.TextChoices):
        PERCENTAGE = "percentage", "Percentage (%)"
        CURRENCY = "currency", "Currency"
        COUNT = "count", "Count"
        RATIO = "ratio", "Ratio"
        DAYS = "days", "Days"
        SCORE = "score", "Score (0–100)"

    class Direction(models.TextChoices):
        HIGHER_BETTER = "higher_is_better", "Higher is Better"
        LOWER_BETTER = "lower_is_better", "Lower is Better"

    class Frequency(models.TextChoices):
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        ANNUAL = "annual", "Annual"

    class Grain(models.TextChoices):
        EVENT = "event", "Event"
        HOURLY = "hourly", "Hourly"
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        ANNUAL = "annual", "Annual"
        SNAPSHOT = "snapshot", "Snapshot"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="kpi_definitions",
    )

    # Core identity
    name = models.CharField(max_length=150)
    code = models.CharField(
        max_length=50,
        help_text="Unique identifier within the org, e.g. COST_VARIANCE_PCT",
    )
    description = models.TextField(blank=True)
    category = models.CharField(max_length=30, choices=Category.choices)
    unit = models.CharField(max_length=20, choices=Unit.choices, default=Unit.PERCENTAGE)
    direction = models.CharField(
        max_length=20,
        choices=Direction.choices,
        default=Direction.HIGHER_BETTER,
    )
    frequency = models.CharField(
        max_length=20,
        choices=Frequency.choices,
        default=Frequency.MONTHLY,
    )
    is_canonical = models.BooleanField(
        default=True,
        help_text="Marks this KPI as part of the canonical org-wide metrics contract.",
    )
    grain = models.CharField(
        max_length=20,
        choices=Grain.choices,
        default=Grain.DAILY,
        help_text="Time grain at which this KPI is computed and stored.",
    )
    dimensions = models.JSONField(
        default=list,
        blank=True,
        help_text="Canonical dimension keys used for slicing this KPI, e.g. ['department', 'location'].",
    )
    owner_role = models.ForeignKey(
        "settings.Role",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_kpi_definitions",
        help_text="Business owner role accountable for this KPI.",
    )
    owner_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_kpi_definitions",
        help_text="Direct owner user accountable for this KPI.",
    )
    freshness_sla_minutes = models.PositiveIntegerField(
        default=1440,
        help_text="Maximum allowed data staleness for this KPI in minutes.",
    )

    # Formula / data source
    formula_expression = models.TextField(
        blank=True,
        help_text="Human-readable formula, e.g. '(Budget - Actual) / Budget × 100'",
    )
    data_source = models.CharField(
        max_length=200,
        blank=True,
        help_text="Where the data is sourced from, e.g. 'Project cost entries'",
    )

    # RAG thresholds — interpretation depends on direction
    # higher_is_better: value >= green → green, value >= amber → amber, else red
    # lower_is_better:  value <= green → green, value <= amber → amber, else red
    green_threshold = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Threshold for green (good) status",
    )
    amber_threshold = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Threshold for amber (warning) status",
    )

    # Optional bonus linkage
    bonus_green_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Bonus multiplier (%) when KPI is green",
    )
    bonus_amber_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Bonus multiplier (%) when KPI is amber",
    )
    bonus_red_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Bonus multiplier (%) when KPI is red",
    )

    is_active = models.BooleanField(default=True)
    is_system = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "sort_order", "name"]
        unique_together = [("organization", "code")]
        verbose_name = "KPI Definition"
        verbose_name_plural = "KPI Definitions"
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="set_kpi_org_created_idx",
            ),
            models.Index(
                fields=["organization", "is_canonical", "grain"],
                name="set_kpi_org_contract_idx",
            ),
        ]

    def __str__(self):
        return f"{self.code} — {self.name}"


class KpiAssignment(models.Model):
    """Assigns a KPI to a role and/or department with a specific target value."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="kpi_assignments",
    )
    kpi = models.ForeignKey(
        KpiDefinition,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    role = models.ForeignKey(
        "settings.Role",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="kpi_assignments",
    )
    department = models.ForeignKey(
        "settings.Department",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="kpi_assignments",
    )

    target_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Target value for this KPI assignment",
    )
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=100,
        help_text="Relative weight of this KPI (0–100) for composite scoring",
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["kpi__category", "kpi__sort_order"]
        verbose_name = "KPI Assignment"
        verbose_name_plural = "KPI Assignments"
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="set_kpia_org_created_idx",
            ),
        ]

    def __str__(self):
        target = self.role or self.department or "Unassigned"
        return f"{self.kpi.code} → {target}"


# ---------------------------------------------------------------------------
# Reporting Engine Settings
# ---------------------------------------------------------------------------


class ReportingEngineSettings(models.Model):
    """Singleton per organization — PDF formatting, watermark rules, board pack automation, dispatch defaults."""

    class PageSize(models.TextChoices):
        A4 = "a4", "A4 (210 × 297 mm)"
        LETTER = "letter", "US Letter (8.5 × 11 in)"
        LEGAL = "legal", "US Legal (8.5 × 14 in)"
        A3 = "a3", "A3 (297 × 420 mm)"

    class Orientation(models.TextChoices):
        PORTRAIT = "portrait", "Portrait"
        LANDSCAPE = "landscape", "Landscape"

    class WatermarkPosition(models.TextChoices):
        CENTER = "center", "Center"
        DIAGONAL = "diagonal", "Diagonal"
        TOP = "top", "Top"
        BOTTOM = "bottom", "Bottom"

    class DispatchFormat(models.TextChoices):
        PDF = "pdf", "PDF"
        XLSX = "xlsx", "Excel (XLSX)"
        CSV = "csv", "CSV"

    class BoardPackFrequency(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        SEMI_ANNUAL = "semi_annual", "Semi-Annual"
        ANNUAL = "annual", "Annual"

    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name="reporting_engine_settings",
    )

    # PDF Formatting Standards
    page_size = models.CharField(
        max_length=10,
        choices=PageSize.choices,
        default=PageSize.A4,
    )
    orientation = models.CharField(
        max_length=10,
        choices=Orientation.choices,
        default=Orientation.PORTRAIT,
    )
    margin_top_mm = models.PositiveIntegerField(default=20)
    margin_bottom_mm = models.PositiveIntegerField(default=20)
    margin_left_mm = models.PositiveIntegerField(default=15)
    margin_right_mm = models.PositiveIntegerField(default=15)
    header_enabled = models.BooleanField(default=True)
    header_text = models.CharField(
        max_length=300,
        blank=True,
        help_text="Supports placeholders: {org_name}, {report_title}, {date}",
    )
    footer_enabled = models.BooleanField(default=True)
    footer_text = models.CharField(
        max_length=300,
        blank=True,
        default="Page {page} of {total_pages}",
        help_text="Supports placeholders: {page}, {total_pages}, {date}",
    )
    font_family = models.CharField(max_length=100, default="Inter")
    font_size_pt = models.PositiveIntegerField(default=10)
    include_cover_page = models.BooleanField(default=True)
    include_table_of_contents = models.BooleanField(default=False)

    # Watermark Rules
    watermark_enabled = models.BooleanField(default=False)
    watermark_text = models.CharField(max_length=100, blank=True, default="CONFIDENTIAL")
    watermark_opacity = models.PositiveIntegerField(
        default=15,
        help_text="Opacity percentage (1–100)",
    )
    watermark_position = models.CharField(
        max_length=10,
        choices=WatermarkPosition.choices,
        default=WatermarkPosition.DIAGONAL,
    )
    watermark_color = models.CharField(max_length=7, default="#CBD5E1")

    # Board Pack Automation
    board_pack_enabled = models.BooleanField(default=False)
    board_pack_frequency = models.CharField(
        max_length=15,
        choices=BoardPackFrequency.choices,
        default=BoardPackFrequency.QUARTERLY,
    )
    board_pack_recipients = models.JSONField(
        default=list,
        blank=True,
        help_text="List of email addresses for board pack distribution",
    )
    board_pack_sections = models.JSONField(
        default=list,
        blank=True,
        help_text="Ordered list of report template codes to include in the board pack",
    )

    # Dispatch Defaults
    default_dispatch_format = models.CharField(
        max_length=10,
        choices=DispatchFormat.choices,
        default=DispatchFormat.PDF,
    )
    dispatch_retention_days = models.PositiveIntegerField(
        default=90,
        help_text="Days to retain generated report files",
    )
    dispatch_reply_to_email = models.EmailField(
        blank=True,
        help_text="Reply-to address for dispatched reports",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Reporting Engine Settings"
        verbose_name_plural = "Reporting Engine Settings"

    def __str__(self):
        return f"Reporting Engine — {self.organization.name}"


class ConfidentialityLabel(models.Model):
    """Classification labels for report confidentiality."""

    class AccessLevel(models.TextChoices):
        PUBLIC = "public", "Public"
        INTERNAL = "internal", "Internal"
        CONFIDENTIAL = "confidential", "Confidential"
        STRICTLY_CONFIDENTIAL = "strictly_confidential", "Strictly Confidential"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="confidentiality_labels",
    )
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    access_level = models.CharField(
        max_length=25,
        choices=AccessLevel.choices,
        default=AccessLevel.INTERNAL,
    )
    color = models.CharField(
        max_length=7,
        default="#6B7280",
        help_text="Hex color for badge display",
    )
    watermark_override = models.BooleanField(
        default=False,
        help_text="Force watermark on reports with this label",
    )
    restrict_printing = models.BooleanField(default=False)
    restrict_download = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_system = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]
        unique_together = [("organization", "code")]
        verbose_name = "Confidentiality Label"
        verbose_name_plural = "Confidentiality Labels"
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="set_clbl_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_access_level_display()})"


class ReportTemplate(models.Model):
    """Report template definitions with data source mapping and cross-module joins."""

    class TemplateType(models.TextChoices):
        FINANCIAL = "financial", "Financial"
        OPERATIONAL = "operational", "Operational"
        COMPLIANCE = "compliance", "Compliance"
        EXECUTIVE = "executive", "Executive Summary"
        PROJECT = "project", "Project"
        PROPERTY = "property", "Property"
        CUSTOM = "custom", "Custom"

    class OutputFormat(models.TextChoices):
        PDF = "pdf", "PDF"
        XLSX = "xlsx", "Excel (XLSX)"
        CSV = "csv", "CSV"
        PDF_XLSX = "pdf_xlsx", "PDF + Excel"

    class Visibility(models.TextChoices):
        PRIVATE = "private", "Private"
        DEPARTMENT = "department", "Department"
        SHARED = "shared", "Shared"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="report_templates",
    )
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    module_source = models.CharField(
        max_length=30,
        choices=Module.choices,
        blank=True,
        default="",
        help_text="Primary module source for categorizing this report.",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_report_templates",
    )
    visibility = models.CharField(
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.SHARED,
    )
    shared_department = models.ForeignKey(
        "settings.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shared_report_templates",
    )
    template_type = models.CharField(
        max_length=20,
        choices=TemplateType.choices,
    )
    output_format = models.CharField(
        max_length=10,
        choices=OutputFormat.choices,
        default=OutputFormat.PDF,
    )

    # Data source mapping (which modules/entities to pull data from)
    data_sources = models.JSONField(
        default=list,
        blank=True,
        help_text='List of data source entries: [{"module": "...", "entity": "...", "fields": [...], "filters": {...}}]',
    )

    # Cross-module joins
    cross_module_joins = models.JSONField(
        default=list,
        blank=True,
        help_text='List of join definitions: [{"left_source": "...", "right_source": "...", "join_key": "...", "join_type": "inner|left|right"}]',
    )

    # Confidentiality
    confidentiality_label = models.ForeignKey(
        ConfidentialityLabel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="report_templates",
    )
    allow_simple_builder = models.BooleanField(
        default=False,
        help_text="Allow end users to create simple derivative reports from this template.",
    )

    is_active = models.BooleanField(default=True)
    is_system = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["template_type", "name"]
        unique_together = [("organization", "code")]
        indexes = [
            models.Index(fields=["organization", "is_active", "visibility"]),
            models.Index(fields=["organization", "module_source", "template_type"]),
        ]
        verbose_name = "Report Template"
        verbose_name_plural = "Report Templates"

    def __str__(self):
        return f"{self.code} — {self.name}"


class ScheduledReportDispatch(models.Model):
    """Auto-schedule report dispatch rules."""

    class Frequency(models.TextChoices):
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        ANNUAL = "annual", "Annual"

    class DayOfWeek(models.IntegerChoices):
        MONDAY = 0, "Monday"
        TUESDAY = 1, "Tuesday"
        WEDNESDAY = 2, "Wednesday"
        THURSDAY = 3, "Thursday"
        FRIDAY = 4, "Friday"
        SATURDAY = 5, "Saturday"
        SUNDAY = 6, "Sunday"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="scheduled_report_dispatches",
    )
    report_template = models.ForeignKey(
        ReportTemplate,
        on_delete=models.CASCADE,
        related_name="schedules",
    )
    name = models.CharField(max_length=200)
    frequency = models.CharField(max_length=15, choices=Frequency.choices)
    dispatch_time = models.TimeField(
        default="08:00",
        help_text="Time of day to dispatch (HH:MM)",
    )
    dispatch_day_of_week = models.IntegerField(
        choices=DayOfWeek.choices,
        null=True,
        blank=True,
        help_text="Day of week for weekly schedules",
    )
    dispatch_day_of_month = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Day of month for monthly/quarterly/annual schedules (1–28)",
    )
    output_format = models.CharField(
        max_length=10,
        choices=ReportTemplate.OutputFormat.choices,
        default=ReportTemplate.OutputFormat.PDF,
    )
    recipients = models.JSONField(
        default=list,
        help_text="List of email addresses to receive the report",
    )
    is_active = models.BooleanField(default=True)
    last_dispatched_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["report_template__name", "frequency"]
        verbose_name = "Scheduled Report Dispatch"
        verbose_name_plural = "Scheduled Report Dispatches"
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="set_srd_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_frequency_display()})"


class ReportSavedView(models.Model):
    """User-defined reusable filter presets for a report template."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="report_saved_views",
    )
    report_template = models.ForeignKey(
        ReportTemplate,
        on_delete=models.CASCADE,
        related_name="saved_views",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="report_saved_views",
    )
    name = models.CharField(max_length=140)
    filters = models.JSONField(default=dict, blank=True)
    column_visibility = models.JSONField(default=dict, blank=True)
    rows_per_page = models.PositiveSmallIntegerField(default=25)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        unique_together = [("user", "report_template", "name")]
        indexes = [
            models.Index(fields=["organization", "user", "is_active"]),
            models.Index(fields=["organization", "report_template"]),
        ]

    def __str__(self):
        return f"{self.report_template.code} — {self.name}"


def default_report_subscription_delivery_channels() -> list[str]:
    return ["email"]


class ReportSubscription(models.Model):
    """Per-user report delivery subscription preferences."""

    class Frequency(models.TextChoices):
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"

    class DeliveryChannel(models.TextChoices):
        EMAIL = "email", "Email"
        IN_APP = "in_app", "In-App Notification"
        DASHBOARD_WIDGET = "dashboard_widget", "Dashboard Widget"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="report_subscriptions",
    )
    report_template = models.ForeignKey(
        ReportTemplate,
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="report_subscriptions",
    )
    frequency = models.CharField(max_length=15, choices=Frequency.choices, default=Frequency.MONTHLY)
    output_format = models.CharField(
        max_length=10,
        choices=ReportTemplate.OutputFormat.choices,
        default=ReportTemplate.OutputFormat.PDF,
    )
    recipients = models.JSONField(
        default=list,
        blank=True,
        help_text="Optional additional recipients in email format.",
    )
    delivery_channels = models.JSONField(
        default=default_report_subscription_delivery_channels,
        blank=True,
        help_text="Delivery channels for personal report subscriptions.",
    )
    is_active = models.BooleanField(default=True)
    last_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["report_template__name", "frequency"]
        unique_together = [("user", "report_template", "frequency")]
        indexes = [
            models.Index(fields=["organization", "user", "is_active"]),
            models.Index(fields=["organization", "report_template"]),
        ]

    def __str__(self):
        return f"{self.user_id} → {self.report_template.code} ({self.frequency})"


class ReportRun(models.Model):
    """Execution/spool records for report runs from centralized reporting workspace."""

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    class Trigger(models.TextChoices):
        MANUAL = "manual", "Manual"
        SCHEDULED = "scheduled", "Scheduled Dispatch"
        SUBSCRIPTION = "subscription", "Subscription"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="report_runs",
    )
    report_template = models.ForeignKey(
        ReportTemplate,
        on_delete=models.CASCADE,
        related_name="runs",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="report_runs",
    )
    scheduled_dispatch = models.ForeignKey(
        ScheduledReportDispatch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="runs",
    )
    subscription = models.ForeignKey(
        ReportSubscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="runs",
    )
    trigger = models.CharField(max_length=20, choices=Trigger.choices, default=Trigger.MANUAL)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    output_format = models.CharField(
        max_length=10,
        choices=ReportTemplate.OutputFormat.choices,
        default=ReportTemplate.OutputFormat.PDF,
    )
    filters = models.JSONField(default=dict, blank=True)
    result_summary = models.JSONField(default=dict, blank=True)
    row_count = models.PositiveIntegerField(default=0)
    file_path = models.CharField(max_length=500, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "report_template", "created_at"]),
            models.Index(fields=["organization", "requested_by", "created_at"]),
            models.Index(fields=["organization", "status", "created_at"]),
        ]

    def __str__(self):
        return f"Run #{self.pk} — {self.report_template.code} ({self.status})"


# ---------------------------------------------------------------------------
# Escalation Matrix Settings
# ---------------------------------------------------------------------------


class EscalationMatrixSettings(models.Model):
    """Singleton per organization — global escalation config and crisis mode activation logic."""

    class CrisisActivationSeverity(models.TextChoices):
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class BoardSeverityThreshold(models.TextChoices):
        CRITICAL_ONLY = "critical_only", "Critical Only"
        HIGH_AND_ABOVE = "high_and_above", "High & Critical"

    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name="escalation_matrix_settings",
    )

    # Global Escalation
    escalation_enabled = models.BooleanField(default=True)
    default_response_time_minutes = models.PositiveIntegerField(
        default=60,
        help_text="Default response time before auto-escalation (minutes)",
    )
    max_escalation_levels = models.PositiveIntegerField(
        default=4,
        help_text="Maximum number of escalation levels",
    )
    auto_escalation_enabled = models.BooleanField(
        default=True,
        help_text="Automatically escalate when response time is breached",
    )
    require_acknowledgment = models.BooleanField(
        default=True,
        help_text="Require explicit acknowledgment before timer pauses",
    )

    # Crisis Mode
    crisis_mode_enabled = models.BooleanField(default=False)
    crisis_activation_severity = models.CharField(
        max_length=10,
        choices=CrisisActivationSeverity.choices,
        default=CrisisActivationSeverity.CRITICAL,
    )
    crisis_activation_threshold = models.PositiveIntegerField(
        default=3,
        help_text="Number of concurrent issues at severity to trigger crisis mode",
    )
    crisis_notification_channels = models.JSONField(
        default=list,
        blank=True,
        help_text="Channels to use during crisis mode: email, in_app, sms, push",
    )
    crisis_war_room_enabled = models.BooleanField(
        default=False,
        help_text="Auto-create a virtual war room channel on crisis activation",
    )
    crisis_auto_deactivate_hours = models.PositiveIntegerField(
        default=24,
        help_text="Auto-deactivate crisis mode after this many hours if unresolved",
    )

    # Board Notifications
    board_notification_enabled = models.BooleanField(default=False)
    board_severity_threshold = models.CharField(
        max_length=20,
        choices=BoardSeverityThreshold.choices,
        default=BoardSeverityThreshold.CRITICAL_ONLY,
    )
    board_notification_recipients = models.JSONField(
        default=list,
        blank=True,
        help_text="Email addresses for board-level notifications",
    )
    board_notification_cooldown_hours = models.PositiveIntegerField(
        default=4,
        help_text="Minimum hours between board notifications for same issue",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Escalation Matrix Settings"
        verbose_name_plural = "Escalation Matrix Settings"

    def __str__(self):
        return f"Escalation Matrix — {self.organization.name}"


class EscalationTier(models.Model):
    """Defines an escalation tier in the hierarchy for a given severity level."""

    class Severity(models.TextChoices):
        INFO = "info", "Info"
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="escalation_tiers",
    )
    severity = models.CharField(max_length=10, choices=Severity.choices)
    tier_level = models.PositiveIntegerField(
        help_text="Escalation level (1 = first responder, 2 = supervisor, etc.)",
    )
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    response_time_minutes = models.PositiveIntegerField(
        help_text="Expected response time at this tier (minutes)",
    )
    escalate_to_roles = models.JSONField(
        default=list,
        help_text="List of role slugs that are notified at this tier",
    )
    notification_channels = models.JSONField(
        default=list,
        help_text="Channels to use: email, in_app, sms, push",
    )
    requires_acknowledgment = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["severity", "tier_level"]
        unique_together = [("organization", "severity", "tier_level")]
        verbose_name = "Escalation Tier"
        verbose_name_plural = "Escalation Tiers"
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="set_etier_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.get_severity_display()} L{self.tier_level} — {self.name}"


class AutoEscalationRule(models.Model):
    """Time-based and parallel escalation rules."""

    class RuleType(models.TextChoices):
        TIME_BASED = "time_based", "Time-Based Auto-Escalation"
        PARALLEL = "parallel", "Parallel Notification"

    class ConditionType(models.TextChoices):
        NO_RESPONSE = "no_response", "No Response"
        NO_RESOLUTION = "no_resolution", "No Resolution"
        THRESHOLD_BREACH = "threshold_breach", "Threshold Breach"
        SEVERITY_MATCH = "severity_match", "Severity Match"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="auto_escalation_rules",
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    rule_type = models.CharField(
        max_length=15,
        choices=RuleType.choices,
        default=RuleType.TIME_BASED,
    )

    # Time-based fields
    source_tier = models.ForeignKey(
        EscalationTier,
        on_delete=models.CASCADE,
        related_name="outgoing_rules",
        null=True,
        blank=True,
        help_text="Source tier for time-based escalation",
    )
    target_tier = models.ForeignKey(
        EscalationTier,
        on_delete=models.CASCADE,
        related_name="incoming_rules",
        null=True,
        blank=True,
        help_text="Target tier to escalate to",
    )
    escalate_after_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Minutes of inaction before auto-escalation",
    )
    condition_type = models.CharField(
        max_length=20,
        choices=ConditionType.choices,
        default=ConditionType.NO_RESPONSE,
    )
    condition_threshold = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Numeric threshold for threshold_breach conditions",
    )
    notify_original_assignee = models.BooleanField(
        default=True,
        help_text="Keep original assignee notified after escalation",
    )

    # Parallel escalation fields
    trigger_severity = models.CharField(
        max_length=10,
        choices=EscalationTier.Severity.choices,
        blank=True,
        help_text="Severity level that triggers parallel notifications",
    )
    parallel_notify_roles = models.JSONField(
        default=list,
        blank=True,
        help_text="Role slugs to notify in parallel",
    )
    parallel_notify_emails = models.JSONField(
        default=list,
        blank=True,
        help_text="External email addresses for parallel notifications",
    )
    parallel_channels = models.JSONField(
        default=list,
        blank=True,
        help_text="Notification channels for parallel escalation",
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["rule_type", "name"]
        verbose_name = "Auto-Escalation Rule"
        verbose_name_plural = "Auto-Escalation Rules"
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="set_aer_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.get_rule_type_display()} — {self.name}"


class BoardNotificationTrigger(models.Model):
    """Conditions that trigger board-level notifications."""

    class TriggerType(models.TextChoices):
        SEVERITY_THRESHOLD = "severity_threshold", "Severity Threshold"
        CONCURRENT_ISSUES = "concurrent_issues", "Concurrent Issues Count"
        FINANCIAL_IMPACT = "financial_impact", "Financial Impact"
        REGULATORY_BREACH = "regulatory_breach", "Regulatory Breach"
        ESCALATION_EXHAUSTED = "escalation_exhausted", "All Escalation Tiers Exhausted"
        MANUAL = "manual", "Manual Trigger"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="board_notification_triggers",
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    trigger_type = models.CharField(
        max_length=25,
        choices=TriggerType.choices,
    )

    # Condition fields (used depending on trigger_type)
    severity_threshold = models.CharField(
        max_length=10,
        choices=EscalationTier.Severity.choices,
        blank=True,
        help_text="Severity level to trigger board notification",
    )
    concurrent_issue_count = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Number of concurrent issues to trigger notification",
    )
    financial_threshold_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Financial impact threshold to trigger notification",
    )

    # Notification config
    notification_message_template = models.TextField(
        blank=True,
        help_text="Template for the notification message. Supports placeholders: {issue_summary}, {severity}, {count}, {amount}",
    )
    recipients = models.JSONField(
        default=list,
        help_text="Email addresses to notify",
    )
    notification_channels = models.JSONField(
        default=list,
        help_text="Channels: email, in_app, sms, push",
    )
    cooldown_hours = models.PositiveIntegerField(
        default=4,
        help_text="Minimum hours between repeat notifications for same trigger",
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["trigger_type", "name"]
        verbose_name = "Board Notification Trigger"
        verbose_name_plural = "Board Notification Triggers"
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="set_bnt_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.get_trigger_type_display()} — {self.name}"


# ---------------------------------------------------------------------------
# Communication & Branding Settings
# ---------------------------------------------------------------------------


class CommunicationBrandingSettings(models.Model):
    """Singleton per organization — external-facing communication branding,
    email/SMS templates, letterhead formats, disclaimers, and signature settings."""

    class PaperSize(models.TextChoices):
        A4 = "a4", "A4"
        LETTER = "letter", "Letter"
        LEGAL = "legal", "Legal"

    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name="communication_branding_settings",
    )

    # ── Email Branding ──────────────────────────────────────────────────
    email_sender_name = models.CharField(max_length=200, blank=True)
    email_sender_address = models.EmailField(blank=True)
    email_reply_to = models.EmailField(blank=True)
    email_header_html = models.TextField(
        blank=True,
        help_text="Custom HTML header injected into outbound email templates.",
    )
    email_footer_html = models.TextField(
        blank=True,
        help_text="Custom HTML footer injected into outbound email templates.",
    )
    email_primary_color = models.CharField(max_length=7, default="#000000")
    email_logo_url = models.URLField(blank=True)

    # ── Notification Branding ───────────────────────────────────────────
    notification_brand_color = models.CharField(max_length=7, default="#000000")
    notification_accent_color = models.CharField(max_length=7, default="#3B82F6")
    notification_logo_url = models.URLField(blank=True)
    notification_app_name = models.CharField(max_length=200, blank=True)
    notification_include_logo = models.BooleanField(default=True)

    # ── SMS Configuration ───────────────────────────────────────────────
    sms_sender_id = models.CharField(max_length=20, blank=True)
    sms_prefix = models.CharField(max_length=50, blank=True)
    sms_opt_out_message = models.CharField(
        max_length=200,
        blank=True,
        default="Reply STOP to opt out.",
    )
    sms_character_limit = models.PositiveIntegerField(default=160)
    sms_enabled = models.BooleanField(default=False)

    # ── Letterhead ──────────────────────────────────────────────────────
    letterhead_header_html = models.TextField(
        blank=True,
        help_text="HTML header for branded document generation (contracts, letters, etc.).",
    )
    letterhead_footer_html = models.TextField(
        blank=True,
        help_text="HTML footer for branded document generation.",
    )
    letterhead_paper_size = models.CharField(
        max_length=10,
        choices=PaperSize.choices,
        default=PaperSize.A4,
    )
    letterhead_margin_top_mm = models.PositiveIntegerField(default=25)
    letterhead_margin_bottom_mm = models.PositiveIntegerField(default=20)
    letterhead_watermark_text = models.CharField(max_length=100, blank=True)
    letterhead_watermark_opacity = models.PositiveIntegerField(
        default=15,
        help_text="Opacity percentage (0-100).",
    )

    # ── Document Footer Disclaimers ─────────────────────────────────────
    default_footer_disclaimer = models.TextField(blank=True)
    contract_footer_disclaimer = models.TextField(blank=True)
    invoice_footer_disclaimer = models.TextField(blank=True)
    report_footer_disclaimer = models.TextField(blank=True)

    # ── Digital Signature Settings ──────────────────────────────────────
    signature_email_subject = models.CharField(
        max_length=255,
        blank=True,
        default="Signature requested: {document_title}",
    )
    signature_email_body = models.TextField(blank=True)
    signature_reminder_enabled = models.BooleanField(default=True)
    signature_reminder_frequency_hours = models.PositiveIntegerField(default=24)
    signature_expiry_days = models.PositiveIntegerField(default=30)
    signature_branding_enabled = models.BooleanField(default=True)

    # ── Meta ────────────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Communication & Branding Settings"
        verbose_name_plural = "Communication & Branding Settings"

    def __str__(self):
        return f"Communication & Branding — {self.organization.name}"


class FunctionalControl(models.Model):
    """Organization-level toggles for activating/deactivating ERP modules and features.

    Org admins can selectively enable or disable major functional areas.
    Disabled modules remain in the database but are hidden from navigation
    and their API endpoints return 403.
    """

    organization = models.OneToOneField(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="functional_controls",
    )

    # ── Domain: Projects ──────────────────────────────────────────────
    projects_enabled = models.BooleanField(default=True, help_text="Project Pipeline, Setup, Feasibility, etc.")
    project_pipeline = models.BooleanField(default=True)
    project_feasibility = models.BooleanField(default=True)
    project_land_acquisition = models.BooleanField(default=True)
    project_dev_budget = models.BooleanField(default=True)
    project_financing = models.BooleanField(default=True)
    project_dev_schedule = models.BooleanField(default=True)
    project_consultants = models.BooleanField(default=True)
    project_approvals_permits = models.BooleanField(default=True)
    project_design_management = models.BooleanField(default=True)
    project_procurement_planning = models.BooleanField(default=True)
    project_sales_forecast = models.BooleanField(default=True)
    project_governance = models.BooleanField(default=True)
    project_milestones_gates = models.BooleanField(default=True)
    project_document_control = models.BooleanField(default=True)
    project_communications = models.BooleanField(default=True)
    project_reports = models.BooleanField(default=True)
    project_closeout = models.BooleanField(default=True)

    # ── Domain: Construction ──────────────────────────────────────────
    construction_enabled = models.BooleanField(default=True, help_text="Construction Schedule, Field Ops, QC, etc.")
    construction_schedule = models.BooleanField(default=True)
    construction_tasks = models.BooleanField(default=True)
    construction_work_packages = models.BooleanField(default=True)
    construction_field_operations = models.BooleanField(default=True)
    construction_quality_control = models.BooleanField(default=True)
    construction_equipment = models.BooleanField(default=True)
    construction_contractor_mgmt = models.BooleanField(default=True)
    construction_hse = models.BooleanField(default=True)
    construction_rfi = models.BooleanField(default=True)
    construction_site_instructions = models.BooleanField(default=True)
    construction_testing_commissioning = models.BooleanField(default=True)
    construction_cost_control = models.BooleanField(default=True)
    construction_reports = models.BooleanField(default=True)

    # ── Domain: Procurement ───────────────────────────────────────────
    procurement_enabled = models.BooleanField(default=True, help_text="Vendors, Requisitions, POs, RFQs.")
    procurement_vendors = models.BooleanField(default=True)
    procurement_requisitions = models.BooleanField(default=True)
    procurement_purchase_orders = models.BooleanField(default=True)
    procurement_rfq = models.BooleanField(default=True)

    # ── Domain: Finance ───────────────────────────────────────────────
    finance_enabled = models.BooleanField(default=True, help_text="Invoices, Bills, Budgets, Banking.")
    finance_invoices = models.BooleanField(default=True)
    finance_bills = models.BooleanField(default=True)
    finance_budgets = models.BooleanField(default=True)
    finance_banking = models.BooleanField(default=True)
    finance_investors = models.BooleanField(default=True)

    # ── Domain: Inventory ─────────────────────────────────────────────
    inventory_enabled = models.BooleanField(default=True, help_text="Warehouses, Items, BOQ, Transfers.")
    inventory_boq = models.BooleanField(default=True)
    inventory_warehouses = models.BooleanField(default=True)
    inventory_items = models.BooleanField(default=True)

    # ── Domain: HR ────────────────────────────────────────────────────
    hr_enabled = models.BooleanField(default=True, help_text="Employees, Payroll, Attendance.")
    hr_employees = models.BooleanField(default=True)
    hr_payroll = models.BooleanField(default=True)
    hr_attendance = models.BooleanField(default=True)

    # ── Domain: CRM ───────────────────────────────────────────────────
    crm_enabled = models.BooleanField(default=True, help_text="Contacts, Leads, Reservations.")

    # ── Domain: Properties ────────────────────────────────────────────
    properties_enabled = models.BooleanField(default=True, help_text="Property Registry, Units.")

    # ── Domain: Support ───────────────────────────────────────────────
    support_desk_enabled = models.BooleanField(default=True, help_text="Tickets, Requests.")

    # ── BOQ Lifecycle Controls ────────────────────────────────────────
    boq_lifecycle_enabled = models.BooleanField(
        default=True,
        help_text="Enable 5-phase BOQ lifecycle (Estimate → Tender → Contract → Execution → Financial Control).",
    )
    boq_lock_after_contract = models.BooleanField(
        default=True,
        help_text="Prevent BOQ rate edits once status is 'contract' or later.",
    )
    boq_require_approval_for_tender = models.BooleanField(
        default=True,
        help_text="BOQ must be in 'approved' or 'estimate' status before it can be issued for tender.",
    )

    # ── 3-Way Matching Controls ───────────────────────────────────────
    three_way_match_enabled = models.BooleanField(
        default=True,
        help_text="Enable automatic 3-way matching (PO vs GRN vs Invoice).",
    )
    three_way_match_tolerance_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("5.00"),
        help_text="Variance tolerance % for auto-matching (e.g. 5% = amounts within 5% are considered matched).",
    )
    three_way_match_block_payment = models.BooleanField(
        default=False,
        help_text="Block bill payment if 3-way match fails.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Functional Control"
        verbose_name_plural = "Functional Controls"

    def __str__(self):
        return f"Functional Controls — {self.organization.name}"


class TaxRate(models.Model):
    """Organization-configurable tax rate for auto-calculation on POs, Bills, Invoices."""

    class TaxType(models.TextChoices):
        VAT = "vat", "VAT"
        WHT = "wht", "Withholding Tax"
        SALES_TAX = "sales_tax", "Sales Tax"
        STAMP_DUTY = "stamp_duty", "Stamp Duty"
        CUSTOM_DUTY = "custom_duty", "Custom Duty"
        OTHER = "other", "Other"

    class AppliesTo(models.TextChoices):
        ALL = "all", "All Transactions"
        PURCHASE_ORDERS = "purchase_orders", "Purchase Orders"
        BILLS = "bills", "Bills / Vendor Invoices"
        INVOICES = "invoices", "Customer Invoices"
        CONTRACTS = "contracts", "Contracts"

    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.CASCADE, related_name="tax_rates",
    )
    name = models.CharField(max_length=100, help_text="e.g. VAT 7.5%, WHT 5%")
    tax_type = models.CharField(max_length=20, choices=TaxType.choices, default=TaxType.VAT)
    rate_pct = models.DecimalField(max_digits=6, decimal_places=3, help_text="Tax rate as percentage, e.g. 7.500")
    applies_to = models.CharField(max_length=20, choices=AppliesTo.choices, default=AppliesTo.ALL)
    is_compound = models.BooleanField(default=False, help_text="If true, applied on top of other taxes (compound).")
    is_inclusive = models.BooleanField(default=False, help_text="If true, tax is included in the price (not added on top).")
    is_default = models.BooleanField(default=False, help_text="Auto-applied to new transactions.")
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    effective_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "Tax Rate"
        verbose_name_plural = "Tax Rates"

    def __str__(self):
        return f"{self.name} ({self.rate_pct}%)"


class ProcurementPolicySettings(models.Model):
    """Organization-level procurement business rules and thresholds."""

    organization = models.OneToOneField(
        "accounts.Organization", on_delete=models.CASCADE, related_name="procurement_policy",
    )

    # PO thresholds
    po_auto_approve_limit = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00"),
        help_text="POs below this amount are auto-approved (0 = disabled).",
    )
    po_single_approval_limit = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00"),
        help_text="POs below this amount need only 1 approver (0 = use workflow).",
    )
    po_director_approval_limit = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00"),
        help_text="POs above this require director-level approval.",
    )

    # Quote requirements
    min_quotes_required = models.PositiveIntegerField(
        default=3,
        help_text="Minimum number of vendor quotes required before PO can be issued.",
    )
    min_quotes_threshold = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("100000.00"),
        help_text="POs above this amount require minimum quotes. Below = single source OK.",
    )
    sole_source_justification_required = models.BooleanField(
        default=True,
        help_text="Require written justification for single-source procurement.",
    )

    # Vendor rules
    require_vendor_compliance = models.BooleanField(
        default=True,
        help_text="Vendors must be 'compliant' before POs can be issued to them.",
    )
    block_blacklisted_vendors = models.BooleanField(
        default=True,
        help_text="Prevent PO creation for blacklisted vendors.",
    )
    vendor_performance_minimum = models.DecimalField(
        max_digits=3, decimal_places=2, default=Decimal("0.00"),
        help_text="Minimum performance rating (0-5) to issue POs. 0 = disabled.",
    )

    # Budget controls
    require_budget_code = models.BooleanField(
        default=False,
        help_text="Require budget code on all PRs and POs.",
    )
    block_over_budget_po = models.BooleanField(
        default=False,
        help_text="Prevent PO creation if it exceeds the linked budget.",
    )

    # GRN controls
    require_grn_before_payment = models.BooleanField(
        default=True,
        help_text="Bills cannot be approved until GRN is recorded.",
    )
    grn_quantity_tolerance_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("5.00"),
        help_text="Acceptable over-delivery tolerance % (e.g. 5% = accept 105 when ordered 100).",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Procurement Policy"
        verbose_name_plural = "Procurement Policies"

    def __str__(self):
        return f"Procurement Policy — {self.organization.name}"
