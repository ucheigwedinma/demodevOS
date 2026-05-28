import re
from decimal import Decimal

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.core.exceptions import ValidationError
from django.db import models


def default_document_confidentiality_levels():
    return ["public", "internal", "confidential", "restricted"]


class DocumentGovernanceCharter(models.Model):
    """Phase 1 governance decisions for the centralized repository."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        SUPERSEDED = "superseded", "Superseded"

    class RepositoryScope(models.TextChoices):
        FORMAL_ONLY = "formal_only", "Formal Documents Only"
        FORMAL_AND_SITE_PHOTOS = "formal_and_site_photos", "Formal Documents + Site Photos"

    class ExternalPortalAccess(models.TextChoices):
        NOT_INCLUDED = "not_included", "Not Included"
        READ_ONLY = "read_only", "Read-Only External Access"
        COLLABORATION = "collaboration", "External Collaboration"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_doc_governance_charters",
    )
    title = models.CharField(max_length=255, default="Document Governance Charter")
    version = models.CharField(max_length=30, default="v1.0")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    purpose = models.TextField(blank=True)
    repository_scope = models.CharField(
        max_length=40,
        choices=RepositoryScope.choices,
        default=RepositoryScope.FORMAL_ONLY,
        help_text="Defines whether site photos are governed in this repository.",
    )
    external_portal_access = models.CharField(
        max_length=20,
        choices=ExternalPortalAccess.choices,
        default=ExternalPortalAccess.NOT_INCLUDED,
        help_text="Defines if external parties can access repository records in v1.",
    )
    includes_digital_signature_v1 = models.BooleanField(
        default=False,
        help_text="Whether digital signature is in Phase 1 scope.",
    )
    scope_notes = models.TextField(blank=True)
    approved_by = models.CharField(max_length=255, blank=True)
    approved_at = models.DateField(null=True, blank=True)
    review_due_at = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]
        indexes = [
            models.Index(fields=["organization", "status"], name="doc_gov_org_status_idx"),
            models.Index(fields=["organization", "-created_at"], name="doc_gov_org_created_idx"),
        ]

    def __str__(self):
        return f"{self.title} ({self.version})"


class DocumentDomain(models.Model):
    """Controlled document domains used across governance workflows."""

    class Code(models.TextChoices):
        LAND_TITLE = "land_title", "Land & Title"
        REGULATORY_STATUTORY = "regulatory_statutory", "Regulatory & Statutory"
        DESIGN_ENGINEERING = "design_engineering", "Design & Engineering"
        CONSTRUCTION_VENDOR = "construction_vendor", "Construction & Vendor"
        SALES_CLIENT = "sales_client", "Sales & Client"
        FINANCE_COMMERCIAL = "finance_commercial", "Finance & Commercial"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_doc_domains",
    )
    code = models.CharField(max_length=40, choices=Code.choices, unique=True)
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="doc_dom_org_created_idx"),
        ]

    def __str__(self):
        return self.name


class ControlledVocabularyTerm(models.Model):
    """Canonical term dictionary for document control metadata."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        DEPRECATED = "deprecated", "Deprecated"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_controlled_vocabulary_terms",
    )
    domain = models.ForeignKey(
        DocumentDomain,
        on_delete=models.CASCADE,
        related_name="vocabulary_terms",
    )
    term = models.CharField(max_length=120)
    term_key = models.SlugField(
        max_length=120,
        help_text="Machine-readable key used in metadata mappings and automations.",
    )
    definition = models.TextField()
    usage_guidance = models.TextField(blank=True)
    synonyms = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    is_required = models.BooleanField(
        default=False,
        help_text="Required terms should be enforced in document metadata validation.",
    )
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["domain__sort_order", "sort_order", "term"]
        indexes = [
            models.Index(fields=["organization", "status"], name="doc_cvt_org_status_idx"),
            models.Index(fields=["organization", "-created_at"], name="doc_cvt_org_created_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["domain", "term"], name="documents_unique_domain_term"),
            models.UniqueConstraint(fields=["domain", "term_key"], name="documents_unique_domain_term_key"),
        ]

    def __str__(self):
        return f"{self.domain.name}: {self.term}"


class DocumentType(models.Model):
    """Normalized lookup for document classification."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_doc_types",
    )
    code = models.SlugField(max_length=60, unique=True)
    name = models.CharField(max_length=120, unique=True)
    category_code = models.CharField(
        max_length=10,
        default="GEN",
        help_text="Numbering category segment (e.g., REG, DES, CON).",
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="doc_dtype_org_created_idx"),
        ]

    def __str__(self):
        return self.name


class DocumentOwnerRole(models.Model):
    """Normalized owner role used for custody and approval routing."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_doc_owner_roles",
    )
    code = models.SlugField(max_length=60, unique=True)
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="doc_ownr_org_created_idx"),
        ]

    def __str__(self):
        return self.name


class DocumentWorkflowPhase(models.Model):
    """Lifecycle phase bucket for repository control."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_doc_workflow_phases",
    )
    code = models.SlugField(max_length=60, unique=True)
    name = models.CharField(max_length=120, unique=True)
    numbering_code = models.CharField(
        max_length=10,
        default="PH0",
        help_text="Numbering phase segment (e.g., PH1, PH2).",
    )
    description = models.TextField(blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "name"]
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="doc_wfph_org_created_idx"),
        ]

    def __str__(self):
        return self.name


class DocumentRetentionPolicy(models.Model):
    """Retention policy referenced by controlled documents."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_doc_retention_policies",
    )
    code = models.SlugField(max_length=60, unique=True)
    name = models.CharField(max_length=120, unique=True)
    retention_years = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Leave empty if policy is indefinite.",
    )
    is_indefinite = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="doc_retn_org_created_idx"),
        ]

    def __str__(self):
        return self.name


class Document(models.Model):
    """Controlled document master record."""

    class ConfidentialityLevel(models.TextChoices):
        PUBLIC = "public", "Public"
        INTERNAL = "internal", "Internal"
        CONFIDENTIAL = "confidential", "Confidential"
        RESTRICTED = "restricted", "Restricted"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under Review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        SUPERSEDED = "superseded", "Superseded"
        ARCHIVED = "archived", "Archived"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_documents",
    )
    title = models.CharField(max_length=255)
    document_number = models.CharField(max_length=100, unique=True)
    project_code = models.CharField(
        max_length=10,
        blank=True,
        help_text="Optional project numbering segment override (e.g., LUA).",
    )
    document_type = models.ForeignKey(
        DocumentType,
        on_delete=models.PROTECT,
        related_name="documents",
    )
    confidentiality_level = models.CharField(
        max_length=20,
        choices=ConfidentialityLevel.choices,
        default=ConfidentialityLevel.INTERNAL,
    )
    owner_role = models.ForeignKey(
        DocumentOwnerRole,
        on_delete=models.PROTECT,
        related_name="owned_documents",
    )
    contract_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Commercial value used for conditional approval routing.",
    )
    business_unit_division = models.ForeignKey(
        "settings.Division",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
    )
    business_unit_department = models.ForeignKey(
        "settings.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
    )
    land = models.ForeignKey(
        "properties.Property",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="land_documents",
    )
    unit = models.ForeignKey(
        "properties.Unit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
    )
    client = models.ForeignKey(
        "finance.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
    )
    vendor = models.ForeignKey(
        "procurement.Vendor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
    )
    # --- Source tracing (auto-bridge from other modules) ---
    source_app_label = models.CharField(
        max_length=60, blank=True, db_index=True,
        help_text="App label of the module that created this document (e.g. 'projects').",
    )
    source_model_name = models.CharField(
        max_length=60, blank=True,
        help_text="Model name of the source record (e.g. 'ProjectSupportingAttachment').",
    )
    source_object_id = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="PK of the source record.",
    )
    phase = models.ForeignKey(
        DocumentWorkflowPhase,
        on_delete=models.PROTECT,
        related_name="documents",
    )
    current_version = models.ForeignKey(
        "DocumentVersion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    sequence_number = models.PositiveIntegerField(
        default=0,
        help_text="Sequential number for PROJECT-PHASE-CATEGORY scope.",
    )
    revision_number = models.PositiveIntegerField(
        default=0,
        help_text="Current revision number represented as Rn.",
    )
    retention_policy = models.ForeignKey(
        DocumentRetentionPolicy,
        on_delete=models.PROTECT,
        related_name="documents",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "confidentiality_level"]),
            models.Index(
                fields=["project", "business_unit_division"],
                name="documents_d_proj_bu_div_idx",
            ),
            models.Index(
                fields=["project", "business_unit_department"],
                name="documents_d_proj_bu_dept_idx",
            ),
            models.Index(
                fields=["organization", "status"],
                name="doc_doc_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="doc_doc_org_created_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["source_app_label", "source_model_name", "source_object_id"],
                condition=~models.Q(source_app_label=""),
                name="documents_unique_source_record",
            ),
        ]

    def __str__(self):
        return f"{self.document_number} - {self.title}"

    @staticmethod
    def _normalize_segment(raw: str, default: str) -> str:
        segment = re.sub(r"[^A-Z0-9]", "", (raw or "").upper())
        if not segment:
            return default
        return segment[:10]

    def _project_segment(self) -> str:
        if self.project_code:
            return self._normalize_segment(self.project_code, "GEN")
        if self.project and self.project.name:
            tokens = re.findall(r"[A-Za-z0-9]+", self.project.name.upper())
            if tokens:
                primary = tokens[0]
                if len(primary) >= 3:
                    return primary[:3]
                return primary.ljust(3, "X")
        return "GEN"

    def _phase_segment(self) -> str:
        if self.phase and self.phase.numbering_code:
            return self._normalize_segment(self.phase.numbering_code, "PH0")
        return "PH0"

    def _category_segment(self) -> str:
        if self.document_type and self.document_type.category_code:
            return self._normalize_segment(self.document_type.category_code, "GEN")
        return "GEN"

    @staticmethod
    def _build_document_number(
        project_segment: str,
        phase_segment: str,
        category_segment: str,
        sequence_number: int,
        revision_number: int,
    ) -> str:
        return (
            f"{project_segment}-{phase_segment}-{category_segment}-"
            f"{sequence_number:03d}-R{revision_number}"
        )

    def _next_sequence_number(
        self,
        project_segment: str,
        phase_segment: str,
        category_segment: str,
    ) -> int:
        prefix = f"{project_segment}-{phase_segment}-{category_segment}-"
        queryset = Document.objects.filter(document_number__startswith=prefix)
        if self.pk:
            queryset = queryset.exclude(pk=self.pk)

        max_sequence = 0
        for number in queryset.values_list("document_number", flat=True):
            parts = number.split("-")
            if len(parts) != 5:
                continue
            if parts[0] != project_segment or parts[1] != phase_segment or parts[2] != category_segment:
                continue
            try:
                sequence = int(parts[3])
            except (TypeError, ValueError):
                continue
            max_sequence = max(max_sequence, sequence)
        return max_sequence + 1

    def save(self, *args, **kwargs):
        project_segment = self._project_segment()
        phase_segment = self._phase_segment()
        category_segment = self._category_segment()

        if self.sequence_number <= 0:
            self.sequence_number = self._next_sequence_number(
                project_segment=project_segment,
                phase_segment=phase_segment,
                category_segment=category_segment,
            )

        if self.current_version_id:
            self.revision_number = max(self.revision_number, self.current_version.version_major)

        self.document_number = self._build_document_number(
            project_segment=project_segment,
            phase_segment=phase_segment,
            category_segment=category_segment,
            sequence_number=self.sequence_number,
            revision_number=self.revision_number,
        )
        super().save(*args, **kwargs)


class DocumentVersion(models.Model):
    """Immutable file revision for a controlled document."""

    class ApprovalStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_doc_versions",
    )
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="versions",
    )
    version_major = models.PositiveIntegerField()
    version_minor = models.PositiveIntegerField(default=0)
    file_path = models.CharField(max_length=500)
    change_summary = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_document_versions",
    )
    approval_status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version_major", "-version_minor", "-uploaded_at"]
        indexes = [
            models.Index(fields=["organization", "-uploaded_at"], name="doc_ver_org_uploaded_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "version_major", "version_minor"],
                name="documents_unique_document_version_number",
            ),
        ]

    def __str__(self):
        return f"{self.document.document_number} v{self.version_major}.{self.version_minor}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        document = self.document
        should_update_document = (
            document.current_version_id is None
            or (self.version_major, self.version_minor) >= (
                document.current_version.version_major,
                document.current_version.version_minor,
            )
        )
        if should_update_document:
            document.current_version = self
            document.revision_number = max(document.revision_number, self.version_major)
            document.save()


class DocumentApproval(models.Model):
    """Approval decision recorded against a specific version."""

    class Decision(models.TextChoices):
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_doc_approvals",
    )
    document_version = models.ForeignKey(
        DocumentVersion,
        on_delete=models.CASCADE,
        related_name="approvals",
    )
    role = models.ForeignKey(
        DocumentOwnerRole,
        on_delete=models.PROTECT,
        related_name="document_approvals",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="document_approvals",
    )
    decision = models.CharField(max_length=20, choices=Decision.choices)
    comments = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["organization", "-timestamp"], name="doc_appr_org_ts_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["document_version", "user"],
                name="documents_unique_document_version_user_approval",
            ),
        ]

    def __str__(self):
        return f"{self.document_version} - {self.get_decision_display()}"


class DocumentExpiry(models.Model):
    """Expiration profile and alert switches for a document."""

    class TriggerCategory(models.TextChoices):
        BUILDING_PERMIT = "building_permit", "Building Permit Expiry"
        INSURANCE = "insurance", "Insurance Expiry"
        PERFORMANCE_BOND = "performance_bond", "Performance Bond Expiry"
        EIA_RENEWAL = "eia_renewal", "EIA Renewal"
        WARRANTY_END = "warranty_end", "Warranty End Date"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_doc_expiries",
    )
    document = models.OneToOneField(
        Document,
        on_delete=models.CASCADE,
        related_name="expiry",
    )
    trigger_category = models.CharField(
        max_length=40,
        choices=TriggerCategory.choices,
        default=TriggerCategory.BUILDING_PERMIT,
    )
    expiry_date = models.DateField()
    alert_90_days = models.BooleanField(default=True)
    alert_30_days = models.BooleanField(default=True)
    alert_expired = models.BooleanField(default=True)
    alert_90_days_sent_at = models.DateTimeField(null=True, blank=True)
    alert_30_days_sent_at = models.DateTimeField(null=True, blank=True)
    expired_alert_sent_at = models.DateTimeField(null=True, blank=True)
    escalated_at = models.DateTimeField(null=True, blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["expiry_date"]
        indexes = [
            models.Index(fields=["trigger_category", "expiry_date"]),
            models.Index(fields=["expiry_date", "alert_90_days", "alert_30_days", "alert_expired"]),
        ]

    def __str__(self):
        return f"{self.document.document_number} expires {self.expiry_date}"


class DocumentSearchIndex(models.Model):
    """Search index materialization for metadata and full-text retrieval."""

    class IndexStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        INDEXED = "indexed", "Indexed"
        FAILED = "failed", "Failed"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_doc_search_indices",
    )
    document = models.OneToOneField(
        Document,
        on_delete=models.CASCADE,
        related_name="search_index",
    )
    document_version = models.ForeignKey(
        DocumentVersion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="search_indexes",
    )
    extracted_text = models.TextField(blank=True)
    ocr_text = models.TextField(blank=True)
    clause_text = models.TextField(blank=True)
    indexed_clauses = models.JSONField(default=list, blank=True)
    combined_text = models.TextField(blank=True)
    search_vector = SearchVectorField(null=True, blank=True)
    content_hash = models.CharField(max_length=64, blank=True)
    index_status = models.CharField(
        max_length=20,
        choices=IndexStatus.choices,
        default=IndexStatus.PENDING,
    )
    indexed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-indexed_at", "-updated_at"]
        indexes = [
            GinIndex(fields=["search_vector"], name="documents_search_vector_gin"),
            models.Index(fields=["index_status", "updated_at"]),
        ]

    def __str__(self):
        return f"SearchIndex<{self.document.document_number}>"


class DocumentComment(models.Model):
    """Thread-safe comment log for collaboration on a document."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_doc_comments",
    )
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    document_version = models.ForeignKey(
        DocumentVersion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="comments",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="document_comments",
    )
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="doc_cmnt_org_created_idx"),
        ]

    def __str__(self):
        return f"Comment<{self.document.document_number}>"


class DocumentAuditEvent(models.Model):
    """Append-only document activity log for institutional traceability."""

    class EventType(models.TextChoices):
        DOCUMENT_CREATED = "document_created", "Document Created"
        METADATA_CHANGED = "metadata_changed", "Metadata Changed"
        VERSION_UPLOADED = "version_uploaded", "Version Uploaded"
        DOCUMENT_GENERATED = "document_generated", "Document Generated"
        APPROVAL_DECISION = "approval_decision", "Approval Decision"
        WORKFLOW_SUBMITTED = "workflow_submitted", "Workflow Submitted"
        WORKFLOW_STEP_DECISION = "workflow_step_decision", "Workflow Step Decision"
        COMMENT_ADDED = "comment_added", "Comment Added"
        DOCUMENT_DOWNLOADED = "document_downloaded", "Document Downloaded"
        DOCUMENT_SHARED = "document_shared", "Document Shared"
        SIGNATURE_REQUEST_SENT = "signature_request_sent", "Signature Request Sent"
        SIGNATURE_COMPLETED = "signature_completed", "Signature Completed"
        SIGNATURE_CANCELLED = "signature_cancelled", "Signature Cancelled"
        DOCUMENT_ARCHIVED = "document_archived", "Document Archived"
        DOCUMENT_SUPERSEDED = "document_superseded", "Document Superseded"
        DOCUMENT_DELETED = "document_deleted", "Document Deleted"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_doc_audit_events",
    )
    document = models.ForeignKey(
        Document,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    document_version = models.ForeignKey(
        DocumentVersion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    event_type = models.CharField(max_length=40, choices=EventType.choices)
    payload = models.JSONField(default=dict, blank=True)

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="document_audit_events",
    )
    actor_role = models.ForeignKey(
        "settings.Role",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="document_audit_events",
    )
    actor_role_name = models.CharField(max_length=120, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    document_number_snapshot = models.CharField(max_length=100, blank=True)
    document_title_snapshot = models.CharField(max_length=255, blank=True)
    version_label_snapshot = models.CharField(max_length=50, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["document", "created_at"]),
            models.Index(fields=["event_type", "created_at"]),
            models.Index(fields=["actor", "created_at"]),
        ]

    def __str__(self):
        return (
            f"{self.get_event_type_display()}::{self.document_number_snapshot or self.document_id or 'unknown'}"
        )

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("DocumentAuditEvent is immutable and cannot be updated.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("DocumentAuditEvent is immutable and cannot be deleted.")


class DocumentRoleScope(models.Model):
    """Role-level scoping constraints for document access control."""

    class ProjectScope(models.TextChoices):
        ALL_PROJECTS = "all_projects", "All Projects"
        ASSIGNED_PROJECTS = "assigned_projects", "Assigned Projects Only"

    class BusinessUnitScope(models.TextChoices):
        ALL_BUSINESS_UNITS = "all_business_units", "All Business Units"
        ASSIGNED_BUSINESS_UNITS = "assigned_business_units", "Assigned Business Units Only"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_doc_role_scopes",
    )
    role = models.OneToOneField(
        "settings.Role",
        on_delete=models.CASCADE,
        related_name="document_scope",
    )
    project_scope = models.CharField(
        max_length=30,
        choices=ProjectScope.choices,
        default=ProjectScope.ALL_PROJECTS,
    )
    business_unit_scope = models.CharField(
        max_length=30,
        choices=BusinessUnitScope.choices,
        default=BusinessUnitScope.ALL_BUSINESS_UNITS,
    )
    allowed_confidentiality_levels = models.JSONField(
        default=default_document_confidentiality_levels,
        help_text="Allowed values from Document.ConfidentialityLevel.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["role__name"]
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="doc_rscope_org_created_idx"),
        ]

    def __str__(self):
        return f"DocumentScope<{self.role.name}>"

    def clean(self):
        allowed_values = {
            Document.ConfidentialityLevel.PUBLIC,
            Document.ConfidentialityLevel.INTERNAL,
            Document.ConfidentialityLevel.CONFIDENTIAL,
            Document.ConfidentialityLevel.RESTRICTED,
        }
        invalid_levels = set(self.allowed_confidentiality_levels or []) - allowed_values
        if invalid_levels:
            raise ValidationError(
                {
                    "allowed_confidentiality_levels": (
                        "Invalid confidentiality level(s): "
                        + ", ".join(sorted(invalid_levels))
                    )
                }
            )

    def normalized_confidentiality_levels(self) -> list[str]:
        values = self.allowed_confidentiality_levels or []
        seen = set()
        normalized = []
        for level in values:
            if level in seen:
                continue
            seen.add(level)
            normalized.append(level)
        return normalized


class DocumentProjectMembership(models.Model):
    """Explicit user membership list used for project-scoped document access."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_doc_project_memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="document_project_memberships",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="document_memberships",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["project__name", "user__email"]
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="doc_pmem_org_created_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "project"],
                name="documents_unique_user_project_membership",
            ),
        ]

    def __str__(self):
        return f"{self.user} -> {self.project}"


class DocumentBusinessUnitMembership(models.Model):
    """User membership list for division/department-scoped document access."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_doc_business_unit_memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="document_business_unit_memberships",
    )
    division = models.ForeignKey(
        "settings.Division",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="document_memberships",
    )
    department = models.ForeignKey(
        "settings.Department",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="document_memberships",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["user__email", "division__name", "department__name"]
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="doc_bumem_org_created_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "division", "department"],
                name="documents_unique_user_business_unit_membership",
            ),
        ]

    def __str__(self):
        if self.department_id:
            label = self.department.name
        elif self.division_id:
            label = self.division.name
        else:
            label = "Unassigned"
        return f"{self.user} -> {label}"

    def clean(self):
        if not self.division_id and not self.department_id:
            raise ValidationError("Either division or department must be provided.")
        if self.department_id and self.division_id and self.department.division_id != self.division_id:
            raise ValidationError(
                {"department": "Selected department does not belong to selected division."}
            )


def default_workflow_confidentiality_levels():
    return ["public", "internal", "confidential", "restricted"]


def default_workflow_project_risk_ratings():
    return ["low", "medium", "high", "critical"]


class DocumentWorkflowTemplate(models.Model):
    """Approval template used to build workflow chains."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_doc_workflow_templates",
    )
    code = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=160, unique=True)
    description = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="doc_wftpl_org_created_idx"),
        ]

    def __str__(self):
        return self.name


class DocumentWorkflowTemplateStep(models.Model):
    """Ordered approval stage inside a workflow template."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_doc_workflow_template_steps",
    )
    template = models.ForeignKey(
        DocumentWorkflowTemplate,
        on_delete=models.CASCADE,
        related_name="steps",
    )
    sequence = models.PositiveIntegerField()
    approver_label = models.CharField(
        max_length=120,
        help_text="Human-readable stage owner label (e.g., Legal, Finance, COO).",
    )
    approver_role_slug = models.SlugField(
        max_length=120,
        blank=True,
        help_text="Optional settings.Role slug for strict role mapping.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["template", "sequence", "id"]
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="doc_wfts_org_created_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["template", "sequence"],
                name="documents_unique_workflow_template_step_sequence",
            ),
        ]

    def __str__(self):
        return f"{self.template.code}#{self.sequence} {self.approver_label}"


class DocumentWorkflowRule(models.Model):
    """Conditional routing rule that maps documents to templates."""

    class ProjectRiskRating(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_doc_workflow_rules",
    )
    name = models.CharField(max_length=160)
    template = models.ForeignKey(
        DocumentWorkflowTemplate,
        on_delete=models.CASCADE,
        related_name="rules",
    )
    document_type = models.ForeignKey(
        DocumentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="workflow_rules",
    )
    min_contract_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
    )
    max_contract_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
    )
    allowed_confidentiality_levels = models.JSONField(
        default=default_workflow_confidentiality_levels,
        help_text="Allowed document confidentiality levels for this rule.",
    )
    allowed_project_risk_ratings = models.JSONField(
        default=default_workflow_project_risk_ratings,
        help_text="Allowed project risk ratings for this rule.",
    )
    priority = models.PositiveIntegerField(
        default=100,
        help_text="Lower value is evaluated first.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["priority", "id"]
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="doc_wfrul_org_created_idx"),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        if self.min_contract_value is not None and self.max_contract_value is not None:
            if self.min_contract_value > self.max_contract_value:
                raise ValidationError(
                    {"max_contract_value": "max_contract_value must be greater than min_contract_value."}
                )

    def normalized_confidentiality_levels(self) -> list[str]:
        allowed_values = {
            Document.ConfidentialityLevel.PUBLIC,
            Document.ConfidentialityLevel.INTERNAL,
            Document.ConfidentialityLevel.CONFIDENTIAL,
            Document.ConfidentialityLevel.RESTRICTED,
        }
        result: list[str] = []
        seen: set[str] = set()
        for value in self.allowed_confidentiality_levels or []:
            if value not in allowed_values or value in seen:
                continue
            seen.add(value)
            result.append(value)
        return result

    def normalized_project_risk_ratings(self) -> list[str]:
        allowed_values = {
            self.ProjectRiskRating.LOW,
            self.ProjectRiskRating.MEDIUM,
            self.ProjectRiskRating.HIGH,
            self.ProjectRiskRating.CRITICAL,
        }
        result: list[str] = []
        seen: set[str] = set()
        for value in self.allowed_project_risk_ratings or []:
            if value not in allowed_values or value in seen:
                continue
            seen.add(value)
            result.append(value)
        return result


class DocumentWorkflowInstance(models.Model):
    """Runtime workflow instance for a specific document."""

    class State(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under Review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        SUPERSEDED = "superseded", "Superseded"
        ARCHIVED = "archived", "Archived"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_doc_workflow_instances",
    )
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="workflow_instances",
    )
    template = models.ForeignKey(
        DocumentWorkflowTemplate,
        on_delete=models.PROTECT,
        related_name="workflow_instances",
    )
    matched_rule = models.ForeignKey(
        DocumentWorkflowRule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="workflow_instances",
    )
    state = models.CharField(
        max_length=20,
        choices=State.choices,
        default=State.DRAFT,
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["document", "state"]),
            models.Index(
                fields=["organization", "-created_at"],
                name="doc_wfi_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"Workflow<{self.document.document_number}>:{self.state}"


class DocumentWorkflowStep(models.Model):
    """Runtime approval step generated from template steps."""

    class Decision(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_doc_workflow_steps",
    )
    workflow_instance = models.ForeignKey(
        DocumentWorkflowInstance,
        on_delete=models.CASCADE,
        related_name="steps",
    )
    sequence = models.PositiveIntegerField()
    approver_label = models.CharField(max_length=120)
    approver_role_slug = models.SlugField(max_length=120, blank=True)
    decision = models.CharField(
        max_length=20,
        choices=Decision.choices,
        default=Decision.PENDING,
    )
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="document_workflow_decisions",
    )
    comments = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["workflow_instance", "sequence", "id"]
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="doc_wfstp_org_created_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["workflow_instance", "sequence"],
                name="documents_unique_workflow_instance_step_sequence",
            ),
        ]

    def __str__(self):
        return f"{self.workflow_instance_id}#{self.sequence}:{self.decision}"


class DocumentSignatureRequest(models.Model):
    """Provider-agnostic e-signature request for a document version."""

    class Provider(models.TextChoices):
        DOCUSIGN = "docusign", "DocuSign"
        ADOBE_ACROBAT_SIGN = "adobe_acrobat_sign", "Adobe Acrobat Sign"
        DROPBOX_SIGN = "dropbox_sign", "Dropbox Sign"
        SIGNNOW = "signnow", "SignNow"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        COMPLETED = "completed", "Completed"
        DECLINED = "declined", "Declined"
        CANCELLED = "cancelled", "Cancelled"
        FAILED = "failed", "Failed"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_doc_signature_requests",
    )
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="signature_requests",
    )
    document_version = models.ForeignKey(
        DocumentVersion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="signature_requests",
    )
    provider = models.CharField(max_length=40, choices=Provider.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    provider_envelope_id = models.CharField(max_length=255, blank=True)
    signing_url = models.URLField(blank=True)
    signers = models.JSONField(
        default=list,
        blank=True,
        help_text="Signer rows: [{name, email, role, order, status}]",
    )
    subject = models.CharField(max_length=255, blank=True)
    message = models.TextField(blank=True)
    provider_payload = models.JSONField(default=dict, blank=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requested_document_signatures",
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-requested_at", "-id"]
        indexes = [
            models.Index(fields=["document", "status"]),
            models.Index(fields=["provider", "status"]),
            models.Index(fields=["requested_by", "requested_at"]),
            models.Index(
                fields=["organization", "status"],
                name="doc_sig_org_status_idx",
            ),
        ]

    def __str__(self):
        return f"Signature<{self.document.document_number}:{self.provider}:{self.status}>"


class DocumentGenerationRecord(models.Model):
    """Tracks automated, branded document generation output."""

    class GenerationKind(models.TextChoices):
        CONTRACT = "contract", "Contract"
        INVOICE = "invoice", "Invoice"
        REPORT = "report", "Report"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_doc_generation_records",
    )
    document = models.ForeignKey(
        Document,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generation_records",
    )
    document_version = models.ForeignKey(
        DocumentVersion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generation_records",
    )
    generation_kind = models.CharField(max_length=20, choices=GenerationKind.choices)
    title = models.CharField(max_length=255)
    template_code = models.CharField(max_length=120, blank=True)
    branding_snapshot = models.JSONField(default=dict, blank=True)
    context_payload = models.JSONField(default=dict, blank=True)
    file_path = models.CharField(max_length=500, blank=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_document_records",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["generation_kind", "created_at"]),
            models.Index(fields=["requested_by", "created_at"]),
            models.Index(fields=["document", "created_at"]),
        ]

    def __str__(self):
        return f"Generated<{self.generation_kind}:{self.title}>"
