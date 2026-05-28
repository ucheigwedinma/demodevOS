from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
                    AuditComplianceSettingsView,
                    AuditLogListView,
                    AutoEscalationRuleViewSet,
                    BackupDisasterRecoverySettingsView,
                    BoardNotificationTriggerViewSet,
                    CommunicationBrandingSettingsView,
                    CompanyProfileView,
                    FunctionalControlView,
                    ProcurementPolicySettingsView,
                    TaxRateViewSet,
                    ConfidentialityLabelViewSet,
                    CostCenterViewSet,
                    DepartmentListView,
                    DepartmentViewSet,
                    DivisionViewSet,
                    DocumentAutomationSettingsView,
                    EscalationMatrixSettingsView,
                    EscalationTierViewSet,
                    FeatureFlagDashboardView,
                    FeatureFlagDefinitionViewSet,
                    FeatureFlagOverrideViewSet,
                    IntegrationGovernanceSettingsView,
                    KpiAssignmentViewSet,
                    KpiDefinitionViewSet,
                    MasterDataEntryViewSet,
                    MilestoneTemplateViewSet,
                    ModuleActivationSettingsView,
                    MyScheduledReportsView,
                    NotificationChannelSettingsView,
                    NotificationTemplateViewSet,
                    NotificationWorkflowCatalogView,
                    PermissionRegistryView,
                    PhaseTemplateViewSet,
                    PlatformEditionViewSet,
                    ProfitCenterViewSet,
                    ProjectGovernanceSettingsView,
                    ProjectTemplateViewSet,
                    ReportingEngineSettingsView,
                    ReportLibraryView,
                    ReportRunViewSet,
                    ReportSavedViewViewSet,
                    ReportSubscriptionViewSet,
                    ReportTemplateViewSet,
                    RiskCategoryViewSet,
                    RiskMitigationRuleViewSet,
                    RiskScoreMatrixView,
                    RoleViewSet,
                    ScheduledReportDispatchViewSet,
                    SecuritySettingsView,
                    SlaSeverityTierViewSet,
                    StageGateChecklistItemViewSet,
                    StageGateRuleViewSet,
                    StatusBadgeRegistryView,
                    SubsidiaryViewSet,
                    SystemPreferencesView,
                    TaskTemplateViewSet,
                    TemplateActivityViewSet,
                    TemplateDependencyViewSet,
                    TemplatePhaseListViewSet,
                    TemplatePlanScenarioViewSet,
                    TemplateScheduleSettingsView,
)

router = DefaultRouter()
router.register(r"platform-editions", PlatformEditionViewSet, basename="platform-edition")
router.register(r"subsidiaries", SubsidiaryViewSet, basename="subsidiary")
router.register(r"master-data", MasterDataEntryViewSet, basename="master-data")
router.register(r"divisions", DivisionViewSet, basename="division")
router.register(r"cost-centers", CostCenterViewSet, basename="cost-center")
router.register(r"profit-centers", ProfitCenterViewSet, basename="profit-center")
router.register(r"roles", RoleViewSet, basename="role")
router.register(r"project-templates", ProjectTemplateViewSet, basename="project-template")
router.register(r"stage-gate-rules", StageGateRuleViewSet, basename="stage-gate-rule")
router.register(r"risk-categories", RiskCategoryViewSet, basename="risk-category")
router.register(r"risk-mitigation-rules", RiskMitigationRuleViewSet, basename="risk-mitigation-rule")
router.register(r"notifications/sla-tiers", SlaSeverityTierViewSet, basename="sla-severity-tier")
router.register(r"notifications/templates", NotificationTemplateViewSet, basename="notification-template")
router.register(r"feature-flags/overrides", FeatureFlagOverrideViewSet, basename="feature-flag-override")
router.register(r"feature-flags/definitions", FeatureFlagDefinitionViewSet, basename="feature-flag-definition")
router.register(r"kpi-definitions", KpiDefinitionViewSet, basename="kpi-definition")
router.register(r"kpi-assignments", KpiAssignmentViewSet, basename="kpi-assignment")
router.register(r"report-templates", ReportTemplateViewSet, basename="report-template")
router.register(r"report-runs", ReportRunViewSet, basename="report-run")
router.register(r"report-saved-views", ReportSavedViewViewSet, basename="report-saved-view")
router.register(r"report-subscriptions", ReportSubscriptionViewSet, basename="report-subscription")
router.register(r"confidentiality-labels", ConfidentialityLabelViewSet, basename="confidentiality-label")
router.register(r"scheduled-dispatches", ScheduledReportDispatchViewSet, basename="scheduled-dispatch")
router.register(r"escalation-tiers", EscalationTierViewSet, basename="escalation-tier")
router.register(r"auto-escalation-rules", AutoEscalationRuleViewSet, basename="auto-escalation-rule")
router.register(r"board-notification-triggers", BoardNotificationTriggerViewSet, basename="board-notification-trigger")
router.register(r"entity-templates/phases", PhaseTemplateViewSet, basename="phase-template")
router.register(r"project-templates/phases", TemplatePhaseListViewSet, basename="template-phase-list")
router.register(r"entity-templates/milestones", MilestoneTemplateViewSet, basename="milestone-template")
router.register(r"entity-templates/tasks", TaskTemplateViewSet, basename="task-template")

activity_router = DefaultRouter()
activity_router.register(r"", TemplateActivityViewSet, basename="template-activity")

dependency_router = DefaultRouter()
dependency_router.register(r"", TemplateDependencyViewSet, basename="template-dependency")

scenario_router = DefaultRouter()
scenario_router.register(r"", TemplatePlanScenarioViewSet, basename="template-scenario")

checklist_router = DefaultRouter()
checklist_router.register(r"", StageGateChecklistItemViewSet, basename="stage-gate-checklist-item")

dept_router = DefaultRouter()
dept_router.register(r"", DepartmentViewSet, basename="department")

urlpatterns = [
    path("company-profile/", CompanyProfileView.as_view(), name="company-profile"),
    path("security/", SecuritySettingsView.as_view(), name="security-settings"),
    path("preferences/", SystemPreferencesView.as_view(), name="system-preferences"),
    path("document-automation/", DocumentAutomationSettingsView.as_view(), name="document-automation-settings"),
    path("notifications/channels/", NotificationChannelSettingsView.as_view(), name="notification-channel-settings"),
    path("notifications/workflow-catalog/", NotificationWorkflowCatalogView.as_view(), name="notification-workflow-catalog"),
    path("audit/", AuditComplianceSettingsView.as_view(), name="audit-compliance-settings"),
    path("audit/logs/", AuditLogListView.as_view(), name="audit-log-list"),
    path("permission-registry/", PermissionRegistryView.as_view(), name="permission-registry"),
    path("project-governance/", ProjectGovernanceSettingsView.as_view(), name="project-governance-settings"),
    path("risk-score-matrix/", RiskScoreMatrixView.as_view(), name="risk-score-matrix"),
    path("module-activation/", ModuleActivationSettingsView.as_view(), name="module-activation-settings"),
    path("feature-flags/dashboard/", FeatureFlagDashboardView.as_view(), name="feature-flag-dashboard"),
    path("backup-dr/", BackupDisasterRecoverySettingsView.as_view(), name="backup-dr-settings"),
    path("integration-governance/", IntegrationGovernanceSettingsView.as_view(), name="integration-governance-settings"),
    path("reporting-engine/", ReportingEngineSettingsView.as_view(), name="reporting-engine-settings"),
    path("reports/library/", ReportLibraryView.as_view(), name="report-library"),
    path("reports/my-scheduled/", MyScheduledReportsView.as_view(), name="my-scheduled-reports"),
    path("escalation-matrix/", EscalationMatrixSettingsView.as_view(), name="escalation-matrix-settings"),
    path("communication-branding/", CommunicationBrandingSettingsView.as_view(), name="communication-branding-settings"),
    path("functional-controls/", FunctionalControlView.as_view(), name="functional-controls"),
    path("procurement-policy/", ProcurementPolicySettingsView.as_view(), name="procurement-policy"),
    path("tax-rates/", TaxRateViewSet.as_view({"get": "list", "post": "create"}), name="tax-rate-list"),
    path("tax-rates/<int:pk>/", TaxRateViewSet.as_view({"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}), name="tax-rate-detail"),
    path("status-badges/", StatusBadgeRegistryView.as_view(), name="status-badge-registry"),
    path("departments/", DepartmentListView.as_view(), name="department-list"),
    path(
        "divisions/<int:division_pk>/departments/",
        include(dept_router.urls),
    ),
    path(
        "stage-gate-rules/<int:rule_pk>/checklist-items/",
        include(checklist_router.urls),
    ),
    path(
        "project-templates/phases/<int:phase_pk>/activities/",
        include(activity_router.urls),
    ),
    path(
        "project-templates/<int:template_pk>/dependencies/",
        include(dependency_router.urls),
    ),
    path(
        "project-templates/<int:template_pk>/schedule-settings/",
        TemplateScheduleSettingsView.as_view(),
        name="template-schedule-settings",
    ),
    path(
        "project-templates/<int:template_pk>/scenarios/",
        include(scenario_router.urls),
    ),
] + router.urls
