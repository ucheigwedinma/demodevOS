from __future__ import annotations

from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Count, Q
from django.utils import timezone

from .models import Campaign, ContactDealLink, Lead, LeadActivity

ACTIVE_DEAL_STATUSES = {
    ContactDealLink.Status.ACTIVE,
    ContactDealLink.Status.ON_HOLD,
}
_CLOSED_WON_STAGE_ALIASES = {"closed won", "won"}
_PIPELINE_STAGE_LABELS = dict(Lead.PipelineStage.choices)


def _to_decimal(value, default: str = "0.00") -> Decimal:
    if value in (None, ""):
        return Decimal(default)
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal(default)


def _money(value: Decimal) -> str:
    return str(_to_decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _pct(numerator: float | int | Decimal, denominator: float | int | Decimal) -> float:
    denominator_val = float(denominator or 0)
    if denominator_val <= 0:
        return 0.0
    return round((float(numerator or 0) / denominator_val) * 100, 1)


def _median(values: list[int]) -> float | None:
    if not values:
        return None
    sorted_values = sorted(values)
    midpoint = len(sorted_values) // 2
    if len(sorted_values) % 2:
        return float(sorted_values[midpoint])
    return round((sorted_values[midpoint - 1] + sorted_values[midpoint]) / 2, 1)


def _normalize_stage(value: str | None) -> str:
    if not value:
        return ""
    normalized = value.replace("_", " ").strip().lower()
    return " ".join(normalized.split())


def _is_closed_won_deal(deal: ContactDealLink) -> bool:
    if deal.status == ContactDealLink.Status.WON:
        return True
    return _normalize_stage(deal.stage) in _CLOSED_WON_STAGE_ALIASES


def _deal_value_for_reporting(deal: ContactDealLink) -> Decimal:
    if deal.deal_value is not None:
        return _to_decimal(deal.deal_value)
    if deal.reservation_id and getattr(deal.reservation, "total_price", None) is not None:
        return _to_decimal(deal.reservation.total_price)
    return Decimal("0.00")


def _agent_display_name(user_obj) -> str:
    if not user_obj:
        return "Unassigned"
    full_name = user_obj.get_full_name().strip()
    if full_name:
        return full_name
    return getattr(user_obj, "username", f"User {user_obj.id}")


def compute_crm_analytics_snapshot(
    *,
    organization_id: int | None,
    window_days: int = 90,
    pipeline_drop_lookback_days: int = 7,
) -> dict:
    now = timezone.now()
    window_days = min(max(int(window_days or 90), 30), 365)
    pipeline_drop_lookback_days = min(max(int(pipeline_drop_lookback_days or 7), 3), 30)

    cutoff_dt = now - timedelta(days=window_days)
    cutoff_date = cutoff_dt.date()

    lead_scope = Q(is_archived=False)
    deal_scope = Q()
    activity_scope = Q(created_at__gte=cutoff_dt, lead__assigned_to__isnull=False)
    if organization_id is not None:
        lead_scope &= Q(organization_id=organization_id)
        deal_scope &= Q(contact__organization_id=organization_id)
        activity_scope &= Q(lead__organization_id=organization_id)

    lead_base_qs = Lead.objects.filter(lead_scope).select_related("source", "assigned_to")
    leads_all = list(lead_base_qs)
    leads_window = list(
        lead_base_qs.filter(
            Q(created_at__gte=cutoff_dt)
            | Q(updated_at__gte=cutoff_dt)
            | Q(inquiry_date__gte=cutoff_date)
            | Q(closed_date__gte=cutoff_date)
        )
    )
    lead_window_ids = {lead.id for lead in leads_window}

    deals = list(
        ContactDealLink.objects.filter(deal_scope)
        .select_related("lead", "lead__source", "lead__assigned_to", "reservation")
    )
    campaign_scope = Q(
        Q(created_at__gte=cutoff_dt)
        | Q(updated_at__gte=cutoff_dt)
        | Q(started_at__gte=cutoff_dt)
        | Q(completed_at__gte=cutoff_dt)
    )
    if organization_id is not None:
        campaign_scope &= Q(organization_id=organization_id)
    campaigns = list(Campaign.objects.filter(campaign_scope))

    # ------------------------------------------------------------------
    # Conversion rates
    # ------------------------------------------------------------------
    total_leads = len(leads_window)
    active_leads = sum(1 for lead in leads_window if lead.status == Lead.Status.ACTIVE)
    won_leads = sum(1 for lead in leads_window if lead.status == Lead.Status.WON)
    lost_leads = sum(1 for lead in leads_window if lead.status == Lead.Status.LOST)
    disqualified_leads = sum(1 for lead in leads_window if lead.status == Lead.Status.DISQUALIFIED)

    qualified_or_beyond = sum(
        1
        for lead in leads_window
        if lead.pipeline_stage
        in {
            Lead.PipelineStage.QUALIFIED,
            Lead.PipelineStage.SITE_VISIT,
            Lead.PipelineStage.OFFER_MADE,
            Lead.PipelineStage.RESERVATION,
            Lead.PipelineStage.SPA_ISSUED,
            Lead.PipelineStage.CLOSED,
        }
    )
    closed_outcomes = won_leads + lost_leads + disqualified_leads

    stage_pairs = [
        (
            "inquiry_date",
            "qualified_date",
            Lead.PipelineStage.INQUIRY,
            Lead.PipelineStage.QUALIFIED,
        ),
        (
            "qualified_date",
            "site_visit_date",
            Lead.PipelineStage.QUALIFIED,
            Lead.PipelineStage.SITE_VISIT,
        ),
        (
            "site_visit_date",
            "offer_date",
            Lead.PipelineStage.SITE_VISIT,
            Lead.PipelineStage.OFFER_MADE,
        ),
        (
            "offer_date",
            "reservation_date",
            Lead.PipelineStage.OFFER_MADE,
            Lead.PipelineStage.RESERVATION,
        ),
        (
            "reservation_date",
            "spa_issued_date",
            Lead.PipelineStage.RESERVATION,
            Lead.PipelineStage.SPA_ISSUED,
        ),
        (
            "spa_issued_date",
            "closed_date",
            Lead.PipelineStage.SPA_ISSUED,
            Lead.PipelineStage.CLOSED,
        ),
    ]
    stage_conversion = []
    for from_field, to_field, from_stage, to_stage in stage_pairs:
        eligible = 0
        progressed = 0
        durations: list[int] = []
        for lead in leads_window:
            from_date = getattr(lead, from_field)
            if not from_date:
                continue
            eligible += 1
            to_date = getattr(lead, to_field)
            if not to_date or to_date < from_date:
                continue
            progressed += 1
            durations.append((to_date - from_date).days)

        avg_days = round(sum(durations) / len(durations), 1) if durations else None
        stage_conversion.append(
            {
                "from_stage": from_stage,
                "to_stage": to_stage,
                "label": f"{_PIPELINE_STAGE_LABELS[from_stage]} -> {_PIPELINE_STAGE_LABELS[to_stage]}",
                "eligible_count": eligible,
                "progressed_count": progressed,
                "conversion_rate": _pct(progressed, eligible),
                "avg_days_to_progress": avg_days,
            }
        )

    # ------------------------------------------------------------------
    # Sales velocity
    # ------------------------------------------------------------------
    closed_won_in_window = [
        lead
        for lead in leads_all
        if lead.status == Lead.Status.WON and lead.closed_date and lead.closed_date >= cutoff_date
    ]
    close_durations = [
        max((lead.closed_date - lead.inquiry_date).days, 0)
        for lead in closed_won_in_window
        if lead.inquiry_date and lead.closed_date
    ]
    avg_days_to_close = round(sum(close_durations) / len(close_durations), 1) if close_durations else None
    median_days_to_close = _median(close_durations)
    deals_per_month = round((len(closed_won_in_window) / window_days) * 30, 2) if window_days else 0.0

    stage_durations = []
    for from_field, to_field, from_stage, to_stage in stage_pairs:
        durations: list[int] = []
        for lead in leads_window:
            from_date = getattr(lead, from_field)
            to_date = getattr(lead, to_field)
            if not from_date or not to_date or to_date < from_date:
                continue
            durations.append((to_date - from_date).days)
        stage_durations.append(
            {
                "label": f"{_PIPELINE_STAGE_LABELS[from_stage]} -> {_PIPELINE_STAGE_LABELS[to_stage]}",
                "from_stage": from_stage,
                "to_stage": to_stage,
                "avg_days": round(sum(durations) / len(durations), 1) if durations else None,
                "sample_size": len(durations),
            }
        )

    # ------------------------------------------------------------------
    # Revenue forecast
    # ------------------------------------------------------------------
    pipeline_value = Decimal("0.00")
    weighted_forecast = Decimal("0.00")
    closed_won_value = Decimal("0.00")
    active_deals = 0
    stage_buckets: dict[str, dict] = {}

    for deal in deals:
        deal_value = _deal_value_for_reporting(deal)
        probability = max(0, min(int(deal.close_probability or 0), 100))
        weighted_value = (deal_value * Decimal(probability) / Decimal("100")).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
        stage_label = (deal.stage or "").strip() or "Unstaged"

        bucket = stage_buckets.setdefault(
            stage_label,
            {
                "stage": stage_label,
                "count": 0,
                "deal_value": Decimal("0.00"),
                "weighted_value": Decimal("0.00"),
            },
        )
        bucket["count"] += 1
        bucket["deal_value"] += deal_value
        bucket["weighted_value"] += weighted_value

        if deal.status in ACTIVE_DEAL_STATUSES:
            active_deals += 1
            pipeline_value += deal_value
            weighted_forecast += weighted_value
        if _is_closed_won_deal(deal):
            closed_won_value += deal_value

    stage_breakdown = sorted(
        stage_buckets.values(),
        key=lambda row: (-_to_decimal(row["deal_value"]), str(row["stage"]).lower()),
    )
    for row in stage_breakdown:
        row["deal_value"] = _money(row["deal_value"])
        row["weighted_value"] = _money(row["weighted_value"])

    # ------------------------------------------------------------------
    # Lead source performance
    # ------------------------------------------------------------------
    source_map: dict[int, dict] = {}

    def _source_row(source_id: int | None, source_name: str) -> dict:
        return {
            "source_id": source_id,
            "source_name": source_name,
            "total_leads": 0,
            "active_leads": 0,
            "won_leads": 0,
            "lost_leads": 0,
            "disqualified_leads": 0,
            "average_score": 0.0,
            "score_sum": 0.0,
            "deal_count": 0,
            "pipeline_value": Decimal("0.00"),
            "weighted_forecast": Decimal("0.00"),
            "closed_won_value": Decimal("0.00"),
        }

    for lead in leads_window:
        source_id = lead.source_id
        source_name = lead.source.name if lead.source_id else "Unattributed"
        row = source_map.setdefault(source_id or 0, _source_row(source_id, source_name))
        row["total_leads"] += 1
        row["score_sum"] += float(lead.score or 0)
        if lead.status == Lead.Status.ACTIVE:
            row["active_leads"] += 1
        elif lead.status == Lead.Status.WON:
            row["won_leads"] += 1
        elif lead.status == Lead.Status.LOST:
            row["lost_leads"] += 1
        elif lead.status == Lead.Status.DISQUALIFIED:
            row["disqualified_leads"] += 1

    for deal in deals:
        lead = deal.lead
        if not lead:
            continue
        include = lead.id in lead_window_ids or (deal.linked_at and deal.linked_at >= cutoff_dt)
        if not include:
            continue
        source_id = lead.source_id
        source_name = lead.source.name if lead.source_id else "Unattributed"
        row = source_map.setdefault(source_id or 0, _source_row(source_id, source_name))
        deal_value = _deal_value_for_reporting(deal)
        probability = max(0, min(int(deal.close_probability or 0), 100))
        weighted_value = (deal_value * Decimal(probability) / Decimal("100")).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
        row["deal_count"] += 1
        if deal.status in ACTIVE_DEAL_STATUSES:
            row["pipeline_value"] += deal_value
            row["weighted_forecast"] += weighted_value
        if _is_closed_won_deal(deal):
            row["closed_won_value"] += deal_value

    lead_source_performance = []
    for row in source_map.values():
        total = row["total_leads"]
        row["conversion_rate"] = _pct(row["won_leads"], total)
        row["average_score"] = round((row["score_sum"] / total), 1) if total else 0.0
        row.pop("score_sum", None)
        row["pipeline_value"] = _money(row["pipeline_value"])
        row["weighted_forecast"] = _money(row["weighted_forecast"])
        row["closed_won_value"] = _money(row["closed_won_value"])
        lead_source_performance.append(row)
    lead_source_performance.sort(
        key=lambda row: (-row["total_leads"], -float(row["pipeline_value"]), row["source_name"].lower())
    )

    # ------------------------------------------------------------------
    # Agent performance
    # ------------------------------------------------------------------
    agent_map: dict[int, dict] = {}

    def _agent_row(agent_id: int, agent_name: str) -> dict:
        return {
            "agent_id": agent_id,
            "agent_name": agent_name,
            "total_leads": 0,
            "active_leads": 0,
            "won_leads": 0,
            "lost_leads": 0,
            "average_score": 0.0,
            "score_sum": 0.0,
            "days_in_pipeline_sum": 0.0,
            "days_in_pipeline_count": 0,
            "closed_duration_days": [],
            "deal_count": 0,
            "active_deals": 0,
            "won_deals": 0,
            "pipeline_value": Decimal("0.00"),
            "weighted_forecast": Decimal("0.00"),
            "activity_count": 0,
        }

    for lead in leads_window:
        if not lead.assigned_to_id:
            continue
        row = agent_map.setdefault(
            lead.assigned_to_id,
            _agent_row(lead.assigned_to_id, _agent_display_name(lead.assigned_to)),
        )
        row["total_leads"] += 1
        row["score_sum"] += float(lead.score or 0)
        row["days_in_pipeline_sum"] += float(lead.days_in_pipeline)
        row["days_in_pipeline_count"] += 1
        if lead.status == Lead.Status.ACTIVE:
            row["active_leads"] += 1
        elif lead.status == Lead.Status.WON:
            row["won_leads"] += 1
            if lead.inquiry_date and lead.closed_date:
                row["closed_duration_days"].append(max((lead.closed_date - lead.inquiry_date).days, 0))
        elif lead.status == Lead.Status.LOST:
            row["lost_leads"] += 1

    activity_counts = (
        LeadActivity.objects.filter(activity_scope)
        .values("lead__assigned_to")
        .annotate(count=Count("id"))
    )
    for row in activity_counts:
        agent_id = row["lead__assigned_to"]
        if not agent_id:
            continue
        if agent_id in agent_map:
            agent_map[agent_id]["activity_count"] = row["count"]

    for deal in deals:
        lead = deal.lead
        if not lead or not lead.assigned_to_id:
            continue
        include = lead.id in lead_window_ids or (deal.linked_at and deal.linked_at >= cutoff_dt)
        if not include:
            continue
        if lead.assigned_to_id not in agent_map:
            agent_map[lead.assigned_to_id] = _agent_row(
                lead.assigned_to_id,
                _agent_display_name(lead.assigned_to),
            )
        row = agent_map[lead.assigned_to_id]
        deal_value = _deal_value_for_reporting(deal)
        probability = max(0, min(int(deal.close_probability or 0), 100))
        weighted_value = (deal_value * Decimal(probability) / Decimal("100")).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
        row["deal_count"] += 1
        if deal.status in ACTIVE_DEAL_STATUSES:
            row["active_deals"] += 1
            row["pipeline_value"] += deal_value
            row["weighted_forecast"] += weighted_value
        if _is_closed_won_deal(deal):
            row["won_deals"] += 1

    agent_performance = []
    for row in agent_map.values():
        total = row["total_leads"]
        row["conversion_rate"] = _pct(row["won_leads"], total)
        row["average_score"] = round((row["score_sum"] / total), 1) if total else 0.0
        row["avg_days_in_pipeline"] = (
            round(row["days_in_pipeline_sum"] / row["days_in_pipeline_count"], 1)
            if row["days_in_pipeline_count"]
            else None
        )
        row["avg_days_to_close"] = (
            round(sum(row["closed_duration_days"]) / len(row["closed_duration_days"]), 1)
            if row["closed_duration_days"]
            else None
        )
        row.pop("score_sum", None)
        row.pop("days_in_pipeline_sum", None)
        row.pop("days_in_pipeline_count", None)
        row.pop("closed_duration_days", None)
        row["pipeline_value"] = _money(row["pipeline_value"])
        row["weighted_forecast"] = _money(row["weighted_forecast"])
        agent_performance.append(row)
    agent_performance.sort(
        key=lambda row: (
            -float(row["weighted_forecast"]),
            -row["won_leads"],
            row["agent_name"].lower(),
        )
    )

    # ------------------------------------------------------------------
    # Pipeline drop monitor baseline
    # ------------------------------------------------------------------
    lookback_delta = timedelta(days=pipeline_drop_lookback_days)
    current_period_start = now - lookback_delta
    previous_period_start = current_period_start - lookback_delta
    current_period_end = now
    previous_period_end = current_period_start

    current_additions = [
        deal
        for deal in deals
        if deal.status in ACTIVE_DEAL_STATUSES and deal.linked_at and deal.linked_at >= current_period_start
    ]
    previous_additions = [
        deal
        for deal in deals
        if deal.status in ACTIVE_DEAL_STATUSES
        and deal.linked_at
        and previous_period_start <= deal.linked_at < previous_period_end
    ]

    current_additions_count = len(current_additions)
    previous_additions_count = len(previous_additions)
    current_additions_value = sum((_deal_value_for_reporting(deal) for deal in current_additions), Decimal("0.00"))
    previous_additions_value = sum(
        (_deal_value_for_reporting(deal) for deal in previous_additions),
        Decimal("0.00"),
    )

    volume_drop_percent = (
        _pct(max(previous_additions_count - current_additions_count, 0), previous_additions_count)
        if previous_additions_count > 0
        else 0.0
    )
    value_drop_percent = (
        _pct(
            max(previous_additions_value - current_additions_value, Decimal("0.00")),
            previous_additions_value,
        )
        if previous_additions_value > 0
        else 0.0
    )
    drop_percent = max(volume_drop_percent, value_drop_percent)
    drop_alert_triggered = (
        (previous_additions_count > 0 or previous_additions_value > 0)
        and drop_percent >= 20.0
    )

    # ------------------------------------------------------------------
    # Campaign performance feed
    # ------------------------------------------------------------------
    campaign_total = len(campaigns)
    campaign_running = sum(1 for campaign in campaigns if campaign.status == Campaign.Status.RUNNING)
    campaign_completed = sum(1 for campaign in campaigns if campaign.status == Campaign.Status.COMPLETED)
    campaign_generated_leads = sum(int(campaign.auto_created_leads_count or 0) for campaign in campaigns)
    campaign_spend = sum((_to_decimal(campaign.spend_amount) for campaign in campaigns), Decimal("0.00"))
    campaign_revenue = sum(
        (_to_decimal(campaign.revenue_attributed) for campaign in campaigns),
        Decimal("0.00"),
    )
    campaign_roi_percent = (
        round(float((campaign_revenue - campaign_spend) / campaign_spend * 100), 1)
        if campaign_spend > 0
        else 0.0
    )
    campaign_rows = []
    for campaign in campaigns:
        row_spend = _to_decimal(campaign.spend_amount)
        row_revenue = _to_decimal(campaign.revenue_attributed)
        row_roi = round(float((row_revenue - row_spend) / row_spend * 100), 1) if row_spend > 0 else 0.0
        campaign_rows.append(
            {
                "campaign_id": campaign.id,
                "name": campaign.name,
                "status": campaign.status,
                "channel": campaign.channel,
                "campaign_type": campaign.campaign_type,
                "total_recipients": int(campaign.total_recipients or 0),
                "auto_created_leads_count": int(campaign.auto_created_leads_count or 0),
                "open_rate": float(campaign.open_rate or 0),
                "click_rate": float(campaign.click_rate or 0),
                "delivery_rate": float(campaign.delivery_rate or 0),
                "spend_amount": _money(row_spend),
                "revenue_attributed": _money(row_revenue),
                "roi_percent": row_roi,
                "target_lead_types": list(campaign.target_lead_types or []),
            }
        )
    campaign_rows.sort(
        key=lambda row: (
            -float(row["revenue_attributed"]),
            -float(row["spend_amount"]),
            row["name"].lower(),
        )
    )

    projects_integration = {
        "last_synced_at": None,
        "demand_insight_count": 0,
        "high_demand_insight_count": 0,
        "top_demand_areas": [],
        "high_demand_areas": [],
    }
    if organization_id is not None:
        try:
            from apps.projects.models import ProjectPlanningInsight

            insight_qs = ProjectPlanningInsight.objects.filter(
                organization_id=organization_id,
                source_module=ProjectPlanningInsight.SourceModule.CRM,
                is_active=True,
            )
            demand_qs = insight_qs.filter(
                insight_type=ProjectPlanningInsight.InsightType.DEMAND_ANALYTICS
            )
            high_qs = insight_qs.filter(
                insight_type=ProjectPlanningInsight.InsightType.NEW_DEVELOPMENT
            )

            latest_insight = insight_qs.order_by("-updated_at").first()
            if latest_insight and latest_insight.updated_at:
                projects_integration["last_synced_at"] = latest_insight.updated_at.isoformat()

            projects_integration["demand_insight_count"] = demand_qs.count()
            projects_integration["high_demand_insight_count"] = high_qs.count()

            for insight in demand_qs.order_by("-demand_share_percent", "-lead_count", "area_name")[:5]:
                projects_integration["top_demand_areas"].append(
                    {
                        "area_name": insight.area_name,
                        "title": insight.title,
                        "summary": insight.summary,
                        "demand_share_percent": float(insight.demand_share_percent or 0),
                        "lead_count": int(insight.lead_count or 0),
                        "qualified_lead_count": int(insight.qualified_lead_count or 0),
                        "won_lead_count": int(insight.won_lead_count or 0),
                        "window_days": int(insight.window_days or 0),
                        "threshold_percent": float(insight.threshold_percent or 0),
                        "is_active": bool(insight.is_active),
                        "last_triggered_at": (
                            insight.last_triggered_at.isoformat() if insight.last_triggered_at else None
                        ),
                        "updated_at": insight.updated_at.isoformat() if insight.updated_at else None,
                    }
                )

            for insight in high_qs.order_by("-demand_share_percent", "-updated_at", "area_name")[:5]:
                projects_integration["high_demand_areas"].append(
                    {
                        "area_name": insight.area_name,
                        "title": insight.title,
                        "summary": insight.summary,
                        "demand_share_percent": float(insight.demand_share_percent or 0),
                        "lead_count": int(insight.lead_count or 0),
                        "qualified_lead_count": int(insight.qualified_lead_count or 0),
                        "won_lead_count": int(insight.won_lead_count or 0),
                        "window_days": int(insight.window_days or 0),
                        "threshold_percent": float(insight.threshold_percent or 0),
                        "is_active": bool(insight.is_active),
                        "last_triggered_at": (
                            insight.last_triggered_at.isoformat() if insight.last_triggered_at else None
                        ),
                        "updated_at": insight.updated_at.isoformat() if insight.updated_at else None,
                    }
                )
        except Exception:
            projects_integration = {
                "last_synced_at": None,
                "demand_insight_count": 0,
                "high_demand_insight_count": 0,
                "top_demand_areas": [],
                "high_demand_areas": [],
            }

    procurement_integration = {
        "last_synced_at": None,
        "bulk_demand_insight_count": 0,
        "furnishing_package_count": 0,
        "add_on_package_count": 0,
        "triggered_areas": [],
        "package_recommendations": [],
    }
    if organization_id is not None:
        try:
            from apps.procurement.models import ProcurementDemandInsight

            insight_qs = ProcurementDemandInsight.objects.filter(
                organization_id=organization_id,
                source_module=ProcurementDemandInsight.SourceModule.CRM,
                is_active=True,
            )
            bulk_qs = insight_qs.filter(
                insight_type=ProcurementDemandInsight.InsightType.BULK_BUYER_DEMAND
            )
            furnishing_qs = insight_qs.filter(
                insight_type=ProcurementDemandInsight.InsightType.FURNISHING_PACKAGE
            )
            add_on_qs = insight_qs.filter(
                insight_type=ProcurementDemandInsight.InsightType.ADD_ON_PACKAGE
            )

            latest_insight = insight_qs.order_by("-updated_at").first()
            if latest_insight and latest_insight.updated_at:
                procurement_integration["last_synced_at"] = latest_insight.updated_at.isoformat()

            procurement_integration["bulk_demand_insight_count"] = bulk_qs.count()
            procurement_integration["furnishing_package_count"] = furnishing_qs.count()
            procurement_integration["add_on_package_count"] = add_on_qs.count()

            triggered_areas = list(
                insight_qs.filter(
                    insight_type__in=[
                        ProcurementDemandInsight.InsightType.FURNISHING_PACKAGE,
                        ProcurementDemandInsight.InsightType.ADD_ON_PACKAGE,
                    ]
                )
                .order_by("-demand_share_percent", "-bulk_buyer_lead_count", "area_name")
                .values_list("area_name", flat=True)
                .distinct()[:5]
            )
            procurement_integration["triggered_areas"] = triggered_areas

            for insight in (
                insight_qs.filter(
                    insight_type__in=[
                        ProcurementDemandInsight.InsightType.FURNISHING_PACKAGE,
                        ProcurementDemandInsight.InsightType.ADD_ON_PACKAGE,
                    ]
                )
                .order_by("-demand_share_percent", "-bulk_buyer_lead_count", "-updated_at", "area_name")[:10]
            ):
                procurement_integration["package_recommendations"].append(
                    {
                        "area_name": insight.area_name,
                        "insight_type": insight.insight_type,
                        "title": insight.title,
                        "summary": insight.summary,
                        "demand_share_percent": float(insight.demand_share_percent or 0),
                        "lead_count": int(insight.lead_count or 0),
                        "qualified_lead_count": int(insight.qualified_lead_count or 0),
                        "won_lead_count": int(insight.won_lead_count or 0),
                        "bulk_buyer_lead_count": int(insight.bulk_buyer_lead_count or 0),
                        "window_days": int(insight.window_days or 0),
                        "threshold_percent": float(insight.threshold_percent or 0),
                        "min_bulk_leads": int(insight.min_bulk_leads or 0),
                        "is_active": bool(insight.is_active),
                        "last_triggered_at": (
                            insight.last_triggered_at.isoformat() if insight.last_triggered_at else None
                        ),
                        "updated_at": insight.updated_at.isoformat() if insight.updated_at else None,
                    }
                )
        except Exception:
            procurement_integration = {
                "last_synced_at": None,
                "bulk_demand_insight_count": 0,
                "furnishing_package_count": 0,
                "add_on_package_count": 0,
                "triggered_areas": [],
                "package_recommendations": [],
            }

    return {
        "generated_at": now.isoformat(),
        "window_days": window_days,
        "summary": {
            "total_leads": total_leads,
            "active_leads": active_leads,
            "won_leads": won_leads,
            "lost_leads": lost_leads,
            "conversion_rate": _pct(won_leads, total_leads),
            "sales_velocity_days": avg_days_to_close,
            "sales_velocity_deals_per_month": deals_per_month,
            "pipeline_value": _money(pipeline_value),
            "weighted_forecast": _money(weighted_forecast),
            "closed_won_revenue": _money(closed_won_value),
            "active_deals": active_deals,
        },
        "conversion_rates": {
            "overall_conversion_rate": _pct(won_leads, total_leads),
            "qualified_conversion_rate": _pct(qualified_or_beyond, total_leads),
            "win_rate": _pct(won_leads, closed_outcomes),
            "qualified_or_beyond_count": qualified_or_beyond,
            "closed_outcomes_count": closed_outcomes,
            "stage_conversion": stage_conversion,
        },
        "sales_velocity": {
            "avg_days_to_close": avg_days_to_close,
            "median_days_to_close": median_days_to_close,
            "closed_won_count": len(closed_won_in_window),
            "deals_per_month": deals_per_month,
            "stage_durations": stage_durations,
        },
        "revenue_forecast": {
            "total_deals": len(deals),
            "active_deals": active_deals,
            "pipeline_value": _money(pipeline_value),
            "weighted_forecast": _money(weighted_forecast),
            "closed_won_value": _money(closed_won_value),
            "forecast_coverage_ratio": _pct(closed_won_value, weighted_forecast),
            "stage_breakdown": stage_breakdown,
        },
        "lead_source_performance": lead_source_performance,
        "agent_performance": agent_performance,
        "pipeline_drop_monitor": {
            "lookback_days": pipeline_drop_lookback_days,
            "current_period_start": current_period_start.isoformat(),
            "current_period_end": current_period_end.isoformat(),
            "previous_period_start": previous_period_start.isoformat(),
            "previous_period_end": previous_period_end.isoformat(),
            "current_additions_count": current_additions_count,
            "previous_additions_count": previous_additions_count,
            "current_additions_value": _money(current_additions_value),
            "previous_additions_value": _money(previous_additions_value),
            "volume_drop_percent": round(volume_drop_percent, 1),
            "value_drop_percent": round(value_drop_percent, 1),
            "drop_percent": round(drop_percent, 1),
            "is_alert": drop_alert_triggered,
        },
        "campaign_performance": {
            "total_campaigns": campaign_total,
            "running_campaigns": campaign_running,
            "completed_campaigns": campaign_completed,
            "generated_leads": campaign_generated_leads,
            "total_spend": _money(campaign_spend),
            "total_revenue": _money(campaign_revenue),
            "roi_percent": campaign_roi_percent,
            "campaigns": campaign_rows[:10],
        },
        "projects_integration": projects_integration,
        "procurement_integration": procurement_integration,
    }
