from django.db.models import Count
from django_filters import rest_framework as filters
from rest_framework import parsers, viewsets
from rest_framework import status as http_status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.mixins import OrgScopedMixin
from apps.settings.permissions import HasRolePermission

from .models import (
    AssetComponent,
    Inspection,
    MaintenanceVendor,
    PreventiveSchedule,
    Property,
    PropertyDocument,
    PropertyEncumbrance,
    PropertyImage,
    PropertyInventory,
    PropertyInventoryEvent,
    PropertyOwnership,
    PropertyValuation,
    ServiceRequest,
    Unit,
    WorkOrder,
)
from .serializers import (
    AssetComponentDetailSerializer,
    AssetComponentListSerializer,
    AssetComponentWriteSerializer,
    InspectionDetailSerializer,
    InspectionListSerializer,
    InspectionWriteSerializer,
    MaintenanceVendorDetailSerializer,
    MaintenanceVendorListSerializer,
    MaintenanceVendorWriteSerializer,
    PreventiveScheduleDetailSerializer,
    PreventiveScheduleListSerializer,
    PreventiveScheduleWriteSerializer,
    PropertyDetailSerializer,
    PropertyDocumentSerializer,
    PropertyEncumbranceSerializer,
    PropertyImageSerializer,
    PropertyInventoryDetailSerializer,
    PropertyInventoryEventSerializer,
    PropertyInventoryListSerializer,
    PropertyInventoryWriteSerializer,
    PropertyListSerializer,
    PropertyOwnershipSerializer,
    PropertyValuationSerializer,
    PropertyWriteSerializer,
    ServiceRequestDetailSerializer,
    ServiceRequestListSerializer,
    ServiceRequestWriteSerializer,
    UnitSerializer,
    WorkOrderDetailSerializer,
    WorkOrderListSerializer,
    WorkOrderWriteSerializer,
)


class PropertyFilter(filters.FilterSet):
    min_value = filters.NumberFilter(field_name="current_value", lookup_expr="gte")
    max_value = filters.NumberFilter(field_name="current_value", lookup_expr="lte")
    min_area = filters.NumberFilter(field_name="total_area_sqft", lookup_expr="gte")
    max_area = filters.NumberFilter(field_name="total_area_sqft", lookup_expr="lte")
    acquired_after = filters.DateFilter(field_name="acquisition_date", lookup_expr="gte")
    acquired_before = filters.DateFilter(field_name="acquisition_date", lookup_expr="lte")

    class Meta:
        model = Property
        fields = ["property_type", "classification", "is_active"]


class PropertyViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    filterset_class = PropertyFilter
    search_fields = ["name", "address", "description"]
    ordering_fields = ["name", "created_at", "current_value", "total_area_sqft", "acquisition_date"]
    ordering = ["-created_at"]
    queryset = Property.objects.all()

    def get_queryset(self):
        return super().get_queryset().annotate(unit_count=Count("units"))

    def perform_create(self, serializer):
        from apps.settings.quotas import check_resource_quota

        org = self._resolve_request_org()
        check_resource_quota(org, Property, "max_properties", "properties")
        super().perform_create(serializer)

    def get_serializer_class(self):
        if self.action == "list":
            return PropertyListSerializer
        if self.action in ("create", "update", "partial_update"):
            return PropertyWriteSerializer
        return PropertyDetailSerializer


class PropertyUnitViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.units"
    serializer_class = UnitSerializer
    queryset = Unit.objects.all()

    def get_queryset(self):
        return super().get_queryset().filter(property_id=self.kwargs["property_pk"])

    def perform_create(self, serializer):
        serializer.save(property_id=self.kwargs["property_pk"], organization=self.request.organization)


class PropertyImageViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.images"
    rbac_action_map = {
        "list": "view", "retrieve": "view", "create": "create",
        "update": "edit", "partial_update": "edit", "destroy": "delete",
        "set_primary": "edit",
    }
    serializer_class = PropertyImageSerializer
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]
    queryset = PropertyImage.objects.all()

    def get_queryset(self):
        return super().get_queryset().filter(property_id=self.kwargs["property_pk"])

    def perform_create(self, serializer):
        serializer.save(property_id=self.kwargs["property_pk"], organization=self.request.organization)

    @action(detail=True, methods=["post"])
    def set_primary(self, request, property_pk=None, pk=None):
        image = self.get_object()
        PropertyImage.objects.filter(
            property_id=property_pk, is_primary=True
        ).update(is_primary=False)
        image.is_primary = True
        image.save(update_fields=["is_primary"])
        return Response(PropertyImageSerializer(image, context={"request": request}).data)


class PropertyDocumentViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.documents"
    serializer_class = PropertyDocumentSerializer
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]
    queryset = PropertyDocument.objects.all()

    def get_queryset(self):
        return super().get_queryset().filter(property_id=self.kwargs["property_pk"])

    def perform_create(self, serializer):
        serializer.save(property_id=self.kwargs["property_pk"], organization=self.request.organization)


class PropertyValuationViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.valuations"
    serializer_class = PropertyValuationSerializer
    queryset = PropertyValuation.objects.all()

    def get_queryset(self):
        return super().get_queryset().filter(property_id=self.kwargs["property_pk"])

    def perform_create(self, serializer):
        serializer.save(property_id=self.kwargs["property_pk"], organization=self.request.organization)


class PropertyOwnershipViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.ownerships"
    serializer_class = PropertyOwnershipSerializer
    queryset = PropertyOwnership.objects.all()

    def get_queryset(self):
        return super().get_queryset().filter(
            property_id=self.kwargs["property_pk"]
        )

    def perform_create(self, serializer):
        serializer.save(property_id=self.kwargs["property_pk"], organization=self.request.organization)


class PropertyEncumbranceViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.encumbrances"
    serializer_class = PropertyEncumbranceSerializer
    queryset = PropertyEncumbrance.objects.all()

    def get_queryset(self):
        return super().get_queryset().filter(
            property_id=self.kwargs["property_pk"]
        )

    def perform_create(self, serializer):
        serializer.save(property_id=self.kwargs["property_pk"], organization=self.request.organization)


# ---------------------------------------------------------------------------
# Maintenance Vendor
# ---------------------------------------------------------------------------

class MaintenanceVendorFilter(filters.FilterSet):
    class Meta:
        model = MaintenanceVendor
        fields = ["specialization", "is_active"]


class MaintenanceVendorViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    filterset_class = MaintenanceVendorFilter
    search_fields = ["name", "contact_person", "email", "license_number"]
    ordering_fields = ["name", "rating", "created_at"]
    ordering = ["name"]
    queryset = MaintenanceVendor.objects.all()

    def get_queryset(self):
        return super().get_queryset().annotate(
            work_order_count=Count("work_orders")
        )

    def get_serializer_class(self):
        if self.action == "list":
            return MaintenanceVendorListSerializer
        if self.action in ("create", "update", "partial_update"):
            return MaintenanceVendorWriteSerializer
        return MaintenanceVendorDetailSerializer


# ---------------------------------------------------------------------------
# Asset Component Register
# ---------------------------------------------------------------------------

class AssetComponentFilter(filters.FilterSet):
    warranty_before = filters.DateFilter(field_name="warranty_expiry", lookup_expr="lte")
    warranty_after = filters.DateFilter(field_name="warranty_expiry", lookup_expr="gte")
    maintenance_due_before = filters.DateFilter(field_name="maintenance_next_due_date", lookup_expr="lte")
    maintenance_due_after = filters.DateFilter(field_name="maintenance_next_due_date", lookup_expr="gte")
    amc_before = filters.DateFilter(field_name="amc_end_date", lookup_expr="lte")
    amc_after = filters.DateFilter(field_name="amc_end_date", lookup_expr="gte")

    class Meta:
        model = AssetComponent
        fields = [
            "property",
            "facility",
            "facility_space",
            "unit",
            "vendor",
            "category",
            "lifecycle_stage",
            "condition_rating",
            "depreciation_enabled",
            "is_iot_enabled",
            "is_active",
        ]


class AssetComponentViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    filterset_class = AssetComponentFilter
    search_fields = ["component_id", "name", "manufacturer", "model_number", "serial_number"]
    ordering_fields = ["component_id", "name", "installation_date", "warranty_expiry", "created_at"]
    ordering = ["component_id"]
    queryset = AssetComponent.objects.all()

    def get_queryset(self):
        return super().get_queryset().select_related(
            "property",
            "facility",
            "facility__property",
            "facility_space",
            "facility_space__unit",
            "unit",
            "vendor",
            "amc_vendor",
        )

    def get_serializer_class(self):
        if self.action == "list":
            return AssetComponentListSerializer
        if self.action in ("create", "update", "partial_update"):
            return AssetComponentWriteSerializer
        return AssetComponentDetailSerializer


# ---------------------------------------------------------------------------
# Work Order (Corrective / Reactive Maintenance)
# ---------------------------------------------------------------------------

class WorkOrderFilter(filters.FilterSet):
    reported_after = filters.DateFilter(field_name="reported_date", lookup_expr="gte")
    reported_before = filters.DateFilter(field_name="reported_date", lookup_expr="lte")

    class Meta:
        model = WorkOrder
        fields = [
            "property",
            "facility",
            "facility_space",
            "unit",
            "asset_component",
            "vendor",
            "category",
            "priority",
            "status",
            "maintenance_mode",
            "is_breakdown",
        ]


class WorkOrderViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    filterset_class = WorkOrderFilter
    search_fields = ["title", "description", "assigned_to", "reported_by"]
    ordering_fields = ["created_at", "due_date", "priority", "status"]
    ordering = ["-created_at"]
    queryset = WorkOrder.objects.all()

    def get_queryset(self):
        return super().get_queryset().select_related(
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

    def get_serializer_class(self):
        if self.action == "list":
            return WorkOrderListSerializer
        if self.action in ("create", "update", "partial_update"):
            return WorkOrderWriteSerializer
        return WorkOrderDetailSerializer


# ---------------------------------------------------------------------------
# Preventive Maintenance Schedule
# ---------------------------------------------------------------------------

class PreventiveScheduleFilter(filters.FilterSet):
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


class PreventiveScheduleViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    filterset_class = PreventiveScheduleFilter
    search_fields = ["title", "description", "assigned_to"]
    ordering_fields = ["next_due_date", "created_at", "frequency"]
    ordering = ["next_due_date"]
    queryset = PreventiveSchedule.objects.all()

    def get_queryset(self):
        return super().get_queryset().select_related(
            "property",
            "facility",
            "facility__property",
            "facility_space",
            "facility_space__unit",
            "asset_component",
            "vendor",
            "last_work_order",
        )

    def get_serializer_class(self):
        if self.action == "list":
            return PreventiveScheduleListSerializer
        if self.action in ("create", "update", "partial_update"):
            return PreventiveScheduleWriteSerializer
        return PreventiveScheduleDetailSerializer


# ---------------------------------------------------------------------------
# Inspection
# ---------------------------------------------------------------------------

class InspectionFilter(filters.FilterSet):
    scheduled_after = filters.DateFilter(field_name="scheduled_date", lookup_expr="gte")
    scheduled_before = filters.DateFilter(field_name="scheduled_date", lookup_expr="lte")
    expiry_before = filters.DateFilter(field_name="expiry_date", lookup_expr="lte")
    expiry_after = filters.DateFilter(field_name="expiry_date", lookup_expr="gte")

    class Meta:
        model = Inspection
        fields = [
            "property", "unit", "asset_component", "inspection_type",
            "status", "rating", "follow_up_required",
            "risk_level", "corrective_action_required", "compliance_status",
        ]


class InspectionViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    filterset_class = InspectionFilter
    search_fields = ["title", "inspector", "findings"]
    ordering_fields = ["scheduled_date", "completed_date", "created_at"]
    ordering = ["-scheduled_date"]
    queryset = Inspection.objects.all()

    def get_queryset(self):
        return super().get_queryset().select_related("property", "unit", "asset_component")

    def get_serializer_class(self):
        if self.action == "list":
            return InspectionListSerializer
        if self.action in ("create", "update", "partial_update"):
            return InspectionWriteSerializer
        return InspectionDetailSerializer


# ---------------------------------------------------------------------------
# Service Request
# ---------------------------------------------------------------------------

class ServiceRequestFilter(filters.FilterSet):
    requested_after = filters.DateFilter(field_name="requested_date", lookup_expr="gte")
    requested_before = filters.DateFilter(field_name="requested_date", lookup_expr="lte")

    class Meta:
        model = ServiceRequest
        fields = ["property", "unit", "category", "priority", "status"]


class ServiceRequestViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    filterset_class = ServiceRequestFilter
    search_fields = ["title", "description", "requested_by", "assigned_to"]
    ordering_fields = ["created_at", "requested_date", "priority", "status"]
    ordering = ["-created_at"]
    queryset = ServiceRequest.objects.all()

    def get_queryset(self):
        return super().get_queryset().select_related("property", "unit", "work_order")

    def get_serializer_class(self):
        if self.action == "list":
            return ServiceRequestListSerializer
        if self.action in ("create", "update", "partial_update"):
            return ServiceRequestWriteSerializer
        return ServiceRequestDetailSerializer


class UnitViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.units"
    queryset = Unit.objects.select_related("property").all()
    serializer_class = UnitSerializer
    search_fields = ["unit_number", "property__name"]
    filterset_fields = ["status", "property"]
    ordering_fields = ["unit_number", "asking_price", "area_sqft", "created_at"]


# ---------------------------------------------------------------------------
# Property Inventory
# ---------------------------------------------------------------------------

class PropertyInventoryFilter(filters.FilterSet):
    property = filters.NumberFilter(field_name="unit__property_id")

    class Meta:
        model = PropertyInventory
        fields = ["status", "property"]


class PropertyInventoryViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    filterset_class = PropertyInventoryFilter
    search_fields = ["unit__unit_number", "unit__property__name", "held_by", "allocated_to"]
    ordering_fields = ["status", "updated_at", "created_at", "list_price"]
    ordering = ["-updated_at"]
    queryset = PropertyInventory.objects.all()

    def get_queryset(self):
        return super().get_queryset().select_related("unit__property")

    def get_serializer_class(self):
        if self.action == "list":
            return PropertyInventoryListSerializer
        if self.action in ("create", "update", "partial_update"):
            return PropertyInventoryWriteSerializer
        return PropertyInventoryDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=self.request.organization)

    @action(detail=True, methods=["post"])
    def hold(self, request, pk=None):
        """Place a hold on a unit inventory record."""
        inventory = self.get_object()
        if inventory.status not in ("available",):
            return Response(
                {"detail": f"Cannot hold a unit that is currently '{inventory.get_status_display()}'."},
                status=http_status.HTTP_400_BAD_REQUEST,
            )
        held_by = request.data.get("held_by", "")
        held_until = request.data.get("held_until")
        notes = request.data.get("notes", "")

        old_status = inventory.status
        inventory.status = PropertyInventory.InventoryStatus.HELD
        inventory.held_by = held_by
        inventory.held_until = held_until
        inventory.save(update_fields=["status", "held_by", "held_until", "updated_at"])

        PropertyInventoryEvent.objects.create(
            organization=inventory.organization,
            inventory=inventory,
            event_type=PropertyInventoryEvent.EventType.HELD,
            from_status=old_status,
            to_status=inventory.status,
            actor_name=request.user.get_full_name() or request.user.email,
            actor_user=request.user,
            hold_expires_at=held_until,
            notes=notes,
        )
        return Response(PropertyInventoryDetailSerializer(inventory).data)

    @action(detail=True, methods=["post"])
    def release(self, request, pk=None):
        """Release a hold on a unit inventory record."""
        inventory = self.get_object()
        if inventory.status not in ("held",):
            return Response(
                {"detail": f"Cannot release a unit that is currently '{inventory.get_status_display()}'."},
                status=http_status.HTTP_400_BAD_REQUEST,
            )
        notes = request.data.get("notes", "")

        old_status = inventory.status
        inventory.status = PropertyInventory.InventoryStatus.AVAILABLE
        inventory.held_by = ""
        inventory.held_until = None
        inventory.save(update_fields=["status", "held_by", "held_until", "updated_at"])

        PropertyInventoryEvent.objects.create(
            organization=inventory.organization,
            inventory=inventory,
            event_type=PropertyInventoryEvent.EventType.HOLD_RELEASED,
            from_status=old_status,
            to_status=inventory.status,
            actor_name=request.user.get_full_name() or request.user.email,
            actor_user=request.user,
            notes=notes,
        )
        return Response(PropertyInventoryDetailSerializer(inventory).data)


class PropertyInventoryEventViewSet(OrgScopedMixin, viewsets.ReadOnlyModelViewSet):
    """Read-only audit trail for a specific inventory record."""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    serializer_class = PropertyInventoryEventSerializer
    ordering = ["-created_at"]
    queryset = PropertyInventoryEvent.objects.all()

    def get_queryset(self):
        return super().get_queryset().filter(
            inventory_id=self.kwargs["inventory_pk"]
        )
