from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from apps.admin_mixins import OrgScopedAdminMixin

from .models import (
    ConsultantCommunicationLog,
    ConsultantDeliverable,
    ConsultantPaymentMilestone,
    DesignPhase,
    DesignReviewMeeting,
    Drawing,
    DrawingRevision,
    PackageBidder,
    ProcurementPackage,
    ProcurementPlan,
    SaleableUnit,
    SalesPhaseTarget,
    SalesRevenueForecast,
    StageGate,
    DocumentTransmittal,
    DocumentVersion,
    MeetingMinutesArchive,
    FinalAccountEntry,
    ProjectAnnouncement,
    ProjectCloseout,
    ProjectDecisionLog,
    ProjectDocument,
    ProjectReport,
    SnagListItem,
    StakeholderUpdate,
    WarrantyTracker,
    PermitQuery,
    PermitSubmission,
    ProjectPermit,
    EquipmentDeploymentLog,
    EquipmentMaintenanceLog,
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
    ProjectContractorProfile,
    ProjectSetupConfig,
    ProjectTeamMember,
    ProjectCostEntry,
    ProjectDailySiteReport,
    ProjectEquipment,
    ProjectDailySiteReportPhoto,
    ProjectExecutionInspection,
    ProjectExecutionInspectionItem,
    ProjectFieldEscalation,
    ProjectMilestone,
    ProjectMilestoneApprovalDecision,
    ProjectMilestoneApprovalRule,
    ProjectPhase,
    ProjectPhaseDependency,
    ProjectRiskRegisterEntry,
    ProjectScheduleDelayLog,
    ProjectSupportingAttachment,
    ProjectTask,
    ProjectTaskComment,
    ProjectVariationOrder,
    ProjectWorkforceLog,
    ProjectWorkPackage,
)


class ProjectPhaseInline(TabularInline):
    model = ProjectPhase
    extra = 0
    fields = [
        "name", "sort_order", "status", "weight",
        "planned_start_date", "planned_end_date",
        "actual_start_date", "actual_end_date",
        "planned_budget", "actual_cost",
    ]


class ProjectMilestoneInline(TabularInline):
    model = ProjectMilestone
    extra = 0
    fields = ["name", "sort_order", "target_date", "completed_date", "is_completed"]


class ProjectTaskInline(TabularInline):
    model = ProjectTask
    extra = 0
    fields = [
        "name",
        "work_package",
        "priority",
        "status",
        "assigned_user",
        "assigned_to",
        "due_date",
        "sla_target_at",
        "completed_date",
        "sort_order",
    ]


class ProjectCostEntryInline(TabularInline):
    model = ProjectCostEntry
    extra = 0
    fields = ["description", "amount", "date", "category", "vendor", "reference_number"]


@admin.register(Project)
class ProjectAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "name",
        "property",
        "status",
        "risk_rating",
        "compliance_status",
        "compliance_score",
        "project_manager",
        "start_date",
        "target_end_date",
        "number_of_units",
        "budget",
    ]
    list_filter = ["status", "property", "risk_rating", "compliance_status"]
    search_fields = ["name", "description", "project_manager"]
    inlines = [ProjectPhaseInline]


@admin.register(ProjectPhase)
class ProjectPhaseAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["name", "project", "status", "sort_order", "planned_budget", "actual_cost"]
    list_filter = ["status"]
    search_fields = ["name"]
    inlines = [ProjectMilestoneInline, ProjectTaskInline, ProjectCostEntryInline]


@admin.register(ProjectMilestone)
class ProjectMilestoneAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["name", "phase", "target_date", "is_completed", "approval_required", "approval_status"]
    list_filter = ["is_completed", "approval_required", "approval_status"]


@admin.register(ProjectTask)
class ProjectTaskAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "name",
        "phase",
        "work_package",
        "priority",
        "status",
        "assigned_user",
        "assigned_to",
        "due_date",
        "sla_target_at",
    ]
    list_filter = ["status", "priority"]
    search_fields = ["name", "work_package", "assigned_to", "assigned_external_ref"]


@admin.register(ProjectTaskComment)
class ProjectTaskCommentAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["task", "author", "created_at"]
    search_fields = ["task__name", "comment", "author__email", "author__first_name", "author__last_name"]


@admin.register(ProjectWorkPackage)
class ProjectWorkPackageAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "package_id",
        "name",
        "project",
        "phase",
        "contractor",
        "budget",
        "start_date",
        "end_date",
    ]
    list_filter = ["project", "contractor", "start_date", "end_date"]
    search_fields = ["package_id", "name", "scope_description", "project__name", "contractor__name"]


@admin.register(ProjectContractorProfile)
class ProjectContractorProfileAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "project",
        "contractor",
        "trade_specialization",
        "contract_value",
        "performance_rating",
        "updated_at",
    ]
    list_filter = ["project", "contractor"]
    search_fields = [
        "project__name",
        "contractor__name",
        "trade_specialization",
        "company_profile",
    ]


@admin.register(ProjectCostEntry)
class ProjectCostEntryAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["description", "phase", "amount", "date", "category"]
    list_filter = ["category"]
    search_fields = ["description", "vendor"]


@admin.register(ProjectRiskRegisterEntry)
class ProjectRiskRegisterEntryAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "title",
        "project",
        "risk_category",
        "severity",
        "status",
        "treatment",
        "owner_role",
        "risk_score",
        "target_resolution_date",
    ]
    list_filter = ["severity", "status", "treatment", "escalation_required"]
    search_fields = ["title", "description", "project__name", "mitigation_plan"]


@admin.register(ProjectVariationOrder)
class ProjectVariationOrderAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "variation_number",
        "project",
        "title",
        "status",
        "contract_value",
        "requested_date",
        "due_date",
        "related_document",
    ]
    list_filter = ["status", "project", "requested_date"]
    search_fields = ["variation_number", "title", "project__name", "change_summary", "reason"]


@admin.register(ProjectWorkforceLog)
class ProjectWorkforceLogAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "project",
        "worker_id",
        "employee",
        "trade",
        "contractor",
        "report_date",
        "daily_attendance",
        "shift",
        "task_assigned",
        "productivity",
        "overtime_hours",
        "laborers_count",
        "skilled_count",
        "supervisors_count",
        "subcontractors_count",
        "equipment_operators_count",
    ]
    list_filter = ["daily_attendance", "shift", "report_date"]
    search_fields = [
        "project__name",
        "worker_id",
        "employee__user__first_name",
        "employee__user__last_name",
        "trade",
        "contractor__name",
        "task_assigned__name",
        "notes",
    ]


class ProjectDailySiteReportPhotoInline(TabularInline):
    model = ProjectDailySiteReportPhoto
    extra = 0
    fields = ["image", "caption", "taken_at", "uploaded_by", "created_at"]
    readonly_fields = ["created_at"]


@admin.register(ProjectDailySiteReport)
class ProjectDailySiteReportAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "project",
        "report_date",
        "shift",
        "status",
        "weather",
        "weather_delay_hours",
        "progress_percent",
        "escalation_required",
    ]
    list_filter = ["status", "shift", "weather", "escalation_required", "report_date"]
    search_fields = ["project__name", "work_completed", "blockers", "incidents"]
    inlines = [ProjectDailySiteReportPhotoInline]


@admin.register(ProjectDailySiteReportPhoto)
class ProjectDailySiteReportPhotoAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["id", "report", "caption", "uploaded_by", "created_at"]
    search_fields = ["report__project__name", "caption"]


@admin.register(ProjectFieldEscalation)
class ProjectFieldEscalationAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "issue_date",
        "title",
        "project",
        "issue_category",
        "issue_type",
        "severity",
        "status",
        "weather_delay_hours",
        "owner_name",
        "due_date",
        "resolved_at",
    ]
    list_filter = ["issue_category", "issue_type", "severity", "status", "issue_date"]
    search_fields = [
        "title",
        "description",
        "project__name",
        "owner_name",
        "location",
        "impact_summary",
        "root_cause",
        "immediate_action",
    ]


class ProjectExecutionInspectionItemInline(TabularInline):
    model = ProjectExecutionInspectionItem
    extra = 0
    fields = [
        "sort_order",
        "checklist_group",
        "checklist_item",
        "result",
        "remarks",
        "action_owner",
        "action_due_date",
        "resolved_on",
    ]


@admin.register(ProjectExecutionInspection)
class ProjectExecutionInspectionAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "inspection_number",
        "project",
        "phase",
        "inspection_type",
        "status",
        "inspected_on",
        "inspector_name",
        "overall_score",
    ]
    list_filter = ["inspection_type", "status", "shift", "inspected_on"]
    search_fields = [
        "inspection_number",
        "project__name",
        "phase__name",
        "work_package",
        "location",
        "inspector_name",
    ]
    inlines = [ProjectExecutionInspectionItemInline]


@admin.register(ProjectSupportingAttachment)
class ProjectSupportingAttachmentAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "id",
        "project",
        "variation",
        "phase",
        "milestone",
        "task",
        "cost_entry",
        "risk_entry",
        "workforce_log",
        "quality_inspection",
        "escalation",
        "uploaded_by",
        "created_at",
    ]
    search_fields = [
        "project__name",
        "variation__variation_number",
        "variation__title",
        "phase__name",
        "milestone__name",
        "task__name",
        "cost_entry__description",
        "risk_entry__title",
        "workforce_log__project__name",
        "quality_inspection__inspection_number",
        "quality_inspection__project__name",
        "escalation__title",
        "caption",
    ]


@admin.register(ProjectPhaseDependency)
class ProjectPhaseDependencyAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "project",
        "predecessor_phase",
        "successor_phase",
        "dependency_type",
        "lag_days",
    ]
    list_filter = ["dependency_type"]
    search_fields = [
        "project__name",
        "predecessor_phase__name",
        "successor_phase__name",
    ]


@admin.register(ProjectMilestoneApprovalRule)
class ProjectMilestoneApprovalRuleAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "project",
        "phase",
        "required_role",
        "sequence_order",
        "is_mandatory",
        "is_active",
    ]
    list_filter = ["is_mandatory", "is_active"]
    search_fields = [
        "project__name",
        "phase__name",
        "required_role__name",
    ]


@admin.register(ProjectMilestoneApprovalDecision)
class ProjectMilestoneApprovalDecisionAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "milestone",
        "approver_role",
        "approver",
        "decision",
        "decided_at",
    ]
    list_filter = ["decision"]
    search_fields = [
        "milestone__name",
        "approver__first_name",
        "approver__last_name",
        "approver_role__name",
    ]


@admin.register(ProjectScheduleDelayLog)
class ProjectScheduleDelayLogAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "project",
        "phase",
        "milestone",
        "delay_date",
        "delay_type",
        "impact_days",
    ]
    list_filter = ["delay_type", "delay_date"]
    search_fields = [
        "project__name",
        "phase__name",
        "milestone__name",
        "reason",
        "mitigation_action",
    ]


class EquipmentMaintenanceLogInline(TabularInline):
    model = EquipmentMaintenanceLog
    extra = 0
    fields = ["log_type", "date", "description", "cost", "performed_by"]


class EquipmentDeploymentLogInline(TabularInline):
    model = EquipmentDeploymentLog
    extra = 0
    fields = ["project", "site_name", "operator", "deployed_date", "returned_date", "hours_used"]


@admin.register(ProjectEquipment)
class ProjectEquipmentAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["asset_id", "name", "equipment_type", "status", "current_location", "last_service_date"]
    list_filter = ["status", "equipment_type", "ownership"]
    search_fields = ["asset_id", "name", "serial_number", "current_location"]
    inlines = [EquipmentMaintenanceLogInline, EquipmentDeploymentLogInline]


@admin.register(PipelineOpportunity)
class PipelineOpportunityAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["pipeline_ref", "name", "stage", "development_type", "estimated_gdv", "expected_irr", "ic_decision"]
    list_filter = ["stage", "development_type", "ic_decision"]
    search_fields = ["pipeline_ref", "name", "location", "description"]


class ProjectTeamMemberInline(TabularInline):
    model = ProjectTeamMember
    extra = 0
    fields = ["name", "role", "access_level", "email", "company", "is_active"]


@admin.register(ProjectSetupConfig)
class ProjectSetupConfigAdmin(ModelAdmin):
    list_display = ["project", "current_step", "is_complete", "pipeline_source", "planned_phases"]
    list_filter = ["current_step", "is_complete"]


@admin.register(FeasibilityStudy)
class FeasibilityStudyAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["study_ref", "project", "version", "status", "expected_irr", "prepared_by"]
    list_filter = ["status", "market_risk", "finance_risk"]
    search_fields = ["study_ref", "prepared_by", "demand_analysis"]


class LandPaymentMilestoneInline(TabularInline):
    model = LandPaymentMilestone
    extra = 0
    fields = ["title", "amount", "due_date", "paid_date", "status", "sort_order"]


@admin.register(LandAcquisition)
class LandAcquisitionAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["parcel_id", "project", "location", "title_type", "verification_status", "acquisition_status", "purchase_price"]
    list_filter = ["title_type", "verification_status", "acquisition_status"]
    search_fields = ["parcel_id", "location", "seller_name"]
    inlines = [LandPaymentMilestoneInline]


class DevelopmentBudgetCategoryInline(TabularInline):
    model = DevelopmentBudgetCategory
    extra = 0
    fields = ["name", "cost_type", "allocated_amount", "actual_amount", "status", "sort_order"]


@admin.register(DevelopmentBudget)
class DevelopmentBudgetAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["project", "version", "status", "is_baseline", "prepared_by"]
    list_filter = ["status", "is_baseline"]
    search_fields = ["prepared_by", "notes"]
    inlines = [DevelopmentBudgetCategoryInline]


class FinancingDrawdownInline(TabularInline):
    model = FinancingDrawdown
    extra = 0
    fields = ["reference", "request_date", "amount_requested", "amount_received", "status", "disbursement_date"]


class FinancingRepaymentInline(TabularInline):
    model = FinancingRepayment
    extra = 0
    fields = ["payment_date", "principal_amount", "interest_amount", "ending_balance", "status"]


class FinancingCovenantInline(TabularInline):
    model = FinancingCovenant
    extra = 0
    fields = ["name", "threshold", "current_value", "status", "last_tested"]


@admin.register(FinancingSource)
class FinancingSourceAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["reference", "name", "project", "source_type", "status", "committed_amount", "drawn_amount"]
    list_filter = ["source_type", "status"]
    search_fields = ["reference", "name", "institution"]
    inlines = [FinancingDrawdownInline, FinancingRepaymentInline, FinancingCovenantInline]


class ConsultantPaymentMilestoneInline(TabularInline):
    model = ConsultantPaymentMilestone
    extra = 0
    fields = ["description", "amount", "trigger_date", "status", "paid_date", "sort_order"]


class ConsultantDeliverableInline(TabularInline):
    model = ConsultantDeliverable
    extra = 0
    fields = ["name", "due_date", "format", "status", "submitted_date", "sort_order"]


class ConsultantCommunicationLogInline(TabularInline):
    model = ConsultantCommunicationLog
    extra = 0
    fields = ["entry_type", "date", "subject", "logged_by"]


@admin.register(ProjectConsultant)
class ProjectConsultantAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["firm_name", "project", "discipline", "status", "contract_value", "compliance_status"]
    list_filter = ["discipline", "status", "compliance_status"]
    search_fields = ["firm_name", "contact_person", "email"]
    inlines = [ConsultantPaymentMilestoneInline, ConsultantDeliverableInline, ConsultantCommunicationLogInline]


class PermitSubmissionInline(TabularInline):
    model = PermitSubmission
    extra = 0
    fields = ["version", "description", "submission_date", "submitted_by", "authority_receipt_ref"]


class PermitQueryInline(TabularInline):
    model = PermitQuery
    extra = 0
    fields = ["query_date", "subject", "assigned_consultant", "status", "response_date"]


@admin.register(ProjectPermit)
class ProjectPermitAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["reference", "name", "project", "permit_type", "status", "is_critical_path", "expected_approval_date"]
    list_filter = ["permit_type", "status", "is_critical_path"]
    search_fields = ["reference", "name", "authority_name"]
    inlines = [PermitSubmissionInline, PermitQueryInline]


@admin.register(DesignPhase)
class DesignPhaseAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["project", "stage", "status", "total_deliverables", "approved_deliverables", "closeout_checked"]
    list_filter = ["stage", "status"]


class DrawingRevisionInline(TabularInline):
    model = DrawingRevision
    extra = 0
    fields = ["revision_code", "submitted_by", "submitted_date", "approval_state", "reviewed_by", "reviewed_date"]


@admin.register(Drawing)
class DrawingAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["drawing_number", "title", "project", "discipline", "current_revision", "approval_state"]
    list_filter = ["discipline", "approval_state"]
    search_fields = ["drawing_number", "title", "submitted_by"]
    inlines = [DrawingRevisionInline]


@admin.register(DesignReviewMeeting)
class DesignReviewMeetingAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["date", "title", "project", "recorded_by"]
    list_filter = ["project"]
    search_fields = ["title", "attendees"]


class ProcurementPackageInline(TabularInline):
    model = ProcurementPackage
    extra = 0
    fields = ["name", "status", "estimated_budget", "contract_value", "awarded_to", "sort_order"]


class PackageBidderInline(TabularInline):
    model = PackageBidder
    extra = 0
    fields = ["firm_name", "bid_amount", "total_score", "is_recommended", "is_prequalified"]


@admin.register(ProcurementPlan)
class ProcurementPlanAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["project", "strategy", "total_budget"]
    list_filter = ["strategy"]
    inlines = [ProcurementPackageInline]


class SaleableUnitInline(TabularInline):
    model = SaleableUnit
    extra = 0
    fields = ["unit_id", "unit_type", "floor_location", "size_sqm", "asking_price", "status", "sort_order"]


class SalesPhaseTargetInline(TabularInline):
    model = SalesPhaseTarget
    extra = 0
    fields = ["phase_name", "start_date", "end_date", "target_units", "target_revenue", "actual_units", "actual_revenue"]


@admin.register(SalesRevenueForecast)
class SalesRevenueForecastAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["project", "gross_development_value", "sales_launch_date"]
    inlines = [SaleableUnitInline, SalesPhaseTargetInline]


@admin.register(StageGate)
class StageGateAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["name", "project", "status", "sort_order", "scheduled_review_date", "decision_date"]
    list_filter = ["status"]
    search_fields = ["name", "decided_by"]
    filter_horizontal = ["prerequisite_milestones"]


class DocumentVersionInline(TabularInline):
    model = DocumentVersion
    extra = 0
    fields = ["version_label", "uploaded_by", "uploaded_date", "is_current"]


class DocumentTransmittalInline(TabularInline):
    model = DocumentTransmittal
    extra = 0
    fields = ["transmittal_ref", "recipient", "purpose", "sent_date", "acknowledged"]


@admin.register(ProjectDocument)
class ProjectDocumentAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["reference", "title", "project", "folder", "classification", "execution_status", "current_version"]
    list_filter = ["folder", "classification", "execution_status"]
    search_fields = ["reference", "title", "author", "source"]
    inlines = [DocumentVersionInline, DocumentTransmittalInline]


@admin.register(MeetingMinutesArchive)
class MeetingMinutesArchiveAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["date", "title", "series", "project", "recorded_by"]
    list_filter = ["series", "project"]
    search_fields = ["title", "series", "attendees"]


@admin.register(ProjectAnnouncement)
class ProjectAnnouncementAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["subject", "project", "priority", "audience", "is_pinned", "published_at"]
    list_filter = ["priority", "audience", "is_pinned"]
    search_fields = ["subject", "body"]


@admin.register(ProjectDecisionLog)
class ProjectDecisionLogAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["decision_id", "subject", "project", "decided_by", "decision_date", "status"]
    list_filter = ["status"]
    search_fields = ["decision_id", "subject", "decided_by"]


@admin.register(StakeholderUpdate)
class StakeholderUpdateAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["title", "project", "frequency", "report_date", "distribution_group", "prepared_by"]
    list_filter = ["frequency"]
    search_fields = ["title", "prepared_by"]


@admin.register(ProjectReport)
class ProjectReportAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["reference", "title", "project", "report_type", "report_date", "schedule_rag", "budget_rag", "is_frozen"]
    list_filter = ["report_type", "is_frozen", "schedule_rag", "budget_rag"]
    search_fields = ["reference", "title", "prepared_by"]


class FinalAccountEntryInline(TabularInline):
    model = FinalAccountEntry
    extra = 0
    fields = ["contractor_name", "original_contract_value", "approved_variations", "final_settled_amount", "retention_released", "closeout_certificate_issued"]


class SnagListItemInline(TabularInline):
    model = SnagListItem
    extra = 0
    fields = ["location", "description", "responsible_contractor", "status", "resolved_date"]


class WarrantyTrackerInline(TabularInline):
    model = WarrantyTracker
    extra = 0
    fields = ["asset_system", "provider", "warranty_start", "warranty_end"]


@admin.register(ProjectCloseout)
class ProjectCloseoutAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["project", "status", "practical_completion_date", "final_project_cost"]
    list_filter = ["status"]
    inlines = [FinalAccountEntryInline, SnagListItemInline, WarrantyTrackerInline]
