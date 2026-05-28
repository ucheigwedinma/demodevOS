from __future__ import annotations

from django.db.models import Q, Sum
from rest_framework import serializers

from apps.facility_management.models import FacilitySpaceProfile, SpaceAllocation, SpaceBooking
from apps.tenants.models import TenantProfile

from .space_occupancy_workflows import (
    ACTIVE_ALLOCATION_STATUSES,
    OPEN_BOOKING_STATUSES,
    ensure_space_profile_defaults,
    occupant_label_for,
    space_label_for,
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


class FacilitySpaceProfileListSerializer(serializers.ModelSerializer):
    facility = serializers.IntegerField(source="facility_space.facility_id", read_only=True)
    facility_code = serializers.CharField(source="facility_space.facility.facility_code", read_only=True)
    zone_code = serializers.CharField(source="facility_space.zone.zone_code", read_only=True)
    zone_name = serializers.CharField(source="facility_space.zone.name", read_only=True)
    unit_number = serializers.CharField(source="facility_space.unit.unit_number", read_only=True)
    space_label = serializers.SerializerMethodField()
    space_type_display = serializers.CharField(source="get_space_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    active_allocation_count = serializers.SerializerMethodField()
    active_booking_count = serializers.SerializerMethodField()
    current_occupancy = serializers.SerializerMethodField()
    vacancy_state = serializers.SerializerMethodField()

    class Meta:
        model = FacilitySpaceProfile
        fields = [
            "id",
            "facility_space",
            "facility",
            "facility_code",
            "zone_code",
            "zone_name",
            "unit_number",
            "space_label",
            "space_type",
            "space_type_display",
            "capacity",
            "is_bookable",
            "booking_requires_approval",
            "requires_check_in",
            "default_booking_duration_minutes",
            "status",
            "status_display",
            "active_allocation_count",
            "active_booking_count",
            "current_occupancy",
            "vacancy_state",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_space_label(self, obj):
        return space_label_for(obj.facility_space)

    def get_active_allocation_count(self, obj):
        return obj.facility_space.space_allocations.filter(status__in=ACTIVE_ALLOCATION_STATUSES).count()

    def get_active_booking_count(self, obj):
        return obj.facility_space.space_bookings.filter(status__in=OPEN_BOOKING_STATUSES).count()

    def get_current_occupancy(self, obj):
        return (
            obj.facility_space.space_allocations.filter(status__in=ACTIVE_ALLOCATION_STATUSES)
            .aggregate(total=Sum("occupant_count"))
            .get("total")
            or 0
        )

    def get_vacancy_state(self, obj):
        current_occupancy = self.get_current_occupancy(obj)
        if obj.status != FacilitySpaceProfile.Status.ACTIVE:
            return "offline"
        if current_occupancy >= obj.capacity:
            return "full"
        if current_occupancy > 0:
            return "partially_occupied"
        return "vacant"


class FacilitySpaceProfileDetailSerializer(FacilitySpaceProfileListSerializer):
    class Meta(FacilitySpaceProfileListSerializer.Meta):
        fields = FacilitySpaceProfileListSerializer.Meta.fields


class FacilitySpaceProfileWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = FacilitySpaceProfile
        fields = [
            "id",
            "facility_space",
            "space_type",
            "capacity",
            "is_bookable",
            "booking_requires_approval",
            "requires_check_in",
            "default_booking_duration_minutes",
            "status",
            "notes",
        ]
        read_only_fields = ["id"]

    def validate_facility_space(self, value):
        org = _resolve_request_org(self.context.get("request"))
        if org and value.organization_id != org.id:
            raise serializers.ValidationError("Selected space is not in your organization.")
        return value

    def validate_capacity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Capacity must be at least 1.")
        return value

    def validate_default_booking_duration_minutes(self, value):
        if value <= 0:
            raise serializers.ValidationError("Default booking duration must be greater than zero.")
        return value

    def create(self, validated_data):
        facility_space = validated_data["facility_space"]
        profile, _created = FacilitySpaceProfile.objects.get_or_create(
            facility_space=facility_space,
            defaults={"organization": facility_space.organization},
        )
        for field_name, value in validated_data.items():
            setattr(profile, field_name, value)
        profile.organization = facility_space.organization
        profile.save()
        return profile


class FacilitySpaceAllocationListSerializer(serializers.ModelSerializer):
    facility = serializers.IntegerField(source="facility_space.facility_id", read_only=True)
    facility_code = serializers.CharField(source="facility_space.facility.facility_code", read_only=True)
    zone_code = serializers.CharField(source="facility_space.zone.zone_code", read_only=True)
    unit_number = serializers.CharField(source="facility_space.unit.unit_number", read_only=True)
    space_label = serializers.SerializerMethodField()
    allocation_type_display = serializers.CharField(source="get_allocation_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    occupant_label = serializers.SerializerMethodField()
    employee_name = serializers.SerializerMethodField()
    department_name = serializers.CharField(source="department.name", read_only=True, default="")
    tenant_name = serializers.SerializerMethodField()

    class Meta:
        model = SpaceAllocation
        fields = [
            "id",
            "facility_space",
            "facility",
            "facility_code",
            "zone_code",
            "unit_number",
            "space_label",
            "allocation_type",
            "allocation_type_display",
            "status",
            "status_display",
            "employee",
            "employee_name",
            "department",
            "department_name",
            "tenant_customer",
            "tenant_contact_account",
            "tenant_name",
            "occupant_label",
            "occupant_count",
            "start_date",
            "end_date",
            "allocated_by",
            "released_at",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_space_label(self, obj):
        return space_label_for(obj.facility_space)

    def get_employee_name(self, obj):
        return _user_display(obj.employee)

    def get_tenant_name(self, obj):
        if obj.tenant_customer_id:
            return obj.tenant_customer.name
        if obj.tenant_contact_account_id:
            return obj.tenant_contact_account.display_name
        return ""

    def get_occupant_label(self, obj):
        return occupant_label_for(obj)


class FacilitySpaceAllocationDetailSerializer(FacilitySpaceAllocationListSerializer):
    linked_tenant_profiles = serializers.SerializerMethodField()

    class Meta(FacilitySpaceAllocationListSerializer.Meta):
        fields = FacilitySpaceAllocationListSerializer.Meta.fields + [
            "linked_tenant_profiles",
        ]

    def get_linked_tenant_profiles(self, obj):
        if obj.allocation_type != SpaceAllocation.AllocationType.TENANT:
            return []
        queryset = TenantProfile.objects.filter(
            organization=obj.organization,
            facility_space=obj.facility_space,
        )
        if obj.tenant_customer_id:
            queryset = queryset.filter(customer_id=obj.tenant_customer_id)
        elif obj.tenant_contact_account_id:
            queryset = queryset.filter(contact_account_id=obj.tenant_contact_account_id)
        profiles = queryset.order_by("-updated_at", "-id")[:5]
        return [
            {
                "id": profile.id,
                "display_name": profile.resolved_display_name,
                "status": profile.status,
            }
            for profile in profiles
        ]


class FacilitySpaceAllocationWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpaceAllocation
        fields = [
            "id",
            "facility_space",
            "allocation_type",
            "employee",
            "department",
            "tenant_customer",
            "tenant_contact_account",
            "occupant_count",
            "start_date",
            "end_date",
            "status",
            "notes",
        ]
        read_only_fields = ["id"]
        extra_kwargs = {
            "employee": {"required": False, "allow_null": True},
            "department": {"required": False, "allow_null": True},
            "tenant_customer": {"required": False, "allow_null": True},
            "tenant_contact_account": {"required": False, "allow_null": True},
            "end_date": {"required": False, "allow_null": True},
            "status": {"required": False},
            "notes": {"required": False, "allow_blank": True},
        }

    def _org(self):
        return _resolve_request_org(self.context.get("request"))

    def _validate_org_owned(self, value, label: str):
        org = self._org()
        if value is None or org is None:
            return value
        if getattr(value, "organization_id", None) != org.id:
            raise serializers.ValidationError(f"Selected {label} is not in your organization.")
        return value

    def validate_facility_space(self, value):
        return self._validate_org_owned(value, "space")

    def validate_employee(self, value):
        org = self._org()
        if value and org and getattr(value, "profile", None) and value.profile.organization_id != org.id:
            raise serializers.ValidationError("Employee must belong to your organization.")
        return value

    def validate_department(self, value):
        org = self._org()
        if value and org and value.division.organization_id != org.id:
            raise serializers.ValidationError("Department must belong to your organization.")
        return value

    def validate_tenant_customer(self, value):
        return self._validate_org_owned(value, "customer")

    def validate_tenant_contact_account(self, value):
        return self._validate_org_owned(value, "contact account")

    def validate_occupant_count(self, value):
        if value <= 0:
            raise serializers.ValidationError("Occupant count must be at least 1.")
        return value

    def validate(self, attrs):
        instance = getattr(self, "instance", None)

        facility_space = attrs.get("facility_space", getattr(instance, "facility_space", None))
        allocation_type = attrs.get("allocation_type", getattr(instance, "allocation_type", None))
        employee = attrs.get("employee", getattr(instance, "employee", None))
        department = attrs.get("department", getattr(instance, "department", None))
        tenant_customer = attrs.get("tenant_customer", getattr(instance, "tenant_customer", None))
        tenant_contact_account = attrs.get("tenant_contact_account", getattr(instance, "tenant_contact_account", None))
        start_date = attrs.get("start_date", getattr(instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(instance, "end_date", None))
        occupant_count = attrs.get("occupant_count", getattr(instance, "occupant_count", 1))

        if facility_space is None:
            raise serializers.ValidationError({"facility_space": "Facility space is required."})

        profile, _changed = ensure_space_profile_defaults(facility_space)
        if profile.status != FacilitySpaceProfile.Status.ACTIVE:
            raise serializers.ValidationError({"facility_space": "Only active spaces can be allocated."})

        if end_date and start_date and end_date < start_date:
            raise serializers.ValidationError({"end_date": "End date cannot be before start date."})

        if allocation_type == SpaceAllocation.AllocationType.EMPLOYEE:
            if employee is None:
                raise serializers.ValidationError({"employee": "Employee is required for employee allocations."})
            attrs["department"] = None
            attrs["tenant_customer"] = None
            attrs["tenant_contact_account"] = None
        elif allocation_type == SpaceAllocation.AllocationType.DEPARTMENT:
            if department is None:
                raise serializers.ValidationError({"department": "Department is required for department allocations."})
            attrs["employee"] = None
            attrs["tenant_customer"] = None
            attrs["tenant_contact_account"] = None
        elif allocation_type == SpaceAllocation.AllocationType.TENANT:
            if tenant_contact_account and not tenant_customer and tenant_contact_account.finance_customer_id:
                attrs["tenant_customer"] = tenant_contact_account.finance_customer
                tenant_customer = tenant_contact_account.finance_customer
            if tenant_customer is None and tenant_contact_account is None:
                raise serializers.ValidationError(
                    {"tenant_customer": "Customer or contact account is required for tenant allocations."}
                )
            if (
                tenant_contact_account
                and tenant_contact_account.finance_customer_id
                and tenant_customer
                and tenant_contact_account.finance_customer_id != tenant_customer.id
            ):
                raise serializers.ValidationError(
                    {"tenant_contact_account": "Selected contact account does not belong to the selected customer."}
                )
            attrs["employee"] = None
            attrs["department"] = None

        overlap_qs = SpaceAllocation.objects.filter(
            facility_space=facility_space,
            start_date__lte=end_date or start_date,
        ).filter(Q(end_date__isnull=True) | Q(end_date__gte=start_date))
        overlap_qs = overlap_qs.exclude(status__in=[SpaceAllocation.Status.ENDED, SpaceAllocation.Status.CANCELLED])
        if instance is not None:
            overlap_qs = overlap_qs.exclude(pk=instance.pk)

        reserved_capacity = overlap_qs.aggregate(total=Sum("occupant_count")).get("total") or 0
        if reserved_capacity + occupant_count > profile.capacity:
            raise serializers.ValidationError(
                {
                    "occupant_count": (
                        f"Allocation exceeds the configured capacity of {profile.capacity} for this space."
                    )
                }
            )

        return attrs


class FacilitySpaceAllocationReleaseSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, default="")


class FacilitySpaceBookingListSerializer(serializers.ModelSerializer):
    facility = serializers.IntegerField(source="facility_space.facility_id", read_only=True)
    facility_code = serializers.CharField(source="facility_space.facility.facility_code", read_only=True)
    zone_code = serializers.CharField(source="facility_space.zone.zone_code", read_only=True)
    unit_number = serializers.CharField(source="facility_space.unit.unit_number", read_only=True)
    space_label = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    requested_by_name = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = SpaceBooking
        fields = [
            "id",
            "facility_space",
            "facility",
            "facility_code",
            "zone_code",
            "unit_number",
            "space_label",
            "title",
            "purpose",
            "requested_by",
            "requested_by_name",
            "approved_by",
            "approved_by_name",
            "start_at",
            "end_at",
            "attendee_count",
            "status",
            "status_display",
            "checked_in_at",
            "checked_out_at",
            "cancelled_at",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_space_label(self, obj):
        return space_label_for(obj.facility_space)

    def get_requested_by_name(self, obj):
        return _user_display(obj.requested_by)

    def get_approved_by_name(self, obj):
        return _user_display(obj.approved_by)


class FacilitySpaceBookingDetailSerializer(FacilitySpaceBookingListSerializer):
    profile = FacilitySpaceProfileListSerializer(source="facility_space.occupancy_profile", read_only=True)

    class Meta(FacilitySpaceBookingListSerializer.Meta):
        fields = FacilitySpaceBookingListSerializer.Meta.fields + [
            "profile",
        ]


class FacilitySpaceBookingWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpaceBooking
        fields = [
            "id",
            "facility_space",
            "title",
            "purpose",
            "requested_by",
            "approved_by",
            "start_at",
            "end_at",
            "attendee_count",
            "status",
            "notes",
        ]
        read_only_fields = ["id"]
        extra_kwargs = {
            "purpose": {"required": False, "allow_blank": True},
            "requested_by": {"required": False, "allow_null": True},
            "approved_by": {"required": False, "allow_null": True},
            "status": {"required": False},
            "notes": {"required": False, "allow_blank": True},
        }

    def _org(self):
        return _resolve_request_org(self.context.get("request"))

    def validate_facility_space(self, value):
        org = self._org()
        if org and value.organization_id != org.id:
            raise serializers.ValidationError("Selected space is not in your organization.")
        return value

    def validate_requested_by(self, value):
        org = self._org()
        if value and org and getattr(value, "profile", None) and value.profile.organization_id != org.id:
            raise serializers.ValidationError("Requester must belong to your organization.")
        return value

    def validate_approved_by(self, value):
        org = self._org()
        if value and org and getattr(value, "profile", None) and value.profile.organization_id != org.id:
            raise serializers.ValidationError("Approver must belong to your organization.")
        return value

    def validate_attendee_count(self, value):
        if value <= 0:
            raise serializers.ValidationError("Attendee count must be at least 1.")
        return value

    def validate(self, attrs):
        instance = getattr(self, "instance", None)
        facility_space = attrs.get("facility_space", getattr(instance, "facility_space", None))
        start_at = attrs.get("start_at", getattr(instance, "start_at", None))
        end_at = attrs.get("end_at", getattr(instance, "end_at", None))
        attendee_count = attrs.get("attendee_count", getattr(instance, "attendee_count", 1))

        if facility_space is None:
            raise serializers.ValidationError({"facility_space": "Facility space is required."})
        if start_at is None or end_at is None:
            raise serializers.ValidationError({"end_at": "Booking start and end times are required."})
        if end_at <= start_at:
            raise serializers.ValidationError({"end_at": "Booking end time must be after the start time."})

        profile, _changed = ensure_space_profile_defaults(facility_space)
        if profile.status != FacilitySpaceProfile.Status.ACTIVE:
            raise serializers.ValidationError({"facility_space": "Only active spaces can be booked."})
        if not profile.is_bookable:
            raise serializers.ValidationError({"facility_space": "This space is not configured for booking."})
        if attendee_count > profile.capacity:
            raise serializers.ValidationError(
                {"attendee_count": f"Attendee count exceeds the configured capacity of {profile.capacity}."}
            )

        overlap_qs = SpaceBooking.objects.filter(
            facility_space=facility_space,
            start_at__lt=end_at,
            end_at__gt=start_at,
            status__in=OPEN_BOOKING_STATUSES,
        )
        if instance is not None:
            overlap_qs = overlap_qs.exclude(pk=instance.pk)
        if overlap_qs.exists():
            raise serializers.ValidationError(
                {"facility_space": "This space already has an overlapping booking for the selected time."}
            )

        if not attrs.get("requested_by") and instance is None:
            attrs["requested_by"] = self.context["request"].user
        if "status" not in attrs:
            attrs["status"] = SpaceBooking.Status.REQUESTED

        return attrs


class FacilitySpaceBookingActionSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, default="")
