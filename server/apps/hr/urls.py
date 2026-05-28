from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

team_router = DefaultRouter()
team_router.register(r"", views.TeamViewSet, basename="team")

position_role_router = DefaultRouter()
position_role_router.register(r"", views.PositionRoleViewSet, basename="position-role")

position_router = DefaultRouter()
position_router.register(r"", views.PositionViewSet, basename="position")

assignment_router = DefaultRouter()
assignment_router.register(
    r"", views.PositionAssignmentViewSet, basename="position-assignment",
)

budget_router = DefaultRouter()
budget_router.register(
    r"", views.PositionBudgetViewSet, basename="position-budget",
)

budget_revision_router = DefaultRouter()
budget_revision_router.register(
    r"", views.PositionBudgetRevisionViewSet, basename="position-budget-revision",
)

vacancy_router = DefaultRouter()
vacancy_router.register(r"", views.VacancyViewSet, basename="vacancy")

employee_record_router = DefaultRouter()
employee_record_router.register(
    r"", views.EmployeeDirectoryViewSet, basename="employee-record",
)

emergency_contact_router = DefaultRouter()
emergency_contact_router.register(
    r"", views.EmergencyContactViewSet, basename="emergency-contact",
)

id_document_router = DefaultRouter()
id_document_router.register(
    r"", views.IdentificationDocumentViewSet, basename="id-document",
)

compensation_router = DefaultRouter()
compensation_router.register(
    r"", views.CompensationRecordViewSet, basename="compensation-record",
)

hr_document_router = DefaultRouter()
hr_document_router.register(
    r"", views.HRDocumentViewSet, basename="hr-document",
)

requisition_router = DefaultRouter()
requisition_router.register(
    r"", views.JobRequisitionViewSet, basename="job-requisition",
)

listing_router = DefaultRouter()
listing_router.register(
    r"", views.JobListingViewSet, basename="job-listing",
)

candidate_router = DefaultRouter()
candidate_router.register(
    r"", views.CandidateViewSet, basename="candidate",
)

interview_router = DefaultRouter()
interview_router.register(
    r"", views.InterviewViewSet, basename="interview",
)

evaluation_router = DefaultRouter()
evaluation_router.register(
    r"", views.CandidateEvaluationViewSet, basename="candidate-evaluation",
)

offer_router = DefaultRouter()
offer_router.register(
    r"", views.JobOfferViewSet, basename="job-offer",
)

# Onboarding routers
onboarding_template_router = DefaultRouter()
onboarding_template_router.register(
    r"", views.OnboardingTemplateViewSet, basename="onboarding-template",
)

onboarding_task_router = DefaultRouter()
onboarding_task_router.register(
    r"", views.OnboardingTaskViewSet, basename="onboarding-task",
)

document_collection_router = DefaultRouter()
document_collection_router.register(
    r"", views.DocumentCollectionViewSet, basename="document-collection",
)

equipment_allocation_router = DefaultRouter()
equipment_allocation_router.register(
    r"", views.EquipmentAllocationViewSet, basename="equipment-allocation",
)

orientation_checklist_router = DefaultRouter()
orientation_checklist_router.register(
    r"", views.OrientationChecklistViewSet, basename="orientation-checklist",
)

probation_record_router = DefaultRouter()
probation_record_router.register(
    r"", views.ProbationRecordViewSet, basename="probation-record",
)

# Performance Management routers
performance_goal_router = DefaultRouter()
performance_goal_router.register(
    r"", views.PerformanceGoalViewSet, basename="performance-goal",
)

performance_review_router = DefaultRouter()
performance_review_router.register(
    r"", views.PerformanceReviewViewSet, basename="performance-review",
)

continuous_feedback_router = DefaultRouter()
continuous_feedback_router.register(
    r"", views.ContinuousFeedbackViewSet, basename="continuous-feedback",
)

manager_evaluation_router = DefaultRouter()
manager_evaluation_router.register(
    r"", views.ManagerEvaluationViewSet, basename="manager-evaluation",
)

peer_review_router = DefaultRouter()
peer_review_router.register(
    r"", views.PeerReviewViewSet, basename="peer-review",
)

pip_router = DefaultRouter()
pip_router.register(
    r"", views.PIPViewSet, basename="pip",
)

# Skills & Capability routers
skill_router = DefaultRouter()
skill_router.register(r"", views.SkillViewSet, basename="skill")

certification_router = DefaultRouter()
certification_router.register(
    r"", views.CertificationViewSet, basename="certification",
)

license_router = DefaultRouter()
license_router.register(
    r"", views.ProfessionalLicenseViewSet, basename="professional-license",
)

competency_assessment_router = DefaultRouter()
competency_assessment_router.register(
    r"", views.CompetencyAssessmentViewSet, basename="competency-assessment",
)

training_record_router = DefaultRouter()
training_record_router.register(
    r"", views.TrainingRecordViewSet, basename="training-record",
)

# Learning & Development routers
training_course_router = DefaultRouter()
training_course_router.register(
    r"", views.TrainingCourseViewSet, basename="training-course",
)

training_plan_router = DefaultRouter()
training_plan_router.register(
    r"", views.TrainingPlanViewSet, basename="training-plan",
)

course_enrollment_router = DefaultRouter()
course_enrollment_router.register(
    r"", views.CourseEnrollmentViewSet, basename="course-enrollment",
)

learning_resource_router = DefaultRouter()
learning_resource_router.register(
    r"", views.LearningResourceViewSet, basename="learning-resource",
)

training_completion_router = DefaultRouter()
training_completion_router.register(
    r"", views.TrainingCompletionViewSet, basename="training-completion",
)

certification_expiry_alert_router = DefaultRouter()
certification_expiry_alert_router.register(
    r"", views.CertificationExpiryAlertViewSet, basename="certification-expiry-alert",
)

# Attendance & Leave routers
attendance_log_router = DefaultRouter()
attendance_log_router.register(
    r"", views.AttendanceLogViewSet, basename="attendance-log",
)

leave_type_router = DefaultRouter()
leave_type_router.register(
    r"", views.LeaveTypeViewSet, basename="leave-type",
)

leave_request_router = DefaultRouter()
leave_request_router.register(
    r"", views.LeaveRequestViewSet, basename="leave-request",
)

leave_balance_router = DefaultRouter()
leave_balance_router.register(
    r"", views.LeaveBalanceViewSet, basename="leave-balance",
)

overtime_request_router = DefaultRouter()
overtime_request_router.register(
    r"", views.OvertimeRequestViewSet, basename="overtime-request",
)

remote_work_log_router = DefaultRouter()
remote_work_log_router.register(
    r"", views.RemoteWorkLogViewSet, basename="remote-work-log",
)

salary_structure_router = DefaultRouter()
salary_structure_router.register(
    r"", views.SalaryStructureViewSet, basename="salary-structure",
)

payroll_run_router = DefaultRouter()
payroll_run_router.register(
    r"", views.PayrollRunViewSet, basename="payroll-run",
)

allowance_router = DefaultRouter()
allowance_router.register(
    r"", views.AllowanceViewSet, basename="allowance",
)

deduction_router = DefaultRouter()
deduction_router.register(
    r"", views.DeductionViewSet, basename="deduction",
)

bonus_router = DefaultRouter()
bonus_router.register(
    r"", views.BonusViewSet, basename="bonus",
)

payslip_router = DefaultRouter()
payslip_router.register(
    r"", views.PayslipViewSet, basename="payslip",
)

tax_record_router = DefaultRouter()
tax_record_router.register(
    r"", views.TaxRecordViewSet, basename="tax-record",
)

# Employee Lifecycle Management routers
promotion_router = DefaultRouter()
promotion_router.register(
    r"", views.PromotionViewSet, basename="promotion",
)

transfer_router = DefaultRouter()
transfer_router.register(
    r"", views.TransferViewSet, basename="transfer",
)

role_change_router = DefaultRouter()
role_change_router.register(
    r"", views.RoleChangeViewSet, basename="role-change",
)

disciplinary_record_router = DefaultRouter()
disciplinary_record_router.register(
    r"", views.DisciplinaryRecordViewSet, basename="disciplinary-record",
)

exit_management_router = DefaultRouter()
exit_management_router.register(
    r"", views.ExitManagementViewSet, basename="exit-management",
)

exit_interview_router = DefaultRouter()
exit_interview_router.register(
    r"", views.ExitInterviewViewSet, basename="exit-interview",
)

# Workforce Analytics routers
headcount_snapshot_router = DefaultRouter()
headcount_snapshot_router.register(
    r"", views.HeadcountSnapshotViewSet, basename="headcount-snapshot",
)

turnover_record_router = DefaultRouter()
turnover_record_router.register(
    r"", views.TurnoverRecordViewSet, basename="turnover-record",
)

dept_staffing_router = DefaultRouter()
dept_staffing_router.register(
    r"", views.DepartmentStaffingReportViewSet, basename="dept-staffing-report",
)

hiring_funnel_router = DefaultRouter()
hiring_funnel_router.register(
    r"", views.HiringFunnelMetricViewSet, basename="hiring-funnel-metric",
)

workforce_cost_router = DefaultRouter()
workforce_cost_router.register(
    r"", views.WorkforceCostReportViewSet, basename="workforce-cost-report",
)

diversity_metric_router = DefaultRouter()
diversity_metric_router.register(
    r"", views.DiversityMetricViewSet, basename="diversity-metric",
)

# HR Documents & Policies routers
hr_policy_router = DefaultRouter()
hr_policy_router.register(
    r"", views.HRPolicyViewSet, basename="hr-policy",
)

handbook_section_router = DefaultRouter()
handbook_section_router.register(
    r"", views.EmployeeHandbookSectionViewSet, basename="handbook-section",
)

compliance_document_router = DefaultRouter()
compliance_document_router.register(
    r"", views.ComplianceDocumentViewSet, basename="compliance-document",
)

policy_acknowledgement_router = DefaultRouter()
policy_acknowledgement_router.register(
    r"", views.PolicyAcknowledgementViewSet, basename="policy-acknowledgement",
)

hr_document_template_router = DefaultRouter()
hr_document_template_router.register(
    r"", views.HRDocumentTemplateViewSet, basename="hr-document-template",
)

urlpatterns = [
    # Read-only aggregate views
    path("org-chart/", views.OrgChartView.as_view(), name="org-chart"),
    path("reporting-lines/", views.ReportingLinesView.as_view(), name="reporting-lines"),
    path(
        "reporting-lines/<int:user_id>/",
        views.ReportingLineUpdateView.as_view(),
        name="reporting-line-update",
    ),
    path("headcount-summary/", views.HeadcountSummaryView.as_view(), name="headcount-summary"),
    path("employment-history/", views.EmploymentHistoryView.as_view(), name="employment-history"),
    path("contact-directory/", views.ContactDirectoryView.as_view(), name="contact-directory"),
    path("hiring-workflow/", views.HiringWorkflowDashboardView.as_view(), name="hiring-workflow"),
    # CRUD resources
    path("teams/", include(team_router.urls)),
    path("position-roles/", include(position_role_router.urls)),
    path("positions/", include(position_router.urls)),
    path("position-assignments/", include(assignment_router.urls)),
    path("position-budgets/", include(budget_router.urls)),
    path("position-budget-revisions/", include(budget_revision_router.urls)),
    path("vacancies/", include(vacancy_router.urls)),
    path("employee-records/", include(employee_record_router.urls)),
    path("emergency-contacts/", include(emergency_contact_router.urls)),
    path("id-documents/", include(id_document_router.urls)),
    path("compensation-records/", include(compensation_router.urls)),
    path("hr-documents/", include(hr_document_router.urls)),
    path("requisitions/", include(requisition_router.urls)),
    path("job-listings/", include(listing_router.urls)),
    path("candidates/", include(candidate_router.urls)),
    path("interviews/", include(interview_router.urls)),
    path("evaluations/", include(evaluation_router.urls)),
    path("job-offers/", include(offer_router.urls)),
    # Onboarding
    path("onboarding-templates/", include(onboarding_template_router.urls)),
    path("onboarding-tasks/", include(onboarding_task_router.urls)),
    path("document-collection/", include(document_collection_router.urls)),
    path("equipment-allocations/", include(equipment_allocation_router.urls)),
    path("orientation-checklists/", include(orientation_checklist_router.urls)),
    path("probation-records/", include(probation_record_router.urls)),
    # Performance Management
    path("performance-goals/", include(performance_goal_router.urls)),
    path("performance-reviews/", include(performance_review_router.urls)),
    path("continuous-feedback/", include(continuous_feedback_router.urls)),
    path("manager-evaluations/", include(manager_evaluation_router.urls)),
    path("peer-reviews/", include(peer_review_router.urls)),
    path("pips/", include(pip_router.urls)),
    # Skills & Capability
    path("skills/", include(skill_router.urls)),
    path("certifications/", include(certification_router.urls)),
    path("licenses/", include(license_router.urls)),
    path("competency-assessments/", include(competency_assessment_router.urls)),
    path("training-records/", include(training_record_router.urls)),
    # Learning & Development
    path("training-courses/", include(training_course_router.urls)),
    path("training-plans/", include(training_plan_router.urls)),
    path("course-enrollments/", include(course_enrollment_router.urls)),
    path("learning-resources/", include(learning_resource_router.urls)),
    path("training-completions/", include(training_completion_router.urls)),
    path("certification-expiry-alerts/", include(certification_expiry_alert_router.urls)),
    # Attendance & Leave
    path("attendance-logs/", include(attendance_log_router.urls)),
    path("leave-types/", include(leave_type_router.urls)),
    path("leave-requests/", include(leave_request_router.urls)),
    path("leave-balances/", include(leave_balance_router.urls)),
    path("overtime-requests/", include(overtime_request_router.urls)),
    path("remote-work-logs/", include(remote_work_log_router.urls)),
    # Payroll & Compensation
    path("salary-structures/", include(salary_structure_router.urls)),
    path("payroll-runs/", include(payroll_run_router.urls)),
    path("allowances/", include(allowance_router.urls)),
    path("deductions/", include(deduction_router.urls)),
    path("bonuses/", include(bonus_router.urls)),
    path("payslips/", include(payslip_router.urls)),
    path("tax-records/", include(tax_record_router.urls)),
    # Employee Lifecycle Management
    path("promotions/", include(promotion_router.urls)),
    path("transfers/", include(transfer_router.urls)),
    path("role-changes/", include(role_change_router.urls)),
    path("disciplinary-records/", include(disciplinary_record_router.urls)),
    path("exit-management/", include(exit_management_router.urls)),
    path("exit-interviews/", include(exit_interview_router.urls)),
    # Workforce Analytics
    path("headcount-snapshots/", include(headcount_snapshot_router.urls)),
    path("turnover-records/", include(turnover_record_router.urls)),
    path("dept-staffing-reports/", include(dept_staffing_router.urls)),
    path("hiring-funnel-metrics/", include(hiring_funnel_router.urls)),
    path("workforce-cost-reports/", include(workforce_cost_router.urls)),
    path("diversity-metrics/", include(diversity_metric_router.urls)),
    # HR Documents & Policies
    path("hr-policies/", include(hr_policy_router.urls)),
    path("handbook-sections/", include(handbook_section_router.urls)),
    path("compliance-documents/", include(compliance_document_router.urls)),
    path("policy-acknowledgements/", include(policy_acknowledgement_router.urls)),
    path("document-templates/", include(hr_document_template_router.urls)),
]
