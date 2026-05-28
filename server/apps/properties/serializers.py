from django.utils import timezone
from rest_framework import serializers

from .asset_workflows import (
    accumulated_depreciation_for,
    amc_status_for,
    current_book_value_for,
    derive_maintenance_due_date,
    maintenance_status_for,
    monthly_depreciation_for,
    warranty_status_for,
)
from .maintenance_workflows import (
    normalize_predictive_rule_payload,
    normalize_preventive_schedule_payload,
    normalize_work_order_payload,
    work_order_sla_status_for,
)
from .models import (
    AssetComponent,
    Inspection,
    MaintenanceVendor,
    PredictiveMaintenanceAlert,
    PredictiveMaintenanceRule,
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


def _resolve_request_org(request):
    org = getattr(request, "organization", None)
    if org is not None:
        return org
    profile = getattr(getattr(request, "user", None), "profile", None)
    return getattr(profile, "organization", None)


class PropertyInventoryInlineSerializer(serializers.ModelSerializer):
    """Minimal inventory data nested inside unit responses."""

    class Meta:
        model = PropertyInventory
        fields = [
            "id", "status", "held_by", "held_until",
            "allocated_to", "allocated_on", "list_price",
            "notes", "updated_at",
        ]
        read_only_fields = ("id", "updated_at")


class UnitSerializer(serializers.ModelSerializer):
    inventory = PropertyInventoryInlineSerializer(read_only=True)

    class Meta:
        model = Unit
        fields = "__all__"
        read_only_fields = ("id", "property", "created_at", "updated_at")

    def validate_gps_latitude(self, value):
        if value is not None and (value < -90 or value > 90):
            raise serializers.ValidationError("Latitude must be between -90 and 90.")
        return value

    def validate_gps_longitude(self, value):
        if value is not None and (value < -180 or value > 180):
            raise serializers.ValidationError("Longitude must be between -180 and 180.")
        return value


# ---------------------------------------------------------------------------
# Property Inventory (authoritative availability record)
# ---------------------------------------------------------------------------

class PropertyInventoryEventSerializer(serializers.ModelSerializer):
    """Read-only serializer for audit trail events."""

    class Meta:
        model = PropertyInventoryEvent
        fields = [
            "id", "event_type", "from_status", "to_status",
            "actor_name", "actor_user", "reservation",
            "hold_expires_at", "metadata", "notes", "created_at",
        ]
        read_only_fields = fields


class PropertyInventoryListSerializer(serializers.ModelSerializer):
    unit_number = serializers.CharField(source="unit.unit_number", read_only=True)
    property_name = serializers.CharField(source="unit.property.name", read_only=True)
    property_id = serializers.IntegerField(source="unit.property_id", read_only=True)

    class Meta:
        model = PropertyInventory
        fields = [
            "id", "unit", "unit_number", "property_id", "property_name",
            "status", "held_by", "held_until",
            "allocated_to", "allocated_on", "list_price",
            "notes", "created_at", "updated_at",
        ]


class PropertyInventoryDetailSerializer(serializers.ModelSerializer):
    unit_number = serializers.CharField(source="unit.unit_number", read_only=True)
    property_name = serializers.CharField(source="unit.property.name", read_only=True)
    property_id = serializers.IntegerField(source="unit.property_id", read_only=True)
    events = PropertyInventoryEventSerializer(many=True, read_only=True)

    class Meta:
        model = PropertyInventory
        fields = "__all__"
        read_only_fields = ("id", "organization", "created_at", "updated_at")


class PropertyInventoryWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyInventory
        fields = [
            "id", "unit", "status", "held_by", "held_until",
            "reservation", "allocated_to", "allocated_on",
            "list_price", "notes",
        ]
        read_only_fields = ("id",)


class PropertyImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyImage
        fields = "__all__"
        read_only_fields = ("id", "property", "uploaded_at")

    def validate_image(self, value):
        from config.upload_validators import validate_upload
        return validate_upload(value, kind="image")


class PropertyDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyDocument
        fields = "__all__"
        read_only_fields = ("id", "property", "uploaded_at")

    def validate_file(self, value):
        from config.upload_validators import validate_upload
        return validate_upload(value, kind="document")


class PropertyValuationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyValuation
        fields = "__all__"
        read_only_fields = ("id", "property", "created_at")


class PropertyOwnershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyOwnership
        fields = "__all__"
        read_only_fields = ("id", "property", "created_at", "updated_at")

    def validate_ownership_percentage(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError(
                "Ownership percentage must be between 0 and 100."
            )
        return value


class PropertyEncumbranceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyEncumbrance
        fields = "__all__"
        read_only_fields = ("id", "property", "created_at")


# ---------------------------------------------------------------------------
# Maintenance Vendor
# ---------------------------------------------------------------------------

class MaintenanceVendorListSerializer(serializers.ModelSerializer):
    work_order_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = MaintenanceVendor
        fields = [
            "id", "name", "contact_person", "email", "phone",
            "specialization", "license_number", "license_expiry",
            "insurance_expiry", "rating", "hourly_rate",
            "is_active", "work_order_count",
            "created_at", "updated_at",
        ]


class MaintenanceVendorDetailSerializer(serializers.ModelSerializer):
    work_order_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = MaintenanceVendor
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class MaintenanceVendorWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceVendor
        fields = [
            "id", "name", "contact_person", "email", "phone", "address",
            "specialization", "license_number", "license_expiry",
            "insurance_expiry", "rating", "hourly_rate",
            "is_active", "notes",
        ]
        read_only_fields = ("id",)


# ---------------------------------------------------------------------------
# Asset Component Register
# ---------------------------------------------------------------------------

class AssetComponentListSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)
    unit_number = serializers.CharField(source="unit.unit_number", read_only=True, default=None)
    facility_code = serializers.CharField(source="facility.facility_code", read_only=True, default=None)
    facility_name = serializers.CharField(source="facility.property.name", read_only=True, default=None)
    facility_space_label = serializers.SerializerMethodField()
    vendor_name = serializers.CharField(source="vendor.name", read_only=True, default=None)
    amc_vendor_name = serializers.CharField(source="amc_vendor.name", read_only=True, default=None)
    warranty_status = serializers.SerializerMethodField()
    amc_status = serializers.SerializerMethodField()
    maintenance_status = serializers.SerializerMethodField()
    monthly_depreciation = serializers.SerializerMethodField()
    accumulated_depreciation = serializers.SerializerMethodField()
    current_book_value = serializers.SerializerMethodField()

    def get_facility_space_label(self, obj):
        if not obj.facility_space_id:
            return None
        if obj.facility_space.space_label:
            return obj.facility_space.space_label
        if obj.facility_space.unit_id:
            return obj.facility_space.unit.unit_number
        return None

    def get_warranty_status(self, obj):
        return warranty_status_for(obj)

    def get_amc_status(self, obj):
        return amc_status_for(obj)

    def get_maintenance_status(self, obj):
        return maintenance_status_for(obj)

    def get_monthly_depreciation(self, obj):
        value = monthly_depreciation_for(obj)
        return f"{value:.2f}" if value is not None else None

    def get_accumulated_depreciation(self, obj):
        value = accumulated_depreciation_for(obj)
        return f"{value:.2f}" if value is not None else None

    def get_current_book_value(self, obj):
        value = current_book_value_for(obj)
        return f"{value:.2f}" if value is not None else None

    class Meta:
        model = AssetComponent
        fields = [
            "id", "component_id", "name", "category", "condition_rating",
            "property", "property_name", "unit", "unit_number",
            "facility", "facility_code", "facility_name", "facility_space", "facility_space_label",
            "vendor", "vendor_name", "lifecycle_stage",
            "manufacturer", "model_number", "serial_number", "location_description",
            "installation_date", "commissioned_date", "warranty_expiry",
            "expected_useful_life_years", "last_inspection_date",
            "maintenance_frequency", "maintenance_next_due_date",
            "warranty_status", "maintenance_status",
            "amc_vendor", "amc_vendor_name", "amc_start_date", "amc_end_date", "amc_amount", "amc_reference", "amc_status",
            "depreciation_enabled", "depreciation_method", "depreciation_start_date", "acquisition_cost", "salvage_value",
            "monthly_depreciation", "accumulated_depreciation", "current_book_value", "last_depreciation_sync_at",
            "is_iot_enabled", "iot_device_id", "iot_status", "iot_last_seen_at",
            "is_active", "created_at", "updated_at",
        ]


class AssetComponentDetailSerializer(AssetComponentListSerializer):

    class Meta:
        model = AssetComponent
        fields = AssetComponentListSerializer.Meta.fields + [
            "description",
            "auto_schedule_maintenance",
            "retired_date",
            "amc_notes",
            "notes",
        ]
        read_only_fields = ("id", "created_at", "updated_at")


class AssetComponentWriteSerializer(serializers.ModelSerializer):
    def _validate_org_owned(self, value, label: str):
        if value is None:
            return value
        org = _resolve_request_org(self.context.get("request"))
        if org is None:
            return value
        if getattr(value, "organization_id", None) != org.id:
            raise serializers.ValidationError(f"Selected {label} is not in your organization.")
        return value

    def validate_property(self, value):
        return self._validate_org_owned(value, "property")

    def validate_unit(self, value):
        return self._validate_org_owned(value, "unit")

    def validate_facility(self, value):
        return self._validate_org_owned(value, "facility")

    def validate_facility_space(self, value):
        return self._validate_org_owned(value, "facility space")

    def validate_vendor(self, value):
        return self._validate_org_owned(value, "vendor")

    def validate_amc_vendor(self, value):
        return self._validate_org_owned(value, "AMC vendor")

    def validate(self, attrs):
        data = dict(attrs)
        instance = getattr(self, "instance", None)

        facility_space = data.get("facility_space", getattr(instance, "facility_space", None))
        facility = data.get("facility", getattr(instance, "facility", None))
        property_obj = data.get("property", getattr(instance, "property", None))
        unit = data.get("unit", getattr(instance, "unit", None))
        installation_date = data.get("installation_date", getattr(instance, "installation_date", None))
        commissioned_date = data.get("commissioned_date", getattr(instance, "commissioned_date", None))
        lifecycle_stage = data.get("lifecycle_stage", getattr(instance, "lifecycle_stage", AssetComponent.LifecycleStage.OPERATE))

        if facility_space is not None:
            data["facility"] = facility_space.facility
            data["unit"] = facility_space.unit
            data["property"] = facility_space.facility.property
            if not data.get("location_description") and facility_space.space_label:
                data["location_description"] = facility_space.space_label
            facility = facility_space.facility
            property_obj = facility_space.facility.property
            unit = facility_space.unit
        elif facility is not None:
            data["property"] = facility.property
            property_obj = facility.property

        if property_obj is None:
            raise serializers.ValidationError(
                {"property": "Property is required when no facility or facility space is selected."}
            )

        if property_obj is not None and unit is not None and unit.property_id != property_obj.id:
            raise serializers.ValidationError({"unit": "Selected unit does not belong to the selected property."})

        if lifecycle_stage == AssetComponent.LifecycleStage.RETIRE:
            data["is_active"] = False
            if not data.get("retired_date"):
                data["retired_date"] = timezone.localdate()

        if data.get("retired_date") and lifecycle_stage != AssetComponent.LifecycleStage.RETIRE:
            data["lifecycle_stage"] = AssetComponent.LifecycleStage.RETIRE
            data["is_active"] = False

        if data.get("maintenance_frequency") and not data.get("maintenance_next_due_date"):
            data["maintenance_next_due_date"] = derive_maintenance_due_date(
                frequency=data["maintenance_frequency"],
                commissioned_date=commissioned_date,
                installation_date=installation_date,
                today=timezone.localdate(),
            )

        amc_start = data.get("amc_start_date", getattr(instance, "amc_start_date", None))
        amc_end = data.get("amc_end_date", getattr(instance, "amc_end_date", None))
        if amc_start and amc_end and amc_end < amc_start:
            raise serializers.ValidationError({"amc_end_date": "AMC end date cannot be before AMC start date."})

        acquisition_cost = data.get("acquisition_cost", getattr(instance, "acquisition_cost", None))
        salvage_value = data.get("salvage_value", getattr(instance, "salvage_value", None))
        if acquisition_cost is not None and salvage_value is not None and salvage_value > acquisition_cost:
            raise serializers.ValidationError({"salvage_value": "Salvage value cannot be greater than acquisition cost."})

        depreciation_enabled = data.get("depreciation_enabled", getattr(instance, "depreciation_enabled", False))
        depreciation_start = data.get("depreciation_start_date", getattr(instance, "depreciation_start_date", None))
        useful_life = data.get("expected_useful_life_years", getattr(instance, "expected_useful_life_years", None))
        if depreciation_enabled and (acquisition_cost is None or not depreciation_start or not useful_life):
            raise serializers.ValidationError(
                {
                    "depreciation_enabled": (
                        "Acquisition cost, depreciation start date, and useful life are required "
                        "when depreciation sync is enabled."
                    )
                }
            )

        if not data.get("is_iot_enabled", getattr(instance, "is_iot_enabled", False)):
            data["iot_status"] = AssetComponent.IoTStatus.NOT_CONNECTED
            data["iot_device_id"] = data.get("iot_device_id", "") or ""
            if not data["iot_device_id"]:
                data["iot_last_seen_at"] = None

        attrs.clear()
        attrs.update(data)
        return attrs

    class Meta:
        model = AssetComponent
        fields = [
            "id", "property", "facility", "facility_space", "unit", "vendor", "component_id", "name", "category",
            "description", "location_description",
            "manufacturer", "model_number", "serial_number",
            "installation_date", "commissioned_date", "warranty_expiry",
            "expected_useful_life_years", "condition_rating",
            "last_inspection_date", "maintenance_frequency", "maintenance_next_due_date", "auto_schedule_maintenance",
            "lifecycle_stage", "retired_date",
            "acquisition_cost", "salvage_value", "depreciation_enabled", "depreciation_method", "depreciation_start_date",
            "amc_vendor", "amc_start_date", "amc_end_date", "amc_amount", "amc_reference", "amc_notes",
            "is_iot_enabled", "iot_device_id", "iot_status", "iot_last_seen_at",
            "is_active", "notes",
        ]
        read_only_fields = ("id",)
        extra_kwargs = {
            "property": {"required": False},
            "facility": {"required": False, "allow_null": True},
            "facility_space": {"required": False, "allow_null": True},
            "unit": {"required": False, "allow_null": True},
            "vendor": {"required": False, "allow_null": True},
            "amc_vendor": {"required": False, "allow_null": True},
        }


# ---------------------------------------------------------------------------
# Work Order (Corrective / Reactive)
# ---------------------------------------------------------------------------

class WorkOrderListSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)
    facility_code = serializers.CharField(source="facility.facility_code", read_only=True, default=None)
    facility_name = serializers.CharField(source="facility.property.name", read_only=True, default=None)
    facility_space_label = serializers.SerializerMethodField()
    unit_number = serializers.CharField(source="unit.unit_number", read_only=True, default=None)
    vendor_name = serializers.CharField(source="vendor.name", read_only=True, default=None)
    asset_component_name = serializers.CharField(source="asset_component.name", read_only=True, default=None)
    sla_status = serializers.SerializerMethodField()

    def get_facility_space_label(self, obj):
        if obj.facility_space_id:
            return obj.facility_space.space_label or obj.facility_space.unit.unit_number
        return None

    def get_sla_status(self, obj):
        return work_order_sla_status_for(obj)

    class Meta:
        model = WorkOrder
        fields = [
            "id", "property", "property_name",
            "facility", "facility_code", "facility_name",
            "facility_space", "facility_space_label",
            "unit", "unit_number",
            "asset_component", "asset_component_name",
            "vendor", "vendor_name",
            "title", "maintenance_mode", "category", "priority", "status", "sla_status",
            "assigned_to", "reported_by", "reported_date", "started_at", "due_date", "sla_target_hours", "sla_due_at",
            "completed_date", "verified_at", "verified_by",
            "preventive_schedule", "is_breakdown", "root_cause",
            "estimated_cost", "actual_cost",
            "created_at", "updated_at",
        ]


class WorkOrderDetailSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)
    facility_code = serializers.CharField(source="facility.facility_code", read_only=True, default=None)
    facility_name = serializers.CharField(source="facility.property.name", read_only=True, default=None)
    facility_space_label = serializers.SerializerMethodField()
    unit_number = serializers.CharField(source="unit.unit_number", read_only=True, default=None)
    vendor_name = serializers.CharField(source="vendor.name", read_only=True, default=None)
    asset_component_name = serializers.CharField(source="asset_component.name", read_only=True, default=None)
    sla_status = serializers.SerializerMethodField()

    def get_facility_space_label(self, obj):
        if obj.facility_space_id:
            return obj.facility_space.space_label or obj.facility_space.unit.unit_number
        return None

    def get_sla_status(self, obj):
        return work_order_sla_status_for(obj)

    class Meta:
        model = WorkOrder
        fields = [
            "id", "property", "property_name",
            "facility", "facility_code", "facility_name",
            "facility_space", "facility_space_label",
            "unit", "unit_number",
            "asset_component", "asset_component_name",
            "vendor", "vendor_name",
            "title", "description", "maintenance_mode", "category",
            "priority", "status", "sla_status",
            "reported_by", "assigned_to", "reported_date",
            "started_at", "due_date", "sla_target_hours", "sla_due_at",
            "completed_date", "verified_at", "verified_by", "verification_notes",
            "preventive_schedule", "is_breakdown", "root_cause",
            "estimated_cost", "actual_cost", "notes",
            "created_at", "updated_at",
        ]
        read_only_fields = ("id", "reported_date", "created_at", "updated_at")


class WorkOrderWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkOrder
        fields = [
            "id", "property", "facility", "facility_space", "unit", "asset_component", "vendor",
            "title", "description", "maintenance_mode", "category", "priority", "status",
            "reported_by", "assigned_to", "started_at", "due_date", "sla_target_hours", "sla_due_at",
            "completed_date", "verified_at", "verified_by", "verification_notes",
            "preventive_schedule", "is_breakdown", "root_cause",
            "estimated_cost", "actual_cost", "notes",
        ]
        read_only_fields = ("id",)
        extra_kwargs = {
            "property": {"required": False, "allow_null": True},
            "facility": {"required": False, "allow_null": True},
            "facility_space": {"required": False, "allow_null": True},
            "unit": {"required": False, "allow_null": True},
            "asset_component": {"required": False, "allow_null": True},
            "vendor": {"required": False, "allow_null": True},
            "preventive_schedule": {"required": False, "allow_null": True},
            "completed_date": {"required": False, "allow_null": True},
            "started_at": {"required": False, "allow_null": True},
            "verified_at": {"required": False, "allow_null": True},
            "due_date": {"required": False, "allow_null": True},
            "sla_target_hours": {"required": False, "allow_null": True},
            "sla_due_at": {"required": False, "allow_null": True},
        }

    def validate(self, attrs):
        return normalize_work_order_payload(attrs, instance=self.instance)


# ---------------------------------------------------------------------------
# Preventive Maintenance Schedule
# ---------------------------------------------------------------------------

class PreventiveScheduleListSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)
    facility_code = serializers.CharField(source="facility.facility_code", read_only=True, default=None)
    facility_name = serializers.CharField(source="facility.property.name", read_only=True, default=None)
    facility_space_label = serializers.SerializerMethodField()
    asset_component_name = serializers.CharField(source="asset_component.name", read_only=True, default=None)
    vendor_name = serializers.CharField(source="vendor.name", read_only=True, default=None)

    def get_facility_space_label(self, obj):
        if obj.facility_space_id:
            return obj.facility_space.space_label or obj.facility_space.unit.unit_number
        return None

    class Meta:
        model = PreventiveSchedule
        fields = [
            "id", "property", "property_name",
            "facility", "facility_code", "facility_name",
            "facility_space", "facility_space_label",
            "asset_component", "asset_component_name",
            "vendor", "vendor_name",
            "title", "category", "frequency", "priority", "status",
            "assigned_to", "next_due_date", "last_completed_date",
            "sla_target_hours", "generate_days_before", "auto_create_work_orders",
            "last_work_order", "last_generated_date", "estimated_cost",
            "created_at", "updated_at",
        ]


class PreventiveScheduleDetailSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)
    facility_code = serializers.CharField(source="facility.facility_code", read_only=True, default=None)
    facility_name = serializers.CharField(source="facility.property.name", read_only=True, default=None)
    facility_space_label = serializers.SerializerMethodField()
    asset_component_name = serializers.CharField(source="asset_component.name", read_only=True, default=None)
    vendor_name = serializers.CharField(source="vendor.name", read_only=True, default=None)

    def get_facility_space_label(self, obj):
        if obj.facility_space_id:
            return obj.facility_space.space_label or obj.facility_space.unit.unit_number
        return None

    class Meta:
        model = PreventiveSchedule
        fields = [
            "id", "property", "property_name",
            "facility", "facility_code", "facility_name",
            "facility_space", "facility_space_label",
            "asset_component", "asset_component_name",
            "vendor", "vendor_name",
            "title", "description", "category", "frequency", "priority", "status",
            "assigned_to", "next_due_date", "last_completed_date",
            "sla_target_hours", "generate_days_before", "auto_create_work_orders",
            "last_work_order", "last_generated_date", "estimated_cost",
            "auto_generated", "notes", "created_at", "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")


class PreventiveScheduleWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PreventiveSchedule
        fields = [
            "id", "property", "facility", "facility_space", "asset_component", "vendor",
            "title", "description", "category", "frequency", "priority",
            "assigned_to", "next_due_date", "last_completed_date",
            "sla_target_hours", "generate_days_before", "auto_create_work_orders",
            "estimated_cost", "status", "notes",
        ]
        read_only_fields = ("id",)
        extra_kwargs = {
            "property": {"required": False, "allow_null": True},
            "facility": {"required": False, "allow_null": True},
            "facility_space": {"required": False, "allow_null": True},
            "asset_component": {"required": False, "allow_null": True},
            "vendor": {"required": False, "allow_null": True},
            "next_due_date": {"required": False, "allow_null": True},
            "last_completed_date": {"required": False, "allow_null": True},
            "sla_target_hours": {"required": False, "allow_null": True},
            "estimated_cost": {"required": False, "allow_null": True},
        }

    def validate(self, attrs):
        return normalize_preventive_schedule_payload(attrs, instance=self.instance)


class PredictiveMaintenanceRuleListSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)
    facility_code = serializers.CharField(source="facility.facility_code", read_only=True, default=None)
    facility_name = serializers.CharField(source="facility.property.name", read_only=True, default=None)
    facility_space_label = serializers.SerializerMethodField()
    asset_component_name = serializers.CharField(source="asset_component.name", read_only=True, default=None)

    def get_facility_space_label(self, obj):
        if obj.facility_space_id:
            return obj.facility_space.space_label or obj.facility_space.unit.unit_number
        return None

    class Meta:
        model = PredictiveMaintenanceRule
        fields = [
            "id", "property", "property_name",
            "facility", "facility_code", "facility_name",
            "facility_space", "facility_space_label",
            "asset_component", "asset_component_name",
            "title", "priority", "assigned_to", "sla_target_hours",
            "runtime_hours_threshold", "cycle_threshold",
            "runtime_hours_reading", "cycle_reading",
            "alert_on_offline", "alert_on_fault",
            "auto_create_work_order", "is_active",
            "last_evaluated_at", "last_triggered_at",
            "created_at", "updated_at",
        ]


class PredictiveMaintenanceRuleDetailSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)
    facility_code = serializers.CharField(source="facility.facility_code", read_only=True, default=None)
    facility_name = serializers.CharField(source="facility.property.name", read_only=True, default=None)
    facility_space_label = serializers.SerializerMethodField()
    asset_component_name = serializers.CharField(source="asset_component.name", read_only=True, default=None)

    def get_facility_space_label(self, obj):
        if obj.facility_space_id:
            return obj.facility_space.space_label or obj.facility_space.unit.unit_number
        return None

    class Meta:
        model = PredictiveMaintenanceRule
        fields = [
            "id", "property", "property_name",
            "facility", "facility_code", "facility_name",
            "facility_space", "facility_space_label",
            "asset_component", "asset_component_name",
            "title", "description", "priority", "assigned_to", "sla_target_hours",
            "runtime_hours_threshold", "cycle_threshold",
            "runtime_hours_reading", "cycle_reading",
            "alert_on_offline", "alert_on_fault",
            "auto_create_work_order", "is_active",
            "last_evaluated_at", "last_triggered_at",
            "notes", "created_at", "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")


class PredictiveMaintenanceRuleWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PredictiveMaintenanceRule
        fields = [
            "id", "property", "facility", "facility_space", "asset_component",
            "title", "description", "priority", "assigned_to", "sla_target_hours",
            "runtime_hours_threshold", "cycle_threshold",
            "runtime_hours_reading", "cycle_reading",
            "alert_on_offline", "alert_on_fault",
            "auto_create_work_order", "is_active", "notes",
        ]
        read_only_fields = ("id",)
        extra_kwargs = {
            "property": {"required": False, "allow_null": True},
            "facility": {"required": False, "allow_null": True},
            "facility_space": {"required": False, "allow_null": True},
            "asset_component": {"required": False, "allow_null": True},
            "runtime_hours_threshold": {"required": False, "allow_null": True},
            "cycle_threshold": {"required": False, "allow_null": True},
            "runtime_hours_reading": {"required": False, "allow_null": True},
            "cycle_reading": {"required": False, "allow_null": True},
            "sla_target_hours": {"required": False, "allow_null": True},
        }

    def validate(self, attrs):
        return normalize_predictive_rule_payload(attrs, instance=self.instance)


class PredictiveMaintenanceAlertListSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)
    facility_code = serializers.CharField(source="facility.facility_code", read_only=True, default=None)
    asset_component_name = serializers.CharField(source="asset_component.name", read_only=True, default=None)
    work_order_title = serializers.CharField(source="work_order.title", read_only=True, default=None)

    class Meta:
        model = PredictiveMaintenanceAlert
        fields = [
            "id", "rule", "property", "property_name",
            "facility", "facility_code", "facility_space",
            "asset_component", "asset_component_name",
            "work_order", "work_order_title",
            "title", "message", "priority", "trigger_type", "status",
            "runtime_hours_reading", "cycle_reading", "iot_status",
            "triggered_at", "resolved_at", "updated_at",
        ]


class PredictiveMaintenanceAlertDetailSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)
    facility_code = serializers.CharField(source="facility.facility_code", read_only=True, default=None)
    asset_component_name = serializers.CharField(source="asset_component.name", read_only=True, default=None)
    work_order_title = serializers.CharField(source="work_order.title", read_only=True, default=None)

    class Meta:
        model = PredictiveMaintenanceAlert
        fields = [
            "id", "rule", "property", "property_name",
            "facility", "facility_code", "facility_space",
            "asset_component", "asset_component_name",
            "work_order", "work_order_title",
            "title", "message", "priority", "trigger_type", "status",
            "runtime_hours_reading", "cycle_reading", "iot_status",
            "triggered_at", "resolved_at", "notes", "updated_at",
        ]
        read_only_fields = (
            "id", "rule", "property", "facility", "facility_space", "asset_component",
            "work_order", "title", "message", "priority", "trigger_type",
            "runtime_hours_reading", "cycle_reading", "iot_status", "triggered_at", "updated_at",
        )


class PredictiveMaintenanceAlertWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PredictiveMaintenanceAlert
        fields = ["id", "status", "notes", "resolved_at"]
        read_only_fields = ("id",)

    def validate(self, attrs):
        if attrs.get("status") == PredictiveMaintenanceAlert.Status.RESOLVED and not attrs.get("resolved_at"):
            attrs["resolved_at"] = timezone.now()
        return attrs


# ---------------------------------------------------------------------------
# Inspection
# ---------------------------------------------------------------------------

class InspectionListSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)
    unit_number = serializers.CharField(source="unit.unit_number", read_only=True, default=None)
    asset_component_name = serializers.CharField(source="asset_component.name", read_only=True, default=None)

    class Meta:
        model = Inspection
        fields = [
            "id", "property", "property_name",
            "unit", "unit_number",
            "asset_component", "asset_component_name",
            "title", "inspection_type", "status",
            "scheduled_date", "completed_date", "inspector",
            "rating", "risk_level", "corrective_action_required",
            "compliance_status", "expiry_date",
            "follow_up_required",
            "created_at", "updated_at",
        ]


class InspectionDetailSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)
    unit_number = serializers.CharField(source="unit.unit_number", read_only=True, default=None)
    asset_component_name = serializers.CharField(source="asset_component.name", read_only=True, default=None)

    class Meta:
        model = Inspection
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class InspectionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Inspection
        fields = [
            "id", "property", "unit", "asset_component",
            "title", "inspection_type", "status",
            "scheduled_date", "completed_date", "inspector",
            "findings", "rating", "risk_level",
            "corrective_action_required", "compliance_status",
            "expiry_date", "follow_up_required",
            "follow_up_notes", "notes",
        ]
        read_only_fields = ("id",)


# ---------------------------------------------------------------------------
# Service Request
# ---------------------------------------------------------------------------

class ServiceRequestListSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)
    unit_number = serializers.CharField(source="unit.unit_number", read_only=True, default=None)

    class Meta:
        model = ServiceRequest
        fields = [
            "id", "property", "property_name",
            "unit", "unit_number",
            "title", "category", "priority", "status",
            "requested_by", "assigned_to",
            "requested_date", "resolved_date",
            "work_order",
            "created_at", "updated_at",
        ]


class ServiceRequestDetailSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)
    unit_number = serializers.CharField(source="unit.unit_number", read_only=True, default=None)

    class Meta:
        model = ServiceRequest
        fields = "__all__"
        read_only_fields = ("id", "requested_date", "created_at", "updated_at")


class ServiceRequestWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceRequest
        fields = [
            "id", "property", "unit",
            "title", "description", "category", "priority", "status",
            "requested_by", "assigned_to",
            "resolved_date", "resolution_notes",
            "work_order", "notes",
        ]
        read_only_fields = ("id",)


# ---------------------------------------------------------------------------
# Property (list / detail / write)
# ---------------------------------------------------------------------------

class PropertyListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""

    unit_count = serializers.IntegerField(read_only=True)
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = [
            "id", "name", "property_type", "classification", "address",
            "acquisition_date", "current_value", "total_area_sqft",
            "is_active", "created_at", "updated_at",
            "unit_count", "primary_image",
        ]

    def get_primary_image(self, obj):
        img = obj.images.filter(is_primary=True).first()
        if img and img.image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(img.image.url)
            return img.image.url
        return None


class PropertyDetailSerializer(serializers.ModelSerializer):
    """Full serializer for detail view with all nested relations."""

    units = UnitSerializer(many=True, read_only=True)
    images = PropertyImageSerializer(many=True, read_only=True)
    documents = PropertyDocumentSerializer(many=True, read_only=True)
    valuations = PropertyValuationSerializer(many=True, read_only=True)
    ownerships = PropertyOwnershipSerializer(many=True, read_only=True)
    encumbrances = PropertyEncumbranceSerializer(many=True, read_only=True)
    unit_count = serializers.IntegerField(read_only=True)
    map_available = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")

    def get_map_available(self, obj):
        from apps.settings.quotas import is_entity_map_available

        if not obj.gps_latitude or not obj.gps_longitude:
            return False
        return is_entity_map_available(obj.organization, obj)


class PropertyWriteSerializer(serializers.ModelSerializer):
    """Flat serializer for create/update operations."""

    class Meta:
        model = Property
        fields = [
            "name", "property_type", "classification", "address", "description",
            "gps_latitude", "gps_longitude", "plot_number",
            "acquisition_date", "acquisition_price", "current_value",
            "total_area_sqft", "is_active",
        ]

    def validate_acquisition_price(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Acquisition price cannot be negative.")
        return value

    def validate_current_value(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Current value cannot be negative.")
        return value

    def validate_gps_latitude(self, value):
        if value is not None and (value < -90 or value > 90):
            raise serializers.ValidationError("Latitude must be between -90 and 90.")
        return value

    def validate_gps_longitude(self, value):
        if value is not None and (value < -180 or value > 180):
            raise serializers.ValidationError("Longitude must be between -180 and 180.")
        return value
