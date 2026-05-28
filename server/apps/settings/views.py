import hashlib
from datetime import timedelta

from django.core.cache import cache
from django.db.models import Count, OuterRef, Prefetch, Q, Subquery
from django.utils import timezone
from django_filters import rest_framework as filters
from rest_framework import generics, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.services import get_workflow_notification_catalog
from apps.settings.permissions import HasRolePermission, bump_role_permission_cache_version
from apps.settings.reporting_dispatch import enqueue_report_run_execution

from .models import (
    TIER_MODULE_MAP,
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
    NotificationChannelSettings,
    NotificationTemplate,
    Permission,
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
    SlaSeverityTier,
    StageGateChecklistItem,
    StageGateRule,
    Subsidiary,
    SystemPreferences,
    TaskTemplate,
    TemplatePhase,
    ensure_default_document_automation_settings,
    ensure_default_notification_settings,
)
from .serializers import (
    AuditComplianceSettingsSerializer,
    AuditLogEntrySerializer,
    AutoEscalationRuleSerializer,
    AutoEscalationRuleWriteSerializer,
    BackupDisasterRecoverySettingsSerializer,
    BoardNotificationTriggerSerializer,
    BoardNotificationTriggerWriteSerializer,
    CommunicationBrandingSettingsSerializer,
    CompanyProfileSerializer,
    FunctionalControlSerializer,
    ProcurementPolicySettingsSerializer,
    TaxRateSerializer,
    ConfidentialityLabelSerializer,
    ConfidentialityLabelWriteSerializer,
    CostCenterSerializer,
    CostCenterWriteSerializer,
    DepartmentSerializer,
    DepartmentWriteSerializer,
    DivisionDetailSerializer,
    DivisionListSerializer,
    DivisionWriteSerializer,
    DocumentAutomationSettingsSerializer,
    EscalationMatrixSettingsSerializer,
    EscalationTierSerializer,
    EscalationTierWriteSerializer,
    FeatureFlagDefinitionSerializer,
    FeatureFlagOverrideSerializer,
    FeatureFlagOverrideWriteSerializer,
    IntegrationGovernanceSettingsSerializer,
    KpiAssignmentSerializer,
    KpiDefinitionDetailSerializer,
    KpiDefinitionListSerializer,
    KpiDefinitionWriteSerializer,
    MasterDataEntryDetailSerializer,
    MasterDataEntryListSerializer,
    MasterDataEntryWriteSerializer,
    MilestoneTemplateSerializer,
    ModuleActivationSettingsSerializer,
    MyScheduledReportResponseSerializer,
    NotificationChannelSettingsSerializer,
    NotificationTemplateDetailSerializer,
    NotificationTemplateListSerializer,
    NotificationTemplateWriteSerializer,
    NotificationWorkflowCatalogSerializer,
    PermissionMatrixUpdateSerializer,
    PhaseTemplateSerializer,
    PlatformEditionDetailSerializer,
    PlatformEditionListSerializer,
    ProfitCenterSerializer,
    ProfitCenterWriteSerializer,
    ProjectGovernanceSettingsSerializer,
    ProjectTemplateDetailSerializer,
    ProjectTemplateListSerializer,
    ProjectTemplateWriteSerializer,
    ReportingEngineSettingsSerializer,
    ReportLibraryResponseSerializer,
    ReportRunRequestSerializer,
    ReportRunSerializer,
    ReportSavedViewSerializer,
    ReportSavedViewWriteSerializer,
    ReportSubscriptionSerializer,
    ReportSubscriptionWriteSerializer,
    ReportTemplateDetailSerializer,
    ReportTemplateListSerializer,
    ReportTemplateWriteSerializer,
    RiskCategorySerializer,
    RiskCategoryWriteSerializer,
    RiskMitigationRuleSerializer,
    RiskMitigationRuleWriteSerializer,
    RiskScoreMatrixSerializer,
    RoleDetailSerializer,
    RoleListSerializer,
    RoleWriteSerializer,
    ScheduledReportDispatchSerializer,
    ScheduledReportDispatchWriteSerializer,
    SecuritySettingsSerializer,
    SlaSeverityTierSerializer,
    StageGateChecklistItemSerializer,
    StageGateRuleDetailSerializer,
    StageGateRuleListSerializer,
    StageGateRuleWriteSerializer,
    SubsidiaryDetailSerializer,
    SubsidiaryListSerializer,
    SubsidiaryWriteSerializer,
    SystemPreferencesSerializer,
    TaskTemplateSerializer,
)


def _user_org(request):
    profile = getattr(request.user, "profile", None)
    return getattr(profile, "organization", None)


def _is_superuser(request):
    return request.user.is_superuser


def _requested_org_id(request):
    raw = request.query_params.get("organization_id") or request.query_params.get("org_id")
    if raw in (None, ""):
        return None
    try:
        value = int(str(raw))
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _scope_queryset_for_request(request, queryset, *, org_field: str = "organization"):
    if _is_superuser(request):
        requested_org_id = _requested_org_id(request)
        if requested_org_id:
            org_id_field = org_field if org_field.endswith("_id") else f"{org_field}_id"
            return queryset.filter(**{org_id_field: requested_org_id})
        return queryset

    organization = _user_org(request)
    if organization is None:
        return queryset.none()
    return queryset.filter(**{org_field: organization})


def _effective_org(request):
    if _is_superuser(request):
        requested_org_id = _requested_org_id(request)
        if requested_org_id:
            from apps.accounts.models import Organization
            return Organization.objects.filter(id=requested_org_id).first()
    if _is_superuser(request) and not _user_org(request):
        from apps.accounts.models import Organization
        return Organization.objects.first()
    return _user_org(request)


ROLE_RESPONSE_CACHE_TTL_SECONDS = 120
PERMISSION_REGISTRY_CACHE_TTL_SECONDS = 900


def _sorted_query_hash(query_params) -> str:
    normalized = []
    for key in sorted(query_params.keys()):
        values = sorted(str(value) for value in query_params.getlist(key))
        normalized.extend(f"{key}={value}" for value in values)
    if not normalized:
        return "noquery"
    return hashlib.sha1("&".join(normalized).encode("utf-8")).hexdigest()[:16]


def _role_response_version_key(org_id: int) -> str:
    return f"settings:roles:{org_id}:response-version"


def _get_role_response_cache_version(org_id: int) -> int:
    version_key = _role_response_version_key(org_id)
    cached = cache.get(version_key)
    if isinstance(cached, int) and cached > 0:
        return cached
    cache.set(version_key, 1, timeout=None)
    return 1


def _bump_role_response_cache_version(org_id: int | None) -> None:
    if not org_id:
        return
    version_key = _role_response_version_key(org_id)
    if cache.add(version_key, 2, timeout=None):
        return
    try:
        cache.incr(version_key)
    except ValueError:
        cache.set(version_key, 2, timeout=None)


def _infer_module_source_from_data_sources(data_sources) -> str:
    if isinstance(data_sources, list):
        for row in data_sources:
            if isinstance(row, dict):
                module_key = str(row.get("module", "")).strip()
                if module_key:
                    return module_key.replace("_", " ").title()
    return "Unspecified"


def _category_for_template(*, template, user, department, recent_ids: list[int]) -> str:
    if template.owner_id == user.id:
        return "my_reports"
    if template.id in recent_ids:
        return "recently_viewed"
    if template.visibility == ReportTemplate.Visibility.DEPARTMENT and department and template.shared_department_id == department.id:
        return "department_reports"
    if getattr(template, "schedule_count", 0) > 0:
        return "scheduled_reports"
    return "shared_reports"


def _ordinal_day(value: int) -> str:
    if 10 <= value % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
    return f"{value}{suffix}"


def _scheduled_dispatch_text(schedule: ScheduledReportDispatch) -> str:
    time_text = schedule.dispatch_time.strftime("%H:%M")
    if schedule.frequency == ScheduledReportDispatch.Frequency.WEEKLY:
        day_name = dict(ScheduledReportDispatch.DayOfWeek.choices).get(schedule.dispatch_day_of_week, "Monday")
        return f"Every {day_name} {time_text}"
    if schedule.frequency == ScheduledReportDispatch.Frequency.MONTHLY:
        day = schedule.dispatch_day_of_month or 1
        return f"{_ordinal_day(day)} of every month"
    if schedule.frequency == ScheduledReportDispatch.Frequency.DAILY:
        return f"Every day {time_text}"
    if schedule.frequency == ScheduledReportDispatch.Frequency.QUARTERLY:
        day = schedule.dispatch_day_of_month or 1
        return f"{_ordinal_day(day)} day of every quarter"
    if schedule.frequency == ScheduledReportDispatch.Frequency.ANNUAL:
        day = schedule.dispatch_day_of_month or 1
        return f"{_ordinal_day(day)} day of every year"
    return f"{schedule.get_frequency_display()} {time_text}"


def _status_indicator_for_scheduled_run(latest_run: ReportRun | None) -> tuple[str, str]:
    if latest_run is None:
        return ("pending", "Pending")
    if latest_run.status == ReportRun.Status.SUCCEEDED:
        return ("delivered", "Delivered")
    if latest_run.status == ReportRun.Status.FAILED:
        return ("failed", "Failed")
    return ("pending", "Pending")


def _recipient_matches_user(recipients, email: str) -> bool:
    if not email or not isinstance(recipients, list):
        return False
    normalized_email = email.strip().lower()
    for recipient in recipients:
        if isinstance(recipient, str) and recipient.strip().lower() == normalized_email:
            return True
    return False


def _ensure_default_report_library_templates(org, user=None):
    """Ensure a minimal reporting library exists for first-time organizations."""
    if org is None:
        return

    owner = getattr(org, "created_by", None)
    run_user = user if getattr(user, "is_authenticated", False) else owner
    run_user_profile = getattr(run_user, "profile", None) if run_user else None
    run_user_department = getattr(run_user_profile, "department", None) if run_user_profile else None
    template_owner = run_user or owner

    default_label = (
        ConfidentialityLabel.objects.filter(
            organization=org,
            is_active=True,
            access_level=ConfidentialityLabel.AccessLevel.INTERNAL,
        )
        .order_by("sort_order", "name")
        .first()
        or ConfidentialityLabel.objects.filter(
            organization=org,
            is_active=True,
        )
        .order_by("sort_order", "name")
        .first()
    )

    template_specs = [
        {
            "code": "seed_employee_headcount_report",
            "name": "Employee Headcount Report",
            "description": "Track approved vs. filled roles by department and period.",
            "module_source": Module.HR,
            "template_type": ReportTemplate.TemplateType.OPERATIONAL,
            "data_sources": [{"module": "hr", "entity": "headcount_snapshots"}],
            "allow_simple_builder": True,
            "visibility": ReportTemplate.Visibility.DEPARTMENT,
            "schedule": {"name": "Weekly Headcount Digest", "frequency": ScheduledReportDispatch.Frequency.WEEKLY, "dispatch_day_of_week": ScheduledReportDispatch.DayOfWeek.MONDAY, "dispatch_time": "08:00"},
        },
        {
            "code": "seed_department_staffing_report",
            "name": "Department Staffing Report",
            "description": "Monitor approved headcount, filled positions, and gaps by department.",
            "module_source": Module.HR,
            "template_type": ReportTemplate.TemplateType.OPERATIONAL,
            "data_sources": [{"module": "hr", "entity": "dept-staffing-reports"}],
            "allow_simple_builder": True,
            "visibility": ReportTemplate.Visibility.DEPARTMENT,
        },
        {
            "code": "seed_workforce_cost_report",
            "name": "Workforce Cost Report",
            "description": "Track payroll burden, allowances, and cost-per-employee trends.",
            "module_source": Module.HR,
            "template_type": ReportTemplate.TemplateType.FINANCIAL,
            "data_sources": [{"module": "hr", "entity": "workforce-cost-reports"}],
            "allow_simple_builder": False,
            "schedule": {"name": "Monthly Workforce Cost Pack", "frequency": ScheduledReportDispatch.Frequency.MONTHLY, "dispatch_day_of_month": 2, "dispatch_time": "08:00"},
        },
        {
            "code": "seed_hiring_funnel_report",
            "name": "Hiring Funnel Report",
            "description": "Review candidate progression and hiring conversion performance.",
            "module_source": Module.HR,
            "template_type": ReportTemplate.TemplateType.OPERATIONAL,
            "data_sources": [{"module": "hr", "entity": "hiring-funnel-metrics"}],
            "allow_simple_builder": True,
            "visibility": ReportTemplate.Visibility.DEPARTMENT,
        },
        {
            "code": "seed_turnover_trend_report",
            "name": "Employee Turnover Trend",
            "description": "Analyze voluntary and involuntary turnover patterns over time.",
            "module_source": Module.HR,
            "template_type": ReportTemplate.TemplateType.OPERATIONAL,
            "data_sources": [{"module": "hr", "entity": "turnover-records"}],
            "allow_simple_builder": True,
        },
        {
            "code": "seed_attendance_leave_report",
            "name": "Attendance & Leave Report",
            "description": "Consolidated attendance behavior, leave usage, and absenteeism indicators.",
            "module_source": Module.HR,
            "template_type": ReportTemplate.TemplateType.OPERATIONAL,
            "data_sources": [{"module": "hr", "entity": "attendance-logs"}, {"module": "hr", "entity": "leave-requests"}],
            "allow_simple_builder": True,
        },
        {
            "code": "seed_payroll_summary_report",
            "name": "Payroll Summary Report",
            "description": "Summarize payroll runs, gross/net pay, and statutory components.",
            "module_source": Module.HR,
            "template_type": ReportTemplate.TemplateType.FINANCIAL,
            "data_sources": [{"module": "hr", "entity": "payroll-runs"}, {"module": "hr", "entity": "payslips"}],
            "allow_simple_builder": False,
        },
        {
            "code": "seed_diversity_metrics_report",
            "name": "Diversity Metrics Report",
            "description": "Measure workforce diversity distribution and demographic movement.",
            "module_source": Module.HR,
            "template_type": ReportTemplate.TemplateType.COMPLIANCE,
            "data_sources": [{"module": "hr", "entity": "diversity-metrics"}],
            "allow_simple_builder": True,
        },
        {
            "code": "seed_reporting_lines_report",
            "name": "Reporting Lines Report",
            "description": "Review team hierarchy, span of control, and manager distribution.",
            "module_source": Module.HR,
            "template_type": ReportTemplate.TemplateType.OPERATIONAL,
            "data_sources": [{"module": "hr", "entity": "reporting-lines"}],
            "allow_simple_builder": True,
            "visibility": ReportTemplate.Visibility.DEPARTMENT,
        },
        {
            "code": "seed_project_budget_variance",
            "name": "Project Budget Variance",
            "description": "Compare planned and actual project spend with variance trends.",
            "module_source": Module.FINANCE,
            "template_type": ReportTemplate.TemplateType.FINANCIAL,
            "data_sources": [{"module": "finance", "entity": "budgets"}],
            "allow_simple_builder": True,
            "schedule": {
                "name": "Weekly Budget Variance Digest",
                "frequency": ScheduledReportDispatch.Frequency.WEEKLY,
                "dispatch_day_of_week": ScheduledReportDispatch.DayOfWeek.MONDAY,
                "dispatch_time": "08:00",
            },
        },
        {
            "code": "seed_trial_balance_report",
            "name": "Trial Balance Report",
            "description": "Provide debit/credit balances by account for period validation.",
            "module_source": Module.FINANCE,
            "template_type": ReportTemplate.TemplateType.FINANCIAL,
            "data_sources": [{"module": "finance", "entity": "reports/trial-balance"}],
            "allow_simple_builder": False,
            "schedule": {"name": "Monthly Trial Balance Dispatch", "frequency": ScheduledReportDispatch.Frequency.MONTHLY, "dispatch_day_of_month": 1, "dispatch_time": "07:30"},
        },
        {
            "code": "seed_general_ledger_report",
            "name": "General Ledger Report",
            "description": "Detailed ledger movement report by account and date range.",
            "module_source": Module.FINANCE,
            "template_type": ReportTemplate.TemplateType.FINANCIAL,
            "data_sources": [{"module": "finance", "entity": "reports/general-ledger"}],
            "allow_simple_builder": False,
            "schedule": {"name": "Monthly GL Dispatch", "frequency": ScheduledReportDispatch.Frequency.MONTHLY, "dispatch_day_of_month": 2, "dispatch_time": "07:30"},
        },
        {
            "code": "seed_receivables_aging_report",
            "name": "Receivables Aging Report",
            "description": "Outstanding invoice balances segmented by aging buckets.",
            "module_source": Module.FINANCE,
            "template_type": ReportTemplate.TemplateType.FINANCIAL,
            "data_sources": [{"module": "finance", "entity": "invoices"}, {"module": "finance", "entity": "invoice-payments"}],
            "allow_simple_builder": True,
        },
        {
            "code": "seed_payables_aging_report",
            "name": "Payables Aging Report",
            "description": "Open bills and vendor obligations segmented by aging buckets.",
            "module_source": Module.FINANCE,
            "template_type": ReportTemplate.TemplateType.FINANCIAL,
            "data_sources": [{"module": "finance", "entity": "bills"}, {"module": "finance", "entity": "bill-payments"}],
            "allow_simple_builder": True,
        },
        {
            "code": "seed_cashflow_movements_report",
            "name": "Cashflow Movements Report",
            "description": "Track inflows/outflows from customer payments and supplier disbursements.",
            "module_source": Module.FINANCE,
            "template_type": ReportTemplate.TemplateType.FINANCIAL,
            "data_sources": [{"module": "finance", "entity": "invoice-payments"}, {"module": "finance", "entity": "bill-payments"}],
            "allow_simple_builder": True,
        },
        {
            "code": "seed_spv_distribution_report",
            "name": "SPV Distribution Summary",
            "description": "Distribution schedules and payout performance per SPV and investor class.",
            "module_source": Module.FINANCE,
            "template_type": ReportTemplate.TemplateType.EXECUTIVE,
            "data_sources": [{"module": "finance", "entity": "spv-entities"}, {"module": "finance", "entity": "distributions"}],
            "allow_simple_builder": False,
        },
        {
            "code": "seed_payment_plan_collection_report",
            "name": "Payment Plan Collection Report",
            "description": "Installment adherence, arrears exposure, and collection performance.",
            "module_source": Module.FINANCE,
            "template_type": ReportTemplate.TemplateType.FINANCIAL,
            "data_sources": [{"module": "finance", "entity": "payment-plans"}, {"module": "finance", "entity": "installments"}],
            "allow_simple_builder": True,
        },
        {
            "code": "seed_project_execution_status",
            "name": "Project Execution Status",
            "description": "Overall project delivery health across schedule, cost, and completion.",
            "module_source": Module.PROJECTS,
            "template_type": ReportTemplate.TemplateType.PROJECT,
            "data_sources": [{"module": "projects", "entity": "projects"}, {"module": "projects", "entity": "tasks"}],
            "allow_simple_builder": True,
            "schedule": {"name": "Weekly Project Execution Brief", "frequency": ScheduledReportDispatch.Frequency.WEEKLY, "dispatch_day_of_week": ScheduledReportDispatch.DayOfWeek.FRIDAY, "dispatch_time": "16:30"},
        },
        {
            "code": "seed_phase_milestone_progress",
            "name": "Phase & Milestone Progress",
            "description": "Track progress across phases, milestones, and dependencies.",
            "module_source": Module.PROJECTS,
            "template_type": ReportTemplate.TemplateType.PROJECT,
            "data_sources": [{"module": "projects", "entity": "phases"}, {"module": "projects", "entity": "milestones"}],
            "allow_simple_builder": True,
        },
        {
            "code": "seed_project_risk_exposure",
            "name": "Project Risk Exposure",
            "description": "Risk register trends by severity, owner, and mitigation progress.",
            "module_source": Module.PROJECTS,
            "template_type": ReportTemplate.TemplateType.COMPLIANCE,
            "data_sources": [{"module": "projects", "entity": "risk-register"}],
            "allow_simple_builder": True,
        },
        {
            "code": "seed_variation_order_impact",
            "name": "Variation Order Impact",
            "description": "Change order volume and financial/time impact analysis.",
            "module_source": Module.PROJECTS,
            "template_type": ReportTemplate.TemplateType.PROJECT,
            "data_sources": [{"module": "projects", "entity": "variations"}],
            "allow_simple_builder": True,
        },
        {
            "code": "seed_field_daily_site_report",
            "name": "Field Daily Site Report",
            "description": "Daily field operations summary from submitted site reports.",
            "module_source": Module.PROJECTS,
            "template_type": ReportTemplate.TemplateType.OPERATIONAL,
            "data_sources": [{"module": "projects", "entity": "field-operations/reports"}],
            "allow_simple_builder": True,
        },
        {
            "code": "seed_schedule_delay_report",
            "name": "Schedule Delay Log Report",
            "description": "Delay root causes, duration impact, and mitigation actions.",
            "module_source": Module.PROJECTS,
            "template_type": ReportTemplate.TemplateType.PROJECT,
            "data_sources": [{"module": "projects", "entity": "schedule-delay-logs"}],
            "allow_simple_builder": True,
        },
        {
            "code": "seed_project_workforce_productivity",
            "name": "Project Workforce Productivity",
            "description": "Workforce utilization and output trends by project and period.",
            "module_source": Module.PROJECTS,
            "template_type": ReportTemplate.TemplateType.OPERATIONAL,
            "data_sources": [{"module": "projects", "entity": "field-operations/workforce"}],
            "allow_simple_builder": True,
        },
        {
            "code": "seed_portfolio_valuation_report",
            "name": "Portfolio Valuation Report",
            "description": "Portfolio valuation snapshots and movement analysis by property.",
            "module_source": Module.PROPERTIES,
            "template_type": ReportTemplate.TemplateType.PROPERTY,
            "data_sources": [{"module": "properties", "entity": "valuations"}],
            "allow_simple_builder": True,
            "schedule": {"name": "Monthly Valuation Pack", "frequency": ScheduledReportDispatch.Frequency.MONTHLY, "dispatch_day_of_month": 5, "dispatch_time": "09:00"},
        },
        {
            "code": "seed_property_maintenance_report",
            "name": "Property Maintenance Performance",
            "description": "Maintenance workload, cycle times, and closure quality across assets.",
            "module_source": Module.PROPERTIES,
            "template_type": ReportTemplate.TemplateType.OPERATIONAL,
            "data_sources": [{"module": "properties", "entity": "work-orders"}, {"module": "properties", "entity": "preventive-schedules"}],
            "allow_simple_builder": True,
        },
        {
            "code": "seed_property_compliance_report",
            "name": "Property Compliance Report",
            "description": "Inspection outcomes, non-conformance counts, and remediation status.",
            "module_source": Module.PROPERTIES,
            "template_type": ReportTemplate.TemplateType.COMPLIANCE,
            "data_sources": [{"module": "properties", "entity": "inspections"}],
            "allow_simple_builder": True,
        },
        {
            "code": "seed_unit_inventory_status",
            "name": "Unit Inventory Status",
            "description": "Inventory of units with segmentation by type, availability, and status.",
            "module_source": Module.PROPERTIES,
            "template_type": ReportTemplate.TemplateType.PROPERTY,
            "data_sources": [{"module": "properties", "entity": "units"}],
            "allow_simple_builder": True,
        },
        {
            "code": "seed_requisition_cycle_time",
            "name": "Requisition Cycle Time Report",
            "description": "Procurement request lead times from creation through approval.",
            "module_source": Module.PROCUREMENT,
            "template_type": ReportTemplate.TemplateType.OPERATIONAL,
            "data_sources": [{"module": "procurement", "entity": "requisitions"}],
            "allow_simple_builder": True,
        },
        {
            "code": "seed_purchase_order_fulfilment",
            "name": "Purchase Order Fulfilment",
            "description": "PO fulfilment status, delivery timeliness, and exceptions.",
            "module_source": Module.PROCUREMENT,
            "template_type": ReportTemplate.TemplateType.OPERATIONAL,
            "data_sources": [{"module": "procurement", "entity": "purchase-orders"}, {"module": "procurement", "entity": "goods-receipts"}],
            "allow_simple_builder": True,
        },
        {
            "code": "seed_vendor_performance_report",
            "name": "Vendor Performance Report",
            "description": "Vendor responsiveness, quality, and compliance indicators.",
            "module_source": Module.PROCUREMENT,
            "template_type": ReportTemplate.TemplateType.COMPLIANCE,
            "data_sources": [{"module": "procurement", "entity": "vendors"}],
            "allow_simple_builder": True,
        },
        {
            "code": "seed_rfq_response_analysis",
            "name": "RFQ Response Analysis",
            "description": "Quote turnaround time and competitiveness across RFQ cycles.",
            "module_source": Module.PROCUREMENT,
            "template_type": ReportTemplate.TemplateType.OPERATIONAL,
            "data_sources": [{"module": "procurement", "entity": "rfqs"}, {"module": "procurement", "entity": "quotes"}],
            "allow_simple_builder": True,
        },
        {
            "code": "seed_lead_pipeline_conversion",
            "name": "Lead Pipeline Conversion",
            "description": "Pipeline flow, conversion rates, and stage leakage patterns.",
            "module_source": Module.CRM,
            "template_type": ReportTemplate.TemplateType.OPERATIONAL,
            "data_sources": [{"module": "crm", "entity": "leads"}, {"module": "crm", "entity": "pipeline-overview"}],
            "allow_simple_builder": True,
            "schedule": {"name": "Weekly Pipeline Conversion Brief", "frequency": ScheduledReportDispatch.Frequency.WEEKLY, "dispatch_day_of_week": ScheduledReportDispatch.DayOfWeek.MONDAY, "dispatch_time": "09:00"},
        },
        {
            "code": "seed_reservation_conversion",
            "name": "Reservation Conversion Report",
            "description": "Lead-to-reservation conversion and reservation drop-off analysis.",
            "module_source": Module.CRM,
            "template_type": ReportTemplate.TemplateType.OPERATIONAL,
            "data_sources": [{"module": "crm", "entity": "reservations"}, {"module": "crm", "entity": "reservation-overview"}],
            "allow_simple_builder": True,
        },
        {
            "code": "seed_broker_commission_performance",
            "name": "Broker Commission Performance",
            "description": "Broker productivity, commission earnings, and tier movement.",
            "module_source": Module.CRM,
            "template_type": ReportTemplate.TemplateType.FINANCIAL,
            "data_sources": [{"module": "crm", "entity": "broker-performance"}, {"module": "crm", "entity": "commission-earnings"}],
            "allow_simple_builder": True,
        },
        {
            "code": "seed_crm_communication_activity",
            "name": "CRM Communication Activity",
            "description": "Communication cadence, response rates, and engagement touchpoints.",
            "module_source": Module.CRM,
            "template_type": ReportTemplate.TemplateType.OPERATIONAL,
            "data_sources": [{"module": "crm", "entity": "communication-overview"}, {"module": "crm", "entity": "communication-logs"}],
            "allow_simple_builder": True,
        },
        {
            "code": "seed_ticket_sla_breach_report",
            "name": "Ticket SLA Breach Report",
            "description": "SLA compliance and breach trends across support queues.",
            "module_source": Module.SUPPORT_DESK,
            "template_type": ReportTemplate.TemplateType.COMPLIANCE,
            "data_sources": [{"module": "support_desk", "entity": "tickets"}, {"module": "support_desk", "entity": "sla-escalations"}],
            "allow_simple_builder": True,
            "schedule": {"name": "Daily Support SLA Digest", "frequency": ScheduledReportDispatch.Frequency.DAILY, "dispatch_time": "08:00"},
        },
        {
            "code": "seed_support_request_volume",
            "name": "Support Request Volume",
            "description": "Inbound support request volume, types, and response trends.",
            "module_source": Module.SUPPORT_DESK,
            "template_type": ReportTemplate.TemplateType.OPERATIONAL,
            "data_sources": [{"module": "support_desk", "entity": "requests"}, {"module": "support_desk", "entity": "overview"}],
            "allow_simple_builder": True,
        },
        {
            "code": "seed_support_automation_effectiveness",
            "name": "Support Automation Effectiveness",
            "description": "Automation trigger success, throughput, and failure breakdown.",
            "module_source": Module.SUPPORT_DESK,
            "template_type": ReportTemplate.TemplateType.OPERATIONAL,
            "data_sources": [{"module": "support_desk", "entity": "automation-runs"}, {"module": "support_desk", "entity": "automation-overview"}],
            "allow_simple_builder": True,
        },
        {
            "code": "seed_knowledge_base_quality",
            "name": "Knowledge Base Quality Report",
            "description": "Article coverage, freshness, and knowledge quality indicators.",
            "module_source": Module.SUPPORT_DESK,
            "template_type": ReportTemplate.TemplateType.COMPLIANCE,
            "data_sources": [{"module": "support_desk", "entity": "knowledge-base"}, {"module": "support_desk", "entity": "knowledge-overview"}],
            "allow_simple_builder": True,
        },
        {
            "code": "seed_iam_access_review_report",
            "name": "IAM Access Review Report",
            "description": "Periodic role and entitlement review outcomes across users.",
            "module_source": Module.IAM,
            "template_type": ReportTemplate.TemplateType.COMPLIANCE,
            "data_sources": [{"module": "iam", "entity": "users"}, {"module": "iam", "entity": "roles"}],
            "allow_simple_builder": False,
        },
        {
            "code": "seed_iam_failed_login_trends",
            "name": "Failed Login Trend Report",
            "description": "Failed authentication patterns, anomaly indicators, and source analysis.",
            "module_source": Module.IAM,
            "template_type": ReportTemplate.TemplateType.COMPLIANCE,
            "data_sources": [{"module": "iam", "entity": "audit/failed-logins"}],
            "allow_simple_builder": False,
        },
        {
            "code": "seed_compliance_exception_register",
            "name": "Compliance Exception Register",
            "description": "Governance exceptions and control-gap monitoring report.",
            "module_source": Module.COMPLIANCE,
            "template_type": ReportTemplate.TemplateType.COMPLIANCE,
            "data_sources": [{"module": "compliance", "entity": "controls"}, {"module": "compliance", "entity": "exceptions"}],
            "allow_simple_builder": False,
        },
        {
            "code": "seed_document_repository_audit",
            "name": "Document Repository Audit",
            "description": "Repository activity, ownership, and document policy conformance.",
            "module_source": Module.DOCUMENTS,
            "template_type": ReportTemplate.TemplateType.COMPLIANCE,
            "data_sources": [{"module": "documents", "entity": "repository"}, {"module": "documents", "entity": "audit-events"}],
            "allow_simple_builder": True,
        },
        {
            "code": "seed_board_metrics_digest",
            "name": "Board Metrics Digest",
            "description": "Executive portfolio metrics spanning project, finance, and risk signals.",
            "module_source": Module.ANALYTICS,
            "template_type": ReportTemplate.TemplateType.EXECUTIVE,
            "data_sources": [{"module": "analytics", "entity": "board-metrics"}, {"module": "analytics", "entity": "portfolio"}],
            "allow_simple_builder": False,
            "schedule": {"name": "Monthly Board Metrics Digest", "frequency": ScheduledReportDispatch.Frequency.MONTHLY, "dispatch_day_of_month": 1, "dispatch_time": "07:00"},
        },
    ]

    recipients = []
    if getattr(owner, "email", ""):
        recipients = [owner.email]
    elif getattr(run_user, "email", ""):
        recipients = [run_user.email]
    elif getattr(org, "email", ""):
        recipients = [org.email]

    for index, spec in enumerate(template_specs):
        visibility = spec.get("visibility", ReportTemplate.Visibility.SHARED)
        if visibility == ReportTemplate.Visibility.DEPARTMENT and run_user_department is None:
            visibility = ReportTemplate.Visibility.SHARED
        shared_department = run_user_department if visibility == ReportTemplate.Visibility.DEPARTMENT else None

        template, _ = ReportTemplate.objects.get_or_create(
            organization=org,
            code=spec["code"],
            defaults={
                "name": spec["name"],
                "description": spec["description"],
                "module_source": spec["module_source"],
                "owner": template_owner,
                "visibility": visibility,
                "shared_department": shared_department,
                "template_type": spec["template_type"],
                "output_format": ReportTemplate.OutputFormat.PDF,
                "data_sources": spec["data_sources"],
                "cross_module_joins": [],
                "confidentiality_label": default_label,
                "allow_simple_builder": spec["allow_simple_builder"],
                "is_active": True,
                "is_system": True,
            },
        )

        schedule = spec.get("schedule")
        if not schedule:
            schedule_frequency = None
        else:
            schedule_frequency = schedule["frequency"]
            ScheduledReportDispatch.objects.get_or_create(
                organization=org,
                report_template=template,
                name=schedule["name"],
                defaults={
                    "frequency": schedule["frequency"],
                    "dispatch_time": schedule.get("dispatch_time", "08:00"),
                    "dispatch_day_of_week": schedule.get("dispatch_day_of_week"),
                    "dispatch_day_of_month": schedule.get("dispatch_day_of_month"),
                    "output_format": ReportTemplate.OutputFormat.PDF,
                    "recipients": recipients,
                    "is_active": True,
                },
            )

        if run_user:
            ReportSavedView.objects.get_or_create(
                organization=org,
                report_template=template,
                user=run_user,
                name="Default View",
                defaults={
                    "filters": {},
                    "column_visibility": {},
                    "rows_per_page": 25,
                    "is_default": index == 0,
                    "is_active": True,
                },
            )

            frequency_map = {
                ScheduledReportDispatch.Frequency.DAILY: ReportSubscription.Frequency.DAILY,
                ScheduledReportDispatch.Frequency.WEEKLY: ReportSubscription.Frequency.WEEKLY,
                ScheduledReportDispatch.Frequency.MONTHLY: ReportSubscription.Frequency.MONTHLY,
                ScheduledReportDispatch.Frequency.QUARTERLY: ReportSubscription.Frequency.QUARTERLY,
            }
            subscription_frequency = frequency_map.get(schedule_frequency)
            if subscription_frequency:
                ReportSubscription.objects.get_or_create(
                    organization=org,
                    report_template=template,
                    user=run_user,
                    frequency=subscription_frequency,
                    defaults={
                        "output_format": ReportTemplate.OutputFormat.PDF,
                        "recipients": recipients,
                        "delivery_channels": [ReportSubscription.DeliveryChannel.EMAIL],
                        "is_active": True,
                    },
                )

        if run_user and not ReportRun.objects.filter(
            organization=org,
            report_template=template,
            requested_by=run_user,
        ).exists():
            days_ago = int(spec.get("seed_run_days_ago", index % 5) or 0)
            run_at = timezone.now() - timedelta(days=days_ago)
            run = ReportRun.objects.create(
                organization=org,
                report_template=template,
                requested_by=run_user,
                trigger=ReportRun.Trigger.MANUAL,
                status=ReportRun.Status.SUCCEEDED,
                output_format=ReportTemplate.OutputFormat.PDF,
                filters={},
                result_summary={
                    "message": "Seeded starter report run for the reporting workspace.",
                    "seeded": True,
                },
                row_count=0,
                started_at=run_at,
                completed_at=run_at,
            )
            if days_ago > 0:
                ReportRun.objects.filter(pk=run.pk).update(created_at=run_at)


# ---------------------------------------------------------------------------
# Company Profile
# ---------------------------------------------------------------------------

class CompanyProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = CompanyProfileSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.company_profile"
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        self.rbac_action = "edit" if self.request.method in ("PUT", "PATCH") else "view"
        return super().get_permissions()

    def get_object(self):
        if _is_superuser(self.request) and not _user_org(self.request):
            from apps.accounts.models import Organization
            return Organization.objects.first()
        return _user_org(self.request)


# ---------------------------------------------------------------------------
# Subsidiaries
# ---------------------------------------------------------------------------

class SubsidiaryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.subsidiaries"
    search_fields = ["name", "legal_name", "city", "country"]
    filterset_fields = ["relationship_type", "status"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def get_queryset(self):
        return _scope_queryset_for_request(self.request, Subsidiary.objects.all())
    def get_serializer_class(self):
        if self.action == "list":
            return SubsidiaryListSerializer
        if self.action in ("create", "update", "partial_update"):
            return SubsidiaryWriteSerializer
        return SubsidiaryDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


# ---------------------------------------------------------------------------
# Divisions
# ---------------------------------------------------------------------------

class DivisionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.hierarchy"
    search_fields = ["name", "code"]
    filterset_fields = ["is_active"]
    ordering_fields = ["sort_order", "name", "created_at"]
    ordering = ["sort_order", "name"]

    def get_queryset(self):
        qs = _scope_queryset_for_request(self.request, Division.objects.all())
        qs = qs.annotate(department_count=Count("departments")).select_related("head")
        if self.request.query_params.get("include_departments") == "true":
            qs = qs.prefetch_related(
                Prefetch(
                    "departments",
                    queryset=Department.objects.select_related("head", "division").prefetch_related("cost_centers"),
                )
            )
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            if self.request.query_params.get("include_departments") == "true":
                return DivisionDetailSerializer
            return DivisionListSerializer
        if self.action in ("create", "update", "partial_update"):
            return DivisionWriteSerializer
        return DivisionDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


# ---------------------------------------------------------------------------
# Departments – flat read-only list (for dropdowns in Teams, Positions, etc.)
# ---------------------------------------------------------------------------

class DepartmentListView(generics.ListAPIView):
    """Return all departments across all divisions for the user's org."""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.hierarchy"
    rbac_action = "view"
    serializer_class = DepartmentSerializer
    search_fields = ["name", "code"]
    filterset_fields = ["is_active"]
    ordering = ["sort_order", "name"]

    def get_queryset(self):
        if _is_superuser(self.request):
            return Department.objects.all().select_related("head", "division").prefetch_related("cost_centers")
        return Department.objects.filter(
            division__organization=_user_org(self.request)
        ).select_related("head", "division").prefetch_related("cost_centers")


# ---------------------------------------------------------------------------
# Departments (nested under Division)
# ---------------------------------------------------------------------------

class DepartmentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.hierarchy"
    search_fields = ["name", "code"]
    filterset_fields = ["is_active"]
    ordering = ["sort_order", "name"]

    def get_queryset(self):
        filters = {"division_id": self.kwargs["division_pk"]}
        if not _is_superuser(self.request):
            filters["division__organization"] = _user_org(self.request)
        return Department.objects.filter(**filters).select_related("head", "division").prefetch_related("cost_centers")

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return DepartmentWriteSerializer
        return DepartmentSerializer

    def perform_create(self, serializer):
        serializer.save(division_id=self.kwargs["division_pk"])


# ---------------------------------------------------------------------------
# Cost Centers
# ---------------------------------------------------------------------------

class CostCenterViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.hierarchy"
    search_fields = ["code", "name"]
    filterset_fields = ["is_active", "department"]
    ordering = ["code"]

    def get_queryset(self):
        qs = _scope_queryset_for_request(self.request, CostCenter.objects.all())
        return qs.select_related("department")

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return CostCenterWriteSerializer
        return CostCenterSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


# ---------------------------------------------------------------------------
# Profit Centers
# ---------------------------------------------------------------------------

class ProfitCenterViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.hierarchy"
    search_fields = ["code", "name"]
    filterset_fields = ["is_active", "department"]
    ordering = ["code"]

    def get_queryset(self):
        qs = _scope_queryset_for_request(self.request, ProfitCenter.objects.all())
        return qs.select_related("department")

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return ProfitCenterWriteSerializer
        return ProfitCenterSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------

class RoleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.roles"
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "create",
        "update": "edit",
        "partial_update": "edit",
        "destroy": "delete",
        "update_permissions": "configure",
    }
    search_fields = ["name"]
    filterset_fields = ["is_system"]
    ordering_fields = ["name", "created_at", "user_count"]
    ordering = ["name"]

    def get_queryset(self):
        qs = _scope_queryset_for_request(self.request, Role.objects.all())
        return qs.annotate(user_count=Count("assigned_users"))

    def _cache_enabled_for_request(self) -> bool:
        org = _effective_org(self.request)
        return bool(getattr(org, "id", None))

    def _cache_org_id(self) -> int | None:
        org = _effective_org(self.request)
        return getattr(org, "id", None)

    def _list_cache_key(self) -> str | None:
        org_id = self._cache_org_id()
        if not org_id:
            return None
        version = _get_role_response_cache_version(org_id)
        query_hash = _sorted_query_hash(self.request.query_params)
        return f"settings:roles:list:{org_id}:{version}:{query_hash}"

    def _detail_cache_key(self, pk: str) -> str | None:
        org_id = self._cache_org_id()
        if not org_id:
            return None
        version = _get_role_response_cache_version(org_id)
        return f"settings:roles:detail:{org_id}:{version}:{pk}"

    def _invalidate_role_caches(self, role: Role) -> None:
        _bump_role_response_cache_version(role.organization_id)
        bump_role_permission_cache_version(role.id)

    def get_serializer_class(self):
        if self.action == "list":
            return RoleListSerializer
        if self.action in ("create", "update", "partial_update"):
            return RoleWriteSerializer
        return RoleDetailSerializer

    def perform_create(self, serializer):
        role = serializer.save(organization=_user_org(self.request))
        self._invalidate_role_caches(role)

    def perform_update(self, serializer):
        role = serializer.save()
        self._invalidate_role_caches(role)

    def perform_destroy(self, instance):
        if instance.is_system:
            from rest_framework.exceptions import ValidationError

            raise ValidationError("System roles cannot be deleted.")
        self._invalidate_role_caches(instance)
        instance.delete()

    def list(self, request, *args, **kwargs):
        cache_key = self._list_cache_key() if self._cache_enabled_for_request() else None
        if cache_key:
            cached = cache.get(cache_key)
            if cached is not None:
                return Response(cached)

        response = super().list(request, *args, **kwargs)
        if cache_key and response.status_code == 200:
            cache.set(
                cache_key,
                response.data,
                timeout=ROLE_RESPONSE_CACHE_TTL_SECONDS,
            )
        return response

    def retrieve(self, request, *args, **kwargs):
        cache_key = self._detail_cache_key(kwargs.get("pk", "")) if self._cache_enabled_for_request() else None
        if cache_key:
            cached = cache.get(cache_key)
            if cached is not None:
                return Response(cached)

        response = super().retrieve(request, *args, **kwargs)
        if cache_key and response.status_code == 200:
            cache.set(
                cache_key,
                response.data,
                timeout=ROLE_RESPONSE_CACHE_TTL_SECONDS,
            )
        return response

    @action(detail=True, methods=["put"], url_path="permissions")
    def update_permissions(self, request, pk=None):
        """Bulk-sync the permission matrix for this role."""
        from apps.accounts.audit import audit_emit
        from apps.accounts.models import UserSecurityEvent

        role = self.get_object()
        serializer = PermissionMatrixUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        prior_count = RolePermission.objects.filter(role=role).count()

        RolePermission.objects.filter(role=role).delete()
        to_create = []
        for perm in serializer.validated_data["permissions"]:
            if perm["granted"]:
                module = perm["sub_module"].split(".")[0]
                permission_obj, _ = Permission.objects.get_or_create(
                    sub_module=perm["sub_module"],
                    action=perm["action"],
                    defaults={
                        "module": module,
                        "key": f"{perm['sub_module']}.{perm['action']}",
                    },
                )
                to_create.append(
                    RolePermission(
                        role=role,
                        permission=permission_obj,
                        module=permission_obj.module,
                        sub_module=permission_obj.sub_module,
                        action=permission_obj.action,
                    )
                )
        RolePermission.objects.bulk_create(to_create)
        new_count = len(to_create)
        self._invalidate_role_caches(role)

        delta = new_count - prior_count
        audit_emit(
            event_type=UserSecurityEvent.EventType.ROLE_PERMISSIONS_CHANGED,
            request=request,
            status=UserSecurityEvent.Status.INFO,
            severity=UserSecurityEvent.Severity.MEDIUM,
            target_type="role",
            target_id=str(role.id),
            detail=(
                f"Permission matrix for '{role.name}' set to {new_count} permission"
                f"{'s' if new_count != 1 else ''} (delta {delta:+d})."
            ),
            metadata={
                "role_id": role.id,
                "prior_count": prior_count,
                "new_count": new_count,
                "delta": delta,
            },
        )
        return Response({"detail": "Permissions updated."})


# ---------------------------------------------------------------------------
# Permission Registry (read-only config)
# ---------------------------------------------------------------------------

class SecuritySettingsView(generics.RetrieveUpdateAPIView):
    serializer_class = SecuritySettingsSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.security"

    def get_permissions(self):
        self.rbac_action = "edit" if self.request.method in ("PUT", "PATCH") else "view"
        return super().get_permissions()

    def get_object(self):
        if _is_superuser(self.request) and not _user_org(self.request):
            from apps.accounts.models import Organization
            org = Organization.objects.first()
        else:
            org = _user_org(self.request)
        obj, _ = SecuritySettings.objects.get_or_create(organization=org)
        return obj


class SystemPreferencesView(generics.RetrieveUpdateAPIView):
    serializer_class = SystemPreferencesSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.system_preferences"

    def get_permissions(self):
        self.rbac_action = "edit" if self.request.method in ("PUT", "PATCH") else "view"
        return super().get_permissions()

    def get_object(self):
        if _is_superuser(self.request) and not _user_org(self.request):
            from apps.accounts.models import Organization
            org = Organization.objects.first()
        else:
            org = _user_org(self.request)
        obj, _ = SystemPreferences.objects.get_or_create(organization=org)
        return obj


class NotificationChannelSettingsView(generics.RetrieveUpdateAPIView):
    serializer_class = NotificationChannelSettingsSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.system_preferences"

    def get_permissions(self):
        self.rbac_action = "edit" if self.request.method in ("PUT", "PATCH") else "view"
        return super().get_permissions()

    def get_object(self):
        org = _effective_org(self.request)
        ensure_default_notification_settings(org)
        obj, _ = NotificationChannelSettings.objects.get_or_create(organization=org)
        return obj


class SlaSeverityTierViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.system_preferences"
    filterset_fields = ["level", "is_active"]
    ordering_fields = ["sort_order", "level", "response_time_hours", "updated_at"]
    ordering = ["sort_order", "level"]

    def get_queryset(self):
        org = _effective_org(self.request)
        ensure_default_notification_settings(org)
        return SlaSeverityTier.objects.filter(organization=org)

    def get_serializer_class(self):
        return SlaSeverityTierSerializer

    def perform_create(self, serializer):
        from rest_framework.exceptions import ValidationError
        raise ValidationError("SLA severity tiers are fixed. Update existing tiers instead.")

    def perform_destroy(self, instance):
        from rest_framework.exceptions import ValidationError
        raise ValidationError("SLA severity tiers cannot be deleted.")


class NotificationTemplateViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.system_preferences"
    search_fields = ["code", "name", "event_key", "subject", "description"]
    filterset_fields = ["channel", "severity_tier", "is_active"]
    ordering_fields = ["name", "channel", "updated_at", "created_at"]
    ordering = ["channel", "name"]

    def get_queryset(self):
        org = _effective_org(self.request)
        ensure_default_notification_settings(org)
        return NotificationTemplate.objects.filter(organization=org)

    def get_serializer_class(self):
        if self.action == "list":
            return NotificationTemplateListSerializer
        if self.action in ("create", "update", "partial_update"):
            return NotificationTemplateWriteSerializer
        return NotificationTemplateDetailSerializer

    def perform_create(self, serializer):
        from rest_framework.exceptions import ValidationError

        org = _effective_org(self.request)
        if org is None:
            raise ValidationError("No organization context found for this user.")
        serializer.save(organization=org)

    def perform_destroy(self, instance):
        if instance.is_system:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("System templates cannot be deleted.")
        instance.delete()


class NotificationWorkflowCatalogView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.system_preferences"
    rbac_action = "view"

    def get(self, request):
        org = _effective_org(request)
        ensure_default_notification_settings(org)

        events = get_workflow_notification_catalog()
        if org is None:
            serializer = NotificationWorkflowCatalogSerializer({"events": events})
            return Response(serializer.data)

        channel_order = ["email", "in_app", "sms", "push"]
        order_index = {channel: idx for idx, channel in enumerate(channel_order)}

        coverage: dict[str, dict[str, int | set[str]]] = {}
        template_rows = NotificationTemplate.objects.filter(organization=org).values(
            "event_key",
            "channel",
            "is_active",
        )
        for row in template_rows:
            event_key = row["event_key"]
            channel = row["channel"]
            is_active = row["is_active"]

            bucket = coverage.setdefault(
                event_key,
                {
                    "template_count": 0,
                    "active_template_count": 0,
                    "configured_channels": set(),
                    "active_channels": set(),
                },
            )
            bucket["template_count"] += 1
            if channel:
                bucket["configured_channels"].add(channel)
            if is_active:
                bucket["active_template_count"] += 1
                if channel:
                    bucket["active_channels"].add(channel)

        payload: list[dict[str, object]] = []
        known_event_keys = {item["key"] for item in events}

        for item in events:
            bucket = coverage.get(item["key"]) or {}
            configured_channels = sorted(
                list(bucket.get("configured_channels", set())),
                key=lambda channel: order_index.get(channel, 999),
            )
            active_channels = sorted(
                list(bucket.get("active_channels", set())),
                key=lambda channel: order_index.get(channel, 999),
            )
            payload.append(
                {
                    **item,
                    "template_count": bucket.get("template_count", 0),
                    "active_template_count": bucket.get("active_template_count", 0),
                    "configured_channels": configured_channels,
                    "active_channels": active_channels,
                }
            )

        uncatalogued_rows = sorted(
            (event_key for event_key in coverage if event_key not in known_event_keys),
            key=lambda event_key: event_key.lower(),
        )
        for event_key in uncatalogued_rows:
            bucket = coverage[event_key]
            configured_channels = sorted(
                list(bucket.get("configured_channels", set())),
                key=lambda channel: order_index.get(channel, 999),
            )
            active_channels = sorted(
                list(bucket.get("active_channels", set())),
                key=lambda channel: order_index.get(channel, 999),
            )
            payload.append(
                {
                    "key": event_key,
                    "label": event_key.replace("_", " ").title(),
                    "module": "custom",
                    "description": "Custom event key configured by administrators.",
                    "default_channels": [],
                    "variables": [],
                    "default_severity_tier": "review",
                    "template_count": bucket.get("template_count", 0),
                    "active_template_count": bucket.get("active_template_count", 0),
                    "configured_channels": configured_channels,
                    "active_channels": active_channels,
                }
            )

        serializer = NotificationWorkflowCatalogSerializer({"events": payload})
        return Response(serializer.data)


class DocumentAutomationSettingsView(generics.RetrieveUpdateAPIView):
    serializer_class = DocumentAutomationSettingsSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.system_preferences"

    def get_permissions(self):
        self.rbac_action = "edit" if self.request.method in ("PUT", "PATCH") else "view"
        return super().get_permissions()

    def get_object(self):
        org = _effective_org(self.request)
        ensure_default_document_automation_settings(org)
        obj, _ = DocumentAutomationSettings.objects.get_or_create(organization=org)
        return obj


class AuditComplianceSettingsView(generics.RetrieveUpdateAPIView):
    serializer_class = AuditComplianceSettingsSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.audit_compliance"

    def get_permissions(self):
        self.rbac_action = "edit" if self.request.method in ("PUT", "PATCH") else "view"
        return super().get_permissions()

    def get_object(self):
        if _is_superuser(self.request) and not _user_org(self.request):
            from apps.accounts.models import Organization
            org = Organization.objects.first()
        else:
            org = _user_org(self.request)
        obj, _ = AuditComplianceSettings.objects.get_or_create(organization=org)
        return obj


class AuditLogListView(generics.ListAPIView):
    serializer_class = AuditLogEntrySerializer
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.audit_compliance"
    rbac_action = "view"

    def get_queryset(self):
        from auditlog.models import LogEntry
        from django.contrib.contenttypes.models import ContentType
        from django.db.models import Q

        from apps.accounts.models import Invitation, Organization
        from apps.compliance.models import ComplianceAudit, ComplianceRequirement
        from apps.crm.models import Broker, Lead, UnitReservation
        from apps.documents.access_control import scoped_document_queryset_for_user
        from apps.documents.models import Document, DocumentApproval
        from apps.finance.models import Account, Bill, Budget, Invoice, JournalEntry, PaymentPlan
        from apps.hr.models import EmployeeRecord, PayrollRun
        from apps.procurement.models import PurchaseOrder, PurchaseRequisition, RequestForQuotation, Vendor
        from apps.projects.models import Project
        from apps.properties.models import Property
        from apps.workflows.models import ApprovalPolicy, WorkflowInstance
        from apps.workspace.models import Team as WorkspaceTeam, TeamMembership as WorkspaceTeamMembership
        from apps.calendar.models import (
            CalendarEvent,
            CalendarEventAttendee,
            CalendarEventOccurrence,
        )
        from apps.internal_tasks.models import Task as InternalTask, TaskComment as InternalTaskComment

        qs = LogEntry.objects.select_related("actor", "content_type").order_by("-timestamp")
        if not self.request.user.is_superuser:
            org = _user_org(self.request)
            if not org:
                return qs.none()

            filters = Q(actor__profile__organization=org)

            def _org_ids(model, org_field="organization"):
                """Return object PKs for a model scoped to org, as strings."""
                ids = list(
                    model.objects.filter(**{org_field: org}).values_list("id", flat=True)
                )
                if not ids:
                    return None
                ct = ContentType.objects.get_for_model(model)
                return Q(content_type=ct, object_pk__in=[str(pk) for pk in ids])

            scoped_doc_ids = list(
                scoped_document_queryset_for_user(self.request.user).values_list("id", flat=True)
            )
            scoped_approval_ids = list(
                DocumentApproval.objects
                .filter(document_version__document_id__in=scoped_doc_ids)
                .values_list("id", flat=True)
            )

            ct_doc = ContentType.objects.get_for_model(Document)
            ct_approval = ContentType.objects.get_for_model(DocumentApproval)
            ct_org = ContentType.objects.get_for_model(Organization)

            scopes = [
                # Accounts & access
                Q(content_type=ct_org, object_pk=str(org.id)),
                _org_ids(Invitation),
                # Properties & projects
                _org_ids(Property),
                _org_ids(Project),
                # Finance
                _org_ids(Bill),
                _org_ids(Invoice),
                _org_ids(Budget),
                _org_ids(Account),
                _org_ids(JournalEntry),
                _org_ids(PaymentPlan),
                # Procurement
                _org_ids(PurchaseOrder),
                _org_ids(PurchaseRequisition),
                _org_ids(Vendor),
                _org_ids(RequestForQuotation),
                # Documents
                Q(content_type=ct_doc, object_pk__in=[str(pk) for pk in scoped_doc_ids]) if scoped_doc_ids else None,
                Q(content_type=ct_approval, object_pk__in=[str(pk) for pk in scoped_approval_ids]) if scoped_approval_ids else None,
                # HR
                _org_ids(EmployeeRecord),
                _org_ids(PayrollRun),
                # Compliance
                _org_ids(ComplianceRequirement),
                _org_ids(ComplianceAudit),
                # Workflows
                _org_ids(WorkflowInstance),
                _org_ids(ApprovalPolicy),
                # CRM
                _org_ids(Lead),
                _org_ids(Broker),
                _org_ids(UnitReservation),
                # Settings (RBAC)
                _org_ids(Role),
                _org_ids(RolePermission, org_field="role__organization"),
                _org_ids(SecuritySettings),
                # Workspace teams (membership scoped via team__organization)
                _org_ids(WorkspaceTeam),
                _org_ids(WorkspaceTeamMembership, org_field="team__organization"),
                # Calendar (attendees + occurrences scoped via event__organization)
                _org_ids(CalendarEvent),
                _org_ids(CalendarEventAttendee, org_field="event__organization"),
                _org_ids(CalendarEventOccurrence, org_field="event__organization"),
                # Internal Tasks (comments scoped via task__organization)
                _org_ids(InternalTask),
                _org_ids(InternalTaskComment, org_field="task__organization"),
            ]
            for scope in scopes:
                if scope is not None:
                    filters |= scope

            qs = qs.filter(filters).distinct()

        action = self.request.query_params.get("action")
        if action is not None:
            qs = qs.filter(action=int(action))

        content_type = self.request.query_params.get("content_type")
        if content_type:
            qs = qs.filter(content_type__model=content_type)

        return qs


class PermissionRegistryView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.roles"
    rbac_action = "view"

    def get(self, request):
        cache_key = "settings:permission-registry:v1"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        from .rbac_defaults import PERMISSION_REGISTRY

        cache.set(
            cache_key,
            PERMISSION_REGISTRY,
            timeout=PERMISSION_REGISTRY_CACHE_TTL_SECONDS,
        )
        return Response(PERMISSION_REGISTRY)


# ---------------------------------------------------------------------------
# Project Governance Settings
# ---------------------------------------------------------------------------


class ProjectGovernanceSettingsView(generics.RetrieveUpdateAPIView):
    serializer_class = ProjectGovernanceSettingsSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.system_preferences"

    def get_permissions(self):
        self.rbac_action = "edit" if self.request.method in ("PUT", "PATCH") else "view"
        return super().get_permissions()

    def get_object(self):
        if _is_superuser(self.request) and not _user_org(self.request):
            from apps.accounts.models import Organization
            org = Organization.objects.first()
        else:
            org = _user_org(self.request)
        obj, _ = ProjectGovernanceSettings.objects.get_or_create(organization=org)
        return obj


class ProjectTemplateViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.workflow_templates"
    search_fields = ["name", "description"]
    filterset_fields = ["template_type", "is_active", "is_system"]
    ordering_fields = ["name", "created_at", "template_type"]
    ordering = ["template_type", "name"]

    def get_queryset(self):
        if _is_superuser(self.request):
            qs = ProjectTemplate.objects.all()
        else:
            org = _user_org(self.request)
            qs = ProjectTemplate.objects.filter(
                Q(organization__isnull=True) | Q(organization=org)
            )
        if self.action == "list":
            qs = qs.annotate(phase_count=Count("phases"))
        elif self.action == "retrieve":
            qs = qs.prefetch_related(
                "phases__milestones",
                "phases__required_documents",
                "phases__compliance_checkpoints",
                "phases__activities__task_templates",
            )
        return qs.select_related("organization")

    def get_serializer_class(self):
        if self.action == "list":
            return ProjectTemplateListSerializer
        if self.action in ("create", "update", "partial_update"):
            return ProjectTemplateWriteSerializer
        return ProjectTemplateDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))

    def perform_destroy(self, instance):
        if instance.is_system:
            from rest_framework.exceptions import ValidationError

            raise ValidationError("System templates cannot be deleted.")
        instance.delete()


class TemplatePlanScenarioViewSet(viewsets.ModelViewSet):
    """CRUD for plan scenarios (what-if analysis) per template."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.workflow_templates"

    def get_queryset(self):
        from .models import TemplatePlanScenario

        return TemplatePlanScenario.objects.filter(
            template_id=self.kwargs.get("template_pk"),
        ).order_by("-is_baseline", "-created_at")

    def get_serializer_class(self):
        from .serializers import TemplatePlanScenarioSerializer

        return TemplatePlanScenarioSerializer

    def perform_create(self, serializer):
        serializer.save(
            template_id=self.kwargs["template_pk"],
            created_by=self.request.user if self.request.user.is_authenticated else None,
        )

    @action(detail=True, methods=["post"], url_path="commit-baseline")
    def commit_baseline(self, request, template_pk=None, pk=None):
        from .models import TemplatePlanScenario

        scenario = self.get_object()
        # Clear other baselines
        TemplatePlanScenario.objects.filter(
            template_id=template_pk, is_baseline=True,
        ).exclude(pk=scenario.pk).update(is_baseline=False)
        scenario.is_baseline = True
        scenario.save(update_fields=["is_baseline", "updated_at"])
        return Response({"detail": f"'{scenario.name}' is now the official baseline."})


class TemplateScheduleSettingsView(generics.RetrieveUpdateAPIView):
    """Get or update schedule settings for a project template."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.workflow_templates"

    def get_serializer_class(self):
        from .serializers import TemplateScheduleSettingsSerializer
        return TemplateScheduleSettingsSerializer

    def get_object(self):
        from .models import TemplateScheduleSettings
        obj, _ = TemplateScheduleSettings.objects.get_or_create(
            template_id=self.kwargs["template_pk"],
        )
        return obj


class TemplateDependencyViewSet(viewsets.ModelViewSet):
    """CRUD for dependency relationships in the Dependency Graph Engine."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.workflow_templates"

    def get_queryset(self):
        from .models import TemplateDependency

        return (
            TemplateDependency.objects.filter(template_id=self.kwargs.get("template_pk"))
            .select_related("from_activity", "from_task", "to_activity", "to_task")
            .order_by("created_at")
        )

    def get_serializer_class(self):
        from .serializers import TemplateDependencySerializer

        return TemplateDependencySerializer

    def perform_create(self, serializer):
        serializer.save(template_id=self.kwargs["template_pk"])


class TemplateActivityViewSet(viewsets.ModelViewSet):
    """CRUD for WBS activities within a template phase."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.workflow_templates"

    def get_queryset(self):
        from .models import TemplateActivity

        return TemplateActivity.objects.filter(
            phase_id=self.kwargs.get("phase_pk"),
        ).prefetch_related("task_templates").order_by("sort_order")

    def get_serializer_class(self):
        from .serializers import TemplateActivitySerializer, TemplateActivityWriteSerializer

        if self.action in ("create", "update", "partial_update"):
            return TemplateActivityWriteSerializer
        return TemplateActivitySerializer

    def perform_create(self, serializer):
        serializer.save(phase_id=self.kwargs["phase_pk"])


class TemplatePhaseListViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only list of TemplatePhase records (phases within project templates).
    Used by the BOQ category mapping form to populate the phase dropdown."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.workflow_templates"
    rbac_action = "view"

    class _Serializer(serializers.ModelSerializer):
        class Meta:
            model = TemplatePhase
            fields = ("id", "name", "template")

    serializer_class = _Serializer

    def get_queryset(self):
        org = _user_org(self.request)
        return (
            TemplatePhase.objects
            .filter(Q(template__organization__isnull=True) | Q(template__organization=org))
            .select_related("template")
            .order_by("template__name", "sort_order")
        )


class PhaseTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only list of standalone phase templates for the Add Phase picker."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.workflow_templates"
    rbac_action = "view"
    queryset = PhaseTemplate.objects.all()
    serializer_class = PhaseTemplateSerializer
    pagination_class = None


class MilestoneTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only list of standalone milestone templates for the Add Milestone picker."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.workflow_templates"
    rbac_action = "view"
    queryset = MilestoneTemplate.objects.all()
    serializer_class = MilestoneTemplateSerializer
    pagination_class = None


class TaskTemplateViewSet(viewsets.ModelViewSet):
    """Full CRUD for task templates used in the Project Planner."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.workflow_templates"
    queryset = TaskTemplate.objects.all()
    serializer_class = TaskTemplateSerializer


class StageGateRuleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.workflow_templates"
    search_fields = ["name", "description"]
    filterset_fields = ["stage", "is_active", "template"]
    ordering_fields = ["name", "stage", "created_at"]
    ordering = ["stage", "name"]

    def get_queryset(self):
        qs = _scope_queryset_for_request(self.request, StageGateRule.objects.all())
        if self.action == "list":
            qs = qs.annotate(checklist_count=Count("checklist_items"))
        return qs.select_related("organization", "template")

    def get_serializer_class(self):
        if self.action == "list":
            return StageGateRuleListSerializer
        if self.action in ("create", "update", "partial_update"):
            return StageGateRuleWriteSerializer
        return StageGateRuleDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


class StageGateChecklistItemViewSet(viewsets.ModelViewSet):
    serializer_class = StageGateChecklistItemSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.workflow_templates"
    ordering = ["sort_order", "id"]

    def get_queryset(self):
        return StageGateChecklistItem.objects.filter(
            rule_id=self.kwargs["rule_pk"],
        )

    def perform_create(self, serializer):
        serializer.save(rule_id=self.kwargs["rule_pk"])


class RiskCategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.system_preferences"
    search_fields = ["name", "description"]
    filterset_fields = ["category_type", "is_active"]
    ordering_fields = ["name", "category_type", "created_at"]
    ordering = ["category_type", "name"]

    def get_queryset(self):
        return _scope_queryset_for_request(self.request, RiskCategory.objects.all())
    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return RiskCategoryWriteSerializer
        return RiskCategorySerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


class RiskScoreMatrixView(generics.RetrieveUpdateAPIView):
    serializer_class = RiskScoreMatrixSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.system_preferences"

    def get_permissions(self):
        self.rbac_action = "edit" if self.request.method in ("PUT", "PATCH") else "view"
        return super().get_permissions()

    def get_object(self):
        if _is_superuser(self.request) and not _user_org(self.request):
            from apps.accounts.models import Organization
            org = Organization.objects.first()
        else:
            org = _user_org(self.request)
        obj, _ = RiskScoreMatrix.objects.get_or_create(
            organization=org,
            defaults={
                "matrix_config": {
                    "likelihood": {
                        "very_low": 1,
                        "low": 2,
                        "medium": 3,
                        "high": 4,
                        "very_high": 5,
                    },
                    "impact": {
                        "very_low": 1,
                        "low": 2,
                        "medium": 3,
                        "high": 4,
                        "very_high": 5,
                    },
                    "thresholds": {"low": 5, "medium": 10, "high": 15, "critical": 20},
                }
            },
        )
        return obj


class RiskMitigationRuleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.system_preferences"
    search_fields = ["risk_category__name"]
    filterset_fields = ["severity", "escalation_required", "is_active", "risk_category"]
    ordering_fields = ["severity", "created_at"]
    ordering = ["severity", "risk_category__name"]

    def get_queryset(self):
        return (
            RiskMitigationRule.objects.all()
            if _is_superuser(self.request)
            else _scope_queryset_for_request(self.request, RiskMitigationRule.objects.all())
        ).select_related("organization", "risk_category", "assign_to_role")

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return RiskMitigationRuleWriteSerializer
        return RiskMitigationRuleSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


# ---------------------------------------------------------------------------
# Master Data Management
# ---------------------------------------------------------------------------


class MasterDataEntryFilter(filters.FilterSet):
    class Meta:
        model = MasterDataEntry
        fields = ["category", "is_active"]


class MasterDataEntryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.system_preferences"
    filterset_class = MasterDataEntryFilter
    search_fields = ["code", "label", "description"]
    ordering_fields = ["sort_order", "label", "created_at"]
    ordering = ["sort_order", "label"]

    def get_queryset(self):
        return MasterDataEntry.objects.all()

    def get_serializer_class(self):
        if self.action == "list":
            return MasterDataEntryListSerializer
        if self.action in ("create", "update", "partial_update"):
            return MasterDataEntryWriteSerializer
        return MasterDataEntryDetailSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_system:
            return Response(
                {"detail": "System entries cannot be deleted."},
                status=403,
            )
        return super().destroy(request, *args, **kwargs)


class StatusBadgeRegistryView(generics.ListAPIView):
    """Unpaginated read-only list of all active status_badge MDM entries."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.system_preferences"
    rbac_action = "view"
    serializer_class = MasterDataEntryListSerializer
    pagination_class = None

    def get_queryset(self):
        return MasterDataEntry.objects.filter(
            category=MasterDataEntry.Category.STATUS_BADGE,
            is_active=True,
        ).order_by("code")


# ---------------------------------------------------------------------------
# Module Activation & Feature Flags
# ---------------------------------------------------------------------------


class ModuleActivationSettingsView(generics.RetrieveUpdateAPIView):
    """Singleton: GET returns current module activation, PATCH updates it."""

    serializer_class = ModuleActivationSettingsSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.system_preferences"

    def get_permissions(self):
        self.rbac_action = "edit" if self.request.method in ("PUT", "PATCH") else "view"
        return super().get_permissions()

    def get_object(self):
        org = _effective_org(self.request)
        obj, _ = ModuleActivationSettings.objects.get_or_create(
            organization=org,
            defaults={
                "enabled_modules": list(
                    TIER_MODULE_MAP.get(org.subscription_tier, set())
                ),
            },
        )
        return obj


class FeatureFlagDashboardView(APIView):
    """
    GET: Composite read — tier, module activation, all flag definitions,
    org overrides, and resolved flag state in a single payload.
    """

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.system_preferences"
    rbac_action = "view"

    def get(self, request):
        from .feature_flags import get_org_flags

        org = _effective_org(request)

        activation, _ = ModuleActivationSettings.objects.get_or_create(
            organization=org,
            defaults={
                "enabled_modules": list(
                    TIER_MODULE_MAP.get(org.subscription_tier, set())
                ),
            },
        )

        flag_defs = FeatureFlagDefinition.objects.filter(is_active=True)
        overrides = FeatureFlagOverride.objects.filter(
            organization=org, flag__is_active=True
        ).select_related("flag")

        available = activation.get_available_modules()

        return Response(
            {
                "tier": org.subscription_tier,
                "tier_display": org.get_subscription_tier_display(),
                "enabled_modules": sorted(activation.get_enabled_modules()),
                "available_modules": [
                    {
                        "key": m.value,
                        "label": m.label,
                        "available": m.value in available,
                    }
                    for m in Module
                    if m.value != "settings"
                ],
                "flags": get_org_flags(org),
                "flag_definitions": FeatureFlagDefinitionSerializer(
                    flag_defs, many=True
                ).data,
                "overrides": FeatureFlagOverrideSerializer(
                    overrides, many=True
                ).data,
            }
        )


class FeatureFlagOverrideViewSet(viewsets.ModelViewSet):
    """Manage feature flag overrides for the current org."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.system_preferences"
    ordering = ["flag__module", "flag__key"]

    def get_queryset(self):
        org = _effective_org(self.request)
        return FeatureFlagOverride.objects.filter(
            organization=org
        ).select_related("flag")

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return FeatureFlagOverrideWriteSerializer
        return FeatureFlagOverrideSerializer

    def perform_create(self, serializer):
        org = _effective_org(self.request)
        serializer.save(organization=org)


class FeatureFlagDefinitionViewSet(viewsets.ModelViewSet):
    """Superuser-only: CRUD on global flag definitions."""

    serializer_class = FeatureFlagDefinitionSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.system_preferences"
    search_fields = ["key", "name", "description"]
    filterset_fields = ["module", "scope", "flag_type", "is_active", "minimum_tier"]
    ordering = ["module", "key"]

    def get_queryset(self):
        return FeatureFlagDefinition.objects.all()

    def check_permissions(self, request):
        super().check_permissions(request)
        if not request.user.is_superuser:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied(
                "Only platform admins can manage flag definitions."
            )


# ---------------------------------------------------------------------------
# Backup & Disaster Recovery Settings
# ---------------------------------------------------------------------------


class BackupDisasterRecoverySettingsView(generics.RetrieveUpdateAPIView):
    serializer_class = BackupDisasterRecoverySettingsSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.security"

    def get_permissions(self):
        self.rbac_action = "edit" if self.request.method in ("PUT", "PATCH") else "view"
        return super().get_permissions()

    def get_object(self):
        if _is_superuser(self.request) and not _user_org(self.request):
            from apps.accounts.models import Organization

            org = Organization.objects.first()
        else:
            org = _user_org(self.request)
        obj, _ = BackupDisasterRecoverySettings.objects.get_or_create(
            organization=org
        )
        return obj


# ---------------------------------------------------------------------------
# Integration Governance Settings
# ---------------------------------------------------------------------------


class IntegrationGovernanceSettingsView(generics.RetrieveUpdateAPIView):
    serializer_class = IntegrationGovernanceSettingsSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.system_preferences"

    def get_permissions(self):
        self.rbac_action = "edit" if self.request.method in ("PUT", "PATCH") else "view"
        return super().get_permissions()

    def get_object(self):
        if _is_superuser(self.request) and not _user_org(self.request):
            from apps.accounts.models import Organization

            org = Organization.objects.first()
        else:
            org = _user_org(self.request)
        obj, _ = IntegrationGovernanceSettings.objects.get_or_create(
            organization=org
        )
        return obj


# ---------------------------------------------------------------------------
# KPI & Performance Configuration
# ---------------------------------------------------------------------------


class KpiDefinitionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.system_preferences"
    search_fields = ["name", "code", "description"]
    filterset_fields = [
        "category",
        "unit",
        "direction",
        "frequency",
        "is_canonical",
        "grain",
        "is_active",
    ]
    ordering_fields = [
        "name",
        "code",
        "category",
        "grain",
        "freshness_sla_minutes",
        "sort_order",
        "created_at",
    ]
    ordering = ["category", "sort_order", "name"]

    def get_queryset(self):
        qs = _scope_queryset_for_request(self.request, KpiDefinition.objects.all())
        qs = qs.select_related("owner_role", "owner_user")
        if self.action == "list":
            qs = qs.annotate(assignment_count=Count("assignments"))
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return KpiDefinitionListSerializer
        if self.action in ("create", "update", "partial_update"):
            return KpiDefinitionWriteSerializer
        return KpiDefinitionDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_effective_org(self.request))

    def perform_destroy(self, instance):
        if instance.is_system:
            from rest_framework.exceptions import ValidationError

            raise ValidationError("System KPIs cannot be deleted.")
        instance.delete()


class KpiAssignmentViewSet(viewsets.ModelViewSet):
    serializer_class = KpiAssignmentSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.system_preferences"
    filterset_fields = ["kpi", "kpi__category", "role", "department", "is_active"]
    ordering_fields = ["kpi__category", "kpi__sort_order", "created_at"]
    ordering = ["kpi__category", "kpi__sort_order"]

    def get_queryset(self):
        qs = _scope_queryset_for_request(self.request, KpiAssignment.objects.all())
        return qs.select_related("kpi", "role", "department")

    def perform_create(self, serializer):
        serializer.save(organization=_effective_org(self.request))


# ---------------------------------------------------------------------------
# Reporting Engine Settings
# ---------------------------------------------------------------------------


class ReportingEngineSettingsView(generics.RetrieveUpdateAPIView):
    serializer_class = ReportingEngineSettingsSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.system_preferences"

    def get_permissions(self):
        self.rbac_action = "edit" if self.request.method in ("PUT", "PATCH") else "view"
        return super().get_permissions()

    def get_object(self):
        if _is_superuser(self.request) and not _user_org(self.request):
            from apps.accounts.models import Organization

            org = Organization.objects.first()
        else:
            org = _user_org(self.request)
        obj, _ = ReportingEngineSettings.objects.get_or_create(
            organization=org
        )
        return obj


class ConfidentialityLabelViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.security"
    search_fields = ["name", "code", "description"]
    filterset_fields = ["access_level", "is_active"]
    ordering_fields = ["sort_order", "name", "access_level", "created_at"]
    ordering = ["sort_order", "name"]

    def get_queryset(self):
        return _scope_queryset_for_request(self.request, ConfidentialityLabel.objects.all())
    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return ConfidentialityLabelWriteSerializer
        return ConfidentialityLabelSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_effective_org(self.request))

    def perform_destroy(self, instance):
        if instance.is_system:
            from rest_framework.exceptions import ValidationError

            raise ValidationError("System labels cannot be deleted.")
        instance.delete()


class ReportTemplateViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.system_preferences"
    search_fields = ["name", "code", "description"]
    filterset_fields = [
        "template_type",
        "output_format",
        "is_active",
        "confidentiality_label",
        "module_source",
        "visibility",
    ]
    ordering_fields = ["name", "code", "template_type", "created_at"]
    ordering = ["template_type", "name"]

    def get_permissions(self):
        if self.action == "run":
            self.rbac_sub_module = "analytics.all"
            self.rbac_action = "view"
        else:
            self.rbac_sub_module = "settings.system_preferences"
            self.rbac_action = None
        return super().get_permissions()

    def get_queryset(self):
        qs = _scope_queryset_for_request(self.request, ReportTemplate.objects.all())
        if self.action == "list":
            qs = qs.annotate(schedule_count=Count("schedules"))
        return qs.select_related("confidentiality_label", "owner", "shared_department")

    def get_serializer_class(self):
        if self.action == "list":
            return ReportTemplateListSerializer
        if self.action in ("create", "update", "partial_update"):
            return ReportTemplateWriteSerializer
        return ReportTemplateDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_effective_org(self.request))

    def perform_destroy(self, instance):
        if instance.is_system:
            from rest_framework.exceptions import ValidationError

            raise ValidationError("System report templates cannot be deleted.")
        instance.delete()

    @action(detail=True, methods=["post"], url_path="run")
    def run(self, request, pk=None):
        from rest_framework.exceptions import ValidationError

        template = self.get_object()
        payload = ReportRunRequestSerializer(data=request.data or {})
        payload.is_valid(raise_exception=True)

        requested_action = payload.validated_data.get("requested_action") or "run"
        output_format = payload.validated_data.get("output_format") or template.output_format
        run_filters = payload.validated_data.get("filters") or {}
        saved_view_id = payload.validated_data.get("saved_view_id")

        label = template.confidentiality_label
        if requested_action == "export" and label and label.restrict_download:
            raise ValidationError(
                {
                    "output_format": (
                        f"Export is blocked by confidentiality label '{label.name}'."
                    )
                }
            )

        if saved_view_id:
            saved_view = ReportSavedView.objects.filter(
                id=saved_view_id,
                report_template=template,
                organization=template.organization,
                user=request.user,
            ).first()
            if saved_view:
                run_filters = saved_view.filters or {}

        now = timezone.now()
        run = ReportRun.objects.create(
            organization=template.organization,
            report_template=template,
            requested_by=request.user,
            trigger=ReportRun.Trigger.MANUAL,
            status=ReportRun.Status.QUEUED,
            output_format=output_format,
            filters=run_filters,
            row_count=0,
            result_summary={
                "message": "Run accepted and queued for asynchronous execution.",
                "template_code": template.code,
                "requested_action": requested_action,
                "queued_at": timezone.localtime(now).isoformat(),
            },
        )
        enqueue_report_run_execution(run=run)
        run.refresh_from_db()

        return Response(ReportRunSerializer(run).data, status=201)


class ReportLibraryView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "analytics.all"
    rbac_action = "view"

    CATEGORY_DEFS = [
        ("my_reports", "My Reports"),
        ("department_reports", "Department Reports"),
        ("shared_reports", "Shared Reports"),
        ("scheduled_reports", "Scheduled Reports"),
        ("recently_viewed", "Recently Viewed"),
    ]

    def get(self, request):
        org = _effective_org(request)
        if org is not None:
            _ensure_default_report_library_templates(org, request.user)
        profile = getattr(request.user, "profile", None)
        department = getattr(profile, "department", None)
        category = str(request.query_params.get("category", "")).strip().lower()
        search = str(request.query_params.get("q", "")).strip()

        base_qs = _scope_queryset_for_request(
            request,
            ReportTemplate.objects.filter(is_active=True),
            org_field="organization",
        )
        if search:
            base_qs = base_qs.filter(
                Q(name__icontains=search)
                | Q(code__icontains=search)
                | Q(description__icontains=search)
            )

        my_filter = (
            Q(owner=request.user)
            | Q(saved_views__user=request.user, saved_views__is_active=True)
            | Q(subscriptions__user=request.user, subscriptions__is_active=True)
        )
        if department:
            department_filter = (
                Q(visibility=ReportTemplate.Visibility.DEPARTMENT)
                & Q(shared_department=department)
            )
        else:
            department_filter = Q(pk__in=[])
        shared_filter = Q(visibility=ReportTemplate.Visibility.SHARED)
        scheduled_filter = Q(schedules__is_active=True)

        recent_run_ids = list(
            _scope_queryset_for_request(
                request,
                ReportRun.objects.filter(requested_by=request.user),
                org_field="organization",
            )
            .order_by("-created_at")
            .values_list("report_template_id", flat=True)[:200]
        )
        recent_run_ids = list(dict.fromkeys(recent_run_ids))
        recent_filter = Q(id__in=recent_run_ids)

        category_filter_map = {
            "my_reports": my_filter,
            "department_reports": department_filter,
            "shared_reports": shared_filter,
            "scheduled_reports": scheduled_filter,
            "recently_viewed": recent_filter,
        }

        categories = []
        for key, label in self.CATEGORY_DEFS:
            condition = category_filter_map[key]
            count = base_qs.filter(condition).distinct().count()
            categories.append({"key": key, "label": label, "count": count})

        list_qs = base_qs
        if category in category_filter_map:
            list_qs = list_qs.filter(category_filter_map[category])

        last_run_subquery = (
            ReportRun.objects.filter(
                report_template=OuterRef("pk"),
                requested_by=request.user,
            )
            .order_by("-created_at")
            .values("created_at")[:1]
        )
        rows = (
            list_qs
            .annotate(last_run_at=Subquery(last_run_subquery))
            .annotate(schedule_count=Count("schedules", filter=Q(schedules__is_active=True), distinct=True))
            .select_related("owner", "confidentiality_label")
            .distinct()
            .order_by("-last_run_at", "name")
        )

        results = []
        for row in rows:
            module_label = (
                row.get_module_source_display()
                if row.module_source
                else _infer_module_source_from_data_sources(row.data_sources)
            )
            results.append(
                {
                    "id": row.id,
                    "code": row.code,
                    "name": row.name,
                    "description": row.description,
                    "module_source": row.module_source,
                    "module_source_display": module_label,
                    "owner_name": (
                        row.owner.get_full_name() or row.owner.username
                        if row.owner
                        else None
                    ),
                    "confidentiality_label": (
                        row.confidentiality_label.name
                        if row.confidentiality_label
                        else None
                    ),
                    "visibility": row.visibility,
                    "category": (
                        category
                        if category in category_filter_map
                        else _category_for_template(
                            template=row,
                            user=request.user,
                            department=department,
                            recent_ids=recent_run_ids,
                        )
                    ),
                    "last_run_at": row.last_run_at,
                }
            )

        serializer = ReportLibraryResponseSerializer(
            {"categories": categories, "results": results}
        )
        return Response(serializer.data)


class MyScheduledReportsView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "analytics.all"
    rbac_action = "view"

    def get(self, request):
        user_email = (getattr(request.user, "email", "") or "").strip().lower()

        schedules_qs = (
            _scope_queryset_for_request(
                request,
                ScheduledReportDispatch.objects.filter(is_active=True),
                org_field="organization",
            )
            .select_related("report_template")
            .order_by("report_template__name", "name")
        )

        if _is_superuser(request) and not user_email:
            schedules = list(schedules_qs)
        else:
            schedules = [
                schedule
                for schedule in schedules_qs
                if _recipient_matches_user(schedule.recipients, user_email)
            ]

        results = []
        for schedule in schedules:
            latest_run = (
                ReportRun.objects.filter(
                    scheduled_dispatch=schedule,
                    trigger=ReportRun.Trigger.SCHEDULED,
                )
                .order_by("-created_at")
                .first()
            )
            status, status_display = _status_indicator_for_scheduled_run(latest_run)
            results.append(
                {
                    "id": schedule.id,
                    "name": schedule.name or schedule.report_template.name,
                    "report_template": schedule.report_template_id,
                    "report_template_name": schedule.report_template.name,
                    "schedule_text": _scheduled_dispatch_text(schedule),
                    "status": status,
                    "status_display": status_display,
                    "last_dispatched_at": schedule.last_dispatched_at,
                    "latest_run_at": latest_run.created_at if latest_run else None,
                }
            )

        serializer = MyScheduledReportResponseSerializer({"results": results})
        return Response(serializer.data)


class ReportRunViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "analytics.all"
    serializer_class = ReportRunSerializer
    filterset_fields = ["report_template", "status", "trigger"]
    ordering_fields = ["created_at", "started_at", "completed_at", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = _scope_queryset_for_request(
            self.request,
            ReportRun.objects.all(),
            org_field="organization",
        ).select_related(
            "report_template",
            "requested_by",
            "scheduled_dispatch",
            "subscription",
        )
        if _is_superuser(self.request):
            return qs
        return qs.filter(Q(requested_by=self.request.user) | Q(trigger=ReportRun.Trigger.SCHEDULED))


class ReportSavedViewViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "analytics.all"
    search_fields = ["name", "report_template__name", "report_template__code"]
    filterset_fields = ["report_template", "is_active", "is_default"]
    ordering_fields = ["name", "created_at", "updated_at"]
    ordering = ["name"]

    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "view",
        "update": "view",
        "partial_update": "view",
        "destroy": "view",
    }

    def get_queryset(self):
        return _scope_queryset_for_request(
            self.request,
            ReportSavedView.objects.filter(
                user=self.request.user,
            ),
            org_field="organization",
        ).select_related("report_template", "user")

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return ReportSavedViewWriteSerializer
        return ReportSavedViewSerializer

    def perform_create(self, serializer):
        serializer.save(
            organization=_effective_org(self.request),
            user=self.request.user,
        )


class ReportSubscriptionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "analytics.all"
    search_fields = ["report_template__name", "report_template__code"]
    filterset_fields = ["report_template", "frequency", "is_active"]
    ordering_fields = ["created_at", "updated_at", "last_sent_at"]
    ordering = ["-created_at"]

    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "view",
        "update": "view",
        "partial_update": "view",
        "destroy": "view",
    }

    def get_queryset(self):
        return _scope_queryset_for_request(
            self.request,
            ReportSubscription.objects.filter(
                user=self.request.user,
            ),
            org_field="organization",
        ).select_related("report_template", "user")

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return ReportSubscriptionWriteSerializer
        return ReportSubscriptionSerializer

    def perform_create(self, serializer):
        serializer.save(
            organization=_effective_org(self.request),
            user=self.request.user,
        )


class ScheduledReportDispatchViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.system_preferences"
    search_fields = ["name"]
    filterset_fields = ["report_template", "frequency", "is_active"]
    ordering_fields = ["name", "frequency", "created_at"]
    ordering = ["report_template__name", "frequency"]

    def get_queryset(self):
        qs = _scope_queryset_for_request(self.request, ScheduledReportDispatch.objects.all())
        return qs.select_related("report_template")

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return ScheduledReportDispatchWriteSerializer
        return ScheduledReportDispatchSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_effective_org(self.request))


# ---------------------------------------------------------------------------
# Escalation Matrix Settings
# ---------------------------------------------------------------------------


class EscalationMatrixSettingsView(generics.RetrieveUpdateAPIView):
    serializer_class = EscalationMatrixSettingsSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.system_preferences"

    def get_permissions(self):
        self.rbac_action = "edit" if self.request.method in ("PUT", "PATCH") else "view"
        return super().get_permissions()

    def get_object(self):
        if _is_superuser(self.request) and not _user_org(self.request):
            from apps.accounts.models import Organization

            org = Organization.objects.first()
        else:
            org = _user_org(self.request)
        obj, _ = EscalationMatrixSettings.objects.get_or_create(
            organization=org
        )
        return obj


class EscalationTierViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.system_preferences"
    search_fields = ["name", "description"]
    filterset_fields = ["severity", "is_active"]
    ordering_fields = ["severity", "tier_level", "sort_order", "created_at"]
    ordering = ["severity", "tier_level"]

    def get_queryset(self):
        return _scope_queryset_for_request(self.request, EscalationTier.objects.all())
    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return EscalationTierWriteSerializer
        return EscalationTierSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_effective_org(self.request))


class AutoEscalationRuleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.system_preferences"
    search_fields = ["name", "description"]
    filterset_fields = ["rule_type", "is_active"]
    ordering_fields = ["rule_type", "name", "created_at"]
    ordering = ["rule_type", "name"]

    def get_queryset(self):
        qs = _scope_queryset_for_request(self.request, AutoEscalationRule.objects.all())
        return qs.select_related("source_tier", "target_tier")

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return AutoEscalationRuleWriteSerializer
        return AutoEscalationRuleSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_effective_org(self.request))


class BoardNotificationTriggerViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.system_preferences"
    search_fields = ["name", "description"]
    filterset_fields = ["trigger_type", "is_active"]
    ordering_fields = ["trigger_type", "name", "created_at"]
    ordering = ["trigger_type", "name"]

    def get_queryset(self):
        return _scope_queryset_for_request(self.request, BoardNotificationTrigger.objects.all())
    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return BoardNotificationTriggerWriteSerializer
        return BoardNotificationTriggerSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_effective_org(self.request))


# ---------------------------------------------------------------------------
# Communication & Branding Settings
# ---------------------------------------------------------------------------


class CommunicationBrandingSettingsView(generics.RetrieveUpdateAPIView):
    serializer_class = CommunicationBrandingSettingsSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.system_preferences"

    def get_permissions(self):
        self.rbac_action = "edit" if self.request.method in ("PUT", "PATCH") else "view"
        return super().get_permissions()

    def get_object(self):
        if _is_superuser(self.request) and not _user_org(self.request):
            from apps.accounts.models import Organization

            org = Organization.objects.first()
        else:
            org = _user_org(self.request)
        obj, _ = CommunicationBrandingSettings.objects.get_or_create(
            organization=org
        )
        return obj


# ---------------------------------------------------------------------------
# Platform Editions (read-only for most users)
# ---------------------------------------------------------------------------


class PlatformEditionViewSet(viewsets.ReadOnlyModelViewSet):
    """List and retrieve platform editions. Read-only — editions are seeded."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.subscriptions"
    rbac_action = "view"
    queryset = PlatformEdition.objects.filter(is_active=True)
    filterset_fields = ["is_custom", "support_tier"]
    ordering = ["tier_level"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return PlatformEditionDetailSerializer
        return PlatformEditionListSerializer


class FunctionalControlView(generics.RetrieveUpdateAPIView):
    """Retrieve or update the org's functional control toggles."""

    serializer_class = FunctionalControlSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.system_preferences"

    def get_permissions(self):
        self.rbac_action = "edit" if self.request.method in ("PUT", "PATCH") else "view"
        return super().get_permissions()

    def get_object(self):
        if _is_superuser(self.request) and not _user_org(self.request):
            from apps.accounts.models import Organization
            org = Organization.objects.first()
        else:
            org = _user_org(self.request)
        obj, _ = FunctionalControl.objects.get_or_create(organization=org)
        return obj


class TaxRateViewSet(viewsets.ModelViewSet):
    """CRUD for org-level tax rates."""

    serializer_class = TaxRateSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.system_preferences"

    def get_permissions(self):
        self.rbac_action = "edit" if self.request.method not in ("GET", "HEAD", "OPTIONS") else "view"
        return super().get_permissions()

    def get_queryset(self):
        org = _user_org(self.request) if not _is_superuser(self.request) else None
        if not org and _is_superuser(self.request):
            from apps.accounts.models import Organization
            org = Organization.objects.first()
        if not org:
            return TaxRate.objects.none()
        return TaxRate.objects.filter(organization=org)

    def perform_create(self, serializer):
        org = _user_org(self.request)
        if not org and _is_superuser(self.request):
            from apps.accounts.models import Organization
            org = Organization.objects.first()
        serializer.save(organization=org)


class ProcurementPolicySettingsView(generics.RetrieveUpdateAPIView):
    """Retrieve or update the org's procurement policy settings."""

    serializer_class = ProcurementPolicySettingsSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.system_preferences"

    def get_permissions(self):
        self.rbac_action = "edit" if self.request.method in ("PUT", "PATCH") else "view"
        return super().get_permissions()

    def get_object(self):
        if _is_superuser(self.request) and not _user_org(self.request):
            from apps.accounts.models import Organization
            org = Organization.objects.first()
        else:
            org = _user_org(self.request)
        obj, _ = ProcurementPolicySettings.objects.get_or_create(organization=org)
        return obj
