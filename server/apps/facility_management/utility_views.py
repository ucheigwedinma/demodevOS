from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django_filters import rest_framework as filters
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.mixins import OrgScopedMixin
from apps.procurement.models import Vendor
from apps.settings.permissions import HasRolePermission

from .models import Facility, UtilityBill, UtilityConsumption, UtilityMeter, UtilityMeterReading
from .utility_serializers import (
    FacilityUtilityBillDetailSerializer,
    FacilityUtilityBillListSerializer,
    FacilityUtilityBillWriteSerializer,
    FacilityUtilityMeterDetailSerializer,
    FacilityUtilityMeterListSerializer,
    FacilityUtilityMeterReadingDetailSerializer,
    FacilityUtilityMeterReadingListSerializer,
    FacilityUtilityMeterReadingWriteSerializer,
    FacilityUtilityMeterWriteSerializer,
)
from .utility_workflows import (
    ensure_utility_bill_defaults,
    ensure_utility_meter_defaults,
    estimate_carbon_kg_co2e,
    rebuild_utility_consumption_for_property,
    recalculate_meter_reading_series,
    run_utility_energy_automation,
    sync_finance_bill_for_utility_bill,
)


def _resolve_user_org(request):
    org = getattr(request, "organization", None)
    if org is not None:
        return org
    profile = getattr(request.user, "profile", None)
    return getattr(profile, "organization", None)


def _facility_property_filter() -> Q:
    return Q(property__facility_registry__isnull=False)


def _decimal(value) -> Decimal:
    return Decimal(value or 0)


def _fmt_decimal(value) -> str:
    return f"{_decimal(value):.2f}"


def _sustainability_score(*, overdue_bills: int, anomalies: int, energy_change_pct: Decimal | None) -> int:
    score = Decimal("100")
    score -= min(Decimal(overdue_bills) * Decimal("6"), Decimal("24"))
    score -= min(Decimal(anomalies) * Decimal("4"), Decimal("24"))
    if energy_change_pct is not None and energy_change_pct > 0:
        score -= min(energy_change_pct, Decimal("20"))
    return max(0, min(100, int(score)))


class FacilityUtilityMeterFilter(filters.FilterSet):
    facility = filters.NumberFilter(field_name="property__facility_registry_id")

    class Meta:
        model = UtilityMeter
        fields = ["facility", "property", "utility_type", "vendor", "is_active", "is_smart_meter"]


class FacilityUtilityMeterReadingFilter(filters.FilterSet):
    facility = filters.NumberFilter(field_name="meter__property__facility_registry_id")
    reading_after = filters.IsoDateTimeFilter(field_name="reading_at", lookup_expr="gte")
    reading_before = filters.IsoDateTimeFilter(field_name="reading_at", lookup_expr="lte")

    class Meta:
        model = UtilityMeterReading
        fields = ["meter", "facility", "is_estimated", "is_anomaly", "meter__utility_type"]


class FacilityUtilityBillFilter(filters.FilterSet):
    facility = filters.NumberFilter(field_name="property__facility_registry_id")
    billing_from = filters.DateFilter(field_name="billing_period_start", lookup_expr="gte")
    billing_to = filters.DateFilter(field_name="billing_period_end", lookup_expr="lte")

    class Meta:
        model = UtilityBill
        fields = ["facility", "property", "meter", "vendor", "utility_type", "status"]


class FacilityUtilitiesOverviewView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    rbac_action = "view"

    def get(self, request):
        org = _resolve_user_org(request)
        if org is None:
            return Response({"detail": "Organization context required."}, status=400)

        today = timezone.localdate()
        now = timezone.now()
        window_start = today - timedelta(days=29)
        six_month_window = today.replace(day=1) - timedelta(days=150)

        meters_qs = (
            UtilityMeter.objects.filter(organization=org)
            .filter(_facility_property_filter())
            .select_related("property", "property__facility_registry", "vendor")
        )
        readings_qs = (
            UtilityMeterReading.objects.filter(organization=org, meter__property__facility_registry__isnull=False)
            .select_related("meter", "meter__property", "meter__property__facility_registry", "entered_by")
        )
        bills_qs = (
            UtilityBill.objects.filter(organization=org)
            .filter(_facility_property_filter())
            .select_related("property", "property__facility_registry", "meter", "vendor", "finance_bill")
        )
        consumptions_qs = UtilityConsumption.objects.filter(
            organization=org,
            property__facility_registry__isnull=False,
        )

        recent_consumption = consumptions_qs.filter(reading_date__gte=window_start).aggregate(
            electricity_kwh=Sum("electricity_kwh"),
            water_m3=Sum("water_m3"),
            gas_m3=Sum("gas_m3"),
            diesel_liters=Sum("diesel_liters"),
        )
        previous_window_start = window_start - timedelta(days=30)
        previous_window_end = window_start - timedelta(days=1)
        previous_consumption = consumptions_qs.filter(
            reading_date__gte=previous_window_start,
            reading_date__lte=previous_window_end,
        ).aggregate(
            electricity_kwh=Sum("electricity_kwh"),
            gas_m3=Sum("gas_m3"),
            diesel_liters=Sum("diesel_liters"),
        )

        electricity_total = _decimal(recent_consumption["electricity_kwh"])
        water_total = _decimal(recent_consumption["water_m3"])
        gas_total = _decimal(recent_consumption["gas_m3"])
        diesel_total = _decimal(recent_consumption["diesel_liters"])
        energy_total = electricity_total + gas_total + diesel_total
        previous_energy_total = (
            _decimal(previous_consumption["electricity_kwh"])
            + _decimal(previous_consumption["gas_m3"])
            + _decimal(previous_consumption["diesel_liters"])
        )
        energy_change_pct = None
        if previous_energy_total > 0:
            energy_change_pct = ((energy_total - previous_energy_total) / previous_energy_total) * Decimal("100")

        total_area_sqft = _decimal(
            Facility.objects.filter(organization=org).aggregate(total=Sum("property__total_area_sqft"))["total"]
        )
        energy_intensity = Decimal("0.00")
        water_intensity = Decimal("0.00")
        if total_area_sqft > 0:
            energy_intensity = (energy_total / total_area_sqft) * Decimal("1000")
            water_intensity = (water_total / total_area_sqft) * Decimal("1000")

        carbon_total = estimate_carbon_kg_co2e(
            electricity_kwh=electricity_total,
            water_m3=water_total,
            gas_m3=gas_total,
            diesel_liters=diesel_total,
        )
        utility_cost_30d = _decimal(
            bills_qs.filter(
                billing_period_end__gte=window_start,
            )
            .exclude(status=UtilityBill.Status.CANCELLED)
            .aggregate(total=Sum("total_amount"))["total"]
        )
        anomalous_readings_qs = readings_qs.filter(is_anomaly=True)
        overdue_bills_qs = bills_qs.filter(status=UtilityBill.Status.OVERDUE)

        monthly_rows = (
            consumptions_qs.filter(reading_date__gte=six_month_window)
            .annotate(month=TruncMonth("reading_date"))
            .values("month")
            .annotate(
                electricity_kwh=Sum("electricity_kwh"),
                water_m3=Sum("water_m3"),
                gas_m3=Sum("gas_m3"),
                diesel_liters=Sum("diesel_liters"),
            )
            .order_by("month")
        )
        monthly_trend = []
        for row in monthly_rows:
            month_value = row["month"]
            month_electricity = _decimal(row["electricity_kwh"])
            month_water = _decimal(row["water_m3"])
            month_gas = _decimal(row["gas_m3"])
            month_diesel = _decimal(row["diesel_liters"])
            monthly_trend.append(
                {
                    "month": month_value.isoformat() if month_value else None,
                    "electricity_kwh": _fmt_decimal(month_electricity),
                    "water_m3": _fmt_decimal(month_water),
                    "gas_m3": _fmt_decimal(month_gas),
                    "diesel_liters": _fmt_decimal(month_diesel),
                    "carbon_kg_co2e": _fmt_decimal(
                        estimate_carbon_kg_co2e(
                            electricity_kwh=month_electricity,
                            water_m3=month_water,
                            gas_m3=month_gas,
                            diesel_liters=month_diesel,
                        )
                    ),
                }
            )

        cost_breakdown = list(
            bills_qs.exclude(status=UtilityBill.Status.CANCELLED)
            .values("utility_type")
            .annotate(
                total_amount=Sum("total_amount"),
                usage_quantity=Sum("usage_quantity"),
                count=Count("id"),
            )
            .order_by("-total_amount", "utility_type")
        )
        sustainability_rows = []
        consumption_by_property = defaultdict(
            lambda: {
                "property_name": "",
                "facility_code": "",
                "electricity_kwh": Decimal("0"),
                "water_m3": Decimal("0"),
                "gas_m3": Decimal("0"),
                "diesel_liters": Decimal("0"),
            }
        )
        for row in consumptions_qs.filter(reading_date__gte=window_start).values(
            "property_id",
            "property__name",
            "property__facility_registry__facility_code",
        ).annotate(
            electricity_kwh=Sum("electricity_kwh"),
            water_m3=Sum("water_m3"),
            gas_m3=Sum("gas_m3"),
            diesel_liters=Sum("diesel_liters"),
        ):
            state = consumption_by_property[row["property_id"]]
            state["property_name"] = row["property__name"]
            state["facility_code"] = row["property__facility_registry__facility_code"] or ""
            state["electricity_kwh"] = _decimal(row["electricity_kwh"])
            state["water_m3"] = _decimal(row["water_m3"])
            state["gas_m3"] = _decimal(row["gas_m3"])
            state["diesel_liters"] = _decimal(row["diesel_liters"])
        for property_id, row in consumption_by_property.items():
            sustainability_rows.append(
                {
                    "property_id": property_id,
                    "property_name": row["property_name"],
                    "facility_code": row["facility_code"],
                    "carbon_kg_co2e": _fmt_decimal(
                        estimate_carbon_kg_co2e(
                            electricity_kwh=row["electricity_kwh"],
                            water_m3=row["water_m3"],
                            gas_m3=row["gas_m3"],
                            diesel_liters=row["diesel_liters"],
                        )
                    ),
                    "energy_total": _fmt_decimal(
                        row["electricity_kwh"] + row["gas_m3"] + row["diesel_liters"]
                    ),
                    "water_m3": _fmt_decimal(row["water_m3"]),
                }
            )
        sustainability_rows.sort(key=lambda item: Decimal(item["carbon_kg_co2e"]), reverse=True)

        payload = {
            "generated_at": now.isoformat(),
            "kpis": {
                "active_meters": meters_qs.filter(is_active=True).count(),
                "smart_meters": meters_qs.filter(is_active=True, is_smart_meter=True).count(),
                "readings_logged_30d": readings_qs.filter(reading_date__gte=window_start).count(),
                "anomalous_readings": anomalous_readings_qs.count(),
                "utility_cost_30d": _fmt_decimal(utility_cost_30d),
                "overdue_bills": overdue_bills_qs.count(),
                "electricity_kwh_30d": _fmt_decimal(electricity_total),
                "water_m3_30d": _fmt_decimal(water_total),
                "gas_m3_30d": _fmt_decimal(gas_total),
                "diesel_liters_30d": _fmt_decimal(diesel_total),
                "carbon_kg_co2e_30d": _fmt_decimal(carbon_total),
                "energy_intensity_per_1000_sqft": _fmt_decimal(energy_intensity),
                "water_intensity_per_1000_sqft": _fmt_decimal(water_intensity),
                "sustainability_score": _sustainability_score(
                    overdue_bills=overdue_bills_qs.count(),
                    anomalies=anomalous_readings_qs.count(),
                    energy_change_pct=energy_change_pct,
                ),
                "energy_change_vs_previous_pct": float(energy_change_pct.quantize(Decimal("0.01"))) if energy_change_pct is not None else None,
            },
            "meter_type_breakdown": list(
                meters_qs.values("utility_type").annotate(count=Count("id")).order_by("-count", "utility_type")
            ),
            "billing_status_breakdown": list(
                bills_qs.values("status").annotate(count=Count("id")).order_by("-count", "status")
            ),
            "monthly_consumption_trend": monthly_trend,
            "cost_breakdown": [
                {
                    "utility_type": row["utility_type"],
                    "total_amount": _fmt_decimal(row["total_amount"]),
                    "usage_quantity": _fmt_decimal(row["usage_quantity"]),
                    "count": row["count"],
                }
                for row in cost_breakdown
            ],
            "anomaly_watchlist": FacilityUtilityMeterReadingListSerializer(
                anomalous_readings_qs.order_by("-reading_at", "-id")[:8],
                many=True,
                context={"request": request},
            ).data,
            "recent_readings_watchlist": FacilityUtilityMeterReadingListSerializer(
                readings_qs.order_by("-reading_at", "-id")[:8],
                many=True,
                context={"request": request},
            ).data,
            "overdue_bill_watchlist": FacilityUtilityBillListSerializer(
                overdue_bills_qs.order_by("due_date", "id")[:8],
                many=True,
                context={"request": request},
            ).data,
            "sustainability_watchlist": sustainability_rows[:8],
        }
        return Response(payload)


class FacilityUtilitiesLookupsView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    rbac_action = "view"

    def get(self, request):
        org = _resolve_user_org(request)
        if org is None:
            return Response({"detail": "Organization context required."}, status=400)

        facilities = Facility.objects.filter(organization=org).select_related("property").order_by("facility_code")
        vendors = Vendor.objects.filter(
            Q(organization=org) | Q(organization__isnull=True),
            is_active=True,
        ).order_by("name")
        meters = (
            UtilityMeter.objects.filter(organization=org, property__facility_registry__isnull=False)
            .select_related("property", "property__facility_registry")
            .order_by("property__facility_registry__facility_code", "utility_type", "meter_number")
        )

        payload = {
            "facilities": [
                {
                    "id": facility.id,
                    "facility_code": facility.facility_code,
                    "property_name": facility.property.name,
                }
                for facility in facilities[:300]
            ],
            "vendors": [
                {
                    "id": vendor.id,
                    "label": vendor.name,
                    "category": vendor.category,
                }
                for vendor in vendors[:300]
            ],
            "meters": [
                {
                    "id": meter.id,
                    "facility": meter.property.facility_registry.id if hasattr(meter.property, "facility_registry") else None,
                    "facility_code": meter.property.facility_registry.facility_code if hasattr(meter.property, "facility_registry") else "",
                    "property_name": meter.property.name,
                    "meter_number": meter.meter_number,
                    "utility_type": meter.utility_type,
                    "utility_type_display": meter.get_utility_type_display(),
                    "unit_of_measure": meter.unit_of_measure,
                    "is_active": meter.is_active,
                }
                for meter in meters[:500]
            ],
        }
        return Response(payload)


class FacilityUtilitiesWorkflowView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    rbac_action = "change"

    def post(self, request):
        org = _resolve_user_org(request)
        if org is None:
            return Response({"detail": "Organization context required."}, status=400)

        result = run_utility_energy_automation(org)
        return Response(result, status=status.HTTP_200_OK)


class FacilityUtilityMeterViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "create",
        "update": "edit",
        "partial_update": "edit",
        "destroy": "delete",
    }
    queryset = UtilityMeter.objects.all()
    filterset_class = FacilityUtilityMeterFilter
    search_fields = ["meter_number", "location_label", "provider_name", "property__name"]
    ordering_fields = ["meter_number", "utility_type", "created_at", "last_reading_at"]
    ordering = ["property__name", "utility_type", "meter_number"]

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(_facility_property_filter())
            .select_related("property", "property__facility_registry", "vendor")
        )

    def get_serializer_class(self):
        if self.action == "list":
            return FacilityUtilityMeterListSerializer
        if self.action == "retrieve":
            return FacilityUtilityMeterDetailSerializer
        return FacilityUtilityMeterWriteSerializer

    def perform_create(self, serializer):
        meter = serializer.save(organization=self._resolve_request_org())
        ensure_utility_meter_defaults(meter)

    def perform_update(self, serializer):
        meter = serializer.save()
        ensure_utility_meter_defaults(meter)

    def perform_destroy(self, instance):
        property_obj = instance.property
        utility_type = instance.utility_type
        instance.delete()
        rebuild_utility_consumption_for_property(property_obj, utility_type)


class FacilityUtilityMeterReadingViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "create",
        "update": "edit",
        "partial_update": "edit",
        "destroy": "delete",
    }
    queryset = UtilityMeterReading.objects.all()
    filterset_class = FacilityUtilityMeterReadingFilter
    search_fields = ["meter__meter_number", "meter__property__name", "anomaly_reason", "notes"]
    ordering_fields = ["reading_at", "reading_date", "reading_value", "consumption_delta"]
    ordering = ["-reading_at", "-id"]

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(meter__property__facility_registry__isnull=False)
            .select_related("meter", "meter__property", "meter__property__facility_registry", "entered_by")
        )

    def get_serializer_class(self):
        if self.action == "list":
            return FacilityUtilityMeterReadingListSerializer
        if self.action == "retrieve":
            return FacilityUtilityMeterReadingDetailSerializer
        return FacilityUtilityMeterReadingWriteSerializer

    def _sync_from_reading(self, reading: UtilityMeterReading):
        recalculate_meter_reading_series(reading.meter)
        rebuild_utility_consumption_for_property(reading.meter.property, reading.meter.utility_type)
        affected_bills = UtilityBill.objects.filter(
            organization=reading.organization,
            property=reading.meter.property,
            utility_type=reading.meter.utility_type,
        ).select_related("meter", "vendor", "finance_bill", "property")
        for bill in affected_bills:
            ensure_utility_bill_defaults(bill)
            sync_finance_bill_for_utility_bill(bill)
            ensure_utility_bill_defaults(bill)

    def perform_create(self, serializer):
        reading = serializer.save(
            organization=self._resolve_request_org(),
            entered_by=self.request.user,
        )
        self._sync_from_reading(reading)

    def perform_update(self, serializer):
        reading = serializer.save()
        self._sync_from_reading(reading)

    def perform_destroy(self, instance):
        meter = instance.meter
        instance.delete()
        recalculate_meter_reading_series(meter)
        rebuild_utility_consumption_for_property(meter.property, meter.utility_type)


class FacilityUtilityBillViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "create",
        "update": "edit",
        "partial_update": "edit",
        "destroy": "delete",
    }
    queryset = UtilityBill.objects.all()
    filterset_class = FacilityUtilityBillFilter
    search_fields = ["bill_number", "provider_name", "property__name", "meter__meter_number", "vendor__name"]
    ordering_fields = ["billing_period_end", "due_date", "issue_date", "total_amount", "status"]
    ordering = ["-billing_period_end", "-issue_date", "-id"]

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(_facility_property_filter())
            .select_related("property", "property__facility_registry", "meter", "vendor", "finance_bill")
        )

    def get_serializer_class(self):
        if self.action == "list":
            return FacilityUtilityBillListSerializer
        if self.action == "retrieve":
            return FacilityUtilityBillDetailSerializer
        return FacilityUtilityBillWriteSerializer

    def perform_create(self, serializer):
        bill = serializer.save(organization=self._resolve_request_org())
        ensure_utility_bill_defaults(bill)
        sync_finance_bill_for_utility_bill(bill)
        ensure_utility_bill_defaults(bill)

    def perform_update(self, serializer):
        bill = serializer.save()
        ensure_utility_bill_defaults(bill)
        sync_finance_bill_for_utility_bill(bill)
        ensure_utility_bill_defaults(bill)
