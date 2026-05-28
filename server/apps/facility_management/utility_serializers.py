from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from .models import Facility, UtilityBill, UtilityMeter, UtilityMeterReading
from .utility_workflows import default_unit_for_utility_type


def _resolve_request_org(request):
    org = getattr(request, "organization", None)
    if org is not None:
        return org
    profile = getattr(getattr(request, "user", None), "profile", None)
    return getattr(profile, "organization", None)


def _user_display(user) -> str:
    if not user:
        return ""
    full_name = user.get_full_name().strip()
    return full_name or user.email or user.username


class FacilityUtilityMeterListSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)
    facility = serializers.IntegerField(source="property.facility_registry.id", read_only=True)
    facility_code = serializers.CharField(source="property.facility_registry.facility_code", read_only=True, default="")
    utility_type_display = serializers.CharField(source="get_utility_type_display", read_only=True)
    vendor_name = serializers.CharField(source="vendor.name", read_only=True, default="")
    total_readings = serializers.SerializerMethodField()
    open_anomalies = serializers.SerializerMethodField()
    latest_reading_value = serializers.SerializerMethodField()

    class Meta:
        model = UtilityMeter
        fields = [
            "id",
            "property",
            "property_name",
            "facility",
            "facility_code",
            "vendor",
            "vendor_name",
            "meter_number",
            "utility_type",
            "utility_type_display",
            "unit_of_measure",
            "location_label",
            "provider_name",
            "installed_at",
            "is_smart_meter",
            "is_active",
            "last_reading_at",
            "latest_reading_value",
            "total_readings",
            "open_anomalies",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_total_readings(self, obj):
        return obj.readings.count()

    def get_open_anomalies(self, obj):
        return obj.readings.filter(is_anomaly=True).count()

    def get_latest_reading_value(self, obj):
        reading = getattr(obj, "_latest_reading_cache", None)
        if reading is None:
            reading = obj.readings.order_by("-reading_at", "-id").only("reading_value").first()
            obj._latest_reading_cache = reading
        if reading is None:
            return None
        return f"{Decimal(reading.reading_value):.3f}"


class FacilityUtilityMeterDetailSerializer(FacilityUtilityMeterListSerializer):
    class Meta(FacilityUtilityMeterListSerializer.Meta):
        fields = FacilityUtilityMeterListSerializer.Meta.fields


class FacilityUtilityMeterWriteSerializer(serializers.ModelSerializer):
    facility = serializers.PrimaryKeyRelatedField(
        queryset=Facility.objects.select_related("property").all(),
        write_only=True,
    )

    class Meta:
        model = UtilityMeter
        fields = [
            "id",
            "facility",
            "vendor",
            "meter_number",
            "utility_type",
            "unit_of_measure",
            "location_label",
            "provider_name",
            "installed_at",
            "is_smart_meter",
            "is_active",
            "notes",
        ]
        read_only_fields = ["id"]
        extra_kwargs = {
            "vendor": {"required": False, "allow_null": True},
            "unit_of_measure": {"required": False, "allow_blank": True},
            "location_label": {"required": False, "allow_blank": True},
            "provider_name": {"required": False, "allow_blank": True},
            "installed_at": {"required": False, "allow_null": True},
            "notes": {"required": False, "allow_blank": True},
        }

    def _org(self):
        return _resolve_request_org(self.context.get("request"))

    def validate_facility(self, value):
        org = self._org()
        if org and value.organization_id != org.id:
            raise serializers.ValidationError("Selected facility is not in your organization.")
        return value

    def validate_vendor(self, value):
        org = self._org()
        if value and org and value.organization_id not in {org.id, None}:
            raise serializers.ValidationError("Selected provider is not in your organization.")
        return value

    def validate_utility_type(self, value):
        if value not in UtilityMeter.UtilityType.values:
            raise serializers.ValidationError("Unsupported utility type.")
        return value

    def validate(self, attrs):
        instance = getattr(self, "instance", None)
        facility = attrs.get("facility")
        if facility is None and instance is not None:
            facility = getattr(instance.property, "facility_registry", None)
        if facility is None:
            raise serializers.ValidationError({"facility": "Facility is required."})
        attrs["property"] = facility.property
        attrs["organization"] = facility.organization

        utility_type = attrs.get("utility_type", getattr(instance, "utility_type", UtilityMeter.UtilityType.ELECTRICITY))
        vendor = attrs.get("vendor", getattr(instance, "vendor", None))
        if not attrs.get("unit_of_measure"):
            attrs["unit_of_measure"] = default_unit_for_utility_type(utility_type)
        if vendor and not attrs.get("provider_name"):
            attrs["provider_name"] = vendor.name
        return attrs

    def create(self, validated_data):
        validated_data.pop("facility", None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop("facility", None)
        return super().update(instance, validated_data)


class FacilityUtilityMeterReadingListSerializer(serializers.ModelSerializer):
    meter_number = serializers.CharField(source="meter.meter_number", read_only=True)
    utility_type = serializers.CharField(source="meter.utility_type", read_only=True)
    utility_type_display = serializers.CharField(source="meter.get_utility_type_display", read_only=True)
    unit_of_measure = serializers.CharField(source="meter.unit_of_measure", read_only=True)
    property_name = serializers.CharField(source="meter.property.name", read_only=True)
    facility = serializers.IntegerField(source="meter.property.facility_registry.id", read_only=True)
    facility_code = serializers.CharField(source="meter.property.facility_registry.facility_code", read_only=True, default="")
    entered_by_name = serializers.SerializerMethodField()

    class Meta:
        model = UtilityMeterReading
        fields = [
            "id",
            "meter",
            "meter_number",
            "utility_type",
            "utility_type_display",
            "unit_of_measure",
            "property_name",
            "facility",
            "facility_code",
            "reading_at",
            "reading_date",
            "reading_value",
            "consumption_delta",
            "entered_by",
            "entered_by_name",
            "is_estimated",
            "is_anomaly",
            "anomaly_reason",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_entered_by_name(self, obj):
        return _user_display(obj.entered_by)


class FacilityUtilityMeterReadingDetailSerializer(FacilityUtilityMeterReadingListSerializer):
    class Meta(FacilityUtilityMeterReadingListSerializer.Meta):
        fields = FacilityUtilityMeterReadingListSerializer.Meta.fields


class FacilityUtilityMeterReadingWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = UtilityMeterReading
        fields = [
            "id",
            "meter",
            "reading_at",
            "reading_value",
            "is_estimated",
            "notes",
        ]
        read_only_fields = ["id"]
        extra_kwargs = {
            "reading_at": {"required": False},
            "is_estimated": {"required": False},
            "notes": {"required": False, "allow_blank": True},
        }

    def _org(self):
        return _resolve_request_org(self.context.get("request"))

    def validate_meter(self, value):
        org = self._org()
        if org and value.organization_id != org.id:
            raise serializers.ValidationError("Selected meter is not in your organization.")
        if not value.is_active:
            raise serializers.ValidationError("Inactive meters cannot receive new readings.")
        return value

    def validate_reading_value(self, value):
        if Decimal(value) < 0:
            raise serializers.ValidationError("Meter reading cannot be negative.")
        return value

    def validate(self, attrs):
        meter = attrs.get("meter", getattr(self.instance, "meter", None))
        reading_at = attrs.get("reading_at", getattr(self.instance, "reading_at", None)) or timezone.now()
        attrs["reading_at"] = reading_at
        attrs["reading_date"] = timezone.localdate(reading_at)
        attrs["organization"] = meter.organization
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated and not attrs.get("entered_by"):
            attrs["entered_by"] = request.user
        return attrs


class FacilityUtilityBillListSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)
    facility = serializers.IntegerField(source="property.facility_registry.id", read_only=True)
    facility_code = serializers.CharField(source="property.facility_registry.facility_code", read_only=True, default="")
    meter_number = serializers.CharField(source="meter.meter_number", read_only=True, default="")
    vendor_name = serializers.CharField(source="vendor.name", read_only=True, default="")
    finance_bill_number = serializers.CharField(source="finance_bill.bill_number", read_only=True, default="")
    utility_type_display = serializers.CharField(source="get_utility_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    balance_due = serializers.SerializerMethodField()

    class Meta:
        model = UtilityBill
        fields = [
            "id",
            "property",
            "property_name",
            "facility",
            "facility_code",
            "meter",
            "meter_number",
            "vendor",
            "vendor_name",
            "finance_bill",
            "finance_bill_number",
            "provider_name",
            "utility_type",
            "utility_type_display",
            "bill_number",
            "billing_period_start",
            "billing_period_end",
            "issue_date",
            "due_date",
            "usage_quantity",
            "unit_rate",
            "subtotal",
            "tax_amount",
            "total_amount",
            "amount_paid",
            "balance_due",
            "status",
            "status_display",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_balance_due(self, obj):
        return f"{max(Decimal(obj.total_amount or 0) - Decimal(obj.amount_paid or 0), Decimal('0.00')):.2f}"


class FacilityUtilityBillDetailSerializer(FacilityUtilityBillListSerializer):
    class Meta(FacilityUtilityBillListSerializer.Meta):
        fields = FacilityUtilityBillListSerializer.Meta.fields


class FacilityUtilityBillWriteSerializer(serializers.ModelSerializer):
    facility = serializers.PrimaryKeyRelatedField(
        queryset=Facility.objects.select_related("property").all(),
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = UtilityBill
        fields = [
            "id",
            "facility",
            "meter",
            "vendor",
            "provider_name",
            "utility_type",
            "bill_number",
            "billing_period_start",
            "billing_period_end",
            "issue_date",
            "due_date",
            "usage_quantity",
            "unit_rate",
            "subtotal",
            "tax_amount",
            "total_amount",
            "amount_paid",
            "status",
            "notes",
        ]
        read_only_fields = ["id"]
        extra_kwargs = {
            "facility": {"required": False, "allow_null": True},
            "meter": {"required": False, "allow_null": True},
            "vendor": {"required": False, "allow_null": True},
            "provider_name": {"required": False, "allow_blank": True},
            "issue_date": {"required": False},
            "due_date": {"required": False},
            "usage_quantity": {"required": False},
            "unit_rate": {"required": False},
            "subtotal": {"required": False},
            "tax_amount": {"required": False},
            "total_amount": {"required": False},
            "amount_paid": {"required": False},
            "status": {"required": False},
            "notes": {"required": False, "allow_blank": True},
        }

    def _org(self):
        return _resolve_request_org(self.context.get("request"))

    def validate_facility(self, value):
        org = self._org()
        if value and org and value.organization_id != org.id:
            raise serializers.ValidationError("Selected facility is not in your organization.")
        return value

    def validate_meter(self, value):
        org = self._org()
        if value and org and value.organization_id != org.id:
            raise serializers.ValidationError("Selected meter is not in your organization.")
        return value

    def validate_vendor(self, value):
        org = self._org()
        if value and org and value.organization_id not in {org.id, None}:
            raise serializers.ValidationError("Selected provider is not in your organization.")
        return value

    def validate(self, attrs):
        instance = getattr(self, "instance", None)

        facility = attrs.get("facility", None)
        meter = attrs.get("meter", getattr(instance, "meter", None))
        vendor = attrs.get("vendor", getattr(instance, "vendor", None))
        billing_period_start = attrs.get("billing_period_start", getattr(instance, "billing_period_start", None))
        billing_period_end = attrs.get("billing_period_end", getattr(instance, "billing_period_end", None))

        property_obj = None
        if facility is not None:
            property_obj = facility.property
        elif meter is not None:
            property_obj = meter.property
        elif instance is not None:
            property_obj = instance.property

        if property_obj is None:
            raise serializers.ValidationError({"facility": "Facility or utility meter is required."})

        if facility is not None and meter is not None and facility.property_id != meter.property_id:
            raise serializers.ValidationError({"meter": "Selected meter does not belong to the selected facility."})

        attrs["property"] = property_obj
        attrs["organization"] = property_obj.organization

        if meter is not None and not attrs.get("utility_type"):
            attrs["utility_type"] = meter.utility_type
        if vendor is not None and not attrs.get("provider_name"):
            attrs["provider_name"] = vendor.name

        if billing_period_start is None or billing_period_end is None:
            raise serializers.ValidationError({"billing_period_start": "Billing period dates are required."})
        if billing_period_end < billing_period_start:
            raise serializers.ValidationError(
                {"billing_period_end": "Billing period end cannot be before the start date."}
            )

        issue_date = attrs.get("issue_date") or getattr(instance, "issue_date", None) or billing_period_end
        attrs["issue_date"] = issue_date
        due_date = attrs.get("due_date") or getattr(instance, "due_date", None) or (issue_date + timedelta(days=14))
        attrs["due_date"] = due_date
        if due_date < issue_date:
            raise serializers.ValidationError({"due_date": "Due date cannot be earlier than issue date."})

        amount_fields = ("usage_quantity", "unit_rate", "subtotal", "tax_amount", "total_amount", "amount_paid")
        for field_name in amount_fields:
            value = attrs.get(field_name)
            if value is not None and Decimal(value) < 0:
                raise serializers.ValidationError({field_name: "Values cannot be negative."})

        return attrs

    def create(self, validated_data):
        validated_data.pop("facility", None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop("facility", None)
        return super().update(instance, validated_data)
