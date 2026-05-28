from calendar import monthrange
from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.utils import timezone
from rest_framework import serializers

from apps.accounts.models import Organization

from .models import (
    DOCUMENT_SIGNATURE_PROVIDER_CHOICES,
    TIER_MODULE_MAP,
    Action,
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
    Module,
    ModuleActivationSettings,
    NotificationChannel,
    NotificationChannelSettings,
    NotificationTemplate,
    PhaseTemplate,
    PlatformEdition,
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
    ScheduledReportDispatch,
    SecuritySettings,
    SlaSeverityLevel,
    SlaSeverityTier,
    StageGateChecklistItem,
    StageGateRule,
    Subsidiary,
    SystemPreferences,
    TaskTemplate,
    TemplateComplianceCheckpoint,
    TemplateMilestone,
    TemplatePhase,
    TemplateRequiredDocument,
)
from .rbac_defaults import PERMISSION_REGISTRY

User = get_user_model()

RBAC_SUB_MODULE_CHOICES = [
    (sub_module["key"], sub_module["label"])
    for module in PERMISSION_REGISTRY
    for sub_module in module["sub_modules"]
]


# ---------------------------------------------------------------------------
# Company Profile
# ---------------------------------------------------------------------------

class CompanyProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "legal_name",
            "trading_name",
            "industry",
            "size",
            "description",
            "registration_number",
            "tax_id",
            "fiscal_year_start_month",
            "email",
            "phone",
            "website",
            "address_line_1",
            "address_line_2",
            "city",
            "state_province",
            "postal_code",
            "country",
            "logo",
            "founded_date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")


# ---------------------------------------------------------------------------
# Subsidiaries
# ---------------------------------------------------------------------------

class SubsidiaryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subsidiary
        fields = [
            "id",
            "name",
            "relationship_type",
            "status",
            "city",
            "country",
            "created_at",
        ]


class SubsidiaryDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subsidiary
        fields = "__all__"
        read_only_fields = ("id", "organization", "created_at", "updated_at")


class SubsidiaryWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subsidiary
        fields = [
            "name",
            "legal_name",
            "registration_number",
            "tax_id",
            "relationship_type",
            "status",
            "address",
            "city",
            "country",
            "contact_email",
            "contact_phone",
            "notes",
        ]


# ---------------------------------------------------------------------------
# Divisions & Departments
# ---------------------------------------------------------------------------

class DepartmentSerializer(serializers.ModelSerializer):
    head_name = serializers.CharField(
        source="head.get_full_name", read_only=True, default=None
    )
    parent_business_unit_id = serializers.IntegerField(source="division_id", read_only=True)
    parent_business_unit_name = serializers.CharField(
        source="division.name", read_only=True, default=None
    )
    parent_business_unit_code = serializers.CharField(
        source="division.code", read_only=True, default=""
    )
    cost_center_id = serializers.SerializerMethodField()
    employee_directory = serializers.SerializerMethodField()
    headcount_summary = serializers.SerializerMethodField()
    skills_matrix = serializers.SerializerMethodField()
    project_allocation = serializers.SerializerMethodField()
    utilization_rate = serializers.SerializerMethodField()
    sop_library = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = [
            "id",
            "name",
            "code",
            "description",
            "head",
            "head_name",
            "parent_business_unit_id",
            "parent_business_unit_name",
            "parent_business_unit_code",
            "cost_center_id",
            "employee_directory",
            "headcount_summary",
            "skills_matrix",
            "project_allocation",
            "utilization_rate",
            "sop_library",
            "is_active",
            "sort_order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")

    def get_cost_center_id(self, obj):
        primary_cost_center = (
            obj.cost_centers.filter(is_active=True).order_by("code").first()
            or obj.cost_centers.order_by("code").first()
        )
        return primary_cost_center.code if primary_cost_center else None

    def _get_talent_snapshot(self, organization_id: int):
        snapshot_cache = getattr(self, "_talent_snapshot_cache", None)
        if snapshot_cache is None:
            snapshot_cache = {}
            self._talent_snapshot_cache = snapshot_cache
        if organization_id in snapshot_cache:
            return snapshot_cache[organization_id]

        from apps.accounts.models import UserProfile
        from apps.hr.models import EmployeeRecord, Position, PositionAssignment, PositionBudget, Skill

        current_year = timezone.localdate().year
        department_ids = set(
            Department.objects.filter(division__organization_id=organization_id).values_list("id", flat=True)
        )
        directory_by_department = defaultdict(dict)
        departments_by_user = defaultdict(set)

        assignment_rows = (
            PositionAssignment.objects.filter(
                organization_id=organization_id,
                is_active=True,
                position__department_id__isnull=False,
                user__employee_record__organization_id=organization_id,
                user__employee_record__employment_status=EmployeeRecord.EmploymentStatus.ACTIVE,
            )
            .order_by("position__department_id", "user_id", "-is_primary", "-start_date", "-id")
            .values(
                "position__department_id",
                "user_id",
                "user__first_name",
                "user__last_name",
                "user__email",
                "user__profile__employee_id",
                "position__title",
                "user__profile__job_title",
            )
        )

        for row in assignment_rows:
            department_id = row["position__department_id"]
            user_id = row["user_id"]
            if not department_id or user_id in directory_by_department[department_id]:
                continue
            full_name = " ".join(
                part for part in [row["user__first_name"], row["user__last_name"]] if part
            ).strip() or row["user__email"]
            directory_by_department[department_id][user_id] = {
                "user_id": user_id,
                "employee_id": row["user__profile__employee_id"] or "",
                "full_name": full_name,
                "job_title": row["position__title"] or row["user__profile__job_title"] or "",
                "email": row["user__email"],
            }
            departments_by_user[user_id].add(department_id)

        profile_rows = (
            UserProfile.objects.filter(
                organization_id=organization_id,
                department_id__isnull=False,
                user__employee_record__organization_id=organization_id,
                user__employee_record__employment_status=EmployeeRecord.EmploymentStatus.ACTIVE,
            )
            .values(
                "department_id",
                "user_id",
                "employee_id",
                "job_title",
                "user__first_name",
                "user__last_name",
                "user__email",
            )
        )

        for row in profile_rows:
            department_id = row["department_id"]
            user_id = row["user_id"]
            if not department_id or user_id in directory_by_department[department_id]:
                continue
            full_name = " ".join(
                part for part in [row["user__first_name"], row["user__last_name"]] if part
            ).strip() or row["user__email"]
            directory_by_department[department_id][user_id] = {
                "user_id": user_id,
                "employee_id": row["employee_id"] or "",
                "full_name": full_name,
                "job_title": row["job_title"] or "",
                "email": row["user__email"],
            }
            departments_by_user[user_id].add(department_id)

        employee_directory = {}
        active_headcount = {}
        for department_id, users in directory_by_department.items():
            people = sorted(
                users.values(),
                key=lambda person: (
                    (person.get("full_name") or "").lower(),
                    (person.get("email") or "").lower(),
                ),
            )
            employee_directory[department_id] = people
            active_headcount[department_id] = len(people)

        approved_budget_rows = PositionBudget.objects.filter(
            organization_id=organization_id,
            fiscal_year=current_year,
            status=PositionBudget.Status.APPROVED,
        ).values("department_id").annotate(total=Sum("approved_headcount"))
        fallback_budget_rows = PositionBudget.objects.filter(
            organization_id=organization_id,
            fiscal_year=current_year,
        ).values("department_id").annotate(total=Sum("approved_headcount"))
        position_budget_rows = Position.objects.filter(
            organization_id=organization_id,
            status=Position.Status.ACTIVE,
        ).values("department_id").annotate(total=Sum("headcount_budget"))

        approved_budget_map = {
            row["department_id"]: int(row["total"] or 0)
            for row in approved_budget_rows
            if row["department_id"]
        }
        fallback_budget_map = {
            row["department_id"]: int(row["total"] or 0)
            for row in fallback_budget_rows
            if row["department_id"]
        }
        position_budget_map = {
            row["department_id"]: int(row["total"] or 0)
            for row in position_budget_rows
            if row["department_id"]
        }

        approved_headcount = {}
        all_department_ids = set(active_headcount.keys()) | set(approved_budget_map.keys()) | set(
            fallback_budget_map.keys()
        ) | set(position_budget_map.keys())
        for department_id in all_department_ids:
            if department_id in approved_budget_map:
                approved_headcount[department_id] = approved_budget_map[department_id]
            elif department_id in fallback_budget_map:
                approved_headcount[department_id] = fallback_budget_map[department_id]
            else:
                approved_headcount[department_id] = position_budget_map.get(department_id, 0)

        skills_matrix = {}
        all_user_ids = list(departments_by_user.keys())
        if all_user_ids:
            skill_rows = Skill.objects.filter(
                organization_id=organization_id,
                employee__organization_id=organization_id,
                employee__employment_status=EmployeeRecord.EmploymentStatus.ACTIVE,
                employee__user_id__in=all_user_ids,
            ).values("employee__user_id", "name")

            skill_users_by_department = defaultdict(lambda: defaultdict(set))
            for row in skill_rows:
                skill_name = (row["name"] or "").strip()
                user_id = row["employee__user_id"]
                if not skill_name or not user_id:
                    continue
                for department_id in departments_by_user.get(user_id, ()):
                    skill_users_by_department[department_id][skill_name].add(user_id)

            for department_id, skill_map in skill_users_by_department.items():
                ranked_skills = sorted(
                    skill_map.items(),
                    key=lambda item: (-len(item[1]), item[0].lower()),
                )
                summary_rows = []
                for skill_name, users in ranked_skills[:5]:
                    count = len(users)
                    summary_rows.append(
                        {
                            "skill_name": skill_name,
                            "employee_count": count,
                            "summary": (
                                f"{count} staff member with {skill_name}"
                                if count == 1
                                else f"{count} staff with {skill_name}"
                            ),
                        }
                    )
                skills_matrix[department_id] = summary_rows

        project_allocation = {}
        utilization_rate = {}
        department_logged_hours = defaultdict(Decimal)
        if all_user_ids:
            from apps.projects.models import Project, ProjectTask

            active_project_statuses = [
                Project.Status.PLANNING,
                Project.Status.IN_PROGRESS,
                Project.Status.ON_HOLD,
            ]
            task_rows = ProjectTask.objects.filter(
                organization_id=organization_id,
                assigned_user_id__in=all_user_ids,
                phase__project__organization_id=organization_id,
                phase__project__status__in=active_project_statuses,
            ).values(
                "assigned_user_id",
                "status",
                "estimated_effort_hours",
                "phase__project_id",
                "phase__project__name",
                "phase__project__status",
            )

            project_map_by_department = defaultdict(dict)
            logged_statuses = {
                ProjectTask.Status.IN_PROGRESS,
                ProjectTask.Status.COMPLETED,
            }

            for row in task_rows:
                user_id = row.get("assigned_user_id")
                project_id = row.get("phase__project_id")
                if not user_id or not project_id:
                    continue
                estimated_effort = Decimal(row.get("estimated_effort_hours") or 0)
                for department_id in departments_by_user.get(user_id, ()):
                    department_projects = project_map_by_department[department_id]
                    project_stats = department_projects.get(project_id)
                    if project_stats is None:
                        project_stats = {
                            "project_id": project_id,
                            "project_name": row.get("phase__project__name") or f"Project {project_id}",
                            "project_status": row.get("phase__project__status") or "",
                            "task_count": 0,
                            "open_task_count": 0,
                            "logged_hours": Decimal("0.0"),
                        }
                        department_projects[project_id] = project_stats

                    project_stats["task_count"] += 1
                    if row.get("status") != ProjectTask.Status.COMPLETED:
                        project_stats["open_task_count"] += 1

                    if row.get("status") in logged_statuses and estimated_effort > 0:
                        project_stats["logged_hours"] += estimated_effort
                        department_logged_hours[department_id] += estimated_effort

            for department_id, projects in project_map_by_department.items():
                ranked_projects = sorted(
                    projects.values(),
                    key=lambda item: ((item.get("project_name") or "").lower(), item.get("project_id") or 0),
                )
                project_allocation[department_id] = [
                    {
                        "project_id": item["project_id"],
                        "project_name": item["project_name"],
                        "project_status": item["project_status"],
                        "task_count": item["task_count"],
                        "open_task_count": item["open_task_count"],
                        "logged_hours": round(float(item["logged_hours"]), 1),
                    }
                    for item in ranked_projects
                ]

        today = timezone.localdate()
        business_days_in_month = sum(
            1
            for day in range(1, monthrange(today.year, today.month)[1] + 1)
            if date(today.year, today.month, day).weekday() < 5
        )
        monthly_staff_capacity_hours = Decimal(str(business_days_in_month * 8))

        for department_id in department_ids:
            staff_count = int(active_headcount.get(department_id, 0))
            available_hours = Decimal(staff_count) * monthly_staff_capacity_hours
            logged_hours = department_logged_hours.get(department_id, Decimal("0.0"))
            utilization_percent = (
                round(float((logged_hours / available_hours) * Decimal("100")), 2)
                if available_hours > 0
                else 0.0
            )
            utilization_rate[department_id] = {
                "percent": utilization_percent,
                "hours_logged": round(float(logged_hours), 1),
                "available_hours": round(float(available_hours), 1),
                "staff_count": staff_count,
                "period_label": today.strftime("%B %Y"),
                "formula": "Total project-task effort hours / Total available staff hours",
            }

        sop_library = {}
        from apps.documents.models import Document

        if department_ids:
            document_rows = Document.objects.filter(
                organization_id=organization_id,
                business_unit_department_id__in=department_ids,
            ).exclude(
                status=Document.Status.ARCHIVED
            ).values(
                "id",
                "business_unit_department_id",
                "title",
                "document_number",
                "status",
                "document_type__name",
                "document_type__code",
                "project_id",
                "project__name",
                "created_at",
            )

            sop_keywords = (
                "sop",
                "standard operating procedure",
                "procedure",
                "checklist",
                "work instruction",
            )

            def _is_sop_document(row):
                haystack = " ".join(
                    [
                        str(row.get("title") or ""),
                        str(row.get("document_type__name") or ""),
                        str(row.get("document_type__code") or ""),
                    ]
                ).lower()
                return any(keyword in haystack for keyword in sop_keywords)

            library_by_department = defaultdict(list)
            department_document_count = defaultdict(int)
            department_sop_count = defaultdict(int)

            for row in document_rows:
                department_id = row.get("business_unit_department_id")
                if not department_id:
                    continue
                is_sop = _is_sop_document(row)
                department_document_count[department_id] += 1
                if is_sop:
                    department_sop_count[department_id] += 1
                library_by_department[department_id].append(
                    {
                        "id": row["id"],
                        "title": row.get("title") or "Untitled document",
                        "document_number": row.get("document_number") or "",
                        "status": row.get("status") or "",
                        "document_type_name": row.get("document_type__name") or "",
                        "project_id": row.get("project_id"),
                        "project_name": row.get("project__name"),
                        "is_sop": is_sop,
                        "_created_at": row.get("created_at"),
                    }
                )

            for department_id in department_ids:
                entries = library_by_department.get(department_id, [])
                ranked_entries = sorted(
                    entries,
                    key=lambda item: (
                        item.get("is_sop", False),
                        item.get("_created_at") or timezone.now(),
                    ),
                    reverse=True,
                )
                documents = []
                for entry in ranked_entries[:8]:
                    created_at = entry.pop("_created_at", None)
                    entry["created_at"] = created_at.isoformat() if created_at else None
                    documents.append(entry)

                sop_library[department_id] = {
                    "document_count": department_document_count.get(department_id, 0),
                    "sop_count": department_sop_count.get(department_id, 0),
                    "documents": documents,
                }

        snapshot = {
            "employee_directory": employee_directory,
            "active_headcount": active_headcount,
            "approved_headcount": approved_headcount,
            "skills_matrix": skills_matrix,
            "project_allocation": project_allocation,
            "utilization_rate": utilization_rate,
            "sop_library": sop_library,
        }
        snapshot_cache[organization_id] = snapshot
        return snapshot

    def get_employee_directory(self, obj):
        snapshot = self._get_talent_snapshot(obj.division.organization_id)
        return snapshot["employee_directory"].get(obj.id, [])

    def get_headcount_summary(self, obj):
        snapshot = self._get_talent_snapshot(obj.division.organization_id)
        active_employees = snapshot["active_headcount"].get(obj.id, 0)
        approved_roles = snapshot["approved_headcount"].get(obj.id, 0)
        return {
            "active_employees": active_employees,
            "approved_roles": approved_roles,
            "filled_vs_approved": f"{active_employees}/{approved_roles}",
            "vacant_roles": max(approved_roles - active_employees, 0),
        }

    def get_skills_matrix(self, obj):
        snapshot = self._get_talent_snapshot(obj.division.organization_id)
        return snapshot["skills_matrix"].get(obj.id, [])

    def get_project_allocation(self, obj):
        snapshot = self._get_talent_snapshot(obj.division.organization_id)
        return snapshot["project_allocation"].get(obj.id, [])

    def get_utilization_rate(self, obj):
        snapshot = self._get_talent_snapshot(obj.division.organization_id)
        return snapshot["utilization_rate"].get(
            obj.id,
            {
                "percent": 0.0,
                "hours_logged": 0.0,
                "available_hours": 0.0,
                "staff_count": 0,
                "period_label": timezone.localdate().strftime("%B %Y"),
                "formula": "Total project-task effort hours / Total available staff hours",
            },
        )

    def get_sop_library(self, obj):
        snapshot = self._get_talent_snapshot(obj.division.organization_id)
        return snapshot["sop_library"].get(
            obj.id,
            {
                "document_count": 0,
                "sop_count": 0,
                "documents": [],
            },
        )


class DepartmentWriteSerializer(serializers.ModelSerializer):
    cost_center_id = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=False,
        max_length=20,
        trim_whitespace=True,
    )

    class Meta:
        model = Department
        fields = [
            "name",
            "code",
            "description",
            "head",
            "cost_center_id",
            "is_active",
            "sort_order",
        ]

    def validate_cost_center_id(self, value):
        return value.strip().upper()

    def _resolve_division(self):
        if self.instance is not None:
            return self.instance.division

        view = self.context.get("view")
        division_pk = (
            str(view.kwargs.get("division_pk")) if view and getattr(view, "kwargs", None) else ""
        )
        if not division_pk:
            return None

        return Division.objects.select_related("organization").filter(pk=division_pk).first()

    def validate(self, attrs):
        cost_center_code = attrs.get("cost_center_id")
        has_existing_cost_center = self.instance is not None and self.instance.cost_centers.exists()

        if self.instance is None and not cost_center_code:
            raise serializers.ValidationError(
                {"cost_center_id": "Cost Center ID is required for accounting sync."}
            )
        if self.instance is not None and not cost_center_code and not has_existing_cost_center:
            raise serializers.ValidationError(
                {"cost_center_id": "Cost Center ID is required for accounting sync."}
            )

        division = self._resolve_division()
        if cost_center_code and division is not None:
            existing = CostCenter.objects.filter(
                organization=division.organization,
                code=cost_center_code,
            ).first()
            current_department_id = self.instance.id if self.instance is not None else None
            if existing and existing.department_id not in (None, current_department_id):
                raise serializers.ValidationError(
                    {"cost_center_id": "This Cost Center ID is already assigned to another department."}
                )

        return attrs

    def _sync_department_cost_center(self, *, department: Department, cost_center_code: str):
        if not cost_center_code:
            return

        organization = department.division.organization
        cost_center = CostCenter.objects.filter(
            organization=organization,
            code=cost_center_code,
        ).first()

        if cost_center is None:
            CostCenter.objects.create(
                organization=organization,
                code=cost_center_code,
                name=f"{department.name} Cost Center",
                department=department,
                is_active=True,
            )
            return

        update_fields = []
        if cost_center.department_id != department.id:
            cost_center.department = department
            update_fields.append("department")
        if not cost_center.is_active:
            cost_center.is_active = True
            update_fields.append("is_active")
        if update_fields:
            cost_center.save(update_fields=update_fields)

    def create(self, validated_data):
        cost_center_code = validated_data.pop("cost_center_id", "").strip().upper()
        department = super().create(validated_data)
        self._sync_department_cost_center(
            department=department,
            cost_center_code=cost_center_code,
        )
        return department

    def update(self, instance, validated_data):
        cost_center_code = validated_data.pop("cost_center_id", "").strip().upper()
        department = super().update(instance, validated_data)
        if cost_center_code:
            self._sync_department_cost_center(
                department=department,
                cost_center_code=cost_center_code,
            )
        return department


class DivisionListSerializer(serializers.ModelSerializer):
    department_count = serializers.IntegerField(read_only=True)
    head_name = serializers.CharField(
        source="head.get_full_name", read_only=True, default=None
    )
    unit_category_display = serializers.CharField(
        source="get_unit_category_display", read_only=True
    )
    total_headcount = serializers.SerializerMethodField()
    operating_budget = serializers.SerializerMethodField()

    class Meta:
        model = Division
        fields = [
            "id",
            "name",
            "code",
            "head",
            "head_name",
            "unit_category",
            "unit_category_display",
            "location_region",
            "is_active",
            "department_count",
            "total_headcount",
            "operating_budget",
            "sort_order",
            "created_at",
        ]

    def get_total_headcount(self, obj):
        from apps.hr.models import EmployeeRecord, PositionAssignment

        return (
            PositionAssignment.objects.filter(
                organization=obj.organization,
                is_active=True,
                position__department__division=obj,
                user__employee_record__organization=obj.organization,
                user__employee_record__employment_status=EmployeeRecord.EmploymentStatus.ACTIVE,
            )
            .values("user_id")
            .distinct()
            .count()
        )

    def get_operating_budget(self, obj):
        from apps.finance.models import AccountSubType, AccountType, Budget, BudgetLineItem

        current_year = timezone.localdate().year
        total = (
            BudgetLineItem.objects.filter(
                budget__organization=obj.organization,
                budget__period_type=Budget.PeriodType.ANNUAL,
                budget__status=Budget.Status.ACTIVE,
                budget__start_date__year=current_year,
                department__division=obj,
                account__account_type=AccountType.EXPENSE,
                account__sub_type=AccountSubType.OPERATING_EXPENSE,
            ).aggregate(total=Sum("budgeted_amount"))["total"]
            or 0
        )
        return str(total)


class DivisionDetailSerializer(serializers.ModelSerializer):
    departments = DepartmentSerializer(many=True, read_only=True)
    head_name = serializers.CharField(
        source="head.get_full_name", read_only=True, default=None
    )
    unit_category_display = serializers.CharField(
        source="get_unit_category_display", read_only=True
    )
    total_headcount = serializers.SerializerMethodField()
    operating_budget = serializers.SerializerMethodField()

    class Meta:
        model = Division
        fields = [
            "id",
            "name",
            "code",
            "description",
            "head",
            "head_name",
            "unit_category",
            "unit_category_display",
            "location_region",
            "is_active",
            "sort_order",
            "total_headcount",
            "operating_budget",
            "departments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")

    def get_total_headcount(self, obj):
        return DivisionListSerializer.get_total_headcount(self, obj)

    def get_operating_budget(self, obj):
        return DivisionListSerializer.get_operating_budget(self, obj)


class DivisionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Division
        fields = [
            "name",
            "code",
            "description",
            "head",
            "unit_category",
            "location_region",
            "is_active",
            "sort_order",
        ]


# ---------------------------------------------------------------------------
# Cost Centers
# ---------------------------------------------------------------------------

class CostCenterSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(
        source="department.name", read_only=True, default=None
    )

    class Meta:
        model = CostCenter
        fields = [
            "id",
            "code",
            "name",
            "department",
            "department_name",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")


class CostCenterWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CostCenter
        fields = ["code", "name", "department", "is_active"]


# ---------------------------------------------------------------------------
# Profit Centers
# ---------------------------------------------------------------------------

class ProfitCenterSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(
        source="department.name", read_only=True, default=None
    )

    class Meta:
        model = ProfitCenter
        fields = [
            "id",
            "code",
            "name",
            "department",
            "department_name",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")


class ProfitCenterWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfitCenter
        fields = ["code", "name", "department", "is_active"]


# ---------------------------------------------------------------------------
# Roles & Permissions
# ---------------------------------------------------------------------------

class RolePermissionSerializer(serializers.ModelSerializer):
    permission_key = serializers.CharField(source="permission.key", read_only=True)

    class Meta:
        model = RolePermission
        fields = ["id", "permission", "permission_key", "module", "sub_module", "action"]


class RoleListSerializer(serializers.ModelSerializer):
    user_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Role
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "is_system",
            "user_count",
            "created_at",
        ]


class RoleDetailSerializer(serializers.ModelSerializer):
    permissions = RolePermissionSerializer(many=True, read_only=True)
    user_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Role
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "is_system",
            "permissions",
            "user_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "slug", "is_system", "created_at", "updated_at")


class RoleWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["name", "description"]

    def create(self, validated_data):
        from django.utils.text import slugify

        validated_data["slug"] = slugify(validated_data["name"])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        from django.utils.text import slugify

        if "name" in validated_data:
            validated_data["slug"] = slugify(validated_data["name"])
        return super().update(instance, validated_data)


class PermissionBulkItemSerializer(serializers.Serializer):
    sub_module = serializers.ChoiceField(choices=RBAC_SUB_MODULE_CHOICES)
    action = serializers.ChoiceField(choices=Action.choices)
    granted = serializers.BooleanField()


class PermissionMatrixUpdateSerializer(serializers.Serializer):
    permissions = PermissionBulkItemSerializer(many=True)


# ---------------------------------------------------------------------------
# Security Settings
# ---------------------------------------------------------------------------

class SecuritySettingsSerializer(serializers.ModelSerializer):
    encryption_at_rest = serializers.SerializerMethodField()
    encryption_in_transit = serializers.SerializerMethodField()

    class Meta:
        model = SecuritySettings
        fields = [
            "id",
            # Authentication
            "mfa_enforced",
            "password_min_length",
            "password_require_uppercase",
            "password_require_lowercase",
            "password_require_digits",
            "password_require_special",
            "session_timeout_minutes",
            # Encryption (read-only, computed)
            "encryption_at_rest",
            "encryption_in_transit",
            # IP Restrictions
            "ip_restriction_enabled",
            "whitelisted_cidrs",
            "geo_blocking_enabled",
            "blocked_countries",
            # Metadata
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")

    def get_encryption_at_rest(self, obj):
        from django.conf import settings as django_settings
        db_conf = django_settings.DATABASES.get("default", {})
        ssl_opts = db_conf.get("OPTIONS", {}).get("sslmode")
        return ssl_opts in ("verify-full", "verify-ca", "require")

    def get_encryption_in_transit(self, obj):
        from django.conf import settings as django_settings
        return getattr(django_settings, "SECURE_SSL_REDIRECT", False)

    def validate_password_min_length(self, value):
        if value < 6 or value > 128:
            raise serializers.ValidationError("Must be between 6 and 128.")
        return value

    def validate_session_timeout_minutes(self, value):
        if value < 5 or value > 1440:
            raise serializers.ValidationError("Must be between 5 and 1440 minutes.")
        return value

    def validate_whitelisted_cidrs(self, value):
        import ipaddress
        validated = []
        for entry in value:
            try:
                network = ipaddress.ip_network(entry, strict=False)
                validated.append(str(network))
            except ValueError:
                raise serializers.ValidationError(f"Invalid CIDR notation: {entry}")
        return validated

    def validate_blocked_countries(self, value):
        import re
        validated = []
        for code in value:
            code = code.strip().upper()
            if not re.match(r"^[A-Z]{2}$", code):
                raise serializers.ValidationError(
                    f"Invalid country code: {code}. Use 2-letter ISO codes."
                )
            validated.append(code)
        return validated


# ---------------------------------------------------------------------------
# System Preferences
# ---------------------------------------------------------------------------

class SystemPreferencesSerializer(serializers.ModelSerializer):
    available_roles = serializers.SerializerMethodField()
    available_landing_pages = serializers.SerializerMethodField()
    available_currencies = serializers.SerializerMethodField()

    class Meta:
        model = SystemPreferences
        fields = [
            "id",
            # Dashboard
            "dashboard_by_role",
            "available_roles",
            "available_landing_pages",
            "available_currencies",
            # Theme
            "theme_mode",
            "accent_color",
            # Localization
            "date_format",
            "number_format",
            "measurement_unit",
            # Currency
            "default_currency",
            "currency_position",
            "currency_decimal_places",
            # Metadata
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")

    def get_available_roles(self, obj):
        roles = Role.objects.filter(organization=obj.organization).values("slug", "name")
        return list(roles)

    def get_available_landing_pages(self, obj):
        return [
            {"value": path, "label": label}
            for path, label in SystemPreferences.LANDING_PAGE_CHOICES
        ]

    def get_available_currencies(self, obj):
        rows = (
            MasterDataEntry.objects.filter(category="currency", is_active=True)
            .order_by("sort_order", "label")
            .values("code", "label")
        )
        return [
            {"code": str(row["code"]).strip().upper(), "label": row["label"]}
            for row in rows
            if str(row["code"]).strip()
        ]

    def validate_dashboard_by_role(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Must be a JSON object mapping role slugs to landing pages.")
        valid_pages = {p for p, _ in SystemPreferences.LANDING_PAGE_CHOICES}
        for slug, page in value.items():
            if page not in valid_pages:
                raise serializers.ValidationError(
                    f"Invalid landing page '{page}' for role '{slug}'."
                )
        return value

    def validate_accent_color(self, value):
        import re
        if not re.match(r"^#[0-9A-Fa-f]{6}$", value):
            raise serializers.ValidationError("Must be a valid hex color (e.g. #171717).")
        return value

    def validate_default_currency(self, value):
        import re

        code = str(value).strip().upper()
        if not re.match(r"^[A-Z]{3}$", code):
            raise serializers.ValidationError("Must be a valid 3-letter ISO currency code.")

        valid = {
            str(item).strip().upper()
            for item in MasterDataEntry.objects.filter(
                category="currency", is_active=True
            ).values_list("code", flat=True)
            if str(item).strip()
        }
        if valid and code not in valid:
            raise serializers.ValidationError(
                f"Must be one of: {', '.join(sorted(valid))}."
            )
        return code

    def validate_currency_decimal_places(self, value):
        if value < 0 or value > 4:
            raise serializers.ValidationError("Must be between 0 and 4.")
        return value


# ---------------------------------------------------------------------------
# Audit & Compliance Settings
# ---------------------------------------------------------------------------

class AuditComplianceSettingsSerializer(serializers.ModelSerializer):
    audit_status = serializers.SerializerMethodField()

    class Meta:
        model = AuditComplianceSettings
        fields = [
            "id",
            # Audit Logging
            "audit_logging_enabled",
            "audit_retention_days",
            "audit_status",
            # Compliance Controls
            "mandatory_fields_enforced",
            "financial_period_locking",
            "locked_before_date",
            "change_approval_required",
            # Data Access
            "access_log_retention_days",
            # Metadata
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")

    def get_audit_status(self, obj):
        from auditlog.models import LogEntry
        from auditlog.registry import auditlog

        return {
            "models_tracked": len(auditlog.get_models()),
            "middleware_active": True,
            "total_log_entries": LogEntry.objects.count(),
        }

    def validate_audit_retention_days(self, value):
        if value < 30 or value > 2555:
            raise serializers.ValidationError("Must be between 30 and 2,555 days (7 years).")
        return value

    def validate_access_log_retention_days(self, value):
        if value < 7 or value > 365:
            raise serializers.ValidationError("Must be between 7 and 365 days.")
        return value

    def validate_locked_before_date(self, value):
        if value:
            from django.utils import timezone
            if value > timezone.now().date():
                raise serializers.ValidationError("Lock date must be in the past.")
        return value


class AuditLogEntrySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    timestamp = serializers.DateTimeField()
    actor_email = serializers.SerializerMethodField()
    actor_role = serializers.SerializerMethodField()
    action_display = serializers.SerializerMethodField()
    object_repr = serializers.CharField()
    content_type_name = serializers.SerializerMethodField()
    ip_address = serializers.SerializerMethodField()
    changes = serializers.JSONField()

    def get_actor_email(self, obj):
        return obj.actor.email if obj.actor else "System"

    def get_actor_role(self, obj):
        if not obj.actor:
            return "System"
        profile = getattr(obj.actor, "profile", None)
        assigned_role = getattr(profile, "assigned_role", None)
        if assigned_role:
            return assigned_role.name
        role = getattr(profile, "role", None)
        if role == "admin":
            return "Organization Admin"
        return str(role).replace("_", " ").title() if role else "User"

    def get_action_display(self, obj):
        return {0: "Create", 1: "Update", 2: "Delete"}.get(obj.action, "Unknown")

    def get_content_type_name(self, obj):
        if not obj.content_type:
            return "Unknown"
        model_class = obj.content_type.model_class()
        if model_class:
            return model_class.__name__
        return obj.content_type.model or "Unknown"

    def get_ip_address(self, obj):
        ip = getattr(obj, "remote_addr", None)
        if ip:
            return str(ip)
        additional_data = getattr(obj, "additional_data", None) or {}
        if isinstance(additional_data, dict):
            addr = additional_data.get("remote_addr")
            return str(addr) if addr else None
        return None


# ---------------------------------------------------------------------------
# Notification & SLA Settings
# ---------------------------------------------------------------------------


class NotificationChannelSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationChannelSettings
        fields = [
            "id",
            "email_enabled",
            "in_app_enabled",
            "sms_enabled",
            "push_enabled",
            "category_overrides",
            "muted_event_keys",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")


class SlaSeverityTierSerializer(serializers.ModelSerializer):
    level_display = serializers.CharField(source="get_level_display", read_only=True)

    class Meta:
        model = SlaSeverityTier
        fields = [
            "id",
            "level",
            "level_display",
            "sort_order",
            "response_time_hours",
            "escalation_path",
            "notification_channels",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_response_time_hours(self, value):
        if value < 1 or value > 720:
            raise serializers.ValidationError("Must be between 1 and 720 hours.")
        return value

    def validate_escalation_path(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Escalation path must be a list.")
        for entry in value:
            if not isinstance(entry, str) or not entry.strip():
                raise serializers.ValidationError("Each escalation path entry must be a non-empty string.")
        return [entry.strip() for entry in value]

    def validate_notification_channels(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Notification channels must be a list.")
        valid_channels = {choice[0] for choice in NotificationChannel.choices}
        normalized: list[str] = []
        for channel in value:
            if channel not in valid_channels:
                raise serializers.ValidationError(
                    f"Invalid channel '{channel}'. Valid channels: {', '.join(sorted(valid_channels))}."
                )
            if channel not in normalized:
                normalized.append(channel)
        return normalized

    def validate_level(self, value):
        valid_levels = {choice[0] for choice in SlaSeverityLevel.choices}
        if value not in valid_levels:
            raise serializers.ValidationError(
                f"Invalid SLA level. Expected one of: {', '.join(sorted(valid_levels))}."
            )
        return value


class NotificationTemplateListSerializer(serializers.ModelSerializer):
    channel_display = serializers.CharField(source="get_channel_display", read_only=True)
    severity_tier_display = serializers.CharField(
        source="get_severity_tier_display", read_only=True
    )

    class Meta:
        model = NotificationTemplate
        fields = [
            "id",
            "code",
            "name",
            "description",
            "channel",
            "channel_display",
            "event_key",
            "severity_tier",
            "severity_tier_display",
            "subject",
            "is_active",
            "is_system",
            "updated_at",
            "created_at",
        ]


class NotificationTemplateDetailSerializer(serializers.ModelSerializer):
    channel_display = serializers.CharField(source="get_channel_display", read_only=True)
    severity_tier_display = serializers.CharField(
        source="get_severity_tier_display", read_only=True
    )

    class Meta:
        model = NotificationTemplate
        fields = [
            "id",
            "code",
            "name",
            "description",
            "channel",
            "channel_display",
            "event_key",
            "severity_tier",
            "severity_tier_display",
            "subject",
            "body_text",
            "body_html",
            "variables",
            "is_active",
            "is_system",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "is_system", "created_at", "updated_at")


class NotificationTemplateWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationTemplate
        fields = [
            "code",
            "name",
            "description",
            "channel",
            "event_key",
            "severity_tier",
            "subject",
            "body_text",
            "body_html",
            "variables",
            "is_active",
        ]

    def validate_variables(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Variables must be a list of placeholder keys.")
        cleaned: list[str] = []
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise serializers.ValidationError("Each variable must be a non-empty string.")
            cleaned.append(item.strip())
        return cleaned

    def validate_event_key(self, value):
        normalized = value.strip().lower().replace(" ", "_")
        if not normalized:
            raise serializers.ValidationError("Event key is required.")
        return normalized

    def validate_code(self, value):
        if not value:
            return ""
        return value.strip().lower().replace(" ", "_")

    def validate(self, data):
        channel = data.get("channel", getattr(self.instance, "channel", None))
        subject = data.get("subject", getattr(self.instance, "subject", ""))
        if channel == NotificationChannel.EMAIL and not subject.strip():
            raise serializers.ValidationError({"subject": "Email templates require a subject."})
        return data


class NotificationWorkflowCatalogItemSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    module = serializers.CharField()
    description = serializers.CharField()
    default_channels = serializers.ListField(
        child=serializers.CharField(),
        default=list,
    )
    variables = serializers.ListField(
        child=serializers.CharField(),
        default=list,
    )
    default_severity_tier = serializers.CharField(default=SlaSeverityLevel.REVIEW)
    template_count = serializers.IntegerField(default=0)
    active_template_count = serializers.IntegerField(default=0)
    configured_channels = serializers.ListField(
        child=serializers.CharField(),
        default=list,
    )
    active_channels = serializers.ListField(
        child=serializers.CharField(),
        default=list,
    )


class NotificationWorkflowCatalogSerializer(serializers.Serializer):
    events = NotificationWorkflowCatalogItemSerializer(many=True)


# ---------------------------------------------------------------------------
# Document Automation Settings
# ---------------------------------------------------------------------------


class DocumentAutomationSettingsSerializer(serializers.ModelSerializer):
    default_generation_owner_role_name = serializers.CharField(
        source="default_generation_owner_role.name",
        read_only=True,
        default=None,
    )
    default_generation_phase_name = serializers.CharField(
        source="default_generation_phase.name",
        read_only=True,
        default=None,
    )
    default_generation_retention_policy_name = serializers.CharField(
        source="default_generation_retention_policy.name",
        read_only=True,
        default=None,
    )

    class Meta:
        model = DocumentAutomationSettings
        fields = [
            "id",
            "default_signature_provider",
            "enabled_signature_providers",
            "default_generation_owner_role",
            "default_generation_owner_role_name",
            "default_generation_phase",
            "default_generation_phase_name",
            "default_generation_retention_policy",
            "default_generation_retention_policy_name",
            "default_generation_confidentiality_level",
            "default_generation_template_code",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_enabled_signature_providers(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Enabled providers must be a list.")
        allowed = {choice[0] for choice in DOCUMENT_SIGNATURE_PROVIDER_CHOICES}
        normalized: list[str] = []
        for provider in value:
            if provider not in allowed:
                raise serializers.ValidationError(
                    f"Unsupported provider '{provider}'. Allowed: {', '.join(sorted(allowed))}."
                )
            if provider not in normalized:
                normalized.append(provider)
        if not normalized:
            raise serializers.ValidationError("At least one signature provider must be enabled.")
        return normalized

    def validate(self, attrs):
        enabled = attrs.get(
            "enabled_signature_providers",
            getattr(self.instance, "enabled_signature_providers", []),
        )
        default_provider = attrs.get(
            "default_signature_provider",
            getattr(self.instance, "default_signature_provider", None),
        )
        if default_provider and default_provider not in set(enabled or []):
            raise serializers.ValidationError(
                {"default_signature_provider": "Default provider must be one of the enabled providers."}
            )
        return attrs


# ---------------------------------------------------------------------------
# Project Governance Settings
# ---------------------------------------------------------------------------


class ProjectGovernanceSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectGovernanceSettings
        fields = [
            "id",
            "stage_gate_enforcement_enabled",
            "require_template_selection",
            "risk_assessment_mandatory",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")


# Template Components
class TemplateMilestoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemplateMilestone
        fields = [
            "id",
            "name",
            "description",
            "sort_order",
            "days_from_phase_start",
        ]
        read_only_fields = ("id",)


class TemplateRequiredDocumentSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = TemplateRequiredDocument
        fields = [
            "id",
            "name",
            "category",
            "category_display",
            "description",
            "is_mandatory",
        ]
        read_only_fields = ("id",)


class TemplateComplianceCheckpointSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemplateComplianceCheckpoint
        fields = [
            "id",
            "name",
            "description",
            "regulatory_reference",
            "is_mandatory",
        ]
        read_only_fields = ("id",)


class TemplateActivityTaskSerializer(serializers.ModelSerializer):
    class Meta:
        from .models import TaskTemplate

        model = TaskTemplate
        fields = [
            "id",
            "name",
            "description",
            "assigned_role",
            "priority",
            "sort_order",
            "reference_code",
            "estimated_effort_hours",
        ]
        read_only_fields = ("id",)


class TemplateActivitySerializer(serializers.ModelSerializer):
    task_templates = TemplateActivityTaskSerializer(many=True, read_only=True)

    class Meta:
        from .models import TemplateActivity

        model = TemplateActivity
        fields = [
            "id",
            "name",
            "description",
            "sort_order",
            "estimated_duration_days",
            "estimated_effort_hours",
            "wbs_code",
            "task_templates",
        ]
        read_only_fields = ("id",)


class TemplateActivityWriteSerializer(serializers.ModelSerializer):
    class Meta:
        from .models import TemplateActivity

        model = TemplateActivity
        fields = [
            "name",
            "description",
            "sort_order",
            "estimated_duration_days",
            "estimated_effort_hours",
            "wbs_code",
            "phase",
        ]


class TemplatePhaseSerializer(serializers.ModelSerializer):
    milestones = TemplateMilestoneSerializer(many=True, read_only=True)
    required_documents = TemplateRequiredDocumentSerializer(many=True, read_only=True)
    compliance_checkpoints = TemplateComplianceCheckpointSerializer(many=True, read_only=True)
    activities = TemplateActivitySerializer(many=True, read_only=True)

    class Meta:
        model = TemplatePhase
        fields = [
            "id",
            "name",
            "description",
            "sort_order",
            "duration_days",
            "weight",
            "milestones",
            "required_documents",
            "compliance_checkpoints",
            "activities",
        ]
        read_only_fields = ("id",)


class TemplatePhaseWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemplatePhase
        fields = [
            "name",
            "description",
            "sort_order",
            "duration_days",
            "weight",
        ]


# Project Templates
class ProjectTemplateListSerializer(serializers.ModelSerializer):
    template_type_display = serializers.CharField(
        source="get_template_type_display", read_only=True
    )
    phase_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ProjectTemplate
        fields = [
            "id",
            "name",
            "template_type",
            "template_type_display",
            "description",
            "is_active",
            "is_system",
            "phase_count",
            "created_at",
        ]


class ProjectTemplateDetailSerializer(serializers.ModelSerializer):
    template_type_display = serializers.CharField(
        source="get_template_type_display", read_only=True
    )
    phases = TemplatePhaseSerializer(many=True, read_only=True)

    class Meta:
        model = ProjectTemplate
        fields = [
            "id",
            "name",
            "template_type",
            "template_type_display",
            "description",
            "is_active",
            "is_system",
            "phases",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "is_system", "created_at", "updated_at")


class ProjectTemplateWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectTemplate
        fields = [
            "id",
            "name",
            "template_type",
            "description",
            "is_active",
        ]
        read_only_fields = ("id",)


# Entity Templates (standalone phase / milestone / task templates)
class PhaseTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhaseTemplate
        fields = "__all__"


class MilestoneTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MilestoneTemplate
        fields = "__all__"


class TaskTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskTemplate
        fields = "__all__"


class TemplateDependencySerializer(serializers.ModelSerializer):
    from_node_id = serializers.CharField(read_only=True)
    to_node_id = serializers.CharField(read_only=True)
    dependency_type_display = serializers.CharField(source="get_dependency_type_display", read_only=True)
    strength_display = serializers.CharField(source="get_strength_display", read_only=True)
    from_label = serializers.SerializerMethodField()
    to_label = serializers.SerializerMethodField()

    class Meta:
        from .models import TemplateDependency

        model = TemplateDependency
        fields = [
            "id",
            "template",
            "from_activity",
            "from_task",
            "to_activity",
            "to_task",
            "from_node_id",
            "to_node_id",
            "from_label",
            "to_label",
            "dependency_type",
            "dependency_type_display",
            "lag_hours",
            "strength",
            "strength_display",
            "risk_impact",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")

    def get_from_label(self, obj):
        if obj.from_task_id and obj.from_task:
            return obj.from_task.name
        if obj.from_activity_id and obj.from_activity:
            return obj.from_activity.name
        return ""

    def get_to_label(self, obj):
        if obj.to_task_id and obj.to_task:
            return obj.to_task.name
        if obj.to_activity_id and obj.to_activity:
            return obj.to_activity.name
        return ""


class TemplatePlanScenarioSerializer(serializers.ModelSerializer):
    risk_level_display = serializers.CharField(source="get_risk_level_display", read_only=True)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        from .models import TemplatePlanScenario

        model = TemplatePlanScenario
        fields = [
            "id", "template", "name", "description", "is_baseline",
            "duration_scalar_pct", "material_markup_pct", "location_factor",
            "contingency_pct", "equipment_daily_rate", "fx_rate_usd_ngn",
            "risk_level", "risk_level_display",
            "projected_duration_days", "projected_material_cost", "projected_labor_cost",
            "projected_equipment_cost", "projected_contingency", "projected_total_cost",
            "sensitivity_fx_10pct_impact", "sensitivity_material_10pct_impact",
            "notes", "created_by", "created_by_name", "created_at", "updated_at",
        ]
        read_only_fields = ("id", "created_by", "created_at", "updated_at")

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.email
        return ""


class TemplateScheduleSettingsSerializer(serializers.ModelSerializer):
    work_days_per_week = serializers.IntegerField(read_only=True)

    class Meta:
        from .models import TemplateScheduleSettings

        model = TemplateScheduleSettings
        fields = [
            "id", "template",
            "work_days", "shift_start", "shift_end", "hours_per_day",
            "public_holidays", "custom_holidays",
            "rainy_season_buffer_enabled", "rainy_season_buffer_pct",
            "rainy_season_months", "outdoor_task_categories",
            "resource_roles", "travel_buffer_hours",
            "duration_scalar_pct", "milestone_anchors",
            "work_days_per_week",
            "created_at", "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")


# Stage Gate Rules
class StageGateChecklistItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = StageGateChecklistItem
        fields = [
            "id",
            "item",
            "is_mandatory",
            "sort_order",
        ]
        read_only_fields = ("id",)


class StageGateRuleListSerializer(serializers.ModelSerializer):
    stage_display = serializers.CharField(source="get_stage_display", read_only=True)
    template_name = serializers.CharField(source="template.name", read_only=True, allow_null=True)
    checklist_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = StageGateRule
        fields = [
            "id",
            "name",
            "stage",
            "stage_display",
            "template",
            "template_name",
            "is_active",
            "checklist_count",
            "created_at",
        ]


class StageGateRuleDetailSerializer(serializers.ModelSerializer):
    stage_display = serializers.CharField(source="get_stage_display", read_only=True)
    template_name = serializers.CharField(source="template.name", read_only=True, allow_null=True)
    checklist_items = StageGateChecklistItemSerializer(many=True, read_only=True)

    class Meta:
        model = StageGateRule
        fields = [
            "id",
            "name",
            "stage",
            "stage_display",
            "template",
            "template_name",
            "description",
            "is_active",
            "checklist_items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")


class StageGateRuleWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = StageGateRule
        fields = [
            "id",
            "name",
            "stage",
            "template",
            "description",
            "is_active",
        ]
        read_only_fields = ("id",)


# Risk Framework
class RiskCategorySerializer(serializers.ModelSerializer):
    category_type_display = serializers.CharField(
        source="get_category_type_display", read_only=True
    )

    class Meta:
        model = RiskCategory
        fields = [
            "id",
            "name",
            "category_type",
            "category_type_display",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")


class RiskCategoryWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskCategory
        fields = [
            "id",
            "name",
            "category_type",
            "description",
            "is_active",
        ]
        read_only_fields = ("id",)


class RiskScoreMatrixSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskScoreMatrix
        fields = [
            "id",
            "matrix_config",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_matrix_config(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Must be a JSON object.")

        required_keys = ["likelihood", "impact", "thresholds"]
        for key in required_keys:
            if key not in value:
                raise serializers.ValidationError(f"Missing required key: {key}")

        return value


class RiskMitigationRuleSerializer(serializers.ModelSerializer):
    severity_display = serializers.CharField(source="get_severity_display", read_only=True)
    risk_category_name = serializers.CharField(source="risk_category.name", read_only=True)
    risk_category_type_display = serializers.CharField(
        source="risk_category.get_category_type_display", read_only=True
    )
    assign_to_role_name = serializers.CharField(
        source="assign_to_role.name", read_only=True, allow_null=True
    )

    class Meta:
        model = RiskMitigationRule
        fields = [
            "id",
            "risk_category",
            "risk_category_name",
            "risk_category_type_display",
            "severity",
            "severity_display",
            "assign_to_role",
            "assign_to_role_name",
            "escalation_required",
            "response_time_hours",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")


class RiskMitigationRuleWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskMitigationRule
        fields = [
            "id",
            "risk_category",
            "severity",
            "assign_to_role",
            "escalation_required",
            "response_time_hours",
            "is_active",
        ]
        read_only_fields = ("id",)


# ---------------------------------------------------------------------------
# Master Data Management
# ---------------------------------------------------------------------------


class MasterDataEntryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = MasterDataEntry
        fields = [
            "id", "category", "code", "label", "description",
            "metadata", "sort_order", "is_active", "is_system",
            "created_at", "updated_at",
        ]


class MasterDataEntryDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = MasterDataEntry
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class MasterDataEntryWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = MasterDataEntry
        fields = [
            "id", "category", "code", "label", "description",
            "metadata", "sort_order", "is_active",
        ]
        read_only_fields = ("id",)


# ---------------------------------------------------------------------------
# Module Activation & Feature Flags
# ---------------------------------------------------------------------------


class ModuleActivationSettingsSerializer(serializers.ModelSerializer):
    available_modules = serializers.SerializerMethodField()
    tier = serializers.CharField(source="organization.subscription_tier", read_only=True)
    tier_display = serializers.CharField(
        source="organization.get_subscription_tier_display", read_only=True
    )

    class Meta:
        model = ModuleActivationSettings
        fields = [
            "id",
            "tier",
            "tier_display",
            "enabled_modules",
            "available_modules",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")

    def get_available_modules(self, obj):
        available = obj.get_available_modules()
        return [
            {"key": m.value, "label": m.label, "available": m.value in available}
            for m in Module
            if m.value != "settings"
        ]

    def validate_enabled_modules(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Must be a list of module keys.")
        valid_keys = {m.value for m in Module}
        for key in value:
            if key not in valid_keys:
                raise serializers.ValidationError(f"Invalid module key: {key}")
        org = self.instance.organization if self.instance else None
        if org:
            allowed = TIER_MODULE_MAP.get(org.subscription_tier, set())
            for key in value:
                if key not in allowed and key != "settings":
                    raise serializers.ValidationError(
                        f"Module '{key}' is not available on the "
                        f"'{org.get_subscription_tier_display()}' tier."
                    )
        return value


class FeatureFlagDefinitionSerializer(serializers.ModelSerializer):
    scope_display = serializers.CharField(source="get_scope_display", read_only=True)
    flag_type_display = serializers.CharField(source="get_flag_type_display", read_only=True)
    module_display = serializers.SerializerMethodField()

    class Meta:
        model = FeatureFlagDefinition
        fields = [
            "id",
            "key",
            "name",
            "description",
            "module",
            "module_display",
            "flag_type",
            "flag_type_display",
            "scope",
            "scope_display",
            "default_enabled",
            "rollout_percentage",
            "minimum_tier",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")

    def get_module_display(self, obj):
        if obj.module:
            return dict(Module.choices).get(obj.module, obj.module)
        return "Platform"


class FeatureFlagOverrideSerializer(serializers.ModelSerializer):
    flag_key = serializers.CharField(source="flag.key", read_only=True)
    flag_name = serializers.CharField(source="flag.name", read_only=True)
    flag_scope = serializers.CharField(source="flag.scope", read_only=True)
    flag_module = serializers.CharField(source="flag.module", read_only=True)
    flag_description = serializers.CharField(source="flag.description", read_only=True)

    class Meta:
        model = FeatureFlagOverride
        fields = [
            "id",
            "flag",
            "flag_key",
            "flag_name",
            "flag_scope",
            "flag_module",
            "flag_description",
            "enabled",
            "scoped_project_ids",
            "scoped_regions",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")


class FeatureFlagOverrideWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeatureFlagOverride
        fields = [
            "flag",
            "enabled",
            "scoped_project_ids",
            "scoped_regions",
            "notes",
        ]

    def validate_scoped_project_ids(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Must be a list of project IDs.")
        for item in value:
            if not isinstance(item, int):
                raise serializers.ValidationError("Each project ID must be an integer.")
        return value

    def validate_scoped_regions(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Must be a list of region codes.")
        return [str(r).strip().upper() for r in value if str(r).strip()]


# ---------------------------------------------------------------------------
# Backup & Disaster Recovery Settings
# ---------------------------------------------------------------------------


class RestoreTestLogEntrySerializer(serializers.Serializer):
    """Validates individual entries in restore_test_logs."""

    date = serializers.DateTimeField()
    status = serializers.ChoiceField(choices=["pass", "fail", "partial"])
    duration_seconds = serializers.IntegerField(min_value=0)
    notes = serializers.CharField(allow_blank=True, required=False, default="")


class BackupDisasterRecoverySettingsSerializer(serializers.ModelSerializer):
    backup_frequency_display = serializers.CharField(
        source="get_backup_frequency_display", read_only=True
    )
    backup_region_display = serializers.CharField(
        source="get_backup_region_display", read_only=True
    )
    rto_display = serializers.SerializerMethodField()
    rpo_display = serializers.SerializerMethodField()

    class Meta:
        model = BackupDisasterRecoverySettings
        fields = [
            "id",
            # Backup configuration
            "backup_frequency",
            "backup_frequency_display",
            "backup_region",
            "backup_region_display",
            # Recovery objectives
            "rto_minutes",
            "rto_display",
            "rpo_minutes",
            "rpo_display",
            # Failover triggers
            "failover_on_db_failure",
            "failover_on_network_outage",
            "failover_on_storage_failure",
            "failover_on_app_crash",
            "failover_on_manual_trigger",
            # Restore testing
            "restore_test_logs",
            # Metadata
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")

    @staticmethod
    def _format_minutes(minutes):
        if minutes < 60:
            return f"{minutes}m"
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours}h {mins}m" if mins else f"{hours}h"

    def get_rto_display(self, obj):
        return self._format_minutes(obj.rto_minutes)

    def get_rpo_display(self, obj):
        return self._format_minutes(obj.rpo_minutes)

    def validate_rto_minutes(self, value):
        if value < 1 or value > 43200:
            raise serializers.ValidationError(
                "RTO must be between 1 and 43,200 minutes (30 days)."
            )
        return value

    def validate_rpo_minutes(self, value):
        if value < 1 or value > 43200:
            raise serializers.ValidationError(
                "RPO must be between 1 and 43,200 minutes (30 days)."
            )
        return value

    def validate_restore_test_logs(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Must be a list of test log entries.")
        for i, entry in enumerate(value):
            entry_serializer = RestoreTestLogEntrySerializer(data=entry)
            if not entry_serializer.is_valid():
                raise serializers.ValidationError(
                    f"Entry {i}: {entry_serializer.errors}"
                )
        return value

    def validate(self, data):
        rpo = data.get("rpo_minutes", getattr(self.instance, "rpo_minutes", 60))
        rto = data.get("rto_minutes", getattr(self.instance, "rto_minutes", 240))
        if rpo > rto:
            raise serializers.ValidationError(
                {"rpo_minutes": "RPO should not exceed RTO."}
            )
        return data


# ---------------------------------------------------------------------------
# Integration Governance Settings
# ---------------------------------------------------------------------------


class VersionCompatibilityEntrySerializer(serializers.Serializer):
    """Validates individual entries in version_compatibility_log."""

    integration_name = serializers.CharField()
    current_version = serializers.CharField()
    min_compatible_version = serializers.CharField()
    status = serializers.ChoiceField(choices=["compatible", "deprecated", "incompatible", "unknown"])
    last_checked = serializers.DateTimeField()


class IntegrationGovernanceSettingsSerializer(serializers.ModelSerializer):
    default_sync_frequency_display = serializers.CharField(
        source="get_default_sync_frequency_display", read_only=True
    )
    conflict_resolution_strategy_display = serializers.CharField(
        source="get_conflict_resolution_strategy_display", read_only=True
    )
    primary_source_of_truth_display = serializers.CharField(
        source="get_primary_source_of_truth_display", read_only=True
    )
    error_severity_threshold_display = serializers.CharField(
        source="get_error_severity_threshold_display", read_only=True
    )
    sla_max_response_time_display = serializers.SerializerMethodField()
    sla_max_sync_latency_display = serializers.SerializerMethodField()

    class Meta:
        model = IntegrationGovernanceSettings
        fields = [
            "id",
            # Data Sync
            "default_sync_frequency",
            "default_sync_frequency_display",
            "sync_retry_attempts",
            "sync_retry_delay_seconds",
            "sync_enabled",
            # Conflict Resolution
            "conflict_resolution_strategy",
            "conflict_resolution_strategy_display",
            "conflict_auto_resolve",
            "conflict_notify_on_resolution",
            "conflict_escalation_after_hours",
            # Source of Truth
            "primary_source_of_truth",
            "primary_source_of_truth_display",
            "source_override_allowed",
            # Error Log Routing
            "error_routing_email",
            "error_routing_webhook",
            "error_routing_in_app",
            "error_routing_syslog",
            "error_webhook_url",
            "error_email_recipients",
            "error_severity_threshold",
            "error_severity_threshold_display",
            # Integration SLA
            "sla_target_uptime_pct",
            "sla_max_response_time_ms",
            "sla_max_response_time_display",
            "sla_max_sync_latency_seconds",
            "sla_max_sync_latency_display",
            "sla_alert_on_breach",
            # Version Compatibility
            "version_compatibility_log",
            # Metadata
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")

    def get_sla_max_response_time_display(self, obj):
        ms = obj.sla_max_response_time_ms
        if ms < 1000:
            return f"{ms}ms"
        secs = ms / 1000
        return f"{secs:.1f}s" if secs != int(secs) else f"{int(secs)}s"

    def get_sla_max_sync_latency_display(self, obj):
        secs = obj.sla_max_sync_latency_seconds
        if secs < 60:
            return f"{secs}s"
        mins = secs // 60
        rem = secs % 60
        return f"{mins}m {rem}s" if rem else f"{mins}m"

    def validate_sync_retry_attempts(self, value):
        if value < 0 or value > 10:
            raise serializers.ValidationError("Must be between 0 and 10.")
        return value

    def validate_sync_retry_delay_seconds(self, value):
        if value < 5 or value > 3600:
            raise serializers.ValidationError("Must be between 5 and 3,600 seconds.")
        return value

    def validate_conflict_escalation_after_hours(self, value):
        if value < 1 or value > 720:
            raise serializers.ValidationError("Must be between 1 and 720 hours.")
        return value

    def validate_error_email_recipients(self, value):
        import re
        if not isinstance(value, list):
            raise serializers.ValidationError("Must be a list of email addresses.")
        for email in value:
            if not isinstance(email, str) or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
                raise serializers.ValidationError(f"Invalid email address: {email}")
        return value

    def validate_error_webhook_url(self, value):
        if value and not value.startswith(("https://", "http://")):
            raise serializers.ValidationError("Must be a valid URL starting with http:// or https://.")
        return value

    def validate_sla_target_uptime_pct(self, value):
        from decimal import Decimal
        if value < Decimal("90.00") or value > Decimal("100.00"):
            raise serializers.ValidationError("Must be between 90.00 and 100.00.")
        return value

    def validate_sla_max_response_time_ms(self, value):
        if value < 100 or value > 60000:
            raise serializers.ValidationError("Must be between 100 and 60,000 milliseconds.")
        return value

    def validate_sla_max_sync_latency_seconds(self, value):
        if value < 10 or value > 86400:
            raise serializers.ValidationError("Must be between 10 and 86,400 seconds (24 hours).")
        return value

    def validate_version_compatibility_log(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Must be a list of version compatibility entries.")
        for i, entry in enumerate(value):
            entry_serializer = VersionCompatibilityEntrySerializer(data=entry)
            if not entry_serializer.is_valid():
                raise serializers.ValidationError(
                    f"Entry {i}: {entry_serializer.errors}"
                )
        return value

    def validate(self, data):
        webhook_enabled = data.get(
            "error_routing_webhook",
            getattr(self.instance, "error_routing_webhook", False),
        )
        webhook_url = data.get(
            "error_webhook_url",
            getattr(self.instance, "error_webhook_url", ""),
        )
        if webhook_enabled and not webhook_url:
            raise serializers.ValidationError(
                {"error_webhook_url": "Webhook URL is required when webhook routing is enabled."}
            )
        return data


# ---------------------------------------------------------------------------
# KPI & Performance Configuration
# ---------------------------------------------------------------------------


class KpiDefinitionListSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    unit_display = serializers.CharField(source="get_unit_display", read_only=True)
    direction_display = serializers.CharField(source="get_direction_display", read_only=True)
    frequency_display = serializers.CharField(source="get_frequency_display", read_only=True)
    grain_display = serializers.CharField(source="get_grain_display", read_only=True)
    owner_role_name = serializers.CharField(source="owner_role.name", read_only=True, default=None)
    owner_user_name = serializers.SerializerMethodField()
    assignment_count = serializers.IntegerField(read_only=True, default=0)

    def get_owner_user_name(self, obj):
        user = obj.owner_user
        if not user:
            return None
        full_name = user.get_full_name() if hasattr(user, "get_full_name") else ""
        return full_name or getattr(user, "username", None) or str(user)

    class Meta:
        model = KpiDefinition
        fields = [
            "id",
            "name",
            "code",
            "category",
            "category_display",
            "unit",
            "unit_display",
            "direction",
            "direction_display",
            "frequency",
            "frequency_display",
            "is_canonical",
            "grain",
            "grain_display",
            "dimensions",
            "owner_role",
            "owner_role_name",
            "owner_user",
            "owner_user_name",
            "freshness_sla_minutes",
            "green_threshold",
            "amber_threshold",
            "bonus_green_pct",
            "bonus_amber_pct",
            "bonus_red_pct",
            "is_active",
            "is_system",
            "sort_order",
            "assignment_count",
            "created_at",
            "updated_at",
        ]


class KpiDefinitionDetailSerializer(KpiDefinitionListSerializer):
    class Meta(KpiDefinitionListSerializer.Meta):
        fields = KpiDefinitionListSerializer.Meta.fields + [
            "description",
            "formula_expression",
            "data_source",
        ]


class KpiDefinitionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = KpiDefinition
        fields = [
            "name",
            "code",
            "description",
            "category",
            "unit",
            "direction",
            "frequency",
            "is_canonical",
            "grain",
            "dimensions",
            "owner_role",
            "owner_user",
            "freshness_sla_minutes",
            "formula_expression",
            "data_source",
            "green_threshold",
            "amber_threshold",
            "bonus_green_pct",
            "bonus_amber_pct",
            "bonus_red_pct",
            "is_active",
            "sort_order",
        ]

    def validate_code(self, value):
        import re
        if not re.match(r"^[A-Z][A-Z0-9_]*$", value):
            raise serializers.ValidationError(
                "Code must be uppercase letters, digits, and underscores, starting with a letter."
            )
        return value

    def validate_dimensions(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Must be a list of dimension keys.")
        cleaned = []
        seen = set()
        for idx, raw in enumerate(value):
            if not isinstance(raw, str):
                raise serializers.ValidationError(
                    f"Entry at index {idx} must be a string dimension key."
                )
            dimension = raw.strip()
            if not dimension:
                raise serializers.ValidationError(
                    f"Entry at index {idx} must not be blank."
                )
            if dimension not in seen:
                cleaned.append(dimension)
                seen.add(dimension)
        return cleaned

    def validate_freshness_sla_minutes(self, value):
        if value < 1 or value > 525600:
            raise serializers.ValidationError("Must be between 1 and 525,600 minutes.")
        return value

    def _resolve_org(self):
        if self.instance is not None:
            return getattr(self.instance, "organization", None)
        request = self.context.get("request")
        if not request:
            return None
        profile = getattr(request.user, "profile", None)
        return getattr(profile, "organization", None)

    @staticmethod
    def _resolve_user_org(user):
        profile = getattr(user, "profile", None)
        profile_org = getattr(profile, "organization", None)
        if profile_org is not None:
            return profile_org
        return getattr(user, "organization", None)

    def validate(self, data):
        direction = data.get("direction", getattr(self.instance, "direction", "higher_is_better"))
        green = data.get("green_threshold", getattr(self.instance, "green_threshold", None))
        amber = data.get("amber_threshold", getattr(self.instance, "amber_threshold", None))
        owner_role = data.get("owner_role", getattr(self.instance, "owner_role", None))
        owner_user = data.get("owner_user", getattr(self.instance, "owner_user", None))
        org = self._resolve_org()

        if green is not None and amber is not None:
            if direction == "higher_is_better" and green < amber:
                raise serializers.ValidationError(
                    {"green_threshold": "For 'higher is better' KPIs, green threshold must be ≥ amber threshold."}
                )
            if direction == "lower_is_better" and green > amber:
                raise serializers.ValidationError(
                    {"green_threshold": "For 'lower is better' KPIs, green threshold must be ≤ amber threshold."}
                )

        if org and owner_role and owner_role.organization_id != org.id:
            raise serializers.ValidationError(
                {"owner_role": "Owner role must belong to the same organization as the KPI."}
            )
        if org and owner_user:
            owner_user_org = self._resolve_user_org(owner_user)
            if owner_user_org is None:
                raise serializers.ValidationError(
                    {"owner_user": "Owner user must have an organization profile."}
                )
            if owner_user_org.id != org.id:
                raise serializers.ValidationError(
                    {"owner_user": "Owner user must belong to the same organization as the KPI."}
                )
        return data


class KpiAssignmentSerializer(serializers.ModelSerializer):
    kpi_name = serializers.CharField(source="kpi.name", read_only=True)
    kpi_code = serializers.CharField(source="kpi.code", read_only=True)
    kpi_category = serializers.CharField(source="kpi.category", read_only=True)
    kpi_category_display = serializers.CharField(source="kpi.get_category_display", read_only=True)
    kpi_unit = serializers.CharField(source="kpi.unit", read_only=True)
    kpi_unit_display = serializers.CharField(source="kpi.get_unit_display", read_only=True)
    role_name = serializers.CharField(source="role.name", read_only=True, default=None)
    department_name = serializers.CharField(source="department.name", read_only=True, default=None)

    class Meta:
        model = KpiAssignment
        fields = [
            "id",
            "kpi",
            "kpi_name",
            "kpi_code",
            "kpi_category",
            "kpi_category_display",
            "kpi_unit",
            "kpi_unit_display",
            "role",
            "role_name",
            "department",
            "department_name",
            "target_value",
            "weight",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, data):
        role = data.get("role", getattr(self.instance, "role", None))
        department = data.get("department", getattr(self.instance, "department", None))
        if not role and not department:
            raise serializers.ValidationError(
                "At least one of 'role' or 'department' must be specified."
            )
        weight = data.get("weight", getattr(self.instance, "weight", 100))
        if weight < 0 or weight > 100:
            raise serializers.ValidationError({"weight": "Must be between 0 and 100."})
        return data


# ---------------------------------------------------------------------------
# Reporting Engine Settings
# ---------------------------------------------------------------------------


class ReportingEngineSettingsSerializer(serializers.ModelSerializer):
    page_size_display = serializers.CharField(source="get_page_size_display", read_only=True)
    orientation_display = serializers.CharField(source="get_orientation_display", read_only=True)
    watermark_position_display = serializers.CharField(source="get_watermark_position_display", read_only=True)
    default_dispatch_format_display = serializers.CharField(source="get_default_dispatch_format_display", read_only=True)
    board_pack_frequency_display = serializers.CharField(source="get_board_pack_frequency_display", read_only=True)

    class Meta:
        model = ReportingEngineSettings
        fields = [
            "id",
            # PDF Formatting
            "page_size",
            "page_size_display",
            "orientation",
            "orientation_display",
            "margin_top_mm",
            "margin_bottom_mm",
            "margin_left_mm",
            "margin_right_mm",
            "header_enabled",
            "header_text",
            "footer_enabled",
            "footer_text",
            "font_family",
            "font_size_pt",
            "include_cover_page",
            "include_table_of_contents",
            # Watermark
            "watermark_enabled",
            "watermark_text",
            "watermark_opacity",
            "watermark_position",
            "watermark_position_display",
            "watermark_color",
            # Board Pack
            "board_pack_enabled",
            "board_pack_frequency",
            "board_pack_frequency_display",
            "board_pack_recipients",
            "board_pack_sections",
            # Dispatch Defaults
            "default_dispatch_format",
            "default_dispatch_format_display",
            "dispatch_retention_days",
            "dispatch_reply_to_email",
            # Metadata
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_margin_top_mm(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("Must be between 0 and 100 mm.")
        return value

    def validate_margin_bottom_mm(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("Must be between 0 and 100 mm.")
        return value

    def validate_margin_left_mm(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("Must be between 0 and 100 mm.")
        return value

    def validate_margin_right_mm(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("Must be between 0 and 100 mm.")
        return value

    def validate_font_size_pt(self, value):
        if value < 6 or value > 24:
            raise serializers.ValidationError("Must be between 6 and 24 pt.")
        return value

    def validate_watermark_opacity(self, value):
        if value < 1 or value > 100:
            raise serializers.ValidationError("Must be between 1 and 100.")
        return value

    def validate_watermark_color(self, value):
        import re
        if not re.match(r"^#[0-9A-Fa-f]{6}$", value):
            raise serializers.ValidationError("Must be a valid hex color (e.g. #CBD5E1).")
        return value

    def validate_dispatch_retention_days(self, value):
        if value < 1 or value > 730:
            raise serializers.ValidationError("Must be between 1 and 730 days (2 years).")
        return value

    def validate_board_pack_recipients(self, value):
        import re
        if not isinstance(value, list):
            raise serializers.ValidationError("Must be a list of email addresses.")
        for email in value:
            if not isinstance(email, str) or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
                raise serializers.ValidationError(f"Invalid email address: {email}")
        return value

    def validate_board_pack_sections(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Must be a list of report template codes.")
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise serializers.ValidationError("Each section must be a non-empty string.")
        return [s.strip() for s in value]


# ---------------------------------------------------------------------------
# Confidentiality Labels
# ---------------------------------------------------------------------------


class ConfidentialityLabelSerializer(serializers.ModelSerializer):
    access_level_display = serializers.CharField(source="get_access_level_display", read_only=True)

    class Meta:
        model = ConfidentialityLabel
        fields = [
            "id",
            "name",
            "code",
            "description",
            "access_level",
            "access_level_display",
            "color",
            "watermark_override",
            "restrict_printing",
            "restrict_download",
            "is_active",
            "is_system",
            "sort_order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "is_system", "created_at", "updated_at")


class ConfidentialityLabelWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfidentialityLabel
        fields = [
            "name",
            "code",
            "description",
            "access_level",
            "color",
            "watermark_override",
            "restrict_printing",
            "restrict_download",
            "is_active",
            "sort_order",
        ]

    def validate_code(self, value):
        import re
        if not re.match(r"^[a-z][a-z0-9_]*$", value):
            raise serializers.ValidationError(
                "Code must be lowercase letters, digits, and underscores, starting with a letter."
            )
        return value

    def validate_color(self, value):
        import re
        if not re.match(r"^#[0-9A-Fa-f]{6}$", value):
            raise serializers.ValidationError("Must be a valid hex color (e.g. #6B7280).")
        return value


# ---------------------------------------------------------------------------
# Report Templates
# ---------------------------------------------------------------------------


class DataSourceEntrySerializer(serializers.Serializer):
    """Validates individual entries in data_sources."""
    module = serializers.CharField()
    entity = serializers.CharField()
    fields = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    filters = serializers.DictField(required=False, default=dict)


class CrossModuleJoinEntrySerializer(serializers.Serializer):
    """Validates individual entries in cross_module_joins."""
    left_source = serializers.CharField()
    right_source = serializers.CharField()
    join_key = serializers.CharField()
    join_type = serializers.ChoiceField(choices=["inner", "left", "right", "full"])


class ReportTemplateListSerializer(serializers.ModelSerializer):
    template_type_display = serializers.CharField(source="get_template_type_display", read_only=True)
    output_format_display = serializers.CharField(source="get_output_format_display", read_only=True)
    confidentiality_label_name = serializers.CharField(
        source="confidentiality_label.name", read_only=True, default=None
    )
    confidentiality_restrict_download = serializers.BooleanField(
        source="confidentiality_label.restrict_download",
        read_only=True,
        default=False,
    )
    confidentiality_restrict_printing = serializers.BooleanField(
        source="confidentiality_label.restrict_printing",
        read_only=True,
        default=False,
    )
    owner_name = serializers.SerializerMethodField()
    module_source_display = serializers.SerializerMethodField()
    schedule_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = ReportTemplate
        fields = [
            "id",
            "name",
            "code",
            "description",
            "module_source",
            "module_source_display",
            "template_type",
            "template_type_display",
            "output_format",
            "output_format_display",
            "owner",
            "owner_name",
            "visibility",
            "shared_department",
            "confidentiality_label",
            "confidentiality_label_name",
            "confidentiality_restrict_download",
            "confidentiality_restrict_printing",
            "allow_simple_builder",
            "is_active",
            "is_system",
            "schedule_count",
            "created_at",
            "updated_at",
        ]

    def get_owner_name(self, obj):
        owner = getattr(obj, "owner", None)
        if not owner:
            return None
        return owner.get_full_name() or owner.username

    def get_module_source_display(self, obj):
        if obj.module_source:
            return obj.get_module_source_display()
        if isinstance(obj.data_sources, list):
            for row in obj.data_sources:
                if isinstance(row, dict):
                    module_value = str(row.get("module", "")).strip()
                    if module_value:
                        return module_value.replace("_", " ").title()
        return "Unspecified"


class ReportTemplateDetailSerializer(ReportTemplateListSerializer):
    class Meta(ReportTemplateListSerializer.Meta):
        fields = ReportTemplateListSerializer.Meta.fields + [
            "data_sources",
            "cross_module_joins",
        ]


class ReportTemplateWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportTemplate
        fields = [
            "name",
            "code",
            "description",
            "module_source",
            "owner",
            "visibility",
            "shared_department",
            "template_type",
            "output_format",
            "data_sources",
            "cross_module_joins",
            "confidentiality_label",
            "allow_simple_builder",
            "is_active",
        ]

    def validate_code(self, value):
        import re
        if not re.match(r"^[A-Z][A-Z0-9_]*$", value):
            raise serializers.ValidationError(
                "Code must be uppercase letters, digits, and underscores, starting with a letter."
            )
        return value

    def validate_data_sources(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Must be a list of data source entries.")
        for i, entry in enumerate(value):
            entry_serializer = DataSourceEntrySerializer(data=entry)
            if not entry_serializer.is_valid():
                raise serializers.ValidationError(f"Entry {i}: {entry_serializer.errors}")
        return value

    def validate_cross_module_joins(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Must be a list of join definitions.")
        for i, entry in enumerate(value):
            entry_serializer = CrossModuleJoinEntrySerializer(data=entry)
            if not entry_serializer.is_valid():
                raise serializers.ValidationError(f"Entry {i}: {entry_serializer.errors}")
        return value

    def validate(self, data):
        visibility = data.get("visibility", getattr(self.instance, "visibility", ReportTemplate.Visibility.SHARED))
        shared_department = data.get("shared_department", getattr(self.instance, "shared_department", None))
        if visibility == ReportTemplate.Visibility.DEPARTMENT and shared_department is None:
            raise serializers.ValidationError(
                {"shared_department": "Department is required for department visibility."}
            )

        request = self.context.get("request")
        request_org = getattr(getattr(request, "user", None), "profile", None)
        request_org = getattr(request_org, "organization", None)

        owner = data.get("owner", getattr(self.instance, "owner", None))
        if owner is not None:
            owner_org = getattr(getattr(owner, "profile", None), "organization", None)
            if request_org is not None and owner_org != request_org:
                raise serializers.ValidationError(
                    {"owner": "Owner must belong to the same organization."}
                )

        if shared_department is not None:
            department_org = getattr(getattr(shared_department, "division", None), "organization", None)
            if request_org is not None and department_org != request_org:
                raise serializers.ValidationError(
                    {"shared_department": "Department must belong to the same organization."}
                )
        return data


class ReportRunSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    trigger_display = serializers.CharField(source="get_trigger_display", read_only=True)
    output_format_display = serializers.CharField(source="get_output_format_display", read_only=True)
    report_template_name = serializers.CharField(source="report_template.name", read_only=True)
    report_template_code = serializers.CharField(source="report_template.code", read_only=True)
    requested_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ReportRun
        fields = [
            "id",
            "report_template",
            "report_template_name",
            "report_template_code",
            "requested_by",
            "requested_by_name",
            "scheduled_dispatch",
            "subscription",
            "trigger",
            "trigger_display",
            "status",
            "status_display",
            "output_format",
            "output_format_display",
            "filters",
            "result_summary",
            "row_count",
            "file_path",
            "error_message",
            "created_at",
            "started_at",
            "completed_at",
        ]
        read_only_fields = [
            "id",
            "report_template_name",
            "report_template_code",
            "requested_by_name",
            "scheduled_dispatch",
            "subscription",
            "trigger_display",
            "status_display",
            "output_format_display",
            "result_summary",
            "row_count",
            "file_path",
            "error_message",
            "created_at",
            "started_at",
            "completed_at",
        ]

    def get_requested_by_name(self, obj):
        user = getattr(obj, "requested_by", None)
        if not user:
            return None
        return user.get_full_name() or user.username


class ReportRunRequestSerializer(serializers.Serializer):
    output_format = serializers.ChoiceField(
        choices=ReportTemplate.OutputFormat.choices,
        required=False,
    )
    requested_action = serializers.ChoiceField(
        choices=["run", "export"],
        required=False,
        default="run",
    )
    filters = serializers.DictField(required=False, default=dict)
    saved_view_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)


class ReportSavedViewSerializer(serializers.ModelSerializer):
    report_template_name = serializers.CharField(source="report_template.name", read_only=True)
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = ReportSavedView
        fields = [
            "id",
            "name",
            "report_template",
            "report_template_name",
            "user",
            "user_name",
            "filters",
            "column_visibility",
            "rows_per_page",
            "is_default",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "report_template_name",
            "user",
            "user_name",
            "created_at",
            "updated_at",
        ]

    def get_user_name(self, obj):
        user = getattr(obj, "user", None)
        if not user:
            return None
        return user.get_full_name() or user.username


class ReportSavedViewWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportSavedView
        fields = [
            "name",
            "report_template",
            "filters",
            "column_visibility",
            "rows_per_page",
            "is_default",
            "is_active",
        ]

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Name is required.")
        return value

    def validate_rows_per_page(self, value):
        if value < 5 or value > 500:
            raise serializers.ValidationError("Rows per page must be between 5 and 500.")
        return value

    def validate_report_template(self, value):
        request = self.context.get("request")
        request_org = getattr(getattr(getattr(request, "user", None), "profile", None), "organization", None)
        if request_org is not None and value.organization_id != request_org.id:
            raise serializers.ValidationError("Report template must belong to your organization.")
        return value


class ReportSubscriptionSerializer(serializers.ModelSerializer):
    frequency_display = serializers.CharField(source="get_frequency_display", read_only=True)
    output_format_display = serializers.CharField(source="get_output_format_display", read_only=True)
    report_template_name = serializers.CharField(source="report_template.name", read_only=True)
    report_template_code = serializers.CharField(source="report_template.code", read_only=True)
    delivery_channels_display = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = ReportSubscription
        fields = [
            "id",
            "report_template",
            "report_template_name",
            "report_template_code",
            "user",
            "user_name",
            "frequency",
            "frequency_display",
            "output_format",
            "output_format_display",
            "recipients",
            "delivery_channels",
            "delivery_channels_display",
            "is_active",
            "last_sent_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "report_template_name",
            "report_template_code",
            "user",
            "user_name",
            "frequency_display",
            "output_format_display",
            "delivery_channels_display",
            "last_sent_at",
            "created_at",
            "updated_at",
        ]

    def get_user_name(self, obj):
        user = getattr(obj, "user", None)
        if not user:
            return None
        return user.get_full_name() or user.username

    def get_delivery_channels_display(self, obj):
        labels = dict(ReportSubscription.DeliveryChannel.choices)
        if not isinstance(obj.delivery_channels, list):
            return []
        return [labels.get(channel, channel.replace("_", " ").title()) for channel in obj.delivery_channels]


class ReportSubscriptionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportSubscription
        fields = [
            "report_template",
            "frequency",
            "output_format",
            "recipients",
            "delivery_channels",
            "is_active",
        ]

    def validate_recipients(self, value):
        import re

        if value in (None, ""):
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError("Recipients must be a list of email addresses.")
        normalized: list[str] = []
        for email in value:
            email_value = email.strip().lower() if isinstance(email, str) else ""
            if not email_value or not re.match(r"^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", email_value):
                raise serializers.ValidationError(f"Invalid email address: {email}")
            if email_value not in normalized:
                normalized.append(email_value)
        return normalized

    def validate_delivery_channels(self, value):
        if value in (None, ""):
            raise serializers.ValidationError("Select at least one delivery channel.")
        if not isinstance(value, list):
            raise serializers.ValidationError("Delivery channels must be a list.")

        allowed = {choice[0] for choice in ReportSubscription.DeliveryChannel.choices}
        normalized: list[str] = []
        for channel in value:
            channel_value = channel.strip().lower() if isinstance(channel, str) else ""
            if channel_value not in allowed:
                raise serializers.ValidationError(f"Invalid delivery channel: {channel}")
            if channel_value not in normalized:
                normalized.append(channel_value)

        if not normalized:
            raise serializers.ValidationError("Select at least one delivery channel.")
        return normalized

    def validate_report_template(self, value):
        request = self.context.get("request")
        request_org = getattr(getattr(getattr(request, "user", None), "profile", None), "organization", None)
        if request_org is not None and value.organization_id != request_org.id:
            raise serializers.ValidationError("Report template must belong to your organization.")
        return value

    def validate(self, attrs):
        channels = attrs.get("delivery_channels")
        if channels is None:
            if self.instance and isinstance(self.instance.delivery_channels, list):
                channels = self.instance.delivery_channels
            else:
                channels = [ReportSubscription.DeliveryChannel.EMAIL]

        recipients = attrs.get("recipients")
        if recipients is None:
            recipients = self.instance.recipients if self.instance else []
        if not isinstance(recipients, list):
            recipients = []

        email_channel = ReportSubscription.DeliveryChannel.EMAIL
        if email_channel in channels and len(recipients) == 0:
            raise serializers.ValidationError(
                {"recipients": "At least one recipient is required when Email delivery is selected."}
            )
        if recipients and email_channel not in channels:
            raise serializers.ValidationError(
                {"delivery_channels": "Include Email delivery when recipients are provided."}
            )
        return attrs


class ReportLibraryItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    code = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    module_source = serializers.CharField(allow_blank=True)
    module_source_display = serializers.CharField()
    owner_name = serializers.CharField(allow_null=True, required=False)
    confidentiality_label = serializers.CharField(allow_null=True, required=False)
    visibility = serializers.CharField()
    category = serializers.CharField()
    last_run_at = serializers.DateTimeField(allow_null=True)


class ReportLibraryResponseSerializer(serializers.Serializer):
    categories = serializers.ListField(child=serializers.DictField())
    results = ReportLibraryItemSerializer(many=True)


class MyScheduledReportItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    report_template = serializers.IntegerField()
    report_template_name = serializers.CharField()
    schedule_text = serializers.CharField()
    status = serializers.ChoiceField(choices=["delivered", "failed", "pending"])
    status_display = serializers.CharField()
    last_dispatched_at = serializers.DateTimeField(allow_null=True)
    latest_run_at = serializers.DateTimeField(allow_null=True)


class MyScheduledReportResponseSerializer(serializers.Serializer):
    results = MyScheduledReportItemSerializer(many=True)


# ---------------------------------------------------------------------------
# Scheduled Report Dispatch
# ---------------------------------------------------------------------------


class ScheduledReportDispatchSerializer(serializers.ModelSerializer):
    frequency_display = serializers.CharField(source="get_frequency_display", read_only=True)
    output_format_display = serializers.CharField(source="get_output_format_display", read_only=True)
    report_template_name = serializers.CharField(source="report_template.name", read_only=True)
    report_template_code = serializers.CharField(source="report_template.code", read_only=True)
    dispatch_day_of_week_display = serializers.SerializerMethodField()

    class Meta:
        model = ScheduledReportDispatch
        fields = [
            "id",
            "name",
            "report_template",
            "report_template_name",
            "report_template_code",
            "frequency",
            "frequency_display",
            "dispatch_time",
            "dispatch_day_of_week",
            "dispatch_day_of_week_display",
            "dispatch_day_of_month",
            "output_format",
            "output_format_display",
            "recipients",
            "is_active",
            "last_dispatched_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "last_dispatched_at", "created_at", "updated_at")

    def get_dispatch_day_of_week_display(self, obj):
        if obj.dispatch_day_of_week is not None:
            return dict(ScheduledReportDispatch.DayOfWeek.choices).get(
                obj.dispatch_day_of_week
            )
        return None


class ScheduledReportDispatchWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScheduledReportDispatch
        fields = [
            "name",
            "report_template",
            "frequency",
            "dispatch_time",
            "dispatch_day_of_week",
            "dispatch_day_of_month",
            "output_format",
            "recipients",
            "is_active",
        ]

    def validate_recipients(self, value):
        import re
        if not isinstance(value, list) or len(value) == 0:
            raise serializers.ValidationError("Must be a non-empty list of email addresses.")
        for email in value:
            if not isinstance(email, str) or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
                raise serializers.ValidationError(f"Invalid email address: {email}")
        return value

    def validate_dispatch_day_of_month(self, value):
        if value is not None and (value < 1 or value > 28):
            raise serializers.ValidationError("Must be between 1 and 28.")
        return value

    def validate(self, data):
        frequency = data.get("frequency", getattr(self.instance, "frequency", None))
        if frequency == "weekly":
            dow = data.get("dispatch_day_of_week", getattr(self.instance, "dispatch_day_of_week", None))
            if dow is None:
                raise serializers.ValidationError(
                    {"dispatch_day_of_week": "Required for weekly schedules."}
                )
        if frequency in ("monthly", "quarterly", "annual"):
            dom = data.get("dispatch_day_of_month", getattr(self.instance, "dispatch_day_of_month", None))
            if dom is None:
                raise serializers.ValidationError(
                    {"dispatch_day_of_month": "Required for monthly/quarterly/annual schedules."}
                )
        return data


# ---------------------------------------------------------------------------
# Escalation Matrix Settings
# ---------------------------------------------------------------------------

VALID_NOTIFICATION_CHANNELS = {"email", "in_app", "sms", "push"}


def _validate_notification_channels(value):
    if not isinstance(value, list):
        raise serializers.ValidationError("Must be a list of channel names.")
    normalized = []
    for ch in value:
        if ch not in VALID_NOTIFICATION_CHANNELS:
            raise serializers.ValidationError(
                f"Invalid channel '{ch}'. Valid: {', '.join(sorted(VALID_NOTIFICATION_CHANNELS))}."
            )
        if ch not in normalized:
            normalized.append(ch)
    return normalized


def _validate_email_list(value):
    import re
    if not isinstance(value, list):
        raise serializers.ValidationError("Must be a list of email addresses.")
    for email in value:
        if not isinstance(email, str) or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            raise serializers.ValidationError(f"Invalid email address: {email}")
    return value


def _validate_role_slug_list(value):
    if not isinstance(value, list):
        raise serializers.ValidationError("Must be a list of role slugs.")
    for slug in value:
        if not isinstance(slug, str) or not slug.strip():
            raise serializers.ValidationError("Each role slug must be a non-empty string.")
    return [s.strip() for s in value]


class EscalationMatrixSettingsSerializer(serializers.ModelSerializer):
    crisis_activation_severity_display = serializers.CharField(
        source="get_crisis_activation_severity_display", read_only=True
    )
    board_severity_threshold_display = serializers.CharField(
        source="get_board_severity_threshold_display", read_only=True
    )

    class Meta:
        model = EscalationMatrixSettings
        fields = [
            "id",
            # Global Escalation
            "escalation_enabled",
            "default_response_time_minutes",
            "max_escalation_levels",
            "auto_escalation_enabled",
            "require_acknowledgment",
            # Crisis Mode
            "crisis_mode_enabled",
            "crisis_activation_severity",
            "crisis_activation_severity_display",
            "crisis_activation_threshold",
            "crisis_notification_channels",
            "crisis_war_room_enabled",
            "crisis_auto_deactivate_hours",
            # Board Notifications
            "board_notification_enabled",
            "board_severity_threshold",
            "board_severity_threshold_display",
            "board_notification_recipients",
            "board_notification_cooldown_hours",
            # Metadata
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_default_response_time_minutes(self, value):
        if value < 1 or value > 43200:
            raise serializers.ValidationError("Must be between 1 and 43,200 minutes (30 days).")
        return value

    def validate_max_escalation_levels(self, value):
        if value < 1 or value > 10:
            raise serializers.ValidationError("Must be between 1 and 10.")
        return value

    def validate_crisis_activation_threshold(self, value):
        if value < 1 or value > 100:
            raise serializers.ValidationError("Must be between 1 and 100.")
        return value

    def validate_crisis_notification_channels(self, value):
        return _validate_notification_channels(value)

    def validate_crisis_auto_deactivate_hours(self, value):
        if value < 1 or value > 168:
            raise serializers.ValidationError("Must be between 1 and 168 hours (7 days).")
        return value

    def validate_board_notification_recipients(self, value):
        return _validate_email_list(value)

    def validate_board_notification_cooldown_hours(self, value):
        if value < 1 or value > 168:
            raise serializers.ValidationError("Must be between 1 and 168 hours (7 days).")
        return value


# ---------------------------------------------------------------------------
# Escalation Tiers
# ---------------------------------------------------------------------------


class EscalationTierSerializer(serializers.ModelSerializer):
    severity_display = serializers.CharField(source="get_severity_display", read_only=True)

    class Meta:
        model = EscalationTier
        fields = [
            "id",
            "severity",
            "severity_display",
            "tier_level",
            "name",
            "description",
            "response_time_minutes",
            "escalate_to_roles",
            "notification_channels",
            "requires_acknowledgment",
            "is_active",
            "sort_order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")


class EscalationTierWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = EscalationTier
        fields = [
            "severity",
            "tier_level",
            "name",
            "description",
            "response_time_minutes",
            "escalate_to_roles",
            "notification_channels",
            "requires_acknowledgment",
            "is_active",
            "sort_order",
        ]

    def validate_tier_level(self, value):
        if value < 1 or value > 10:
            raise serializers.ValidationError("Must be between 1 and 10.")
        return value

    def validate_response_time_minutes(self, value):
        if value < 1 or value > 43200:
            raise serializers.ValidationError("Must be between 1 and 43,200 minutes.")
        return value

    def validate_escalate_to_roles(self, value):
        return _validate_role_slug_list(value)

    def validate_notification_channels(self, value):
        return _validate_notification_channels(value)


# ---------------------------------------------------------------------------
# Auto-Escalation Rules
# ---------------------------------------------------------------------------


class AutoEscalationRuleSerializer(serializers.ModelSerializer):
    rule_type_display = serializers.CharField(source="get_rule_type_display", read_only=True)
    condition_type_display = serializers.CharField(source="get_condition_type_display", read_only=True)
    trigger_severity_display = serializers.SerializerMethodField()
    source_tier_name = serializers.CharField(source="source_tier.name", read_only=True, default=None)
    target_tier_name = serializers.CharField(source="target_tier.name", read_only=True, default=None)

    class Meta:
        model = AutoEscalationRule
        fields = [
            "id",
            "name",
            "description",
            "rule_type",
            "rule_type_display",
            # Time-based
            "source_tier",
            "source_tier_name",
            "target_tier",
            "target_tier_name",
            "escalate_after_minutes",
            "condition_type",
            "condition_type_display",
            "condition_threshold",
            "notify_original_assignee",
            # Parallel
            "trigger_severity",
            "trigger_severity_display",
            "parallel_notify_roles",
            "parallel_notify_emails",
            "parallel_channels",
            # Status
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")

    def get_trigger_severity_display(self, obj):
        if obj.trigger_severity:
            return dict(EscalationTier.Severity.choices).get(obj.trigger_severity)
        return None


class AutoEscalationRuleWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutoEscalationRule
        fields = [
            "name",
            "description",
            "rule_type",
            # Time-based
            "source_tier",
            "target_tier",
            "escalate_after_minutes",
            "condition_type",
            "condition_threshold",
            "notify_original_assignee",
            # Parallel
            "trigger_severity",
            "parallel_notify_roles",
            "parallel_notify_emails",
            "parallel_channels",
            # Status
            "is_active",
        ]

    def validate_escalate_after_minutes(self, value):
        if value is not None and (value < 1 or value > 43200):
            raise serializers.ValidationError("Must be between 1 and 43,200 minutes.")
        return value

    def validate_parallel_notify_roles(self, value):
        return _validate_role_slug_list(value)

    def validate_parallel_notify_emails(self, value):
        return _validate_email_list(value)

    def validate_parallel_channels(self, value):
        return _validate_notification_channels(value)

    def validate(self, data):
        rule_type = data.get("rule_type", getattr(self.instance, "rule_type", None))
        if rule_type == "time_based":
            source = data.get("source_tier", getattr(self.instance, "source_tier", None))
            target = data.get("target_tier", getattr(self.instance, "target_tier", None))
            minutes = data.get("escalate_after_minutes", getattr(self.instance, "escalate_after_minutes", None))
            if not source:
                raise serializers.ValidationError({"source_tier": "Required for time-based rules."})
            if not target:
                raise serializers.ValidationError({"target_tier": "Required for time-based rules."})
            if not minutes:
                raise serializers.ValidationError({"escalate_after_minutes": "Required for time-based rules."})
        if rule_type == "parallel":
            severity = data.get("trigger_severity", getattr(self.instance, "trigger_severity", ""))
            if not severity:
                raise serializers.ValidationError({"trigger_severity": "Required for parallel rules."})
        return data


# ---------------------------------------------------------------------------
# Board Notification Triggers
# ---------------------------------------------------------------------------


class BoardNotificationTriggerSerializer(serializers.ModelSerializer):
    trigger_type_display = serializers.CharField(source="get_trigger_type_display", read_only=True)
    severity_threshold_display = serializers.SerializerMethodField()

    class Meta:
        model = BoardNotificationTrigger
        fields = [
            "id",
            "name",
            "description",
            "trigger_type",
            "trigger_type_display",
            "severity_threshold",
            "severity_threshold_display",
            "concurrent_issue_count",
            "financial_threshold_amount",
            "notification_message_template",
            "recipients",
            "notification_channels",
            "cooldown_hours",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")

    def get_severity_threshold_display(self, obj):
        if obj.severity_threshold:
            return dict(EscalationTier.Severity.choices).get(obj.severity_threshold)
        return None


class BoardNotificationTriggerWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = BoardNotificationTrigger
        fields = [
            "name",
            "description",
            "trigger_type",
            "severity_threshold",
            "concurrent_issue_count",
            "financial_threshold_amount",
            "notification_message_template",
            "recipients",
            "notification_channels",
            "cooldown_hours",
            "is_active",
        ]

    def validate_recipients(self, value):
        return _validate_email_list(value)

    def validate_notification_channels(self, value):
        return _validate_notification_channels(value)

    def validate_cooldown_hours(self, value):
        if value < 1 or value > 168:
            raise serializers.ValidationError("Must be between 1 and 168 hours (7 days).")
        return value

    def validate_concurrent_issue_count(self, value):
        if value is not None and (value < 1 or value > 1000):
            raise serializers.ValidationError("Must be between 1 and 1,000.")
        return value

    def validate_financial_threshold_amount(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("Must be a positive amount.")
        return value

    def validate(self, data):
        tt = data.get("trigger_type", getattr(self.instance, "trigger_type", None))
        if tt == "severity_threshold":
            sev = data.get("severity_threshold", getattr(self.instance, "severity_threshold", ""))
            if not sev:
                raise serializers.ValidationError(
                    {"severity_threshold": "Required for severity threshold triggers."}
                )
        if tt == "concurrent_issues":
            count = data.get("concurrent_issue_count", getattr(self.instance, "concurrent_issue_count", None))
            if not count:
                raise serializers.ValidationError(
                    {"concurrent_issue_count": "Required for concurrent issues triggers."}
                )
        if tt == "financial_impact":
            amt = data.get("financial_threshold_amount", getattr(self.instance, "financial_threshold_amount", None))
            if not amt:
                raise serializers.ValidationError(
                    {"financial_threshold_amount": "Required for financial impact triggers."}
                )
        return data


# ---------------------------------------------------------------------------
# Communication & Branding Settings
# ---------------------------------------------------------------------------


class CommunicationBrandingSettingsSerializer(serializers.ModelSerializer):
    letterhead_paper_size_display = serializers.CharField(
        source="get_letterhead_paper_size_display", read_only=True
    )

    class Meta:
        model = CommunicationBrandingSettings
        fields = [
            "id",
            # Email Branding
            "email_sender_name",
            "email_sender_address",
            "email_reply_to",
            "email_header_html",
            "email_footer_html",
            "email_primary_color",
            "email_logo_url",
            # Notification Branding
            "notification_brand_color",
            "notification_accent_color",
            "notification_logo_url",
            "notification_app_name",
            "notification_include_logo",
            # SMS Configuration
            "sms_sender_id",
            "sms_prefix",
            "sms_opt_out_message",
            "sms_character_limit",
            "sms_enabled",
            # Letterhead
            "letterhead_header_html",
            "letterhead_footer_html",
            "letterhead_paper_size",
            "letterhead_paper_size_display",
            "letterhead_margin_top_mm",
            "letterhead_margin_bottom_mm",
            "letterhead_watermark_text",
            "letterhead_watermark_opacity",
            # Document Footer Disclaimers
            "default_footer_disclaimer",
            "contract_footer_disclaimer",
            "invoice_footer_disclaimer",
            "report_footer_disclaimer",
            # Digital Signature
            "signature_email_subject",
            "signature_email_body",
            "signature_reminder_enabled",
            "signature_reminder_frequency_hours",
            "signature_expiry_days",
            "signature_branding_enabled",
            # Metadata
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_email_primary_color(self, value):
        if value and not value.startswith("#"):
            raise serializers.ValidationError("Must be a valid hex color (e.g. #FF0000).")
        return value

    def validate_notification_brand_color(self, value):
        if value and not value.startswith("#"):
            raise serializers.ValidationError("Must be a valid hex color (e.g. #FF0000).")
        return value

    def validate_notification_accent_color(self, value):
        if value and not value.startswith("#"):
            raise serializers.ValidationError("Must be a valid hex color (e.g. #FF0000).")
        return value

    def validate_sms_character_limit(self, value):
        if value < 50 or value > 1600:
            raise serializers.ValidationError("Must be between 50 and 1,600.")
        return value

    def validate_letterhead_watermark_opacity(self, value):
        if value > 100:
            raise serializers.ValidationError("Must be between 0 and 100.")
        return value

    def validate_signature_reminder_frequency_hours(self, value):
        if value < 1 or value > 720:
            raise serializers.ValidationError("Must be between 1 and 720 hours (30 days).")
        return value

    def validate_signature_expiry_days(self, value):
        if value < 1 or value > 365:
            raise serializers.ValidationError("Must be between 1 and 365 days.")
        return value


# ---------------------------------------------------------------------------
# Platform Edition
# ---------------------------------------------------------------------------


class PlatformEditionListSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformEdition
        fields = [
            "id", "key", "name", "tier_level", "is_custom", "description",
            "max_users", "max_storage_gb", "api_rate_limit_rpm",
            "data_retention_days", "max_projects",
            "support_tier", "support_response_hours", "support_resolution_hours",
            "monthly_price", "annual_price", "currency",
            "is_active",
        ]


class PlatformEditionDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformEdition
        fields = [
            "id", "key", "name", "tier_level", "is_custom", "description",
            "included_modules",
            "max_users", "max_storage_gb", "api_rate_limit_rpm",
            "data_retention_days", "max_projects",
            "support_tier", "support_response_hours", "support_resolution_hours",
            "monthly_price", "annual_price", "currency",
            "is_active", "created_at", "updated_at",
        ]


class FunctionalControlSerializer(serializers.ModelSerializer):
    class Meta:
        model = FunctionalControl
        exclude = ("organization",)
        read_only_fields = ("id", "created_at", "updated_at")


class TaxRateSerializer(serializers.ModelSerializer):
    tax_type_display = serializers.CharField(source="get_tax_type_display", read_only=True)
    applies_to_display = serializers.CharField(source="get_applies_to_display", read_only=True)

    class Meta:
        model = TaxRate
        exclude = ("organization",)
        read_only_fields = ("id", "created_at", "updated_at")


class ProcurementPolicySettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcurementPolicySettings
        exclude = ("organization",)
        read_only_fields = ("id", "created_at", "updated_at")
