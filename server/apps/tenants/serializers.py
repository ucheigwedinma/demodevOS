from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.crm.models import ContactAccount
from apps.facility_management.models import Facility, FacilityUnitSpace
from apps.finance.models import Customer
from apps.finance.serializers import InvoiceLineItemSerializer, InvoicePaymentSerializer
from apps.properties.models import Property, Unit

from .lease_context import ensure_tenant_profile_lease_context, seed_lease_payload_for_profile
from .lease_context import profile_facility as _profile_facility
from .lease_context import profile_property as _profile_property
from .lease_context import profile_unit as _profile_unit
from .models import (
    TenantCommunicationLog,
    TenantIdentityDocument,
    TenantIncidentRecord,
    TenantInventoryItem,
    TenantProfile,
    TenantRelationshipContact,
)

User = get_user_model()
ACTIVE_OCCUPANCY_STATUSES = {
    TenantProfile.Status.PENDING_MOVE_IN,
    TenantProfile.Status.ACTIVE,
}
ZERO_DECIMAL = Decimal("0.00")


def _resolve_request_org(request):
    org = getattr(request, "organization", None)
    if org is not None:
        return org
    profile = getattr(getattr(request, "user", None), "profile", None)
    return getattr(profile, "organization", None)


def _property_location(property_record):
    address = (getattr(property_record, "address", "") or "").strip()
    if not address:
        return ""
    parts = [part.strip() for part in address.split(",") if part.strip()]
    return parts[-1] if parts else address


def _primary_user_name(user):
    if not user:
        return ""
    full_name = user.get_full_name().strip()
    return full_name or user.email or user.username


def _profile_contact_email(obj):
    if obj.primary_user_id and obj.primary_user and obj.primary_user.email:
        return obj.primary_user.email.strip()
    if obj.customer_id and obj.customer and obj.customer.email:
        return obj.customer.email.strip()
    if obj.contact_account_id and obj.contact_account and obj.contact_account.email:
        return obj.contact_account.email.strip()
    return ""


def _profile_contact_phone(obj):
    if obj.customer_id and obj.customer and obj.customer.phone:
        return obj.customer.phone.strip()
    if obj.contact_account_id and obj.contact_account:
        if obj.contact_account.phone:
            return obj.contact_account.phone.strip()
        if obj.contact_account.secondary_phone:
            return obj.contact_account.secondary_phone.strip()
    return ""


def _derived_display_name(*, customer=None, contact_account=None, primary_user=None, fallback=""):
    fallback = (fallback or "").strip()
    if fallback:
        return fallback
    if customer:
        return customer.name
    if contact_account:
        return contact_account.display_name
    return _primary_user_name(primary_user)


def _sync_unit_status(unit):
    if unit is None:
        return
    active_exists = TenantProfile.objects.filter(
        organization=unit.organization,
        unit=unit,
        status=TenantProfile.Status.ACTIVE,
    ).exists()
    pending_exists = TenantProfile.objects.filter(
        organization=unit.organization,
        unit=unit,
        status=TenantProfile.Status.PENDING_MOVE_IN,
    ).exists()

    target_status = Unit.UnitStatus.AVAILABLE
    if active_exists:
        target_status = Unit.UnitStatus.LEASED
    elif pending_exists:
        target_status = Unit.UnitStatus.RESERVED

    if unit.status != target_status:
        unit.status = target_status
        unit.save(update_fields=["status", "updated_at"])


class TenantProfileListSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True, default="")
    contact_account_name = serializers.CharField(source="contact_account.display_name", read_only=True, default="")
    property_name = serializers.SerializerMethodField()
    property_location = serializers.SerializerMethodField()
    unit_number = serializers.SerializerMethodField()
    facility_code = serializers.SerializerMethodField()
    space_label = serializers.SerializerMethodField()
    tenant_type_display = serializers.CharField(source="get_tenant_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    resolved_display_name = serializers.CharField(read_only=True)
    primary_user_name = serializers.SerializerMethodField()
    contact_email = serializers.SerializerMethodField()
    contact_phone = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()
    payment_status_display = serializers.SerializerMethodField()

    class Meta:
        model = TenantProfile
        fields = [
            "id",
            "customer",
            "customer_name",
            "contact_account",
            "contact_account_name",
            "primary_user",
            "property",
            "property_name",
            "unit",
            "unit_number",
            "facility",
            "facility_code",
            "facility_space",
            "space_label",
            "tenant_type",
            "tenant_type_display",
            "status",
            "status_display",
            "display_name",
            "resolved_display_name",
            "primary_user_name",
            "contact_email",
            "contact_phone",
            "payment_status",
            "payment_status_display",
            "property_location",
            "lease_start_date",
            "lease_end_date",
            "move_in_date",
            "move_out_date",
            "occupant_count",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_property_name(self, obj):
        property_record = _profile_property(obj)
        return property_record.name if property_record else ""

    def get_property_location(self, obj):
        return _property_location(_profile_property(obj))

    def get_unit_number(self, obj):
        unit = _profile_unit(obj)
        return unit.unit_number if unit else ""

    def get_facility_code(self, obj):
        facility = _profile_facility(obj)
        return facility.facility_code if facility else ""

    def get_space_label(self, obj):
        if obj.facility_space_id and obj.facility_space:
            return obj.facility_space.space_label or obj.facility_space.unit.unit_number
        return ""

    def get_primary_user_name(self, obj):
        return _primary_user_name(obj.primary_user if obj.primary_user_id else None)

    def get_contact_email(self, obj):
        return _profile_contact_email(obj)

    def get_contact_phone(self, obj):
        return _profile_contact_phone(obj)

    def _payment_snapshot(self, obj):
        snapshot_by_customer = self.context.get("tenant_invoice_snapshot_by_customer") or {}
        if not obj.customer_id:
            return None
        return snapshot_by_customer.get(obj.customer_id)

    def get_payment_status(self, obj):
        snapshot = self._payment_snapshot(obj)
        if snapshot is None:
            return "unknown"
        balance_due = snapshot.get("balance_due", ZERO_DECIMAL) or ZERO_DECIMAL
        return "debt_free" if balance_due <= ZERO_DECIMAL else "delinquent"

    def get_payment_status_display(self, obj):
        status = self.get_payment_status(obj)
        if status == "debt_free":
            return "Debt-Free"
        if status == "delinquent":
            return "Delinquent"
        return "Payment Unlinked"


class TenantProfileDetailSerializer(TenantProfileListSerializer):
    pass


class TenantIdentityDocumentSerializer(serializers.ModelSerializer):
    document_type_display = serializers.CharField(source="get_document_type_display", read_only=True)

    class Meta:
        model = TenantIdentityDocument
        fields = [
            "id",
            "document_type",
            "document_type_display",
            "document_number",
            "holder_name",
            "issuing_country",
            "issue_date",
            "expiry_date",
            "scan_on_file",
            "scan_reference",
            "is_verified",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class TenantIdentityDocumentWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantIdentityDocument
        fields = [
            "document_type",
            "document_number",
            "holder_name",
            "issuing_country",
            "issue_date",
            "expiry_date",
            "scan_on_file",
            "scan_reference",
            "is_verified",
            "notes",
        ]


class TenantRelationshipContactSerializer(serializers.ModelSerializer):
    contact_role_display = serializers.CharField(source="get_contact_role_display", read_only=True)

    class Meta:
        model = TenantRelationshipContact
        fields = [
            "id",
            "contact_role",
            "contact_role_display",
            "full_name",
            "relationship",
            "phone",
            "email",
            "address",
            "is_primary",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class TenantRelationshipContactWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantRelationshipContact
        fields = [
            "contact_role",
            "full_name",
            "relationship",
            "phone",
            "email",
            "address",
            "is_primary",
            "notes",
        ]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if not (attrs.get("phone") or attrs.get("email")):
            raise serializers.ValidationError({"phone": ["Provide at least a phone or email for this contact."]})
        return attrs


class TenantInventoryItemSerializer(serializers.ModelSerializer):
    condition_display = serializers.CharField(source="get_condition_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = TenantInventoryItem
        fields = [
            "id",
            "item_name",
            "quantity",
            "condition",
            "condition_display",
            "status",
            "status_display",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class TenantInventoryItemWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantInventoryItem
        fields = [
            "item_name",
            "quantity",
            "condition",
            "status",
            "notes",
        ]


class TenantIncidentRecordSerializer(serializers.ModelSerializer):
    incident_type_display = serializers.CharField(source="get_incident_type_display", read_only=True)
    severity_display = serializers.CharField(source="get_severity_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    work_order_title = serializers.CharField(source="work_order.title", read_only=True, default="")

    class Meta:
        model = TenantIncidentRecord
        fields = [
            "id",
            "incident_type",
            "incident_type_display",
            "severity",
            "severity_display",
            "status",
            "status_display",
            "title",
            "description",
            "occurred_at",
            "resolved_at",
            "notes",
            "work_order",
            "work_order_title",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class TenantIncidentRecordWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantIncidentRecord
        fields = [
            "incident_type",
            "severity",
            "status",
            "title",
            "description",
            "occurred_at",
            "resolved_at",
            "notes",
            "work_order",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        org = _resolve_request_org(request)
        if org is not None:
            self.fields["work_order"].queryset = self.fields["work_order"].queryset.filter(organization=org)


class TenantLedgerLineItemSerializer(InvoiceLineItemSerializer):
    class Meta(InvoiceLineItemSerializer.Meta):
        fields = [
            "id",
            "description",
            "quantity",
            "unit_price",
            "amount",
            "sort_order",
        ]
        read_only_fields = fields


class TenantLedgerPaymentSerializer(InvoicePaymentSerializer):
    class Meta(InvoicePaymentSerializer.Meta):
        fields = [
            "id",
            "amount",
            "payment_date",
            "payment_method",
            "reference_number",
            "notes",
            "created_at",
        ]
        read_only_fields = fields


class TenantProfileWriteSerializer(serializers.ModelSerializer):
    occupant_count = serializers.IntegerField(min_value=1, required=False)

    class Meta:
        model = TenantProfile
        fields = [
            "id",
            "customer",
            "contact_account",
            "primary_user",
            "property",
            "unit",
            "facility",
            "facility_space",
            "tenant_type",
            "status",
            "display_name",
            "lease_start_date",
            "lease_end_date",
            "move_in_date",
            "move_out_date",
            "occupant_count",
            "notes",
        ]
        read_only_fields = ["id"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        org = _resolve_request_org(request)
        if org is None:
            return

        self.fields["customer"].queryset = Customer.objects.filter(organization=org).order_by("name")
        self.fields["contact_account"].queryset = ContactAccount.objects.filter(organization=org).order_by("-created_at")
        self.fields["primary_user"].queryset = User.objects.filter(profile__organization=org).order_by("email")
        self.fields["property"].queryset = Property.objects.filter(organization=org).order_by("name")
        self.fields["unit"].queryset = Unit.objects.filter(organization=org).select_related("property").order_by("property__name", "unit_number")
        self.fields["facility"].queryset = Facility.objects.filter(organization=org).select_related("property").order_by("property__name")
        self.fields["facility_space"].queryset = (
            FacilityUnitSpace.objects.filter(organization=org)
            .select_related("unit", "facility", "facility__property")
            .order_by("facility__property__name", "unit__unit_number")
        )

    def validate(self, attrs):
        request = self.context.get("request")
        org = _resolve_request_org(request)
        instance = self.instance
        today = timezone.localdate()

        selected_unit = attrs.get("unit")
        selected_facility = attrs.get("facility")
        customer = attrs.get("customer", getattr(instance, "customer", None))
        contact_account = attrs.get("contact_account", getattr(instance, "contact_account", None))
        primary_user = attrs.get("primary_user", getattr(instance, "primary_user", None))
        property_record = attrs.get("property", getattr(instance, "property", None))
        unit = attrs.get("unit", getattr(instance, "unit", None))
        facility = attrs.get("facility", getattr(instance, "facility", None))
        facility_space = attrs.get("facility_space", getattr(instance, "facility_space", None))
        status_value = attrs.get("status", getattr(instance, "status", TenantProfile.Status.PENDING_MOVE_IN))
        lease_start_date = attrs.get("lease_start_date", getattr(instance, "lease_start_date", None))
        lease_end_date = attrs.get("lease_end_date", getattr(instance, "lease_end_date", None))
        move_in_date = attrs.get("move_in_date", getattr(instance, "move_in_date", None))
        move_out_date = attrs.get("move_out_date", getattr(instance, "move_out_date", None))
        display_name = (attrs.get("display_name", getattr(instance, "display_name", "")) or "").strip()

        if not customer and contact_account and contact_account.finance_customer_id:
            customer = contact_account.finance_customer
            attrs["customer"] = customer

        if facility_space:
            if selected_unit is not None and unit and facility_space.unit_id != unit.id:
                raise serializers.ValidationError({"facility_space": ["Selected space does not belong to the chosen unit."]})
            if selected_facility is not None and facility and facility_space.facility_id != facility.id:
                raise serializers.ValidationError({"facility_space": ["Selected space does not belong to the chosen facility."]})
            unit = facility_space.unit
            facility = facility_space.facility
            property_record = facility_space.facility.property
            attrs["unit"] = unit
            attrs["facility"] = facility
            attrs["property"] = property_record
        elif unit:
            if property_record and unit.property_id != property_record.id:
                raise serializers.ValidationError({"unit": ["Selected unit does not belong to the chosen property."]})
            property_record = unit.property
            attrs["property"] = property_record
            linked_space = getattr(unit, "facility_space", None)
            if linked_space and linked_space.organization_id == getattr(org, "id", None):
                facility_space = linked_space
                facility = linked_space.facility
                attrs["facility_space"] = linked_space
                attrs["facility"] = facility
        elif facility:
            if property_record and facility.property_id != property_record.id:
                raise serializers.ValidationError({"facility": ["Selected facility does not belong to the chosen property."]})
            property_record = facility.property
            attrs["property"] = property_record

        if facility and property_record and facility.property_id != property_record.id:
            raise serializers.ValidationError({"facility": ["Selected facility does not match the property assignment."]})

        if lease_start_date and lease_end_date and lease_end_date <= lease_start_date:
            raise serializers.ValidationError({"lease_end_date": ["Lease end date must be after the lease start date."]})

        if status_value == TenantProfile.Status.PENDING_MOVE_IN and move_in_date and move_in_date <= today:
            status_value = TenantProfile.Status.ACTIVE
            attrs["status"] = status_value
        if status_value == TenantProfile.Status.ACTIVE and move_out_date and move_out_date < today:
            status_value = TenantProfile.Status.MOVED_OUT
            attrs["status"] = status_value

        if not display_name:
            display_name = _derived_display_name(
                customer=customer,
                contact_account=contact_account,
                primary_user=primary_user,
            )
            if display_name:
                attrs["display_name"] = display_name

        if not display_name and not customer and not contact_account and not primary_user:
            raise serializers.ValidationError(
                {"display_name": ["Provide a display name or link a customer, contact account, or primary user."]}
            )

        if status_value in ACTIVE_OCCUPANCY_STATUSES:
            conflict_qs = TenantProfile.objects.filter(
                organization=org,
                status__in=ACTIVE_OCCUPANCY_STATUSES,
            )
            if instance is not None:
                conflict_qs = conflict_qs.exclude(pk=instance.pk)
            if unit and conflict_qs.filter(unit=unit).exists():
                raise serializers.ValidationError({"unit": ["Another active tenant profile already uses this unit."]})
            if facility_space and conflict_qs.filter(facility_space=facility_space).exists():
                raise serializers.ValidationError({"facility_space": ["Another active tenant profile already uses this space."]})

        candidate = TenantProfile(
            organization=org,
            customer=customer,
            contact_account=contact_account,
            primary_user=primary_user,
            property=property_record,
            unit=unit,
            facility=facility,
            facility_space=facility_space,
            tenant_type=attrs.get("tenant_type", getattr(instance, "tenant_type", TenantProfile.TenantType.CORPORATE)),
            status=status_value,
            display_name=display_name,
            lease_start_date=lease_start_date,
            lease_end_date=lease_end_date,
            move_in_date=move_in_date,
            move_out_date=move_out_date,
            occupant_count=attrs.get("occupant_count", getattr(instance, "occupant_count", 1) or 1),
        )
        if instance is None or not instance.lease_agreements.exists():
            _, lease_context_errors = seed_lease_payload_for_profile(candidate)
            if lease_context_errors:
                raise serializers.ValidationError(lease_context_errors)

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        profile = super().create(validated_data)
        _sync_unit_status(profile.unit)
        lease, lease_created, lease_updated = ensure_tenant_profile_lease_context(profile)
        profile._lease_context_ready = lease is not None
        profile._lease_context_created = lease_created
        profile._lease_context_updated = lease_updated
        return profile

    @transaction.atomic
    def update(self, instance, validated_data):
        previous_unit = instance.unit
        profile = super().update(instance, validated_data)
        previous_unit_id = getattr(previous_unit, "id", None)
        if previous_unit and previous_unit_id:
            if profile.unit_id != previous_unit_id:
                _sync_unit_status(previous_unit)
        _sync_unit_status(profile.unit)
        lease, lease_created, lease_updated = ensure_tenant_profile_lease_context(profile)
        profile._lease_context_ready = lease is not None
        profile._lease_context_created = lease_created
        profile._lease_context_updated = lease_updated
        return profile

    def to_representation(self, instance):
        return TenantProfileDetailSerializer(instance, context=self.context).data


class TenantCommunicationLogSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    interaction_type_display = serializers.CharField(source="get_interaction_type_display", read_only=True)
    channel_display = serializers.CharField(source="get_channel_display", read_only=True)
    direction_display = serializers.CharField(source="get_direction_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = TenantCommunicationLog
        fields = [
            "id",
            "interaction_type",
            "interaction_type_display",
            "channel",
            "channel_display",
            "direction",
            "direction_display",
            "status",
            "status_display",
            "subject",
            "message",
            "metadata",
            "happened_at",
            "author_name",
        ]
        read_only_fields = fields

    def get_author_name(self, obj):
        if not obj.author_id or not obj.author:
            return ""
        full_name = obj.author.get_full_name().strip()
        return full_name or obj.author.email or obj.author.username
