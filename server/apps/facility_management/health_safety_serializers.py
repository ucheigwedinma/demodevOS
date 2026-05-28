from __future__ import annotations

from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from apps.compliance.models import ComplianceViolation
from apps.properties.models import Inspection, PropertyDocument, WorkOrder

from .models import (
    Facility,
    FacilityComplianceChecklist,
    FacilityComplianceChecklistItem,
    FacilityIncident,
    FacilityRegulatoryDocument,
    FacilitySafetyAuditLog,
    FacilityUnitSpace,
)


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


def _facility_for_property(property_obj):
    return getattr(property_obj, "facility_registry", None) if property_obj else None


def _space_for_unit(unit):
    return getattr(unit, "facility_space", None) if unit else None


def _space_label(space) -> str:
    if not space:
        return ""
    return space.space_label or space.unit.unit_number


class FacilityIncidentListSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True, default="")
    facility = serializers.SerializerMethodField()
    facility_code = serializers.SerializerMethodField()
    facility_space = serializers.SerializerMethodField()
    space_label = serializers.SerializerMethodField()
    unit_number = serializers.SerializerMethodField()
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    severity_display = serializers.CharField(source="get_severity_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    work_order_status = serializers.CharField(source="work_order.status", read_only=True, default="")
    follow_up_inspection_status = serializers.CharField(
        source="follow_up_inspection.status", read_only=True, default=""
    )

    class Meta:
        model = FacilityIncident
        fields = [
            "id",
            "incident_code",
            "property",
            "property_name",
            "facility",
            "facility_code",
            "facility_space",
            "space_label",
            "unit_number",
            "work_order",
            "work_order_status",
            "follow_up_inspection",
            "follow_up_inspection_status",
            "title",
            "description",
            "category",
            "category_display",
            "severity",
            "severity_display",
            "status",
            "status_display",
            "occurred_at",
            "resolved_at",
            "reported_by",
            "assigned_to",
            "requires_regulatory_report",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_facility(self, obj):
        facility = obj.facility or _facility_for_property(obj.property)
        return facility.id if facility else None

    def get_facility_code(self, obj):
        facility = obj.facility or _facility_for_property(obj.property)
        return facility.facility_code if facility else ""

    def get_facility_space(self, obj):
        if obj.facility_space_id:
            return obj.facility_space_id
        return None

    def get_space_label(self, obj):
        return _space_label(obj.facility_space)

    def get_unit_number(self, obj):
        if obj.facility_space_id and obj.facility_space.unit_id:
            return obj.facility_space.unit.unit_number
        return ""


class FacilityIncidentDetailSerializer(FacilityIncidentListSerializer):
    class Meta(FacilityIncidentListSerializer.Meta):
        fields = FacilityIncidentListSerializer.Meta.fields


class FacilityIncidentWriteSerializer(serializers.ModelSerializer):
    facility = serializers.PrimaryKeyRelatedField(
        queryset=Facility.objects.select_related("property").all(),
        required=False,
        allow_null=True,
    )
    facility_space = serializers.PrimaryKeyRelatedField(
        queryset=FacilityUnitSpace.objects.select_related("facility", "unit").all(),
        required=False,
        allow_null=True,
    )
    work_order = serializers.PrimaryKeyRelatedField(
        queryset=WorkOrder.objects.select_related("property", "facility", "facility_space").all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = FacilityIncident
        fields = [
            "id",
            "property",
            "facility",
            "facility_space",
            "work_order",
            "title",
            "description",
            "category",
            "severity",
            "status",
            "occurred_at",
            "resolved_at",
            "reported_by",
            "assigned_to",
            "requires_regulatory_report",
        ]
        read_only_fields = ["id"]
        extra_kwargs = {
            "property": {"required": False, "allow_null": True},
            "description": {"required": False, "allow_blank": True},
            "resolved_at": {"required": False, "allow_null": True},
            "reported_by": {"required": False, "allow_blank": True},
            "assigned_to": {"required": False, "allow_blank": True},
            "requires_regulatory_report": {"required": False},
        }

    def _org(self):
        return _resolve_request_org(self.context.get("request"))

    def _validate_org(self, value, label: str):
        org = self._org()
        if value is not None and org is not None and getattr(value, "organization_id", None) != org.id:
            raise serializers.ValidationError(f"Selected {label} is not in your organization.")
        return value

    def validate_property(self, value):
        return self._validate_org(value, "property")

    def validate_facility(self, value):
        return self._validate_org(value, "facility")

    def validate_facility_space(self, value):
        return self._validate_org(value, "space")

    def validate_work_order(self, value):
        return self._validate_org(value, "work order")

    def validate_occurred_at(self, value):
        if value > timezone.now() + timedelta(hours=1):
            raise serializers.ValidationError("Incident occurrence time cannot be in the future.")
        return value

    def validate(self, attrs):
        instance = getattr(self, "instance", None)
        property_obj = attrs.get("property", getattr(instance, "property", None))
        facility = attrs.get("facility", getattr(instance, "facility", None))
        facility_space = attrs.get("facility_space", getattr(instance, "facility_space", None))
        work_order = attrs.get("work_order", getattr(instance, "work_order", None))

        if facility_space is not None:
            if facility and facility_space.facility_id != facility.id:
                raise serializers.ValidationError({"facility_space": "Selected space does not belong to the chosen facility."})
            facility = facility_space.facility
            property_obj = facility_space.facility.property
        elif facility is not None:
            property_obj = facility.property
        elif work_order is not None:
            property_obj = work_order.property
            facility = work_order.facility or _facility_for_property(work_order.property)
            if work_order.facility_space_id:
                facility_space = work_order.facility_space

        if property_obj is None and instance is None:
            raise serializers.ValidationError(
                {"property": "Select a facility, room, property, or linked work order for this incident."}
            )

        if property_obj is not None:
            attrs["property"] = property_obj
            facility = facility or _facility_for_property(property_obj)
        if facility is not None:
            attrs["facility"] = facility
        if facility_space is not None:
            attrs["facility_space"] = facility_space

        if not attrs.get("reported_by") and instance is None:
            request = self.context.get("request")
            if request and request.user and request.user.is_authenticated:
                attrs["reported_by"] = _user_display(request.user)

        org = self._org()
        if org is not None:
            attrs["organization"] = org
        return attrs


class FacilityHealthSafetyInspectionListSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)
    facility = serializers.SerializerMethodField()
    facility_code = serializers.SerializerMethodField()
    facility_space = serializers.SerializerMethodField()
    space_label = serializers.SerializerMethodField()
    unit_number = serializers.CharField(source="unit.unit_number", read_only=True, default="")
    inspection_type_display = serializers.CharField(source="get_inspection_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    rating_display = serializers.CharField(source="get_rating_display", read_only=True)
    risk_level_display = serializers.CharField(source="get_risk_level_display", read_only=True)
    compliance_status_display = serializers.CharField(
        source="get_compliance_status_display", read_only=True
    )
    linked_incident = serializers.SerializerMethodField()
    linked_incident_code = serializers.SerializerMethodField()

    class Meta:
        model = Inspection
        fields = [
            "id",
            "property",
            "property_name",
            "facility",
            "facility_code",
            "facility_space",
            "space_label",
            "unit",
            "unit_number",
            "linked_incident",
            "linked_incident_code",
            "title",
            "inspection_type",
            "inspection_type_display",
            "status",
            "status_display",
            "scheduled_date",
            "completed_date",
            "inspector",
            "findings",
            "rating",
            "rating_display",
            "risk_level",
            "risk_level_display",
            "corrective_action_required",
            "compliance_status",
            "compliance_status_display",
            "expiry_date",
            "follow_up_required",
            "follow_up_notes",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def _linked_incident(self, obj):
        incident = getattr(obj, "_linked_incident_cache", None)
        if incident is None:
            incident = obj.facility_incident_follow_ups.order_by("-updated_at", "-id").first()
            obj._linked_incident_cache = incident
        return incident

    def get_facility(self, obj):
        facility = _facility_for_property(obj.property)
        return facility.id if facility else None

    def get_facility_code(self, obj):
        facility = _facility_for_property(obj.property)
        return facility.facility_code if facility else ""

    def get_facility_space(self, obj):
        space = _space_for_unit(obj.unit)
        return space.id if space else None

    def get_space_label(self, obj):
        return _space_label(_space_for_unit(obj.unit))

    def get_linked_incident(self, obj):
        incident = self._linked_incident(obj)
        return incident.id if incident else None

    def get_linked_incident_code(self, obj):
        incident = self._linked_incident(obj)
        return incident.incident_code if incident else ""


class FacilityHealthSafetyInspectionDetailSerializer(FacilityHealthSafetyInspectionListSerializer):
    class Meta(FacilityHealthSafetyInspectionListSerializer.Meta):
        fields = FacilityHealthSafetyInspectionListSerializer.Meta.fields


class FacilityHealthSafetyInspectionWriteSerializer(serializers.ModelSerializer):
    facility = serializers.PrimaryKeyRelatedField(
        queryset=Facility.objects.select_related("property").all(),
        required=False,
        allow_null=True,
        write_only=True,
    )
    facility_space = serializers.PrimaryKeyRelatedField(
        queryset=FacilityUnitSpace.objects.select_related("facility", "unit").all(),
        required=False,
        allow_null=True,
        write_only=True,
    )
    incident = serializers.PrimaryKeyRelatedField(
        queryset=FacilityIncident.objects.select_related("facility", "facility_space", "property").all(),
        required=False,
        allow_null=True,
        write_only=True,
    )

    class Meta:
        model = Inspection
        fields = [
            "id",
            "property",
            "facility",
            "facility_space",
            "incident",
            "unit",
            "title",
            "inspection_type",
            "status",
            "scheduled_date",
            "completed_date",
            "inspector",
            "findings",
            "rating",
            "risk_level",
            "corrective_action_required",
            "compliance_status",
            "expiry_date",
            "follow_up_required",
            "follow_up_notes",
            "notes",
        ]
        read_only_fields = ["id"]
        extra_kwargs = {
            "property": {"required": False, "allow_null": True},
            "unit": {"required": False, "allow_null": True},
            "completed_date": {"required": False, "allow_null": True},
            "inspector": {"required": False, "allow_blank": True},
            "findings": {"required": False, "allow_blank": True},
            "rating": {"required": False, "allow_blank": True},
            "risk_level": {"required": False, "allow_blank": True},
            "compliance_status": {"required": False, "allow_blank": True},
            "expiry_date": {"required": False, "allow_null": True},
            "follow_up_required": {"required": False},
            "follow_up_notes": {"required": False, "allow_blank": True},
            "notes": {"required": False, "allow_blank": True},
        }

    @property
    def linked_incident(self):
        return getattr(self, "_linked_incident", None)

    def _org(self):
        return _resolve_request_org(self.context.get("request"))

    def _validate_org(self, value, label: str):
        org = self._org()
        if value is not None and org is not None and getattr(value, "organization_id", None) != org.id:
            raise serializers.ValidationError(f"Selected {label} is not in your organization.")
        return value

    def validate_property(self, value):
        return self._validate_org(value, "property")

    def validate_facility(self, value):
        return self._validate_org(value, "facility")

    def validate_facility_space(self, value):
        return self._validate_org(value, "space")

    def validate_incident(self, value):
        return self._validate_org(value, "incident")

    def validate_unit(self, value):
        return self._validate_org(value, "unit")

    def validate(self, attrs):
        instance = getattr(self, "instance", None)
        property_obj = attrs.get("property", getattr(instance, "property", None))
        unit = attrs.get("unit", getattr(instance, "unit", None))
        facility = attrs.get("facility")
        facility_space = attrs.get("facility_space")
        incident = attrs.get("incident")

        if facility_space is not None:
            if facility is not None and facility_space.facility_id != facility.id:
                raise serializers.ValidationError({"facility_space": "Selected space does not belong to the chosen facility."})
            facility = facility_space.facility
            property_obj = facility_space.facility.property
            unit = facility_space.unit
        elif facility is not None:
            property_obj = facility.property
        elif incident is not None:
            if incident.facility_space_id:
                facility_space = incident.facility_space
                unit = incident.facility_space.unit
            facility = incident.facility or _facility_for_property(incident.property)
            property_obj = incident.property or (facility.property if facility else None)
        elif unit is not None and property_obj is None:
            property_obj = unit.property

        if property_obj is None and instance is None:
            raise serializers.ValidationError(
                {"property": "Select a facility, room, incident, or property for this inspection."}
            )

        if property_obj is not None:
            attrs["property"] = property_obj
        if unit is not None:
            attrs["unit"] = unit

        status_value = attrs.get("status", getattr(instance, "status", Inspection.Status.SCHEDULED))
        if status_value == Inspection.Status.COMPLETED and not attrs.get(
            "completed_date", getattr(instance, "completed_date", None)
        ):
            attrs["completed_date"] = timezone.localdate()

        self._linked_incident = incident or getattr(self, "_linked_incident", None)
        return attrs

    def create(self, validated_data):
        validated_data.pop("facility", None)
        validated_data.pop("facility_space", None)
        validated_data.pop("incident", None)
        org = self._org()
        if org is not None:
            validated_data["organization"] = org
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop("facility", None)
        validated_data.pop("facility_space", None)
        validated_data.pop("incident", None)
        return super().update(instance, validated_data)


class FacilityComplianceChecklistItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = FacilityComplianceChecklistItem
        fields = [
            "id",
            "title",
            "description",
            "is_mandatory",
            "is_compliant",
            "response_note",
            "corrective_action",
            "sort_order",
        ]
        read_only_fields = ["id"]
        extra_kwargs = {
            "description": {"required": False, "allow_blank": True},
            "response_note": {"required": False, "allow_blank": True},
            "corrective_action": {"required": False, "allow_blank": True},
            "sort_order": {"required": False},
        }


class FacilityComplianceChecklistListSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)
    facility_code = serializers.CharField(source="facility.facility_code", read_only=True, default="")
    space_label = serializers.SerializerMethodField()
    checklist_type_display = serializers.CharField(source="get_checklist_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    compliance_requirement_name = serializers.CharField(
        source="compliance_requirement.name", read_only=True, default=""
    )
    linked_incident_code = serializers.CharField(source="linked_incident.incident_code", read_only=True, default="")
    linked_inspection_title = serializers.CharField(source="linked_inspection.title", read_only=True, default="")
    failure_count = serializers.SerializerMethodField()

    class Meta:
        model = FacilityComplianceChecklist
        fields = [
            "id",
            "property",
            "property_name",
            "facility",
            "facility_code",
            "facility_space",
            "space_label",
            "linked_incident",
            "linked_incident_code",
            "linked_inspection",
            "linked_inspection_title",
            "compliance_requirement",
            "compliance_requirement_name",
            "title",
            "checklist_type",
            "checklist_type_display",
            "frequency",
            "status",
            "status_display",
            "responsible_person",
            "due_date",
            "completed_at",
            "last_completed_date",
            "next_due_date",
            "overall_score",
            "compliant_items_count",
            "total_items_count",
            "failure_count",
            "auto_create_violation",
            "auto_create_follow_up_inspection",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_space_label(self, obj):
        return _space_label(obj.facility_space)

    def get_failure_count(self, obj):
        return obj.items.filter(is_compliant=False).count()


class FacilityComplianceChecklistDetailSerializer(FacilityComplianceChecklistListSerializer):
    items = FacilityComplianceChecklistItemSerializer(many=True, read_only=True)

    class Meta(FacilityComplianceChecklistListSerializer.Meta):
        fields = FacilityComplianceChecklistListSerializer.Meta.fields + ["items"]


class FacilityComplianceChecklistWriteSerializer(serializers.ModelSerializer):
    facility = serializers.PrimaryKeyRelatedField(
        queryset=Facility.objects.select_related("property").all(),
        required=False,
        allow_null=True,
    )
    facility_space = serializers.PrimaryKeyRelatedField(
        queryset=FacilityUnitSpace.objects.select_related("facility", "unit").all(),
        required=False,
        allow_null=True,
    )
    items = FacilityComplianceChecklistItemSerializer(many=True, required=False)

    class Meta:
        model = FacilityComplianceChecklist
        fields = [
            "id",
            "property",
            "facility",
            "facility_space",
            "linked_incident",
            "linked_inspection",
            "compliance_requirement",
            "title",
            "checklist_type",
            "frequency",
            "status",
            "responsible_person",
            "due_date",
            "completed_at",
            "last_completed_date",
            "next_due_date",
            "auto_create_violation",
            "auto_create_follow_up_inspection",
            "notes",
            "items",
        ]
        read_only_fields = ["id", "last_completed_date", "next_due_date"]
        extra_kwargs = {
            "property": {"required": False, "allow_null": True},
            "linked_incident": {"required": False, "allow_null": True},
            "linked_inspection": {"required": False, "allow_null": True},
            "compliance_requirement": {"required": False, "allow_null": True},
            "responsible_person": {"required": False, "allow_blank": True},
            "completed_at": {"required": False, "allow_null": True},
            "notes": {"required": False, "allow_blank": True},
            "auto_create_violation": {"required": False},
            "auto_create_follow_up_inspection": {"required": False},
        }

    def _org(self):
        return _resolve_request_org(self.context.get("request"))

    def _validate_org(self, value, label: str):
        org = self._org()
        if value is not None and org is not None and getattr(value, "organization_id", None) != org.id:
            raise serializers.ValidationError(f"Selected {label} is not in your organization.")
        return value

    def validate_property(self, value):
        return self._validate_org(value, "property")

    def validate_facility(self, value):
        return self._validate_org(value, "facility")

    def validate_facility_space(self, value):
        return self._validate_org(value, "space")

    def validate_linked_incident(self, value):
        return self._validate_org(value, "incident")

    def validate_linked_inspection(self, value):
        return self._validate_org(value, "inspection")

    def validate_compliance_requirement(self, value):
        return self._validate_org(value, "compliance requirement")

    def validate(self, attrs):
        instance = getattr(self, "instance", None)
        property_obj = attrs.get("property", getattr(instance, "property", None))
        facility = attrs.get("facility", getattr(instance, "facility", None))
        facility_space = attrs.get("facility_space", getattr(instance, "facility_space", None))
        linked_incident = attrs.get("linked_incident", getattr(instance, "linked_incident", None))
        linked_inspection = attrs.get("linked_inspection", getattr(instance, "linked_inspection", None))

        if facility_space is not None:
            if facility is not None and facility_space.facility_id != facility.id:
                raise serializers.ValidationError({"facility_space": "Selected space does not belong to the chosen facility."})
            facility = facility_space.facility
            property_obj = facility_space.facility.property
        elif facility is not None:
            property_obj = facility.property
        elif linked_incident is not None:
            property_obj = linked_incident.property
            facility = linked_incident.facility or _facility_for_property(linked_incident.property)
            facility_space = linked_incident.facility_space
        elif linked_inspection is not None:
            property_obj = linked_inspection.property
            facility = _facility_for_property(linked_inspection.property)
            facility_space = _space_for_unit(linked_inspection.unit)

        if property_obj is None and instance is None:
            raise serializers.ValidationError(
                {"property": "Select a facility, room, linked incident, inspection, or property."}
            )

        if property_obj is not None:
            attrs["property"] = property_obj
        if facility is not None:
            attrs["facility"] = facility
        if facility_space is not None:
            attrs["facility_space"] = facility_space

        org = self._org()
        if org is not None:
            attrs["organization"] = org
        return attrs

    def _replace_items(self, checklist, items_data):
        checklist.items.all().delete()
        FacilityComplianceChecklistItem.objects.bulk_create(
            [FacilityComplianceChecklistItem(checklist=checklist, **item) for item in items_data]
        )

    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        checklist = super().create(validated_data)
        if items_data:
            self._replace_items(checklist, items_data)
        return checklist

    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)
        checklist = super().update(instance, validated_data)
        if items_data is not None:
            self._replace_items(checklist, items_data)
        return checklist


class FacilityComplianceViolationListSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)
    severity_display = serializers.CharField(source="get_severity_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = ComplianceViolation
        fields = [
            "id",
            "property",
            "property_name",
            "title",
            "description",
            "violation_type",
            "severity",
            "severity_display",
            "status",
            "status_display",
            "reported_date",
            "due_date",
            "resolved_date",
            "corrective_action",
            "assigned_to",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class FacilityRegulatoryDocumentListSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source="property_document.title", read_only=True)
    description = serializers.CharField(source="property_document.description", read_only=True)
    document_type = serializers.CharField(source="property_document.document_type", read_only=True)
    document_type_display = serializers.SerializerMethodField()
    property_name = serializers.CharField(source="property.name", read_only=True)
    facility_code = serializers.CharField(source="facility.facility_code", read_only=True, default="")
    compliance_requirement_name = serializers.CharField(
        source="compliance_requirement.name", read_only=True, default=""
    )
    uploaded_by_name = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = FacilityRegulatoryDocument
        fields = [
            "id",
            "property",
            "property_name",
            "facility",
            "facility_code",
            "property_document",
            "title",
            "description",
            "document_type",
            "document_type_display",
            "file_url",
            "compliance_requirement",
            "compliance_requirement_name",
            "status",
            "status_display",
            "issuing_authority",
            "reference_number",
            "issue_date",
            "expiry_date",
            "review_due_date",
            "uploaded_by",
            "uploaded_by_name",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_uploaded_by_name(self, obj):
        return _user_display(obj.uploaded_by)

    def get_document_type_display(self, obj):
        return obj.property_document.get_document_type_display()

    def get_file_url(self, obj):
        request = self.context.get("request")
        file_field = obj.property_document.file
        if not file_field:
            return ""
        if request:
            return request.build_absolute_uri(file_field.url)
        return file_field.url


class FacilityRegulatoryDocumentDetailSerializer(FacilityRegulatoryDocumentListSerializer):
    class Meta(FacilityRegulatoryDocumentListSerializer.Meta):
        fields = FacilityRegulatoryDocumentListSerializer.Meta.fields


class FacilityRegulatoryDocumentWriteSerializer(serializers.ModelSerializer):
    facility = serializers.PrimaryKeyRelatedField(
        queryset=Facility.objects.select_related("property").all(),
        required=False,
        allow_null=True,
    )
    file = serializers.FileField(required=False, write_only=True)
    title = serializers.CharField(write_only=True)
    document_type = serializers.ChoiceField(choices=PropertyDocument.DocumentType.choices, write_only=True)
    description = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = FacilityRegulatoryDocument
        fields = [
            "id",
            "facility",
            "file",
            "title",
            "document_type",
            "description",
            "compliance_requirement",
            "status",
            "issuing_authority",
            "reference_number",
            "issue_date",
            "expiry_date",
            "review_due_date",
            "notes",
        ]
        read_only_fields = ["id"]
        extra_kwargs = {
            "compliance_requirement": {"required": False, "allow_null": True},
            "status": {"required": False},
            "issuing_authority": {"required": False, "allow_blank": True},
            "reference_number": {"required": False, "allow_blank": True},
            "issue_date": {"required": False, "allow_null": True},
            "expiry_date": {"required": False, "allow_null": True},
            "review_due_date": {"required": False, "allow_null": True},
            "notes": {"required": False, "allow_blank": True},
        }

    def _org(self):
        return _resolve_request_org(self.context.get("request"))

    def validate_facility(self, value):
        org = self._org()
        if value is not None and org is not None and value.organization_id != org.id:
            raise serializers.ValidationError("Selected facility is not in your organization.")
        return value

    def validate_compliance_requirement(self, value):
        org = self._org()
        if value is not None and org is not None and value.organization_id != org.id:
            raise serializers.ValidationError("Selected compliance requirement is not in your organization.")
        return value

    def validate(self, attrs):
        instance = getattr(self, "instance", None)
        facility = attrs.get("facility", getattr(instance, "facility", None))
        property_obj = facility.property if facility else getattr(instance, "property", None)

        if facility is None and instance is None:
            raise serializers.ValidationError({"facility": "Facility is required for regulatory documents."})
        if property_obj is None and instance is None:
            raise serializers.ValidationError({"facility": "Facility is required for regulatory documents."})

        if instance is None and not attrs.get("file"):
            raise serializers.ValidationError({"file": "A document file is required."})

        attrs["property"] = property_obj
        org = self._org()
        if org is not None:
            attrs["organization"] = org
        return attrs

    def create(self, validated_data):
        file_obj = validated_data.pop("file")
        title = validated_data.pop("title")
        document_type = validated_data.pop("document_type")
        description = validated_data.pop("description", "")
        property_obj = validated_data["property"]

        request = self.context.get("request")
        property_document = PropertyDocument.objects.create(
            organization=property_obj.organization,
            property=property_obj,
            file=file_obj,
            title=title,
            document_type=document_type,
            description=description,
        )
        if request and request.user and request.user.is_authenticated and not validated_data.get("uploaded_by"):
            validated_data["uploaded_by"] = request.user
        validated_data["property_document"] = property_document
        return super().create(validated_data)

    def update(self, instance, validated_data):
        property_document = instance.property_document
        file_obj = validated_data.pop("file", None)
        title = validated_data.pop("title", None)
        document_type = validated_data.pop("document_type", None)
        description = validated_data.pop("description", None)

        if title is not None and property_document.title != title:
            property_document.title = title
        if document_type is not None and property_document.document_type != document_type:
            property_document.document_type = document_type
        if description is not None and property_document.description != description:
            property_document.description = description
        if file_obj is not None:
            property_document.file = file_obj
        property_document.property = validated_data.get("property", instance.property)
        property_document.save()

        return super().update(instance, validated_data)


class FacilitySafetyAuditLogSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True, default="")
    facility_code = serializers.CharField(source="facility.facility_code", read_only=True, default="")
    actor_name = serializers.SerializerMethodField()
    entity_type_display = serializers.CharField(source="get_entity_type_display", read_only=True)
    event_type_display = serializers.CharField(source="get_event_type_display", read_only=True)

    class Meta:
        model = FacilitySafetyAuditLog
        fields = [
            "id",
            "property",
            "property_name",
            "facility",
            "facility_code",
            "entity_type",
            "entity_type_display",
            "event_type",
            "event_type_display",
            "entity_id",
            "actor",
            "actor_name",
            "summary",
            "details",
            "created_at",
        ]
        read_only_fields = fields

    def get_actor_name(self, obj):
        return _user_display(obj.actor)
