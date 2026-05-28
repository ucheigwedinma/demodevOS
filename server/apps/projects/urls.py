from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .blueprint_api import (
                            BlueprintActivityViewSet,
                            BlueprintDependencyViewSet,
                            BlueprintPhaseViewSet,
                            BlueprintScenarioViewSet,
                            BlueprintTaskViewSet,
                            BlueprintViewSet,
)
from .views import (
                            CommissioningDashboardView,
                            CommissioningPlanViewSet,
                            CommissioningPunchItemViewSet,
                            EquipmentDeploymentLogViewSet,
                            EquipmentMaintenanceLogViewSet,
                            HSEDashboardView,
                            HSEIncidentViewSet,
                            HSEPermitToWorkViewSet,
                            HSEToolboxTalkViewSet,
                            NonConformanceReportViewSet,
                            TestRecordViewSet,
                            DevelopmentBudgetCategoryViewSet,
                            DevelopmentBudgetViewSet,
                            FeasibilityStudyViewSet,
                            FinancingCovenantViewSet,
                            FinancingDrawdownViewSet,
                            FinancingRepaymentViewSet,
                            FinancingSourceViewSet,
                            ConsultantCommunicationLogViewSet,
                            ConsultantDeliverableViewSet,
                            ConsultantPaymentMilestoneViewSet,
                            DesignPhaseViewSet,
                            DesignReviewMeetingViewSet,
                            DrawingRevisionViewSet,
                            DrawingViewSet,
                            PackageBidderViewSet,
                            ProcurementPackageViewSet,
                            ProcurementPlanViewSet,
                            SaleableUnitViewSet,
                            SalesPhaseTargetViewSet,
                            SalesRevenueForecastViewSet,
                            StageGateViewSet,
                            DocumentTransmittalViewSet,
                            DocumentVersionViewSet,
                            MeetingMinutesArchiveViewSet,
                            ProjectDocumentViewSet,
                            ProjectAnnouncementViewSet,
                            ProjectDecisionLogViewSet,
                            StakeholderUpdateViewSet,
                            ProjectReportViewSet,
                            ConstructionReportViewSet,
                            CostCodeBudgetViewSet,
                            CostTransactionViewSet,
                            RFIViewSet,
                            RFICommentViewSet,
                            SiteInstructionViewSet,
                            FinalAccountEntryViewSet,
                            ProjectCloseoutViewSet,
                            SnagListItemViewSet,
                            WarrantyTrackerViewSet,
                            PermitQueryViewSet,
                            PermitSubmissionViewSet,
                            ProjectPermitViewSet,
                            ProjectConsultantViewSet,
                            LandAcquisitionViewSet,
                            LandPaymentMilestoneViewSet,
                            PipelineOpportunityViewSet,
                            ProjectSetupConfigViewSet,
                            ProjectTeamMemberViewSet,
                            PhaseCostEntryViewSet,
                            PhaseMilestoneViewSet,
                            PhaseTaskViewSet,
                            ProjectContractorManagementViewSet,
                            ProjectDailySiteReportViewSet,
                            ProjectDeliveryConfirmationViewSet,
                            ProjectEquipmentViewSet,
                            ProjectExecutionInspectionViewSet,
                            ProjectFieldEscalationViewSet,
                            ProjectMilestoneApprovalDecisionViewSet,
                            ProjectMilestoneApprovalRuleViewSet,
                            ProjectPhaseDependencyViewSet,
                            ProjectPhaseViewSet,
                            ProjectPlanningInsightViewSet,
                            ProjectRiskRegisterViewSet,
                            ProjectScheduleDelayLogViewSet,
                            ProjectTaskWorkspaceViewSet,
                            ProjectVariationOrderViewSet,
                            ProjectViewSet,
                            ProjectWorkforceLogViewSet,
                            ProjectWorkPackageWorkspaceViewSet,
                            QualityCheckTemplateViewSet,
                            QualityControlDashboardView,
                            QualityPlanViewSet,
)

router = DefaultRouter()
router.register(r"", ProjectViewSet, basename="project")

planning_insight_router = DefaultRouter()
planning_insight_router.register(r"", ProjectPlanningInsightViewSet, basename="project-planning-insight")

task_workspace_router = DefaultRouter()
task_workspace_router.register(r"", ProjectTaskWorkspaceViewSet, basename="project-task-workspace")

work_package_workspace_router = DefaultRouter()
work_package_workspace_router.register(
    r"",
    ProjectWorkPackageWorkspaceViewSet,
    basename="project-work-package-workspace",
)

contractor_management_router = DefaultRouter()
contractor_management_router.register(
    r"",
    ProjectContractorManagementViewSet,
    basename="project-contractor-management",
)

risk_register_router = DefaultRouter()
risk_register_router.register(r"", ProjectRiskRegisterViewSet, basename="project-risk-register")

variation_router = DefaultRouter()
variation_router.register(r"", ProjectVariationOrderViewSet, basename="project-variation-order")

phase_router = DefaultRouter()
phase_router.register(r"", ProjectPhaseViewSet, basename="project-phase")

milestone_router = DefaultRouter()
milestone_router.register(r"", PhaseMilestoneViewSet, basename="phase-milestone")

task_router = DefaultRouter()
task_router.register(r"", PhaseTaskViewSet, basename="phase-task")

cost_router = DefaultRouter()
cost_router.register(r"", PhaseCostEntryViewSet, basename="phase-cost")

phase_dependency_router = DefaultRouter()
phase_dependency_router.register(r"", ProjectPhaseDependencyViewSet, basename="project-phase-dependency")

approval_rule_router = DefaultRouter()
approval_rule_router.register(r"", ProjectMilestoneApprovalRuleViewSet, basename="project-milestone-approval-rule")

approval_decision_router = DefaultRouter()
approval_decision_router.register(r"", ProjectMilestoneApprovalDecisionViewSet, basename="project-milestone-approval-decision")

delay_log_router = DefaultRouter()
delay_log_router.register(r"", ProjectScheduleDelayLogViewSet, basename="project-schedule-delay-log")

workforce_router = DefaultRouter()
workforce_router.register(r"", ProjectWorkforceLogViewSet, basename="project-workforce-log")

daily_report_router = DefaultRouter()
daily_report_router.register(r"", ProjectDailySiteReportViewSet, basename="project-daily-site-report")

delivery_router = DefaultRouter()
delivery_router.register(r"", ProjectDeliveryConfirmationViewSet, basename="project-delivery-confirmation")

inspection_router = DefaultRouter()
inspection_router.register(r"", ProjectExecutionInspectionViewSet, basename="project-execution-inspection")

escalation_router = DefaultRouter()
escalation_router.register(r"", ProjectFieldEscalationViewSet, basename="project-field-escalation")

issues_router = DefaultRouter()
issues_router.register(r"", ProjectFieldEscalationViewSet, basename="project-issue")

blueprint_router = DefaultRouter()
blueprint_router.register(r"", BlueprintViewSet, basename="blueprint")

blueprint_phase_router = DefaultRouter()
blueprint_phase_router.register(r"", BlueprintPhaseViewSet, basename="blueprint-phase")

blueprint_activity_router = DefaultRouter()
blueprint_activity_router.register(r"", BlueprintActivityViewSet, basename="blueprint-activity")

blueprint_task_router = DefaultRouter()
blueprint_task_router.register(r"", BlueprintTaskViewSet, basename="blueprint-task")

blueprint_dep_router = DefaultRouter()
blueprint_dep_router.register(r"", BlueprintDependencyViewSet, basename="blueprint-dependency")

blueprint_scenario_router = DefaultRouter()
blueprint_scenario_router.register(r"", BlueprintScenarioViewSet, basename="blueprint-scenario")

equipment_router = DefaultRouter()
equipment_router.register(r"", ProjectEquipmentViewSet, basename="project-equipment")

equipment_maintenance_router = DefaultRouter()
equipment_maintenance_router.register(r"", EquipmentMaintenanceLogViewSet, basename="equipment-maintenance-log")

equipment_deployment_router = DefaultRouter()
equipment_deployment_router.register(r"", EquipmentDeploymentLogViewSet, basename="equipment-deployment-log")

quality_plan_router = DefaultRouter()
quality_plan_router.register(r"", QualityPlanViewSet, basename="quality-plan")

quality_check_router = DefaultRouter()
quality_check_router.register(r"", QualityCheckTemplateViewSet, basename="quality-check-template")

ncr_router = DefaultRouter()
ncr_router.register(r"", NonConformanceReportViewSet, basename="ncr")

pipeline_router = DefaultRouter()
pipeline_router.register(r"", PipelineOpportunityViewSet, basename="pipeline-opportunity")

setup_config_router = DefaultRouter()
setup_config_router.register(r"", ProjectSetupConfigViewSet, basename="project-setup-config")

team_member_router = DefaultRouter()
team_member_router.register(r"", ProjectTeamMemberViewSet, basename="project-team-member")

feasibility_router = DefaultRouter()
feasibility_router.register(r"", FeasibilityStudyViewSet, basename="feasibility-study")

land_acquisition_router = DefaultRouter()
land_acquisition_router.register(r"", LandAcquisitionViewSet, basename="land-acquisition")

land_payment_router = DefaultRouter()
land_payment_router.register(r"", LandPaymentMilestoneViewSet, basename="land-payment-milestone")

dev_budget_router = DefaultRouter()
dev_budget_router.register(r"", DevelopmentBudgetViewSet, basename="development-budget")

dev_budget_category_router = DefaultRouter()
dev_budget_category_router.register(r"", DevelopmentBudgetCategoryViewSet, basename="dev-budget-category")

financing_router = DefaultRouter()
financing_router.register(r"", FinancingSourceViewSet, basename="financing-source")

financing_drawdown_router = DefaultRouter()
financing_drawdown_router.register(r"", FinancingDrawdownViewSet, basename="financing-drawdown")

financing_repayment_router = DefaultRouter()
financing_repayment_router.register(r"", FinancingRepaymentViewSet, basename="financing-repayment")

financing_covenant_router = DefaultRouter()
financing_covenant_router.register(r"", FinancingCovenantViewSet, basename="financing-covenant")

consultant_router = DefaultRouter()
consultant_router.register(r"", ProjectConsultantViewSet, basename="project-consultant")

consultant_payment_router = DefaultRouter()
consultant_payment_router.register(r"", ConsultantPaymentMilestoneViewSet, basename="consultant-payment")

consultant_deliverable_router = DefaultRouter()
consultant_deliverable_router.register(r"", ConsultantDeliverableViewSet, basename="consultant-deliverable")

consultant_comms_router = DefaultRouter()
consultant_comms_router.register(r"", ConsultantCommunicationLogViewSet, basename="consultant-comms")

permit_router = DefaultRouter()
permit_router.register(r"", ProjectPermitViewSet, basename="project-permit")

permit_submission_router = DefaultRouter()
permit_submission_router.register(r"", PermitSubmissionViewSet, basename="permit-submission")

permit_query_router = DefaultRouter()
permit_query_router.register(r"", PermitQueryViewSet, basename="permit-query")

design_phase_router = DefaultRouter()
design_phase_router.register(r"", DesignPhaseViewSet, basename="design-phase")

drawing_router = DefaultRouter()
drawing_router.register(r"", DrawingViewSet, basename="drawing")

drawing_revision_router = DefaultRouter()
drawing_revision_router.register(r"", DrawingRevisionViewSet, basename="drawing-revision")

design_meeting_router = DefaultRouter()
design_meeting_router.register(r"", DesignReviewMeetingViewSet, basename="design-meeting")

procurement_plan_router = DefaultRouter()
procurement_plan_router.register(r"", ProcurementPlanViewSet, basename="procurement-plan")

procurement_package_router = DefaultRouter()
procurement_package_router.register(r"", ProcurementPackageViewSet, basename="procurement-package")

package_bidder_router = DefaultRouter()
package_bidder_router.register(r"", PackageBidderViewSet, basename="package-bidder")

sales_forecast_router = DefaultRouter()
sales_forecast_router.register(r"", SalesRevenueForecastViewSet, basename="sales-forecast")

saleable_unit_router = DefaultRouter()
saleable_unit_router.register(r"", SaleableUnitViewSet, basename="saleable-unit")

sales_phase_target_router = DefaultRouter()
sales_phase_target_router.register(r"", SalesPhaseTargetViewSet, basename="sales-phase-target")

stage_gate_router = DefaultRouter()
stage_gate_router.register(r"", StageGateViewSet, basename="stage-gate")

document_router = DefaultRouter()
document_router.register(r"", ProjectDocumentViewSet, basename="project-document")

document_version_router = DefaultRouter()
document_version_router.register(r"", DocumentVersionViewSet, basename="document-version")

document_transmittal_router = DefaultRouter()
document_transmittal_router.register(r"", DocumentTransmittalViewSet, basename="document-transmittal")

meeting_minutes_router = DefaultRouter()
meeting_minutes_router.register(r"", MeetingMinutesArchiveViewSet, basename="meeting-minutes")

announcement_router = DefaultRouter()
announcement_router.register(r"", ProjectAnnouncementViewSet, basename="project-announcement")

decision_log_router = DefaultRouter()
decision_log_router.register(r"", ProjectDecisionLogViewSet, basename="project-decision-log")

stakeholder_update_router = DefaultRouter()
stakeholder_update_router.register(r"", StakeholderUpdateViewSet, basename="stakeholder-update")

report_router = DefaultRouter()
report_router.register(r"", ProjectReportViewSet, basename="project-report")

closeout_router = DefaultRouter()
closeout_router.register(r"", ProjectCloseoutViewSet, basename="project-closeout")

final_account_router = DefaultRouter()
final_account_router.register(r"", FinalAccountEntryViewSet, basename="final-account")

snag_router = DefaultRouter()
snag_router.register(r"", SnagListItemViewSet, basename="snag-item")

warranty_router = DefaultRouter()
warranty_router.register(r"", WarrantyTrackerViewSet, basename="warranty-tracker")

construction_report_router = DefaultRouter()
construction_report_router.register(r"", ConstructionReportViewSet, basename="construction-report")

rfi_router = DefaultRouter()
rfi_router.register(r"", RFIViewSet, basename="rfi")

rfi_comment_router = DefaultRouter()
rfi_comment_router.register(r"", RFICommentViewSet, basename="rfi-comment")

site_instruction_router = DefaultRouter()
site_instruction_router.register(r"", SiteInstructionViewSet, basename="site-instruction")

hse_incident_router = DefaultRouter()
hse_incident_router.register(r"", HSEIncidentViewSet, basename="hse-incident")

hse_permit_router = DefaultRouter()
hse_permit_router.register(r"", HSEPermitToWorkViewSet, basename="hse-permit")

hse_toolbox_router = DefaultRouter()
hse_toolbox_router.register(r"", HSEToolboxTalkViewSet, basename="hse-toolbox-talk")

commissioning_plan_router = DefaultRouter()
commissioning_plan_router.register(r"", CommissioningPlanViewSet, basename="commissioning-plan")

commissioning_test_router = DefaultRouter()
commissioning_test_router.register(r"", TestRecordViewSet, basename="commissioning-test")

commissioning_punch_router = DefaultRouter()
commissioning_punch_router.register(r"", CommissioningPunchItemViewSet, basename="commissioning-punch-item")

cost_budget_router = DefaultRouter()
cost_budget_router.register(r"", CostCodeBudgetViewSet, basename="cost-code-budget")

cost_transaction_router = DefaultRouter()
cost_transaction_router.register(r"", CostTransactionViewSet, basename="cost-transaction")

from .views import PredictiveIntelligenceView, ResourceOptimizationView

urlpatterns = [
    # Resource Optimization & Predictive Intelligence
    path("resource-optimization/", ResourceOptimizationView.as_view(), name="resource-optimization"),
    path("predictive-intelligence/", PredictiveIntelligenceView.as_view(), name="predictive-intelligence"),
    # Blueprint routes
    path("blueprints/", include(blueprint_router.urls)),
    path("blueprints/<int:blueprint_pk>/phases/", include(blueprint_phase_router.urls)),
    path("blueprints/<int:blueprint_pk>/phases/<int:phase_pk>/activities/", include(blueprint_activity_router.urls)),
    path("blueprints/<int:blueprint_pk>/phases/<int:phase_pk>/activities/<int:activity_pk>/tasks/", include(blueprint_task_router.urls)),
    path("blueprints/<int:blueprint_pk>/dependencies/", include(blueprint_dep_router.urls)),
    path("blueprints/<int:blueprint_pk>/scenarios/", include(blueprint_scenario_router.urls)),
    # Existing routes
    path("planning-insights/", include(planning_insight_router.urls)),
    path("tasks/", include(task_workspace_router.urls)),
    path("work-packages/", include(work_package_workspace_router.urls)),
    path("contractor-management/", include(contractor_management_router.urls)),
    path("risk-register/", include(risk_register_router.urls)),
    path("variations/", include(variation_router.urls)),
    path("field-operations/workforce/", include(workforce_router.urls)),
    path("field-operations/reports/", include(daily_report_router.urls)),
    path("field-operations/deliveries/", include(delivery_router.urls)),
    path("field-operations/quality-inspections/", include(inspection_router.urls)),
    path("field-operations/escalations/", include(escalation_router.urls)),
    path("issues/", include(issues_router.urls)),
    path("equipment/", include(equipment_router.urls)),
    path("equipment/<int:equipment_pk>/maintenance-logs/", include(equipment_maintenance_router.urls)),
    path("equipment/<int:equipment_pk>/deployment-logs/", include(equipment_deployment_router.urls)),
    path("quality-plans/", include(quality_plan_router.urls)),
    path("quality-plans/<int:plan_pk>/checks/", include(quality_check_router.urls)),
    path("ncrs/", include(ncr_router.urls)),
    path("quality-control/dashboard/", QualityControlDashboardView.as_view(), name="quality-control-dashboard"),
    path("pipeline/", include(pipeline_router.urls)),
    path("setup/", include(setup_config_router.urls)),
    path("team-members/", include(team_member_router.urls)),
    path("feasibility/", include(feasibility_router.urls)),
    path("land-acquisitions/", include(land_acquisition_router.urls)),
    path("land-acquisitions/<int:acquisition_pk>/payments/", include(land_payment_router.urls)),
    path("dev-budgets/", include(dev_budget_router.urls)),
    path("dev-budgets/<int:budget_pk>/categories/", include(dev_budget_category_router.urls)),
    path("financing/", include(financing_router.urls)),
    path("financing/<int:source_pk>/drawdowns/", include(financing_drawdown_router.urls)),
    path("financing/<int:source_pk>/repayments/", include(financing_repayment_router.urls)),
    path("financing/<int:source_pk>/covenants/", include(financing_covenant_router.urls)),
    path("consultants/", include(consultant_router.urls)),
    path("consultants/<int:consultant_pk>/payment-milestones/", include(consultant_payment_router.urls)),
    path("consultants/<int:consultant_pk>/deliverables/", include(consultant_deliverable_router.urls)),
    path("consultants/<int:consultant_pk>/communications/", include(consultant_comms_router.urls)),
    path("permits/", include(permit_router.urls)),
    path("permits/<int:permit_pk>/submissions/", include(permit_submission_router.urls)),
    path("permits/<int:permit_pk>/queries/", include(permit_query_router.urls)),
    path("design-phases/", include(design_phase_router.urls)),
    path("drawings/", include(drawing_router.urls)),
    path("drawings/<int:drawing_pk>/revisions/", include(drawing_revision_router.urls)),
    path("design-meetings/", include(design_meeting_router.urls)),
    path("procurement-plans/", include(procurement_plan_router.urls)),
    path("procurement-plans/<int:plan_pk>/packages/", include(procurement_package_router.urls)),
    path("procurement-plans/<int:plan_pk>/packages/<int:package_pk>/bidders/", include(package_bidder_router.urls)),
    path("sales-forecasts/", include(sales_forecast_router.urls)),
    path("sales-forecasts/<int:forecast_pk>/units/", include(saleable_unit_router.urls)),
    path("sales-forecasts/<int:forecast_pk>/phase-targets/", include(sales_phase_target_router.urls)),
    path("stage-gates/", include(stage_gate_router.urls)),
    path("documents/", include(document_router.urls)),
    path("documents/<int:document_pk>/versions/", include(document_version_router.urls)),
    path("documents/<int:document_pk>/transmittals/", include(document_transmittal_router.urls)),
    path("meeting-minutes/", include(meeting_minutes_router.urls)),
    path("announcements/", include(announcement_router.urls)),
    path("decisions/", include(decision_log_router.urls)),
    path("stakeholder-updates/", include(stakeholder_update_router.urls)),
    path("reports/", include(report_router.urls)),
    path("closeouts/", include(closeout_router.urls)),
    path("closeouts/<int:closeout_pk>/final-accounts/", include(final_account_router.urls)),
    path("closeouts/<int:closeout_pk>/snags/", include(snag_router.urls)),
    path("closeouts/<int:closeout_pk>/warranties/", include(warranty_router.urls)),
    path("construction-reports/", include(construction_report_router.urls)),
    path("rfis/", include(rfi_router.urls)),
    path("rfis/<int:rfi_pk>/comments/", include(rfi_comment_router.urls)),
    path("site-instructions/", include(site_instruction_router.urls)),
    # Cost Control
    path("cost-control/budgets/", include(cost_budget_router.urls)),
    path("cost-control/transactions/", include(cost_transaction_router.urls)),
    # HSE
    path("hse/incidents/", include(hse_incident_router.urls)),
    path("hse/permits/", include(hse_permit_router.urls)),
    path("hse/toolbox-talks/", include(hse_toolbox_router.urls)),
    path("hse/dashboard/", HSEDashboardView.as_view(), name="hse-dashboard"),
    # Commissioning
    path("commissioning-plans/dashboard/", CommissioningDashboardView.as_view(), name="commissioning-dashboard"),
    path("commissioning-plans/", include(commissioning_plan_router.urls)),
    path("commissioning-plans/<int:plan_pk>/tests/", include(commissioning_test_router.urls)),
    path("commissioning-plans/<int:plan_pk>/punch-items/", include(commissioning_punch_router.urls)),
    path("", include(router.urls)),
    path("<int:project_pk>/phases/", include(phase_router.urls)),
    path("<int:project_pk>/phases/<int:phase_pk>/milestones/", include(milestone_router.urls)),
    path("<int:project_pk>/phases/<int:phase_pk>/tasks/", include(task_router.urls)),
    path("<int:project_pk>/phases/<int:phase_pk>/costs/", include(cost_router.urls)),
    path("<int:project_pk>/phase-dependencies/", include(phase_dependency_router.urls)),
    path("<int:project_pk>/milestone-approval-rules/", include(approval_rule_router.urls)),
    path("<int:project_pk>/milestone-approval-decisions/", include(approval_decision_router.urls)),
    path("<int:project_pk>/schedule-delay-logs/", include(delay_log_router.urls)),
]
