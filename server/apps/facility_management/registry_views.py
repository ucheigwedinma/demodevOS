from datetime import timedelta

from django.db.models import Count
from django.utils import timezone
from django_filters import rest_framework as filters
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.mixins import OrgScopedMixin
from apps.properties.models import Unit
from apps.properties.serializers import UnitSerializer
from apps.settings.permissions import HasRolePermission

from .models import Facility, FacilityFloor, FacilityUnitSpace, FacilityZone
from .serializers import (
    FacilityDetailSerializer,
    FacilityFloorDetailSerializer,
    FacilityFloorListSerializer,
    FacilityFloorWriteSerializer,
    FacilityListSerializer,
    FacilityUnitSpaceDetailSerializer,
    FacilityUnitSpaceListSerializer,
    FacilityUnitSpaceWriteSerializer,
    FacilityWriteSerializer,
    FacilityZoneDetailSerializer,
    FacilityZoneListSerializer,
    FacilityZoneWriteSerializer,
)


def _resolve_user_org(request):
    org = getattr(request, "organization", None)
    if org is not None:
        return org
    profile = getattr(request.user, "profile", None)
    return getattr(profile, "organization", None)


class FacilityRegistryOverviewView(APIView):
    """Aggregated registry metrics for facilities, hierarchy, and lease posture."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    rbac_action = "view"

    def get(self, request):
        org = _resolve_user_org(request)
        if org is None:
            return Response({"detail": "Organization context required."}, status=400)

        today = timezone.localdate()
        lease_horizon = today + timedelta(days=90)

        facilities_qs = Facility.objects.filter(organization=org)
        floors_qs = FacilityFloor.objects.filter(organization=org)
        zones_qs = FacilityZone.objects.filter(organization=org)
        spaces_qs = FacilityUnitSpace.objects.filter(organization=org)

        classification_breakdown = list(
            facilities_qs.values("facility_classification")
            .annotate(count=Count("id"))
            .order_by("-count", "facility_classification")
        )
        ownership_breakdown = list(
            facilities_qs.values("ownership_type")
            .annotate(count=Count("id"))
            .order_by("-count", "ownership_type")
        )
        facility_type_breakdown = list(
            facilities_qs.values("property__property_type")
            .annotate(count=Count("id"))
            .order_by("-count", "property__property_type")
        )

        payload = {
            "generated_at": timezone.now().isoformat(),
            "kpis": {
                "facilities": facilities_qs.count(),
                "floors": floors_qs.count(),
                "zones": zones_qs.count(),
                "unit_spaces": spaces_qs.count(),
                "leased_facilities": facilities_qs.filter(ownership_type=Facility.OwnershipType.LEASED).count(),
                "lease_expiring_90_days": facilities_qs.filter(
                    ownership_type=Facility.OwnershipType.LEASED,
                    lease_end_date__isnull=False,
                    lease_end_date__gte=today,
                    lease_end_date__lte=lease_horizon,
                ).count(),
            },
            "classification_breakdown": [
                {
                    "key": row["facility_classification"],
                    "count": row["count"],
                }
                for row in classification_breakdown
            ],
            "ownership_breakdown": [
                {
                    "key": row["ownership_type"],
                    "count": row["count"],
                }
                for row in ownership_breakdown
            ],
            "facility_type_breakdown": [
                {
                    "key": row["property__property_type"],
                    "count": row["count"],
                }
                for row in facility_type_breakdown
            ],
        }
        return Response(payload)


class FacilityFilter(filters.FilterSet):
    lease_expiring_before = filters.DateFilter(field_name="lease_end_date", lookup_expr="lte")
    lease_expiring_after = filters.DateFilter(field_name="lease_end_date", lookup_expr="gte")
    property_type = filters.CharFilter(field_name="property__property_type")

    class Meta:
        model = Facility
        fields = ["facility_classification", "ownership_type", "property", "property_type"]


class FacilityViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    filterset_class = FacilityFilter
    search_fields = ["facility_code", "property__name", "property__address", "lease_party_name"]
    ordering_fields = [
        "facility_code",
        "facility_classification",
        "ownership_type",
        "property__name",
        "lease_end_date",
        "created_at",
    ]
    ordering = ["property__name"]
    queryset = Facility.objects.all()

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("property")
            .annotate(
                floors_count=Count("floors", distinct=True),
                zones_count=Count("zones", distinct=True),
                unit_spaces_count=Count("unit_spaces", distinct=True),
            )
        )

    def get_serializer_class(self):
        if self.action == "list":
            return FacilityListSerializer
        if self.action in ("create", "update", "partial_update"):
            return FacilityWriteSerializer
        return FacilityDetailSerializer


class FacilityFloorFilter(filters.FilterSet):
    class Meta:
        model = FacilityFloor
        fields = ["facility", "is_active"]


class FacilityFloorViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    filterset_class = FacilityFloorFilter
    search_fields = ["name", "floor_code", "facility__facility_code", "facility__property__name"]
    ordering_fields = ["floor_number", "name", "facility__property__name", "created_at"]
    ordering = ["facility__property__name", "floor_number", "name"]
    queryset = FacilityFloor.objects.all()

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("facility", "facility__property")
            .annotate(zone_count=Count("zones", distinct=True))
        )

    def get_serializer_class(self):
        if self.action == "list":
            return FacilityFloorListSerializer
        if self.action in ("create", "update", "partial_update"):
            return FacilityFloorWriteSerializer
        return FacilityFloorDetailSerializer


class FacilityZoneFilter(filters.FilterSet):
    class Meta:
        model = FacilityZone
        fields = ["facility", "floor", "zone_type", "is_active"]


class FacilityZoneViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    filterset_class = FacilityZoneFilter
    search_fields = ["name", "zone_code", "facility__facility_code", "floor__name"]
    ordering_fields = ["facility__property__name", "floor__floor_number", "name", "zone_code", "created_at"]
    ordering = ["facility__property__name", "floor__floor_number", "name"]
    queryset = FacilityZone.objects.all()

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("facility", "facility__property", "floor")
            .annotate(unit_spaces_count=Count("unit_spaces", distinct=True))
        )

    def get_serializer_class(self):
        if self.action == "list":
            return FacilityZoneListSerializer
        if self.action in ("create", "update", "partial_update"):
            return FacilityZoneWriteSerializer
        return FacilityZoneDetailSerializer


class FacilityUnitSpaceFilter(filters.FilterSet):
    unit_status = filters.CharFilter(field_name="unit__status")

    class Meta:
        model = FacilityUnitSpace
        fields = ["facility", "zone", "unit", "unit_status"]


class FacilityUnitSpaceViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    filterset_class = FacilityUnitSpaceFilter
    search_fields = [
        "space_label",
        "unit__unit_number",
        "zone__name",
        "zone__zone_code",
        "facility__facility_code",
        "facility__property__name",
    ]
    ordering_fields = [
        "facility__property__name",
        "zone__floor__floor_number",
        "zone__name",
        "unit__unit_number",
        "created_at",
    ]
    ordering = ["facility__property__name", "zone__floor__floor_number", "zone__name", "unit__unit_number"]
    queryset = FacilityUnitSpace.objects.all()

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related(
                "facility",
                "facility__property",
                "zone",
                "zone__floor",
                "unit",
                "unit__property",
            )
        )

    def get_serializer_class(self):
        if self.action == "list":
            return FacilityUnitSpaceListSerializer
        if self.action in ("create", "update", "partial_update"):
            return FacilityUnitSpaceWriteSerializer
        return FacilityUnitSpaceDetailSerializer


class FacilityAvailableUnitFilter(filters.FilterSet):
    facility = filters.NumberFilter(method="filter_facility")

    class Meta:
        model = Unit
        fields = ["facility", "property", "status"]

    def filter_facility(self, queryset, name, value):
        property_id = Facility.objects.filter(pk=value).values_list("property_id", flat=True).first()
        if not property_id:
            return queryset.none()
        return queryset.filter(property_id=property_id)


class FacilityAvailableUnitViewSet(OrgScopedMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    serializer_class = UnitSerializer
    filterset_class = FacilityAvailableUnitFilter
    search_fields = ["unit_number", "property__name"]
    ordering_fields = ["unit_number", "floor", "created_at"]
    ordering = ["unit_number"]
    queryset = Unit.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset().select_related("property")
        include_mapped = self.request.query_params.get("include_mapped")
        if include_mapped not in {"1", "true", "True"}:
            queryset = queryset.filter(facility_space__isnull=True)
        return queryset
