"""
Drilldown computation functions for board KPI detail views.

Each function returns richer detail data for a specific board KPI,
complementing the summary values from computations.py.
No request objects — accepts org_id and date params.
"""

import statistics
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce, TruncMonth

from apps.finance.budget_utils import get_actual_spent
from apps.finance.models import Budget
from apps.procurement.models import PurchaseOrder, PurchaseRequisition, Vendor
from apps.projects.models import Project
from apps.workflows.models import WorkflowInstance


def drilldown_procurement_cycle_time(start_date, end_date, organization_id):
    """
    Duration histogram, top 10 slowest POs, and statistical summary.
    """
    qs = PurchaseOrder.objects.filter(
        organization_id=organization_id,
        requisition__isnull=False,
        issue_date__gte=start_date,
        issue_date__lte=end_date,
    ).select_related("requisition", "vendor")

    records = []
    for po in qs:
        if not po.requisition or not po.requisition.created_at:
            continue
        days = (po.issue_date - po.requisition.created_at.date()).days
        if days >= 0:
            records.append(
                {
                    "po_number": po.po_number,
                    "vendor": po.vendor.name if po.vendor else "",
                    "duration_days": days,
                    "issue_date": po.issue_date.isoformat(),
                    "requisition_date": po.requisition.created_at.date().isoformat(),
                }
            )

    durations = [r["duration_days"] for r in records]

    # Histogram buckets
    buckets = [
        ("0-5", 0, 5),
        ("6-10", 6, 10),
        ("11-15", 11, 15),
        ("16-20", 16, 20),
        ("21-30", 21, 30),
        ("31+", 31, None),
    ]
    histogram = []
    for label, lo, hi in buckets:
        count = sum(
            1
            for d in durations
            if d >= lo and (hi is None or d <= hi)
        )
        histogram.append({"bucket": label, "count": count})

    # Slowest POs (top 10)
    slowest = sorted(records, key=lambda r: r["duration_days"], reverse=True)[:10]

    # Statistics
    if durations:
        sorted_d = sorted(durations)
        p90_idx = int(len(sorted_d) * 0.9)
        summary = {
            "median_days": round(statistics.median(durations), 1),
            "p90_days": sorted_d[min(p90_idx, len(sorted_d) - 1)],
            "min_days": sorted_d[0],
            "max_days": sorted_d[-1],
        }
    else:
        summary = {"median_days": 0, "p90_days": 0, "min_days": 0, "max_days": 0}

    return {"histogram": histogram, "slowest_pos": slowest, "summary": summary}


def drilldown_cost_variance(organization_id):
    """
    Per-project cost variance breakdown.

    Date-window agnostic by design: variance is the cumulative position of
    each active Project (planned vs. actual across all phases), not a stream
    of date-stamped events. The board-metrics date filter is intentionally
    not threaded through this function.
    """
    projects = (
        Project.objects.exclude(status=Project.Status.COMPLETED)
        .filter(organization_id=organization_id)
        .annotate(
            total_planned=Coalesce(Sum("phases__planned_budget"), Decimal("0")),
            total_actual=Coalesce(Sum("phases__cost_entries__amount"), Decimal("0")),
        )
        .order_by("name")
    )

    per_project = []
    over_budget = []
    total_planned_sum = Decimal("0")
    total_actual_sum = Decimal("0")

    for p in projects:
        planned = p.total_planned or Decimal("0")
        actual = p.total_actual or Decimal("0")
        if planned <= 0:
            continue
        variance_pct = round(float((actual - planned) / planned * Decimal("100")), 2)
        item = {
            "id": p.id,
            "name": p.name,
            "planned": str(planned),
            "actual": str(actual),
            "variance_pct": variance_pct,
        }
        per_project.append(item)
        if actual > planned:
            over_budget.append(item)
        total_planned_sum += planned
        total_actual_sum += actual

    per_project.sort(key=lambda x: x["variance_pct"], reverse=True)
    variances = [x["variance_pct"] for x in per_project]

    return {
        "per_project": per_project,
        "over_budget_projects": over_budget,
        "summary": {
            "worst_variance_pct": max(variances) if variances else 0,
            "best_variance_pct": min(variances) if variances else 0,
            "total_planned": str(total_planned_sum),
            "total_actual": str(total_actual_sum),
        },
    }


def drilldown_vendor_reliability(organization_id):
    """
    Top/bottom vendors, score distribution histogram.

    Date-window agnostic by design: the score is computed from each Vendor's
    current performance_rating, delivery_timeliness_score, and
    compliance_status — current-state fields, not historical events. The
    board-metrics date filter is intentionally not threaded through here.
    """
    vendors = (
        Vendor.objects.filter(
            is_active=True,
            organization_id=organization_id,
        )
        .annotate(po_count=Count("purchase_orders", distinct=True))
    )

    compliance_map = {
        Vendor.ComplianceStatus.COMPLIANT: 100.0,
        Vendor.ComplianceStatus.PENDING_REVIEW: 60.0,
        Vendor.ComplianceStatus.NON_COMPLIANT: 25.0,
        Vendor.ComplianceStatus.EXPIRED: 0.0,
    }

    scored = []
    for v in vendors:
        performance = float(
            (v.performance_rating or Decimal("0")) / Decimal("5") * Decimal("100")
        )
        timeliness = float(v.delivery_timeliness_score or Decimal("0"))
        compliance = compliance_map.get(v.compliance_status, 50.0)
        score = (0.45 * performance) + (0.45 * timeliness) + (0.10 * compliance)
        if v.is_blacklisted:
            score = min(score, 20.0)
        scored.append(
            {
                "id": v.id,
                "name": v.name,
                "score": round(score, 2),
                "performance": round(performance, 1),
                "timeliness": round(timeliness, 1),
                "compliance": v.compliance_status,
                "po_count": v.po_count,
            }
        )

    scored.sort(key=lambda x: x["score"], reverse=True)
    top_vendors = scored[:10]
    bottom_vendors = list(reversed(scored[-10:])) if len(scored) > 10 else list(reversed(scored))

    # Score distribution histogram
    score_buckets = [
        ("0-20", 0, 20),
        ("21-40", 21, 40),
        ("41-60", 41, 60),
        ("61-80", 61, 80),
        ("81-100", 81, 100),
    ]
    all_scores = [s["score"] for s in scored]
    histogram = []
    for label, lo, hi in score_buckets:
        count = sum(1 for s in all_scores if lo <= s <= hi)
        histogram.append({"bucket": label, "count": count})

    median_score = round(statistics.median(all_scores), 1) if all_scores else 0

    return {
        "top_vendors": top_vendors,
        "bottom_vendors": bottom_vendors,
        "score_distribution": histogram,
        "summary": {"median_score": median_score, "vendor_count": len(scored)},
    }


def drilldown_emergency_purchases(start_date, end_date, organization_id):
    """
    Monthly emergency purchase trend, by-project breakdown, recent emergencies.
    """
    base_qs = (
        PurchaseRequisition.objects.filter(
            organization_id=organization_id,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
        )
        .exclude(status=PurchaseRequisition.Status.CANCELLED)
    )

    # Monthly trend
    monthly = (
        base_qs.annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(
            total=Count("id"),
            emergency=Count(
                "id", filter=Q(priority=PurchaseRequisition.Priority.URGENT)
            ),
        )
        .order_by("month")
    )
    trend = []
    for m in monthly:
        pct = round((m["emergency"] / m["total"]) * 100, 2) if m["total"] else 0
        trend.append(
            {
                "month": m["month"].strftime("%Y-%m"),
                "total": m["total"],
                "emergency": m["emergency"],
                "pct": pct,
            }
        )

    # By project breakdown
    by_project = (
        base_qs.filter(project__isnull=False)
        .values("project__name")
        .annotate(
            total=Count("id"),
            emergency=Count(
                "id", filter=Q(priority=PurchaseRequisition.Priority.URGENT)
            ),
        )
        .order_by("-emergency")[:10]
    )
    by_category = []
    for row in by_project:
        pct = (
            round((row["emergency"] / row["total"]) * 100, 2) if row["total"] else 0
        )
        by_category.append(
            {
                "category": row["project__name"],
                "total": row["total"],
                "emergency": row["emergency"],
                "pct": pct,
            }
        )

    # Recent emergencies
    recent = (
        base_qs.filter(priority=PurchaseRequisition.Priority.URGENT)
        .select_related("project")
        .order_by("-created_at")[:10]
    )
    recent_list = [
        {
            "pr_number": pr.pr_number,
            "title": pr.title,
            "requester": pr.requester or "",
            "created_at": pr.created_at.isoformat(),
            "project": pr.project.name if pr.project else None,
        }
        for pr in recent
    ]

    return {
        "trend": trend,
        "by_category": by_category,
        "recent_emergencies": recent_list,
    }


def drilldown_budget_overrun(organization_id):
    """
    Per-budget overrun breakdown and worst offending line items.

    Date-window agnostic by design: each active Budget brings its own period
    (set on the Budget record) and the line-item actuals are lifetime totals
    via ``get_actual_spent``. The board-metrics date filter is intentionally
    not threaded through here.
    """
    budgets = (
        Budget.objects.filter(
            status=Budget.Status.ACTIVE,
            organization_id=organization_id,
        )
        .prefetch_related("line_items__account")
    )

    per_budget = []
    worst_items = []
    total_budgeted = Decimal("0")
    total_actual = Decimal("0")

    for budget in budgets:
        tolerance = (budget.overspend_tolerance_pct or Decimal("0")) / Decimal("100")
        allowed = Decimal("1") + tolerance
        tracked = 0
        overruns = 0

        for item in budget.line_items.all():
            budgeted = item.budgeted_amount or Decimal("0")
            if budgeted <= 0:
                continue
            tracked += 1
            actual = get_actual_spent(item)
            total_budgeted += budgeted
            total_actual += actual

            if actual > (budgeted * allowed):
                overruns += 1
                overrun_pct = round(
                    float((actual - budgeted) / budgeted * Decimal("100")), 2
                )
                worst_items.append(
                    {
                        "budget_name": budget.name,
                        "account_code": item.account.code if item.account else "",
                        "account_name": item.account.name if item.account else "",
                        "budgeted": str(budgeted),
                        "actual": str(actual),
                        "overrun_pct": overrun_pct,
                    }
                )

        freq = round((overruns / tracked) * 100, 2) if tracked else 0
        per_budget.append(
            {
                "id": budget.id,
                "name": budget.name,
                "tracked_items": tracked,
                "overrun_items": overruns,
                "frequency_pct": freq,
            }
        )

    worst_items.sort(key=lambda x: x["overrun_pct"], reverse=True)

    return {
        "per_budget": per_budget,
        "worst_line_items": worst_items[:10],
        "summary": {
            "total_budgeted": str(total_budgeted),
            "total_actual": str(total_actual),
            "net_overrun": str(total_actual - total_budgeted),
        },
    }


def drilldown_approval_time(start_date, end_date, organization_id):
    """
    Approval time breakdown by workflow template and slowest individual approvals.
    """
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
    ).select_related("template")

    by_type = {}
    all_records = []

    for inst in workflows:
        if not inst.submitted_at or not inst.completed_at:
            continue
        hours = round(
            (inst.completed_at - inst.submitted_at).total_seconds() / 3600.0, 2
        )
        if hours < 0:
            continue

        template_name = inst.template.name if inst.template else "Unknown"
        if template_name not in by_type:
            by_type[template_name] = []
        by_type[template_name].append(hours)

        all_records.append(
            {
                "id": inst.id,
                "template_name": template_name,
                "submitted_at": inst.submitted_at.isoformat(),
                "completed_at": inst.completed_at.isoformat(),
                "hours": hours,
                "state": inst.state,
            }
        )

    # By workflow type
    by_workflow_type = []
    for name, hours_list in sorted(by_type.items()):
        by_workflow_type.append(
            {
                "template_name": name,
                "avg_hours": round(sum(hours_list) / len(hours_list), 2),
                "count": len(hours_list),
                "median_hours": round(statistics.median(hours_list), 2),
            }
        )

    # Slowest approvals
    slowest = sorted(all_records, key=lambda r: r["hours"], reverse=True)[:10]

    # Summary statistics
    all_hours = [r["hours"] for r in all_records]
    if all_hours:
        sorted_h = sorted(all_hours)
        p90_idx = int(len(sorted_h) * 0.9)
        summary = {
            "median_hours": round(statistics.median(all_hours), 2),
            "p90_hours": sorted_h[min(p90_idx, len(sorted_h) - 1)],
            "fastest_hours": sorted_h[0],
            "slowest_hours": sorted_h[-1],
        }
    else:
        summary = {
            "median_hours": 0,
            "p90_hours": 0,
            "fastest_hours": 0,
            "slowest_hours": 0,
        }

    return {
        "by_workflow_type": by_workflow_type,
        "slowest_approvals": slowest,
        "summary": summary,
    }
