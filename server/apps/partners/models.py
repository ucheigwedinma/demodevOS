import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class PartnerType(models.TextChoices):
    CLIENT = "client", "Client"
    CONTRACTOR = "contractor", "Contractor"
    INVESTOR = "investor", "Investor"


class PortalRole(models.TextChoices):
    CLIENT = "client", "Client"
    CONTRACTOR = "contractor", "Contractor"
    INVESTOR = "investor", "Investor"
    LEAD_INVESTOR = "lead_investor", "Lead Investor"


class BudgetScope(models.TextChoices):
    NONE = "none", "No Budget Visibility"
    BOQ_ONLY = "boq_only", "BOQ-Only"
    AGGREGATED = "aggregated", "Aggregated Budget View"
    FULL = "full", "Full Budget Visibility"


class OnboardingTemplate(models.Model):
    """Role-specific onboarding blueprint (client/contractor/investor)."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="partner_onboarding_templates",
        null=True,
        blank=True,
        help_text="Leave blank for global templates available to all organizations.",
    )
    partner_type = models.CharField(max_length=20, choices=PartnerType.choices)
    code = models.SlugField(max_length=80)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    version = models.PositiveIntegerField(default=1)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_partner_onboarding_templates",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_partner_onboarding_templates",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["partner_type", "organization_id", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "partner_type", "code", "version"],
                name="unique_partner_onboarding_template_version",
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="part_tmpl_org_created_idx",
            ),
        ]

    def __str__(self):
        org_part = self.organization.name if self.organization_id else "Global"
        return f"{org_part} • {self.partner_type} • {self.name} v{self.version}"


class OnboardingTemplateStage(models.Model):
    """Ordered stage definitions that make up a template flow."""

    template = models.ForeignKey(
        OnboardingTemplate,
        on_delete=models.CASCADE,
        related_name="stages",
    )
    sequence = models.PositiveIntegerField()
    code = models.SlugField(max_length=80)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_required = models.BooleanField(default=True)
    approval_required = models.BooleanField(default=False)
    approval_role_label = models.CharField(max_length=120, blank=True)
    sla_hours = models.PositiveIntegerField(null=True, blank=True)
    auto_complete = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["template_id", "sequence"]
        constraints = [
            models.UniqueConstraint(
                fields=["template", "sequence"],
                name="unique_onboarding_stage_sequence",
            ),
            models.UniqueConstraint(
                fields=["template", "code"],
                name="unique_onboarding_stage_code",
            ),
        ]

    def __str__(self):
        return f"{self.template.name} • {self.sequence}. {self.name}"


class OnboardingTemplateDocumentRequirement(models.Model):
    """Required intake documents configured per onboarding template."""

    template = models.ForeignKey(
        OnboardingTemplate,
        on_delete=models.CASCADE,
        related_name="document_requirements",
    )
    sequence = models.PositiveIntegerField(default=1)
    code = models.SlugField(max_length=80)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_required = models.BooleanField(default=True)
    applies_to_stage = models.ForeignKey(
        OnboardingTemplateStage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="document_requirements",
    )
    accepted_sources = models.JSONField(
        default=list,
        blank=True,
        help_text="Allowed values from PartnerOnboardingIntakeDocument.SourceChannel.",
    )
    allowed_extensions = models.JSONField(
        default=list,
        blank=True,
        help_text="Optional list of file extensions (e.g. ['pdf', 'jpg']).",
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["template_id", "sequence", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["template", "code"],
                name="unique_onboarding_template_document_requirement_code",
            ),
        ]
        indexes = [
            models.Index(fields=["template", "is_required"]),
            models.Index(fields=["applies_to_stage", "is_required"]),
        ]

    def __str__(self):
        return f"{self.template.name} • {self.name}"


class PartnerOnboardingCase(models.Model):
    """Execution record of one external partner onboarding journey."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        IN_PROGRESS = "in_progress", "In Progress"
        UNDER_REVIEW = "under_review", "Under Review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="partner_onboarding_cases",
    )
    partner_type = models.CharField(max_length=20, choices=PartnerType.choices)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    template = models.ForeignKey(
        OnboardingTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="onboarding_cases",
    )
    title = models.CharField(max_length=255)

    # Counterparty details (pre-identity state)
    contact_name = models.CharField(max_length=255, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)

    # Source entities
    lead = models.ForeignKey(
        "crm.Lead",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="partner_onboarding_cases",
    )
    vendor = models.ForeignKey(
        "procurement.Vendor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="partner_onboarding_cases",
    )
    investor = models.ForeignKey(
        "finance.Investor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="partner_onboarding_cases",
    )
    customer = models.ForeignKey(
        "finance.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="partner_onboarding_cases",
    )

    # Partition scopes
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="partner_onboarding_cases",
    )
    spv_entity = models.ForeignKey(
        "finance.SPVEntity",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="partner_onboarding_cases",
    )
    contract_reference = models.CharField(max_length=120, blank=True)
    investment_vehicle_reference = models.CharField(max_length=120, blank=True)

    current_stage = models.ForeignKey(
        OnboardingTemplateStage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="current_for_cases",
    )
    assigned_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_partner_onboarding_cases",
    )

    portal_access_granted = models.BooleanField(default=False)
    portal_access_granted_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_partner_onboarding_cases",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_partner_onboarding_cases",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "partner_type", "status"]),
            models.Index(fields=["partner_type", "portal_access_granted"]),
            models.Index(fields=["project", "spv_entity"]),
            models.Index(
                fields=["organization", "status"],
                name="part_case_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="part_case_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.get_partner_type_display()} onboarding • {self.title}"

    @property
    def has_erp_profile(self) -> bool:
        if self.partner_type == PartnerType.CLIENT:
            if self.customer_id:
                return True
            if self.lead_id and self.lead and self.lead.converted_customer_id:
                return True
            return False
        if self.partner_type == PartnerType.CONTRACTOR:
            return self.vendor_id is not None
        if self.partner_type == PartnerType.INVESTOR:
            return self.investor_id is not None
        return False


def partner_intake_upload_path(instance, filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "pdf"
    return f"partners/onboarding/{instance.case_id}/intake/{uuid.uuid4()}.{ext}"


class PartnerOnboardingIntakeDocument(models.Model):
    """Pre-onboarding intake records for partner documents before portal activation."""

    class SourceChannel(models.TextChoices):
        PHYSICAL_SCAN = "physical_scan", "Physical Submission (Scanned)"
        EMAIL = "email", "Email"
        SECURE_UPLOAD_LINK = "secure_upload_link", "Secure Upload Link"
        TENDER_PORTAL = "tender_portal", "Tender Portal"
        DATA_ROOM = "data_room", "Data Room"
        INTERNAL_GENERATED = "internal_generated", "Internal Generated"
        OTHER = "other", "Other"

    class ReviewStatus(models.TextChoices):
        RECEIVED = "received", "Received"
        UNDER_REVIEW = "under_review", "Under Review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        WAIVED = "waived", "Waived"

    case = models.ForeignKey(
        PartnerOnboardingCase,
        on_delete=models.CASCADE,
        related_name="intake_documents",
    )
    requirement = models.ForeignKey(
        OnboardingTemplateDocumentRequirement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="case_documents",
    )
    template_stage = models.ForeignKey(
        OnboardingTemplateStage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="intake_documents",
    )
    document_code = models.SlugField(max_length=80)
    document_name = models.CharField(max_length=200)
    source_channel = models.CharField(max_length=40, choices=SourceChannel.choices)
    file = models.FileField(upload_to=partner_intake_upload_path, null=True, blank=True)
    external_reference_url = models.URLField(blank=True)
    external_reference_number = models.CharField(max_length=120, blank=True)
    received_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(
        max_length=20,
        choices=ReviewStatus.choices,
        default=ReviewStatus.RECEIVED,
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submitted_partner_onboarding_intake_documents",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_partner_onboarding_intake_documents",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    linked_repository_document = models.ForeignKey(
        "documents.Document",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="partner_onboarding_intake_documents",
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-received_at", "-id"]
        indexes = [
            models.Index(fields=["case", "status"]),
            models.Index(fields=["requirement", "status"]),
            models.Index(fields=["source_channel", "status"]),
        ]

    def __str__(self):
        return f"Case {self.case_id} • {self.document_name} • {self.get_status_display()}"


class PartnerOnboardingStageProgress(models.Model):
    """Per-case stage execution state (required for audit and SLA tracking)."""

    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Not Started"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        WAIVED = "waived", "Waived"
        BLOCKED = "blocked", "Blocked"

    case = models.ForeignKey(
        PartnerOnboardingCase,
        on_delete=models.CASCADE,
        related_name="stage_progress",
    )
    template_stage = models.ForeignKey(
        OnboardingTemplateStage,
        on_delete=models.CASCADE,
        related_name="case_progress",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NOT_STARTED,
    )
    is_required = models.BooleanField(default=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="completed_partner_onboarding_stage_progress",
    )
    notes = models.TextField(blank=True)
    evidence_links = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["template_stage__sequence", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["case", "template_stage"],
                name="unique_case_template_stage_progress",
            ),
        ]
        indexes = [
            models.Index(fields=["case", "status"]),
            models.Index(fields=["template_stage", "status"]),
        ]

    def __str__(self):
        return f"{self.case_id} • {self.template_stage.name} • {self.get_status_display()}"


class PartnerOnboardingApproval(models.Model):
    """Approval decisions for onboarding gates and final sign-off."""

    class Decision(models.TextChoices):
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CHANGES_REQUIRED = "changes_required", "Changes Required"

    case = models.ForeignKey(
        PartnerOnboardingCase,
        on_delete=models.CASCADE,
        related_name="approvals",
    )
    stage_progress = models.ForeignKey(
        PartnerOnboardingStageProgress,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approvals",
    )
    decision = models.CharField(max_length=20, choices=Decision.choices)
    approver_role_label = models.CharField(max_length=120, blank=True)
    comments = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="partner_onboarding_approvals",
    )
    decided_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-decided_at"]
        indexes = [
            models.Index(fields=["case", "decision", "decided_at"]),
        ]

    def __str__(self):
        return f"Case {self.case_id} • {self.get_decision_display()}"


class PartnerEntitlement(models.Model):
    """Entitlement matrix output scoped by project/SPV/contract/investment vehicle."""

    case = models.ForeignKey(
        PartnerOnboardingCase,
        on_delete=models.CASCADE,
        related_name="entitlements",
    )
    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="partner_entitlements",
    )
    portal_role = models.CharField(max_length=20, choices=PortalRole.choices)

    # Data partitioning scopes
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="partner_entitlements",
    )
    spv_entity = models.ForeignKey(
        "finance.SPVEntity",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="partner_entitlements",
    )
    contract_reference = models.CharField(max_length=120, blank=True)
    investment_vehicle_reference = models.CharField(max_length=120, blank=True)

    # Matrix capabilities
    budget_scope = models.CharField(
        max_length=20,
        choices=BudgetScope.choices,
        default=BudgetScope.NONE,
    )
    can_view_other_investors = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    can_approve = models.BooleanField(default=False)
    can_comment = models.BooleanField(default=True)
    can_download_documents = models.BooleanField(default=True)

    is_active = models.BooleanField(default=True)
    effective_from = models.DateField(default=timezone.localdate)
    expires_at = models.DateField(null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_partner_entitlements",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "portal_role", "is_active"]),
            models.Index(fields=["project", "spv_entity"]),
            models.Index(fields=["contract_reference", "investment_vehicle_reference"]),
            models.Index(
                fields=["organization", "-created_at"],
                name="part_ent_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"Case {self.case_id} • {self.get_portal_role_display()}"


class PartnerOnboardingAuditLog(models.Model):
    """Immutable audit timeline entries for onboarding and entitlement events."""

    class EventType(models.TextChoices):
        CASE_CREATED = "case_created", "Case Created"
        STAGES_INITIALIZED = "stages_initialized", "Stages Initialized"
        STAGE_STATUS_CHANGED = "stage_status_changed", "Stage Status Changed"
        CASE_STATUS_CHANGED = "case_status_changed", "Case Status Changed"
        APPROVAL_RECORDED = "approval_recorded", "Approval Recorded"
        ENTITLEMENT_PROVISIONED = "entitlement_provisioned", "Entitlement Provisioned"
        PORTAL_ACCESS_GRANTED = "portal_access_granted", "Portal Access Granted"
        ERP_ENTITY_CREATED = "erp_entity_created", "ERP Entity Created"
        LEAD_ARCHIVED = "lead_archived", "Lead Archived"

    case = models.ForeignKey(
        PartnerOnboardingCase,
        on_delete=models.CASCADE,
        related_name="audit_events",
    )
    event_type = models.CharField(max_length=40, choices=EventType.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="partner_onboarding_audit_events",
    )
    actor_role_label = models.CharField(max_length=120, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    message = models.CharField(max_length=255)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["case", "created_at"]),
            models.Index(fields=["event_type", "created_at"]),
        ]

    def __str__(self):
        return f"Case {self.case_id} • {self.get_event_type_display()}"


class PartnerPortalLegalAcceptance(models.Model):
    """Tracks first legal acceptance before portal operations access."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="partner_portal_legal_acceptance",
    )
    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="partner_portal_legal_acceptances",
    )
    terms_version = models.CharField(max_length=30, default="v1")
    privacy_version = models.CharField(max_length=30, default="v1")
    accepted_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-accepted_at", "-id"]
        indexes = [
            models.Index(fields=["organization", "accepted_at"]),
        ]

    def __str__(self):
        return f"{self.user.email} accepted legal terms {self.terms_version}/{self.privacy_version}"
