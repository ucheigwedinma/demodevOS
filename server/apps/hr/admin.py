from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from apps.admin_mixins import OrgScopedAdminMixin

from .models import (
    Allowance,
    AttendanceLog,
    Bonus,
    Candidate,
    CandidateEvaluation,
    Certification,
    CertificationExpiryAlert,
    CompensationRecord,
    CompetencyAssessment,
    ComplianceDocument,
    ContinuousFeedback,
    CourseEnrollment,
    Deduction,
    DepartmentStaffingReport,
    DisciplinaryRecord,
    DiversityMetric,
    DocumentCollectionItem,
    EmergencyContact,
    EmployeeHandbookSection,
    EmployeeRecord,
    EquipmentAllocation,
    ExitInterview,
    ExitManagement,
    HeadcountSnapshot,
    HiringFunnelMetric,
    HRDocument,
    HRDocumentTemplate,
    HRPolicy,
    IdentificationDocument,
    Interview,
    JobListing,
    JobOffer,
    JobRequisition,
    LearningResource,
    LeaveBalance,
    LeaveRequest,
    LeaveType,
    ManagerEvaluation,
    OnboardingTask,
    OnboardingTemplate,
    OrientationChecklistItem,
    OvertimeRequest,
    PayrollRun,
    Payslip,
    PeerReview,
    PerformanceGoal,
    PerformanceImprovementPlan,
    PerformanceReview,
    PolicyAcknowledgement,
    Position,
    PositionAssignment,
    PositionBudget,
    PositionBudgetRevision,
    PositionRole,
    ProbationRecord,
    ProfessionalLicense,
    Promotion,
    RemoteWorkLog,
    RoleChange,
    SalaryStructure,
    Skill,
    TaxRecord,
    Team,
    TrainingCompletion,
    TrainingCourse,
    TrainingPlan,
    TrainingRecord,
    Transfer,
    TurnoverRecord,
    Vacancy,
    WorkforceCostReport,
)


class PositionAssignmentInline(TabularInline):
    model = PositionAssignment
    extra = 0
    fields = ["user", "start_date", "end_date", "is_primary", "is_active"]
    raw_id_fields = ["user"]


@admin.register(Team)
class TeamAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["name", "code", "department", "lead", "is_active", "sort_order"]
    list_filter = ["is_active", "department__division"]
    search_fields = ["name", "code"]
    raw_id_fields = ["lead"]


@admin.register(Position)
class PositionAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "code", "title", "role", "department", "team", "level",
        "employment_type", "slot_status", "criticality_score",
        "status", "headcount_budget", "is_active",
    ]
    list_filter = [
        "slot_status", "status", "level", "employment_type", "is_active",
        "department", "role",
    ]
    search_fields = ["title", "code", "description"]
    raw_id_fields = ["reports_to", "cost_center", "role", "salary_structure"]
    inlines = [PositionAssignmentInline]


@admin.register(PositionRole)
class PositionRoleAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["code", "name", "grade", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name", "code", "description"]


@admin.register(PositionAssignment)
class PositionAssignmentAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["user", "position", "start_date", "end_date", "is_primary", "is_active"]
    list_filter = ["is_active", "is_primary"]
    raw_id_fields = ["user", "position"]


@admin.register(PositionBudget)
class PositionBudgetAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "department", "position", "fiscal_year",
        "approved_headcount", "filled_headcount", "budget_amount", "status",
    ]
    list_filter = ["fiscal_year", "status", "department"]
    raw_id_fields = ["position", "approved_by"]


@admin.register(PositionBudgetRevision)
class PositionBudgetRevisionAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "budget", "revision_number", "status", "requested_by", "reviewed_by", "created_at",
    ]
    list_filter = ["status", "created_at"]
    search_fields = ["budget__department__name", "budget__position__title", "reason", "review_notes"]
    raw_id_fields = ["budget", "requested_by", "reviewed_by"]


@admin.register(Vacancy)
class VacancyAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "title", "position", "status", "priority",
        "hiring_manager", "opened_date", "target_fill_date", "filled_date",
    ]
    list_filter = ["status", "priority"]
    search_fields = ["title", "reason", "notes"]
    raw_id_fields = ["position", "hiring_manager", "approved_by", "filled_by"]


@admin.register(EmployeeRecord)
class EmployeeRecordAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["user", "hire_date", "employment_status", "contract_type"]
    list_filter = ["employment_status", "contract_type"]
    search_fields = ["user__first_name", "user__last_name", "user__email"]
    raw_id_fields = ["user"]


@admin.register(EmergencyContact)
class EmergencyContactAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["user", "name", "relationship", "phone", "is_primary"]
    list_filter = ["relationship", "is_primary"]
    search_fields = ["name", "phone", "user__first_name", "user__last_name"]
    raw_id_fields = ["user"]


@admin.register(IdentificationDocument)
class IdentificationDocumentAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["user", "document_type", "document_number", "expiry_date"]
    list_filter = ["document_type"]
    search_fields = ["document_number", "user__first_name", "user__last_name"]
    raw_id_fields = ["user"]


@admin.register(CompensationRecord)
class CompensationRecordAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["user", "effective_date", "base_salary", "currency", "total_package", "status"]
    list_filter = ["status", "currency", "pay_frequency"]
    search_fields = ["user__first_name", "user__last_name"]
    raw_id_fields = ["user", "approved_by"]


@admin.register(HRDocument)
class HRDocumentAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["user", "title", "category", "file_size", "created_at"]
    list_filter = ["category"]
    search_fields = ["title", "user__first_name", "user__last_name"]
    raw_id_fields = ["user", "uploaded_by"]


@admin.register(JobRequisition)
class JobRequisitionAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["title", "department", "priority", "status", "requested_by", "created_at"]
    list_filter = ["status", "priority"]
    search_fields = ["title", "justification"]
    raw_id_fields = ["position", "vacancy", "department", "requested_by", "approved_by"]


@admin.register(JobListing)
class JobListingAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["title", "status", "posted_date", "closing_date", "created_at"]
    list_filter = ["status"]
    search_fields = ["title"]
    raw_id_fields = ["requisition", "posted_by"]


@admin.register(Candidate)
class CandidateAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["first_name", "last_name", "email", "stage", "source", "applied_date"]
    list_filter = ["stage", "source"]
    search_fields = ["first_name", "last_name", "email"]
    raw_id_fields = ["job_listing", "job_requisition", "referred_by"]


@admin.register(Interview)
class InterviewAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["candidate", "interview_type", "interviewer", "scheduled_date", "status"]
    list_filter = ["status", "interview_type"]
    raw_id_fields = ["candidate", "interviewer"]


@admin.register(CandidateEvaluation)
class CandidateEvaluationAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["candidate", "evaluator", "overall_rating", "recommendation", "evaluated_at"]
    list_filter = ["recommendation"]
    raw_id_fields = ["candidate", "interview", "evaluator"]


@admin.register(JobOffer)
class JobOfferAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "candidate", "offered_salary", "currency", "status",
        "cfo_override_approved", "start_date", "expiry_date",
    ]
    list_filter = ["status"]
    raw_id_fields = [
        "candidate", "requisition", "position", "approved_by", "cfo_override_by",
    ]


# Onboarding


@admin.register(OnboardingTemplate)
class OnboardingTemplateAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["name", "department", "position", "is_active", "task_count", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name", "description"]
    raw_id_fields = ["department", "position", "created_by"]


@admin.register(OnboardingTask)
class OnboardingTaskAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["title", "employee", "category", "status", "is_required", "due_date"]
    list_filter = ["status", "category", "is_required"]
    search_fields = ["title"]
    raw_id_fields = ["employee", "template", "assigned_to"]


@admin.register(DocumentCollectionItem)
class DocumentCollectionItemAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["document_name", "employee", "status", "due_date", "submitted_date"]
    list_filter = ["status"]
    search_fields = ["document_name"]
    raw_id_fields = ["employee", "verified_by"]


@admin.register(EquipmentAllocation)
class EquipmentAllocationAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["item_name", "employee", "category", "status", "allocated_date"]
    list_filter = ["status", "category"]
    search_fields = ["item_name", "serial_number", "asset_tag"]
    raw_id_fields = ["employee", "allocated_by"]


@admin.register(OrientationChecklistItem)
class OrientationChecklistItemAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["title", "employee", "category", "is_completed", "completed_date"]
    list_filter = ["category", "is_completed"]
    search_fields = ["title"]
    raw_id_fields = ["employee", "completed_by"]


@admin.register(ProbationRecord)
class ProbationRecordAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["employee", "start_date", "end_date", "status", "performance_rating", "recommendation"]
    list_filter = ["status", "recommendation"]
    raw_id_fields = ["employee", "reviewer"]


# Performance Management


@admin.register(PerformanceGoal)
class PerformanceGoalAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["title", "employee", "goal_type", "status", "priority", "progress", "due_date"]
    list_filter = ["goal_type", "status", "priority"]
    search_fields = ["title", "description"]
    raw_id_fields = ["employee", "parent_goal"]


@admin.register(PerformanceReview)
class PerformanceReviewAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["employee", "reviewer", "review_type", "review_period_end", "status", "overall_rating"]
    list_filter = ["review_type", "status"]
    raw_id_fields = ["employee", "reviewer"]


@admin.register(ContinuousFeedback)
class ContinuousFeedbackAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["subject", "employee", "given_by", "feedback_type", "visibility", "created_at"]
    list_filter = ["feedback_type", "visibility"]
    search_fields = ["subject", "content"]
    raw_id_fields = ["employee", "given_by"]


@admin.register(ManagerEvaluation)
class ManagerEvaluationAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["employee", "evaluator", "evaluation_date", "overall_rating"]
    raw_id_fields = ["employee", "evaluator", "review"]


@admin.register(PeerReview)
class PeerReviewAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["employee", "reviewer", "status", "overall_rating", "is_anonymous", "submitted_at"]
    list_filter = ["status", "is_anonymous"]
    raw_id_fields = ["employee", "reviewer", "review"]


@admin.register(PerformanceImprovementPlan)
class PerformanceImprovementPlanAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["title", "employee", "start_date", "end_date", "status", "outcome"]
    list_filter = ["status", "outcome"]
    search_fields = ["title", "reason"]
    raw_id_fields = ["employee", "created_by"]


# Skills & Capability Management


@admin.register(Skill)
class SkillAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["name", "employee", "category", "proficiency", "years_experience", "is_primary", "verified"]
    list_filter = ["category", "proficiency", "is_primary", "verified"]
    search_fields = ["name", "employee__user__first_name", "employee__user__last_name"]
    raw_id_fields = ["employee", "verified_by"]


@admin.register(Certification)
class CertificationAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["name", "employee", "issuing_body", "issue_date", "expiry_date", "status"]
    list_filter = ["status"]
    search_fields = ["name", "issuing_body", "credential_id"]
    raw_id_fields = ["employee"]


@admin.register(ProfessionalLicense)
class ProfessionalLicenseAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["license_type", "license_number", "employee", "issuing_authority", "issue_date", "expiry_date", "status", "is_mandatory"]
    list_filter = ["status", "is_mandatory"]
    search_fields = ["license_type", "license_number", "issuing_authority"]
    raw_id_fields = ["employee"]


@admin.register(CompetencyAssessment)
class CompetencyAssessmentAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["competency_area", "employee", "assessor", "assessment_date", "score", "max_score", "status"]
    list_filter = ["status"]
    search_fields = ["competency_area"]
    raw_id_fields = ["employee", "assessor"]


@admin.register(TrainingRecord)
class TrainingRecordAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["title", "employee", "provider", "delivery_method", "start_date", "status", "is_mandatory"]
    list_filter = ["status", "delivery_method", "is_mandatory"]
    search_fields = ["title", "provider"]
    raw_id_fields = ["employee"]


# Learning & Development


@admin.register(TrainingCourse)
class TrainingCourseAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["title", "code", "provider", "format", "level", "status", "is_mandatory", "duration_hours"]
    list_filter = ["format", "level", "status", "is_mandatory"]
    search_fields = ["title", "code", "provider"]
    raw_id_fields = ["created_by"]


@admin.register(TrainingPlan)
class TrainingPlanAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["title", "department", "employee", "start_date", "end_date", "status"]
    list_filter = ["status"]
    search_fields = ["title"]
    raw_id_fields = ["department", "employee", "created_by"]


@admin.register(CourseEnrollment)
class CourseEnrollmentAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["employee", "course", "enrolled_date", "status", "progress", "score"]
    list_filter = ["status"]
    raw_id_fields = ["employee", "course", "training_plan", "enrolled_by"]


@admin.register(LearningResource)
class LearningResourceAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["title", "resource_type", "category", "status", "view_count", "created_at"]
    list_filter = ["resource_type", "status"]
    search_fields = ["title", "category", "tags"]
    raw_id_fields = ["uploaded_by"]


@admin.register(TrainingCompletion)
class TrainingCompletionAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["employee", "course", "completion_date", "result", "score", "certificate_number", "certificate_expiry"]
    list_filter = ["result"]
    search_fields = ["certificate_number"]
    raw_id_fields = ["employee", "course", "enrollment", "verified_by"]


@admin.register(CertificationExpiryAlert)
class CertificationExpiryAlertAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["reference_name", "employee", "alert_type", "expiry_date", "alert_date", "status"]
    list_filter = ["alert_type", "status"]
    search_fields = ["reference_name"]
    raw_id_fields = ["employee"]


# Attendance & Leave


@admin.register(AttendanceLog)
class AttendanceLogAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["employee", "date", "status", "clock_in", "clock_out", "total_hours", "location"]
    list_filter = ["status", "date"]
    search_fields = ["employee__user__first_name", "employee__user__last_name", "location"]
    raw_id_fields = ["employee"]


@admin.register(LeaveType)
class LeaveTypeAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["name", "code", "default_days_per_year", "is_paid", "requires_approval", "is_active", "sort_order"]
    list_filter = ["is_active", "is_paid", "requires_approval"]
    search_fields = ["name", "code"]


@admin.register(LeaveRequest)
class LeaveRequestAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["employee", "leave_type", "start_date", "end_date", "total_days", "status", "reviewed_by"]
    list_filter = ["status", "leave_type"]
    search_fields = ["employee__user__first_name", "employee__user__last_name", "reason"]
    raw_id_fields = ["employee", "leave_type", "reviewed_by"]


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["employee", "leave_type", "fiscal_year", "entitled_days", "used_days", "pending_days"]
    list_filter = ["fiscal_year", "leave_type"]
    search_fields = ["employee__user__first_name", "employee__user__last_name"]
    raw_id_fields = ["employee", "leave_type"]


@admin.register(OvertimeRequest)
class OvertimeRequestAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["employee", "date", "start_time", "end_time", "total_hours", "status", "approved_by"]
    list_filter = ["status"]
    search_fields = ["employee__user__first_name", "employee__user__last_name", "reason"]
    raw_id_fields = ["employee", "approved_by"]


@admin.register(RemoteWorkLog)
class RemoteWorkLogAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["employee", "date", "status", "location", "work_hours", "approved_by"]
    list_filter = ["status"]
    search_fields = ["employee__user__first_name", "employee__user__last_name", "location"]
    raw_id_fields = ["employee", "approved_by"]


# ---------------------------------------------------------------------------
# Payroll & Compensation
# ---------------------------------------------------------------------------


@admin.register(SalaryStructure)
class SalaryStructureAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["name", "code", "grade_level", "min_salary", "max_salary", "currency", "is_active"]
    list_filter = ["is_active", "currency"]
    search_fields = ["name", "code"]


@admin.register(PayrollRun)
class PayrollRunAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["name", "period_start", "period_end", "run_date", "status", "total_net", "currency"]
    list_filter = ["status"]
    search_fields = ["name"]
    raw_id_fields = ["processed_by"]


@admin.register(Allowance)
class AllowanceAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["employee", "allowance_type", "name", "amount", "currency", "frequency", "is_taxable", "is_active"]
    list_filter = ["allowance_type", "frequency", "is_active", "is_taxable"]
    search_fields = ["employee__user__first_name", "employee__user__last_name", "name"]
    raw_id_fields = ["employee"]


@admin.register(Deduction)
class DeductionAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["employee", "deduction_type", "name", "amount", "currency", "frequency", "is_active"]
    list_filter = ["deduction_type", "frequency", "is_active"]
    search_fields = ["employee__user__first_name", "employee__user__last_name", "name"]
    raw_id_fields = ["employee"]


@admin.register(Bonus)
class BonusAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["employee", "bonus_type", "amount", "currency", "date", "status", "approved_by"]
    list_filter = ["bonus_type", "status"]
    search_fields = ["employee__user__first_name", "employee__user__last_name", "reason"]
    raw_id_fields = ["employee", "approved_by"]


@admin.register(Payslip)
class PayslipAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["employee", "period_start", "period_end", "gross_salary", "net_salary", "currency", "status"]
    list_filter = ["status"]
    search_fields = ["employee__user__first_name", "employee__user__last_name"]
    raw_id_fields = ["employee", "payroll_run"]


@admin.register(TaxRecord)
class TaxRecordAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["employee", "fiscal_year", "tax_type", "tax_amount", "tax_paid", "filing_status"]
    list_filter = ["tax_type", "filing_status", "fiscal_year"]
    search_fields = ["employee__user__first_name", "employee__user__last_name", "fiscal_year"]
    raw_id_fields = ["employee"]


# Employee Lifecycle Management
@admin.register(Promotion)
class PromotionAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["employee", "from_position", "to_position", "effective_date", "status", "approved_by"]
    list_filter = ["status"]
    search_fields = ["employee__user__first_name", "employee__user__last_name", "to_position"]
    raw_id_fields = ["employee", "approved_by"]


@admin.register(Transfer)
class TransferAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["employee", "transfer_type", "from_department", "to_department", "effective_date", "status"]
    list_filter = ["transfer_type", "status"]
    search_fields = ["employee__user__first_name", "employee__user__last_name", "to_department"]
    raw_id_fields = ["employee", "approved_by"]


@admin.register(RoleChange)
class RoleChangeAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["employee", "change_type", "from_role", "to_role", "effective_date", "status"]
    list_filter = ["change_type", "status"]
    search_fields = ["employee__user__first_name", "employee__user__last_name", "to_role"]
    raw_id_fields = ["employee", "approved_by"]


@admin.register(DisciplinaryRecord)
class DisciplinaryRecordAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["employee", "incident_date", "category", "severity", "status"]
    list_filter = ["category", "severity", "status"]
    search_fields = ["employee__user__first_name", "employee__user__last_name", "description"]
    raw_id_fields = ["employee", "reported_by"]


@admin.register(ExitManagement)
class ExitManagementAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["employee", "exit_type", "notice_date", "last_working_day", "clearance_status", "final_settlement_status"]
    list_filter = ["exit_type", "clearance_status", "final_settlement_status"]
    search_fields = ["employee__user__first_name", "employee__user__last_name"]
    raw_id_fields = ["employee", "processed_by"]


@admin.register(ExitInterview)
class ExitInterviewAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["employee", "interview_date", "overall_satisfaction", "would_recommend", "would_rejoin"]
    list_filter = ["overall_satisfaction", "would_recommend", "would_rejoin"]
    search_fields = ["employee__user__first_name", "employee__user__last_name", "reason_for_leaving"]
    raw_id_fields = ["employee", "interviewer", "exit_record"]


# Workforce Analytics
@admin.register(HeadcountSnapshot)
class HeadcountSnapshotAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["snapshot_date", "department", "team", "active_count", "inactive_count", "new_hires", "departures"]
    list_filter = ["snapshot_date"]
    search_fields = ["department", "team"]


@admin.register(TurnoverRecord)
class TurnoverRecordAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["period_start", "period_end", "department", "starting_headcount", "ending_headcount", "voluntary_departures", "involuntary_departures"]
    list_filter = ["period_start"]
    search_fields = ["department"]


@admin.register(DepartmentStaffingReport)
class DepartmentStaffingReportAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["report_date", "department", "budgeted_positions", "filled_positions", "vacant_positions", "pending_hires"]
    list_filter = ["report_date"]
    search_fields = ["department"]


@admin.register(HiringFunnelMetric)
class HiringFunnelMetricAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["period_start", "period_end", "department", "requisitions_opened", "offers_made", "offers_accepted", "avg_time_to_hire_days"]
    list_filter = ["period_start"]
    search_fields = ["department"]


@admin.register(WorkforceCostReport)
class WorkforceCostReportAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["period_start", "period_end", "department", "total_salary", "total_bonuses", "headcount", "currency"]
    list_filter = ["period_start", "currency"]
    search_fields = ["department"]


@admin.register(DiversityMetric)
class DiversityMetricAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["snapshot_date", "department", "dimension", "category_value", "count", "percentage"]
    list_filter = ["dimension", "snapshot_date"]
    search_fields = ["department", "category_value"]


@admin.register(HRPolicy)
class HRPolicyAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["title", "category", "status", "version", "effective_date", "department"]
    list_filter = ["category", "status"]
    search_fields = ["title", "department"]


@admin.register(EmployeeHandbookSection)
class EmployeeHandbookSectionAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["section_number", "title", "handbook_version", "status", "order"]
    list_filter = ["status"]
    search_fields = ["title", "section_number"]


@admin.register(ComplianceDocument)
class ComplianceDocumentAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["title", "document_type", "status", "reference_number", "issuing_authority", "expiry_date"]
    list_filter = ["document_type", "status"]
    search_fields = ["title", "reference_number"]


@admin.register(PolicyAcknowledgement)
class PolicyAcknowledgementAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["employee", "policy", "acknowledged", "acknowledged_date"]
    list_filter = ["acknowledged"]
    search_fields = ["employee__username", "policy__title"]
    raw_id_fields = ["employee", "policy"]


@admin.register(HRDocumentTemplate)
class HRDocumentTemplateAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["title", "category", "version", "status", "created_at"]
    list_filter = ["category", "status"]
    search_fields = ["title"]
