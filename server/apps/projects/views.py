import hashlib
import re
from collections import defaultdict, deque
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import Avg, Count, DecimalField, F, Q, Sum, Value
from django.db.models.functions import Coalesce, TruncMonth
from django.utils import timezone
from django_filters import rest_framework as filters
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.mixins import OrgScopedMixin
from apps.documents.models import Document
from apps.hr.models import EmployeeRecord, EquipmentAllocation
from apps.inventory.services import delete_project_cost_transaction, sync_project_cost_entry
from apps.procurement.models import GoodsReceipt, PurchaseOrder, Vendor
from apps.settings.currency import get_default_currency_code
from apps.settings.data_scopes import scope_queryset_by_projects_for_user, scoped_project_queryset_for_user
from apps.settings.permissions import HasRolePermission

from .cache_utils import get_project_summary_cache_version
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
    Project,
    ProjectConsultant,
    ProjectConstructionSchedule,
    ProjectSetupConfig,
    ProjectTeamMember,
    ProjectCostEntry,
    ProjectDailySiteReport,
    ProjectEquipment,
    ProjectExecutionInspection,
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
    ProjectTask,
    ProjectTaskComment,
    ProjectVariationOrder,
    ProjectWorkforceLog,
    ProjectWorkPackage,
    QualityCheckTemplate,
    QualityPlan,
)
from .serializers import (
    MOBILIZATION_MANUAL_CHECKLIST_FIELDS,
    MOBILIZATION_SITE_PREPARATION_FIELD_MAP,
    ProjectConstructionScheduleReadSerializer,
    ProjectConstructionScheduleUpdateSerializer,
    ProjectContractorProfileSerializer,
    ProjectCostEntrySerializer,
    ProjectDailySiteReportPhotoSerializer,
    ProjectDailySiteReportSerializer,
    ProjectDeliveryConfirmationSerializer,
    ProjectDetailSerializer,
    ProjectExecutionInspectionSerializer,
    ProjectFieldEscalationSerializer,
    ProjectListSerializer,
    ProjectMilestoneApprovalDecisionSerializer,
    ProjectMilestoneApprovalRuleSerializer,
    ProjectMilestoneSerializer,
    ProjectPhaseDependencySerializer,
    ProjectPhaseSerializer,
    ProjectPlanningInsightSerializer,
    ProjectRiskRegisterListSerializer,
    ProjectRiskRegisterWriteSerializer,
    ProjectScheduleDelayLogSerializer,
    ProjectSiteMobilizationReadSerializer,
    ProjectSiteMobilizationUpdateSerializer,
    ProjectSupportingAttachmentSerializer,
    ProjectTaskCommentSerializer,
    ProjectTaskSerializer,
    ProjectVariationOrderSerializer,
    ProjectWorkforceLogSerializer,
    ProjectWorkPackageSerializer,
    ProjectWriteSerializer,
    EquipmentDeploymentLogSerializer,
    EquipmentMaintenanceLogSerializer,
    NonConformanceReportDetailSerializer,
    NonConformanceReportListSerializer,
    NonConformanceReportWriteSerializer,
    ConsultantCommunicationLogSerializer,
    ConsultantDeliverableSerializer,
    ConsultantPaymentMilestoneSerializer,
    DesignPhaseSerializer,
    DesignReviewMeetingSerializer,
    DrawingDetailSerializer,
    DrawingListSerializer,
    DrawingRevisionSerializer,
    DrawingWriteSerializer,
    PackageBidderSerializer,
    ProcurementPackageDetailSerializer,
    ProcurementPackageListSerializer,
    ProcurementPackageWriteSerializer,
    ProcurementPlanDetailSerializer,
    ProcurementPlanListSerializer,
    ProcurementPlanWriteSerializer,
    SaleableUnitSerializer,
    SalesPhaseTargetSerializer,
    SalesRevenueForecastDetailSerializer,
    SalesRevenueForecastListSerializer,
    SalesRevenueForecastWriteSerializer,
    StageGateDetailSerializer,
    StageGateListSerializer,
    StageGateWriteSerializer,
    DocumentTransmittalSerializer,
    DocumentVersionSerializer,
    MeetingMinutesArchiveSerializer,
    ProjectDocumentDetailSerializer,
    ProjectDocumentListSerializer,
    ProjectDocumentWriteSerializer,
    ProjectAnnouncementSerializer,
    ProjectDecisionLogSerializer,
    StakeholderUpdateDetailSerializer,
    StakeholderUpdateListSerializer,
    StakeholderUpdateWriteSerializer,
    ProjectReportDetailSerializer,
    ProjectReportListSerializer,
    ProjectReportWriteSerializer,
    ConstructionReportDetailSerializer,
    ConstructionReportListSerializer,
    ConstructionReportWriteSerializer,
    CostCodeBudgetDetailSerializer,
    CostCodeBudgetListSerializer,
    CostCodeBudgetWriteSerializer,
    CostTransactionSerializer,
    RFICommentSerializer,
    RFIDetailSerializer,
    RFIListSerializer,
    RFIWriteSerializer,
    SiteInstructionDetailSerializer,
    SiteInstructionListSerializer,
    SiteInstructionWriteSerializer,
    FinalAccountEntrySerializer,
    ProjectCloseoutDetailSerializer,
    ProjectCloseoutListSerializer,
    ProjectCloseoutWriteSerializer,
    SnagListItemSerializer,
    WarrantyTrackerSerializer,
    PermitQuerySerializer,
    PermitSubmissionSerializer,
    ProjectPermitDetailSerializer,
    ProjectPermitListSerializer,
    ProjectPermitWriteSerializer,
    ProjectConsultantDetailSerializer,
    ProjectConsultantListSerializer,
    ProjectConsultantWriteSerializer,
    DevelopmentBudgetCategorySerializer,
    DevelopmentBudgetDetailSerializer,
    DevelopmentBudgetListSerializer,
    DevelopmentBudgetWriteSerializer,
    FinancingCovenantSerializer,
    FinancingDrawdownSerializer,
    FinancingRepaymentSerializer,
    FinancingSourceDetailSerializer,
    FinancingSourceListSerializer,
    FinancingSourceWriteSerializer,
    FeasibilityStudyDetailSerializer,
    FeasibilityStudyListSerializer,
    FeasibilityStudyWriteSerializer,
    LandAcquisitionDetailSerializer,
    LandAcquisitionListSerializer,
    LandAcquisitionWriteSerializer,
    LandPaymentMilestoneSerializer,
    PipelineOpportunityDetailSerializer,
    PipelineOpportunityListSerializer,
    PipelineOpportunityWriteSerializer,
    ProjectSetupConfigSerializer,
    ProjectSetupInitSerializer,
    ProjectTeamMemberSerializer,
    ProjectEquipmentDetailSerializer,
    ProjectEquipmentListSerializer,
    ProjectEquipmentWriteSerializer,
    QualityCheckTemplateSerializer,
    QualityPlanDetailSerializer,
    QualityPlanListSerializer,
    QualityPlanWriteSerializer,
    HSEIncidentDetailSerializer,
    HSEIncidentListSerializer,
    HSEIncidentWriteSerializer,
    HSEPermitDetailSerializer,
    HSEPermitListSerializer,
    HSEPermitWriteSerializer,
    HSEToolboxTalkDetailSerializer,
    HSEToolboxTalkListSerializer,
    HSEToolboxTalkWriteSerializer,
    CommissioningPlanDetailSerializer,
    CommissioningPlanListSerializer,
    CommissioningPlanWriteSerializer,
    CommissioningPunchItemSerializer,
    TestRecordSerializer,
)
from .site_mobilization import sync_site_mobilization_for_project


def _user_org(request):
    profile = getattr(request.user, "profile", None)
    return getattr(profile, "organization", None)


def _is_superuser(request):
    return request.user.is_superuser


def _scope_to_visible_projects(
    queryset,
    request,
    *,
    project_lookup: str = "id",
    sub_module: str = "projects.projects",
):
    if _is_superuser(request):
        return queryset
    return scope_queryset_by_projects_for_user(
        queryset,
        request.user,
        project_lookup=project_lookup,
        sub_module=sub_module,
    )


PROJECT_SUMMARY_CACHE_TTL_SECONDS = 120


def _sorted_query_hash(query_params) -> str:
    normalized = []
    for key in sorted(query_params.keys()):
        values = sorted(str(value) for value in query_params.getlist(key))
        normalized.extend(f"{key}={value}" for value in values)
    if not normalized:
        return "noquery"
    return hashlib.sha1("&".join(normalized).encode("utf-8")).hexdigest()[:16]


def _project_summary_cache_key(request, scope: str) -> str:
    org = _user_org(request)
    org_id = getattr(org, "id", 0) or 0
    cache_version = get_project_summary_cache_version(org_id)
    query_hash = _sorted_query_hash(request.query_params)
    return (
        f"projects:summary:{scope}:u:{request.user.id}:"
        f"org:{org_id}:super:{int(_is_superuser(request))}:v:{cache_version}:q:{query_hash}"
    )


def _save_supporting_attachment(request, **kwargs):
    serializer = ProjectSupportingAttachmentSerializer(
        data=request.data,
        context={"request": request},
    )
    serializer.is_valid(raise_exception=True)
    if "organization" not in kwargs and "project" in kwargs:
        kwargs["organization"] = kwargs["project"].organization
    serializer.save(uploaded_by=request.user, **kwargs)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


_WORKFORCE_COUNT_FIELDS = (
    "laborers_count",
    "skilled_count",
    "supervisors_count",
    "subcontractors_count",
    "equipment_operators_count",
)


def _sync_workforce_log_from_site_report(site_report, user):
    actor = user if getattr(user, "is_authenticated", False) else None
    workforce_log, created = ProjectWorkforceLog.objects.get_or_create(
        project=site_report.project,
        report_date=site_report.report_date,
        shift=site_report.shift,
        defaults={
            "organization": site_report.organization,
            **{
                field: getattr(site_report, field)
                for field in _WORKFORCE_COUNT_FIELDS
            },
            "created_by": actor,
            "updated_by": actor,
        },
    )
    if created:
        return workforce_log

    update_fields = []
    for field in _WORKFORCE_COUNT_FIELDS:
        value = getattr(site_report, field)
        if getattr(workforce_log, field) != value:
            setattr(workforce_log, field, value)
            update_fields.append(field)

    actor_id = getattr(actor, "id", None)
    if workforce_log.updated_by_id != actor_id:
        workforce_log.updated_by = actor
        update_fields.append("updated_by")

    if update_fields:
        update_fields.append("updated_at")
        workforce_log.save(update_fields=update_fields)
    return workforce_log


def _sync_site_report_from_workforce_log(workforce_log, user):
    actor = user if getattr(user, "is_authenticated", False) else None
    site_report, created = ProjectDailySiteReport.objects.get_or_create(
        project=workforce_log.project,
        report_date=workforce_log.report_date,
        shift=workforce_log.shift,
        defaults={
            "organization": workforce_log.organization,
            **{
                field: getattr(workforce_log, field)
                for field in _WORKFORCE_COUNT_FIELDS
            },
            "created_by": actor,
            "updated_by": actor,
        },
    )
    if created:
        return site_report

    update_fields = []
    for field in _WORKFORCE_COUNT_FIELDS:
        value = getattr(workforce_log, field)
        if getattr(site_report, field) != value:
            setattr(site_report, field, value)
            update_fields.append(field)

    actor_id = getattr(actor, "id", None)
    if site_report.updated_by_id != actor_id:
        site_report.updated_by = actor
        update_fields.append("updated_by")

    if update_fields:
        update_fields.append("updated_at")
        site_report.save(update_fields=update_fields)
    return site_report


def _sync_inspection_closed_at(inspection):
    if (
        inspection.status == ProjectExecutionInspection.Status.CLOSED
        and not inspection.closed_at
    ):
        inspection.closed_at = timezone.now()
        inspection.save(update_fields=["closed_at", "updated_at"])
    elif (
        inspection.status != ProjectExecutionInspection.Status.CLOSED
        and inspection.closed_at is not None
    ):
        inspection.closed_at = None
        inspection.save(update_fields=["closed_at", "updated_at"])


UserModel = get_user_model()


def _sync_task_sla_breach(task):
    if task.completed_date or not task.sla_target_at:
        if task.sla_breached_at is not None:
            task.sla_breached_at = None
            task.save(update_fields=["sla_breached_at", "updated_at"])
        return

    now = timezone.now()
    if now >= task.sla_target_at and task.sla_breached_at is None:
        task.sla_breached_at = now
        task.save(update_fields=["sla_breached_at", "updated_at"])
    elif now < task.sla_target_at and task.sla_breached_at is not None:
        task.sla_breached_at = None
        task.save(update_fields=["sla_breached_at", "updated_at"])


def _phase_duration_days(phase):
    start = phase.revised_start_date or phase.planned_start_date
    end = phase.revised_end_date or phase.planned_end_date
    if start and end and end >= start:
        return max(1, (end - start).days + 1)
    return 1


def _compute_critical_path(phase_list, dependency_list):
    phase_ids = [phase.id for phase in phase_list]
    if not phase_ids:
        return set(), {}

    durations = {phase.id: _phase_duration_days(phase) for phase in phase_list}
    indegree = {pid: 0 for pid in phase_ids}
    edges = defaultdict(list)
    reverse_edges = defaultdict(list)

    for dependency in dependency_list:
        pred = dependency.predecessor_phase_id
        succ = dependency.successor_phase_id
        if pred not in indegree or succ not in indegree:
            continue
        edges[pred].append((succ, dependency.lag_days))
        reverse_edges[succ].append((pred, dependency.lag_days))
        indegree[succ] += 1

    queue = deque(sorted(pid for pid, value in indegree.items() if value == 0))
    topo = []
    while queue:
        node = queue.popleft()
        topo.append(node)
        for succ, _lag in edges[node]:
            indegree[succ] -= 1
            if indegree[succ] == 0:
                queue.append(succ)

    # Fallback for cyclic graphs: keep deterministic ordering and skip strict CPM math.
    if len(topo) != len(phase_ids):
        topo = phase_ids

    earliest_start = {}
    earliest_finish = {}
    for node in topo:
        constraints = [
            earliest_finish[pred] + lag
            for pred, lag in reverse_edges[node]
            if pred in earliest_finish
        ]
        es = max([0, *constraints])
        ef = es + durations[node]
        earliest_start[node] = es
        earliest_finish[node] = ef

    project_duration = max(earliest_finish.values()) if earliest_finish else 0
    latest_finish = {}
    latest_start = {}
    for node in reversed(topo):
        successor_constraints = [
            latest_start[succ] - lag
            for succ, lag in edges[node]
            if succ in latest_start
        ]
        lf = min(successor_constraints) if successor_constraints else project_duration
        ls = lf - durations[node]
        latest_finish[node] = lf
        latest_start[node] = ls

    slack_days = {
        node: max(0, latest_start.get(node, 0) - earliest_start.get(node, 0))
        for node in topo
    }
    critical_nodes = {node for node, slack in slack_days.items() if slack == 0}
    return critical_nodes, slack_days


CONSTRUCTION_SCHEDULE_PHASE_EXAMPLES = [
    "Site Clearing",
    "Excavation",
    "Foundation",
    "Structure",
    "Masonry",
    "Roofing",
    "MEP Installation",
    "Interior Finishing",
    "External Works",
    "Landscaping",
]


def _date_to_iso(value):
    return value.isoformat() if value else None


def _schedule_duration_days(start_date, end_date):
    if not start_date or not end_date or end_date < start_date:
        return None
    return (end_date - start_date).days + 1


def _task_assignee_label(task):
    if task.assigned_user_id:
        full_name = task.assigned_user.get_full_name().strip()
        if full_name:
            return full_name
        if task.assigned_user.email:
            return task.assigned_user.email
        return task.assigned_user.username
    if task.assigned_to:
        return task.assigned_to
    return "Unassigned"


def _phase_progress_percent(phase, tasks_for_phase):
    if tasks_for_phase:
        completed = sum(1 for task in tasks_for_phase if task.status == ProjectTask.Status.COMPLETED)
        return round((completed / len(tasks_for_phase)) * 100, 2)
    if phase.status == ProjectPhase.Status.COMPLETED:
        return 100.0
    if phase.status == ProjectPhase.Status.IN_PROGRESS:
        return 50.0
    return 0.0


def _build_construction_schedule_payload(project, schedule):
    phases = list(
        project.phases.all().order_by("sort_order", "id")
    )
    dependencies = list(
        ProjectPhaseDependency.objects.filter(project=project)
        .select_related("predecessor_phase", "successor_phase")
        .order_by("predecessor_phase_id", "successor_phase_id", "id")
    )
    critical_path_phase_ids, slack_by_phase = _compute_critical_path(phases, dependencies)

    tasks = list(
        ProjectTask.objects.filter(phase__project=project)
        .select_related("phase", "assigned_user")
        .order_by("due_date", "sort_order", "id")
    )
    task_total = len(tasks)
    task_completed = sum(1 for task in tasks if task.status == ProjectTask.Status.COMPLETED)
    task_completion_percent = round((task_completed / task_total) * 100, 2) if task_total else 0.0

    phase_tasks_map = defaultdict(list)
    for task in tasks:
        phase_tasks_map[task.phase_id].append(task)

    phase_schedule_rows = []
    for phase in phases:
        phase_tasks = phase_tasks_map.get(phase.id, [])
        planned_start = phase.revised_start_date or phase.planned_start_date or phase.baseline_start_date
        planned_end = phase.revised_end_date or phase.planned_end_date or phase.baseline_end_date
        duration_days = _schedule_duration_days(planned_start, planned_end)
        assigned_tasks_count = sum(
            1 for task in phase_tasks if task.assigned_user_id or (task.assigned_to or "").strip()
        )

        phase_schedule_rows.append(
            {
                "phase_id": phase.id,
                "phase_name": phase.name,
                "status": phase.status,
                "planned_start_date": _date_to_iso(planned_start),
                "planned_end_date": _date_to_iso(planned_end),
                "actual_start_date": _date_to_iso(phase.actual_start_date),
                "actual_end_date": _date_to_iso(phase.actual_end_date),
                "duration_days": duration_days,
                "planned_budget": float(phase.planned_budget or 0),
                "actual_cost": float(phase.actual_cost or 0),
                "task_count": len(phase_tasks),
                "assigned_tasks_count": assigned_tasks_count,
                "unassigned_tasks_count": max(0, len(phase_tasks) - assigned_tasks_count),
                "progress_percent": _phase_progress_percent(phase, phase_tasks),
                "slack_days": int(slack_by_phase.get(phase.id, 0)),
                "is_critical_path": phase.id in critical_path_phase_ids,
            }
        )

    phase_name_lookup = {phase.id: phase.name for phase in phases}
    critical_path_rows = [
        {
            "phase_id": phase_id,
            "phase_name": phase_name_lookup.get(phase_id, f"Phase {phase_id}"),
            "slack_days": int(slack_by_phase.get(phase_id, 0)),
        }
        for phase_id in sorted(critical_path_phase_ids)
    ]

    project_start_candidates = [project.start_date] + [
        phase.revised_start_date or phase.planned_start_date or phase.baseline_start_date
        for phase in phases
    ]
    project_start_candidates = [candidate for candidate in project_start_candidates if candidate]

    project_end_candidates = [project.target_end_date] + [
        phase.revised_end_date or phase.planned_end_date or phase.baseline_end_date
        for phase in phases
    ]
    project_end_candidates = [candidate for candidate in project_end_candidates if candidate]

    planned_project_start = min(project_start_candidates) if project_start_candidates else None
    planned_project_end = max(project_end_candidates) if project_end_candidates else None

    today = timezone.localdate()
    lookahead_window_days = int(schedule.lookahead_window_days or 21)
    lookahead_end = today + timedelta(days=lookahead_window_days)

    lookahead_rows = []
    overdue_open_tasks = 0
    for task in tasks:
        if task.status == ProjectTask.Status.COMPLETED:
            continue
        if task.due_date and task.due_date < today:
            overdue_open_tasks += 1
        if not task.due_date or not (today <= task.due_date <= lookahead_end):
            continue

        predecessor_count = len(task.predecessors) if isinstance(task.predecessors, list) else 0
        lookahead_rows.append(
            {
                "task_id": task.id,
                "task_name": task.name,
                "phase_id": task.phase_id,
                "phase_name": task.phase.name if task.phase_id else "",
                "status": task.status,
                "priority": task.priority,
                "due_date": _date_to_iso(task.due_date),
                "assignee": _task_assignee_label(task),
                "dependency_count": predecessor_count,
            }
        )

    dependency_rows = []
    for dependency in dependencies:
        dependency_rows.append(
            {
                "scope": "phase",
                "from": dependency.predecessor_phase.name,
                "to": dependency.successor_phase.name,
                "dependency_type": dependency.dependency_type,
                "lag_days": dependency.lag_days,
            }
        )

    for task in tasks:
        if not isinstance(task.predecessors, list):
            continue
        for predecessor in task.predecessors:
            if not isinstance(predecessor, dict):
                continue
            lag_days = predecessor.get("lag_days", 0)
            try:
                lag_days = int(lag_days)
            except (TypeError, ValueError):
                lag_days = 0
            dependency_rows.append(
                {
                    "scope": "task",
                    "from": (
                        predecessor.get("task")
                        or predecessor.get("task_name")
                        or predecessor.get("name")
                        or "Upstream task"
                    ),
                    "to": task.name,
                    "dependency_type": predecessor.get("dependency_type") or "fs",
                    "lag_days": lag_days,
                }
            )

    assigned_user_ids = sorted({task.assigned_user_id for task in tasks if task.assigned_user_id})
    assigned_user_labels = sorted(
        {
            _task_assignee_label(task)
            for task in tasks
            if task.assigned_user_id or (task.assigned_to or "").strip()
        }
    )

    open_tasks = [
        task
        for task in tasks
        if task.status in (ProjectTask.Status.PENDING, ProjectTask.Status.IN_PROGRESS)
    ]
    unassigned_open_tasks = sum(
        1 for task in open_tasks if not task.assigned_user_id and not (task.assigned_to or "").strip()
    )

    active_employee_count = EmployeeRecord.objects.filter(
        organization=project.organization,
        employment_status=EmployeeRecord.EmploymentStatus.ACTIVE,
    ).count()

    equipment_qs = EquipmentAllocation.objects.filter(organization=project.organization)
    if assigned_user_ids:
        equipment_qs = equipment_qs.filter(employee__user_id__in=assigned_user_ids)
    else:
        equipment_qs = equipment_qs.none()

    allocated_equipment_count = equipment_qs.filter(
        status=EquipmentAllocation.Status.ALLOCATED
    ).count()
    pending_equipment_count = equipment_qs.filter(
        status=EquipmentAllocation.Status.PENDING
    ).count()

    latest_workforce_log = (
        ProjectWorkforceLog.objects.filter(project=project)
        .order_by("-report_date", "-id")
        .first()
    )
    site_workers_count = 0
    if latest_workforce_log:
        site_workers_count = (
            latest_workforce_log.laborers_count
            + latest_workforce_log.skilled_count
            + latest_workforce_log.supervisors_count
            + latest_workforce_log.subcontractors_count
            + latest_workforce_log.equipment_operators_count
        )

    delivery_open_statuses = [
        PurchaseOrder.Status.APPROVED,
        PurchaseOrder.Status.ISSUED,
        PurchaseOrder.Status.PARTIALLY_RECEIVED,
    ]
    project_purchase_orders = PurchaseOrder.objects.filter(project=project)
    upcoming_deliveries = project_purchase_orders.filter(
        status__in=delivery_open_statuses,
        expected_delivery_date__gte=today,
    ).count()
    overdue_deliveries = project_purchase_orders.filter(
        status__in=delivery_open_statuses,
        expected_delivery_date__lt=today,
    ).count()
    received_deliveries = project_purchase_orders.filter(
        status=PurchaseOrder.Status.RECEIVED,
    ).count()
    goods_receipts_logged = GoodsReceipt.objects.filter(
        purchase_order__project=project,
        status__in=[GoodsReceipt.Status.ACCEPTED, GoodsReceipt.Status.PARTIALLY_ACCEPTED],
    ).count()

    serialized_schedule = ProjectConstructionScheduleReadSerializer(schedule).data
    serialized_schedule["example_phases"] = [
        {
            "name": phase_name,
            "present": any(phase.name.strip().lower() == phase_name.lower() for phase in phases),
        }
        for phase_name in CONSTRUCTION_SCHEDULE_PHASE_EXAMPLES
    ]
    serialized_schedule["master_schedule"] = {
        "planned_start_date": _date_to_iso(planned_project_start),
        "planned_end_date": _date_to_iso(planned_project_end),
        "actual_end_date": _date_to_iso(project.actual_end_date),
        "duration_days": _schedule_duration_days(planned_project_start, planned_project_end),
        "phase_count": len(phases),
        "task_count": task_total,
        "task_completion_percent": task_completion_percent,
        "critical_phase_count": len(critical_path_rows),
    }
    serialized_schedule["phase_schedules"] = phase_schedule_rows
    serialized_schedule["lookahead_schedules"] = {
        "window_days": lookahead_window_days,
        "start_date": _date_to_iso(today),
        "end_date": _date_to_iso(lookahead_end),
        "tasks": lookahead_rows,
        "overdue_open_tasks": overdue_open_tasks,
    }
    serialized_schedule["task_dependencies"] = dependency_rows
    serialized_schedule["critical_path"] = {
        "phase_ids": [row["phase_id"] for row in critical_path_rows],
        "phases": critical_path_rows,
        "total_duration_days": sum(
            _phase_duration_days(phase) for phase in phases if phase.id in critical_path_phase_ids
        ),
    }
    serialized_schedule["resource_assignments"] = {
        "project_manager": project.project_manager or "",
        "assigned_user_count": len(assigned_user_ids),
        "assigned_people": assigned_user_labels,
        "open_tasks_count": len(open_tasks),
        "unassigned_open_tasks": unassigned_open_tasks,
        "site_workers_count": site_workers_count,
        "equipment_allocated_count": allocated_equipment_count,
    }
    serialized_schedule["linked_sources"] = {
        "procurement_deliveries": {
            "upcoming": upcoming_deliveries,
            "overdue": overdue_deliveries,
            "received": received_deliveries,
            "goods_receipts_logged": goods_receipts_logged,
        },
        "labour_availability": {
            "active_employees": active_employee_count,
            "assigned_to_schedule": len(assigned_user_ids),
            "unassigned_open_tasks": unassigned_open_tasks,
        },
        "equipment_scheduling": {
            "allocated": allocated_equipment_count,
            "pending": pending_equipment_count,
        },
    }
    return serialized_schedule


class ProjectFilter(filters.FilterSet):
    started_after = filters.DateFilter(field_name="start_date", lookup_expr="gte")
    started_before = filters.DateFilter(field_name="start_date", lookup_expr="lte")
    target_before = filters.DateFilter(field_name="target_end_date", lookup_expr="lte")

    class Meta:
        model = Project
        fields = ["status", "property", "risk_rating", "compliance_status", "project_type", "land_status"]


_PROJECT_ACTION_MAP = {
    "list": "view", "retrieve": "view", "create": "create",
    "update": "edit", "partial_update": "edit", "destroy": "delete",
    "timeline": "view", "summary": "view", "setup_options": "view",
    "construction_site_overview": "view",
    "construction_site_mobilization": "view",
    "construction_schedule": "view",
    "provision_role_library": "edit",
    "comments": "view", "upload_supporting_file": "create",
    "upload_photo": "create", "submit_approval": "approve",
    "decide_approval": "approve",
}


class ProjectPlanningInsightViewSet(OrgScopedMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    queryset = ProjectPlanningInsight.objects.all()
    serializer_class = ProjectPlanningInsightSerializer
    filterset_fields = ["insight_type", "source_module", "is_active", "area_name"]
    ordering_fields = [
        "updated_at",
        "created_at",
        "demand_share_percent",
        "lead_count",
        "qualified_lead_count",
        "won_lead_count",
    ]
    ordering = ["-is_active", "-demand_share_percent", "-updated_at"]


class ProjectViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    queryset = Project.objects.all()
    filterset_class = ProjectFilter
    search_fields = ["name", "description", "project_manager", "location", "spv_entity"]
    ordering_fields = [
        "name",
        "created_at",
        "start_date",
        "target_end_date",
        "status",
        "risk_rating",
        "compliance_score",
        "compliance_status",
        "compliance_last_evaluated_at",
    ]
    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = (
            super().get_queryset()
            .select_related("property")
            .prefetch_related("phases")
            .annotate(phase_count=Count("phases"))
        )
        return scoped_project_queryset_for_user(
            queryset,
            self.request.user,
            sub_module=self.rbac_sub_module,
        )

    def get_permissions(self):
        if self.action in ("construction_site_mobilization", "construction_schedule"):
            self.rbac_action = "edit" if self.request.method in ("PATCH", "PUT") else "view"
        return super().get_permissions()

    def perform_create(self, serializer):
        from apps.settings.quotas import check_resource_quota

        org = self._resolve_request_org()
        check_resource_quota(org, Project, "max_projects", "projects")
        super().perform_create(serializer)

    def get_serializer_class(self):
        if self.action == "list":
            return ProjectListSerializer
        if self.action in ("create", "update", "partial_update"):
            return ProjectWriteSerializer
        return ProjectDetailSerializer

    @action(detail=True, methods=["get"])
    def timeline(self, request, pk=None):
        """Return phases + milestones for Gantt visualization."""
        project = self.get_object()
        phases = project.phases.prefetch_related(
            "milestones__approval_decisions__approver",
            "milestones__approval_decisions__approver_role",
        ).all()
        dependencies = ProjectPhaseDependency.objects.filter(project=project).select_related(
            "predecessor_phase",
            "successor_phase",
        )
        critical_path_phase_ids, slack_by_phase = _compute_critical_path(phases, dependencies)
        return Response({
            "project": {
                "id": project.id,
                "name": project.name,
                "start_date": project.start_date,
                "target_end_date": project.target_end_date,
            },
            "dependencies": [
                {
                    "id": dependency.id,
                    "predecessor_phase_id": dependency.predecessor_phase_id,
                    "predecessor_phase_name": dependency.predecessor_phase.name,
                    "successor_phase_id": dependency.successor_phase_id,
                    "successor_phase_name": dependency.successor_phase.name,
                    "dependency_type": dependency.dependency_type,
                    "lag_days": dependency.lag_days,
                }
                for dependency in dependencies
            ],
            "critical_path_phase_ids": sorted(critical_path_phase_ids),
            "phases": [
                {
                    "id": p.id,
                    "name": p.name,
                    "status": p.status,
                    "baseline_start_date": p.baseline_start_date,
                    "baseline_end_date": p.baseline_end_date,
                    "revised_start_date": p.revised_start_date,
                    "revised_end_date": p.revised_end_date,
                    "schedule_revision_reason": p.schedule_revision_reason,
                    "planned_start_date": p.planned_start_date,
                    "planned_end_date": p.planned_end_date,
                    "actual_start_date": p.actual_start_date,
                    "actual_end_date": p.actual_end_date,
                    "slack_days": slack_by_phase.get(p.id),
                    "is_critical_path": p.id in critical_path_phase_ids,
                    "milestones": [
                        {
                            "id": m.id,
                            "name": m.name,
                            "baseline_target_date": m.baseline_target_date,
                            "revised_target_date": m.revised_target_date,
                            "schedule_revision_reason": m.schedule_revision_reason,
                            "target_date": m.target_date,
                            "completed_date": m.completed_date,
                            "is_completed": m.is_completed,
                            "approval_required": m.approval_required,
                            "approval_status": m.approval_status,
                            "approved_at": m.approved_at,
                            "approved_by_id": m.approved_by_id,
                            "approvals": [
                                {
                                    "id": decision.id,
                                    "decision": decision.decision,
                                    "comments": decision.comments,
                                    "decided_at": decision.decided_at,
                                    "approver_id": decision.approver_id,
                                    "approver_name": (
                                        decision.approver.get_full_name()
                                        if decision.approver_id else None
                                    ),
                                    "approver_role_id": decision.approver_role_id,
                                    "approver_role_name": (
                                        decision.approver_role.name
                                        if decision.approver_role_id else None
                                    ),
                                }
                                for decision in m.approval_decisions.all()
                            ],
                        }
                        for m in p.milestones.all()
                    ],
                }
                for p in phases
            ],
        })

    @action(detail=False, methods=["get"], url_path="construction/site-overview")
    def construction_site_overview(self, request):
        cache_key = _project_summary_cache_key(request, "construction-site-overview")
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        def _parse_date_param(value, fallback):
            if not value:
                return fallback
            try:
                return date.fromisoformat(str(value))
            except ValueError:
                return fallback

        def _to_float(value):
            return float(value or 0)

        today = timezone.localdate()
        default_start_date = today - timedelta(days=90)
        requested_start = _parse_date_param(
            request.query_params.get("start_date"),
            default_start_date,
        )
        requested_end = _parse_date_param(
            request.query_params.get("end_date"),
            today,
        )
        if requested_start > requested_end:
            requested_start, requested_end = requested_end, requested_start

        visible_projects_qs = scoped_project_queryset_for_user(
            Project.objects.order_by("name"),
            request.user,
            sub_module=self.rbac_sub_module,
        )
        project_options = list(
            visible_projects_qs.values("id", "name")[:500]
        )

        project_id_param = request.query_params.get("project")
        selected_project_id = None
        selected_projects_qs = visible_projects_qs
        if project_id_param:
            try:
                selected_project_id = int(project_id_param)
            except (TypeError, ValueError):
                return Response(
                    {"detail": "project must be a valid integer id."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            selected_projects_qs = selected_projects_qs.filter(id=selected_project_id)

        selected_projects = list(selected_projects_qs.values("id", "name"))
        project_ids = [row["id"] for row in selected_projects]

        zero_payload = {
            "filters": {
                "project": selected_project_id,
                "start_date": requested_start.isoformat(),
                "end_date": requested_end.isoformat(),
            },
            "currency_code": get_default_currency_code(),
            "projects": project_options,
            "kpis": {
                "project_progress_percent": 0.0,
                "schedule_variance_days": 0.0,
                "cost_variance_amount": 0.0,
                "cost_variance_percent": 0.0,
                "open_rfis": 0,
                "pending_inspections": 0,
                "safety_incidents": 0,
                "material_shortages": 0,
                "workforce_count": 0,
                "equipment_utilization_percent": 0.0,
                "quality_issues": 0,
                "delayed_tasks": 0,
                "contractor_performance_score": 0.0,
                "contractor_performance_band": "watch",
            },
            "widgets": {
                "progress_curve": [],
                "cost_vs_budget": [],
                "labour_distribution": [],
                "material_consumption": [],
                "safety_index": [],
                "inspection_status": [],
            },
        }
        if not project_ids:
            cache.set(cache_key, zero_payload, timeout=PROJECT_SUMMARY_CACHE_TTL_SECONDS)
            return Response(zero_payload)

        open_escalation_statuses = [
            ProjectFieldEscalation.Status.OPEN,
            ProjectFieldEscalation.Status.ACKNOWLEDGED,
            ProjectFieldEscalation.Status.IN_PROGRESS,
        ]
        safety_issue_types = [
            ProjectFieldEscalation.IssueType.SAFETY_INCIDENT,
            ProjectFieldEscalation.IssueType.NEAR_MISS,
            ProjectFieldEscalation.IssueType.ACCIDENT_INJURY,
        ]
        quality_issue_types = [
            ProjectFieldEscalation.IssueType.QUALITY_DEFECT,
            ProjectFieldEscalation.IssueType.REWORK_REQUIRED,
            ProjectFieldEscalation.IssueType.INSPECTION_FAILURE,
            ProjectFieldEscalation.IssueType.TEST_FAILURE,
            ProjectFieldEscalation.IssueType.HANDOVER_DEFECT,
        ]
        contractor_issue_types = [
            ProjectFieldEscalation.IssueType.VENDOR_NON_PERFORMANCE,
            ProjectFieldEscalation.IssueType.SUBCONTRACTOR_NON_PERFORMANCE,
        ]

        reports_range_qs = ProjectDailySiteReport.objects.filter(
            project_id__in=project_ids,
            report_date__range=(requested_start, requested_end),
        )
        workforce_range_qs = ProjectWorkforceLog.objects.filter(
            project_id__in=project_ids,
            report_date__range=(requested_start, requested_end),
        )
        inspections_range_qs = ProjectExecutionInspection.objects.filter(
            project_id__in=project_ids,
            inspected_on__range=(requested_start, requested_end),
        )
        escalations_range_qs = ProjectFieldEscalation.objects.filter(
            project_id__in=project_ids,
            issue_date__range=(requested_start, requested_end),
        )

        escalations_snapshot_qs = ProjectFieldEscalation.objects.filter(
            project_id__in=project_ids,
            issue_date__lte=requested_end,
        )
        inspections_snapshot_qs = ProjectExecutionInspection.objects.filter(
            project_id__in=project_ids,
            inspected_on__lte=requested_end,
        )

        schedule_variance_days = _to_float(
            ProjectScheduleDelayLog.objects.filter(
                project_id__in=project_ids,
                delay_date__range=(requested_start, requested_end),
            ).aggregate(
                total=Coalesce(
                    Sum("impact_days"),
                    Value(0),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                )
            )["total"]
        )

        planned_budget_total = _to_float(
            ProjectPhase.objects.filter(
                project_id__in=project_ids,
            ).aggregate(
                total=Coalesce(
                    Sum("planned_budget"),
                    Value(0),
                    output_field=DecimalField(max_digits=18, decimal_places=2),
                )
            )["total"]
        )
        actual_cost_total = _to_float(
            ProjectCostEntry.objects.filter(
                phase__project_id__in=project_ids,
                date__lte=requested_end,
            ).aggregate(
                total=Coalesce(
                    Sum("amount"),
                    Value(0),
                    output_field=DecimalField(max_digits=18, decimal_places=2),
                )
            )["total"]
        )
        cost_variance_amount = actual_cost_total - planned_budget_total
        cost_variance_percent = (
            (cost_variance_amount / planned_budget_total) * 100
            if planned_budget_total > 0
            else 0.0
        )

        progress_curve = [
            {
                "date": row["report_date"].isoformat(),
                "progress_percent": round(_to_float(row["progress_percent"]), 2),
            }
            for row in reports_range_qs.values("report_date")
            .annotate(progress_percent=Avg("progress_percent"))
            .order_by("report_date")
        ]
        milestone_totals = ProjectMilestone.objects.filter(
            phase__project_id__in=project_ids,
        ).aggregate(
            total=Count("id"),
            completed=Count(
                "id",
                filter=Q(is_completed=True) | Q(completed_date__isnull=False),
            ),
        )
        total_milestones = int(milestone_totals.get("total") or 0)
        completed_milestones = int(milestone_totals.get("completed") or 0)
        milestone_progress_percent = (
            round((completed_milestones / total_milestones) * 100, 2)
            if total_milestones > 0
            else 0.0
        )

        report_progress_percent = (
            progress_curve[-1]["progress_percent"]
            if progress_curve
            else 0.0
        )
        project_progress_percent = max(report_progress_percent, milestone_progress_percent)

        workforce_latest = ProjectWorkforceLog.objects.filter(
            project_id__in=project_ids,
            report_date__lte=requested_end,
        ).order_by("-report_date", "-created_at").first()
        workforce_count = 0
        if workforce_latest is not None:
            workforce_count = (
                workforce_latest.laborers_count
                + workforce_latest.skilled_count
                + workforce_latest.supervisors_count
                + workforce_latest.subcontractors_count
                + workforce_latest.equipment_operators_count
            )

        workforce_totals = workforce_range_qs.aggregate(
            laborers=Coalesce(Sum("laborers_count"), Value(0)),
            skilled=Coalesce(Sum("skilled_count"), Value(0)),
            supervisors=Coalesce(Sum("supervisors_count"), Value(0)),
            subcontractors=Coalesce(Sum("subcontractors_count"), Value(0)),
            equipment_operators=Coalesce(Sum("equipment_operators_count"), Value(0)),
        )
        labour_distribution = [
            {"label": "Laborers", "count": int(workforce_totals["laborers"] or 0)},
            {"label": "Skilled", "count": int(workforce_totals["skilled"] or 0)},
            {"label": "Supervisors", "count": int(workforce_totals["supervisors"] or 0)},
            {"label": "Subcontractors", "count": int(workforce_totals["subcontractors"] or 0)},
            {
                "label": "Equipment Operators",
                "count": int(workforce_totals["equipment_operators"] or 0),
            },
        ]
        total_labour_for_utilization = sum(item["count"] for item in labour_distribution)
        equipment_utilization_percent = (
            (int(workforce_totals["equipment_operators"] or 0) / total_labour_for_utilization) * 100
            if total_labour_for_utilization > 0
            else 0.0
        )

        open_rfis = escalations_snapshot_qs.filter(
            issue_type=ProjectFieldEscalation.IssueType.RFI_PENDING,
            status__in=open_escalation_statuses,
        ).count()
        material_shortages = escalations_snapshot_qs.filter(
            issue_type=ProjectFieldEscalation.IssueType.MATERIAL_SHORTAGE,
            status__in=open_escalation_statuses,
        ).count()
        safety_incidents = escalations_range_qs.filter(
            issue_type__in=safety_issue_types
        ).count()
        pending_inspections = inspections_snapshot_qs.filter(
            status__in=[
                ProjectExecutionInspection.Status.PLANNED,
                ProjectExecutionInspection.Status.IN_PROGRESS,
                ProjectExecutionInspection.Status.BLOCKED,
            ]
        ).count()
        quality_issues = (
            escalations_snapshot_qs.filter(
                Q(issue_category=ProjectFieldEscalation.IssueCategory.QUALITY)
                | Q(issue_type__in=quality_issue_types),
                status__in=open_escalation_statuses,
            ).count()
            + inspections_snapshot_qs.filter(
                status=ProjectExecutionInspection.Status.FAILED
            ).count()
        )
        delayed_tasks = ProjectTask.objects.filter(
            phase__project_id__in=project_ids,
            due_date__isnull=False,
            due_date__lt=today,
        ).exclude(status=ProjectTask.Status.COMPLETED).count()

        delivery_qs = GoodsReceipt.objects.filter(
            purchase_order__project_id__in=project_ids,
            received_date__range=(requested_start, requested_end),
        )
        late_deliveries = delivery_qs.filter(
            purchase_order__expected_delivery_date__isnull=False,
            received_date__gt=F("purchase_order__expected_delivery_date"),
        ).count()
        total_deliveries = delivery_qs.count()
        on_time_deliveries = max(total_deliveries - late_deliveries, 0)
        on_time_rate = (
            (on_time_deliveries / total_deliveries) * 100
            if total_deliveries > 0
            else 100.0
        )
        open_contractor_issues = escalations_snapshot_qs.filter(
            issue_type__in=contractor_issue_types,
            status__in=open_escalation_statuses,
        ).count()
        contractor_performance_score = max(
            0.0,
            min(
                100.0,
                round(on_time_rate - min(open_contractor_issues * 7.5, 40), 2),
            ),
        )
        if contractor_performance_score >= 85:
            contractor_performance_band = "strong"
        elif contractor_performance_score >= 65:
            contractor_performance_band = "watch"
        else:
            contractor_performance_band = "weak"

        planned_by_project = {
            row["project_id"]: _to_float(row["planned_total"])
            for row in ProjectPhase.objects.filter(project_id__in=project_ids)
            .values("project_id")
            .annotate(
                planned_total=Coalesce(
                    Sum("planned_budget"),
                    Value(0),
                    output_field=DecimalField(max_digits=18, decimal_places=2),
                )
            )
        }
        actual_by_project = {
            row["phase__project_id"]: _to_float(row["actual_total"])
            for row in ProjectCostEntry.objects.filter(
                phase__project_id__in=project_ids,
                date__lte=requested_end,
            )
            .values("phase__project_id")
            .annotate(
                actual_total=Coalesce(
                    Sum("amount"),
                    Value(0),
                    output_field=DecimalField(max_digits=18, decimal_places=2),
                )
            )
        }
        cost_vs_budget = []
        for project in selected_projects:
            project_id = project["id"]
            planned_value = planned_by_project.get(project_id, 0.0)
            actual_value = actual_by_project.get(project_id, 0.0)
            if planned_value == 0 and actual_value == 0:
                continue
            cost_vs_budget.append(
                {
                    "project_id": project_id,
                    "project_name": project["name"],
                    "planned": round(planned_value, 2),
                    "actual": round(actual_value, 2),
                }
            )
        cost_vs_budget.sort(key=lambda row: max(row["planned"], row["actual"]), reverse=True)
        cost_vs_budget = cost_vs_budget[:8]

        material_consumption = [
            {
                "period": row["period"].isoformat(),
                "amount": round(_to_float(row["amount"]), 2),
            }
            for row in ProjectCostEntry.objects.filter(
                phase__project_id__in=project_ids,
                category=ProjectCostEntry.Category.MATERIALS,
                date__range=(requested_start, requested_end),
            )
            .annotate(period=TruncMonth("date"))
            .values("period")
            .annotate(
                amount=Coalesce(
                    Sum("amount"),
                    Value(0),
                    output_field=DecimalField(max_digits=18, decimal_places=2),
                )
            )
            .order_by("period")
        ]

        safety_incidents_by_period = {
            row["period"].isoformat(): int(row["incidents"])
            for row in escalations_range_qs.filter(issue_type__in=safety_issue_types)
            .annotate(period=TruncMonth("issue_date"))
            .values("period")
            .annotate(incidents=Count("id"))
            .order_by("period")
        }
        workforce_by_period = {}
        workforce_by_period_rows = (
            workforce_range_qs
            .annotate(period=TruncMonth("report_date"))
            .values("period")
            .annotate(
                laborers=Coalesce(Sum("laborers_count"), Value(0)),
                skilled=Coalesce(Sum("skilled_count"), Value(0)),
                supervisors=Coalesce(Sum("supervisors_count"), Value(0)),
                subcontractors=Coalesce(Sum("subcontractors_count"), Value(0)),
                equipment_operators=Coalesce(Sum("equipment_operators_count"), Value(0)),
            )
            .order_by("period")
        )
        for row in workforce_by_period_rows:
            key = row["period"].isoformat()
            workforce_by_period[key] = (
                int(row["laborers"] or 0)
                + int(row["skilled"] or 0)
                + int(row["supervisors"] or 0)
                + int(row["subcontractors"] or 0)
                + int(row["equipment_operators"] or 0)
            )

        safety_periods = sorted(set(safety_incidents_by_period) | set(workforce_by_period))
        safety_index = []
        for period in safety_periods:
            incidents = safety_incidents_by_period.get(period, 0)
            workforce_total = workforce_by_period.get(period, 0)
            index_value = 100.0
            if incidents > 0:
                index_value = max(
                    0.0,
                    min(
                        100.0,
                        round(100 - ((incidents * 1000) / max(workforce_total, 1)), 2),
                    ),
                )
            safety_index.append(
                {
                    "period": period,
                    "index": index_value,
                    "incidents": incidents,
                    "workforce_count": workforce_total,
                }
            )

        status_order = [
            ProjectExecutionInspection.Status.PLANNED,
            ProjectExecutionInspection.Status.IN_PROGRESS,
            ProjectExecutionInspection.Status.PASSED,
            ProjectExecutionInspection.Status.FAILED,
            ProjectExecutionInspection.Status.BLOCKED,
            ProjectExecutionInspection.Status.CLOSED,
        ]
        inspection_counts = {
            row["status"]: int(row["count"])
            for row in inspections_range_qs.values("status").annotate(count=Count("id"))
        }
        inspection_status = [
            {"status": status_key, "count": inspection_counts.get(status_key, 0)}
            for status_key in status_order
        ]

        payload = {
            "filters": {
                "project": selected_project_id,
                "start_date": requested_start.isoformat(),
                "end_date": requested_end.isoformat(),
            },
            "currency_code": get_default_currency_code(),
            "projects": project_options,
            "kpis": {
                "project_progress_percent": round(project_progress_percent, 2),
                "schedule_variance_days": round(schedule_variance_days, 2),
                "cost_variance_amount": round(cost_variance_amount, 2),
                "cost_variance_percent": round(cost_variance_percent, 2),
                "open_rfis": open_rfis,
                "pending_inspections": pending_inspections,
                "safety_incidents": safety_incidents,
                "material_shortages": material_shortages,
                "workforce_count": workforce_count,
                "equipment_utilization_percent": round(equipment_utilization_percent, 2),
                "quality_issues": quality_issues,
                "delayed_tasks": delayed_tasks,
                "contractor_performance_score": contractor_performance_score,
                "contractor_performance_band": contractor_performance_band,
            },
            "widgets": {
                "progress_curve": progress_curve,
                "cost_vs_budget": cost_vs_budget,
                "labour_distribution": labour_distribution,
                "material_consumption": material_consumption,
                "safety_index": safety_index,
                "inspection_status": inspection_status,
            },
        }
        cache.set(cache_key, payload, timeout=PROJECT_SUMMARY_CACHE_TTL_SECONDS)
        return Response(payload)

    @action(
        detail=False,
        methods=["get", "patch"],
        url_path="construction/site-mobilization",
    )
    def construction_site_mobilization(self, request):
        visible_projects_qs = scoped_project_queryset_for_user(
            Project.objects.order_by("name"),
            request.user,
            sub_module=self.rbac_sub_module,
        )

        if request.method == "GET":
            project_options = list(visible_projects_qs.values("id", "name")[:500])
            project_id_param = request.query_params.get("project")
            selected_project_id = None

            if project_id_param:
                try:
                    selected_project_id = int(project_id_param)
                except (TypeError, ValueError):
                    return Response(
                        {"detail": "project must be a valid integer id."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            elif project_options:
                selected_project_id = int(project_options[0]["id"])

            selected_project = None
            if selected_project_id:
                selected_project = visible_projects_qs.filter(id=selected_project_id).first()
                if selected_project is None:
                    return Response(
                        {"detail": "Project not found or not accessible."},
                        status=status.HTTP_404_NOT_FOUND,
                    )

            mobilization_payload = None
            if selected_project is not None:
                mobilization = sync_site_mobilization_for_project(selected_project)
                mobilization_payload = ProjectSiteMobilizationReadSerializer(
                    mobilization
                ).data

            return Response(
                {
                    "filters": {"project": selected_project_id},
                    "projects": project_options,
                    "mobilization": mobilization_payload,
                }
            )

        update_serializer = ProjectSiteMobilizationUpdateSerializer(
            data=request.data,
            partial=True,
        )
        update_serializer.is_valid(raise_exception=True)
        validated = update_serializer.validated_data

        project_id = validated["project"]
        project = visible_projects_qs.filter(id=project_id).first()
        if project is None:
            return Response(
                {"detail": "Project not found or not accessible."},
                status=status.HTTP_404_NOT_FOUND,
            )

        mobilization, _ = ProjectSiteMobilization.objects.get_or_create(
            project=project,
            defaults={"organization": project.organization},
        )

        update_fields: list[str] = []
        for field_name in ("planned_start_date", "actual_start_date", "notes"):
            if field_name in validated and getattr(mobilization, field_name) != validated[field_name]:
                setattr(mobilization, field_name, validated[field_name])
                update_fields.append(field_name)

        site_preparation_updates = validated.get("site_preparation") or {}
        for payload_key, model_field in MOBILIZATION_SITE_PREPARATION_FIELD_MAP.items():
            if payload_key in site_preparation_updates:
                next_value = site_preparation_updates[payload_key]
                if getattr(mobilization, model_field) != next_value:
                    setattr(mobilization, model_field, next_value)
                    update_fields.append(model_field)

        checklist_updates = validated.get("checklist") or {}
        for field_name in MOBILIZATION_MANUAL_CHECKLIST_FIELDS:
            if field_name in checklist_updates:
                next_value = bool(checklist_updates[field_name])
                if getattr(mobilization, field_name) != next_value:
                    setattr(mobilization, field_name, next_value)
                    update_fields.append(field_name)

        if update_fields:
            mobilization.save(update_fields=[*update_fields, "updated_at"])

        mobilization = sync_site_mobilization_for_project(project)
        return Response(
            {
                "mobilization": ProjectSiteMobilizationReadSerializer(mobilization).data,
            }
        )

    @action(
        detail=False,
        methods=["get", "patch"],
        url_path="construction/schedule",
    )
    def construction_schedule(self, request):
        visible_projects_qs = scoped_project_queryset_for_user(
            Project.objects.order_by("name"),
            request.user,
            sub_module=self.rbac_sub_module,
        )

        if request.method == "GET":
            project_options = list(visible_projects_qs.values("id", "name")[:500])
            project_id_param = request.query_params.get("project")
            selected_project_id = None

            if project_id_param:
                try:
                    selected_project_id = int(project_id_param)
                except (TypeError, ValueError):
                    return Response(
                        {"detail": "project must be a valid integer id."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            elif project_options:
                selected_project_id = int(project_options[0]["id"])

            schedule_payload = None
            if selected_project_id:
                project = visible_projects_qs.filter(id=selected_project_id).first()
                if project is None:
                    return Response(
                        {"detail": "Project not found or not accessible."},
                        status=status.HTTP_404_NOT_FOUND,
                    )
                schedule, _ = ProjectConstructionSchedule.objects.get_or_create(
                    project=project,
                    defaults={"organization": project.organization},
                )
                schedule_payload = _build_construction_schedule_payload(project, schedule)

            return Response(
                {
                    "filters": {"project": selected_project_id},
                    "projects": project_options,
                    "schedule": schedule_payload,
                }
            )

        update_serializer = ProjectConstructionScheduleUpdateSerializer(
            data=request.data,
            partial=True,
        )
        update_serializer.is_valid(raise_exception=True)
        validated = update_serializer.validated_data

        project_id = validated["project"]
        project = visible_projects_qs.filter(id=project_id).first()
        if project is None:
            return Response(
                {"detail": "Project not found or not accessible."},
                status=status.HTTP_404_NOT_FOUND,
            )

        schedule, _ = ProjectConstructionSchedule.objects.get_or_create(
            project=project,
            defaults={"organization": project.organization},
        )
        if schedule.organization_id != project.organization_id:
            schedule.organization = project.organization
            schedule.save(update_fields=["organization", "updated_at"])

        update_fields: list[str] = []
        if (
            "lookahead_window_days" in validated
            and schedule.lookahead_window_days != validated["lookahead_window_days"]
        ):
            schedule.lookahead_window_days = validated["lookahead_window_days"]
            update_fields.append("lookahead_window_days")

        if "notes" in validated and schedule.notes != validated["notes"]:
            schedule.notes = validated["notes"]
            update_fields.append("notes")

        section_notes_map = {
            "master_schedule": "master_schedule_notes",
            "phase_schedules": "phase_schedule_notes",
            "lookahead_schedules": "lookahead_schedule_notes",
            "task_dependencies": "task_dependency_notes",
            "critical_path": "critical_path_notes",
            "resource_assignments": "resource_assignment_notes",
        }
        for payload_key, model_field in section_notes_map.items():
            if payload_key in (validated.get("section_notes") or {}):
                next_value = validated["section_notes"][payload_key]
                if getattr(schedule, model_field) != next_value:
                    setattr(schedule, model_field, next_value)
                    update_fields.append(model_field)

        timeline_sections_map = {
            "project_manager": "project_manager_updates",
            "task_assignees": "task_assignee_updates",
            "site_workers": "site_worker_updates",
        }
        for payload_key, model_field in timeline_sections_map.items():
            if payload_key in (validated.get("timeline_sections") or {}):
                next_value = validated["timeline_sections"][payload_key]
                if getattr(schedule, model_field) != next_value:
                    setattr(schedule, model_field, next_value)
                    update_fields.append(model_field)

        if update_fields:
            schedule.save(update_fields=[*update_fields, "updated_at"])

        return Response(
            {
                "schedule": _build_construction_schedule_payload(project, schedule),
            }
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="provision-role-library",
    )
    def provision_role_library(self, request, pk=None):
        """
        Provision project staffing slots from HR role templates.
        Example use-case: "3 Site Supervisors" in one request.
        """
        from django.db import transaction

        from apps.hr.models import Position, PositionRole, Team
        from apps.settings.models import CostCenter, Department

        project = self.get_object()
        org_id = project.organization_id

        class RoleProvisionEntrySerializer(serializers.Serializer):
            role = serializers.IntegerField(min_value=1)
            department = serializers.IntegerField(min_value=1)
            cost_center = serializers.IntegerField(min_value=1)
            quantity = serializers.IntegerField(min_value=1, max_value=500)
            team = serializers.IntegerField(min_value=1, required=False, allow_null=True)
            title = serializers.CharField(required=False, allow_blank=True, max_length=200)
            code_prefix = serializers.CharField(required=False, allow_blank=True, max_length=24)
            employment_type = serializers.ChoiceField(
                required=False,
                choices=[choice[0] for choice in Position.EmploymentType.choices],
            )
            level = serializers.ChoiceField(
                required=False,
                choices=[choice[0] for choice in Position.Level.choices],
            )
            criticality_score = serializers.IntegerField(
                required=False, min_value=0, max_value=100,
            )

        class RoleProvisionRequestSerializer(serializers.Serializer):
            append_project_name = serializers.BooleanField(required=False, default=True)
            entries = RoleProvisionEntrySerializer(many=True, allow_empty=False)

        payload = RoleProvisionRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        validated = payload.validated_data

        entries = validated["entries"]
        append_project_name = validated.get("append_project_name", True)

        role_ids = {entry["role"] for entry in entries}
        department_ids = {entry["department"] for entry in entries}
        cost_center_ids = {entry["cost_center"] for entry in entries}
        team_ids = {entry["team"] for entry in entries if entry.get("team")}

        role_map = PositionRole.objects.filter(
            organization_id=org_id,
            is_active=True,
            id__in=role_ids,
        ).in_bulk()
        department_map = Department.objects.filter(
            division__organization_id=org_id,
            id__in=department_ids,
        ).in_bulk()
        cost_center_map = CostCenter.objects.filter(
            organization_id=org_id,
            is_active=True,
            id__in=cost_center_ids,
        ).in_bulk()
        team_map = Team.objects.filter(
            organization_id=org_id,
            is_active=True,
            id__in=team_ids,
        ).in_bulk()

        entry_errors = []
        for idx, entry in enumerate(entries):
            row_errors = []
            role = role_map.get(entry["role"])
            if role is None:
                row_errors.append("Role template was not found in this organization.")

            department = department_map.get(entry["department"])
            if department is None:
                row_errors.append("Department was not found in this organization.")

            cost_center = cost_center_map.get(entry["cost_center"])
            if cost_center is None:
                row_errors.append("Cost center was not found in this organization.")
            elif (
                department is not None
                and cost_center.department_id is not None
                and cost_center.department_id != department.id
            ):
                row_errors.append(
                    "Selected cost center must belong to the same department as this row.",
                )

            team_id = entry.get("team")
            if team_id:
                team = team_map.get(team_id)
                if team is None:
                    row_errors.append("Selected team was not found in this organization.")
                elif department is not None and team.department_id != department.id:
                    row_errors.append(
                        "Selected team must belong to the same department as this row.",
                    )

            if row_errors:
                entry_errors.append(
                    {
                        "row": idx + 1,
                        "errors": row_errors,
                    }
                )

        if entry_errors:
            return Response(
                {
                    "detail": "One or more role-library rows are invalid.",
                    "errors": entry_errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        def normalize_prefix(raw: str) -> str:
            cleaned = re.sub(r"[^A-Z0-9]+", "", (raw or "").upper())
            return cleaned[:12] or "GEN"

        def generate_codes(*, prefix: str, quantity: int) -> list[str]:
            existing_codes = set(
                Position.objects.filter(
                    organization_id=org_id,
                    code__startswith=f"{prefix}-",
                ).values_list("code", flat=True)
            )
            next_serial = 1
            generated: list[str] = []
            while len(generated) < quantity:
                candidate = f"{prefix}-{next_serial:03d}"
                if candidate not in existing_codes:
                    generated.append(candidate)
                    existing_codes.add(candidate)
                next_serial += 1
            return generated

        created_count = 0
        summary = []
        with transaction.atomic():
            for entry in entries:
                role = role_map[entry["role"]]
                department = department_map[entry["department"]]
                cost_center = cost_center_map[entry["cost_center"]]
                team = team_map.get(entry.get("team"))
                quantity = int(entry["quantity"])

                base_title = (entry.get("title") or "").strip() or role.name
                title = (
                    f"{base_title} — {project.name}"
                    if append_project_name and project.name
                    else base_title
                )
                code_prefix = (
                    entry.get("code_prefix")
                    or role.code
                    or role.name
                )
                code_root = f"POS-{normalize_prefix(code_prefix)}"
                codes = generate_codes(prefix=code_root, quantity=quantity)

                for code in codes:
                    Position.objects.create(
                        organization_id=org_id,
                        role=role,
                        title=title,
                        code=code,
                        department=department,
                        team=team,
                        cost_center=cost_center,
                        employment_type=entry.get(
                            "employment_type",
                            Position.EmploymentType.FULL_TIME,
                        ),
                        level=entry.get("level", Position.Level.MID),
                        status=Position.Status.ACTIVE,
                        slot_status=Position.SlotStatus.PROPOSED,
                        criticality_score=entry.get("criticality_score", 0),
                        description=role.description or "",
                        requirements=role.requirements or "",
                        headcount_budget=1,
                        is_active=True,
                    )
                created_count += quantity
                summary.append(
                    {
                        "role_id": role.id,
                        "role_name": role.name,
                        "department_id": department.id,
                        "department_name": department.name,
                        "cost_center_id": cost_center.id,
                        "cost_center_name": cost_center.name,
                        "cost_center_code": cost_center.code,
                        "team_id": team.id if team else None,
                        "team_name": team.name if team else None,
                        "quantity": quantity,
                        "code_prefix": code_root,
                        "position_codes": codes,
                    }
                )

        return Response(
            {
                "project_id": project.id,
                "project_name": project.name,
                "created_count": created_count,
                "entries": summary,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="upload-supporting-file",
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_supporting_file(self, request, pk=None):
        project = self.get_object()
        return _save_supporting_attachment(
            request,
            project=project,
        )


class ProjectPhaseViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.phases"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = ProjectPhaseSerializer
    ordering_fields = [
        "sort_order",
        "name",
        "status",
        "planned_start_date",
        "planned_end_date",
        "created_at",
    ]
    ordering = ["sort_order", "id"]

    def get_queryset(self):
        queryset = (
            super().get_queryset()
            .filter(project_id=self.kwargs["project_pk"])
            .annotate(
                task_count=Count("tasks"),
                completed_task_count=Count(
                    "tasks", filter=Q(tasks__status="completed"),
                ),
                milestone_count=Count("milestones"),
                cost_total=Sum("cost_entries__amount"),
            )
            .order_by("sort_order", "id")
        )
        return _scope_to_visible_projects(
            queryset,
            self.request,
            project_lookup="project_id",
            sub_module=self.rbac_sub_module,
        )

    def perform_create(self, serializer):
        serializer.save(
            project_id=self.kwargs["project_pk"],
            organization=self._resolve_request_org(),
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="upload-supporting-file",
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_supporting_file(self, request, project_pk=None, pk=None):
        phase = self.get_object()
        return _save_supporting_attachment(
            request,
            project=phase.project,
            phase=phase,
        )


class PhaseMilestoneViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.milestones"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = ProjectMilestoneSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = super().get_queryset().filter(
            phase_id=self.kwargs["phase_pk"],
            phase__project_id=self.kwargs["project_pk"],
        ).select_related("approved_by").prefetch_related(
            "approval_decisions__approver",
            "approval_decisions__approver_role",
        )
        return _scope_to_visible_projects(
            queryset,
            self.request,
            project_lookup="phase__project_id",
            sub_module=self.rbac_sub_module,
        )

    def perform_create(self, serializer):
        serializer.save(
            phase_id=self.kwargs["phase_pk"],
            organization=self._resolve_request_org(),
        )

    def _sync_milestone_approval_state(self, milestone, acted_by=None):
        decisions = milestone.approval_decisions.all()
        has_decisions = decisions.exists()
        has_rejected = decisions.filter(
            decision=ProjectMilestoneApprovalDecision.Decision.REJECTED
        ).exists()
        has_pending = decisions.filter(
            decision=ProjectMilestoneApprovalDecision.Decision.PENDING
        ).exists()

        fields = ["updated_at"]
        if not milestone.approval_required:
            milestone.approval_status = ProjectMilestone.ApprovalStatus.NOT_REQUIRED
            milestone.approved_by = None
            milestone.approved_at = None
            fields.extend(["approval_status", "approved_by", "approved_at"])
        elif has_rejected:
            milestone.approval_status = ProjectMilestone.ApprovalStatus.REJECTED
            milestone.approved_by = None
            milestone.approved_at = None
            fields.extend(["approval_status", "approved_by", "approved_at"])
        elif has_pending:
            milestone.approval_status = ProjectMilestone.ApprovalStatus.PENDING
            milestone.approved_by = None
            milestone.approved_at = None
            fields.extend(["approval_status", "approved_by", "approved_at"])
        elif has_decisions:
            milestone.approval_status = ProjectMilestone.ApprovalStatus.APPROVED
            milestone.approved_by = acted_by or milestone.approved_by
            milestone.approved_at = timezone.now()
            fields.extend(["approval_status", "approved_by", "approved_at"])
        else:
            milestone.approval_status = ProjectMilestone.ApprovalStatus.NOT_REQUIRED
            milestone.approved_by = None
            milestone.approved_at = None
            fields.extend(["approval_status", "approved_by", "approved_at"])

        milestone.save(update_fields=fields)

    @action(detail=True, methods=["post"], url_path="submit-approval")
    def submit_approval(self, request, project_pk=None, phase_pk=None, pk=None):
        milestone = self.get_object()
        phase = milestone.phase

        rules = ProjectMilestoneApprovalRule.objects.filter(
            project_id=project_pk,
            is_active=True,
        ).filter(
            Q(phase__isnull=True) | Q(phase_id=phase.id)
        ).select_related("required_role").order_by("sequence_order", "id")

        milestone.approval_required = True
        milestone.approval_status = ProjectMilestone.ApprovalStatus.PENDING
        milestone.approved_by = None
        milestone.approved_at = None
        milestone.save(
            update_fields=[
                "approval_required",
                "approval_status",
                "approved_by",
                "approved_at",
                "updated_at",
            ]
        )

        created_count = 0
        for rule in rules:
            _, created = ProjectMilestoneApprovalDecision.objects.get_or_create(
                milestone=milestone,
                rule=rule,
                defaults={
                    "approver_role": rule.required_role,
                    "decision": ProjectMilestoneApprovalDecision.Decision.PENDING,
                },
            )
            if created:
                created_count += 1

        if not rules.exists():
            milestone.approval_status = ProjectMilestone.ApprovalStatus.APPROVED
            milestone.approved_by = request.user
            milestone.approved_at = timezone.now()
            milestone.save(update_fields=["approval_status", "approved_by", "approved_at", "updated_at"])
        elif created_count > 0:
            # Notify approvers that milestone needs approval
            from apps.notifications.models import Notification
            from apps.notifications.services import dispatch_workflow_notification, resolve_raci_recipients

            project = phase.project
            raci = resolve_raci_recipients(
                organization=project.organization,
                process_key="projects.milestone",
            )
            recipients = raci.decision_makers or raci.all
            if not recipients:
                from apps.accounts.models import UserProfile

                recipients = [
                    p.user
                    for p in UserProfile.objects.filter(
                        organization=project.organization,
                        role="admin",
                        user__is_active=True,
                    ).select_related("user")
                ]
            if recipients:
                dispatch_workflow_notification(
                    organization=project.organization,
                    event_key="projects_milestone_approval_needed",
                    recipients=recipients,
                    context={
                        "project_name": project.name,
                        "milestone_name": milestone.name,
                        "action_url": f"/projects/{project.id}",
                    },
                    link_url=f"/projects/{project.id}",
                    fallback_channels=["in_app", "email"],
                    fallback_title=f"Approval needed: {milestone.name}",
                    fallback_message=(
                        f'Milestone "{milestone.name}" on project {project.name} '
                        f"requires your approval."
                    ),
                    fallback_category=Notification.Category.WORKFLOW_PENDING,
                    fallback_severity=Notification.Severity.WARNING,
                )

        serializer = self.get_serializer(milestone)
        return Response(
            {
                "milestone": serializer.data,
                "created_approval_steps": created_count,
            }
        )

    @action(detail=True, methods=["post"], url_path="decide-approval")
    def decide_approval(self, request, project_pk=None, phase_pk=None, pk=None):
        milestone = self.get_object()
        decision_value = str(request.data.get("decision", "")).strip().lower()
        comments = str(request.data.get("comments", "") or "").strip()
        decision_id = request.data.get("decision_id")

        if decision_value not in {
            ProjectMilestoneApprovalDecision.Decision.APPROVED,
            ProjectMilestoneApprovalDecision.Decision.REJECTED,
        }:
            return Response(
                {"detail": "decision must be 'approved' or 'rejected'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        decision_qs = milestone.approval_decisions.select_related("approver_role")
        decision_obj = None

        if decision_id:
            decision_obj = decision_qs.filter(id=decision_id).first()
            if decision_obj is None:
                return Response(
                    {"detail": "Approval step not found for this milestone."},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            user_role = getattr(getattr(request.user, "profile", None), "assigned_role", None)
            if user_role is not None:
                decision_obj = decision_qs.filter(
                    decision=ProjectMilestoneApprovalDecision.Decision.PENDING,
                    approver_role=user_role,
                ).order_by("id").first()
            if decision_obj is None and request.user.is_superuser:
                decision_obj = decision_qs.filter(
                    decision=ProjectMilestoneApprovalDecision.Decision.PENDING
                ).order_by("id").first()

        if decision_obj is None:
            return Response(
                {"detail": "No pending approval step is assigned to your role."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        decision_obj.decision = decision_value
        decision_obj.comments = comments
        decision_obj.approver = request.user
        if decision_obj.approver_role is None:
            decision_obj.approver_role = getattr(
                getattr(request.user, "profile", None),
                "assigned_role",
                None,
            )
        decision_obj.decided_at = timezone.now()
        decision_obj.save(
            update_fields=[
                "decision",
                "comments",
                "approver",
                "approver_role",
                "decided_at",
                "updated_at",
            ]
        )

        self._sync_milestone_approval_state(milestone, acted_by=request.user)

        # Notify stakeholders of the decision
        if milestone.approval_status in (
            ProjectMilestone.ApprovalStatus.APPROVED,
            ProjectMilestone.ApprovalStatus.REJECTED,
        ):
            from apps.notifications.models import Notification
            from apps.notifications.services import dispatch_workflow_notification

            project = milestone.phase.project
            category = (
                Notification.Category.WORKFLOW_APPROVED
                if milestone.approval_status == ProjectMilestone.ApprovalStatus.APPROVED
                else Notification.Category.WORKFLOW_REJECTED
            )
            recipients = []
            if milestone.created_by_id:
                recipients.append(milestone.created_by)
            if recipients:
                dispatch_workflow_notification(
                    organization=project.organization,
                    event_key="projects_milestone_decision",
                    recipients=recipients,
                    context={
                        "project_name": project.name,
                        "milestone_name": milestone.name,
                        "decision": milestone.approval_status,
                        "decided_by": request.user.get_full_name() or request.user.email,
                        "action_url": f"/projects/{project.id}",
                    },
                    link_url=f"/projects/{project.id}",
                    fallback_channels=["in_app", "email"],
                    fallback_title=f"Milestone {milestone.approval_status}: {milestone.name}",
                    fallback_message=(
                        f'Milestone "{milestone.name}" on project {project.name} '
                        f"has been {milestone.approval_status} by "
                        f"{request.user.get_full_name() or request.user.email}."
                    ),
                    fallback_category=category,
                    fallback_severity=Notification.Severity.INFO,
                )

        serializer = self.get_serializer(milestone)
        return Response({"milestone": serializer.data})

    @action(
        detail=True,
        methods=["post"],
        url_path="upload-supporting-file",
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_supporting_file(self, request, project_pk=None, phase_pk=None, pk=None):
        milestone = self.get_object()
        return _save_supporting_attachment(
            request,
            project=milestone.phase.project,
            phase=milestone.phase,
            milestone=milestone,
        )


class ProjectTaskWorkspaceViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.tasks"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = ProjectTaskSerializer
    search_fields = [
        "name",
        "description",
        "work_package",
        "assigned_to",
        "assigned_external_ref",
        "phase__name",
        "phase__project__name",
    ]
    filterset_fields = ["phase", "phase__project", "status", "priority", "assigned_user"]
    ordering_fields = [
        "created_at",
        "updated_at",
        "due_date",
        "sla_target_at",
        "priority",
        "status",
        "phase__project__name",
    ]
    ordering = ["-updated_at", "-created_at"]

    def get_queryset(self):
        queryset = (
            super().get_queryset()
            .select_related(
                "phase",
                "phase__project",
                "assigned_user",
                "created_by",
                "updated_by",
            )
            .prefetch_related(
                "linked_documents",
                "linked_variation_orders",
                "linked_risks",
            )
            .annotate(comments_count=Count("comments"))
        )
        queryset = _scope_to_visible_projects(
            queryset,
            self.request,
            project_lookup="phase__project_id",
            sub_module=self.rbac_sub_module,
        )
        params = self.request.query_params
        project_id = params.get("project")
        phase_id = params.get("phase")
        due_from = params.get("due_from")
        due_to = params.get("due_to")
        sla_status = params.get("sla_status")
        view_scope = params.get("view_scope", "cross_project")

        if project_id:
            queryset = queryset.filter(phase__project_id=project_id)
        if phase_id:
            queryset = queryset.filter(phase_id=phase_id)
        if due_from:
            queryset = queryset.filter(due_date__gte=due_from)
        if due_to:
            queryset = queryset.filter(due_date__lte=due_to)

        queryset = self._apply_view_scope(queryset, view_scope)

        now = timezone.now()
        if sla_status == "breached":
            queryset = queryset.filter(
                sla_target_at__isnull=False,
                completed_date__isnull=True,
                sla_target_at__lte=now,
            )
        elif sla_status == "at_risk":
            queryset = queryset.filter(
                sla_target_at__isnull=False,
                completed_date__isnull=True,
                sla_target_at__gt=now,
                sla_target_at__lte=now + timedelta(hours=24),
            )
        elif sla_status == "on_track":
            queryset = queryset.filter(
                sla_target_at__isnull=False,
                completed_date__isnull=True,
                sla_target_at__gt=now + timedelta(hours=24),
            )
        elif sla_status == "completed":
            queryset = queryset.filter(completed_date__isnull=False)
        elif sla_status == "not_configured":
            queryset = queryset.filter(sla_target_at__isnull=True)

        return queryset.distinct()

    def _apply_view_scope(self, queryset, scope):
        if scope == "personal":
            return queryset.filter(assigned_user=self.request.user)

        if scope == "team":
            profile = getattr(self.request.user, "profile", None)
            role_id = getattr(profile, "assigned_role_id", None)
            organization_id = getattr(profile, "organization_id", None)

            if role_id:
                return queryset.filter(assigned_user__profile__assigned_role_id=role_id)
            if organization_id:
                return queryset.filter(assigned_user__profile__organization_id=organization_id)

            project_ids = (
                ProjectTask.objects.filter(assigned_user=self.request.user)
                .values_list("phase__project_id", flat=True)
                .distinct()
            )
            return queryset.filter(phase__project_id__in=project_ids)

        return queryset

    def perform_create(self, serializer):
        task = serializer.save(
            created_by=self.request.user,
            updated_by=self.request.user,
            organization=self._resolve_request_org(),
        )
        _sync_task_sla_breach(task)

    def perform_update(self, serializer):
        task = serializer.save(updated_by=self.request.user)
        _sync_task_sla_breach(task)

    @action(detail=False, methods=["get"], url_path="setup-options")
    def setup_options(self, request):
        project_id = request.query_params.get("project")
        projects_qs = scoped_project_queryset_for_user(
            Project.objects.order_by("name"),
            request.user,
            sub_module=self.rbac_sub_module,
        )
        visible_project_ids = projects_qs.values_list("id", flat=True)

        if project_id:
            projects_qs = projects_qs.filter(id=project_id)

        phases_qs = ProjectPhase.objects.select_related("project").order_by(
            "project__name", "sort_order", "id"
        )
        phases_qs = phases_qs.filter(project_id__in=visible_project_ids)
        if project_id:
            phases_qs = phases_qs.filter(project_id=project_id)

        variations_qs = ProjectVariationOrder.objects.select_related("project").order_by(
            "-updated_at", "-created_at"
        )
        variations_qs = variations_qs.filter(project_id__in=visible_project_ids)
        risks_qs = ProjectRiskRegisterEntry.objects.select_related("project").order_by(
            "-updated_at", "-created_at"
        )
        risks_qs = risks_qs.filter(project_id__in=visible_project_ids)
        documents_qs = Document.objects.select_related("project").order_by("-created_at")
        documents_qs = documents_qs.filter(
            Q(project_id__in=visible_project_ids) | Q(project__isnull=True)
        )

        if project_id:
            variations_qs = variations_qs.filter(project_id=project_id)
            risks_qs = risks_qs.filter(project_id=project_id)
            documents_qs = documents_qs.filter(Q(project_id=project_id) | Q(project__isnull=True))

        org_id = getattr(getattr(request.user, "profile", None), "organization_id", None)
        users_qs = UserModel.objects.filter(is_active=True).select_related(
            "profile",
            "profile__assigned_role",
        )
        if org_id:
            users_qs = users_qs.filter(profile__organization_id=org_id)
        users_qs = users_qs.order_by("first_name", "last_name", "email")

        return Response(
            {
                "projects": [
                    {"id": row.id, "name": row.name}
                    for row in projects_qs[:500]
                ],
                "phases": [
                    {
                        "id": row.id,
                        "project": row.project_id,
                        "project_name": row.project.name,
                        "name": row.name,
                        "status": row.status,
                    }
                    for row in phases_qs[:1000]
                ],
                "documents": [
                    {
                        "id": row.id,
                        "project": row.project_id,
                        "title": row.title,
                        "document_number": row.document_number,
                        "status": row.status,
                    }
                    for row in documents_qs[:400]
                ],
                "contracts": [
                    {
                        "id": row.id,
                        "project": row.project_id,
                        "variation_number": row.variation_number,
                        "title": row.title,
                        "status": row.status,
                    }
                    for row in variations_qs[:400]
                ],
                "risks": [
                    {
                        "id": row.id,
                        "project": row.project_id,
                        "title": row.title,
                        "severity": row.severity,
                        "status": row.status,
                    }
                    for row in risks_qs[:400]
                ],
                "users": [
                    {
                        "id": row.id,
                        "email": row.email,
                        "full_name": row.get_full_name().strip() or row.email,
                        "role_name": getattr(getattr(row, "profile", None), "assigned_role", None).name
                        if getattr(getattr(row, "profile", None), "assigned_role", None)
                        else None,
                    }
                    for row in users_qs[:500]
                ],
            }
        )

    @action(detail=True, methods=["get", "post"], url_path="comments")
    def comments(self, request, pk=None):
        task = self.get_object()
        if request.method.lower() == "get":
            queryset = task.comments.select_related("author")
            page = self.paginate_queryset(queryset)
            serializer = ProjectTaskCommentSerializer(
                page if page is not None else queryset,
                many=True,
            )
            if page is not None:
                return self.get_paginated_response(serializer.data)
            return Response(serializer.data)

        comment_text = str(request.data.get("comment", "") or "").strip()
        if not comment_text:
            raise serializers.ValidationError({"comment": "Comment is required."})

        comment = ProjectTaskComment.objects.create(
            task=task,
            author=request.user,
            comment=comment_text,
        )
        serializer = ProjectTaskCommentSerializer(comment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["post"],
        url_path="upload-supporting-file",
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_supporting_file(self, request, pk=None):
        task = self.get_object()
        return _save_supporting_attachment(
            request,
            project=task.phase.project,
            phase=task.phase,
            task=task,
        )


class ProjectWorkPackageWorkspaceViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.tasks"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = ProjectWorkPackageSerializer
    search_fields = [
        "package_id",
        "name",
        "scope_description",
        "project__name",
        "phase__name",
        "contractor__name",
    ]
    filterset_fields = ["project", "phase", "contractor"]
    ordering_fields = [
        "created_at",
        "updated_at",
        "start_date",
        "end_date",
        "budget",
        "name",
        "project__name",
    ]
    ordering = ["-updated_at", "-created_at"]

    def get_queryset(self):
        queryset = (
            super().get_queryset()
            .select_related(
                "project",
                "phase",
                "contractor",
                "created_by",
                "updated_by",
            )
            .prefetch_related(
                "drawings",
                "linked_purchase_orders__vendor",
                "linked_cost_entries__phase",
                "linked_contractors",
                "linked_inspections",
            )
        )
        queryset = _scope_to_visible_projects(
            queryset,
            self.request,
            project_lookup="project_id",
            sub_module=self.rbac_sub_module,
        )

        params = self.request.query_params
        project_id = params.get("project")
        phase_id = params.get("phase")
        contractor_id = params.get("contractor")
        start_from = params.get("start_from")
        start_to = params.get("start_to")
        end_from = params.get("end_from")
        end_to = params.get("end_to")

        if project_id:
            queryset = queryset.filter(project_id=project_id)
        if phase_id:
            queryset = queryset.filter(phase_id=phase_id)
        if contractor_id:
            queryset = queryset.filter(contractor_id=contractor_id)
        if start_from:
            queryset = queryset.filter(start_date__gte=start_from)
        if start_to:
            queryset = queryset.filter(start_date__lte=start_to)
        if end_from:
            queryset = queryset.filter(end_date__gte=end_from)
        if end_to:
            queryset = queryset.filter(end_date__lte=end_to)

        return queryset.distinct()

    def perform_create(self, serializer):
        serializer.save(
            organization=self._resolve_request_org(),
            created_by=self.request.user,
            updated_by=self.request.user,
        )

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(detail=False, methods=["get"], url_path="setup-options")
    def setup_options(self, request):
        project_id = request.query_params.get("project")
        projects_qs = scoped_project_queryset_for_user(
            Project.objects.order_by("name"),
            request.user,
            sub_module=self.rbac_sub_module,
        )
        visible_project_ids = projects_qs.values_list("id", flat=True)

        if project_id:
            projects_qs = projects_qs.filter(id=project_id)

        phases_qs = ProjectPhase.objects.select_related("project").order_by(
            "project__name", "sort_order", "id"
        )
        phases_qs = phases_qs.filter(project_id__in=visible_project_ids)
        if project_id:
            phases_qs = phases_qs.filter(project_id=project_id)

        drawings_qs = Document.objects.select_related("project").order_by("-created_at")
        drawings_qs = drawings_qs.filter(
            Q(project_id__in=visible_project_ids) | Q(project__isnull=True)
        )
        if project_id:
            drawings_qs = drawings_qs.filter(Q(project_id=project_id) | Q(project__isnull=True))

        purchase_orders_qs = (
            PurchaseOrder.objects.select_related("vendor", "project")
            .order_by("-updated_at", "-created_at")
            .filter(project_id__in=visible_project_ids)
        )
        if project_id:
            purchase_orders_qs = purchase_orders_qs.filter(project_id=project_id)

        cost_entries_qs = (
            ProjectCostEntry.objects.select_related("phase", "phase__project")
            .order_by("-date", "-id")
            .filter(phase__project_id__in=visible_project_ids)
        )
        if project_id:
            cost_entries_qs = cost_entries_qs.filter(phase__project_id=project_id)

        inspections_qs = (
            ProjectExecutionInspection.objects.select_related("project")
            .order_by("-inspected_on", "-id")
            .filter(project_id__in=visible_project_ids)
        )
        if project_id:
            inspections_qs = inspections_qs.filter(project_id=project_id)

        org_id = getattr(getattr(request.user, "profile", None), "organization_id", None)
        contractors_qs = Vendor.objects.order_by("name")
        if org_id:
            contractors_qs = contractors_qs.filter(organization_id=org_id)

        return Response(
            {
                "projects": [
                    {"id": row.id, "name": row.name}
                    for row in projects_qs[:500]
                ],
                "phases": [
                    {
                        "id": row.id,
                        "project": row.project_id,
                        "project_name": row.project.name,
                        "name": row.name,
                        "status": row.status,
                    }
                    for row in phases_qs[:1000]
                ],
                "contractors": [
                    {
                        "id": row.id,
                        "name": row.name,
                        "category": row.category,
                        "compliance_status": row.compliance_status,
                    }
                    for row in contractors_qs[:500]
                ],
                "drawings": [
                    {
                        "id": row.id,
                        "project": row.project_id,
                        "title": row.title,
                        "document_number": row.document_number,
                        "status": row.status,
                    }
                    for row in drawings_qs[:500]
                ],
                "purchase_orders": [
                    {
                        "id": row.id,
                        "project": row.project_id,
                        "po_number": row.po_number,
                        "status": row.status,
                        "vendor_name": row.vendor.name,
                        "expected_delivery_date": row.expected_delivery_date,
                        "total_amount": str(row.total_amount),
                    }
                    for row in purchase_orders_qs[:500]
                ],
                "cost_entries": [
                    {
                        "id": row.id,
                        "project": row.phase.project_id,
                        "phase": row.phase_id,
                        "phase_name": row.phase.name,
                        "description": row.description,
                        "amount": str(row.amount),
                        "category": row.category,
                        "date": row.date,
                    }
                    for row in cost_entries_qs[:500]
                ],
                "inspections": [
                    {
                        "id": row.id,
                        "project": row.project_id,
                        "inspection_number": row.inspection_number,
                        "status": row.status,
                        "inspected_on": row.inspected_on,
                        "work_package": row.work_package,
                        "inspector_name": row.inspector_name,
                    }
                    for row in inspections_qs[:500]
                ],
                "examples": [
                    "Structural concrete",
                    "Block work",
                    "Plumbing installation",
                    "Electrical wiring",
                    "HVAC installation",
                    "Tiling",
                    "Painting",
                    "Landscaping",
                ],
            }
        )


class ProjectContractorManagementViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.tasks"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = ProjectContractorProfileSerializer
    search_fields = [
        "project__name",
        "contractor__name",
        "trade_specialization",
        "company_profile",
    ]
    filterset_fields = ["project", "contractor"]
    ordering_fields = [
        "created_at",
        "updated_at",
        "contract_value",
        "performance_rating",
        "project__name",
        "contractor__name",
    ]
    ordering = ["-updated_at", "-created_at"]

    def get_queryset(self):
        queryset = (
            super().get_queryset()
            .select_related(
                "project",
                "contractor",
                "created_by",
                "updated_by",
            )
            .prefetch_related(
                "work_packages",
                "rfis",
                "inspection_results",
            )
        )
        queryset = _scope_to_visible_projects(
            queryset,
            self.request,
            project_lookup="project_id",
            sub_module=self.rbac_sub_module,
        )

        project_id = self.request.query_params.get("project")
        contractor_id = self.request.query_params.get("contractor")
        min_contract_value = self.request.query_params.get("min_contract_value")
        max_contract_value = self.request.query_params.get("max_contract_value")
        min_rating = self.request.query_params.get("min_rating")

        if project_id:
            queryset = queryset.filter(project_id=project_id)
        if contractor_id:
            queryset = queryset.filter(contractor_id=contractor_id)
        if min_contract_value:
            queryset = queryset.filter(contract_value__gte=min_contract_value)
        if max_contract_value:
            queryset = queryset.filter(contract_value__lte=max_contract_value)
        if min_rating:
            queryset = queryset.filter(performance_rating__gte=min_rating)

        return queryset.distinct()

    def perform_create(self, serializer):
        project = serializer.validated_data["project"]
        organization = self._resolve_request_org() or project.organization
        serializer.save(
            organization=organization,
            created_by=self.request.user,
            updated_by=self.request.user,
        )

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(detail=False, methods=["get"], url_path="setup-options")
    def setup_options(self, request):
        project_id = request.query_params.get("project")
        projects_qs = scoped_project_queryset_for_user(
            Project.objects.order_by("name"),
            request.user,
            sub_module=self.rbac_sub_module,
        )
        visible_project_ids = list(projects_qs.values_list("id", flat=True))
        selected_project_id = None
        if project_id:
            try:
                selected_project_id = int(project_id)
            except (TypeError, ValueError):
                return Response(
                    {"detail": "project must be a valid integer id."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            projects_qs = projects_qs.filter(id=selected_project_id)

        contractors_qs = Vendor.objects.order_by("name")
        # Scope contractors to the selected project's org first, then
        # fall back to the requesting user's org.
        contractor_org_id = None
        if selected_project_id:
            contractor_org_id = (
                Project.objects.filter(id=selected_project_id)
                .values_list("organization_id", flat=True)
                .first()
            )
        if not contractor_org_id:
            contractor_org_id = getattr(
                getattr(request.user, "profile", None), "organization_id", None
            )
        if contractor_org_id:
            contractors_qs = contractors_qs.filter(organization_id=contractor_org_id)
        else:
            contractors_qs = contractors_qs.none()
        contractors_qs = contractors_qs.distinct()

        work_packages_qs = (
            ProjectWorkPackage.objects.select_related("project", "contractor")
            .order_by("-updated_at", "-created_at")
            .filter(project_id__in=visible_project_ids)
        )
        if selected_project_id:
            work_packages_qs = work_packages_qs.filter(project_id=selected_project_id)

        rfis_qs = (
            ProjectFieldEscalation.objects.select_related("project")
            .order_by("-issue_date", "-created_at")
            .filter(
                project_id__in=visible_project_ids,
                issue_type=ProjectFieldEscalation.IssueType.RFI_PENDING,
            )
        )
        if selected_project_id:
            rfis_qs = rfis_qs.filter(project_id=selected_project_id)

        inspections_qs = (
            ProjectExecutionInspection.objects.select_related("project")
            .order_by("-inspected_on", "-created_at")
            .filter(project_id__in=visible_project_ids)
        )
        if selected_project_id:
            inspections_qs = inspections_qs.filter(project_id=selected_project_id)

        return Response(
            {
                "projects": [{"id": row.id, "name": row.name} for row in projects_qs[:500]],
                "contractors": [
                    {
                        "id": row.id,
                        "name": row.name,
                        "category": row.category,
                        "contact_person": row.contact_person,
                        "email": row.email,
                        "phone": row.phone,
                        "compliance_status": row.compliance_status,
                        "performance_rating": str(row.performance_rating),
                    }
                    for row in contractors_qs[:500]
                ],
                "work_packages": [
                    {
                        "id": row.id,
                        "project": row.project_id,
                        "project_name": row.project.name,
                        "package_id": row.package_id,
                        "name": row.name,
                        "contractor_id": row.contractor_id,
                        "contractor_name": row.contractor.name if row.contractor_id else None,
                        "budget": str(row.budget),
                    }
                    for row in work_packages_qs[:600]
                ],
                "rfis": [
                    {
                        "id": row.id,
                        "project": row.project_id,
                        "project_name": row.project.name,
                        "title": row.title,
                        "status": row.status,
                        "issue_date": row.issue_date,
                        "severity": row.severity,
                    }
                    for row in rfis_qs[:600]
                ],
                "inspections": [
                    {
                        "id": row.id,
                        "project": row.project_id,
                        "project_name": row.project.name,
                        "inspection_number": row.inspection_number,
                        "status": row.status,
                        "inspected_on": row.inspected_on,
                        "overall_score": str(row.overall_score) if row.overall_score is not None else None,
                    }
                    for row in inspections_qs[:600]
                ],
            }
        )


class PhaseTaskViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.tasks"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = ProjectTaskSerializer
    pagination_class = None

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["phase_locked"] = True
        return context

    def get_queryset(self):
        queryset = (
            super().get_queryset()
            .filter(
                phase_id=self.kwargs["phase_pk"],
                phase__project_id=self.kwargs["project_pk"],
            )
            .select_related(
                "phase",
                "phase__project",
                "assigned_user",
                "created_by",
                "updated_by",
            )
            .prefetch_related(
                "linked_documents",
                "linked_variation_orders",
                "linked_risks",
            )
            .annotate(comments_count=Count("comments"))
        )
        return _scope_to_visible_projects(
            queryset,
            self.request,
            project_lookup="phase__project_id",
            sub_module=self.rbac_sub_module,
        )

    def perform_create(self, serializer):
        task = serializer.save(
            phase_id=self.kwargs["phase_pk"],
            created_by=self.request.user,
            updated_by=self.request.user,
            organization=self._resolve_request_org(),
        )
        _sync_task_sla_breach(task)

    def perform_update(self, serializer):
        task = serializer.save(updated_by=self.request.user)
        _sync_task_sla_breach(task)

    @action(detail=True, methods=["get", "post"], url_path="comments")
    def comments(self, request, project_pk=None, phase_pk=None, pk=None):
        task = self.get_object()
        if request.method.lower() == "get":
            serializer = ProjectTaskCommentSerializer(
                task.comments.select_related("author"),
                many=True,
            )
            return Response(serializer.data)

        comment_text = str(request.data.get("comment", "") or "").strip()
        if not comment_text:
            raise serializers.ValidationError({"comment": "Comment is required."})

        comment = ProjectTaskComment.objects.create(
            task=task,
            author=request.user,
            comment=comment_text,
        )
        serializer = ProjectTaskCommentSerializer(comment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["post"],
        url_path="upload-supporting-file",
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_supporting_file(self, request, project_pk=None, phase_pk=None, pk=None):
        task = self.get_object()
        return _save_supporting_attachment(
            request,
            project=task.phase.project,
            phase=task.phase,
            task=task,
        )


class PhaseCostEntryViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.costs"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = ProjectCostEntrySerializer
    pagination_class = None

    def get_queryset(self):
        queryset = super().get_queryset().filter(
            phase_id=self.kwargs["phase_pk"],
            phase__project_id=self.kwargs["project_pk"],
        )
        return _scope_to_visible_projects(
            queryset,
            self.request,
            project_lookup="phase__project_id",
            sub_module=self.rbac_sub_module,
        )

    def perform_create(self, serializer):
        cost_entry = serializer.save(
            phase_id=self.kwargs["phase_pk"],
            organization=self._resolve_request_org(),
        )
        sync_project_cost_entry(cost_entry, performed_by=self.request.user)

    def perform_update(self, serializer):
        cost_entry = serializer.save()
        sync_project_cost_entry(cost_entry, performed_by=self.request.user)

    def perform_destroy(self, instance):
        cost_entry_id = instance.id
        instance.delete()
        delete_project_cost_transaction(cost_entry_id)

    @action(
        detail=True,
        methods=["post"],
        url_path="upload-supporting-file",
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_supporting_file(self, request, project_pk=None, phase_pk=None, pk=None):
        cost_entry = self.get_object()
        return _save_supporting_attachment(
            request,
            project=cost_entry.phase.project,
            phase=cost_entry.phase,
            cost_entry=cost_entry,
        )


class ProjectPhaseDependencyViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.phases"
    serializer_class = ProjectPhaseDependencySerializer
    pagination_class = None
    ordering = ["predecessor_phase__sort_order", "successor_phase__sort_order", "id"]

    def get_queryset(self):
        queryset = super().get_queryset().filter(
            project_id=self.kwargs["project_pk"]
        ).select_related("predecessor_phase", "successor_phase")
        return _scope_to_visible_projects(
            queryset,
            self.request,
            project_lookup="project_id",
            sub_module=self.rbac_sub_module,
        )

    def perform_create(self, serializer):
        serializer.save(
            project_id=self.kwargs["project_pk"],
            organization=self._resolve_request_org(),
        )


class ProjectMilestoneApprovalRuleViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.milestones"
    serializer_class = ProjectMilestoneApprovalRuleSerializer
    pagination_class = None
    ordering = ["phase_id", "sequence_order", "id"]

    def get_queryset(self):
        queryset = super().get_queryset().filter(
            project_id=self.kwargs["project_pk"]
        ).select_related("phase", "required_role")
        return _scope_to_visible_projects(
            queryset,
            self.request,
            project_lookup="project_id",
            sub_module=self.rbac_sub_module,
        )

    def perform_create(self, serializer):
        serializer.save(
            project_id=self.kwargs["project_pk"],
            organization=self._resolve_request_org(),
        )


class ProjectMilestoneApprovalDecisionViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.milestones"
    serializer_class = ProjectMilestoneApprovalDecisionSerializer
    pagination_class = None
    ordering = ["created_at", "id"]

    def get_queryset(self):
        queryset = super().get_queryset().filter(
            milestone__phase__project_id=self.kwargs["project_pk"]
        ).select_related("milestone", "rule", "approver", "approver_role")
        queryset = _scope_to_visible_projects(
            queryset,
            self.request,
            project_lookup="milestone__phase__project_id",
            sub_module=self.rbac_sub_module,
        )
        milestone_id = self.request.query_params.get("milestone")
        if milestone_id:
            queryset = queryset.filter(milestone_id=milestone_id)
        return queryset

    def perform_create(self, serializer):
        milestone = serializer.validated_data["milestone"]
        if milestone.phase.project_id != int(self.kwargs["project_pk"]):
            raise serializers.ValidationError(
                {"milestone": "Milestone does not belong to selected project."}
            )
        decision_value = serializer.validated_data.get(
            "decision",
            ProjectMilestoneApprovalDecision.Decision.PENDING,
        )
        decided_at = timezone.now() if decision_value != ProjectMilestoneApprovalDecision.Decision.PENDING else None
        serializer.save(
            approver=self.request.user,
            decided_at=decided_at,
            organization=self._resolve_request_org(),
        )


class ProjectScheduleDelayLogViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = ProjectScheduleDelayLogSerializer
    pagination_class = None
    search_fields = ["reason", "mitigation_action", "phase__name", "milestone__name"]
    filterset_fields = ["delay_type", "delay_date", "phase", "milestone", "source_issue"]
    ordering_fields = ["delay_date", "impact_days", "created_at"]
    ordering = ["-delay_date", "-created_at"]

    def get_queryset(self):
        queryset = super().get_queryset().filter(
            project_id=self.kwargs["project_pk"]
        ).select_related("project", "phase", "milestone", "source_issue", "created_by")
        return _scope_to_visible_projects(
            queryset,
            self.request,
            project_lookup="project_id",
            sub_module=self.rbac_sub_module,
        )

    def perform_create(self, serializer):
        serializer.save(
            project_id=self.kwargs["project_pk"],
            created_by=self.request.user,
            organization=self._resolve_request_org(),
        )

    def perform_update(self, serializer):
        serializer.save()


class ProjectRiskRegisterViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    search_fields = ["title", "description", "mitigation_plan", "project__name"]
    filterset_fields = [
        "project",
        "risk_category",
        "severity",
        "status",
        "treatment",
        "escalation_required",
        "owner_role",
    ]
    ordering_fields = [
        "created_at",
        "updated_at",
        "risk_score",
        "severity",
        "status",
        "identified_on",
        "target_resolution_date",
    ]
    ordering = ["-risk_score", "-created_at"]

    def get_queryset(self):
        queryset = (
            super().get_queryset()
            .select_related(
                "project",
                "risk_category",
                "owner_role",
                "created_by",
                "updated_by",
            )
        )
        return _scope_to_visible_projects(
            queryset,
            self.request,
            project_lookup="project_id",
            sub_module=self.rbac_sub_module,
        )

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return ProjectRiskRegisterWriteSerializer
        return ProjectRiskRegisterListSerializer

    @action(detail=False, methods=["get"])
    def summary(self, request):
        cache_key = _project_summary_cache_key(request, "risk-register")
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        queryset = self.filter_queryset(self.get_queryset())
        total = queryset.count()
        by_severity = {
            "low": queryset.filter(severity=ProjectRiskRegisterEntry.Severity.LOW).count(),
            "medium": queryset.filter(severity=ProjectRiskRegisterEntry.Severity.MEDIUM).count(),
            "high": queryset.filter(severity=ProjectRiskRegisterEntry.Severity.HIGH).count(),
            "critical": queryset.filter(severity=ProjectRiskRegisterEntry.Severity.CRITICAL).count(),
        }
        by_status = {
            "open": queryset.filter(status=ProjectRiskRegisterEntry.Status.OPEN).count(),
            "in_progress": queryset.filter(status=ProjectRiskRegisterEntry.Status.IN_PROGRESS).count(),
            "mitigated": queryset.filter(status=ProjectRiskRegisterEntry.Status.MITIGATED).count(),
            "accepted": queryset.filter(status=ProjectRiskRegisterEntry.Status.ACCEPTED).count(),
            "closed": queryset.filter(status=ProjectRiskRegisterEntry.Status.CLOSED).count(),
        }
        payload = {
            "total_risks": total,
            "high_and_critical_risks": by_severity["high"] + by_severity["critical"],
            "open_risks": by_status["open"] + by_status["in_progress"],
            "mitigated_risks": by_status["mitigated"] + by_status["closed"],
            "overdue_mitigation_risks": queryset.filter(
                target_resolution_date__isnull=False,
                target_resolution_date__lt=timezone.localdate(),
            )
            .exclude(
                status__in=[
                    ProjectRiskRegisterEntry.Status.MITIGATED,
                    ProjectRiskRegisterEntry.Status.ACCEPTED,
                    ProjectRiskRegisterEntry.Status.CLOSED,
                ]
            )
            .count(),
            "by_severity": by_severity,
            "by_status": by_status,
        }
        cache.set(cache_key, payload, timeout=PROJECT_SUMMARY_CACHE_TTL_SECONDS)
        return Response(payload)

    @action(
        detail=True,
        methods=["post"],
        url_path="upload-supporting-file",
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_supporting_file(self, request, pk=None):
        risk_entry = self.get_object()
        return _save_supporting_attachment(
            request,
            project=risk_entry.project,
            risk_entry=risk_entry,
        )


class ProjectVariationOrderViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = ProjectVariationOrderSerializer
    search_fields = ["variation_number", "title", "change_summary", "reason", "project__name"]
    filterset_fields = ["project", "status", "related_document"]
    ordering_fields = ["created_at", "updated_at", "requested_date", "due_date", "contract_value"]
    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            "project",
            "related_document",
            "created_by",
            "updated_by",
        )
        return _scope_to_visible_projects(
            queryset,
            self.request,
            project_lookup="project_id",
            sub_module=self.rbac_sub_module,
        )

    @action(detail=False, methods=["get"])
    def summary(self, request):
        cache_key = _project_summary_cache_key(request, "variation-orders")
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        queryset = self.filter_queryset(self.get_queryset())
        pending_queryset = queryset.filter(
            status__in=[
                ProjectVariationOrder.Status.SUBMITTED,
                ProjectVariationOrder.Status.UNDER_REVIEW,
            ]
        )
        approved_queryset = queryset.filter(status=ProjectVariationOrder.Status.APPROVED)
        payload = {
            "total": queryset.count(),
            "pending": pending_queryset.count(),
            "high_value_pending": pending_queryset.filter(contract_value__gte=100000).count(),
            "approved_value": float(
                approved_queryset.aggregate(total=Sum("contract_value")).get("total") or 0
            ),
            "pending_value": float(
                pending_queryset.aggregate(total=Sum("contract_value")).get("total") or 0
            ),
            "projects_impacted": queryset.values("project_id").distinct().count(),
        }
        cache.set(cache_key, payload, timeout=PROJECT_SUMMARY_CACHE_TTL_SECONDS)
        return Response(payload)

    @action(
        detail=True,
        methods=["post"],
        url_path="upload-supporting-file",
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_supporting_file(self, request, pk=None):
        variation = self.get_object()
        return _save_supporting_attachment(
            request,
            project=variation.project,
            variation=variation,
        )


class ProjectWorkforceLogViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = ProjectWorkforceLogSerializer
    search_fields = [
        "project__name",
        "worker_id",
        "trade",
        "employee__user__first_name",
        "employee__user__last_name",
        "contractor__name",
        "task_assigned__name",
        "notes",
    ]
    filterset_fields = [
        "project",
        "employee",
        "contractor",
        "daily_attendance",
        "task_assigned",
        "report_date",
        "shift",
    ]
    ordering_fields = [
        "report_date",
        "created_at",
        "updated_at",
        "daily_attendance",
        "overtime_hours",
        "productivity",
        "laborers_count",
        "skilled_count",
        "supervisors_count",
    ]
    ordering = ["-report_date", "-created_at"]

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            "project",
            "employee__user",
            "contractor",
            "task_assigned",
            "created_by",
            "updated_by",
        )
        return _scope_to_visible_projects(
            queryset,
            self.request,
            project_lookup="project_id",
            sub_module=self.rbac_sub_module,
        )

    def perform_create(self, serializer):
        instance = serializer.save(
            created_by=self.request.user,
            updated_by=self.request.user,
            organization=self._resolve_request_org(),
        )
        _sync_site_report_from_workforce_log(instance, self.request.user)

    def perform_update(self, serializer):
        instance = serializer.save(updated_by=self.request.user)
        _sync_site_report_from_workforce_log(instance, self.request.user)

    @action(detail=False, methods=["get"], url_path="setup-options")
    def setup_options(self, request):
        project_id = request.query_params.get("project")
        org = self._resolve_request_org()

        employee_queryset = EmployeeRecord.objects.select_related("user").order_by(
            "user__first_name",
            "user__last_name",
            "id",
        )
        contractor_queryset = Vendor.objects.order_by("name", "id")
        task_queryset = ProjectTask.objects.select_related("phase__project").order_by(
            "-updated_at",
            "-created_at",
            "-id",
        )

        if not request.user.is_superuser:
            if org is None:
                return Response(
                    {"employees": [], "contractors": [], "tasks": []},
                    status=status.HTTP_200_OK,
                )
            employee_queryset = employee_queryset.filter(organization=org)
            contractor_queryset = contractor_queryset.filter(organization=org)
            task_queryset = task_queryset.filter(organization=org)

        if project_id:
            task_queryset = task_queryset.filter(phase__project_id=project_id)

        task_queryset = _scope_to_visible_projects(
            task_queryset,
            request,
            project_lookup="phase__project_id",
            sub_module=self.rbac_sub_module,
        )

        employee_rows = []
        for employee in employee_queryset[:500]:
            full_name = employee.user.get_full_name() if employee.user_id else ""
            fallback_name = employee.user.username if employee.user_id else f"Employee {employee.id}"
            employee_rows.append(
                {
                    "id": employee.id,
                    "worker_id": f"EMP-{employee.id}",
                    "name": full_name or fallback_name,
                    "employment_status": employee.employment_status,
                }
            )

        contractor_rows = [
            {
                "id": contractor.id,
                "name": contractor.name,
                "category": contractor.category,
                "compliance_status": contractor.compliance_status,
            }
            for contractor in contractor_queryset[:500]
        ]

        task_rows = []
        for task in task_queryset[:600]:
            project = task.phase.project if task.phase_id and task.phase else None
            task_rows.append(
                {
                    "id": task.id,
                    "name": task.name,
                    "project": project.id if project else None,
                    "project_name": project.name if project else None,
                    "status": task.status,
                    "due_date": task.due_date,
                }
            )

        return Response(
            {
                "employees": employee_rows,
                "contractors": contractor_rows,
                "tasks": task_rows,
            }
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="upload-supporting-file",
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_supporting_file(self, request, pk=None):
        workforce_log = self.get_object()
        return _save_supporting_attachment(
            request,
            project=workforce_log.project,
            workforce_log=workforce_log,
        )


class ProjectDailySiteReportViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = ProjectDailySiteReportSerializer
    search_fields = [
        "project__name",
        "work_completed",
        "planned_next_day",
        "blockers",
        "incidents",
    ]
    filterset_fields = [
        "project",
        "report_date",
        "shift",
        "weather",
        "status",
        "escalation_required",
    ]
    ordering_fields = [
        "report_date",
        "progress_percent",
        "weather_delay_hours",
        "created_at",
        "updated_at",
    ]
    ordering = ["-report_date", "-created_at"]

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            "project",
            "submitted_by",
            "reviewed_by",
            "created_by",
            "updated_by",
        ).prefetch_related("photos")
        return _scope_to_visible_projects(
            queryset,
            self.request,
            project_lookup="project_id",
            sub_module=self.rbac_sub_module,
        )

    def perform_create(self, serializer):
        user = self.request.user
        instance = serializer.save(
            created_by=user,
            updated_by=user,
            organization=self._resolve_request_org(),
        )
        if instance.status == ProjectDailySiteReport.Status.SUBMITTED and not instance.submitted_by:
            instance.submitted_by = user
            instance.save(update_fields=["submitted_by", "updated_at"])
        _sync_workforce_log_from_site_report(instance, user)

    def perform_update(self, serializer):
        user = self.request.user
        instance = serializer.save(updated_by=user)

        update_fields = []
        if instance.status == ProjectDailySiteReport.Status.SUBMITTED and not instance.submitted_by:
            instance.submitted_by = user
            update_fields.append("submitted_by")

        if instance.status == ProjectDailySiteReport.Status.REVIEWED:
            if not instance.reviewed_by:
                instance.reviewed_by = user
                update_fields.append("reviewed_by")
            if not instance.reviewed_at:
                instance.reviewed_at = timezone.now()
                update_fields.append("reviewed_at")

        if update_fields:
            update_fields.append("updated_at")
            instance.save(update_fields=update_fields)
        _sync_workforce_log_from_site_report(instance, user)

    @action(
        detail=True,
        methods=["post"],
        url_path="upload-photo",
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_photo(self, request, pk=None):
        report = self.get_object()
        serializer = ProjectDailySiteReportPhotoSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(report=report, uploaded_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ProjectDeliveryConfirmationViewSet(
    OrgScopedMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = ProjectDeliveryConfirmationSerializer
    search_fields = [
        "grn_number",
        "purchase_order__po_number",
        "purchase_order__vendor__name",
        "delivery_note_number",
        "received_by",
        "inspection_notes",
        "notes",
    ]
    filterset_fields = [
        "purchase_order__project",
        "purchase_order__vendor",
        "purchase_order",
        "status",
        "received_date",
    ]
    ordering_fields = [
        "received_date",
        "created_at",
        "purchase_order__expected_delivery_date",
        "purchase_order__po_number",
        "status",
    ]
    ordering = ["-received_date", "-created_at"]

    def get_queryset(self):
        queryset = (
            GoodsReceipt.objects.filter(purchase_order__project__isnull=False)
            .select_related(
                "purchase_order__project",
                "purchase_order__vendor",
                "purchase_order__organization",
            )
            .annotate(
                item_count=Count("items", distinct=True),
                accepted_quantity=Coalesce(
                    Sum("items__quantity_accepted"),
                    Value(0),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                ),
                rejected_quantity=Coalesce(
                    Sum("items__quantity_rejected"),
                    Value(0),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                ),
            )
        )

        if _is_superuser(self.request):
            return queryset

        organization = _user_org(self.request)
        if not organization:
            return queryset.none()

        queryset = queryset.filter(
            Q(organization=organization)
            | Q(organization__isnull=True, purchase_order__organization=organization)
            | Q(
                organization__isnull=True,
                purchase_order__project__organization=organization,
            )
        ).distinct()
        return _scope_to_visible_projects(
            queryset,
            self.request,
            project_lookup="purchase_order__project_id",
            sub_module=self.rbac_sub_module,
        )

    @action(detail=False, methods=["get"])
    def summary(self, request):
        cache_key = _project_summary_cache_key(request, "delivery-confirmations")
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        queryset = self.filter_queryset(self.get_queryset())

        late_filter = Q(
            purchase_order__expected_delivery_date__isnull=False,
            received_date__gt=F("purchase_order__expected_delivery_date"),
        )
        open_escalation_statuses = [
            ProjectFieldEscalation.Status.OPEN,
            ProjectFieldEscalation.Status.ACKNOWLEDGED,
            ProjectFieldEscalation.Status.IN_PROGRESS,
        ]
        project_ids = queryset.values_list("purchase_order__project_id", flat=True).distinct()
        open_late_delivery_escalations = ProjectFieldEscalation.objects.filter(
            project_id__in=project_ids,
            issue_type=ProjectFieldEscalation.IssueType.LATE_DELIVERY,
            status__in=open_escalation_statuses,
        ).count()

        payload = {
            "total": queryset.count(),
            "on_time": queryset.exclude(late_filter).count(),
            "late": queryset.filter(late_filter).count(),
            "pending_inspection": queryset.filter(
                status__in=[
                    GoodsReceipt.Status.PENDING,
                    GoodsReceipt.Status.INSPECTED,
                ]
            ).count(),
            "partial_acceptance": queryset.filter(
                status=GoodsReceipt.Status.PARTIALLY_ACCEPTED
            ).count(),
            "rejected": queryset.filter(status=GoodsReceipt.Status.REJECTED).count(),
            "accepted": queryset.filter(status=GoodsReceipt.Status.ACCEPTED).count(),
            "open_late_delivery_escalations": open_late_delivery_escalations,
        }
        cache.set(cache_key, payload, timeout=PROJECT_SUMMARY_CACHE_TTL_SECONDS)
        return Response(payload)


class ProjectExecutionInspectionViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = ProjectExecutionInspectionSerializer
    search_fields = [
        "inspection_number",
        "project__name",
        "phase__name",
        "work_package",
        "location",
        "inspector_name",
        "inspector_role",
        "observations",
        "corrective_actions",
    ]
    filterset_fields = [
        "project",
        "phase",
        "source_report",
        "inspection_type",
        "status",
        "shift",
        "inspected_on",
    ]
    ordering_fields = [
        "inspected_on",
        "created_at",
        "updated_at",
        "status",
        "overall_score",
        "critical_findings",
        "major_findings",
        "minor_findings",
        "due_date",
    ]
    ordering = ["-inspected_on", "-created_at"]

    def get_queryset(self):
        org = self._resolve_request_org()
        queryset = ProjectExecutionInspection.objects.filter(
            organization=org,
        ).select_related(
            "project",
            "phase",
            "source_report",
            "created_by",
            "updated_by",
        ).prefetch_related("checklist_items")
        return queryset

    def perform_create(self, serializer):
        inspection = serializer.save(
            created_by=self.request.user,
            updated_by=self.request.user,
            organization=self._resolve_request_org(),
        )
        _sync_inspection_closed_at(inspection)

    def perform_update(self, serializer):
        inspection = serializer.save(updated_by=self.request.user)
        _sync_inspection_closed_at(inspection)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        cache_key = _project_summary_cache_key(request, "execution-inspections")
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        queryset = self.filter_queryset(self.get_queryset())
        open_count = queryset.filter(
            status__in=[
                ProjectExecutionInspection.Status.PLANNED,
                ProjectExecutionInspection.Status.IN_PROGRESS,
                ProjectExecutionInspection.Status.BLOCKED,
            ]
        ).count()
        failed_count = queryset.filter(
            status=ProjectExecutionInspection.Status.FAILED
        ).count()
        due_actions = queryset.filter(
            due_date__isnull=False,
            due_date__lt=timezone.localdate(),
            status__in=[
                ProjectExecutionInspection.Status.PLANNED,
                ProjectExecutionInspection.Status.IN_PROGRESS,
                ProjectExecutionInspection.Status.BLOCKED,
                ProjectExecutionInspection.Status.FAILED,
            ],
        ).count()
        payload = {
            "total": queryset.count(),
            "open": open_count,
            "failed": failed_count,
            "due_actions": due_actions,
        }
        cache.set(cache_key, payload, timeout=PROJECT_SUMMARY_CACHE_TTL_SECONDS)
        return Response(payload)

    @action(
        detail=True,
        methods=["post"],
        url_path="upload-supporting-file",
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_supporting_file(self, request, pk=None):
        inspection = self.get_object()
        return _save_supporting_attachment(
            request,
            project=inspection.project,
            quality_inspection=inspection,
        )


class ProjectFieldEscalationViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = ProjectFieldEscalationSerializer
    search_fields = [
        "project__name",
        "title",
        "description",
        "resolution_notes",
        "owner_name",
        "issue_category",
        "issue_type",
        "location",
        "impact_summary",
        "root_cause",
        "immediate_action",
    ]
    filterset_fields = [
        "project",
        "source_report",
        "issue_date",
        "issue_category",
        "issue_type",
        "weather_condition",
        "severity",
        "status",
    ]
    ordering_fields = [
        "issue_date",
        "created_at",
        "updated_at",
        "due_date",
        "severity",
        "status",
        "weather_delay_hours",
        "estimated_schedule_impact_days",
        "estimated_cost_impact",
    ]
    ordering = ["-issue_date", "-created_at"]

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            "project",
            "source_report",
            "created_by",
            "updated_by",
        )
        return _scope_to_visible_projects(
            queryset,
            self.request,
            project_lookup="project_id",
            sub_module=self.rbac_sub_module,
        )

    def perform_create(self, serializer):
        user = self.request.user
        instance = serializer.save(
            created_by=user,
            updated_by=user,
            organization=self._resolve_request_org(),
        )
        if (
            instance.status in (
                ProjectFieldEscalation.Status.RESOLVED,
                ProjectFieldEscalation.Status.CLOSED,
            )
            and not instance.resolved_at
        ):
            instance.resolved_at = timezone.now()
            instance.save(update_fields=["resolved_at", "updated_at"])

        # Notify PM + admins about the field escalation
        from apps.accounts.models import UserProfile
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification

        org = self._resolve_request_org()
        recipients = [
            p.user
            for p in UserProfile.objects.filter(
                organization=org,
                role="admin",
                user__is_active=True,
            ).select_related("user")
        ]
        project = instance.project if hasattr(instance, "project") else None
        if recipients:
            dispatch_workflow_notification(
                organization=org,
                event_key="projects_field_escalation",
                recipients=recipients,
                context={
                    "project_name": project.name if project else "",
                    "escalation_title": instance.title if hasattr(instance, "title") else str(instance),
                    "severity": instance.severity,
                    "action_url": f"/projects/{project.id}/field-operations" if project else "/projects",
                },
                link_url=f"/projects/{project.id}/field-operations" if project else "/projects",
                fallback_channels=["in_app", "email"],
                fallback_title=f"Field escalation: {instance.title if hasattr(instance, 'title') else 'New'}",
                fallback_message=(
                    f"A field escalation has been raised"
                    f"{f' on project {project.name}' if project else ''}."
                ),
                fallback_category=Notification.Category.WORKFLOW_ESCALATED,
                fallback_severity=Notification.Severity.WARNING,
            )

    def perform_update(self, serializer):
        instance = serializer.save(updated_by=self.request.user)
        if (
            instance.status in (
                ProjectFieldEscalation.Status.RESOLVED,
                ProjectFieldEscalation.Status.CLOSED,
            )
            and not instance.resolved_at
        ):
            instance.resolved_at = timezone.now()
            instance.save(update_fields=["resolved_at", "updated_at"])

    @action(detail=False, methods=["get"])
    def summary(self, request):
        cache_key = _project_summary_cache_key(request, "field-escalations")
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        queryset = self.filter_queryset(self.get_queryset())
        total = queryset.count()
        open_count = queryset.filter(
            status__in=[
                ProjectFieldEscalation.Status.OPEN,
                ProjectFieldEscalation.Status.ACKNOWLEDGED,
                ProjectFieldEscalation.Status.IN_PROGRESS,
            ]
        ).count()
        critical_count = queryset.filter(
            severity=ProjectFieldEscalation.Severity.ESCALATION
        ).count()
        overdue_count = queryset.filter(
            due_date__isnull=False,
            due_date__lt=timezone.localdate(),
            status__in=[
                ProjectFieldEscalation.Status.OPEN,
                ProjectFieldEscalation.Status.ACKNOWLEDGED,
                ProjectFieldEscalation.Status.IN_PROGRESS,
            ],
        ).count()
        weather_issue_count = queryset.filter(
            issue_category=ProjectFieldEscalation.IssueCategory.WEATHER
        ).count()
        weather_delay_total = (
            queryset.filter(weather_delay_hours__gt=0).aggregate(total=Sum("weather_delay_hours"))["total"]
            or 0
        )
        payload = {
            "total": total,
            "open": open_count,
            "critical": critical_count,
            "overdue": overdue_count,
            "weather_issues": weather_issue_count,
            "weather_delay_hours_total": weather_delay_total,
        }
        cache.set(cache_key, payload, timeout=PROJECT_SUMMARY_CACHE_TTL_SECONDS)
        return Response(payload)

    @action(
        detail=True,
        methods=["post"],
        url_path="upload-supporting-file",
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_supporting_file(self, request, pk=None):
        escalation = self.get_object()
        return _save_supporting_attachment(
            request,
            project=escalation.project,
            escalation=escalation,
        )


# ---------------------------------------------------------------------------
# Equipment & Machinery
# ---------------------------------------------------------------------------


class ProjectEquipmentViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.tasks"
    rbac_action_map = _PROJECT_ACTION_MAP
    search_fields = ["asset_id", "name", "serial_number", "current_location", "make", "model_name"]
    filterset_fields = ["status", "equipment_type", "ownership", "current_project"]
    ordering_fields = ["asset_id", "name", "status", "current_book_value", "last_service_date", "created_at"]
    ordering = ["asset_id"]

    def get_queryset(self):
        return (
            super().get_queryset()
            .select_related("current_project")
        )

    def get_serializer_class(self):
        if self.action == "list":
            return ProjectEquipmentListSerializer
        if self.action in ("create", "update", "partial_update"):
            return ProjectEquipmentWriteSerializer
        return ProjectEquipmentDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))

    @action(detail=False, methods=["get"], url_path="fleet-kpis")
    def fleet_kpis(self, request):
        qs = self.get_queryset()
        total = qs.count()
        operational = qs.filter(status="operational").count()
        in_repair = qs.filter(status="in_repair").count()
        idle = qs.filter(status="idle").count()

        deployment_rate = round(operational / total * 100, 1) if total > 0 else 0

        today = date.today()
        maintenance_due = qs.filter(
            next_service_due__isnull=False,
            next_service_due__lte=today,
        ).count()

        total_book_value = qs.aggregate(
            total=Coalesce(Sum("current_book_value"), Value(0, output_field=DecimalField()))
        )["total"]

        utilization_index = round(
            (operational + in_repair) / total * 100, 1
        ) if total > 0 else 0

        return Response({
            "total_fleet": total,
            "operational": operational,
            "in_repair": in_repair,
            "idle": idle,
            "deployment_rate": deployment_rate,
            "maintenance_due": maintenance_due,
            "total_book_value": str(total_book_value),
            "utilization_index": utilization_index,
        })


class EquipmentMaintenanceLogViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.tasks"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = EquipmentMaintenanceLogSerializer
    filterset_fields = ["log_type"]
    ordering = ["-date"]

    def get_queryset(self):
        return EquipmentMaintenanceLog.objects.filter(
            equipment_id=self.kwargs.get("equipment_pk"),
        )

    def perform_create(self, serializer):
        serializer.save(equipment_id=self.kwargs["equipment_pk"])


class EquipmentDeploymentLogViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.tasks"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = EquipmentDeploymentLogSerializer
    ordering = ["-deployed_date"]

    def get_queryset(self):
        return EquipmentDeploymentLog.objects.filter(
            equipment_id=self.kwargs.get("equipment_pk"),
        ).select_related("project")

    def perform_create(self, serializer):
        instance = serializer.save(equipment_id=self.kwargs["equipment_pk"])
        self._check_conflicts(instance)

    def perform_update(self, serializer):
        instance = serializer.save()
        self._check_conflicts(instance)

    def _check_conflicts(self, instance):
        """Detect overlapping deployments for the same equipment and notify."""
        from apps.notifications.services import dispatch_workflow_notification
        from apps.notifications.models import Notification

        equipment = instance.equipment
        end_date = instance.returned_date

        overlaps = EquipmentDeploymentLog.objects.filter(
            equipment=equipment,
        ).exclude(pk=instance.pk)

        if end_date:
            overlaps = overlaps.filter(
                deployed_date__lte=end_date,
            ).filter(
                Q(returned_date__isnull=True) | Q(returned_date__gte=instance.deployed_date),
            )
        else:
            overlaps = overlaps.filter(
                Q(returned_date__isnull=True) | Q(returned_date__gte=instance.deployed_date),
            )

        if overlaps.exists():
            conflict_list = overlaps.select_related("project")[:5]
            conflict_details = ", ".join(
                f"{c.project.name} ({c.deployed_date}\u2013{c.returned_date or 'ongoing'})"
                for c in conflict_list
            )
            org = equipment.organization
            try:
                dispatch_workflow_notification(
                    organization=org,
                    event_key="equipment_deployment_conflict",
                    recipients=list(org.members.filter(role__in=["admin", "manager"])[:10]),
                    context={
                        "equipment_name": f"{equipment.asset_id} \u2014 {equipment.name}",
                        "deployed_to": instance.project.name if instance.project_id else "Unknown",
                        "conflicts": conflict_details,
                    },
                    link_url="/construction/equipment",
                    fallback_channels=["in_app"],
                    fallback_title=f"Equipment Conflict \u2014 {equipment.asset_id}",
                    fallback_message=(
                        f"Equipment '{equipment.asset_id} \u2014 {equipment.name}' deployed to "
                        f"'{instance.project.name}' ({instance.deployed_date}\u2013{instance.returned_date or 'ongoing'}) "
                        f"conflicts with: {conflict_details}. Please resolve the scheduling conflict."
                    ),
                    fallback_category=Notification.Category.ESCALATION_ALERT,
                    fallback_severity=Notification.Severity.WARNING,
                )
            except Exception:
                pass


# ── Quality Control ──────────────────────────────────────────────────


class QualityPlanViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    search_fields = ["plan_number", "name", "compliance_standards", "description"]
    filterset_fields = ["project", "approval_status", "review_cycle"]
    ordering_fields = ["created_at", "updated_at", "name", "approval_status"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return QualityPlanListSerializer
        if self.action in ("create", "update", "partial_update"):
            return QualityPlanWriteSerializer
        return QualityPlanDetailSerializer

    def get_queryset(self):
        return (
            QualityPlan.objects.filter(organization=self._resolve_request_org())
            .select_related("project", "created_by")
            .prefetch_related("check_templates")
            .annotate(check_count=Count("check_templates"))
        )

    def perform_create(self, serializer):
        serializer.save(
            organization=self._resolve_request_org(),
            created_by=self.request.user,
        )


class QualityCheckTemplateViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    """Nested under /quality-plans/<pk>/checks/"""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = QualityCheckTemplateSerializer
    ordering = ["sort_order", "id"]

    def get_queryset(self):
        return QualityCheckTemplate.objects.filter(
            quality_plan_id=self.kwargs.get("plan_pk"),
            organization=self._resolve_request_org(),
        )

    def perform_create(self, serializer):
        serializer.save(
            quality_plan_id=self.kwargs["plan_pk"],
            organization=self._resolve_request_org(),
        )


class NonConformanceReportViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    search_fields = [
        "ncr_number", "title", "description", "location",
        "raised_by", "assigned_to", "rectification_plan",
    ]
    filterset_fields = ["project", "inspection", "severity", "root_cause", "status"]
    ordering_fields = [
        "raised_date", "created_at", "severity", "status",
        "rectification_due_date", "cost_impact",
    ]
    ordering = ["-raised_date", "-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return NonConformanceReportListSerializer
        if self.action in ("create", "update", "partial_update"):
            return NonConformanceReportWriteSerializer
        return NonConformanceReportDetailSerializer

    def get_queryset(self):
        return (
            NonConformanceReport.objects.filter(
                organization=self._resolve_request_org(),
            )
            .select_related("project", "inspection", "created_by")
        )

    def perform_create(self, serializer):
        serializer.save(
            organization=self._resolve_request_org(),
            created_by=self.request.user,
        )

    @action(detail=False, methods=["get"])
    def summary(self, request):
        org = self._resolve_request_org()
        qs = NonConformanceReport.objects.filter(organization=org)
        today = date.today()
        open_statuses = ["open", "under_review", "rectification", "verification"]
        return Response({
            "total": qs.count(),
            "open": qs.filter(status__in=open_statuses).count(),
            "critical_open": qs.filter(
                severity="critical", status__in=open_statuses,
            ).count(),
            "overdue": qs.filter(
                status__in=open_statuses,
                rectification_due_date__lt=today,
            ).count(),
            "closed_this_month": qs.filter(
                status="closed",
                closed_date__month=today.month,
                closed_date__year=today.year,
            ).count(),
        })


class QualityControlDashboardView(OrgScopedMixin, APIView):
    """Aggregate KPIs across inspections, QC plans, and NCRs."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP

    def get(self, request):
        org = self._resolve_request_org()
        today = date.today()

        # Inspection stats
        inspections = ProjectExecutionInspection.objects.filter(
            organization=org,
        )
        total_inspections = inspections.count()
        passed = inspections.filter(status="passed").count()
        failed = inspections.filter(status="failed").count()
        first_time_pass_rate = (
            round(passed / total_inspections * 100, 1)
            if total_inspections > 0 else 0
        )

        # NCR stats
        ncrs = NonConformanceReport.objects.filter(organization=org)
        open_statuses = ["open", "under_review", "rectification", "verification"]
        open_ncrs = ncrs.filter(status__in=open_statuses).count()
        critical_ncrs = ncrs.filter(
            severity="critical", status__in=open_statuses,
        ).count()

        # QC Plan stats
        plans = QualityPlan.objects.filter(organization=org)
        active_plans = plans.filter(approval_status="approved").count()
        plans_due_review = plans.filter(
            approval_status="approved",
            next_review_date__lte=today,
        ).count()

        # Top recurring defect root causes
        top_defects = list(
            ncrs.values("root_cause")
            .annotate(count=Count("id"))
            .order_by("-count")[:5]
        )
        root_cause_labels = dict(NonConformanceReport.RootCause.choices)
        for entry in top_defects:
            entry["label"] = root_cause_labels.get(entry["root_cause"], entry["root_cause"])

        return Response({
            "total_inspections": total_inspections,
            "passed_inspections": passed,
            "failed_inspections": failed,
            "first_time_pass_rate": first_time_pass_rate,
            "open_ncrs": open_ncrs,
            "critical_ncrs": critical_ncrs,
            "active_plans": active_plans,
            "plans_due_review": plans_due_review,
            "top_defects": top_defects,
        })


# ── Project Pipeline ─────────────────────────────────────────────────


class PipelineOpportunityViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    search_fields = ["pipeline_ref", "name", "location", "description", "land_status"]
    filterset_fields = ["stage", "development_type", "ic_decision"]
    ordering_fields = ["created_at", "stage", "estimated_gdv", "expected_irr", "stage_order"]
    ordering = ["stage", "stage_order", "-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return PipelineOpportunityListSerializer
        if self.action in ("create", "update", "partial_update"):
            return PipelineOpportunityWriteSerializer
        return PipelineOpportunityDetailSerializer

    def get_queryset(self):
        return (
            PipelineOpportunity.objects.filter(organization=self._resolve_request_org())
            .select_related("project", "created_by")
        )

    def perform_create(self, serializer):
        serializer.save(
            organization=self._resolve_request_org(),
            created_by=self.request.user,
        )

    @action(detail=False, methods=["get"])
    def summary(self, request):
        org = self._resolve_request_org()
        qs = PipelineOpportunity.objects.filter(organization=org)
        stages = list(
            qs.values("stage")
            .annotate(count=Count("id"), total_gdv=Sum("estimated_gdv"))
            .order_by("stage")
        )
        stage_labels = dict(PipelineOpportunity.Stage.choices)
        for s in stages:
            s["label"] = stage_labels.get(s["stage"], s["stage"])
            s["total_gdv"] = str(s["total_gdv"] or 0)

        return Response({
            "total": qs.count(),
            "total_gdv": str(qs.aggregate(total=Sum("estimated_gdv"))["total"] or 0),
            "approved": qs.filter(stage="approved").count(),
            "stages": stages,
        })

    @action(detail=True, methods=["post"])
    def move_stage(self, request, pk=None):
        """Move an opportunity to a new stage. If moved to 'approved', optionally initialize a project."""
        opp = self.get_object()
        new_stage = request.data.get("stage")
        if new_stage not in dict(PipelineOpportunity.Stage.choices):
            return Response({"detail": "Invalid stage."}, status=400)
        opp.stage = new_stage
        opp.stage_order = int(request.data.get("stage_order", 0))
        opp.save()
        return Response(PipelineOpportunityListSerializer(opp).data)


# ── Project Setup ────────────────────────────────────────────────────


class ProjectSetupConfigViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = ProjectSetupConfigSerializer
    filterset_fields = ["project", "is_complete", "current_step"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return (
            ProjectSetupConfig.objects.filter(project__organization=self._resolve_request_org())
            .select_related("project", "pipeline_source")
            .prefetch_related("project__team_members")
        )

    @action(detail=False, methods=["post"])
    def initialize(self, request):
        """Create a new project + setup config in one step (the wizard endpoint)."""
        ser = ProjectSetupInitSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        org = self._resolve_request_org()

        project = Project.objects.create(
            organization=org,
            name=d["name"],
            project_type=d.get("project_type", "residential"),
            location=d.get("location", ""),
            description=d.get("description", ""),
            start_date=d.get("start_date"),
            target_end_date=d.get("target_end_date"),
            budget=d.get("budget"),
            number_of_units=d.get("number_of_units"),
            status="planning",
        )

        pipeline_source = None
        pipeline_id = d.get("pipeline_source")
        if pipeline_id:
            try:
                pipeline_source = PipelineOpportunity.objects.get(pk=pipeline_id, organization=org)
                pipeline_source.project = project
                pipeline_source.save(update_fields=["project"])
                # Seed budget from pipeline if not provided
                if not project.budget and pipeline_source.estimated_cost:
                    project.budget = pipeline_source.estimated_cost
                    project.save(update_fields=["budget"])
            except PipelineOpportunity.DoesNotExist:
                pass

        setup = ProjectSetupConfig.objects.create(
            project=project,
            pipeline_source=pipeline_source,
            planned_phases=d.get("planned_phases", 3),
            survey_plan_ref=d.get("survey_plan_ref", ""),
            certificate_of_occupancy=d.get("certificate_of_occupancy", ""),
            current_step="team_allocation",
        )

        return Response(ProjectSetupConfigSerializer(setup).data, status=201)


class ProjectTeamMemberViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = ProjectTeamMemberSerializer
    filterset_fields = ["project", "role", "is_active"]
    search_fields = ["name", "email", "company"]
    ordering = ["role", "name"]

    def get_queryset(self):
        return ProjectTeamMember.objects.filter(
            project__organization=self._resolve_request_org(),
        ).select_related("project", "user")

    def perform_create(self, serializer):
        serializer.save()


# ── Feasibility & Viability ──────────────────────────────────────────


class FeasibilityStudyViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    search_fields = ["study_ref", "prepared_by", "demand_analysis", "notes"]
    filterset_fields = ["project", "status", "market_risk", "finance_risk"]
    ordering_fields = ["created_at", "expected_irr", "status"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return FeasibilityStudyListSerializer
        if self.action in ("create", "update", "partial_update"):
            return FeasibilityStudyWriteSerializer
        return FeasibilityStudyDetailSerializer

    def get_queryset(self):
        return (
            FeasibilityStudy.objects.filter(organization=self._resolve_request_org())
            .select_related("project", "pipeline_source", "created_by")
        )

    def perform_create(self, serializer):
        serializer.save(
            organization=self._resolve_request_org(),
            created_by=self.request.user,
        )


# ── Land Acquisition ────────────────────────────────────────────────


class LandAcquisitionViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    search_fields = ["parcel_id", "location", "seller_name", "description"]
    filterset_fields = ["project", "title_type", "verification_status", "acquisition_status"]
    ordering_fields = ["created_at", "purchase_price", "acquisition_status"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return LandAcquisitionListSerializer
        if self.action in ("create", "update", "partial_update"):
            return LandAcquisitionWriteSerializer
        return LandAcquisitionDetailSerializer

    def get_queryset(self):
        return (
            LandAcquisition.objects.filter(organization=self._resolve_request_org())
            .select_related("project", "created_by")
            .prefetch_related("payment_milestones")
        )

    def perform_create(self, serializer):
        serializer.save(
            organization=self._resolve_request_org(),
            created_by=self.request.user,
        )


class LandPaymentMilestoneViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    """Nested under /land-acquisitions/<pk>/payments/"""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = LandPaymentMilestoneSerializer
    ordering = ["sort_order", "due_date"]

    def get_queryset(self):
        return LandPaymentMilestone.objects.filter(
            land_acquisition_id=self.kwargs.get("acquisition_pk"),
        )

    def perform_create(self, serializer):
        serializer.save(land_acquisition_id=self.kwargs["acquisition_pk"])


# ── Development Budget ───────────────────────────────────────────────


class DevelopmentBudgetViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    search_fields = ["prepared_by", "notes"]
    filterset_fields = ["project", "status", "is_baseline"]
    ordering_fields = ["created_at", "version", "status"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return DevelopmentBudgetListSerializer
        if self.action in ("create", "update", "partial_update"):
            return DevelopmentBudgetWriteSerializer
        return DevelopmentBudgetDetailSerializer

    def get_queryset(self):
        return (
            DevelopmentBudget.objects.filter(organization=self._resolve_request_org())
            .select_related("project", "created_by")
            .prefetch_related("categories")
            .annotate(category_count=Count("categories"))
        )

    def perform_create(self, serializer):
        serializer.save(
            organization=self._resolve_request_org(),
            created_by=self.request.user,
        )


class DevelopmentBudgetCategoryViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    """Nested under /dev-budgets/<pk>/categories/"""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = DevelopmentBudgetCategorySerializer
    ordering = ["sort_order", "id"]

    def get_queryset(self):
        return DevelopmentBudgetCategory.objects.filter(
            budget_id=self.kwargs.get("budget_pk"),
        ).select_related("budget")

    def perform_create(self, serializer):
        serializer.save(budget_id=self.kwargs["budget_pk"])


# ── Project Financing ────────────────────────────────────────────────


class FinancingSourceViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    search_fields = ["reference", "name", "institution", "contact_person"]
    filterset_fields = ["project", "source_type", "status"]
    ordering_fields = ["created_at", "committed_amount", "drawn_amount", "maturity_date"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return FinancingSourceListSerializer
        if self.action in ("create", "update", "partial_update"):
            return FinancingSourceWriteSerializer
        return FinancingSourceDetailSerializer

    def get_queryset(self):
        return (
            FinancingSource.objects.filter(organization=self._resolve_request_org())
            .select_related("project", "created_by")
            .prefetch_related("drawdowns", "repayments", "covenants")
        )

    def perform_create(self, serializer):
        serializer.save(
            organization=self._resolve_request_org(),
            created_by=self.request.user,
        )

    @action(detail=False, methods=["get"])
    def dashboard(self, request):
        org = self._resolve_request_org()
        today = date.today()
        sources = FinancingSource.objects.filter(organization=org)
        active = sources.filter(status__in=["active", "fully_drawn"])

        total_committed = active.aggregate(t=Sum("committed_amount"))["t"] or Decimal("0")
        total_drawn = active.aggregate(t=Sum("drawn_amount"))["t"] or Decimal("0")
        available = total_committed - total_drawn

        # WACC approximation
        weighted_sum = Decimal("0")
        for s in active.filter(interest_rate__isnull=False):
            weight = s.committed_amount / total_committed if total_committed > 0 else Decimal("0")
            weighted_sum += (s.interest_rate or Decimal("0")) * weight
        wacc = round(float(weighted_sum), 2)

        # Funding mix
        equity_total = active.filter(source_type="equity").aggregate(t=Sum("committed_amount"))["t"] or Decimal("0")
        debt_total = total_committed - equity_total

        # Next repayment
        next_repayment = (
            FinancingRepayment.objects.filter(
                source__organization=org,
                status="scheduled",
                payment_date__gte=today,
            )
            .order_by("payment_date")
            .values("payment_date", "principal_amount", "interest_amount")
            .first()
        )

        # Alerts
        upcoming_drawdowns = sources.filter(
            status="active",
            first_drawdown_date__lte=today + timedelta(days=30),
            first_drawdown_date__gte=today,
        ).count()
        at_risk_covenants = FinancingCovenant.objects.filter(
            source__organization=org,
            status__in=["at_risk", "breached"],
        ).count()

        return Response({
            "total_committed": str(total_committed),
            "total_drawn": str(total_drawn),
            "available_liquidity": str(available),
            "wacc": wacc,
            "equity_total": str(equity_total),
            "debt_total": str(debt_total),
            "next_repayment": next_repayment,
            "upcoming_drawdowns": upcoming_drawdowns,
            "at_risk_covenants": at_risk_covenants,
        })


class FinancingDrawdownViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    """Nested under /financing/<pk>/drawdowns/"""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = FinancingDrawdownSerializer
    ordering = ["-request_date"]

    def get_queryset(self):
        return FinancingDrawdown.objects.filter(
            source_id=self.kwargs.get("source_pk"),
        )

    def perform_create(self, serializer):
        serializer.save(source_id=self.kwargs["source_pk"])


class FinancingRepaymentViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    """Nested under /financing/<pk>/repayments/"""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = FinancingRepaymentSerializer
    ordering = ["payment_date"]

    def get_queryset(self):
        return FinancingRepayment.objects.filter(
            source_id=self.kwargs.get("source_pk"),
        )

    def perform_create(self, serializer):
        serializer.save(source_id=self.kwargs["source_pk"])


class FinancingCovenantViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    """Nested under /financing/<pk>/covenants/"""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = FinancingCovenantSerializer
    ordering = ["name"]

    def get_queryset(self):
        return FinancingCovenant.objects.filter(
            source_id=self.kwargs.get("source_pk"),
        )

    def perform_create(self, serializer):
        serializer.save(source_id=self.kwargs["source_pk"])


# ── Consultants & Stakeholders ───────────────────────────────────────


class ProjectConsultantViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    search_fields = ["firm_name", "contact_person", "email", "scope_of_work"]
    filterset_fields = ["project", "discipline", "status", "compliance_status"]
    ordering_fields = ["created_at", "firm_name", "discipline", "contract_value"]
    ordering = ["discipline", "firm_name"]

    def get_serializer_class(self):
        if self.action == "list":
            return ProjectConsultantListSerializer
        if self.action in ("create", "update", "partial_update"):
            return ProjectConsultantWriteSerializer
        return ProjectConsultantDetailSerializer

    def get_queryset(self):
        return (
            ProjectConsultant.objects.filter(organization=self._resolve_request_org())
            .select_related("project", "created_by")
            .prefetch_related("payment_milestones", "deliverables", "communication_logs")
        )

    def perform_create(self, serializer):
        serializer.save(
            organization=self._resolve_request_org(),
            created_by=self.request.user,
        )


class ConsultantPaymentMilestoneViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    """Nested under /consultants/<pk>/payment-milestones/"""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = ConsultantPaymentMilestoneSerializer
    ordering = ["sort_order", "trigger_date"]

    def get_queryset(self):
        return ConsultantPaymentMilestone.objects.filter(
            consultant_id=self.kwargs.get("consultant_pk"),
        )

    def perform_create(self, serializer):
        serializer.save(consultant_id=self.kwargs["consultant_pk"])


class ConsultantDeliverableViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    """Nested under /consultants/<pk>/deliverables/"""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = ConsultantDeliverableSerializer
    ordering = ["sort_order", "due_date"]

    def get_queryset(self):
        return ConsultantDeliverable.objects.filter(
            consultant_id=self.kwargs.get("consultant_pk"),
        )

    def perform_create(self, serializer):
        serializer.save(consultant_id=self.kwargs["consultant_pk"])


class ConsultantCommunicationLogViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    """Nested under /consultants/<pk>/communications/"""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = ConsultantCommunicationLogSerializer
    ordering = ["-date"]

    def get_queryset(self):
        return ConsultantCommunicationLog.objects.filter(
            consultant_id=self.kwargs.get("consultant_pk"),
        )

    def perform_create(self, serializer):
        serializer.save(consultant_id=self.kwargs["consultant_pk"])


# ── Approvals & Permits ──────────────────────────────────────────────


class ProjectPermitViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    search_fields = ["reference", "name", "authority_name", "approval_certificate_ref"]
    filterset_fields = ["project", "permit_type", "status", "is_critical_path"]
    ordering_fields = ["created_at", "sort_order", "expected_approval_date", "expiry_date"]
    ordering = ["sort_order", "-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return ProjectPermitListSerializer
        if self.action in ("create", "update", "partial_update"):
            return ProjectPermitWriteSerializer
        return ProjectPermitDetailSerializer

    def get_queryset(self):
        return (
            ProjectPermit.objects.filter(organization=self._resolve_request_org())
            .select_related("project", "depends_on", "created_by")
            .prefetch_related("submissions", "queries")
        )

    def perform_create(self, serializer):
        serializer.save(
            organization=self._resolve_request_org(),
            created_by=self.request.user,
        )

    @action(detail=False, methods=["get"])
    def summary(self, request):
        org = self._resolve_request_org()
        qs = ProjectPermit.objects.filter(organization=org)
        today = date.today()
        pending_statuses = ["not_started", "application_filed", "under_review", "clarification"]
        delayed = qs.filter(
            status__in=pending_statuses,
            expected_approval_date__lt=today,
        ).count()
        return Response({
            "total": qs.count(),
            "pending": qs.filter(status__in=pending_statuses).count(),
            "approved": qs.filter(status__in=["approved", "conditional", "renewed"]).count(),
            "rejected": qs.filter(status="rejected").count(),
            "expired": qs.filter(status="expired").count(),
            "delayed": delayed,
            "critical_path_pending": qs.filter(is_critical_path=True, status__in=pending_statuses).count(),
        })


class PermitSubmissionViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    """Nested under /permits/<pk>/submissions/"""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = PermitSubmissionSerializer
    ordering = ["-submission_date"]

    def get_queryset(self):
        return PermitSubmission.objects.filter(
            permit_id=self.kwargs.get("permit_pk"),
        )

    def perform_create(self, serializer):
        serializer.save(permit_id=self.kwargs["permit_pk"])


class PermitQueryViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    """Nested under /permits/<pk>/queries/"""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = PermitQuerySerializer
    ordering = ["-query_date"]

    def get_queryset(self):
        return PermitQuery.objects.filter(
            permit_id=self.kwargs.get("permit_pk"),
        )

    def perform_create(self, serializer):
        serializer.save(permit_id=self.kwargs["permit_pk"])


# ── Design Management ────────────────────────────────────────────────


class DesignPhaseViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = DesignPhaseSerializer
    filterset_fields = ["project", "status"]
    ordering = ["sort_order"]

    def get_queryset(self):
        return DesignPhase.objects.filter(organization=self._resolve_request_org()).select_related("project")

    def perform_create(self, serializer):
        serializer.save(organization=self._resolve_request_org())


class DrawingViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    search_fields = ["drawing_number", "title", "submitted_by"]
    filterset_fields = ["project", "design_phase", "discipline", "approval_state"]
    ordering_fields = ["drawing_number", "discipline", "last_updated", "approval_state"]
    ordering = ["discipline", "drawing_number"]

    def get_serializer_class(self):
        if self.action == "list":
            return DrawingListSerializer
        if self.action in ("create", "update", "partial_update"):
            return DrawingWriteSerializer
        return DrawingDetailSerializer

    def get_queryset(self):
        return (
            Drawing.objects.filter(organization=self._resolve_request_org())
            .select_related("project", "design_phase", "created_by")
            .prefetch_related("revisions")
        )

    def perform_create(self, serializer):
        serializer.save(
            organization=self._resolve_request_org(),
            created_by=self.request.user,
        )


class DrawingRevisionViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    """Nested under /drawings/<pk>/revisions/"""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = DrawingRevisionSerializer
    ordering = ["-submitted_date"]

    def get_queryset(self):
        return DrawingRevision.objects.filter(drawing_id=self.kwargs.get("drawing_pk"))

    def perform_create(self, serializer):
        rev = serializer.save(drawing_id=self.kwargs["drawing_pk"])
        # Auto-supersede previous revision on the parent drawing
        drawing = rev.drawing
        drawing.current_revision = rev.revision_code
        if rev.approval_state:
            drawing.approval_state = rev.approval_state
        drawing.save(update_fields=["current_revision", "approval_state"])


class DesignReviewMeetingViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = DesignReviewMeetingSerializer
    search_fields = ["title", "attendees", "key_decisions"]
    filterset_fields = ["project"]
    ordering = ["-date"]

    def get_queryset(self):
        return (
            DesignReviewMeeting.objects.filter(organization=self._resolve_request_org())
            .select_related("project")
            .prefetch_related("linked_drawings")
        )

    def perform_create(self, serializer):
        serializer.save(organization=self._resolve_request_org())


# ── Procurement Planning ─────────────────────────────────────────────


class ProcurementPlanViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    filterset_fields = ["project"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return ProcurementPlanListSerializer
        if self.action in ("create", "update", "partial_update"):
            return ProcurementPlanWriteSerializer
        return ProcurementPlanDetailSerializer

    def get_queryset(self):
        return (
            ProcurementPlan.objects.filter(organization=self._resolve_request_org())
            .select_related("project", "created_by")
            .prefetch_related("packages", "packages__bidders")
            .annotate(
                package_count=Count("packages"),
                total_allocated=Sum("packages__estimated_budget"),
                total_contracted=Sum("packages__contract_value"),
            )
        )

    def perform_create(self, serializer):
        serializer.save(
            organization=self._resolve_request_org(),
            created_by=self.request.user,
        )


class ProcurementPackageViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    """Nested under /procurement-plans/<pk>/packages/"""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    search_fields = ["name", "awarded_to"]
    filterset_fields = ["status"]
    ordering = ["sort_order", "name"]

    def get_serializer_class(self):
        if self.action == "list":
            return ProcurementPackageListSerializer
        if self.action in ("create", "update", "partial_update"):
            return ProcurementPackageWriteSerializer
        return ProcurementPackageDetailSerializer

    def get_queryset(self):
        return (
            ProcurementPackage.objects.filter(plan_id=self.kwargs.get("plan_pk"))
            .prefetch_related("bidders")
            .annotate(bidder_count=Count("bidders"))
        )

    def perform_create(self, serializer):
        serializer.save(plan_id=self.kwargs["plan_pk"])


class PackageBidderViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    """Nested under /procurement-plans/<pk>/packages/<pk>/bidders/"""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = PackageBidderSerializer
    ordering = ["-total_score", "firm_name"]

    def get_queryset(self):
        return PackageBidder.objects.filter(package_id=self.kwargs.get("package_pk"))

    def perform_create(self, serializer):
        serializer.save(package_id=self.kwargs["package_pk"])


# ── Sales & Revenue Forecast ─────────────────────────────────────────


class SalesRevenueForecastViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    filterset_fields = ["project"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return SalesRevenueForecastListSerializer
        if self.action in ("create", "update", "partial_update"):
            return SalesRevenueForecastWriteSerializer
        return SalesRevenueForecastDetailSerializer

    def get_queryset(self):
        return (
            SalesRevenueForecast.objects.filter(organization=self._resolve_request_org())
            .select_related("project", "created_by")
            .prefetch_related("units", "phase_targets")
            .annotate(
                total_units=Count("units"),
                sold_units=Count("units", filter=Q(units__status="sold")),
                reserved_units=Count("units", filter=Q(units__status="reserved")),
                actual_revenue=Sum("units__sold_price", filter=Q(units__status="sold")),
            )
        )

    def perform_create(self, serializer):
        serializer.save(
            organization=self._resolve_request_org(),
            created_by=self.request.user,
        )


class SaleableUnitViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    """Nested under /sales-forecasts/<pk>/units/"""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = SaleableUnitSerializer
    search_fields = ["unit_id", "buyer_name"]
    filterset_fields = ["unit_type", "status"]
    ordering = ["sort_order", "unit_id"]

    def get_queryset(self):
        return SaleableUnit.objects.filter(forecast_id=self.kwargs.get("forecast_pk"))

    def perform_create(self, serializer):
        serializer.save(forecast_id=self.kwargs["forecast_pk"])


class SalesPhaseTargetViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    """Nested under /sales-forecasts/<pk>/phase-targets/"""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = SalesPhaseTargetSerializer
    ordering = ["sort_order", "start_date"]

    def get_queryset(self):
        return SalesPhaseTarget.objects.filter(forecast_id=self.kwargs.get("forecast_pk"))

    def perform_create(self, serializer):
        serializer.save(forecast_id=self.kwargs["forecast_pk"])


# ── Stage Gates ──────────────────────────────────────────────────────


class StageGateViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    search_fields = ["name", "decided_by", "conditions"]
    filterset_fields = ["project", "status"]
    ordering_fields = ["sort_order", "scheduled_review_date", "decision_date"]
    ordering = ["sort_order"]

    def get_serializer_class(self):
        if self.action == "list":
            return StageGateListSerializer
        if self.action in ("create", "update", "partial_update"):
            return StageGateWriteSerializer
        return StageGateDetailSerializer

    def get_queryset(self):
        return (
            StageGate.objects.filter(organization=self._resolve_request_org())
            .select_related("project", "created_by")
            .prefetch_related("prerequisite_milestones")
            .annotate(prerequisite_count=Count("prerequisite_milestones"))
        )

    def perform_create(self, serializer):
        serializer.save(
            organization=self._resolve_request_org(),
            created_by=self.request.user,
        )

    @action(detail=False, methods=["get"])
    def summary(self, request):
        org = self._resolve_request_org()
        today = date.today()
        qs = StageGate.objects.filter(organization=org)
        project_id = request.query_params.get("project")
        if project_id:
            qs = qs.filter(project_id=project_id)

        locked = qs.filter(status="locked").count()
        under_review = qs.filter(status="under_review").count()
        passed = qs.filter(status__in=["open", "conditional"]).count()
        overdue = qs.filter(
            status__in=["locked", "under_review"],
            scheduled_review_date__lt=today,
        ).count()

        upcoming = list(
            qs.filter(
                status__in=["locked", "under_review"],
                scheduled_review_date__gte=today,
                scheduled_review_date__lte=today + timedelta(days=90),
            )
            .order_by("scheduled_review_date")
            .values("id", "name", "scheduled_review_date", "status")[:5]
        )

        return Response({
            "total": qs.count(),
            "locked": locked,
            "under_review": under_review,
            "passed": passed,
            "overdue": overdue,
            "upcoming": upcoming,
        })


# ── Document Control ─────────────────────────────────────────────────


class ProjectDocumentViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    search_fields = ["reference", "title", "author", "source", "description", "linked_module"]
    filterset_fields = ["project", "folder", "classification", "execution_status"]
    ordering_fields = ["created_at", "updated_at", "title", "folder", "expiry_date"]
    ordering = ["folder", "title"]

    def get_serializer_class(self):
        if self.action == "list":
            return ProjectDocumentListSerializer
        if self.action in ("create", "update", "partial_update"):
            return ProjectDocumentWriteSerializer
        return ProjectDocumentDetailSerializer

    def get_queryset(self):
        return (
            ProjectDocument.objects.filter(organization=self._resolve_request_org())
            .select_related("project", "created_by")
            .prefetch_related("versions", "transmittals")
        )

    def perform_create(self, serializer):
        serializer.save(
            organization=self._resolve_request_org(),
            created_by=self.request.user,
        )


class DocumentVersionViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    """Nested under /documents/<pk>/versions/"""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = DocumentVersionSerializer
    ordering = ["-uploaded_date"]

    def get_queryset(self):
        return DocumentVersion.objects.filter(document_id=self.kwargs.get("document_pk"))

    def perform_create(self, serializer):
        doc_pk = self.kwargs["document_pk"]
        # Mark previous versions as not current
        DocumentVersion.objects.filter(document_id=doc_pk, is_current=True).update(is_current=False)
        version = serializer.save(document_id=doc_pk, is_current=True)
        # Update parent document's current_version
        ProjectDocument.objects.filter(id=doc_pk).update(current_version=version.version_label)


class DocumentTransmittalViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    """Nested under /documents/<pk>/transmittals/"""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = DocumentTransmittalSerializer
    ordering = ["-sent_date"]

    def get_queryset(self):
        return DocumentTransmittal.objects.filter(document_id=self.kwargs.get("document_pk"))

    def perform_create(self, serializer):
        serializer.save(document_id=self.kwargs["document_pk"])


class MeetingMinutesArchiveViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = MeetingMinutesArchiveSerializer
    search_fields = ["title", "series", "attendees", "minutes_text"]
    filterset_fields = ["project", "series"]
    ordering = ["-date"]

    def get_queryset(self):
        return MeetingMinutesArchive.objects.filter(
            organization=self._resolve_request_org(),
        ).select_related("project")

    def perform_create(self, serializer):
        serializer.save(organization=self._resolve_request_org())


# ── Project Communications ───────────────────────────────────────────


class ProjectAnnouncementViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = ProjectAnnouncementSerializer
    search_fields = ["subject", "body", "published_by"]
    filterset_fields = ["project", "priority", "audience", "is_pinned"]
    ordering = ["-is_pinned", "-published_at"]

    def get_queryset(self):
        return (
            ProjectAnnouncement.objects.filter(organization=self._resolve_request_org())
            .select_related("project")
        )

    def perform_create(self, serializer):
        serializer.save(organization=self._resolve_request_org())


class ProjectDecisionLogViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = ProjectDecisionLogSerializer
    search_fields = ["decision_id", "subject", "description", "decided_by", "rationale"]
    filterset_fields = ["project", "status"]
    ordering = ["-decision_date"]

    def get_queryset(self):
        return (
            ProjectDecisionLog.objects.filter(organization=self._resolve_request_org())
            .select_related("project", "created_by")
        )

    def perform_create(self, serializer):
        serializer.save(
            organization=self._resolve_request_org(),
            created_by=self.request.user,
        )


class StakeholderUpdateViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    search_fields = ["title", "executive_summary", "prepared_by"]
    filterset_fields = ["project", "frequency"]
    ordering = ["-report_date"]

    def get_serializer_class(self):
        if self.action == "list":
            return StakeholderUpdateListSerializer
        if self.action in ("create", "update", "partial_update"):
            return StakeholderUpdateWriteSerializer
        return StakeholderUpdateDetailSerializer

    def get_queryset(self):
        return (
            StakeholderUpdate.objects.filter(organization=self._resolve_request_org())
            .select_related("project")
        )

    def perform_create(self, serializer):
        serializer.save(organization=self._resolve_request_org())


# ── Project Reporting ────────────────────────────────────────────────


class ProjectReportViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    search_fields = ["reference", "title", "executive_summary", "prepared_by"]
    filterset_fields = ["project", "report_type", "is_frozen"]
    ordering_fields = ["report_date", "created_at", "report_type"]
    ordering = ["-report_date"]

    def get_serializer_class(self):
        if self.action == "list":
            return ProjectReportListSerializer
        if self.action in ("create", "update", "partial_update"):
            return ProjectReportWriteSerializer
        return ProjectReportDetailSerializer

    def get_queryset(self):
        return (
            ProjectReport.objects.filter(organization=self._resolve_request_org())
            .select_related("project", "created_by")
        )

    def perform_create(self, serializer):
        serializer.save(
            organization=self._resolve_request_org(),
            created_by=self.request.user,
        )


# ── Project Closeout ─────────────────────────────────────────────────


class ProjectCloseoutViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    filterset_fields = ["project", "status"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return ProjectCloseoutListSerializer
        if self.action in ("create", "update", "partial_update"):
            return ProjectCloseoutWriteSerializer
        return ProjectCloseoutDetailSerializer

    def get_queryset(self):
        return (
            ProjectCloseout.objects.filter(organization=self._resolve_request_org())
            .select_related("project", "created_by")
            .prefetch_related("final_accounts", "snag_items", "warranties")
            .annotate(
                snag_count=Count("snag_items"),
                open_snag_count=Count("snag_items", filter=Q(snag_items__status__in=["open", "in_progress"])),
            )
        )

    def perform_create(self, serializer):
        serializer.save(
            organization=self._resolve_request_org(),
            created_by=self.request.user,
        )


class FinalAccountEntryViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    """Nested under /closeouts/<pk>/final-accounts/"""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = FinalAccountEntrySerializer
    ordering = ["contractor_name"]

    def get_queryset(self):
        return FinalAccountEntry.objects.filter(closeout_id=self.kwargs.get("closeout_pk"))

    def perform_create(self, serializer):
        serializer.save(closeout_id=self.kwargs["closeout_pk"])


class SnagListItemViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    """Nested under /closeouts/<pk>/snags/"""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = SnagListItemSerializer
    filterset_fields = ["status"]
    ordering = ["status", "-reported_date"]

    def get_queryset(self):
        return SnagListItem.objects.filter(closeout_id=self.kwargs.get("closeout_pk"))

    def perform_create(self, serializer):
        serializer.save(closeout_id=self.kwargs["closeout_pk"])


class WarrantyTrackerViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    """Nested under /closeouts/<pk>/warranties/"""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = WarrantyTrackerSerializer
    ordering = ["warranty_end"]

    def get_queryset(self):
        return WarrantyTracker.objects.filter(closeout_id=self.kwargs.get("closeout_pk"))

    def perform_create(self, serializer):
        serializer.save(closeout_id=self.kwargs["closeout_pk"])


# ── Resource Optimization (Cross-Project) ────────────────────────────


class ResourceOptimizationView(APIView):
    """
    Cross-project resource aggregation for multi-project optimization.
    Returns workforce demand, equipment deployments, and over-allocation alerts.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from collections import defaultdict

        org = request.user.profile.organization

        active_projects = list(
            Project.objects.filter(
                organization=org,
                status__in=["active", "in_progress", "planning"],
            ).values("id", "name", "start_date", "target_end_date", "budget")
        )

        # Workforce by trade × project
        workforce_raw = (
            ProjectWorkforceLog.objects.filter(organization=org)
            .values("project__id", "project__name", "trade")
            .annotate(
                headcount=Sum("laborers_count") + Sum("skilled_count") + Sum("supervisors_count"),
            )
            .order_by("-headcount")
        )

        trade_demand = defaultdict(lambda: {"total_headcount": 0, "projects": defaultdict(int)})
        for row in workforce_raw:
            trade = row["trade"] or "Unspecified"
            hc = row["headcount"] or 0
            trade_demand[trade]["total_headcount"] += hc
            trade_demand[trade]["projects"][row["project__name"]] += hc

        trade_summary = [
            {
                "trade": trade,
                "total_headcount": data["total_headcount"],
                "project_breakdown": [
                    {"project": pname, "headcount": hc}
                    for pname, hc in data["projects"].items()
                ],
                "project_count": len(data["projects"]),
            }
            for trade, data in sorted(trade_demand.items(), key=lambda x: -x[1]["total_headcount"])
        ]

        # Equipment conflict detection
        equipment_deployments = (
            EquipmentDeploymentLog.objects.filter(equipment__organization=org)
            .select_related("equipment", "project")
            .order_by("deployed_date")
        )

        equipment_conflicts = []
        equipment_usage = defaultdict(list)
        for dep in equipment_deployments:
            equipment_usage[dep.equipment_id].append(dep)

        for _eid, deps in equipment_usage.items():
            for i, a in enumerate(deps):
                for b in deps[i + 1:]:
                    a_end = a.returned_date
                    b_end = b.returned_date
                    if a_end and b.deployed_date > a_end:
                        continue
                    if b_end and a.deployed_date > b_end:
                        continue
                    equipment_conflicts.append({
                        "equipment": f"{a.equipment.asset_id} \u2014 {a.equipment.name}",
                        "project_a": a.project.name,
                        "dates_a": f"{a.deployed_date}\u2013{a.returned_date or 'ongoing'}",
                        "project_b": b.project.name,
                        "dates_b": f"{b.deployed_date}\u2013{b.returned_date or 'ongoing'}",
                    })

        # Over-allocation alerts
        alerts = []
        for ts in trade_summary:
            if ts["project_count"] > 1:
                alerts.append({
                    "type": "workforce",
                    "severity": "warning" if ts["project_count"] <= 3 else "critical",
                    "message": f"{ts['trade']} allocated across {ts['project_count']} projects ({ts['total_headcount']} total headcount)",
                    "trade": ts["trade"],
                    "projects": [p["project"] for p in ts["project_breakdown"]],
                })
        for conflict in equipment_conflicts:
            alerts.append({
                "type": "equipment",
                "severity": "critical",
                "message": f"{conflict['equipment']} double-booked: {conflict['project_a']} ({conflict['dates_a']}) vs {conflict['project_b']} ({conflict['dates_b']})",
                "equipment": conflict["equipment"],
                "projects": [conflict["project_a"], conflict["project_b"]],
            })

        return Response({
            "projects": active_projects,
            "trade_summary": trade_summary,
            "equipment_conflicts": equipment_conflicts,
            "alerts": alerts,
        })


class PredictiveIntelligenceView(APIView):
    """
    Predictive intelligence engine — uses historical + live data to
    forecast delays and recommend adjustments.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from collections import defaultdict
        from datetime import date

        from django.db.models import Avg as DbAvg
        from django.db.models import Max as DbMax

        org = request.user.profile.organization
        today = date.today()

        # ── 1. Historical performance: completed tasks ──
        completed_tasks = ProjectTask.objects.filter(
            organization=org,
            status="completed",
            due_date__isnull=False,
            completed_date__isnull=False,
        ).select_related("phase__project")

        # Category performance: avg overrun/underrun per category
        category_perf = defaultdict(lambda: {"count": 0, "total_delta": 0, "overrun_count": 0})
        trade_perf = defaultdict(lambda: {"count": 0, "total_delta": 0, "overrun_count": 0})

        for task in completed_tasks:
            delta = (task.completed_date - task.due_date).days
            cat = task.work_package or "General"
            category_perf[cat]["count"] += 1
            category_perf[cat]["total_delta"] += delta
            if delta > 0:
                category_perf[cat]["overrun_count"] += 1

            role = task.assigned_to or task.assigned_user.get_full_name() if task.assigned_user else "Unassigned"
            trade_perf[role]["count"] += 1
            trade_perf[role]["total_delta"] += delta
            if delta > 0:
                trade_perf[role]["overrun_count"] += 1

        historical_categories = sorted([
            {
                "category": cat,
                "tasks_completed": data["count"],
                "avg_delta_days": round(data["total_delta"] / data["count"], 1) if data["count"] else 0,
                "overrun_rate_pct": round(data["overrun_count"] / data["count"] * 100) if data["count"] else 0,
            }
            for cat, data in category_perf.items()
        ], key=lambda x: -x["overrun_rate_pct"])

        # ── 2. Active project forecasts ──
        active_projects = Project.objects.filter(
            organization=org,
            status__in=["active", "in_progress", "planning"],
        ).prefetch_related("phases", "phases__tasks")

        project_forecasts = []
        for project in active_projects:
            phases = project.phases.all()
            total_tasks = 0
            completed = 0
            overdue = 0
            total_budget = float(project.budget or 0)

            # Actual cost from phases
            actual_cost = sum(float(p.actual_cost or 0) for p in phases)

            for phase in phases:
                tasks = phase.tasks.all()
                total_tasks += tasks.count()
                completed += tasks.filter(status="completed").count()
                overdue += tasks.filter(
                    status__in=["pending", "in_progress"],
                    due_date__lt=today,
                ).count()

            completion_pct = round(completed / total_tasks * 100) if total_tasks else 0
            overdue_pct = round(overdue / total_tasks * 100) if total_tasks else 0

            # Burn rate forecast
            days_elapsed = (today - project.start_date).days if project.start_date else 0
            days_planned = (project.target_end_date - project.start_date).days if project.start_date and project.target_end_date else 0

            if days_elapsed > 0 and completion_pct > 0:
                # At current rate, how many total days to finish?
                projected_total_days = round(days_elapsed / (completion_pct / 100))
                projected_end_delta = projected_total_days - days_planned if days_planned else 0
            else:
                projected_total_days = days_planned
                projected_end_delta = 0

            # Cost Performance Index
            if actual_cost > 0 and completion_pct > 0:
                earned_value = total_budget * (completion_pct / 100)
                cpi = round(earned_value / actual_cost, 2) if actual_cost else 1.0
                cost_at_completion = round(total_budget / cpi) if cpi > 0 else total_budget
                cost_variance = cost_at_completion - total_budget
            else:
                cpi = 1.0
                cost_at_completion = total_budget
                cost_variance = 0

            # Schedule Performance Index
            if days_planned > 0 and days_elapsed > 0:
                planned_pct = min(100, round(days_elapsed / days_planned * 100))
                spi = round(completion_pct / planned_pct, 2) if planned_pct > 0 else 1.0
            else:
                spi = 1.0
                planned_pct = 0

            # Risk level
            if spi < 0.8 or cpi < 0.8:
                risk_level = "critical"
            elif spi < 0.95 or cpi < 0.95:
                risk_level = "at_risk"
            elif overdue_pct > 20:
                risk_level = "at_risk"
            else:
                risk_level = "on_track"

            project_forecasts.append({
                "id": project.id,
                "name": project.name,
                "start_date": str(project.start_date) if project.start_date else None,
                "target_end_date": str(project.target_end_date) if project.target_end_date else None,
                "total_tasks": total_tasks,
                "completed_tasks": completed,
                "overdue_tasks": overdue,
                "completion_pct": completion_pct,
                "overdue_pct": overdue_pct,
                "days_elapsed": days_elapsed,
                "days_planned": days_planned,
                "projected_total_days": projected_total_days,
                "projected_end_delta": projected_end_delta,
                "budget": total_budget,
                "actual_cost": round(actual_cost),
                "cpi": cpi,
                "spi": spi,
                "cost_at_completion": round(cost_at_completion),
                "cost_variance": round(cost_variance),
                "risk_level": risk_level,
            })

        # Sort: critical first, then at_risk, then on_track
        risk_order = {"critical": 0, "at_risk": 1, "on_track": 2}
        project_forecasts.sort(key=lambda x: risk_order.get(x["risk_level"], 3))

        # ── 3. Recommendations ──
        recommendations = []

        for pf in project_forecasts:
            if pf["risk_level"] == "critical":
                if pf["spi"] < 0.8:
                    recommendations.append({
                        "project": pf["name"],
                        "type": "schedule",
                        "severity": "critical",
                        "title": "Significant schedule slippage detected",
                        "detail": f"SPI is {pf['spi']} — project is completing work at {round(pf['spi'] * 100)}% of planned rate. At current pace, expect +{pf['projected_end_delta']} days beyond target.",
                        "action": "Consider adding resources, reducing scope, or fast-tracking parallel activities.",
                    })
                if pf["cpi"] < 0.8:
                    recommendations.append({
                        "project": pf["name"],
                        "type": "cost",
                        "severity": "critical",
                        "title": "Budget overrun trajectory",
                        "detail": f"CPI is {pf['cpi']} — spending {round((1 / pf['cpi'] - 1) * 100)}% more per unit of work than planned. Estimated cost at completion: {round(pf['cost_at_completion']):,}.",
                        "action": "Review procurement costs, negotiate with vendors, or value-engineer remaining scope.",
                    })
            elif pf["risk_level"] == "at_risk":
                if pf["overdue_tasks"] > 0:
                    recommendations.append({
                        "project": pf["name"],
                        "type": "schedule",
                        "severity": "warning",
                        "title": f"{pf['overdue_tasks']} overdue task(s)",
                        "detail": f"{pf['overdue_pct']}% of tasks are past due date. This may cascade to downstream dependencies.",
                        "action": "Prioritize overdue tasks, reassign resources, or negotiate deadline extensions.",
                    })

        for hc in historical_categories[:3]:
            if hc["overrun_rate_pct"] > 50:
                recommendations.append({
                    "project": "Portfolio-wide",
                    "type": "pattern",
                    "severity": "info",
                    "title": f"'{hc['category']}' tasks historically overrun",
                    "detail": f"{hc['overrun_rate_pct']}% of '{hc['category']}' tasks finish late (avg {hc['avg_delta_days']:+.1f} days). Consider adding buffer to future estimates.",
                    "action": f"Apply a {min(30, max(10, abs(int(hc['avg_delta_days'])) * 2))}% contingency buffer to '{hc['category']}' task durations.",
                })

        return Response({
            "project_forecasts": project_forecasts,
            "historical_performance": historical_categories[:15],
            "recommendations": recommendations,
            "generated_at": today.isoformat(),
        })


# ── Construction Reports ─────────────────────────────────────────────


class ConstructionReportViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    search_fields = ["reference", "title", "executive_summary", "prepared_by"]
    filterset_fields = ["project", "category", "status", "frequency"]
    ordering_fields = ["created_at", "reporting_period_end", "category", "status"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return ConstructionReportListSerializer
        if self.action in ("create", "update", "partial_update"):
            return ConstructionReportWriteSerializer
        return ConstructionReportDetailSerializer

    def get_queryset(self):
        return (
            ConstructionReport.objects.filter(organization=self._resolve_request_org())
            .select_related("project", "created_by")
        )

    def perform_create(self, serializer):
        serializer.save(
            organization=self._resolve_request_org(),
            created_by=self.request.user,
        )

    @action(detail=False, methods=["get"])
    def summary(self, request):
        org = self._resolve_request_org()
        qs = ConstructionReport.objects.filter(organization=org)
        return Response({
            "total": qs.count(),
            "draft": qs.filter(status="draft").count(),
            "in_review": qs.filter(status="in_review").count(),
            "published": qs.filter(status="published").count(),
            "by_category": list(
                qs.values("category").annotate(count=Count("id")).order_by("category")
            ),
        })


# ── RFIs ─────────────────────────────────────────────────────────────


class RFIViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    search_fields = ["rfi_number", "subject", "query", "ball_in_court", "submitted_by"]
    filterset_fields = ["project", "discipline", "urgency", "status"]
    ordering_fields = ["created_at", "submitted_date", "urgency", "status"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return RFIListSerializer
        if self.action in ("create", "update", "partial_update"):
            return RFIWriteSerializer
        return RFIDetailSerializer

    def get_queryset(self):
        return (
            RFI.objects.filter(organization=self._resolve_request_org())
            .select_related("project", "created_by")
            .prefetch_related("comments")
            .annotate(comment_count=Count("comments"))
        )

    def perform_create(self, serializer):
        serializer.save(
            organization=self._resolve_request_org(),
            created_by=self.request.user,
        )

    @action(detail=False, methods=["get"])
    def summary(self, request):
        org = self._resolve_request_org()
        today = date.today()
        qs = RFI.objects.filter(organization=org)
        open_statuses = ["open", "under_review"]
        return Response({
            "total": qs.count(),
            "open": qs.filter(status__in=open_statuses).count(),
            "answered": qs.filter(status="answered").count(),
            "closed": qs.filter(status="closed").count(),
            "high_urgency": qs.filter(urgency="high", status__in=open_statuses).count(),
            "overdue_sla": qs.filter(
                status__in=open_statuses,
                submitted_date__lt=today - timedelta(days=2),
            ).count(),
        })


class RFICommentViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    """Nested under /rfis/<pk>/comments/"""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = RFICommentSerializer
    ordering = ["created_at"]

    def get_queryset(self):
        return RFIComment.objects.filter(rfi_id=self.kwargs.get("rfi_pk"))

    def perform_create(self, serializer):
        serializer.save(
            rfi_id=self.kwargs["rfi_pk"],
            created_by=self.request.user,
        )


# ── Site Instructions ────────────────────────────────────────────────


class SiteInstructionViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    search_fields = ["si_number", "title", "description", "issued_by", "location"]
    filterset_fields = ["project", "instruction_type", "priority", "status"]
    ordering_fields = ["created_at", "issued_date", "compliance_deadline", "priority", "status"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return SiteInstructionListSerializer
        if self.action in ("create", "update", "partial_update"):
            return SiteInstructionWriteSerializer
        return SiteInstructionDetailSerializer

    def get_queryset(self):
        return (
            SiteInstruction.objects.filter(organization=self._resolve_request_org())
            .select_related("project", "linked_variation", "created_by")
        )

    def perform_create(self, serializer):
        serializer.save(
            organization=self._resolve_request_org(),
            created_by=self.request.user,
        )

    @action(detail=False, methods=["get"])
    def summary(self, request):
        org = self._resolve_request_org()
        qs = SiteInstruction.objects.filter(organization=org)
        open_statuses = ["issued", "acknowledged", "in_progress"]
        return Response({
            "total": qs.count(),
            "open": qs.filter(status__in=open_statuses).count(),
            "completed": qs.filter(status__in=["completed", "verified", "closed"]).count(),
            "urgent": qs.filter(priority="urgent", status__in=open_statuses).count(),
            "with_financial_impact": qs.filter(has_financial_impact=True).count(),
        })


# ── HSE Incidents ────────────────────────────────────────────────────


class HSEIncidentViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    search_fields = [
        "incident_number", "title", "description", "location",
        "reported_by", "persons_involved",
    ]
    filterset_fields = ["project", "classification", "root_cause", "status"]
    ordering_fields = [
        "incident_date", "created_at", "classification", "status", "lost_time_days",
    ]
    ordering = ["-incident_date", "-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return HSEIncidentListSerializer
        if self.action in ("create", "update", "partial_update"):
            return HSEIncidentWriteSerializer
        return HSEIncidentDetailSerializer

    def get_queryset(self):
        return (
            HSEIncident.objects.filter(organization=self._resolve_request_org())
            .select_related("project", "created_by")
        )

    def perform_create(self, serializer):
        serializer.save(
            organization=self._resolve_request_org(),
            created_by=self.request.user,
        )

    @action(detail=False, methods=["get"])
    def summary(self, request):
        org = self._resolve_request_org()
        qs = HSEIncident.objects.filter(organization=org)
        open_statuses = ["reported", "investigating", "corrective_action"]
        return Response({
            "total": qs.count(),
            "open": qs.filter(status__in=open_statuses).count(),
            "closed": qs.filter(status="closed").count(),
            "near_misses": qs.filter(classification="near_miss").count(),
            "lost_time_incidents": qs.filter(lost_time_days__gt=0).count(),
            "requires_regulatory": qs.filter(requires_regulatory_report=True, status__in=open_statuses).count(),
        })


# ── HSE Permits to Work ─────────────────────────────────────────────


class HSEPermitToWorkViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    search_fields = [
        "permit_number", "title", "description", "location",
        "requested_by", "approved_by", "task_description",
    ]
    filterset_fields = ["project", "permit_type", "status"]
    ordering_fields = [
        "created_at", "valid_from", "valid_until", "permit_type", "status",
    ]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return HSEPermitListSerializer
        if self.action in ("create", "update", "partial_update"):
            return HSEPermitWriteSerializer
        return HSEPermitDetailSerializer

    def get_queryset(self):
        return (
            HSEPermitToWork.objects.filter(organization=self._resolve_request_org())
            .select_related("project", "created_by")
        )

    def perform_create(self, serializer):
        serializer.save(
            organization=self._resolve_request_org(),
            created_by=self.request.user,
        )

    @action(detail=False, methods=["get"])
    def summary(self, request):
        org = self._resolve_request_org()
        now = timezone.now()
        qs = HSEPermitToWork.objects.filter(organization=org)
        return Response({
            "total": qs.count(),
            "active": qs.filter(status="active").count(),
            "pending_approval": qs.filter(status="pending_approval").count(),
            "expired": qs.filter(status="expired").count(),
            "expiring_soon": qs.filter(
                status="active",
                valid_until__lte=now + timedelta(days=2),
                valid_until__gt=now,
            ).count(),
        })


# ── HSE Toolbox Talks ───────────────────────────────────────────────


class HSEToolboxTalkViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    search_fields = [
        "tbt_number", "topic", "description", "conducted_by",
        "location", "key_points",
    ]
    filterset_fields = ["project", "shift"]
    ordering_fields = ["conducted_date", "created_at", "attendees_count"]
    ordering = ["-conducted_date", "-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return HSEToolboxTalkListSerializer
        if self.action in ("create", "update", "partial_update"):
            return HSEToolboxTalkWriteSerializer
        return HSEToolboxTalkDetailSerializer

    def get_queryset(self):
        return (
            HSEToolboxTalk.objects.filter(organization=self._resolve_request_org())
            .select_related("project", "created_by")
        )

    def perform_create(self, serializer):
        serializer.save(
            organization=self._resolve_request_org(),
            created_by=self.request.user,
        )

    @action(detail=False, methods=["get"])
    def summary(self, request):
        org = self._resolve_request_org()
        today = date.today()
        qs = HSEToolboxTalk.objects.filter(organization=org)
        return Response({
            "total": qs.count(),
            "this_month": qs.filter(
                conducted_date__year=today.year,
                conducted_date__month=today.month,
            ).count(),
            "total_attendees": qs.aggregate(total=Coalesce(Sum("attendees_count"), 0))["total"],
        })


# ── HSE Dashboard ────────────────────────────────────────────────────


class HSEDashboardView(OrgScopedMixin, APIView):
    """Aggregate KPIs across HSE incidents, permits, and toolbox talks."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP

    def get(self, request):
        org = self._resolve_request_org()
        today = date.today()

        # Incident stats
        incidents = HSEIncident.objects.filter(organization=org)
        open_statuses = ["reported", "investigating", "corrective_action"]
        total_incidents = incidents.count()
        open_incidents = incidents.filter(status__in=open_statuses).count()
        total_lost_days = incidents.aggregate(
            total=Coalesce(Sum("lost_time_days"), 0),
        )["total"]

        # Safe days: days since last incident with lost time
        last_lost_time = (
            incidents.filter(lost_time_days__gt=0)
            .order_by("-incident_date")
            .values_list("incident_date", flat=True)
            .first()
        )
        safe_days_count = (today - last_lost_time).days if last_lost_time else None

        # Incident count by classification
        classification_labels = dict(HSEIncident.Classification.choices)
        incident_count_by_classification = list(
            incidents.values("classification")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        for entry in incident_count_by_classification:
            entry["label"] = classification_labels.get(entry["classification"], entry["classification"])

        # Incident count by root cause
        root_cause_labels = dict(HSEIncident.RootCause.choices)
        incident_count_by_root_cause = list(
            incidents.exclude(root_cause="")
            .values("root_cause")
            .annotate(count=Count("id"))
            .order_by("-count")[:5]
        )
        for entry in incident_count_by_root_cause:
            entry["label"] = root_cause_labels.get(entry["root_cause"], entry["root_cause"])

        # Permit stats
        permits = HSEPermitToWork.objects.filter(organization=org)
        active_permits = permits.filter(status="active").count()
        expired_permits = permits.filter(status="expired").count()

        # Toolbox talk stats
        talks = HSEToolboxTalk.objects.filter(organization=org)
        talks_this_month = talks.filter(
            conducted_date__year=today.year,
            conducted_date__month=today.month,
        ).count()
        total_attendees_this_month = talks.filter(
            conducted_date__year=today.year,
            conducted_date__month=today.month,
        ).aggregate(total=Coalesce(Sum("attendees_count"), 0))["total"]

        # Additional stats the frontend expects
        lost_time_injuries = incidents.filter(lost_time_days__gt=0).count()
        pending_permits = permits.filter(status="pending").count()
        total_tbts = talks.count()

        return Response({
            "safe_days": safe_days_count,
            "lost_time_injuries": lost_time_injuries,
            "total_incidents": total_incidents,
            "open_incidents": open_incidents,
            "total_lost_days": total_lost_days,
            "classification_breakdown": incident_count_by_classification,
            "root_cause_breakdown": incident_count_by_root_cause,
            "active_permits": active_permits,
            "expired_permits": expired_permits,
            "pending_permits": pending_permits,
            "total_tbts": total_tbts,
            "tbts_this_month": talks_this_month,
            "total_attendees_this_month": total_attendees_this_month,
        })


# ── Commissioning Plans ─────────────────────────────────────────────


class CommissioningPlanViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    search_fields = [
        "plan_number", "name", "description",
        "witness_name", "notes",
    ]
    filterset_fields = ["project", "system_type", "status"]
    ordering_fields = [
        "created_at", "target_date", "completed_date", "system_type", "status",
    ]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return CommissioningPlanListSerializer
        if self.action in ("create", "update", "partial_update"):
            return CommissioningPlanWriteSerializer
        return CommissioningPlanDetailSerializer

    def get_queryset(self):
        return (
            CommissioningPlan.objects.filter(organization=self._resolve_request_org())
            .select_related("project", "created_by")
            .prefetch_related("test_records", "punch_items")
            .annotate(
                test_count=Count("test_records", distinct=True),
                punch_item_count=Count("punch_items", distinct=True),
            )
        )

    def perform_create(self, serializer):
        serializer.save(
            organization=self._resolve_request_org(),
            created_by=self.request.user,
        )

    @action(detail=False, methods=["get"])
    def summary(self, request):
        org = self._resolve_request_org()
        qs = CommissioningPlan.objects.filter(organization=org)
        return Response({
            "total": qs.count(),
            "draft": qs.filter(status="draft").count(),
            "in_progress": qs.filter(status="in_progress").count(),
            "passed": qs.filter(status="passed").count(),
            "failed": qs.filter(status="failed").count(),
            "certified": qs.filter(status="certified").count(),
        })

    @action(detail=True, methods=["post"])
    def certify(self, request, pk=None):
        """Validate all tests passed + witness present, then certify the plan."""
        plan = self.get_object()

        # Validation checks
        errors = []
        if plan.status == "certified":
            return Response({"detail": "Plan is already certified."}, status=status.HTTP_400_BAD_REQUEST)

        test_records = plan.test_records.all()
        if not test_records.exists():
            errors.append("No test records found — cannot certify without tests.")

        pending_tests = test_records.filter(result="pending")
        if pending_tests.exists():
            errors.append(f"{pending_tests.count()} test(s) still pending.")

        failed_tests = test_records.filter(result__in=["fail", "retest"])
        if failed_tests.exists():
            errors.append(f"{failed_tests.count()} test(s) failed or require retest.")

        open_punch = plan.punch_items.exclude(status__in=["resolved", "accepted"])
        if open_punch.exists():
            errors.append(f"{open_punch.count()} punch item(s) still open.")

        if plan.witness_required and not plan.witness_present:
            errors.append("Witness is required but not recorded as present.")

        if errors:
            return Response({
                "detail": "Certification blocked — prerequisites not met.",
                "errors": errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        # All checks passed — certify
        from django.utils import timezone
        plan.status = "certified"
        plan.completed_date = date.today()
        plan.certified_by = request.data.get("certified_by", request.user.get_full_name() or request.user.username)
        plan.certified_date = date.today()
        plan.approved_by = request.data.get("approved_by", "")
        plan.approved_date = date.today() if request.data.get("approved_by") else None
        plan.client_signoff_name = request.data.get("client_signoff_name", "")
        plan.client_signoff_date = date.today() if request.data.get("client_signoff_name") else None

        # Generate certificate number
        last_cert = (
            CommissioningPlan.objects.filter(certificate_number__startswith="CERT-")
            .order_by("-certificate_number")
            .values_list("certificate_number", flat=True)
            .first()
        )
        seq = 1
        if last_cert:
            try:
                seq = int(last_cert.split("-")[1]) + 1
            except (IndexError, ValueError):
                pass
        plan.certificate_number = f"CERT-{seq:05d}"
        plan.save()

        return Response({
            "detail": "Plan certified successfully.",
            "certificate_number": plan.certificate_number,
            "certified_by": plan.certified_by,
            "certified_date": str(plan.certified_date),
        })

    @action(detail=True, methods=["post"], url_path="submit-approval")
    def submit_approval(self, request, pk=None):
        """Submit commissioning plan for formal workflow approval."""
        plan = self.get_object()
        if plan.status not in ("passed",):
            return Response(
                {"detail": "Only plans with all tests passed can be submitted for approval."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            from apps.workflows.engine import submit_for_approval
            instance = submit_for_approval(plan, request.user)
            return Response({
                "detail": "Submitted for approval.",
                "workflow_instance_id": instance.pk,
            }, status=status.HTTP_201_CREATED)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class TestRecordViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    """Nested under /commissioning-plans/<pk>/tests/"""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = TestRecordSerializer
    search_fields = ["test_description", "reference_standard", "tested_by"]
    filterset_fields = ["result"]
    ordering = ["sort_order", "id"]

    def get_queryset(self):
        return TestRecord.objects.filter(
            plan_id=self.kwargs.get("plan_pk"),
        )

    def perform_create(self, serializer):
        serializer.save(plan_id=self.kwargs["plan_pk"])


class CommissioningPunchItemViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    """Nested under /commissioning-plans/<pk>/punch-items/"""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = CommissioningPunchItemSerializer
    search_fields = ["item_number", "description", "location", "assigned_to"]
    filterset_fields = ["priority", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return CommissioningPunchItem.objects.filter(
            plan_id=self.kwargs.get("plan_pk"),
        )

    def perform_create(self, serializer):
        serializer.save(plan_id=self.kwargs["plan_pk"])


# ── Commissioning Dashboard ──────────────────────────────────────────


class CommissioningDashboardView(OrgScopedMixin, APIView):
    """Aggregate KPIs across commissioning plans, tests, and punch items."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP

    def get(self, request):
        org = self._resolve_request_org()

        plans = CommissioningPlan.objects.filter(organization=org)
        total_plans = plans.count()
        completed = plans.filter(status__in=["passed", "certified"]).count()
        in_progress = plans.filter(status="in_progress").count()
        has_failures = plans.filter(status="failed").count()

        # Test record stats
        tests = TestRecord.objects.filter(plan__organization=org)
        total_tests = tests.count()
        tests_passed = tests.filter(result="pass").count()
        tests_failed = tests.filter(result="fail").count()
        tests_pending = tests.filter(result="pending").count()

        # Punch item stats
        punch_items = CommissioningPunchItem.objects.filter(plan__organization=org)
        open_punch = punch_items.filter(status__in=["open", "in_progress"]).count()
        critical_punch = punch_items.filter(priority="critical", status__in=["open", "in_progress"]).count()

        # Go / No-go: all plans certified and no open critical punch items
        all_certified = total_plans > 0 and plans.exclude(status="certified").count() == 0
        no_critical_open = critical_punch == 0
        go_no_go = "GO" if (all_certified and no_critical_open) else "NO-GO"

        return Response({
            "total_plans": total_plans,
            "completed": completed,
            "in_progress": in_progress,
            "has_failures": has_failures,
            "total_tests": total_tests,
            "tests_passed": tests_passed,
            "tests_failed": tests_failed,
            "tests_pending": tests_pending,
            "open_punch_items": open_punch,
            "critical_punch_items": critical_punch,
            "go_no_go": go_no_go,
        })


# ── Cost Control ─────────────────────────────────────────────────────


class CostCodeBudgetViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    search_fields = ["cost_code", "description"]
    filterset_fields = ["project"]
    ordering_fields = ["sort_order", "cost_code", "original_budget", "actual_cost"]
    ordering = ["sort_order", "cost_code"]

    def get_serializer_class(self):
        if self.action == "list":
            return CostCodeBudgetListSerializer
        if self.action in ("create", "update", "partial_update"):
            return CostCodeBudgetWriteSerializer
        return CostCodeBudgetDetailSerializer

    def get_queryset(self):
        return (
            CostCodeBudget.objects.filter(organization=self._resolve_request_org())
            .select_related("project")
            .prefetch_related("transactions")
        )

    def perform_create(self, serializer):
        serializer.save(organization=self._resolve_request_org())

    @action(detail=False, methods=["get"], url_path="variance-summary")
    def variance_summary(self, request):
        org = self._resolve_request_org()
        qs = CostCodeBudget.objects.filter(organization=org)
        project_id = request.query_params.get("project")
        if project_id:
            qs = qs.filter(project_id=project_id)

        total_budget = qs.aggregate(t=Sum("original_budget"))["t"] or Decimal("0")
        total_changes = qs.aggregate(t=Sum("approved_changes"))["t"] or Decimal("0")
        total_committed = qs.aggregate(t=Sum("committed"))["t"] or Decimal("0")
        total_actual = qs.aggregate(t=Sum("actual_cost"))["t"] or Decimal("0")
        total_ftc = qs.aggregate(t=Sum("forecast_to_complete"))["t"] or Decimal("0")

        revised = total_budget + total_changes
        fac = total_actual + total_ftc
        variance = revised - fac

        return Response({
            "total_original_budget": str(total_budget),
            "total_approved_changes": str(total_changes),
            "total_revised_budget": str(revised),
            "total_committed": str(total_committed),
            "total_actual_cost": str(total_actual),
            "total_forecast_to_complete": str(total_ftc),
            "forecast_at_completion": str(fac),
            "total_variance": str(variance),
            "cost_code_count": qs.count(),
        })


class CostTransactionViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _PROJECT_ACTION_MAP
    serializer_class = CostTransactionSerializer
    search_fields = ["reference", "description", "vendor"]
    filterset_fields = ["project", "cost_code_budget", "transaction_type"]
    ordering = ["-transaction_date"]

    def get_queryset(self):
        return CostTransaction.objects.filter(organization=self._resolve_request_org())

    def perform_create(self, serializer):
        serializer.save(
            organization=self._resolve_request_org(),
            created_by=self.request.user,
        )
