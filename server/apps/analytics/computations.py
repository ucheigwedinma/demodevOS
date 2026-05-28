"""
Pure computation functions for analytics metrics.

Called by both views (live fallback) and Celery tasks (snapshot backfill).
No request objects — accepts querysets or organization IDs.
"""


from datetime import timedelta
from decimal import Decimal

from django.db import OperationalError, ProgrammingError
from django.db.models import Avg, Count, DecimalField, ExpressionWrapper, F, Max, Q, Sum
from django.db.models.functions import Coalesce, TruncMonth
from django.utils import timezone

from apps.finance.budget_utils import get_actual_spent
from apps.finance.models import Budget
from apps.procurement.models import PurchaseOrder, PurchaseRequisition, Vendor
from apps.projects.models import Project
from apps.properties.models import (
    Property,
    PropertyEncumbrance,
    PropertyValuation,
    Unit,
)
from apps.workflows.models import WorkflowInstance

# ── Portfolio ────────────────────────────────────────────────────────────


def get_active_properties(organization_id):
    return Property.objects.filter(is_active=True, organization_id=organization_id)


def compute_portfolio_kpis(qs):
    agg = qs.aggregate(
        total_value=Coalesce(Sum("current_value"), Decimal("0")),
        total_acquisition=Coalesce(Sum("acquisition_price"), Decimal("0")),
        property_count=Count("id"),
        total_area=Coalesce(Sum("total_area_sqft"), Decimal("0")),
    )

    total_value = agg["total_value"]
    total_area = agg["total_area"]
    avg_psf = (total_value / total_area) if total_area else Decimal("0")

    gain_agg = qs.filter(
        current_value__isnull=False,
        acquisition_price__isnull=False,
    ).aggregate(
        unrealized_gain=Coalesce(
            Sum(F("current_value") - F("acquisition_price")),
            Decimal("0"),
        ),
    )

    return {
        "total_value": str(agg["total_value"]),
        "total_acquisition": str(agg["total_acquisition"]),
        "property_count": agg["property_count"],
        "total_area_sqft": str(agg["total_area"]),
        "avg_price_per_sqft": str(round(avg_psf, 2)),
        "unrealized_gain": str(gain_agg["unrealized_gain"]),
    }


def compute_type_distribution(qs):
    rows = (
        qs.values("property_type")
        .annotate(
            count=Count("id"),
            total_value=Coalesce(Sum("current_value"), Decimal("0")),
            total_area=Coalesce(Sum("total_area_sqft"), Decimal("0")),
        )
        .order_by("property_type")
    )
    return [
        {
            "type": r["property_type"],
            "count": r["count"],
            "total_value": str(r["total_value"]),
            "total_area": str(r["total_area"]),
        }
        for r in rows
    ]


def compute_classification_breakdown(qs):
    rows = (
        qs.values("classification")
        .annotate(
            count=Count("id"),
            total_value=Coalesce(Sum("current_value"), Decimal("0")),
        )
        .order_by("classification")
    )
    return [
        {
            "classification": r["classification"],
            "count": r["count"],
            "total_value": str(r["total_value"]),
        }
        for r in rows
    ]


def compute_valuation_history(organization_id):
    qs = PropertyValuation.objects.filter(
        property__is_active=True,
        organization_id=organization_id,
    )
    rows = (
        qs.annotate(month=TruncMonth("valuation_date"))
        .values("month")
        .annotate(
            total_value=Sum("value"),
            valuation_count=Count("id"),
        )
        .order_by("month")
    )
    return [
        {
            "month": r["month"].isoformat(),
            "total_value": str(r["total_value"]),
            "valuation_count": r["valuation_count"],
        }
        for r in rows
    ]


def compute_unit_occupancy(qs):
    rows = (
        Unit.objects.filter(property__in=qs)
        .values("status")
        .annotate(
            count=Count("id"),
            total_area=Coalesce(Sum("area_sqft"), Decimal("0")),
            total_asking_price=Coalesce(Sum("asking_price"), Decimal("0")),
        )
        .order_by("status")
    )
    return [
        {
            "status": r["status"],
            "count": r["count"],
            "total_area": str(r["total_area"]),
            "total_asking_price": str(r["total_asking_price"]),
        }
        for r in rows
    ]


def compute_project_budget_summary(organization_id):
    qs = Project.objects.exclude(status="completed")
    if organization_id is not None:
        qs = qs.filter(organization_id=organization_id)
    projects = (
        qs.annotate(
            total_planned=Coalesce(Sum("phases__planned_budget"), Decimal("0")),
            total_actual=Coalesce(Sum("phases__cost_entries__amount"), Decimal("0")),
        )
        .order_by("-total_actual")[:10]
    )
    return [
        {
            "id": p.id,
            "name": p.name,
            "status": p.status,
            "budget": str(p.budget) if p.budget else None,
            "total_planned": str(p.total_planned),
            "total_actual": str(p.total_actual),
            "variance": str(p.total_planned - p.total_actual),
        }
        for p in projects
    ]


def compute_top_properties(qs, ascending=False, limit=5):
    rows = (
        qs.filter(
            current_value__isnull=False,
            acquisition_price__isnull=False,
            acquisition_price__gt=0,
        )
        .annotate(
            gain=F("current_value") - F("acquisition_price"),
            gain_pct=(
                (F("current_value") - F("acquisition_price"))
                * Decimal("100.0")
                / F("acquisition_price")
            ),
        )
        .order_by("gain" if ascending else "-gain")[:limit]
    )
    return [
        {
            "id": r.id,
            "name": r.name,
            "property_type": r.property_type,
            "acquisition_price": str(r.acquisition_price),
            "current_value": str(r.current_value),
            "gain": str(r.gain),
            "gain_pct": str(round(r.gain_pct, 1)),
        }
        for r in rows
    ]


def compute_encumbrance_summary(qs):
    base = PropertyEncumbrance.objects.filter(
        property__in=qs,
        status__in=["active", "pending"],
    )
    by_type = (
        base.values("encumbrance_type")
        .annotate(
            count=Count("id"),
            total_amount=Coalesce(Sum("amount"), Decimal("0")),
        )
        .order_by("encumbrance_type")
    )
    totals = base.aggregate(
        total_count=Count("id"),
        total_amount=Coalesce(Sum("amount"), Decimal("0")),
    )
    return {
        "by_type": [
            {
                "type": r["encumbrance_type"],
                "count": r["count"],
                "total_amount": str(r["total_amount"]),
            }
            for r in by_type
        ],
        "total_count": totals["total_count"],
        "total_amount": str(totals["total_amount"]),
    }


def compute_construction_summary(organization_id):
    """Cross-module construction pulse derived from field-ops and delay registers."""
    default = {
        "active_site_reports": 0,
        "avg_progress_percent": 0.0,
        "open_field_issues": 0,
        "recent_delay_entries": 0,
    }

    try:
        from apps.projects.models import (
            ProjectDailySiteReport,
            ProjectFieldEscalation,
            ProjectScheduleDelayLog,
        )
    except Exception:
        return default

    try:
        window_start = timezone.localdate() - timedelta(days=30)
        reports = ProjectDailySiteReport.objects.filter(
            organization_id=organization_id,
            report_date__gte=window_start,
        )
        report_count = reports.count()
        avg_progress = reports.aggregate(
            avg=Coalesce(Avg("progress_percent"), Decimal("0")),
        ).get("avg")
        progress_pct = round(float(avg_progress or Decimal("0")), 2)

        open_issues = ProjectFieldEscalation.objects.filter(
            organization_id=organization_id,
            status__in=[
                ProjectFieldEscalation.Status.OPEN,
                ProjectFieldEscalation.Status.ACKNOWLEDGED,
                ProjectFieldEscalation.Status.IN_PROGRESS,
            ],
        ).count()
        delay_entries = ProjectScheduleDelayLog.objects.filter(
            organization_id=organization_id,
            delay_date__gte=window_start,
        ).count()

        return {
            "active_site_reports": report_count,
            "avg_progress_percent": progress_pct,
            "open_field_issues": open_issues,
            "recent_delay_entries": delay_entries,
        }
    except (ProgrammingError, OperationalError):
        return default


def compute_crm_summary(organization_id):
    """CRM pipeline and reservation conversion summary."""
    default = {
        "active_leads": 0,
        "tenant_leads": 0,
        "active_reservations": 0,
        "converted_reservations": 0,
        "converted_value": "0",
    }

    try:
        from apps.crm.models import Lead, UnitReservation
    except Exception:
        return default

    try:
        leads = Lead.objects.filter(organization_id=organization_id)
        reservations = UnitReservation.objects.filter(organization_id=organization_id)
        converted_value = reservations.filter(
            status=UnitReservation.Status.CONVERTED,
        ).aggregate(
            total=Coalesce(Sum("total_price"), Decimal("0")),
        )["total"]

        return {
            "active_leads": leads.filter(status=Lead.Status.ACTIVE).count(),
            "tenant_leads": leads.filter(
                status=Lead.Status.ACTIVE,
                lead_type=Lead.LeadType.TENANT,
            ).count(),
            "active_reservations": reservations.filter(
                status__in=[
                    UnitReservation.Status.HOLD,
                    UnitReservation.Status.RESERVED,
                    UnitReservation.Status.PAYMENT_PENDING,
                    UnitReservation.Status.PAID,
                    UnitReservation.Status.CONVERTING,
                ],
            ).count(),
            "converted_reservations": reservations.filter(
                status=UnitReservation.Status.CONVERTED,
            ).count(),
            "converted_value": str(converted_value or Decimal("0")),
        }
    except (ProgrammingError, OperationalError):
        return default


def compute_hr_summary(organization_id):
    """Workforce and vacancy roll-up from HR."""
    default = {
        "active_employees": 0,
        "employees_on_leave": 0,
        "open_vacancies": 0,
        "staffing_gap": 0,
    }

    try:
        from apps.hr.models import EmployeeRecord, Vacancy
    except Exception:
        return default

    try:
        employees = EmployeeRecord.objects.filter(organization_id=organization_id)
        active = employees.filter(
            employment_status=EmployeeRecord.EmploymentStatus.ACTIVE,
        ).count()
        on_leave = employees.filter(
            employment_status=EmployeeRecord.EmploymentStatus.ON_LEAVE,
        ).count()
        open_vacancies = Vacancy.objects.filter(
            organization_id=organization_id,
            status__in=[Vacancy.Status.OPEN, Vacancy.Status.ON_HOLD],
        ).count()

        return {
            "active_employees": active,
            "employees_on_leave": on_leave,
            "open_vacancies": open_vacancies,
            "staffing_gap": max(open_vacancies - on_leave, 0),
        }
    except (ProgrammingError, OperationalError):
        return default


def compute_procurement_summary(organization_id):
    """Procurement commitments and delivery pressure summary."""
    default = {
        "open_commitments": 0,
        "committed_amount": "0",
        "overdue_deliveries": 0,
        "pending_requisitions": 0,
    }

    try:
        open_pos = PurchaseOrder.objects.filter(
            organization_id=organization_id,
            status__in=[
                PurchaseOrder.Status.APPROVED,
                PurchaseOrder.Status.ISSUED,
                PurchaseOrder.Status.PARTIALLY_RECEIVED,
            ],
        )
        committed_amount = open_pos.aggregate(
            total=Coalesce(Sum("total_amount"), Decimal("0")),
        )["total"]
        overdue_deliveries = open_pos.filter(
            expected_delivery_date__isnull=False,
            expected_delivery_date__lt=timezone.localdate(),
        ).count()
        pending_requisitions = PurchaseRequisition.objects.filter(
            organization_id=organization_id,
            status__in=[
                PurchaseRequisition.Status.SUBMITTED,
                PurchaseRequisition.Status.APPROVED,
            ],
        ).count()

        return {
            "open_commitments": open_pos.count(),
            "committed_amount": str(committed_amount or Decimal("0")),
            "overdue_deliveries": overdue_deliveries,
            "pending_requisitions": pending_requisitions,
        }
    except (ProgrammingError, OperationalError):
        return default


def compute_facility_summary(organization_id):
    """Facilities and maintenance execution summary."""
    default = {
        "open_work_orders": 0,
        "urgent_work_orders": 0,
        "open_service_requests": 0,
        "pending_inspections": 0,
    }

    try:
        from apps.properties.models import Inspection, ServiceRequest, WorkOrder
    except Exception:
        return default

    try:
        open_work_orders = WorkOrder.objects.filter(
            organization_id=organization_id,
            status__in=[
                WorkOrder.Status.OPEN,
                WorkOrder.Status.ASSIGNED,
                WorkOrder.Status.IN_PROGRESS,
                WorkOrder.Status.ON_HOLD,
            ],
        )
        return {
            "open_work_orders": open_work_orders.count(),
            "urgent_work_orders": open_work_orders.filter(
                priority=WorkOrder.Priority.URGENT,
            ).count(),
            "open_service_requests": ServiceRequest.objects.filter(
                organization_id=organization_id,
                status__in=[
                    ServiceRequest.Status.OPEN,
                    ServiceRequest.Status.ACKNOWLEDGED,
                    ServiceRequest.Status.IN_PROGRESS,
                ],
            ).count(),
            "pending_inspections": Inspection.objects.filter(
                organization_id=organization_id,
                status__in=[
                    Inspection.Status.SCHEDULED,
                    Inspection.Status.IN_PROGRESS,
                ],
            ).count(),
        }
    except (ProgrammingError, OperationalError):
        return default


def compute_tenant_summary(organization_id):
    """Tenant pulse derived from leased inventory, service requests, and tenant sales leads."""
    default = {
        "active_tenants": 0,
        "open_tenant_requests": 0,
        "tenant_leads": 0,
        "active_tenant_reservations": 0,
    }

    try:
        from apps.crm.models import Lead, UnitReservation
        from apps.properties.models import ServiceRequest, Unit
    except Exception:
        return default

    try:
        tenant_leads = Lead.objects.filter(
            organization_id=organization_id,
            lead_type=Lead.LeadType.TENANT,
            status=Lead.Status.ACTIVE,
        ).count()
        active_tenant_reservations = UnitReservation.objects.filter(
            organization_id=organization_id,
            lead__lead_type=Lead.LeadType.TENANT,
            status__in=[
                UnitReservation.Status.HOLD,
                UnitReservation.Status.RESERVED,
                UnitReservation.Status.PAYMENT_PENDING,
                UnitReservation.Status.PAID,
                UnitReservation.Status.CONVERTING,
            ],
        ).count()

        return {
            "active_tenants": Unit.objects.filter(
                organization_id=organization_id,
                status=Unit.UnitStatus.LEASED,
            ).count(),
            "open_tenant_requests": ServiceRequest.objects.filter(
                organization_id=organization_id,
                status__in=[
                    ServiceRequest.Status.OPEN,
                    ServiceRequest.Status.ACKNOWLEDGED,
                    ServiceRequest.Status.IN_PROGRESS,
                ],
            ).count(),
            "tenant_leads": tenant_leads,
            "active_tenant_reservations": active_tenant_reservations,
        }
    except (ProgrammingError, OperationalError):
        return default


def compute_risk_alerts(organization_id):
    """Cross-module risk alert feed used by the dashboard risk center."""
    today = timezone.localdate()
    now = timezone.now()
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}

    def empty_severity():
        return {"critical": 0, "high": 0, "medium": 0, "low": 0}

    def clamp_severity(value):
        if value in severity_order:
            return value
        return "medium"

    def to_iso(value):
        return value.isoformat() if value is not None else None

    def module_stub(label):
        return {
            "label": label,
            "open_alerts": 0,
            "critical_alerts": 0,
            "high_alerts": 0,
            "medium_alerts": 0,
            "low_alerts": 0,
            "last_event_at": None,
            "summary": {},
            "items": [],
        }

    def apply_counts(module_payload, counts):
        module_payload["critical_alerts"] = int(counts.get("critical", 0))
        module_payload["high_alerts"] = int(counts.get("high", 0))
        module_payload["medium_alerts"] = int(counts.get("medium", 0))
        module_payload["low_alerts"] = int(counts.get("low", 0))
        module_payload["open_alerts"] = (
            module_payload["critical_alerts"]
            + module_payload["high_alerts"]
            + module_payload["medium_alerts"]
            + module_payload["low_alerts"]
        )

    def currency(value):
        return str(value or Decimal("0"))

    def max_dt(*values):
        populated = [value for value in values if value is not None]
        return max(populated) if populated else None

    feeds = {
        "projects": module_stub("Projects"),
        "workflows": module_stub("Workflows"),
        "finance": module_stub("Finance"),
        "procurement": module_stub("Procurement"),
        "facilities": module_stub("Facilities"),
        "crm": module_stub("CRM"),
    }

    resolved_last_7d = 0
    all_feed_items = []

    # --- Projects risk register feed ---
    project_counts = empty_severity()
    try:
        from apps.projects.models import ProjectRiskRegisterEntry

        active_risks = ProjectRiskRegisterEntry.objects.filter(
            organization_id=organization_id,
            status__in=[
                ProjectRiskRegisterEntry.Status.OPEN,
                ProjectRiskRegisterEntry.Status.IN_PROGRESS,
                ProjectRiskRegisterEntry.Status.ACCEPTED,
            ],
        ).select_related("project", "owner_role")

        for row in (
            active_risks.values("severity")
            .annotate(count=Count("id"))
            .order_by()
        ):
            severity = clamp_severity(row["severity"])
            project_counts[severity] += int(row["count"] or 0)

        by_status = {
            row["status"]: int(row["count"] or 0)
            for row in active_risks.values("status").annotate(count=Count("id"))
        }
        overdue_mitigations = active_risks.filter(
            target_resolution_date__isnull=False,
            target_resolution_date__lt=today,
        ).count()
        projects_last_event = active_risks.aggregate(last_event=Max("updated_at")).get(
            "last_event"
        )
        resolved_last_7d += ProjectRiskRegisterEntry.objects.filter(
            organization_id=organization_id,
            status__in=[
                ProjectRiskRegisterEntry.Status.MITIGATED,
                ProjectRiskRegisterEntry.Status.CLOSED,
            ],
            resolved_on__gte=today - timedelta(days=7),
        ).count()

        project_items = []
        for risk in active_risks.order_by("-risk_score", "target_resolution_date", "-updated_at")[:24]:
            severity = clamp_severity(risk.severity)
            owner = ""
            if risk.owner_role_id and getattr(risk.owner_role, "name", ""):
                owner = risk.owner_role.name
            item = {
                "id": f"project-risk-{risk.id}",
                "module": "projects",
                "module_label": "Projects",
                "alert_type": "risk_register",
                "title": risk.title,
                "subject": getattr(risk.project, "name", ""),
                "severity": severity,
                "status": risk.status,
                "owner": owner,
                "due_date": to_iso(risk.target_resolution_date),
                "amount": None,
                "risk_score": int(risk.risk_score or 0),
                "note": "Mitigation overdue"
                if (risk.target_resolution_date and risk.target_resolution_date < today)
                else "Open register risk",
                "updated_at": to_iso(risk.updated_at),
            }
            project_items.append(item)
            all_feed_items.append(item)

        feeds["projects"]["summary"] = {
            "open_risks": active_risks.count(),
            "critical_open_risks": project_counts["critical"],
            "high_open_risks": project_counts["high"],
            "overdue_mitigations": overdue_mitigations,
            "in_progress_risks": by_status.get(ProjectRiskRegisterEntry.Status.IN_PROGRESS, 0),
            "accepted_risks": by_status.get(ProjectRiskRegisterEntry.Status.ACCEPTED, 0),
        }
        feeds["projects"]["items"] = project_items
        feeds["projects"]["last_event_at"] = to_iso(projects_last_event)
    except (ProgrammingError, OperationalError):
        pass
    except Exception:
        pass
    apply_counts(feeds["projects"], project_counts)

    # --- Workflow SLA risk feed ---
    workflow_counts = empty_severity()
    try:
        from apps.workflows.models import WorkflowInstance, WorkflowStep

        pending_steps = WorkflowStep.objects.filter(
            decision=WorkflowStep.Decision.PENDING,
            workflow_instance__state__in=[
                WorkflowInstance.State.PENDING,
                WorkflowInstance.State.IN_PROGRESS,
            ],
            workflow_instance__template__organization_id=organization_id,
        ).select_related("workflow_instance__template", "approver_user")

        total_pending = pending_steps.count()
        breached_steps = pending_steps.filter(sla_breached=True).count()
        due_in_12h = pending_steps.filter(
            sla_breached=False,
            sla_deadline__isnull=False,
            sla_deadline__lte=now + timedelta(hours=12),
        ).count()
        due_in_24h = pending_steps.filter(
            sla_breached=False,
            sla_deadline__isnull=False,
            sla_deadline__gt=now + timedelta(hours=12),
            sla_deadline__lte=now + timedelta(hours=24),
        ).count()
        no_deadline = pending_steps.filter(sla_deadline__isnull=True).count()

        workflow_counts["critical"] = breached_steps
        workflow_counts["high"] = due_in_12h
        workflow_counts["medium"] = due_in_24h
        workflow_counts["low"] = max(total_pending - breached_steps - due_in_12h - due_in_24h, 0)

        workflow_last_event = pending_steps.aggregate(last_event=Max("updated_at")).get(
            "last_event"
        )
        resolved_last_7d += WorkflowStep.objects.filter(
            workflow_instance__template__organization_id=organization_id,
            decision__in=[
                WorkflowStep.Decision.APPROVED,
                WorkflowStep.Decision.REJECTED,
                WorkflowStep.Decision.SKIPPED,
            ],
            decided_at__gte=now - timedelta(days=7),
        ).count()

        workflow_items = []
        for step in pending_steps.order_by("-sla_breached", "sla_deadline", "created_at")[:24]:
            if step.sla_breached:
                severity = "critical"
            elif step.sla_deadline and step.sla_deadline <= now + timedelta(hours=12):
                severity = "high"
            elif step.sla_deadline and step.sla_deadline <= now + timedelta(hours=24):
                severity = "medium"
            else:
                severity = "low"
            owner = ""
            if step.approver_user_id:
                owner = step.approver_user.get_full_name() or step.approver_user.username
            elif step.approver_role_slug:
                owner = step.approver_role_slug.replace("-", " ").replace("_", " ").title()
            item = {
                "id": f"workflow-step-{step.id}",
                "module": "workflows",
                "module_label": "Workflows",
                "alert_type": "approval_sla",
                "title": step.name,
                "subject": step.workflow_instance.template.name,
                "severity": severity,
                "status": "sla_breached" if step.sla_breached else "pending",
                "owner": owner,
                "due_date": to_iso(step.sla_deadline),
                "amount": None,
                "risk_score": None,
                "note": "SLA breached" if step.sla_breached else "Pending approval",
                "updated_at": to_iso(step.updated_at),
            }
            workflow_items.append(item)
            all_feed_items.append(item)

        feeds["workflows"]["summary"] = {
            "pending_steps": total_pending,
            "sla_breached_steps": breached_steps,
            "due_within_24_hours": due_in_12h + due_in_24h,
            "steps_without_deadline": no_deadline,
        }
        feeds["workflows"]["items"] = workflow_items
        feeds["workflows"]["last_event_at"] = to_iso(workflow_last_event)
    except (ProgrammingError, OperationalError):
        pass
    except Exception:
        pass
    apply_counts(feeds["workflows"], workflow_counts)

    # --- Finance risk feed ---
    finance_counts = empty_severity()
    try:
        from apps.finance.models import Bill, Invoice

        balance_field = DecimalField(max_digits=18, decimal_places=2)

        bills = (
            Bill.objects.filter(organization_id=organization_id)
            .exclude(status__in=[Bill.Status.PAID, Bill.Status.CANCELLED])
            .select_related("vendor")
            .annotate(
                paid_amount=Coalesce(Sum("payments__amount"), Decimal("0")),
            )
            .annotate(
                balance_amount=ExpressionWrapper(
                    F("total_amount") - F("paid_amount"),
                    output_field=balance_field,
                )
            )
        )
        invoices = (
            Invoice.objects.filter(organization_id=organization_id)
            .exclude(status__in=[Invoice.Status.PAID, Invoice.Status.CANCELLED])
            .select_related("customer")
            .annotate(
                paid_amount=Coalesce(Sum("payments__amount"), Decimal("0")),
            )
            .annotate(
                balance_amount=ExpressionWrapper(
                    F("total_amount") - F("paid_amount"),
                    output_field=balance_field,
                )
            )
        )

        overdue_bills = bills.filter(due_date__lt=today)
        overdue_invoices = invoices.filter(due_date__lt=today)
        upcoming_bills = bills.filter(due_date__gte=today, due_date__lte=today + timedelta(days=7))
        upcoming_invoices = invoices.filter(
            due_date__gte=today, due_date__lte=today + timedelta(days=7)
        )

        finance_counts["critical"] = overdue_bills.filter(
            due_date__lte=today - timedelta(days=30)
        ).count() + overdue_invoices.filter(due_date__lte=today - timedelta(days=30)).count()
        finance_counts["high"] = (
            overdue_bills.count()
            + overdue_invoices.count()
            - finance_counts["critical"]
        )
        finance_counts["medium"] = upcoming_bills.count() + upcoming_invoices.count()

        bills_overdue_exposure = overdue_bills.aggregate(
            total=Coalesce(Sum("balance_amount"), Decimal("0"))
        ).get("total")
        invoices_overdue_exposure = overdue_invoices.aggregate(
            total=Coalesce(Sum("balance_amount"), Decimal("0"))
        ).get("total")
        due_soon_exposure = (
            upcoming_bills.aggregate(total=Coalesce(Sum("balance_amount"), Decimal("0"))).get("total")
            or Decimal("0")
        ) + (
            upcoming_invoices.aggregate(total=Coalesce(Sum("balance_amount"), Decimal("0"))).get(
                "total"
            )
            or Decimal("0")
        )

        finance_last_event = max_dt(
            bills.aggregate(last_event=Max("updated_at")).get("last_event"),
            invoices.aggregate(last_event=Max("updated_at")).get("last_event"),
        )

        finance_items = []
        for bill in bills.filter(
            Q(due_date__lt=today) | Q(due_date__lte=today + timedelta(days=7))
        ).order_by("due_date", "-updated_at")[:16]:
            overdue_days = (today - bill.due_date).days
            if overdue_days >= 30:
                severity = "critical"
            elif overdue_days > 0:
                severity = "high"
            else:
                severity = "medium"
            due_note = (
                f"{overdue_days} days overdue"
                if overdue_days > 0
                else f"Due in {max((bill.due_date - today).days, 0)} days"
            )
            item = {
                "id": f"finance-bill-{bill.id}",
                "module": "finance",
                "module_label": "Finance",
                "alert_type": "payables",
                "title": bill.bill_number,
                "subject": getattr(bill.vendor, "name", ""),
                "severity": severity,
                "status": "overdue" if overdue_days > 0 else "due_soon",
                "owner": "Finance",
                "due_date": to_iso(bill.due_date),
                "amount": currency(getattr(bill, "balance_amount", Decimal("0"))),
                "risk_score": None,
                "note": due_note,
                "updated_at": to_iso(bill.updated_at),
            }
            finance_items.append(item)
            all_feed_items.append(item)

        for invoice in invoices.filter(
            Q(due_date__lt=today) | Q(due_date__lte=today + timedelta(days=7))
        ).order_by("due_date", "-updated_at")[:16]:
            overdue_days = (today - invoice.due_date).days
            if overdue_days >= 30:
                severity = "critical"
            elif overdue_days > 0:
                severity = "high"
            else:
                severity = "medium"
            due_note = (
                f"{overdue_days} days overdue"
                if overdue_days > 0
                else f"Due in {max((invoice.due_date - today).days, 0)} days"
            )
            item = {
                "id": f"finance-invoice-{invoice.id}",
                "module": "finance",
                "module_label": "Finance",
                "alert_type": "receivables",
                "title": invoice.invoice_number,
                "subject": getattr(invoice.customer, "name", ""),
                "severity": severity,
                "status": "overdue" if overdue_days > 0 else "due_soon",
                "owner": "Finance",
                "due_date": to_iso(invoice.due_date),
                "amount": currency(getattr(invoice, "balance_amount", Decimal("0"))),
                "risk_score": None,
                "note": due_note,
                "updated_at": to_iso(invoice.updated_at),
            }
            finance_items.append(item)
            all_feed_items.append(item)

        feeds["finance"]["summary"] = {
            "open_payables": bills.count(),
            "open_receivables": invoices.count(),
            "overdue_bills": overdue_bills.count(),
            "overdue_invoices": overdue_invoices.count(),
            "overdue_exposure": currency(
                (bills_overdue_exposure or Decimal("0"))
                + (invoices_overdue_exposure or Decimal("0"))
            ),
            "due_soon_exposure": currency(due_soon_exposure),
        }
        feeds["finance"]["items"] = finance_items
        feeds["finance"]["last_event_at"] = to_iso(finance_last_event)
    except (ProgrammingError, OperationalError):
        pass
    except Exception:
        pass
    apply_counts(feeds["finance"], finance_counts)

    # --- Procurement risk feed ---
    procurement_counts = empty_severity()
    try:
        from apps.procurement.models import PurchaseOrder, PurchaseRequisition, Vendor

        open_purchase_orders = PurchaseOrder.objects.filter(
            organization_id=organization_id,
            status__in=[
                PurchaseOrder.Status.APPROVED,
                PurchaseOrder.Status.ISSUED,
                PurchaseOrder.Status.PARTIALLY_RECEIVED,
            ],
            expected_delivery_date__isnull=False,
        ).select_related("vendor", "project")

        overdue_deliveries = open_purchase_orders.filter(expected_delivery_date__lt=today)
        upcoming_deliveries = open_purchase_orders.filter(
            expected_delivery_date__gte=today,
            expected_delivery_date__lte=today + timedelta(days=7),
        )

        requisitions = PurchaseRequisition.objects.filter(
            organization_id=organization_id,
            status__in=[
                PurchaseRequisition.Status.SUBMITTED,
                PurchaseRequisition.Status.APPROVED,
            ],
            required_date__isnull=False,
        ).select_related("project")
        overdue_requisitions = requisitions.filter(required_date__lt=today)
        upcoming_requisitions = requisitions.filter(
            required_date__gte=today,
            required_date__lte=today + timedelta(days=7),
        )
        vendor_risks = Vendor.objects.filter(
            organization_id=organization_id,
            is_active=True,
        ).filter(
            Q(is_blacklisted=True)
            | Q(compliance_status=Vendor.ComplianceStatus.EXPIRED)
            | Q(compliance_status=Vendor.ComplianceStatus.NON_COMPLIANT)
        )

        procurement_counts["critical"] = (
            overdue_deliveries.filter(
                expected_delivery_date__lte=today - timedelta(days=14)
            ).count()
            + overdue_requisitions.filter(priority=PurchaseRequisition.Priority.URGENT).count()
            + vendor_risks.filter(
                Q(is_blacklisted=True) | Q(compliance_status=Vendor.ComplianceStatus.EXPIRED)
            ).count()
        )
        procurement_counts["high"] = (
            overdue_deliveries.count()
            - overdue_deliveries.filter(expected_delivery_date__lte=today - timedelta(days=14)).count()
            + overdue_requisitions.exclude(priority=PurchaseRequisition.Priority.URGENT).count()
            + upcoming_requisitions.filter(
                priority__in=[
                    PurchaseRequisition.Priority.URGENT,
                    PurchaseRequisition.Priority.HIGH,
                ]
            ).count()
            + vendor_risks.count()
            - vendor_risks.filter(
                Q(is_blacklisted=True) | Q(compliance_status=Vendor.ComplianceStatus.EXPIRED)
            ).count()
        )
        procurement_counts["medium"] = (
            upcoming_deliveries.count()
            + upcoming_requisitions.exclude(
                priority__in=[
                    PurchaseRequisition.Priority.URGENT,
                    PurchaseRequisition.Priority.HIGH,
                ]
            ).count()
        )

        procurement_last_event = max_dt(
            open_purchase_orders.aggregate(last_event=Max("updated_at")).get("last_event"),
            requisitions.aggregate(last_event=Max("updated_at")).get("last_event"),
            vendor_risks.aggregate(last_event=Max("updated_at")).get("last_event"),
        )

        procurement_items = []
        for po in open_purchase_orders.filter(
            Q(expected_delivery_date__lt=today)
            | Q(expected_delivery_date__lte=today + timedelta(days=7))
        ).order_by("expected_delivery_date", "-updated_at")[:12]:
            delta_days = (today - po.expected_delivery_date).days
            if delta_days >= 14:
                severity = "critical"
            elif delta_days > 0:
                severity = "high"
            else:
                severity = "medium"
            item = {
                "id": f"procurement-po-{po.id}",
                "module": "procurement",
                "module_label": "Procurement",
                "alert_type": "delivery_delay",
                "title": po.po_number,
                "subject": getattr(po.vendor, "name", ""),
                "severity": severity,
                "status": "overdue_delivery" if delta_days > 0 else "delivery_due",
                "owner": "Supply Chain",
                "due_date": to_iso(po.expected_delivery_date),
                "amount": currency(po.total_amount),
                "risk_score": None,
                "note": (
                    f"Delivery overdue by {delta_days} days"
                    if delta_days > 0
                    else f"Delivery due in {max((po.expected_delivery_date - today).days, 0)} days"
                ),
                "updated_at": to_iso(po.updated_at),
            }
            procurement_items.append(item)
            all_feed_items.append(item)

        for requisition in requisitions.filter(
            Q(required_date__lt=today) | Q(required_date__lte=today + timedelta(days=7))
        ).order_by("required_date", "-updated_at")[:12]:
            delta_days = (today - requisition.required_date).days
            if requisition.priority == PurchaseRequisition.Priority.URGENT and delta_days > 0:
                severity = "critical"
            elif delta_days > 0 or requisition.priority in [
                PurchaseRequisition.Priority.URGENT,
                PurchaseRequisition.Priority.HIGH,
            ]:
                severity = "high"
            else:
                severity = "medium"
            item = {
                "id": f"procurement-pr-{requisition.id}",
                "module": "procurement",
                "module_label": "Procurement",
                "alert_type": "requisition_pressure",
                "title": requisition.pr_number,
                "subject": requisition.title,
                "severity": severity,
                "status": requisition.status,
                "owner": requisition.requester,
                "due_date": to_iso(requisition.required_date),
                "amount": currency(requisition.estimated_total),
                "risk_score": None,
                "note": (
                    f"Required date overdue by {delta_days} days"
                    if delta_days > 0
                    else f"Required within {max((requisition.required_date - today).days, 0)} days"
                ),
                "updated_at": to_iso(requisition.updated_at),
            }
            procurement_items.append(item)
            all_feed_items.append(item)

        for vendor in vendor_risks.order_by("name")[:8]:
            if vendor.is_blacklisted or vendor.compliance_status == Vendor.ComplianceStatus.EXPIRED:
                severity = "critical"
            else:
                severity = "high"
            item = {
                "id": f"procurement-vendor-{vendor.id}",
                "module": "procurement",
                "module_label": "Procurement",
                "alert_type": "vendor_compliance",
                "title": vendor.name,
                "subject": vendor.get_compliance_status_display(),
                "severity": severity,
                "status": vendor.compliance_status,
                "owner": "Vendor Management",
                "due_date": None,
                "amount": None,
                "risk_score": None,
                "note": "Vendor blacklisted" if vendor.is_blacklisted else "Compliance requires action",
                "updated_at": to_iso(vendor.updated_at),
            }
            procurement_items.append(item)
            all_feed_items.append(item)

        feeds["procurement"]["summary"] = {
            "open_purchase_orders": open_purchase_orders.count(),
            "overdue_deliveries": overdue_deliveries.count(),
            "requisitions_needing_attention": overdue_requisitions.count()
            + upcoming_requisitions.count(),
            "vendor_compliance_alerts": vendor_risks.count(),
            "open_commitment_amount": currency(
                open_purchase_orders.aggregate(total=Coalesce(Sum("total_amount"), Decimal("0"))).get(
                    "total"
                )
            ),
        }
        feeds["procurement"]["items"] = procurement_items
        feeds["procurement"]["last_event_at"] = to_iso(procurement_last_event)
    except (ProgrammingError, OperationalError):
        pass
    except Exception:
        pass
    apply_counts(feeds["procurement"], procurement_counts)

    # --- Facilities risk feed ---
    facilities_counts = empty_severity()
    try:
        from apps.properties.models import Inspection, ServiceRequest, WorkOrder

        open_work_orders = WorkOrder.objects.filter(
            organization_id=organization_id,
            status__in=[
                WorkOrder.Status.OPEN,
                WorkOrder.Status.ASSIGNED,
                WorkOrder.Status.IN_PROGRESS,
                WorkOrder.Status.ON_HOLD,
            ],
            priority__in=[WorkOrder.Priority.URGENT, WorkOrder.Priority.HIGH],
        ).select_related("property")
        inspections = Inspection.objects.filter(
            organization_id=organization_id,
        ).filter(
            Q(risk_level__in=[Inspection.RiskLevel.HIGH, Inspection.RiskLevel.CRITICAL])
            | Q(compliance_status=Inspection.ComplianceStatus.NON_COMPLIANT)
            | Q(corrective_action_required=True)
        ).select_related("property")
        service_requests = ServiceRequest.objects.filter(
            organization_id=organization_id,
            status__in=[
                ServiceRequest.Status.OPEN,
                ServiceRequest.Status.ACKNOWLEDGED,
                ServiceRequest.Status.IN_PROGRESS,
            ],
            priority__in=[ServiceRequest.Priority.URGENT, ServiceRequest.Priority.HIGH],
        ).select_related("property")

        facilities_counts["critical"] = (
            open_work_orders.filter(
                priority=WorkOrder.Priority.URGENT,
                due_date__isnull=False,
                due_date__lt=today,
            ).count()
            + inspections.filter(risk_level=Inspection.RiskLevel.CRITICAL).count()
            + service_requests.filter(priority=ServiceRequest.Priority.URGENT).count()
        )
        facilities_counts["high"] = (
            open_work_orders.count()
            - open_work_orders.filter(
                priority=WorkOrder.Priority.URGENT,
                due_date__isnull=False,
                due_date__lt=today,
            ).count()
            + inspections.filter(risk_level=Inspection.RiskLevel.HIGH).count()
            + inspections.filter(
                risk_level="",
                compliance_status=Inspection.ComplianceStatus.NON_COMPLIANT,
            ).count()
            + service_requests.filter(priority=ServiceRequest.Priority.HIGH).count()
        )
        facilities_counts["medium"] = inspections.filter(
            risk_level=Inspection.RiskLevel.MEDIUM
        ).count()

        facilities_last_event = max_dt(
            open_work_orders.aggregate(last_event=Max("updated_at")).get("last_event"),
            inspections.aggregate(last_event=Max("updated_at")).get("last_event"),
            service_requests.aggregate(last_event=Max("updated_at")).get("last_event"),
        )
        resolved_last_7d += ServiceRequest.objects.filter(
            organization_id=organization_id,
            status__in=[
                ServiceRequest.Status.RESOLVED,
                ServiceRequest.Status.CLOSED,
            ],
            resolved_date__gte=today - timedelta(days=7),
        ).count()

        facilities_items = []
        for work_order in open_work_orders.order_by("due_date", "-updated_at")[:12]:
            overdue = bool(work_order.due_date and work_order.due_date < today)
            if work_order.priority == WorkOrder.Priority.URGENT and overdue:
                severity = "critical"
            elif work_order.priority in [WorkOrder.Priority.URGENT, WorkOrder.Priority.HIGH]:
                severity = "high"
            else:
                severity = "medium"
            item = {
                "id": f"facilities-wo-{work_order.id}",
                "module": "facilities",
                "module_label": "Facilities",
                "alert_type": "work_order",
                "title": work_order.title,
                "subject": getattr(work_order.property, "name", ""),
                "severity": severity,
                "status": work_order.status,
                "owner": work_order.assigned_to or work_order.reported_by or "Facilities",
                "due_date": to_iso(work_order.due_date),
                "amount": currency(work_order.estimated_cost),
                "risk_score": None,
                "note": "Urgent maintenance overdue" if overdue else "Open high-priority work order",
                "updated_at": to_iso(work_order.updated_at),
            }
            facilities_items.append(item)
            all_feed_items.append(item)

        for inspection in inspections.order_by("-scheduled_date", "-updated_at")[:10]:
            severity = "high"
            if inspection.risk_level == Inspection.RiskLevel.CRITICAL:
                severity = "critical"
            elif inspection.risk_level == Inspection.RiskLevel.HIGH:
                severity = "high"
            elif inspection.risk_level == Inspection.RiskLevel.MEDIUM:
                severity = "medium"
            item = {
                "id": f"facilities-insp-{inspection.id}",
                "module": "facilities",
                "module_label": "Facilities",
                "alert_type": "inspection",
                "title": inspection.title,
                "subject": getattr(inspection.property, "name", ""),
                "severity": severity,
                "status": inspection.status,
                "owner": inspection.inspector or "Facilities QA",
                "due_date": to_iso(inspection.scheduled_date),
                "amount": None,
                "risk_score": None,
                "note": "Corrective action required"
                if inspection.corrective_action_required
                else "Compliance review required",
                "updated_at": to_iso(inspection.updated_at),
            }
            facilities_items.append(item)
            all_feed_items.append(item)

        for service_request in service_requests.order_by("-created_at")[:10]:
            severity = "critical" if service_request.priority == ServiceRequest.Priority.URGENT else "high"
            item = {
                "id": f"facilities-sr-{service_request.id}",
                "module": "facilities",
                "module_label": "Facilities",
                "alert_type": "service_request",
                "title": service_request.title,
                "subject": getattr(service_request.property, "name", ""),
                "severity": severity,
                "status": service_request.status,
                "owner": service_request.assigned_to or service_request.requested_by,
                "due_date": None,
                "amount": None,
                "risk_score": None,
                "note": "Occupant service risk",
                "updated_at": to_iso(service_request.updated_at),
            }
            facilities_items.append(item)
            all_feed_items.append(item)

        feeds["facilities"]["summary"] = {
            "urgent_or_high_work_orders": open_work_orders.count(),
            "high_risk_or_non_compliant_inspections": inspections.count(),
            "urgent_or_high_service_requests": service_requests.count(),
            "overdue_urgent_work_orders": open_work_orders.filter(
                priority=WorkOrder.Priority.URGENT,
                due_date__isnull=False,
                due_date__lt=today,
            ).count(),
        }
        feeds["facilities"]["items"] = facilities_items
        feeds["facilities"]["last_event_at"] = to_iso(facilities_last_event)
    except (ProgrammingError, OperationalError):
        pass
    except Exception:
        pass
    apply_counts(feeds["facilities"], facilities_counts)

    # --- CRM risk feed ---
    crm_counts = empty_severity()
    try:
        from apps.crm.models import Lead, LeadFinancialAssessment

        risky_assessments = LeadFinancialAssessment.objects.filter(
            lead__organization_id=organization_id,
            status__in=[
                LeadFinancialAssessment.Status.PENDING,
                LeadFinancialAssessment.Status.IN_PROGRESS,
                LeadFinancialAssessment.Status.COMPLETED,
            ],
            risk_level__in=[
                LeadFinancialAssessment.RiskLevel.HIGH,
                LeadFinancialAssessment.RiskLevel.CRITICAL,
            ],
        ).select_related("lead")

        stale_leads = Lead.objects.filter(
            organization_id=organization_id,
            status=Lead.Status.ACTIVE,
        ).filter(
            Q(priority__in=[Lead.Priority.HIGH, Lead.Priority.URGENT])
            | Q(inquiry_date__lte=today - timedelta(days=30))
        ).select_related("assigned_to", "source")

        for row in risky_assessments.values("risk_level").annotate(count=Count("id")).order_by():
            severity = "critical" if row["risk_level"] == LeadFinancialAssessment.RiskLevel.CRITICAL else "high"
            crm_counts[severity] += int(row["count"] or 0)

        stale_critical = 0
        stale_high = 0
        stale_medium = 0
        for lead in stale_leads:
            age_days = max((today - lead.inquiry_date).days, 0)
            if age_days >= 60 or (
                lead.priority == Lead.Priority.URGENT and age_days >= 21
            ):
                stale_critical += 1
            elif age_days >= 30 or lead.priority in [Lead.Priority.HIGH, Lead.Priority.URGENT]:
                stale_high += 1
            else:
                stale_medium += 1
        crm_counts["critical"] += stale_critical
        crm_counts["high"] += stale_high
        crm_counts["medium"] += stale_medium

        crm_last_event = max_dt(
            risky_assessments.aggregate(last_event=Max("updated_at")).get("last_event"),
            stale_leads.aggregate(last_event=Max("updated_at")).get("last_event"),
        )
        resolved_last_7d += Lead.objects.filter(
            organization_id=organization_id,
            status__in=[Lead.Status.WON, Lead.Status.LOST],
            closed_date__gte=today - timedelta(days=7),
        ).count()

        crm_items = []
        for assessment in risky_assessments.order_by("-risk_score", "-updated_at")[:12]:
            severity = (
                "critical"
                if assessment.risk_level == LeadFinancialAssessment.RiskLevel.CRITICAL
                else "high"
            )
            lead = assessment.lead
            item = {
                "id": f"crm-assessment-{assessment.id}",
                "module": "crm",
                "module_label": "CRM",
                "alert_type": "financial_assessment",
                "title": lead.full_name,
                "subject": f"{lead.get_pipeline_stage_display()} stage",
                "severity": severity,
                "status": assessment.status,
                "owner": lead.assigned_to.get_full_name() if lead.assigned_to_id else "",
                "due_date": to_iso(assessment.assessment_date),
                "amount": None,
                "risk_score": int(assessment.risk_score or 0),
                "note": "High financing risk profile",
                "updated_at": to_iso(assessment.updated_at),
            }
            crm_items.append(item)
            all_feed_items.append(item)

        for lead in stale_leads.order_by("inquiry_date", "-updated_at")[:12]:
            age_days = max((today - lead.inquiry_date).days, 0)
            if age_days >= 60 or (lead.priority == Lead.Priority.URGENT and age_days >= 21):
                severity = "critical"
            elif age_days >= 30 or lead.priority in [Lead.Priority.HIGH, Lead.Priority.URGENT]:
                severity = "high"
            else:
                severity = "medium"
            owner = ""
            if lead.assigned_to_id:
                owner = lead.assigned_to.get_full_name() or lead.assigned_to.username
            source_name = lead.source.name if lead.source_id else "Inbound"
            item = {
                "id": f"crm-lead-{lead.id}",
                "module": "crm",
                "module_label": "CRM",
                "alert_type": "pipeline_stall",
                "title": lead.full_name,
                "subject": source_name,
                "severity": severity,
                "status": lead.pipeline_stage,
                "owner": owner,
                "due_date": to_iso(lead.inquiry_date),
                "amount": None,
                "risk_score": None,
                "note": f"{age_days} days in pipeline",
                "updated_at": to_iso(lead.updated_at),
            }
            crm_items.append(item)
            all_feed_items.append(item)

        feeds["crm"]["summary"] = {
            "active_leads": Lead.objects.filter(
                organization_id=organization_id,
                status=Lead.Status.ACTIVE,
            ).count(),
            "high_risk_assessments": risky_assessments.count(),
            "stale_priority_leads": stale_leads.count(),
            "critical_assessments": risky_assessments.filter(
                risk_level=LeadFinancialAssessment.RiskLevel.CRITICAL
            ).count(),
        }
        feeds["crm"]["items"] = crm_items
        feeds["crm"]["last_event_at"] = to_iso(crm_last_event)
    except (ProgrammingError, OperationalError):
        pass
    except Exception:
        pass
    apply_counts(feeds["crm"], crm_counts)

    global_counts = empty_severity()
    for feed in feeds.values():
        global_counts["critical"] += int(feed["critical_alerts"])
        global_counts["high"] += int(feed["high_alerts"])
        global_counts["medium"] += int(feed["medium_alerts"])
        global_counts["low"] += int(feed["low_alerts"])

    module_totals = []
    for module_key in [
        "projects",
        "workflows",
        "finance",
        "procurement",
        "facilities",
        "crm",
    ]:
        feed = feeds[module_key]
        module_totals.append(
            {
                "module": module_key,
                "label": feed["label"],
                "open_alerts": feed["open_alerts"],
                "critical_alerts": feed["critical_alerts"],
                "high_alerts": feed["high_alerts"],
                "medium_alerts": feed["medium_alerts"],
                "low_alerts": feed["low_alerts"],
            }
        )

    # ── Acknowledgement overlay ─────────────────────────────────────────
    from .models import RiskAlertAcknowledgement

    ack_map = {}
    ack_qs = RiskAlertAcknowledgement.objects.filter(
        organization_id=organization_id,
    ).select_related("assigned_to", "updated_by")
    for ack in ack_qs:
        assigned_user = ack.assigned_to
        updated_user = ack.updated_by
        ack_map[ack.alert_id] = {
            "status": ack.status,
            "assigned_to": assigned_user.id if assigned_user else None,
            "assigned_to_name": (
                (assigned_user.get_full_name() or assigned_user.username or assigned_user.email)
                if assigned_user
                else None
            ),
            "note": ack.note or "",
            "acknowledged_at": to_iso(ack.acknowledged_at),
            "resolved_at": to_iso(ack.resolved_at),
            "updated_by_name": (
                (updated_user.get_full_name() or updated_user.username or updated_user.email)
                if updated_user
                else None
            ),
            "updated_at": to_iso(ack.updated_at),
        }

    acknowledged_count = 0
    resolved_count = 0
    for item in all_feed_items:
        ack_entry = ack_map.get(item.get("id"))
        item["acknowledgement"] = ack_entry
        if ack_entry is not None:
            if ack_entry["status"] == "acknowledged":
                acknowledged_count += 1
            elif ack_entry["status"] == "resolved":
                resolved_count += 1

    recent_alerts = sorted(
        all_feed_items,
        key=lambda item: (
            severity_order.get(clamp_severity(item.get("severity")), 2),
            item.get("due_date") or "9999-12-31",
            item.get("module") or "",
            item.get("title") or "",
        ),
    )[:80]

    total_open = sum(feed["open_alerts"] for feed in feeds.values())
    modules_affected = sum(1 for feed in feeds.values() if feed["open_alerts"] > 0)

    return {
        "generated_at": now.isoformat(),
        "overview": {
            "total_open_alerts": total_open,
            "critical_alerts": global_counts["critical"],
            "high_alerts": global_counts["high"],
            "medium_alerts": global_counts["medium"],
            "low_alerts": global_counts["low"],
            "watch_alerts": global_counts["high"] + global_counts["medium"],
            "resolved_last_7_days": resolved_last_7d,
            "modules_affected": modules_affected,
            "acknowledged_alerts": acknowledged_count,
            "resolved_alerts": resolved_count,
        },
        "severity_distribution": global_counts,
        "module_totals": module_totals,
        "feeds": feeds,
        "recent_alerts": recent_alerts,
    }


def compute_full_portfolio_snapshot(organization_id):
    """Compute all portfolio metrics for one org. Returns dict matching PortfolioSnapshot fields."""
    qs = get_active_properties(organization_id)
    kpis = compute_portfolio_kpis(qs)
    return {
        "total_value": Decimal(kpis["total_value"]),
        "total_acquisition": Decimal(kpis["total_acquisition"]),
        "property_count": kpis["property_count"],
        "total_area_sqft": Decimal(kpis["total_area_sqft"]),
        "avg_price_per_sqft": Decimal(kpis["avg_price_per_sqft"]),
        "unrealized_gain": Decimal(kpis["unrealized_gain"]),
        "type_distribution": compute_type_distribution(qs),
        "classification_breakdown": compute_classification_breakdown(qs),
        "valuation_history": compute_valuation_history(organization_id),
        "unit_occupancy": compute_unit_occupancy(qs),
        "project_budget_summary": compute_project_budget_summary(organization_id),
        "top_appreciating": compute_top_properties(qs, ascending=False),
        "top_depreciating": compute_top_properties(qs, ascending=True),
        "encumbrance_summary": compute_encumbrance_summary(qs),
    }


# ── Board KPIs ───────────────────────────────────────────────────────────


def compute_procurement_cycle_time(start_date, end_date, organization_id):
    qs = PurchaseOrder.objects.filter(
        organization_id=organization_id,
        requisition__isnull=False,
        issue_date__gte=start_date,
        issue_date__lte=end_date,
    ).select_related("requisition")

    durations = []
    for po in qs:
        if not po.requisition or not po.requisition.created_at:
            continue
        delta = (po.issue_date - po.requisition.created_at.date()).days
        if delta >= 0:
            durations.append(delta)

    avg_days = round(sum(durations) / len(durations), 2) if durations else 0.0
    return {
        "value": avg_days,
        "sample_size": len(durations),
        "unit": "days",
    }


def compute_cost_variance(organization_id):
    qs = Project.objects.exclude(status=Project.Status.COMPLETED).filter(
        organization_id=organization_id,
    )
    projects = qs.annotate(
        total_planned=Coalesce(Sum("phases__planned_budget"), Decimal("0")),
        total_actual=Coalesce(Sum("phases__cost_entries__amount"), Decimal("0")),
    )

    variances = []
    over_budget = 0
    for project in projects:
        planned = project.total_planned or Decimal("0")
        actual = project.total_actual or Decimal("0")
        if planned <= 0:
            continue
        pct = float((actual - planned) / planned * Decimal("100"))
        variances.append(pct)
        if actual > planned:
            over_budget += 1

    avg_pct = round(sum(variances) / len(variances), 2) if variances else 0.0
    return {
        "value": avg_pct,
        "project_count": len(variances),
        "over_budget_projects": over_budget,
        "unit": "percentage",
    }


def compute_vendor_reliability(organization_id):
    vendors = Vendor.objects.filter(
        is_active=True,
        organization_id=organization_id,
    )

    compliance_score_map = {
        Vendor.ComplianceStatus.COMPLIANT: 100.0,
        Vendor.ComplianceStatus.PENDING_REVIEW: 60.0,
        Vendor.ComplianceStatus.NON_COMPLIANT: 25.0,
        Vendor.ComplianceStatus.EXPIRED: 0.0,
    }

    scores = []
    for vendor in vendors:
        performance = float((vendor.performance_rating or Decimal("0")) / Decimal("5") * Decimal("100"))
        timeliness = float(vendor.delivery_timeliness_score or Decimal("0"))
        compliance = compliance_score_map.get(vendor.compliance_status, 50.0)
        score = (0.45 * performance) + (0.45 * timeliness) + (0.10 * compliance)
        if vendor.is_blacklisted:
            score = min(score, 20.0)
        scores.append(score)

    avg_score = round(sum(scores) / len(scores), 2) if scores else 0.0
    return {
        "value": avg_score,
        "vendor_count": len(scores),
        "unit": "score_0_100",
    }


def compute_emergency_purchases(start_date, end_date, organization_id):
    requisitions = PurchaseRequisition.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
    ).exclude(status=PurchaseRequisition.Status.CANCELLED)

    requisitions = requisitions.filter(organization_id=organization_id)

    total = requisitions.count()
    urgent = requisitions.filter(
        priority=PurchaseRequisition.Priority.URGENT
    ).count()
    pct = round((urgent / total) * 100, 2) if total else 0.0
    return {
        "value": pct,
        "emergency_count": urgent,
        "total_requisitions": total,
        "unit": "percentage",
    }


def compute_budget_overrun(organization_id):
    budgets = Budget.objects.filter(
        status=Budget.Status.ACTIVE,
        organization_id=organization_id,
    ).prefetch_related("line_items__account")

    tracked = 0
    overruns = 0
    for budget in budgets:
        tolerance = (budget.overspend_tolerance_pct or Decimal("0")) / Decimal("100")
        allowed_multiplier = Decimal("1") + tolerance
        for item in budget.line_items.all():
            if (item.budgeted_amount or Decimal("0")) <= 0:
                continue
            tracked += 1
            actual = get_actual_spent(item)
            if actual > (item.budgeted_amount * allowed_multiplier):
                overruns += 1

    frequency = round((overruns / tracked) * 100, 2) if tracked else 0.0
    return {
        "value": frequency,
        "overrun_items": overruns,
        "tracked_items": tracked,
        "unit": "percentage",
    }


def compute_approval_time(start_date, end_date, organization_id):
    workflows = WorkflowInstance.objects.filter(
        submitted_at__isnull=False,
        completed_at__isnull=False,
        submitted_at__date__gte=start_date,
        submitted_at__date__lte=end_date,
        state__in=[
            WorkflowInstance.State.APPROVED,
            WorkflowInstance.State.REJECTED,
        ],
        template__organization_id=organization_id,
    )

    durations = []
    for instance in workflows:
        if not instance.submitted_at or not instance.completed_at:
            continue
        delta = instance.completed_at - instance.submitted_at
        hours = delta.total_seconds() / 3600.0
        if hours >= 0:
            durations.append(hours)

    avg_hours = round(sum(durations) / len(durations), 2) if durations else 0.0
    return {
        "value": avg_hours,
        "completed_workflows": len(durations),
        "unit": "hours",
    }


def compute_full_board_kpis(organization_id, start_date, end_date):
    """Compute all board KPIs for one org + period. Returns dict matching BoardKpiSnapshot fields."""
    return {
        "procurement_cycle_time_days": compute_procurement_cycle_time(start_date, end_date, organization_id),
        "cost_variance_per_project_pct": compute_cost_variance(organization_id),
        "vendor_reliability_score": compute_vendor_reliability(organization_id),
        "emergency_purchases_pct": compute_emergency_purchases(start_date, end_date, organization_id),
        "budget_overrun_frequency_pct": compute_budget_overrun(organization_id),
        "average_approval_time_hours": compute_approval_time(start_date, end_date, organization_id),
        "period_start": start_date,
        "period_end": end_date,
    }
