from __future__ import annotations

import logging
from datetime import timedelta

from django.db.models import Q, Sum
from django.utils import timezone

from apps.crm.models import ContactPropertyLink
from apps.properties.models import PropertyInventory, PropertyInventoryEvent
from apps.tenants.lease_context import ensure_tenant_profile_lease_context
from apps.tenants.models import TenantProfile

from .models import FacilitySpaceProfile, SpaceAllocation, SpaceBooking

logger = logging.getLogger(__name__)


def _notify_space_cascade(*, organization, event_key, title, message):
    try:
        from apps.accounts.models import UserProfile
        from apps.notifications.services import Notification, dispatch_workflow_notification

        admins = [
            p.user
            for p in UserProfile.objects.filter(
                organization=organization, role="admin", user__is_active=True
            ).select_related("user")
        ]
        if admins:
            dispatch_workflow_notification(
                organization=organization,
                event_key=event_key,
                recipients=admins,
                fallback_title=title,
                fallback_message=message,
                fallback_category=Notification.Category.SYSTEM,
            )
    except Exception:
        logger.debug("Space cascade notification skipped", exc_info=True)


ACTIVE_ALLOCATION_STATUSES = {
    SpaceAllocation.Status.ACTIVE,
    SpaceAllocation.Status.ENDING_SOON,
}

OPEN_BOOKING_STATUSES = {
    SpaceBooking.Status.REQUESTED,
    SpaceBooking.Status.CONFIRMED,
    SpaceBooking.Status.CHECKED_IN,
}


def space_label_for(space) -> str:
    return space.space_label or space.unit.unit_number


def occupant_label_for(allocation: SpaceAllocation) -> str:
    if allocation.allocation_type == SpaceAllocation.AllocationType.EMPLOYEE and allocation.employee_id:
        full_name = allocation.employee.get_full_name().strip()
        return full_name or allocation.employee.email or allocation.employee.username
    if allocation.allocation_type == SpaceAllocation.AllocationType.DEPARTMENT and allocation.department_id:
        return allocation.department.name
    if allocation.tenant_customer_id:
        return allocation.tenant_customer.name
    if allocation.tenant_contact_account_id:
        return allocation.tenant_contact_account.display_name
    return "Unassigned"


def default_space_type_for(facility_space) -> str:
    label = (facility_space.space_label or facility_space.unit.unit_number or "").lower()
    unit_category = getattr(facility_space.unit, "unit_category", "")

    if "desk" in label or "workstation" in label:
        return FacilitySpaceProfile.SpaceType.DESK
    if "meeting" in label or "conference" in label or "board" in label:
        return FacilitySpaceProfile.SpaceType.MEETING_ROOM
    if unit_category in {"retail", "warehouse"}:
        return FacilitySpaceProfile.SpaceType.TENANT_SUITE
    if unit_category == "office":
        return FacilitySpaceProfile.SpaceType.ROOM
    return FacilitySpaceProfile.SpaceType.OTHER


def ensure_space_profile_defaults(facility_space) -> tuple[FacilitySpaceProfile, bool]:
    profile, created = FacilitySpaceProfile.objects.get_or_create(
        facility_space=facility_space,
        defaults={
            "organization": facility_space.organization,
            "space_type": default_space_type_for(facility_space),
            "capacity": 1,
            "is_bookable": False,
            "status": FacilitySpaceProfile.Status.ACTIVE,
        },
    )

    changed = created
    update_fields: list[str] = []

    if profile.organization_id != facility_space.organization_id:
        profile.organization = facility_space.organization
        update_fields.append("organization")
        changed = True
    if profile.capacity <= 0:
        profile.capacity = 1
        update_fields.append("capacity")
        changed = True
    if not profile.space_type:
        profile.space_type = default_space_type_for(facility_space)
        update_fields.append("space_type")
        changed = True

    if update_fields:
        profile.save(update_fields=[*dict.fromkeys([*update_fields, "updated_at"])])

    return profile, changed


def ensure_space_profiles_for_organization(organization) -> int:
    created_or_fixed = 0
    spaces = (
        organization.facility_unit_spaces.select_related("unit")
        .all()
    )
    for facility_space in spaces:
        _profile, changed = ensure_space_profile_defaults(facility_space)
        if changed:
            created_or_fixed += 1
    return created_or_fixed


def allocation_status_for(allocation: SpaceAllocation, *, today=None) -> str:
    today = today or timezone.localdate()
    if allocation.status == SpaceAllocation.Status.CANCELLED:
        return SpaceAllocation.Status.CANCELLED
    if allocation.status == SpaceAllocation.Status.ENDED or allocation.released_at is not None:
        return SpaceAllocation.Status.ENDED
    if allocation.end_date and allocation.end_date < today:
        return SpaceAllocation.Status.ENDED
    if allocation.start_date > today:
        return SpaceAllocation.Status.PENDING
    if allocation.end_date and allocation.end_date <= today + timedelta(days=30):
        return SpaceAllocation.Status.ENDING_SOON
    return SpaceAllocation.Status.ACTIVE


def ensure_allocation_defaults(allocation: SpaceAllocation, *, today=None) -> bool:
    today = today or timezone.localdate()
    ensure_space_profile_defaults(allocation.facility_space)

    changed = False
    update_fields: list[str] = []

    if allocation.tenant_contact_account_id and not allocation.tenant_customer_id:
        finance_customer = allocation.tenant_contact_account.finance_customer
        if finance_customer_id := getattr(finance_customer, "id", None):
            allocation.tenant_customer = finance_customer
            update_fields.append("tenant_customer")
            changed = True

    target_status = allocation_status_for(allocation, today=today)
    if allocation.status != target_status:
        allocation.status = target_status
        update_fields.append("status")
        changed = True

    if allocation.status in {SpaceAllocation.Status.ENDED, SpaceAllocation.Status.CANCELLED} and allocation.released_at is None:
        allocation.released_at = timezone.now()
        update_fields.append("released_at")
        changed = True

    if changed:
        allocation.save(update_fields=[*dict.fromkeys([*update_fields, "updated_at"])])
    return changed


def sync_tenant_profile_for_allocation(allocation: SpaceAllocation, *, today=None) -> bool:
    if allocation.allocation_type != SpaceAllocation.AllocationType.TENANT:
        return False

    today = today or timezone.localdate()
    facility_space = allocation.facility_space

    profile_qs = TenantProfile.objects.filter(
        organization=allocation.organization,
        facility_space=facility_space,
    )
    if allocation.tenant_customer_id:
        profile_qs = profile_qs.filter(customer_id=allocation.tenant_customer_id)
    elif allocation.tenant_contact_account_id:
        profile_qs = profile_qs.filter(contact_account_id=allocation.tenant_contact_account_id)

    profile = profile_qs.order_by("-updated_at", "-id").first()
    created = False
    if profile is None:
        customer = allocation.tenant_customer
        contact = allocation.tenant_contact_account
        tenant_type = TenantProfile.TenantType.CORPORATE
        if contact and contact.entity_type == contact.EntityType.INDIVIDUAL:
            tenant_type = TenantProfile.TenantType.INDIVIDUAL
        profile = TenantProfile.objects.create(
            organization=allocation.organization,
            customer=customer,
            contact_account=contact,
            property=facility_space.facility.property,
            unit=facility_space.unit,
            facility=facility_space.facility,
            facility_space=facility_space,
            tenant_type=tenant_type,
            display_name=occupant_label_for(allocation),
            lease_start_date=allocation.start_date,
            lease_end_date=allocation.end_date,
            occupant_count=max(1, allocation.occupant_count),
        )
        created = True

    status_map = {
        SpaceAllocation.Status.PENDING: TenantProfile.Status.PENDING_MOVE_IN,
        SpaceAllocation.Status.ACTIVE: TenantProfile.Status.ACTIVE,
        SpaceAllocation.Status.ENDING_SOON: TenantProfile.Status.ACTIVE,
        SpaceAllocation.Status.ENDED: TenantProfile.Status.MOVED_OUT,
        SpaceAllocation.Status.CANCELLED: TenantProfile.Status.INACTIVE,
    }
    target_status = status_map.get(allocation.status, TenantProfile.Status.PENDING_MOVE_IN)

    changed = created
    update_fields: list[str] = []
    field_values = {
        "customer": allocation.tenant_customer,
        "contact_account": allocation.tenant_contact_account,
        "property": facility_space.facility.property,
        "unit": facility_space.unit,
        "facility": facility_space.facility,
        "facility_space": facility_space,
        "display_name": occupant_label_for(allocation),
        "lease_start_date": allocation.start_date,
        "lease_end_date": allocation.end_date,
        "occupant_count": max(1, allocation.occupant_count),
        "status": target_status,
    }

    if target_status == TenantProfile.Status.ACTIVE and profile.move_in_date is None:
        field_values["move_in_date"] = allocation.start_date
    elif target_status in {TenantProfile.Status.MOVED_OUT, TenantProfile.Status.INACTIVE}:
        field_values["move_out_date"] = allocation.end_date or today

    for field_name, value in field_values.items():
        if getattr(profile, field_name) != value:
            setattr(profile, field_name, value)
            update_fields.append(field_name)
            changed = True

    if changed and update_fields:
        profile.save(update_fields=[*dict.fromkeys([*update_fields, "updated_at"])])
    if created or changed:
        ensure_tenant_profile_lease_context(profile)

    if (
        allocation.tenant_contact_account_id
        and allocation.status in ACTIVE_ALLOCATION_STATUSES
        and facility_space.unit_id
    ):
        ContactPropertyLink.objects.get_or_create(
            contact=allocation.tenant_contact_account,
            property=facility_space.facility.property,
            unit=facility_space.unit,
            relationship_type=ContactPropertyLink.RelationshipType.LEASED,
            defaults={"notes": f"Synced from facility allocation #{allocation.id}."},
        )

    if changed:
        tenant_name = profile.resolved_display_name
        if created:
            _notify_space_cascade(
                organization=allocation.organization,
                event_key="tenant_profile_auto_created",
                title=f"Tenant Profile Auto-Created — {tenant_name}",
                message=(
                    f"A tenant profile for '{tenant_name}' has been automatically created "
                    f"from space allocation #{allocation.id} in facility "
                    f"{facility_space.facility.facility_code}."
                ),
            )
        else:
            _notify_space_cascade(
                organization=allocation.organization,
                event_key="tenant_profile_synced",
                title=f"Tenant Profile Synced — {tenant_name}",
                message=(
                    f"Tenant profile for '{tenant_name}' has been automatically updated "
                    f"to {target_status} based on space allocation changes."
                ),
            )

    return changed


def sync_inventory_for_tenant_allocation(allocation: SpaceAllocation) -> bool:
    if allocation.allocation_type != SpaceAllocation.AllocationType.TENANT:
        return False

    unit = allocation.facility_space.unit
    inventory, _created = PropertyInventory.objects.get_or_create(
        unit=unit,
        defaults={
            "organization": allocation.organization,
            "status": PropertyInventory.InventoryStatus.AVAILABLE,
            "list_price": unit.asking_price,
        },
    )

    active_tenant_allocations = SpaceAllocation.objects.filter(
        organization=allocation.organization,
        facility_space__unit=unit,
        allocation_type=SpaceAllocation.AllocationType.TENANT,
        status__in=ACTIVE_ALLOCATION_STATUSES,
    ).select_related("tenant_customer", "tenant_contact_account")

    active_tenant = active_tenant_allocations.order_by("start_date", "id").first()
    changed = False

    if active_tenant:
        desired_status = PropertyInventory.InventoryStatus.LEASED
        desired_allocated_to = occupant_label_for(active_tenant)
        desired_allocated_on = active_tenant.start_date
        if inventory.status != desired_status:
            old_status = inventory.status
            inventory.status = desired_status
            changed = True
            PropertyInventoryEvent.objects.create(
                organization=inventory.organization,
                inventory=inventory,
                event_type=PropertyInventoryEvent.EventType.LEASED,
                from_status=old_status,
                to_status=desired_status,
                actor_name="System",
                notes="Leased from facility tenant allocation sync.",
            )
        if inventory.allocated_to != desired_allocated_to:
            inventory.allocated_to = desired_allocated_to
            changed = True
        if inventory.allocated_on != desired_allocated_on:
            inventory.allocated_on = desired_allocated_on
            changed = True
    else:
        if inventory.status == PropertyInventory.InventoryStatus.LEASED:
            old_status = inventory.status
            inventory.status = PropertyInventory.InventoryStatus.AVAILABLE
            changed = True
            PropertyInventoryEvent.objects.create(
                organization=inventory.organization,
                inventory=inventory,
                event_type=PropertyInventoryEvent.EventType.MADE_AVAILABLE,
                from_status=old_status,
                to_status=inventory.status,
                actor_name="System",
                notes="Released after tenant allocation ended.",
            )
        if inventory.allocated_to:
            inventory.allocated_to = ""
            changed = True
        if inventory.allocated_on is not None:
            inventory.allocated_on = None
            changed = True

    if changed:
        inventory.save(update_fields=["status", "allocated_to", "allocated_on", "updated_at"])

        unit_label = str(unit) if unit else "Unknown unit"
        if inventory.status == PropertyInventory.InventoryStatus.LEASED:
            _notify_space_cascade(
                organization=allocation.organization,
                event_key="unit_inventory_leased_from_allocation",
                title=f"Unit Inventory Updated — {unit_label} Leased",
                message=(
                    f"Unit {unit_label} has been automatically marked as leased in property inventory "
                    f"following tenant allocation. Allocated to: {inventory.allocated_to}."
                ),
            )
        elif inventory.status == PropertyInventory.InventoryStatus.AVAILABLE:
            _notify_space_cascade(
                organization=allocation.organization,
                event_key="unit_inventory_released_from_allocation",
                title=f"Unit Inventory Released — {unit_label}",
                message=(
                    f"Unit {unit_label} has been automatically released back to available inventory "
                    f"following the end of a tenant allocation."
                ),
            )

    return changed


def ensure_booking_defaults(booking: SpaceBooking, *, now=None) -> bool:
    now = now or timezone.now()
    profile, _changed = ensure_space_profile_defaults(booking.facility_space)

    changed = False
    update_fields: list[str] = []

    if booking.status == SpaceBooking.Status.REQUESTED and not profile.booking_requires_approval:
        booking.status = SpaceBooking.Status.CONFIRMED
        update_fields.append("status")
        changed = True
        if booking.approved_by_id is None and booking.requested_by_id:
            booking.approved_by = booking.requested_by
            update_fields.append("approved_by")

    if (
        booking.status == SpaceBooking.Status.CONFIRMED
        and booking.start_at <= now < booking.end_at
        and not profile.requires_check_in
    ):
        booking.status = SpaceBooking.Status.CHECKED_IN
        booking.checked_in_at = booking.checked_in_at or now
        update_fields.extend(["status", "checked_in_at"])
        changed = True

    if (
        booking.status == SpaceBooking.Status.CONFIRMED
        and profile.requires_check_in
        and booking.checked_in_at is None
        and now > booking.start_at + timedelta(minutes=30)
    ):
        booking.status = SpaceBooking.Status.NO_SHOW
        update_fields.append("status")
        changed = True

    if booking.status in {SpaceBooking.Status.CONFIRMED, SpaceBooking.Status.CHECKED_IN} and booking.end_at <= now:
        booking.status = SpaceBooking.Status.COMPLETED
        booking.checked_out_at = booking.checked_out_at or now
        update_fields.extend(["status", "checked_out_at"])
        changed = True

    if booking.status == SpaceBooking.Status.CANCELLED and booking.cancelled_at is None:
        booking.cancelled_at = now
        update_fields.append("cancelled_at")
        changed = True

    if changed:
        booking.save(update_fields=[*dict.fromkeys([*update_fields, "updated_at"])])
    return changed


def run_space_occupancy_automation(organization) -> dict[str, int]:
    now = timezone.now()
    today = timezone.localdate()
    summary = {
        "space_profiles_synced": ensure_space_profiles_for_organization(organization),
        "allocations_synced": 0,
        "allocations_ended": 0,
        "tenant_profiles_synced": 0,
        "inventory_updates": 0,
        "bookings_synced": 0,
        "bookings_completed": 0,
        "bookings_no_show": 0,
    }

    allocations = (
        SpaceAllocation.objects.filter(organization=organization)
        .select_related(
            "facility_space",
            "facility_space__facility",
            "facility_space__unit",
            "tenant_customer",
            "tenant_contact_account",
            "employee",
            "department",
        )
    )

    for allocation in allocations:
        previous_status = allocation.status
        if ensure_allocation_defaults(allocation, today=today):
            summary["allocations_synced"] += 1
        if previous_status != allocation.status and allocation.status == SpaceAllocation.Status.ENDED:
            summary["allocations_ended"] += 1
        if allocation.allocation_type == SpaceAllocation.AllocationType.TENANT:
            if sync_tenant_profile_for_allocation(allocation, today=today):
                summary["tenant_profiles_synced"] += 1
            if sync_inventory_for_tenant_allocation(allocation):
                summary["inventory_updates"] += 1

    bookings = (
        SpaceBooking.objects.filter(organization=organization)
        .exclude(
            status__in=[
                SpaceBooking.Status.COMPLETED,
                SpaceBooking.Status.CANCELLED,
                SpaceBooking.Status.NO_SHOW,
                SpaceBooking.Status.REJECTED,
            ]
        )
        .select_related("facility_space", "facility_space__unit", "facility_space__occupancy_profile")
    )

    for booking in bookings:
        previous_status = booking.status
        if ensure_booking_defaults(booking, now=now):
            summary["bookings_synced"] += 1
        if previous_status != booking.status and booking.status == SpaceBooking.Status.COMPLETED:
            summary["bookings_completed"] += 1
        if previous_status != booking.status and booking.status == SpaceBooking.Status.NO_SHOW:
            summary["bookings_no_show"] += 1

    return summary


def overlapping_allocation_occupancy(facility_space, *, start_date, end_date=None, exclude_id=None) -> int:
    queryset = SpaceAllocation.objects.filter(
        facility_space=facility_space,
        status__in=[
            SpaceAllocation.Status.PENDING,
            SpaceAllocation.Status.ACTIVE,
            SpaceAllocation.Status.ENDING_SOON,
        ],
        start_date__lte=end_date or start_date,
    )
    if end_date is None:
        queryset = queryset.filter(Q(end_date__isnull=True) | Q(end_date__gte=start_date))
    else:
        queryset = queryset.filter(Q(end_date__isnull=True) | Q(end_date__gte=start_date))
    if exclude_id:
        queryset = queryset.exclude(id=exclude_id)
    return queryset.aggregate(total=Sum("occupant_count"))["total"] or 0
