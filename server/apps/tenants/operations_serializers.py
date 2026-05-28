from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers

from apps.facility_management.models import Facility, FacilityUnitSpace
from apps.finance.models import Invoice, InvoicePayment
from apps.properties.models import Property, ServiceRequest, Unit

from .models import (
    LeaseAgreement,
    LeaseRenewalRequest,
    LeaseTerminationRequest,
    OccupancyRecord,
    RecurringChargeRule,
    TenantBroadcast,
    TenantComplaint,
    TenantDocumentRecord,
    TenantInspection,
    TenantProfile,
)

User = get_user_model()


def _resolve_request_org(request):
    org = getattr(request, "organization", None)
    if org is not None:
        return org
    profile = getattr(getattr(request, "user", None), "profile", None)
    return getattr(profile, "organization", None)


def _profile_context(profile: TenantProfile | None) -> dict:
    if profile is None:
        return {
            "property": None,
            "unit": None,
            "facility": None,
            "facility_space": None,
        }
    property_record = profile.property
    unit = profile.unit
    facility = profile.facility
    facility_space = profile.facility_space
    if facility_space:
        unit = facility_space.unit
        facility = facility_space.facility
        property_record = facility_space.facility.property
    elif unit:
        property_record = unit.property
        linked_space = getattr(unit, "facility_space", None)
        if linked_space and linked_space.organization_id == profile.organization_id:
            facility_space = linked_space
            facility = linked_space.facility
    elif facility:
        property_record = facility.property
    return {
        "property": property_record,
        "unit": unit,
        "facility": facility,
        "facility_space": facility_space,
    }


def _derive_context(*, tenant_profile=None, lease_agreement=None, property_record=None, unit=None, facility=None, facility_space=None):
    if lease_agreement is not None:
        property_record = lease_agreement.property or property_record
        unit = lease_agreement.unit or unit
        facility = lease_agreement.facility or facility
        facility_space = lease_agreement.facility_space or facility_space
    if facility_space is not None:
        if unit is None:
            unit = facility_space.unit
        if facility is None:
            facility = facility_space.facility
        if property_record is None:
            property_record = facility_space.facility.property
    elif unit is not None:
        if property_record is None:
            property_record = unit.property
        linked_space = getattr(unit, "facility_space", None)
        if facility_space is None and linked_space and linked_space.organization_id == unit.organization_id:
            facility_space = linked_space
            if facility is None:
                facility = linked_space.facility
        elif facility is None:
            facility = getattr(unit.property, "facility_registry", None)
    elif facility is not None:
        if property_record is None:
            property_record = facility.property
    elif property_record is not None:
        facility = getattr(property_record, "facility_registry", None)
    elif tenant_profile is not None:
        profile_ctx = _profile_context(tenant_profile)
        property_record = profile_ctx["property"]
        unit = profile_ctx["unit"]
        facility = profile_ctx["facility"]
        facility_space = profile_ctx["facility_space"]
    return {
        "property": property_record,
        "unit": unit,
        "facility": facility,
        "facility_space": facility_space,
    }


def _display_name(user):
    if not user:
        return ""
    full_name = user.get_full_name().strip()
    return full_name or user.email or user.username


def _space_label(obj) -> str:
    if getattr(obj, "facility_space_id", None) and getattr(obj, "facility_space", None):
        return obj.facility_space.space_label or obj.facility_space.unit.unit_number
    return ""


def _unit_label(obj) -> str:
    if getattr(obj, "unit_id", None) and getattr(obj, "unit", None):
        return obj.unit.unit_number
    if getattr(obj, "facility_space_id", None) and getattr(obj, "facility_space", None):
        return obj.facility_space.unit.unit_number
    return ""


def _property_name(obj) -> str:
    if getattr(obj, "property_id", None) and getattr(obj, "property", None):
        return obj.property.name
    if getattr(obj, "facility_id", None) and getattr(obj, "facility", None):
        return obj.facility.property.name
    if getattr(obj, "facility_space_id", None) and getattr(obj, "facility_space", None):
        return obj.facility_space.facility.property.name
    if getattr(obj, "unit_id", None) and getattr(obj, "unit", None):
        return obj.unit.property.name
    return ""


def _set_org_queryset(field, model, org, *, order_by=None, select_related=None):
    queryset = model.objects.filter(organization=org)
    if select_related:
        queryset = queryset.select_related(*select_related)
    if order_by:
        queryset = queryset.order_by(*order_by)
    field.queryset = queryset


def _sync_and_validate_relationships(instance):
    if hasattr(instance, "sync_relationships"):
        instance.sync_relationships()
    if hasattr(instance, "clean"):
        try:
            instance.clean()
        except DjangoValidationError as exc:
            if hasattr(exc, "message_dict"):
                raise serializers.ValidationError(exc.message_dict) from exc
            raise serializers.ValidationError(exc.messages) from exc


class LeaseAgreementSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source="tenant_profile.resolved_display_name", read_only=True)
    property_name = serializers.SerializerMethodField()
    unit_label = serializers.SerializerMethodField()
    facility_code = serializers.CharField(source="facility.facility_code", read_only=True, default="")
    space_label = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    payment_frequency_display = serializers.CharField(source="get_payment_frequency_display", read_only=True)

    class Meta:
        model = LeaseAgreement
        fields = [
            "id",
            "tenant_profile",
            "tenant_name",
            "property",
            "property_name",
            "unit",
            "unit_label",
            "facility",
            "facility_code",
            "facility_space",
            "space_label",
            "lease_code",
            "title",
            "status",
            "status_display",
            "start_date",
            "end_date",
            "rent_amount",
            "service_charge_amount",
            "security_deposit",
            "currency",
            "payment_frequency",
            "payment_frequency_display",
            "escalation_rule",
            "escalation_value",
            "escalation_frequency_months",
            "notice_period_days",
            "renewal_option",
            "auto_generate_billing",
            "next_billing_date",
            "last_billing_date",
            "last_escalation_date",
            "signed_on",
            "terminated_on",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "lease_code",
            "last_billing_date",
            "last_escalation_date",
            "created_at",
            "updated_at",
        ]

    def get_property_name(self, obj):
        return _property_name(obj)

    def get_unit_label(self, obj):
        return _unit_label(obj)

    def get_space_label(self, obj):
        return _space_label(obj)


class LeaseAgreementWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaseAgreement
        fields = [
            "tenant_profile",
            "property",
            "unit",
            "facility",
            "facility_space",
            "title",
            "status",
            "start_date",
            "end_date",
            "rent_amount",
            "service_charge_amount",
            "security_deposit",
            "currency",
            "payment_frequency",
            "escalation_rule",
            "escalation_value",
            "escalation_frequency_months",
            "notice_period_days",
            "renewal_option",
            "auto_generate_billing",
            "next_billing_date",
            "signed_on",
            "terminated_on",
            "notes",
        ]
        extra_kwargs = {
            "property": {"required": False, "allow_null": True},
            "unit": {"required": False, "allow_null": True},
            "facility": {"required": False, "allow_null": True},
            "facility_space": {"required": False, "allow_null": True},
            "next_billing_date": {"required": False, "allow_null": True},
            "signed_on": {"required": False, "allow_null": True},
            "terminated_on": {"required": False, "allow_null": True},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        org = _resolve_request_org(self.context.get("request"))
        if org is None:
            return
        _set_org_queryset(self.fields["tenant_profile"], TenantProfile, org, order_by=["display_name", "id"])
        _set_org_queryset(self.fields["property"], Property, org, order_by=["name"])
        _set_org_queryset(self.fields["unit"], Unit, org, order_by=["property__name", "unit_number"], select_related=["property"])
        _set_org_queryset(self.fields["facility"], Facility, org, order_by=["property__name", "facility_code"], select_related=["property"])
        _set_org_queryset(
            self.fields["facility_space"],
            FacilityUnitSpace,
            org,
            order_by=["facility__property__name", "unit__unit_number"],
            select_related=["facility", "facility__property", "unit"],
        )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start_date and end_date and end_date <= start_date:
            raise serializers.ValidationError({"end_date": ["End date must be after the start date."]})

        tenant_profile = attrs.get("tenant_profile", getattr(self.instance, "tenant_profile", None))
        context = _derive_context(
            tenant_profile=tenant_profile,
            property_record=attrs.get("property", getattr(self.instance, "property", None)),
            unit=attrs.get("unit", getattr(self.instance, "unit", None)),
            facility=attrs.get("facility", getattr(self.instance, "facility", None)),
            facility_space=attrs.get("facility_space", getattr(self.instance, "facility_space", None)),
        )
        attrs["property"] = context["property"]
        attrs["unit"] = context["unit"]
        attrs["facility"] = context["facility"]
        attrs["facility_space"] = context["facility_space"]

        title = (attrs.get("title") or "").strip()
        if not title and tenant_profile:
            attrs["title"] = f"{tenant_profile.resolved_display_name} lease"
        if attrs.get("auto_generate_billing") and not attrs.get("next_billing_date"):
            attrs["next_billing_date"] = start_date

        candidate = self.instance or LeaseAgreement(organization=tenant_profile.organization if tenant_profile else None)
        for field_name, value in attrs.items():
            setattr(candidate, field_name, value)
        _sync_and_validate_relationships(candidate)
        attrs["property"] = candidate.property
        attrs["unit"] = candidate.unit
        attrs["facility"] = candidate.facility
        attrs["facility_space"] = candidate.facility_space
        return attrs

    def create(self, validated_data):
        return LeaseAgreement.objects.create(**validated_data)

    def to_representation(self, instance):
        return LeaseAgreementSerializer(instance, context=self.context).data


class OccupancyRecordSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source="tenant_profile.resolved_display_name", read_only=True)
    lease_code = serializers.CharField(source="lease_agreement.lease_code", read_only=True, default="")
    property_name = serializers.SerializerMethodField()
    unit_label = serializers.SerializerMethodField()
    facility_code = serializers.CharField(source="facility.facility_code", read_only=True, default="")
    space_label = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = OccupancyRecord
        fields = [
            "id",
            "tenant_profile",
            "tenant_name",
            "lease_agreement",
            "lease_code",
            "property",
            "property_name",
            "unit",
            "unit_label",
            "facility",
            "facility_code",
            "facility_space",
            "space_label",
            "status",
            "status_display",
            "move_in_date",
            "notice_date",
            "move_out_date",
            "vacated_on",
            "occupant_count",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_property_name(self, obj):
        return _property_name(obj)

    def get_unit_label(self, obj):
        return _unit_label(obj)

    def get_space_label(self, obj):
        return _space_label(obj)


class OccupancyRecordWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = OccupancyRecord
        fields = [
            "tenant_profile",
            "lease_agreement",
            "property",
            "unit",
            "facility",
            "facility_space",
            "status",
            "move_in_date",
            "notice_date",
            "move_out_date",
            "vacated_on",
            "occupant_count",
            "notes",
        ]
        extra_kwargs = {
            "property": {"required": False, "allow_null": True},
            "unit": {"required": False, "allow_null": True},
            "facility": {"required": False, "allow_null": True},
            "facility_space": {"required": False, "allow_null": True},
            "notice_date": {"required": False, "allow_null": True},
            "move_out_date": {"required": False, "allow_null": True},
            "vacated_on": {"required": False, "allow_null": True},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        org = _resolve_request_org(self.context.get("request"))
        if org is None:
            return
        _set_org_queryset(self.fields["tenant_profile"], TenantProfile, org, order_by=["display_name", "id"])
        _set_org_queryset(self.fields["lease_agreement"], LeaseAgreement, org, order_by=["end_date", "tenant_profile__display_name"])
        _set_org_queryset(self.fields["property"], Property, org, order_by=["name"])
        _set_org_queryset(self.fields["unit"], Unit, org, order_by=["property__name", "unit_number"], select_related=["property"])
        _set_org_queryset(self.fields["facility"], Facility, org, order_by=["property__name", "facility_code"], select_related=["property"])
        _set_org_queryset(
            self.fields["facility_space"],
            FacilityUnitSpace,
            org,
            order_by=["facility__property__name", "unit__unit_number"],
            select_related=["facility", "facility__property", "unit"],
        )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        tenant_profile = attrs.get("tenant_profile", getattr(self.instance, "tenant_profile", None))
        lease_agreement = attrs.get("lease_agreement", getattr(self.instance, "lease_agreement", None))
        context = _derive_context(
            tenant_profile=tenant_profile,
            lease_agreement=lease_agreement,
            property_record=attrs.get("property", getattr(self.instance, "property", None)),
            unit=attrs.get("unit", getattr(self.instance, "unit", None)),
            facility=attrs.get("facility", getattr(self.instance, "facility", None)),
            facility_space=attrs.get("facility_space", getattr(self.instance, "facility_space", None)),
        )
        attrs["property"] = context["property"]
        attrs["unit"] = context["unit"]
        attrs["facility"] = context["facility"]
        attrs["facility_space"] = context["facility_space"]
        move_in_date = attrs.get("move_in_date", getattr(self.instance, "move_in_date", None))
        move_out_date = attrs.get("move_out_date", getattr(self.instance, "move_out_date", None))
        if move_in_date and move_out_date and move_out_date < move_in_date:
            raise serializers.ValidationError({"move_out_date": ["Move-out date cannot be before move-in date."]})
        candidate = self.instance or OccupancyRecord(organization=tenant_profile.organization if tenant_profile else None)
        for field_name, value in attrs.items():
            setattr(candidate, field_name, value)
        _sync_and_validate_relationships(candidate)
        attrs["property"] = candidate.property
        attrs["unit"] = candidate.unit
        attrs["facility"] = candidate.facility
        attrs["facility_space"] = candidate.facility_space
        return attrs

    def to_representation(self, instance):
        return OccupancyRecordSerializer(instance, context=self.context).data


class LeaseRenewalRequestSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source="tenant_profile.resolved_display_name", read_only=True)
    lease_code = serializers.CharField(source="lease_agreement.lease_code", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    decided_by_name = serializers.SerializerMethodField()

    class Meta:
        model = LeaseRenewalRequest
        fields = [
            "id",
            "tenant_profile",
            "tenant_name",
            "lease_agreement",
            "lease_code",
            "status",
            "status_display",
            "proposed_start_date",
            "proposed_end_date",
            "proposed_rent_amount",
            "proposed_service_charge_amount",
            "generated_automatically",
            "requested_by",
            "decided_by",
            "decided_by_name",
            "decided_at",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_decided_by_name(self, obj):
        return _display_name(obj.decided_by)


class LeaseRenewalRequestWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaseRenewalRequest
        fields = [
            "tenant_profile",
            "lease_agreement",
            "status",
            "proposed_start_date",
            "proposed_end_date",
            "proposed_rent_amount",
            "proposed_service_charge_amount",
            "generated_automatically",
            "notes",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        org = _resolve_request_org(self.context.get("request"))
        if org is None:
            return
        _set_org_queryset(self.fields["tenant_profile"], TenantProfile, org, order_by=["display_name", "id"])
        _set_org_queryset(self.fields["lease_agreement"], LeaseAgreement, org, order_by=["end_date", "tenant_profile__display_name"])

    def validate(self, attrs):
        attrs = super().validate(attrs)
        tenant_profile = attrs.get("tenant_profile", getattr(self.instance, "tenant_profile", None))
        lease_agreement = attrs.get("lease_agreement", getattr(self.instance, "lease_agreement", None))
        if lease_agreement and tenant_profile and lease_agreement.tenant_profile_id != tenant_profile.id:
            raise serializers.ValidationError({"lease_agreement": ["The selected lease does not belong to this tenant."]})
        proposed_start_date = attrs.get("proposed_start_date", getattr(self.instance, "proposed_start_date", None))
        proposed_end_date = attrs.get("proposed_end_date", getattr(self.instance, "proposed_end_date", None))
        if proposed_start_date and proposed_end_date and proposed_end_date <= proposed_start_date:
            raise serializers.ValidationError({"proposed_end_date": ["Proposed end date must be after the start date."]})
        return attrs

    def to_representation(self, instance):
        return LeaseRenewalRequestSerializer(instance, context=self.context).data


class LeaseTerminationRequestSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source="tenant_profile.resolved_display_name", read_only=True)
    lease_code = serializers.CharField(source="lease_agreement.lease_code", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    approved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = LeaseTerminationRequest
        fields = [
            "id",
            "tenant_profile",
            "tenant_name",
            "lease_agreement",
            "lease_code",
            "status",
            "status_display",
            "requested_move_out_date",
            "effective_date",
            "notice_period_days",
            "reason",
            "generated_automatically",
            "requested_by",
            "approved_by",
            "approved_by_name",
            "approved_at",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_approved_by_name(self, obj):
        return _display_name(obj.approved_by)


class LeaseTerminationRequestWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaseTerminationRequest
        fields = [
            "tenant_profile",
            "lease_agreement",
            "status",
            "requested_move_out_date",
            "effective_date",
            "notice_period_days",
            "reason",
            "generated_automatically",
            "notes",
        ]
        extra_kwargs = {
            "effective_date": {"required": False, "allow_null": True},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        org = _resolve_request_org(self.context.get("request"))
        if org is None:
            return
        _set_org_queryset(self.fields["tenant_profile"], TenantProfile, org, order_by=["display_name", "id"])
        _set_org_queryset(self.fields["lease_agreement"], LeaseAgreement, org, order_by=["end_date", "tenant_profile__display_name"])

    def validate(self, attrs):
        attrs = super().validate(attrs)
        tenant_profile = attrs.get("tenant_profile", getattr(self.instance, "tenant_profile", None))
        lease_agreement = attrs.get("lease_agreement", getattr(self.instance, "lease_agreement", None))
        if lease_agreement and tenant_profile and lease_agreement.tenant_profile_id != tenant_profile.id:
            raise serializers.ValidationError({"lease_agreement": ["The selected lease does not belong to this tenant."]})
        effective_date = attrs.get("effective_date", getattr(self.instance, "effective_date", None))
        requested_move_out_date = attrs.get("requested_move_out_date", getattr(self.instance, "requested_move_out_date", None))
        if effective_date and requested_move_out_date and effective_date < requested_move_out_date:
            raise serializers.ValidationError({"effective_date": ["Effective date cannot be earlier than the requested move-out date."]})
        return attrs

    def to_representation(self, instance):
        return LeaseTerminationRequestSerializer(instance, context=self.context).data


class RecurringChargeRuleSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source="tenant_profile.resolved_display_name", read_only=True)
    lease_code = serializers.CharField(source="lease_agreement.lease_code", read_only=True, default="")
    property_name = serializers.SerializerMethodField()
    unit_label = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    charge_type_display = serializers.CharField(source="get_charge_type_display", read_only=True)
    frequency_display = serializers.CharField(source="get_frequency_display", read_only=True)

    class Meta:
        model = RecurringChargeRule
        fields = [
            "id",
            "tenant_profile",
            "tenant_name",
            "lease_agreement",
            "lease_code",
            "property",
            "property_name",
            "unit",
            "unit_label",
            "facility",
            "facility_space",
            "title",
            "charge_type",
            "charge_type_display",
            "status",
            "status_display",
            "amount",
            "currency",
            "frequency",
            "frequency_display",
            "start_date",
            "end_date",
            "next_invoice_date",
            "last_invoiced_date",
            "applies_mid_period_proration",
            "auto_invoice",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "last_invoiced_date", "created_at", "updated_at"]

    def get_property_name(self, obj):
        return _property_name(obj)

    def get_unit_label(self, obj):
        return _unit_label(obj)


class RecurringChargeRuleWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecurringChargeRule
        fields = [
            "tenant_profile",
            "lease_agreement",
            "property",
            "unit",
            "facility",
            "facility_space",
            "title",
            "charge_type",
            "status",
            "amount",
            "currency",
            "frequency",
            "start_date",
            "end_date",
            "next_invoice_date",
            "applies_mid_period_proration",
            "auto_invoice",
            "notes",
        ]
        extra_kwargs = {
            "property": {"required": False, "allow_null": True},
            "unit": {"required": False, "allow_null": True},
            "facility": {"required": False, "allow_null": True},
            "facility_space": {"required": False, "allow_null": True},
            "lease_agreement": {"required": False, "allow_null": True},
            "end_date": {"required": False, "allow_null": True},
            "next_invoice_date": {"required": False, "allow_null": True},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        org = _resolve_request_org(self.context.get("request"))
        if org is None:
            return
        _set_org_queryset(self.fields["tenant_profile"], TenantProfile, org, order_by=["display_name", "id"])
        _set_org_queryset(self.fields["lease_agreement"], LeaseAgreement, org, order_by=["end_date", "tenant_profile__display_name"])
        _set_org_queryset(self.fields["property"], Property, org, order_by=["name"])
        _set_org_queryset(self.fields["unit"], Unit, org, order_by=["property__name", "unit_number"], select_related=["property"])
        _set_org_queryset(self.fields["facility"], Facility, org, order_by=["property__name", "facility_code"], select_related=["property"])
        _set_org_queryset(
            self.fields["facility_space"],
            FacilityUnitSpace,
            org,
            order_by=["facility__property__name", "unit__unit_number"],
            select_related=["facility", "facility__property", "unit"],
        )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({"end_date": ["End date cannot be before start date."]})
        tenant_profile = attrs.get("tenant_profile", getattr(self.instance, "tenant_profile", None))
        lease_agreement = attrs.get("lease_agreement", getattr(self.instance, "lease_agreement", None))
        context = _derive_context(
            tenant_profile=tenant_profile,
            lease_agreement=lease_agreement,
            property_record=attrs.get("property", getattr(self.instance, "property", None)),
            unit=attrs.get("unit", getattr(self.instance, "unit", None)),
            facility=attrs.get("facility", getattr(self.instance, "facility", None)),
            facility_space=attrs.get("facility_space", getattr(self.instance, "facility_space", None)),
        )
        attrs["property"] = context["property"]
        attrs["unit"] = context["unit"]
        attrs["facility"] = context["facility"]
        attrs["facility_space"] = context["facility_space"]
        if not attrs.get("next_invoice_date"):
            attrs["next_invoice_date"] = start_date
        candidate = self.instance or RecurringChargeRule(organization=tenant_profile.organization if tenant_profile else None)
        for field_name, value in attrs.items():
            setattr(candidate, field_name, value)
        _sync_and_validate_relationships(candidate)
        attrs["property"] = candidate.property
        attrs["unit"] = candidate.unit
        attrs["facility"] = candidate.facility
        attrs["facility_space"] = candidate.facility_space
        return attrs

    def to_representation(self, instance):
        return RecurringChargeRuleSerializer(instance, context=self.context).data


class TenantDocumentRecordSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source="tenant_profile.resolved_display_name", read_only=True)
    lease_code = serializers.CharField(source="lease_agreement.lease_code", read_only=True, default="")
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = TenantDocumentRecord
        fields = [
            "id",
            "tenant_profile",
            "tenant_name",
            "lease_agreement",
            "lease_code",
            "inspection",
            "invoice",
            "payment",
            "title",
            "category",
            "category_display",
            "status",
            "status_display",
            "reference_number",
            "file_reference",
            "issue_date",
            "expiry_date",
            "is_signed",
            "signed_at",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class TenantDocumentRecordWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantDocumentRecord
        fields = [
            "tenant_profile",
            "lease_agreement",
            "inspection",
            "invoice",
            "payment",
            "title",
            "category",
            "status",
            "reference_number",
            "file_reference",
            "issue_date",
            "expiry_date",
            "is_signed",
            "signed_at",
            "notes",
        ]
        extra_kwargs = {
            "lease_agreement": {"required": False, "allow_null": True},
            "inspection": {"required": False, "allow_null": True},
            "invoice": {"required": False, "allow_null": True},
            "payment": {"required": False, "allow_null": True},
            "issue_date": {"required": False, "allow_null": True},
            "expiry_date": {"required": False, "allow_null": True},
            "signed_at": {"required": False, "allow_null": True},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        org = _resolve_request_org(self.context.get("request"))
        if org is None:
            return
        _set_org_queryset(self.fields["tenant_profile"], TenantProfile, org, order_by=["display_name", "id"])
        _set_org_queryset(self.fields["lease_agreement"], LeaseAgreement, org, order_by=["end_date", "tenant_profile__display_name"])
        _set_org_queryset(self.fields["inspection"], TenantInspection, org, order_by=["-scheduled_date"])
        self.fields["invoice"].queryset = Invoice.objects.filter(organization=org).order_by("-issue_date", "-id")
        self.fields["payment"].queryset = InvoicePayment.objects.filter(invoice__organization=org).select_related("invoice").order_by("-payment_date", "-id")

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if attrs.get("payment") and not attrs.get("invoice"):
            attrs["invoice"] = attrs["payment"].invoice
        tenant_profile = attrs.get("tenant_profile", getattr(self.instance, "tenant_profile", None))
        lease_agreement = attrs.get("lease_agreement", getattr(self.instance, "lease_agreement", None))
        if lease_agreement and tenant_profile and lease_agreement.tenant_profile_id != tenant_profile.id:
            raise serializers.ValidationError({"lease_agreement": ["The selected lease does not belong to this tenant."]})
        if attrs.get("expiry_date") and attrs.get("issue_date") and attrs["expiry_date"] < attrs["issue_date"]:
            raise serializers.ValidationError({"expiry_date": ["Expiry date cannot be before issue date."]})
        return attrs

    def to_representation(self, instance):
        return TenantDocumentRecordSerializer(instance, context=self.context).data


class TenantInspectionSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source="tenant_profile.resolved_display_name", read_only=True)
    lease_code = serializers.CharField(source="lease_agreement.lease_code", read_only=True, default="")
    property_name = serializers.SerializerMethodField()
    unit_label = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    inspection_type_display = serializers.CharField(source="get_inspection_type_display", read_only=True)
    inspector_name = serializers.SerializerMethodField()

    class Meta:
        model = TenantInspection
        fields = [
            "id",
            "tenant_profile",
            "tenant_name",
            "lease_agreement",
            "lease_code",
            "property",
            "property_name",
            "unit",
            "unit_label",
            "facility",
            "facility_space",
            "inspection_type",
            "inspection_type_display",
            "status",
            "status_display",
            "title",
            "scheduled_date",
            "completed_date",
            "inspector",
            "inspector_name",
            "checklist_summary",
            "damage_assessment",
            "security_deposit_deduction",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_property_name(self, obj):
        return _property_name(obj)

    def get_unit_label(self, obj):
        return _unit_label(obj)

    def get_inspector_name(self, obj):
        return _display_name(obj.inspector)


class TenantInspectionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantInspection
        fields = [
            "tenant_profile",
            "lease_agreement",
            "property",
            "unit",
            "facility",
            "facility_space",
            "inspection_type",
            "status",
            "title",
            "scheduled_date",
            "completed_date",
            "inspector",
            "checklist_summary",
            "damage_assessment",
            "security_deposit_deduction",
            "notes",
        ]
        extra_kwargs = {
            "lease_agreement": {"required": False, "allow_null": True},
            "property": {"required": False, "allow_null": True},
            "unit": {"required": False, "allow_null": True},
            "facility": {"required": False, "allow_null": True},
            "facility_space": {"required": False, "allow_null": True},
            "completed_date": {"required": False, "allow_null": True},
            "inspector": {"required": False, "allow_null": True},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        org = _resolve_request_org(self.context.get("request"))
        if org is None:
            return
        _set_org_queryset(self.fields["tenant_profile"], TenantProfile, org, order_by=["display_name", "id"])
        _set_org_queryset(self.fields["lease_agreement"], LeaseAgreement, org, order_by=["end_date", "tenant_profile__display_name"])
        _set_org_queryset(self.fields["property"], Property, org, order_by=["name"])
        _set_org_queryset(self.fields["unit"], Unit, org, order_by=["property__name", "unit_number"], select_related=["property"])
        _set_org_queryset(self.fields["facility"], Facility, org, order_by=["property__name", "facility_code"], select_related=["property"])
        _set_org_queryset(
            self.fields["facility_space"],
            FacilityUnitSpace,
            org,
            order_by=["facility__property__name", "unit__unit_number"],
            select_related=["facility", "facility__property", "unit"],
        )
        self.fields["inspector"].queryset = User.objects.filter(profile__organization=org, is_active=True).order_by("email")

    def validate(self, attrs):
        attrs = super().validate(attrs)
        tenant_profile = attrs.get("tenant_profile", getattr(self.instance, "tenant_profile", None))
        lease_agreement = attrs.get("lease_agreement", getattr(self.instance, "lease_agreement", None))
        context = _derive_context(
            tenant_profile=tenant_profile,
            lease_agreement=lease_agreement,
            property_record=attrs.get("property", getattr(self.instance, "property", None)),
            unit=attrs.get("unit", getattr(self.instance, "unit", None)),
            facility=attrs.get("facility", getattr(self.instance, "facility", None)),
            facility_space=attrs.get("facility_space", getattr(self.instance, "facility_space", None)),
        )
        attrs["property"] = context["property"]
        attrs["unit"] = context["unit"]
        attrs["facility"] = context["facility"]
        attrs["facility_space"] = context["facility_space"]
        if not (attrs.get("title") or "").strip() and tenant_profile:
            attrs["title"] = f"{tenant_profile.resolved_display_name} inspection"
        return attrs

    def to_representation(self, instance):
        return TenantInspectionSerializer(instance, context=self.context).data


class TenantComplaintSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source="tenant_profile.resolved_display_name", read_only=True)
    property_name = serializers.SerializerMethodField()
    unit_label = serializers.SerializerMethodField()
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    priority_display = serializers.CharField(source="get_priority_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    assigned_to_name = serializers.SerializerMethodField()
    service_request_title = serializers.CharField(source="service_request.title", read_only=True, default="")

    class Meta:
        model = TenantComplaint
        fields = [
            "id",
            "tenant_profile",
            "tenant_name",
            "property",
            "property_name",
            "unit",
            "unit_label",
            "facility",
            "facility_space",
            "service_request",
            "service_request_title",
            "assigned_to",
            "assigned_to_name",
            "category",
            "category_display",
            "priority",
            "priority_display",
            "status",
            "status_display",
            "subject",
            "description",
            "sla_target_hours",
            "sla_due_at",
            "escalated_at",
            "resolved_at",
            "feedback_rating",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_property_name(self, obj):
        return _property_name(obj)

    def get_unit_label(self, obj):
        return _unit_label(obj)

    def get_assigned_to_name(self, obj):
        return _display_name(obj.assigned_to)


class TenantComplaintWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantComplaint
        fields = [
            "tenant_profile",
            "property",
            "unit",
            "facility",
            "facility_space",
            "service_request",
            "assigned_to",
            "category",
            "priority",
            "status",
            "subject",
            "description",
            "sla_target_hours",
            "sla_due_at",
            "resolved_at",
            "feedback_rating",
            "notes",
        ]
        extra_kwargs = {
            "property": {"required": False, "allow_null": True},
            "unit": {"required": False, "allow_null": True},
            "facility": {"required": False, "allow_null": True},
            "facility_space": {"required": False, "allow_null": True},
            "service_request": {"required": False, "allow_null": True},
            "assigned_to": {"required": False, "allow_null": True},
            "sla_due_at": {"required": False, "allow_null": True},
            "resolved_at": {"required": False, "allow_null": True},
            "feedback_rating": {"required": False, "allow_null": True},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        org = _resolve_request_org(self.context.get("request"))
        if org is None:
            return
        _set_org_queryset(self.fields["tenant_profile"], TenantProfile, org, order_by=["display_name", "id"])
        _set_org_queryset(self.fields["property"], Property, org, order_by=["name"])
        _set_org_queryset(self.fields["unit"], Unit, org, order_by=["property__name", "unit_number"], select_related=["property"])
        _set_org_queryset(self.fields["facility"], Facility, org, order_by=["property__name", "facility_code"], select_related=["property"])
        _set_org_queryset(
            self.fields["facility_space"],
            FacilityUnitSpace,
            org,
            order_by=["facility__property__name", "unit__unit_number"],
            select_related=["facility", "facility__property", "unit"],
        )
        self.fields["service_request"].queryset = ServiceRequest.objects.filter(organization=org).order_by("-created_at")
        self.fields["assigned_to"].queryset = User.objects.filter(profile__organization=org, is_active=True).order_by("email")

    def validate(self, attrs):
        attrs = super().validate(attrs)
        tenant_profile = attrs.get("tenant_profile", getattr(self.instance, "tenant_profile", None))
        context = _derive_context(
            tenant_profile=tenant_profile,
            property_record=attrs.get("property", getattr(self.instance, "property", None)),
            unit=attrs.get("unit", getattr(self.instance, "unit", None)),
            facility=attrs.get("facility", getattr(self.instance, "facility", None)),
            facility_space=attrs.get("facility_space", getattr(self.instance, "facility_space", None)),
        )
        attrs["property"] = context["property"]
        attrs["unit"] = context["unit"]
        attrs["facility"] = context["facility"]
        attrs["facility_space"] = context["facility_space"]

        priority = attrs.get("priority", getattr(self.instance, "priority", TenantComplaint.Priority.MEDIUM))
        sla_target_hours = attrs.get("sla_target_hours", getattr(self.instance, "sla_target_hours", 24))
        if attrs.get("sla_due_at") is None and attrs.get("status", getattr(self.instance, "status", TenantComplaint.Status.OPEN)) in {
            TenantComplaint.Status.OPEN,
            TenantComplaint.Status.ACKNOWLEDGED,
        }:
            default_hours = {
                TenantComplaint.Priority.LOW: 72,
                TenantComplaint.Priority.MEDIUM: 24,
                TenantComplaint.Priority.HIGH: 8,
                TenantComplaint.Priority.CRITICAL: 4,
            }.get(priority, sla_target_hours or 24)
            attrs["sla_target_hours"] = default_hours
            attrs["sla_due_at"] = timezone.now() + timedelta(hours=default_hours)

        feedback_rating = attrs.get("feedback_rating")
        if feedback_rating is not None and feedback_rating not in {1, 2, 3, 4, 5}:
            raise serializers.ValidationError({"feedback_rating": ["Feedback rating must be between 1 and 5."]})
        return attrs

    def to_representation(self, instance):
        return TenantComplaintSerializer(instance, context=self.context).data


class TenantBroadcastSerializer(serializers.ModelSerializer):
    audience_type_display = serializers.CharField(source="get_audience_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    created_by_name = serializers.SerializerMethodField()
    property_name = serializers.CharField(source="property.name", read_only=True, default="")
    facility_code = serializers.CharField(source="facility.facility_code", read_only=True, default="")

    class Meta:
        model = TenantBroadcast
        fields = [
            "id",
            "created_by",
            "created_by_name",
            "property",
            "property_name",
            "facility",
            "facility_code",
            "audience_type",
            "audience_type_display",
            "tenant_type_filter",
            "status",
            "status_display",
            "subject",
            "message",
            "send_email",
            "send_whatsapp",
            "send_in_app",
            "recipient_count",
            "delivered_count",
            "sent_at",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "recipient_count", "delivered_count", "sent_at", "created_at", "updated_at"]

    def get_created_by_name(self, obj):
        return _display_name(obj.created_by)


class TenantBroadcastWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantBroadcast
        fields = [
            "property",
            "facility",
            "audience_type",
            "tenant_type_filter",
            "status",
            "subject",
            "message",
            "send_email",
            "send_whatsapp",
            "send_in_app",
            "notes",
        ]
        extra_kwargs = {
            "property": {"required": False, "allow_null": True},
            "facility": {"required": False, "allow_null": True},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        org = _resolve_request_org(self.context.get("request"))
        if org is None:
            return
        _set_org_queryset(self.fields["property"], Property, org, order_by=["name"])
        _set_org_queryset(self.fields["facility"], Facility, org, order_by=["property__name", "facility_code"], select_related=["property"])

    def validate(self, attrs):
        attrs = super().validate(attrs)
        audience_type = attrs.get("audience_type", getattr(self.instance, "audience_type", TenantBroadcast.AudienceType.ALL_TENANTS))
        property_record = attrs.get("property", getattr(self.instance, "property", None))
        facility = attrs.get("facility", getattr(self.instance, "facility", None))
        if audience_type == TenantBroadcast.AudienceType.PROPERTY and property_record is None:
            raise serializers.ValidationError({"property": ["Select a property for property-scoped broadcasts."]})
        if audience_type == TenantBroadcast.AudienceType.FACILITY and facility is None:
            raise serializers.ValidationError({"facility": ["Select a facility for facility-scoped broadcasts."]})
        if audience_type == TenantBroadcast.AudienceType.TENANT_TYPE and not attrs.get("tenant_type_filter", getattr(self.instance, "tenant_type_filter", "")):
            raise serializers.ValidationError({"tenant_type_filter": ["Choose a tenant type audience filter."]})
        return attrs

    def to_representation(self, instance):
        return TenantBroadcastSerializer(instance, context=self.context).data
