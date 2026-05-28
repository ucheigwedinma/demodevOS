from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from apps.admin_mixins import OrgScopedAdminMixin

from .models import (
    AccessPolicy,
    AuditComplianceSettings,
    AutoEscalationRule,
    BackupDisasterRecoverySettings,
    BoardNotificationTrigger,
    CommunicationBrandingSettings,
    ConfidentialityLabel,
    FunctionalControl,
    ProcurementPolicySettings,
    TaxRate,
    CostCenter,
    DataScope,
    Department,
    Division,
    DocumentAutomationSettings,
    EscalationMatrixSettings,
    EscalationTier,
    FeatureFlagDefinition,
    FeatureFlagOverride,
    IntegrationGovernanceSettings,
    KpiAssignment,
    KpiDefinition,
    MasterDataEntry,
    MilestoneTemplate,
    ModuleActivationSettings,
    NotificationChannelSettings,
    NotificationTemplate,
    Permission,
    PhaseTemplate,
    PlatformEdition,
    PolicyAction,
    PolicyCondition,
    ProfitCenter,
    ProjectGovernanceSettings,
    ProjectTemplate,
    ReportingEngineSettings,
    ReportRun,
    ReportSavedView,
    ReportSubscription,
    ReportTemplate,
    RiskCategory,
    RiskMitigationRule,
    RiskScoreMatrix,
    Role,
    RolePermission,
    RoleScope,
    ScheduledReportDispatch,
    SecuritySettings,
    SlaSeverityTier,
    StageGateChecklistItem,
    StageGateRule,
    SubscriptionAddOn,
    Subsidiary,
    SystemPreferences,
    TaskTemplate,
    TemplateComplianceCheckpoint,
    TemplateMilestone,
    TemplatePhase,
    TemplateRequiredDocument,
    UserScopeAssignment,
)


class DepartmentInline(TabularInline):
    model = Department
    extra = 0
    fields = ("name", "code", "head", "is_active", "sort_order")


@admin.register(Subsidiary)
class SubsidiaryAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("name", "organization", "relationship_type", "status", "city", "country")
    list_filter = ("relationship_type", "status")
    search_fields = ("name", "legal_name")


@admin.register(Division)
class DivisionAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("name", "code", "organization", "unit_category", "location_region", "head", "is_active", "sort_order")
    list_filter = ("unit_category", "is_active", "organization")
    search_fields = ("name", "code")
    inlines = [DepartmentInline]


@admin.register(Department)
class DepartmentAdmin(OrgScopedAdminMixin, ModelAdmin):
    org_lookup = "division__organization"
    list_display = ("name", "code", "division", "head", "is_active", "sort_order")
    list_filter = ("is_active", "division__organization")
    search_fields = ("name", "code")


@admin.register(CostCenter)
class CostCenterAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("code", "name", "organization", "department", "is_active")
    list_filter = ("is_active", "organization")
    search_fields = ("code", "name")


@admin.register(ProfitCenter)
class ProfitCenterAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("code", "name", "organization", "department", "is_active")
    list_filter = ("is_active", "organization", "department")
    search_fields = ("code", "name")


class RolePermissionInline(TabularInline):
    model = RolePermission
    extra = 0
    fields = ("permission", "module", "sub_module", "action")


class RoleScopeInline(TabularInline):
    model = RoleScope
    extra = 0
    fields = ("data_scope", "module", "sub_module")


@admin.register(Permission)
class PermissionAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("key", "module", "sub_module", "action")
    list_filter = ("module", "action")
    search_fields = ("key", "sub_module")


@admin.register(Role)
class RoleAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("name", "slug", "organization", "is_system", "created_at")
    list_filter = ("is_system", "organization")
    search_fields = ("name", "slug")
    inlines = [RolePermissionInline, RoleScopeInline]


@admin.register(DataScope)
class DataScopeAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("key", "label", "is_system", "created_at")
    list_filter = ("is_system",)
    search_fields = ("key", "label")


@admin.register(RoleScope)
class RoleScopeAdmin(OrgScopedAdminMixin, ModelAdmin):
    org_lookup = "role__organization"
    list_display = ("role", "data_scope", "module", "sub_module", "created_at")
    list_filter = ("data_scope", "module", "role__organization")
    search_fields = ("role__name", "sub_module")


@admin.register(UserScopeAssignment)
class UserScopeAssignmentAdmin(OrgScopedAdminMixin, ModelAdmin):
    org_lookup = "user__profile__organization"
    list_display = ("user", "data_scope", "module", "sub_module", "created_by", "created_at")
    list_filter = ("data_scope", "module")
    search_fields = ("user__email", "user__first_name", "user__last_name", "sub_module")


class PolicyConditionInline(TabularInline):
    model = PolicyCondition
    extra = 0
    fields = ("condition_type", "operator", "value", "sort_order", "is_active")


class PolicyActionInline(TabularInline):
    model = PolicyAction
    extra = 0
    fields = ("action_type", "parameters", "message", "sort_order", "is_active")


@admin.register(AccessPolicy)
class AccessPolicyAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("name", "key", "organization", "module", "sub_module", "action", "priority", "is_active", "updated_at")
    list_filter = ("organization", "module", "action", "is_active")
    search_fields = ("name", "key", "description", "sub_module")
    inlines = [PolicyConditionInline, PolicyActionInline]


@admin.register(SecuritySettings)
class SecuritySettingsAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("organization", "mfa_enforced", "ip_restriction_enabled", "updated_at")
    list_filter = ("mfa_enforced", "ip_restriction_enabled", "geo_blocking_enabled")
    readonly_fields = ("created_at", "updated_at")


@admin.register(SystemPreferences)
class SystemPreferencesAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("organization", "theme_mode", "default_currency", "measurement_unit", "updated_at")
    list_filter = ("theme_mode", "measurement_unit", "default_currency")
    readonly_fields = ("created_at", "updated_at")


@admin.register(AuditComplianceSettings)
class AuditComplianceSettingsAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("organization", "audit_logging_enabled", "financial_period_locking", "change_approval_required", "updated_at")
    list_filter = ("audit_logging_enabled", "mandatory_fields_enforced", "financial_period_locking")
    readonly_fields = ("created_at", "updated_at")


@admin.register(NotificationChannelSettings)
class NotificationChannelSettingsAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("organization", "email_enabled", "in_app_enabled", "sms_enabled", "push_enabled", "updated_at")
    list_filter = ("email_enabled", "in_app_enabled", "sms_enabled", "push_enabled")
    readonly_fields = ("created_at", "updated_at")


@admin.register(SlaSeverityTier)
class SlaSeverityTierAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("organization", "level", "response_time_hours", "is_active", "sort_order", "updated_at")
    list_filter = ("level", "is_active")
    search_fields = ("organization__name",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("organization", "code", "name", "channel", "event_key", "severity_tier", "is_active", "is_system", "updated_at")
    list_filter = ("channel", "severity_tier", "is_active", "is_system", "organization")
    search_fields = ("code", "name", "event_key", "subject")
    readonly_fields = ("created_at", "updated_at")


@admin.register(DocumentAutomationSettings)
class DocumentAutomationSettingsAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = (
        "organization",
        "default_signature_provider",
        "default_generation_owner_role",
        "default_generation_phase",
        "default_generation_retention_policy",
        "updated_at",
    )
    readonly_fields = ("created_at", "updated_at")


# ---------------------------------------------------------------------------
# Project Governance
# ---------------------------------------------------------------------------


class TemplatePhaseInline(TabularInline):
    model = TemplatePhase
    extra = 0
    fields = ("name", "sort_order", "duration_days", "weight")


class TemplateMilestoneInline(TabularInline):
    model = TemplateMilestone
    extra = 0
    fields = ("name", "sort_order", "days_from_phase_start")


class TemplateRequiredDocumentInline(TabularInline):
    model = TemplateRequiredDocument
    extra = 0
    fields = ("name", "category", "is_mandatory")


class TemplateComplianceCheckpointInline(TabularInline):
    model = TemplateComplianceCheckpoint
    extra = 0
    fields = ("name", "regulatory_reference", "is_mandatory")


class StageGateChecklistItemInline(TabularInline):
    model = StageGateChecklistItem
    extra = 0
    fields = ("item", "is_mandatory", "sort_order")


@admin.register(ProjectGovernanceSettings)
class ProjectGovernanceSettingsAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("organization", "stage_gate_enforcement_enabled", "require_template_selection", "risk_assessment_mandatory", "updated_at")
    list_filter = ("stage_gate_enforcement_enabled", "require_template_selection", "risk_assessment_mandatory")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ProjectTemplate)
class ProjectTemplateAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("name", "template_type", "organization", "is_active", "is_system")
    list_filter = ("template_type", "is_active", "is_system", "organization")
    search_fields = ("name", "description")
    inlines = [TemplatePhaseInline]
    readonly_fields = ("created_at", "updated_at")


@admin.register(TemplatePhase)
class TemplatePhaseAdmin(OrgScopedAdminMixin, ModelAdmin):
    org_lookup = "template__organization"
    list_display = ("name", "template", "sort_order", "duration_days", "weight")
    list_filter = ("template__template_type", "template__organization")
    search_fields = ("name", "template__name")
    inlines = [TemplateMilestoneInline, TemplateRequiredDocumentInline, TemplateComplianceCheckpointInline]


@admin.register(StageGateRule)
class StageGateRuleAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("name", "stage", "template", "organization", "is_active")
    list_filter = ("stage", "is_active", "organization")
    search_fields = ("name", "description")
    inlines = [StageGateChecklistItemInline]
    readonly_fields = ("created_at", "updated_at")


@admin.register(RiskCategory)
class RiskCategoryAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("name", "category_type", "organization", "is_active")
    list_filter = ("category_type", "is_active", "organization")
    search_fields = ("name", "description")
    readonly_fields = ("created_at", "updated_at")


@admin.register(RiskScoreMatrix)
class RiskScoreMatrixAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("organization", "updated_at")
    readonly_fields = ("created_at", "updated_at")


@admin.register(RiskMitigationRule)
class RiskMitigationRuleAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("risk_category", "severity", "assign_to_role", "escalation_required", "response_time_hours", "is_active")
    list_filter = ("severity", "escalation_required", "is_active", "organization")
    search_fields = ("risk_category__name",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(MasterDataEntry)
class MasterDataEntryAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("category", "code", "label", "is_active", "is_system", "sort_order")
    list_filter = ("category", "is_active", "is_system")
    search_fields = ("code", "label", "description")
    readonly_fields = ("created_at", "updated_at")


# ---------------------------------------------------------------------------
# Module Activation & Feature Flags
# ---------------------------------------------------------------------------


@admin.register(ModuleActivationSettings)
class ModuleActivationSettingsAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("organization", "enabled_modules", "updated_at")
    readonly_fields = ("created_at", "updated_at", "enabled_modules")


class FeatureFlagOverrideInline(TabularInline):
    model = FeatureFlagOverride
    extra = 0
    fields = ("organization", "enabled", "scoped_project_ids", "scoped_regions", "notes")


@admin.register(FeatureFlagDefinition)
class FeatureFlagDefinitionAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("key", "name", "module", "scope", "flag_type", "default_enabled", "minimum_tier", "is_active", "updated_at")
    list_filter = ("module", "scope", "flag_type", "is_active", "minimum_tier")
    search_fields = ("key", "name", "description")
    readonly_fields = ("created_at", "updated_at")
    inlines = [FeatureFlagOverrideInline]


@admin.register(FeatureFlagOverride)
class FeatureFlagOverrideAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("flag", "organization", "enabled", "updated_at")
    list_filter = ("enabled", "flag__module", "flag__scope", "organization")
    search_fields = ("flag__key", "flag__name", "organization__name")
    readonly_fields = ("created_at", "updated_at")


# ---------------------------------------------------------------------------
# Backup & Disaster Recovery
# ---------------------------------------------------------------------------


@admin.register(BackupDisasterRecoverySettings)
class BackupDisasterRecoverySettingsAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = (
        "organization",
        "backup_frequency",
        "backup_region",
        "rto_minutes",
        "rpo_minutes",
        "updated_at",
    )
    list_filter = ("backup_frequency", "backup_region")
    readonly_fields = ("created_at", "updated_at")


# ---------------------------------------------------------------------------
# Integration Governance
# ---------------------------------------------------------------------------


@admin.register(IntegrationGovernanceSettings)
class IntegrationGovernanceSettingsAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = (
        "organization",
        "default_sync_frequency",
        "conflict_resolution_strategy",
        "primary_source_of_truth",
        "sla_target_uptime_pct",
        "updated_at",
    )
    list_filter = ("default_sync_frequency", "conflict_resolution_strategy", "primary_source_of_truth")
    readonly_fields = ("created_at", "updated_at")


# ---------------------------------------------------------------------------
# KPI & Performance
# ---------------------------------------------------------------------------


class KpiAssignmentInline(TabularInline):
    model = KpiAssignment
    extra = 0
    fields = ("role", "department", "target_value", "weight", "is_active")


@admin.register(KpiDefinition)
class KpiDefinitionAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = (
        "code",
        "name",
        "category",
        "unit",
        "direction",
        "frequency",
        "grain",
        "is_canonical",
        "owner_role",
        "owner_user",
        "freshness_sla_minutes",
        "is_active",
        "is_system",
        "sort_order",
    )
    list_filter = (
        "category",
        "unit",
        "direction",
        "frequency",
        "grain",
        "is_canonical",
        "is_active",
        "is_system",
        "organization",
    )
    search_fields = ("name", "code", "description")
    readonly_fields = ("created_at", "updated_at")
    inlines = [KpiAssignmentInline]


@admin.register(KpiAssignment)
class KpiAssignmentAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("kpi", "role", "department", "target_value", "weight", "is_active")
    list_filter = ("is_active", "kpi__category", "organization")
    search_fields = ("kpi__name", "kpi__code", "role__name", "department__name")
    readonly_fields = ("created_at", "updated_at")


# ---------------------------------------------------------------------------
# Reporting Engine
# ---------------------------------------------------------------------------


@admin.register(ReportingEngineSettings)
class ReportingEngineSettingsAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = (
        "organization",
        "page_size",
        "orientation",
        "watermark_enabled",
        "board_pack_enabled",
        "default_dispatch_format",
        "updated_at",
    )
    list_filter = ("page_size", "orientation", "watermark_enabled", "board_pack_enabled")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ConfidentialityLabel)
class ConfidentialityLabelAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("name", "code", "access_level", "color", "watermark_override", "is_active", "is_system", "sort_order")
    list_filter = ("access_level", "is_active", "is_system", "organization")
    search_fields = ("name", "code", "description")
    readonly_fields = ("created_at", "updated_at")


class ScheduledReportDispatchInline(TabularInline):
    model = ScheduledReportDispatch
    extra = 0
    fields = ("name", "frequency", "dispatch_time", "output_format", "is_active")


@admin.register(ReportTemplate)
class ReportTemplateAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = (
        "code",
        "name",
        "module_source",
        "visibility",
        "owner",
        "template_type",
        "output_format",
        "confidentiality_label",
        "is_active",
        "is_system",
    )
    list_filter = (
        "module_source",
        "visibility",
        "template_type",
        "output_format",
        "is_active",
        "is_system",
        "organization",
    )
    search_fields = ("name", "code", "description")
    readonly_fields = ("created_at", "updated_at")
    inlines = [ScheduledReportDispatchInline]


@admin.register(ScheduledReportDispatch)
class ScheduledReportDispatchAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("name", "report_template", "frequency", "dispatch_time", "output_format", "is_active", "last_dispatched_at")
    list_filter = ("frequency", "is_active", "organization")
    search_fields = ("name", "report_template__name", "report_template__code")
    readonly_fields = ("last_dispatched_at", "created_at", "updated_at")


@admin.register(ReportSavedView)
class ReportSavedViewAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("name", "report_template", "user", "rows_per_page", "is_default", "is_active", "updated_at")
    list_filter = ("is_default", "is_active", "organization")
    search_fields = ("name", "report_template__name", "report_template__code", "user__username")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ReportSubscription)
class ReportSubscriptionAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("report_template", "user", "frequency", "delivery_channels", "output_format", "is_active", "last_sent_at", "updated_at")
    list_filter = ("frequency", "output_format", "is_active", "organization")
    search_fields = ("report_template__name", "report_template__code", "user__username")
    readonly_fields = ("last_sent_at", "created_at", "updated_at")


@admin.register(ReportRun)
class ReportRunAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = (
        "id",
        "report_template",
        "requested_by",
        "trigger",
        "status",
        "output_format",
        "row_count",
        "created_at",
    )
    list_filter = ("trigger", "status", "output_format", "organization")
    search_fields = ("report_template__name", "report_template__code", "requested_by__username")
    readonly_fields = (
        "organization",
        "report_template",
        "requested_by",
        "scheduled_dispatch",
        "subscription",
        "trigger",
        "status",
        "output_format",
        "filters",
        "result_summary",
        "row_count",
        "file_path",
        "error_message",
        "created_at",
        "started_at",
        "completed_at",
    )


# ---------------------------------------------------------------------------
# Escalation Matrix
# ---------------------------------------------------------------------------


class EscalationTierInline(TabularInline):
    model = EscalationTier
    extra = 0
    fields = ("severity", "tier_level", "name", "response_time_minutes", "is_active")


@admin.register(EscalationMatrixSettings)
class EscalationMatrixSettingsAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = (
        "organization",
        "escalation_enabled",
        "auto_escalation_enabled",
        "crisis_mode_enabled",
        "board_notification_enabled",
        "updated_at",
    )
    list_filter = ("escalation_enabled", "crisis_mode_enabled", "board_notification_enabled")
    readonly_fields = ("created_at", "updated_at")


@admin.register(EscalationTier)
class EscalationTierAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("name", "severity", "tier_level", "response_time_minutes", "is_active", "organization")
    list_filter = ("severity", "is_active", "organization")
    search_fields = ("name", "description")
    readonly_fields = ("created_at", "updated_at")


@admin.register(AutoEscalationRule)
class AutoEscalationRuleAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("name", "rule_type", "source_tier", "target_tier", "escalate_after_minutes", "is_active")
    list_filter = ("rule_type", "is_active", "organization")
    search_fields = ("name", "description")
    readonly_fields = ("created_at", "updated_at")


@admin.register(BoardNotificationTrigger)
class BoardNotificationTriggerAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("name", "trigger_type", "cooldown_hours", "is_active", "organization")
    list_filter = ("trigger_type", "is_active", "organization")
    search_fields = ("name", "description")
    readonly_fields = ("created_at", "updated_at")


# ---------------------------------------------------------------------------
# Communication & Branding
# ---------------------------------------------------------------------------


@admin.register(CommunicationBrandingSettings)
class CommunicationBrandingSettingsAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = (
        "organization",
        "email_sender_name",
        "sms_enabled",
        "letterhead_paper_size",
        "signature_reminder_enabled",
        "updated_at",
    )
    list_filter = ("sms_enabled", "letterhead_paper_size", "signature_reminder_enabled")
    readonly_fields = ("created_at", "updated_at")


@admin.register(PlatformEdition)
class PlatformEditionAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("key", "name", "tier_level", "max_users", "monthly_price", "is_active")
    list_filter = ("is_active", "is_custom", "support_tier")
    search_fields = ("key", "name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(SubscriptionAddOn)
class SubscriptionAddOnAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("key", "name", "add_on_type", "monthly_price", "is_active", "sort_order")
    list_filter = ("add_on_type", "is_active")
    search_fields = ("key", "name")
    readonly_fields = ("created_at",)


@admin.register(PhaseTemplate)
class PhaseTemplateAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("name", "sort_order", "weight", "budget_pct", "estimated_duration_days", "phase_owner_role")
    list_editable = ("sort_order", "weight", "budget_pct")
    ordering = ("sort_order",)
    search_fields = ("name",)
    fieldsets = (
        ("Section A: Overview & Metadata", {
            "fields": ("name", "description", "sort_order", "weight", "budget_pct",
                       "objective", "estimated_duration_days", "phase_owner_role"),
        }),
        ("Section B: Governance & Stakeholders", {
            "classes": ("grp-collapse", "grp-open"),
            "fields": ("raci_matrix", "approval_authority"),
        }),
        ("Section C: Scope & Deliverables", {
            "classes": ("grp-collapse", "grp-open"),
            "fields": ("key_tasks", "deliverables", "out_of_scope"),
        }),
        ("Section D: Resource & Risk Management", {
            "classes": ("grp-collapse", "grp-open"),
            "fields": ("resource_requirements", "phase_risks", "budget_notes"),
        }),
        ("Section E: Quality & Completion Criteria", {
            "classes": ("grp-collapse", "grp-open"),
            "fields": ("success_metrics", "exit_criteria", "lessons_learned_prompt"),
        }),
    )


@admin.register(MilestoneTemplate)
class MilestoneTemplateAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("name", "sort_order", "phase_sort_order", "reference_code", "owner_role")
    list_editable = ("sort_order", "phase_sort_order")
    ordering = ("sort_order",)
    search_fields = ("name",)
    fieldsets = (
        ("Section A: Milestone Identification", {
            "fields": ("name", "description", "sort_order", "phase_sort_order", "reference_code"),
        }),
        ("Section B: Scheduling & Status", {
            "classes": ("grp-collapse", "grp-open"),
            "fields": ("typical_offset_days",),
        }),
        ("Section C: Completion Requirements", {
            "classes": ("grp-collapse", "grp-open"),
            "fields": ("success_criteria", "key_deliverables", "predecessors", "successors"),
        }),
        ("Section D: Accountability & Approval", {
            "classes": ("grp-collapse", "grp-open"),
            "fields": ("owner_role", "approver_role", "stakeholders_to_notify"),
        }),
    )


@admin.register(TaskTemplate)
class TaskTemplateAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("name", "assigned_role", "priority", "sort_order", "phase_sort_order", "reference_code")
    list_editable = ("sort_order", "phase_sort_order")
    list_filter = ("priority",)
    ordering = ("sort_order",)
    search_fields = ("name",)
    fieldsets = (
        ("Section A: Task Definition & Context", {
            "fields": ("name", "description", "sort_order", "phase_sort_order", "reference_code"),
        }),
        ("Section B: Assignment & Ownership", {
            "classes": ("grp-collapse", "grp-open"),
            "fields": ("assigned_role", "priority", "reviewer_role", "collaborators"),
        }),
        ("Section C: Scheduling & Effort", {
            "classes": ("grp-collapse", "grp-open"),
            "fields": ("estimated_effort_hours",),
        }),
        ("Section D: Execution Details", {
            "classes": ("grp-collapse", "grp-open"),
            "fields": ("predecessors", "successors", "definition_of_done"),
        }),
        ("Section E: Resources & Attachments", {
            "classes": ("grp-collapse", "grp-open"),
            "fields": ("tools_required", "reference_links"),
        }),
    )


@admin.register(FunctionalControl)
class FunctionalControlAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["organization", "projects_enabled", "construction_enabled", "procurement_enabled", "finance_enabled", "boq_lifecycle_enabled"]
    fieldsets = (
        ("Projects", {"fields": (
            "projects_enabled", "project_pipeline", "project_feasibility",
            "project_land_acquisition", "project_dev_budget", "project_financing",
            "project_dev_schedule", "project_consultants", "project_approvals_permits",
            "project_design_management", "project_procurement_planning",
            "project_sales_forecast", "project_governance", "project_milestones_gates",
            "project_document_control", "project_communications", "project_reports", "project_closeout",
        )}),
        ("Construction", {"fields": (
            "construction_enabled", "construction_schedule", "construction_tasks",
            "construction_work_packages", "construction_field_operations",
            "construction_quality_control", "construction_equipment",
            "construction_contractor_mgmt", "construction_hse", "construction_rfi",
            "construction_site_instructions", "construction_testing_commissioning",
            "construction_cost_control", "construction_reports",
        )}),
        ("Procurement", {"fields": ("procurement_enabled", "procurement_vendors", "procurement_requisitions", "procurement_purchase_orders", "procurement_rfq")}),
        ("Finance", {"fields": ("finance_enabled", "finance_invoices", "finance_bills", "finance_budgets", "finance_banking", "finance_investors")}),
        ("Inventory", {"fields": ("inventory_enabled", "inventory_boq", "inventory_warehouses", "inventory_items")}),
        ("HR", {"fields": ("hr_enabled", "hr_employees", "hr_payroll", "hr_attendance")}),
        ("Other Domains", {"fields": ("crm_enabled", "properties_enabled", "support_desk_enabled")}),
        ("BOQ Lifecycle", {"fields": ("boq_lifecycle_enabled", "boq_lock_after_contract", "boq_require_approval_for_tender")}),
        ("3-Way Matching", {"fields": ("three_way_match_enabled", "three_way_match_tolerance_pct", "three_way_match_block_payment")}),
    )


@admin.register(TaxRate)
class TaxRateAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["name", "tax_type", "rate_pct", "applies_to", "is_default", "is_active"]
    list_filter = ["tax_type", "applies_to", "is_active", "is_default"]
    search_fields = ["name"]


@admin.register(ProcurementPolicySettings)
class ProcurementPolicySettingsAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["organization", "po_auto_approve_limit", "min_quotes_required", "require_grn_before_payment"]
    fieldsets = (
        ("PO Thresholds", {"fields": ("po_auto_approve_limit", "po_single_approval_limit", "po_director_approval_limit")}),
        ("Quote Requirements", {"fields": ("min_quotes_required", "min_quotes_threshold", "sole_source_justification_required")}),
        ("Vendor Rules", {"fields": ("require_vendor_compliance", "block_blacklisted_vendors", "vendor_performance_minimum")}),
        ("Budget Controls", {"fields": ("require_budget_code", "block_over_budget_po")}),
        ("GRN Controls", {"fields": ("require_grn_before_payment", "grn_quantity_tolerance_pct")}),
    )
