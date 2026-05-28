"""
Project Blueprint models.

A blueprint is a fully authored, self-contained project plan — the single
source of truth that drives project execution. It contains the WBS hierarchy,
dependencies, schedule rules, resource model, cost projections, and scenarios.

Blueprints can be:
- Created empty ("Create Custom")
- Seeded from a ProjectTemplate ("Create from Template")
- Once saved and finalized, they appear in the Blueprints list as "draft"
- Committed to create a live Project
- Edited post-commitment — changes cascade to the live project
"""


from django.conf import settings
from django.db import models


class ProjectBlueprint(models.Model):
    """The master plan document."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        REVIEW = "review", "Under Review"
        COMMITTED = "committed", "Committed"
        ARCHIVED = "archived", "Archived"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="project_blueprints",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)

    # Origin
    source_template = models.ForeignKey(
        "settings.ProjectTemplate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="derived_blueprints",
        help_text="Template this blueprint was seeded from (if any).",
    )
    source_bom = models.ForeignKey(
        "inventory.BillOfMaterials",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="derived_blueprints",
        help_text="BOM this blueprint was auto-generated from (Route B).",
    )

    # Linked project (set when committed)
    project = models.OneToOneField(
        "projects.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="blueprint",
    )

    # Schedule settings (embedded, not a separate model)
    work_days = models.JSONField(default=dict, blank=True)
    shift_start = models.TimeField(default="08:00")
    shift_end = models.TimeField(default="17:00")
    hours_per_day = models.DecimalField(max_digits=4, decimal_places=1, default=9)
    public_holidays = models.JSONField(default=list, blank=True)
    custom_holidays = models.JSONField(default=list, blank=True)
    rainy_season_buffer_enabled = models.BooleanField(default=False)
    rainy_season_buffer_pct = models.DecimalField(max_digits=5, decimal_places=1, default=15)
    rainy_season_months = models.JSONField(default=list, blank=True)
    outdoor_task_categories = models.JSONField(default=list, blank=True)
    duration_scalar_pct = models.DecimalField(max_digits=5, decimal_places=1, default=100)

    # Resource roles
    resource_roles = models.JSONField(default=list, blank=True)
    travel_buffer_hours = models.DecimalField(max_digits=5, decimal_places=1, default=0)

    # Cost assumptions
    material_markup_pct = models.DecimalField(max_digits=5, decimal_places=1, default=10)
    location_factor = models.CharField(max_length=30, default="lagos")
    contingency_pct = models.DecimalField(max_digits=5, decimal_places=1, default=10)
    equipment_daily_rate = models.DecimalField(max_digits=12, decimal_places=2, default=50000)
    fx_rate_usd_ngn = models.DecimalField(max_digits=10, decimal_places=2, default=1550)

    # Projected totals (computed)
    projected_duration_days = models.PositiveIntegerField(default=0)
    projected_total_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # Authoring
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_blueprints",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["organization", "status", "-updated_at"], name="bp_org_status_idx"),
        ]

    def __str__(self):
        return f"{self.name} [{self.get_status_display()}]"


class BlueprintPhase(models.Model):
    """A phase in the blueprint's WBS."""

    blueprint = models.ForeignKey(
        ProjectBlueprint, on_delete=models.CASCADE, related_name="phases",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    duration_days = models.PositiveIntegerField(null=True, blank=True)
    weight = models.PositiveIntegerField(default=1)
    planned_budget = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.blueprint.name} — {self.name}"


class BlueprintActivity(models.Model):
    """An activity within a blueprint phase (WBS intermediate layer)."""

    phase = models.ForeignKey(
        BlueprintPhase, on_delete=models.CASCADE, related_name="activities",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    wbs_code = models.CharField(max_length=50, blank=True)
    estimated_duration_days = models.PositiveIntegerField(null=True, blank=True)
    estimated_effort_hours = models.DecimalField(max_digits=8, decimal_places=1, null=True, blank=True)

    class Meta:
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.phase.name} — {self.name}"


class BlueprintTask(models.Model):
    """A task within a blueprint activity."""

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    activity = models.ForeignKey(
        BlueprintActivity, on_delete=models.CASCADE, related_name="tasks",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    reference_code = models.CharField(max_length=100, blank=True)
    assigned_role = models.CharField(max_length=200, blank=True)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    standard_duration_hours = models.DecimalField(max_digits=7, decimal_places=1, null=True, blank=True)
    estimated_effort_hours = models.DecimalField(max_digits=7, decimal_places=1, null=True, blank=True)
    crew_size = models.PositiveIntegerField(null=True, blank=True)
    estimated_labor_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    output_unit = models.CharField(max_length=50, blank=True)
    equipment_type = models.CharField(max_length=255, blank=True)
    category = models.CharField(max_length=50, blank=True)
    is_milestone = models.BooleanField(default=False)
    complexity = models.CharField(max_length=10, default="medium")

    # BoQ, quality, safety
    required_materials = models.JSONField(default=list, blank=True)
    required_ppe = models.JSONField(default=list, blank=True)
    quality_gates = models.JSONField(default=list, blank=True)
    photo_requirements = models.JSONField(default=list, blank=True)
    sop_markdown = models.TextField(blank=True)

    # BOQ-driven planning fields
    estimated_duration_days = models.PositiveIntegerField(null=True, blank=True, help_text="Duration calculated from BOQ quantity ÷ production rate.")
    boq_quantity = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Quantity from BOQ item.")
    boq_unit = models.CharField(max_length=50, blank=True, help_text="Unit of measure from BOQ item.")
    boq_item = models.ForeignKey(
        "inventory.BOMItem", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="blueprint_tasks",
        help_text="Source BOQ line item (for traceability).",
    )

    # Source template (for traceability)
    source_task_template = models.ForeignKey(
        "settings.TaskTemplate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="blueprint_instances",
    )

    class Meta:
        ordering = ["sort_order"]

    def __str__(self):
        return self.name


class BlueprintDependency(models.Model):
    """Dependency between activities/tasks in the blueprint."""

    class DependencyType(models.TextChoices):
        FS = "fs", "Finish-to-Start"
        SS = "ss", "Start-to-Start"
        FF = "ff", "Finish-to-Finish"
        SF = "sf", "Start-to-Finish"

    class Strength(models.TextChoices):
        HARD = "hard", "Hard"
        SOFT = "soft", "Soft"

    blueprint = models.ForeignKey(
        ProjectBlueprint, on_delete=models.CASCADE, related_name="dependencies",
    )
    from_activity = models.ForeignKey(
        BlueprintActivity, on_delete=models.CASCADE, null=True, blank=True,
        related_name="outgoing_deps",
    )
    from_task = models.ForeignKey(
        BlueprintTask, on_delete=models.CASCADE, null=True, blank=True,
        related_name="outgoing_deps",
    )
    to_activity = models.ForeignKey(
        BlueprintActivity, on_delete=models.CASCADE, null=True, blank=True,
        related_name="incoming_deps",
    )
    to_task = models.ForeignKey(
        BlueprintTask, on_delete=models.CASCADE, null=True, blank=True,
        related_name="incoming_deps",
    )
    dependency_type = models.CharField(max_length=2, choices=DependencyType.choices, default=DependencyType.FS)
    lag_hours = models.DecimalField(max_digits=7, decimal_places=1, default=0)
    strength = models.CharField(max_length=4, choices=Strength.choices, default=Strength.HARD)
    risk_impact = models.PositiveSmallIntegerField(default=5)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["id"]

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


class BlueprintScenario(models.Model):
    """A what-if scenario within a blueprint."""

    class RiskLevel(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    blueprint = models.ForeignKey(
        ProjectBlueprint, on_delete=models.CASCADE, related_name="scenarios",
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_baseline = models.BooleanField(default=False)
    risk_level = models.CharField(max_length=10, choices=RiskLevel.choices, default=RiskLevel.MEDIUM)

    # Assumptions
    duration_scalar_pct = models.DecimalField(max_digits=5, decimal_places=1, default=100)
    material_markup_pct = models.DecimalField(max_digits=5, decimal_places=1, default=10)
    location_factor = models.CharField(max_length=30, default="lagos")
    contingency_pct = models.DecimalField(max_digits=5, decimal_places=1, default=10)

    # Projected results
    projected_duration_days = models.PositiveIntegerField(default=0)
    projected_total_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_baseline", "-created_at"]

    def __str__(self):
        return f"{self.blueprint.name} — {self.name}"
