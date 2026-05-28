from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers

from apps.documents.models import Document
from apps.hr.models import OrientationChecklistItem, Payslip, TrainingCompletion, TrainingRecord
from apps.procurement.models import GoodsReceipt, PurchaseOrder, Vendor
from apps.settings.models import RiskMitigationRule, RiskScoreMatrix

from .models import (
    CommissioningPlan,
    CommissioningPunchItem,
    ConsultantCommunicationLog,
    ConsultantDeliverable,
    ConsultantPaymentMilestone,
    DesignPhase,
    DesignReviewMeeting,
    Drawing,
    DrawingRevision,
    HSEIncident,
    HSEPermitToWork,
    HSEToolboxTalk,
    PackageBidder,
    ProcurementPackage,
    ProcurementPlan,
    DocumentTransmittal,
    DocumentVersion,
    MeetingMinutesArchive,
    ConstructionReport,
    CostCodeBudget,
    CostTransaction,
    RFI,
    RFIComment,
    SiteInstruction,
    TestRecord,
    FinalAccountEntry,
    ProjectAnnouncement,
    ProjectCloseout,
    ProjectDecisionLog,
    ProjectDocument,
    ProjectReport,
    SnagListItem,
    StakeholderUpdate,
    WarrantyTracker,
    SaleableUnit,
    SalesPhaseTarget,
    SalesRevenueForecast,
    StageGate,
    PermitQuery,
    PermitSubmission,
    ProjectPermit,
    EquipmentDeploymentLog,
    EquipmentMaintenanceLog,
    NonConformanceReport,
    DevelopmentBudget,
    DevelopmentBudgetCategory,
    FeasibilityStudy,
    FinancingCovenant,
    FinancingDrawdown,
    FinancingRepayment,
    FinancingSource,
    LandAcquisition,
    LandPaymentMilestone,
    PipelineOpportunity,
    ProjectConsultant,
    Project,
    ProjectSetupConfig,
    ProjectTeamMember,
    ProjectConstructionSchedule,
    ProjectContractorProfile,
    ProjectCostEntry,
    ProjectDailySiteReport,
    ProjectDailySiteReportPhoto,
    ProjectEquipment,
    ProjectExecutionInspection,
    ProjectExecutionInspectionItem,
    ProjectFieldEscalation,
    ProjectMilestone,
    ProjectMilestoneApprovalDecision,
    ProjectMilestoneApprovalRule,
    ProjectPhase,
    ProjectPhaseDependency,
    ProjectPlanningInsight,
    ProjectRiskRegisterEntry,
    ProjectScheduleDelayLog,
    ProjectSiteMobilization,
    ProjectSupportingAttachment,
    ProjectTask,
    ProjectTaskComment,
    ProjectVariationOrder,
    ProjectWorkforceLog,
    ProjectWorkPackage,
    QualityCheckTemplate,
    QualityPlan,
)

DEFAULT_MATRIX_CONFIG = {
    "likelihood": {
        "very_low": 1,
        "low": 2,
        "medium": 3,
        "high": 4,
        "very_high": 5,
    },
    "impact": {
        "very_low": 1,
        "low": 2,
        "medium": 3,
        "high": 4,
        "very_high": 5,
    },
    "thresholds": {"low": 5, "medium": 10, "high": 15, "critical": 20},
}

UserModel = get_user_model()


def _normalize_score_map(raw: object, fallback: dict[str, int]) -> dict[str, int]:
    if not isinstance(raw, dict):
        return fallback
    normalized: dict[str, int] = {}
    for key, value in raw.items():
        try:
            normalized[str(key)] = int(value)
        except (TypeError, ValueError):
            continue
    return normalized or fallback


def _normalize_thresholds(raw: object) -> dict[str, int]:
    fallback = DEFAULT_MATRIX_CONFIG["thresholds"]
    if not isinstance(raw, dict):
        return fallback
    normalized: dict[str, int] = {}
    for key in ("low", "medium", "high", "critical"):
        value = raw.get(key)
        try:
            normalized[key] = int(value)
        except (TypeError, ValueError):
            normalized[key] = fallback[key]
    return normalized


def _resolve_org_from_request(request) -> object:
    if not request:
        return None
    profile = getattr(request.user, "profile", None)
    organization = getattr(profile, "organization", None)
    if request.user.is_superuser and organization is None:
        from apps.accounts.models import Organization

        return Organization.objects.first()
    return organization


def _matrix_config_for_org(organization) -> dict:
    if not organization:
        return DEFAULT_MATRIX_CONFIG
    matrix = RiskScoreMatrix.objects.filter(organization=organization).first()
    if not matrix or not isinstance(matrix.matrix_config, dict):
        return DEFAULT_MATRIX_CONFIG
    return matrix.matrix_config


def _calculate_risk_score(
    matrix_config: dict,
    likelihood_key: str,
    impact_key: str,
) -> tuple[int, int, int, str]:
    likelihood_map = _normalize_score_map(
        matrix_config.get("likelihood"),
        DEFAULT_MATRIX_CONFIG["likelihood"],
    )
    impact_map = _normalize_score_map(
        matrix_config.get("impact"),
        DEFAULT_MATRIX_CONFIG["impact"],
    )
    thresholds = _normalize_thresholds(matrix_config.get("thresholds"))

    if likelihood_key not in likelihood_map:
        raise serializers.ValidationError(
            {"likelihood_key": f"Invalid likelihood key '{likelihood_key}' for configured matrix."}
        )
    if impact_key not in impact_map:
        raise serializers.ValidationError(
            {"impact_key": f"Invalid impact key '{impact_key}' for configured matrix."}
        )

    likelihood_score = likelihood_map[likelihood_key]
    impact_score = impact_map[impact_key]
    risk_score = likelihood_score * impact_score

    if risk_score <= thresholds["low"]:
        severity = ProjectRiskRegisterEntry.Severity.LOW
    elif risk_score <= thresholds["medium"]:
        severity = ProjectRiskRegisterEntry.Severity.MEDIUM
    elif risk_score <= thresholds["high"]:
        severity = ProjectRiskRegisterEntry.Severity.HIGH
    else:
        severity = ProjectRiskRegisterEntry.Severity.CRITICAL

    return likelihood_score, impact_score, risk_score, severity


def compute_progress(phases):
    """Weighted progress from phase statuses."""
    total_weight = 0
    weighted_complete = 0
    for phase in phases:
        if phase.status == ProjectPhase.Status.SKIPPED:
            continue
        total_weight += phase.weight
        if phase.status == ProjectPhase.Status.COMPLETED:
            weighted_complete += phase.weight
        elif phase.status == ProjectPhase.Status.IN_PROGRESS:
            weighted_complete += phase.weight * 0.5
    if total_weight == 0:
        return 0
    return round(weighted_complete / total_weight * 100)


MOBILIZATION_SITE_PREPARATION_FIELD_MAP = {
    "fencing": "fencing_status",
    "site_offices": "site_offices_status",
    "storage_yards": "storage_yards_status",
    "worker_welfare_facilities": "worker_welfare_facilities_status",
    "utilities_connection": "utilities_connection_status",
    "temporary_roads": "temporary_roads_status",
    "security_deployment": "security_deployment_status",
}

MOBILIZATION_CHECKLIST_FIELDS = (
    "contractors_mobilized",
    "equipment_delivered",
    "material_staging",
    "survey_control_established",
    "permits_obtained",
    "insurance_certificates",
    "safety_induction",
)

MOBILIZATION_LINKED_CHECKLIST_FIELDS = (
    "contractors_mobilized",
    "equipment_delivered",
    "material_staging",
    "safety_induction",
)

MOBILIZATION_MANUAL_CHECKLIST_FIELDS = (
    "survey_control_established",
    "permits_obtained",
    "insurance_certificates",
)


class ProjectSitePreparationUpdateSerializer(serializers.Serializer):
    fencing = serializers.ChoiceField(
        choices=ProjectSiteMobilization.PreparationStatus.choices,
        required=False,
    )
    site_offices = serializers.ChoiceField(
        choices=ProjectSiteMobilization.PreparationStatus.choices,
        required=False,
    )
    storage_yards = serializers.ChoiceField(
        choices=ProjectSiteMobilization.PreparationStatus.choices,
        required=False,
    )
    worker_welfare_facilities = serializers.ChoiceField(
        choices=ProjectSiteMobilization.PreparationStatus.choices,
        required=False,
    )
    utilities_connection = serializers.ChoiceField(
        choices=ProjectSiteMobilization.PreparationStatus.choices,
        required=False,
    )
    temporary_roads = serializers.ChoiceField(
        choices=ProjectSiteMobilization.PreparationStatus.choices,
        required=False,
    )
    security_deployment = serializers.ChoiceField(
        choices=ProjectSiteMobilization.PreparationStatus.choices,
        required=False,
    )


class ProjectSiteMobilizationChecklistUpdateSerializer(serializers.Serializer):
    survey_control_established = serializers.BooleanField(required=False)
    permits_obtained = serializers.BooleanField(required=False)
    insurance_certificates = serializers.BooleanField(required=False)


class ProjectSiteMobilizationUpdateSerializer(serializers.Serializer):
    project = serializers.IntegerField(min_value=1)
    planned_start_date = serializers.DateField(required=False, allow_null=True)
    actual_start_date = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    site_preparation = ProjectSitePreparationUpdateSerializer(required=False)
    checklist = ProjectSiteMobilizationChecklistUpdateSerializer(required=False)

    def validate(self, attrs):
        start = attrs.get("planned_start_date")
        actual = attrs.get("actual_start_date")
        if start and actual and actual < start:
            raise serializers.ValidationError(
                {"actual_start_date": "Actual start date cannot be earlier than planned start date."}
            )
        return attrs


class ProjectSiteMobilizationReadSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    site_preparation = serializers.SerializerMethodField()
    checklist = serializers.SerializerMethodField()
    linked_sources = serializers.SerializerMethodField()
    completion = serializers.SerializerMethodField()

    class Meta:
        model = ProjectSiteMobilization
        fields = [
            "id",
            "project",
            "project_name",
            "planned_start_date",
            "actual_start_date",
            "site_preparation",
            "checklist",
            "linked_sources",
            "completion",
            "notes",
            "last_integrations_synced_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_site_preparation(self, obj):
        return {
            key: getattr(obj, field_name)
            for key, field_name in MOBILIZATION_SITE_PREPARATION_FIELD_MAP.items()
        }

    def get_checklist(self, obj):
        values = {field_name: bool(getattr(obj, field_name)) for field_name in MOBILIZATION_CHECKLIST_FIELDS}
        values["_linked_fields"] = list(MOBILIZATION_LINKED_CHECKLIST_FIELDS)
        values["_manual_fields"] = list(MOBILIZATION_MANUAL_CHECKLIST_FIELDS)
        return values

    def get_linked_sources(self, obj):
        return {
            "procurement": {
                "contractors_count": obj.linked_procurement_contractors_count,
                "material_staging_count": obj.linked_procurement_material_staging_count,
            },
            "hr": {
                "equipment_delivery_count": obj.linked_hr_equipment_delivery_count,
                "safety_induction_count": obj.linked_hr_safety_induction_count,
            },
        }

    def get_completion(self, obj):
        preparation_values = [
            getattr(obj, field_name)
            for field_name in MOBILIZATION_SITE_PREPARATION_FIELD_MAP.values()
        ]
        preparation_total = len(preparation_values) or 1
        preparation_completed = sum(
            1
            for value in preparation_values
            if value == ProjectSiteMobilization.PreparationStatus.COMPLETED
        )
        preparation_blocked = sum(
            1
            for value in preparation_values
            if value == ProjectSiteMobilization.PreparationStatus.BLOCKED
        )

        checklist_values = [
            bool(getattr(obj, field_name))
            for field_name in MOBILIZATION_CHECKLIST_FIELDS
        ]
        checklist_total = len(checklist_values) or 1
        checklist_completed = sum(1 for value in checklist_values if value)

        combined_total = preparation_total + checklist_total
        combined_completed = preparation_completed + checklist_completed

        return {
            "site_preparation_percent": round((preparation_completed / preparation_total) * 100, 2),
            "checklist_percent": round((checklist_completed / checklist_total) * 100, 2),
            "overall_percent": round((combined_completed / combined_total) * 100, 2),
            "blocked_items": preparation_blocked,
        }


class ProjectConstructionScheduleSectionNotesUpdateSerializer(serializers.Serializer):
    master_schedule = serializers.CharField(required=False, allow_blank=True)
    phase_schedules = serializers.CharField(required=False, allow_blank=True)
    lookahead_schedules = serializers.CharField(required=False, allow_blank=True)
    task_dependencies = serializers.CharField(required=False, allow_blank=True)
    critical_path = serializers.CharField(required=False, allow_blank=True)
    resource_assignments = serializers.CharField(required=False, allow_blank=True)


class ProjectConstructionScheduleTimelineUpdateSerializer(serializers.Serializer):
    project_manager = serializers.CharField(required=False, allow_blank=True)
    task_assignees = serializers.CharField(required=False, allow_blank=True)
    site_workers = serializers.CharField(required=False, allow_blank=True)


class ProjectConstructionScheduleUpdateSerializer(serializers.Serializer):
    project = serializers.IntegerField(min_value=1)
    lookahead_window_days = serializers.IntegerField(required=False, min_value=7, max_value=90)
    notes = serializers.CharField(required=False, allow_blank=True)
    section_notes = ProjectConstructionScheduleSectionNotesUpdateSerializer(required=False)
    timeline_sections = ProjectConstructionScheduleTimelineUpdateSerializer(required=False)


class ProjectConstructionScheduleReadSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    section_notes = serializers.SerializerMethodField()
    timeline_sections = serializers.SerializerMethodField()

    class Meta:
        model = ProjectConstructionSchedule
        fields = [
            "id",
            "project",
            "project_name",
            "lookahead_window_days",
            "section_notes",
            "timeline_sections",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_section_notes(self, obj):
        return {
            "master_schedule": obj.master_schedule_notes,
            "phase_schedules": obj.phase_schedule_notes,
            "lookahead_schedules": obj.lookahead_schedule_notes,
            "task_dependencies": obj.task_dependency_notes,
            "critical_path": obj.critical_path_notes,
            "resource_assignments": obj.resource_assignment_notes,
        }

    def get_timeline_sections(self, obj):
        return {
            "project_manager": obj.project_manager_updates,
            "task_assignees": obj.task_assignee_updates,
            "site_workers": obj.site_worker_updates,
        }


# --- Nested resource serializers ---

class ProjectPhaseSerializer(serializers.ModelSerializer):
    budget_variance = serializers.SerializerMethodField()
    schedule_variance_days = serializers.SerializerMethodField()
    task_count = serializers.IntegerField(read_only=True, default=0)
    completed_task_count = serializers.IntegerField(read_only=True, default=0)
    milestone_count = serializers.IntegerField(read_only=True, default=0)
    cost_total = serializers.DecimalField(
        max_digits=15, decimal_places=2, read_only=True, default=0,
    )

    class Meta:
        model = ProjectPhase
        fields = "__all__"
        read_only_fields = ("id", "project", "organization", "created_at", "updated_at")

    def get_budget_variance(self, obj):
        if obj.planned_budget is not None:
            actual = getattr(obj, "cost_total", obj.actual_cost) or 0
            return str(obj.planned_budget - actual)
        return None

    def get_schedule_variance_days(self, obj):
        baseline_end = obj.baseline_end_date or obj.planned_end_date
        revised_end = obj.revised_end_date or obj.planned_end_date
        if not baseline_end or not revised_end:
            return None
        return (revised_end - baseline_end).days


class ProjectMilestoneSerializer(serializers.ModelSerializer):
    schedule_variance_days = serializers.SerializerMethodField()
    approval_history = serializers.SerializerMethodField()

    class Meta:
        model = ProjectMilestone
        fields = [
            "id",
            "phase",
            "name",
            "description",
            "baseline_target_date",
            "revised_target_date",
            "schedule_revision_reason",
            "target_date",
            "completed_date",
            "is_completed",
            "approval_required",
            "approval_status",
            "approved_by",
            "approved_at",
            "sort_order",
            "reference_code",
            "typical_offset_days",
            "success_criteria",
            "key_deliverables",
            "predecessors",
            "successors",
            "owner_role",
            "approver_role",
            "stakeholders_to_notify",
            "created_at",
            "updated_at",
            "schedule_variance_days",
            "approval_history",
        ]
        read_only_fields = ("id", "phase", "created_at", "updated_at")

    def get_schedule_variance_days(self, obj):
        baseline_target = obj.baseline_target_date or obj.target_date
        revised_target = obj.revised_target_date or obj.target_date
        if not baseline_target or not revised_target:
            return None
        return (revised_target - baseline_target).days

    def get_approval_history(self, obj):
        decisions = obj.approval_decisions.select_related("approver", "approver_role")
        return ProjectMilestoneApprovalDecisionSerializer(decisions, many=True).data


class ProjectPhaseDependencySerializer(serializers.ModelSerializer):
    predecessor_phase_name = serializers.CharField(
        source="predecessor_phase.name",
        read_only=True,
    )
    successor_phase_name = serializers.CharField(
        source="successor_phase.name",
        read_only=True,
    )

    class Meta:
        model = ProjectPhaseDependency
        fields = [
            "id",
            "project",
            "predecessor_phase",
            "predecessor_phase_name",
            "successor_phase",
            "successor_phase_name",
            "dependency_type",
            "lag_days",
            "notes",
            "created_at",
        ]
        read_only_fields = ["id", "project", "predecessor_phase_name", "successor_phase_name", "created_at"]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        project = attrs.get("project", getattr(self.instance, "project", None))
        predecessor = attrs.get("predecessor_phase", getattr(self.instance, "predecessor_phase", None))
        successor = attrs.get("successor_phase", getattr(self.instance, "successor_phase", None))
        if project and predecessor and predecessor.project_id != project.id:
            raise serializers.ValidationError(
                {"predecessor_phase": "Predecessor phase must belong to selected project."}
            )
        if project and successor and successor.project_id != project.id:
            raise serializers.ValidationError(
                {"successor_phase": "Successor phase must belong to selected project."}
            )
        if predecessor and successor and predecessor.id == successor.id:
            raise serializers.ValidationError(
                {"successor_phase": "Predecessor and successor must be different phases."}
            )
        return attrs


class ProjectMilestoneApprovalRuleSerializer(serializers.ModelSerializer):
    required_role_name = serializers.CharField(source="required_role.name", read_only=True)
    phase_name = serializers.CharField(source="phase.name", read_only=True, allow_null=True)

    class Meta:
        model = ProjectMilestoneApprovalRule
        fields = [
            "id",
            "project",
            "phase",
            "phase_name",
            "required_role",
            "required_role_name",
            "sequence_order",
            "is_mandatory",
            "is_active",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "project",
            "phase_name",
            "required_role_name",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        project = attrs.get("project", getattr(self.instance, "project", None))
        phase = attrs.get("phase", getattr(self.instance, "phase", None))
        if project and phase and phase.project_id != project.id:
            raise serializers.ValidationError(
                {"phase": "Selected phase does not belong to selected project."}
            )
        return attrs


class ProjectMilestoneApprovalDecisionSerializer(serializers.ModelSerializer):
    milestone_name = serializers.CharField(source="milestone.name", read_only=True)
    approver_name = serializers.CharField(source="approver.get_full_name", read_only=True, allow_null=True)
    approver_role_name = serializers.CharField(source="approver_role.name", read_only=True, allow_null=True)

    class Meta:
        model = ProjectMilestoneApprovalDecision
        fields = [
            "id",
            "milestone",
            "milestone_name",
            "rule",
            "approver_role",
            "approver_role_name",
            "approver",
            "approver_name",
            "decision",
            "comments",
            "decided_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "milestone_name",
            "approver_role_name",
            "approver_name",
            "created_at",
            "updated_at",
        ]


class ProjectScheduleDelayLogSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    phase_name = serializers.CharField(source="phase.name", read_only=True, allow_null=True)
    milestone_name = serializers.CharField(source="milestone.name", read_only=True, allow_null=True)
    source_issue_title = serializers.CharField(source="source_issue.title", read_only=True, allow_null=True)

    class Meta:
        model = ProjectScheduleDelayLog
        fields = [
            "id",
            "project",
            "project_name",
            "phase",
            "phase_name",
            "milestone",
            "milestone_name",
            "source_issue",
            "source_issue_title",
            "delay_date",
            "delay_type",
            "impact_days",
            "reason",
            "mitigation_action",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "project_name",
            "phase_name",
            "milestone_name",
            "source_issue_title",
            "created_by",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        project = attrs.get("project", getattr(self.instance, "project", None))
        phase = attrs.get("phase", getattr(self.instance, "phase", None))
        milestone = attrs.get("milestone", getattr(self.instance, "milestone", None))
        source_issue = attrs.get("source_issue", getattr(self.instance, "source_issue", None))
        if project and phase and phase.project_id != project.id:
            raise serializers.ValidationError(
                {"phase": "Selected phase does not belong to selected project."}
            )
        if project and milestone and milestone.phase.project_id != project.id:
            raise serializers.ValidationError(
                {"milestone": "Selected milestone does not belong to selected project."}
            )
        if phase and milestone and milestone.phase_id != phase.id:
            raise serializers.ValidationError(
                {"milestone": "Selected milestone does not belong to selected phase."}
            )
        if project and source_issue and source_issue.project_id != project.id:
            raise serializers.ValidationError(
                {"source_issue": "Selected source issue does not belong to selected project."}
            )
        return attrs


class ProjectTaskCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = ProjectTaskComment
        fields = ["id", "task", "author", "author_name", "comment", "created_at", "updated_at"]
        read_only_fields = ["id", "task", "author", "author_name", "created_at", "updated_at"]

    def get_author_name(self, obj):
        if obj.author_id:
            full_name = obj.author.get_full_name().strip()
            if full_name:
                return full_name
            return obj.author.email
        return None


class ProjectTaskSerializer(serializers.ModelSerializer):
    phase = serializers.PrimaryKeyRelatedField(
        queryset=ProjectPhase.objects.all(),
        required=False,
    )
    project = serializers.IntegerField(source="phase.project_id", read_only=True)
    project_name = serializers.CharField(source="phase.project.name", read_only=True)
    phase_name = serializers.CharField(source="phase.name", read_only=True)
    assigned_user_name = serializers.SerializerMethodField()
    linked_document_records = serializers.SerializerMethodField()
    linked_contract_records = serializers.SerializerMethodField()
    linked_risk_records = serializers.SerializerMethodField()
    sla_status = serializers.SerializerMethodField()
    sla_time_remaining_seconds = serializers.SerializerMethodField()
    comments_count = serializers.IntegerField(read_only=True, default=0)
    assigned_user = serializers.PrimaryKeyRelatedField(
        queryset=UserModel.objects.all(),
        allow_null=True,
        required=False,
    )
    linked_documents = serializers.PrimaryKeyRelatedField(
        queryset=Document.objects.all(),
        many=True,
        required=False,
    )
    linked_variation_orders = serializers.PrimaryKeyRelatedField(
        queryset=ProjectVariationOrder.objects.all(),
        many=True,
        required=False,
    )
    linked_risks = serializers.PrimaryKeyRelatedField(
        queryset=ProjectRiskRegisterEntry.objects.all(),
        many=True,
        required=False,
    )

    class Meta:
        model = ProjectTask
        fields = [
            "id",
            "project",
            "project_name",
            "phase",
            "phase_name",
            "name",
            "description",
            "work_package",
            "status",
            "priority",
            "assigned_to",
            "assigned_user",
            "assigned_user_name",
            "assigned_external_ref",
            "linked_documents",
            "linked_document_records",
            "linked_variation_orders",
            "linked_contract_records",
            "linked_risks",
            "linked_risk_records",
            "sla_target_at",
            "sla_breached_at",
            "sla_status",
            "sla_time_remaining_seconds",
            "due_date",
            "completed_date",
            "sort_order",
            "reference_code",
            "reviewer_role",
            "collaborators",
            "estimated_effort_hours",
            "predecessors",
            "successors",
            "definition_of_done",
            "tools_required",
            "reference_links",
            "comments_count",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = (
            "id",
            "project",
            "project_name",
            "phase_name",
            "assigned_user_name",
            "linked_document_records",
            "linked_contract_records",
            "linked_risk_records",
            "sla_status",
            "sla_time_remaining_seconds",
            "sla_breached_at",
            "comments_count",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        )

    def get_assigned_user_name(self, obj):
        if obj.assigned_user_id:
            full_name = obj.assigned_user.get_full_name().strip()
            if full_name:
                return full_name
            return obj.assigned_user.email
        return None

    def get_linked_document_records(self, obj):
        return [
            {
                "id": document.id,
                "title": document.title,
                "document_number": document.document_number,
                "status": document.status,
                "project": document.project_id,
            }
            for document in obj.linked_documents.all()
        ]

    def get_linked_contract_records(self, obj):
        return [
            {
                "id": variation.id,
                "project": variation.project_id,
                "variation_number": variation.variation_number,
                "title": variation.title,
                "status": variation.status,
                "contract_value": str(variation.contract_value),
            }
            for variation in obj.linked_variation_orders.all()
        ]

    def get_linked_risk_records(self, obj):
        return [
            {
                "id": risk.id,
                "project": risk.project_id,
                "title": risk.title,
                "severity": risk.severity,
                "status": risk.status,
                "risk_score": risk.risk_score,
            }
            for risk in obj.linked_risks.all()
        ]

    def get_sla_status(self, obj):
        if obj.completed_date:
            return "completed"
        if not obj.sla_target_at:
            return "not_configured"
        now = timezone.now()
        if now >= obj.sla_target_at:
            return "breached"
        if (obj.sla_target_at - now).total_seconds() <= 86400:
            return "at_risk"
        return "on_track"

    def get_sla_time_remaining_seconds(self, obj):
        if obj.completed_date or not obj.sla_target_at:
            return None
        return int((obj.sla_target_at - timezone.now()).total_seconds())

    def validate(self, attrs):
        attrs = super().validate(attrs)
        phase = attrs.get("phase", getattr(self.instance, "phase", None))
        linked_documents = attrs.get("linked_documents")
        linked_variation_orders = attrs.get("linked_variation_orders")
        linked_risks = attrs.get("linked_risks")

        if phase and linked_documents is not None:
            invalid_docs = [
                doc.document_number
                for doc in linked_documents
                if doc.project_id and doc.project_id != phase.project_id
            ]
            if invalid_docs:
                raise serializers.ValidationError(
                    {
                        "linked_documents": (
                            "Linked documents must belong to the selected project "
                            "or be project-agnostic."
                        )
                    }
                )

        if phase and linked_variation_orders is not None:
            if any(variation.project_id != phase.project_id for variation in linked_variation_orders):
                raise serializers.ValidationError(
                    {"linked_variation_orders": "All linked contracts must belong to the selected project."}
                )

        if phase and linked_risks is not None:
            if any(risk.project_id != phase.project_id for risk in linked_risks):
                raise serializers.ValidationError(
                    {"linked_risks": "All linked risks must belong to the selected project."}
                )

        if phase is None and not self.context.get("phase_locked"):
            raise serializers.ValidationError({"phase": "This field is required."})

        assigned_user = attrs.get("assigned_user", getattr(self.instance, "assigned_user", None))
        request = self.context.get("request")
        actor_org_id = getattr(getattr(getattr(request, "user", None), "profile", None), "organization_id", None)
        assigned_org_id = getattr(getattr(assigned_user, "profile", None), "organization_id", None)
        if actor_org_id and assigned_user and assigned_org_id and assigned_org_id != actor_org_id:
            raise serializers.ValidationError(
                {"assigned_user": "Assigned user must belong to the same organization."}
            )

        return attrs


class ProjectWorkPackageSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    phase_name = serializers.CharField(source="phase.name", read_only=True, allow_null=True)
    contractor_name = serializers.CharField(
        source="contractor.name",
        read_only=True,
        allow_null=True,
    )
    drawings = serializers.PrimaryKeyRelatedField(
        queryset=Document.objects.all(),
        many=True,
        required=False,
    )
    linked_purchase_orders = serializers.PrimaryKeyRelatedField(
        queryset=PurchaseOrder.objects.all(),
        many=True,
        required=False,
    )
    linked_cost_entries = serializers.PrimaryKeyRelatedField(
        queryset=ProjectCostEntry.objects.all(),
        many=True,
        required=False,
    )
    linked_contractors = serializers.PrimaryKeyRelatedField(
        queryset=Vendor.objects.all(),
        many=True,
        required=False,
    )
    linked_inspections = serializers.PrimaryKeyRelatedField(
        queryset=ProjectExecutionInspection.objects.all(),
        many=True,
        required=False,
    )
    drawings_records = serializers.SerializerMethodField()
    linked_purchase_order_records = serializers.SerializerMethodField()
    linked_cost_entry_records = serializers.SerializerMethodField()
    linked_contractor_records = serializers.SerializerMethodField()
    linked_inspection_records = serializers.SerializerMethodField()
    linked_modules = serializers.SerializerMethodField()

    class Meta:
        model = ProjectWorkPackage
        fields = [
            "id",
            "package_id",
            "project",
            "project_name",
            "phase",
            "phase_name",
            "name",
            "scope_description",
            "contractor",
            "contractor_name",
            "boq_items",
            "budget",
            "start_date",
            "end_date",
            "drawings",
            "drawings_records",
            "quality_requirements",
            "safety_requirements",
            "inspection_plan",
            "linked_purchase_orders",
            "linked_purchase_order_records",
            "linked_cost_entries",
            "linked_cost_entry_records",
            "linked_contractors",
            "linked_contractor_records",
            "linked_inspections",
            "linked_inspection_records",
            "linked_modules",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = (
            "id",
            "project_name",
            "phase_name",
            "contractor_name",
            "drawings_records",
            "linked_purchase_order_records",
            "linked_cost_entry_records",
            "linked_contractor_records",
            "linked_inspection_records",
            "linked_modules",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        )

    def get_drawings_records(self, obj):
        return [
            {
                "id": document.id,
                "title": document.title,
                "document_number": document.document_number,
                "status": document.status,
                "project": document.project_id,
            }
            for document in obj.drawings.all()
        ]

    def get_linked_purchase_order_records(self, obj):
        return [
            {
                "id": po.id,
                "po_number": po.po_number,
                "status": po.status,
                "project": po.project_id,
                "vendor_name": po.vendor.name,
                "expected_delivery_date": po.expected_delivery_date,
                "total_amount": str(po.total_amount),
            }
            for po in obj.linked_purchase_orders.select_related("vendor")
        ]

    def get_linked_cost_entry_records(self, obj):
        return [
            {
                "id": cost.id,
                "phase": cost.phase_id,
                "description": cost.description,
                "amount": str(cost.amount),
                "date": cost.date,
                "category": cost.category,
            }
            for cost in obj.linked_cost_entries.select_related("phase")
        ]

    def get_linked_contractor_records(self, obj):
        return [
            {
                "id": contractor.id,
                "name": contractor.name,
                "category": contractor.category,
                "compliance_status": contractor.compliance_status,
            }
            for contractor in obj.linked_contractors.all()
        ]

    def get_linked_inspection_records(self, obj):
        return [
            {
                "id": inspection.id,
                "inspection_number": inspection.inspection_number,
                "status": inspection.status,
                "inspected_on": inspection.inspected_on,
                "work_package": inspection.work_package,
                "inspector_name": inspection.inspector_name,
            }
            for inspection in obj.linked_inspections.all()
        ]

    def get_linked_modules(self, obj):
        linked_contractors_total = obj.linked_contractors.count()
        if obj.contractor_id:
            linked_contractors_total += 1
        return {
            "procurement": {
                "purchase_orders": obj.linked_purchase_orders.count(),
            },
            "finance": {
                "cost_entries": obj.linked_cost_entries.count(),
            },
            "contractors": {
                "count": linked_contractors_total,
            },
            "inspections": {
                "count": obj.linked_inspections.count(),
            },
        }

    def validate(self, attrs):
        attrs = super().validate(attrs)
        project = attrs.get("project", getattr(self.instance, "project", None))
        phase = attrs.get("phase", getattr(self.instance, "phase", None))
        contractor = attrs.get("contractor", getattr(self.instance, "contractor", None))

        if project and phase and phase.project_id != project.id:
            raise serializers.ValidationError(
                {"phase": "Selected phase must belong to the selected project."}
            )

        if (
            contractor
            and project
            and contractor.organization_id
            and contractor.organization_id != project.organization_id
        ):
            raise serializers.ValidationError(
                {"contractor": "Selected contractor must belong to the selected project organization."}
            )

        linked_drawings = attrs.get("drawings")
        if project and linked_drawings is not None:
            invalid_drawings = [
                document.document_number
                for document in linked_drawings
                if document.project_id and document.project_id != project.id
            ]
            if invalid_drawings:
                raise serializers.ValidationError(
                    {
                        "drawings": (
                            "Drawings must belong to the selected project "
                            "or be project-agnostic."
                        )
                    }
                )

        linked_pos = attrs.get("linked_purchase_orders")
        if project and linked_pos is not None:
            if any(po.project_id != project.id for po in linked_pos):
                raise serializers.ValidationError(
                    {"linked_purchase_orders": "All linked purchase orders must belong to the selected project."}
                )

        linked_cost_entries = attrs.get("linked_cost_entries")
        if project and linked_cost_entries is not None:
            if any(cost.phase.project_id != project.id for cost in linked_cost_entries):
                raise serializers.ValidationError(
                    {"linked_cost_entries": "All linked cost entries must belong to the selected project."}
                )

        linked_contractors = attrs.get("linked_contractors")
        if project and linked_contractors is not None:
            if any(
                contractor.organization_id
                and contractor.organization_id != project.organization_id
                for contractor in linked_contractors
            ):
                raise serializers.ValidationError(
                    {"linked_contractors": "All linked contractors must belong to the selected project organization."}
                )

        linked_inspections = attrs.get("linked_inspections")
        if project and linked_inspections is not None:
            if any(inspection.project_id != project.id for inspection in linked_inspections):
                raise serializers.ValidationError(
                    {"linked_inspections": "All linked inspections must belong to the selected project."}
                )

        return attrs


class ProjectContractorProfileSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    contractor_name = serializers.CharField(source="contractor.name", read_only=True)
    company_snapshot = serializers.SerializerMethodField()
    work_packages = serializers.PrimaryKeyRelatedField(
        queryset=ProjectWorkPackage.objects.all(),
        many=True,
        required=False,
    )
    rfis = serializers.PrimaryKeyRelatedField(
        queryset=ProjectFieldEscalation.objects.all(),
        many=True,
        required=False,
    )
    inspection_results = serializers.PrimaryKeyRelatedField(
        queryset=ProjectExecutionInspection.objects.all(),
        many=True,
        required=False,
    )
    work_package_records = serializers.SerializerMethodField()
    rfi_records = serializers.SerializerMethodField()
    inspection_result_records = serializers.SerializerMethodField()
    received_items = serializers.SerializerMethodField()

    class Meta:
        model = ProjectContractorProfile
        fields = [
            "id",
            "project",
            "project_name",
            "contractor",
            "contractor_name",
            "company_snapshot",
            "company_profile",
            "trade_specialization",
            "contract_value",
            "insurance",
            "licenses",
            "performance_rating",
            "payment_history",
            "safety_record",
            "quality_record",
            "site_instructions",
            "work_packages",
            "work_package_records",
            "rfis",
            "rfi_records",
            "inspection_results",
            "inspection_result_records",
            "received_items",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = (
            "id",
            "project_name",
            "contractor_name",
            "company_snapshot",
            "work_package_records",
            "rfi_records",
            "inspection_result_records",
            "received_items",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        )

    def get_company_snapshot(self, obj):
        contractor = obj.contractor
        return {
            "id": contractor.id,
            "name": contractor.name,
            "category": contractor.category,
            "contact_person": contractor.contact_person,
            "email": contractor.email,
            "phone": contractor.phone,
            "address": contractor.address,
            "compliance_status": contractor.compliance_status,
            "performance_rating": str(contractor.performance_rating),
        }

    def get_work_package_records(self, obj):
        return [
            {
                "id": row.id,
                "package_id": row.package_id,
                "name": row.name,
                "budget": str(row.budget),
                "start_date": row.start_date,
                "end_date": row.end_date,
            }
            for row in obj.work_packages.all()
        ]

    def get_rfi_records(self, obj):
        return [
            {
                "id": row.id,
                "title": row.title,
                "status": row.status,
                "issue_date": row.issue_date,
                "severity": row.severity,
            }
            for row in obj.rfis.all()
        ]

    def get_inspection_result_records(self, obj):
        return [
            {
                "id": row.id,
                "inspection_number": row.inspection_number,
                "status": row.status,
                "inspected_on": row.inspected_on,
                "overall_score": str(row.overall_score) if row.overall_score is not None else None,
            }
            for row in obj.inspection_results.all()
        ]

    def get_received_items(self, obj):
        site_instruction_items = [
            line.strip()
            for line in (obj.site_instructions or "").splitlines()
            if line.strip()
        ]
        return {
            "site_instructions": {
                "count": len(site_instruction_items),
                "items": site_instruction_items,
            },
            "rfis": {"count": obj.rfis.count()},
            "inspection_results": {"count": obj.inspection_results.count()},
        }

    def validate(self, attrs):
        attrs = super().validate(attrs)
        project = attrs.get("project", getattr(self.instance, "project", None))
        contractor = attrs.get("contractor", getattr(self.instance, "contractor", None))

        if (
            project
            and contractor
            and contractor.organization_id
            and contractor.organization_id != project.organization_id
        ):
            raise serializers.ValidationError(
                {"contractor": "Selected contractor must belong to the selected project organization."}
            )

        work_packages = attrs.get("work_packages")
        if project and work_packages is not None:
            if any(row.project_id != project.id for row in work_packages):
                raise serializers.ValidationError(
                    {"work_packages": "All assigned work packages must belong to the selected project."}
                )

        rfis = attrs.get("rfis")
        if project and rfis is not None:
            for rfi in rfis:
                if rfi.project_id != project.id:
                    raise serializers.ValidationError(
                        {"rfis": "All linked RFIs must belong to the selected project."}
                    )
                if rfi.issue_type != ProjectFieldEscalation.IssueType.RFI_PENDING:
                    raise serializers.ValidationError(
                        {"rfis": "Only RFI issue records can be linked in contractor management."}
                    )

        inspection_results = attrs.get("inspection_results")
        if project and inspection_results is not None:
            if any(row.project_id != project.id for row in inspection_results):
                raise serializers.ValidationError(
                    {"inspection_results": "All linked inspections must belong to the selected project."}
                )

        return attrs


class ProjectCostEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectCostEntry
        fields = "__all__"
        read_only_fields = ("id", "phase", "organization", "created_at")


class ProjectVariationOrderSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    project_risk_rating = serializers.CharField(source="project.risk_rating", read_only=True)
    related_document_number = serializers.CharField(
        source="related_document.document_number",
        read_only=True,
        allow_null=True,
    )
    related_document_title = serializers.CharField(
        source="related_document.title",
        read_only=True,
        allow_null=True,
    )
    is_high_value = serializers.SerializerMethodField()

    class Meta:
        model = ProjectVariationOrder
        fields = [
            "id",
            "project",
            "project_name",
            "project_risk_rating",
            "variation_number",
            "title",
            "change_summary",
            "reason",
            "status",
            "contract_value",
            "currency",
            "requested_date",
            "due_date",
            "related_document",
            "related_document_number",
            "related_document_title",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
            "is_high_value",
        ]
        read_only_fields = [
            "id",
            "project_name",
            "project_risk_rating",
            "related_document_number",
            "related_document_title",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
            "is_high_value",
        ]
        extra_kwargs = {
            "variation_number": {"required": False, "allow_blank": True},
            "related_document": {"required": False, "allow_null": True},
            "due_date": {"required": False, "allow_null": True},
        }

    def get_is_high_value(self, obj):
        return (obj.contract_value or 0) >= 100000

    def validate_contract_value(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Contract value cannot be negative.")
        return value

    def _generate_variation_number(self, project_id: int) -> str:
        prefix = f"VO-{project_id:03d}"
        sequence = ProjectVariationOrder.objects.filter(project_id=project_id).count() + 1
        while True:
            candidate = f"{prefix}-{sequence:04d}"
            if not ProjectVariationOrder.objects.filter(variation_number=candidate).exists():
                return candidate
            sequence += 1

    def create(self, validated_data):
        request = self.context.get("request")
        if not validated_data.get("variation_number"):
            validated_data["variation_number"] = self._generate_variation_number(
                validated_data["project"].id
            )
        validated_data["created_by"] = getattr(request, "user", None)
        validated_data["updated_by"] = getattr(request, "user", None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        request = self.context.get("request")
        if (
            "variation_number" in validated_data
            and not validated_data.get("variation_number")
        ):
            validated_data["variation_number"] = instance.variation_number
        validated_data["updated_by"] = getattr(request, "user", None)
        return super().update(instance, validated_data)


class ProjectWorkforceLogSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    employee_name = serializers.SerializerMethodField()
    contractor_name = serializers.CharField(source="contractor.name", read_only=True)
    task_assigned_name = serializers.CharField(source="task_assigned.name", read_only=True)
    hr_employment_status = serializers.CharField(source="employee.employment_status", read_only=True)
    payroll_status = serializers.SerializerMethodField()
    latest_payslip_period_end = serializers.SerializerMethodField()
    latest_payslip_net_salary = serializers.SerializerMethodField()
    safety_training_status = serializers.SerializerMethodField()
    total_headcount = serializers.SerializerMethodField()

    class Meta:
        model = ProjectWorkforceLog
        fields = [
            "id",
            "project",
            "project_name",
            "worker_id",
            "employee",
            "employee_name",
            "trade",
            "contractor",
            "contractor_name",
            "report_date",
            "daily_attendance",
            "shift",
            "task_assigned",
            "task_assigned_name",
            "productivity",
            "overtime_hours",
            "laborers_count",
            "skilled_count",
            "supervisors_count",
            "subcontractors_count",
            "equipment_operators_count",
            "notes",
            "hr_employment_status",
            "payroll_status",
            "latest_payslip_period_end",
            "latest_payslip_net_salary",
            "safety_training_status",
            "total_headcount",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "project_name",
            "employee_name",
            "contractor_name",
            "task_assigned_name",
            "hr_employment_status",
            "payroll_status",
            "latest_payslip_period_end",
            "latest_payslip_net_salary",
            "safety_training_status",
            "total_headcount",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]

    def get_employee_name(self, obj):
        if not obj.employee_id or not getattr(obj.employee, "user", None):
            return None
        full_name = obj.employee.user.get_full_name()
        return full_name or getattr(obj.employee.user, "username", None)

    def _latest_payslip(self, obj):
        cache_attr = "_latest_project_workforce_payslip"
        if hasattr(obj, cache_attr):
            return getattr(obj, cache_attr)
        if not obj.employee_id:
            setattr(obj, cache_attr, None)
            return None
        payslip = (
            Payslip.objects.filter(
                organization_id=obj.organization_id,
                employee_id=obj.employee_id,
            )
            .order_by("-period_end", "-created_at", "-id")
            .first()
        )
        setattr(obj, cache_attr, payslip)
        return payslip

    def get_payroll_status(self, obj):
        if not obj.employee_id:
            return "not_linked"
        return "synced" if self._latest_payslip(obj) else "pending"

    def get_latest_payslip_period_end(self, obj):
        payslip = self._latest_payslip(obj)
        return payslip.period_end if payslip else None

    def get_latest_payslip_net_salary(self, obj):
        payslip = self._latest_payslip(obj)
        return str(payslip.net_salary) if payslip else None

    def get_safety_training_status(self, obj):
        if not obj.employee_id:
            return "not_linked"
        completed_safety_induction = OrientationChecklistItem.objects.filter(
            organization_id=obj.organization_id,
            employee_id=obj.employee_id,
            category=OrientationChecklistItem.Category.SAFETY_TRAINING,
            is_completed=True,
        ).exists()
        completed_safety_training = TrainingCompletion.objects.filter(
            organization_id=obj.organization_id,
            employee_id=obj.employee_id,
            result__in=[
                TrainingCompletion.Result.PASS,
                TrainingCompletion.Result.DISTINCTION,
            ],
        ).filter(
            Q(course__title__icontains="safety")
            | Q(enrollment__course__title__icontains="safety")
        ).exists() or TrainingRecord.objects.filter(
            organization_id=obj.organization_id,
            employee_id=obj.employee_id,
            status=TrainingRecord.Status.COMPLETED,
            title__icontains="safety",
        ).exists()
        return "compliant" if (completed_safety_induction or completed_safety_training) else "pending"

    def get_total_headcount(self, obj):
        return (
            obj.laborers_count
            + obj.skilled_count
            + obj.supervisors_count
            + obj.subcontractors_count
            + obj.equipment_operators_count
        )

    def validate(self, attrs):
        project = attrs.get("project", getattr(self.instance, "project", None))
        employee = attrs.get("employee", getattr(self.instance, "employee", None))
        contractor = attrs.get("contractor", getattr(self.instance, "contractor", None))
        task_assigned = attrs.get("task_assigned", getattr(self.instance, "task_assigned", None))

        errors = {}
        if project and employee and employee.organization_id != project.organization_id:
            errors["employee"] = "Selected HR employee must belong to the project organization."

        if project and contractor and contractor.organization_id != project.organization_id:
            errors["contractor"] = "Selected contractor must belong to the project organization."

        if project and task_assigned:
            if task_assigned.organization_id != project.organization_id:
                errors["task_assigned"] = "Selected task must belong to the project organization."
            elif not task_assigned.phase_id or task_assigned.phase.project_id != project.id:
                errors["task_assigned"] = "Selected task must belong to the selected project."

        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class ProjectDailySiteReportPhotoSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ProjectDailySiteReportPhoto
        fields = [
            "id",
            "report",
            "image",
            "image_url",
            "caption",
            "taken_at",
            "uploaded_by",
            "created_at",
        ]
        read_only_fields = ["id", "report", "image_url", "uploaded_by", "created_at"]

    def validate_image(self, value):
        from config.upload_validators import validate_upload
        return validate_upload(value, kind="image")

    def get_image_url(self, obj):
        if not obj.image:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url


class ProjectSupportingAttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = ProjectSupportingAttachment
        fields = [
            "id",
            "project",
            "variation",
            "phase",
            "milestone",
            "task",
            "cost_entry",
            "risk_entry",
            "workforce_log",
            "site_report",
            "quality_inspection",
            "escalation",
            "file",
            "file_url",
            "caption",
            "uploaded_by",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "project",
            "variation",
            "phase",
            "milestone",
            "task",
            "cost_entry",
            "risk_entry",
            "workforce_log",
            "site_report",
            "quality_inspection",
            "escalation",
            "file_url",
            "uploaded_by",
            "created_at",
        ]

    def validate_file(self, value):
        from config.upload_validators import validate_upload
        return validate_upload(value, kind="any")

    def get_file_url(self, obj):
        if not obj.file:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url


class ProjectDailySiteReportSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    photo_count = serializers.SerializerMethodField()
    photos = ProjectDailySiteReportPhotoSerializer(many=True, read_only=True)

    class Meta:
        model = ProjectDailySiteReport
        fields = [
            "id",
            "project",
            "project_name",
            "report_date",
            "shift",
            "weather",
            "weather_notes",
            "weather_delay_hours",
            "progress_percent",
            "laborers_count",
            "skilled_count",
            "supervisors_count",
            "subcontractors_count",
            "equipment_operators_count",
            "workforce_summary",
            "work_completed",
            "planned_next_day",
            "equipment_used",
            "materials_delivered",
            "materials_consumed",
            "material_updates",
            "visitors_log",
            "instructions_issued",
            "safety_observations",
            "quality_observations",
            "incidents",
            "blockers",
            "status",
            "escalation_required",
            "submitted_by",
            "reviewed_by",
            "reviewed_at",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
            "photo_count",
            "photos",
        ]
        read_only_fields = [
            "id",
            "project_name",
            "submitted_by",
            "reviewed_by",
            "reviewed_at",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
            "photo_count",
            "photos",
        ]

    def get_photo_count(self, obj):
        return obj.photos.count()


class ProjectDeliveryConfirmationSerializer(serializers.ModelSerializer):
    project = serializers.IntegerField(source="purchase_order.project_id", read_only=True)
    project_name = serializers.CharField(
        source="purchase_order.project.name",
        read_only=True,
        allow_null=True,
    )
    purchase_order = serializers.IntegerField(source="purchase_order_id", read_only=True)
    po_number = serializers.CharField(source="purchase_order.po_number", read_only=True)
    vendor = serializers.IntegerField(source="purchase_order.vendor_id", read_only=True)
    vendor_name = serializers.CharField(source="purchase_order.vendor.name", read_only=True)
    expected_delivery_date = serializers.DateField(
        source="purchase_order.expected_delivery_date",
        read_only=True,
        allow_null=True,
    )
    item_count = serializers.IntegerField(read_only=True)
    accepted_quantity = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    rejected_quantity = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    is_late = serializers.SerializerMethodField()
    delay_days = serializers.SerializerMethodField()

    class Meta:
        model = GoodsReceipt
        fields = [
            "id",
            "grn_number",
            "project",
            "project_name",
            "purchase_order",
            "po_number",
            "vendor",
            "vendor_name",
            "status",
            "received_date",
            "expected_delivery_date",
            "received_by",
            "delivery_note_number",
            "inspection_notes",
            "notes",
            "item_count",
            "accepted_quantity",
            "rejected_quantity",
            "is_late",
            "delay_days",
            "created_at",
        ]
        read_only_fields = fields

    def get_is_late(self, obj):
        expected_date = getattr(obj.purchase_order, "expected_delivery_date", None)
        if not expected_date:
            return False
        return obj.received_date > expected_date

    def get_delay_days(self, obj):
        expected_date = getattr(obj.purchase_order, "expected_delivery_date", None)
        if not expected_date or obj.received_date <= expected_date:
            return 0
        return (obj.received_date - expected_date).days


class ProjectFieldEscalationSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    source_report_date = serializers.DateField(source="source_report.report_date", read_only=True)
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = ProjectFieldEscalation
        fields = [
            "id",
            "project",
            "project_name",
            "source_report",
            "source_report_date",
            "issue_date",
            "issue_category",
            "issue_type",
            "location",
            "weather_condition",
            "weather_delay_hours",
            "estimated_schedule_impact_days",
            "estimated_cost_impact",
            "impact_summary",
            "root_cause",
            "immediate_action",
            "title",
            "description",
            "severity",
            "status",
            "owner_name",
            "due_date",
            "resolved_at",
            "resolution_notes",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
            "is_overdue",
        ]
        read_only_fields = [
            "id",
            "project_name",
            "source_report_date",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
            "is_overdue",
        ]

    def get_is_overdue(self, obj):
        if not obj.due_date:
            return False
        if obj.status in (
            ProjectFieldEscalation.Status.RESOLVED,
            ProjectFieldEscalation.Status.CLOSED,
        ):
            return False
        return obj.due_date < date.today()


class ProjectExecutionInspectionItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectExecutionInspectionItem
        fields = [
            "id",
            "inspection",
            "sort_order",
            "checklist_group",
            "checklist_item",
            "result",
            "remarks",
            "action_owner",
            "action_due_date",
            "resolved_on",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "inspection", "created_at", "updated_at"]


class ProjectExecutionInspectionSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    phase_name = serializers.CharField(source="phase.name", read_only=True, allow_null=True)
    source_report_date = serializers.DateField(source="source_report.report_date", read_only=True)
    checklist_items = ProjectExecutionInspectionItemSerializer(many=True, required=False)
    failed_items_count = serializers.SerializerMethodField()
    pending_actions_count = serializers.SerializerMethodField()

    class Meta:
        model = ProjectExecutionInspection
        fields = [
            "id",
            "project",
            "project_name",
            "phase",
            "phase_name",
            "source_report",
            "source_report_date",
            "inspection_number",
            "inspection_type",
            "status",
            "inspected_on",
            "shift",
            "work_package",
            "location",
            "inspector_name",
            "inspector_role",
            "overall_score",
            "critical_findings",
            "major_findings",
            "minor_findings",
            "observations",
            "corrective_actions",
            "due_date",
            "closed_at",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
            "checklist_items",
            "failed_items_count",
            "pending_actions_count",
        ]
        read_only_fields = [
            "id",
            "project_name",
            "phase_name",
            "source_report_date",
            "inspection_number",
            "closed_at",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
            "failed_items_count",
            "pending_actions_count",
        ]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        project = attrs.get("project", getattr(self.instance, "project", None))
        phase = attrs.get("phase", getattr(self.instance, "phase", None))
        source_report = attrs.get(
            "source_report",
            getattr(self.instance, "source_report", None),
        )

        if project and phase and phase.project_id != project.id:
            raise serializers.ValidationError(
                {"phase": "Selected phase does not belong to selected project."}
            )

        if project and source_report and source_report.project_id != project.id:
            raise serializers.ValidationError(
                {"source_report": "Selected site report does not belong to selected project."}
            )

        return attrs

    def create(self, validated_data):
        checklist_items_data = validated_data.pop("checklist_items", [])
        inspection = super().create(validated_data)
        self._replace_checklist_items(inspection, checklist_items_data)
        return inspection

    def update(self, instance, validated_data):
        checklist_items_data = validated_data.pop("checklist_items", None)
        inspection = super().update(instance, validated_data)
        if checklist_items_data is not None:
            self._replace_checklist_items(inspection, checklist_items_data)
        return inspection

    def _replace_checklist_items(self, inspection, checklist_items_data):
        inspection.checklist_items.all().delete()
        rows = []
        for index, row in enumerate(checklist_items_data, start=1):
            checklist_item = (row.get("checklist_item") or "").strip()
            if not checklist_item:
                continue
            rows.append(
                ProjectExecutionInspectionItem(
                    inspection=inspection,
                    sort_order=row.get("sort_order", index - 1),
                    checklist_group=(row.get("checklist_group") or "").strip(),
                    checklist_item=checklist_item,
                    result=row.get("result", ProjectExecutionInspectionItem.Result.PASS),
                    remarks=(row.get("remarks") or "").strip(),
                    action_owner=(row.get("action_owner") or "").strip(),
                    action_due_date=row.get("action_due_date"),
                    resolved_on=row.get("resolved_on"),
                )
            )
        if rows:
            ProjectExecutionInspectionItem.objects.bulk_create(rows)

    def get_failed_items_count(self, obj):
        return obj.checklist_items.filter(
            result=ProjectExecutionInspectionItem.Result.FAIL
        ).count()

    def get_pending_actions_count(self, obj):
        return obj.checklist_items.filter(
            result__in=[
                ProjectExecutionInspectionItem.Result.FAIL,
                ProjectExecutionInspectionItem.Result.HOLD,
            ],
            resolved_on__isnull=True,
        ).count()


# --- Project split serializers ---

class ProjectListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""

    property_name = serializers.SerializerMethodField()
    phase_count = serializers.IntegerField(read_only=True, default=0)
    progress = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "id", "name", "property", "property_name", "status",
            "project_type", "number_of_units",
            "location", "gps_latitude", "gps_longitude",
            "spv_entity", "land_status",
            "risk_rating",
            "compliance_score",
            "compliance_status",
            "compliance_last_evaluated_at",
            "start_date", "target_end_date", "actual_end_date",
            "budget", "target_irr", "project_manager", "description",
            "created_at", "updated_at",
            "phase_count", "progress",
        ]

    def get_progress(self, obj):
        phases = obj.phases.all()
        return compute_progress(phases)

    def get_property_name(self, obj):
        return obj.property.name if obj.property else None


class ProjectDetailSerializer(serializers.ModelSerializer):
    """Full detail with nested phases."""

    property_name = serializers.SerializerMethodField()
    ownership_allocations = serializers.SerializerMethodField()
    phases = ProjectPhaseSerializer(many=True, read_only=True)
    progress = serializers.SerializerMethodField()
    total_planned_budget = serializers.SerializerMethodField()
    total_actual_cost = serializers.SerializerMethodField()
    total_budget_variance = serializers.SerializerMethodField()
    map_available = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = "__all__"
        read_only_fields = ("id", "organization", "created_at", "updated_at")

    def get_map_available(self, obj):
        from apps.settings.quotas import is_entity_map_available

        if not obj.gps_latitude or not obj.gps_longitude:
            return False
        return is_entity_map_available(obj.organization, obj)

    def get_progress(self, obj):
        return compute_progress(obj.phases.all())

    def get_property_name(self, obj):
        return obj.property.name if obj.property else None

    def get_total_planned_budget(self, obj):
        total = sum(p.planned_budget or 0 for p in obj.phases.all())
        return str(total)

    def get_total_actual_cost(self, obj):
        total = sum(
            getattr(p, "cost_total", p.actual_cost) or 0
            for p in obj.phases.all()
        )
        return str(total)

    def get_total_budget_variance(self, obj):
        planned = sum(p.planned_budget or 0 for p in obj.phases.all())
        actual = sum(
            getattr(p, "cost_total", p.actual_cost) or 0
            for p in obj.phases.all()
        )
        return str(planned - actual)

    def get_ownership_allocations(self, obj):
        allocations = (
            obj.investors.select_related("investor")
            .order_by("sort_order", "id")
        )
        return [
            {
                "investor_id": item.investor_id,
                "party_name": item.investor.name,
                "ownership_percentage": str(item.ownership_percentage),
                "capital_committed": str(item.capital_committed),
                "capital_contributed": str(item.capital_contributed),
                "sort_order": item.sort_order,
                "notes": item.notes,
            }
            for item in allocations
        ]


class ProjectOwnershipAllocationInputSerializer(serializers.Serializer):
    investor_id = serializers.IntegerField(required=False, min_value=1)
    party_name = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=255,
    )
    ownership_percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal("0.01"),
        max_value=Decimal("100.00"),
    )
    capital_committed = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        required=False,
        min_value=Decimal("0.00"),
    )
    capital_contributed = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        required=False,
        min_value=Decimal("0.00"),
    )
    sort_order = serializers.IntegerField(required=False, min_value=0)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        party_name = (attrs.get("party_name") or "").strip()
        if not attrs.get("investor_id") and not party_name:
            raise serializers.ValidationError(
                "Each ownership row must include either investor_id or party_name.",
            )
        attrs["party_name"] = party_name

        capital_committed = attrs.get("capital_committed")
        capital_contributed = attrs.get("capital_contributed")
        if (
            capital_committed is not None
            and capital_contributed is not None
            and capital_contributed > capital_committed
        ):
            raise serializers.ValidationError(
                "capital_contributed cannot be greater than capital_committed.",
            )
        return attrs


class ProjectWriteSerializer(serializers.ModelSerializer):
    """Flat writes for create/update."""

    ownership_allocations = ProjectOwnershipAllocationInputSerializer(
        many=True,
        required=False,
        write_only=True,
    )
    template_id = serializers.IntegerField(
        required=False,
        write_only=True,
        allow_null=True,
        help_text="Project template ID to instantiate from.",
    )

    class Meta:
        model = Project
        fields = [
            "id", "property", "name", "description", "status", "project_type",
            "number_of_units",
            "location", "gps_latitude", "gps_longitude",
            "spv_entity", "ownership_structure", "land_status",
            "ownership_allocations",
            "template_id",
            "start_date", "target_end_date", "actual_end_date",
            "land_acquisition_date", "permit_approval_date", "construction_start_date",
            "budget", "target_irr", "risk_rating",
            "project_manager", "raci_summary",
        ]
        read_only_fields = ("id",)
        extra_kwargs = {
            "property": {"required": False, "allow_null": True},
        }

    def validate_budget(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Budget cannot be negative.")
        return value

    def validate_ownership_structure(self, value):
        return (value or "").strip()

    def validate_ownership_allocations(self, value):
        seen = set()
        total = Decimal("0.00")
        for idx, row in enumerate(value):
            investor_id = row.get("investor_id")
            party_name = row.get("party_name", "")
            identity_key = (
                f"id:{investor_id}"
                if investor_id
                else f"name:{party_name.lower()}"
            )
            if identity_key in seen:
                raise serializers.ValidationError(
                    f"Duplicate ownership party in row {idx + 1}.",
                )
            seen.add(identity_key)
            total += row["ownership_percentage"]

        if total > Decimal("100.00"):
            raise serializers.ValidationError(
                "Total ownership allocation cannot exceed 100%.",
            )
        return value

    def create(self, validated_data):
        ownership_allocations = validated_data.pop("ownership_allocations", None)
        template_id = validated_data.pop("template_id", None)
        with transaction.atomic():
            project = super().create(validated_data)
            if ownership_allocations is not None:
                self._sync_ownership_allocations(project, ownership_allocations)
            if template_id:
                from apps.projects.template_instantiation import instantiate_project_from_template

                transaction.on_commit(
                    lambda: instantiate_project_from_template(project, template_id)
                )
        return project

    def update(self, instance, validated_data):
        ownership_allocations = validated_data.pop("ownership_allocations", None)
        with transaction.atomic():
            project = super().update(instance, validated_data)
            if ownership_allocations is not None:
                self._sync_ownership_allocations(project, ownership_allocations)
        return project

    def _sync_ownership_allocations(self, project, allocations):
        from apps.finance.models import Investor, ProjectInvestor

        org = project.organization
        if org is None:
            raise serializers.ValidationError(
                {"ownership_allocations": "Project organization is required."},
            )

        active_investor_ids = []
        summary_parts = []

        for idx, allocation in enumerate(allocations):
            investor_id = allocation.get("investor_id")
            party_name = (allocation.get("party_name") or "").strip()
            investor = None

            if investor_id:
                investor = Investor.objects.filter(
                    id=investor_id,
                    organization=org,
                ).first()
                if investor is None:
                    raise serializers.ValidationError(
                        {
                            "ownership_allocations": (
                                f"Investor {investor_id} in row {idx + 1} "
                                "was not found in this organization."
                            ),
                        },
                    )

            if investor is None:
                investor, _ = Investor.objects.get_or_create(
                    organization=org,
                    name=party_name,
                    defaults={"investor_type": Investor.InvestorType.JV_PARTNER},
                )

            project_investor, created = ProjectInvestor.objects.get_or_create(
                organization=org,
                project=project,
                investor=investor,
                defaults={
                    "ownership_percentage": allocation["ownership_percentage"],
                    "sort_order": allocation.get("sort_order", idx),
                    "capital_committed": allocation.get(
                        "capital_committed",
                        Decimal("0.00"),
                    ),
                    "capital_contributed": allocation.get(
                        "capital_contributed",
                        Decimal("0.00"),
                    ),
                    "notes": (allocation.get("notes") or "").strip(),
                },
            )
            if not created:
                project_investor.ownership_percentage = allocation["ownership_percentage"]
                project_investor.sort_order = allocation.get("sort_order", idx)
                if "capital_committed" in allocation:
                    project_investor.capital_committed = allocation["capital_committed"]
                if "capital_contributed" in allocation:
                    project_investor.capital_contributed = allocation["capital_contributed"]
                if "notes" in allocation:
                    project_investor.notes = (allocation.get("notes") or "").strip()
                project_investor.save()

            active_investor_ids.append(investor.id)
            summary_parts.append(
                f"{investor.name}: {project_investor.ownership_percentage}%",
            )

        existing_allocations = ProjectInvestor.objects.filter(
            organization=org,
            project=project,
        )
        if active_investor_ids:
            existing_allocations.exclude(investor_id__in=active_investor_ids).delete()
        else:
            existing_allocations.delete()

        derived_summary = "; ".join(summary_parts)
        if project.ownership_structure != derived_summary:
            Project.objects.filter(pk=project.pk).update(
                ownership_structure=derived_summary,
            )
            project.ownership_structure = derived_summary


class ProjectRiskRegisterListSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    risk_category_name = serializers.CharField(source="risk_category.name", read_only=True, allow_null=True)
    risk_category_type_display = serializers.CharField(
        source="risk_category.get_category_type_display", read_only=True, allow_null=True
    )
    owner_role_name = serializers.CharField(source="owner_role.name", read_only=True, allow_null=True)
    severity_display = serializers.CharField(source="get_severity_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    treatment_display = serializers.CharField(source="get_treatment_display", read_only=True)
    created_by_name = serializers.CharField(source="created_by.get_full_name", read_only=True, allow_null=True)
    updated_by_name = serializers.CharField(source="updated_by.get_full_name", read_only=True, allow_null=True)

    class Meta:
        model = ProjectRiskRegisterEntry
        fields = [
            "id",
            "project",
            "project_name",
            "title",
            "description",
            "risk_category",
            "risk_category_name",
            "risk_category_type_display",
            "likelihood_key",
            "likelihood_score",
            "impact_key",
            "impact_score",
            "risk_score",
            "severity",
            "severity_display",
            "status",
            "status_display",
            "treatment",
            "treatment_display",
            "mitigation_plan",
            "mitigation_actions",
            "contingency_plan",
            "owner_role",
            "owner_role_name",
            "response_time_hours",
            "escalation_required",
            "identified_on",
            "target_resolution_date",
            "last_reviewed_on",
            "resolved_on",
            "created_by",
            "created_by_name",
            "updated_by",
            "updated_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "project_name",
            "risk_category_name",
            "risk_category_type_display",
            "owner_role_name",
            "likelihood_score",
            "impact_score",
            "risk_score",
            "severity",
            "severity_display",
            "status_display",
            "treatment_display",
            "created_by",
            "created_by_name",
            "updated_by",
            "updated_by_name",
            "resolved_on",
            "created_at",
            "updated_at",
        ]


class ProjectRiskRegisterWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectRiskRegisterEntry
        fields = [
            "project",
            "title",
            "description",
            "risk_category",
            "likelihood_key",
            "impact_key",
            "status",
            "treatment",
            "mitigation_plan",
            "mitigation_actions",
            "contingency_plan",
            "owner_role",
            "response_time_hours",
            "escalation_required",
            "identified_on",
            "target_resolution_date",
            "last_reviewed_on",
        ]
        extra_kwargs = {
            "mitigation_plan": {"required": False, "allow_blank": True},
            "mitigation_actions": {"required": False, "allow_blank": True},
            "contingency_plan": {"required": False, "allow_blank": True},
            "owner_role": {"required": False, "allow_null": True},
            "response_time_hours": {"required": False, "allow_null": True},
            "identified_on": {"required": False},
            "target_resolution_date": {"required": False, "allow_null": True},
            "last_reviewed_on": {"required": False, "allow_null": True},
        }

    def validate(self, attrs):
        request = self.context.get("request")
        organization = _resolve_org_from_request(request)
        matrix_config = _matrix_config_for_org(organization)

        likelihood_key = attrs.get(
            "likelihood_key",
            getattr(self.instance, "likelihood_key", "medium"),
        )
        impact_key = attrs.get(
            "impact_key",
            getattr(self.instance, "impact_key", "medium"),
        )
        likelihood_score, impact_score, risk_score, severity = _calculate_risk_score(
            matrix_config,
            str(likelihood_key),
            str(impact_key),
        )
        attrs["likelihood_score"] = likelihood_score
        attrs["impact_score"] = impact_score
        attrs["risk_score"] = risk_score
        attrs["severity"] = severity

        risk_category = attrs.get("risk_category", getattr(self.instance, "risk_category", None))
        if risk_category and organization and getattr(risk_category, "organization_id", None) != getattr(organization, "id", None):
            raise serializers.ValidationError(
                {"risk_category": "Selected risk category does not belong to your organization."}
            )
        if risk_category and organization:
            mitigation_rule = (
                RiskMitigationRule.objects.filter(
                    organization=organization,
                    risk_category=risk_category,
                    severity=severity,
                    is_active=True,
                )
                .select_related("assign_to_role")
                .order_by("id")
                .first()
            )
            if mitigation_rule:
                if attrs.get("owner_role") is None and not getattr(self.instance, "owner_role", None):
                    attrs["owner_role"] = mitigation_rule.assign_to_role
                if attrs.get("response_time_hours") is None and getattr(self.instance, "response_time_hours", None) is None:
                    attrs["response_time_hours"] = mitigation_rule.response_time_hours
                if "escalation_required" not in attrs:
                    attrs["escalation_required"] = mitigation_rule.escalation_required

        status = attrs.get("status", getattr(self.instance, "status", ProjectRiskRegisterEntry.Status.OPEN))
        if status in (
            ProjectRiskRegisterEntry.Status.MITIGATED,
            ProjectRiskRegisterEntry.Status.ACCEPTED,
            ProjectRiskRegisterEntry.Status.CLOSED,
        ):
            attrs["resolved_on"] = attrs.get("resolved_on") or date.today()
        elif status in (ProjectRiskRegisterEntry.Status.OPEN, ProjectRiskRegisterEntry.Status.IN_PROGRESS):
            attrs["resolved_on"] = None

        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        validated_data["organization"] = _resolve_org_from_request(request)
        validated_data["created_by"] = getattr(request, "user", None)
        validated_data["updated_by"] = getattr(request, "user", None)
        if not validated_data.get("identified_on"):
            validated_data["identified_on"] = date.today()
        return super().create(validated_data)

    def update(self, instance, validated_data):
        request = self.context.get("request")
        validated_data["updated_by"] = getattr(request, "user", None)
        return super().update(instance, validated_data)


class ProjectPlanningInsightSerializer(serializers.ModelSerializer):
    insight_type_display = serializers.CharField(source="get_insight_type_display", read_only=True)
    source_module_display = serializers.CharField(source="get_source_module_display", read_only=True)

    class Meta:
        model = ProjectPlanningInsight
        fields = [
            "id",
            "organization",
            "source_module",
            "source_module_display",
            "insight_type",
            "insight_type_display",
            "area_name",
            "title",
            "summary",
            "demand_share_percent",
            "lead_count",
            "qualified_lead_count",
            "won_lead_count",
            "window_days",
            "threshold_percent",
            "is_active",
            "metadata",
            "first_triggered_at",
            "last_triggered_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Equipment & Machinery
# ---------------------------------------------------------------------------


class EquipmentMaintenanceLogSerializer(serializers.ModelSerializer):
    log_type_display = serializers.CharField(source="get_log_type_display", read_only=True)

    class Meta:
        model = EquipmentMaintenanceLog
        fields = [
            "id", "equipment", "log_type", "log_type_display",
            "date", "description", "parts_replaced", "cost",
            "performed_by", "hour_meter_at_service", "downtime_hours",
            "created_at",
        ]
        read_only_fields = ("id", "created_at")


class EquipmentDeploymentLogSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)

    class Meta:
        model = EquipmentDeploymentLog
        fields = [
            "id", "equipment", "project", "project_name",
            "site_name", "operator", "deployed_date", "returned_date",
            "hours_used", "notes", "created_at",
        ]
        read_only_fields = ("id", "created_at")


class ProjectEquipmentListSerializer(serializers.ModelSerializer):
    equipment_type_display = serializers.CharField(source="get_equipment_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    ownership_display = serializers.CharField(source="get_ownership_display", read_only=True)
    current_project_name = serializers.CharField(source="current_project.name", read_only=True, default=None)
    maintenance_due = serializers.SerializerMethodField()

    class Meta:
        model = ProjectEquipment
        fields = [
            "id", "asset_id", "name", "equipment_type", "equipment_type_display",
            "status", "status_display", "make", "model_name",
            "current_project", "current_project_name", "current_location",
            "ownership", "ownership_display",
            "last_service_date", "next_service_due", "maintenance_due",
            "current_book_value", "internal_daily_rate",
            "created_at", "updated_at",
        ]

    def get_maintenance_due(self, obj) -> bool:
        if not obj.next_service_due:
            return False
        return obj.next_service_due <= date.today()


class ProjectEquipmentDetailSerializer(serializers.ModelSerializer):
    equipment_type_display = serializers.CharField(source="get_equipment_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    fuel_type_display = serializers.CharField(source="get_fuel_type_display", read_only=True)
    ownership_display = serializers.CharField(source="get_ownership_display", read_only=True)
    current_project_name = serializers.CharField(source="current_project.name", read_only=True, default=None)
    maintenance_logs = EquipmentMaintenanceLogSerializer(many=True, read_only=True)
    deployment_logs = EquipmentDeploymentLogSerializer(many=True, read_only=True)
    maintenance_due = serializers.SerializerMethodField()

    class Meta:
        model = ProjectEquipment
        fields = "__all__"
        read_only_fields = ("id", "asset_id", "created_at", "updated_at")

    def get_maintenance_due(self, obj) -> bool:
        if not obj.next_service_due:
            return False
        return obj.next_service_due <= date.today()


class ProjectEquipmentWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectEquipment
        fields = "__all__"
        read_only_fields = ("id", "asset_id", "organization", "created_at", "updated_at")


# ── Quality Control ──────────────────────────────────────────────────


class QualityCheckTemplateSerializer(serializers.ModelSerializer):
    evidence_type_display = serializers.CharField(
        source="get_evidence_type_display", read_only=True,
    )

    class Meta:
        model = QualityCheckTemplate
        fields = (
            "id", "quality_plan", "check_id", "inspection_point",
            "requirement_standard", "evidence_type", "evidence_type_display",
            "is_critical", "sort_order", "created_at", "updated_at",
        )
        read_only_fields = ("id", "check_id", "quality_plan", "created_at", "updated_at")


class QualityPlanListSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True, default=None)
    approval_status_display = serializers.CharField(
        source="get_approval_status_display", read_only=True,
    )
    review_cycle_display = serializers.CharField(
        source="get_review_cycle_display", read_only=True,
    )
    check_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = QualityPlan
        fields = (
            "id", "plan_number", "name", "project", "project_name",
            "compliance_standards", "review_cycle", "review_cycle_display",
            "approval_status", "approval_status_display",
            "approved_by", "approved_date", "next_review_date",
            "revision", "check_count", "created_at", "updated_at",
        )


class QualityPlanDetailSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True, default=None)
    approval_status_display = serializers.CharField(
        source="get_approval_status_display", read_only=True,
    )
    review_cycle_display = serializers.CharField(
        source="get_review_cycle_display", read_only=True,
    )
    check_templates = QualityCheckTemplateSerializer(many=True, read_only=True)

    class Meta:
        model = QualityPlan
        fields = (
            "id", "plan_number", "name", "description", "project", "project_name",
            "compliance_standards", "review_cycle", "review_cycle_display",
            "approval_status", "approval_status_display",
            "approved_by", "approved_date", "next_review_date",
            "revision", "notes", "check_templates",
            "created_by", "created_at", "updated_at",
        )


class QualityPlanWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = QualityPlan
        fields = (
            "name", "description", "project", "compliance_standards",
            "review_cycle", "approval_status", "approved_by", "approved_date",
            "next_review_date", "revision", "notes",
        )


class NonConformanceReportListSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    inspection_number = serializers.CharField(
        source="inspection.inspection_number", read_only=True, default=None,
    )
    severity_display = serializers.CharField(source="get_severity_display", read_only=True)
    root_cause_display = serializers.CharField(source="get_root_cause_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = NonConformanceReport
        fields = (
            "id", "ncr_number", "title", "project", "project_name",
            "inspection", "inspection_number",
            "severity", "severity_display",
            "root_cause", "root_cause_display",
            "status", "status_display",
            "location", "raised_by", "raised_date",
            "assigned_to", "rectification_due_date",
            "cost_impact", "schedule_impact_days",
            "created_at", "updated_at",
        )


class NonConformanceReportDetailSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    inspection_number = serializers.CharField(
        source="inspection.inspection_number", read_only=True, default=None,
    )
    severity_display = serializers.CharField(source="get_severity_display", read_only=True)
    root_cause_display = serializers.CharField(source="get_root_cause_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = NonConformanceReport
        fields = "__all__"
        read_only_fields = ("id", "ncr_number", "organization", "created_by", "created_at", "updated_at")


class NonConformanceReportWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = NonConformanceReport
        fields = (
            "project", "inspection", "title", "description",
            "severity", "root_cause", "status",
            "location", "raised_by", "assigned_to",
            "rectification_plan", "rectification_due_date",
            "rectification_completed_date",
            "verification_notes", "verified_by", "closed_date",
            "cost_impact", "schedule_impact_days", "notes",
        )


# ── Project Pipeline ─────────────────────────────────────────────────


class PipelineOpportunityListSerializer(serializers.ModelSerializer):
    stage_display = serializers.CharField(source="get_stage_display", read_only=True)
    development_type_display = serializers.CharField(source="get_development_type_display", read_only=True)
    ic_decision_display = serializers.CharField(source="get_ic_decision_display", read_only=True)
    meets_hurdle = serializers.BooleanField(read_only=True)
    profit = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    project_name = serializers.CharField(source="project.name", read_only=True, default=None)

    class Meta:
        model = PipelineOpportunity
        fields = (
            "id", "pipeline_ref", "name", "location", "description",
            "stage", "stage_display", "stage_order",
            "development_type", "development_type_display",
            "land_size_sqm", "land_cost", "land_status",
            "estimated_gdv", "estimated_cost", "expected_irr", "hurdle_rate",
            "expected_margin_pct", "number_of_units",
            "meets_hurdle", "profit",
            "ic_decision", "ic_decision_display",
            "project", "project_name",
            "identified_date", "target_start_date",
            "created_at", "updated_at",
        )


class PipelineOpportunityDetailSerializer(serializers.ModelSerializer):
    stage_display = serializers.CharField(source="get_stage_display", read_only=True)
    development_type_display = serializers.CharField(source="get_development_type_display", read_only=True)
    ic_decision_display = serializers.CharField(source="get_ic_decision_display", read_only=True)
    meets_hurdle = serializers.BooleanField(read_only=True)
    profit = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    project_name = serializers.CharField(source="project.name", read_only=True, default=None)

    class Meta:
        model = PipelineOpportunity
        fields = "__all__"
        read_only_fields = ("id", "pipeline_ref", "organization", "expected_margin_pct", "created_by", "created_at", "updated_at")


class PipelineOpportunityWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PipelineOpportunity
        fields = (
            "name", "location", "gps_coordinates", "description",
            "stage", "stage_order", "development_type",
            "land_size_sqm", "land_cost", "land_status",
            "estimated_gdv", "estimated_cost", "expected_irr", "hurdle_rate",
            "number_of_units",
            "market_analysis", "feasibility_notes",
            "ic_decision", "ic_review_date", "ic_conditions", "ic_reviewers",
            "identified_date", "target_start_date", "target_completion_date",
            "project", "notes",
        )


# ── Project Setup ────────────────────────────────────────────────────


class ProjectTeamMemberSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source="get_role_display", read_only=True)
    access_level_display = serializers.CharField(source="get_access_level_display", read_only=True)

    class Meta:
        model = ProjectTeamMember
        fields = (
            "id", "project", "user", "name", "role", "role_display",
            "access_level", "access_level_display",
            "email", "phone", "company", "is_active",
            "assigned_date", "notes",
        )
        read_only_fields = ("id", "assigned_date")


class ProjectSetupConfigSerializer(serializers.ModelSerializer):
    current_step_display = serializers.CharField(source="get_current_step_display", read_only=True)
    pipeline_source_name = serializers.CharField(source="pipeline_source.name", read_only=True, default=None)
    pipeline_source_ref = serializers.CharField(source="pipeline_source.pipeline_ref", read_only=True, default=None)
    project_name = serializers.CharField(source="project.name", read_only=True)
    project_status = serializers.CharField(source="project.status", read_only=True)
    team_members = ProjectTeamMemberSerializer(source="project.team_members", many=True, read_only=True)

    class Meta:
        model = ProjectSetupConfig
        fields = (
            "id", "project", "project_name", "project_status",
            "pipeline_source", "pipeline_source_name", "pipeline_source_ref",
            "current_step", "current_step_display", "is_complete",
            "survey_plan_ref", "certificate_of_occupancy",
            "planned_phases", "boq_initialized", "template_applied", "template_name",
            "notes", "completed_at", "team_members",
            "created_at", "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class ProjectSetupInitSerializer(serializers.Serializer):
    """Used to initialize a project from the setup wizard."""
    pipeline_source = serializers.IntegerField(required=False, allow_null=True)
    name = serializers.CharField(max_length=255)
    project_type = serializers.ChoiceField(choices=Project.ProjectType.choices, default="residential")
    location = serializers.CharField(max_length=500, required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    start_date = serializers.DateField(required=False, allow_null=True)
    target_end_date = serializers.DateField(required=False, allow_null=True)
    budget = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, allow_null=True)
    number_of_units = serializers.IntegerField(required=False, allow_null=True)
    planned_phases = serializers.IntegerField(default=3)
    survey_plan_ref = serializers.CharField(max_length=255, required=False, allow_blank=True)
    certificate_of_occupancy = serializers.CharField(max_length=255, required=False, allow_blank=True)


# ── Feasibility & Viability ──────────────────────────────────────────


class FeasibilityStudyListSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    gdv = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    total_development_cost = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    profit = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    profit_on_cost = serializers.FloatField(read_only=True)
    margin_pct = serializers.FloatField(read_only=True)
    meets_hurdle = serializers.BooleanField(read_only=True)

    class Meta:
        model = FeasibilityStudy
        fields = (
            "id", "study_ref", "version", "project", "project_name",
            "status", "status_display",
            "total_sales_value", "other_income", "gdv",
            "total_development_cost", "profit", "profit_on_cost", "margin_pct",
            "expected_irr", "hurdle_rate", "meets_hurdle",
            "breakeven_units_pct", "sales_velocity",
            "market_risk", "finance_risk", "construction_risk",
            "prepared_by", "created_at", "updated_at",
        )


class FeasibilityStudyDetailSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    gdv = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    total_development_cost = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    profit = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    profit_on_cost = serializers.FloatField(read_only=True)
    margin_pct = serializers.FloatField(read_only=True)
    meets_hurdle = serializers.BooleanField(read_only=True)

    class Meta:
        model = FeasibilityStudy
        fields = "__all__"
        read_only_fields = ("id", "study_ref", "organization", "created_by", "created_at", "updated_at")


class FeasibilityStudyWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeasibilityStudy
        fields = (
            "project", "pipeline_source", "version", "status",
            "total_sales_value", "other_income", "number_of_units",
            "avg_price_per_unit", "avg_price_per_sqm",
            "land_cost", "land_legal_fees", "construction_cost",
            "professional_fees", "professional_fees_pct",
            "marketing_sales_cost", "sales_commission_pct",
            "finance_cost", "contingency", "contingency_pct",
            "target_irr", "expected_irr", "hurdle_rate",
            "breakeven_units_pct", "sales_velocity", "project_duration_months",
            "market_risk", "finance_risk", "construction_risk",
            "demand_analysis", "competitor_projects", "pricing_benchmarks",
            "sensitivity_matrix",
            "prepared_by", "reviewed_by", "notes",
        )


# ── Land Acquisition ────────────────────────────────────────────────


class LandPaymentMilestoneSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = LandPaymentMilestone
        fields = (
            "id", "land_acquisition", "title", "amount", "due_date", "paid_date",
            "status", "status_display", "payment_reference", "recipient",
            "notes", "sort_order", "created_at",
        )
        read_only_fields = ("id", "land_acquisition", "created_at")


class LandAcquisitionListSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    title_type_display = serializers.CharField(source="get_title_type_display", read_only=True)
    verification_status_display = serializers.CharField(source="get_verification_status_display", read_only=True)
    acquisition_status_display = serializers.CharField(source="get_acquisition_status_display", read_only=True)
    total_acquisition_cost = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    balance_remaining = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)

    class Meta:
        model = LandAcquisition
        fields = (
            "id", "parcel_id", "project", "project_name", "location",
            "land_size_sqm", "title_type", "title_type_display",
            "verification_status", "verification_status_display",
            "acquisition_status", "acquisition_status_display",
            "purchase_price", "total_acquisition_cost", "total_paid", "balance_remaining",
            "seller_name", "escrow_secured",
            "created_at", "updated_at",
        )


class LandAcquisitionDetailSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    title_type_display = serializers.CharField(source="get_title_type_display", read_only=True)
    verification_status_display = serializers.CharField(source="get_verification_status_display", read_only=True)
    acquisition_status_display = serializers.CharField(source="get_acquisition_status_display", read_only=True)
    total_acquisition_cost = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    balance_remaining = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    payment_milestones = LandPaymentMilestoneSerializer(many=True, read_only=True)

    class Meta:
        model = LandAcquisition
        fields = "__all__"
        read_only_fields = ("id", "parcel_id", "organization", "created_by", "created_at", "updated_at")


class LandAcquisitionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = LandAcquisition
        fields = (
            "project", "location", "gps_latitude", "gps_longitude",
            "land_size_sqm", "description",
            "title_type", "verification_status", "acquisition_status",
            "survey_plan_ref", "title_document_ref",
            "purchase_price", "agency_fees", "legal_fees", "stamp_duty",
            "registration_fees", "total_paid",
            "land_search_date", "land_search_registry",
            "encumbrance_check", "encumbrance_notes",
            "govt_approval_status", "govt_approval_tracking", "govt_approval_days_elapsed",
            "escrow_holder", "escrow_secured",
            "seller_name", "seller_contact", "notes",
        )


# ── Development Budget ───────────────────────────────────────────────


class DevelopmentBudgetCategorySerializer(serializers.ModelSerializer):
    cost_type_display = serializers.CharField(source="get_cost_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    variance = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    pct_of_tdc = serializers.SerializerMethodField()

    class Meta:
        model = DevelopmentBudgetCategory
        fields = (
            "id", "budget", "name", "cost_type", "cost_type_display",
            "allocated_amount", "actual_amount", "variance",
            "status", "status_display", "pct_of_tdc",
            "sub_items", "sort_order", "notes",
            "created_at", "updated_at",
        )
        read_only_fields = ("id", "budget", "created_at", "updated_at")

    def get_pct_of_tdc(self, obj) -> float:
        budget = obj.budget
        tdc = sum(c.allocated_amount for c in budget.categories.all())
        if tdc and tdc > 0:
            return round(float(obj.allocated_amount) / float(tdc) * 100, 1)
        return 0


class DevelopmentBudgetListSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    total_development_cost = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    cost_per_sqm = serializers.FloatField(read_only=True)
    category_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = DevelopmentBudget
        fields = (
            "id", "project", "project_name", "version",
            "status", "status_display", "is_baseline",
            "total_development_cost", "cost_per_sqm",
            "equity_amount", "debt_amount",
            "total_land_area_sqm", "contingency_pct",
            "category_count", "prepared_by",
            "locked_date", "created_at", "updated_at",
        )


class DevelopmentBudgetDetailSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    total_development_cost = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    cost_per_sqm = serializers.FloatField(read_only=True)
    categories = DevelopmentBudgetCategorySerializer(many=True, read_only=True)

    class Meta:
        model = DevelopmentBudget
        fields = "__all__"
        read_only_fields = ("id", "organization", "created_by", "created_at", "updated_at")


class DevelopmentBudgetWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = DevelopmentBudget
        fields = (
            "id", "project", "version", "status", "is_baseline",
            "equity_amount", "debt_amount",
            "total_land_area_sqm", "contingency_pct",
            "prepared_by", "approved_by", "locked_date", "notes",
        )
        read_only_fields = ("id",)


# ── Project Financing ────────────────────────────────────────────────


class FinancingCovenantSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = FinancingCovenant
        fields = (
            "id", "source", "name", "description", "threshold",
            "current_value", "status", "status_display",
            "last_tested", "next_test_date", "notes",
            "created_at", "updated_at",
        )
        read_only_fields = ("id", "source", "created_at", "updated_at")


class FinancingDrawdownSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = FinancingDrawdown
        fields = (
            "id", "source", "reference", "request_date",
            "amount_requested", "amount_received",
            "status", "status_display", "disbursement_date",
            "milestone_reference", "notes", "created_at",
        )
        read_only_fields = ("id", "source", "created_at")


class FinancingRepaymentSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    total_payment = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)

    class Meta:
        model = FinancingRepayment
        fields = (
            "id", "source", "payment_date",
            "principal_amount", "interest_amount", "total_payment",
            "ending_balance", "status", "status_display",
            "actual_payment_date", "notes", "created_at",
        )
        read_only_fields = ("id", "source", "created_at")


class FinancingSourceListSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    source_type_display = serializers.CharField(source="get_source_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    rate_type_display = serializers.CharField(source="get_rate_type_display", read_only=True)
    available_amount = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)

    class Meta:
        model = FinancingSource
        fields = (
            "id", "reference", "name", "project", "project_name",
            "source_type", "source_type_display",
            "status", "status_display",
            "committed_amount", "drawn_amount", "available_amount",
            "interest_rate", "rate_type", "rate_type_display",
            "tenor_months", "maturity_date", "next_repayment_date",
            "institution", "created_at", "updated_at",
        )


class FinancingSourceDetailSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    source_type_display = serializers.CharField(source="get_source_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    rate_type_display = serializers.CharField(source="get_rate_type_display", read_only=True)
    available_amount = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    drawdowns = FinancingDrawdownSerializer(many=True, read_only=True)
    repayments = FinancingRepaymentSerializer(many=True, read_only=True)
    covenants = FinancingCovenantSerializer(many=True, read_only=True)

    class Meta:
        model = FinancingSource
        fields = "__all__"
        read_only_fields = ("id", "reference", "organization", "created_by", "created_at", "updated_at")


class FinancingSourceWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancingSource
        fields = (
            "project", "name", "source_type", "status",
            "committed_amount", "drawn_amount",
            "interest_rate", "rate_type", "rate_benchmark",
            "arrangement_fee_pct", "grace_period_months",
            "tenor_months", "repayment_frequency",
            "agreement_date", "first_drawdown_date",
            "maturity_date", "next_repayment_date",
            "institution", "contact_person", "contact_email", "notes",
        )


# ── Consultants & Stakeholders ───────────────────────────────────────


class ConsultantPaymentMilestoneSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = ConsultantPaymentMilestone
        fields = (
            "id", "consultant", "description", "amount",
            "trigger_date", "status", "status_display",
            "paid_date", "notes", "sort_order", "created_at",
        )
        read_only_fields = ("id", "consultant", "created_at")


class ConsultantDeliverableSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    format_display = serializers.CharField(source="get_format_display", read_only=True)

    class Meta:
        model = ConsultantDeliverable
        fields = (
            "id", "consultant", "name", "due_date",
            "format", "format_display",
            "status", "status_display",
            "submitted_date", "notes", "sort_order", "created_at",
        )
        read_only_fields = ("id", "consultant", "created_at")


class ConsultantCommunicationLogSerializer(serializers.ModelSerializer):
    entry_type_display = serializers.CharField(source="get_entry_type_display", read_only=True)

    class Meta:
        model = ConsultantCommunicationLog
        fields = (
            "id", "consultant", "entry_type", "entry_type_display",
            "date", "subject", "summary", "attendees",
            "action_items", "logged_by", "created_at",
        )
        read_only_fields = ("id", "consultant", "created_at")


class ProjectConsultantListSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    discipline_display = serializers.CharField(source="get_discipline_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    compliance_status_display = serializers.CharField(source="get_compliance_status_display", read_only=True)
    payment_progress = serializers.FloatField(read_only=True)
    amount_remaining = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)

    class Meta:
        model = ProjectConsultant
        fields = (
            "id", "project", "project_name",
            "firm_name", "contact_person", "contact_role",
            "email", "phone", "whatsapp",
            "discipline", "discipline_display",
            "status", "status_display",
            "contract_value", "amount_paid", "amount_remaining", "payment_progress",
            "compliance_status", "compliance_status_display",
            "insurance_expiry", "license_expiry",
            "contract_start_date", "contract_end_date",
            "created_at", "updated_at",
        )


class ProjectConsultantDetailSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    discipline_display = serializers.CharField(source="get_discipline_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    compliance_status_display = serializers.CharField(source="get_compliance_status_display", read_only=True)
    payment_progress = serializers.FloatField(read_only=True)
    amount_remaining = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    payment_milestones = ConsultantPaymentMilestoneSerializer(many=True, read_only=True)
    deliverables = ConsultantDeliverableSerializer(many=True, read_only=True)
    communication_logs = ConsultantCommunicationLogSerializer(many=True, read_only=True)

    class Meta:
        model = ProjectConsultant
        fields = "__all__"
        read_only_fields = ("id", "organization", "created_by", "created_at", "updated_at")


class ProjectConsultantWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectConsultant
        fields = (
            "project", "firm_name", "contact_person", "contact_role",
            "email", "phone", "whatsapp", "address",
            "discipline", "status",
            "scope_of_work", "contract_value", "amount_paid",
            "contract_start_date", "contract_end_date",
            "compliance_status", "insurance_policy", "insurance_expiry",
            "license_number", "license_expiry",
            "reports_to", "collaborates_with", "notes",
        )


# ── Approvals & Permits ──────────────────────────────────────────────


class PermitSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PermitSubmission
        fields = (
            "id", "permit", "version", "description",
            "documents_list", "submission_date", "submitted_by",
            "authority_receipt_ref", "notes", "created_at",
        )
        read_only_fields = ("id", "permit", "created_at")


class PermitQuerySerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = PermitQuery
        fields = (
            "id", "permit", "query_date", "subject", "description",
            "assigned_consultant", "response", "response_date",
            "status", "status_display", "notes", "created_at",
        )
        read_only_fields = ("id", "permit", "created_at")


class ProjectPermitListSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    permit_type_display = serializers.CharField(source="get_permit_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    is_delayed = serializers.BooleanField(read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)
    depends_on_name = serializers.CharField(source="depends_on.name", read_only=True, default=None)

    class Meta:
        model = ProjectPermit
        fields = (
            "id", "reference", "name", "project", "project_name",
            "permit_type", "permit_type_display",
            "status", "status_display", "is_critical_path", "is_delayed",
            "authority_name", "application_date",
            "expected_approval_date", "actual_approval_date",
            "expiry_date", "days_until_expiry",
            "application_fee", "fee_paid",
            "depends_on", "depends_on_name", "sort_order",
            "created_at", "updated_at",
        )


class ProjectPermitDetailSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    permit_type_display = serializers.CharField(source="get_permit_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    is_delayed = serializers.BooleanField(read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)
    depends_on_name = serializers.CharField(source="depends_on.name", read_only=True, default=None)
    submissions = PermitSubmissionSerializer(many=True, read_only=True)
    queries = PermitQuerySerializer(many=True, read_only=True)

    class Meta:
        model = ProjectPermit
        fields = "__all__"
        read_only_fields = ("id", "reference", "organization", "created_by", "created_at", "updated_at")


class ProjectPermitWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectPermit
        fields = (
            "project", "name", "permit_type", "status", "is_critical_path",
            "authority_name", "authority_contact", "authority_portal",
            "application_date", "expected_approval_date",
            "actual_approval_date", "expiry_date", "renewal_date",
            "application_fee", "fee_paid",
            "approval_certificate_ref", "conditions", "rejection_reason",
            "depends_on", "sort_order", "notes",
        )


# ── Design Management ────────────────────────────────────────────────


class DesignPhaseSerializer(serializers.ModelSerializer):
    stage_display = serializers.CharField(source="get_stage_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    progress = serializers.FloatField(read_only=True)

    class Meta:
        model = DesignPhase
        fields = (
            "id", "project", "stage", "stage_display",
            "status", "status_display",
            "total_deliverables", "approved_deliverables", "progress",
            "closeout_checked", "sort_order", "notes",
            "created_at", "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class DrawingRevisionSerializer(serializers.ModelSerializer):
    approval_state_display = serializers.CharField(source="get_approval_state_display", read_only=True)

    class Meta:
        model = DrawingRevision
        fields = (
            "id", "drawing", "revision_code", "change_description",
            "submitted_by", "submitted_date",
            "approval_state", "approval_state_display",
            "reviewer_comments", "reviewed_by", "reviewed_date",
            "created_at",
        )
        read_only_fields = ("id", "drawing", "created_at")


class DrawingListSerializer(serializers.ModelSerializer):
    discipline_display = serializers.CharField(source="get_discipline_display", read_only=True)
    approval_state_display = serializers.CharField(source="get_approval_state_display", read_only=True)
    design_phase_stage = serializers.CharField(source="design_phase.get_stage_display", read_only=True, default=None)
    project_name = serializers.CharField(source="project.name", read_only=True)

    class Meta:
        model = Drawing
        fields = (
            "id", "project", "project_name", "design_phase", "design_phase_stage",
            "drawing_number", "title", "discipline", "discipline_display",
            "current_revision", "approval_state", "approval_state_display",
            "scale", "submitted_by", "last_updated", "created_at",
        )


class DrawingDetailSerializer(serializers.ModelSerializer):
    discipline_display = serializers.CharField(source="get_discipline_display", read_only=True)
    approval_state_display = serializers.CharField(source="get_approval_state_display", read_only=True)
    design_phase_stage = serializers.CharField(source="design_phase.get_stage_display", read_only=True, default=None)
    project_name = serializers.CharField(source="project.name", read_only=True)
    revisions = DrawingRevisionSerializer(many=True, read_only=True)

    class Meta:
        model = Drawing
        fields = "__all__"
        read_only_fields = ("id", "organization", "created_by", "created_at", "last_updated")


class DrawingWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Drawing
        fields = (
            "project", "design_phase", "drawing_number", "title",
            "discipline", "current_revision", "approval_state",
            "scale", "submitted_by", "notes",
        )


class DesignReviewMeetingSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)

    class Meta:
        model = DesignReviewMeeting
        fields = (
            "id", "project", "project_name", "date", "title",
            "attendees", "key_decisions", "action_items",
            "linked_drawings", "minutes_notes", "recorded_by",
            "created_at",
        )
        read_only_fields = ("id", "created_at")


# ── Procurement Planning ─────────────────────────────────────────────


class PackageBidderSerializer(serializers.ModelSerializer):
    class Meta:
        model = PackageBidder
        fields = (
            "id", "package", "firm_name", "specialization",
            "bid_amount", "proposed_duration_days",
            "score_price", "score_technical", "score_timeline", "score_safety",
            "total_score", "is_recommended", "is_prequalified",
            "compliance_notes", "notes", "created_at",
        )
        read_only_fields = ("id", "package", "created_at")


class ProcurementPackageListSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    budget_variance = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    is_behind_schedule = serializers.BooleanField(read_only=True)
    bidder_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = ProcurementPackage
        fields = (
            "id", "plan", "name", "description",
            "status", "status_display",
            "estimated_budget", "contract_value", "budget_variance",
            "pqq_issue_date", "rfp_issue_date", "tender_return_date",
            "evaluation_end_date", "award_date", "contract_start_date",
            "awarded_to", "is_behind_schedule", "bidder_count",
            "sort_order", "created_at", "updated_at",
        )


class ProcurementPackageDetailSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    budget_variance = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    is_behind_schedule = serializers.BooleanField(read_only=True)
    bidders = PackageBidderSerializer(many=True, read_only=True)

    class Meta:
        model = ProcurementPackage
        fields = "__all__"
        read_only_fields = ("id", "plan", "created_at", "updated_at")


class ProcurementPackageWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcurementPackage
        fields = (
            "name", "description", "status",
            "estimated_budget", "contract_value",
            "pqq_issue_date", "rfp_issue_date", "tender_return_date",
            "evaluation_end_date", "award_date", "contract_start_date",
            "awarded_to", "award_justification", "sort_order", "notes",
        )


class ProcurementPlanListSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    strategy_display = serializers.CharField(source="get_strategy_display", read_only=True)
    package_count = serializers.IntegerField(read_only=True, default=0)
    total_allocated = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True, default=Decimal("0"))
    total_contracted = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True, default=Decimal("0"))

    class Meta:
        model = ProcurementPlan
        fields = (
            "id", "project", "project_name",
            "strategy", "strategy_display",
            "total_budget", "contingency_pct",
            "package_count", "total_allocated", "total_contracted",
            "created_at", "updated_at",
        )


class ProcurementPlanDetailSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    strategy_display = serializers.CharField(source="get_strategy_display", read_only=True)
    packages = ProcurementPackageListSerializer(many=True, read_only=True)

    class Meta:
        model = ProcurementPlan
        fields = "__all__"
        read_only_fields = ("id", "organization", "created_by", "created_at", "updated_at")


class ProcurementPlanWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcurementPlan
        fields = ("project", "strategy", "total_budget", "contingency_pct", "notes")


# ── Sales & Revenue Forecast ─────────────────────────────────────────


class SaleableUnitSerializer(serializers.ModelSerializer):
    unit_type_display = serializers.CharField(source="get_unit_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    price_per_sqm = serializers.FloatField(read_only=True)

    class Meta:
        model = SaleableUnit
        fields = (
            "id", "forecast", "unit_id", "unit_type", "unit_type_display",
            "floor_location", "size_sqm", "asking_price", "minimum_price",
            "sold_price", "price_per_sqm",
            "status", "status_display",
            "buyer_name", "reserved_date", "sold_date",
            "notes", "sort_order", "created_at", "updated_at",
        )
        read_only_fields = ("id", "forecast", "created_at", "updated_at")


class SalesPhaseTargetSerializer(serializers.ModelSerializer):
    variance = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    unit_variance = serializers.IntegerField(read_only=True)

    class Meta:
        model = SalesPhaseTarget
        fields = (
            "id", "forecast", "phase_name",
            "start_date", "end_date",
            "target_units", "target_revenue",
            "actual_units", "actual_revenue",
            "variance", "unit_variance",
            "milestone_trigger", "sort_order", "created_at",
        )
        read_only_fields = ("id", "forecast", "created_at")


class SalesRevenueForecastListSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    total_units = serializers.IntegerField(read_only=True, default=0)
    sold_units = serializers.IntegerField(read_only=True, default=0)
    reserved_units = serializers.IntegerField(read_only=True, default=0)
    actual_revenue = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True, default=Decimal("0"))

    class Meta:
        model = SalesRevenueForecast
        fields = (
            "id", "project", "project_name",
            "gross_development_value", "marketing_budget", "marketing_budget_pct",
            "sales_launch_date", "target_sellout_date",
            "total_units", "sold_units", "reserved_units", "actual_revenue",
            "created_at", "updated_at",
        )


class SalesRevenueForecastDetailSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    units = SaleableUnitSerializer(many=True, read_only=True)
    phase_targets = SalesPhaseTargetSerializer(many=True, read_only=True)

    class Meta:
        model = SalesRevenueForecast
        fields = "__all__"
        read_only_fields = ("id", "organization", "created_by", "created_at", "updated_at")


class SalesRevenueForecastWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesRevenueForecast
        fields = (
            "project", "gross_development_value",
            "marketing_budget", "marketing_budget_pct",
            "sales_launch_date", "target_sellout_date",
            "payment_structure", "agents", "notes",
        )


# ── Stage Gates ──────────────────────────────────────────────────────


class StageGateListSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    gate_type_display = serializers.CharField(source="get_gate_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    prerequisites_met = serializers.BooleanField(read_only=True)
    prerequisite_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = StageGate
        fields = (
            "id", "project", "project_name",
            "gate_type", "gate_type_display",
            "name", "description",
            "status", "status_display", "sort_order",
            "scheduled_review_date", "actual_review_date",
            "decided_by", "decision_date",
            "baseline_date", "delay_days",
            "is_overdue", "prerequisites_met", "prerequisite_count",
            "financial_release_triggered",
            "created_at", "updated_at",
        )


class StageGateDetailSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    gate_type_display = serializers.CharField(source="get_gate_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    prerequisites_met = serializers.BooleanField(read_only=True)
    prerequisite_milestones_detail = serializers.SerializerMethodField()

    class Meta:
        model = StageGate
        fields = "__all__"
        read_only_fields = ("id", "organization", "created_by", "created_at", "updated_at")

    def get_prerequisite_milestones_detail(self, obj):
        return [
            {
                "id": m.id,
                "name": m.name,
                "is_completed": m.is_completed,
                "target_date": m.target_date,
                "completed_date": m.completed_date,
                "reference_code": m.reference_code,
            }
            for m in obj.prerequisite_milestones.all()
        ]


class StageGateWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = StageGate
        fields = (
            "project", "gate_type", "name", "description", "status", "sort_order",
            "prerequisite_milestones", "prerequisite_notes",
            "scheduled_review_date", "actual_review_date",
            "decided_by", "decision_date",
            "conditions", "rejection_reason",
            "baseline_date", "delay_days",
            "delay_root_cause", "recovery_plan",
            "financial_release_triggered", "financial_release_notes",
            "notes",
        )


# ── Document Control ─────────────────────────────────────────────────


class DocumentVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentVersion
        fields = (
            "id", "document", "version_label", "change_summary",
            "uploaded_by", "uploaded_date", "is_current", "notes", "created_at",
        )
        read_only_fields = ("id", "document", "created_at")


class DocumentTransmittalSerializer(serializers.ModelSerializer):
    purpose_display = serializers.CharField(source="get_purpose_display", read_only=True)

    class Meta:
        model = DocumentTransmittal
        fields = (
            "id", "document", "transmittal_ref", "recipient",
            "purpose", "purpose_display", "sent_date",
            "acknowledged", "acknowledged_date",
            "sent_by", "notes", "created_at",
        )
        read_only_fields = ("id", "document", "created_at")


class ProjectDocumentListSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    folder_display = serializers.CharField(source="get_folder_display", read_only=True)
    classification_display = serializers.CharField(source="get_classification_display", read_only=True)
    execution_status_display = serializers.CharField(source="get_execution_status_display", read_only=True)
    is_expiring_soon = serializers.BooleanField(read_only=True)

    class Meta:
        model = ProjectDocument
        fields = (
            "id", "reference", "title", "project", "project_name",
            "folder", "folder_display",
            "classification", "classification_display",
            "execution_status", "execution_status_display",
            "current_version", "author", "source",
            "expiry_date", "is_expiring_soon",
            "linked_module", "created_at", "updated_at",
        )


class ProjectDocumentDetailSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    folder_display = serializers.CharField(source="get_folder_display", read_only=True)
    classification_display = serializers.CharField(source="get_classification_display", read_only=True)
    execution_status_display = serializers.CharField(source="get_execution_status_display", read_only=True)
    is_expiring_soon = serializers.BooleanField(read_only=True)
    versions = DocumentVersionSerializer(many=True, read_only=True)
    transmittals = DocumentTransmittalSerializer(many=True, read_only=True)

    class Meta:
        model = ProjectDocument
        fields = "__all__"
        read_only_fields = ("id", "reference", "organization", "created_by", "created_at", "updated_at")


class ProjectDocumentWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectDocument
        fields = (
            "project", "title", "folder", "classification",
            "execution_status", "current_version",
            "author", "source", "description",
            "retention_years", "expiry_date", "linked_module", "notes",
        )


class MeetingMinutesArchiveSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)

    class Meta:
        model = MeetingMinutesArchive
        fields = (
            "id", "project", "project_name", "series",
            "date", "title", "attendees", "minutes_text",
            "action_items", "recorded_by", "created_at",
        )
        read_only_fields = ("id", "created_at")


# ── Project Communications ───────────────────────────────────────────


class ProjectAnnouncementSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    priority_display = serializers.CharField(source="get_priority_display", read_only=True)
    audience_display = serializers.CharField(source="get_audience_display", read_only=True)

    class Meta:
        model = ProjectAnnouncement
        fields = (
            "id", "project", "project_name",
            "subject", "body",
            "priority", "priority_display",
            "audience", "audience_display",
            "is_pinned", "published_by", "published_at",
        )
        read_only_fields = ("id", "published_at")


class ProjectDecisionLogSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)

    class Meta:
        model = ProjectDecisionLog
        fields = (
            "id", "project", "project_name",
            "decision_id", "subject", "description",
            "decided_by", "rationale", "decision_date",
            "meeting_reference", "impact_modules",
            "status", "notes", "created_at",
        )
        read_only_fields = ("id", "decision_id", "created_at")


class StakeholderUpdateListSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    frequency_display = serializers.CharField(source="get_frequency_display", read_only=True)
    read_count = serializers.IntegerField(read_only=True)
    recipient_count = serializers.SerializerMethodField()

    class Meta:
        model = StakeholderUpdate
        fields = (
            "id", "project", "project_name",
            "title", "frequency", "frequency_display",
            "report_date", "distribution_group",
            "prepared_by", "sent_at",
            "read_count", "recipient_count",
            "created_at",
        )

    def get_recipient_count(self, obj) -> int:
        return len(obj.recipients) if obj.recipients else 0


class StakeholderUpdateDetailSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    frequency_display = serializers.CharField(source="get_frequency_display", read_only=True)
    read_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = StakeholderUpdate
        fields = "__all__"
        read_only_fields = ("id", "organization", "created_at")


class StakeholderUpdateWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = StakeholderUpdate
        fields = (
            "project", "title", "frequency", "report_date",
            "executive_summary", "schedule_status",
            "financial_status", "risk_blockers",
            "distribution_group", "recipients",
            "prepared_by", "notes",
        )


# ── Project Reporting ────────────────────────────────────────────────


class ProjectReportListSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    report_type_display = serializers.CharField(source="get_report_type_display", read_only=True)
    budget_variance = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    budget_variance_pct = serializers.FloatField(read_only=True)

    class Meta:
        model = ProjectReport
        fields = (
            "id", "reference", "title", "project", "project_name",
            "report_type", "report_type_display",
            "report_date", "period_start", "period_end",
            "schedule_rag", "budget_rag", "quality_rag", "safety_rag",
            "overall_completion_pct",
            "original_budget", "forecast_at_completion",
            "budget_variance", "budget_variance_pct",
            "is_frozen", "prepared_by",
            "created_at", "updated_at",
        )


class ProjectReportDetailSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    report_type_display = serializers.CharField(source="get_report_type_display", read_only=True)
    budget_variance = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    budget_variance_pct = serializers.FloatField(read_only=True)

    class Meta:
        model = ProjectReport
        fields = "__all__"
        read_only_fields = ("id", "reference", "organization", "created_by", "created_at", "updated_at")


class ProjectReportWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectReport
        fields = (
            "project", "title", "report_type",
            "report_date", "period_start", "period_end",
            "schedule_rag", "budget_rag", "quality_rag", "safety_rag",
            "executive_summary", "key_achievements", "key_issues",
            "original_budget", "committed_spend", "actual_spend",
            "forecast_at_completion", "contingency_used_pct",
            "schedule_variance_summary", "critical_path_impact",
            "overall_completion_pct", "top_risks",
            "is_frozen", "prepared_by", "approved_by", "notes",
        )


# ── Project Closeout ─────────────────────────────────────────────────


class FinalAccountEntrySerializer(serializers.ModelSerializer):
    variance = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)

    class Meta:
        model = FinalAccountEntry
        fields = (
            "id", "closeout", "contractor_name",
            "original_contract_value", "approved_variations",
            "final_settled_amount", "variance",
            "retention_held", "retention_released",
            "closeout_certificate_issued",
            "performance_rating", "performance_notes", "created_at",
        )
        read_only_fields = ("id", "closeout", "created_at")


class SnagListItemSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = SnagListItem
        fields = (
            "id", "closeout", "location", "description",
            "responsible_contractor", "status", "status_display",
            "reported_date", "resolved_date", "notes", "created_at",
        )
        read_only_fields = ("id", "closeout", "reported_date", "created_at")


class WarrantyTrackerSerializer(serializers.ModelSerializer):
    is_active = serializers.BooleanField(read_only=True)
    days_remaining = serializers.IntegerField(read_only=True)

    class Meta:
        model = WarrantyTracker
        fields = (
            "id", "closeout", "asset_system", "provider",
            "warranty_start", "warranty_end",
            "is_active", "days_remaining",
            "claim_log", "notes", "created_at",
        )
        read_only_fields = ("id", "closeout", "created_at")


class ProjectCloseoutListSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    completion_pct = serializers.IntegerField(read_only=True)
    budget_variance = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    snag_count = serializers.IntegerField(read_only=True, default=0)
    open_snag_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = ProjectCloseout
        fields = (
            "id", "project", "project_name",
            "status", "status_display", "completion_pct",
            "practical_completion_date", "final_completion_date",
            "final_project_cost", "original_budget", "budget_variance",
            "retention_held", "retention_released",
            "snag_count", "open_snag_count",
            "created_at", "updated_at",
        )


class ProjectCloseoutDetailSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    completion_pct = serializers.IntegerField(read_only=True)
    budget_variance = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    final_accounts = FinalAccountEntrySerializer(many=True, read_only=True)
    snag_items = SnagListItemSerializer(many=True, read_only=True)
    warranties = WarrantyTrackerSerializer(many=True, read_only=True)

    class Meta:
        model = ProjectCloseout
        fields = "__all__"
        read_only_fields = ("id", "organization", "created_by", "created_at", "updated_at")


class ProjectCloseoutWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectCloseout
        fields = (
            "project", "status",
            "practical_completion_date", "final_completion_date",
            "final_project_cost", "original_budget", "total_variations",
            "retention_held", "retention_released", "retention_release_date",
            "financial_reconciliation_done", "contracts_closed",
            "handover_completed", "snags_resolved",
            "documentation_archived", "warranties_registered",
            "notes",
        )


# ── Construction Reports ─────────────────────────────────────────────


class RFICommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = RFIComment
        fields = ("id", "rfi", "author_name", "body", "created_by", "created_at")
        read_only_fields = ("id", "rfi", "created_by", "created_at")


class RFIListSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    discipline_display = serializers.CharField(source="get_discipline_display", read_only=True)
    urgency_display = serializers.CharField(source="get_urgency_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    comment_count = serializers.IntegerField(read_only=True, default=0)
    days_open = serializers.SerializerMethodField()

    class Meta:
        model = RFI
        fields = (
            "id", "rfi_number", "subject", "project", "project_name",
            "discipline", "discipline_display",
            "urgency", "urgency_display",
            "status", "status_display",
            "ball_in_court", "submitted_by", "submitted_date",
            "responded_date", "closed_date",
            "has_cost_impact", "has_schedule_impact",
            "response_sla_hours", "comment_count", "days_open",
            "created_at", "updated_at",
        )

    def get_days_open(self, obj) -> int:
        if obj.closed_date:
            return (obj.closed_date - obj.submitted_date).days
        from datetime import date
        return (date.today() - obj.submitted_date).days


class RFIDetailSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    discipline_display = serializers.CharField(source="get_discipline_display", read_only=True)
    urgency_display = serializers.CharField(source="get_urgency_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    comments = RFICommentSerializer(many=True, read_only=True)

    class Meta:
        model = RFI
        fields = "__all__"
        read_only_fields = ("id", "rfi_number", "organization", "created_by", "created_at", "updated_at")


class RFIWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = RFI
        fields = (
            "project", "subject", "query", "discipline", "urgency",
            "status", "ball_in_court", "proposed_solution",
            "reference", "location", "submitted_by",
            "response", "responded_by", "responded_date",
            "has_cost_impact", "has_schedule_impact",
            "cost_impact_notes", "schedule_impact_notes",
            "response_sla_hours", "notes",
        )


class ConstructionReportListSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    frequency_display = serializers.CharField(source="get_frequency_display", read_only=True)
    reference = serializers.CharField(source="report_number", read_only=True)
    published_at = serializers.DateTimeField(source="published_date", read_only=True)

    class Meta:
        model = ConstructionReport
        fields = (
            "id", "reference", "title", "project", "project_name",
            "category", "category_display",
            "status", "status_display",
            "frequency", "frequency_display",
            "reporting_period_start", "reporting_period_end",
            "prepared_by", "published_at",
            "created_at", "updated_at",
        )


class ConstructionReportDetailSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    frequency_display = serializers.CharField(source="get_frequency_display", read_only=True)
    reference = serializers.CharField(source="report_number", read_only=True)
    published_at = serializers.DateTimeField(source="published_date", read_only=True)

    class Meta:
        model = ConstructionReport
        fields = "__all__"
        read_only_fields = ("id", "report_number", "organization", "created_by", "created_at", "updated_at")


class ConstructionReportWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConstructionReport
        fields = (
            "project", "title", "category", "status", "frequency",
            "reporting_period_start", "reporting_period_end",
            "executive_summary", "key_highlights", "key_risks",
            "recommendations", "recipients", "prepared_by", "notes",
        )


# ── Site Instructions ────────────────────────────────────────────────


class SiteInstructionListSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    instruction_type_display = serializers.CharField(source="get_instruction_type_display", read_only=True)
    priority_display = serializers.CharField(source="get_priority_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = SiteInstruction
        fields = (
            "id", "si_number", "title", "project", "project_name",
            "instruction_type", "instruction_type_display",
            "priority", "priority_display",
            "status", "status_display",
            "location", "has_financial_impact",
            "estimated_cost_impact", "schedule_impact_days",
            "issued_by", "issued_date", "compliance_deadline",
            "acknowledged_by", "acknowledged_date",
            "completed_date", "verified_date",
            "created_at", "updated_at",
        )


class SiteInstructionDetailSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    instruction_type_display = serializers.CharField(source="get_instruction_type_display", read_only=True)
    priority_display = serializers.CharField(source="get_priority_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    linked_variation_number = serializers.CharField(source="linked_variation.variation_number", read_only=True, default=None)

    class Meta:
        model = SiteInstruction
        fields = "__all__"
        read_only_fields = ("id", "si_number", "organization", "created_by", "created_at", "updated_at")


class SiteInstructionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteInstruction
        fields = (
            "project", "title", "description",
            "instruction_type", "priority", "status",
            "location", "cost_code",
            "has_financial_impact", "estimated_cost_impact", "schedule_impact_days",
            "issued_by", "issued_date", "compliance_deadline",
            "acknowledged_by",
            "contractor_timeline_impact", "contractor_estimated_cost", "contractor_remarks",
            "linked_variation", "notes",
        )


# ── HSE Incidents ────────────────────────────────────────────────────


class HSEIncidentListSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    classification_display = serializers.CharField(source="get_classification_display", read_only=True)
    root_cause_display = serializers.CharField(source="get_root_cause_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = HSEIncident
        fields = (
            "id", "incident_number", "title", "project", "project_name",
            "classification", "classification_display",
            "root_cause", "root_cause_display",
            "status", "status_display",
            "location", "incident_date", "incident_time",
            "reported_by", "lost_time_days",
            "requires_regulatory_report", "closed_date",
            "created_at", "updated_at",
        )


class HSEIncidentDetailSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    classification_display = serializers.CharField(source="get_classification_display", read_only=True)
    root_cause_display = serializers.CharField(source="get_root_cause_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = HSEIncident
        fields = "__all__"
        read_only_fields = ("id", "incident_number", "organization", "created_by", "created_at", "updated_at")


class HSEIncidentWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = HSEIncident
        fields = (
            "project", "title", "description",
            "classification", "root_cause", "status",
            "location", "incident_date", "incident_time",
            "reported_by", "persons_involved", "witness_statements",
            "injuries_description", "lost_time_days",
            "corrective_actions", "preventive_actions",
            "requires_regulatory_report", "closed_date", "notes",
        )


# ── HSE Permits to Work ─────────────────────────────────────────────


class HSEPermitListSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    permit_type_display = serializers.CharField(source="get_permit_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = HSEPermitToWork
        fields = (
            "id", "permit_number", "title", "project", "project_name",
            "permit_type", "permit_type_display",
            "status", "status_display",
            "location", "valid_from", "valid_until",
            "requested_by", "approved_by", "approved_date",
            "closed_date",
            "created_at", "updated_at",
        )


class HSEPermitDetailSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    permit_type_display = serializers.CharField(source="get_permit_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = HSEPermitToWork
        fields = "__all__"
        read_only_fields = ("id", "permit_number", "organization", "created_by", "created_at", "updated_at")


class HSEPermitWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = HSEPermitToWork
        fields = (
            "project", "permit_type", "title", "description", "status",
            "location", "task_description",
            "hazards_identified", "mitigations", "required_ppe",
            "valid_from", "valid_until",
            "requested_by", "approved_by", "approved_date",
            "site_supervisor_signoff", "site_supervisor_signoff_date",
            "closed_by", "closed_date", "notes",
        )


# ── HSE Toolbox Talks ───────────────────────────────────────────────


class HSEToolboxTalkListSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    shift_display = serializers.CharField(source="get_shift_display", read_only=True)

    class Meta:
        model = HSEToolboxTalk
        fields = (
            "id", "tbt_number", "topic", "project", "project_name",
            "conducted_by", "conducted_date",
            "shift", "shift_display",
            "location", "attendees_count",
            "created_at", "updated_at",
        )


class HSEToolboxTalkDetailSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    shift_display = serializers.CharField(source="get_shift_display", read_only=True)

    class Meta:
        model = HSEToolboxTalk
        fields = "__all__"
        read_only_fields = ("id", "tbt_number", "organization", "created_by", "created_at", "updated_at")


class HSEToolboxTalkWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = HSEToolboxTalk
        fields = (
            "project", "topic", "description",
            "conducted_by", "conducted_date", "shift",
            "location", "attendees_count", "attendees_names",
            "key_points", "follow_up_actions", "notes",
        )


# ── Commissioning Plans ─────────────────────────────────────────────


class TestRecordSerializer(serializers.ModelSerializer):
    result_display = serializers.CharField(source="get_result_display", read_only=True)
    retest_result_display = serializers.CharField(source="get_retest_result_display", read_only=True)

    class Meta:
        model = TestRecord
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class CommissioningPunchItemSerializer(serializers.ModelSerializer):
    priority_display = serializers.CharField(source="get_priority_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = CommissioningPunchItem
        fields = "__all__"
        read_only_fields = ("id", "item_number", "created_at", "updated_at")


class CommissioningPlanListSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    system_type_display = serializers.CharField(source="get_system_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    test_count = serializers.IntegerField(read_only=True, default=0)
    punch_item_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = CommissioningPlan
        fields = (
            "id", "plan_number", "name", "project", "project_name",
            "system_type", "system_type_display",
            "status", "status_display",
            "witness_required", "target_date", "completed_date",
            "certified_by", "certified_date", "certificate_number",
            "test_count", "punch_item_count",
            "created_at", "updated_at",
        )


class CommissioningPlanDetailSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    system_type_display = serializers.CharField(source="get_system_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    test_records = TestRecordSerializer(many=True, read_only=True)
    punch_items = CommissioningPunchItemSerializer(many=True, read_only=True)

    class Meta:
        model = CommissioningPlan
        fields = "__all__"
        read_only_fields = ("id", "plan_number", "certificate_number", "organization", "created_by", "created_at", "updated_at")


class CommissioningPlanWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommissioningPlan
        fields = (
            "project", "name", "system_type", "status",
            "description", "witness_required", "witness_name", "witness_present",
            "target_date", "completed_date", "notes",
        )


# ── Cost Control ─────────────────────────────────────────────────────


class CostTransactionSerializer(serializers.ModelSerializer):
    transaction_type_display = serializers.CharField(source="get_transaction_type_display", read_only=True)

    class Meta:
        model = CostTransaction
        fields = (
            "id", "project", "cost_code_budget",
            "transaction_type", "transaction_type_display",
            "reference", "description", "amount",
            "transaction_date", "vendor", "notes", "created_at",
        )
        read_only_fields = ("id", "created_at")


class CostCodeBudgetListSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    revised_budget = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    forecast_at_completion = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    variance = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)

    class Meta:
        model = CostCodeBudget
        fields = (
            "id", "project", "project_name",
            "cost_code", "description",
            "original_budget", "approved_changes", "revised_budget",
            "committed", "actual_cost",
            "forecast_to_complete", "forecast_at_completion", "variance",
            "sort_order", "created_at", "updated_at",
        )


class CostCodeBudgetDetailSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    revised_budget = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    forecast_at_completion = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    variance = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    transactions = CostTransactionSerializer(many=True, read_only=True)

    class Meta:
        model = CostCodeBudget
        fields = "__all__"
        read_only_fields = ("id", "organization", "created_at", "updated_at")


class CostCodeBudgetWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CostCodeBudget
        fields = (
            "project", "cost_code", "description",
            "original_budget", "approved_changes",
            "committed", "actual_cost", "forecast_to_complete",
            "sort_order", "notes",
        )
