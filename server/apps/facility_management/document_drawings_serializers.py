from __future__ import annotations

from rest_framework import serializers

from apps.properties.models import Inspection, WorkOrder

from .models import Facility, FacilityDocument, FacilityUnitSpace


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


class FacilityDocumentListSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)
    facility_code = serializers.CharField(source="facility.facility_code", read_only=True, default="")
    space_label = serializers.SerializerMethodField()
    asset_component_name = serializers.CharField(source="asset_component.name", read_only=True, default="")
    work_order_title = serializers.CharField(source="linked_work_order.title", read_only=True, default="")
    inspection_title = serializers.CharField(source="linked_inspection.title", read_only=True, default="")
    document_type_display = serializers.CharField(source="get_document_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    source_display = serializers.CharField(source="get_source_display", read_only=True)
    uploaded_by_name = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = FacilityDocument
        fields = [
            "id",
            "property",
            "property_name",
            "facility",
            "facility_code",
            "facility_space",
            "space_label",
            "asset_component",
            "asset_component_name",
            "linked_work_order",
            "work_order_title",
            "linked_inspection",
            "inspection_title",
            "title",
            "document_type",
            "document_type_display",
            "description",
            "version_label",
            "reference_number",
            "issued_date",
            "expiry_date",
            "review_due_date",
            "status",
            "status_display",
            "source",
            "source_display",
            "generated_summary",
            "uploaded_by",
            "uploaded_by_name",
            "file_url",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_space_label(self, obj):
        return _space_label(obj.facility_space)

    def get_uploaded_by_name(self, obj):
        return _user_display(obj.uploaded_by)

    def get_file_url(self, obj):
        if not obj.file:
            return ""
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url


class FacilityDocumentDetailSerializer(FacilityDocumentListSerializer):
    class Meta(FacilityDocumentListSerializer.Meta):
        fields = FacilityDocumentListSerializer.Meta.fields


class FacilityDocumentWriteSerializer(serializers.ModelSerializer):
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
    linked_work_order = serializers.PrimaryKeyRelatedField(
        queryset=WorkOrder.objects.select_related("property", "facility", "facility_space", "asset_component").all(),
        required=False,
        allow_null=True,
    )
    linked_inspection = serializers.PrimaryKeyRelatedField(
        queryset=Inspection.objects.select_related("property", "unit").all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = FacilityDocument
        fields = [
            "id",
            "facility",
            "facility_space",
            "asset_component",
            "linked_work_order",
            "linked_inspection",
            "title",
            "document_type",
            "file",
            "description",
            "version_label",
            "reference_number",
            "issued_date",
            "expiry_date",
            "review_due_date",
            "status",
            "source",
            "generated_summary",
            "notes",
        ]
        read_only_fields = ["id"]
        extra_kwargs = {
            "asset_component": {"required": False, "allow_null": True},
            "file": {"required": False, "allow_null": True},
            "description": {"required": False, "allow_blank": True},
            "version_label": {"required": False, "allow_blank": True},
            "reference_number": {"required": False, "allow_blank": True},
            "issued_date": {"required": False, "allow_null": True},
            "expiry_date": {"required": False, "allow_null": True},
            "review_due_date": {"required": False, "allow_null": True},
            "status": {"required": False},
            "source": {"required": False},
            "generated_summary": {"required": False, "allow_blank": True},
            "notes": {"required": False, "allow_blank": True},
        }

    def _org(self):
        return _resolve_request_org(self.context.get("request"))

    def _validate_org(self, value, label: str):
        org = self._org()
        if value is not None and org is not None and getattr(value, "organization_id", None) != org.id:
            raise serializers.ValidationError(f"Selected {label} is not in your organization.")
        return value

    def validate_facility(self, value):
        return self._validate_org(value, "facility")

    def validate_facility_space(self, value):
        return self._validate_org(value, "space")

    def validate_asset_component(self, value):
        return self._validate_org(value, "asset")

    def validate_linked_work_order(self, value):
        return self._validate_org(value, "work order")

    def validate_linked_inspection(self, value):
        return self._validate_org(value, "inspection")

    def validate(self, attrs):
        instance = getattr(self, "instance", None)
        property_obj = getattr(instance, "property", None)
        facility = attrs.get("facility", getattr(instance, "facility", None))
        facility_space = attrs.get("facility_space", getattr(instance, "facility_space", None))
        asset_component = attrs.get("asset_component", getattr(instance, "asset_component", None))
        linked_work_order = attrs.get("linked_work_order", getattr(instance, "linked_work_order", None))
        linked_inspection = attrs.get("linked_inspection", getattr(instance, "linked_inspection", None))

        if asset_component is not None:
            property_obj = asset_component.property
            facility = asset_component.facility or _facility_for_property(asset_component.property)
            facility_space = asset_component.facility_space or _space_for_unit(asset_component.unit)
        elif facility_space is not None:
            if facility is not None and facility_space.facility_id != facility.id:
                raise serializers.ValidationError({"facility_space": "Selected space does not belong to the chosen facility."})
            facility = facility_space.facility
            property_obj = facility_space.facility.property
        elif facility is not None:
            property_obj = facility.property
        elif linked_work_order is not None:
            property_obj = linked_work_order.property
            facility = linked_work_order.facility or _facility_for_property(linked_work_order.property)
            facility_space = linked_work_order.facility_space
            asset_component = linked_work_order.asset_component
        elif linked_inspection is not None:
            property_obj = linked_inspection.property
            facility = _facility_for_property(linked_inspection.property)
            facility_space = _space_for_unit(linked_inspection.unit)

        if property_obj is None and instance is None:
            raise serializers.ValidationError(
                {"facility": "Select a facility, room, asset, work order, or inspection."}
            )

        attrs["property"] = property_obj
        if facility is not None:
            attrs["facility"] = facility
        if facility_space is not None:
            attrs["facility_space"] = facility_space
        if asset_component is not None:
            attrs["asset_component"] = asset_component

        source = attrs.get("source", getattr(instance, "source", FacilityDocument.Source.MANUAL))
        document_type = attrs.get(
            "document_type",
            getattr(instance, "document_type", FacilityDocument.DocumentType.OTHER),
        )
        file_obj = attrs.get("file", getattr(instance, "file", None))
        summary = attrs.get("generated_summary", getattr(instance, "generated_summary", ""))
        if (
            document_type
            in {
                FacilityDocument.DocumentType.BLUEPRINT,
                FacilityDocument.DocumentType.DRAWING,
                FacilityDocument.DocumentType.EQUIPMENT_MANUAL,
                FacilityDocument.DocumentType.COMPLIANCE_CERTIFICATE,
            }
            and not file_obj
        ):
            raise serializers.ValidationError({"file": "A file upload is required for this document type."})
        if document_type == FacilityDocument.DocumentType.MAINTENANCE_LOG and not file_obj and not summary and not attrs.get(
            "description",
            getattr(instance, "description", ""),
        ):
            raise serializers.ValidationError(
                {"generated_summary": "Provide a maintenance summary or upload a supporting file."}
            )
        if source == FacilityDocument.Source.GENERATED:
            attrs["source"] = FacilityDocument.Source.GENERATED
        elif instance is None:
            attrs["source"] = FacilityDocument.Source.MANUAL

        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated and instance is None:
            attrs["uploaded_by"] = request.user
        org = self._org()
        if org is not None:
            attrs["organization"] = org
        return attrs
