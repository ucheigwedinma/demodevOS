from datetime import timedelta

from django.db.models import F, Sum
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.properties.models import AssetComponent, Inspection, PreventiveSchedule, ServiceRequest, WorkOrder
from apps.settings.permissions import HasRolePermission

from .models import FacilityIncident, UtilityConsumption


def _user_org(request):
    profile = getattr(request.user, "profile", None)
    return getattr(profile, "organization", None)


def _to_float(value, digits: int = 2) -> float:
    if value is None:
        return 0.0
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return 0.0


def _pct(part: int, whole: int) -> float:
    if whole <= 0:
        return 100.0
    return round((part * 100) / whole, 1)


def _pct_change(current: float, previous: float) -> float | None:
    if previous <= 0:
        return None if current <= 0 else 100.0
    return round(((current - previous) / previous) * 100, 1)


def _utility_totals(qs):
    totals = qs.aggregate(
        electricity_kwh=Sum("electricity_kwh"),
        water_m3=Sum("water_m3"),
        diesel_liters=Sum("diesel_liters"),
        gas_m3=Sum("gas_m3"),
    )
    return {
        "electricity_kwh": _to_float(totals.get("electricity_kwh")),
        "water_m3": _to_float(totals.get("water_m3")),
        "diesel_liters": _to_float(totals.get("diesel_liters")),
        "gas_m3": _to_float(totals.get("gas_m3")),
    }


class FacilityDashboardOverviewView(APIView):
    """Cross-module facility management dashboard metrics."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    rbac_action = "view"

    def get(self, request):
        org = _user_org(request)
        if org is None:
            return Response(
                {"detail": "Organization context required."},
                status=400,
            )

        today = timezone.localdate()
        next_30_days = today + timedelta(days=30)

        open_work_orders_qs = WorkOrder.objects.filter(
            organization=org,
            status__in=[
                WorkOrder.Status.OPEN,
                WorkOrder.Status.ASSIGNED,
                WorkOrder.Status.IN_PROGRESS,
                WorkOrder.Status.ON_HOLD,
            ],
        )
        open_work_orders_count = open_work_orders_qs.count()

        open_service_requests_count = ServiceRequest.objects.filter(
            organization=org,
            status__in=[
                ServiceRequest.Status.OPEN,
                ServiceRequest.Status.ACKNOWLEDGED,
                ServiceRequest.Status.IN_PROGRESS,
                ServiceRequest.Status.ESCALATED,
            ],
        ).count()

        completed_with_due_qs = WorkOrder.objects.filter(
            organization=org,
            status=WorkOrder.Status.COMPLETED,
            due_date__isnull=False,
            completed_date__isnull=False,
        )
        sla_measured_count = completed_with_due_qs.count()
        sla_on_time_count = completed_with_due_qs.filter(
            completed_date__lte=F("due_date"),
        ).count()
        sla_compliance_rate = _pct(sla_on_time_count, sla_measured_count)

        active_assets_count = AssetComponent.objects.filter(
            organization=org,
            is_active=True,
        ).count()
        degraded_assets_count = AssetComponent.objects.filter(
            organization=org,
            is_active=True,
            condition_rating__in=[
                AssetComponent.ConditionRating.POOR,
                AssetComponent.ConditionRating.CRITICAL,
            ],
        ).count()
        healthy_assets_count = max(active_assets_count - degraded_assets_count, 0)
        asset_uptime_pct = _pct(healthy_assets_count, active_assets_count)
        asset_downtime_pct = round(100.0 - asset_uptime_pct, 1)

        preventive_active_qs = PreventiveSchedule.objects.filter(
            organization=org,
            status=PreventiveSchedule.Status.ACTIVE,
        )
        preventive_active_count = preventive_active_qs.count()
        preventive_overdue_count = preventive_active_qs.filter(
            next_due_date__lt=today,
        ).count()
        preventive_readiness_pct = _pct(
            max(preventive_active_count - preventive_overdue_count, 0),
            preventive_active_count,
        )

        upcoming_preventive_qs = (
            preventive_active_qs.filter(
                next_due_date__gte=today,
                next_due_date__lte=next_30_days,
            )
            .select_related("property", "asset_component")
            .order_by("next_due_date")
        )
        upcoming_preventive_items = [
            {
                "id": row.id,
                "title": row.title,
                "next_due_date": row.next_due_date.isoformat(),
                "property_name": row.property.name,
                "asset_component_name": row.asset_component.name if row.asset_component_id else "",
                "assigned_to": row.assigned_to,
                "category": row.category,
            }
            for row in upcoming_preventive_qs[:8]
        ]

        incident_open_qs = FacilityIncident.objects.filter(
            organization=org,
            status__in=[
                FacilityIncident.Status.OPEN,
                FacilityIncident.Status.INVESTIGATING,
            ],
        )
        incident_open_count = incident_open_qs.count()
        incident_critical_count = incident_open_qs.filter(
            severity=FacilityIncident.Severity.CRITICAL,
        ).count()
        incident_high_count = incident_open_qs.filter(
            severity=FacilityIncident.Severity.HIGH,
        ).count()

        inspection_post_incident_count = Inspection.objects.filter(
            organization=org,
            inspection_type=Inspection.InspectionType.POST_INCIDENT,
            status__in=[
                Inspection.Status.SCHEDULED,
                Inspection.Status.IN_PROGRESS,
            ],
        ).count()

        inspection_high_risk_count = Inspection.objects.filter(
            organization=org,
            risk_level__in=[
                Inspection.RiskLevel.HIGH,
                Inspection.RiskLevel.CRITICAL,
            ],
            status__in=[
                Inspection.Status.SCHEDULED,
                Inspection.Status.IN_PROGRESS,
            ],
        ).count()

        incident_alert_total = (
            incident_open_count
            + inspection_post_incident_count
            + inspection_high_risk_count
        )

        current_window_start = today - timedelta(days=29)
        previous_window_start = today - timedelta(days=59)
        previous_window_end = today - timedelta(days=30)

        utility_current = _utility_totals(
            UtilityConsumption.objects.filter(
                organization=org,
                reading_date__gte=current_window_start,
                reading_date__lte=today,
            )
        )
        utility_previous = _utility_totals(
            UtilityConsumption.objects.filter(
                organization=org,
                reading_date__gte=previous_window_start,
                reading_date__lte=previous_window_end,
            )
        )
        energy_index_current = round(
            utility_current["electricity_kwh"]
            + utility_current["diesel_liters"]
            + utility_current["gas_m3"],
            2,
        )
        energy_index_previous = round(
            utility_previous["electricity_kwh"]
            + utility_previous["diesel_liters"]
            + utility_previous["gas_m3"],
            2,
        )
        energy_change_pct = _pct_change(energy_index_current, energy_index_previous)

        incident_penalty = min(
            (incident_critical_count * 20)
            + (incident_high_count * 10)
            + (inspection_post_incident_count * 8)
            + (inspection_high_risk_count * 6),
            100,
        )
        incident_health_score = max(0.0, 100.0 - float(incident_penalty))

        facility_health_score = round(
            (sla_compliance_rate * 0.35)
            + (asset_uptime_pct * 0.30)
            + (preventive_readiness_pct * 0.20)
            + (incident_health_score * 0.15),
            1,
        )

        payload = {
            "generated_at": timezone.now().isoformat(),
            "facility_health_score": facility_health_score,
            "active_maintenance_requests": {
                "work_orders": open_work_orders_count,
                "service_requests": open_service_requests_count,
                "total": open_work_orders_count + open_service_requests_count,
            },
            "sla_compliance_rate": {
                "value": sla_compliance_rate,
                "measured_count": sla_measured_count,
                "on_time_count": sla_on_time_count,
            },
            "asset_uptime_downtime": {
                "tracked_assets": active_assets_count,
                "degraded_assets": degraded_assets_count,
                "uptime_pct": asset_uptime_pct,
                "downtime_pct": asset_downtime_pct,
            },
            "energy_utility_consumption": {
                "window_days": 30,
                "electricity_kwh": utility_current["electricity_kwh"],
                "water_m3": utility_current["water_m3"],
                "diesel_liters": utility_current["diesel_liters"],
                "gas_m3": utility_current["gas_m3"],
                "energy_index": energy_index_current,
                "energy_change_vs_previous_pct": energy_change_pct,
            },
            "incident_alerts": {
                "total_alerts": incident_alert_total,
                "open_incidents": incident_open_count,
                "critical_incidents": incident_critical_count,
                "high_incidents": incident_high_count,
                "post_incident_inspections": inspection_post_incident_count,
                "high_risk_inspections": inspection_high_risk_count,
            },
            "upcoming_preventive_maintenance": {
                "upcoming_count": upcoming_preventive_qs.count(),
                "overdue_count": preventive_overdue_count,
                "items": upcoming_preventive_items,
            },
        }
        return Response(payload)
