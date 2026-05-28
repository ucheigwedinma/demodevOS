from rest_framework import serializers

from .models import Facility, FacilityFloor, FacilityUnitSpace, FacilityZone


def _resolve_request_org(request):
    org = getattr(request, "organization", None)
    if org is not None:
        return org
    profile = getattr(getattr(request, "user", None), "profile", None)
    return getattr(profile, "organization", None)


class FacilityListSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)
    property_type = serializers.CharField(source="property.property_type", read_only=True)
    property_classification = serializers.CharField(source="property.classification", read_only=True)
    property_address = serializers.CharField(source="property.address", read_only=True)
    floors_count = serializers.IntegerField(read_only=True)
    zones_count = serializers.IntegerField(read_only=True)
    unit_spaces_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Facility
        fields = [
            "id",
            "property",
            "property_name",
            "property_type",
            "property_classification",
            "property_address",
            "facility_code",
            "facility_classification",
            "ownership_type",
            "lease_start_date",
            "lease_end_date",
            "lease_party_name",
            "lease_amount",
            "floors_count",
            "zones_count",
            "unit_spaces_count",
            "created_at",
            "updated_at",
        ]


class FacilityDetailSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)
    property_type = serializers.CharField(source="property.property_type", read_only=True)
    property_classification = serializers.CharField(source="property.classification", read_only=True)
    property_address = serializers.CharField(source="property.address", read_only=True)
    ownership_records_count = serializers.IntegerField(source="property.ownerships.count", read_only=True)

    class Meta:
        model = Facility
        fields = "__all__"
        read_only_fields = ("id", "organization", "created_at", "updated_at")


class FacilityWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Facility
        fields = [
            "id",
            "property",
            "facility_code",
            "facility_classification",
            "ownership_type",
            "lease_start_date",
            "lease_end_date",
            "lease_party_name",
            "lease_amount",
            "lease_terms",
            "notes",
        ]
        read_only_fields = ("id",)

    def validate_property(self, value):
        request = self.context.get("request")
        org = _resolve_request_org(request)
        if org and value.organization_id != org.id:
            raise serializers.ValidationError("Selected property is not in your organization.")
        return value

    def validate(self, attrs):
        start = attrs.get("lease_start_date")
        end = attrs.get("lease_end_date")
        if start and end and end < start:
            raise serializers.ValidationError({"lease_end_date": "Lease end date cannot be before lease start date."})
        return attrs


class FacilityFloorListSerializer(serializers.ModelSerializer):
    facility_code = serializers.CharField(source="facility.facility_code", read_only=True)
    facility_name = serializers.CharField(source="facility.property.name", read_only=True)
    zone_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = FacilityFloor
        fields = [
            "id",
            "facility",
            "facility_code",
            "facility_name",
            "name",
            "floor_code",
            "floor_number",
            "gross_area_sqft",
            "usage_type",
            "is_active",
            "zone_count",
            "created_at",
            "updated_at",
        ]


class FacilityFloorDetailSerializer(serializers.ModelSerializer):
    facility_code = serializers.CharField(source="facility.facility_code", read_only=True)
    facility_name = serializers.CharField(source="facility.property.name", read_only=True)

    class Meta:
        model = FacilityFloor
        fields = "__all__"
        read_only_fields = ("id", "organization", "created_at", "updated_at")


class FacilityFloorWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = FacilityFloor
        fields = [
            "id",
            "facility",
            "name",
            "floor_code",
            "floor_number",
            "gross_area_sqft",
            "usage_type",
            "is_active",
        ]
        read_only_fields = ("id",)

    def validate_facility(self, value):
        request = self.context.get("request")
        org = _resolve_request_org(request)
        if org and value.organization_id != org.id:
            raise serializers.ValidationError("Selected facility is not in your organization.")
        return value


class FacilityZoneListSerializer(serializers.ModelSerializer):
    facility_code = serializers.CharField(source="facility.facility_code", read_only=True)
    facility_name = serializers.CharField(source="facility.property.name", read_only=True)
    floor_name = serializers.CharField(source="floor.name", read_only=True)
    floor_number = serializers.IntegerField(source="floor.floor_number", read_only=True)
    unit_spaces_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = FacilityZone
        fields = [
            "id",
            "facility",
            "facility_code",
            "facility_name",
            "floor",
            "floor_name",
            "floor_number",
            "name",
            "zone_code",
            "zone_type",
            "gross_area_sqft",
            "is_active",
            "unit_spaces_count",
            "created_at",
            "updated_at",
        ]


class FacilityZoneDetailSerializer(serializers.ModelSerializer):
    facility_code = serializers.CharField(source="facility.facility_code", read_only=True)
    facility_name = serializers.CharField(source="facility.property.name", read_only=True)
    floor_name = serializers.CharField(source="floor.name", read_only=True)
    floor_number = serializers.IntegerField(source="floor.floor_number", read_only=True)

    class Meta:
        model = FacilityZone
        fields = "__all__"
        read_only_fields = ("id", "organization", "created_at", "updated_at")


class FacilityZoneWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = FacilityZone
        fields = [
            "id",
            "facility",
            "floor",
            "name",
            "zone_code",
            "zone_type",
            "gross_area_sqft",
            "is_active",
        ]
        read_only_fields = ("id",)

    def validate(self, attrs):
        instance = getattr(self, "instance", None)
        facility = attrs.get("facility") or getattr(instance, "facility", None)
        floor = attrs.get("floor") or getattr(instance, "floor", None)
        if facility and floor and floor.facility_id != facility.id:
            raise serializers.ValidationError({"floor": "Floor must belong to the selected facility."})
        request = self.context.get("request")
        org = _resolve_request_org(request)
        if org and facility and facility.organization_id != org.id:
            raise serializers.ValidationError({"facility": "Selected facility is not in your organization."})
        return attrs


class FacilityUnitSpaceListSerializer(serializers.ModelSerializer):
    facility_code = serializers.CharField(source="facility.facility_code", read_only=True)
    facility_name = serializers.CharField(source="facility.property.name", read_only=True)
    floor_name = serializers.CharField(source="zone.floor.name", read_only=True)
    floor_number = serializers.IntegerField(source="zone.floor.floor_number", read_only=True)
    zone_name = serializers.CharField(source="zone.name", read_only=True)
    zone_code = serializers.CharField(source="zone.zone_code", read_only=True)
    unit_number = serializers.CharField(source="unit.unit_number", read_only=True)
    unit_status = serializers.CharField(source="unit.status", read_only=True)
    property_name = serializers.CharField(source="unit.property.name", read_only=True)

    class Meta:
        model = FacilityUnitSpace
        fields = [
            "id",
            "facility",
            "facility_code",
            "facility_name",
            "zone",
            "zone_name",
            "zone_code",
            "floor_name",
            "floor_number",
            "unit",
            "unit_number",
            "unit_status",
            "property_name",
            "space_label",
            "notes",
            "created_at",
            "updated_at",
        ]


class FacilityUnitSpaceDetailSerializer(serializers.ModelSerializer):
    facility_code = serializers.CharField(source="facility.facility_code", read_only=True)
    facility_name = serializers.CharField(source="facility.property.name", read_only=True)
    zone_name = serializers.CharField(source="zone.name", read_only=True)
    zone_code = serializers.CharField(source="zone.zone_code", read_only=True)
    floor_name = serializers.CharField(source="zone.floor.name", read_only=True)
    floor_number = serializers.IntegerField(source="zone.floor.floor_number", read_only=True)
    unit_number = serializers.CharField(source="unit.unit_number", read_only=True)
    property_name = serializers.CharField(source="unit.property.name", read_only=True)

    class Meta:
        model = FacilityUnitSpace
        fields = "__all__"
        read_only_fields = ("id", "organization", "created_at", "updated_at")


class FacilityUnitSpaceWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = FacilityUnitSpace
        fields = [
            "id",
            "facility",
            "zone",
            "unit",
            "space_label",
            "notes",
        ]
        read_only_fields = ("id",)

    def validate(self, attrs):
        instance = getattr(self, "instance", None)
        facility = attrs.get("facility") or getattr(instance, "facility", None)
        zone = attrs.get("zone") or getattr(instance, "zone", None)
        unit = attrs.get("unit") or getattr(instance, "unit", None)

        request = self.context.get("request")
        org = _resolve_request_org(request)
        if org and facility and facility.organization_id != org.id:
            raise serializers.ValidationError({"facility": "Selected facility is not in your organization."})

        if facility and zone and zone.facility_id != facility.id:
            raise serializers.ValidationError({"zone": "Zone must belong to the selected facility."})

        if facility and unit and unit.property_id != facility.property_id:
            raise serializers.ValidationError({"unit": "Unit must belong to the facility's property."})

        if org and unit and unit.organization_id != org.id:
            raise serializers.ValidationError({"unit": "Selected unit is not in your organization."})
        return attrs
