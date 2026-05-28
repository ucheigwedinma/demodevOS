from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from apps.settings.currency import get_default_currency_code

from .blueprint_models import (  # noqa: F401 — register with Django
    BlueprintActivity,
    BlueprintDependency,
    BlueprintPhase,
    BlueprintScenario,
    BlueprintTask,
    ProjectBlueprint,
)


def project_daily_report_photo_upload_to(instance, filename):
    ext = filename.split(".")[-1] if "." in filename else "bin"
    return (
        f"projects/{instance.report.project_id}/field-ops/reports/"
        f"{instance.report_id}/{uuid4().hex}.{ext}"
    )


def project_supporting_attachment_upload_to(instance, filename):
    ext = filename.split(".")[-1] if "." in filename else "bin"
    path = f"projects/{instance.project_id}/supporting"
    if instance.variation_id:
        path = f"{path}/variations/{instance.variation_id}"
    elif instance.phase_id:
        path = f"{path}/phases/{instance.phase_id}"
    elif instance.milestone_id:
        path = f"{path}/milestones/{instance.milestone_id}"
    elif instance.task_id:
        path = f"{path}/tasks/{instance.task_id}"
    elif instance.cost_entry_id:
        path = f"{path}/costs/{instance.cost_entry_id}"
    elif instance.risk_entry_id:
        path = f"{path}/risk-register/{instance.risk_entry_id}"
    elif instance.workforce_log_id:
        path = f"{path}/field-ops/workforce/{instance.workforce_log_id}"
    elif instance.site_report_id:
        path = f"{path}/field-ops/reports/{instance.site_report_id}"
    elif instance.quality_inspection_id:
        path = f"{path}/field-ops/quality-inspections/{instance.quality_inspection_id}"
    elif instance.escalation_id:
        path = f"{path}/field-ops/escalations/{instance.escalation_id}"
    return f"{path}/{uuid4().hex}.{ext}"


class Project(models.Model):
    """Development project that can optionally link to a property."""

    class Status(models.TextChoices):
        PLANNING = "planning", "Planning"
        IN_PROGRESS = "in_progress", "In Progress"
        ON_HOLD = "on_hold", "On Hold"
        COMPLETED = "completed", "Completed"

    class ProjectType(models.TextChoices):
        RESIDENTIAL = "residential", "Residential"
        MIXED_USE = "mixed_use", "Mixed-Use"
        COMMERCIAL = "commercial", "Commercial"
        INFRASTRUCTURE = "infrastructure", "Infrastructure"

    class LandStatus(models.TextChoices):
        FREEHOLD = "freehold", "Freehold"
        LEASEHOLD = "leasehold", "Leasehold"
        UNDER_CONTRACT = "under_contract", "Under Contract"
        TO_ACQUIRE = "to_acquire", "To Acquire"
        JOINT_VENTURE = "joint_venture", "Joint Venture"

    class RiskRating(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class ComplianceStatus(models.TextChoices):
        COMPLIANT = "compliant", "Compliant"
        WARNING = "warning", "Warning"
        NON_COMPLIANT = "non_compliant", "Non-Compliant"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_projects",
    )
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.CASCADE,
        related_name="projects",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNING)

    # Project type
    project_type = models.CharField(
        max_length=20,
        choices=ProjectType.choices,
        default=ProjectType.RESIDENTIAL,
    )
    number_of_units = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Planned number of units for the project plan.",
    )

    # Location
    location = models.CharField(
        max_length=500, blank=True,
        help_text="Project site address or location description",
    )
    gps_latitude = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True,
        validators=[MinValueValidator(Decimal("-90")), MaxValueValidator(Decimal("90"))],
        help_text="Latitude of project site (-90 to 90)",
    )
    gps_longitude = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True,
        validators=[MinValueValidator(Decimal("-180")), MaxValueValidator(Decimal("180"))],
        help_text="Longitude of project site (-180 to 180)",
    )

    # SPV / Entity
    spv_entity = models.CharField(
        max_length=255, blank=True,
        help_text="Special Purpose Vehicle or legal entity for this project",
    )
    spv = models.ForeignKey(
        "finance.SPVEntity", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="projects",
    )

    # Ownership structure
    ownership_structure = models.TextField(
        blank=True,
        help_text="Description of ownership / equity structure",
    )

    # Land status
    land_status = models.CharField(
        max_length=20,
        choices=LandStatus.choices,
        blank=True,
    )

    # Key dates
    start_date = models.DateField(null=True, blank=True)
    target_end_date = models.DateField(null=True, blank=True)
    actual_end_date = models.DateField(null=True, blank=True)
    land_acquisition_date = models.DateField(null=True, blank=True)
    permit_approval_date = models.DateField(null=True, blank=True)
    construction_start_date = models.DateField(null=True, blank=True)

    # Budget & financials
    budget = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    target_irr = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        help_text="Target Internal Rate of Return (%)",
    )

    # RACI matrix summary
    raci_summary = models.JSONField(
        default=dict, blank=True,
        help_text="RACI matrix summary: { role: responsibility_level }",
    )

    risk_rating = models.CharField(
        max_length=20,
        choices=RiskRating.choices,
        default=RiskRating.MEDIUM,
    )
    compliance_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("100.00"),
        help_text="Project compliance score derived from controlled-document expiries.",
    )
    compliance_status = models.CharField(
        max_length=20,
        choices=ComplianceStatus.choices,
        default=ComplianceStatus.COMPLIANT,
    )
    compliance_last_evaluated_at = models.DateTimeField(null=True, blank=True)
    project_manager = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["organization", "status"], name="proj_proj_org_status_idx"),
            models.Index(fields=["organization", "-created_at"], name="proj_proj_org_created_idx"),
        ]

    def __str__(self):
        return self.name


class ProjectPlanningInsight(models.Model):
    """Cross-module planning insight generated from CRM demand analytics."""

    class SourceModule(models.TextChoices):
        CRM = "crm", "CRM"
        PROJECTS = "projects", "Projects"
        ANALYTICS = "analytics", "Analytics"

    class InsightType(models.TextChoices):
        DEMAND_ANALYTICS = "demand_analytics", "Demand Analytics"
        NEW_DEVELOPMENT = "new_development", "New Development Trigger"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="project_planning_insights",
    )
    source_module = models.CharField(
        max_length=20,
        choices=SourceModule.choices,
        default=SourceModule.CRM,
    )
    insight_type = models.CharField(
        max_length=32,
        choices=InsightType.choices,
        default=InsightType.DEMAND_ANALYTICS,
    )
    area_name = models.CharField(max_length=200)
    title = models.CharField(max_length=255)
    summary = models.TextField(blank=True)
    demand_share_percent = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    lead_count = models.PositiveIntegerField(default=0)
    qualified_lead_count = models.PositiveIntegerField(default=0)
    won_lead_count = models.PositiveIntegerField(default=0)
    window_days = models.PositiveIntegerField(default=90)
    threshold_percent = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("25.00"))
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    first_triggered_at = models.DateTimeField(null=True, blank=True)
    last_triggered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-demand_share_percent", "-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "insight_type", "area_name"],
                name="unique_org_planning_insight_area_type",
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization", "source_module", "insight_type", "is_active"],
                name="proj_pi_org_type_act_idx",
            ),
            models.Index(
                fields=["organization", "-updated_at"],
                name="proj_pi_org_updated_idx",
            ),
        ]

    def __str__(self):
        return f"{self.get_insight_type_display()}: {self.area_name}"


class ProjectPhase(models.Model):
    """A lifecycle phase within a development project."""

    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Not Started"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        SKIPPED = "skipped", "Skipped"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_project_phases",
    )
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="phases")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NOT_STARTED)
    baseline_start_date = models.DateField(null=True, blank=True)
    baseline_end_date = models.DateField(null=True, blank=True)
    revised_start_date = models.DateField(null=True, blank=True)
    revised_end_date = models.DateField(null=True, blank=True)
    schedule_revision_reason = models.TextField(blank=True)
    planned_start_date = models.DateField(null=True, blank=True)
    planned_end_date = models.DateField(null=True, blank=True)
    actual_start_date = models.DateField(null=True, blank=True)
    actual_end_date = models.DateField(null=True, blank=True)
    planned_budget = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    actual_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    weight = models.PositiveIntegerField(
        default=1,
        help_text="Relative weight for progress calculation",
    )

    # --- Section A: Phase Overview & Metadata ---
    objective = models.TextField(blank=True)
    estimated_duration_days = models.PositiveIntegerField(null=True, blank=True)
    phase_owner_role = models.CharField(max_length=200, blank=True)

    # --- Section B: Governance & Stakeholders ---
    raci_matrix = models.JSONField(default=list, blank=True)
    approval_authority = models.TextField(blank=True)

    # --- Section C: Scope & Deliverables ---
    key_tasks = models.JSONField(default=list, blank=True)
    deliverables = models.JSONField(default=list, blank=True)
    out_of_scope = models.TextField(blank=True)

    # --- Section D: Resource & Risk Management ---
    resource_requirements = models.JSONField(default=list, blank=True)
    phase_risks = models.JSONField(default=list, blank=True)
    budget_notes = models.TextField(blank=True)

    # --- Section E: Quality & Completion Criteria ---
    success_metrics = models.JSONField(default=list, blank=True)
    exit_criteria = models.JSONField(default=list, blank=True)
    lessons_learned_prompt = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order"]
        verbose_name_plural = "project phases"
        indexes = [
            models.Index(fields=["organization", "status"], name="proj_phase_org_status_idx"),
            models.Index(fields=["organization", "-created_at"], name="proj_phase_org_created_idx"),
        ]

    def __str__(self):
        return f"{self.project.name} — {self.name}"

    def save(self, **kwargs):
        if self.planned_start_date and not self.baseline_start_date:
            self.baseline_start_date = self.planned_start_date
        if self.planned_end_date and not self.baseline_end_date:
            self.baseline_end_date = self.planned_end_date
        super().save(**kwargs)


class ProjectMilestone(models.Model):
    """A checkpoint within a project phase."""

    class ApprovalStatus(models.TextChoices):
        NOT_REQUIRED = "not_required", "Not Required"
        PENDING = "pending", "Pending Approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_project_milestones",
    )
    phase = models.ForeignKey(ProjectPhase, on_delete=models.CASCADE, related_name="milestones")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    baseline_target_date = models.DateField(null=True, blank=True)
    revised_target_date = models.DateField(null=True, blank=True)
    schedule_revision_reason = models.TextField(blank=True)
    target_date = models.DateField(null=True, blank=True)
    completed_date = models.DateField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    approval_required = models.BooleanField(default=False)
    approval_status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.NOT_REQUIRED,
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_project_milestones",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    # --- Section A: Milestone Identification ---
    reference_code = models.CharField(max_length=100, blank=True, help_text="Milestone ID/code, e.g. MS-001.")

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
    owner_role = models.CharField(max_length=200, blank=True, help_text="Role responsible for this milestone.")
    approver_role = models.CharField(max_length=200, blank=True, help_text="Role that approves this milestone.")
    stakeholders_to_notify = models.JSONField(default=list, blank=True, help_text='[{"role","notification_trigger"}]')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "target_date"]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="proj_ms_org_created_idx",
            ),
        ]

    def __str__(self):
        return self.name

    def save(self, **kwargs):
        if self.target_date and not self.baseline_target_date:
            self.baseline_target_date = self.target_date
        if not self.approval_required and self.approval_status != self.ApprovalStatus.NOT_REQUIRED:
            self.approval_status = self.ApprovalStatus.NOT_REQUIRED
            self.approved_by = None
            self.approved_at = None
        super().save(**kwargs)


class ProjectPhaseDependency(models.Model):
    """Dependency graph between project phases for critical-path analysis."""

    class DependencyType(models.TextChoices):
        FINISH_TO_START = "fs", "Finish to Start"
        START_TO_START = "ss", "Start to Start"
        FINISH_TO_FINISH = "ff", "Finish to Finish"
        START_TO_FINISH = "sf", "Start to Finish"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_project_phase_dependencies",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="phase_dependencies",
    )
    predecessor_phase = models.ForeignKey(
        ProjectPhase,
        on_delete=models.CASCADE,
        related_name="successor_dependencies",
    )
    successor_phase = models.ForeignKey(
        ProjectPhase,
        on_delete=models.CASCADE,
        related_name="predecessor_dependencies",
    )
    dependency_type = models.CharField(
        max_length=2,
        choices=DependencyType.choices,
        default=DependencyType.FINISH_TO_START,
    )
    lag_days = models.IntegerField(default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["predecessor_phase_id", "successor_phase_id", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "predecessor_phase", "successor_phase"],
                name="unique_project_phase_dependency_edge",
            ),
            models.CheckConstraint(
                check=~models.Q(predecessor_phase=models.F("successor_phase")),
                name="project_phase_dependency_no_self_loop",
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="proj_pdep_org_created_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.project.name}: "
            f"{self.predecessor_phase.name} -> {self.successor_phase.name}"
        )


class ProjectMilestoneApprovalRule(models.Model):
    """Configurable milestone approval chain rules."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_project_milestone_approval_rules",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="milestone_approval_rules",
    )
    phase = models.ForeignKey(
        ProjectPhase,
        on_delete=models.CASCADE,
        related_name="approval_rules",
        null=True,
        blank=True,
    )
    required_role = models.ForeignKey(
        "settings.Role",
        on_delete=models.CASCADE,
        related_name="project_milestone_approval_rules",
    )
    sequence_order = models.PositiveIntegerField(default=0)
    is_mandatory = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["phase_id", "sequence_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "phase", "required_role", "sequence_order"],
                name="unique_project_milestone_approval_rule",
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="proj_mar_org_created_idx",
            ),
        ]

    def __str__(self):
        scope = self.phase.name if self.phase else "All phases"
        return f"{self.project.name} {scope}: {self.required_role.name}"


class ProjectMilestoneApprovalDecision(models.Model):
    """Operational approval decisions logged against milestone rule steps."""

    class Decision(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_project_milestone_approval_decisions",
    )
    milestone = models.ForeignKey(
        ProjectMilestone,
        on_delete=models.CASCADE,
        related_name="approval_decisions",
    )
    rule = models.ForeignKey(
        ProjectMilestoneApprovalRule,
        on_delete=models.SET_NULL,
        related_name="decisions",
        null=True,
        blank=True,
    )
    approver_role = models.ForeignKey(
        "settings.Role",
        on_delete=models.SET_NULL,
        related_name="project_milestone_approval_decisions",
        null=True,
        blank=True,
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="project_milestone_approval_decisions",
        null=True,
        blank=True,
    )
    decision = models.CharField(
        max_length=16,
        choices=Decision.choices,
        default=Decision.PENDING,
    )
    comments = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["milestone", "decision"]),
            models.Index(fields=["approver_role", "decision"]),
        ]

    def __str__(self):
        return f"Milestone {self.milestone_id} {self.decision}"


class ProjectTask(models.Model):
    """A granular work item within a project phase."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_project_tasks",
    )
    phase = models.ForeignKey(ProjectPhase, on_delete=models.CASCADE, related_name="tasks")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    work_package = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    assigned_to = models.CharField(max_length=255, blank=True)
    assigned_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="project_tasks",
    )
    assigned_external_ref = models.CharField(
        max_length=255,
        blank=True,
        help_text="External directory/ERP/ITSM assignee reference for future integrations.",
    )
    linked_documents = models.ManyToManyField(
        "documents.Document",
        blank=True,
        related_name="linked_project_tasks",
    )
    linked_variation_orders = models.ManyToManyField(
        "projects.ProjectVariationOrder",
        blank=True,
        related_name="linked_tasks",
    )
    linked_risks = models.ManyToManyField(
        "projects.ProjectRiskRegisterEntry",
        blank=True,
        related_name="linked_tasks",
    )
    sla_target_at = models.DateTimeField(null=True, blank=True)
    sla_breached_at = models.DateTimeField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    completed_date = models.DateField(null=True, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    # --- Section A: Task Definition & Context ---
    reference_code = models.CharField(max_length=100, blank=True, help_text="Task ID, e.g. TASK-101.")

    # --- Section B: Assignment & Ownership ---
    reviewer_role = models.CharField(max_length=200, blank=True, help_text="Role that reviews/approves the task output.")
    collaborators = models.JSONField(default=list, blank=True, help_text='[{"role","responsibility"}]')

    # --- Section C: Scheduling & Effort ---
    estimated_effort_hours = models.DecimalField(max_digits=7, decimal_places=1, null=True, blank=True, help_text="Expected effort in hours.")

    # --- Section D: Execution Details ---
    predecessors = models.JSONField(default=list, blank=True, help_text='[{"task","dependency_type","lag_days"}]')
    successors = models.JSONField(default=list, blank=True, help_text='[{"task","dependency_type","lag_days"}]')
    definition_of_done = models.JSONField(default=list, blank=True, help_text='[{"criterion","is_required"}]')

    # --- Section E: Resources & Attachments ---
    tools_required = models.JSONField(default=list, blank=True, help_text='[{"name","description"}]')
    reference_links = models.JSONField(default=list, blank=True, help_text='[{"title","url"}]')

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_project_tasks",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_project_tasks",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "due_date"]
        indexes = [
            models.Index(fields=["status", "priority", "due_date"]),
            models.Index(fields=["assigned_user", "status"]),
            models.Index(fields=["sla_target_at", "status"]),
            models.Index(fields=["organization", "status"], name="proj_task_org_status_idx"),
            models.Index(fields=["organization", "-created_at"], name="proj_task_org_created_idx"),
        ]

    def __str__(self):
        return self.name


class ProjectTaskComment(models.Model):
    """Comment stream for project task collaboration and traceability."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_project_task_comments",
    )
    task = models.ForeignKey(
        ProjectTask,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="project_task_comments",
    )
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["task", "created_at"]),
        ]

    def __str__(self):
        return f"Task {self.task_id} comment {self.id}"


class ProjectWorkPackage(models.Model):
    """Construction scope package grouped for execution, controls, and traceability."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_project_work_packages",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="work_packages",
    )
    phase = models.ForeignKey(
        ProjectPhase,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="work_packages",
    )
    package_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
        help_text="Work package identifier, auto-generated as WP-##### when blank.",
    )
    name = models.CharField(max_length=255)
    scope_description = models.TextField(blank=True)
    contractor = models.ForeignKey(
        "procurement.Vendor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="project_work_packages",
    )
    boq_items = models.JSONField(
        default=list,
        blank=True,
        help_text="Legacy JSON list of BOQ line items.",
    )
    linked_bom_items = models.ManyToManyField(
        "inventory.BOMItem",
        blank=True,
        related_name="linked_work_packages",
        help_text="Structured link to BoQ line items via the mapping engine.",
    )
    budget = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    drawings = models.ManyToManyField(
        "documents.Document",
        blank=True,
        related_name="linked_project_work_packages",
    )
    quality_requirements = models.TextField(blank=True)
    safety_requirements = models.TextField(blank=True)
    inspection_plan = models.TextField(blank=True)

    # Cross-module links
    linked_purchase_orders = models.ManyToManyField(
        "procurement.PurchaseOrder",
        blank=True,
        related_name="linked_project_work_packages",
    )
    linked_cost_entries = models.ManyToManyField(
        "projects.ProjectCostEntry",
        blank=True,
        related_name="linked_work_packages",
    )
    linked_contractors = models.ManyToManyField(
        "procurement.Vendor",
        blank=True,
        related_name="linked_project_work_package_contractors",
    )
    linked_inspections = models.ManyToManyField(
        "projects.ProjectExecutionInspection",
        blank=True,
        related_name="linked_work_packages",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_project_work_packages",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_project_work_packages",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-created_at"]
        indexes = [
            models.Index(fields=["organization", "-updated_at"], name="proj_wp_org_updated_idx"),
            models.Index(fields=["project", "start_date"], name="proj_wp_proj_start_idx"),
        ]

    def save(self, *args, **kwargs):
        creating = self._state.adding
        super().save(*args, **kwargs)
        if creating and not self.package_id:
            self.package_id = f"WP-{self.pk:05d}"
            super().save(update_fields=["package_id"])

    @property
    def boq_total_quantity(self):
        """Sum of allocated quantities from linked BOQ items via BoqTaskMapping."""
        from inventory.models import BoqTaskMapping
        return BoqTaskMapping.objects.filter(
            project=self.project,
            bom_item__in=self.linked_bom_items.all(),
        ).aggregate(total=Sum("allocated_quantity"))["total"] or Decimal("0")

    @property
    def boq_total_cost(self):
        """Sum of allocated costs from linked BOQ items."""
        from inventory.models import BoqTaskMapping
        return BoqTaskMapping.objects.filter(
            project=self.project,
            bom_item__in=self.linked_bom_items.all(),
        ).aggregate(total=Sum("allocated_cost"))["total"] or Decimal("0")

    @property
    def boq_consumed_quantity(self):
        """Sum of actual material consumed from daily reports."""
        return DailyReportMaterialUsage.objects.filter(
            bom_item__in=self.linked_bom_items.all(),
            report__project=self.project,
        ).aggregate(total=Sum("quantity_used"))["total"] or Decimal("0")

    def __str__(self):
        return f"{self.package_id or 'WP'} — {self.name}"


class ProjectCostEntry(models.Model):
    """An individual cost line item for tracking actuals against a phase budget."""

    class Category(models.TextChoices):
        MATERIALS = "materials", "Materials"
        LABOR = "labor", "Labor"
        PERMITS = "permits", "Permits & Fees"
        EQUIPMENT = "equipment", "Equipment"
        SUBCONTRACTOR = "subcontractor", "Subcontractor"
        OTHER = "other", "Other"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_project_cost_entries",
    )
    phase = models.ForeignKey(ProjectPhase, on_delete=models.CASCADE, related_name="cost_entries")
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    date = models.DateField()
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    vendor = models.CharField(max_length=255, blank=True)
    reference_number = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]
        verbose_name_plural = "project cost entries"
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="proj_cost_org_created_idx"),
        ]

    def __str__(self):
        return f"{self.description} — {self.amount}"


class ProjectRiskRegisterEntry(models.Model):
    """Risk register record tied to a project with mitigation tracking."""

    class Severity(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In Progress"
        MITIGATED = "mitigated", "Mitigated"
        ACCEPTED = "accepted", "Accepted"
        CLOSED = "closed", "Closed"

    class Treatment(models.TextChoices):
        MITIGATE = "mitigate", "Mitigate"
        AVOID = "avoid", "Avoid"
        TRANSFER = "transfer", "Transfer"
        ACCEPT = "accept", "Accept"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="project_risk_entries",
        null=True,
        blank=True,
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="risk_entries",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    risk_category = models.ForeignKey(
        "settings.RiskCategory",
        on_delete=models.SET_NULL,
        related_name="project_risk_entries",
        null=True,
        blank=True,
    )
    likelihood_key = models.CharField(max_length=32, default="medium")
    likelihood_score = models.PositiveSmallIntegerField(default=3)
    impact_key = models.CharField(max_length=32, default="medium")
    impact_score = models.PositiveSmallIntegerField(default=3)
    risk_score = models.PositiveIntegerField(default=9)
    severity = models.CharField(
        max_length=10,
        choices=Severity.choices,
        default=Severity.MEDIUM,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )
    treatment = models.CharField(
        max_length=20,
        choices=Treatment.choices,
        default=Treatment.MITIGATE,
    )
    mitigation_plan = models.TextField(blank=True)
    mitigation_actions = models.TextField(blank=True)
    contingency_plan = models.TextField(blank=True)
    owner_role = models.ForeignKey(
        "settings.Role",
        on_delete=models.SET_NULL,
        related_name="project_risk_owner_roles",
        null=True,
        blank=True,
    )
    response_time_hours = models.PositiveIntegerField(null=True, blank=True)
    escalation_required = models.BooleanField(default=False)
    identified_on = models.DateField(default=timezone.now)
    target_resolution_date = models.DateField(null=True, blank=True)
    last_reviewed_on = models.DateField(null=True, blank=True)
    resolved_on = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_project_risk_entries",
        null=True,
        blank=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="updated_project_risk_entries",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-risk_score", "-created_at"]
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="proj_risk_org_created_idx"),
        ]

    def __str__(self):
        return f"{self.project.name} — {self.title} ({self.get_severity_display()})"


class ProjectVariationOrder(models.Model):
    """Change order register for project variation orders."""

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
        related_name="org_project_variation_orders",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="variation_orders",
    )
    variation_number = models.CharField(max_length=80, unique=True)
    title = models.CharField(max_length=255)
    change_summary = models.TextField(blank=True)
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    contract_value = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=3, default=get_default_currency_code)
    requested_date = models.DateField(default=timezone.localdate)
    due_date = models.DateField(null=True, blank=True)
    related_document = models.ForeignKey(
        "documents.Document",
        on_delete=models.SET_NULL,
        related_name="variation_orders",
        null=True,
        blank=True,
    )
    cost_code_budget = models.ForeignKey(
        "CostCodeBudget",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="variation_orders",
        help_text="The cost code this variation impacts.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_project_variation_orders",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_project_variation_orders",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["project", "status"]),
            models.Index(fields=["contract_value", "status"]),
            models.Index(fields=["organization", "status"], name="proj_vo_org_status_idx"),
        ]

    def __str__(self):
        return f"{self.variation_number} — {self.title}"


class ProjectWorkforceLog(models.Model):
    """Daily workforce headcount and deployment log for a project."""

    class Shift(models.TextChoices):
        DAY = "day", "Day"
        NIGHT = "night", "Night"
        FULL_DAY = "full_day", "Full Day"

    class AttendanceStatus(models.TextChoices):
        PRESENT = "present", "Present"
        ABSENT = "absent", "Absent"
        LATE = "late", "Late"
        HALF_DAY = "half_day", "Half Day"
        EXCUSED = "excused", "Excused"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_project_workforce_logs",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="workforce_logs",
    )
    worker_id = models.CharField(max_length=120, blank=True)
    employee = models.ForeignKey(
        "hr.EmployeeRecord",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="project_workforce_logs",
    )
    trade = models.CharField(max_length=120, blank=True)
    contractor = models.ForeignKey(
        "procurement.Vendor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="project_workforce_logs",
    )
    report_date = models.DateField(default=timezone.localdate)
    daily_attendance = models.CharField(
        max_length=16,
        choices=AttendanceStatus.choices,
        default=AttendanceStatus.PRESENT,
    )
    shift = models.CharField(max_length=16, choices=Shift.choices, default=Shift.DAY)
    task_assigned = models.ForeignKey(
        ProjectTask,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="workforce_logs",
    )
    productivity = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    overtime_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    laborers_count = models.PositiveIntegerField(default=0)
    skilled_count = models.PositiveIntegerField(default=0)
    supervisors_count = models.PositiveIntegerField(default=0)
    subcontractors_count = models.PositiveIntegerField(default=0)
    equipment_operators_count = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_project_workforce_logs",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_project_workforce_logs",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-report_date", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "report_date", "shift"],
                name="unique_project_workforce_log_per_shift",
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="proj_wlog_org_created_idx"),
        ]

    def __str__(self):
        return f"{self.project.name} workforce {self.report_date} ({self.get_shift_display()})"


class ProjectDailySiteReport(models.Model):
    """Structured daily site execution report for field operations."""

    class Shift(models.TextChoices):
        DAY = "day", "Day"
        NIGHT = "night", "Night"
        FULL_DAY = "full_day", "Full Day"

    class Weather(models.TextChoices):
        CLEAR = "clear", "Clear"
        CLOUDY = "cloudy", "Cloudy"
        RAIN = "rain", "Rain"
        STORM = "storm", "Storm"
        WINDY = "windy", "Windy"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        REVIEWED = "reviewed", "Reviewed"
        CLOSED = "closed", "Closed"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_project_daily_site_reports",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="daily_site_reports",
    )
    report_date = models.DateField(default=timezone.localdate)
    shift = models.CharField(max_length=16, choices=Shift.choices, default=Shift.DAY)
    weather = models.CharField(max_length=16, choices=Weather.choices, default=Weather.CLEAR)
    weather_notes = models.TextField(blank=True)
    weather_delay_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    progress_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00")), MaxValueValidator(Decimal("100.00"))],
    )
    laborers_count = models.PositiveIntegerField(default=0)
    skilled_count = models.PositiveIntegerField(default=0)
    supervisors_count = models.PositiveIntegerField(default=0)
    subcontractors_count = models.PositiveIntegerField(default=0)
    equipment_operators_count = models.PositiveIntegerField(default=0)
    workforce_summary = models.TextField(blank=True)
    work_completed = models.TextField(blank=True)
    planned_next_day = models.TextField(blank=True)
    equipment_used = models.TextField(blank=True)
    materials_delivered = models.TextField(blank=True)
    materials_consumed = models.TextField(blank=True)
    material_updates = models.TextField(blank=True)
    visitors_log = models.TextField(blank=True)
    instructions_issued = models.TextField(blank=True)
    safety_observations = models.TextField(blank=True)
    quality_observations = models.TextField(blank=True)
    incidents = models.TextField(blank=True)
    blockers = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    escalation_required = models.BooleanField(default=False)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submitted_project_daily_site_reports",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_project_daily_site_reports",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_project_daily_site_reports",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_project_daily_site_reports",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-report_date", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "report_date", "shift"],
                name="unique_project_daily_site_report_per_shift",
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="proj_dsr_org_created_idx"),
        ]

    def __str__(self):
        return f"{self.project.name} site report {self.report_date} ({self.get_shift_display()})"


class DailyReportMaterialUsage(models.Model):
    """Structured material consumption record linking daily reports to BOQ items."""

    report = models.ForeignKey(
        ProjectDailySiteReport, on_delete=models.CASCADE,
        related_name="material_usages",
    )
    bom_item = models.ForeignKey(
        "inventory.BOMItem", on_delete=models.CASCADE,
        related_name="daily_report_usages",
        help_text="The specific BOQ item consumed.",
    )
    quantity_used = models.DecimalField(max_digits=12, decimal_places=2)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.bom_item.material_name} × {self.quantity_used}"


class ProjectDailySiteReportPhoto(models.Model):
    """Photo evidence attached to a daily site report."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_project_daily_site_report_photos",
    )
    report = models.ForeignKey(
        ProjectDailySiteReport,
        on_delete=models.CASCADE,
        related_name="photos",
    )
    image = models.ImageField(upload_to=project_daily_report_photo_upload_to)
    caption = models.CharField(max_length=255, blank=True)
    taken_at = models.DateTimeField(null=True, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_project_daily_site_report_photos",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="proj_dsrp_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"Report #{self.report_id} photo {self.id}"


class ProjectExecutionInspection(models.Model):
    """Execution-stage quality inspection log with checklist traceability."""

    class InspectionType(models.TextChoices):
        MATERIAL_RECEIPT = "material_receipt", "Material Receipt"
        WORKMANSHIP = "workmanship", "Workmanship"
        MEP = "mep", "MEP Installation"
        FINISHES = "finishes", "Finishes"
        SAFETY_QUALITY = "safety_quality", "Safety & Quality"
        PRE_HANDOVER = "pre_handover", "Pre-Handover"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        IN_PROGRESS = "in_progress", "In Progress"
        PASSED = "passed", "Passed"
        FAILED = "failed", "Failed"
        BLOCKED = "blocked", "Blocked"
        CLOSED = "closed", "Closed"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_project_execution_inspections",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="execution_inspections",
    )
    phase = models.ForeignKey(
        ProjectPhase,
        on_delete=models.SET_NULL,
        related_name="execution_inspections",
        null=True,
        blank=True,
    )
    source_report = models.ForeignKey(
        ProjectDailySiteReport,
        on_delete=models.SET_NULL,
        related_name="quality_inspections",
        null=True,
        blank=True,
    )
    inspection_number = models.CharField(max_length=100, unique=True, blank=True)
    inspection_type = models.CharField(
        max_length=30,
        choices=InspectionType.choices,
        default=InspectionType.WORKMANSHIP,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNED,
    )
    inspected_on = models.DateField(default=timezone.localdate)
    shift = models.CharField(
        max_length=16,
        choices=ProjectWorkforceLog.Shift.choices,
        default=ProjectWorkforceLog.Shift.DAY,
    )
    work_package = models.CharField(max_length=255, blank=True)
    location = models.CharField(max_length=255, blank=True)
    inspector_name = models.CharField(max_length=255)
    inspector_role = models.CharField(max_length=255, blank=True)
    overall_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("100.00")),
        ],
    )
    critical_findings = models.PositiveIntegerField(default=0)
    major_findings = models.PositiveIntegerField(default=0)
    minor_findings = models.PositiveIntegerField(default=0)
    observations = models.TextField(blank=True)
    corrective_actions = models.TextField(blank=True)
    due_date = models.DateField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_project_execution_inspections",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_project_execution_inspections",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-inspected_on", "-created_at"]
        indexes = [
            models.Index(fields=["project", "status", "inspected_on"]),
            models.Index(fields=["inspection_type", "status", "inspected_on"]),
        ]

    def __str__(self):
        return f"{self.inspection_number} — {self.project.name}"

    def save(self, **kwargs):
        if not self.inspection_number:
            self.inspection_number = self._generate_inspection_number()
        super().save(**kwargs)

    @staticmethod
    def _generate_inspection_number() -> str:
        last = (
            ProjectExecutionInspection.objects.filter(
                inspection_number__startswith="QINSP-"
            )
            .order_by("-inspection_number")
            .values_list("inspection_number", flat=True)
            .first()
        )
        if last:
            try:
                seq = int(last.split("-", 1)[1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f"QINSP-{seq:05d}"


class ProjectExecutionInspectionItem(models.Model):
    """Checklist row for project execution inspections."""

    class Result(models.TextChoices):
        PASS = "pass", "Pass"
        FAIL = "fail", "Fail"
        HOLD = "hold", "Hold"
        NA = "na", "Not Applicable"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_project_execution_inspection_items",
    )
    inspection = models.ForeignKey(
        ProjectExecutionInspection,
        on_delete=models.CASCADE,
        related_name="checklist_items",
    )
    sort_order = models.PositiveIntegerField(default=0)
    checklist_group = models.CharField(max_length=120, blank=True)
    checklist_item = models.CharField(max_length=255)
    result = models.CharField(
        max_length=16,
        choices=Result.choices,
        default=Result.PASS,
    )
    remarks = models.TextField(blank=True)
    action_owner = models.CharField(max_length=255, blank=True)
    action_due_date = models.DateField(null=True, blank=True)
    resolved_on = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "id"]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="proj_eii_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.inspection.inspection_number} — {self.checklist_item}"


class ProjectSupportingAttachment(models.Model):
    """Supporting file attached to project module records."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_project_supporting_attachments",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="supporting_attachments",
    )
    variation = models.ForeignKey(
        ProjectVariationOrder,
        on_delete=models.CASCADE,
        related_name="supporting_attachments",
        null=True,
        blank=True,
    )
    phase = models.ForeignKey(
        ProjectPhase,
        on_delete=models.CASCADE,
        related_name="supporting_attachments",
        null=True,
        blank=True,
    )
    milestone = models.ForeignKey(
        ProjectMilestone,
        on_delete=models.CASCADE,
        related_name="supporting_attachments",
        null=True,
        blank=True,
    )
    task = models.ForeignKey(
        ProjectTask,
        on_delete=models.CASCADE,
        related_name="supporting_attachments",
        null=True,
        blank=True,
    )
    cost_entry = models.ForeignKey(
        ProjectCostEntry,
        on_delete=models.CASCADE,
        related_name="supporting_attachments",
        null=True,
        blank=True,
    )
    risk_entry = models.ForeignKey(
        ProjectRiskRegisterEntry,
        on_delete=models.CASCADE,
        related_name="supporting_attachments",
        null=True,
        blank=True,
    )
    workforce_log = models.ForeignKey(
        ProjectWorkforceLog,
        on_delete=models.CASCADE,
        related_name="supporting_attachments",
        null=True,
        blank=True,
    )
    site_report = models.ForeignKey(
        ProjectDailySiteReport,
        on_delete=models.CASCADE,
        related_name="supporting_attachments",
        null=True,
        blank=True,
    )
    quality_inspection = models.ForeignKey(
        ProjectExecutionInspection,
        on_delete=models.CASCADE,
        related_name="supporting_attachments",
        null=True,
        blank=True,
    )
    escalation = models.ForeignKey(
        "projects.ProjectFieldEscalation",
        on_delete=models.CASCADE,
        related_name="supporting_attachments",
        null=True,
        blank=True,
    )
    file = models.FileField(upload_to=project_supporting_attachment_upload_to)
    caption = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_project_supporting_attachments",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="proj_sa_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"Project {self.project_id} supporting attachment {self.id}"


class ProjectFieldEscalation(models.Model):
    """Escalation records raised from field execution issues."""

    class IssueCategory(models.TextChoices):
        WEATHER = "weather", "Weather"
        SAFETY = "safety", "Safety"
        QUALITY = "quality", "Quality"
        SCHEDULE = "schedule", "Schedule"
        COST = "cost", "Cost"
        WORKFORCE = "workforce", "Workforce"
        PROCUREMENT = "procurement", "Procurement"
        EQUIPMENT = "equipment", "Equipment"
        DESIGN = "design", "Design"
        COMPLIANCE = "compliance", "Compliance"
        LOGISTICS = "logistics", "Logistics"
        COMMUNITY = "community", "Community"
        OPERATIONS = "operations", "Operations"
        EXTERNAL = "external", "External"
        OTHER = "other", "Other"

    class IssueType(models.TextChoices):
        WEATHER_DELAY = "weather_delay", "Weather Delay"
        EXTREME_RAIN_FLOODING = "extreme_rain_flooding", "Extreme Rain / Flooding"
        HIGH_WIND = "high_wind", "High Wind"
        LIGHTNING_STORM = "lightning_storm", "Lightning Storm"
        EXTREME_HEAT = "extreme_heat", "Extreme Heat"
        MATERIAL_SHORTAGE = "material_shortage", "Material Shortage"
        MATERIAL_DAMAGE = "material_damage", "Material Damage"
        LATE_DELIVERY = "late_delivery", "Late Delivery"
        VENDOR_NON_PERFORMANCE = "vendor_non_performance", "Vendor Non-Performance"
        SUBCONTRACTOR_NON_PERFORMANCE = "subcontractor_non_performance", "Subcontractor Non-Performance"
        WORKFORCE_SHORTAGE = "workforce_shortage", "Workforce Shortage"
        LABOR_DISPUTE = "labor_dispute", "Labor Dispute"
        EQUIPMENT_BREAKDOWN = "equipment_breakdown", "Equipment Breakdown"
        EQUIPMENT_UNAVAILABLE = "equipment_unavailable", "Equipment Unavailable"
        QUALITY_DEFECT = "quality_defect", "Quality Defect"
        REWORK_REQUIRED = "rework_required", "Rework Required"
        INSPECTION_FAILURE = "inspection_failure", "Inspection Failure"
        TEST_FAILURE = "test_failure", "Test Failure"
        SAFETY_INCIDENT = "safety_incident", "Safety Incident"
        NEAR_MISS = "near_miss", "Near Miss"
        ACCIDENT_INJURY = "accident_injury", "Accident / Injury"
        SECURITY_BREACH = "security_breach", "Security Breach"
        THEFT_VANDALISM = "theft_vandalism", "Theft / Vandalism"
        DESIGN_CHANGE = "design_change", "Design Change"
        DRAWING_CONFLICT = "drawing_conflict", "Drawing Conflict"
        RFI_PENDING = "rfi_pending", "RFI Pending"
        PERMIT_HOLD = "permit_hold", "Permit Hold"
        REGULATORY_STOP_NOTICE = "regulatory_stop_notice", "Regulatory Stop Notice"
        ENVIRONMENTAL_NON_COMPLIANCE = "environmental_non_compliance", "Environmental Non-Compliance"
        ACCESS_RESTRICTION = "access_restriction", "Access Restriction"
        TRAFFIC_LOGISTICS = "traffic_logistics", "Traffic / Logistics Constraint"
        UTILITY_OUTAGE = "utility_outage", "Utility Outage"
        COMMUNITY_COMPLAINT = "community_complaint", "Community Complaint"
        SCOPE_CHANGE = "scope_change", "Scope Change"
        SCHEDULE_SLIPPAGE = "schedule_slippage", "Schedule Slippage"
        COST_OVERRUN = "cost_overrun", "Cost Overrun"
        PAYMENT_DELAY = "payment_delay", "Payment Delay"
        IT_SYSTEM_OUTAGE = "it_system_outage", "IT System Outage"
        DATA_LOSS = "data_loss", "Data Loss"
        HANDOVER_DEFECT = "handover_defect", "Handover Defect"
        FORCE_MAJEURE = "force_majeure", "Force Majeure"
        GENERAL_SITE_ISSUE = "general_site_issue", "General Site Issue"
        OTHER = "other", "Other"

    class Severity(models.TextChoices):
        INFO = "info", "Info"
        REVIEW = "review", "Review"
        ACTION_REQUIRED = "action_required", "Action Required"
        ESCALATION = "escalation", "Escalation"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        ACKNOWLEDGED = "acknowledged", "Acknowledged"
        IN_PROGRESS = "in_progress", "In Progress"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_project_field_escalations",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="field_escalations",
    )
    source_report = models.ForeignKey(
        ProjectDailySiteReport,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="escalations",
    )
    issue_date = models.DateField(default=timezone.localdate)
    issue_category = models.CharField(
        max_length=24,
        choices=IssueCategory.choices,
        default=IssueCategory.OPERATIONS,
    )
    issue_type = models.CharField(
        max_length=40,
        choices=IssueType.choices,
        default=IssueType.GENERAL_SITE_ISSUE,
    )
    location = models.CharField(max_length=255, blank=True)
    weather_condition = models.CharField(
        max_length=16,
        choices=ProjectDailySiteReport.Weather.choices,
        blank=True,
    )
    weather_delay_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    estimated_schedule_impact_days = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    estimated_cost_impact = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    impact_summary = models.TextField(blank=True)
    root_cause = models.TextField(blank=True)
    immediate_action = models.TextField(blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.REVIEW)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    owner_name = models.CharField(max_length=255, blank=True)
    due_date = models.DateField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_project_field_escalations",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_project_field_escalations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-issue_date", "-created_at"]
        indexes = [
            models.Index(fields=["project", "issue_date", "status"]),
            models.Index(fields=["issue_category", "issue_type", "status"]),
            models.Index(fields=["issue_type", "issue_date"]),
        ]

    def __str__(self):
        return f"{self.project.name} issue: {self.title}"


class ProjectScheduleDelayLog(models.Model):
    """Operational delay register for schedule slippages and root-cause tracking."""

    class DelayType(models.TextChoices):
        WEATHER = "weather", "Weather"
        PERMIT = "permit", "Permit / Regulatory"
        DESIGN = "design", "Design / RFI"
        PROCUREMENT = "procurement", "Procurement / Delivery"
        WORKFORCE = "workforce", "Workforce"
        EQUIPMENT = "equipment", "Equipment"
        SAFETY = "safety", "Safety Incident"
        FINANCIAL = "financial", "Financial / Payment"
        CLIENT = "client", "Client Change"
        OTHER = "other", "Other"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_project_schedule_delay_logs",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="schedule_delay_logs",
    )
    phase = models.ForeignKey(
        ProjectPhase,
        on_delete=models.SET_NULL,
        related_name="delay_logs",
        null=True,
        blank=True,
    )
    milestone = models.ForeignKey(
        ProjectMilestone,
        on_delete=models.SET_NULL,
        related_name="delay_logs",
        null=True,
        blank=True,
    )
    source_issue = models.ForeignKey(
        "projects.ProjectFieldEscalation",
        on_delete=models.SET_NULL,
        related_name="delay_logs",
        null=True,
        blank=True,
    )
    delay_date = models.DateField(default=timezone.localdate)
    delay_type = models.CharField(
        max_length=20,
        choices=DelayType.choices,
        default=DelayType.OTHER,
    )
    impact_days = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    reason = models.TextField(blank=True)
    mitigation_action = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_project_schedule_delay_logs",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-delay_date", "-created_at"]
        indexes = [
            models.Index(fields=["project", "delay_date"]),
            models.Index(fields=["delay_type", "delay_date"]),
        ]

    def __str__(self):
        return f"{self.project.name} delay {self.delay_date} ({self.delay_type})"


class ProjectConstructionWorkspace(models.Model):
    """Project-level construction workspace artifacts initialized at project creation."""

    class WorkspaceType(models.TextChoices):
        SITE_OVERVIEW_DASHBOARD = (
            "site_overview_dashboard",
            "Site Overview Dashboard",
        )
        SITE_MOBILIZATION_WORKSPACE = (
            "site_mobilization_workspace",
            "Site Mobilization Workspace",
        )
        CONSTRUCTION_SCHEDULE = (
            "construction_schedule_workspace",
            "Construction Schedule Workspace",
        )
        CONTRACTOR_MANAGEMENT = (
            "contractor_management_workspace",
            "Contractor Management Workspace",
        )

    class MenuGroup(models.TextChoices):
        DASHBOARD = "dashboard", "Dashboard"
        PRE_CONSTRUCTION = "pre_construction", "Pre-Construction"
        EXECUTION = "execution", "Execution"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="project_construction_workspaces",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="construction_workspaces",
    )
    workspace_type = models.CharField(
        max_length=48,
        choices=WorkspaceType.choices,
    )
    name = models.CharField(max_length=120)
    menu_path = models.CharField(max_length=255)
    menu_group = models.CharField(
        max_length=32,
        choices=MenuGroup.choices,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["project", "workspace_type"]
        unique_together = [("project", "workspace_type")]
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="proj_cws_org_created_idx"),
            models.Index(fields=["project", "menu_group"], name="proj_cws_proj_group_idx"),
        ]

    def __str__(self):
        return f"{self.project.name} — {self.get_workspace_type_display()}"


class ProjectContractorProfile(models.Model):
    """Project-scoped contractor management record with linked execution artifacts."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="project_contractor_profiles",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="contractor_profiles",
    )
    contractor = models.ForeignKey(
        "procurement.Vendor",
        on_delete=models.CASCADE,
        related_name="project_contractor_profiles",
    )
    company_profile = models.TextField(blank=True)
    trade_specialization = models.CharField(max_length=255, blank=True)
    contract_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    insurance = models.TextField(blank=True)
    licenses = models.TextField(blank=True)
    performance_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("5.00")),
        ],
    )
    payment_history = models.TextField(blank=True)
    safety_record = models.TextField(blank=True)
    quality_record = models.TextField(blank=True)
    site_instructions = models.TextField(blank=True)
    work_packages = models.ManyToManyField(
        "projects.ProjectWorkPackage",
        blank=True,
        related_name="contractor_profiles",
    )
    rfis = models.ManyToManyField(
        "projects.ProjectFieldEscalation",
        blank=True,
        related_name="contractor_profiles",
    )
    inspection_results = models.ManyToManyField(
        "projects.ProjectExecutionInspection",
        blank=True,
        related_name="contractor_profiles",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_project_contractor_profiles",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_project_contractor_profiles",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "contractor"],
                name="uniq_project_contractor_profile",
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "-updated_at"], name="proj_cp_org_updated_idx"),
            models.Index(fields=["project", "contractor"], name="proj_cp_project_contractor_idx"),
        ]

    def __str__(self):
        return f"{self.project.name} — {self.contractor.name}"


class ProjectSiteMobilization(models.Model):
    """Pre-construction mobilization tracker linked to Procurement and HR signals."""

    class PreparationStatus(models.TextChoices):
        NOT_STARTED = "not_started", "Not Started"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        BLOCKED = "blocked", "Blocked"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="project_site_mobilizations",
    )
    project = models.OneToOneField(
        Project,
        on_delete=models.CASCADE,
        related_name="site_mobilization",
    )

    planned_start_date = models.DateField(null=True, blank=True)
    actual_start_date = models.DateField(null=True, blank=True)

    # Site preparation
    fencing_status = models.CharField(
        max_length=20,
        choices=PreparationStatus.choices,
        default=PreparationStatus.NOT_STARTED,
    )
    site_offices_status = models.CharField(
        max_length=20,
        choices=PreparationStatus.choices,
        default=PreparationStatus.NOT_STARTED,
    )
    storage_yards_status = models.CharField(
        max_length=20,
        choices=PreparationStatus.choices,
        default=PreparationStatus.NOT_STARTED,
    )
    worker_welfare_facilities_status = models.CharField(
        max_length=20,
        choices=PreparationStatus.choices,
        default=PreparationStatus.NOT_STARTED,
    )
    utilities_connection_status = models.CharField(
        max_length=20,
        choices=PreparationStatus.choices,
        default=PreparationStatus.NOT_STARTED,
    )
    temporary_roads_status = models.CharField(
        max_length=20,
        choices=PreparationStatus.choices,
        default=PreparationStatus.NOT_STARTED,
    )
    security_deployment_status = models.CharField(
        max_length=20,
        choices=PreparationStatus.choices,
        default=PreparationStatus.NOT_STARTED,
    )

    # Mobilization checklist
    contractors_mobilized = models.BooleanField(default=False)
    equipment_delivered = models.BooleanField(default=False)
    material_staging = models.BooleanField(default=False)
    survey_control_established = models.BooleanField(default=False)
    permits_obtained = models.BooleanField(default=False)
    insurance_certificates = models.BooleanField(default=False)
    safety_induction = models.BooleanField(default=False)

    # Linked signals from Procurement + HR
    linked_procurement_contractors_count = models.PositiveIntegerField(default=0)
    linked_procurement_material_staging_count = models.PositiveIntegerField(default=0)
    linked_hr_equipment_delivery_count = models.PositiveIntegerField(default=0)
    linked_hr_safety_induction_count = models.PositiveIntegerField(default=0)
    last_integrations_synced_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-created_at"]
        indexes = [
            models.Index(fields=["organization", "-updated_at"], name="proj_sm_org_updated_idx"),
        ]

    def __str__(self):
        return f"{self.project.name} — Site Mobilization"


class ProjectConstructionSchedule(models.Model):
    """Execution timeline workspace for construction schedule management."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="project_construction_schedules",
    )
    project = models.OneToOneField(
        Project,
        on_delete=models.CASCADE,
        related_name="construction_schedule",
    )
    lookahead_window_days = models.PositiveSmallIntegerField(
        default=21,
        validators=[MinValueValidator(7), MaxValueValidator(90)],
    )

    # Schedule section notes
    master_schedule_notes = models.TextField(blank=True)
    phase_schedule_notes = models.TextField(blank=True)
    lookahead_schedule_notes = models.TextField(blank=True)
    task_dependency_notes = models.TextField(blank=True)
    critical_path_notes = models.TextField(blank=True)
    resource_assignment_notes = models.TextField(blank=True)

    # Timeline fields for role-based execution inputs
    project_manager_updates = models.TextField(blank=True)
    task_assignee_updates = models.TextField(blank=True)
    site_worker_updates = models.TextField(blank=True)

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-created_at"]
        indexes = [
            models.Index(fields=["organization", "-updated_at"], name="proj_cs_org_updated_idx"),
        ]

    def __str__(self):
        return f"{self.project.name} — Construction Schedule"


# ---------------------------------------------------------------------------
# Equipment & Machinery
# ---------------------------------------------------------------------------


class ProjectEquipment(models.Model):
    """A high-value physical asset tracked across construction sites."""

    class Status(models.TextChoices):
        OPERATIONAL = "operational", "Operational"
        IN_REPAIR = "in_repair", "In Repair"
        IDLE = "idle", "Idle"
        DECOMMISSIONED = "decommissioned", "Decommissioned"
        IN_TRANSIT = "in_transit", "In Transit"

    class EquipmentType(models.TextChoices):
        EARTHMOVING = "earthmoving", "Earthmoving"
        LIFTING = "lifting", "Lifting"
        MATERIAL_HANDLING = "material_handling", "Material Handling"
        CONCRETE = "concrete", "Concrete"
        PILING = "piling", "Piling"
        COMPACTION = "compaction", "Compaction"
        TRANSPORT = "transport", "Transport"
        SCAFFOLDING = "scaffolding", "Scaffolding"
        POWER_GENERATION = "power_generation", "Power Generation"
        OTHER = "other", "Other"

    class FuelType(models.TextChoices):
        DIESEL = "diesel", "Diesel"
        PETROL = "petrol", "Petrol"
        ELECTRIC = "electric", "Electric"
        HYBRID = "hybrid", "Hybrid"
        NA = "na", "N/A"

    class Ownership(models.TextChoices):
        OWNED = "owned", "Owned"
        LEASED = "leased", "Leased"
        RENTED = "rented", "Rented"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="equipment",
    )

    # --- Identity ---
    asset_id = models.CharField(max_length=50, unique=True, blank=True)
    name = models.CharField(max_length=255)
    equipment_type = models.CharField(
        max_length=30, choices=EquipmentType.choices, default=EquipmentType.OTHER,
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.IDLE,
    )
    make = models.CharField(max_length=100, blank=True)
    model_name = models.CharField(max_length=100, blank=True)
    year_of_manufacture = models.PositiveSmallIntegerField(null=True, blank=True)

    # --- Technical Specifications ---
    serial_number = models.CharField(max_length=100, blank=True)
    engine_number = models.CharField(max_length=100, blank=True)
    fuel_type = models.CharField(
        max_length=20, choices=FuelType.choices, default=FuelType.DIESEL,
    )
    fuel_consumption_rate = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        help_text="Litres per hour",
    )
    capacity = models.CharField(
        max_length=100, blank=True, help_text="e.g. 15 Ton, 380 HP",
    )
    weight_kg = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
    )

    # --- Location & Deployment ---
    current_project = models.ForeignKey(
        "projects.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="equipment_on_site",
    )
    current_location = models.CharField(
        max_length=255, blank=True, help_text="Site name or warehouse",
    )
    gps_latitude = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True,
    )
    gps_longitude = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True,
    )
    current_operator = models.CharField(max_length=255, blank=True)
    operator_license_verified = models.BooleanField(default=False)

    # --- Maintenance & Telematics ---
    hour_meter_reading = models.DecimalField(
        max_digits=10, decimal_places=1, default=0,
        help_text="Current hour meter reading",
    )
    odometer_reading = models.DecimalField(
        max_digits=10, decimal_places=1, default=0,
        help_text="Current odometer (km)",
    )
    last_service_date = models.DateField(null=True, blank=True)
    next_service_due = models.DateField(null=True, blank=True)
    service_interval_hours = models.PositiveIntegerField(
        null=True, blank=True, help_text="Hours between services",
    )

    # --- Financial & Cost Recovery ---
    ownership = models.CharField(
        max_length=20, choices=Ownership.choices, default=Ownership.OWNED,
    )
    purchase_price = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
    )
    current_book_value = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
    )
    internal_daily_rate = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Internal rental charge per day",
    )
    internal_hourly_rate = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Internal rental charge per hour",
    )
    mobilization_cost = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Standard fee for transport between sites",
    )
    insurance_policy_number = models.CharField(max_length=100, blank=True)
    insurance_expiry = models.DateField(null=True, blank=True)

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["asset_id"]
        verbose_name_plural = "Equipment"
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="proj_eq_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="proj_eq_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.asset_id} — {self.name}"

    def save(self, **kwargs):
        if not self.asset_id:
            self.asset_id = self._generate_asset_id()
        super().save(**kwargs)

    @staticmethod
    def _generate_asset_id() -> str:
        last = (
            ProjectEquipment.objects.filter(asset_id__startswith="EQ-")
            .order_by("-asset_id")
            .values_list("asset_id", flat=True)
            .first()
        )
        if last:
            try:
                seq = int(last.split("-", 1)[1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f"EQ-{seq:04d}"


class EquipmentMaintenanceLog(models.Model):
    """Fault logs, parts replaced, and service records."""

    class LogType(models.TextChoices):
        SCHEDULED_SERVICE = "scheduled_service", "Scheduled Service"
        REPAIR = "repair", "Repair"
        BREAKDOWN = "breakdown", "Breakdown"
        INSPECTION = "inspection", "Inspection"
        FUEL_INTAKE = "fuel_intake", "Fuel Intake"

    equipment = models.ForeignKey(
        ProjectEquipment, on_delete=models.CASCADE, related_name="maintenance_logs",
    )
    log_type = models.CharField(
        max_length=30, choices=LogType.choices, default=LogType.SCHEDULED_SERVICE,
    )
    date = models.DateField()
    description = models.TextField()
    parts_replaced = models.TextField(blank=True)
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    performed_by = models.CharField(max_length=255, blank=True)
    hour_meter_at_service = models.DecimalField(
        max_digits=10, decimal_places=1, null=True, blank=True,
    )
    downtime_hours = models.DecimalField(
        max_digits=8, decimal_places=1, default=0,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.equipment.asset_id} — {self.get_log_type_display()} — {self.date}"


class EquipmentDeploymentLog(models.Model):
    """Tracks which project/site a machine worked on and for how long."""

    equipment = models.ForeignKey(
        ProjectEquipment, on_delete=models.CASCADE, related_name="deployment_logs",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="equipment_deployments",
    )
    site_name = models.CharField(max_length=255, blank=True)
    operator = models.CharField(max_length=255, blank=True)
    deployed_date = models.DateField()
    returned_date = models.DateField(null=True, blank=True)
    hours_used = models.DecimalField(
        max_digits=8, decimal_places=1, default=0,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-deployed_date"]

    def __str__(self):
        return f"{self.equipment.asset_id} → {self.project.name} ({self.deployed_date})"


# ── Quality Control ──────────────────────────────────────────────────


class QualityPlan(models.Model):
    """Master quality plan defining inspection strategy for a project or project type."""

    class ReviewCycle(models.TextChoices):
        WEEKLY = "weekly", "Weekly"
        FORTNIGHTLY = "fortnightly", "Fortnightly"
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        BIANNUAL = "biannual", "Bi-Annual"
        ANNUAL = "annual", "Annual"
        AS_NEEDED = "as_needed", "As Needed"

    class ApprovalStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        IN_REVIEW = "in_review", "In Review"
        APPROVED = "approved", "Approved"
        SUPERSEDED = "superseded", "Superseded"
        ARCHIVED = "archived", "Archived"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_quality_plans",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="quality_plans",
        null=True,
        blank=True,
        help_text="Link to a specific project, or leave blank for a reusable template.",
    )
    plan_number = models.CharField(
        max_length=100,
        blank=True,
        unique=True,
        help_text="Auto-generated as QCP-##### when blank.",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    compliance_standards = models.TextField(
        blank=True,
        help_text="References to applicable standards (ISO, NIS, BS, etc.).",
    )
    review_cycle = models.CharField(
        max_length=20,
        choices=ReviewCycle.choices,
        default=ReviewCycle.QUARTERLY,
    )
    approval_status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.DRAFT,
    )
    approved_by = models.CharField(max_length=255, blank=True)
    approved_date = models.DateField(null=True, blank=True)
    next_review_date = models.DateField(null=True, blank=True)
    revision = models.PositiveIntegerField(default=1)
    notes = models.TextField(blank=True)

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
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["organization", "approval_status"],
                name="qcp_org_status_idx",
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.plan_number:
            last = (
                QualityPlan.objects.filter(plan_number__startswith="QCP-")
                .order_by("-plan_number")
                .values_list("plan_number", flat=True)
                .first()
            )
            seq = 1
            if last:
                try:
                    seq = int(last.split("-")[1]) + 1
                except (IndexError, ValueError):
                    pass
            self.plan_number = f"QCP-{seq:05d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.plan_number} — {self.name}"


class QualityCheckTemplate(models.Model):
    """Individual inspection check point within a quality plan."""

    class EvidenceType(models.TextChoices):
        NUMERICAL = "numerical", "Numerical Entry"
        PHOTO = "photo", "Photo Upload"
        PASS_FAIL = "pass_fail", "Pass / Fail"
        TEXT = "text", "Text / Notes"
        DOCUMENT = "document", "Document Upload"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_quality_check_templates",
    )
    quality_plan = models.ForeignKey(
        QualityPlan,
        on_delete=models.CASCADE,
        related_name="check_templates",
    )
    check_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="Auto-generated as QA-### when blank.",
    )
    inspection_point = models.CharField(max_length=255)
    requirement_standard = models.TextField(
        blank=True,
        help_text="Specific requirement or reference standard.",
    )
    evidence_type = models.CharField(
        max_length=20,
        choices=EvidenceType.choices,
        default=EvidenceType.PASS_FAIL,
    )
    is_critical = models.BooleanField(
        default=False,
        help_text="Critical checks trigger automatic NCR on failure.",
    )
    sort_order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "id"]

    def save(self, *args, **kwargs):
        if not self.check_id:
            last = (
                QualityCheckTemplate.objects.filter(
                    quality_plan=self.quality_plan,
                    check_id__startswith="QA-",
                )
                .order_by("-check_id")
                .values_list("check_id", flat=True)
                .first()
            )
            seq = 101
            if last:
                try:
                    seq = int(last.split("-")[1]) + 1
                except (IndexError, ValueError):
                    pass
            self.check_id = f"QA-{seq:03d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.check_id} — {self.inspection_point}"


class NonConformanceReport(models.Model):
    """NCR raised when an inspection check fails — tracks defect through resolution."""

    class Severity(models.TextChoices):
        CRITICAL = "critical", "Critical / Safety"
        MAJOR = "major", "Major"
        MINOR = "minor", "Minor / Cosmetic"
        OBSERVATION = "observation", "Observation"

    class RootCause(models.TextChoices):
        MATERIAL_DEFECT = "material_defect", "Material Defect"
        WORKMANSHIP = "workmanship", "Workmanship"
        DESIGN_ERROR = "design_error", "Design Error"
        WEATHER = "weather", "Weather / Environmental"
        EQUIPMENT = "equipment", "Equipment Failure"
        PROCESS = "process", "Process Non-compliance"
        OTHER = "other", "Other"

    class NCRStatus(models.TextChoices):
        OPEN = "open", "Open"
        UNDER_REVIEW = "under_review", "Under Review"
        RECTIFICATION = "rectification", "Rectification In Progress"
        VERIFICATION = "verification", "Awaiting Verification"
        CLOSED = "closed", "Closed"
        ACCEPTED = "accepted", "Accepted (Use As-Is)"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_ncrs",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="ncrs",
    )
    inspection = models.ForeignKey(
        "ProjectExecutionInspection",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ncrs",
    )
    ncr_number = models.CharField(
        max_length=100,
        blank=True,
        unique=True,
        help_text="Auto-generated as NCR-##### when blank.",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        default=Severity.MINOR,
    )
    root_cause = models.CharField(
        max_length=30,
        choices=RootCause.choices,
        default=RootCause.WORKMANSHIP,
    )
    status = models.CharField(
        max_length=20,
        choices=NCRStatus.choices,
        default=NCRStatus.OPEN,
    )
    location = models.CharField(max_length=255, blank=True)
    raised_by = models.CharField(max_length=255, blank=True)
    raised_date = models.DateField(auto_now_add=True)
    assigned_to = models.CharField(max_length=255, blank=True)
    rectification_plan = models.TextField(blank=True)
    rectification_due_date = models.DateField(null=True, blank=True)
    rectification_completed_date = models.DateField(null=True, blank=True)
    verification_notes = models.TextField(blank=True)
    verified_by = models.CharField(max_length=255, blank=True)
    closed_date = models.DateField(null=True, blank=True)
    cost_impact = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Estimated cost impact of the non-conformance.",
    )
    schedule_impact_days = models.PositiveIntegerField(
        default=0,
        help_text="Estimated schedule delay in days.",
    )
    notes = models.TextField(blank=True)

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
        ordering = ["-raised_date", "-created_at"]
        indexes = [
            models.Index(
                fields=["organization", "status", "severity"],
                name="ncr_org_status_sev_idx",
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.ncr_number:
            last = (
                NonConformanceReport.objects.filter(ncr_number__startswith="NCR-")
                .order_by("-ncr_number")
                .values_list("ncr_number", flat=True)
                .first()
            )
            seq = 1
            if last:
                try:
                    seq = int(last.split("-")[1]) + 1
                except (IndexError, ValueError):
                    pass
            self.ncr_number = f"NCR-{seq:05d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ncr_number} — {self.title}"


# ── HSE (Health, Safety & Environment) ───────────────────────────────


class HSEIncident(models.Model):
    class Classification(models.TextChoices):
        NEAR_MISS = "near_miss", "Near Miss"
        FIRST_AID = "first_aid", "First Aid"
        MINOR_INJURY = "minor_injury", "Minor Injury"
        MAJOR_ACCIDENT = "major_accident", "Major Accident"
        FATALITY = "fatality", "Fatality"
        ENVIRONMENTAL = "environmental", "Environmental Spill"
        PROPERTY_DAMAGE = "property_damage", "Property Damage"

    class RootCause(models.TextChoices):
        HUMAN_ERROR = "human_error", "Human Error"
        EQUIPMENT_FAILURE = "equipment_failure", "Equipment Failure"
        UNSAFE_CONDITIONS = "unsafe_conditions", "Unsafe Work Conditions"
        LACK_OF_TRAINING = "lack_of_training", "Lack of Training"
        PPE_FAILURE = "ppe_failure", "PPE Failure / Not Worn"
        WEATHER = "weather", "Weather / Environmental"
        PROCEDURAL = "procedural", "Procedural Non-compliance"
        OTHER = "other", "Other"

    class IncidentStatus(models.TextChoices):
        REPORTED = "reported", "Reported"
        INVESTIGATING = "investigating", "Investigating"
        CORRECTIVE_ACTION = "corrective_action", "Corrective Action"
        CLOSED = "closed", "Closed"

    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="org_hse_incidents")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="hse_incidents")
    incident_number = models.CharField(max_length=100, blank=True, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    classification = models.CharField(max_length=30, choices=Classification.choices, default=Classification.NEAR_MISS)
    root_cause = models.CharField(max_length=30, choices=RootCause.choices, blank=True)
    status = models.CharField(max_length=30, choices=IncidentStatus.choices, default=IncidentStatus.REPORTED)
    location = models.CharField(max_length=255, blank=True)
    incident_date = models.DateField()
    incident_time = models.TimeField(null=True, blank=True)
    reported_by = models.CharField(max_length=255, blank=True)
    persons_involved = models.TextField(blank=True)
    witness_statements = models.TextField(blank=True)
    injuries_description = models.TextField(blank=True)
    lost_time_days = models.PositiveIntegerField(default=0)
    corrective_actions = models.TextField(blank=True)
    preventive_actions = models.TextField(blank=True)
    requires_regulatory_report = models.BooleanField(default=False)
    closed_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-incident_date", "-created_at"]
        indexes = [models.Index(fields=["organization", "classification", "status"], name="hse_inc_org_cls_sts_idx")]

    def save(self, *args, **kwargs):
        if not self.incident_number:
            last = HSEIncident.objects.filter(incident_number__startswith="INC-").order_by("-incident_number").values_list("incident_number", flat=True).first()
            seq = int(last.split("-")[1]) + 1 if last else 1
            self.incident_number = f"INC-{seq:05d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.incident_number} — {self.title}"


class HSEPermitToWork(models.Model):
    class PermitType(models.TextChoices):
        WORKING_AT_HEIGHTS = "working_at_heights", "Working at Heights"
        HOT_WORK = "hot_work", "Hot Work (Welding/Cutting)"
        EXCAVATION = "excavation", "Excavation"
        ELECTRICAL_ISOLATION = "electrical_isolation", "Electrical Isolation"
        CONFINED_SPACE = "confined_space", "Confined Space Entry"
        LIFTING_OPERATIONS = "lifting_operations", "Lifting Operations"
        DEMOLITION = "demolition", "Demolition"
        OTHER = "other", "Other"

    class PermitStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING_APPROVAL = "pending_approval", "Pending Approval"
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"
        EXPIRED = "expired", "Expired"
        CLOSED = "closed", "Closed"
        REVOKED = "revoked", "Revoked"

    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="org_hse_permits")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="hse_permits")
    permit_number = models.CharField(max_length=100, blank=True, unique=True)
    permit_type = models.CharField(max_length=30, choices=PermitType.choices)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=30, choices=PermitStatus.choices, default=PermitStatus.DRAFT)
    location = models.CharField(max_length=255, blank=True)
    task_description = models.TextField(blank=True)
    hazards_identified = models.TextField(blank=True)
    mitigations = models.TextField(blank=True)
    required_ppe = models.TextField(blank=True)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    requested_by = models.CharField(max_length=255, blank=True)
    approved_by = models.CharField(max_length=255, blank=True)
    approved_date = models.DateTimeField(null=True, blank=True)
    site_supervisor_signoff = models.CharField(max_length=255, blank=True)
    site_supervisor_signoff_date = models.DateTimeField(null=True, blank=True)
    closed_by = models.CharField(max_length=255, blank=True)
    closed_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["organization", "status", "permit_type"], name="hse_ptw_org_sts_type_idx")]

    def save(self, *args, **kwargs):
        if not self.permit_number:
            last = HSEPermitToWork.objects.filter(permit_number__startswith="PTW-").order_by("-permit_number").values_list("permit_number", flat=True).first()
            seq = int(last.split("-")[1]) + 1 if last else 1
            self.permit_number = f"PTW-{seq:05d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.permit_number} — {self.title}"


class HSEToolboxTalk(models.Model):
    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="org_hse_toolbox_talks")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="hse_toolbox_talks")
    tbt_number = models.CharField(max_length=100, blank=True, unique=True)
    topic = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    conducted_by = models.CharField(max_length=255, blank=True)
    conducted_date = models.DateField()
    shift = models.CharField(max_length=16, choices=ProjectWorkforceLog.Shift.choices, default=ProjectWorkforceLog.Shift.DAY)
    location = models.CharField(max_length=255, blank=True)
    attendees_count = models.PositiveIntegerField(default=0)
    attendees_names = models.TextField(blank=True)
    key_points = models.TextField(blank=True)
    follow_up_actions = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-conducted_date", "-created_at"]

    def save(self, *args, **kwargs):
        if not self.tbt_number:
            last = HSEToolboxTalk.objects.filter(tbt_number__startswith="TBT-").order_by("-tbt_number").values_list("tbt_number", flat=True).first()
            seq = int(last.split("-")[1]) + 1 if last else 1
            self.tbt_number = f"TBT-{seq:05d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.tbt_number} — {self.topic}"


# ── RFI (Request for Information) ────────────────────────────────────


class RFI(models.Model):
    class Discipline(models.TextChoices):
        STRUCTURAL = "structural", "Structural"
        ELECTRICAL = "electrical", "Electrical"
        MECHANICAL = "mechanical", "Mechanical"
        CIVIL = "civil", "Civil"
        ARCHITECTURAL = "architectural", "Architectural"
        PLUMBING = "plumbing", "Plumbing"
        FIRE = "fire", "Fire Protection"
        PROCUREMENT = "procurement", "Procurement"
        OTHER = "other", "Other"

    class Urgency(models.TextChoices):
        HIGH = "high", "High — Work Stopped"
        NORMAL = "normal", "Normal"
        LOW = "low", "Low — Future Phase"

    class RFIStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        OPEN = "open", "Open"
        UNDER_REVIEW = "under_review", "Under Review"
        ANSWERED = "answered", "Answered"
        CLOSED = "closed", "Closed"
        VOID = "void", "Void"

    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="org_rfis")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="rfis")
    rfi_number = models.CharField(max_length=100, blank=True, unique=True)
    subject = models.CharField(max_length=255)
    query = models.TextField()
    discipline = models.CharField(max_length=30, choices=Discipline.choices, default=Discipline.OTHER)
    urgency = models.CharField(max_length=20, choices=Urgency.choices, default=Urgency.NORMAL)
    status = models.CharField(max_length=20, choices=RFIStatus.choices, default=RFIStatus.OPEN)
    ball_in_court = models.CharField(max_length=255, blank=True)
    proposed_solution = models.TextField(blank=True)
    reference = models.CharField(max_length=255, blank=True)
    location = models.CharField(max_length=255, blank=True)
    submitted_by = models.CharField(max_length=255, blank=True)
    submitted_date = models.DateField(auto_now_add=True)
    response = models.TextField(blank=True)
    responded_by = models.CharField(max_length=255, blank=True)
    responded_date = models.DateField(null=True, blank=True)
    has_cost_impact = models.BooleanField(default=False)
    has_schedule_impact = models.BooleanField(default=False)
    cost_impact_notes = models.TextField(blank=True)
    schedule_impact_notes = models.TextField(blank=True)
    response_sla_hours = models.PositiveIntegerField(default=48)
    closed_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "RFI"
        verbose_name_plural = "RFIs"
        indexes = [models.Index(fields=["organization", "status", "urgency"], name="rfi_org_sts_urg_idx")]

    def save(self, *args, **kwargs):
        if not self.rfi_number:
            last = RFI.objects.filter(rfi_number__startswith="RFI-").order_by("-rfi_number").values_list("rfi_number", flat=True).first()
            seq = int(last.split("-")[1]) + 1 if last else 1
            self.rfi_number = f"RFI-{seq:05d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.rfi_number} — {self.subject}"


class RFIComment(models.Model):
    rfi = models.ForeignKey(RFI, on_delete=models.CASCADE, related_name="comments")
    author_name = models.CharField(max_length=255)
    body = models.TextField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment on {self.rfi.rfi_number} by {self.author_name}"


# ── Progress Measurement ─────────────────────────────────────────────


class ProgressMeasurement(models.Model):
    class MeasurementMethod(models.TextChoices):
        UNITS_COMPLETE = "units_complete", "Units Complete"
        COST_RATIO = "cost_ratio", "Cost Ratio"
        MILESTONES = "milestones", "Milestone Weighted"
        SUPERVISOR = "supervisor", "Supervisor Estimate"
        EARNED_VALUE = "earned_value", "Earned Value"

    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="org_progress_measurements")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="progress_measurements")
    phase = models.ForeignKey(ProjectPhase, on_delete=models.SET_NULL, null=True, blank=True, related_name="progress_measurements")
    task = models.ForeignKey(ProjectTask, on_delete=models.SET_NULL, null=True, blank=True, related_name="progress_measurements")
    work_package = models.ForeignKey("ProjectWorkPackage", on_delete=models.SET_NULL, null=True, blank=True, related_name="progress_measurements")
    bom_item = models.ForeignKey(
        "inventory.BOMItem", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="progress_measurements",
        help_text="Optional: measure progress for a specific BOQ item.",
    )
    measurement_date = models.DateField()
    measurement_method = models.CharField(max_length=20, choices=MeasurementMethod.choices, default=MeasurementMethod.SUPERVISOR)
    planned_progress = models.DecimalField(max_digits=6, decimal_places=2, validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))])
    actual_progress = models.DecimalField(max_digits=6, decimal_places=2, validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))])
    earned_value = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    planned_value = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    actual_cost = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    quantity_planned = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    quantity_complete = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    unit_of_measure = models.CharField(max_length=50, blank=True)
    measured_by = models.CharField(max_length=255, blank=True)
    remarks = models.TextField(blank=True)
    blockers = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-measurement_date", "-created_at"]
        indexes = [models.Index(fields=["organization", "project", "measurement_date"], name="pm_org_proj_date_idx")]

    @property
    def variance(self):
        return self.actual_progress - self.planned_progress

    @property
    def spi(self):
        if self.planned_value and self.planned_value > 0:
            return round(float(self.earned_value) / float(self.planned_value), 2)
        return None

    @property
    def cpi(self):
        if self.actual_cost and self.actual_cost > 0:
            return round(float(self.earned_value) / float(self.actual_cost), 2)
        return None

    def __str__(self):
        label = self.phase.name if self.phase else self.project.name
        return f"Progress {self.measurement_date} — {label} ({self.actual_progress}%)"


# ── Site Instructions ────────────────────────────────────────────────


class SiteInstruction(models.Model):
    class InstructionType(models.TextChoices):
        SAFETY = "safety", "Safety"
        QUALITY = "quality", "Quality"
        VARIATION = "variation", "Variation"
        URGENT_CORRECTIVE = "urgent_corrective", "Urgent Corrective Action"
        TECHNICAL = "technical", "Technical Clarification"
        DESIGN_CHANGE = "design_change", "Design Change"
        OTHER = "other", "Other"

    class SIStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        ISSUED = "issued", "Issued"
        ACKNOWLEDGED = "acknowledged", "Acknowledged"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        VERIFIED = "verified", "Verified"
        CLOSED = "closed", "Closed"
        VOID = "void", "Void"

    class Priority(models.TextChoices):
        URGENT = "urgent", "Urgent — Immediate Action"
        HIGH = "high", "High"
        NORMAL = "normal", "Normal"
        LOW = "low", "Low"

    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="org_site_instructions")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="site_instructions")
    si_number = models.CharField(max_length=100, blank=True, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    instruction_type = models.CharField(max_length=30, choices=InstructionType.choices, default=InstructionType.TECHNICAL)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.NORMAL)
    status = models.CharField(max_length=20, choices=SIStatus.choices, default=SIStatus.DRAFT)
    location = models.CharField(max_length=255, blank=True)
    cost_code = models.CharField(max_length=100, blank=True)
    has_financial_impact = models.BooleanField(default=False)
    estimated_cost_impact = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(Decimal("0.00"))])
    schedule_impact_days = models.PositiveIntegerField(default=0)
    issued_by = models.CharField(max_length=255, blank=True)
    issued_date = models.DateField(null=True, blank=True)
    compliance_deadline = models.DateField(null=True, blank=True)
    acknowledged_by = models.CharField(max_length=255, blank=True)
    acknowledged_date = models.DateTimeField(null=True, blank=True)
    contractor_timeline_impact = models.BooleanField(default=False)
    contractor_estimated_cost = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    contractor_remarks = models.TextField(blank=True)
    completed_date = models.DateField(null=True, blank=True)
    verified_by = models.CharField(max_length=255, blank=True)
    verified_date = models.DateField(null=True, blank=True)
    linked_variation = models.ForeignKey(ProjectVariationOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name="source_instructions")
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Site Instruction"
        indexes = [models.Index(fields=["organization", "status", "instruction_type"], name="si_org_sts_type_idx")]

    def save(self, *args, **kwargs):
        if not self.si_number:
            last = SiteInstruction.objects.filter(si_number__startswith="SI-").order_by("-si_number").values_list("si_number", flat=True).first()
            seq = int(last.split("-")[1]) + 1 if last else 1
            self.si_number = f"SI-{seq:05d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.si_number} — {self.title}"


# ── Testing & Commissioning ──────────────────────────────────────────


class CommissioningPlan(models.Model):
    class SystemType(models.TextChoices):
        ELECTRICAL = "electrical", "Electrical"
        MECHANICAL = "mechanical", "Mechanical / HVAC"
        PLUMBING = "plumbing", "Plumbing & Water"
        FIRE = "fire", "Fire Protection"
        ELEVATOR = "elevator", "Elevator / Lift"
        SECURITY = "security", "Security Systems"
        BMS = "bms", "Building Management System"
        SOLAR = "solar", "Solar / Renewable"
        STRUCTURAL = "structural", "Structural Load"
        OTHER = "other", "Other"

    class PlanStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        READY = "ready", "Ready for Testing"
        IN_PROGRESS = "in_progress", "In Progress"
        PASSED = "passed", "All Tests Passed"
        FAILED = "failed", "Has Failures"
        CERTIFIED = "certified", "Certified & Handed Over"

    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="org_commissioning_plans")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="commissioning_plans")
    plan_number = models.CharField(max_length=100, blank=True, unique=True)
    name = models.CharField(max_length=255)
    system_type = models.CharField(max_length=30, choices=SystemType.choices, default=SystemType.OTHER)
    status = models.CharField(max_length=20, choices=PlanStatus.choices, default=PlanStatus.DRAFT)
    description = models.TextField(blank=True)
    witness_required = models.BooleanField(default=False)
    witness_name = models.CharField(max_length=255, blank=True)
    witness_present = models.BooleanField(default=False)
    target_date = models.DateField(null=True, blank=True)
    completed_date = models.DateField(null=True, blank=True)

    # Sign-off / Certification
    certified_by = models.CharField(max_length=255, blank=True)
    certified_date = models.DateField(null=True, blank=True)
    approved_by = models.CharField(max_length=255, blank=True)
    approved_date = models.DateField(null=True, blank=True)
    client_signoff_name = models.CharField(max_length=255, blank=True)
    client_signoff_date = models.DateField(null=True, blank=True)
    certificate_number = models.CharField(max_length=100, blank=True, help_text="Generated on certification.")

    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["organization", "status"], name="tc_plan_org_sts_idx")]

    def save(self, *args, **kwargs):
        if not self.plan_number:
            last = CommissioningPlan.objects.filter(plan_number__startswith="TCP-").order_by("-plan_number").values_list("plan_number", flat=True).first()
            seq = int(last.split("-")[1]) + 1 if last else 1
            self.plan_number = f"TCP-{seq:05d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.plan_number} — {self.name}"


class TestRecord(models.Model):
    class TestResult(models.TextChoices):
        PENDING = "pending", "Pending"
        PASS = "pass", "Pass"
        FAIL = "fail", "Fail"
        RETEST = "retest", "Retest Required"
        NA = "na", "N/A"

    plan = models.ForeignKey(CommissioningPlan, on_delete=models.CASCADE, related_name="test_records")
    sort_order = models.PositiveIntegerField(default=0)
    test_description = models.CharField(max_length=255)
    reference_standard = models.CharField(max_length=255, blank=True)
    required_value = models.CharField(max_length=255, blank=True)
    actual_value = models.CharField(max_length=255, blank=True)
    result = models.CharField(max_length=20, choices=TestResult.choices, default=TestResult.PENDING)
    tested_by = models.CharField(max_length=255, blank=True)
    tested_date = models.DateField(null=True, blank=True)
    fault_comment = models.TextField(blank=True)
    retest_notes = models.TextField(blank=True)
    retest_date = models.DateField(null=True, blank=True)
    retest_result = models.CharField(max_length=20, choices=TestResult.choices, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.plan.plan_number} — {self.test_description}"


class CommissioningPunchItem(models.Model):
    class PunchPriority(models.TextChoices):
        CRITICAL = "critical", "Critical — Blocks Handover"
        MAJOR = "major", "Major"
        MINOR = "minor", "Minor"

    class PunchStatus(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In Progress"
        RECTIFIED = "rectified", "Rectified"
        VERIFIED = "verified", "Verified"
        CLOSED = "closed", "Closed"

    plan = models.ForeignKey(CommissioningPlan, on_delete=models.CASCADE, related_name="punch_items")
    test_record = models.ForeignKey(TestRecord, on_delete=models.SET_NULL, null=True, blank=True, related_name="punch_items")
    item_number = models.CharField(max_length=100, blank=True)
    description = models.TextField()
    priority = models.CharField(max_length=20, choices=PunchPriority.choices, default=PunchPriority.MAJOR)
    status = models.CharField(max_length=20, choices=PunchStatus.choices, default=PunchStatus.OPEN)
    location = models.CharField(max_length=255, blank=True)
    assigned_to = models.CharField(max_length=255, blank=True)
    corrective_action = models.TextField(blank=True)
    rectified_date = models.DateField(null=True, blank=True)
    verified_by = models.CharField(max_length=255, blank=True)
    verified_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.item_number:
            last = CommissioningPunchItem.objects.filter(plan=self.plan, item_number__startswith="PL-").order_by("-item_number").values_list("item_number", flat=True).first()
            seq = int(last.split("-")[1]) + 1 if last else 1
            self.item_number = f"PL-{seq:03d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.item_number} — {self.description[:50]}"


# ── Cost Control ─────────────────────────────────────────────────────


class CostCodeBudget(models.Model):
    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="org_cost_code_budgets")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="cost_code_budgets")
    cost_code = models.CharField(max_length=50)
    description = models.CharField(max_length=255)
    original_budget = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    approved_changes = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    committed = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    actual_cost = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    forecast_to_complete = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    notes = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "cost_code"]
        unique_together = [("project", "cost_code")]

    @property
    def revised_budget(self):
        return self.original_budget + self.approved_changes

    @property
    def forecast_at_completion(self):
        return self.actual_cost + self.forecast_to_complete

    @property
    def variance(self):
        return self.revised_budget - self.forecast_at_completion

    def __str__(self):
        return f"{self.cost_code} — {self.description}"


class CostTransaction(models.Model):
    class TransactionType(models.TextChoices):
        COMMITMENT = "commitment", "Commitment (PO/Contract)"
        INVOICE = "invoice", "Invoice"
        PAYMENT = "payment", "Payment"
        VARIATION = "variation", "Variation / Change Order"
        TRANSFER = "transfer", "Budget Transfer"
        CONTINGENCY = "contingency", "Contingency Drawdown"

    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="org_cost_transactions")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="cost_transactions")
    cost_code_budget = models.ForeignKey(CostCodeBudget, on_delete=models.CASCADE, related_name="transactions")
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)
    reference = models.CharField(max_length=255, blank=True)
    description = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    transaction_date = models.DateField()
    vendor = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-transaction_date", "-created_at"]

    def __str__(self):
        return f"{self.get_transaction_type_display()} — {self.reference or self.description} ({self.amount})"


class ProjectContingency(models.Model):
    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="org_project_contingencies")
    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name="contingency")
    total_contingency = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    drawn_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    notes = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Project Contingencies"

    @property
    def remaining(self):
        return self.total_contingency - self.drawn_amount

    @property
    def drawn_percent(self):
        if self.total_contingency and self.total_contingency > 0:
            return round(float(self.drawn_amount) / float(self.total_contingency) * 100, 1)
        return 0

    def __str__(self):
        return f"Contingency — {self.project.name}"


# ── Construction Reports ─────────────────────────────────────────────


class ConstructionReport(models.Model):
    class ReportCategory(models.TextChoices):
        FINANCIAL = "financial", "Financial"
        PROGRESS = "progress", "Progress"
        HSE = "hse", "HSE & Compliance"
        CONTRACTUAL = "contractual", "Contractual"
        EXECUTIVE = "executive", "Executive Summary"
        CUSTOM = "custom", "Custom"

    class ReportStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        IN_REVIEW = "in_review", "In Review"
        APPROVED = "approved", "Approved"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    class ReportFrequency(models.TextChoices):
        WEEKLY = "weekly", "Weekly"
        FORTNIGHTLY = "fortnightly", "Fortnightly"
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        AD_HOC = "ad_hoc", "Ad Hoc"

    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="org_construction_reports")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="construction_reports")
    report_number = models.CharField(max_length=100, blank=True, unique=True)
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=20, choices=ReportCategory.choices, default=ReportCategory.PROGRESS)
    status = models.CharField(max_length=20, choices=ReportStatus.choices, default=ReportStatus.DRAFT)
    frequency = models.CharField(max_length=20, choices=ReportFrequency.choices, default=ReportFrequency.AD_HOC)
    reporting_period_start = models.DateField(null=True, blank=True)
    reporting_period_end = models.DateField(null=True, blank=True)
    executive_summary = models.TextField(blank=True)
    key_highlights = models.TextField(blank=True)
    key_risks = models.TextField(blank=True)
    recommendations = models.TextField(blank=True)
    financial_snapshot = models.JSONField(default=dict, blank=True)
    progress_snapshot = models.JSONField(default=dict, blank=True)
    hse_snapshot = models.JSONField(default=dict, blank=True)
    recipients = models.TextField(blank=True)
    auto_send = models.BooleanField(default=False)
    published_date = models.DateTimeField(null=True, blank=True)
    prepared_by = models.CharField(max_length=255, blank=True)
    reviewed_by = models.CharField(max_length=255, blank=True)
    approved_by = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["organization", "category", "status"], name="cr_org_cat_sts_idx")]

    def save(self, *args, **kwargs):
        if not self.report_number:
            prefix_map = {"financial": "MCR", "progress": "WPR", "hse": "HSR", "contractual": "CTR", "executive": "EXR", "custom": "RPT"}
            prefix = prefix_map.get(self.category, "RPT")
            last = ConstructionReport.objects.filter(report_number__startswith=f"{prefix}-").order_by("-report_number").values_list("report_number", flat=True).first()
            seq = int(last.split("-")[1]) + 1 if last else 1
            self.report_number = f"{prefix}-{seq:05d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.report_number} — {self.title}"


# ── Project Pipeline ─────────────────────────────────────────────────


class PipelineOpportunity(models.Model):
    """Development opportunity tracked through the investment pipeline."""

    class Stage(models.TextChoices):
        OPPORTUNITY = "opportunity", "Opportunity Identified"
        FEASIBILITY = "feasibility", "Feasibility Study"
        FINANCIAL_MODEL = "financial_model", "Financial Modeling"
        DUE_DILIGENCE = "due_diligence", "Due Diligence"
        IC_REVIEW = "ic_review", "IC Review"
        APPROVED = "approved", "Approved"
        ON_HOLD = "on_hold", "On Hold"
        REJECTED = "rejected", "Rejected"

    class DevType(models.TextChoices):
        RESIDENTIAL = "residential", "Residential"
        COMMERCIAL = "commercial", "Commercial"
        MIXED_USE = "mixed_use", "Mixed-Use"
        INDUSTRIAL = "industrial", "Industrial"
        HOSPITALITY = "hospitality", "Hospitality"
        RETAIL = "retail", "Retail"
        INFRASTRUCTURE = "infrastructure", "Infrastructure"
        OTHER = "other", "Other"

    class ICDecision(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        DEFERRED = "deferred", "Deferred"
        REJECTED = "rejected", "Rejected"

    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="org_pipeline_opportunities")
    # Links to a formal project once approved
    project = models.OneToOneField(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name="pipeline_opportunity")

    pipeline_ref = models.CharField(max_length=100, blank=True, unique=True)
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True)
    gps_coordinates = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)

    stage = models.CharField(max_length=20, choices=Stage.choices, default=Stage.OPPORTUNITY)
    stage_order = models.PositiveIntegerField(default=0, help_text="Sort position within the stage column.")
    development_type = models.CharField(max_length=20, choices=DevType.choices, default=DevType.RESIDENTIAL)

    # Land
    land_size_sqm = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    land_cost = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    land_status = models.CharField(max_length=255, blank=True, help_text="e.g. MOU Signed, Under Survey, Title Verified")

    # Financials
    estimated_gdv = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"), help_text="Gross Development Value")
    estimated_cost = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"), help_text="Total all-in development cost")
    expected_irr = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"), help_text="Expected IRR %")
    hurdle_rate = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("25.00"), help_text="Minimum acceptable IRR %")
    expected_margin_pct = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    number_of_units = models.PositiveIntegerField(default=0)

    # Feasibility
    market_analysis = models.TextField(blank=True, help_text="Absorption rates, comps, demographics.")
    feasibility_notes = models.TextField(blank=True)

    # IC Review
    ic_decision = models.CharField(max_length=20, choices=ICDecision.choices, default=ICDecision.PENDING)
    ic_review_date = models.DateField(null=True, blank=True)
    ic_conditions = models.TextField(blank=True, help_text="Conditions for approval.")
    ic_reviewers = models.TextField(blank=True, help_text="Comma-separated reviewer names.")

    # Dates
    identified_date = models.DateField(null=True, blank=True)
    target_start_date = models.DateField(null=True, blank=True)
    target_completion_date = models.DateField(null=True, blank=True)

    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["stage", "stage_order", "-created_at"]
        verbose_name_plural = "Pipeline Opportunities"
        indexes = [models.Index(fields=["organization", "stage"], name="pipe_org_stage_idx")]

    def save(self, *args, **kwargs):
        if not self.pipeline_ref:
            last = PipelineOpportunity.objects.filter(pipeline_ref__startswith="PIP-").order_by("-pipeline_ref").values_list("pipeline_ref", flat=True).first()
            seq = int(last.split("-")[1]) + 1 if last else 1
            self.pipeline_ref = f"PIP-{seq:05d}"
        # Auto-compute margin
        if self.estimated_gdv and self.estimated_gdv > 0:
            self.expected_margin_pct = round(
                (float(self.estimated_gdv) - float(self.estimated_cost)) / float(self.estimated_gdv) * 100, 2
            )
        super().save(*args, **kwargs)

    @property
    def meets_hurdle(self):
        return self.expected_irr >= self.hurdle_rate

    @property
    def profit(self):
        return self.estimated_gdv - self.estimated_cost

    def __str__(self):
        return f"{self.pipeline_ref} — {self.name}"


class ProjectTeamMember(models.Model):
    """Team member assigned to a project with a specific role."""

    class Role(models.TextChoices):
        PROJECT_MANAGER = "project_manager", "Project Manager"
        LEAD_ARCHITECT = "lead_architect", "Lead Architect"
        STRUCTURAL_ENGINEER = "structural_engineer", "Structural Engineer"
        MEP_CONSULTANT = "mep_consultant", "MEP Consultant"
        QUANTITY_SURVEYOR = "quantity_surveyor", "Quantity Surveyor"
        SITE_ENGINEER = "site_engineer", "Site Engineer"
        SAFETY_OFFICER = "safety_officer", "Safety Officer"
        PROJECT_DIRECTOR = "project_director", "Project Director"
        LEGAL_COUNSEL = "legal_counsel", "Legal Counsel"
        FINANCE_CONTROLLER = "finance_controller", "Finance Controller"
        OTHER = "other", "Other"

    class AccessLevel(models.TextChoices):
        READ_ONLY = "read_only", "Read Only"
        CONTRIBUTOR = "contributor", "Contributor"
        FINANCIAL_EDIT = "financial_edit", "Financial Edit"
        FULL_ACCESS = "full_access", "Full Access"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="team_members")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=30, choices=Role.choices, default=Role.OTHER)
    access_level = models.CharField(max_length=20, choices=AccessLevel.choices, default=AccessLevel.CONTRIBUTOR)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    company = models.CharField(max_length=255, blank=True, help_text="External firm if consultant.")
    is_active = models.BooleanField(default=True)
    assigned_date = models.DateField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["role", "name"]

    def __str__(self):
        return f"{self.name} — {self.get_role_display()} ({self.project.name})"


class ProjectSetupConfig(models.Model):
    """Setup wizard state and configuration for a project."""

    class SetupStep(models.TextChoices):
        BASIC_INFO = "basic_info", "Basic Info"
        TEAM_ALLOCATION = "team_allocation", "Team Allocation"
        PHASE_DEFINITION = "phase_definition", "Phase Definition"
        BOQ_BASELINE = "boq_baseline", "BoQ Baseline"
        COMPLETED = "completed", "Setup Complete"

    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name="setup_config")
    pipeline_source = models.ForeignKey(PipelineOpportunity, on_delete=models.SET_NULL, null=True, blank=True, related_name="setup_configs")
    current_step = models.CharField(max_length=20, choices=SetupStep.choices, default=SetupStep.BASIC_INFO)
    is_complete = models.BooleanField(default=False)

    # Land parcel
    survey_plan_ref = models.CharField(max_length=255, blank=True)
    certificate_of_occupancy = models.CharField(max_length=255, blank=True)

    # Phase config
    planned_phases = models.PositiveIntegerField(default=3)

    # BoQ baseline
    boq_initialized = models.BooleanField(default=False)
    template_applied = models.BooleanField(default=False)
    template_name = models.CharField(max_length=255, blank=True)

    notes = models.TextField(blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Setup — {self.project.name} ({self.get_current_step_display()})"


# ── Feasibility & Viability ──────────────────────────────────────────


class FeasibilityStudy(models.Model):
    """Financial feasibility analysis for a development project."""

    class StudyStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        IN_REVIEW = "in_review", "In Review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        SUPERSEDED = "superseded", "Superseded"

    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="org_feasibility_studies")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="feasibility_studies")
    pipeline_source = models.ForeignKey(PipelineOpportunity, on_delete=models.SET_NULL, null=True, blank=True, related_name="feasibility_studies")

    study_ref = models.CharField(max_length=100, blank=True, unique=True)
    version = models.CharField(max_length=20, default="1.0")
    status = models.CharField(max_length=20, choices=StudyStatus.choices, default=StudyStatus.DRAFT)

    # ── Revenue (GDV) ────────────────────────────────────────────────
    total_sales_value = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    other_income = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"), help_text="Parking, facility mgmt, storage.")
    number_of_units = models.PositiveIntegerField(default=0)
    avg_price_per_unit = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    avg_price_per_sqm = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    # ── Cost Stack ───────────────────────────────────────────────────
    land_cost = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    land_legal_fees = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    construction_cost = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    professional_fees = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    professional_fees_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("8.00"), help_text="% of construction cost")
    marketing_sales_cost = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    sales_commission_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("5.00"))
    finance_cost = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    contingency = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    contingency_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("5.00"))

    # ── KPIs ─────────────────────────────────────────────────────────
    target_irr = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("25.00"))
    expected_irr = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    hurdle_rate = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("25.00"))
    breakeven_units_pct = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"), help_text="% of units to break even")
    sales_velocity = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"), help_text="Units per month")
    project_duration_months = models.PositiveIntegerField(default=36)

    # ── Risk Assessment ──────────────────────────────────────────────
    market_risk = models.CharField(max_length=10, choices=[("low", "Low"), ("medium", "Medium"), ("high", "High")], default="medium")
    finance_risk = models.CharField(max_length=10, choices=[("low", "Low"), ("medium", "Medium"), ("high", "High")], default="medium")
    construction_risk = models.CharField(max_length=10, choices=[("low", "Low"), ("medium", "Medium"), ("high", "High")], default="medium")

    # ── Market Study ─────────────────────────────────────────────────
    demand_analysis = models.TextField(blank=True)
    competitor_projects = models.JSONField(default=list, blank=True, help_text="List of {name, units, price_per_unit, price_per_sqm, status}")
    pricing_benchmarks = models.TextField(blank=True)

    # ── Sensitivity Matrix ───────────────────────────────────────────
    sensitivity_matrix = models.JSONField(default=dict, blank=True, help_text="Precomputed {price_change: {cost_change: irr}}")

    notes = models.TextField(blank=True)
    prepared_by = models.CharField(max_length=255, blank=True)
    reviewed_by = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Feasibility Studies"
        indexes = [models.Index(fields=["organization", "project", "status"], name="feas_org_proj_sts_idx")]

    def save(self, *args, **kwargs):
        if not self.study_ref:
            last = FeasibilityStudy.objects.filter(study_ref__startswith="FS-").order_by("-study_ref").values_list("study_ref", flat=True).first()
            seq = int(last.split("-")[1]) + 1 if last else 1
            self.study_ref = f"FS-{seq:05d}"
        super().save(*args, **kwargs)

    @property
    def gdv(self):
        return self.total_sales_value + self.other_income

    @property
    def total_development_cost(self):
        return (self.land_cost + self.land_legal_fees + self.construction_cost +
                self.professional_fees + self.marketing_sales_cost +
                self.finance_cost + self.contingency)

    @property
    def profit(self):
        return self.gdv - self.total_development_cost

    @property
    def profit_on_cost(self):
        tdc = self.total_development_cost
        if tdc and tdc > 0:
            return round(float(self.profit) / float(tdc) * 100, 2)
        return 0

    @property
    def margin_pct(self):
        g = self.gdv
        if g and g > 0:
            return round(float(self.profit) / float(g) * 100, 2)
        return 0

    @property
    def meets_hurdle(self):
        return self.expected_irr >= self.hurdle_rate

    def __str__(self):
        return f"{self.study_ref} v{self.version} — {self.project.name}"


# ── Land Acquisition ─────────────────────────────────────────────────


class LandAcquisition(models.Model):
    """Tracks land parcels, title status, due diligence, and payment milestones."""

    class TitleType(models.TextChoices):
        C_OF_O = "c_of_o", "Certificate of Occupancy (C of O)"
        GOVERNORS_CONSENT = "governors_consent", "Governor's Consent"
        EXCISION = "excision", "Excision"
        DEED_OF_ASSIGNMENT = "deed_of_assignment", "Deed of Assignment"
        RIGHT_OF_OCCUPANCY = "right_of_occupancy", "Right of Occupancy"
        FREEHOLD = "freehold", "Freehold"
        LEASEHOLD = "leasehold", "Leasehold"
        PENDING = "pending", "Pending / Not Yet Determined"

    class VerificationStatus(models.TextChoices):
        NOT_STARTED = "not_started", "Not Started"
        IN_PROGRESS = "in_progress", "Due Diligence In Progress"
        ENCUMBRANCE_FOUND = "encumbrance_found", "Encumbrance Found"
        VERIFIED = "verified", "Legally Verified"
        REGISTERED = "registered", "Title Registered"

    class AcquisitionStatus(models.TextChoices):
        PROSPECTING = "prospecting", "Prospecting"
        NEGOTIATION = "negotiation", "Negotiation"
        MOU_SIGNED = "mou_signed", "MOU Signed"
        DUE_DILIGENCE = "due_diligence", "Due Diligence"
        CONTRACT_SIGNED = "contract_signed", "Contract Signed"
        PAYMENT_IN_PROGRESS = "payment_in_progress", "Payment In Progress"
        COMPLETED = "completed", "Acquisition Complete"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="org_land_acquisitions")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="land_acquisitions")

    parcel_id = models.CharField(max_length=100, blank=True, unique=True)
    location = models.CharField(max_length=500, blank=True)
    gps_latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    gps_longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    land_size_sqm = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    description = models.TextField(blank=True)

    # Title
    title_type = models.CharField(max_length=30, choices=TitleType.choices, default=TitleType.PENDING)
    verification_status = models.CharField(max_length=30, choices=VerificationStatus.choices, default=VerificationStatus.NOT_STARTED)
    acquisition_status = models.CharField(max_length=30, choices=AcquisitionStatus.choices, default=AcquisitionStatus.PROSPECTING)
    survey_plan_ref = models.CharField(max_length=255, blank=True)
    title_document_ref = models.CharField(max_length=255, blank=True)

    # Financial
    purchase_price = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    agency_fees = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    legal_fees = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    stamp_duty = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    registration_fees = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    total_paid = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))

    # Legal verification
    land_search_date = models.DateField(null=True, blank=True)
    land_search_registry = models.CharField(max_length=255, blank=True, help_text="e.g. Alausa, AGIS")
    encumbrance_check = models.BooleanField(default=False)
    encumbrance_notes = models.TextField(blank=True)
    govt_approval_status = models.CharField(max_length=255, blank=True)
    govt_approval_tracking = models.CharField(max_length=255, blank=True, help_text="LUCPS/NIBS tracking number")
    govt_approval_days_elapsed = models.PositiveIntegerField(default=0)

    # Escrow
    escrow_holder = models.CharField(max_length=255, blank=True)
    escrow_secured = models.BooleanField(default=False)

    # Seller
    seller_name = models.CharField(max_length=255, blank=True)
    seller_contact = models.CharField(max_length=255, blank=True)

    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["organization", "acquisition_status"], name="land_org_acq_sts_idx")]

    def save(self, *args, **kwargs):
        if not self.parcel_id:
            last = LandAcquisition.objects.filter(parcel_id__startswith="L-").order_by("-parcel_id").values_list("parcel_id", flat=True).first()
            seq = int(last.split("-")[1]) + 1 if last else 1
            self.parcel_id = f"L-{seq:05d}"
        super().save(*args, **kwargs)

    @property
    def total_acquisition_cost(self):
        return self.purchase_price + self.agency_fees + self.legal_fees + self.stamp_duty + self.registration_fees

    @property
    def balance_remaining(self):
        return self.total_acquisition_cost - self.total_paid

    def __str__(self):
        return f"{self.parcel_id} — {self.location or self.project.name}"


class LandPaymentMilestone(models.Model):
    """Payment tranche within a land acquisition."""

    class MilestoneStatus(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        INVOICED = "invoiced", "Invoiced"
        PAID = "paid", "Paid"
        OVERDUE = "overdue", "Overdue"

    land_acquisition = models.ForeignKey(LandAcquisition, on_delete=models.CASCADE, related_name="payment_milestones")
    title = models.CharField(max_length=255, help_text="e.g. Initial Deposit, 2nd Tranche, Final Balance")
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    due_date = models.DateField(null=True, blank=True)
    paid_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=MilestoneStatus.choices, default=MilestoneStatus.SCHEDULED)
    payment_reference = models.CharField(max_length=255, blank=True)
    recipient = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "due_date"]

    def __str__(self):
        return f"{self.title} — {self.amount}"


# ── Development Budget ───────────────────────────────────────────────


class DevelopmentBudget(models.Model):
    """High-level development budget baseline for a project."""

    class BudgetStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        BASELINE = "baseline", "Baseline Locked"
        REVISED = "revised", "Revised"
        APPROVED = "approved", "Approved"

    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="org_dev_budgets")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="development_budgets")
    version = models.CharField(max_length=20, default="1.0")
    status = models.CharField(max_length=20, choices=BudgetStatus.choices, default=BudgetStatus.DRAFT)
    is_baseline = models.BooleanField(default=False)

    # Funding mix
    equity_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    debt_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))

    # Land
    total_land_area_sqm = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    contingency_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("5.00"))

    notes = models.TextField(blank=True)
    prepared_by = models.CharField(max_length=255, blank=True)
    approved_by = models.CharField(max_length=255, blank=True)
    locked_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def total_development_cost(self):
        return sum(c.allocated_amount for c in self.categories.all())

    @property
    def cost_per_sqm(self):
        tdc = self.total_development_cost
        if self.total_land_area_sqm and self.total_land_area_sqm > 0 and tdc > 0:
            return round(float(tdc) / float(self.total_land_area_sqm), 2)
        return 0

    def __str__(self):
        return f"Budget v{self.version} — {self.project.name}"


class DevelopmentBudgetCategory(models.Model):
    """Budget line category within a development budget."""

    class CostType(models.TextChoices):
        HARD = "hard", "Hard Cost"
        SOFT = "soft", "Soft Cost"

    class CategoryStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        ESTIMATED = "estimated", "Estimated"
        PLANNED = "planned", "Planned"
        CONTRACTED = "contracted", "Contracted"
        LOCKED = "locked", "Locked"

    budget = models.ForeignKey(DevelopmentBudget, on_delete=models.CASCADE, related_name="categories")
    name = models.CharField(max_length=255)
    cost_type = models.CharField(max_length=10, choices=CostType.choices, default=CostType.HARD)
    allocated_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    actual_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=20, choices=CategoryStatus.choices, default=CategoryStatus.DRAFT)
    sub_items = models.JSONField(default=list, blank=True, help_text="[{name, amount}]")
    sort_order = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "id"]

    @property
    def variance(self):
        return self.allocated_amount - self.actual_amount

    def __str__(self):
        return f"{self.name} — {self.allocated_amount}"


# ── Project Financing ────────────────────────────────────────────────


class FinancingSource(models.Model):
    """A capital provider for a project (bank loan, equity, JV partner, etc.)."""

    class SourceType(models.TextChoices):
        BANK_LOAN = "bank_loan", "Bank Loan"
        MEZZANINE = "mezzanine", "Mezzanine Finance"
        EQUITY = "equity", "Equity"
        JOINT_VENTURE = "joint_venture", "Joint Venture"
        PRIVATE_PLACEMENT = "private_placement", "Private Placement"
        GRANT = "grant", "Grant / Subsidy"
        OTHER = "other", "Other"

    class RateType(models.TextChoices):
        FIXED = "fixed", "Fixed"
        VARIABLE = "variable", "Variable"

    class SourceStatus(models.TextChoices):
        PENDING = "pending", "Pending Approval"
        ACTIVE = "active", "Active"
        FULLY_DRAWN = "fully_drawn", "Fully Drawn"
        REPAID = "repaid", "Repaid"
        EXPIRED = "expired", "Expired"

    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="org_financing_sources")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="financing_sources")

    reference = models.CharField(max_length=100, blank=True, unique=True, help_text="Auto-generated as FIN-##### when blank.")
    name = models.CharField(max_length=255, help_text="e.g. GTBank Construction Facility")
    source_type = models.CharField(max_length=30, choices=SourceType.choices, default=SourceType.BANK_LOAN)
    status = models.CharField(max_length=20, choices=SourceStatus.choices, default=SourceStatus.PENDING)

    # Financial terms
    committed_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    drawn_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    interest_rate = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True, help_text="Annual rate %")
    rate_type = models.CharField(max_length=10, choices=RateType.choices, default=RateType.FIXED)
    rate_benchmark = models.CharField(max_length=50, blank=True, help_text="e.g. SOFR, NIBOR, MPR")
    arrangement_fee_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    grace_period_months = models.PositiveIntegerField(default=0)
    tenor_months = models.PositiveIntegerField(default=0, help_text="Total facility duration in months")
    repayment_frequency = models.CharField(
        max_length=20,
        choices=[("monthly", "Monthly"), ("quarterly", "Quarterly"), ("semi_annual", "Semi-Annual"), ("annual", "Annual"), ("bullet", "Bullet")],
        default="quarterly",
    )

    # Dates
    agreement_date = models.DateField(null=True, blank=True)
    first_drawdown_date = models.DateField(null=True, blank=True)
    maturity_date = models.DateField(null=True, blank=True)
    next_repayment_date = models.DateField(null=True, blank=True)

    # Contact
    institution = models.CharField(max_length=255, blank=True)
    contact_person = models.CharField(max_length=255, blank=True)
    contact_email = models.EmailField(blank=True)

    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"], name="finsrc_org_status_idx"),
        ]

    @property
    def available_amount(self):
        return self.committed_amount - self.drawn_amount

    def save(self, *args, **kwargs):
        if not self.reference:
            last = (
                FinancingSource.objects.filter(reference__startswith="FIN-")
                .order_by("-reference")
                .values_list("reference", flat=True)
                .first()
            )
            seq = 1
            if last:
                try:
                    seq = int(last.split("-")[1]) + 1
                except (IndexError, ValueError):
                    pass
            self.reference = f"FIN-{seq:05d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference} — {self.name}"


class FinancingDrawdown(models.Model):
    """Record of a drawdown request/disbursement from a financing source."""

    class DrawdownStatus(models.TextChoices):
        REQUESTED = "requested", "Requested"
        APPROVED = "approved", "Approved"
        DISBURSED = "disbursed", "Disbursed"
        REJECTED = "rejected", "Rejected"

    source = models.ForeignKey(FinancingSource, on_delete=models.CASCADE, related_name="drawdowns")
    reference = models.CharField(max_length=100, blank=True)
    request_date = models.DateField()
    amount_requested = models.DecimalField(max_digits=15, decimal_places=2)
    amount_received = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, help_text="Net after bank fees")
    status = models.CharField(max_length=20, choices=DrawdownStatus.choices, default=DrawdownStatus.REQUESTED)
    disbursement_date = models.DateField(null=True, blank=True)
    milestone_reference = models.CharField(max_length=255, blank=True, help_text="Linked milestone or certificate of work")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-request_date"]

    def __str__(self):
        return f"Drawdown {self.reference} — {self.amount_requested}"


class FinancingRepayment(models.Model):
    """Scheduled or actual repayment entry for a financing source."""

    class RepaymentStatus(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        PAID = "paid", "Paid"
        OVERDUE = "overdue", "Overdue"
        WAIVED = "waived", "Waived"

    source = models.ForeignKey(FinancingSource, on_delete=models.CASCADE, related_name="repayments")
    payment_date = models.DateField()
    principal_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    interest_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    ending_balance = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=20, choices=RepaymentStatus.choices, default=RepaymentStatus.SCHEDULED)
    actual_payment_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["payment_date"]

    @property
    def total_payment(self):
        return self.principal_amount + self.interest_amount

    def __str__(self):
        return f"Repayment {self.payment_date} — {self.total_payment}"


class FinancingCovenant(models.Model):
    """Financial or operational covenant tied to a financing source."""

    class CovenantStatus(models.TextChoices):
        COMPLIANT = "compliant", "Compliant"
        AT_RISK = "at_risk", "At Risk"
        BREACHED = "breached", "Breached"
        NOT_TESTED = "not_tested", "Not Yet Tested"

    source = models.ForeignKey(FinancingSource, on_delete=models.CASCADE, related_name="covenants")
    name = models.CharField(max_length=255, help_text="e.g. Debt-to-Equity Ratio")
    description = models.TextField(blank=True)
    threshold = models.CharField(max_length=100, blank=True, help_text="e.g. ≤ 2.5x or ≥ 1.2x DSCR")
    current_value = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=CovenantStatus.choices, default=CovenantStatus.NOT_TESTED)
    last_tested = models.DateField(null=True, blank=True)
    next_test_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} — {self.status}"


# ── Consultants & Stakeholders ───────────────────────────────────────


class ProjectConsultant(models.Model):
    """External professional/firm engaged on a project."""

    class Discipline(models.TextChoices):
        ARCHITECTURAL = "architectural", "Architectural"
        STRUCTURAL = "structural", "Structural"
        MEP = "mep", "MEP (Mechanical, Electrical, Plumbing)"
        QUANTITY_SURVEYING = "quantity_surveying", "Quantity Surveying"
        LEGAL = "legal", "Legal"
        GEOTECHNICAL = "geotechnical", "Geotechnical"
        ENVIRONMENTAL = "environmental", "Environmental"
        TOWN_PLANNING = "town_planning", "Town Planning"
        LAND_SURVEYING = "land_surveying", "Land Surveying"
        PROJECT_MANAGEMENT = "project_management", "Project Management"
        INTERIOR_DESIGN = "interior_design", "Interior Design"
        LANDSCAPE = "landscape", "Landscape"
        OTHER = "other", "Other"

    class EngagementStatus(models.TextChoices):
        ONBOARDING = "onboarding", "On-Boarding"
        ACTIVE = "active", "Active"
        ON_HOLD = "on_hold", "On Hold"
        COMPLETED = "completed", "Contract Completed"
        TERMINATED = "terminated", "Terminated"

    class ComplianceStatus(models.TextChoices):
        GREEN = "green", "Green — On Track"
        YELLOW = "yellow", "Yellow — Minor Delays"
        RED = "red", "Red — Critical Issues"

    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="org_project_consultants")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="consultants")

    # Firm / Individual info
    firm_name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=255, blank=True)
    contact_role = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    whatsapp = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)

    discipline = models.CharField(max_length=30, choices=Discipline.choices, default=Discipline.ARCHITECTURAL)
    status = models.CharField(max_length=20, choices=EngagementStatus.choices, default=EngagementStatus.ONBOARDING)

    # Contract & Scope
    scope_of_work = models.TextField(blank=True)
    contract_value = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    amount_paid = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    contract_start_date = models.DateField(null=True, blank=True)
    contract_end_date = models.DateField(null=True, blank=True)

    # Compliance
    compliance_status = models.CharField(max_length=10, choices=ComplianceStatus.choices, default=ComplianceStatus.GREEN)
    insurance_policy = models.CharField(max_length=255, blank=True)
    insurance_expiry = models.DateField(null=True, blank=True)
    license_number = models.CharField(max_length=100, blank=True)
    license_expiry = models.DateField(null=True, blank=True)

    # Hierarchy
    reports_to = models.CharField(max_length=255, blank=True, help_text="e.g. Project Manager")
    collaborates_with = models.JSONField(default=list, blank=True, help_text="[discipline strings]")

    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["discipline", "firm_name"]
        indexes = [
            models.Index(fields=["organization", "status"], name="cons_org_status_idx"),
        ]

    @property
    def payment_progress(self):
        if self.contract_value and self.contract_value > 0:
            return round(float(self.amount_paid) / float(self.contract_value) * 100, 1)
        return 0

    @property
    def amount_remaining(self):
        return self.contract_value - self.amount_paid

    def __str__(self):
        return f"{self.firm_name} — {self.get_discipline_display()}"


class ConsultantPaymentMilestone(models.Model):
    """Payment milestone within a consultant engagement."""

    class MilestoneStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        INVOICED = "invoiced", "Invoiced"
        PAID = "paid", "Paid"
        CANCELLED = "cancelled", "Cancelled"

    consultant = models.ForeignKey(ProjectConsultant, on_delete=models.CASCADE, related_name="payment_milestones")
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    trigger_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=MilestoneStatus.choices, default=MilestoneStatus.PENDING)
    paid_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "trigger_date"]

    def __str__(self):
        return f"{self.description} — {self.amount}"


class ConsultantDeliverable(models.Model):
    """Specific output required from a consultant."""

    class DeliverableStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under Review"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"

    class DeliverableFormat(models.TextChoices):
        DWG = "dwg", "DWG"
        PDF = "pdf", "PDF"
        DOCX = "docx", "DOCX"
        XLSX = "xlsx", "XLSX"
        BIM = "bim", "BIM / Revit"
        OTHER = "other", "Other"

    consultant = models.ForeignKey(ProjectConsultant, on_delete=models.CASCADE, related_name="deliverables")
    name = models.CharField(max_length=255)
    due_date = models.DateField(null=True, blank=True)
    format = models.CharField(max_length=10, choices=DeliverableFormat.choices, default=DeliverableFormat.PDF)
    status = models.CharField(max_length=20, choices=DeliverableStatus.choices, default=DeliverableStatus.PENDING)
    submitted_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "due_date"]

    def __str__(self):
        return f"{self.name} ({self.get_format_display()})"


class ConsultantCommunicationLog(models.Model):
    """Record of meetings, site visits, or technical queries with a consultant."""

    class EntryType(models.TextChoices):
        MEETING = "meeting", "Meeting"
        SITE_VISIT = "site_visit", "Site Visit"
        DESIGN_REVIEW = "design_review", "Design Review"
        RFI = "rfi", "Technical Query / RFI"
        PHONE_CALL = "phone_call", "Phone Call"
        EMAIL = "email", "Email"
        OTHER = "other", "Other"

    consultant = models.ForeignKey(ProjectConsultant, on_delete=models.CASCADE, related_name="communication_logs")
    entry_type = models.CharField(max_length=20, choices=EntryType.choices, default=EntryType.MEETING)
    date = models.DateField()
    subject = models.CharField(max_length=255)
    summary = models.TextField(blank=True)
    attendees = models.TextField(blank=True)
    action_items = models.TextField(blank=True)
    logged_by = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.get_entry_type_display()} — {self.subject}"


# ── Approvals & Permits ──────────────────────────────────────────────


class ProjectPermit(models.Model):
    """Regulatory permit or approval required for a project."""

    class PermitType(models.TextChoices):
        ENVIRONMENTAL = "environmental", "Environmental Approval (EIA)"
        PLANNING = "planning", "Planning Permission"
        BUILDING = "building", "Building Permit"
        FIRE_SAFETY = "fire_safety", "Fire Safety Approval"
        UTILITY_WATER = "utility_water", "Water Connection"
        UTILITY_POWER = "utility_power", "Power Connection"
        UTILITY_SEWER = "utility_sewer", "Sewer / Drainage"
        ROAD_CLOSURE = "road_closure", "Road Closure / Traffic"
        HERITAGE = "heritage", "Heritage / Conservation"
        AVIATION = "aviation", "Aviation Height Clearance"
        OCCUPANCY = "occupancy", "Certificate of Occupancy"
        OTHER = "other", "Other"

    class PermitStatus(models.TextChoices):
        NOT_STARTED = "not_started", "Not Started"
        APPLICATION_FILED = "application_filed", "Application Filed"
        UNDER_REVIEW = "under_review", "Under Review"
        CLARIFICATION = "clarification", "Clarification Requested"
        APPROVED = "approved", "Approved"
        CONDITIONAL = "conditional", "Conditionally Approved"
        REJECTED = "rejected", "Rejected"
        EXPIRED = "expired", "Expired"
        RENEWED = "renewed", "Renewed"

    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="org_project_permits")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="permits")

    reference = models.CharField(max_length=100, blank=True, unique=True, help_text="Auto-generated as PRM-##### when blank.")
    name = models.CharField(max_length=255)
    permit_type = models.CharField(max_length=30, choices=PermitType.choices, default=PermitType.BUILDING)
    status = models.CharField(max_length=20, choices=PermitStatus.choices, default=PermitStatus.NOT_STARTED)
    is_critical_path = models.BooleanField(default=False, help_text="Blocks the development schedule if delayed.")

    # Authority
    authority_name = models.CharField(max_length=255, blank=True)
    authority_contact = models.CharField(max_length=255, blank=True)
    authority_portal = models.URLField(blank=True)

    # Dates
    application_date = models.DateField(null=True, blank=True)
    expected_approval_date = models.DateField(null=True, blank=True)
    actual_approval_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    renewal_date = models.DateField(null=True, blank=True)

    # Financials
    application_fee = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    fee_paid = models.BooleanField(default=False)

    # Resolution
    approval_certificate_ref = models.CharField(max_length=255, blank=True, help_text="Certificate number once approved.")
    conditions = models.TextField(blank=True, help_text="Conditions attached to approval.")
    rejection_reason = models.TextField(blank=True)

    # Sequencing
    depends_on = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="unlocks", help_text="Permit that must be approved first.",
    )
    sort_order = models.PositiveIntegerField(default=0)

    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"], name="prm_org_status_idx"),
        ]

    @property
    def is_delayed(self):
        if self.status in ("approved", "conditional", "renewed", "rejected", "expired"):
            return False
        if self.expected_approval_date and self.expected_approval_date < date.today():
            return True
        return False

    @property
    def days_until_expiry(self):
        if not self.expiry_date:
            return None
        return (self.expiry_date - date.today()).days

    def save(self, *args, **kwargs):
        if not self.reference:
            last = (
                ProjectPermit.objects.filter(reference__startswith="PRM-")
                .order_by("-reference")
                .values_list("reference", flat=True)
                .first()
            )
            seq = 1
            if last:
                try:
                    seq = int(last.split("-")[1]) + 1
                except (IndexError, ValueError):
                    pass
            self.reference = f"PRM-{seq:05d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference} — {self.name}"


class PermitSubmission(models.Model):
    """Document submission record for a permit application."""

    permit = models.ForeignKey(ProjectPermit, on_delete=models.CASCADE, related_name="submissions")
    version = models.CharField(max_length=20, default="Rev 01")
    description = models.CharField(max_length=255)
    documents_list = models.TextField(blank=True, help_text="List of documents submitted.")
    submission_date = models.DateField()
    submitted_by = models.CharField(max_length=255, blank=True)
    authority_receipt_ref = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-submission_date"]

    def __str__(self):
        return f"{self.version} — {self.description}"


class PermitQuery(models.Model):
    """Query or clarification request from the regulatory authority."""

    class QueryStatus(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In Progress"
        RESOLVED = "resolved", "Resolved"

    permit = models.ForeignKey(ProjectPermit, on_delete=models.CASCADE, related_name="queries")
    query_date = models.DateField()
    subject = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    assigned_consultant = models.CharField(max_length=255, blank=True)
    response = models.TextField(blank=True)
    response_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=QueryStatus.choices, default=QueryStatus.OPEN)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-query_date"]

    def __str__(self):
        return f"{self.subject} — {self.status}"


# ── Design Management ────────────────────────────────────────────────


class DesignPhase(models.Model):
    """High-level design stage within a project lifecycle."""

    class StageName(models.TextChoices):
        CONCEPT = "concept", "Concept Design"
        SCHEMATIC = "schematic", "Schematic Design"
        DETAILED = "detailed", "Detailed Design"
        CONSTRUCTION = "construction", "Construction Drawings"
        AS_BUILT = "as_built", "As-Built"

    class StageStatus(models.TextChoices):
        NOT_STARTED = "not_started", "Not Started"
        IN_PROGRESS = "in_progress", "In Progress"
        IN_REVIEW = "in_review", "In Review"
        CLOSED = "closed", "Closed"

    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="org_design_phases")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="design_phases")
    stage = models.CharField(max_length=20, choices=StageName.choices)
    status = models.CharField(max_length=20, choices=StageStatus.choices, default=StageStatus.NOT_STARTED)
    total_deliverables = models.PositiveIntegerField(default=0)
    approved_deliverables = models.PositiveIntegerField(default=0)
    closeout_checked = models.BooleanField(default=False, help_text="Phase gate checked before advancing.")
    sort_order = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order"]
        unique_together = [("project", "stage")]

    @property
    def progress(self):
        if self.total_deliverables > 0:
            return round(self.approved_deliverables / self.total_deliverables * 100, 1)
        return 0

    def __str__(self):
        return f"{self.get_stage_display()} — {self.project.name}"


class Drawing(models.Model):
    """A technical drawing/sheet in the project drawing register."""

    class Discipline(models.TextChoices):
        ARCHITECTURAL = "architectural", "Architectural"
        STRUCTURAL = "structural", "Structural"
        MEP_MECHANICAL = "mep_mechanical", "MEP — Mechanical"
        MEP_ELECTRICAL = "mep_electrical", "MEP — Electrical"
        MEP_PLUMBING = "mep_plumbing", "MEP — Plumbing"
        CIVIL = "civil", "Civil"
        LANDSCAPE = "landscape", "Landscape"
        INTERIOR = "interior", "Interior Design"
        OTHER = "other", "Other"

    class ApprovalState(models.TextChoices):
        DRAFT = "draft", "Draft"
        FOR_REVIEW = "for_review", "For Review"
        APPROVED_NOTED = "approved_noted", "Approved as Noted"
        AFC = "afc", "Approved for Construction"
        SUPERSEDED = "superseded", "Superseded"
        REVISE_RESUBMIT = "revise_resubmit", "Revise and Resubmit"

    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="org_drawings")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="drawings")
    design_phase = models.ForeignKey(DesignPhase, on_delete=models.SET_NULL, null=True, blank=True, related_name="drawings")

    drawing_number = models.CharField(max_length=100, help_text="e.g. ARCH-P1-001")
    title = models.CharField(max_length=255)
    discipline = models.CharField(max_length=20, choices=Discipline.choices, default=Discipline.ARCHITECTURAL)
    current_revision = models.CharField(max_length=20, default="Rev A")
    approval_state = models.CharField(max_length=20, choices=ApprovalState.choices, default=ApprovalState.DRAFT)
    scale = models.CharField(max_length=50, blank=True, help_text="e.g. 1:100")

    # Submitter info
    submitted_by = models.CharField(max_length=255, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["discipline", "drawing_number"]
        indexes = [
            models.Index(fields=["organization", "approval_state"], name="drw_org_approval_idx"),
        ]

    def __str__(self):
        return f"{self.drawing_number} ({self.current_revision}) — {self.title}"


class DrawingRevision(models.Model):
    """Revision history for a drawing — tracks changes between versions."""

    drawing = models.ForeignKey(Drawing, on_delete=models.CASCADE, related_name="revisions")
    revision_code = models.CharField(max_length=20, help_text="e.g. Rev A, Rev B")
    change_description = models.TextField(blank=True)
    submitted_by = models.CharField(max_length=255, blank=True)
    submitted_date = models.DateField()
    approval_state = models.CharField(max_length=20, choices=Drawing.ApprovalState.choices, default="draft")
    reviewer_comments = models.TextField(blank=True)
    reviewed_by = models.CharField(max_length=255, blank=True)
    reviewed_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-submitted_date"]

    def __str__(self):
        return f"{self.drawing.drawing_number} — {self.revision_code}"


class DesignReviewMeeting(models.Model):
    """Record of a design review meeting."""

    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="org_design_meetings")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="design_review_meetings")
    date = models.DateField()
    title = models.CharField(max_length=255)
    attendees = models.TextField(blank=True)
    key_decisions = models.TextField(blank=True)
    action_items = models.JSONField(default=list, blank=True, help_text="[{description, assigned_to, due_date}]")
    linked_drawings = models.ManyToManyField(Drawing, blank=True, related_name="meetings")
    minutes_notes = models.TextField(blank=True)
    recorded_by = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.date} — {self.title}"


# ── Procurement Planning ─────────────────────────────────────────────


class ProcurementPlan(models.Model):
    """Master procurement strategy for a project."""

    class ContractingStrategy(models.TextChoices):
        DESIGN_BUILD = "design_build", "Design & Build"
        TRADITIONAL = "traditional", "Traditional"
        MANAGEMENT = "management", "Management Contracting"
        CONSTRUCTION_MGMT = "construction_mgmt", "Construction Management"
        TURNKEY = "turnkey", "Turnkey / EPC"
        OTHER = "other", "Other"

    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="org_procurement_plans")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="procurement_plans")
    strategy = models.CharField(max_length=20, choices=ContractingStrategy.choices, default=ContractingStrategy.TRADITIONAL)
    total_budget = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    contingency_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("5.00"))
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_strategy_display()} — {self.project.name}"


class ProcurementPackage(models.Model):
    """A buyable contract package within a procurement plan."""

    class PackageStatus(models.TextChoices):
        PLANNING = "planning", "Planning"
        PQQ = "pqq", "Prequalification"
        TENDERING = "tendering", "Tendering (RFP Out)"
        EVALUATION = "evaluation", "Evaluation"
        NEGOTIATION = "negotiation", "Negotiation"
        AWARDED = "awarded", "Contract Awarded"
        SIGNED = "signed", "Contract Signed"
        ON_HOLD = "on_hold", "On Hold"
        CANCELLED = "cancelled", "Cancelled"

    plan = models.ForeignKey(ProcurementPlan, on_delete=models.CASCADE, related_name="packages")
    name = models.CharField(max_length=255, help_text="e.g. Piling Works, Main Shell/Core, MEP Fit-out")
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=PackageStatus.choices, default=PackageStatus.PLANNING)

    # Budget
    estimated_budget = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    contract_value = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"), help_text="Actual value once awarded")

    # Timeline
    pqq_issue_date = models.DateField(null=True, blank=True)
    rfp_issue_date = models.DateField(null=True, blank=True)
    tender_return_date = models.DateField(null=True, blank=True)
    evaluation_end_date = models.DateField(null=True, blank=True)
    award_date = models.DateField(null=True, blank=True)
    contract_start_date = models.DateField(null=True, blank=True)

    # Award
    awarded_to = models.CharField(max_length=255, blank=True)
    award_justification = models.TextField(blank=True)

    sort_order = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]

    @property
    def budget_variance(self):
        if self.contract_value and self.estimated_budget:
            return self.estimated_budget - self.contract_value
        return None

    @property
    def is_behind_schedule(self):
        today = date.today()
        if self.status in ("awarded", "signed", "cancelled"):
            return False
        if self.tender_return_date and self.tender_return_date < today and self.status in ("tendering",):
            return True
        if self.evaluation_end_date and self.evaluation_end_date < today and self.status in ("evaluation",):
            return True
        return False

    def __str__(self):
        return f"{self.name} — {self.get_status_display()}"


class PackageBidder(models.Model):
    """A bidder/contractor in the evaluation for a procurement package."""

    package = models.ForeignKey(ProcurementPackage, on_delete=models.CASCADE, related_name="bidders")
    firm_name = models.CharField(max_length=255)
    specialization = models.CharField(max_length=255, blank=True)
    bid_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    proposed_duration_days = models.PositiveIntegerField(null=True, blank=True)

    # Scoring
    score_price = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    score_technical = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    score_timeline = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    score_safety = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    total_score = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)

    is_recommended = models.BooleanField(default=False)
    is_prequalified = models.BooleanField(default=True)
    compliance_notes = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-total_score", "firm_name"]

    def __str__(self):
        return f"{self.firm_name} — {self.package.name}"


# ── Sales & Revenue Forecast ─────────────────────────────────────────


class SalesRevenueForecast(models.Model):
    """Master revenue forecast for a project."""

    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="org_sales_forecasts")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="sales_forecasts")
    gross_development_value = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    marketing_budget = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    marketing_budget_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("2.00"))
    sales_launch_date = models.DateField(null=True, blank=True)
    target_sellout_date = models.DateField(null=True, blank=True)
    payment_structure = models.JSONField(
        default=list, blank=True,
        help_text='[{"stage":"Deposit","pct":30},{"stage":"Construction","pct":40},{"stage":"Handover","pct":30}]',
    )
    agents = models.JSONField(default=list, blank=True, help_text='[{"firm","commission_pct"}]')
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Sales Forecast — {self.project.name}"


class SaleableUnit(models.Model):
    """Individual saleable asset (apartment, shop, parking, etc.)."""

    class UnitType(models.TextChoices):
        STUDIO = "studio", "Studio"
        ONE_BED = "1_bed", "1-Bedroom"
        TWO_BED = "2_bed", "2-Bedroom"
        THREE_BED = "3_bed", "3-Bedroom"
        FOUR_BED = "4_bed", "4-Bedroom"
        PENTHOUSE = "penthouse", "Penthouse"
        DUPLEX = "duplex", "Duplex"
        COMMERCIAL = "commercial", "Commercial / Retail"
        OFFICE = "office", "Office"
        PARKING = "parking", "Parking Bay"
        STORAGE = "storage", "Storage Unit"
        OTHER = "other", "Other"

    class UnitStatus(models.TextChoices):
        AVAILABLE = "available", "Available"
        RESERVED = "reserved", "Reserved"
        UNDER_CONTRACT = "under_contract", "Under Contract"
        SOLD = "sold", "Sold"
        HELD = "held", "Held / Not for Sale"

    forecast = models.ForeignKey(SalesRevenueForecast, on_delete=models.CASCADE, related_name="units")
    unit_id = models.CharField(max_length=50, help_text="e.g. Apt 402, Shop G1")
    unit_type = models.CharField(max_length=20, choices=UnitType.choices, default=UnitType.TWO_BED)
    floor_location = models.CharField(max_length=100, blank=True)
    size_sqm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    asking_price = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    minimum_price = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    sold_price = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=UnitStatus.choices, default=UnitStatus.AVAILABLE)
    buyer_name = models.CharField(max_length=255, blank=True)
    reserved_date = models.DateField(null=True, blank=True)
    sold_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "unit_id"]

    @property
    def price_per_sqm(self):
        if self.size_sqm and self.size_sqm > 0 and self.asking_price:
            return round(float(self.asking_price) / float(self.size_sqm), 2)
        return None

    def __str__(self):
        return f"{self.unit_id} — {self.get_unit_type_display()}"


class SalesPhaseTarget(models.Model):
    """Monthly/phased sales targets within a forecast."""

    forecast = models.ForeignKey(SalesRevenueForecast, on_delete=models.CASCADE, related_name="phase_targets")
    phase_name = models.CharField(max_length=255, help_text="e.g. Off-Plan, Construction, Post-Completion")
    start_date = models.DateField()
    end_date = models.DateField()
    target_units = models.PositiveIntegerField(default=0)
    target_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    actual_units = models.PositiveIntegerField(default=0)
    actual_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    milestone_trigger = models.CharField(max_length=255, blank=True, help_text="e.g. Showroom Launch, Topped Out")
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "start_date"]

    @property
    def variance(self):
        return self.actual_revenue - self.target_revenue

    @property
    def unit_variance(self):
        return self.actual_units - self.target_units

    def __str__(self):
        return f"{self.phase_name} — {self.target_units} units"


# ── Milestones & Stage Gates ─────────────────────────────────────────


class StageGate(models.Model):
    """Formal gate between project phases — enforces prerequisites before advancement."""

    class GateType(models.TextChoices):
        FEASIBILITY = "feasibility", "Feasibility Gate"
        INVESTMENT_APPROVAL = "investment_approval", "Investment Approval Gate"
        PRE_CONSTRUCTION = "pre_construction", "Pre-Construction Gate"
        DESIGN_COMPLETION = "design_completion", "Design Completion Gate"
        PROCUREMENT_COMPLETION = "procurement_completion", "Procurement Completion Gate"
        CONSTRUCTION_MIDPOINT = "construction_midpoint", "Construction Midpoint Gate"
        PRACTICAL_COMPLETION = "practical_completion", "Practical Completion Gate"
        TESTING_COMMISSIONING = "testing_commissioning", "Testing & Commissioning Gate"
        HANDOVER = "handover", "Handover Gate"
        CLOSEOUT = "closeout", "Closeout Gate"
        CUSTOM = "custom", "Custom Gate"

    class GateStatus(models.TextChoices):
        LOCKED = "locked", "Locked"
        UNDER_REVIEW = "under_review", "Under Review"
        OPEN = "open", "Open (Passed)"
        CONDITIONAL = "conditional", "Approved with Conditions"
        FAILED = "failed", "Failed / Rejected"

    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="org_stage_gates")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="stage_gates")

    gate_type = models.CharField(max_length=30, choices=GateType.choices, default=GateType.CUSTOM)
    name = models.CharField(max_length=255, help_text="e.g. Pre-Construction Gate, Construction Completion Gate")
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=GateStatus.choices, default=GateStatus.LOCKED)
    sort_order = models.PositiveIntegerField(default=0)

    # Prerequisites
    prerequisite_milestones = models.ManyToManyField(
        "ProjectMilestone", blank=True, related_name="gate_prerequisites",
        help_text="Milestones that must be achieved before this gate can open.",
    )
    prerequisite_notes = models.TextField(blank=True)

    # Decision
    scheduled_review_date = models.DateField(null=True, blank=True)
    actual_review_date = models.DateField(null=True, blank=True)
    decided_by = models.CharField(max_length=255, blank=True, help_text="e.g. Investment Committee, Steering Committee")
    decision_date = models.DateField(null=True, blank=True)
    conditions = models.TextField(blank=True, help_text="Conditions attached to approval.")
    rejection_reason = models.TextField(blank=True)

    # Variance
    baseline_date = models.DateField(null=True, blank=True)
    delay_days = models.IntegerField(default=0)
    delay_root_cause = models.TextField(blank=True)
    recovery_plan = models.TextField(blank=True)

    # Financial trigger
    financial_release_triggered = models.BooleanField(default=False)
    financial_release_notes = models.TextField(blank=True)

    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order"]
        indexes = [
            models.Index(fields=["organization", "status"], name="sgate_org_status_idx"),
        ]

    @property
    def is_overdue(self):
        if self.status in ("open", "conditional"):
            return False
        if self.scheduled_review_date and self.scheduled_review_date < date.today():
            return True
        return False

    @property
    def prerequisites_met(self):
        """Check if all prerequisite milestones are completed."""
        return not self.prerequisite_milestones.filter(is_completed=False).exists()

    def __str__(self):
        return f"{self.name} — {self.get_status_display()}"


# ── Document Control ─────────────────────────────────────────────────

DOCUMENT_FOLDER_CHOICES = [
    ("01_feasibility", "01 — Feasibility & Strategy"),
    ("02_legal", "02 — Legal & Contracts"),
    ("03_design", "03 — Design Development"),
    ("04_permits", "04 — Permits & Regulatory"),
    ("05_governance", "05 — Governance & Minutes"),
    ("06_financial", "06 — Financial & Banking"),
    ("07_procurement", "07 — Procurement & Tenders"),
    ("08_construction", "08 — Construction Records"),
    ("09_hse", "09 — HSE & Compliance"),
    ("10_closeout", "10 — Closeout & Handover"),
    ("other", "Other"),
]


class ProjectDocument(models.Model):
    """A controlled document in the project archive."""

    class Classification(models.TextChoices):
        PUBLIC = "public", "Public"
        INTERNAL = "internal", "Internal"
        CONFIDENTIAL = "confidential", "Confidential"
        RESTRICTED = "restricted", "Restricted"

    class ExecutionStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        FOR_REVIEW = "for_review", "For Review"
        APPROVED = "approved", "Approved"
        EXECUTED = "executed", "Original Executed"
        SCANNED = "scanned", "Scanned Copy"
        SUPERSEDED = "superseded", "Superseded"

    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="org_project_documents")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="controlled_documents")

    reference = models.CharField(max_length=100, blank=True, unique=True, help_text="Auto-generated as DOC-##### when blank.")
    title = models.CharField(max_length=255)
    folder = models.CharField(max_length=30, choices=DOCUMENT_FOLDER_CHOICES, default="other")
    classification = models.CharField(max_length=20, choices=Classification.choices, default=Classification.INTERNAL)
    execution_status = models.CharField(max_length=20, choices=ExecutionStatus.choices, default=ExecutionStatus.DRAFT)
    current_version = models.CharField(max_length=50, default="v1")

    author = models.CharField(max_length=255, blank=True)
    source = models.CharField(max_length=255, blank=True, help_text="e.g. Legal Counsel, Lead Architect")
    description = models.TextField(blank=True)
    retention_years = models.PositiveIntegerField(null=True, blank=True, help_text="How long to keep for audit.")
    expiry_date = models.DateField(null=True, blank=True)
    linked_module = models.CharField(max_length=100, blank=True, help_text="e.g. Consultant: Adesanya, Permit: PRM-00012")

    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["folder", "title"]
        indexes = [
            models.Index(fields=["organization", "folder", "classification"], name="doc_org_folder_class_idx"),
        ]

    @property
    def is_expiring_soon(self):
        if not self.expiry_date:
            return False
        return (self.expiry_date - date.today()).days <= 30

    def save(self, *args, **kwargs):
        if not self.reference:
            last = (
                ProjectDocument.objects.filter(reference__startswith="DOC-")
                .order_by("-reference")
                .values_list("reference", flat=True)
                .first()
            )
            seq = 1
            if last:
                try:
                    seq = int(last.split("-")[1]) + 1
                except (IndexError, ValueError):
                    pass
            self.reference = f"DOC-{seq:05d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference} — {self.title}"


class DocumentVersion(models.Model):
    """Version history entry for a controlled document."""

    document = models.ForeignKey(ProjectDocument, on_delete=models.CASCADE, related_name="versions")
    version_label = models.CharField(max_length=50, help_text="e.g. v1, v2, Final")
    change_summary = models.TextField(blank=True)
    uploaded_by = models.CharField(max_length=255, blank=True)
    uploaded_date = models.DateField()
    is_current = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_date", "-created_at"]

    def __str__(self):
        return f"{self.document.reference} — {self.version_label}"


class DocumentTransmittal(models.Model):
    """Formal transmission record of a document to external parties."""

    class Purpose(models.TextChoices):
        FOR_INFORMATION = "for_information", "For Information"
        FOR_APPROVAL = "for_approval", "For Approval"
        FOR_CONSTRUCTION = "for_construction", "For Construction"
        FOR_RECORD = "for_record", "For Record"
        FOR_REVIEW = "for_review", "For Review"

    document = models.ForeignKey(ProjectDocument, on_delete=models.CASCADE, related_name="transmittals")
    transmittal_ref = models.CharField(max_length=100, blank=True)
    recipient = models.CharField(max_length=255)
    purpose = models.CharField(max_length=20, choices=Purpose.choices, default=Purpose.FOR_INFORMATION)
    sent_date = models.DateField()
    acknowledged = models.BooleanField(default=False)
    acknowledged_date = models.DateTimeField(null=True, blank=True)
    sent_by = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sent_date"]

    def __str__(self):
        return f"{self.transmittal_ref} → {self.recipient}"


class MeetingMinutesArchive(models.Model):
    """Structured meeting minutes in the document archive."""

    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="org_meeting_minutes")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="meeting_minutes")
    series = models.CharField(max_length=255, help_text="e.g. Weekly Site Meetings, Monthly Steering Committee")
    date = models.DateField()
    title = models.CharField(max_length=255)
    attendees = models.TextField(blank=True)
    minutes_text = models.TextField(blank=True)
    action_items = models.JSONField(default=list, blank=True, help_text="[{description, assigned_to, due_date, status}]")
    recorded_by = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.series} — {self.date}"


# ── Project Communications ───────────────────────────────────────────


class ProjectAnnouncement(models.Model):
    """Project-wide announcement / update."""

    class Priority(models.TextChoices):
        CRITICAL = "critical", "Critical"
        HIGH = "high", "High"
        NORMAL = "normal", "Normal"
        LOW = "low", "Low"

    class Audience(models.TextChoices):
        ALL = "all", "All Stakeholders"
        INTERNAL = "internal", "Internal Team"
        EXTERNAL = "external", "External Stakeholders"
        INVESTORS = "investors", "Investors"
        CONSULTANTS = "consultants", "Consultants"

    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="org_project_announcements")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="announcements")

    subject = models.CharField(max_length=255)
    body = models.TextField()
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.NORMAL)
    audience = models.CharField(max_length=20, choices=Audience.choices, default=Audience.ALL)
    is_pinned = models.BooleanField(default=False)
    published_by = models.CharField(max_length=255, blank=True)
    published_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_pinned", "-published_at"]

    def __str__(self):
        return f"{self.subject}"


class ProjectDecisionLog(models.Model):
    """Centralized log of project decisions for dispute prevention."""

    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="org_project_decisions")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="decisions")

    decision_id = models.CharField(max_length=100, blank=True, unique=True, help_text="Auto-generated as DEC-### when blank.")
    subject = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    decided_by = models.CharField(max_length=255, help_text="e.g. Steering Committee, Project Director")
    rationale = models.TextField(blank=True, help_text="Summary of the data or logic used.")
    decision_date = models.DateField()
    meeting_reference = models.CharField(max_length=255, blank=True, help_text="Link to specific meeting minutes.")
    impact_modules = models.JSONField(default=list, blank=True, help_text='["Design","Budget","Schedule"]')
    status = models.CharField(
        max_length=20,
        choices=[("active", "Active"), ("superseded", "Superseded"), ("reversed", "Reversed")],
        default="active",
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-decision_date"]

    def save(self, *args, **kwargs):
        if not self.decision_id:
            last = (
                ProjectDecisionLog.objects.filter(decision_id__startswith="DEC-")
                .order_by("-decision_id")
                .values_list("decision_id", flat=True)
                .first()
            )
            seq = 1
            if last:
                try:
                    seq = int(last.split("-")[1]) + 1
                except (IndexError, ValueError):
                    pass
            self.decision_id = f"DEC-{seq:03d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.decision_id} — {self.subject}"


class StakeholderUpdate(models.Model):
    """Structured progress report distributed to stakeholder groups."""

    class Frequency(models.TextChoices):
        WEEKLY = "weekly", "Weekly"
        FORTNIGHTLY = "fortnightly", "Fortnightly"
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        AD_HOC = "ad_hoc", "Ad-Hoc"

    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="org_stakeholder_updates")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="stakeholder_updates")

    title = models.CharField(max_length=255)
    frequency = models.CharField(max_length=20, choices=Frequency.choices, default=Frequency.MONTHLY)
    report_date = models.DateField()
    executive_summary = models.TextField(blank=True)
    schedule_status = models.TextField(blank=True)
    financial_status = models.TextField(blank=True)
    risk_blockers = models.TextField(blank=True)
    distribution_group = models.CharField(max_length=255, blank=True, help_text="e.g. Investors Group, Lending Bank")
    recipients = models.JSONField(default=list, blank=True, help_text='[{"name","email","read":false}]')
    prepared_by = models.CharField(max_length=255, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-report_date"]

    @property
    def read_count(self):
        return sum(1 for r in self.recipients if r.get("read"))

    def __str__(self):
        return f"{self.title} — {self.report_date}"


# ── Project Reporting ────────────────────────────────────────────────


class ProjectReport(models.Model):
    """Snapshot report aggregating data across project modules."""

    class ReportType(models.TextChoices):
        EXECUTIVE = "executive", "Executive Summary"
        FINANCIAL = "financial", "Financial (BvA)"
        SCHEDULE = "schedule", "Schedule Variance"
        RISK = "risk", "Risk & Issue Matrix"
        INVESTOR = "investor", "Investor / Stakeholder"
        MONTHLY = "monthly", "Monthly Progress"
        CUSTOM = "custom", "Custom"

    class RAGStatus(models.TextChoices):
        GREEN = "green", "Green — On Track"
        AMBER = "amber", "Amber — At Risk"
        RED = "red", "Red — Critical"

    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="org_project_reports")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="reports")

    reference = models.CharField(max_length=100, blank=True, unique=True, help_text="Auto-generated as RPT-##### when blank.")
    title = models.CharField(max_length=255)
    report_type = models.CharField(max_length=20, choices=ReportType.choices, default=ReportType.EXECUTIVE)
    report_date = models.DateField()
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)

    # RAG statuses
    schedule_rag = models.CharField(max_length=10, choices=RAGStatus.choices, default=RAGStatus.GREEN)
    budget_rag = models.CharField(max_length=10, choices=RAGStatus.choices, default=RAGStatus.GREEN)
    quality_rag = models.CharField(max_length=10, choices=RAGStatus.choices, default=RAGStatus.GREEN)
    safety_rag = models.CharField(max_length=10, choices=RAGStatus.choices, default=RAGStatus.GREEN)

    # Content sections
    executive_summary = models.TextField(blank=True)
    key_achievements = models.JSONField(default=list, blank=True, help_text='["Milestone achieved","Permit obtained"]')
    key_issues = models.JSONField(default=list, blank=True, help_text='["Delay in permit","Budget overrun"]')

    # Financial snapshot
    original_budget = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    committed_spend = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    actual_spend = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    forecast_at_completion = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    contingency_used_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # Schedule snapshot
    schedule_variance_summary = models.TextField(blank=True)
    critical_path_impact = models.TextField(blank=True)
    overall_completion_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # Risk snapshot
    top_risks = models.JSONField(default=list, blank=True, help_text='[{"risk","impact","probability","mitigation","owner"}]')

    is_frozen = models.BooleanField(default=False, help_text="Locked snapshot — cannot be edited.")
    prepared_by = models.CharField(max_length=255, blank=True)
    approved_by = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-report_date"]
        indexes = [
            models.Index(fields=["organization", "report_type"], name="rpt_org_type_idx"),
        ]

    @property
    def budget_variance(self):
        if self.original_budget and self.forecast_at_completion:
            return self.original_budget - self.forecast_at_completion
        return None

    @property
    def budget_variance_pct(self):
        if self.original_budget and self.forecast_at_completion and self.original_budget > 0:
            return round(float(self.original_budget - self.forecast_at_completion) / float(self.original_budget) * 100, 1)
        return None

    def save(self, *args, **kwargs):
        if not self.reference:
            last = (
                ProjectReport.objects.filter(reference__startswith="RPT-")
                .order_by("-reference")
                .values_list("reference", flat=True)
                .first()
            )
            seq = 1
            if last:
                try:
                    seq = int(last.split("-")[1]) + 1
                except (IndexError, ValueError):
                    pass
            self.reference = f"RPT-{seq:05d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference} — {self.title}"


# ── Project Closeout ─────────────────────────────────────────────────


class ProjectCloseout(models.Model):
    """Master closeout record for a project."""

    class CloseoutStatus(models.TextChoices):
        IN_PROGRESS = "in_progress", "In Progress"
        PENDING_REVIEW = "pending_review", "Pending Review"
        COMPLETED = "completed", "Completed"
        ARCHIVED = "archived", "Archived"

    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="org_project_closeouts")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="closeouts")

    status = models.CharField(max_length=20, choices=CloseoutStatus.choices, default=CloseoutStatus.IN_PROGRESS)
    practical_completion_date = models.DateField(null=True, blank=True)
    final_completion_date = models.DateField(null=True, blank=True)

    final_project_cost = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    original_budget = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    total_variations = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    retention_held = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    retention_released = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    retention_release_date = models.DateField(null=True, blank=True)

    financial_reconciliation_done = models.BooleanField(default=False)
    contracts_closed = models.BooleanField(default=False)
    handover_completed = models.BooleanField(default=False)
    snags_resolved = models.BooleanField(default=False)
    documentation_archived = models.BooleanField(default=False)
    warranties_registered = models.BooleanField(default=False)

    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def completion_pct(self):
        checks = [
            self.financial_reconciliation_done, self.contracts_closed,
            self.handover_completed, self.snags_resolved,
            self.documentation_archived, self.warranties_registered,
        ]
        return round(sum(1 for c in checks if c) / len(checks) * 100)

    @property
    def budget_variance(self):
        if self.original_budget and self.final_project_cost:
            return self.original_budget - self.final_project_cost
        return None

    def __str__(self):
        return f"Closeout — {self.project.name}"


class FinalAccountEntry(models.Model):
    closeout = models.ForeignKey(ProjectCloseout, on_delete=models.CASCADE, related_name="final_accounts")
    contractor_name = models.CharField(max_length=255)
    original_contract_value = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    approved_variations = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    final_settled_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    retention_held = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    retention_released = models.BooleanField(default=False)
    closeout_certificate_issued = models.BooleanField(default=False)
    performance_rating = models.PositiveIntegerField(null=True, blank=True, help_text="1-5 star rating")
    performance_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["contractor_name"]

    @property
    def variance(self):
        return self.original_contract_value + self.approved_variations - self.final_settled_amount

    def __str__(self):
        return f"{self.contractor_name} — {self.final_settled_amount}"


class SnagListItem(models.Model):
    class SnagStatus(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In Progress"
        RESOLVED = "resolved", "Resolved"
        ACCEPTED = "accepted", "Accepted (As-Is)"

    closeout = models.ForeignKey(ProjectCloseout, on_delete=models.CASCADE, related_name="snag_items")
    location = models.CharField(max_length=255)
    description = models.TextField()
    responsible_contractor = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=SnagStatus.choices, default=SnagStatus.OPEN)
    reported_date = models.DateField(auto_now_add=True)
    resolved_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["status", "-reported_date"]

    def __str__(self):
        return f"{self.location} — {self.description[:50]}"


class WarrantyTracker(models.Model):
    closeout = models.ForeignKey(ProjectCloseout, on_delete=models.CASCADE, related_name="warranties")
    asset_system = models.CharField(max_length=255, help_text="e.g. Roof Waterproofing, HVAC System")
    provider = models.CharField(max_length=255, blank=True)
    warranty_start = models.DateField()
    warranty_end = models.DateField()
    claim_log = models.JSONField(default=list, blank=True, help_text='[{"date","issue","resolution","status"}]')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["warranty_end"]

    @property
    def is_active(self):
        return self.warranty_end >= date.today()

    @property
    def days_remaining(self):
        return (self.warranty_end - date.today()).days

    def __str__(self):
        return f"{self.asset_system} — expires {self.warranty_end}"


# ── Interim Valuations ───────────────────────────────────────────────


class InterimValuation(models.Model):
    """Payment certificate / interim valuation for work completed on a project."""

    class ValuationStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under Review"
        CERTIFIED = "certified", "Certified"
        PAID = "paid", "Paid"
        DISPUTED = "disputed", "Disputed"

    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="org_interim_valuations")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="interim_valuations")
    contractor_name = models.CharField(max_length=255)
    work_package = models.ForeignKey(
        "ProjectWorkPackage", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="interim_valuations",
    )

    valuation_number = models.CharField(max_length=100, blank=True, unique=True, help_text="Auto-generated as IPC-##### when blank.")
    valuation_date = models.DateField()
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=ValuationStatus.choices, default=ValuationStatus.DRAFT)

    # Totals (computed from line items but stored for performance)
    gross_value = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"), help_text="Sum of line item amounts")
    previous_certified = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    this_period_value = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    retention_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("5.00"))
    retention_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    net_payable = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))

    certified_by = models.CharField(max_length=255, blank=True)
    certified_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-valuation_date"]
        indexes = [
            models.Index(fields=["organization", "project", "status"], name="iv_org_proj_status_idx"),
        ]

    def recalculate(self):
        """Recalculate totals from line items."""
        items = self.line_items.all()
        self.gross_value = sum(i.amount for i in items)
        self.this_period_value = self.gross_value - self.previous_certified
        self.retention_amount = self.this_period_value * self.retention_pct / Decimal("100")
        self.net_payable = self.this_period_value - self.retention_amount

    def save(self, *args, **kwargs):
        if not self.valuation_number:
            last = (
                InterimValuation.objects.filter(valuation_number__startswith="IPC-")
                .order_by("-valuation_number")
                .values_list("valuation_number", flat=True)
                .first()
            )
            seq = 1
            if last:
                try:
                    seq = int(last.split("-")[1]) + 1
                except (IndexError, ValueError):
                    pass
            self.valuation_number = f"IPC-{seq:05d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.valuation_number} — {self.contractor_name}"


class ValuationLineItem(models.Model):
    """Individual BOQ line in an interim valuation — completed qty × contract rate."""

    valuation = models.ForeignKey(InterimValuation, on_delete=models.CASCADE, related_name="line_items")
    bom_item = models.ForeignKey(
        "inventory.BOMItem", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="valuation_line_items",
        help_text="Links to the specific BOQ item being valued.",
    )
    description = models.CharField(max_length=255)
    unit_of_measure = models.CharField(max_length=50, blank=True)
    contract_rate = models.DecimalField(max_digits=15, decimal_places=2)
    contract_quantity = models.DecimalField(max_digits=12, decimal_places=2, help_text="Total BOQ quantity")
    previous_quantity = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"), help_text="Quantity certified in prior valuations")
    this_period_quantity = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"), help_text="Quantity completed this period")
    cumulative_quantity = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"), help_text="previous + this period")
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"), help_text="cumulative_quantity × contract_rate")
    sort_order = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order"]

    def save(self, *args, **kwargs):
        self.cumulative_quantity = self.previous_quantity + self.this_period_quantity
        self.amount = self.cumulative_quantity * self.contract_rate
        super().save(*args, **kwargs)

    @property
    def completion_pct(self):
        if self.contract_quantity and self.contract_quantity > 0:
            return round(float(self.cumulative_quantity) / float(self.contract_quantity) * 100, 1)
        return 0

    def __str__(self):
        return f"{self.description} — {self.cumulative_quantity} × {self.contract_rate}"
