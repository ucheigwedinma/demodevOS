from __future__ import annotations

from datetime import timedelta

from django.db.models import Count
from django.utils import timezone
from django_filters import rest_framework as filters
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.mixins import OrgScopedMixin
from apps.crm.models import ContactAccount
from apps.finance.models import Customer
from apps.settings.models import Department
from apps.settings.permissions import HasRolePermission
from apps.tenants.models import TenantProfile

from .models import Facility, FacilitySpaceProfile, SpaceAllocation, SpaceBooking
from .space_occupancy_serializers import (
    FacilitySpaceAllocationDetailSerializer,
    FacilitySpaceAllocationListSerializer,
    FacilitySpaceAllocationReleaseSerializer,
    FacilitySpaceAllocationWriteSerializer,
    FacilitySpaceBookingActionSerializer,
    FacilitySpaceBookingDetailSerializer,
    FacilitySpaceBookingListSerializer,
    FacilitySpaceBookingWriteSerializer,
    FacilitySpaceProfileDetailSerializer,
    FacilitySpaceProfileListSerializer,
    FacilitySpaceProfileWriteSerializer,
)
from .space_occupancy_workflows import (
    ACTIVE_ALLOCATION_STATUSES,
    OPEN_BOOKING_STATUSES,
    ensure_allocation_defaults,
    ensure_booking_defaults,
    ensure_space_profile_defaults,
    ensure_space_profiles_for_organization,
    run_space_occupancy_automation,
)


def _resolve_user_org(request):
    org = getattr(request, "organization", None)
    if org is not None:
        return org
    profile = getattr(request.user, "profile", None)
    return getattr(profile, "organization", None)


class FacilitySpaceProfileFilter(filters.FilterSet):
    facility = filters.NumberFilter(field_name="facility_space__facility_id")
    zone = filters.NumberFilter(field_name="facility_space__zone_id")

    class Meta:
        model = FacilitySpaceProfile
        fields = ["facility_space", "facility", "zone", "space_type", "status", "is_bookable"]


class FacilitySpaceAllocationFilter(filters.FilterSet):
    facility = filters.NumberFilter(field_name="facility_space__facility_id")
    zone = filters.NumberFilter(field_name="facility_space__zone_id")
    starts_after = filters.DateFilter(field_name="start_date", lookup_expr="gte")
    starts_before = filters.DateFilter(field_name="start_date", lookup_expr="lte")
    ends_after = filters.DateFilter(field_name="end_date", lookup_expr="gte")
    ends_before = filters.DateFilter(field_name="end_date", lookup_expr="lte")

    class Meta:
        model = SpaceAllocation
        fields = [
            "facility_space",
            "facility",
            "zone",
            "allocation_type",
            "status",
            "employee",
            "department",
            "tenant_customer",
            "tenant_contact_account",
        ]


class FacilitySpaceBookingFilter(filters.FilterSet):
    facility = filters.NumberFilter(field_name="facility_space__facility_id")
    zone = filters.NumberFilter(field_name="facility_space__zone_id")
    starts_after = filters.IsoDateTimeFilter(field_name="start_at", lookup_expr="gte")
    starts_before = filters.IsoDateTimeFilter(field_name="start_at", lookup_expr="lte")
    ends_after = filters.IsoDateTimeFilter(field_name="end_at", lookup_expr="gte")
    ends_before = filters.IsoDateTimeFilter(field_name="end_at", lookup_expr="lte")

    class Meta:
        model = SpaceBooking
        fields = [
            "facility_space",
            "facility",
            "zone",
            "status",
            "requested_by",
            "approved_by",
        ]


class FacilitySpaceOccupancyOverviewView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    rbac_action = "view"

    def get(self, request):
        org = _resolve_user_org(request)
        if org is None:
            return Response({"detail": "Organization context required."}, status=400)

        ensure_space_profiles_for_organization(org)

        now = timezone.now()
        today = timezone.localdate()
        upcoming_window = now + timedelta(days=7)

        profiles = list(
            FacilitySpaceProfile.objects.filter(organization=org)
            .select_related(
                "facility_space",
                "facility_space__facility",
                "facility_space__zone",
                "facility_space__unit",
            )
            .order_by(
                "facility_space__facility__facility_code",
                "facility_space__zone__zone_code",
                "facility_space__unit__unit_number",
            )
        )
        allocations = list(
            SpaceAllocation.objects.filter(organization=org)
            .select_related(
                "facility_space",
                "facility_space__facility",
                "facility_space__zone",
                "facility_space__unit",
                "employee",
                "department",
                "tenant_customer",
                "tenant_contact_account",
                "allocated_by",
            )
            .order_by("end_date", "start_date", "id")
        )
        bookings = list(
            SpaceBooking.objects.filter(organization=org)
            .select_related(
                "facility_space",
                "facility_space__facility",
                "facility_space__zone",
                "facility_space__unit",
                "facility_space__occupancy_profile",
                "requested_by",
                "approved_by",
            )
            .order_by("start_at", "id")
        )

        active_profiles = [profile for profile in profiles if profile.status == FacilitySpaceProfile.Status.ACTIVE]
        active_allocations = [allocation for allocation in allocations if allocation.status in ACTIVE_ALLOCATION_STATUSES]
        occupied_space_ids = {allocation.facility_space_id for allocation in active_allocations}
        occupied_spaces = len(occupied_space_ids)
        vacant_profiles = [profile for profile in active_profiles if profile.facility_space_id not in occupied_space_ids]

        total_capacity = sum(profile.capacity for profile in active_profiles)
        occupied_capacity = sum(allocation.occupant_count for allocation in active_allocations)
        occupancy_rate = round((occupied_capacity / total_capacity) * 100, 2) if total_capacity else 0.0
        vacancy_rate = round(100 - occupancy_rate, 2) if total_capacity else 0.0

        open_bookings = [booking for booking in bookings if booking.status in OPEN_BOOKING_STATUSES]
        upcoming_bookings = [
            booking
            for booking in open_bookings
            if booking.start_at >= now and booking.start_at <= upcoming_window
        ]
        live_bookings = [booking for booking in open_bookings if booking.start_at <= now < booking.end_at]
        ending_soon_allocations = [
            allocation for allocation in allocations if allocation.status == SpaceAllocation.Status.ENDING_SOON
        ]
        tenant_profiles = list(
            TenantProfile.objects.filter(organization=org)
            .select_related("facility", "facility_space", "unit", "customer", "contact_account")
            .order_by("lease_end_date", "display_name", "id")
        )
        active_tenants = [
            profile for profile in tenant_profiles if profile.status == TenantProfile.Status.ACTIVE
        ]

        payload = {
            "generated_at": now.isoformat(),
            "kpis": {
                "total_spaces": len(profiles),
                "active_spaces": len(active_profiles),
                "occupied_spaces": occupied_spaces,
                "vacant_spaces": len(vacant_profiles),
                "occupancy_rate": occupancy_rate,
                "vacancy_rate": vacancy_rate,
                "bookable_spaces": sum(1 for profile in active_profiles if profile.is_bookable),
                "active_bookings": len(open_bookings),
                "live_bookings": len(live_bookings),
                "tenant_allocations": sum(
                    1
                    for allocation in active_allocations
                    if allocation.allocation_type == SpaceAllocation.AllocationType.TENANT
                ),
                "employee_allocations": sum(
                    1
                    for allocation in active_allocations
                    if allocation.allocation_type == SpaceAllocation.AllocationType.EMPLOYEE
                ),
                "department_allocations": sum(
                    1
                    for allocation in active_allocations
                    if allocation.allocation_type == SpaceAllocation.AllocationType.DEPARTMENT
                ),
                "tenant_profiles_active": len(active_tenants),
                "occupancy_capacity_used": occupied_capacity,
                "occupancy_capacity_total": total_capacity,
            },
            "space_type_breakdown": list(
                FacilitySpaceProfile.objects.filter(organization=org)
                .values("space_type")
                .annotate(count=Count("id"))
                .order_by("-count", "space_type")
            ),
            "allocation_status_breakdown": list(
                SpaceAllocation.objects.filter(organization=org)
                .values("status")
                .annotate(count=Count("id"))
                .order_by("-count", "status")
            ),
            "vacancy_watchlist": FacilitySpaceProfileListSerializer(
                vacant_profiles[:8],
                many=True,
                context={"request": request},
            ).data,
            "allocation_watchlist": FacilitySpaceAllocationListSerializer(
                sorted(
                    ending_soon_allocations,
                    key=lambda allocation: (
                        allocation.end_date or today + timedelta(days=3650),
                        allocation.id,
                    ),
                )[:8],
                many=True,
                context={"request": request},
            ).data,
            "booking_watchlist": FacilitySpaceBookingListSerializer(
                sorted(
                    open_bookings,
                    key=lambda booking: (
                        booking.start_at,
                        booking.id,
                    ),
                )[:8],
                many=True,
                context={"request": request},
            ).data,
            "tenant_watchlist": [
                {
                    "id": profile.id,
                    "display_name": profile.resolved_display_name,
                    "status": profile.status,
                    "facility_code": profile.facility.facility_code if profile.facility_id else "",
                    "space_label": profile.facility_space.space_label if profile.facility_space_id else "",
                    "unit_number": profile.unit.unit_number if profile.unit_id else "",
                    "lease_end_date": profile.lease_end_date.isoformat() if profile.lease_end_date else None,
                    "occupant_count": profile.occupant_count,
                }
                for profile in active_tenants[:8]
            ],
            "upcoming_bookings_count": len(upcoming_bookings),
        }
        return Response(payload)


class FacilitySpaceOccupancyLookupsView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    rbac_action = "view"

    def get(self, request):
        org = _resolve_user_org(request)
        if org is None:
            return Response({"detail": "Organization context required."}, status=400)

        ensure_space_profiles_for_organization(org)

        User = request.user.__class__
        users = User.objects.filter(profile__organization=org, is_active=True).select_related("profile").order_by(
            "first_name",
            "last_name",
            "email",
        )
        facilities = Facility.objects.filter(organization=org).select_related("property").order_by("facility_code")
        profiles = (
            FacilitySpaceProfile.objects.filter(organization=org)
            .select_related(
                "facility_space",
                "facility_space__facility",
                "facility_space__zone",
                "facility_space__unit",
            )
            .order_by(
                "facility_space__facility__facility_code",
                "facility_space__zone__zone_code",
                "facility_space__unit__unit_number",
            )
        )
        departments = Department.objects.filter(
            division__organization=org,
            is_active=True,
        ).select_related("division").order_by("name")
        customers = Customer.objects.filter(organization=org).order_by("name")
        contacts = ContactAccount.objects.filter(organization=org, is_active=True).select_related(
            "finance_customer"
        ).order_by("entity_type", "legal_name", "first_name", "last_name", "email")
        tenants = TenantProfile.objects.filter(organization=org).select_related(
            "customer",
            "contact_account",
            "facility",
            "facility_space",
            "unit",
        ).order_by("display_name", "id")

        payload = {
            "users": [
                {
                    "id": user.id,
                    "label": user.get_full_name().strip() or user.email or user.username,
                    "email": user.email or "",
                }
                for user in users[:200]
            ],
            "facilities": [
                {
                    "id": facility.id,
                    "facility_code": facility.facility_code,
                    "property_name": facility.property.name,
                }
                for facility in facilities[:200]
            ],
            "spaces": FacilitySpaceProfileListSerializer(
                profiles[:500],
                many=True,
                context={"request": request},
            ).data,
            "departments": [
                {
                    "id": department.id,
                    "label": department.name,
                    "division_name": department.division.name,
                }
                for department in departments[:200]
            ],
            "customers": [
                {
                    "id": customer.id,
                    "label": customer.name,
                    "email": customer.email or "",
                    "phone": customer.phone or "",
                }
                for customer in customers[:200]
            ],
            "contact_accounts": [
                {
                    "id": contact.id,
                    "label": contact.display_name,
                    "entity_type": contact.entity_type,
                    "customer": contact.finance_customer_id,
                    "customer_name": contact.finance_customer.name if contact.finance_customer_id else "",
                    "email": contact.email or "",
                    "phone": contact.phone or "",
                }
                for contact in contacts[:300]
            ],
            "tenant_profiles": [
                {
                    "id": tenant.id,
                    "display_name": tenant.resolved_display_name,
                    "status": tenant.status,
                    "facility_code": tenant.facility.facility_code if tenant.facility_id else "",
                    "space_label": tenant.facility_space.space_label if tenant.facility_space_id else "",
                    "unit_number": tenant.unit.unit_number if tenant.unit_id else "",
                }
                for tenant in tenants[:300]
            ],
        }
        return Response(payload)


class FacilitySpaceOccupancyWorkflowView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    rbac_action = "edit"

    def post(self, request):
        org = _resolve_user_org(request)
        if org is None:
            return Response({"detail": "Organization context required."}, status=400)

        result = run_space_occupancy_automation(org)
        return Response(result, status=status.HTTP_200_OK)


class FacilitySpaceProfileViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    filterset_class = FacilitySpaceProfileFilter
    search_fields = [
        "facility_space__space_label",
        "facility_space__unit__unit_number",
        "facility_space__zone__name",
        "facility_space__zone__zone_code",
        "facility_space__facility__facility_code",
    ]
    ordering_fields = [
        "facility_space__facility__facility_code",
        "facility_space__zone__zone_code",
        "facility_space__unit__unit_number",
        "space_type",
        "status",
        "capacity",
        "updated_at",
    ]
    ordering = [
        "facility_space__facility__facility_code",
        "facility_space__zone__zone_code",
        "facility_space__unit__unit_number",
    ]
    queryset = FacilitySpaceProfile.objects.all()

    def get_queryset(self):
        org = self._resolve_request_org()
        if org is not None:
            ensure_space_profiles_for_organization(org)
        return (
            super()
            .get_queryset()
            .select_related(
                "facility_space",
                "facility_space__facility",
                "facility_space__zone",
                "facility_space__unit",
            )
        )

    def get_serializer_class(self):
        if self.action == "list":
            return FacilitySpaceProfileListSerializer
        if self.action == "retrieve":
            return FacilitySpaceProfileDetailSerializer
        if self.action in {"create", "update", "partial_update"}:
            return FacilitySpaceProfileWriteSerializer
        return FacilitySpaceProfileDetailSerializer

    def perform_create(self, serializer):
        profile = serializer.save(organization=self._resolve_request_org())
        ensure_space_profile_defaults(profile.facility_space)

    def perform_update(self, serializer):
        profile = serializer.save()
        ensure_space_profile_defaults(profile.facility_space)


class FacilitySpaceAllocationViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "create",
        "update": "edit",
        "partial_update": "edit",
        "destroy": "delete",
        "release": "edit",
    }
    filterset_class = FacilitySpaceAllocationFilter
    search_fields = [
        "facility_space__space_label",
        "facility_space__unit__unit_number",
        "facility_space__facility__facility_code",
        "department__name",
        "tenant_customer__name",
        "tenant_contact_account__legal_name",
        "tenant_contact_account__first_name",
        "tenant_contact_account__last_name",
        "notes",
    ]
    ordering_fields = [
        "start_date",
        "end_date",
        "status",
        "allocation_type",
        "occupant_count",
        "updated_at",
    ]
    ordering = ["start_date", "facility_space__unit__unit_number", "id"]
    queryset = SpaceAllocation.objects.all()

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related(
                "facility_space",
                "facility_space__facility",
                "facility_space__zone",
                "facility_space__unit",
                "employee",
                "department",
                "tenant_customer",
                "tenant_contact_account",
                "allocated_by",
            )
        )

    def get_serializer_class(self):
        if self.action == "list":
            return FacilitySpaceAllocationListSerializer
        if self.action == "retrieve":
            return FacilitySpaceAllocationDetailSerializer
        if self.action in {"create", "update", "partial_update"}:
            return FacilitySpaceAllocationWriteSerializer
        if self.action == "release":
            return FacilitySpaceAllocationReleaseSerializer
        return FacilitySpaceAllocationDetailSerializer

    def perform_create(self, serializer):
        allocation = serializer.save(
            organization=self._resolve_request_org(),
            allocated_by=self.request.user,
        )
        ensure_allocation_defaults(allocation)
        if allocation.allocation_type == SpaceAllocation.AllocationType.TENANT:
            from .space_occupancy_workflows import (
                sync_inventory_for_tenant_allocation,
                sync_tenant_profile_for_allocation,
            )

            sync_tenant_profile_for_allocation(allocation)
            sync_inventory_for_tenant_allocation(allocation)

    def perform_update(self, serializer):
        allocation = serializer.save()
        ensure_allocation_defaults(allocation)
        if allocation.allocation_type == SpaceAllocation.AllocationType.TENANT:
            from .space_occupancy_workflows import (
                sync_inventory_for_tenant_allocation,
                sync_tenant_profile_for_allocation,
            )

            sync_tenant_profile_for_allocation(allocation)
            sync_inventory_for_tenant_allocation(allocation)

    @action(detail=True, methods=["post"], url_path="release")
    def release(self, request, pk=None):
        allocation = self.get_object()
        serializer = FacilitySpaceAllocationReleaseSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)

        today = timezone.localdate()
        now = timezone.now()
        update_fields = {"released_at", "updated_at", "status"}

        if allocation.status == SpaceAllocation.Status.PENDING or allocation.start_date > today:
            allocation.status = SpaceAllocation.Status.CANCELLED
        else:
            allocation.status = SpaceAllocation.Status.ENDED
            if not allocation.end_date or allocation.end_date > today:
                allocation.end_date = today
                update_fields.add("end_date")

        allocation.released_at = now
        note = serializer.validated_data.get("note", "").strip()
        if note:
            allocation.notes = (
                f"{allocation.notes}\n\n[Released {today.isoformat()}] {note}"
                if allocation.notes
                else f"[Released {today.isoformat()}] {note}"
            )
            update_fields.add("notes")

        allocation.save(update_fields=sorted(update_fields))
        ensure_allocation_defaults(allocation)

        if allocation.allocation_type == SpaceAllocation.AllocationType.TENANT:
            from .space_occupancy_workflows import (
                sync_inventory_for_tenant_allocation,
                sync_tenant_profile_for_allocation,
            )

            sync_tenant_profile_for_allocation(allocation)
            sync_inventory_for_tenant_allocation(allocation)

        data = FacilitySpaceAllocationDetailSerializer(allocation, context={"request": request}).data
        return Response(data, status=status.HTTP_200_OK)


class FacilitySpaceBookingViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "create",
        "update": "edit",
        "partial_update": "edit",
        "destroy": "delete",
        "confirm": "edit",
        "cancel": "edit",
        "check_in": "edit",
    }
    filterset_class = FacilitySpaceBookingFilter
    search_fields = [
        "title",
        "purpose",
        "facility_space__space_label",
        "facility_space__unit__unit_number",
        "facility_space__facility__facility_code",
        "requested_by__email",
        "requested_by__first_name",
        "requested_by__last_name",
    ]
    ordering_fields = ["start_at", "end_at", "status", "attendee_count", "updated_at"]
    ordering = ["start_at", "facility_space__unit__unit_number", "id"]
    queryset = SpaceBooking.objects.all()

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related(
                "facility_space",
                "facility_space__facility",
                "facility_space__zone",
                "facility_space__unit",
                "facility_space__occupancy_profile",
                "requested_by",
                "approved_by",
            )
        )

    def get_serializer_class(self):
        if self.action == "list":
            return FacilitySpaceBookingListSerializer
        if self.action == "retrieve":
            return FacilitySpaceBookingDetailSerializer
        if self.action in {"create", "update", "partial_update"}:
            return FacilitySpaceBookingWriteSerializer
        if self.action in {"confirm", "cancel", "check_in"}:
            return FacilitySpaceBookingActionSerializer
        return FacilitySpaceBookingDetailSerializer

    def perform_create(self, serializer):
        booking = serializer.save(organization=self._resolve_request_org())
        ensure_booking_defaults(booking)

    def perform_update(self, serializer):
        booking = serializer.save()
        ensure_booking_defaults(booking)

    @action(detail=True, methods=["post"], url_path="confirm")
    def confirm(self, request, pk=None):
        booking = self.get_object()
        serializer = FacilitySpaceBookingActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)

        note = serializer.validated_data.get("note", "").strip()
        if note:
            booking.notes = f"{booking.notes}\n\n{note}" if booking.notes else note
        booking.status = SpaceBooking.Status.CONFIRMED
        booking.approved_by = request.user
        booking.save(update_fields=["status", "approved_by", "notes", "updated_at"])
        ensure_booking_defaults(booking)
        data = FacilitySpaceBookingDetailSerializer(booking, context={"request": request}).data
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        booking = self.get_object()
        serializer = FacilitySpaceBookingActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)

        note = serializer.validated_data.get("note", "").strip()
        if note:
            booking.notes = (
                f"{booking.notes}\n\n[Cancelled {timezone.now().isoformat()}] {note}"
                if booking.notes
                else f"[Cancelled {timezone.now().isoformat()}] {note}"
            )
        booking.status = SpaceBooking.Status.CANCELLED
        booking.save(update_fields=["status", "notes", "updated_at"])
        ensure_booking_defaults(booking)
        data = FacilitySpaceBookingDetailSerializer(booking, context={"request": request}).data
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="check-in")
    def check_in(self, request, pk=None):
        booking = self.get_object()
        serializer = FacilitySpaceBookingActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)

        note = serializer.validated_data.get("note", "").strip()
        if note:
            booking.notes = f"{booking.notes}\n\n{note}" if booking.notes else note
        booking.status = SpaceBooking.Status.CHECKED_IN
        booking.checked_in_at = timezone.now()
        booking.save(update_fields=["status", "checked_in_at", "notes", "updated_at"])
        data = FacilitySpaceBookingDetailSerializer(booking, context={"request": request}).data
        return Response(data, status=status.HTTP_200_OK)
