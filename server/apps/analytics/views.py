import hashlib
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import status as drf_status
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.properties.models import Property
from apps.settings.permissions import HasRolePermission

from .cache_utils import bump_analytics_cache_version, get_analytics_cache_version
from .computations import (
    compute_classification_breakdown,
    compute_construction_summary,
    compute_crm_summary,
    compute_encumbrance_summary,
    compute_facility_summary,
    compute_hr_summary,
    compute_portfolio_kpis,
    compute_procurement_summary,
    compute_project_budget_summary,
    compute_risk_alerts,
    compute_tenant_summary,
    compute_top_properties,
    compute_type_distribution,
    compute_unit_occupancy,
    compute_valuation_history,
)


def _user_org(request):
    """Return the requesting user's organization, or None."""
    profile = getattr(request.user, "profile", None)
    return getattr(profile, "organization", None)


def _is_superuser(request):
    return bool(getattr(request.user, "is_superuser", False))


def _resolve_org(request):
    """
    Return (org_or_none, error_response_or_none).
    ALL users (including superusers) are scoped to their profile org
    to prevent cross-tenant data leakage in analytics aggregations.
    """
    org = _user_org(request)
    if org is None:
        return None, Response(
            {"detail": "Organization context required."},
            status=400,
        )
    return org, None


def _parse_period(request):
    end = parse_date(request.query_params.get("end_date", "")) or timezone.localdate()
    start = parse_date(request.query_params.get("start_date", ""))
    if start is None:
        start = end - timedelta(days=180)
    if start > end:
        start, end = end, start
    return start, end


PORTFOLIO_WIDGET_CACHE_TTL_SECONDS = 120


def _sorted_query_hash(query_params) -> str:
    normalized = []
    for key in sorted(query_params.keys()):
        values = sorted(str(value) for value in query_params.getlist(key))
        normalized.extend(f"{key}={value}" for value in values)
    if not normalized:
        return "noquery"
    return hashlib.sha1("&".join(normalized).encode("utf-8")).hexdigest()[:16]


def _analytics_cache_key(request, scope: str) -> str:
    org = _user_org(request)
    org_id = getattr(org, "id", 0) or 0
    cache_version = get_analytics_cache_version(org_id)
    return (
        f"analytics:{scope}:u:{request.user.id}:"
        f"org:{org_id}:super:{int(_is_superuser(request))}:"
        f"v:{cache_version}:q:{_sorted_query_hash(request.query_params)}"
    )


class PortfolioAnalyticsView(APIView):
    """
    GET /api/analytics/portfolio/
    Returns the full analytics payload for the market analysis dashboard.
    Reads from pre-computed snapshots when available, falls back to live.
    """

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "analytics.all"
    rbac_action = "view"

    def get(self, request):
        org, err = _resolve_org(request)
        if err:
            return err

        org_id = org.id
        cache_key = _analytics_cache_key(request, "portfolio-widgets")
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        cross_module_summaries = {
            "construction_summary": compute_construction_summary(org_id),
            "crm_summary": compute_crm_summary(org_id),
            "hr_summary": compute_hr_summary(org_id),
            "procurement_summary": compute_procurement_summary(org_id),
            "facility_summary": compute_facility_summary(org_id),
            "tenant_summary": compute_tenant_summary(org_id),
        }

        # Snapshot-first: serve pre-computed data when available
        snapshot = self._latest_snapshot(org)
        if snapshot is not None:
            data = self._serialize_snapshot(snapshot)
            # Keep budget widgets real-time even when serving snapshot-first payload.
            data["project_budget_summary"] = compute_project_budget_summary(org_id)
            data.update(cross_module_summaries)
            cache.set(cache_key, data, timeout=PORTFOLIO_WIDGET_CACHE_TTL_SECONDS)
            return Response(data)

        # Live fallback
        active = Property.objects.filter(is_active=True, organization=org)
        data = {
            "kpis": compute_portfolio_kpis(active),
            "type_distribution": compute_type_distribution(active),
            "classification_breakdown": compute_classification_breakdown(active),
            "valuation_history": compute_valuation_history(org_id),
            "unit_occupancy": compute_unit_occupancy(active),
            "project_budget_summary": compute_project_budget_summary(org_id),
            "top_appreciating": compute_top_properties(active, ascending=False),
            "top_depreciating": compute_top_properties(active, ascending=True),
            "encumbrance_summary": compute_encumbrance_summary(active),
            **cross_module_summaries,
        }
        cache.set(cache_key, data, timeout=PORTFOLIO_WIDGET_CACHE_TTL_SECONDS)
        return Response(data)

    def _latest_snapshot(self, org):
        from .models import PortfolioSnapshot

        return (
            PortfolioSnapshot.objects
            .filter(organization=org)
            .order_by("-snapshot_date")
            .first()
        )

    def _serialize_snapshot(self, snapshot):
        return {
            "kpis": {
                "total_value": str(snapshot.total_value),
                "total_acquisition": str(snapshot.total_acquisition),
                "property_count": snapshot.property_count,
                "total_area_sqft": str(snapshot.total_area_sqft),
                "avg_price_per_sqft": str(snapshot.avg_price_per_sqft),
                "unrealized_gain": str(snapshot.unrealized_gain),
            },
            "type_distribution": snapshot.type_distribution,
            "classification_breakdown": snapshot.classification_breakdown,
            "valuation_history": snapshot.valuation_history,
            "unit_occupancy": snapshot.unit_occupancy,
            "project_budget_summary": snapshot.project_budget_summary,
            "top_appreciating": snapshot.top_appreciating,
            "top_depreciating": snapshot.top_depreciating,
            "encumbrance_summary": snapshot.encumbrance_summary,
            "_snapshot": {
                "snapshot_date": snapshot.snapshot_date.isoformat(),
                "computed_at": snapshot.computed_at.isoformat(),
            },
        }


class BoardKpiView(APIView):
    """
    GET /api/analytics/board-kpis/
    Board-level KPI snapshot across procurement, projects, finance, and workflows.
    Reads from pre-computed snapshots when available, falls back to live.
    """

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "analytics.all"
    rbac_action = "view"

    def get(self, request):
        org, err = _resolve_org(request)
        if err:
            return err

        start_date, end_date = _parse_period(request)

        # Snapshot-first: serve pre-computed data for default period
        snapshot = self._latest_snapshot(org, start_date, end_date)
        if snapshot is not None:
            data = self._serialize_snapshot(snapshot)
            return Response(data)

        # Live fallback
        from .computations import (
            compute_approval_time,
            compute_budget_overrun,
            compute_cost_variance,
            compute_emergency_purchases,
            compute_procurement_cycle_time,
            compute_vendor_reliability,
        )

        org_id = org.id
        kpis = {
            "procurement_cycle_time_days": compute_procurement_cycle_time(start_date, end_date, org_id),
            "cost_variance_per_project_pct": compute_cost_variance(org_id),
            "vendor_reliability_score": compute_vendor_reliability(org_id),
            "emergency_purchases_pct": compute_emergency_purchases(start_date, end_date, org_id),
            "budget_overrun_frequency_pct": compute_budget_overrun(org_id),
            "average_approval_time_hours": compute_approval_time(start_date, end_date, org_id),
        }

        return Response(
            {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": (end_date - start_date).days + 1,
                },
                "kpis": kpis,
            }
        )

    def _latest_snapshot(self, org, start_date, end_date):
        from .models import BoardKpiSnapshot

        # Only use snapshot if the requested period matches the default 180-day lookback
        expected_start = end_date - timedelta(days=180)
        if start_date != expected_start:
            return None
        return (
            BoardKpiSnapshot.objects
            .filter(organization=org)
            .order_by("-snapshot_hour")
            .first()
        )

    def _serialize_snapshot(self, snapshot):
        return {
            "period": {
                "start_date": snapshot.period_start.isoformat(),
                "end_date": snapshot.period_end.isoformat(),
                "days": (snapshot.period_end - snapshot.period_start).days + 1,
            },
            "kpis": {
                "procurement_cycle_time_days": snapshot.procurement_cycle_time_days,
                "cost_variance_per_project_pct": snapshot.cost_variance_per_project_pct,
                "vendor_reliability_score": snapshot.vendor_reliability_score,
                "emergency_purchases_pct": snapshot.emergency_purchases_pct,
                "budget_overrun_frequency_pct": snapshot.budget_overrun_frequency_pct,
                "average_approval_time_hours": snapshot.average_approval_time_hours,
            },
            "_snapshot": {
                "snapshot_hour": snapshot.snapshot_hour.isoformat(),
                "computed_at": snapshot.computed_at.isoformat(),
            },
        }


class RiskAlertsView(APIView):
    """
    GET /api/analytics/risk-alerts/
    Consolidated risk alert feed across projects, workflows, finance,
    procurement, facilities, and CRM.
    """

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "analytics.all"
    rbac_action = "view"

    def get(self, request):
        org, err = _resolve_org(request)
        if err:
            return err

        cache_key = _analytics_cache_key(request, "risk-alerts")
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        payload = compute_risk_alerts(org.id)
        cache.set(cache_key, payload, timeout=PORTFOLIO_WIDGET_CACHE_TTL_SECONDS)
        return Response(payload)


class RiskAlertAckView(APIView):
    """
    POST   /api/analytics/risk-alerts/<alert_id>/ack/   upsert ack
    DELETE /api/analytics/risk-alerts/<alert_id>/ack/   clear ack

    Risk alerts are computed live and have synthetic IDs. This endpoint
    overlays user acknowledgement state without touching source records.
    """

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "analytics.all"
    rbac_action = "view"

    VALID_STATUSES = {"open", "acknowledged", "resolved"}
    MAX_ALERT_ID_LEN = 128
    MAX_NOTE_LEN = 2000

    def post(self, request, alert_id: str):
        from .models import RiskAlertAcknowledgement
        from .serializers import RiskAlertAcknowledgementSerializer

        org, err = _resolve_org(request)
        if err:
            return err

        if not alert_id or len(alert_id) > self.MAX_ALERT_ID_LEN:
            return Response(
                {"detail": "Invalid alert id."},
                status=drf_status.HTTP_400_BAD_REQUEST,
            )

        body = request.data if isinstance(request.data, dict) else {}
        new_status = body.get("status", "acknowledged")
        if new_status not in self.VALID_STATUSES:
            return Response(
                {"detail": f"status must be one of {sorted(self.VALID_STATUSES)}."},
                status=drf_status.HTTP_400_BAD_REQUEST,
            )

        note = body.get("note", "") or ""
        if not isinstance(note, str) or len(note) > self.MAX_NOTE_LEN:
            return Response(
                {"detail": "note must be a string under 2000 chars."},
                status=drf_status.HTTP_400_BAD_REQUEST,
            )

        assigned_to_user = None
        assigned_to_id = body.get("assigned_to")
        if assigned_to_id is not None:
            if assigned_to_id == "me":
                assigned_to_user = request.user
            else:
                try:
                    assigned_to_user = get_user_model().objects.get(pk=int(assigned_to_id))
                except (ValueError, TypeError, get_user_model().DoesNotExist):
                    return Response(
                        {"detail": "assigned_to must be a valid user id or 'me'."},
                        status=drf_status.HTTP_400_BAD_REQUEST,
                    )
                # Org scoping: only allow assignment to a user in same org
                profile = getattr(assigned_to_user, "profile", None)
                target_org_id = getattr(profile, "organization_id", None)
                if target_org_id != org.id and not _is_superuser(request):
                    return Response(
                        {"detail": "assigned_to must belong to your organization."},
                        status=drf_status.HTTP_400_BAD_REQUEST,
                    )

        now = timezone.now()
        defaults = {
            "status": new_status,
            "note": note,
            "updated_by": request.user,
        }
        if assigned_to_id is not None:
            defaults["assigned_to"] = assigned_to_user

        ack, created = RiskAlertAcknowledgement.objects.get_or_create(
            organization=org,
            alert_id=alert_id,
            defaults={**defaults, "created_by": request.user},
        )
        if not created:
            for field, value in defaults.items():
                setattr(ack, field, value)

        # Stamp transition timestamps
        if new_status == "acknowledged" and ack.acknowledged_at is None:
            ack.acknowledged_at = now
        if new_status == "resolved" and ack.resolved_at is None:
            ack.resolved_at = now
        if new_status == "open":
            ack.acknowledged_at = None
            ack.resolved_at = None

        ack.save()

        bump_analytics_cache_version(org.id)
        return Response(
            RiskAlertAcknowledgementSerializer(ack).data,
            status=drf_status.HTTP_200_OK if not created else drf_status.HTTP_201_CREATED,
        )

    def delete(self, request, alert_id: str):
        from .models import RiskAlertAcknowledgement

        org, err = _resolve_org(request)
        if err:
            return err

        if not alert_id or len(alert_id) > self.MAX_ALERT_ID_LEN:
            return Response(
                {"detail": "Invalid alert id."},
                status=drf_status.HTTP_400_BAD_REQUEST,
            )

        deleted, _ = RiskAlertAcknowledgement.objects.filter(
            organization=org, alert_id=alert_id,
        ).delete()
        if deleted:
            bump_analytics_cache_version(org.id)
        return Response(status=drf_status.HTTP_204_NO_CONTENT)


# ── Snapshot Freshness Health ───────────────────────────────────────────


class SnapshotHealthView(APIView):
    """
    GET /api/analytics/health/
    Returns freshness metadata for portfolio and board KPI snapshots.
    """

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "analytics.all"
    rbac_action = "view"

    PORTFOLIO_STALE_THRESHOLD_HOURS = 25
    BOARD_KPI_STALE_THRESHOLD_HOURS = 2

    def get(self, request):
        from .models import BoardKpiSnapshot, PortfolioSnapshot

        org, err = _resolve_org(request)
        if err:
            return err

        now = timezone.now()

        portfolio_snapshot = (
            PortfolioSnapshot.objects.filter(organization=org)
            .order_by("-snapshot_date")
            .first()
        )
        board_snapshot = (
            BoardKpiSnapshot.objects.filter(organization=org)
            .order_by("-snapshot_hour")
            .first()
        )

        return Response(
            {
                "checked_at": now.isoformat(),
                "portfolio": self._freshness(
                    portfolio_snapshot, self.PORTFOLIO_STALE_THRESHOLD_HOURS, now
                ),
                "board_kpis": self._freshness(
                    board_snapshot, self.BOARD_KPI_STALE_THRESHOLD_HOURS, now
                ),
            }
        )

    @staticmethod
    def _freshness(snapshot, threshold_hours, now):
        if snapshot is None:
            return {
                "status": "missing",
                "last_computed": None,
                "age_hours": None,
                "is_stale": True,
            }
        age_hours = round(
            (now - snapshot.computed_at).total_seconds() / 3600, 2
        )
        return {
            "status": "stale" if age_hours > threshold_hours else "fresh",
            "last_computed": snapshot.computed_at.isoformat(),
            "age_hours": age_hours,
            "is_stale": age_hours > threshold_hours,
        }


# ── Board KPI Drilldowns ───────────────────────────────────────────────


class BoardKpiDrilldownBaseView(APIView):
    """Base for board KPI drilldown endpoints."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "analytics.all"
    rbac_action = "view"

    def _get_org_and_period(self, request):
        """
        Resolve org (with tenant guard) and date period.
        Returns (org_id_or_none, start_date, end_date, error_response_or_none).
        """
        org, err = _resolve_org(request)
        if err:
            return None, None, None, err
        start_date, end_date = _parse_period(request)
        org_id = org.id if org else None
        return org_id, start_date, end_date, None

    def _require_org(self, org_id):
        """Drilldowns require a concrete org (even superusers must pick one)."""
        if org_id is None:
            return Response(
                {"detail": "Org context required for drilldowns."}, status=400
            )
        return None


class ProcurementCycleDrilldownView(BoardKpiDrilldownBaseView):
    def get(self, request):
        from .drilldowns import drilldown_procurement_cycle_time

        org_id, start_date, end_date, err = self._get_org_and_period(request)
        if err:
            return err
        err = self._require_org(org_id)
        if err:
            return err
        return Response(
            drilldown_procurement_cycle_time(start_date, end_date, org_id)
        )


class CostVarianceDrilldownView(BoardKpiDrilldownBaseView):
    def get(self, request):
        from .drilldowns import drilldown_cost_variance

        org_id, _, _, err = self._get_org_and_period(request)
        if err:
            return err
        err = self._require_org(org_id)
        if err:
            return err
        return Response(drilldown_cost_variance(org_id))


class VendorReliabilityDrilldownView(BoardKpiDrilldownBaseView):
    def get(self, request):
        from .drilldowns import drilldown_vendor_reliability

        org_id, _, _, err = self._get_org_and_period(request)
        if err:
            return err
        err = self._require_org(org_id)
        if err:
            return err
        return Response(drilldown_vendor_reliability(org_id))


class EmergencyPurchasesDrilldownView(BoardKpiDrilldownBaseView):
    def get(self, request):
        from .drilldowns import drilldown_emergency_purchases

        org_id, start_date, end_date, err = self._get_org_and_period(request)
        if err:
            return err
        err = self._require_org(org_id)
        if err:
            return err
        return Response(
            drilldown_emergency_purchases(start_date, end_date, org_id)
        )


class BudgetOverrunDrilldownView(BoardKpiDrilldownBaseView):
    def get(self, request):
        from .drilldowns import drilldown_budget_overrun

        org_id, _, _, err = self._get_org_and_period(request)
        if err:
            return err
        err = self._require_org(org_id)
        if err:
            return err
        return Response(drilldown_budget_overrun(org_id))


class ApprovalTimeDrilldownView(BoardKpiDrilldownBaseView):
    def get(self, request):
        from .drilldowns import drilldown_approval_time

        org_id, start_date, end_date, err = self._get_org_and_period(request)
        if err:
            return err
        err = self._require_org(org_id)
        if err:
            return err
        return Response(
            drilldown_approval_time(start_date, end_date, org_id)
        )


# ── Custom Dashboard CRUD ──────────────────────────────────────────────


class CustomDashboardViewSet(viewsets.ModelViewSet):
    """
    CRUD for user's custom dashboard layouts.
    Scoped to the authenticated user (personal resource, no RBAC).

    Pagination is explicitly disabled — a user's dashboards are a small
    bounded list and the frontend consumes a flat array. Inheriting the
    global PageNumberPagination would return ``{count, next, previous,
    results}`` which would silently break the viewer.
    """

    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_serializer_class(self):
        from .serializers import CustomDashboardSerializer

        return CustomDashboardSerializer

    def get_queryset(self):
        from .models import CustomDashboard

        return CustomDashboard.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
