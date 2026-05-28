from __future__ import annotations

from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone
from django_filters import rest_framework as filters
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.mixins import OrgScopedMixin
from apps.properties.maintenance_workflows import (
    OPEN_WORK_ORDER_STATUSES,
    run_maintenance_automation,
    work_order_sla_status_for,
)
from apps.properties.models import PredictiveMaintenanceAlert, PredictiveMaintenanceRule, PreventiveSchedule, WorkOrder
from apps.properties.serializers import (
    PredictiveMaintenanceAlertDetailSerializer,
    PredictiveMaintenanceAlertListSerializer,
    PredictiveMaintenanceAlertWriteSerializer,
    PredictiveMaintenanceRuleDetailSerializer,
    PredictiveMaintenanceRuleListSerializer,
    PredictiveMaintenanceRuleWriteSerializer,
    PreventiveScheduleDetailSerializer,
    PreventiveScheduleListSerializer,
    PreventiveScheduleWriteSerializer,
    WorkOrderDetailSerializer,
    WorkOrderListSerializer,
    WorkOrderWriteSerializer,
)
from apps.settings.permissions import HasRolePermission


def _resolve_user_org(request):
    org = getattr(request, "organization", None)
    if org is not None:
        return org
    profile = getattr(request.user, "profile", None)
    return getattr(profile, "organization", None)


def _facility_context_filter() -> Q:
    return (
        Q(facility__isnull=False)
        | Q(facility_space__isnull=False)
        | Q(asset_component__facility__isnull=False)
        | Q(asset_component__facility_space__isnull=False)
    )


def _work_order_location_label(work_order: WorkOrder) -> str:
    if work_order.facility_space_id:
        return work_order.facility_space.space_label or work_order.facility_space.unit.unit_number
    if work_order.unit_id:
        return work_order.unit.unit_number
    if work_order.asset_component_id:
        return work_order.asset_component.location_description or ""
    return ""


def _work_order_row(work_order: WorkOrder) -> dict[str, object]:
    return {
        "id": work_order.id,
        "title": work_order.title,
        "priority": work_order.priority,
        "status": work_order.status,
        "maintenance_mode": work_order.maintenance_mode,
        "facility_code": work_order.facility.facility_code if work_order.facility_id else "",
        "location_label": _work_order_location_label(work_order),
        "asset_component_name": work_order.asset_component.name if work_order.asset_component_id else "",
        "assigned_to": work_order.assigned_to,
        "due_date": work_order.due_date.isoformat() if work_order.due_date else None,
        "sla_due_at": work_order.sla_due_at.isoformat() if work_order.sla_due_at else None,
        "sla_status": work_order_sla_status_for(work_order),
    }


def _preventive_row(schedule: PreventiveSchedule) -> dict[str, object]:
    return {
        "id": schedule.id,
        "title": schedule.title,
        "facility_code": schedule.facility.facility_code if schedule.facility_id else "",
        "asset_component_name": schedule.asset_component.name if schedule.asset_component_id else "",
        "assigned_to": schedule.assigned_to,
        "frequency": schedule.frequency,
        "priority": schedule.priority,
        "next_due_date": schedule.next_due_date.isoformat(),
        "generate_days_before": schedule.generate_days_before,
        "last_work_order_id": schedule.last_work_order_id,
        "status": schedule.status,
    }


def _predictive_alert_row(alert: PredictiveMaintenanceAlert) -> dict[str, object]:
    return {
        "id": alert.id,
        "title": alert.title,
        "facility_code": alert.facility.facility_code if alert.facility_id else "",
        "asset_component_name": alert.asset_component.name if alert.asset_component_id else "",
        "priority": alert.priority,
        "trigger_type": alert.trigger_type,
        "status": alert.status,
        "message": alert.message,
        "work_order_id": alert.work_order_id,
        "triggered_at": alert.triggered_at.isoformat(),
    }


class FacilityMaintenanceOverviewView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    rbac_action = "view"

    def get(self, request):
        org = _resolve_user_org(request)
        if org is None:
            return Response({"detail": "Organization context required."}, status=400)

        today = timezone.localdate()
        now = timezone.now()
        next_30_days = today + timedelta(days=30)

        work_orders_qs = (
            WorkOrder.objects.filter(organization=org)
            .filter(_facility_context_filter())
            .select_related(
                "facility",
                "facility_space",
                "facility_space__unit",
                "unit",
                "asset_component",
            )
        )
        open_work_orders_qs = work_orders_qs.filter(status__in=OPEN_WORK_ORDER_STATUSES)
        at_risk_work_orders = [row for row in open_work_orders_qs if work_order_sla_status_for(row, now=now) == "at_risk"]
        overdue_work_orders = [row for row in open_work_orders_qs if work_order_sla_status_for(row, now=now) == "overdue"]

        schedules_qs = (
            PreventiveSchedule.objects.filter(organization=org)
            .filter(
                Q(facility__isnull=False)
                | Q(facility_space__isnull=False)
                | Q(asset_component__facility__isnull=False)
                | Q(asset_component__facility_space__isnull=False)
            )
            .select_related("facility", "asset_component", "last_work_order")
        )
        active_schedules_qs = schedules_qs.filter(status=PreventiveSchedule.Status.ACTIVE)

        predictive_rules_qs = (
            PredictiveMaintenanceRule.objects.filter(organization=org)
            .filter(
                Q(facility__isnull=False)
                | Q(facility_space__isnull=False)
                | Q(asset_component__facility__isnull=False)
                | Q(asset_component__facility_space__isnull=False)
            )
        )
        predictive_alerts_qs = (
            PredictiveMaintenanceAlert.objects.filter(organization=org)
            .filter(
                Q(facility__isnull=False)
                | Q(facility_space__isnull=False)
                | Q(asset_component__facility__isnull=False)
                | Q(asset_component__facility_space__isnull=False)
            )
            .select_related("facility", "asset_component", "work_order")
        )

        payload = {
            "generated_at": now.isoformat(),
            "kpis": {
                "open_work_orders": open_work_orders_qs.count(),
                "in_progress_work_orders": open_work_orders_qs.filter(status=WorkOrder.Status.IN_PROGRESS).count(),
                "verified_work_orders": work_orders_qs.filter(status=WorkOrder.Status.VERIFIED).count(),
                "completed_today": work_orders_qs.filter(completed_date=today).count(),
                "sla_at_risk": len(at_risk_work_orders),
                "sla_overdue": len(overdue_work_orders),
                "breakdown_open": open_work_orders_qs.filter(is_breakdown=True).count(),
                "preventive_active": active_schedules_qs.count(),
                "preventive_due_30_days": active_schedules_qs.filter(
                    next_due_date__gte=today,
                    next_due_date__lte=next_30_days,
                ).count(),
                "preventive_overdue": active_schedules_qs.filter(next_due_date__lt=today).count(),
                "predictive_rules_active": predictive_rules_qs.filter(is_active=True).count(),
                "predictive_alerts_open": predictive_alerts_qs.filter(
                    status__in=[
                        PredictiveMaintenanceAlert.Status.OPEN,
                        PredictiveMaintenanceAlert.Status.ACKNOWLEDGED,
                        PredictiveMaintenanceAlert.Status.WORK_ORDER_CREATED,
                    ]
                ).count(),
            },
            "priority_breakdown": list(
                work_orders_qs.values("priority").annotate(count=Count("id")).order_by("-count", "priority")
            ),
            "status_breakdown": list(
                work_orders_qs.values("status").annotate(count=Count("id")).order_by("-count", "status")
            ),
            "work_orders_watchlist": [
                _work_order_row(item)
                for item in sorted(
                    list(open_work_orders_qs),
                    key=lambda row: (
                        row.sla_due_at or (now + timedelta(days=3650)),
                        row.due_date or (today + timedelta(days=3650)),
                        row.id,
                    ),
                )[:8]
            ],
            "preventive_watchlist": [
                _preventive_row(item)
                for item in active_schedules_qs.order_by("next_due_date")[:8]
            ],
            "predictive_alerts_watchlist": [
                _predictive_alert_row(item)
                for item in predictive_alerts_qs.exclude(status=PredictiveMaintenanceAlert.Status.RESOLVED).order_by("-triggered_at")[:8]
            ],
        }
        return Response(payload)


class FacilityMaintenanceWorkflowView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    rbac_action = "change"

    def post(self, request):
        org = _resolve_user_org(request)
        if org is None:
            return Response({"detail": "Organization context required."}, status=400)

        raw_rule_ids = request.data.get("rule_ids") or []
        rule_ids = [int(value) for value in raw_rule_ids if str(value).isdigit()]
        result = run_maintenance_automation(org, rule_ids=rule_ids or None)
        return Response(result, status=status.HTTP_200_OK)


class FacilityMaintenanceWorkOrderFilter(filters.FilterSet):
    reported_after = filters.DateFilter(field_name="reported_date", lookup_expr="gte")
    reported_before = filters.DateFilter(field_name="reported_date", lookup_expr="lte")

    class Meta:
        model = WorkOrder
        fields = [
            "property",
            "facility",
            "facility_space",
            "asset_component",
            "vendor",
            "category",
            "priority",
            "status",
            "maintenance_mode",
            "is_breakdown",
        ]


class FacilityMaintenanceWorkOrderViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    filterset_class = FacilityMaintenanceWorkOrderFilter
    search_fields = ["title", "description", "assigned_to", "reported_by", "root_cause"]
    ordering_fields = ["created_at", "due_date", "priority", "status", "sla_due_at"]
    ordering = ["-created_at"]
    queryset = WorkOrder.objects.all()

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(_facility_context_filter())
            .select_related(
                "property",
                "facility",
                "facility__property",
                "facility_space",
                "facility_space__unit",
                "unit",
                "vendor",
                "asset_component",
                "preventive_schedule",
            )
        )

    def get_serializer_class(self):
        if self.action == "list":
            return WorkOrderListSerializer
        if self.action in ("create", "update", "partial_update"):
            return WorkOrderWriteSerializer
        return WorkOrderDetailSerializer

    @action(detail=False, methods=["post"], url_path="run-automation")
    def run_automation(self, request):
        org = _resolve_user_org(request)
        if org is None:
            return Response({"detail": "Organization context required."}, status=400)
        return Response(run_maintenance_automation(org), status=status.HTTP_200_OK)


class FacilityMaintenancePreventiveFilter(filters.FilterSet):
    due_before = filters.DateFilter(field_name="next_due_date", lookup_expr="lte")
    due_after = filters.DateFilter(field_name="next_due_date", lookup_expr="gte")

    class Meta:
        model = PreventiveSchedule
        fields = [
            "property",
            "facility",
            "facility_space",
            "asset_component",
            "vendor",
            "category",
            "frequency",
            "status",
        ]


class FacilityMaintenancePreventiveViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    filterset_class = FacilityMaintenancePreventiveFilter
    search_fields = ["title", "description", "assigned_to"]
    ordering_fields = ["next_due_date", "created_at", "frequency", "priority"]
    ordering = ["next_due_date"]
    queryset = PreventiveSchedule.objects.all()

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(
                Q(facility__isnull=False)
                | Q(facility_space__isnull=False)
                | Q(asset_component__facility__isnull=False)
                | Q(asset_component__facility_space__isnull=False)
            )
            .select_related(
                "property",
                "facility",
                "facility__property",
                "facility_space",
                "facility_space__unit",
                "asset_component",
                "vendor",
                "last_work_order",
            )
        )

    def get_serializer_class(self):
        if self.action == "list":
            return PreventiveScheduleListSerializer
        if self.action in ("create", "update", "partial_update"):
            return PreventiveScheduleWriteSerializer
        return PreventiveScheduleDetailSerializer


class FacilityMaintenancePredictiveRuleFilter(filters.FilterSet):
    class Meta:
        model = PredictiveMaintenanceRule
        fields = ["property", "facility", "facility_space", "asset_component", "priority", "is_active"]


class FacilityMaintenancePredictiveRuleViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    filterset_class = FacilityMaintenancePredictiveRuleFilter
    search_fields = ["title", "description", "assigned_to"]
    ordering_fields = ["title", "priority", "created_at", "last_triggered_at"]
    ordering = ["title", "id"]
    queryset = PredictiveMaintenanceRule.objects.all()

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(
                Q(facility__isnull=False)
                | Q(facility_space__isnull=False)
                | Q(asset_component__facility__isnull=False)
                | Q(asset_component__facility_space__isnull=False)
            )
            .select_related(
                "property",
                "facility",
                "facility__property",
                "facility_space",
                "facility_space__unit",
                "asset_component",
            )
        )

    def get_serializer_class(self):
        if self.action == "list":
            return PredictiveMaintenanceRuleListSerializer
        if self.action in ("create", "update", "partial_update"):
            return PredictiveMaintenanceRuleWriteSerializer
        return PredictiveMaintenanceRuleDetailSerializer

    @action(detail=True, methods=["post"], url_path="evaluate")
    def evaluate(self, request, pk=None):
        org = _resolve_user_org(request)
        if org is None:
            return Response({"detail": "Organization context required."}, status=400)
        return Response(run_maintenance_automation(org, rule_ids=[int(pk)]), status=status.HTTP_200_OK)


class FacilityMaintenancePredictiveAlertFilter(filters.FilterSet):
    triggered_after = filters.DateTimeFilter(field_name="triggered_at", lookup_expr="gte")
    triggered_before = filters.DateTimeFilter(field_name="triggered_at", lookup_expr="lte")

    class Meta:
        model = PredictiveMaintenanceAlert
        fields = ["rule", "property", "facility", "facility_space", "asset_component", "status", "trigger_type"]


class FacilityMaintenancePredictiveAlertViewSet(
    OrgScopedMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    filterset_class = FacilityMaintenancePredictiveAlertFilter
    search_fields = ["title", "message", "notes"]
    ordering_fields = ["triggered_at", "priority", "status"]
    ordering = ["-triggered_at"]
    queryset = PredictiveMaintenanceAlert.objects.all()

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(
                Q(facility__isnull=False)
                | Q(facility_space__isnull=False)
                | Q(asset_component__facility__isnull=False)
                | Q(asset_component__facility_space__isnull=False)
            )
            .select_related(
                "rule",
                "property",
                "facility",
                "facility_space",
                "asset_component",
                "work_order",
            )
        )

    def get_serializer_class(self):
        if self.action == "list":
            return PredictiveMaintenanceAlertListSerializer
        if self.action in ("update", "partial_update"):
            return PredictiveMaintenanceAlertWriteSerializer
        return PredictiveMaintenanceAlertDetailSerializer
