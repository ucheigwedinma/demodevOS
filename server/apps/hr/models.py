import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.accounts.models import Organization
from apps.settings.currency import get_default_currency_code

# Categories that count as "contract" documents for HR
CONTRACT_CATEGORIES = {
    "employment_contract",
    "contract_amendment",
    "contract_renewal",
    "nda",
    "non_compete",
}


def hr_id_document_upload_to(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "pdf"
    return f"hr/id-documents/{instance.user_id}/{uuid.uuid4()}.{ext}"


def hr_document_upload_to(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "pdf"
    return f"hr/documents/{instance.user_id}/{uuid.uuid4()}.{ext}"


def hr_resume_upload_to(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "pdf"
    return f"hr/resumes/{uuid.uuid4()}.{ext}"


def hr_offer_letter_upload_to(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "pdf"
    return f"hr/offer-letters/{uuid.uuid4()}.{ext}"


class Team(models.Model):
    """Operational team within a department."""

    class TeamType(models.TextChoices):
        PERMANENT = "permanent", "Permanent"
        PROJECT_BASED = "project_based", "Project-Based"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="teams",
    )
    department = models.ForeignKey(
        "settings.Department",
        on_delete=models.CASCADE,
        related_name="teams",
    )
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, blank=True)
    description = models.TextField(blank=True)
    team_type = models.CharField(
        max_length=20,
        choices=TeamType.choices,
        default=TeamType.PERMANENT,
    )
    lead = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="led_teams",
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]
        unique_together = [("department", "code")]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_team_org_created_idx",
            ),
        ]

    def __str__(self):
        return self.name


class PositionRole(models.Model):
    """Reusable functional role template shared by one or more positions."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="position_roles",
    )
    name = models.CharField(max_length=200)
    grade = models.CharField(max_length=50, blank=True)
    code = models.CharField(max_length=30, blank=True)
    description = models.TextField(blank=True)
    requirements = models.TextField(blank=True)
    key_responsibilities = models.TextField(blank=True)
    hard_skills = models.JSONField(default=list, blank=True)
    soft_skills = models.JSONField(default=list, blank=True)
    kpi_metrics = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_prol_org_created_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"],
                condition=~models.Q(code=""),
                name="hr_positionrole_org_code_uniq",
            ),
        ]

    def __str__(self):
        if self.code:
            return f"{self.code} — {self.name}"
        return self.name


class Position(models.Model):
    """Formal position definition within the organization hierarchy."""

    class EmploymentType(models.TextChoices):
        FULL_TIME = "full_time", "Full-Time"
        PART_TIME = "part_time", "Part-Time"
        CONTRACT = "contract", "Contract"
        TEMPORARY = "temporary", "Temporary"
        INTERN = "intern", "Intern"

    class Level(models.TextChoices):
        INTERN = "intern", "Intern"
        JUNIOR = "junior", "Junior"
        MID = "mid", "Mid-Level"
        SENIOR = "senior", "Senior"
        LEAD = "lead", "Lead"
        MANAGER = "manager", "Manager"
        DIRECTOR = "director", "Director"
        VP = "vp", "Vice President"
        C_SUITE = "c_suite", "C-Suite"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        FROZEN = "frozen", "Frozen"
        ABOLISHED = "abolished", "Abolished"

    class SlotStatus(models.TextChoices):
        VACANT = "vacant", "Vacant"
        FILLED = "filled", "Filled"
        PROPOSED = "proposed", "Proposed"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="positions",
    )
    role = models.ForeignKey(
        PositionRole,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="positions",
    )
    title = models.CharField(max_length=200)
    code = models.CharField(max_length=30)
    department = models.ForeignKey(
        "settings.Department",
        on_delete=models.CASCADE,
        related_name="positions",
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="positions",
    )
    reports_to = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="direct_reports",
    )
    cost_center = models.ForeignKey(
        "settings.CostCenter",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="positions",
    )
    salary_structure = models.ForeignKey(
        "SalaryStructure",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="positions",
    )
    employment_type = models.CharField(
        max_length=20,
        choices=EmploymentType.choices,
        default=EmploymentType.FULL_TIME,
    )
    level = models.CharField(
        max_length=10,
        choices=Level.choices,
        default=Level.MID,
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    slot_status = models.CharField(
        max_length=10,
        choices=SlotStatus.choices,
        default=SlotStatus.PROPOSED,
    )
    criticality_score = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="0-100 score used to identify succession-critical roles.",
    )
    vacant_since = models.DateField(
        null=True,
        blank=True,
        help_text="Date the position last became vacant.",
    )
    vacancy_alert_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp for last critical vacancy escalation alert.",
    )
    description = models.TextField(blank=True)
    requirements = models.TextField(blank=True)
    headcount_budget = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["department", "level", "title"]
        unique_together = [("organization", "code")]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="hr_pos_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_pos_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.code} — {self.title}"


class PositionAssignment(models.Model):
    """Links a user to a position with an effective date range."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="position_assignments",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="position_assignments",
    )
    position = models.ForeignKey(
        Position,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_primary = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date"]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_pasn_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} → {self.position.title}"


class PositionBudget(models.Model):
    """Annual headcount planning per department / position."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        APPROVED = "approved", "Approved"
        FROZEN = "frozen", "Frozen"

    class BudgetSource(models.TextChoices):
        CORPORATE_OVERHEAD = "corporate_overhead", "Corporate Overhead (Fixed)"
        PROJECT_FUNDING = "project_funding", "Project Loan / Investor Fund (Variable)"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="position_budgets",
    )
    department = models.ForeignKey(
        "settings.Department",
        on_delete=models.CASCADE,
        related_name="position_budgets",
    )
    position = models.ForeignKey(
        Position,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="budgets",
    )
    fiscal_period_label = models.CharField(
        max_length=120,
        blank=True,
        default="",
    )
    fiscal_year = models.IntegerField()
    budget_source = models.CharField(
        max_length=30,
        choices=BudgetSource.choices,
        default=BudgetSource.CORPORATE_OVERHEAD,
    )
    currency = models.CharField(max_length=3, default=get_default_currency_code)
    fte = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=1.00,
        validators=[MinValueValidator(0.10), MaxValueValidator(2.00)],
        help_text="Full-time equivalent allocation for this position budget row.",
    )
    statutory_benefits_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=15.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Statutory burden percentage applied on base salary.",
    )
    allowances_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Allowance burden percentage applied on base salary.",
    )
    local_tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Local payroll tax burden percentage applied on base salary.",
    )
    insurance_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Insurance burden percentage applied on base salary.",
    )
    approved_headcount = models.PositiveIntegerField(default=0)
    filled_headcount = models.PositiveIntegerField(default=0)
    budget_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    notes = models.TextField(blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_position_budgets",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fiscal_year", "department"]
        unique_together = [("organization", "department", "position", "fiscal_year")]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="hr_pbud_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_pbud_org_created_idx",
            ),
        ]

    def __str__(self):
        pos = self.position.title if self.position else "All"
        period = self.fiscal_period_label or f"FY{self.fiscal_year}"
        return f"{period} — {self.department.name} / {pos}"


class PositionBudgetRevision(models.Model):
    """Formal revision workflow for changes on locked/approved position budgets."""

    class Status(models.TextChoices):
        PENDING_APPROVAL = "pending_approval", "Pending Approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="position_budget_revisions",
    )
    budget = models.ForeignKey(
        PositionBudget,
        on_delete=models.CASCADE,
        related_name="revisions",
    )
    revision_number = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING_APPROVAL,
    )
    reason = models.TextField()
    proposed_changes = models.JSONField(default=dict, blank=True)
    snapshot_before = models.JSONField(default=dict, blank=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requested_position_budget_revisions",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_position_budget_revisions",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("budget", "revision_number")]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="hr_pbr_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_pbr_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"Revision {self.revision_number} — Budget #{self.budget_id}"


class Vacancy(models.Model):
    """Open position requiring recruitment."""

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        ON_HOLD = "on_hold", "On Hold"
        FILLED = "filled", "Filled"
        CANCELLED = "cancelled", "Cancelled"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="vacancies",
    )
    position = models.ForeignKey(
        Position,
        on_delete=models.CASCADE,
        related_name="vacancies",
    )
    title = models.CharField(max_length=200)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.OPEN,
    )
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    hiring_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_vacancies",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_vacancies",
    )
    opened_date = models.DateField(auto_now_add=True)
    target_fill_date = models.DateField(null=True, blank=True)
    filled_date = models.DateField(null=True, blank=True)
    filled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="filled_vacancies",
        help_text="The user who was hired to fill this vacancy.",
    )
    reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-opened_date"]
        verbose_name_plural = "vacancies"
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="hr_vac_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_vac_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"


# ---------------------------------------------------------------------------
# Employee Directory models
# ---------------------------------------------------------------------------


class EmployeeRecord(models.Model):
    """HR-specific employment data linked 1:1 to a user."""

    class EmploymentStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        ON_LEAVE = "on_leave", "On Leave"
        PROBATION = "probation", "Probation"
        NOTICE_PERIOD = "notice_period", "Notice Period"
        TERMINATED = "terminated", "Terminated"
        RESIGNED = "resigned", "Resigned"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="employee_records",
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="employee_record",
    )
    hire_date = models.DateField(null=True, blank=True)
    probation_end_date = models.DateField(null=True, blank=True)
    contract_start_date = models.DateField(null=True, blank=True)
    contract_end_date = models.DateField(null=True, blank=True)
    contract_type = models.CharField(max_length=30, blank=True)
    employment_status = models.CharField(
        max_length=20,
        choices=EmploymentStatus.choices,
        default=EmploymentStatus.ACTIVE,
    )
    termination_date = models.DateField(null=True, blank=True)
    termination_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("organization", "user")]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_erec_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} — {self.get_employment_status_display()}"


class EmergencyContact(models.Model):
    """Emergency contact for an employee."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="emergency_contacts",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="emergency_contacts",
    )
    name = models.CharField(max_length=200)
    relationship = models.CharField(max_length=50, blank=True)
    phone = models.CharField(max_length=50)
    secondary_phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    is_primary = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_econ_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.relationship})"


class IdentificationDocument(models.Model):
    """Government-issued or official identification document for an employee."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="identification_documents",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="identification_documents",
    )
    document_type = models.CharField(max_length=50)
    document_number = models.CharField(max_length=100)
    issuing_authority = models.CharField(max_length=200, blank=True)
    issuing_country = models.CharField(max_length=100, blank=True)
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    file = models.FileField(upload_to=hr_id_document_upload_to, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-issue_date"]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_idoc_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.document_type} — {self.document_number}"


class CompensationRecord(models.Model):
    """Compensation package effective for a date range."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        SUPERSEDED = "superseded", "Superseded"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="compensation_records",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="compensation_records",
    )
    effective_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    base_salary = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3, default=get_default_currency_code)
    pay_frequency = models.CharField(max_length=20, blank=True)
    allowances = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    bonus = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_package = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_compensation_records",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-effective_date"]
        unique_together = [("organization", "user", "effective_date")]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="hr_comp_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_comp_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} — {self.effective_date}"


class HRDocument(models.Model):
    """HR document or attachment linked to an employee."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="hr_documents",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="hr_documents",
    )
    title = models.CharField(max_length=300)
    category = models.CharField(max_length=50, blank=True)
    file = models.FileField(upload_to=hr_document_upload_to)
    file_size = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_hr_documents",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_hdoc_org_created_idx",
            ),
        ]

    def __str__(self):
        return self.title


# ---------------------------------------------------------------------------
# Recruitment & Hiring models
# ---------------------------------------------------------------------------


class JobRequisition(models.Model):
    """Formal request to fill a position — triggers approval workflow."""

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING_APPROVAL = "pending_approval", "Pending Approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"
        FILLED = "filled", "Filled"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="job_requisitions",
    )
    title = models.CharField(max_length=200)
    position = models.ForeignKey(
        Position,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requisitions",
    )
    vacancy = models.ForeignKey(
        Vacancy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requisitions",
    )
    department = models.ForeignKey(
        "settings.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="job_requisitions",
    )
    requisition_type = models.CharField(max_length=30, blank=True)
    justification = models.TextField(blank=True)
    headcount_requested = models.PositiveIntegerField(default=1)
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    salary_range_min = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
    )
    salary_range_max = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
    )
    currency = models.CharField(max_length=3, default=get_default_currency_code)
    target_start_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="requested_requisitions",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_requisitions",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="hr_jreq_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_jreq_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"


class JobListing(models.Model):
    """Published job posting derived from an approved requisition."""

    class SalaryDisplay(models.TextChoices):
        HIDDEN = "hidden", "Hidden"
        RANGE = "range", "Range"
        EXACT = "exact", "Exact"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        CLOSED = "closed", "Closed"
        ARCHIVED = "archived", "Archived"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="job_listings",
    )
    requisition = models.ForeignKey(
        JobRequisition,
        on_delete=models.CASCADE,
        related_name="listings",
    )
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    requirements = models.TextField(blank=True)
    location = models.CharField(max_length=200, blank=True)
    employment_type = models.CharField(max_length=20, blank=True)
    salary_display = models.CharField(
        max_length=10,
        choices=SalaryDisplay.choices,
        default=SalaryDisplay.HIDDEN,
    )
    salary_min = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
    )
    salary_max = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
    )
    currency = models.CharField(max_length=3, default=get_default_currency_code)
    is_internal = models.BooleanField(default=False)
    is_external = models.BooleanField(default=True)
    posted_date = models.DateField(null=True, blank=True)
    closing_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posted_job_listings",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-posted_date", "-created_at"]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="hr_jlst_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_jlst_org_created_idx",
            ),
        ]

    def __str__(self):
        return self.title


class Candidate(models.Model):
    """Applicant tracking through the recruitment pipeline."""

    class Stage(models.TextChoices):
        APPLIED = "applied", "Applied"
        SCREENING = "screening", "Screening"
        SHORTLISTED = "shortlisted", "Shortlisted"
        INTERVIEWING = "interviewing", "Interviewing"
        EVALUATED = "evaluated", "Evaluated"
        OFFER_PENDING = "offer_pending", "Offer Pending"
        HIRED = "hired", "Hired"
        REJECTED = "rejected", "Rejected"
        WITHDRAWN = "withdrawn", "Withdrawn"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="candidates",
    )
    job_listing = models.ForeignKey(
        JobListing,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="candidates",
    )
    job_requisition = models.ForeignKey(
        JobRequisition,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="candidates",
    )
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=50, blank=True)
    source = models.CharField(max_length=30, blank=True)
    referred_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="referred_candidates",
    )
    resume = models.FileField(upload_to=hr_resume_upload_to, null=True, blank=True)
    current_title = models.CharField(max_length=200, blank=True)
    current_employer = models.CharField(max_length=200, blank=True)
    expected_salary = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
    )
    currency = models.CharField(max_length=3, default=get_default_currency_code)
    stage = models.CharField(
        max_length=20,
        choices=Stage.choices,
        default=Stage.APPLIED,
    )
    applied_date = models.DateField(auto_now_add=True)
    rejection_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-applied_date"]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_cand_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Interview(models.Model):
    """Scheduled interview for a candidate."""

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        NO_SHOW = "no_show", "No Show"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="interviews",
    )
    candidate = models.ForeignKey(
        Candidate,
        on_delete=models.CASCADE,
        related_name="interviews",
    )
    interview_type = models.CharField(max_length=30, blank=True)
    interviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conducted_interviews",
    )
    scheduled_date = models.DateField()
    scheduled_time = models.TimeField()
    duration_minutes = models.PositiveIntegerField(default=60)
    location = models.CharField(max_length=200, blank=True)
    meeting_link = models.URLField(blank=True)
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.SCHEDULED,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-scheduled_date", "-scheduled_time"]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="hr_intv_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_intv_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"Interview: {self.candidate} — {self.scheduled_date}"


class CandidateEvaluation(models.Model):
    """Evaluation or feedback for a candidate, optionally linked to an interview."""

    class Recommendation(models.TextChoices):
        STRONGLY_HIRE = "strongly_hire", "Strongly Hire"
        HIRE = "hire", "Hire"
        MAYBE = "maybe", "Maybe"
        NO_HIRE = "no_hire", "No Hire"
        STRONGLY_NO_HIRE = "strongly_no_hire", "Strongly No Hire"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="candidate_evaluations",
    )
    candidate = models.ForeignKey(
        Candidate,
        on_delete=models.CASCADE,
        related_name="evaluations",
    )
    interview = models.ForeignKey(
        Interview,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="evaluations",
    )
    evaluator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="candidate_evaluations",
    )
    overall_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    recommendation = models.CharField(
        max_length=20,
        choices=Recommendation.choices,
    )
    strengths = models.TextField(blank=True)
    concerns = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    evaluated_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-evaluated_at"]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_cevl_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"Eval: {self.candidate} — {self.get_recommendation_display()}"


class JobOffer(models.Model):
    """Job offer extended to a candidate — triggers approval workflow."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING_APPROVAL = "pending_approval", "Pending Approval"
        APPROVED = "approved", "Approved"
        EXTENDED = "extended", "Extended"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        WITHDRAWN = "withdrawn", "Withdrawn"
        EXPIRED = "expired", "Expired"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="job_offers",
    )
    candidate = models.ForeignKey(
        Candidate,
        on_delete=models.CASCADE,
        related_name="offers",
    )
    requisition = models.ForeignKey(
        JobRequisition,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="offers",
    )
    position = models.ForeignKey(
        Position,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="job_offers",
    )
    offered_salary = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3, default=get_default_currency_code)
    start_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    offer_letter = models.FileField(
        upload_to=hr_offer_letter_upload_to, null=True, blank=True,
    )
    terms = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_job_offers",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    cfo_override_approved = models.BooleanField(
        default=False,
        help_text="Set when CFO-approved salary override is granted.",
    )
    cfo_override_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cfo_overridden_job_offers",
    )
    cfo_override_at = models.DateTimeField(null=True, blank=True)
    cfo_override_reason = models.TextField(blank=True)
    extended_at = models.DateTimeField(null=True, blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    response_notes = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("organization", "candidate", "requisition")]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="hr_jofr_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_jofr_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"Offer: {self.candidate} — {self.get_status_display()}"


# ---------------------------------------------------------------------------
# Onboarding models
# ---------------------------------------------------------------------------


def hr_onboarding_document_upload_to(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "pdf"
    return f"hr/onboarding-documents/{instance.employee_id}/{uuid.uuid4()}.{ext}"


class OnboardingTemplate(models.Model):
    """Reusable onboarding checklist template for a department/position."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="onboarding_templates",
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    department = models.ForeignKey(
        "settings.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="onboarding_templates",
    )
    position = models.ForeignKey(
        Position,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="onboarding_templates",
    )
    is_active = models.BooleanField(default=True)
    task_count = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_onboarding_templates",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_obtpl_org_created_idx",
            ),
        ]

    def __str__(self):
        return self.name


class OnboardingTask(models.Model):
    """Individual onboarding task assigned to a new employee."""

    class Category(models.TextChoices):
        DOCUMENTATION = "documentation", "Documentation"
        TRAINING = "training", "Training"
        ACCESS = "access", "Access Setup"
        INTRODUCTION = "introduction", "Introduction"
        COMPLIANCE = "compliance", "Compliance"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        SKIPPED = "skipped", "Skipped"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="onboarding_tasks",
    )
    employee = models.ForeignKey(
        EmployeeRecord,
        on_delete=models.CASCADE,
        related_name="onboarding_tasks",
    )
    template = models.ForeignKey(
        OnboardingTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
    )
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.OTHER,
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_onboarding_tasks",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    is_required = models.BooleanField(default=True)
    due_date = models.DateField(null=True, blank=True)
    completed_date = models.DateField(null=True, blank=True)
    sort_order = models.IntegerField(default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "title"]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="hr_obtsk_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_obtsk_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.title} — {self.get_status_display()}"


class DocumentCollectionItem(models.Model):
    """Document request for a new employee during onboarding."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUBMITTED = "submitted", "Submitted"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="document_collection_items",
    )
    employee = models.ForeignKey(
        EmployeeRecord,
        on_delete=models.CASCADE,
        related_name="document_collection_items",
    )
    document_name = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    file = models.FileField(
        upload_to=hr_onboarding_document_upload_to,
        null=True,
        blank=True,
    )
    due_date = models.DateField(null=True, blank=True)
    submitted_date = models.DateField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_document_collections",
    )
    verified_date = models.DateField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="hr_dci_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_dci_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.document_name} — {self.get_status_display()}"


class EquipmentAllocation(models.Model):
    """Equipment or asset allocated to an employee during onboarding."""

    class Category(models.TextChoices):
        LAPTOP = "laptop", "Laptop"
        PHONE = "phone", "Phone"
        ACCESS_CARD = "access_card", "Access Card"
        DESK = "desk", "Desk"
        VEHICLE = "vehicle", "Vehicle"
        UNIFORM = "uniform", "Uniform"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ALLOCATED = "allocated", "Allocated"
        RETURNED = "returned", "Returned"
        LOST = "lost", "Lost"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="equipment_allocations",
    )
    employee = models.ForeignKey(
        EmployeeRecord,
        on_delete=models.CASCADE,
        related_name="equipment_allocations",
    )
    item_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.OTHER,
    )
    serial_number = models.CharField(max_length=100, blank=True)
    asset_tag = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    allocated_date = models.DateField(null=True, blank=True)
    return_date = models.DateField(null=True, blank=True)
    allocated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="allocated_equipment",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="hr_eqal_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_eqal_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.item_name} ({self.get_status_display()})"


class OrientationChecklistItem(models.Model):
    """Orientation checklist item for an employee."""

    class Category(models.TextChoices):
        COMPANY_OVERVIEW = "company_overview", "Company Overview"
        TEAM_INTRODUCTION = "team_introduction", "Team Introduction"
        SYSTEM_TRAINING = "system_training", "System Training"
        SAFETY_TRAINING = "safety_training", "Safety Training"
        POLICY_REVIEW = "policy_review", "Policy Review"
        FACILITY_TOUR = "facility_tour", "Facility Tour"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="orientation_checklist_items",
    )
    employee = models.ForeignKey(
        EmployeeRecord,
        on_delete=models.CASCADE,
        related_name="orientation_checklist_items",
    )
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.COMPANY_OVERVIEW,
    )
    is_completed = models.BooleanField(default=False)
    completed_date = models.DateField(null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="completed_orientation_items",
    )
    sort_order = models.IntegerField(default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "title"]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_oci_org_created_idx",
            ),
        ]

    def __str__(self):
        return self.title


class ProbationRecord(models.Model):
    """Probation tracking for a new employee."""

    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "In Progress"
        PASSED = "passed", "Passed"
        FAILED = "failed", "Failed"
        EXTENDED = "extended", "Extended"

    class Recommendation(models.TextChoices):
        CONFIRM = "confirm", "Confirm Employment"
        EXTEND = "extend", "Extend Probation"
        TERMINATE = "terminate", "Terminate"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="probation_records",
    )
    employee = models.OneToOneField(
        EmployeeRecord,
        on_delete=models.CASCADE,
        related_name="probation_record",
    )
    start_date = models.DateField()
    end_date = models.DateField()
    extended_end_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.IN_PROGRESS,
    )
    review_date = models.DateField(null=True, blank=True)
    next_review_date = models.DateField(null=True, blank=True)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_probation_records",
    )
    performance_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
    )
    recommendation = models.CharField(
        max_length=10,
        choices=Recommendation.choices,
        blank=True,
    )
    notes = models.TextField(blank=True)
    outcome_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date"]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="hr_prob_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_prob_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"Probation: {self.employee.user.get_full_name()} — {self.get_status_display()}"


# ---------------------------------------------------------------------------
# Performance Management models
# ---------------------------------------------------------------------------


class PerformanceGoal(models.Model):
    """OKR/KPI goal for an employee."""

    class GoalType(models.TextChoices):
        OKR = "okr", "OKR"
        KPI = "kpi", "KPI"
        PROJECT = "project", "Project Goal"
        DEVELOPMENT = "development", "Development"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="performance_goals",
    )
    employee = models.ForeignKey(
        EmployeeRecord,
        on_delete=models.CASCADE,
        related_name="performance_goals",
    )
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    goal_type = models.CharField(
        max_length=15,
        choices=GoalType.choices,
        default=GoalType.KPI,
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    target_value = models.CharField(max_length=200, blank=True)
    current_value = models.CharField(max_length=200, blank=True)
    unit = models.CharField(max_length=50, blank=True)
    weight = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    completed_date = models.DateField(null=True, blank=True)
    progress = models.PositiveIntegerField(default=0)
    parent_goal = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sub_goals",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="hr_pgoal_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_pgoal_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_goal_type_display()})"


class PerformanceReview(models.Model):
    """Formal periodic performance review for an employee."""

    class ReviewType(models.TextChoices):
        ANNUAL = "annual", "Annual"
        SEMI_ANNUAL = "semi_annual", "Semi-Annual"
        QUARTERLY = "quarterly", "Quarterly"
        PROBATION = "probation", "Probation Review"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        IN_PROGRESS = "in_progress", "In Progress"
        SUBMITTED = "submitted", "Submitted"
        ACKNOWLEDGED = "acknowledged", "Acknowledged"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="performance_reviews",
    )
    employee = models.ForeignKey(
        EmployeeRecord,
        on_delete=models.CASCADE,
        related_name="performance_reviews",
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conducted_reviews",
    )
    review_type = models.CharField(
        max_length=15,
        choices=ReviewType.choices,
        default=ReviewType.ANNUAL,
    )
    review_period_start = models.DateField()
    review_period_end = models.DateField()
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    overall_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
    )
    strengths = models.TextField(blank=True)
    areas_for_improvement = models.TextField(blank=True)
    goals_summary = models.TextField(blank=True)
    employee_comments = models.TextField(blank=True)
    reviewer_comments = models.TextField(blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-review_period_end"]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="hr_prev_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_prev_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"Review: {self.employee.user.get_full_name()} — {self.review_period_end}"


class ContinuousFeedback(models.Model):
    """Ongoing feedback entries (not tied to a formal review cycle)."""

    class FeedbackType(models.TextChoices):
        PRAISE = "praise", "Praise"
        CONSTRUCTIVE = "constructive", "Constructive"
        SUGGESTION = "suggestion", "Suggestion"
        CONCERN = "concern", "Concern"

    class Visibility(models.TextChoices):
        PRIVATE = "private", "Private"
        MANAGER = "manager", "Manager Only"
        PUBLIC = "public", "Public"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="continuous_feedback",
    )
    employee = models.ForeignKey(
        EmployeeRecord,
        on_delete=models.CASCADE,
        related_name="received_feedback",
    )
    given_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="given_feedback",
    )
    feedback_type = models.CharField(
        max_length=15,
        choices=FeedbackType.choices,
        default=FeedbackType.PRAISE,
    )
    visibility = models.CharField(
        max_length=10,
        choices=Visibility.choices,
        default=Visibility.MANAGER,
    )
    subject = models.CharField(max_length=300)
    content = models.TextField()
    is_anonymous = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "continuous feedback"
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_cfb_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.get_feedback_type_display()}: {self.subject}"


class ManagerEvaluation(models.Model):
    """Manager's structured evaluation of a direct report."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="manager_evaluations",
    )
    employee = models.ForeignKey(
        EmployeeRecord,
        on_delete=models.CASCADE,
        related_name="manager_evaluations",
    )
    review = models.ForeignKey(
        PerformanceReview,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="manager_evaluations",
    )
    evaluator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="manager_evaluations_given",
    )
    evaluation_date = models.DateField()
    overall_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    leadership_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
    )
    communication_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
    )
    technical_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
    )
    teamwork_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
    )
    strengths = models.TextField(blank=True)
    areas_for_improvement = models.TextField(blank=True)
    goals_for_next_period = models.TextField(blank=True)
    comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-evaluation_date"]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_mevl_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"Manager Eval: {self.employee.user.get_full_name()} — {self.evaluation_date}"


class PeerReview(models.Model):
    """Peer review feedback for an employee."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUBMITTED = "submitted", "Submitted"
        DECLINED = "declined", "Declined"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="peer_reviews",
    )
    employee = models.ForeignKey(
        EmployeeRecord,
        on_delete=models.CASCADE,
        related_name="peer_reviews_received",
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="peer_reviews_given",
    )
    review = models.ForeignKey(
        PerformanceReview,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="peer_reviews",
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    overall_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
    )
    collaboration_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
    )
    communication_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
    )
    strengths = models.TextField(blank=True)
    areas_for_improvement = models.TextField(blank=True)
    comments = models.TextField(blank=True)
    is_anonymous = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="hr_peer_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_peer_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"Peer Review: {self.employee.user.get_full_name()} by {self.reviewer.get_full_name()}"


class PerformanceImprovementPlan(models.Model):
    """Formal PIP for an underperforming employee."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        EXTENDED = "extended", "Extended"
        TERMINATED = "terminated", "Terminated"

    class Outcome(models.TextChoices):
        IMPROVED = "improved", "Improved"
        NO_IMPROVEMENT = "no_improvement", "No Improvement"
        PARTIAL = "partial", "Partial Improvement"
        TERMINATED = "terminated", "Employment Terminated"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="performance_improvement_plans",
    )
    employee = models.ForeignKey(
        EmployeeRecord,
        on_delete=models.CASCADE,
        related_name="pips",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_pips",
    )
    title = models.CharField(max_length=300)
    reason = models.TextField()
    objectives = models.TextField()
    support_provided = models.TextField(blank=True)
    success_criteria = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    extended_end_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    outcome = models.CharField(
        max_length=15,
        choices=Outcome.choices,
        blank=True,
    )
    outcome_notes = models.TextField(blank=True)
    review_dates = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="hr_pip_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_pip_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"PIP: {self.employee.user.get_full_name()} — {self.get_status_display()}"


# ---------------------------------------------------------------------------
# Skills & Capability Management models
# ---------------------------------------------------------------------------


def hr_certification_upload_to(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "pdf"
    return f"hr/certifications/{instance.employee_id}/{uuid.uuid4()}.{ext}"


def hr_license_upload_to(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "pdf"
    return f"hr/licenses/{instance.employee_id}/{uuid.uuid4()}.{ext}"


def hr_training_upload_to(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "pdf"
    return f"hr/training-records/{instance.employee_id}/{uuid.uuid4()}.{ext}"


class Skill(models.Model):
    """Skill definition for the organisation-wide skills matrix."""

    class Category(models.TextChoices):
        TECHNICAL = "technical", "Technical"
        MANAGEMENT = "management", "Management"
        SOFT = "soft", "Soft Skill"
        DOMAIN = "domain", "Domain Knowledge"
        REGULATORY = "regulatory", "Regulatory"

    class ProficiencyLevel(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"
        EXPERT = "expert", "Expert"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="skills",
    )
    employee = models.ForeignKey(
        EmployeeRecord,
        on_delete=models.CASCADE,
        related_name="skills",
    )
    name = models.CharField(max_length=200)
    category = models.CharField(
        max_length=15,
        choices=Category.choices,
        default=Category.TECHNICAL,
    )
    proficiency = models.CharField(
        max_length=15,
        choices=ProficiencyLevel.choices,
        default=ProficiencyLevel.BEGINNER,
    )
    years_experience = models.DecimalField(
        max_digits=4, decimal_places=1, default=0,
    )
    is_primary = models.BooleanField(default=False)
    verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_skills",
    )
    verified_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "name"]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_skill_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.name} — {self.get_proficiency_display()}"


class Certification(models.Model):
    """Professional certification held by an employee."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        PENDING = "pending", "Pending"
        REVOKED = "revoked", "Revoked"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="certifications",
    )
    employee = models.ForeignKey(
        EmployeeRecord,
        on_delete=models.CASCADE,
        related_name="certifications",
    )
    name = models.CharField(max_length=300)
    issuing_body = models.CharField(max_length=300)
    credential_id = models.CharField(max_length=200, blank=True)
    issue_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    verification_url = models.URLField(blank=True)
    attachment = models.FileField(upload_to=hr_certification_upload_to, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-issue_date"]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="hr_cert_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_cert_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.name} — {self.employee.user.get_full_name()}"


class ProfessionalLicense(models.Model):
    """Professional or regulatory licence held by an employee."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        PENDING = "pending", "Pending Renewal"
        SUSPENDED = "suspended", "Suspended"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="professional_licenses",
    )
    employee = models.ForeignKey(
        EmployeeRecord,
        on_delete=models.CASCADE,
        related_name="professional_licenses",
    )
    license_type = models.CharField(max_length=200)
    license_number = models.CharField(max_length=200)
    issuing_authority = models.CharField(max_length=300)
    jurisdiction = models.CharField(max_length=200, blank=True)
    issue_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    is_mandatory = models.BooleanField(default=False)
    attachment = models.FileField(upload_to=hr_license_upload_to, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-issue_date"]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="hr_plic_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_plic_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.license_type} #{self.license_number}"


class CompetencyAssessment(models.Model):
    """Competency assessment for an employee."""

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="competency_assessments",
    )
    employee = models.ForeignKey(
        EmployeeRecord,
        on_delete=models.CASCADE,
        related_name="competency_assessments",
    )
    assessor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conducted_assessments",
    )
    competency_area = models.CharField(max_length=200)
    assessment_date = models.DateField()
    score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
    )
    max_score = models.DecimalField(
        max_digits=5, decimal_places=2, default=100,
    )
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.SCHEDULED,
    )
    strengths = models.TextField(blank=True)
    gaps = models.TextField(blank=True)
    development_plan = models.TextField(blank=True)
    next_assessment_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-assessment_date"]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="hr_cass_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_cass_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.competency_area} — {self.employee.user.get_full_name()}"


class TrainingRecord(models.Model):
    """Training course or programme completed by an employee."""

    class Status(models.TextChoices):
        ENROLLED = "enrolled", "Enrolled"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    class DeliveryMethod(models.TextChoices):
        IN_PERSON = "in_person", "In-Person"
        ONLINE = "online", "Online"
        HYBRID = "hybrid", "Hybrid"
        SELF_PACED = "self_paced", "Self-Paced"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="training_records",
    )
    employee = models.ForeignKey(
        EmployeeRecord,
        on_delete=models.CASCADE,
        related_name="training_records",
    )
    title = models.CharField(max_length=300)
    provider = models.CharField(max_length=300, blank=True)
    delivery_method = models.CharField(
        max_length=15,
        choices=DeliveryMethod.choices,
        default=DeliveryMethod.IN_PERSON,
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    duration_hours = models.DecimalField(
        max_digits=6, decimal_places=1, null=True, blank=True,
    )
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.ENROLLED,
    )
    score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
    )
    cost = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
    )
    currency = models.CharField(max_length=3, default=get_default_currency_code)
    certificate = models.FileField(upload_to=hr_training_upload_to, null=True, blank=True)
    is_mandatory = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date"]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="hr_trec_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_trec_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.title} — {self.employee.user.get_full_name()}"


# ---------------------------------------------------------------------------
# Learning & Development models
# ---------------------------------------------------------------------------


def hr_course_material_upload_to(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "pdf"
    return f"hr/course-materials/{instance.organization_id}/{uuid.uuid4()}.{ext}"


def hr_learning_resource_upload_to(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "pdf"
    return f"hr/learning-library/{instance.organization_id}/{uuid.uuid4()}.{ext}"


class TrainingCourse(models.Model):
    """Reusable training course definition."""

    class Format(models.TextChoices):
        IN_PERSON = "in_person", "In-Person"
        ONLINE = "online", "Online"
        HYBRID = "hybrid", "Hybrid"
        SELF_PACED = "self_paced", "Self-Paced"
        WORKSHOP = "workshop", "Workshop"

    class Level(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="training_courses",
    )
    title = models.CharField(max_length=300)
    code = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    provider = models.CharField(max_length=300, blank=True)
    format = models.CharField(
        max_length=15,
        choices=Format.choices,
        default=Format.IN_PERSON,
    )
    level = models.CharField(
        max_length=15,
        choices=Level.choices,
        default=Level.BEGINNER,
    )
    duration_hours = models.DecimalField(
        max_digits=6, decimal_places=1, null=True, blank=True,
    )
    max_participants = models.PositiveIntegerField(null=True, blank=True)
    cost_per_participant = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
    )
    currency = models.CharField(max_length=3, default=get_default_currency_code)
    prerequisites = models.TextField(blank=True)
    learning_objectives = models.TextField(blank=True)
    syllabus = models.TextField(blank=True)
    material = models.FileField(
        upload_to=hr_course_material_upload_to, null=True, blank=True,
    )
    is_mandatory = models.BooleanField(default=False)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_training_courses",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="hr_tcrs_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_tcrs_org_created_idx",
            ),
        ]

    def __str__(self):
        return self.title


class TrainingPlan(models.Model):
    """Structured training plan for a team, department, or individual."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="training_plans",
    )
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    department = models.ForeignKey(
        "settings.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="training_plans",
    )
    employee = models.ForeignKey(
        EmployeeRecord,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="training_plans",
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    budget = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
    )
    currency = models.CharField(max_length=3, default=get_default_currency_code)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    objectives = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_training_plans",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date"]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="hr_tpln_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_tpln_org_created_idx",
            ),
        ]

    def __str__(self):
        return self.title


class CourseEnrollment(models.Model):
    """Enrolment of an employee in a specific training course."""

    class Status(models.TextChoices):
        ENROLLED = "enrolled", "Enrolled"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        WITHDRAWN = "withdrawn", "Withdrawn"
        WAITLISTED = "waitlisted", "Waitlisted"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="course_enrollments",
    )
    employee = models.ForeignKey(
        EmployeeRecord,
        on_delete=models.CASCADE,
        related_name="course_enrollments",
    )
    course = models.ForeignKey(
        TrainingCourse,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    training_plan = models.ForeignKey(
        TrainingPlan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="enrollments",
    )
    enrolled_date = models.DateField(auto_now_add=True)
    start_date = models.DateField(null=True, blank=True)
    completion_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.ENROLLED,
    )
    score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
    )
    progress = models.PositiveIntegerField(default=0)
    feedback = models.TextField(blank=True)
    enrolled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="enrolled_courses",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-enrolled_date"]
        unique_together = [["employee", "course"]]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="hr_cenr_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_cenr_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.employee.user.get_full_name()} — {self.course.title}"


class LearningResource(models.Model):
    """Self-serve resource in the learning library."""

    class ResourceType(models.TextChoices):
        DOCUMENT = "document", "Document"
        VIDEO = "video", "Video"
        ARTICLE = "article", "Article"
        EBOOK = "ebook", "E-Book"
        TEMPLATE = "template", "Template"
        LINK = "link", "External Link"

    class Status(models.TextChoices):
        PUBLISHED = "published", "Published"
        DRAFT = "draft", "Draft"
        ARCHIVED = "archived", "Archived"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="learning_resources",
    )
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    resource_type = models.CharField(
        max_length=10,
        choices=ResourceType.choices,
        default=ResourceType.DOCUMENT,
    )
    category = models.CharField(max_length=200, blank=True)
    url = models.URLField(blank=True)
    file = models.FileField(
        upload_to=hr_learning_resource_upload_to, null=True, blank=True,
    )
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    tags = models.CharField(max_length=500, blank=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_learning_resources",
    )
    view_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="hr_lres_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_lres_org_created_idx",
            ),
        ]

    def __str__(self):
        return self.title


class TrainingCompletion(models.Model):
    """Finalised record of a completed training, including certificate tracking."""

    class Result(models.TextChoices):
        PASS = "pass", "Pass"
        FAIL = "fail", "Fail"
        DISTINCTION = "distinction", "Distinction"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="training_completions",
    )
    employee = models.ForeignKey(
        EmployeeRecord,
        on_delete=models.CASCADE,
        related_name="training_completions",
    )
    course = models.ForeignKey(
        TrainingCourse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="completions",
    )
    enrollment = models.OneToOneField(
        CourseEnrollment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="completion",
    )
    completion_date = models.DateField()
    result = models.CharField(
        max_length=15,
        choices=Result.choices,
        default=Result.PASS,
    )
    score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
    )
    certificate_number = models.CharField(max_length=200, blank=True)
    certificate_expiry = models.DateField(null=True, blank=True)
    hours_completed = models.DecimalField(
        max_digits=6, decimal_places=1, null=True, blank=True,
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_training_completions",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-completion_date"]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_tcom_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.employee.user.get_full_name()} — {self.course.title if self.course else 'N/A'}"


class CertificationExpiryAlert(models.Model):
    """Alert tracking for expiring certifications and licences."""

    class AlertStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        ACKNOWLEDGED = "acknowledged", "Acknowledged"
        RENEWED = "renewed", "Renewed"
        EXPIRED = "expired", "Expired"

    class AlertType(models.TextChoices):
        CERTIFICATION = "certification", "Certification"
        LICENSE = "license", "Professional License"
        TRAINING = "training", "Training Completion"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="certification_expiry_alerts",
    )
    employee = models.ForeignKey(
        EmployeeRecord,
        on_delete=models.CASCADE,
        related_name="certification_expiry_alerts",
    )
    alert_type = models.CharField(
        max_length=15,
        choices=AlertType.choices,
        default=AlertType.CERTIFICATION,
    )
    reference_name = models.CharField(max_length=300)
    reference_id = models.PositiveIntegerField(null=True, blank=True)
    expiry_date = models.DateField()
    alert_date = models.DateField()
    days_before_expiry = models.PositiveIntegerField(default=30)
    status = models.CharField(
        max_length=15,
        choices=AlertStatus.choices,
        default=AlertStatus.PENDING,
    )
    renewal_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["expiry_date"]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="hr_cea_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_cea_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"Alert: {self.reference_name} expires {self.expiry_date}"


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  8. Attendance & Leave                                                   ║
# ╚═══════════════════════════════════════════════════════════════════════════╝


class AttendanceLog(models.Model):
    """Daily attendance record for an employee."""

    class Status(models.TextChoices):
        PRESENT = "present", "Present"
        ABSENT = "absent", "Absent"
        LATE = "late", "Late"
        HALF_DAY = "half_day", "Half Day"
        ON_LEAVE = "on_leave", "On Leave"
        REMOTE = "remote", "Remote"
        HOLIDAY = "holiday", "Holiday"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="attendance_logs",
    )
    employee = models.ForeignKey(
        EmployeeRecord,
        on_delete=models.CASCADE,
        related_name="attendance_logs",
    )
    date = models.DateField()
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PRESENT,
    )
    clock_in = models.TimeField(null=True, blank=True)
    clock_out = models.TimeField(null=True, blank=True)
    break_minutes = models.PositiveIntegerField(default=0)
    total_hours = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
    )
    location = models.CharField(max_length=300, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date"]
        unique_together = [["employee", "date"]]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="hr_att_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_att_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.employee.user.get_full_name()} — {self.date}"


class LeaveType(models.Model):
    """Configurable leave type (Annual, Sick, Compassionate, etc.)."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="leave_types",
    )
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=30, blank=True)
    description = models.TextField(blank=True)
    default_days_per_year = models.DecimalField(
        max_digits=5, decimal_places=1, default=0,
    )
    is_paid = models.BooleanField(default=True)
    is_carry_over_allowed = models.BooleanField(default=False)
    max_carry_over_days = models.DecimalField(
        max_digits=5, decimal_places=1, default=0,
    )
    requires_approval = models.BooleanField(default=True)
    requires_attachment = models.BooleanField(default=False)
    min_days_notice = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_ltyp_org_created_idx",
            ),
        ]

    def __str__(self):
        return self.name


def hr_leave_attachment_upload_to(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "pdf"
    return f"hr/leave-attachments/{instance.employee_id}/{uuid.uuid4()}.{ext}"


class LeaveRequest(models.Model):
    """Employee leave/absence request."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending", "Pending Approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="leave_requests",
    )
    employee = models.ForeignKey(
        EmployeeRecord,
        on_delete=models.CASCADE,
        related_name="leave_requests",
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.PROTECT,
        related_name="leave_requests",
    )
    start_date = models.DateField()
    end_date = models.DateField()
    total_days = models.DecimalField(max_digits=5, decimal_places=1)
    is_half_day = models.BooleanField(default=False)
    reason = models.TextField(blank=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_leave_requests",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewer_notes = models.TextField(blank=True)
    attachment = models.FileField(
        upload_to=hr_leave_attachment_upload_to,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="hr_lreq_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_lreq_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.employee.user.get_full_name()} — {self.leave_type.name} ({self.start_date} to {self.end_date})"


class LeaveBalance(models.Model):
    """Annual leave balance per employee per leave type."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="leave_balances",
    )
    employee = models.ForeignKey(
        EmployeeRecord,
        on_delete=models.CASCADE,
        related_name="leave_balances",
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.CASCADE,
        related_name="leave_balances",
    )
    fiscal_year = models.PositiveIntegerField()
    entitled_days = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    carried_over = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    used_days = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    pending_days = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    adjustment = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fiscal_year", "leave_type__name"]
        unique_together = [["employee", "leave_type", "fiscal_year"]]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_lbal_org_created_idx",
            ),
        ]

    @property
    def available_days(self):
        return self.entitled_days + self.carried_over + self.adjustment - self.used_days - self.pending_days

    def __str__(self):
        return f"{self.employee.user.get_full_name()} — {self.leave_type.name} ({self.fiscal_year})"


class OvertimeRequest(models.Model):
    """Request for overtime hours worked."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending", "Pending Approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="overtime_requests",
    )
    employee = models.ForeignKey(
        EmployeeRecord,
        on_delete=models.CASCADE,
        related_name="overtime_requests",
    )
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    total_hours = models.DecimalField(max_digits=5, decimal_places=2)
    reason = models.TextField(blank=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_overtime_requests",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    approver_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date"]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="hr_otr_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_otr_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.employee.user.get_full_name()} — {self.date} ({self.total_hours}h)"


class RemoteWorkLog(models.Model):
    """Daily log for remote/hybrid work tracking."""

    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="remote_work_logs",
    )
    employee = models.ForeignKey(
        EmployeeRecord,
        on_delete=models.CASCADE,
        related_name="remote_work_logs",
    )
    date = models.DateField()
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PLANNED,
    )
    location = models.CharField(max_length=300, blank=True)
    work_hours = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
    )
    tasks_completed = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_remote_work_logs",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date"]
        unique_together = [["employee", "date"]]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="hr_rwl_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_rwl_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.employee.user.get_full_name()} — Remote {self.date}"


# ---------------------------------------------------------------------------
# Payroll & Compensation
# ---------------------------------------------------------------------------


class SalaryStructure(models.Model):
    """Defines salary grades / bands with base-salary ranges."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="salary_structures",
    )
    name = models.CharField(max_length=300)
    code = models.CharField(max_length=50, blank=True)
    grade_level = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Numeric grade level for ordering",
    )
    min_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    max_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default=get_default_currency_code)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["grade_level", "name"]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_sal_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})" if self.code else self.name


class PayrollRun(models.Model):
    """A single payroll processing run covering a pay period."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="payroll_runs",
    )
    name = models.CharField(max_length=300)
    period_start = models.DateField()
    period_end = models.DateField()
    run_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    total_gross = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_net = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default=get_default_currency_code)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processed_payroll_runs",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-period_end"]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="hr_prun_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_prun_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.period_start} – {self.period_end})"


class Allowance(models.Model):
    """Recurring or one-time employee allowances."""

    class AllowanceType(models.TextChoices):
        HOUSING = "housing", "Housing"
        TRANSPORT = "transport", "Transport"
        MEAL = "meal", "Meal"
        PHONE = "phone", "Phone"
        MEDICAL = "medical", "Medical"
        EDUCATION = "education", "Education"
        OTHER = "other", "Other"

    class Frequency(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        ANNUALLY = "annually", "Annually"
        ONE_TIME = "one_time", "One-Time"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="hr_allowances",
    )
    employee = models.ForeignKey(
        EmployeeRecord,
        on_delete=models.CASCADE,
        related_name="allowances",
    )
    allowance_type = models.CharField(
        max_length=12,
        choices=AllowanceType.choices,
        default=AllowanceType.OTHER,
    )
    name = models.CharField(max_length=300)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default=get_default_currency_code)
    frequency = models.CharField(
        max_length=12,
        choices=Frequency.choices,
        default=Frequency.MONTHLY,
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_taxable = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_alw_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.employee.user.get_full_name()} — {self.name}"


class Deduction(models.Model):
    """Recurring or one-time payroll deductions."""

    class DeductionType(models.TextChoices):
        TAX = "tax", "Tax"
        INSURANCE = "insurance", "Insurance"
        PENSION = "pension", "Pension"
        LOAN = "loan", "Loan Repayment"
        UNION = "union", "Union Dues"
        OTHER = "other", "Other"

    class Frequency(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        ANNUALLY = "annually", "Annually"
        ONE_TIME = "one_time", "One-Time"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="hr_deductions",
    )
    employee = models.ForeignKey(
        EmployeeRecord,
        on_delete=models.CASCADE,
        related_name="deductions",
    )
    deduction_type = models.CharField(
        max_length=12,
        choices=DeductionType.choices,
        default=DeductionType.OTHER,
    )
    name = models.CharField(max_length=300)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default=get_default_currency_code)
    frequency = models.CharField(
        max_length=12,
        choices=Frequency.choices,
        default=Frequency.MONTHLY,
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_ded_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.employee.user.get_full_name()} — {self.name}"


class Bonus(models.Model):
    """One-time bonus payments."""

    class BonusType(models.TextChoices):
        PERFORMANCE = "performance", "Performance"
        ANNUAL = "annual", "Annual"
        SIGNING = "signing", "Signing"
        REFERRAL = "referral", "Referral"
        PROJECT = "project", "Project"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        PAID = "paid", "Paid"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="hr_bonuses",
    )
    employee = models.ForeignKey(
        EmployeeRecord,
        on_delete=models.CASCADE,
        related_name="bonuses",
    )
    bonus_type = models.CharField(
        max_length=12,
        choices=BonusType.choices,
        default=BonusType.OTHER,
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default=get_default_currency_code)
    date = models.DateField()
    reason = models.TextField(blank=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_bonuses",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date"]
        verbose_name_plural = "bonuses"
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="hr_bon_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_bon_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.employee.user.get_full_name()} — {self.get_bonus_type_display()} {self.amount}"


class Payslip(models.Model):
    """Individual pay-period payslip for an employee."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        GENERATED = "generated", "Generated"
        SENT = "sent", "Sent"
        ACKNOWLEDGED = "acknowledged", "Acknowledged"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="payslips",
    )
    employee = models.ForeignKey(
        EmployeeRecord,
        on_delete=models.CASCADE,
        related_name="payslips",
    )
    payroll_run = models.ForeignKey(
        PayrollRun,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payslips",
    )
    period_start = models.DateField()
    period_end = models.DateField()
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_allowances = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gross_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default=get_default_currency_code)
    status = models.CharField(
        max_length=14,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    generated_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-period_end"]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="hr_pslp_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_pslp_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.employee.user.get_full_name()} — Payslip {self.period_start}–{self.period_end}"


class TaxRecord(models.Model):
    """Employee tax records per fiscal year."""

    class TaxType(models.TextChoices):
        INCOME_TAX = "income_tax", "Income Tax"
        SOCIAL_SECURITY = "social_security", "Social Security"
        MUNICIPAL = "municipal", "Municipal Tax"
        OTHER = "other", "Other"

    class FilingStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        FILED = "filed", "Filed"
        ASSESSED = "assessed", "Assessed"
        PAID = "paid", "Paid"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="hr_tax_records",
    )
    employee = models.ForeignKey(
        EmployeeRecord,
        on_delete=models.CASCADE,
        related_name="tax_records",
    )
    fiscal_year = models.CharField(max_length=9, help_text="e.g. 2025-2026")
    tax_type = models.CharField(
        max_length=16,
        choices=TaxType.choices,
        default=TaxType.INCOME_TAX,
    )
    taxable_income = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tax_paid = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default=get_default_currency_code)
    filing_status = models.CharField(
        max_length=10,
        choices=FilingStatus.choices,
        default=FilingStatus.PENDING,
    )
    filed_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def balance(self):
        return self.tax_amount - self.tax_paid

    class Meta:
        ordering = ["-fiscal_year", "tax_type"]
        indexes = [
            models.Index(
                fields=["organization", "filing_status"],
                name="hr_tax_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_tax_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.employee.user.get_full_name()} — {self.get_tax_type_display()} {self.fiscal_year}"


# =========================================================================
# 10. Employee Lifecycle Management
# =========================================================================


class Promotion(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        EFFECTIVE = "effective", "Effective"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="hr_promotions",
    )
    employee = models.ForeignKey(
        EmployeeRecord,
        on_delete=models.CASCADE,
        related_name="promotions",
    )
    from_position = models.CharField(max_length=200, blank=True)
    to_position = models.CharField(max_length=200)
    from_grade = models.CharField(max_length=50, blank=True)
    to_grade = models.CharField(max_length=50, blank=True)
    effective_date = models.DateField()
    salary_adjustment = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
        help_text="Increment amount",
    )
    new_salary = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
    )
    currency = models.CharField(max_length=3, default=get_default_currency_code)
    reason = models.TextField(blank=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_promotions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-effective_date"]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="hr_promo_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_promo_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.employee.user.get_full_name()} → {self.to_position}"


class Transfer(models.Model):
    class TransferType(models.TextChoices):
        LATERAL = "lateral", "Lateral"
        RELOCATION = "relocation", "Relocation"
        TEMPORARY = "temporary", "Temporary"
        PERMANENT = "permanent", "Permanent"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        EFFECTIVE = "effective", "Effective"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="hr_transfers",
    )
    employee = models.ForeignKey(
        EmployeeRecord,
        on_delete=models.CASCADE,
        related_name="transfers",
    )
    transfer_type = models.CharField(
        max_length=12,
        choices=TransferType.choices,
        default=TransferType.PERMANENT,
    )
    from_department = models.CharField(max_length=200, blank=True)
    to_department = models.CharField(max_length=200)
    from_location = models.CharField(max_length=200, blank=True)
    to_location = models.CharField(max_length=200, blank=True)
    effective_date = models.DateField()
    reason = models.TextField(blank=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_transfers",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-effective_date"]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="hr_tran_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_tran_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.employee.user.get_full_name()} → {self.to_department}"


class RoleChange(models.Model):
    class ChangeType(models.TextChoices):
        PROMOTION = "promotion", "Promotion"
        LATERAL = "lateral", "Lateral Move"
        DEMOTION = "demotion", "Demotion"
        RESTRUCTURE = "restructure", "Restructure"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        EFFECTIVE = "effective", "Effective"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="hr_role_changes",
    )
    employee = models.ForeignKey(
        EmployeeRecord,
        on_delete=models.CASCADE,
        related_name="role_changes",
    )
    change_type = models.CharField(
        max_length=12,
        choices=ChangeType.choices,
        default=ChangeType.LATERAL,
    )
    from_role = models.CharField(max_length=200, blank=True)
    to_role = models.CharField(max_length=200)
    effective_date = models.DateField()
    reason = models.TextField(blank=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_role_changes",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-effective_date"]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="hr_rchg_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_rchg_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.employee.user.get_full_name()} — {self.get_change_type_display()}: {self.to_role}"


class DisciplinaryRecord(models.Model):
    class Category(models.TextChoices):
        MISCONDUCT = "misconduct", "Misconduct"
        PERFORMANCE = "performance", "Performance"
        ATTENDANCE = "attendance", "Attendance"
        POLICY_VIOLATION = "policy_violation", "Policy Violation"
        OTHER = "other", "Other"

    class Severity(models.TextChoices):
        VERBAL_WARNING = "verbal_warning", "Verbal Warning"
        WRITTEN_WARNING = "written_warning", "Written Warning"
        FINAL_WARNING = "final_warning", "Final Warning"
        SUSPENSION = "suspension", "Suspension"
        TERMINATION = "termination", "Termination"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        UNDER_REVIEW = "under_review", "Under Review"
        RESOLVED = "resolved", "Resolved"
        APPEALED = "appealed", "Appealed"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="hr_disciplinary_records",
    )
    employee = models.ForeignKey(
        EmployeeRecord,
        on_delete=models.CASCADE,
        related_name="disciplinary_records",
    )
    incident_date = models.DateField()
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reported_disciplinaries",
    )
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.OTHER,
    )
    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        default=Severity.VERBAL_WARNING,
    )
    description = models.TextField()
    action_taken = models.TextField(blank=True)
    follow_up_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.OPEN,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-incident_date"]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="hr_disc_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_disc_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.employee.user.get_full_name()} — {self.get_category_display()} ({self.get_severity_display()})"


class ExitManagement(models.Model):
    class ExitType(models.TextChoices):
        RESIGNATION = "resignation", "Resignation"
        TERMINATION = "termination", "Termination"
        RETIREMENT = "retirement", "Retirement"
        END_OF_CONTRACT = "end_of_contract", "End of Contract"
        REDUNDANCY = "redundancy", "Redundancy"
        OTHER = "other", "Other"

    class ClearanceStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"

    class SettlementStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        PAID = "paid", "Paid"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="hr_exit_managements",
    )
    employee = models.ForeignKey(
        EmployeeRecord,
        on_delete=models.CASCADE,
        related_name="exit_records",
    )
    exit_type = models.CharField(
        max_length=16,
        choices=ExitType.choices,
    )
    notice_date = models.DateField()
    last_working_day = models.DateField()
    reason = models.TextField(blank=True)
    clearance_status = models.CharField(
        max_length=12,
        choices=ClearanceStatus.choices,
        default=ClearanceStatus.PENDING,
    )
    final_settlement_status = models.CharField(
        max_length=12,
        choices=SettlementStatus.choices,
        default=SettlementStatus.PENDING,
    )
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processed_exits",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_working_day"]
        verbose_name_plural = "exit management records"
        indexes = [
            models.Index(
                fields=["organization", "clearance_status"],
                name="hr_exit_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_exit_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.employee.user.get_full_name()} — {self.get_exit_type_display()}"


class ExitInterview(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="hr_exit_interviews",
    )
    employee = models.ForeignKey(
        EmployeeRecord,
        on_delete=models.CASCADE,
        related_name="exit_interviews",
    )
    exit_record = models.ForeignKey(
        ExitManagement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="interviews",
    )
    interview_date = models.DateField()
    interviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conducted_exit_interviews",
    )
    overall_satisfaction = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="1 = Very Dissatisfied, 5 = Very Satisfied",
    )
    reason_for_leaving = models.TextField()
    feedback = models.TextField(blank=True)
    would_recommend = models.BooleanField(default=False)
    would_rejoin = models.BooleanField(default=False)
    key_concerns = models.TextField(blank=True)
    suggestions = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-interview_date"]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_eint_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"Exit Interview — {self.employee.user.get_full_name()}"


# =========================================================================
# 11. Workforce Analytics
# =========================================================================


class HeadcountSnapshot(models.Model):
    """Periodic snapshot of headcount figures."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="hr_headcount_snapshots",
    )
    snapshot_date = models.DateField()
    department = models.CharField(max_length=200, blank=True)
    team = models.CharField(max_length=200, blank=True)
    active_count = models.PositiveIntegerField(default=0)
    inactive_count = models.PositiveIntegerField(default=0)
    new_hires = models.PositiveIntegerField(default=0)
    departures = models.PositiveIntegerField(default=0)
    contractors = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_headcount(self):
        return self.active_count + self.inactive_count

    class Meta:
        ordering = ["-snapshot_date"]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_hsnp_org_created_idx",
            ),
        ]

    def __str__(self):
        label = self.department or self.team or "Organization"
        return f"{label} — {self.snapshot_date}"


class TurnoverRecord(models.Model):
    """Turnover metrics for a reporting period."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="hr_turnover_records",
    )
    period_start = models.DateField()
    period_end = models.DateField()
    department = models.CharField(max_length=200, blank=True)
    starting_headcount = models.PositiveIntegerField(default=0)
    ending_headcount = models.PositiveIntegerField(default=0)
    voluntary_departures = models.PositiveIntegerField(default=0)
    involuntary_departures = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_departures(self):
        return self.voluntary_departures + self.involuntary_departures

    @property
    def turnover_rate(self):
        avg = (self.starting_headcount + self.ending_headcount) / 2
        if avg == 0:
            return 0
        return round(self.total_departures / avg * 100, 2)

    class Meta:
        ordering = ["-period_end"]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_turn_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"Turnover {self.period_start} – {self.period_end}"


class DepartmentStaffingReport(models.Model):
    """Staffing levels vs. budget per department."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="hr_dept_staffing_reports",
    )
    report_date = models.DateField()
    department = models.CharField(max_length=200)
    budgeted_positions = models.PositiveIntegerField(default=0)
    filled_positions = models.PositiveIntegerField(default=0)
    vacant_positions = models.PositiveIntegerField(default=0)
    pending_hires = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def fill_rate(self):
        if self.budgeted_positions == 0:
            return 0
        return round(self.filled_positions / self.budgeted_positions * 100, 2)

    class Meta:
        ordering = ["-report_date", "department"]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_dsr_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.department} — {self.report_date}"


class HiringFunnelMetric(models.Model):
    """Hiring pipeline metrics for a reporting period."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="hr_hiring_funnel_metrics",
    )
    period_start = models.DateField()
    period_end = models.DateField()
    department = models.CharField(max_length=200, blank=True)
    requisitions_opened = models.PositiveIntegerField(default=0)
    applications_received = models.PositiveIntegerField(default=0)
    candidates_screened = models.PositiveIntegerField(default=0)
    candidates_interviewed = models.PositiveIntegerField(default=0)
    offers_made = models.PositiveIntegerField(default=0)
    offers_accepted = models.PositiveIntegerField(default=0)
    avg_time_to_hire_days = models.DecimalField(
        max_digits=6, decimal_places=1, default=0,
    )
    avg_cost_per_hire = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
    )
    currency = models.CharField(max_length=3, default=get_default_currency_code)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def offer_acceptance_rate(self):
        if self.offers_made == 0:
            return 0
        return round(self.offers_accepted / self.offers_made * 100, 2)

    class Meta:
        ordering = ["-period_end"]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_hfm_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"Hiring Funnel {self.period_start} – {self.period_end}"


class WorkforceCostReport(models.Model):
    """Workforce cost breakdown for a reporting period."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="hr_workforce_cost_reports",
    )
    period_start = models.DateField()
    period_end = models.DateField()
    department = models.CharField(max_length=200, blank=True)
    total_salary = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_allowances = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_bonuses = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_benefits = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_overtime = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default=get_default_currency_code)
    headcount = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_cost(self):
        return (
            self.total_salary
            + self.total_allowances
            + self.total_bonuses
            + self.total_benefits
            + self.total_overtime
        )

    @property
    def cost_per_employee(self):
        if self.headcount == 0:
            return 0
        return round(self.total_cost / self.headcount, 2)

    class Meta:
        ordering = ["-period_end"]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_wcr_org_created_idx",
            ),
        ]

    def __str__(self):
        label = self.department or "Organization"
        return f"Cost Report — {label} {self.period_start} – {self.period_end}"


class DiversityMetric(models.Model):
    class Dimension(models.TextChoices):
        GENDER = "gender", "Gender"
        AGE_GROUP = "age_group", "Age Group"
        ETHNICITY = "ethnicity", "Ethnicity"
        NATIONALITY = "nationality", "Nationality"
        DISABILITY = "disability", "Disability"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="hr_diversity_metrics",
    )
    snapshot_date = models.DateField()
    department = models.CharField(max_length=200, blank=True)
    dimension = models.CharField(
        max_length=16,
        choices=Dimension.choices,
    )
    category_value = models.CharField(
        max_length=100,
        help_text="e.g. Male, Female, 25-34, etc.",
    )
    count = models.PositiveIntegerField(default=0)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-snapshot_date", "dimension", "-count"]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_dvm_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.get_dimension_display()}: {self.category_value} — {self.snapshot_date}"


# ---------------------------------------------------------------------------
# HR Documents & Policies
# ---------------------------------------------------------------------------


class HRPolicy(models.Model):
    class Category(models.TextChoices):
        GENERAL = "general", "General"
        EMPLOYMENT = "employment", "Employment"
        COMPENSATION = "compensation", "Compensation"
        LEAVE = "leave", "Leave"
        CONDUCT = "conduct", "Code of Conduct"
        SAFETY = "safety", "Health & Safety"
        DATA_PRIVACY = "data_privacy", "Data Privacy"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        UNDER_REVIEW = "under_review", "Under Review"
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="hr_policies",
    )
    title = models.CharField(max_length=300)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.GENERAL)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    version = models.CharField(max_length=30, blank=True)
    effective_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    content = models.TextField(blank=True, help_text="Full policy text or rich content")
    department = models.CharField(max_length=200, blank=True, help_text="Leave blank for org-wide policies")
    created_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hr_policies_created",
    )
    approved_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hr_policies_approved",
    )
    approval_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name_plural = "HR Policies"
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="hr_hpol_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_hpol_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.title} (v{self.version})" if self.version else self.title


class EmployeeHandbookSection(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="hr_handbook_sections",
    )
    handbook_version = models.CharField(max_length=30, blank=True)
    section_number = models.CharField(max_length=20, help_text="e.g. 1.0, 2.3")
    title = models.CharField(max_length=300)
    content = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    last_updated_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hr_handbook_sections_updated",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "section_number"]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="hr_ehbs_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_ehbs_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.section_number} — {self.title}"


class ComplianceDocument(models.Model):
    class DocumentType(models.TextChoices):
        REGULATION = "regulation", "Regulation"
        CERTIFICATION = "certification", "Certification"
        AUDIT_REPORT = "audit_report", "Audit Report"
        LEGAL = "legal", "Legal"
        POLICY = "policy", "Policy"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        CURRENT = "current", "Current"
        EXPIRED = "expired", "Expired"
        PENDING_REVIEW = "pending_review", "Pending Review"
        ARCHIVED = "archived", "Archived"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="hr_compliance_documents",
    )
    title = models.CharField(max_length=300)
    document_type = models.CharField(max_length=16, choices=DocumentType.choices, default=DocumentType.POLICY)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.CURRENT)
    reference_number = models.CharField(max_length=100, blank=True)
    issuing_authority = models.CharField(max_length=200, blank=True)
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    department = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="hr_cdoc_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_cdoc_org_created_idx",
            ),
        ]

    def __str__(self):
        return self.title


class PolicyAcknowledgement(models.Model):
    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="hr_policy_acknowledgements",
    )
    employee = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="hr_policy_acknowledgements",
    )
    policy = models.ForeignKey(
        HRPolicy,
        on_delete=models.CASCADE,
        related_name="acknowledgements",
    )
    acknowledged_date = models.DateTimeField(null=True, blank=True)
    acknowledged = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-acknowledged_date"]
        unique_together = [("employee", "policy")]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_pack_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.employee} — {self.policy}"


class HRDocumentTemplate(models.Model):
    class Category(models.TextChoices):
        OFFER_LETTER = "offer_letter", "Offer Letter"
        CONTRACT = "contract", "Contract"
        WARNING_LETTER = "warning_letter", "Warning Letter"
        TERMINATION = "termination", "Termination"
        PROMOTION = "promotion", "Promotion"
        TRANSFER = "transfer", "Transfer"
        GENERAL = "general", "General"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        DRAFT = "draft", "Draft"
        ARCHIVED = "archived", "Archived"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="hr_document_templates",
    )
    title = models.CharField(max_length=300)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.GENERAL)
    description = models.TextField(blank=True)
    content = models.TextField(blank=True, help_text="Template body with placeholders")
    version = models.CharField(max_length=30, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hr_document_templates_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="hr_dtpl_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="hr_dtpl_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.title} (v{self.version})" if self.version else self.title
