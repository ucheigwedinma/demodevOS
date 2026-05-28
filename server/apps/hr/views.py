from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from django.db import transaction
from django.db.models import Count, Exists, Max, OuterRef, Prefetch, Q, Subquery, Sum
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.settings.models import AuditComplianceSettings, Division
from apps.settings.permissions import HasRolePermission, get_user_permissions

from .automation import (
    enforce_candidate_hire_budget,
    get_business_unit_budget_guardrails,
    user_has_cfo_override_authority,
)
from .models import (
    CONTRACT_CATEGORIES,
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
from .serializers import (
    AllowanceDetailSerializer,
    AllowanceListSerializer,
    AllowanceWriteSerializer,
    AttendanceLogDetailSerializer,
    AttendanceLogListSerializer,
    AttendanceLogWriteSerializer,
    BonusDetailSerializer,
    BonusListSerializer,
    BonusWriteSerializer,
    CandidateDetailSerializer,
    CandidateEvaluationDetailSerializer,
    CandidateEvaluationListSerializer,
    CandidateEvaluationWriteSerializer,
    CandidateListSerializer,
    CandidateWriteSerializer,
    CertificationDetailSerializer,
    CertificationExpiryAlertDetailSerializer,
    CertificationExpiryAlertListSerializer,
    CertificationExpiryAlertWriteSerializer,
    CertificationListSerializer,
    CertificationWriteSerializer,
    CompensationRecordDetailSerializer,
    CompensationRecordListSerializer,
    CompensationRecordWriteSerializer,
    CompetencyAssessmentDetailSerializer,
    CompetencyAssessmentListSerializer,
    CompetencyAssessmentWriteSerializer,
    ComplianceDocumentDetailSerializer,
    ComplianceDocumentListSerializer,
    ComplianceDocumentWriteSerializer,
    ContinuousFeedbackDetailSerializer,
    ContinuousFeedbackListSerializer,
    ContinuousFeedbackWriteSerializer,
    CourseEnrollmentDetailSerializer,
    CourseEnrollmentListSerializer,
    CourseEnrollmentWriteSerializer,
    DeductionDetailSerializer,
    DeductionListSerializer,
    DeductionWriteSerializer,
    DepartmentStaffingReportDetailSerializer,
    DepartmentStaffingReportListSerializer,
    DepartmentStaffingReportWriteSerializer,
    DisciplinaryRecordDetailSerializer,
    DisciplinaryRecordListSerializer,
    DisciplinaryRecordWriteSerializer,
    DiversityMetricDetailSerializer,
    DiversityMetricListSerializer,
    DiversityMetricWriteSerializer,
    DocumentCollectionListSerializer,
    DocumentCollectionWriteSerializer,
    EmergencyContactListSerializer,
    EmergencyContactWriteSerializer,
    EmployeeDirectoryDetailSerializer,
    EmployeeDirectoryListSerializer,
    EmployeeHandbookSectionDetailSerializer,
    EmployeeHandbookSectionListSerializer,
    EmployeeHandbookSectionWriteSerializer,
    EmployeeRecordWriteSerializer,
    EmploymentHistoryEntrySerializer,
    EquipmentAllocationListSerializer,
    EquipmentAllocationWriteSerializer,
    ExitInterviewDetailSerializer,
    ExitInterviewListSerializer,
    ExitInterviewWriteSerializer,
    ExitManagementDetailSerializer,
    ExitManagementListSerializer,
    ExitManagementWriteSerializer,
    HeadcountSnapshotDetailSerializer,
    HeadcountSnapshotListSerializer,
    HeadcountSnapshotWriteSerializer,
    HiringFunnelMetricDetailSerializer,
    HiringFunnelMetricListSerializer,
    HiringFunnelMetricWriteSerializer,
    HRDocumentListSerializer,
    HRDocumentTemplateDetailSerializer,
    HRDocumentTemplateListSerializer,
    HRDocumentTemplateWriteSerializer,
    HRDocumentWriteSerializer,
    HRPolicyDetailSerializer,
    HRPolicyListSerializer,
    HRPolicyWriteSerializer,
    IdentificationDocumentListSerializer,
    IdentificationDocumentWriteSerializer,
    InterviewDetailSerializer,
    InterviewListSerializer,
    InterviewWriteSerializer,
    JobListingDetailSerializer,
    JobListingListSerializer,
    JobListingWriteSerializer,
    JobOfferDetailSerializer,
    JobOfferListSerializer,
    JobOfferWriteSerializer,
    JobRequisitionDetailSerializer,
    JobRequisitionListSerializer,
    JobRequisitionWriteSerializer,
    LearningResourceDetailSerializer,
    LearningResourceListSerializer,
    LearningResourceWriteSerializer,
    LeaveBalanceDetailSerializer,
    LeaveBalanceListSerializer,
    LeaveBalanceWriteSerializer,
    LeaveRequestDetailSerializer,
    LeaveRequestListSerializer,
    LeaveRequestWriteSerializer,
    LeaveTypeDetailSerializer,
    LeaveTypeListSerializer,
    LeaveTypeWriteSerializer,
    ManagerEvaluationDetailSerializer,
    ManagerEvaluationListSerializer,
    ManagerEvaluationWriteSerializer,
    OnboardingTaskListSerializer,
    OnboardingTaskWriteSerializer,
    OnboardingTemplateListSerializer,
    OnboardingTemplateWriteSerializer,
    OrgChartPositionSerializer,
    OrgChartTeamSerializer,
    OrientationChecklistListSerializer,
    OrientationChecklistWriteSerializer,
    OvertimeRequestDetailSerializer,
    OvertimeRequestListSerializer,
    OvertimeRequestWriteSerializer,
    PayrollRunDetailSerializer,
    PayrollRunListSerializer,
    PayrollRunWriteSerializer,
    PayslipDetailSerializer,
    PayslipListSerializer,
    PayslipWriteSerializer,
    PeerReviewDetailSerializer,
    PeerReviewListSerializer,
    PeerReviewWriteSerializer,
    PerformanceGoalDetailSerializer,
    PerformanceGoalListSerializer,
    PerformanceGoalWriteSerializer,
    PerformanceReviewDetailSerializer,
    PerformanceReviewListSerializer,
    PerformanceReviewWriteSerializer,
    PIPDetailSerializer,
    PIPListSerializer,
    PIPWriteSerializer,
    PolicyAcknowledgementDetailSerializer,
    PolicyAcknowledgementListSerializer,
    PolicyAcknowledgementWriteSerializer,
    PositionAssignmentDetailSerializer,
    PositionAssignmentListSerializer,
    PositionAssignmentWriteSerializer,
    PositionBudgetDetailSerializer,
    PositionBudgetListSerializer,
    PositionBudgetRevisionDetailSerializer,
    PositionBudgetRevisionListSerializer,
    PositionBudgetRevisionWriteSerializer,
    PositionBudgetWriteSerializer,
    PositionDetailSerializer,
    PositionListSerializer,
    PositionRoleDetailSerializer,
    PositionRoleListSerializer,
    PositionRoleWriteSerializer,
    PositionWriteSerializer,
    ProbationRecordDetailSerializer,
    ProbationRecordListSerializer,
    ProbationRecordWriteSerializer,
    ProfessionalLicenseDetailSerializer,
    ProfessionalLicenseListSerializer,
    ProfessionalLicenseWriteSerializer,
    PromotionDetailSerializer,
    PromotionListSerializer,
    PromotionWriteSerializer,
    RemoteWorkLogDetailSerializer,
    RemoteWorkLogListSerializer,
    RemoteWorkLogWriteSerializer,
    RoleChangeDetailSerializer,
    RoleChangeListSerializer,
    RoleChangeWriteSerializer,
    SalaryStructureDetailSerializer,
    SalaryStructureListSerializer,
    SalaryStructureWriteSerializer,
    SkillDetailSerializer,
    SkillListSerializer,
    SkillWriteSerializer,
    TaxRecordDetailSerializer,
    TaxRecordListSerializer,
    TaxRecordWriteSerializer,
    TeamDetailSerializer,
    TeamListSerializer,
    TeamWriteSerializer,
    TrainingCompletionDetailSerializer,
    TrainingCompletionListSerializer,
    TrainingCompletionWriteSerializer,
    TrainingCourseDetailSerializer,
    TrainingCourseListSerializer,
    TrainingCourseWriteSerializer,
    TrainingPlanDetailSerializer,
    TrainingPlanListSerializer,
    TrainingPlanWriteSerializer,
    TrainingRecordDetailSerializer,
    TrainingRecordListSerializer,
    TrainingRecordWriteSerializer,
    TransferDetailSerializer,
    TransferListSerializer,
    TransferWriteSerializer,
    TurnoverRecordDetailSerializer,
    TurnoverRecordListSerializer,
    TurnoverRecordWriteSerializer,
    VacancyDetailSerializer,
    VacancyListSerializer,
    VacancyWriteSerializer,
    WorkforceCostReportDetailSerializer,
    WorkforceCostReportListSerializer,
    WorkforceCostReportWriteSerializer,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _user_org(request):
    profile = getattr(request.user, "profile", None)
    return getattr(profile, "organization", None)


def _is_superuser(request):
    # All users are org-scoped — no bypass
    return False


def _can_view_position_salary_band(request) -> bool:
    if _is_superuser(request):
        return True

    profile = getattr(request.user, "profile", None)
    if profile is None:
        return False

    if getattr(profile, "role", "") == "admin":
        return True

    permission_keys = get_user_permissions(request.user)
    if "*" in permission_keys:
        return True

    return any(
        key.startswith("hr.") or key.startswith("finance.")
        for key in permission_keys
    )


# ---------------------------------------------------------------------------
# Action Map
# ---------------------------------------------------------------------------

_HR_ACTION_MAP = {
    "list": "view", "retrieve": "view", "create": "create",
    "update": "edit", "partial_update": "edit", "destroy": "delete",
    "approve": "approve", "fill": "edit", "cancel": "edit", "reopen": "edit",
    "submit_for_approval": "edit", "advance_stage": "edit",
    "reject": "edit", "withdraw": "edit", "close": "edit",
    "archive": "edit", "complete": "edit", "extend": "edit", "accept": "edit",
    "member_picker": "view", "sync_member_picker": "edit",
    "budget_guardrails": "view",
    "cfo_override": "approve",
    "what_if": "view",
    "approve_revision": "approve",
    "reject_revision": "approve",
    "cancel_revision": "edit",
    # Payroll → GL bridge
    "post_to_gl": "approve",
    "reconcile_gl": "approve",
    "bulk_sync_gl": "approve",
}

POSITION_BUDGET_REVISIONABLE_FIELDS = (
    "department",
    "position",
    "fiscal_period_label",
    "fiscal_year",
    "budget_source",
    "currency",
    "fte",
    "statutory_benefits_rate",
    "allowances_rate",
    "local_tax_rate",
    "insurance_rate",
    "approved_headcount",
    "filled_headcount",
    "budget_amount",
    "status",
    "notes",
)


# ---------------------------------------------------------------------------
# ViewSets
# ---------------------------------------------------------------------------


class TeamViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.org_structure"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["name", "code", "description"]
    filterset_fields = ["department", "team_type", "is_active"]
    ordering_fields = ["name", "sort_order", "created_at"]
    ordering = ["sort_order", "name"]

    def get_queryset(self):
        qs = Team.objects.select_related("department", "department__division", "lead").annotate(
            member_count=Count(
                "positions__assignments",
                filter=Q(positions__assignments__is_active=True),
            ),
        )
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return TeamListSerializer
        if self.action in ("create", "update", "partial_update"):
            return TeamWriteSerializer
        return TeamDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))

    def _team_member_picker_position(self, team: Team) -> Position:
        """Return the dedicated non-primary position used by the dynamic member picker."""
        code = f"TMM-{team.id:05d}"
        defaults = {
            "title": f"{team.name} Team Member",
            "department": team.department,
            "team": team,
            "employment_type": Position.EmploymentType.FULL_TIME,
            "level": Position.Level.MID,
            "status": Position.Status.ACTIVE,
            "description": "Auto-managed position used by Team dynamic member picker.",
            "is_active": True,
        }
        position, created = Position.objects.get_or_create(
            organization=team.organization,
            code=code,
            defaults=defaults,
        )
        if created:
            return position

        update_fields: list[str] = []
        if position.team_id != team.id:
            position.team = team
            update_fields.append("team")
        if position.department_id != team.department_id:
            position.department = team.department
            update_fields.append("department")
        if position.status != Position.Status.ACTIVE:
            position.status = Position.Status.ACTIVE
            update_fields.append("status")
        if not position.is_active:
            position.is_active = True
            update_fields.append("is_active")
        if update_fields:
            position.save(update_fields=update_fields)
        return position

    def _member_picker_employee_payload(self, rec, *, is_locked: bool, is_picker_managed: bool):
        profile = getattr(rec.user, "profile", None)
        full_name = rec.user.get_full_name() or rec.user.email
        return {
            "user_id": rec.user_id,
            "employee_record_id": rec.id,
            "employee_id": (profile.employee_id if profile else "") or "",
            "full_name": full_name,
            "job_title": (profile.job_title if profile else "") or "",
            "department_name": (
                profile.department.name
                if profile and getattr(profile, "department_id", None)
                else None
            ),
            "employment_status": rec.employment_status,
            "is_locked": bool(is_locked),
            "is_picker_managed": bool(is_picker_managed),
        }

    def _member_picker_payload(self, team: Team, *, search: str = ""):
        picker_position = self._team_member_picker_position(team)
        active_assignments = (
            PositionAssignment.objects.filter(
                organization=team.organization,
                position__team=team,
                is_active=True,
            )
            .select_related("position")
            .order_by("user_id")
        )

        assignment_map: dict[int, dict[str, bool]] = {}
        for assignment in active_assignments:
            flags = assignment_map.setdefault(
                assignment.user_id,
                {"is_locked": False, "is_picker_managed": False},
            )
            if assignment.position_id == picker_position.id:
                flags["is_picker_managed"] = True
            else:
                flags["is_locked"] = True

        employee_qs = EmployeeRecord.objects.select_related(
            "user",
            "user__profile",
            "user__profile__department",
        ).filter(
            organization=team.organization,
            user__is_active=True,
        ).exclude(
            employment_status__in=[
                EmployeeRecord.EmploymentStatus.TERMINATED,
                EmployeeRecord.EmploymentStatus.RESIGNED,
            ],
        )
        if search:
            employee_qs = employee_qs.filter(
                Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
                | Q(user__email__icontains=search)
                | Q(user__profile__employee_id__icontains=search)
            )

        employees = list(employee_qs.order_by("user__first_name", "user__last_name", "id")[:400])
        assigned_user_ids = set(assignment_map.keys())

        assigned = []
        available = []
        for rec in employees:
            flags = assignment_map.get(rec.user_id, {"is_locked": False, "is_picker_managed": False})
            payload = self._member_picker_employee_payload(
                rec,
                is_locked=flags["is_locked"],
                is_picker_managed=flags["is_picker_managed"],
            )
            if rec.user_id in assigned_user_ids:
                assigned.append(payload)
            else:
                available.append(payload)

        assigned.sort(key=lambda item: (item["full_name"] or "").lower())
        available.sort(key=lambda item: (item["full_name"] or "").lower())
        return {
            "team_id": team.id,
            "team_name": team.name,
            "picker_position_id": picker_position.id,
            "assigned": assigned,
            "available": available,
            "locked_assigned_count": sum(1 for row in assigned if row["is_locked"]),
            "picker_assigned_count": sum(1 for row in assigned if row["is_picker_managed"]),
        }

    @action(detail=True, methods=["get"], url_path="member-picker")
    def member_picker(self, request, pk=None):
        team = self.get_object()
        search = (request.query_params.get("search") or "").strip()
        return Response(self._member_picker_payload(team, search=search))

    @action(detail=True, methods=["post"], url_path="sync-member-picker")
    def sync_member_picker(self, request, pk=None):
        team = self.get_object()
        user_ids = request.data.get("user_ids")
        if not isinstance(user_ids, list):
            raise ValidationError({"user_ids": "Expected a list of user ids."})

        normalized_user_ids: set[int] = set()
        for value in user_ids:
            try:
                normalized_user_ids.add(int(value))
            except (TypeError, ValueError):
                raise ValidationError({"user_ids": "All user ids must be valid integers."})

        employee_user_ids = set(
            EmployeeRecord.objects.filter(
                organization=team.organization,
                user__is_active=True,
            )
            .exclude(
                employment_status__in=[
                    EmployeeRecord.EmploymentStatus.TERMINATED,
                    EmployeeRecord.EmploymentStatus.RESIGNED,
                ],
            )
            .values_list("user_id", flat=True)
        )
        invalid_user_ids = sorted(normalized_user_ids - employee_user_ids)
        if invalid_user_ids:
            raise ValidationError({
                "user_ids": (
                    "Some users are not valid active employees for this organization: "
                    f"{', '.join(str(uid) for uid in invalid_user_ids)}"
                ),
            })

        picker_position = self._team_member_picker_position(team)
        active_team_assignments = list(
            PositionAssignment.objects.filter(
                organization=team.organization,
                position__team=team,
                is_active=True,
            ).select_related("position")
        )
        active_team_user_ids = {assignment.user_id for assignment in active_team_assignments}
        locked_user_ids = {
            assignment.user_id
            for assignment in active_team_assignments
            if assignment.position_id != picker_position.id
        }
        blocked_locked_user_ids = sorted(locked_user_ids - normalized_user_ids)
        if blocked_locked_user_ids:
            raise ValidationError({
                "user_ids": (
                    "Cannot remove locked members tied to role assignments. "
                    f"Blocked user ids: {', '.join(str(uid) for uid in blocked_locked_user_ids)}"
                ),
            })

        today = timezone.localdate()
        picker_active_assignments = PositionAssignment.objects.filter(
            organization=team.organization,
            position=picker_position,
            is_active=True,
        )
        for assignment in picker_active_assignments.exclude(user_id__in=normalized_user_ids):
            update_fields: list[str] = []
            if assignment.is_active:
                assignment.is_active = False
                update_fields.append("is_active")
            if assignment.end_date is None or assignment.end_date > today:
                assignment.end_date = today
                update_fields.append("end_date")
            if update_fields:
                assignment.save(update_fields=update_fields + ["updated_at"])

        existing_picker_by_user: dict[int, PositionAssignment] = {}
        for assignment in PositionAssignment.objects.filter(
            organization=team.organization,
            position=picker_position,
            user_id__in=normalized_user_ids,
        ).order_by("user_id", "-is_active", "-start_date", "-id"):
            if assignment.user_id not in existing_picker_by_user:
                existing_picker_by_user[assignment.user_id] = assignment

        for user_id in sorted(normalized_user_ids):
            if user_id in active_team_user_ids:
                continue

            assignment = existing_picker_by_user.get(user_id)
            if assignment:
                update_fields: list[str] = []
                if not assignment.is_active:
                    assignment.is_active = True
                    update_fields.append("is_active")
                if assignment.end_date is not None:
                    assignment.end_date = None
                    update_fields.append("end_date")
                if assignment.start_date is None:
                    assignment.start_date = today
                    update_fields.append("start_date")
                if update_fields:
                    assignment.save(update_fields=update_fields + ["updated_at"])
                continue

            PositionAssignment.objects.create(
                organization=team.organization,
                user_id=user_id,
                position=picker_position,
                start_date=today,
                is_primary=False,
                is_active=True,
                notes="Managed by Team dynamic member picker.",
            )

        return Response(self._member_picker_payload(team))


class PositionRoleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.positions"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["name", "code", "description"]
    filterset_fields = ["is_active"]
    ordering_fields = ["name", "code", "created_at"]
    ordering = ["name"]

    def get_queryset(self):
        qs = PositionRole.objects.annotate(
            position_count=Count("positions"),
        )
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return PositionRoleListSerializer
        if self.action in ("create", "update", "partial_update"):
            return PositionRoleWriteSerializer
        return PositionRoleDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


class PositionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.positions"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["title", "code", "description", "role__name", "role__code"]
    filterset_fields = [
        "role", "department", "team", "salary_structure",
        "employment_type", "level", "status", "is_active",
    ]
    ordering_fields = ["title", "code", "level", "department", "created_at"]
    ordering = ["department", "level", "title"]

    def get_queryset(self):
        active_requisition_qs = JobRequisition.objects.filter(
            organization_id=OuterRef("organization_id"),
            position_id=OuterRef("pk"),
            status__in=[
                JobRequisition.Status.DRAFT,
                JobRequisition.Status.PENDING_APPROVAL,
                JobRequisition.Status.APPROVED,
            ],
        ).order_by("-created_at", "-id")
        budget_guard_qs = PositionBudget.objects.filter(
            organization_id=OuterRef("organization_id"),
            department_id=OuterRef("department_id"),
        ).filter(
            Q(position_id=OuterRef("pk")) | Q(position__isnull=True),
        )
        qs = (
            Position.objects
            .select_related(
                "role", "department", "team", "cost_center", "reports_to",
                "salary_structure",
            )
            .annotate(
                filled_count=Count(
                    "assignments",
                    filter=Q(assignments__is_active=True),
                    distinct=True,
                ),
                vacancy_count=Count(
                    "vacancies",
                    filter=Q(vacancies__status=Vacancy.Status.OPEN),
                    distinct=True,
                ),
                direct_report_count=Count("direct_reports", distinct=True),
                active_requisition_id=Subquery(active_requisition_qs.values("id")[:1]),
                active_requisition_status=Subquery(active_requisition_qs.values("status")[:1]),
                has_position_budget=Exists(budget_guard_qs),
            )
        )
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        slot_status = (self.request.query_params.get("slot_status") or "").strip()
        if slot_status == Position.SlotStatus.PROPOSED:
            qs = qs.filter(slot_status=Position.SlotStatus.PROPOSED)
        elif slot_status == Position.SlotStatus.FILLED:
            qs = qs.exclude(slot_status=Position.SlotStatus.PROPOSED).filter(filled_count__gt=0)
        elif slot_status == Position.SlotStatus.VACANT:
            qs = qs.exclude(slot_status=Position.SlotStatus.PROPOSED).filter(filled_count=0)
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return PositionListSerializer
        if self.action in ("create", "update", "partial_update"):
            return PositionWriteSerializer
        return PositionDetailSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["can_view_salary_band"] = _can_view_position_salary_band(self.request)
        return context

    def perform_create(self, serializer):
        organization = _user_org(self.request)
        department = serializer.validated_data.get("department")
        if organization and department and getattr(department, "division_id", None):
            guardrails = get_business_unit_budget_guardrails(
                organization_id=organization.id,
            )
            division_guardrail = next(
                (
                    row
                    for row in guardrails
                    if row.get("division_id") == department.division_id
                ),
                None,
            )
            if division_guardrail and bool(division_guardrail.get("hiring_freeze")):
                raise ValidationError(
                    {
                        "non_field_errors": [
                            (
                                "Hiring freeze is active for this Business Unit because "
                                "position-budget variance has reached zero."
                            )
                        ],
                        "department": [
                            "Selected department belongs to a Business Unit under hiring freeze."
                        ],
                        "business_unit": division_guardrail.get("division_name"),
                        "requires_budget_increase": True,
                        "unallocated_budget": str(division_guardrail.get("unallocated_budget", Decimal("0"))),
                    }
                )
        serializer.save(organization=organization)

    @action(
        detail=False,
        methods=["get"],
        url_path="budget-guardrails",
    )
    def budget_guardrails(self, request):
        org = _user_org(request)
        if org is None:
            return Response(
                {
                    "business_units": [],
                    "all_frozen": False,
                }
            )

        fiscal_year_param = (request.query_params.get("fiscal_year") or "").strip()
        fiscal_year = int(fiscal_year_param) if fiscal_year_param.isdigit() else None
        guardrails = get_business_unit_budget_guardrails(
            organization_id=org.id,
            fiscal_year=fiscal_year,
        )
        payload = [
            {
                "division_id": row["division_id"],
                "division_name": row["division_name"],
                "budget_cap": str(row["budget_cap"]),
                "committed": str(row["committed"]),
                "pipeline": str(row["pipeline"]),
                "variance": str(row["variance"]),
                "unallocated_budget": str(row["unallocated_budget"]),
                "hiring_freeze": bool(row["hiring_freeze"]),
            }
            for row in guardrails
        ]
        return Response(
            {
                "business_units": payload,
                "all_frozen": bool(payload) and all(row["hiring_freeze"] for row in payload),
            }
        )

    @action(
        detail=False,
        methods=["get"],
        url_path="my-position",
        permission_classes=[IsAuthenticated],
    )
    def my_position(self, request):
        org = _user_org(request)
        if org is None:
            return Response(
                {"detail": "Organization context is not available."},
                status=status.HTTP_404_NOT_FOUND,
            )

        assignment = (
            PositionAssignment.objects
            .select_related("position")
            .filter(
                organization=org,
                user=request.user,
                is_active=True,
            )
            .order_by("-is_primary", "-start_date", "-id")
            .first()
        )
        if assignment is None:
            return Response(
                {"detail": "No active position assignment found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = PositionDetailSerializer(
            assignment.position,
            context={
                **self.get_serializer_context(),
                "can_view_salary_band": False,
            },
        )
        return Response(serializer.data)


class PositionAssignmentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.positions"
    rbac_action_map = _HR_ACTION_MAP
    filterset_fields = ["position", "user", "is_primary", "is_active"]
    ordering_fields = ["start_date", "end_date", "created_at"]
    ordering = ["-start_date"]

    def get_queryset(self):
        qs = PositionAssignment.objects.select_related(
            "user", "position", "position__department",
        )
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return PositionAssignmentListSerializer
        if self.action in ("create", "update", "partial_update"):
            return PositionAssignmentWriteSerializer
        return PositionAssignmentDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


class PositionBudgetViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.budgeting"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = [
        "department__name",
        "position__title",
        "fiscal_period_label",
        "notes",
    ]
    filterset_fields = [
        "department",
        "position",
        "fiscal_year",
        "budget_source",
        "currency",
        "status",
    ]
    ordering_fields = [
        "fiscal_year",
        "fiscal_period_label",
        "department",
        "budget_amount",
        "created_at",
    ]
    ordering = ["-fiscal_year", "department"]
    lock_guard_message = (
        "Financial period is locked. Submit a formal budget revision instead of editing this budget directly."
    )
    revision_required_message = (
        "Approved/Frozen budgets cannot be edited directly. Submit a formal budget revision workflow request."
    )

    @staticmethod
    def _to_decimal(value: Any, default=Decimal("0")) -> Decimal:
        if value is None:
            return default
        if isinstance(value, Decimal):
            return value
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return default

    @staticmethod
    def _format_money(value: Decimal) -> str:
        return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    @staticmethod
    def _normalize_for_payload(value: Any):
        if hasattr(value, "pk"):
            return value.pk
        if isinstance(value, Decimal):
            return str(value)
        return value

    @staticmethod
    def _normalize_for_compare(value: Any):
        if hasattr(value, "pk"):
            return value.pk
        if isinstance(value, Decimal):
            return value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        return value

    def _settings_for_org(self, org):
        if org is None:
            return None
        return (
            AuditComplianceSettings.objects.filter(organization=org)
            .only("financial_period_locking", "locked_before_date", "change_approval_required")
            .first()
        )

    def _is_fiscal_year_locked(self, *, org, fiscal_year: int | None) -> bool:
        if org is None or fiscal_year is None:
            return False
        lock_settings = self._settings_for_org(org)
        if not lock_settings or not lock_settings.financial_period_locking:
            return False
        if not lock_settings.locked_before_date:
            return False
        return int(fiscal_year) <= lock_settings.locked_before_date.year

    def _changed_fields(self, budget: PositionBudget, validated_data: dict[str, Any]) -> list[str]:
        changed: list[str] = []
        for field in POSITION_BUDGET_REVISIONABLE_FIELDS:
            if field not in validated_data:
                continue
            current = getattr(budget, field)
            incoming = validated_data[field]
            if self._normalize_for_compare(current) != self._normalize_for_compare(incoming):
                changed.append(field)
        return changed

    def _enforce_budget_mutation_guard(
        self,
        *,
        budget: PositionBudget,
        changed_fields: list[str],
        target_fiscal_year: int | None,
    ) -> None:
        if not changed_fields:
            return

        if self._is_fiscal_year_locked(org=budget.organization, fiscal_year=target_fiscal_year):
            raise ValidationError(
                {
                    "detail": self.lock_guard_message,
                    "locked": True,
                    "requires_revision_workflow": True,
                    "changed_fields": changed_fields,
                }
            )

        if budget.status in (PositionBudget.Status.APPROVED, PositionBudget.Status.FROZEN):
            raise ValidationError(
                {
                    "detail": self.revision_required_message,
                    "requires_revision_workflow": True,
                    "changed_fields": changed_fields,
                }
            )

    def _row_per_head_cost(self, row: PositionBudget) -> Decimal:
        structure = getattr(getattr(row, "position", None), "salary_structure", None)
        base_mid = None
        if structure:
            min_salary = self._to_decimal(getattr(structure, "min_salary", None), default=None)
            max_salary = self._to_decimal(getattr(structure, "max_salary", None), default=None)
            if min_salary is not None and max_salary is not None:
                base_mid = (min_salary + max_salary) / Decimal("2")
            else:
                base_mid = min_salary if min_salary is not None else max_salary

        if base_mid is not None:
            fte = self._to_decimal(getattr(row, "fte", None), Decimal("1"))
            statutory_rate = self._to_decimal(getattr(row, "statutory_benefits_rate", None))
            allowances_rate = self._to_decimal(getattr(row, "allowances_rate", None))
            local_tax_rate = self._to_decimal(getattr(row, "local_tax_rate", None))
            insurance_rate = self._to_decimal(getattr(row, "insurance_rate", None))
            multiplier = Decimal("1") + (
                statutory_rate + allowances_rate + local_tax_rate + insurance_rate
            ) / Decimal("100")
            return base_mid * multiplier * fte

        approved = int(row.approved_headcount or 0)
        if approved > 0:
            return self._to_decimal(row.budget_amount) / Decimal(str(approved))
        return Decimal("0")

    def _resolve_vacancy_pipeline(self, vacancy: Vacancy, row_map: dict[int, PositionBudget]) -> Decimal:
        position = getattr(vacancy, "position", None)
        if not position:
            return Decimal("0")
        budget_row = row_map.get(position.id)
        if budget_row is not None:
            return self._row_per_head_cost(budget_row)

        structure = getattr(position, "salary_structure", None)
        if not structure:
            return Decimal("0")
        min_salary = self._to_decimal(getattr(structure, "min_salary", None), default=None)
        max_salary = self._to_decimal(getattr(structure, "max_salary", None), default=None)
        if min_salary is not None and max_salary is not None:
            base_mid = (min_salary + max_salary) / Decimal("2")
        else:
            base_mid = min_salary if min_salary is not None else max_salary
        if base_mid is None:
            return Decimal("0")
        return base_mid * Decimal("1.25")

    def get_queryset(self):
        qs = PositionBudget.objects.select_related(
            "department", "position", "position__salary_structure", "approved_by",
        )
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return PositionBudgetListSerializer
        if self.action in ("create", "update", "partial_update"):
            return PositionBudgetWriteSerializer
        return PositionBudgetDetailSerializer

    def perform_create(self, serializer):
        org = _user_org(self.request)
        fiscal_year = serializer.validated_data.get("fiscal_year")
        if self._is_fiscal_year_locked(org=org, fiscal_year=fiscal_year):
            raise ValidationError(
                {
                    "detail": self.lock_guard_message,
                    "locked": True,
                    "requires_revision_workflow": True,
                }
            )
        serializer.save(organization=org)

    def perform_update(self, serializer):
        budget = serializer.instance
        changed_fields = self._changed_fields(budget, serializer.validated_data)
        target_fiscal_year = serializer.validated_data.get("fiscal_year", budget.fiscal_year)
        self._enforce_budget_mutation_guard(
            budget=budget,
            changed_fields=changed_fields,
            target_fiscal_year=target_fiscal_year,
        )
        serializer.save()

    def perform_destroy(self, instance):
        if self._is_fiscal_year_locked(org=instance.organization, fiscal_year=instance.fiscal_year):
            raise ValidationError(
                {
                    "detail": self.lock_guard_message,
                    "locked": True,
                    "requires_revision_workflow": True,
                }
            )
        if instance.status in (PositionBudget.Status.APPROVED, PositionBudget.Status.FROZEN):
            raise ValidationError(
                {
                    "detail": self.revision_required_message,
                    "requires_revision_workflow": True,
                }
            )
        instance.delete()

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        budget = self.get_object()
        budget.status = PositionBudget.Status.APPROVED
        budget.approved_by = request.user
        budget.approved_at = timezone.now()
        budget.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
        return Response(PositionBudgetDetailSerializer(budget).data)

    @action(detail=False, methods=["post"], url_path="what-if")
    def what_if(self, request):
        org = _user_org(request) if not _is_superuser(request) else None
        fiscal_year_raw = request.data.get("fiscal_year")
        department_id_raw = request.data.get("department")
        position_id_raw = request.data.get("position")
        currency_code = (request.data.get("currency") or "").strip().upper()

        try:
            additional_headcount = int(request.data.get("additional_headcount", 0))
        except (TypeError, ValueError):
            raise ValidationError({"additional_headcount": "Must be a valid integer greater than zero."})
        if additional_headcount <= 0:
            raise ValidationError({"additional_headcount": "Must be greater than zero."})

        try:
            fiscal_year = int(fiscal_year_raw) if fiscal_year_raw not in (None, "") else None
        except (TypeError, ValueError):
            raise ValidationError({"fiscal_year": "Must be a valid year."})
        try:
            department_id = int(department_id_raw) if department_id_raw not in (None, "") else None
        except (TypeError, ValueError):
            raise ValidationError({"department": "Must be a valid department id."})
        try:
            position_id = int(position_id_raw) if position_id_raw not in (None, "") else None
        except (TypeError, ValueError):
            raise ValidationError({"position": "Must be a valid position id."})

        budgets_qs = PositionBudget.objects.select_related(
            "department",
            "position",
            "position__salary_structure",
        )
        if org:
            budgets_qs = budgets_qs.filter(organization=org)
        if fiscal_year is not None:
            budgets_qs = budgets_qs.filter(fiscal_year=fiscal_year)
        if department_id is not None:
            budgets_qs = budgets_qs.filter(department_id=department_id)
        if position_id is not None:
            budgets_qs = budgets_qs.filter(position_id=position_id)
        if currency_code:
            budgets_qs = budgets_qs.filter(currency=currency_code)
        budget_rows = list(budgets_qs.order_by("-fiscal_year", "-updated_at", "-id"))

        position_budget_map: dict[int, PositionBudget] = {}
        baseline_budgeted = Decimal("0")
        baseline_committed = Decimal("0")
        for row in budget_rows:
            baseline_budgeted += self._to_decimal(row.budget_amount)
            baseline_committed += self._row_per_head_cost(row) * Decimal(str(int(row.filled_headcount or 0)))
            if row.position_id and row.position_id not in position_budget_map:
                position_budget_map[row.position_id] = row

        vacancies_qs = Vacancy.objects.filter(
            status__in=(Vacancy.Status.OPEN, Vacancy.Status.ON_HOLD),
        ).select_related("position", "position__department", "position__salary_structure")
        if org:
            vacancies_qs = vacancies_qs.filter(organization=org)
        if department_id is not None:
            vacancies_qs = vacancies_qs.filter(position__department_id=department_id)
        if position_id is not None:
            vacancies_qs = vacancies_qs.filter(position_id=position_id)

        baseline_pipeline = Decimal("0")
        for vacancy in vacancies_qs:
            baseline_pipeline += self._resolve_vacancy_pipeline(vacancy, position_budget_map)

        reference_row = None
        if position_id is not None:
            reference_row = position_budget_map.get(position_id)
        if reference_row is None and budget_rows:
            reference_row = budget_rows[0]

        per_head_override = request.data.get("per_head_cost")
        if per_head_override in ("", None):
            per_head_cost = self._row_per_head_cost(reference_row) if reference_row else Decimal("0")
        else:
            per_head_cost = self._to_decimal(per_head_override)
            if per_head_cost <= 0:
                raise ValidationError({"per_head_cost": "Must be greater than zero when provided."})

        additional_cost = per_head_cost * Decimal(str(additional_headcount))
        scenario_committed = baseline_committed + additional_cost
        baseline_variance = baseline_budgeted - baseline_committed - baseline_pipeline
        scenario_variance = baseline_budgeted - scenario_committed - baseline_pipeline

        project_revenue = self._to_decimal(request.data.get("project_revenue"), default=None)
        other_project_costs = self._to_decimal(request.data.get("other_project_costs"), default=Decimal("0"))
        baseline_margin_percent = None
        scenario_margin_percent = None
        margin_delta_percent = None
        if project_revenue is not None and project_revenue > 0:
            baseline_total_cost = baseline_committed + baseline_pipeline + other_project_costs
            scenario_total_cost = scenario_committed + baseline_pipeline + other_project_costs
            baseline_margin_percent = (
                ((project_revenue - baseline_total_cost) / project_revenue) * Decimal("100")
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            scenario_margin_percent = (
                ((project_revenue - scenario_total_cost) / project_revenue) * Decimal("100")
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            margin_delta_percent = (
                scenario_margin_percent - baseline_margin_percent
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return Response(
            {
                "fiscal_year": fiscal_year,
                "department_id": department_id,
                "position_id": position_id,
                "currency": currency_code or (budget_rows[0].currency if budget_rows else None),
                "assumptions": {
                    "additional_headcount": additional_headcount,
                    "per_head_cost": self._format_money(per_head_cost),
                    "project_revenue": self._format_money(project_revenue) if project_revenue is not None else None,
                    "other_project_costs": self._format_money(other_project_costs),
                },
                "baseline": {
                    "budgeted": self._format_money(baseline_budgeted),
                    "committed": self._format_money(baseline_committed),
                    "pipeline": self._format_money(baseline_pipeline),
                    "variance": self._format_money(baseline_variance),
                    "project_margin_percent": (
                        float(baseline_margin_percent)
                        if baseline_margin_percent is not None
                        else None
                    ),
                },
                "scenario": {
                    "additional_cost": self._format_money(additional_cost),
                    "committed": self._format_money(scenario_committed),
                    "variance": self._format_money(scenario_variance),
                    "project_margin_percent": (
                        float(scenario_margin_percent)
                        if scenario_margin_percent is not None
                        else None
                    ),
                    "margin_delta_percent": (
                        float(margin_delta_percent)
                        if margin_delta_percent is not None
                        else None
                    ),
                },
            }
        )


class PositionBudgetRevisionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.budgeting"
    rbac_action_map = _HR_ACTION_MAP
    filterset_fields = ["budget", "status", "budget__fiscal_year", "budget__department"]
    ordering_fields = ["created_at", "revision_number", "status"]
    ordering = ["-created_at"]

    @staticmethod
    def _to_decimal(value: Any, default=Decimal("0")) -> Decimal:
        if value is None:
            return default
        if isinstance(value, Decimal):
            return value
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return default

    @staticmethod
    def _normalize_for_payload(value: Any):
        if hasattr(value, "pk"):
            return value.pk
        if isinstance(value, Decimal):
            return str(value)
        return value

    def _snapshot_budget(self, budget: PositionBudget) -> dict[str, Any]:
        snapshot: dict[str, Any] = {}
        for field in POSITION_BUDGET_REVISIONABLE_FIELDS:
            snapshot[field] = self._normalize_for_payload(getattr(budget, field))
        return snapshot

    def _normalize_proposed_changes(
        self,
        *,
        budget: PositionBudget,
        proposed_changes: dict[str, Any],
    ) -> dict[str, Any]:
        write_serializer = PositionBudgetWriteSerializer(
            budget,
            data=proposed_changes,
            partial=True,
            context={"request": self.request},
        )
        write_serializer.is_valid(raise_exception=True)
        normalized: dict[str, Any] = {}
        for field in POSITION_BUDGET_REVISIONABLE_FIELDS:
            if field not in write_serializer.validated_data:
                continue
            normalized[field] = self._normalize_for_payload(write_serializer.validated_data[field])
        return normalized

    def _changed_fields(self, *, budget: PositionBudget, normalized_changes: dict[str, Any]) -> list[str]:
        snapshot = self._snapshot_budget(budget)
        return [
            field
            for field, incoming in normalized_changes.items()
            if snapshot.get(field) != incoming
        ]

    def get_queryset(self):
        qs = PositionBudgetRevision.objects.select_related(
            "budget",
            "budget__department",
            "budget__position",
            "requested_by",
            "reviewed_by",
        )
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return PositionBudgetRevisionListSerializer
        if self.action in ("create",):
            return PositionBudgetRevisionWriteSerializer
        return PositionBudgetRevisionDetailSerializer

    def perform_create(self, serializer):
        org = _user_org(self.request)
        budget = serializer.validated_data["budget"]
        if org and budget.organization_id != org.id:
            raise ValidationError({"budget": "Selected budget does not belong to your organization."})

        if PositionBudgetRevision.objects.filter(
            budget=budget,
            status=PositionBudgetRevision.Status.PENDING_APPROVAL,
        ).exists():
            raise ValidationError(
                {
                    "budget": (
                        "There is already a pending revision request for this budget. "
                        "Resolve it before submitting another revision."
                    )
                }
            )

        reason = (serializer.validated_data.get("reason") or "").strip()
        if not reason:
            raise ValidationError({"reason": "Revision reason is required."})

        raw_changes = serializer.validated_data.get("proposed_changes") or {}
        if not isinstance(raw_changes, dict):
            raise ValidationError({"proposed_changes": "Proposed changes must be a JSON object."})

        normalized_changes = self._normalize_proposed_changes(
            budget=budget,
            proposed_changes=raw_changes,
        )
        changed_fields = self._changed_fields(
            budget=budget,
            normalized_changes=normalized_changes,
        )
        if not changed_fields:
            raise ValidationError(
                {"proposed_changes": "No effective changes were detected for this revision request."}
            )

        next_revision = (
            PositionBudgetRevision.objects.filter(budget=budget).aggregate(max_n=Max("revision_number"))["max_n"] or 0
        ) + 1

        serializer.save(
            organization=budget.organization,
            budget=budget,
            reason=reason,
            revision_number=next_revision,
            status=PositionBudgetRevision.Status.PENDING_APPROVAL,
            requested_by=self.request.user,
            proposed_changes=normalized_changes,
            snapshot_before=self._snapshot_budget(budget),
        )

    @action(detail=True, methods=["post"], url_path="approve")
    def approve_revision(self, request, pk=None):
        revision = self.get_object()
        if revision.status != PositionBudgetRevision.Status.PENDING_APPROVAL:
            raise ValidationError({"detail": "Only pending revisions can be approved."})

        proposed_changes = revision.proposed_changes or {}
        if not isinstance(proposed_changes, dict) or not proposed_changes:
            raise ValidationError({"detail": "Revision does not contain proposed changes to apply."})

        review_notes = (request.data.get("review_notes") or "").strip()
        with transaction.atomic():
            budget_serializer = PositionBudgetWriteSerializer(
                revision.budget,
                data=proposed_changes,
                partial=True,
                context={"request": request},
            )
            budget_serializer.is_valid(raise_exception=True)
            budget = budget_serializer.save()
            budget.status = PositionBudget.Status.APPROVED
            budget.approved_by = request.user
            budget.approved_at = timezone.now()
            budget.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])

            revision.status = PositionBudgetRevision.Status.APPROVED
            revision.reviewed_by = request.user
            revision.reviewed_at = timezone.now()
            revision.review_notes = review_notes
            revision.save(
                update_fields=[
                    "status",
                    "reviewed_by",
                    "reviewed_at",
                    "review_notes",
                    "updated_at",
                ]
            )

        return Response(PositionBudgetRevisionDetailSerializer(revision).data)

    @action(detail=True, methods=["post"], url_path="reject")
    def reject_revision(self, request, pk=None):
        revision = self.get_object()
        if revision.status != PositionBudgetRevision.Status.PENDING_APPROVAL:
            raise ValidationError({"detail": "Only pending revisions can be rejected."})

        review_notes = (request.data.get("review_notes") or "").strip()
        if not review_notes:
            raise ValidationError({"review_notes": "Provide a reason for rejecting this revision."})

        revision.status = PositionBudgetRevision.Status.REJECTED
        revision.reviewed_by = request.user
        revision.reviewed_at = timezone.now()
        revision.review_notes = review_notes
        revision.save(
            update_fields=["status", "reviewed_by", "reviewed_at", "review_notes", "updated_at"]
        )
        return Response(PositionBudgetRevisionDetailSerializer(revision).data)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel_revision(self, request, pk=None):
        revision = self.get_object()
        if revision.status != PositionBudgetRevision.Status.PENDING_APPROVAL:
            raise ValidationError({"detail": "Only pending revisions can be cancelled."})
        requester_id = revision.requested_by_id
        is_org_admin = getattr(getattr(request.user, "profile", None), "role", "") == "admin"
        if not request.user.is_superuser and not is_org_admin and request.user.id != requester_id:
            raise PermissionDenied("Only the requester or an admin can cancel this revision.")

        cancel_notes = (request.data.get("review_notes") or "").strip()
        revision.status = PositionBudgetRevision.Status.CANCELLED
        revision.reviewed_by = request.user
        revision.reviewed_at = timezone.now()
        revision.review_notes = cancel_notes
        revision.save(
            update_fields=["status", "reviewed_by", "reviewed_at", "review_notes", "updated_at"]
        )
        return Response(PositionBudgetRevisionDetailSerializer(revision).data)


class VacancyViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.vacancies"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["title", "reason", "notes"]
    filterset_fields = ["position", "status", "priority", "hiring_manager"]
    ordering_fields = ["opened_date", "target_fill_date", "priority", "created_at"]
    ordering = ["-opened_date"]

    def get_queryset(self):
        qs = Vacancy.objects.select_related(
            "position", "position__department",
            "hiring_manager", "approved_by", "filled_by",
        )
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return VacancyListSerializer
        if self.action in ("create", "update", "partial_update"):
            return VacancyWriteSerializer
        return VacancyDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))

    @action(detail=True, methods=["post"])
    def fill(self, request, pk=None):
        vacancy = self.get_object()
        vacancy.status = Vacancy.Status.FILLED
        vacancy.filled_date = timezone.localdate()
        filled_by_id = request.data.get("filled_by")
        if filled_by_id:
            from django.contrib.auth import get_user_model
            vacancy.filled_by = get_user_model().objects.get(pk=filled_by_id)
        vacancy.save(update_fields=[
            "status", "filled_date", "filled_by", "updated_at",
        ])
        return Response(VacancyDetailSerializer(vacancy).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        vacancy = self.get_object()
        vacancy.status = Vacancy.Status.CANCELLED
        vacancy.save(update_fields=["status", "updated_at"])
        return Response(VacancyDetailSerializer(vacancy).data)

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        vacancy = self.get_object()
        vacancy.status = Vacancy.Status.OPEN
        vacancy.filled_date = None
        vacancy.filled_by = None
        vacancy.save(update_fields=[
            "status", "filled_date", "filled_by", "updated_at",
        ])
        return Response(VacancyDetailSerializer(vacancy).data)


# ---------------------------------------------------------------------------
# Read-only API Views
# ---------------------------------------------------------------------------


class OrgChartView(APIView):
    """Nested organization chart: divisions → departments → teams → positions."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.org_structure"
    rbac_action = "view"

    def get(self, request):
        from apps.accounts.models import UserProfile
        from apps.projects.models import ProjectTask

        org = _user_org(request) if not _is_superuser(request) else None

        divisions_qs = Division.objects.select_related("head").order_by("sort_order", "name")
        if org:
            divisions_qs = divisions_qs.filter(organization=org)

        active_assignments_qs = PositionAssignment.objects.filter(
            is_active=True,
        ).select_related("user", "user__profile", "position", "position__department")
        if org:
            active_assignments_qs = active_assignments_qs.filter(organization=org)
        active_assignments_qs = active_assignments_qs.order_by("-is_primary", "-start_date", "-id")
        active_assignments = list(active_assignments_qs)

        user_ids = sorted({assignment.user_id for assignment in active_assignments})
        employee_node_map: dict[int, dict] = {}
        if user_ids:
            profiles_qs = UserProfile.objects.select_related("department").filter(user_id__in=user_ids)
            if org:
                profiles_qs = profiles_qs.filter(organization=org)
            profiles_by_user = {profile.user_id: profile for profile in profiles_qs}

            direct_reports_qs = UserProfile.objects.filter(reporting_manager_id__in=user_ids)
            if org:
                direct_reports_qs = direct_reports_qs.filter(organization=org)
            direct_report_counts = dict(
                direct_reports_qs.values("reporting_manager_id")
                .annotate(total=Count("id"))
                .values_list("reporting_manager_id", "total"),
            )

            compensation_qs = CompensationRecord.objects.filter(
                user_id__in=user_ids,
                status=CompensationRecord.Status.ACTIVE,
            ).order_by("user_id", "-effective_date", "-id")
            if org:
                compensation_qs = compensation_qs.filter(organization=org)
            active_compensation_by_user: dict[int, CompensationRecord] = {}
            for compensation in compensation_qs:
                active_compensation_by_user.setdefault(compensation.user_id, compensation)

            structures_qs = SalaryStructure.objects.filter(is_active=True).order_by(
                "organization_id", "grade_level", "name",
            )
            if org:
                structures_qs = structures_qs.filter(organization=org)
            salary_structures_by_org: dict[int, list[SalaryStructure]] = defaultdict(list)
            for structure in structures_qs:
                salary_structures_by_org[structure.organization_id].append(structure)

            acting_roles_map: dict[int, list[str]] = defaultdict(list)
            for assignment in active_assignments:
                if assignment.is_primary:
                    continue
                title = assignment.position.title.strip()
                if title and title not in acting_roles_map[assignment.user_id]:
                    acting_roles_map[assignment.user_id].append(title)

            project_tasks_qs = ProjectTask.objects.filter(
                assigned_user_id__in=user_ids,
                assigned_user__isnull=False,
            ).select_related("phase__project").order_by("assigned_user_id", "due_date", "id")
            if org:
                project_tasks_qs = project_tasks_qs.filter(organization=org)
            project_tasks = list(project_tasks_qs)

            project_assignment_count_map: dict[int, int] = defaultdict(int)
            project_assignments_map: dict[int, list[dict]] = defaultdict(list)
            for task in project_tasks:
                project_assignment_count_map[task.assigned_user_id] += 1
                assignments_for_user = project_assignments_map[task.assigned_user_id]
                if len(assignments_for_user) >= 5:
                    continue
                assignments_for_user.append({
                    "project_id": task.phase.project_id,
                    "project_name": task.phase.project.name,
                    "task_id": task.id,
                    "task_name": task.name,
                    "status": task.status,
                    "due_date": task.due_date.isoformat() if task.due_date else None,
                })

            for user_id in user_ids:
                profile = profiles_by_user.get(user_id)
                compensation = active_compensation_by_user.get(user_id)
                salary_band = None
                if compensation:
                    structures = salary_structures_by_org.get(compensation.organization_id, [])
                    for structure in structures:
                        if structure.min_salary <= compensation.base_salary <= structure.max_salary:
                            salary_band = (
                                f"{structure.name} "
                                f"({structure.currency} {structure.min_salary} - {structure.max_salary})"
                            )
                            break
                    if salary_band is None:
                        salary_band = f"{compensation.currency} {compensation.base_salary}"

                employee_node_map[user_id] = {
                    "phone": profile.phone if profile else "",
                    "office_location": profile.office_location if profile else "",
                    "department_name": profile.department.name if profile and profile.department_id else None,
                    "direct_report_count": direct_report_counts.get(user_id, 0),
                    "salary_band": salary_band,
                    "acting_roles": acting_roles_map.get(user_id, []),
                    "project_assignment_count": project_assignment_count_map.get(user_id, 0),
                    "project_assignments": project_assignments_map.get(user_id, []),
                }

        result = []
        for div in divisions_qs:
            departments_data = []
            for dept in div.departments.select_related("head").order_by("sort_order", "name"):
                # Teams with positions
                teams = (
                    Team.objects.filter(department=dept, is_active=True)
                    .select_related("lead")
                    .prefetch_related(
                        Prefetch(
                            "positions",
                            queryset=Position.objects.filter(
                                is_active=True,
                            ).select_related("department").prefetch_related(
                                Prefetch(
                                    "assignments",
                                    queryset=active_assignments_qs,
                                    to_attr="prefetched_active_assignments",
                                ),
                            ),
                        ),
                    )
                    .order_by("sort_order", "name")
                )

                # Positions not assigned to any team
                unassigned_positions = (
                    Position.objects.filter(
                        department=dept, team__isnull=True, is_active=True,
                    ).select_related("department").prefetch_related(
                        Prefetch(
                            "assignments",
                            queryset=active_assignments_qs,
                            to_attr="prefetched_active_assignments",
                        ),
                    )
                )

                departments_data.append({
                    "id": dept.id,
                    "name": dept.name,
                    "code": dept.code,
                    "head_name": dept.head.get_full_name() if dept.head_id else None,
                    "teams": OrgChartTeamSerializer(
                        teams,
                        many=True,
                        context={"employee_node_map": employee_node_map},
                    ).data,
                    "positions": OrgChartPositionSerializer(
                        unassigned_positions,
                        many=True,
                        context={"employee_node_map": employee_node_map},
                    ).data,
                })

            result.append({
                "id": div.id,
                "name": div.name,
                "code": div.code,
                "head_name": div.head.get_full_name() if div.head_id else None,
                "departments": departments_data,
            })

        return Response(result)


class ReportingLineUpdateView(APIView):
    """Update a user's reporting manager within the organization."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.org_structure"
    rbac_action = "edit"

    def patch(self, request, user_id: int):
        from apps.accounts.models import UserProfile

        org = _user_org(request) if not _is_superuser(request) else None
        profiles_qs = UserProfile.objects.select_related("user", "reporting_manager")
        if org:
            profiles_qs = profiles_qs.filter(organization=org)

        target_profile = profiles_qs.filter(user_id=user_id).first()
        if not target_profile:
            return Response(
                {"detail": "Target user profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        reports_to_raw = request.data.get("reports_to", None)
        if reports_to_raw in ("", "null", "None"):
            reports_to_raw = None

        if reports_to_raw is None:
            manager_profile = None
        else:
            try:
                reports_to_id = int(reports_to_raw)
            except (TypeError, ValueError):
                return Response(
                    {"reports_to": ["reports_to must be a valid user id or null."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if reports_to_id == user_id:
                return Response(
                    {"reports_to": ["A user cannot report to themselves."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            manager_profile = profiles_qs.filter(user_id=reports_to_id).first()
            if not manager_profile:
                return Response(
                    {"reports_to": ["Selected manager profile was not found in this organization."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if manager_profile.organization_id != target_profile.organization_id:
                return Response(
                    {"reports_to": ["Manager must belong to the same organization."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Prevent circular manager chains.
            seen: set[int] = {manager_profile.user_id}
            current_manager_id = manager_profile.reporting_manager_id
            while current_manager_id:
                if current_manager_id == target_profile.user_id:
                    return Response(
                        {"reports_to": ["Circular reporting relationships are not allowed."]},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if current_manager_id in seen:
                    break
                seen.add(current_manager_id)
                current_manager_id = (
                    profiles_qs.filter(user_id=current_manager_id)
                    .values_list("reporting_manager_id", flat=True)
                    .first()
                )

        target_profile.reporting_manager = manager_profile.user if manager_profile else None
        target_profile.save(update_fields=["reporting_manager"])

        return Response({
            "user_id": target_profile.user_id,
            "user_name": target_profile.user.get_full_name(),
            "reports_to": manager_profile.user_id if manager_profile else None,
            "reports_to_name": manager_profile.user.get_full_name() if manager_profile else None,
        })


class ReportingLinesView(APIView):
    """Flat list of users with their reporting relationships."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.org_structure"
    rbac_action = "view"

    def get(self, request):
        from apps.accounts.models import UserProfile

        org = _user_org(request) if not _is_superuser(request) else None

        profiles_qs = (
            UserProfile.objects
            .filter(identity_type__in=["user", "employee"])
            .select_related("user", "department", "reporting_manager")
        )
        if org:
            profiles_qs = profiles_qs.filter(organization=org)

        # Count direct reports per user
        direct_report_counts = dict(
            profiles_qs.filter(reporting_manager__isnull=False)
            .values_list("reporting_manager_id")
            .annotate(count=Count("id"))
            .values_list("reporting_manager_id", "count")
        )

        result = []
        for profile in profiles_qs:
            result.append({
                "id": profile.user_id,
                "full_name": profile.user.get_full_name(),
                "job_title": profile.job_title,
                "department": profile.department.name if profile.department_id else None,
                "reports_to": profile.reporting_manager_id,
                "direct_report_count": direct_report_counts.get(profile.user_id, 0),
            })

        return Response(result)


class HeadcountSummaryView(APIView):
    """Aggregate headcount metrics by department for the current fiscal year."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.budgeting"
    rbac_action = "view"

    @staticmethod
    def _to_decimal(value, default=Decimal("0")):
        if value is None:
            return default
        if isinstance(value, Decimal):
            return value
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return default

    @staticmethod
    def _format_money(value: Decimal) -> str:
        return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    @staticmethod
    def _resolve_heat(utilization_ratio: Decimal) -> tuple[str, str]:
        if utilization_ratio >= Decimal("0.90"):
            return ("red", "Critical burn")
        if utilization_ratio >= Decimal("0.75"):
            return ("yellow", "Watchlist")
        return ("green", "Healthy")

    def get(self, request):
        org = _user_org(request) if not _is_superuser(request) else None
        fiscal_year = request.query_params.get("fiscal_year")
        currency_code = (request.query_params.get("currency") or "").strip().upper()

        budgets_qs = PositionBudget.objects.all()
        if fiscal_year:
            budgets_qs = budgets_qs.filter(fiscal_year=fiscal_year)
        if currency_code:
            budgets_qs = budgets_qs.filter(currency=currency_code)
        if org:
            budgets_qs = budgets_qs.filter(organization=org)

        budget_rows = list(
            budgets_qs.select_related(
                "position",
                "position__department",
                "position__salary_structure",
            )
        )

        position_budget_map: dict[int, PositionBudget] = {}

        budgeted_total = Decimal("0")
        committed_total = Decimal("0")
        project_buckets: dict[str, dict[str, Decimal | str]] = {}
        department_buckets: dict[int, dict[str, Decimal | str | int]] = {}

        def _row_base_mid(row: PositionBudget) -> Decimal | None:
            if not row.position_id:
                return None
            structure = getattr(row.position, "salary_structure", None)
            if not structure:
                return None
            min_salary = self._to_decimal(getattr(structure, "min_salary", None), default=None)
            max_salary = self._to_decimal(getattr(structure, "max_salary", None), default=None)
            if min_salary is not None and max_salary is not None:
                return (min_salary + max_salary) / Decimal("2")
            return min_salary if min_salary is not None else max_salary

        def _row_per_head(row: PositionBudget) -> Decimal:
            base_mid = _row_base_mid(row)
            if base_mid is not None:
                fte = self._to_decimal(row.fte, Decimal("1"))
                statutory_rate = self._to_decimal(row.statutory_benefits_rate)
                allowances_rate = self._to_decimal(row.allowances_rate)
                local_tax_rate = self._to_decimal(getattr(row, "local_tax_rate", None))
                insurance_rate = self._to_decimal(getattr(row, "insurance_rate", None))
                multiplier = Decimal("1") + (
                    statutory_rate + allowances_rate + local_tax_rate + insurance_rate
                ) / Decimal("100")
                return base_mid * multiplier * fte

            approved = int(row.approved_headcount or 0)
            if approved > 0:
                return self._to_decimal(row.budget_amount) / Decimal(str(approved))
            return Decimal("0")

        for row in budget_rows:
            row_budget_amount = self._to_decimal(row.budget_amount)
            row_filled = int(row.filled_headcount or 0)
            row_per_head = _row_per_head(row)
            row_committed = row_per_head * Decimal(str(row_filled))

            budgeted_total += row_budget_amount
            committed_total += row_committed
            if row.position_id and row.position_id not in position_budget_map:
                position_budget_map[row.position_id] = row

            dept_key = row.department_id
            if dept_key not in department_buckets:
                department_buckets[dept_key] = {
                    "department_id": dept_key,
                    "department_name": row.department.name,
                    "budgeted": Decimal("0"),
                    "committed": Decimal("0"),
                    "pipeline": Decimal("0"),
                }
            department_buckets[dept_key]["budgeted"] += row_budget_amount
            department_buckets[dept_key]["committed"] += row_committed

            if row.budget_source == PositionBudget.BudgetSource.PROJECT_FUNDING:
                project_label = (row.fiscal_period_label or "").strip() or f"FY {row.fiscal_year}"
                if project_label not in project_buckets:
                    project_buckets[project_label] = {
                        "label": project_label,
                        "budgeted": Decimal("0"),
                        "committed": Decimal("0"),
                        "pipeline": Decimal("0"),
                    }
                project_buckets[project_label]["budgeted"] += row_budget_amount
                project_buckets[project_label]["committed"] += row_committed

        summary = (
            budgets_qs.values("department__id", "department__name")
            .annotate(
                total_approved=Sum("approved_headcount"),
                total_filled=Sum("filled_headcount"),
                total_budget=Sum("budget_amount"),
            )
            .order_by("department__name")
        )

        # Overall totals
        totals = budgets_qs.aggregate(
            total_approved=Sum("approved_headcount"),
            total_filled=Sum("filled_headcount"),
            total_budget=Sum("budget_amount"),
        )

        # Open vacancy count + recruitment pipeline estimate
        vacancies_qs = Vacancy.objects.filter(
            status__in=(Vacancy.Status.OPEN, Vacancy.Status.ON_HOLD)
        ).select_related("position", "position__department", "position__salary_structure")
        if org:
            vacancies_qs = vacancies_qs.filter(organization=org)

        pipeline_total = Decimal("0")
        open_vacancies = 0
        for vacancy in vacancies_qs:
            open_vacancies += 1

            position = vacancy.position
            if not position:
                continue

            budget_row = position_budget_map.get(position.id)

            # Respect currency filter for non-matching rows.
            if currency_code:
                structure_currency = getattr(getattr(position, "salary_structure", None), "currency", None)
                row_currency = budget_row.currency if budget_row else None
                if structure_currency and structure_currency.upper() != currency_code:
                    continue
                if not structure_currency and row_currency and row_currency.upper() != currency_code:
                    continue
                if not structure_currency and not row_currency:
                    continue

            if budget_row is not None:
                vacancy_pipeline = _row_per_head(budget_row)
            else:
                structure = getattr(position, "salary_structure", None)
                if not structure:
                    continue
                min_salary = self._to_decimal(getattr(structure, "min_salary", None), default=None)
                max_salary = self._to_decimal(getattr(structure, "max_salary", None), default=None)
                if min_salary is not None and max_salary is not None:
                    base_mid = (min_salary + max_salary) / Decimal("2")
                else:
                    base_mid = min_salary if min_salary is not None else max_salary
                if base_mid is None:
                    continue
                vacancy_pipeline = base_mid * Decimal("1.25")

            pipeline_total += vacancy_pipeline

            dept_bucket = department_buckets.get(position.department_id)
            if dept_bucket is not None:
                dept_bucket["pipeline"] += vacancy_pipeline

            if budget_row and budget_row.budget_source == PositionBudget.BudgetSource.PROJECT_FUNDING:
                project_label = (budget_row.fiscal_period_label or "").strip() or f"FY {budget_row.fiscal_year}"
                if project_label not in project_buckets:
                    project_buckets[project_label] = {
                        "label": project_label,
                        "budgeted": Decimal("0"),
                        "committed": Decimal("0"),
                        "pipeline": Decimal("0"),
                    }
                project_buckets[project_label]["pipeline"] += vacancy_pipeline

        variance_total = budgeted_total - committed_total - pipeline_total
        merit_pool_total = variance_total if variance_total > Decimal("0") else Decimal("0")

        department_heatmap = []
        for department in sorted(department_buckets.values(), key=lambda row: row["department_name"]):
            budgeted = self._to_decimal(department["budgeted"])
            committed = self._to_decimal(department["committed"])
            pipeline = self._to_decimal(department["pipeline"])
            utilization_ratio = (
                (committed + pipeline) / budgeted
                if budgeted > 0
                else Decimal("0")
            )
            heat_status, heat_label = self._resolve_heat(utilization_ratio)
            department_heatmap.append({
                "department_id": department["department_id"],
                "department_name": department["department_name"],
                "budgeted": self._format_money(budgeted),
                "committed": self._format_money(committed),
                "pipeline": self._format_money(pipeline),
                "utilization_ratio": float(utilization_ratio.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)),
                "utilization_percent": float((utilization_ratio * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
                "heat_status": heat_status,
                "heat_label": heat_label,
            })

        project_heatmap = []
        for project in sorted(project_buckets.values(), key=lambda row: row["label"]):
            budgeted = self._to_decimal(project["budgeted"])
            committed = self._to_decimal(project["committed"])
            pipeline = self._to_decimal(project["pipeline"])
            utilization_ratio = (
                (committed + pipeline) / budgeted
                if budgeted > 0
                else Decimal("0")
            )
            heat_status, heat_label = self._resolve_heat(utilization_ratio)
            project_heatmap.append({
                "key": project["label"].lower().replace(" ", "_"),
                "label": project["label"],
                "budgeted": self._format_money(budgeted),
                "committed": self._format_money(committed),
                "pipeline": self._format_money(pipeline),
                "utilization_ratio": float(utilization_ratio.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)),
                "utilization_percent": float((utilization_ratio * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
                "heat_status": heat_status,
                "heat_label": heat_label,
            })

        business_unit_guardrails = []
        if org:
            for row in get_business_unit_budget_guardrails(
                organization_id=org.id,
                fiscal_year=int(fiscal_year) if fiscal_year else None,
            ):
                business_unit_guardrails.append(
                    {
                        "division_id": row["division_id"],
                        "division_name": row["division_name"],
                        "budget_cap": self._format_money(self._to_decimal(row["budget_cap"])),
                        "committed": self._format_money(self._to_decimal(row["committed"])),
                        "pipeline": self._format_money(self._to_decimal(row["pipeline"])),
                        "variance": self._format_money(self._to_decimal(row["variance"])),
                        "unallocated_budget": self._format_money(
                            self._to_decimal(row["unallocated_budget"]),
                        ),
                        "hiring_freeze": bool(row["hiring_freeze"]),
                    }
                )

        return Response({
            "fiscal_year": int(fiscal_year) if fiscal_year else None,
            "currency": currency_code or None,
            "departments": [
                {
                    "department_id": row["department__id"],
                    "department_name": row["department__name"],
                    "approved_headcount": row["total_approved"] or 0,
                    "filled_headcount": row["total_filled"] or 0,
                    "vacant": (row["total_approved"] or 0) - (row["total_filled"] or 0),
                    "budget_amount": str(row["total_budget"] or 0),
                }
                for row in summary
            ],
            "totals": {
                "approved_headcount": totals["total_approved"] or 0,
                "filled_headcount": totals["total_filled"] or 0,
                "vacant": (totals["total_approved"] or 0) - (totals["total_filled"] or 0),
                "budget_amount": str(totals["total_budget"] or 0),
                "open_vacancies": open_vacancies,
            },
            "budget_vs_actual": {
                "budgeted": self._format_money(budgeted_total),
                "committed": self._format_money(committed_total),
                "pipeline": self._format_money(pipeline_total),
                "variance": self._format_money(variance_total),
                "merit_pool": self._format_money(merit_pool_total),
                "variance_status": "over_budget" if variance_total < 0 else "buffer",
            },
            "utilization_heatmap": {
                "departments": department_heatmap,
                "projects": project_heatmap,
            },
            "business_units": business_unit_guardrails,
        })


# ---------------------------------------------------------------------------
# Employee Directory ViewSets
# ---------------------------------------------------------------------------


class EmployeeDirectoryViewSet(viewsets.ModelViewSet):
    """Employee records — composite of EmployeeRecord + UserProfile."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.employee_directory"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = [
        "user__first_name", "user__last_name", "user__email",
        "user__profile__employee_id", "user__profile__job_title",
    ]
    filterset_fields = ["employment_status"]
    ordering_fields = ["hire_date", "created_at", "user__last_name"]
    ordering = ["user__last_name"]

    def get_queryset(self):
        qs = EmployeeRecord.objects.select_related(
            "user", "user__profile", "user__profile__department",
            "user__profile__reporting_manager",
        )
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()

        # Filter by department (via UserProfile FK)
        dept = self.request.query_params.get("department")
        if dept:
            qs = qs.filter(user__profile__department_id=dept)

        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return EmployeeDirectoryListSerializer
        if self.action in ("create", "update", "partial_update"):
            return EmployeeRecordWriteSerializer
        return EmployeeDirectoryDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))

    @action(detail=False, methods=["get"], url_path="choices")
    def choices(self, request):
        """Lightweight list for dropdown selectors: id, full_name, employee_id."""
        qs = self.get_queryset().order_by("user__first_name", "user__last_name")
        search = request.query_params.get("search", "").strip()
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
                | Q(user__profile__employee_id__icontains=search)
            )
        results = []
        for rec in qs[:100]:
            profile = getattr(rec.user, "profile", None)
            results.append({
                "id": rec.id,
                "full_name": rec.user.get_full_name() or rec.user.email,
                "employee_id": profile.employee_id if profile else "",
            })
        return Response(results)


class EmergencyContactViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.employee_directory"
    rbac_action_map = _HR_ACTION_MAP
    filterset_fields = ["user"]
    ordering = ["sort_order", "name"]

    def get_queryset(self):
        qs = EmergencyContact.objects.select_related("user")
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return EmergencyContactWriteSerializer
        return EmergencyContactListSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


class IdentificationDocumentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.employee_directory"
    rbac_action_map = _HR_ACTION_MAP
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filterset_fields = ["user", "document_type"]
    ordering = ["-issue_date"]

    def get_queryset(self):
        qs = IdentificationDocument.objects.select_related("user")
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return IdentificationDocumentWriteSerializer
        return IdentificationDocumentListSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


class CompensationRecordViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.compensation"
    rbac_action_map = _HR_ACTION_MAP
    filterset_fields = ["user", "status", "currency"]
    ordering_fields = ["effective_date", "base_salary", "total_package", "created_at"]
    ordering = ["-effective_date"]

    def get_queryset(self):
        qs = CompensationRecord.objects.select_related("user", "approved_by")
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return CompensationRecordListSerializer
        if self.action in ("create", "update", "partial_update"):
            return CompensationRecordWriteSerializer
        return CompensationRecordDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        record = self.get_object()
        record.status = CompensationRecord.Status.ACTIVE
        record.approved_by = request.user
        record.approved_at = timezone.now()
        record.save(update_fields=[
            "status", "approved_by", "approved_at", "updated_at",
        ])
        return Response(CompensationRecordDetailSerializer(record).data)


class HRDocumentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.employee_directory"
    rbac_action_map = _HR_ACTION_MAP
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filterset_fields = ["user", "category"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = HRDocument.objects.select_related("user", "uploaded_by")
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()

        # Filter for contract documents only
        is_contract = self.request.query_params.get("is_contract")
        if is_contract == "true":
            qs = qs.filter(category__in=CONTRACT_CATEGORIES)
        elif is_contract == "false":
            qs = qs.exclude(category__in=CONTRACT_CATEGORIES)

        return qs

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return HRDocumentWriteSerializer
        return HRDocumentListSerializer

    def perform_create(self, serializer):
        file_obj = serializer.validated_data.get("file")
        file_size = file_obj.size if file_obj else 0
        serializer.save(
            organization=_user_org(self.request),
            uploaded_by=self.request.user,
            file_size=file_size,
        )


# ---------------------------------------------------------------------------
# Employee Directory read-only API Views
# ---------------------------------------------------------------------------


class EmploymentHistoryView(APIView):
    """Position assignment history + contract timeline for a specific user."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.employee_directory"
    rbac_action = "view"

    def get(self, request):
        user_id = request.query_params.get("user")
        if not user_id:
            return Response(
                {"detail": "Query parameter 'user' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        org = _user_org(request) if not _is_superuser(request) else None

        assignments_qs = PositionAssignment.objects.select_related(
            "position", "position__department",
        ).filter(user_id=user_id).order_by("-start_date")
        if org:
            assignments_qs = assignments_qs.filter(organization=org)

        entries = []
        for a in assignments_qs:
            entries.append({
                "id": a.id,
                "position_title": a.position.title,
                "position_code": a.position.code,
                "department_name": a.position.department.name,
                "start_date": a.start_date,
                "end_date": a.end_date,
                "is_primary": a.is_primary,
                "is_active": a.is_active,
            })

        # Also include the employee record for contract timeline
        employee_record = None
        try:
            er = EmployeeRecord.objects.get(user_id=user_id)
            if org and er.organization_id != org.id:
                er = None
            if er:
                employee_record = {
                    "hire_date": er.hire_date,
                    "contract_start_date": er.contract_start_date,
                    "contract_end_date": er.contract_end_date,
                    "contract_type": er.contract_type,
                    "employment_status": er.employment_status,
                    "termination_date": er.termination_date,
                }
        except EmployeeRecord.DoesNotExist:
            pass

        return Response({
            "position_history": EmploymentHistoryEntrySerializer(entries, many=True).data,
            "employee_record": employee_record,
        })


class ContactDirectoryView(APIView):
    """Lightweight contact directory: name, department, phone, email, location."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.employee_directory"
    rbac_action = "view"

    def get(self, request):
        from apps.accounts.models import UserProfile

        org = _user_org(request) if not _is_superuser(request) else None

        profiles_qs = (
            UserProfile.objects
            .filter(identity_type__in=["user", "employee"])
            .select_related("user", "department")
        )
        if org:
            profiles_qs = profiles_qs.filter(organization=org)

        search = request.query_params.get("search", "").strip()
        if search:
            profiles_qs = profiles_qs.filter(
                Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
                | Q(user__email__icontains=search)
                | Q(phone__icontains=search)
            )

        result = []
        for p in profiles_qs.order_by("user__last_name", "user__first_name"):
            result.append({
                "user_id": p.user_id,
                "full_name": p.user.get_full_name(),
                "department_name": p.department.name if p.department_id else None,
                "phone": p.phone,
                "email": p.user.email,
                "office_location": p.office_location,
            })

        return Response(result)


# ---------------------------------------------------------------------------
# Recruitment & Hiring ViewSets
# ---------------------------------------------------------------------------


class JobRequisitionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.requisitions"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["title", "justification"]
    filterset_fields = ["department", "position", "status", "priority", "requested_by"]
    ordering_fields = ["title", "priority", "status", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = JobRequisition.objects.select_related(
            "position", "vacancy", "department",
            "requested_by", "approved_by",
        )
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return JobRequisitionListSerializer
        if self.action in ("create", "update", "partial_update"):
            return JobRequisitionWriteSerializer
        return JobRequisitionDetailSerializer

    def perform_create(self, serializer):
        serializer.save(
            organization=_user_org(self.request),
            requested_by=self.request.user,
        )

    @action(detail=True, methods=["post"])
    def submit_for_approval(self, request, pk=None):
        requisition = self.get_object()
        if requisition.status != JobRequisition.Status.DRAFT:
            return Response(
                {"detail": "Only draft requisitions can be submitted."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from apps.workflows.engine import submit_for_approval as wf_submit
        requisition.status = JobRequisition.Status.PENDING_APPROVAL
        requisition.save(update_fields=["status", "updated_at"])
        wf_submit(requisition, request.user)
        return Response(JobRequisitionDetailSerializer(requisition).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        requisition = self.get_object()
        requisition.status = JobRequisition.Status.CANCELLED
        requisition.save(update_fields=["status", "updated_at"])
        return Response(JobRequisitionDetailSerializer(requisition).data)


class JobListingViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.job_listings"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["title", "description", "requirements"]
    filterset_fields = ["requisition", "status", "employment_type", "is_internal", "is_external"]
    ordering_fields = ["title", "posted_date", "closing_date", "status", "created_at"]
    ordering = ["-posted_date", "-created_at"]

    def get_queryset(self):
        qs = JobListing.objects.select_related(
            "requisition", "posted_by",
        ).annotate(
            candidate_count_val=Count("candidates"),
        )
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return JobListingListSerializer
        if self.action in ("create", "update", "partial_update"):
            return JobListingWriteSerializer
        return JobListingDetailSerializer

    def perform_create(self, serializer):
        serializer.save(
            organization=_user_org(self.request),
            posted_by=self.request.user,
            posted_date=timezone.localdate(),
            status=JobListing.Status.ACTIVE,
        )

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        listing = self.get_object()
        listing.status = JobListing.Status.CLOSED
        listing.save(update_fields=["status", "updated_at"])
        return Response(JobListingDetailSerializer(listing).data)

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        listing = self.get_object()
        listing.status = JobListing.Status.ARCHIVED
        listing.save(update_fields=["status", "updated_at"])
        return Response(JobListingDetailSerializer(listing).data)


class CandidateViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.candidates"
    rbac_action_map = _HR_ACTION_MAP
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    search_fields = ["first_name", "last_name", "email", "current_title", "current_employer"]
    filterset_fields = ["job_listing", "job_requisition", "stage", "source"]
    ordering_fields = ["applied_date", "stage", "created_at"]
    ordering = ["-applied_date"]

    def get_queryset(self):
        qs = Candidate.objects.select_related(
            "job_listing", "job_requisition", "referred_by",
        )
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return CandidateListSerializer
        if self.action in ("create", "update", "partial_update"):
            return CandidateWriteSerializer
        return CandidateDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))

    @action(detail=True, methods=["post"])
    def advance_stage(self, request, pk=None):
        candidate = self.get_object()
        new_stage = request.data.get("stage")
        if not new_stage:
            return Response(
                {"detail": "Field 'stage' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        valid = [c[0] for c in Candidate.Stage.choices]
        if new_stage not in valid:
            return Response(
                {"detail": f"Invalid stage. Must be one of: {', '.join(valid)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if new_stage == Candidate.Stage.HIRED:
            enforce_candidate_hire_budget(candidate, request.user)
        candidate.stage = new_stage
        candidate.save(update_fields=["stage", "updated_at"])
        return Response(CandidateDetailSerializer(candidate).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        candidate = self.get_object()
        candidate.stage = Candidate.Stage.REJECTED
        candidate.rejection_reason = request.data.get("rejection_reason", "")
        candidate.save(update_fields=["stage", "rejection_reason", "updated_at"])
        return Response(CandidateDetailSerializer(candidate).data)

    @action(detail=True, methods=["post"])
    def withdraw(self, request, pk=None):
        candidate = self.get_object()
        candidate.stage = Candidate.Stage.WITHDRAWN
        candidate.save(update_fields=["stage", "updated_at"])
        return Response(CandidateDetailSerializer(candidate).data)


class InterviewViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.interviews"
    rbac_action_map = _HR_ACTION_MAP
    filterset_fields = ["candidate", "interviewer", "interview_type", "status"]
    ordering_fields = ["scheduled_date", "scheduled_time", "created_at"]
    ordering = ["-scheduled_date", "-scheduled_time"]

    def get_queryset(self):
        qs = Interview.objects.select_related(
            "candidate", "interviewer",
        )
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return InterviewListSerializer
        if self.action in ("create", "update", "partial_update"):
            return InterviewWriteSerializer
        return InterviewDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        interview = self.get_object()
        interview.status = Interview.Status.COMPLETED
        interview.save(update_fields=["status", "updated_at"])
        return Response(InterviewDetailSerializer(interview).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        interview = self.get_object()
        interview.status = Interview.Status.CANCELLED
        interview.save(update_fields=["status", "updated_at"])
        return Response(InterviewDetailSerializer(interview).data)


class CandidateEvaluationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.candidates"
    rbac_action_map = _HR_ACTION_MAP
    filterset_fields = ["candidate", "interview", "evaluator", "recommendation"]
    ordering_fields = ["overall_rating", "evaluated_at", "created_at"]
    ordering = ["-evaluated_at"]

    def get_queryset(self):
        qs = CandidateEvaluation.objects.select_related(
            "candidate", "interview", "evaluator",
        )
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return CandidateEvaluationListSerializer
        if self.action in ("create", "update", "partial_update"):
            return CandidateEvaluationWriteSerializer
        return CandidateEvaluationDetailSerializer

    def perform_create(self, serializer):
        serializer.save(
            organization=_user_org(self.request),
            evaluator=self.request.user,
        )


class JobOfferViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.offers"
    rbac_action_map = _HR_ACTION_MAP
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    search_fields = ["candidate__first_name", "candidate__last_name"]
    filterset_fields = ["candidate", "requisition", "position", "status"]
    ordering_fields = ["offered_salary", "start_date", "expiry_date", "status", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = JobOffer.objects.select_related(
            "candidate", "requisition", "position", "approved_by", "cfo_override_by",
        )
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return JobOfferListSerializer
        if self.action in ("create", "update", "partial_update"):
            return JobOfferWriteSerializer
        return JobOfferDetailSerializer

    def perform_create(self, serializer):
        offer = serializer.save(organization=_user_org(self.request))

        # Notify HR managers of new job offer
        from apps.notifications.models import Notification
        from apps.notifications.services import (
            dispatch_workflow_notification,
            resolve_raci_recipients,
        )

        org = _user_org(self.request)
        raci = resolve_raci_recipients(
            organization=org,
            process_key="hr.recruitment",
        )
        recipients = raci.all
        if not recipients:
            from apps.accounts.models import UserProfile

            recipients = [
                p.user
                for p in UserProfile.objects.filter(
                    organization=org,
                    role="admin",
                    user__is_active=True,
                ).select_related("user")
            ]
        if recipients:
            candidate_name = str(offer.candidate) if offer.candidate_id else ""
            position_name = str(offer.position) if offer.position_id else ""
            dispatch_workflow_notification(
                organization=org,
                event_key="hr_job_offer_sent",
                recipients=recipients,
                context={
                    "candidate_name": candidate_name,
                    "position": position_name,
                    "action_url": f"/hr/recruitment/offers/{offer.id}",
                },
                link_url=f"/hr/recruitment/offers/{offer.id}",
                fallback_channels=["in_app"],
                fallback_title=f"Job offer created: {candidate_name}",
                fallback_message=(
                    f"A job offer has been created for {candidate_name}"
                    f"{f' ({position_name})' if position_name else ''}."
                ),
                fallback_category=Notification.Category.HR_LIFECYCLE,
                fallback_severity=Notification.Severity.INFO,
            )

    @action(detail=True, methods=["post"])
    def submit_for_approval(self, request, pk=None):
        offer = self.get_object()
        if offer.status != JobOffer.Status.DRAFT:
            return Response(
                {"detail": "Only draft offers can be submitted."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from apps.workflows.engine import submit_for_approval as wf_submit
        offer.status = JobOffer.Status.PENDING_APPROVAL
        offer.save(update_fields=["status", "updated_at"])
        wf_submit(offer, request.user)
        return Response(JobOfferDetailSerializer(offer).data)

    @action(detail=True, methods=["post"], url_path="cfo-override")
    def cfo_override(self, request, pk=None):
        offer = self.get_object()
        if not user_has_cfo_override_authority(request.user):
            raise PermissionDenied("Only CFO-authorized users can grant salary override.")

        now = timezone.now()
        offer.cfo_override_approved = True
        offer.cfo_override_by = request.user
        offer.cfo_override_at = now
        offer.cfo_override_reason = (request.data.get("reason") or "").strip()
        offer.save(
            update_fields=[
                "cfo_override_approved",
                "cfo_override_by",
                "cfo_override_at",
                "cfo_override_reason",
                "updated_at",
            ],
        )
        return Response(JobOfferDetailSerializer(offer).data)

    @action(detail=True, methods=["post"])
    def extend(self, request, pk=None):
        offer = self.get_object()
        if offer.status not in (JobOffer.Status.APPROVED, JobOffer.Status.EXTENDED):
            return Response(
                {"detail": "Only approved offers can be extended."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        offer.status = JobOffer.Status.EXTENDED
        offer.extended_at = timezone.now()
        offer.save(update_fields=["status", "extended_at", "updated_at"])
        return Response(JobOfferDetailSerializer(offer).data)

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        offer = self.get_object()
        offer.status = JobOffer.Status.ACCEPTED
        offer.responded_at = timezone.now()
        offer.response_notes = request.data.get("response_notes", "")
        offer.save(update_fields=[
            "status", "responded_at", "response_notes", "updated_at",
        ])
        return Response(JobOfferDetailSerializer(offer).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        offer = self.get_object()
        offer.status = JobOffer.Status.REJECTED
        offer.responded_at = timezone.now()
        offer.response_notes = request.data.get("response_notes", "")
        offer.save(update_fields=[
            "status", "responded_at", "response_notes", "updated_at",
        ])
        return Response(JobOfferDetailSerializer(offer).data)

    @action(detail=True, methods=["post"])
    def withdraw(self, request, pk=None):
        offer = self.get_object()
        offer.status = JobOffer.Status.WITHDRAWN
        offer.save(update_fields=["status", "updated_at"])
        return Response(JobOfferDetailSerializer(offer).data)


class HiringWorkflowDashboardView(APIView):
    """Dashboard view showing workflow status for requisitions and offers."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.requisitions"
    rbac_action = "view"

    def get(self, request):
        from django.contrib.contenttypes.models import ContentType

        from apps.workflows.models import WorkflowInstance

        org = _user_org(request) if not _is_superuser(request) else None

        req_ct = ContentType.objects.get_for_model(JobRequisition)
        offer_ct = ContentType.objects.get_for_model(JobOffer)

        instances_qs = (
            WorkflowInstance.objects
            .filter(content_type__in=[req_ct, offer_ct])
            .select_related("template", "submitted_by", "content_type")
            .prefetch_related("steps__decided_by")
            .order_by("-created_at")
        )
        if org:
            instances_qs = instances_qs.filter(template__organization=org)

        state_filter = request.query_params.get("state")
        if state_filter:
            instances_qs = instances_qs.filter(state=state_filter)

        results = []
        for wf in instances_qs:
            obj = wf.content_object
            if obj is None:
                continue
            obj_label = str(obj)
            obj_type = "requisition" if wf.content_type_id == req_ct.id else "offer"

            steps_data = []
            for step in wf.steps.order_by("sequence"):
                steps_data.append({
                    "id": step.id,
                    "sequence": step.sequence,
                    "name": step.name,
                    "decision": step.decision,
                    "decided_by_name": (
                        step.decided_by.get_full_name()
                        if step.decided_by_id else None
                    ),
                    "decided_at": step.decided_at,
                    "comments": step.comments,
                })

            results.append({
                "id": wf.id,
                "object_type": obj_type,
                "object_id": wf.object_id,
                "object_label": obj_label,
                "template_name": wf.template.name,
                "state": wf.state,
                "submitted_by_name": (
                    wf.submitted_by.get_full_name()
                    if wf.submitted_by_id else None
                ),
                "submitted_at": wf.submitted_at,
                "completed_at": wf.completed_at,
                "steps": steps_data,
            })

        # Group by state
        grouped = {}
        for item in results:
            grouped.setdefault(item["state"], []).append(item)

        return Response({
            "items": results,
            "by_state": grouped,
            "counts": {k: len(v) for k, v in grouped.items()},
        })


# ---------------------------------------------------------------------------
# Onboarding ViewSets
# ---------------------------------------------------------------------------


class OnboardingTemplateViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.onboarding"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["name", "description"]
    filterset_fields = ["department", "position", "is_active"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def get_queryset(self):
        qs = OnboardingTemplate.objects.select_related(
            "department", "position", "created_by",
        )
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return OnboardingTemplateWriteSerializer
        return OnboardingTemplateListSerializer

    def perform_create(self, serializer):
        serializer.save(
            organization=_user_org(self.request),
            created_by=self.request.user,
        )


class OnboardingTaskViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.onboarding"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["title", "description"]
    filterset_fields = ["employee", "template", "category", "status", "is_required"]
    ordering_fields = ["sort_order", "due_date", "created_at"]
    ordering = ["sort_order", "title"]

    def get_queryset(self):
        qs = OnboardingTask.objects.select_related(
            "employee__user", "template", "assigned_to",
        )
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return OnboardingTaskWriteSerializer
        return OnboardingTaskListSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


class DocumentCollectionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.onboarding"
    rbac_action_map = _HR_ACTION_MAP
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    search_fields = ["document_name", "description"]
    filterset_fields = ["employee", "status"]
    ordering_fields = ["due_date", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = DocumentCollectionItem.objects.select_related(
            "employee__user", "verified_by",
        )
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return DocumentCollectionWriteSerializer
        return DocumentCollectionListSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


class EquipmentAllocationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.onboarding"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["item_name", "serial_number", "asset_tag"]
    filterset_fields = ["employee", "category", "status"]
    ordering_fields = ["allocated_date", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = EquipmentAllocation.objects.select_related(
            "employee__user", "allocated_by",
        )
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return EquipmentAllocationWriteSerializer
        return EquipmentAllocationListSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


class OrientationChecklistViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.onboarding"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["title", "description"]
    filterset_fields = ["employee", "category", "is_completed"]
    ordering_fields = ["sort_order", "created_at"]
    ordering = ["sort_order", "title"]

    def get_queryset(self):
        qs = OrientationChecklistItem.objects.select_related(
            "employee__user", "completed_by",
        )
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return OrientationChecklistWriteSerializer
        return OrientationChecklistListSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


class ProbationRecordViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.onboarding"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["employee__user__first_name", "employee__user__last_name"]
    filterset_fields = ["employee", "status", "recommendation", "reviewer"]
    ordering_fields = ["start_date", "end_date", "created_at"]
    ordering = ["-start_date"]

    def get_queryset(self):
        qs = ProbationRecord.objects.select_related(
            "employee__user", "reviewer",
        )
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return ProbationRecordListSerializer
        if self.action in ("create", "update", "partial_update"):
            return ProbationRecordWriteSerializer
        return ProbationRecordDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


# ---------------------------------------------------------------------------
# Performance Management ViewSets
# ---------------------------------------------------------------------------


class PerformanceGoalViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.performance"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["title", "description"]
    filterset_fields = ["employee", "goal_type", "status", "priority"]
    ordering_fields = ["title", "due_date", "progress", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = PerformanceGoal.objects.select_related("employee__user")
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return PerformanceGoalListSerializer
        if self.action in ("create", "update", "partial_update"):
            return PerformanceGoalWriteSerializer
        return PerformanceGoalDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


class PerformanceReviewViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.performance"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["employee__user__first_name", "employee__user__last_name"]
    filterset_fields = ["employee", "reviewer", "review_type", "status"]
    ordering_fields = ["review_period_end", "overall_rating", "created_at"]
    ordering = ["-review_period_end"]

    def get_queryset(self):
        qs = PerformanceReview.objects.select_related(
            "employee__user", "reviewer",
        )
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return PerformanceReviewListSerializer
        if self.action in ("create", "update", "partial_update"):
            return PerformanceReviewWriteSerializer
        return PerformanceReviewDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


class ContinuousFeedbackViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.performance"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["subject", "content"]
    filterset_fields = ["employee", "given_by", "feedback_type", "visibility"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = ContinuousFeedback.objects.select_related(
            "employee__user", "given_by",
        )
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return ContinuousFeedbackListSerializer
        if self.action in ("create", "update", "partial_update"):
            return ContinuousFeedbackWriteSerializer
        return ContinuousFeedbackDetailSerializer

    def perform_create(self, serializer):
        serializer.save(
            organization=_user_org(self.request),
            given_by=self.request.user,
        )


class ManagerEvaluationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.performance"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["employee__user__first_name", "employee__user__last_name"]
    filterset_fields = ["employee", "evaluator", "review"]
    ordering_fields = ["evaluation_date", "overall_rating", "created_at"]
    ordering = ["-evaluation_date"]

    def get_queryset(self):
        qs = ManagerEvaluation.objects.select_related(
            "employee__user", "evaluator", "review",
        )
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return ManagerEvaluationListSerializer
        if self.action in ("create", "update", "partial_update"):
            return ManagerEvaluationWriteSerializer
        return ManagerEvaluationDetailSerializer

    def perform_create(self, serializer):
        serializer.save(
            organization=_user_org(self.request),
            evaluator=self.request.user,
        )


class PeerReviewViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.performance"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["employee__user__first_name", "employee__user__last_name"]
    filterset_fields = ["employee", "reviewer", "review", "status"]
    ordering_fields = ["submitted_at", "overall_rating", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = PeerReview.objects.select_related(
            "employee__user", "reviewer", "review",
        )
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return PeerReviewListSerializer
        if self.action in ("create", "update", "partial_update"):
            return PeerReviewWriteSerializer
        return PeerReviewDetailSerializer

    def perform_create(self, serializer):
        serializer.save(
            organization=_user_org(self.request),
            reviewer=self.request.user,
        )


class PIPViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.performance"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["title", "reason", "employee__user__first_name", "employee__user__last_name"]
    filterset_fields = ["employee", "status", "outcome", "created_by"]
    ordering_fields = ["start_date", "end_date", "status", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = PerformanceImprovementPlan.objects.select_related(
            "employee__user", "created_by",
        )
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return PIPListSerializer
        if self.action in ("create", "update", "partial_update"):
            return PIPWriteSerializer
        return PIPDetailSerializer

    def perform_create(self, serializer):
        serializer.save(
            organization=_user_org(self.request),
            created_by=self.request.user,
        )


# ---------------------------------------------------------------------------
# Skills & Capability Management
# ---------------------------------------------------------------------------


class SkillViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.skills"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["name", "employee__user__first_name", "employee__user__last_name"]
    filterset_fields = ["employee", "category", "proficiency", "is_primary", "verified"]
    ordering_fields = ["name", "category", "proficiency", "years_experience", "created_at"]
    ordering = ["category", "name"]

    def get_queryset(self):
        qs = Skill.objects.select_related("employee__user", "verified_by")
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return SkillListSerializer
        if self.action in ("create", "update", "partial_update"):
            return SkillWriteSerializer
        return SkillDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


class CertificationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.skills"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["name", "issuing_body", "credential_id", "employee__user__first_name", "employee__user__last_name"]
    filterset_fields = ["employee", "status"]
    ordering_fields = ["name", "issue_date", "expiry_date", "status", "created_at"]
    ordering = ["-issue_date"]

    def get_queryset(self):
        qs = Certification.objects.select_related("employee__user")
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return CertificationListSerializer
        if self.action in ("create", "update", "partial_update"):
            return CertificationWriteSerializer
        return CertificationDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


class ProfessionalLicenseViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.skills"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["license_type", "license_number", "issuing_authority", "employee__user__first_name", "employee__user__last_name"]
    filterset_fields = ["employee", "status", "is_mandatory"]
    ordering_fields = ["license_type", "issue_date", "expiry_date", "status", "created_at"]
    ordering = ["-issue_date"]

    def get_queryset(self):
        qs = ProfessionalLicense.objects.select_related("employee__user")
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return ProfessionalLicenseListSerializer
        if self.action in ("create", "update", "partial_update"):
            return ProfessionalLicenseWriteSerializer
        return ProfessionalLicenseDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


class CompetencyAssessmentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.skills"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["competency_area", "employee__user__first_name", "employee__user__last_name"]
    filterset_fields = ["employee", "assessor", "status"]
    ordering_fields = ["competency_area", "assessment_date", "score", "status", "created_at"]
    ordering = ["-assessment_date"]

    def get_queryset(self):
        qs = CompetencyAssessment.objects.select_related("employee__user", "assessor")
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return CompetencyAssessmentListSerializer
        if self.action in ("create", "update", "partial_update"):
            return CompetencyAssessmentWriteSerializer
        return CompetencyAssessmentDetailSerializer

    def perform_create(self, serializer):
        serializer.save(
            organization=_user_org(self.request),
            assessor=self.request.user,
        )


class TrainingRecordViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.skills"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["title", "provider", "employee__user__first_name", "employee__user__last_name"]
    filterset_fields = ["employee", "status", "delivery_method", "is_mandatory"]
    ordering_fields = ["title", "start_date", "end_date", "status", "created_at"]
    ordering = ["-start_date"]

    def get_queryset(self):
        qs = TrainingRecord.objects.select_related("employee__user")
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return TrainingRecordListSerializer
        if self.action in ("create", "update", "partial_update"):
            return TrainingRecordWriteSerializer
        return TrainingRecordDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


# ---------------------------------------------------------------------------
# Learning & Development
# ---------------------------------------------------------------------------


class TrainingCourseViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.learning"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["title", "code", "provider", "description"]
    filterset_fields = ["format", "level", "status", "is_mandatory"]
    ordering_fields = ["title", "code", "level", "status", "created_at"]
    ordering = ["title"]

    def get_queryset(self):
        qs = TrainingCourse.objects.select_related("created_by")
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return TrainingCourseListSerializer
        if self.action in ("create", "update", "partial_update"):
            return TrainingCourseWriteSerializer
        return TrainingCourseDetailSerializer

    def perform_create(self, serializer):
        serializer.save(
            organization=_user_org(self.request),
            created_by=self.request.user,
        )


class TrainingPlanViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.learning"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["title", "description"]
    filterset_fields = ["department", "employee", "status"]
    ordering_fields = ["title", "start_date", "end_date", "status", "created_at"]
    ordering = ["-start_date"]

    def get_queryset(self):
        qs = TrainingPlan.objects.select_related(
            "department", "employee__user", "created_by",
        )
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return TrainingPlanListSerializer
        if self.action in ("create", "update", "partial_update"):
            return TrainingPlanWriteSerializer
        return TrainingPlanDetailSerializer

    def perform_create(self, serializer):
        serializer.save(
            organization=_user_org(self.request),
            created_by=self.request.user,
        )


class CourseEnrollmentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.learning"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["course__title", "employee__user__first_name", "employee__user__last_name"]
    filterset_fields = ["employee", "course", "training_plan", "status"]
    ordering_fields = ["enrolled_date", "start_date", "completion_date", "status", "progress"]
    ordering = ["-enrolled_date"]

    def get_queryset(self):
        qs = CourseEnrollment.objects.select_related(
            "employee__user", "course", "training_plan",
        )
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return CourseEnrollmentListSerializer
        if self.action in ("create", "update", "partial_update"):
            return CourseEnrollmentWriteSerializer
        return CourseEnrollmentDetailSerializer

    def perform_create(self, serializer):
        serializer.save(
            organization=_user_org(self.request),
            enrolled_by=self.request.user,
        )


class LearningResourceViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.learning"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["title", "description", "category", "tags"]
    filterset_fields = ["resource_type", "status", "category"]
    ordering_fields = ["title", "resource_type", "view_count", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = LearningResource.objects.select_related("uploaded_by")
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return LearningResourceListSerializer
        if self.action in ("create", "update", "partial_update"):
            return LearningResourceWriteSerializer
        return LearningResourceDetailSerializer

    def perform_create(self, serializer):
        serializer.save(
            organization=_user_org(self.request),
            uploaded_by=self.request.user,
        )


class TrainingCompletionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.learning"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["course__title", "certificate_number", "employee__user__first_name", "employee__user__last_name"]
    filterset_fields = ["employee", "course", "result"]
    ordering_fields = ["completion_date", "result", "score", "created_at"]
    ordering = ["-completion_date"]

    def get_queryset(self):
        qs = TrainingCompletion.objects.select_related(
            "employee__user", "course", "verified_by",
        )
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return TrainingCompletionListSerializer
        if self.action in ("create", "update", "partial_update"):
            return TrainingCompletionWriteSerializer
        return TrainingCompletionDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


class CertificationExpiryAlertViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.learning"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["reference_name", "employee__user__first_name", "employee__user__last_name"]
    filterset_fields = ["employee", "alert_type", "status"]
    ordering_fields = ["expiry_date", "alert_date", "status", "created_at"]
    ordering = ["expiry_date"]

    def get_queryset(self):
        qs = CertificationExpiryAlert.objects.select_related("employee__user")
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return CertificationExpiryAlertListSerializer
        if self.action in ("create", "update", "partial_update"):
            return CertificationExpiryAlertWriteSerializer
        return CertificationExpiryAlertDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


# ═══════════════════════════════════════════════════════════════════════════
# 8. Attendance & Leave
# ═══════════════════════════════════════════════════════════════════════════


class AttendanceLogViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.attendance"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["employee__user__first_name", "employee__user__last_name", "location"]
    filterset_fields = ["employee", "status", "date"]
    ordering_fields = ["date", "status", "created_at"]
    ordering = ["-date"]

    def get_queryset(self):
        qs = AttendanceLog.objects.select_related("employee__user")
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return AttendanceLogListSerializer
        if self.action in ("create", "update", "partial_update"):
            return AttendanceLogWriteSerializer
        return AttendanceLogDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


class LeaveTypeViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.attendance"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["name", "code"]
    filterset_fields = ["is_active", "is_paid"]
    ordering_fields = ["sort_order", "name", "created_at"]
    ordering = ["sort_order", "name"]

    def get_queryset(self):
        qs = LeaveType.objects.all()
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return LeaveTypeListSerializer
        if self.action in ("create", "update", "partial_update"):
            return LeaveTypeWriteSerializer
        return LeaveTypeDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


class LeaveRequestViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.attendance"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["employee__user__first_name", "employee__user__last_name", "reason"]
    filterset_fields = ["employee", "leave_type", "status"]
    ordering_fields = ["start_date", "end_date", "status", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = LeaveRequest.objects.select_related("employee__user", "leave_type", "reviewed_by")
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return LeaveRequestListSerializer
        if self.action in ("create", "update", "partial_update"):
            return LeaveRequestWriteSerializer
        return LeaveRequestDetailSerializer

    def perform_create(self, serializer):
        requested_status = serializer.validated_data.get("status")
        status_override = None
        if requested_status in (LeaveRequest.Status.APPROVED, LeaveRequest.Status.REJECTED):
            status_override = LeaveRequest.Status.PENDING
        serializer.save(
            organization=_user_org(self.request),
            **({"status": status_override} if status_override else {}),
        )

    def _team_lead_user_ids_for_leave_request(self, leave_request: LeaveRequest) -> set[int]:
        employee_user_id = getattr(leave_request.employee, "user_id", None)
        if not employee_user_id:
            return set()

        return set(
            PositionAssignment.objects.filter(
                organization=leave_request.organization,
                user_id=employee_user_id,
                is_active=True,
                position__team__lead__isnull=False,
            ).values_list("position__team__lead_id", flat=True).distinct()
        )

    def _can_user_review_leave_request(self, user, leave_request: LeaveRequest) -> bool:
        if user.is_superuser:
            return True

        team_lead_user_ids = self._team_lead_user_ids_for_leave_request(leave_request)
        if team_lead_user_ids:
            return user.id in team_lead_user_ids

        employee_profile = getattr(getattr(leave_request.employee, "user", None), "profile", None)
        if employee_profile and employee_profile.reporting_manager_id:
            return employee_profile.reporting_manager_id == user.id

        reviewer_profile = getattr(user, "profile", None)
        return bool(reviewer_profile and reviewer_profile.role == "admin")

    def _enforce_leave_review_permission(self, user, leave_request: LeaveRequest):
        if self._can_user_review_leave_request(user, leave_request):
            return
        raise PermissionDenied(
            "Only the assigned Team Lead can approve or reject this leave request."
        )

    def _apply_leave_review_decision(
        self,
        leave_request: LeaveRequest,
        *,
        reviewer,
        status_value: str,
        reviewer_notes: str = "",
    ):
        leave_request.status = status_value
        leave_request.reviewed_by = reviewer
        leave_request.reviewed_at = timezone.now()
        leave_request.reviewer_notes = reviewer_notes or ""
        leave_request.save(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
                "reviewer_notes",
                "updated_at",
            ]
        )
        return leave_request

    def perform_update(self, serializer):
        instance: LeaveRequest = serializer.instance
        next_status = serializer.validated_data.get("status", instance.status)
        if (
            next_status in (LeaveRequest.Status.APPROVED, LeaveRequest.Status.REJECTED)
            and next_status != instance.status
        ):
            self._enforce_leave_review_permission(self.request.user, instance)
            reviewer_notes = serializer.validated_data.get("reviewer_notes", instance.reviewer_notes)
            serializer.save(
                reviewed_by=self.request.user,
                reviewed_at=timezone.now(),
                reviewer_notes=reviewer_notes or "",
            )
            return

        serializer.save()

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        leave_request = self.get_object()
        self._enforce_leave_review_permission(request.user, leave_request)
        self._apply_leave_review_decision(
            leave_request,
            reviewer=request.user,
            status_value=LeaveRequest.Status.APPROVED,
            reviewer_notes=(request.data.get("reviewer_notes") or "").strip(),
        )
        serializer = LeaveRequestDetailSerializer(leave_request)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        leave_request = self.get_object()
        self._enforce_leave_review_permission(request.user, leave_request)
        self._apply_leave_review_decision(
            leave_request,
            reviewer=request.user,
            status_value=LeaveRequest.Status.REJECTED,
            reviewer_notes=(request.data.get("reviewer_notes") or "").strip(),
        )
        serializer = LeaveRequestDetailSerializer(leave_request)
        return Response(serializer.data)


class LeaveBalanceViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.attendance"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["employee__user__first_name", "employee__user__last_name"]
    filterset_fields = ["employee", "leave_type", "fiscal_year"]
    ordering_fields = ["fiscal_year", "entitled_days", "used_days", "created_at"]
    ordering = ["-fiscal_year"]

    def get_queryset(self):
        qs = LeaveBalance.objects.select_related("employee__user", "leave_type")
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return LeaveBalanceListSerializer
        if self.action in ("create", "update", "partial_update"):
            return LeaveBalanceWriteSerializer
        return LeaveBalanceDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


class OvertimeRequestViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.attendance"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["employee__user__first_name", "employee__user__last_name", "reason"]
    filterset_fields = ["employee", "status", "date"]
    ordering_fields = ["date", "total_hours", "status", "created_at"]
    ordering = ["-date"]

    def get_queryset(self):
        qs = OvertimeRequest.objects.select_related("employee__user", "approved_by")
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return OvertimeRequestListSerializer
        if self.action in ("create", "update", "partial_update"):
            return OvertimeRequestWriteSerializer
        return OvertimeRequestDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


class RemoteWorkLogViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.attendance"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["employee__user__first_name", "employee__user__last_name", "location"]
    filterset_fields = ["employee", "status", "date"]
    ordering_fields = ["date", "work_hours", "status", "created_at"]
    ordering = ["-date"]

    def get_queryset(self):
        qs = RemoteWorkLog.objects.select_related("employee__user", "approved_by")
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return RemoteWorkLogListSerializer
        if self.action in ("create", "update", "partial_update"):
            return RemoteWorkLogWriteSerializer
        return RemoteWorkLogDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


# ---------------------------------------------------------------------------
# Payroll & Compensation
# ---------------------------------------------------------------------------


class SalaryStructureViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.payroll"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["name", "code"]
    filterset_fields = ["is_active"]
    ordering_fields = ["grade_level", "name", "min_salary", "max_salary", "created_at"]
    ordering = ["grade_level", "name"]

    def get_queryset(self):
        qs = SalaryStructure.objects.all()
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return SalaryStructureListSerializer
        if self.action in ("create", "update", "partial_update"):
            return SalaryStructureWriteSerializer
        return SalaryStructureDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


class PayrollRunViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.payroll"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["name"]
    filterset_fields = ["status"]
    ordering_fields = ["period_start", "period_end", "run_date", "status", "total_net", "created_at"]
    ordering = ["-period_end"]

    def get_queryset(self):
        qs = PayrollRun.objects.select_related("processed_by")
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return PayrollRunListSerializer
        if self.action in ("create", "update", "partial_update"):
            return PayrollRunWriteSerializer
        return PayrollRunDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))

    @action(detail=True, methods=["post"], url_path="post-to-gl")
    def post_to_gl(self, request, pk=None):
        from django.core.exceptions import ValidationError as DjangoValidationError

        from apps.finance.payroll_gl import post_payroll_run_to_gl
        from apps.finance.serializers import PayrollGLPostingSerializer

        run = self.get_object()
        try:
            posting = post_payroll_run_to_gl(run, request.user)
        except DjangoValidationError as exc:
            detail = " ".join(exc.messages) if hasattr(exc, "messages") else str(exc)
            return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            PayrollGLPostingSerializer(posting).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="reconcile-gl")
    def reconcile_gl(self, request, pk=None):
        from django.core.exceptions import ValidationError as DjangoValidationError

        from apps.finance.payroll_gl import reconcile_payroll_run
        from apps.finance.serializers import PayrollGLPostingSerializer

        run = self.get_object()
        try:
            posting = reconcile_payroll_run(run, request.user)
        except DjangoValidationError as exc:
            detail = " ".join(exc.messages) if hasattr(exc, "messages") else str(exc)
            return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            PayrollGLPostingSerializer(posting).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="bulk-sync-gl")
    def bulk_sync_gl(self, request):
        from apps.finance.payroll_gl import bulk_sync_payroll_runs

        org = _user_org(request)
        if org is None:
            return Response(
                {"detail": "No organization scope."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        result = bulk_sync_payroll_runs(org, request.user)
        return Response(result, status=status.HTTP_200_OK)


class AllowanceViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.payroll"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["employee__user__first_name", "employee__user__last_name", "name"]
    filterset_fields = ["employee", "allowance_type", "frequency", "is_active"]
    ordering_fields = ["name", "amount", "allowance_type", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = Allowance.objects.select_related("employee__user")
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return AllowanceListSerializer
        if self.action in ("create", "update", "partial_update"):
            return AllowanceWriteSerializer
        return AllowanceDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


class DeductionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.payroll"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["employee__user__first_name", "employee__user__last_name", "name"]
    filterset_fields = ["employee", "deduction_type", "frequency", "is_active"]
    ordering_fields = ["name", "amount", "deduction_type", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = Deduction.objects.select_related("employee__user")
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return DeductionListSerializer
        if self.action in ("create", "update", "partial_update"):
            return DeductionWriteSerializer
        return DeductionDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


class BonusViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.payroll"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["employee__user__first_name", "employee__user__last_name", "reason"]
    filterset_fields = ["employee", "bonus_type", "status"]
    ordering_fields = ["date", "amount", "bonus_type", "status", "created_at"]
    ordering = ["-date"]

    def get_queryset(self):
        qs = Bonus.objects.select_related("employee__user", "approved_by")
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return BonusListSerializer
        if self.action in ("create", "update", "partial_update"):
            return BonusWriteSerializer
        return BonusDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


class PayslipViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.payroll"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["employee__user__first_name", "employee__user__last_name"]
    filterset_fields = ["employee", "payroll_run", "status"]
    ordering_fields = ["period_start", "period_end", "net_salary", "status", "created_at"]
    ordering = ["-period_end"]

    def get_queryset(self):
        qs = Payslip.objects.select_related("employee__user", "payroll_run")
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return PayslipListSerializer
        if self.action in ("create", "update", "partial_update"):
            return PayslipWriteSerializer
        return PayslipDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


class TaxRecordViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.payroll"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["employee__user__first_name", "employee__user__last_name", "fiscal_year"]
    filterset_fields = ["employee", "tax_type", "filing_status", "fiscal_year"]
    ordering_fields = ["fiscal_year", "tax_type", "tax_amount", "filing_status", "created_at"]
    ordering = ["-fiscal_year", "tax_type"]

    def get_queryset(self):
        qs = TaxRecord.objects.select_related("employee__user")
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return TaxRecordListSerializer
        if self.action in ("create", "update", "partial_update"):
            return TaxRecordWriteSerializer
        return TaxRecordDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


# =========================================================================
# 10. Employee Lifecycle Management
# =========================================================================


class PromotionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.lifecycle"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["employee__user__first_name", "employee__user__last_name", "to_position"]
    filterset_fields = ["employee", "status"]
    ordering_fields = ["effective_date", "status", "created_at"]
    ordering = ["-effective_date"]

    def get_queryset(self):
        qs = Promotion.objects.select_related("employee__user", "approved_by")
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return PromotionListSerializer
        if self.action in ("create", "update", "partial_update"):
            return PromotionWriteSerializer
        return PromotionDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


class TransferViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.lifecycle"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["employee__user__first_name", "employee__user__last_name", "to_department"]
    filterset_fields = ["employee", "transfer_type", "status"]
    ordering_fields = ["effective_date", "transfer_type", "status", "created_at"]
    ordering = ["-effective_date"]

    def get_queryset(self):
        qs = Transfer.objects.select_related("employee__user", "approved_by")
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return TransferListSerializer
        if self.action in ("create", "update", "partial_update"):
            return TransferWriteSerializer
        return TransferDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


class RoleChangeViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.lifecycle"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["employee__user__first_name", "employee__user__last_name", "to_role"]
    filterset_fields = ["employee", "change_type", "status"]
    ordering_fields = ["effective_date", "change_type", "status", "created_at"]
    ordering = ["-effective_date"]

    def get_queryset(self):
        qs = RoleChange.objects.select_related("employee__user", "approved_by")
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return RoleChangeListSerializer
        if self.action in ("create", "update", "partial_update"):
            return RoleChangeWriteSerializer
        return RoleChangeDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


class DisciplinaryRecordViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.lifecycle"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["employee__user__first_name", "employee__user__last_name", "description"]
    filterset_fields = ["employee", "category", "severity", "status"]
    ordering_fields = ["incident_date", "category", "severity", "status", "created_at"]
    ordering = ["-incident_date"]

    def get_queryset(self):
        qs = DisciplinaryRecord.objects.select_related("employee__user", "reported_by")
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return DisciplinaryRecordListSerializer
        if self.action in ("create", "update", "partial_update"):
            return DisciplinaryRecordWriteSerializer
        return DisciplinaryRecordDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


class ExitManagementViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.lifecycle"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["employee__user__first_name", "employee__user__last_name"]
    filterset_fields = ["employee", "exit_type", "clearance_status", "final_settlement_status"]
    ordering_fields = ["last_working_day", "exit_type", "clearance_status", "created_at"]
    ordering = ["-last_working_day"]

    def get_queryset(self):
        qs = ExitManagement.objects.select_related("employee__user", "processed_by")
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return ExitManagementListSerializer
        if self.action in ("create", "update", "partial_update"):
            return ExitManagementWriteSerializer
        return ExitManagementDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


class ExitInterviewViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.lifecycle"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["employee__user__first_name", "employee__user__last_name", "reason_for_leaving"]
    filterset_fields = ["employee", "overall_satisfaction", "would_recommend", "would_rejoin"]
    ordering_fields = ["interview_date", "overall_satisfaction", "created_at"]
    ordering = ["-interview_date"]

    def get_queryset(self):
        qs = ExitInterview.objects.select_related("employee__user", "interviewer", "exit_record")
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return ExitInterviewListSerializer
        if self.action in ("create", "update", "partial_update"):
            return ExitInterviewWriteSerializer
        return ExitInterviewDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


# =========================================================================
# 11. Workforce Analytics
# =========================================================================


class HeadcountSnapshotViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.analytics"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["department", "team"]
    filterset_fields = ["snapshot_date", "department"]
    ordering_fields = ["snapshot_date", "active_count", "created_at"]
    ordering = ["-snapshot_date"]

    def get_queryset(self):
        qs = HeadcountSnapshot.objects.all()
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return HeadcountSnapshotListSerializer
        if self.action in ("create", "update", "partial_update"):
            return HeadcountSnapshotWriteSerializer
        return HeadcountSnapshotDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


class TurnoverRecordViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.analytics"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["department"]
    filterset_fields = ["department"]
    ordering_fields = ["period_end", "period_start", "created_at"]
    ordering = ["-period_end"]

    def get_queryset(self):
        qs = TurnoverRecord.objects.all()
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return TurnoverRecordListSerializer
        if self.action in ("create", "update", "partial_update"):
            return TurnoverRecordWriteSerializer
        return TurnoverRecordDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


class DepartmentStaffingReportViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.analytics"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["department"]
    filterset_fields = ["department", "report_date"]
    ordering_fields = ["report_date", "department", "created_at"]
    ordering = ["-report_date", "department"]

    def get_queryset(self):
        qs = DepartmentStaffingReport.objects.all()
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return DepartmentStaffingReportListSerializer
        if self.action in ("create", "update", "partial_update"):
            return DepartmentStaffingReportWriteSerializer
        return DepartmentStaffingReportDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


class HiringFunnelMetricViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.analytics"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["department"]
    filterset_fields = ["department"]
    ordering_fields = ["period_end", "period_start", "offers_accepted", "created_at"]
    ordering = ["-period_end"]

    def get_queryset(self):
        qs = HiringFunnelMetric.objects.all()
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return HiringFunnelMetricListSerializer
        if self.action in ("create", "update", "partial_update"):
            return HiringFunnelMetricWriteSerializer
        return HiringFunnelMetricDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


class WorkforceCostReportViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.analytics"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["department"]
    filterset_fields = ["department", "currency"]
    ordering_fields = ["period_end", "period_start", "headcount", "created_at"]
    ordering = ["-period_end"]

    def get_queryset(self):
        qs = WorkforceCostReport.objects.all()
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return WorkforceCostReportListSerializer
        if self.action in ("create", "update", "partial_update"):
            return WorkforceCostReportWriteSerializer
        return WorkforceCostReportDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


class DiversityMetricViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.analytics"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["department", "category_value"]
    filterset_fields = ["dimension", "department", "snapshot_date"]
    ordering_fields = ["snapshot_date", "dimension", "count", "created_at"]
    ordering = ["-snapshot_date", "dimension", "-count"]

    def get_queryset(self):
        qs = DiversityMetric.objects.all()
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return DiversityMetricListSerializer
        if self.action in ("create", "update", "partial_update"):
            return DiversityMetricWriteSerializer
        return DiversityMetricDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


# ---------------------------------------------------------------------------
# HR Documents & Policies
# ---------------------------------------------------------------------------


class HRPolicyViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.documents"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["title", "department"]
    filterset_fields = ["category", "status"]
    ordering_fields = ["title", "effective_date", "updated_at"]
    ordering = ["-updated_at"]

    def get_queryset(self):
        qs = HRPolicy.objects.all()
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return HRPolicyListSerializer
        if self.action in ("create", "update", "partial_update"):
            return HRPolicyWriteSerializer
        return HRPolicyDetailSerializer

    def perform_create(self, serializer):
        serializer.save(
            organization=_user_org(self.request),
            created_by=self.request.user,
        )


class EmployeeHandbookSectionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.documents"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["title", "section_number"]
    filterset_fields = ["status", "handbook_version"]
    ordering_fields = ["order", "section_number", "updated_at"]
    ordering = ["order", "section_number"]

    def get_queryset(self):
        qs = EmployeeHandbookSection.objects.all()
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return EmployeeHandbookSectionListSerializer
        if self.action in ("create", "update", "partial_update"):
            return EmployeeHandbookSectionWriteSerializer
        return EmployeeHandbookSectionDetailSerializer

    def perform_create(self, serializer):
        serializer.save(
            organization=_user_org(self.request),
            last_updated_by=self.request.user,
        )

    def perform_update(self, serializer):
        serializer.save(last_updated_by=self.request.user)


class ComplianceDocumentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.documents"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["title", "reference_number", "issuing_authority"]
    filterset_fields = ["document_type", "status"]
    ordering_fields = ["title", "expiry_date", "updated_at"]
    ordering = ["-updated_at"]

    def get_queryset(self):
        qs = ComplianceDocument.objects.all()
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return ComplianceDocumentListSerializer
        if self.action in ("create", "update", "partial_update"):
            return ComplianceDocumentWriteSerializer
        return ComplianceDocumentDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


class PolicyAcknowledgementViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.documents"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["employee__username", "employee__first_name", "employee__last_name", "policy__title"]
    filterset_fields = ["acknowledged"]
    ordering_fields = ["acknowledged_date", "created_at"]
    ordering = ["-acknowledged_date"]

    def get_queryset(self):
        qs = PolicyAcknowledgement.objects.select_related("employee", "policy")
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return PolicyAcknowledgementListSerializer
        if self.action in ("create", "update", "partial_update"):
            return PolicyAcknowledgementWriteSerializer
        return PolicyAcknowledgementDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


class HRDocumentTemplateViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.documents"
    rbac_action_map = _HR_ACTION_MAP
    search_fields = ["title"]
    filterset_fields = ["category", "status"]
    ordering_fields = ["title", "updated_at"]
    ordering = ["-updated_at"]

    def get_queryset(self):
        qs = HRDocumentTemplate.objects.all()
        if not _is_superuser(self.request):
            org = _user_org(self.request)
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return HRDocumentTemplateListSerializer
        if self.action in ("create", "update", "partial_update"):
            return HRDocumentTemplateWriteSerializer
        return HRDocumentTemplateDetailSerializer

    def perform_create(self, serializer):
        serializer.save(
            organization=_user_org(self.request),
            created_by=self.request.user,
        )
