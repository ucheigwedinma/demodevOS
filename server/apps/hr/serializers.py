from calendar import monthrange
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Q, Sum
from django.utils import timezone
from rest_framework import serializers

from apps.settings.models import CostCenter, MasterDataEntry

from .automation import get_department_budget_health
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

# ---------------------------------------------------------------------------
# Team
# ---------------------------------------------------------------------------


class TeamListSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)
    business_unit_id = serializers.IntegerField(source="department.division_id", read_only=True)
    business_unit_name = serializers.CharField(source="department.division.name", read_only=True)
    team_type_display = serializers.CharField(source="get_team_type_display", read_only=True)
    lead_name = serializers.SerializerMethodField()
    member_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Team
        fields = [
            "id", "name", "code", "department", "department_name",
            "business_unit_id", "business_unit_name",
            "team_type", "team_type_display",
            "lead", "lead_name", "member_count",
            "is_active", "sort_order", "created_at", "updated_at",
        ]

    def get_lead_name(self, obj):
        return obj.lead.get_full_name() if obj.lead_id else None


class TeamDetailSerializer(TeamListSerializer):
    description = serializers.CharField()
    member_roster = serializers.SerializerMethodField()
    operational_performance = serializers.SerializerMethodField()
    automation_triggers = serializers.SerializerMethodField()

    class Meta(TeamListSerializer.Meta):
        fields = TeamListSerializer.Meta.fields + [
            "description",
            "member_roster",
            "operational_performance",
            "automation_triggers",
        ]

    def _build_team_member_roster(self, obj):
        cache = getattr(self, "_team_detail_cache", {})
        if obj.id in cache and "member_roster" in cache[obj.id]:
            return cache[obj.id]["member_roster"]

        from .models import PositionAssignment

        assignments = (
            PositionAssignment.objects
            .select_related(
                "user__profile__department",
                "position__department",
                "position__team",
            )
            .filter(
                organization=obj.organization,
                position__team=obj,
                is_active=True,
            )
            .order_by("user_id", "-is_primary", "-start_date", "-id")
        )

        if not assignments:
            cache[obj.id] = {
                "member_roster": [],
                "user_ids": [],
                "active_member_ids": [],
            }
            self._team_detail_cache = cache
            return []

        user_ids = []
        roster_by_user: dict[int, dict] = {}
        for assignment in assignments:
            user = assignment.user
            user_id = user.id
            profile = getattr(user, "profile", None)
            profile_photo_url = None
            if profile and profile.profile_photo:
                try:
                    profile_photo_url = profile.profile_photo.url
                except ValueError:
                    profile_photo_url = None

            if user_id not in roster_by_user:
                full_name = user.get_full_name() or user.email
                home_department = profile.department if profile and profile.department_id else None
                home_department_name = (
                    home_department.name if home_department else obj.department.name
                )
                roster_by_user[user_id] = {
                    "user_id": user_id,
                    "full_name": full_name,
                    "profile_photo_url": profile_photo_url,
                    "role_title": "",
                    "role_titles": [],
                    "home_department_name": home_department_name,
                    "is_cross_functional": bool(
                        home_department and home_department.id != obj.department_id
                    ),
                    "availability_status": "active",
                    "availability_label": "Active",
                }
                user_ids.append(user_id)

            role_title = (assignment.position.title or "").strip()
            if role_title and role_title not in roster_by_user[user_id]["role_titles"]:
                roster_by_user[user_id]["role_titles"].append(role_title)
            if not roster_by_user[user_id]["role_title"]:
                roster_by_user[user_id]["role_title"] = role_title

        employment_status_by_user = dict(
            EmployeeRecord.objects.filter(
                organization=obj.organization,
                user_id__in=user_ids,
            ).values_list("user_id", "employment_status")
        )
        primary_rows = (
            PositionAssignment.objects
            .filter(
                organization=obj.organization,
                user_id__in=user_ids,
                is_active=True,
                is_primary=True,
            )
            .order_by("user_id", "-start_date", "-id")
            .values_list("user_id", "position__team_id")
        )
        primary_team_by_user: dict[int, int | None] = {}
        for user_id, team_id in primary_rows:
            if user_id not in primary_team_by_user:
                primary_team_by_user[user_id] = team_id

        active_like_statuses = {
            EmployeeRecord.EmploymentStatus.ACTIVE,
            EmployeeRecord.EmploymentStatus.PROBATION,
            EmployeeRecord.EmploymentStatus.NOTICE_PERIOD,
        }

        for user_id, entry in roster_by_user.items():
            employment_status = employment_status_by_user.get(user_id)
            primary_team_id = primary_team_by_user.get(user_id)

            if employment_status == EmployeeRecord.EmploymentStatus.ON_LEAVE:
                entry["availability_status"] = "on_leave"
                entry["availability_label"] = "On Leave"
            elif primary_team_id and primary_team_id != obj.id:
                entry["availability_status"] = "reassigned"
                entry["availability_label"] = "Reassigned"
            elif employment_status and employment_status not in active_like_statuses:
                entry["availability_status"] = "reassigned"
                entry["availability_label"] = "Reassigned"

        roster = sorted(
            roster_by_user.values(),
            key=lambda item: (item["full_name"] or "").lower(),
        )
        cache[obj.id] = {
            "member_roster": roster,
            "user_ids": user_ids,
            "active_member_ids": [
                member["user_id"]
                for member in roster
                if member.get("availability_status") == "active"
            ],
        }
        self._team_detail_cache = cache
        return roster

    def get_member_roster(self, obj):
        return self._build_team_member_roster(obj)

    def get_operational_performance(self, obj):
        from apps.projects.models import Project, ProjectMilestone, ProjectTask

        cache = getattr(self, "_team_detail_cache", {})
        if obj.id in cache and "operational_performance" in cache[obj.id]:
            return cache[obj.id]["operational_performance"]

        self._build_team_member_roster(obj)
        cache = getattr(self, "_team_detail_cache", {})
        team_cache = cache.get(obj.id, {})
        user_ids = team_cache.get("user_ids", [])
        active_member_ids = team_cache.get("active_member_ids", [])
        today = timezone.localdate()

        empty_workload = {
            "booked_hours": 0.0,
            "capacity_hours": 0.0,
            "workload_percent": 0.0,
            "active_member_count": 0,
            "heat_level": "low",
            "heat_label": "Low",
            "period_label": today.strftime("%B %Y"),
            "formula": "Open task effort hours / (active team members x business days x 8h)",
        }
        empty_milestones = {
            "health": "no_milestones",
            "health_label": "No Milestones",
            "total_milestones": 0,
            "completed_milestones": 0,
            "due_soon_milestones": 0,
            "overdue_milestones": 0,
            "completion_percent": 0.0,
            "on_time_completion_percent": 0.0,
        }

        if not user_ids:
            payload = {
                "active_project_links": [],
                "workload": empty_workload,
                "milestone_progress": empty_milestones,
            }
            cache.setdefault(obj.id, {})
            cache[obj.id]["operational_performance"] = payload
            self._team_detail_cache = cache
            return payload

        active_project_statuses = [
            Project.Status.PLANNING,
            Project.Status.IN_PROGRESS,
            Project.Status.ON_HOLD,
        ]
        open_task_statuses = {
            ProjectTask.Status.PENDING,
            ProjectTask.Status.IN_PROGRESS,
        }

        task_rows = (
            ProjectTask.objects.filter(
                organization=obj.organization,
                assigned_user_id__in=user_ids,
                phase__project__organization=obj.organization,
                phase__project__status__in=active_project_statuses,
            )
            .values(
                "phase__project_id",
                "phase__project__name",
                "phase__project__status",
                "status",
                "estimated_effort_hours",
                "due_date",
            )
        )

        project_map = {}
        total_booked_hours = Decimal("0.0")
        for row in task_rows:
            project_id = row.get("phase__project_id")
            if not project_id:
                continue

            project_entry = project_map.get(project_id)
            if project_entry is None:
                project_entry = {
                    "project_id": project_id,
                    "project_name": row.get("phase__project__name") or f"Project {project_id}",
                    "project_status": row.get("phase__project__status") or "",
                    "project_href": f"/projects/{project_id}",
                    "task_count": 0,
                    "open_task_count": 0,
                    "overdue_open_task_count": 0,
                    "booked_hours": Decimal("0.0"),
                }
                project_map[project_id] = project_entry

            project_entry["task_count"] += 1
            status = row.get("status")
            if status in open_task_statuses:
                project_entry["open_task_count"] += 1
                due_date = row.get("due_date")
                if due_date and due_date < today:
                    project_entry["overdue_open_task_count"] += 1

                effort = Decimal(row.get("estimated_effort_hours") or 0)
                if effort > 0:
                    project_entry["booked_hours"] += effort
                    total_booked_hours += effort

        business_days_in_month = sum(
            1
            for day in range(1, monthrange(today.year, today.month)[1] + 1)
            if date(today.year, today.month, day).weekday() < 5
        )
        capacity_hours = Decimal(len(active_member_ids) * business_days_in_month * 8)
        workload_percent = (
            round(float((total_booked_hours / capacity_hours) * Decimal("100")), 2)
            if capacity_hours > 0
            else 0.0
        )

        if workload_percent > 100:
            heat_level = "critical"
            heat_label = "Critical"
        elif workload_percent > 85:
            heat_level = "high"
            heat_label = "High"
        elif workload_percent > 60:
            heat_level = "medium"
            heat_label = "Medium"
        else:
            heat_level = "low"
            heat_label = "Low"

        active_project_links = sorted(
            [
                {
                    "project_id": entry["project_id"],
                    "project_name": entry["project_name"],
                    "project_status": entry["project_status"],
                    "project_href": entry["project_href"],
                    "task_count": entry["task_count"],
                    "open_task_count": entry["open_task_count"],
                    "overdue_open_task_count": entry["overdue_open_task_count"],
                    "booked_hours": round(float(entry["booked_hours"]), 1),
                }
                for entry in project_map.values()
            ],
            key=lambda item: ((item["project_name"] or "").lower(), item["project_id"]),
        )

        milestone_progress = dict(empty_milestones)
        project_ids = [item["project_id"] for item in active_project_links]
        if project_ids:
            milestone_rows = ProjectMilestone.objects.filter(
                organization=obj.organization,
                phase__project_id__in=project_ids,
            ).values(
                "phase__project_id",
                "target_date",
                "completed_date",
                "is_completed",
            )

            total_milestones = 0
            completed_milestones = 0
            due_soon_milestones = 0
            overdue_milestones = 0
            on_time_completed = 0
            due_soon_cutoff = today + timedelta(days=14)

            for row in milestone_rows:
                total_milestones += 1
                target_date = row.get("target_date")
                is_completed = bool(row.get("is_completed"))
                completed_date = row.get("completed_date")

                if is_completed:
                    completed_milestones += 1
                    if target_date is None or (
                        completed_date is not None and completed_date <= target_date
                    ):
                        on_time_completed += 1
                    continue

                if target_date:
                    if target_date < today:
                        overdue_milestones += 1
                    elif today <= target_date <= due_soon_cutoff:
                        due_soon_milestones += 1

            completion_percent = (
                round((completed_milestones / total_milestones) * 100, 2)
                if total_milestones
                else 0.0
            )
            on_time_percent = (
                round((on_time_completed / completed_milestones) * 100, 2)
                if completed_milestones
                else 0.0
            )

            if total_milestones == 0:
                health = "no_milestones"
                health_label = "No Milestones"
            elif overdue_milestones > 0:
                health = "delayed"
                health_label = "Delayed"
            elif due_soon_milestones > 0:
                health = "at_risk"
                health_label = "At Risk"
            else:
                health = "on_track"
                health_label = "On Track"

            milestone_progress = {
                "health": health,
                "health_label": health_label,
                "total_milestones": total_milestones,
                "completed_milestones": completed_milestones,
                "due_soon_milestones": due_soon_milestones,
                "overdue_milestones": overdue_milestones,
                "completion_percent": completion_percent,
                "on_time_completion_percent": on_time_percent,
            }

        payload = {
            "active_project_links": active_project_links,
            "workload": {
                "booked_hours": round(float(total_booked_hours), 1),
                "capacity_hours": round(float(capacity_hours), 1),
                "workload_percent": workload_percent,
                "active_member_count": len(active_member_ids),
                "heat_level": heat_level,
                "heat_label": heat_label,
                "period_label": today.strftime("%B %Y"),
                "formula": "Open task effort hours / (active team members x business days x 8h)",
            },
            "milestone_progress": milestone_progress,
        }
        cache.setdefault(obj.id, {})
        cache[obj.id]["operational_performance"] = payload
        self._team_detail_cache = cache
        return payload

    def get_automation_triggers(self, obj):
        from apps.finance.models import Budget
        from apps.projects.models import ProjectCostEntry

        self._build_team_member_roster(obj)
        cache = getattr(self, "_team_detail_cache", {})
        team_cache = cache.get(obj.id, {})
        active_member_ids = team_cache.get("active_member_ids", [])
        performance = self.get_operational_performance(obj)
        active_project_links = performance.get("active_project_links", [])
        milestone_progress = performance.get("milestone_progress", {})
        today = timezone.localdate()
        month_start = today.replace(day=1)

        total_hours_logged = float(
            AttendanceLog.objects.filter(
                organization=obj.organization,
                employee__user_id__in=active_member_ids,
                date__gte=month_start,
                date__lte=today,
            ).aggregate(total=Sum("total_hours"))["total"]
            or Decimal("0")
        )
        project_ids = [item.get("project_id") for item in active_project_links if item.get("project_id")]
        billable_hours = total_hours_logged if project_ids else 0.0

        budget_map = {
            budget.project_id: budget
            for budget in Budget.objects.filter(
                organization=obj.organization,
                project_id__in=project_ids,
            ).only("id", "name", "project_id")
        }
        total_booked_hours = sum(float(item.get("booked_hours") or 0.0) for item in active_project_links)
        project_count = len(active_project_links)
        project_budget_allocations = []
        for item in active_project_links:
            project_id = item.get("project_id")
            booked_hours = float(item.get("booked_hours") or 0.0)
            if billable_hours <= 0:
                allocated = 0.0
            elif total_booked_hours > 0 and booked_hours > 0:
                allocated = round((billable_hours * booked_hours) / total_booked_hours, 2)
            elif project_count > 0:
                allocated = round(billable_hours / project_count, 2)
            else:
                allocated = 0.0

            budget = budget_map.get(project_id)
            project_budget_allocations.append(
                {
                    "project_id": project_id,
                    "project_name": item.get("project_name"),
                    "project_href": item.get("project_href"),
                    "budget_id": budget.id if budget else None,
                    "budget_name": budget.name if budget else None,
                    "allocated_billable_hours": allocated,
                }
            )

        linked_budget_count = sum(
            1 for allocation in project_budget_allocations if allocation.get("budget_id")
        )
        if total_hours_logged <= 0:
            timesheet_status = "pending"
            timesheet_message = "No team timesheet hours logged in the current period."
        elif billable_hours <= 0 or not project_budget_allocations:
            timesheet_status = "pending"
            timesheet_message = "Hours logged, but no active project workload is currently linked."
        elif linked_budget_count <= 0:
            timesheet_status = "pending"
            timesheet_message = (
                "Hours logged and project workload found, but no project budget container "
                "is available for charging yet."
            )
        else:
            timesheet_status = "triggered"
            timesheet_message = (
                f"{round(billable_hours, 2)} billable hours mapped to "
                f"{linked_budget_count} linked project budget target(s)."
            )

        petty_cash_qs = ProjectCostEntry.objects.filter(
            organization=obj.organization,
            phase__project_id__in=project_ids,
            category=ProjectCostEntry.Category.OTHER,
            date__gte=month_start,
            date__lte=today,
        ).filter(
            Q(description__icontains="petty cash")
            | Q(reference_number__startswith="HOOK:hr_team_petty_cash")
        )
        team_petty_cash = float(petty_cash_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0"))
        petty_cash_count = petty_cash_qs.count()
        if team_petty_cash > 0 and petty_cash_count > 0:
            expense_status = "triggered"
            expense_message = (
                f"{petty_cash_count} petty cash expense item(s) aggregated for Finance reimbursement."
            )
        else:
            expense_status = "pending"
            expense_message = "No petty cash expenses captured in the current period."

        success_rate = float(milestone_progress.get("on_time_completion_percent") or 0.0)
        completed_milestones = int(milestone_progress.get("completed_milestones") or 0)
        overdue_milestones = int(milestone_progress.get("overdue_milestones") or 0)
        high_performance_threshold = 85.0
        high_performance_tag = (
            success_rate >= high_performance_threshold
            and completed_milestones >= 3
            and overdue_milestones == 0
        )
        if high_performance_tag:
            kpi_status = "triggered"
            kpi_message = "High Performance tag raised for Team Lead annual review."
        else:
            kpi_status = "pending"
            kpi_message = "High Performance threshold not yet met consistently."

        return {
            "timesheets": {
                "feature": "Timesheets",
                "data_field": "Total Hours Logged",
                "total_hours_logged": round(total_hours_logged, 2),
                "billable_hours": round(billable_hours, 2),
                "project_budget_allocations": project_budget_allocations,
                "trigger_status": timesheet_status,
                "trigger_message": timesheet_message,
                "trigger_automation": (
                    "Accounting Trigger: Automatically calculates billable hours "
                    "to be charged against linked project budgets."
                ),
            },
            "expense_claims": {
                "feature": "Expense Claims",
                "data_field": "Team Petty Cash",
                "team_petty_cash": round(team_petty_cash, 2),
                "reimbursement_item_count": petty_cash_count,
                "trigger_status": expense_status,
                "trigger_message": expense_message,
                "trigger_automation": (
                    "Finance Trigger: Aggregates small field expenses for reimbursement processing."
                ),
            },
            "kpis": {
                "feature": "KPIs",
                "data_field": "Team Success Rate",
                "team_success_rate": round(success_rate, 2),
                "high_performance_threshold": high_performance_threshold,
                "high_performance_tag": high_performance_tag,
                "trigger_status": kpi_status,
                "trigger_message": kpi_message,
                "trigger_automation": (
                    "HR Trigger: Consistent early milestone delivery flags High Performance "
                    "for the Team Lead annual review."
                ),
            },
        }


class TeamWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = [
            "name", "code", "department", "team_type", "lead",
            "description", "is_active", "sort_order",
        ]


# ---------------------------------------------------------------------------
# Position Role
# ---------------------------------------------------------------------------


class PositionRoleListSerializer(serializers.ModelSerializer):
    position_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = PositionRole
        fields = [
            "id", "name", "grade", "code",
            "position_count",
            "is_active", "created_at", "updated_at",
        ]


class PositionRoleDetailSerializer(PositionRoleListSerializer):
    class Meta(PositionRoleListSerializer.Meta):
        fields = PositionRoleListSerializer.Meta.fields + [
            "description", "requirements",
            "key_responsibilities",
            "hard_skills", "soft_skills",
            "kpi_metrics",
        ]


class PositionRoleWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PositionRole
        fields = [
            "name", "grade", "code",
            "description", "requirements", "key_responsibilities",
            "hard_skills", "soft_skills", "kpi_metrics",
            "is_active",
        ]

    @staticmethod
    def _normalize_string_list(value, field_label: str):
        if value is None or value == "":
            return []
        if isinstance(value, str):
            value = [part.strip() for part in value.split(",")]
        if not isinstance(value, list):
            raise serializers.ValidationError(f"{field_label} must be a list of strings.")

        cleaned: list[str] = []
        for item in value:
            if item is None:
                continue
            if not isinstance(item, str):
                raise serializers.ValidationError(
                    f"{field_label} must contain only string values."
                )
            normalized = item.strip()
            if normalized:
                cleaned.append(normalized)
        # Preserve order while dropping duplicates.
        return list(dict.fromkeys(cleaned))

    def validate_hard_skills(self, value):
        return self._normalize_string_list(value, "Hard skills")

    def validate_soft_skills(self, value):
        return self._normalize_string_list(value, "Soft skills")

    def validate_kpi_metrics(self, value):
        return self._normalize_string_list(value, "KPI metrics")


# ---------------------------------------------------------------------------
# Position
# ---------------------------------------------------------------------------


class PositionListSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source="role.name", read_only=True, default=None)
    role_grade = serializers.CharField(source="role.grade", read_only=True, default=None)
    role_code = serializers.CharField(source="role.code", read_only=True, default=None)
    salary_structure_name = serializers.CharField(
        source="salary_structure.name", read_only=True, default=None,
    )
    salary_range_min = serializers.DecimalField(
        source="salary_structure.min_salary",
        max_digits=12,
        decimal_places=2,
        read_only=True,
        default=None,
    )
    salary_range_max = serializers.DecimalField(
        source="salary_structure.max_salary",
        max_digits=12,
        decimal_places=2,
        read_only=True,
        default=None,
    )
    salary_currency = serializers.CharField(
        source="salary_structure.currency", read_only=True, default=None,
    )
    salary_band_link = serializers.SerializerMethodField()
    department_name = serializers.CharField(source="department.name", read_only=True)
    team_name = serializers.CharField(source="team.name", read_only=True, default=None)
    cost_center_code = serializers.CharField(
        source="cost_center.code", read_only=True, default=None,
    )
    reports_to_title = serializers.CharField(
        source="reports_to.title", read_only=True, default=None,
    )
    direct_report_count = serializers.IntegerField(read_only=True, default=0)
    slot_status = serializers.SerializerMethodField()
    filled_count = serializers.IntegerField(read_only=True, default=0)
    vacancy_count = serializers.IntegerField(read_only=True, default=0)
    active_requisition_id = serializers.IntegerField(read_only=True, default=None)
    active_requisition_status = serializers.CharField(read_only=True, default=None)
    budget_guard_active = serializers.SerializerMethodField()
    vacancy_days_open = serializers.SerializerMethodField()
    succession_alert_due = serializers.SerializerMethodField()

    class Meta:
        model = Position
        fields = [
            "id", "role", "role_name", "role_grade", "role_code",
            "salary_structure", "salary_structure_name",
            "salary_range_min", "salary_range_max", "salary_currency", "salary_band_link",
            "title", "code", "department", "department_name",
            "team", "team_name", "reports_to", "reports_to_title",
            "direct_report_count",
            "cost_center", "cost_center_code",
            "employment_type", "level", "status", "slot_status",
            "criticality_score", "vacant_since", "vacancy_alert_sent_at",
            "headcount_budget", "filled_count", "vacancy_count",
            "active_requisition_id", "active_requisition_status",
            "budget_guard_active", "vacancy_days_open", "succession_alert_due",
            "is_active", "created_at", "updated_at",
        ]

    SALARY_BAND_FIELDS = (
        "salary_structure",
        "salary_structure_name",
        "salary_range_min",
        "salary_range_max",
        "salary_currency",
        "salary_band_link",
    )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if self.context.get("can_view_salary_band", False):
            return data
        for field in self.SALARY_BAND_FIELDS:
            data[field] = None
        return data

    def get_slot_status(self, obj):
        if obj.slot_status == Position.SlotStatus.PROPOSED:
            return Position.SlotStatus.PROPOSED

        filled_count = getattr(obj, "filled_count", None)
        if filled_count is None:
            filled_count = obj.assignments.filter(is_active=True).count()
        return (
            Position.SlotStatus.FILLED
            if int(filled_count or 0) > 0
            else Position.SlotStatus.VACANT
        )

    def get_salary_band_link(self, obj):
        if not obj.salary_structure_id:
            return None
        return f"/hr/salary-structures?focus={obj.salary_structure_id}"

    def get_budget_guard_active(self, obj):
        if obj.salary_structure_id:
            return True
        return bool(getattr(obj, "has_position_budget", False))

    def get_vacancy_days_open(self, obj):
        if not obj.vacant_since:
            return 0
        return max((timezone.localdate() - obj.vacant_since).days, 0)

    def get_succession_alert_due(self, obj):
        if obj.criticality_score < 80:
            return False
        if self.get_slot_status(obj) != Position.SlotStatus.VACANT:
            return False
        if obj.vacancy_alert_sent_at is not None:
            return False
        return self.get_vacancy_days_open(obj) > 30


class PositionDetailSerializer(PositionListSerializer):
    direct_reports = serializers.SerializerMethodField()

    class Meta(PositionListSerializer.Meta):
        fields = PositionListSerializer.Meta.fields + [
            "description", "requirements", "direct_reports",
        ]

    def get_direct_reports(self, obj):
        return [
            {
                "id": child.id,
                "title": child.title,
                "code": child.code,
                "department_name": child.department.name,
                "employment_type": child.employment_type,
                "slot_status": child.slot_status,
            }
            for child in obj.direct_reports.select_related("department").order_by("title")
        ]


class PositionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = [
            "role", "title", "code", "department", "team", "reports_to",
            "cost_center", "salary_structure",
            "employment_type", "level", "status", "slot_status",
            "criticality_score",
            "description", "requirements", "headcount_budget", "is_active",
        ]
        extra_kwargs = {
            "cost_center": {
                "required": False,
                "allow_null": True,
            }
        }

    def validate_role(self, value):
        if value is None:
            return value
        request = self.context.get("request")
        profile = getattr(getattr(request, "user", None), "profile", None)
        org_id = getattr(profile, "organization_id", None)
        if org_id and value.organization_id != org_id:
            raise serializers.ValidationError(
                "Selected role template does not belong to your organization."
            )
        return value

    def validate_salary_structure(self, value):
        if value is None:
            return value
        request = self.context.get("request")
        profile = getattr(getattr(request, "user", None), "profile", None)
        org_id = getattr(profile, "organization_id", None)
        if org_id and value.organization_id != org_id:
            raise serializers.ValidationError(
                "Selected salary structure does not belong to your organization."
            )
        return value

    def _request_org_id(self):
        request = self.context.get("request")
        profile = getattr(getattr(request, "user", None), "profile", None)
        return getattr(profile, "organization_id", None)

    def _infer_department_cost_center(self, org_id, department):
        if not org_id or not department:
            return None
        candidates = list(
            CostCenter.objects.filter(
                organization_id=org_id,
                department=department,
                is_active=True,
            ).order_by("id")[:2]
        )
        if len(candidates) == 1:
            return candidates[0]
        return None

    def validate(self, attrs):
        attrs = super().validate(attrs)

        department = attrs.get("department") or getattr(self.instance, "department", None)
        org_id = self._request_org_id() or getattr(
            getattr(department, "division", None),
            "organization_id",
            None,
        )
        explicit_cost_center = "cost_center" in attrs
        cost_center = (
            attrs.get("cost_center")
            if explicit_cost_center
            else getattr(self.instance, "cost_center", None)
        )

        if cost_center is None:
            inferred = self._infer_department_cost_center(org_id, department)
            if inferred is not None:
                attrs["cost_center"] = inferred
                cost_center = inferred

        if cost_center is None:
            raise serializers.ValidationError(
                {"cost_center": "Cost center is required for each position."}
            )

        if org_id and cost_center.organization_id != org_id:
            raise serializers.ValidationError(
                {"cost_center": "Selected cost center does not belong to your organization."}
            )

        if department and cost_center.department_id and cost_center.department_id != department.id:
            raise serializers.ValidationError(
                {
                    "cost_center": (
                        "Selected cost center must belong to the same department as this position."
                    )
                }
            )

        return attrs


# ---------------------------------------------------------------------------
# Position Assignment
# ---------------------------------------------------------------------------


class PositionAssignmentListSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    position_title = serializers.CharField(source="position.title", read_only=True)
    position_code = serializers.CharField(source="position.code", read_only=True)

    class Meta:
        model = PositionAssignment
        fields = [
            "id", "user", "user_name", "position", "position_title", "position_code",
            "start_date", "end_date", "is_primary", "is_active",
            "created_at", "updated_at",
        ]

    def get_user_name(self, obj):
        return obj.user.get_full_name()


class PositionAssignmentDetailSerializer(PositionAssignmentListSerializer):
    class Meta(PositionAssignmentListSerializer.Meta):
        fields = PositionAssignmentListSerializer.Meta.fields + ["notes"]


class PositionAssignmentWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PositionAssignment
        fields = [
            "user", "position", "start_date", "end_date",
            "is_primary", "is_active", "notes",
        ]


# ---------------------------------------------------------------------------
# Position Budget
# ---------------------------------------------------------------------------


class PositionBudgetListSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)
    position_title = serializers.CharField(
        source="position.title", read_only=True, default=None,
    )
    budget_source_display = serializers.CharField(
        source="get_budget_source_display",
        read_only=True,
    )
    variance = serializers.SerializerMethodField()
    base_salary_min = serializers.SerializerMethodField()
    base_salary_mid = serializers.SerializerMethodField()
    base_salary_max = serializers.SerializerMethodField()
    salary_band_currency = serializers.SerializerMethodField()
    burden_multiplier = serializers.SerializerMethodField()
    statutory_benefits_cost = serializers.SerializerMethodField()
    allowances_cost = serializers.SerializerMethodField()
    local_tax_cost = serializers.SerializerMethodField()
    insurance_cost = serializers.SerializerMethodField()
    fully_burdened_cost = serializers.SerializerMethodField()

    class Meta:
        model = PositionBudget
        fields = [
            "id", "department", "department_name",
            "position", "position_title",
            "fiscal_period_label", "fiscal_year",
            "budget_source", "budget_source_display",
            "currency",
            "fte",
            "statutory_benefits_rate",
            "allowances_rate",
            "local_tax_rate",
            "insurance_rate",
            "base_salary_min",
            "base_salary_mid",
            "base_salary_max",
            "salary_band_currency",
            "burden_multiplier",
            "statutory_benefits_cost",
            "allowances_cost",
            "local_tax_cost",
            "insurance_cost",
            "fully_burdened_cost",
            "approved_headcount", "filled_headcount",
            "budget_amount", "status", "variance",
            "created_at", "updated_at",
        ]

    def get_variance(self, obj):
        return obj.approved_headcount - obj.filled_headcount

    @staticmethod
    def _as_decimal(value):
        if value is None:
            return None
        if isinstance(value, Decimal):
            return value
        try:
            return Decimal(str(value))
        except Exception:
            return None

    @staticmethod
    def _money(value):
        if value is None:
            return None
        return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    @staticmethod
    def _multiplier(value):
        if value is None:
            return None
        return str(value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))

    def _salary_structure(self, obj):
        if not obj.position_id:
            return None
        return getattr(obj.position, "salary_structure", None)

    def _base_salary_values(self, obj):
        structure = self._salary_structure(obj)
        if not structure:
            return (None, None, None)

        min_salary = self._as_decimal(getattr(structure, "min_salary", None))
        max_salary = self._as_decimal(getattr(structure, "max_salary", None))
        if min_salary is not None and max_salary is not None:
            mid_salary = (min_salary + max_salary) / Decimal("2")
        else:
            mid_salary = min_salary if min_salary is not None else max_salary
        return (min_salary, mid_salary, max_salary)

    def _financial_components(self, obj):
        _min, base_mid, _max = self._base_salary_values(obj)
        if base_mid is None:
            return {
                "multiplier": None,
                "statutory": None,
                "allowances": None,
                "local_tax": None,
                "insurance": None,
                "fully_burdened": None,
            }

        fte = self._as_decimal(getattr(obj, "fte", None)) or Decimal("1")
        statutory_rate = self._as_decimal(getattr(obj, "statutory_benefits_rate", None)) or Decimal("0")
        allowances_rate = self._as_decimal(getattr(obj, "allowances_rate", None)) or Decimal("0")
        local_tax_rate = self._as_decimal(getattr(obj, "local_tax_rate", None)) or Decimal("0")
        insurance_rate = self._as_decimal(getattr(obj, "insurance_rate", None)) or Decimal("0")
        multiplier = Decimal("1") + (
            statutory_rate + allowances_rate + local_tax_rate + insurance_rate
        ) / Decimal("100")

        statutory_cost = base_mid * (statutory_rate / Decimal("100")) * fte
        allowances_cost = base_mid * (allowances_rate / Decimal("100")) * fte
        local_tax_cost = base_mid * (local_tax_rate / Decimal("100")) * fte
        insurance_cost = base_mid * (insurance_rate / Decimal("100")) * fte
        fully_burdened = base_mid * multiplier * fte
        return {
            "multiplier": multiplier,
            "statutory": statutory_cost,
            "allowances": allowances_cost,
            "local_tax": local_tax_cost,
            "insurance": insurance_cost,
            "fully_burdened": fully_burdened,
        }

    def get_base_salary_min(self, obj):
        min_salary, _mid_salary, _max_salary = self._base_salary_values(obj)
        return self._money(min_salary)

    def get_base_salary_mid(self, obj):
        _min_salary, mid_salary, _max_salary = self._base_salary_values(obj)
        return self._money(mid_salary)

    def get_base_salary_max(self, obj):
        _min_salary, _mid_salary, max_salary = self._base_salary_values(obj)
        return self._money(max_salary)

    def get_salary_band_currency(self, obj):
        structure = self._salary_structure(obj)
        if structure and getattr(structure, "currency", None):
            return structure.currency
        return obj.currency

    def get_burden_multiplier(self, obj):
        values = self._financial_components(obj)
        return self._multiplier(values["multiplier"])

    def get_statutory_benefits_cost(self, obj):
        values = self._financial_components(obj)
        return self._money(values["statutory"])

    def get_allowances_cost(self, obj):
        values = self._financial_components(obj)
        return self._money(values["allowances"])

    def get_local_tax_cost(self, obj):
        values = self._financial_components(obj)
        return self._money(values["local_tax"])

    def get_insurance_cost(self, obj):
        values = self._financial_components(obj)
        return self._money(values["insurance"])

    def get_fully_burdened_cost(self, obj):
        values = self._financial_components(obj)
        return self._money(values["fully_burdened"])


class PositionBudgetDetailSerializer(PositionBudgetListSerializer):
    approved_by_name = serializers.SerializerMethodField()

    class Meta(PositionBudgetListSerializer.Meta):
        fields = PositionBudgetListSerializer.Meta.fields + [
            "notes", "approved_by", "approved_by_name", "approved_at",
        ]

    def get_approved_by_name(self, obj):
        return obj.approved_by.get_full_name() if obj.approved_by_id else None


class PositionBudgetWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PositionBudget
        fields = [
            "department", "position",
            "fiscal_period_label", "fiscal_year",
            "budget_source", "currency",
            "fte", "statutory_benefits_rate", "allowances_rate",
            "local_tax_rate", "insurance_rate",
            "approved_headcount", "filled_headcount",
            "budget_amount", "status", "notes",
        ]

    def validate_currency(self, value):
        code = (value or "").strip().upper()
        if not code:
            raise serializers.ValidationError("Currency is required.")
        exists = MasterDataEntry.objects.filter(
            category=MasterDataEntry.Category.CURRENCY,
            code=code,
            is_active=True,
        ).exists()
        if not exists:
            raise serializers.ValidationError(
                "Currency must be an active MDM currency entry."
            )
        return code

    def validate(self, attrs):
        attrs = super().validate(attrs)
        fiscal_year = attrs.get("fiscal_year")
        if fiscal_year is None and self.instance is not None:
            fiscal_year = self.instance.fiscal_year
        fiscal_period_label = (attrs.get("fiscal_period_label") or "").strip()
        if not fiscal_period_label and fiscal_year:
            attrs["fiscal_period_label"] = f"FY {fiscal_year}"
        return attrs


class PositionBudgetRevisionListSerializer(serializers.ModelSerializer):
    budget_department_name = serializers.CharField(source="budget.department.name", read_only=True)
    budget_position_title = serializers.CharField(
        source="budget.position.title",
        read_only=True,
        default=None,
    )
    requested_by_name = serializers.SerializerMethodField()
    reviewed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = PositionBudgetRevision
        fields = [
            "id",
            "budget",
            "revision_number",
            "status",
            "reason",
            "budget_department_name",
            "budget_position_title",
            "requested_by",
            "requested_by_name",
            "reviewed_by",
            "reviewed_by_name",
            "reviewed_at",
            "review_notes",
            "created_at",
            "updated_at",
        ]

    def get_requested_by_name(self, obj):
        return obj.requested_by.get_full_name() if obj.requested_by_id else None

    def get_reviewed_by_name(self, obj):
        return obj.reviewed_by.get_full_name() if obj.reviewed_by_id else None


class PositionBudgetRevisionDetailSerializer(PositionBudgetRevisionListSerializer):
    class Meta(PositionBudgetRevisionListSerializer.Meta):
        fields = PositionBudgetRevisionListSerializer.Meta.fields + [
            "proposed_changes",
            "snapshot_before",
        ]


class PositionBudgetRevisionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PositionBudgetRevision
        fields = [
            "budget",
            "reason",
            "proposed_changes",
        ]


# ---------------------------------------------------------------------------
# Vacancy
# ---------------------------------------------------------------------------


class VacancyListSerializer(serializers.ModelSerializer):
    position_title = serializers.CharField(source="position.title", read_only=True)
    position_code = serializers.CharField(source="position.code", read_only=True)
    department_name = serializers.CharField(
        source="position.department.name", read_only=True,
    )
    hiring_manager_name = serializers.SerializerMethodField()
    days_open = serializers.SerializerMethodField()

    class Meta:
        model = Vacancy
        fields = [
            "id", "title", "position", "position_title", "position_code",
            "department_name", "status", "priority",
            "hiring_manager", "hiring_manager_name",
            "opened_date", "target_fill_date", "filled_date", "days_open",
            "created_at", "updated_at",
        ]

    def get_hiring_manager_name(self, obj):
        return obj.hiring_manager.get_full_name() if obj.hiring_manager_id else None

    def get_days_open(self, obj):
        if obj.status == Vacancy.Status.FILLED and obj.filled_date:
            return (obj.filled_date - obj.opened_date).days
        if obj.status in (Vacancy.Status.OPEN, Vacancy.Status.ON_HOLD):
            from django.utils import timezone
            return (timezone.localdate() - obj.opened_date).days
        return None


class VacancyDetailSerializer(VacancyListSerializer):
    approved_by_name = serializers.SerializerMethodField()
    filled_by_name = serializers.SerializerMethodField()

    class Meta(VacancyListSerializer.Meta):
        fields = VacancyListSerializer.Meta.fields + [
            "approved_by", "approved_by_name",
            "filled_by", "filled_by_name",
            "reason", "notes",
        ]

    def get_approved_by_name(self, obj):
        return obj.approved_by.get_full_name() if obj.approved_by_id else None

    def get_filled_by_name(self, obj):
        return obj.filled_by.get_full_name() if obj.filled_by_id else None


class VacancyWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vacancy
        fields = [
            "position", "title", "status", "priority",
            "hiring_manager", "approved_by",
            "target_fill_date", "reason", "notes",
        ]


# ---------------------------------------------------------------------------
# Org Chart (read-only, nested tree)
# ---------------------------------------------------------------------------


class OrgChartPositionSerializer(serializers.ModelSerializer):
    assigned_users = serializers.SerializerMethodField()
    is_vacant = serializers.SerializerMethodField()

    class Meta:
        model = Position
        fields = [
            "id",
            "title",
            "code",
            "level",
            "employment_type",
            "is_vacant",
            "assigned_users",
        ]

    def get_is_vacant(self, obj):
        assignments = getattr(obj, "prefetched_active_assignments", [])
        return len(assignments) == 0

    def get_assigned_users(self, obj):
        assignments = getattr(obj, "prefetched_active_assignments", [])
        employee_node_map = self.context.get("employee_node_map", {})
        serialized = []
        for assignment in assignments:
            details = employee_node_map.get(assignment.user_id, {})
            profile = getattr(assignment.user, "profile", None)
            serialized.append({
                "id": assignment.user_id,
                "name": assignment.user.get_full_name(),
                "title": obj.title,
                "department_name": details.get("department_name")
                or (profile.department.name if profile and profile.department_id else obj.department.name),
                "direct_report_count": details.get("direct_report_count", 0),
                "email": assignment.user.email,
                "phone": details.get("phone") or (profile.phone if profile else ""),
                "office_location": details.get("office_location")
                or (profile.office_location if profile else ""),
                "employment_type": obj.employment_type,
                "salary_band": details.get("salary_band"),
                "is_primary": assignment.is_primary,
                "is_acting": not assignment.is_primary,
                "acting_roles": details.get("acting_roles", []),
                "project_assignment_count": details.get("project_assignment_count", 0),
                "project_assignments": details.get("project_assignments", []),
            })
        return serialized


class OrgChartTeamSerializer(serializers.ModelSerializer):
    positions = OrgChartPositionSerializer(many=True, read_only=True)
    lead_name = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = ["id", "name", "code", "lead", "lead_name", "positions"]

    def get_lead_name(self, obj):
        return obj.lead.get_full_name() if obj.lead_id else None


class OrgChartDepartmentSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    code = serializers.CharField()
    head_name = serializers.CharField(allow_null=True)
    teams = OrgChartTeamSerializer(many=True)
    positions = OrgChartPositionSerializer(many=True)


class OrgChartDivisionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    code = serializers.CharField()
    head_name = serializers.CharField(allow_null=True)
    departments = OrgChartDepartmentSerializer(many=True)


# ---------------------------------------------------------------------------
# Reporting Lines (read-only)
# ---------------------------------------------------------------------------


class ReportingLineUserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    full_name = serializers.CharField()
    job_title = serializers.CharField()
    department = serializers.CharField(allow_null=True)
    reports_to = serializers.IntegerField(allow_null=True)
    direct_report_count = serializers.IntegerField()


# ---------------------------------------------------------------------------
# Employee Record
# ---------------------------------------------------------------------------


class EmployeeDirectoryListSerializer(serializers.ModelSerializer):
    """Read-only composite: UserProfile fields + EmployeeRecord fields."""

    user_id = serializers.IntegerField(source="user.id", read_only=True)
    full_name = serializers.SerializerMethodField()
    email = serializers.EmailField(source="user.email", read_only=True)
    employee_id = serializers.CharField(source="user.profile.employee_id", read_only=True, default="")
    job_title = serializers.CharField(source="user.profile.job_title", read_only=True, default="")
    department_name = serializers.SerializerMethodField()
    position_title = serializers.SerializerMethodField()
    employment_type = serializers.SerializerMethodField()
    manager_name = serializers.SerializerMethodField()
    office_location = serializers.CharField(source="user.profile.office_location", read_only=True, default="")
    profile_photo = serializers.ImageField(source="user.profile.profile_photo", read_only=True)
    user_status = serializers.CharField(source="user.profile.user_status", read_only=True, default="")

    class Meta:
        model = EmployeeRecord
        fields = [
            "id", "user_id", "full_name", "email", "employee_id",
            "job_title", "department_name", "position_title", "employment_type",
            "manager_name", "office_location", "profile_photo", "user_status",
            "employment_status", "hire_date", "contract_type",
            "created_at", "updated_at",
        ]

    def get_full_name(self, obj):
        return obj.user.get_full_name()

    def get_department_name(self, obj):
        dept = getattr(obj.user, "profile", None) and obj.user.profile.department
        return dept.name if dept else None

    def get_position_title(self, obj):
        assignment = getattr(obj, "primary_assignment", None)
        if assignment:
            return assignment.position.title
        return None

    def get_employment_type(self, obj):
        assignment = getattr(obj, "primary_assignment", None)
        if assignment:
            return assignment.position.employment_type
        return None

    def get_manager_name(self, obj):
        mgr = getattr(obj.user, "profile", None) and obj.user.profile.reporting_manager
        return mgr.get_full_name() if mgr else None


class EmployeeDirectoryDetailSerializer(EmployeeDirectoryListSerializer):
    emergency_contacts_count = serializers.SerializerMethodField()
    id_documents_count = serializers.SerializerMethodField()
    hr_documents_count = serializers.SerializerMethodField()

    class Meta(EmployeeDirectoryListSerializer.Meta):
        fields = EmployeeDirectoryListSerializer.Meta.fields + [
            "probation_end_date", "contract_start_date", "contract_end_date",
            "termination_date", "termination_reason", "notes",
            "emergency_contacts_count", "id_documents_count", "hr_documents_count",
        ]

    def get_emergency_contacts_count(self, obj):
        return obj.user.emergency_contacts.count()

    def get_id_documents_count(self, obj):
        return obj.user.identification_documents.count()

    def get_hr_documents_count(self, obj):
        return obj.user.hr_documents.count()


class EmployeeRecordWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeRecord
        fields = [
            "user", "hire_date", "probation_end_date",
            "contract_start_date", "contract_end_date", "contract_type",
            "employment_status", "termination_date", "termination_reason",
            "notes",
        ]


# ---------------------------------------------------------------------------
# Emergency Contact
# ---------------------------------------------------------------------------


class EmergencyContactListSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = EmergencyContact
        fields = [
            "id", "user", "user_name", "name", "relationship",
            "phone", "secondary_phone", "email", "address",
            "is_primary", "sort_order", "created_at", "updated_at",
        ]

    def get_user_name(self, obj):
        return obj.user.get_full_name()


class EmergencyContactWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyContact
        fields = [
            "user", "name", "relationship", "phone", "secondary_phone",
            "email", "address", "is_primary", "sort_order",
        ]


# ---------------------------------------------------------------------------
# Identification Document
# ---------------------------------------------------------------------------


class IdentificationDocumentListSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = IdentificationDocument
        fields = [
            "id", "user", "user_name", "document_type", "document_number",
            "issuing_authority", "issuing_country",
            "issue_date", "expiry_date", "file", "notes",
            "created_at", "updated_at",
        ]

    def get_user_name(self, obj):
        return obj.user.get_full_name()


class IdentificationDocumentWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = IdentificationDocument
        fields = [
            "user", "document_type", "document_number",
            "issuing_authority", "issuing_country",
            "issue_date", "expiry_date", "file", "notes",
        ]

    def validate_file(self, value):
        from config.upload_validators import validate_upload
        return validate_upload(value, kind="any")


# ---------------------------------------------------------------------------
# Compensation Record
# ---------------------------------------------------------------------------


class CompensationRecordListSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = CompensationRecord
        fields = [
            "id", "user", "user_name", "effective_date", "end_date",
            "base_salary", "currency", "pay_frequency",
            "allowances", "bonus", "total_package",
            "status", "approved_by", "approved_by_name", "approved_at",
            "created_at", "updated_at",
        ]

    def get_user_name(self, obj):
        return obj.user.get_full_name()

    def get_approved_by_name(self, obj):
        return obj.approved_by.get_full_name() if obj.approved_by_id else None


class CompensationRecordDetailSerializer(CompensationRecordListSerializer):
    class Meta(CompensationRecordListSerializer.Meta):
        fields = CompensationRecordListSerializer.Meta.fields + ["notes"]


class CompensationRecordWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompensationRecord
        fields = [
            "user", "effective_date", "end_date",
            "base_salary", "currency", "pay_frequency",
            "allowances", "bonus", "total_package",
            "status", "notes",
        ]


# ---------------------------------------------------------------------------
# HR Document
# ---------------------------------------------------------------------------


class HRDocumentListSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    uploaded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = HRDocument
        fields = [
            "id", "user", "user_name", "title", "category",
            "file", "file_size", "description",
            "uploaded_by", "uploaded_by_name",
            "created_at", "updated_at",
        ]

    def get_user_name(self, obj):
        return obj.user.get_full_name()

    def get_uploaded_by_name(self, obj):
        return obj.uploaded_by.get_full_name() if obj.uploaded_by_id else None


class HRDocumentWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = HRDocument
        fields = [
            "user", "title", "category", "file", "description",
        ]

    def validate_file(self, value):
        from config.upload_validators import validate_upload
        return validate_upload(value, kind="any")


# ---------------------------------------------------------------------------
# Employment History (read-only)
# ---------------------------------------------------------------------------


class EmploymentHistoryEntrySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    position_title = serializers.CharField()
    position_code = serializers.CharField()
    department_name = serializers.CharField()
    start_date = serializers.DateField()
    end_date = serializers.DateField(allow_null=True)
    is_primary = serializers.BooleanField()
    is_active = serializers.BooleanField()


# ---------------------------------------------------------------------------
# Contact Directory (read-only, lightweight)
# ---------------------------------------------------------------------------


class ContactDirectoryItemSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    full_name = serializers.CharField()
    department_name = serializers.CharField(allow_null=True)
    phone = serializers.CharField()
    email = serializers.EmailField()
    office_location = serializers.CharField()


# ---------------------------------------------------------------------------
# Job Requisition
# ---------------------------------------------------------------------------


class JobRequisitionListSerializer(serializers.ModelSerializer):
    position_title = serializers.SerializerMethodField()
    department_name = serializers.SerializerMethodField()
    requested_by_name = serializers.SerializerMethodField()

    class Meta:
        model = JobRequisition
        fields = [
            "id", "title", "position", "position_title",
            "department", "department_name", "requisition_type",
            "headcount_requested", "priority", "status",
            "requested_by", "requested_by_name",
            "salary_range_min", "salary_range_max", "currency",
            "target_start_date", "created_at", "updated_at",
        ]

    def get_position_title(self, obj):
        return obj.position.title if obj.position_id else None

    def get_department_name(self, obj):
        return obj.department.name if obj.department_id else None

    def get_requested_by_name(self, obj):
        return obj.requested_by.get_full_name()


class JobRequisitionDetailSerializer(JobRequisitionListSerializer):
    approved_by_name = serializers.SerializerMethodField()

    class Meta(JobRequisitionListSerializer.Meta):
        fields = JobRequisitionListSerializer.Meta.fields + [
            "vacancy", "justification",
            "approved_by", "approved_by_name", "approved_at", "notes",
        ]

    def get_approved_by_name(self, obj):
        return obj.approved_by.get_full_name() if obj.approved_by_id else None


class JobRequisitionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobRequisition
        fields = [
            "title", "position", "vacancy", "department",
            "requisition_type", "justification", "headcount_requested",
            "priority", "salary_range_min", "salary_range_max",
            "currency", "target_start_date", "notes",
        ]


# ---------------------------------------------------------------------------
# Job Listing
# ---------------------------------------------------------------------------


class JobListingListSerializer(serializers.ModelSerializer):
    requisition_title = serializers.SerializerMethodField()
    candidate_count = serializers.SerializerMethodField()

    class Meta:
        model = JobListing
        fields = [
            "id", "requisition", "requisition_title", "title",
            "location", "employment_type", "is_internal", "is_external",
            "posted_date", "closing_date", "status",
            "candidate_count", "created_at", "updated_at",
        ]

    def get_requisition_title(self, obj):
        return obj.requisition.title if obj.requisition_id else None

    def get_candidate_count(self, obj):
        return obj.candidates.count()


class JobListingDetailSerializer(JobListingListSerializer):
    posted_by_name = serializers.SerializerMethodField()

    class Meta(JobListingListSerializer.Meta):
        fields = JobListingListSerializer.Meta.fields + [
            "description", "requirements", "salary_display",
            "salary_min", "salary_max", "currency",
            "posted_by", "posted_by_name", "notes",
        ]

    def get_posted_by_name(self, obj):
        return obj.posted_by.get_full_name() if obj.posted_by_id else None


class JobListingWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobListing
        fields = [
            "requisition", "title", "description", "requirements",
            "location", "employment_type", "salary_display",
            "salary_min", "salary_max", "currency",
            "is_internal", "is_external", "closing_date", "notes",
        ]


# ---------------------------------------------------------------------------
# Candidate
# ---------------------------------------------------------------------------


class CandidateListSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    listing_title = serializers.SerializerMethodField()
    requisition_title = serializers.SerializerMethodField()
    interview_count = serializers.SerializerMethodField()
    evaluation_count = serializers.SerializerMethodField()
    avg_rating = serializers.SerializerMethodField()

    class Meta:
        model = Candidate
        fields = [
            "id", "full_name", "email", "phone",
            "job_listing", "listing_title",
            "job_requisition", "requisition_title",
            "source", "stage", "current_title", "current_employer",
            "applied_date", "interview_count", "evaluation_count",
            "avg_rating", "created_at", "updated_at",
        ]

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

    def get_listing_title(self, obj):
        return obj.job_listing.title if obj.job_listing_id else None

    def get_requisition_title(self, obj):
        return obj.job_requisition.title if obj.job_requisition_id else None

    def get_interview_count(self, obj):
        return obj.interviews.count()

    def get_evaluation_count(self, obj):
        return obj.evaluations.count()

    def get_avg_rating(self, obj):
        evals = obj.evaluations.all()
        if not evals.exists():
            return None
        from django.db.models import Avg
        return evals.aggregate(avg=Avg("overall_rating"))["avg"]


class CandidateDetailSerializer(CandidateListSerializer):
    referred_by_name = serializers.SerializerMethodField()

    class Meta(CandidateListSerializer.Meta):
        fields = CandidateListSerializer.Meta.fields + [
            "first_name", "last_name", "resume",
            "expected_salary", "currency",
            "referred_by", "referred_by_name",
            "rejection_reason", "notes",
        ]

    def get_referred_by_name(self, obj):
        return obj.referred_by.get_full_name() if obj.referred_by_id else None


class CandidateWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Candidate
        fields = [
            "job_listing", "job_requisition",
            "first_name", "last_name", "email", "phone",
            "source", "referred_by", "resume",
            "current_title", "current_employer",
            "expected_salary", "currency", "notes",
        ]


# ---------------------------------------------------------------------------
# Interview
# ---------------------------------------------------------------------------


class InterviewListSerializer(serializers.ModelSerializer):
    candidate_name = serializers.SerializerMethodField()
    interviewer_name = serializers.SerializerMethodField()
    has_evaluation = serializers.SerializerMethodField()

    class Meta:
        model = Interview
        fields = [
            "id", "candidate", "candidate_name",
            "interview_type", "interviewer", "interviewer_name",
            "scheduled_date", "scheduled_time", "duration_minutes",
            "location", "meeting_link", "status",
            "has_evaluation", "created_at", "updated_at",
        ]

    def get_candidate_name(self, obj):
        return str(obj.candidate)

    def get_interviewer_name(self, obj):
        return obj.interviewer.get_full_name()

    def get_has_evaluation(self, obj):
        return obj.evaluations.exists()


class InterviewDetailSerializer(InterviewListSerializer):
    class Meta(InterviewListSerializer.Meta):
        fields = InterviewListSerializer.Meta.fields + ["notes"]


class InterviewWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interview
        fields = [
            "candidate", "interview_type", "interviewer",
            "scheduled_date", "scheduled_time", "duration_minutes",
            "location", "meeting_link", "notes",
        ]


# ---------------------------------------------------------------------------
# Candidate Evaluation
# ---------------------------------------------------------------------------


class CandidateEvaluationListSerializer(serializers.ModelSerializer):
    candidate_name = serializers.SerializerMethodField()
    evaluator_name = serializers.SerializerMethodField()

    class Meta:
        model = CandidateEvaluation
        fields = [
            "id", "candidate", "candidate_name",
            "interview", "evaluator", "evaluator_name",
            "overall_rating", "recommendation",
            "evaluated_at", "created_at", "updated_at",
        ]

    def get_candidate_name(self, obj):
        return str(obj.candidate)

    def get_evaluator_name(self, obj):
        return obj.evaluator.get_full_name()


class CandidateEvaluationDetailSerializer(CandidateEvaluationListSerializer):
    class Meta(CandidateEvaluationListSerializer.Meta):
        fields = CandidateEvaluationListSerializer.Meta.fields + [
            "strengths", "concerns", "notes",
        ]


class CandidateEvaluationWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateEvaluation
        fields = [
            "candidate", "interview",
            "overall_rating", "recommendation",
            "strengths", "concerns", "notes",
        ]


# ---------------------------------------------------------------------------
# Job Offer
# ---------------------------------------------------------------------------


class JobOfferListSerializer(serializers.ModelSerializer):
    candidate_name = serializers.SerializerMethodField()
    requisition_title = serializers.SerializerMethodField()
    position_title = serializers.SerializerMethodField()

    class Meta:
        model = JobOffer
        fields = [
            "id", "candidate", "candidate_name",
            "requisition", "requisition_title",
            "position", "position_title",
            "offered_salary", "currency",
            "start_date", "expiry_date", "status", "cfo_override_approved",
            "created_at", "updated_at",
        ]

    def get_candidate_name(self, obj):
        return str(obj.candidate)

    def get_requisition_title(self, obj):
        return obj.requisition.title if obj.requisition_id else None

    def get_position_title(self, obj):
        return obj.position.title if obj.position_id else None


class JobOfferDetailSerializer(JobOfferListSerializer):
    approved_by_name = serializers.SerializerMethodField()
    cfo_override_by_name = serializers.SerializerMethodField()

    class Meta(JobOfferListSerializer.Meta):
        fields = JobOfferListSerializer.Meta.fields + [
            "offer_letter", "terms",
            "approved_by", "approved_by_name", "approved_at",
            "cfo_override_by", "cfo_override_by_name", "cfo_override_at",
            "cfo_override_reason",
            "extended_at", "responded_at", "response_notes", "notes",
        ]

    def get_approved_by_name(self, obj):
        return obj.approved_by.get_full_name() if obj.approved_by_id else None

    def get_cfo_override_by_name(self, obj):
        return obj.cfo_override_by.get_full_name() if obj.cfo_override_by_id else None


class JobOfferWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobOffer
        fields = [
            "candidate", "requisition", "position",
            "offered_salary", "currency",
            "start_date", "expiry_date",
            "offer_letter", "terms", "notes",
        ]


# ---------------------------------------------------------------------------
# Onboarding Template
# ---------------------------------------------------------------------------


class OnboardingTemplateListSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True, default=None)
    position_title = serializers.CharField(source="position.title", read_only=True, default=None)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = OnboardingTemplate
        fields = [
            "id", "name", "description", "department", "department_name",
            "position", "position_title", "is_active", "task_count",
            "created_by", "created_by_name", "created_at", "updated_at",
        ]

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by_id else None


class OnboardingTemplateWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnboardingTemplate
        fields = [
            "name", "description", "department", "position", "is_active",
        ]


# ---------------------------------------------------------------------------
# Onboarding Task
# ---------------------------------------------------------------------------


class OnboardingTaskListSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    template_name = serializers.CharField(source="template.name", read_only=True, default=None)
    assigned_to_name = serializers.SerializerMethodField()

    class Meta:
        model = OnboardingTask
        fields = [
            "id", "employee", "employee_name", "template", "template_name",
            "title", "description", "category", "assigned_to", "assigned_to_name",
            "status", "is_required", "due_date", "completed_date",
            "sort_order", "created_at", "updated_at",
        ]

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name()

    def get_assigned_to_name(self, obj):
        return obj.assigned_to.get_full_name() if obj.assigned_to_id else None


class OnboardingTaskWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnboardingTask
        fields = [
            "employee", "template", "title", "description", "category",
            "assigned_to", "status", "is_required", "due_date",
            "completed_date", "sort_order", "notes",
        ]


# ---------------------------------------------------------------------------
# Document Collection
# ---------------------------------------------------------------------------


class DocumentCollectionListSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    verified_by_name = serializers.SerializerMethodField()

    class Meta:
        model = DocumentCollectionItem
        fields = [
            "id", "employee", "employee_name", "document_name", "description",
            "status", "due_date", "submitted_date",
            "verified_by", "verified_by_name", "verified_date",
            "rejection_reason", "created_at", "updated_at",
        ]

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name()

    def get_verified_by_name(self, obj):
        return obj.verified_by.get_full_name() if obj.verified_by_id else None


class DocumentCollectionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentCollectionItem
        fields = [
            "employee", "document_name", "description", "status",
            "file", "due_date", "submitted_date", "rejection_reason",
        ]

    def validate_file(self, value):
        from config.upload_validators import validate_upload
        return validate_upload(value, kind="any")


# ---------------------------------------------------------------------------
# Equipment Allocation
# ---------------------------------------------------------------------------


class EquipmentAllocationListSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    allocated_by_name = serializers.SerializerMethodField()

    class Meta:
        model = EquipmentAllocation
        fields = [
            "id", "employee", "employee_name", "item_name", "description",
            "category", "serial_number", "asset_tag", "status",
            "allocated_date", "return_date",
            "allocated_by", "allocated_by_name",
            "created_at", "updated_at",
        ]

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name()

    def get_allocated_by_name(self, obj):
        return obj.allocated_by.get_full_name() if obj.allocated_by_id else None


class EquipmentAllocationWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = EquipmentAllocation
        fields = [
            "employee", "item_name", "description", "category",
            "serial_number", "asset_tag", "status",
            "allocated_date", "return_date", "notes",
        ]


# ---------------------------------------------------------------------------
# Orientation Checklist
# ---------------------------------------------------------------------------


class OrientationChecklistListSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    completed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = OrientationChecklistItem
        fields = [
            "id", "employee", "employee_name", "title", "description",
            "category", "is_completed", "completed_date",
            "completed_by", "completed_by_name", "sort_order",
            "created_at", "updated_at",
        ]

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name()

    def get_completed_by_name(self, obj):
        return obj.completed_by.get_full_name() if obj.completed_by_id else None


class OrientationChecklistWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrientationChecklistItem
        fields = [
            "employee", "title", "description", "category",
            "is_completed", "completed_date", "sort_order", "notes",
        ]


# ---------------------------------------------------------------------------
# Probation Record
# ---------------------------------------------------------------------------


class ProbationRecordListSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    reviewer_name = serializers.SerializerMethodField()

    class Meta:
        model = ProbationRecord
        fields = [
            "id", "employee", "employee_name",
            "start_date", "end_date", "extended_end_date",
            "status", "review_date", "next_review_date",
            "reviewer", "reviewer_name",
            "performance_rating", "recommendation",
            "created_at", "updated_at",
        ]

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name()

    def get_reviewer_name(self, obj):
        return obj.reviewer.get_full_name() if obj.reviewer_id else None


class ProbationRecordDetailSerializer(ProbationRecordListSerializer):
    class Meta(ProbationRecordListSerializer.Meta):
        fields = ProbationRecordListSerializer.Meta.fields + [
            "notes", "outcome_notes",
        ]


class ProbationRecordWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProbationRecord
        fields = [
            "employee", "start_date", "end_date", "extended_end_date",
            "status", "review_date", "next_review_date", "reviewer",
            "performance_rating", "recommendation",
            "notes", "outcome_notes",
        ]


# ---------------------------------------------------------------------------
# Performance Goal
# ---------------------------------------------------------------------------


class PerformanceGoalListSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = PerformanceGoal
        fields = [
            "id", "employee", "employee_name", "title", "goal_type",
            "status", "priority", "target_value", "current_value",
            "unit", "weight", "start_date", "due_date", "completed_date",
            "progress", "parent_goal", "created_at", "updated_at",
        ]

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name()


class PerformanceGoalDetailSerializer(PerformanceGoalListSerializer):
    class Meta(PerformanceGoalListSerializer.Meta):
        fields = PerformanceGoalListSerializer.Meta.fields + [
            "description", "notes",
        ]


class PerformanceGoalWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PerformanceGoal
        fields = [
            "employee", "title", "description", "goal_type",
            "status", "priority", "target_value", "current_value",
            "unit", "weight", "start_date", "due_date",
            "progress", "parent_goal", "notes",
        ]


# ---------------------------------------------------------------------------
# Performance Review
# ---------------------------------------------------------------------------


class PerformanceReviewListSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    reviewer_name = serializers.SerializerMethodField()

    class Meta:
        model = PerformanceReview
        fields = [
            "id", "employee", "employee_name",
            "reviewer", "reviewer_name", "review_type",
            "review_period_start", "review_period_end",
            "status", "overall_rating",
            "submitted_at", "acknowledged_at",
            "created_at", "updated_at",
        ]

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name()

    def get_reviewer_name(self, obj):
        return obj.reviewer.get_full_name()


class PerformanceReviewDetailSerializer(PerformanceReviewListSerializer):
    class Meta(PerformanceReviewListSerializer.Meta):
        fields = PerformanceReviewListSerializer.Meta.fields + [
            "strengths", "areas_for_improvement", "goals_summary",
            "employee_comments", "reviewer_comments", "notes",
        ]


class PerformanceReviewWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PerformanceReview
        fields = [
            "employee", "reviewer", "review_type",
            "review_period_start", "review_period_end",
            "overall_rating", "strengths", "areas_for_improvement",
            "goals_summary", "employee_comments", "reviewer_comments",
            "notes",
        ]


# ---------------------------------------------------------------------------
# Continuous Feedback
# ---------------------------------------------------------------------------


class ContinuousFeedbackListSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    given_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ContinuousFeedback
        fields = [
            "id", "employee", "employee_name",
            "given_by", "given_by_name",
            "feedback_type", "visibility", "subject",
            "is_anonymous", "created_at", "updated_at",
        ]

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name()

    def get_given_by_name(self, obj):
        if obj.is_anonymous:
            return "Anonymous"
        return obj.given_by.get_full_name()


class ContinuousFeedbackDetailSerializer(ContinuousFeedbackListSerializer):
    class Meta(ContinuousFeedbackListSerializer.Meta):
        fields = ContinuousFeedbackListSerializer.Meta.fields + ["content"]


class ContinuousFeedbackWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContinuousFeedback
        fields = [
            "employee", "feedback_type", "visibility",
            "subject", "content", "is_anonymous",
        ]


# ---------------------------------------------------------------------------
# Manager Evaluation
# ---------------------------------------------------------------------------


class ManagerEvaluationListSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    evaluator_name = serializers.SerializerMethodField()

    class Meta:
        model = ManagerEvaluation
        fields = [
            "id", "employee", "employee_name",
            "review", "evaluator", "evaluator_name",
            "evaluation_date", "overall_rating",
            "leadership_rating", "communication_rating",
            "technical_rating", "teamwork_rating",
            "created_at", "updated_at",
        ]

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name()

    def get_evaluator_name(self, obj):
        return obj.evaluator.get_full_name()


class ManagerEvaluationDetailSerializer(ManagerEvaluationListSerializer):
    class Meta(ManagerEvaluationListSerializer.Meta):
        fields = ManagerEvaluationListSerializer.Meta.fields + [
            "strengths", "areas_for_improvement",
            "goals_for_next_period", "comments",
        ]


class ManagerEvaluationWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManagerEvaluation
        fields = [
            "employee", "review", "evaluation_date",
            "overall_rating", "leadership_rating",
            "communication_rating", "technical_rating",
            "teamwork_rating", "strengths", "areas_for_improvement",
            "goals_for_next_period", "comments",
        ]


# ---------------------------------------------------------------------------
# Peer Review
# ---------------------------------------------------------------------------


class PeerReviewListSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    reviewer_name = serializers.SerializerMethodField()

    class Meta:
        model = PeerReview
        fields = [
            "id", "employee", "employee_name",
            "reviewer", "reviewer_name", "review",
            "status", "overall_rating",
            "collaboration_rating", "communication_rating",
            "is_anonymous", "submitted_at",
            "created_at", "updated_at",
        ]

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name()

    def get_reviewer_name(self, obj):
        if obj.is_anonymous:
            return "Anonymous"
        return obj.reviewer.get_full_name()


class PeerReviewDetailSerializer(PeerReviewListSerializer):
    class Meta(PeerReviewListSerializer.Meta):
        fields = PeerReviewListSerializer.Meta.fields + [
            "strengths", "areas_for_improvement", "comments",
        ]


class PeerReviewWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PeerReview
        fields = [
            "employee", "review", "overall_rating",
            "collaboration_rating", "communication_rating",
            "strengths", "areas_for_improvement",
            "comments", "is_anonymous",
        ]


# ---------------------------------------------------------------------------
# Performance Improvement Plan
# ---------------------------------------------------------------------------


class PIPListSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = PerformanceImprovementPlan
        fields = [
            "id", "employee", "employee_name",
            "created_by", "created_by_name",
            "title", "start_date", "end_date", "extended_end_date",
            "status", "outcome", "created_at", "updated_at",
        ]

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name()

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name()


class PIPDetailSerializer(PIPListSerializer):
    class Meta(PIPListSerializer.Meta):
        fields = PIPListSerializer.Meta.fields + [
            "reason", "objectives", "support_provided",
            "success_criteria", "outcome_notes",
            "review_dates", "notes",
        ]


class PIPWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PerformanceImprovementPlan
        fields = [
            "employee", "title", "reason", "objectives",
            "support_provided", "success_criteria",
            "start_date", "end_date", "status",
            "outcome", "outcome_notes", "review_dates", "notes",
        ]


# ---------------------------------------------------------------------------
# Skills Matrix
# ---------------------------------------------------------------------------


class SkillListSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    verified_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Skill
        fields = [
            "id", "employee", "employee_name",
            "name", "category", "proficiency",
            "years_experience", "is_primary", "verified",
            "verified_by", "verified_by_name", "verified_date",
            "created_at", "updated_at",
        ]

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name()

    def get_verified_by_name(self, obj):
        return obj.verified_by.get_full_name() if obj.verified_by_id else None


class SkillDetailSerializer(SkillListSerializer):
    class Meta(SkillListSerializer.Meta):
        fields = SkillListSerializer.Meta.fields + ["notes"]


class SkillWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = [
            "employee", "name", "category", "proficiency",
            "years_experience", "is_primary", "verified",
            "verified_by", "verified_date", "notes",
        ]


# ---------------------------------------------------------------------------
# Certifications
# ---------------------------------------------------------------------------


class CertificationListSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = Certification
        fields = [
            "id", "employee", "employee_name",
            "name", "issuing_body", "credential_id",
            "issue_date", "expiry_date", "status",
            "created_at", "updated_at",
        ]

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name()


class CertificationDetailSerializer(CertificationListSerializer):
    class Meta(CertificationListSerializer.Meta):
        fields = CertificationListSerializer.Meta.fields + [
            "verification_url", "notes",
        ]


class CertificationWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Certification
        fields = [
            "employee", "name", "issuing_body", "credential_id",
            "issue_date", "expiry_date", "status",
            "verification_url", "notes",
        ]


# ---------------------------------------------------------------------------
# Professional Licenses
# ---------------------------------------------------------------------------


class ProfessionalLicenseListSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = ProfessionalLicense
        fields = [
            "id", "employee", "employee_name",
            "license_type", "license_number", "issuing_authority",
            "jurisdiction", "issue_date", "expiry_date",
            "status", "is_mandatory",
            "created_at", "updated_at",
        ]

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name()


class ProfessionalLicenseDetailSerializer(ProfessionalLicenseListSerializer):
    class Meta(ProfessionalLicenseListSerializer.Meta):
        fields = ProfessionalLicenseListSerializer.Meta.fields + ["notes"]


class ProfessionalLicenseWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfessionalLicense
        fields = [
            "employee", "license_type", "license_number",
            "issuing_authority", "jurisdiction",
            "issue_date", "expiry_date", "status",
            "is_mandatory", "notes",
        ]


# ---------------------------------------------------------------------------
# Competency Assessments
# ---------------------------------------------------------------------------


class CompetencyAssessmentListSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    assessor_name = serializers.SerializerMethodField()

    class Meta:
        model = CompetencyAssessment
        fields = [
            "id", "employee", "employee_name",
            "assessor", "assessor_name",
            "competency_area", "assessment_date",
            "score", "max_score", "status",
            "next_assessment_date",
            "created_at", "updated_at",
        ]

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name()

    def get_assessor_name(self, obj):
        return obj.assessor.get_full_name()


class CompetencyAssessmentDetailSerializer(CompetencyAssessmentListSerializer):
    class Meta(CompetencyAssessmentListSerializer.Meta):
        fields = CompetencyAssessmentListSerializer.Meta.fields + [
            "strengths", "gaps", "development_plan", "notes",
        ]


class CompetencyAssessmentWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompetencyAssessment
        fields = [
            "employee", "competency_area", "assessment_date",
            "score", "max_score", "status",
            "strengths", "gaps", "development_plan",
            "next_assessment_date", "notes",
        ]


# ---------------------------------------------------------------------------
# Training Records
# ---------------------------------------------------------------------------


class TrainingRecordListSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = TrainingRecord
        fields = [
            "id", "employee", "employee_name",
            "title", "provider", "delivery_method",
            "start_date", "end_date", "duration_hours",
            "status", "score", "cost", "currency",
            "is_mandatory",
            "created_at", "updated_at",
        ]

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name()


class TrainingRecordDetailSerializer(TrainingRecordListSerializer):
    class Meta(TrainingRecordListSerializer.Meta):
        fields = TrainingRecordListSerializer.Meta.fields + ["notes"]


class TrainingRecordWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingRecord
        fields = [
            "employee", "title", "provider", "delivery_method",
            "start_date", "end_date", "duration_hours",
            "status", "score", "cost", "currency",
            "is_mandatory", "notes",
        ]


# ---------------------------------------------------------------------------
# Training Course
# ---------------------------------------------------------------------------


class TrainingCourseListSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = TrainingCourse
        fields = [
            "id", "title", "code", "provider", "format", "level",
            "duration_hours", "max_participants",
            "cost_per_participant", "currency",
            "is_mandatory", "status",
            "created_by", "created_by_name",
            "created_at", "updated_at",
        ]

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by_id else None


class TrainingCourseDetailSerializer(TrainingCourseListSerializer):
    class Meta(TrainingCourseListSerializer.Meta):
        fields = TrainingCourseListSerializer.Meta.fields + [
            "description", "prerequisites", "learning_objectives", "syllabus",
        ]


class TrainingCourseWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingCourse
        fields = [
            "title", "code", "description", "provider",
            "format", "level", "duration_hours", "max_participants",
            "cost_per_participant", "currency",
            "prerequisites", "learning_objectives", "syllabus",
            "is_mandatory", "status",
        ]


# ---------------------------------------------------------------------------
# Training Plan
# ---------------------------------------------------------------------------


class TrainingPlanListSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True, default=None)
    employee_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = TrainingPlan
        fields = [
            "id", "title", "department", "department_name",
            "employee", "employee_name",
            "start_date", "end_date", "budget", "currency",
            "status", "created_by", "created_by_name",
            "created_at", "updated_at",
        ]

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name() if obj.employee_id else None

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by_id else None


class TrainingPlanDetailSerializer(TrainingPlanListSerializer):
    class Meta(TrainingPlanListSerializer.Meta):
        fields = TrainingPlanListSerializer.Meta.fields + [
            "description", "objectives", "notes",
        ]


class TrainingPlanWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingPlan
        fields = [
            "title", "description", "department", "employee",
            "start_date", "end_date", "budget", "currency",
            "status", "objectives", "notes",
        ]


# ---------------------------------------------------------------------------
# Course Enrollment
# ---------------------------------------------------------------------------


class CourseEnrollmentListSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    course_title = serializers.CharField(source="course.title", read_only=True)
    training_plan_title = serializers.CharField(
        source="training_plan.title", read_only=True, default=None,
    )

    class Meta:
        model = CourseEnrollment
        fields = [
            "id", "employee", "employee_name",
            "course", "course_title",
            "training_plan", "training_plan_title",
            "enrolled_date", "start_date", "completion_date",
            "status", "score", "progress",
            "created_at", "updated_at",
        ]

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name()


class CourseEnrollmentDetailSerializer(CourseEnrollmentListSerializer):
    class Meta(CourseEnrollmentListSerializer.Meta):
        fields = CourseEnrollmentListSerializer.Meta.fields + [
            "feedback", "enrolled_by", "notes",
        ]


class CourseEnrollmentWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseEnrollment
        fields = [
            "employee", "course", "training_plan",
            "start_date", "completion_date",
            "status", "score", "progress",
            "feedback", "notes",
        ]


# ---------------------------------------------------------------------------
# Learning Library
# ---------------------------------------------------------------------------


class LearningResourceListSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = LearningResource
        fields = [
            "id", "title", "resource_type", "category",
            "url", "duration_minutes", "tags",
            "status", "view_count",
            "uploaded_by", "uploaded_by_name",
            "created_at", "updated_at",
        ]

    def get_uploaded_by_name(self, obj):
        return obj.uploaded_by.get_full_name() if obj.uploaded_by_id else None


class LearningResourceDetailSerializer(LearningResourceListSerializer):
    class Meta(LearningResourceListSerializer.Meta):
        fields = LearningResourceListSerializer.Meta.fields + ["description"]


class LearningResourceWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningResource
        fields = [
            "title", "description", "resource_type", "category",
            "url", "duration_minutes", "tags", "status",
        ]


# ---------------------------------------------------------------------------
# Training Completion
# ---------------------------------------------------------------------------


class TrainingCompletionListSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    course_title = serializers.CharField(source="course.title", read_only=True, default=None)
    verified_by_name = serializers.SerializerMethodField()

    class Meta:
        model = TrainingCompletion
        fields = [
            "id", "employee", "employee_name",
            "course", "course_title", "enrollment",
            "completion_date", "result", "score",
            "certificate_number", "certificate_expiry",
            "hours_completed",
            "verified_by", "verified_by_name",
            "created_at", "updated_at",
        ]

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name()

    def get_verified_by_name(self, obj):
        return obj.verified_by.get_full_name() if obj.verified_by_id else None


class TrainingCompletionDetailSerializer(TrainingCompletionListSerializer):
    class Meta(TrainingCompletionListSerializer.Meta):
        fields = TrainingCompletionListSerializer.Meta.fields + ["notes"]


class TrainingCompletionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingCompletion
        fields = [
            "employee", "course", "enrollment",
            "completion_date", "result", "score",
            "certificate_number", "certificate_expiry",
            "hours_completed", "verified_by", "notes",
        ]


# ---------------------------------------------------------------------------
# Certification Expiry Alerts
# ---------------------------------------------------------------------------


class CertificationExpiryAlertListSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = CertificationExpiryAlert
        fields = [
            "id", "employee", "employee_name",
            "alert_type", "reference_name", "reference_id",
            "expiry_date", "alert_date", "days_before_expiry",
            "status", "renewal_date",
            "created_at", "updated_at",
        ]

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name()


class CertificationExpiryAlertDetailSerializer(CertificationExpiryAlertListSerializer):
    class Meta(CertificationExpiryAlertListSerializer.Meta):
        fields = CertificationExpiryAlertListSerializer.Meta.fields + ["notes"]


class CertificationExpiryAlertWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CertificationExpiryAlert
        fields = [
            "employee", "alert_type", "reference_name", "reference_id",
            "expiry_date", "alert_date", "days_before_expiry",
            "status", "renewal_date", "notes",
        ]


# ═══════════════════════════════════════════════════════════════════════════
# 8. Attendance & Leave
# ═══════════════════════════════════════════════════════════════════════════


# ---------------------------------------------------------------------------
# Attendance Log
# ---------------------------------------------------------------------------


class AttendanceLogListSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = AttendanceLog
        fields = [
            "id", "employee", "employee_name",
            "date", "status",
            "clock_in", "clock_out", "break_minutes", "total_hours",
            "location",
            "created_at", "updated_at",
        ]

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name()


class AttendanceLogDetailSerializer(AttendanceLogListSerializer):
    class Meta(AttendanceLogListSerializer.Meta):
        fields = AttendanceLogListSerializer.Meta.fields + ["notes"]


class AttendanceLogWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceLog
        fields = [
            "employee", "date", "status",
            "clock_in", "clock_out", "break_minutes", "total_hours",
            "location", "notes",
        ]


# ---------------------------------------------------------------------------
# Leave Type
# ---------------------------------------------------------------------------


class LeaveTypeListSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = [
            "id", "name", "code", "default_days_per_year",
            "is_paid", "is_carry_over_allowed", "max_carry_over_days",
            "requires_approval", "requires_attachment", "min_days_notice",
            "is_active", "sort_order",
            "created_at", "updated_at",
        ]


class LeaveTypeDetailSerializer(LeaveTypeListSerializer):
    class Meta(LeaveTypeListSerializer.Meta):
        fields = LeaveTypeListSerializer.Meta.fields + ["description"]


class LeaveTypeWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = [
            "name", "code", "description", "default_days_per_year",
            "is_paid", "is_carry_over_allowed", "max_carry_over_days",
            "requires_approval", "requires_attachment", "min_days_notice",
            "is_active", "sort_order",
        ]


# ---------------------------------------------------------------------------
# Leave Request
# ---------------------------------------------------------------------------


class LeaveRequestListSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    reviewed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = LeaveRequest
        fields = [
            "id", "employee", "employee_name",
            "leave_type", "leave_type_name",
            "start_date", "end_date", "total_days", "is_half_day",
            "status",
            "reviewed_by", "reviewed_by_name", "reviewed_at",
            "created_at", "updated_at",
        ]

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name()

    def get_reviewed_by_name(self, obj):
        return obj.reviewed_by.get_full_name() if obj.reviewed_by_id else None


class LeaveRequestDetailSerializer(LeaveRequestListSerializer):
    class Meta(LeaveRequestListSerializer.Meta):
        fields = LeaveRequestListSerializer.Meta.fields + [
            "reason", "reviewer_notes",
        ]


class LeaveRequestWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = [
            "employee", "leave_type",
            "start_date", "end_date", "total_days", "is_half_day",
            "reason", "status",
        ]


# ---------------------------------------------------------------------------
# Leave Balance
# ---------------------------------------------------------------------------


class LeaveBalanceListSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    available_days = serializers.DecimalField(max_digits=5, decimal_places=1, read_only=True)

    class Meta:
        model = LeaveBalance
        fields = [
            "id", "employee", "employee_name",
            "leave_type", "leave_type_name",
            "fiscal_year",
            "entitled_days", "carried_over", "used_days",
            "pending_days", "adjustment", "available_days",
            "created_at", "updated_at",
        ]

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name()


class LeaveBalanceDetailSerializer(LeaveBalanceListSerializer):
    class Meta(LeaveBalanceListSerializer.Meta):
        fields = LeaveBalanceListSerializer.Meta.fields + ["notes"]


class LeaveBalanceWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = [
            "employee", "leave_type", "fiscal_year",
            "entitled_days", "carried_over", "used_days",
            "pending_days", "adjustment", "notes",
        ]


# ---------------------------------------------------------------------------
# Overtime Request
# ---------------------------------------------------------------------------


class OvertimeRequestListSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = OvertimeRequest
        fields = [
            "id", "employee", "employee_name",
            "date", "start_time", "end_time", "total_hours",
            "status",
            "approved_by", "approved_by_name", "approved_at",
            "created_at", "updated_at",
        ]

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name()

    def get_approved_by_name(self, obj):
        return obj.approved_by.get_full_name() if obj.approved_by_id else None


class OvertimeRequestDetailSerializer(OvertimeRequestListSerializer):
    class Meta(OvertimeRequestListSerializer.Meta):
        fields = OvertimeRequestListSerializer.Meta.fields + [
            "reason", "approver_notes",
        ]


class OvertimeRequestWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = OvertimeRequest
        fields = [
            "employee", "date", "start_time", "end_time",
            "total_hours", "reason", "status",
        ]


# ---------------------------------------------------------------------------
# Remote Work Log
# ---------------------------------------------------------------------------


class RemoteWorkLogListSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = RemoteWorkLog
        fields = [
            "id", "employee", "employee_name",
            "date", "status", "location", "work_hours",
            "approved_by", "approved_by_name",
            "created_at", "updated_at",
        ]

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name()

    def get_approved_by_name(self, obj):
        return obj.approved_by.get_full_name() if obj.approved_by_id else None


class RemoteWorkLogDetailSerializer(RemoteWorkLogListSerializer):
    class Meta(RemoteWorkLogListSerializer.Meta):
        fields = RemoteWorkLogListSerializer.Meta.fields + [
            "tasks_completed", "notes",
        ]


class RemoteWorkLogWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = RemoteWorkLog
        fields = [
            "employee", "date", "status", "location",
            "work_hours", "tasks_completed", "notes",
        ]


# ---------------------------------------------------------------------------
# Salary Structure
# ---------------------------------------------------------------------------


class SalaryStructureListSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalaryStructure
        fields = [
            "id", "name", "code", "grade_level",
            "min_salary", "max_salary", "currency",
            "is_active", "created_at", "updated_at",
        ]


class SalaryStructureDetailSerializer(SalaryStructureListSerializer):
    class Meta(SalaryStructureListSerializer.Meta):
        fields = SalaryStructureListSerializer.Meta.fields + [
            "description",
        ]


class SalaryStructureWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalaryStructure
        fields = [
            "name", "code", "grade_level",
            "min_salary", "max_salary", "currency",
            "description", "is_active",
        ]


# ---------------------------------------------------------------------------
# Payroll Run
# ---------------------------------------------------------------------------


class PayrollRunListSerializer(serializers.ModelSerializer):
    processed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = PayrollRun
        fields = [
            "id", "name", "period_start", "period_end", "run_date",
            "status", "total_gross", "total_deductions", "total_net",
            "currency", "processed_by", "processed_by_name",
            "created_at", "updated_at",
        ]

    def get_processed_by_name(self, obj):
        return obj.processed_by.get_full_name() if obj.processed_by_id else None


class PayrollRunDetailSerializer(PayrollRunListSerializer):
    class Meta(PayrollRunListSerializer.Meta):
        fields = PayrollRunListSerializer.Meta.fields + [
            "notes",
        ]


class PayrollRunWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollRun
        fields = [
            "name", "period_start", "period_end", "run_date",
            "status", "total_gross", "total_deductions", "total_net",
            "currency", "notes",
        ]


# ---------------------------------------------------------------------------
# Allowance
# ---------------------------------------------------------------------------


class AllowanceListSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = Allowance
        fields = [
            "id", "employee", "employee_name",
            "allowance_type", "name", "amount", "currency",
            "frequency", "is_taxable", "is_active",
            "created_at", "updated_at",
        ]

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name()


class AllowanceDetailSerializer(AllowanceListSerializer):
    class Meta(AllowanceListSerializer.Meta):
        fields = AllowanceListSerializer.Meta.fields + [
            "start_date", "end_date",
        ]


class AllowanceWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Allowance
        fields = [
            "employee", "allowance_type", "name", "amount", "currency",
            "frequency", "start_date", "end_date",
            "is_taxable", "is_active",
        ]


# ---------------------------------------------------------------------------
# Deduction
# ---------------------------------------------------------------------------


class DeductionListSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = Deduction
        fields = [
            "id", "employee", "employee_name",
            "deduction_type", "name", "amount", "currency",
            "frequency", "is_active",
            "created_at", "updated_at",
        ]

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name()


class DeductionDetailSerializer(DeductionListSerializer):
    class Meta(DeductionListSerializer.Meta):
        fields = DeductionListSerializer.Meta.fields + [
            "start_date", "end_date",
        ]


class DeductionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deduction
        fields = [
            "employee", "deduction_type", "name", "amount", "currency",
            "frequency", "start_date", "end_date", "is_active",
        ]


# ---------------------------------------------------------------------------
# Bonus
# ---------------------------------------------------------------------------


class BonusListSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Bonus
        fields = [
            "id", "employee", "employee_name",
            "bonus_type", "amount", "currency", "date",
            "status", "approved_by", "approved_by_name",
            "created_at", "updated_at",
        ]

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name()

    def get_approved_by_name(self, obj):
        return obj.approved_by.get_full_name() if obj.approved_by_id else None


class BonusDetailSerializer(BonusListSerializer):
    class Meta(BonusListSerializer.Meta):
        fields = BonusListSerializer.Meta.fields + [
            "reason", "approved_at",
        ]


class BonusWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bonus
        fields = [
            "employee", "bonus_type", "amount", "currency",
            "date", "reason", "status",
        ]


# ---------------------------------------------------------------------------
# Payslip
# ---------------------------------------------------------------------------


class PayslipListSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    payroll_run_name = serializers.SerializerMethodField()

    class Meta:
        model = Payslip
        fields = [
            "id", "employee", "employee_name",
            "payroll_run", "payroll_run_name",
            "period_start", "period_end",
            "gross_salary", "net_salary", "currency",
            "status", "created_at", "updated_at",
        ]

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name()

    def get_payroll_run_name(self, obj):
        return obj.payroll_run.name if obj.payroll_run_id else None


class PayslipDetailSerializer(PayslipListSerializer):
    class Meta(PayslipListSerializer.Meta):
        fields = PayslipListSerializer.Meta.fields + [
            "basic_salary", "total_allowances", "total_deductions",
            "generated_at", "sent_at",
        ]


class PayslipWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payslip
        fields = [
            "employee", "payroll_run", "period_start", "period_end",
            "basic_salary", "total_allowances", "total_deductions",
            "gross_salary", "net_salary", "currency", "status",
        ]


# ---------------------------------------------------------------------------
# Tax Record
# ---------------------------------------------------------------------------


class TaxRecordListSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    balance = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = TaxRecord
        fields = [
            "id", "employee", "employee_name",
            "fiscal_year", "tax_type",
            "tax_amount", "tax_paid", "balance", "currency",
            "filing_status", "created_at", "updated_at",
        ]

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name()


class TaxRecordDetailSerializer(TaxRecordListSerializer):
    class Meta(TaxRecordListSerializer.Meta):
        fields = TaxRecordListSerializer.Meta.fields + [
            "taxable_income", "filed_date", "notes",
        ]


class TaxRecordWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxRecord
        fields = [
            "employee", "fiscal_year", "tax_type",
            "taxable_income", "tax_amount", "tax_paid", "currency",
            "filing_status", "filed_date", "notes",
        ]


# ---------------------------------------------------------------------------
# Promotion
# ---------------------------------------------------------------------------


class PromotionListSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Promotion
        fields = [
            "id", "employee", "employee_name",
            "from_position", "to_position",
            "effective_date", "salary_adjustment", "currency",
            "status", "approved_by_name",
            "created_at", "updated_at",
        ]

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name()

    def get_approved_by_name(self, obj):
        return obj.approved_by.get_full_name() if obj.approved_by else None


class PromotionDetailSerializer(PromotionListSerializer):
    class Meta(PromotionListSerializer.Meta):
        fields = PromotionListSerializer.Meta.fields + [
            "from_grade", "to_grade", "new_salary", "reason",
        ]


class PromotionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Promotion
        fields = [
            "employee", "from_position", "to_position",
            "from_grade", "to_grade",
            "effective_date", "salary_adjustment", "new_salary", "currency",
            "reason", "status", "approved_by",
        ]

    @staticmethod
    def _as_decimal(value, default=Decimal("0")) -> Decimal:
        if value is None:
            return default
        if isinstance(value, Decimal):
            return value
        try:
            return Decimal(str(value))
        except Exception:
            return default

    def _resolve_employee_department_id(self, employee: EmployeeRecord | None) -> int | None:
        if employee is None:
            return None

        profile = getattr(getattr(employee, "user", None), "profile", None)
        department_id = getattr(profile, "department_id", None)
        if department_id:
            return department_id

        assignment = (
            PositionAssignment.objects.filter(
                organization_id=employee.organization_id,
                user_id=employee.user_id,
                is_active=True,
                position__department_id__isnull=False,
            )
            .order_by("-is_primary", "-start_date", "-id")
            .select_related("position")
            .first()
        )
        if assignment and assignment.position_id:
            return assignment.position.department_id
        return None

    def validate(self, attrs):
        attrs = super().validate(attrs)

        if self.instance is not None and not any(
            field in attrs
            for field in ("salary_adjustment", "new_salary", "employee", "effective_date")
        ):
            return attrs

        salary_adjustment = attrs.get("salary_adjustment")
        if salary_adjustment is None and self.instance is not None:
            salary_adjustment = self.instance.salary_adjustment
        adjustment_amount = self._as_decimal(salary_adjustment)
        if adjustment_amount <= Decimal("0"):
            return attrs

        employee = attrs.get("employee") or getattr(self.instance, "employee", None)
        department_id = self._resolve_employee_department_id(employee)
        if employee is None or not department_id:
            return attrs

        effective_date = attrs.get("effective_date") or getattr(self.instance, "effective_date", None)
        fiscal_year = effective_date.year if effective_date else None
        budget_health = get_department_budget_health(
            organization_id=employee.organization_id,
            department_id=department_id,
            fiscal_year=fiscal_year,
        )
        merit_pool = budget_health.unallocated if budget_health.unallocated > Decimal("0") else Decimal("0")
        if adjustment_amount <= merit_pool:
            return attrs

        shortfall = adjustment_amount - merit_pool
        raise serializers.ValidationError(
            {
                "non_field_errors": [
                    (
                        "Proposed salary increase exceeds the department's unallocated "
                        "merit pool and requires board-level approval."
                    )
                ],
                "salary_adjustment": [
                    "Requested raise exceeds the available unallocated budget."
                ],
                "requires_board_approval": True,
                "requested_raise": str(adjustment_amount),
                "unallocated_budget": str(merit_pool),
                "budget_shortfall": str(shortfall),
            }
        )


# ---------------------------------------------------------------------------
# Transfer
# ---------------------------------------------------------------------------


class TransferListSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Transfer
        fields = [
            "id", "employee", "employee_name",
            "transfer_type", "from_department", "to_department",
            "effective_date", "status", "approved_by_name",
            "created_at", "updated_at",
        ]

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name()

    def get_approved_by_name(self, obj):
        return obj.approved_by.get_full_name() if obj.approved_by else None


class TransferDetailSerializer(TransferListSerializer):
    class Meta(TransferListSerializer.Meta):
        fields = TransferListSerializer.Meta.fields + [
            "from_location", "to_location", "reason",
        ]


class TransferWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transfer
        fields = [
            "employee", "transfer_type",
            "from_department", "to_department",
            "from_location", "to_location",
            "effective_date", "reason", "status", "approved_by",
        ]


# ---------------------------------------------------------------------------
# Role Change
# ---------------------------------------------------------------------------


class RoleChangeListSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = RoleChange
        fields = [
            "id", "employee", "employee_name",
            "change_type", "from_role", "to_role",
            "effective_date", "status", "approved_by_name",
            "created_at", "updated_at",
        ]

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name()

    def get_approved_by_name(self, obj):
        return obj.approved_by.get_full_name() if obj.approved_by else None


class RoleChangeDetailSerializer(RoleChangeListSerializer):
    class Meta(RoleChangeListSerializer.Meta):
        fields = RoleChangeListSerializer.Meta.fields + ["reason"]


class RoleChangeWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleChange
        fields = [
            "employee", "change_type",
            "from_role", "to_role",
            "effective_date", "reason", "status", "approved_by",
        ]


# ---------------------------------------------------------------------------
# Disciplinary Record
# ---------------------------------------------------------------------------


class DisciplinaryRecordListSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    reported_by_name = serializers.SerializerMethodField()

    class Meta:
        model = DisciplinaryRecord
        fields = [
            "id", "employee", "employee_name",
            "incident_date", "category", "severity",
            "status", "reported_by_name",
            "created_at", "updated_at",
        ]

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name()

    def get_reported_by_name(self, obj):
        return obj.reported_by.get_full_name() if obj.reported_by else None


class DisciplinaryRecordDetailSerializer(DisciplinaryRecordListSerializer):
    class Meta(DisciplinaryRecordListSerializer.Meta):
        fields = DisciplinaryRecordListSerializer.Meta.fields + [
            "description", "action_taken", "follow_up_date",
        ]


class DisciplinaryRecordWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = DisciplinaryRecord
        fields = [
            "employee", "incident_date", "reported_by",
            "category", "severity",
            "description", "action_taken", "follow_up_date", "status",
        ]


# ---------------------------------------------------------------------------
# Exit Management
# ---------------------------------------------------------------------------


class ExitManagementListSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    processed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ExitManagement
        fields = [
            "id", "employee", "employee_name",
            "exit_type", "notice_date", "last_working_day",
            "clearance_status", "final_settlement_status",
            "processed_by_name",
            "created_at", "updated_at",
        ]

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name()

    def get_processed_by_name(self, obj):
        return obj.processed_by.get_full_name() if obj.processed_by else None


class ExitManagementDetailSerializer(ExitManagementListSerializer):
    class Meta(ExitManagementListSerializer.Meta):
        fields = ExitManagementListSerializer.Meta.fields + [
            "reason", "notes",
        ]


class ExitManagementWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExitManagement
        fields = [
            "employee", "exit_type",
            "notice_date", "last_working_day",
            "reason", "clearance_status", "final_settlement_status",
            "processed_by", "notes",
        ]


# ---------------------------------------------------------------------------
# Exit Interview
# ---------------------------------------------------------------------------


class ExitInterviewListSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    interviewer_name = serializers.SerializerMethodField()

    class Meta:
        model = ExitInterview
        fields = [
            "id", "employee", "employee_name",
            "interview_date", "overall_satisfaction",
            "would_recommend", "would_rejoin",
            "interviewer_name",
            "created_at", "updated_at",
        ]

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name()

    def get_interviewer_name(self, obj):
        return obj.interviewer.get_full_name() if obj.interviewer else None


class ExitInterviewDetailSerializer(ExitInterviewListSerializer):
    class Meta(ExitInterviewListSerializer.Meta):
        fields = ExitInterviewListSerializer.Meta.fields + [
            "exit_record", "reason_for_leaving", "feedback",
            "key_concerns", "suggestions",
        ]


class ExitInterviewWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExitInterview
        fields = [
            "employee", "exit_record",
            "interview_date", "interviewer",
            "overall_satisfaction", "reason_for_leaving",
            "feedback", "would_recommend", "would_rejoin",
            "key_concerns", "suggestions",
        ]


# ---------------------------------------------------------------------------
# Headcount Snapshot
# ---------------------------------------------------------------------------


class HeadcountSnapshotListSerializer(serializers.ModelSerializer):
    total_headcount = serializers.IntegerField(read_only=True)

    class Meta:
        model = HeadcountSnapshot
        fields = [
            "id", "snapshot_date", "department", "team",
            "active_count", "inactive_count", "total_headcount",
            "new_hires", "departures", "contractors",
            "created_at", "updated_at",
        ]


class HeadcountSnapshotDetailSerializer(HeadcountSnapshotListSerializer):
    class Meta(HeadcountSnapshotListSerializer.Meta):
        fields = HeadcountSnapshotListSerializer.Meta.fields + ["notes"]


class HeadcountSnapshotWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = HeadcountSnapshot
        fields = [
            "snapshot_date", "department", "team",
            "active_count", "inactive_count",
            "new_hires", "departures", "contractors", "notes",
        ]


# ---------------------------------------------------------------------------
# Turnover Record
# ---------------------------------------------------------------------------


class TurnoverRecordListSerializer(serializers.ModelSerializer):
    total_departures = serializers.IntegerField(read_only=True)
    turnover_rate = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)

    class Meta:
        model = TurnoverRecord
        fields = [
            "id", "period_start", "period_end", "department",
            "starting_headcount", "ending_headcount",
            "voluntary_departures", "involuntary_departures",
            "total_departures", "turnover_rate",
            "created_at", "updated_at",
        ]


class TurnoverRecordDetailSerializer(TurnoverRecordListSerializer):
    class Meta(TurnoverRecordListSerializer.Meta):
        fields = TurnoverRecordListSerializer.Meta.fields + ["notes"]


class TurnoverRecordWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TurnoverRecord
        fields = [
            "period_start", "period_end", "department",
            "starting_headcount", "ending_headcount",
            "voluntary_departures", "involuntary_departures", "notes",
        ]


# ---------------------------------------------------------------------------
# Department Staffing Report
# ---------------------------------------------------------------------------


class DepartmentStaffingReportListSerializer(serializers.ModelSerializer):
    fill_rate = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)

    class Meta:
        model = DepartmentStaffingReport
        fields = [
            "id", "report_date", "department",
            "budgeted_positions", "filled_positions",
            "vacant_positions", "pending_hires", "fill_rate",
            "created_at", "updated_at",
        ]


class DepartmentStaffingReportDetailSerializer(DepartmentStaffingReportListSerializer):
    class Meta(DepartmentStaffingReportListSerializer.Meta):
        fields = DepartmentStaffingReportListSerializer.Meta.fields + ["notes"]


class DepartmentStaffingReportWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = DepartmentStaffingReport
        fields = [
            "report_date", "department",
            "budgeted_positions", "filled_positions",
            "vacant_positions", "pending_hires", "notes",
        ]


# ---------------------------------------------------------------------------
# Hiring Funnel Metric
# ---------------------------------------------------------------------------


class HiringFunnelMetricListSerializer(serializers.ModelSerializer):
    offer_acceptance_rate = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)

    class Meta:
        model = HiringFunnelMetric
        fields = [
            "id", "period_start", "period_end", "department",
            "requisitions_opened", "applications_received",
            "candidates_screened", "candidates_interviewed",
            "offers_made", "offers_accepted", "offer_acceptance_rate",
            "avg_time_to_hire_days", "avg_cost_per_hire", "currency",
            "created_at", "updated_at",
        ]


class HiringFunnelMetricDetailSerializer(HiringFunnelMetricListSerializer):
    class Meta(HiringFunnelMetricListSerializer.Meta):
        fields = HiringFunnelMetricListSerializer.Meta.fields + ["notes"]


class HiringFunnelMetricWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = HiringFunnelMetric
        fields = [
            "period_start", "period_end", "department",
            "requisitions_opened", "applications_received",
            "candidates_screened", "candidates_interviewed",
            "offers_made", "offers_accepted",
            "avg_time_to_hire_days", "avg_cost_per_hire", "currency", "notes",
        ]


# ---------------------------------------------------------------------------
# Workforce Cost Report
# ---------------------------------------------------------------------------


class WorkforceCostReportListSerializer(serializers.ModelSerializer):
    total_cost = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    cost_per_employee = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = WorkforceCostReport
        fields = [
            "id", "period_start", "period_end", "department",
            "total_salary", "total_allowances", "total_bonuses",
            "total_benefits", "total_overtime",
            "total_cost", "headcount", "cost_per_employee", "currency",
            "created_at", "updated_at",
        ]


class WorkforceCostReportDetailSerializer(WorkforceCostReportListSerializer):
    class Meta(WorkforceCostReportListSerializer.Meta):
        fields = WorkforceCostReportListSerializer.Meta.fields + ["notes"]


class WorkforceCostReportWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkforceCostReport
        fields = [
            "period_start", "period_end", "department",
            "total_salary", "total_allowances", "total_bonuses",
            "total_benefits", "total_overtime",
            "headcount", "currency", "notes",
        ]


# ---------------------------------------------------------------------------
# Diversity Metric
# ---------------------------------------------------------------------------


class DiversityMetricListSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiversityMetric
        fields = [
            "id", "snapshot_date", "department",
            "dimension", "category_value",
            "count", "percentage",
            "created_at", "updated_at",
        ]


class DiversityMetricDetailSerializer(DiversityMetricListSerializer):
    class Meta(DiversityMetricListSerializer.Meta):
        fields = DiversityMetricListSerializer.Meta.fields + ["notes"]


class DiversityMetricWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiversityMetric
        fields = [
            "snapshot_date", "department",
            "dimension", "category_value",
            "count", "percentage", "notes",
        ]


# ---------------------------------------------------------------------------
# HR Policy
# ---------------------------------------------------------------------------


class HRPolicyListSerializer(serializers.ModelSerializer):
    class Meta:
        model = HRPolicy
        fields = [
            "id", "title", "category", "status",
            "version", "effective_date", "expiry_date",
            "department", "created_at", "updated_at",
        ]


class HRPolicyDetailSerializer(HRPolicyListSerializer):
    class Meta(HRPolicyListSerializer.Meta):
        fields = HRPolicyListSerializer.Meta.fields + [
            "description", "content", "created_by", "approved_by", "approval_date",
        ]


class HRPolicyWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = HRPolicy
        fields = [
            "title", "category", "status", "version",
            "effective_date", "expiry_date", "description",
            "content", "department", "approved_by", "approval_date",
        ]


# ---------------------------------------------------------------------------
# Employee Handbook Section
# ---------------------------------------------------------------------------


class EmployeeHandbookSectionListSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeHandbookSection
        fields = [
            "id", "handbook_version", "section_number",
            "title", "order", "status",
            "created_at", "updated_at",
        ]


class EmployeeHandbookSectionDetailSerializer(EmployeeHandbookSectionListSerializer):
    class Meta(EmployeeHandbookSectionListSerializer.Meta):
        fields = EmployeeHandbookSectionListSerializer.Meta.fields + [
            "content", "last_updated_by",
        ]


class EmployeeHandbookSectionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeHandbookSection
        fields = [
            "handbook_version", "section_number", "title",
            "content", "order", "status",
        ]


# ---------------------------------------------------------------------------
# Compliance Document
# ---------------------------------------------------------------------------


class ComplianceDocumentListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplianceDocument
        fields = [
            "id", "title", "document_type", "status",
            "reference_number", "issuing_authority",
            "issue_date", "expiry_date", "department",
            "created_at", "updated_at",
        ]


class ComplianceDocumentDetailSerializer(ComplianceDocumentListSerializer):
    class Meta(ComplianceDocumentListSerializer.Meta):
        fields = ComplianceDocumentListSerializer.Meta.fields + ["description"]


class ComplianceDocumentWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplianceDocument
        fields = [
            "title", "document_type", "status",
            "reference_number", "issuing_authority",
            "issue_date", "expiry_date", "description", "department",
        ]


# ---------------------------------------------------------------------------
# Policy Acknowledgement
# ---------------------------------------------------------------------------


class PolicyAcknowledgementListSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    policy_title = serializers.CharField(source="policy.title", read_only=True)

    class Meta:
        model = PolicyAcknowledgement
        fields = [
            "id", "employee", "employee_name",
            "policy", "policy_title",
            "acknowledged", "acknowledged_date",
            "created_at", "updated_at",
        ]

    def get_employee_name(self, obj):
        return obj.employee.get_full_name() or obj.employee.username


class PolicyAcknowledgementDetailSerializer(PolicyAcknowledgementListSerializer):
    class Meta(PolicyAcknowledgementListSerializer.Meta):
        fields = PolicyAcknowledgementListSerializer.Meta.fields + [
            "ip_address", "notes",
        ]


class PolicyAcknowledgementWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PolicyAcknowledgement
        fields = [
            "employee", "policy", "acknowledged",
            "acknowledged_date", "ip_address", "notes",
        ]


# ---------------------------------------------------------------------------
# HR Document Template
# ---------------------------------------------------------------------------


class HRDocumentTemplateListSerializer(serializers.ModelSerializer):
    class Meta:
        model = HRDocumentTemplate
        fields = [
            "id", "title", "category", "version",
            "status", "created_at", "updated_at",
        ]


class HRDocumentTemplateDetailSerializer(HRDocumentTemplateListSerializer):
    class Meta(HRDocumentTemplateListSerializer.Meta):
        fields = HRDocumentTemplateListSerializer.Meta.fields + [
            "description", "content", "created_by",
        ]


class HRDocumentTemplateWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = HRDocumentTemplate
        fields = [
            "title", "category", "description",
            "content", "version", "status",
        ]
