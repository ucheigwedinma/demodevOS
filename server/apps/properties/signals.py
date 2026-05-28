import logging

from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)

# Status mapping: PropertyInventory → Unit (forward sync)
_INVENTORY_TO_UNIT_STATUS = {
    "available": "available",
    "held": "reserved",  # closest Unit status for a hold
    "reserved": "reserved",
    "sold": "sold",
    "leased": "leased",
    # "unavailable" has no Unit equivalent — skip
}

# Status mapping: Unit → PropertyInventory (reverse sync)
_UNIT_TO_INVENTORY_STATUS = {
    "available": "available",
    "reserved": "reserved",
    "sold": "sold",
    "leased": "leased",
}

# Event type mapping for reverse-sync transitions
_STATUS_EVENT_TYPE = {
    "available": "made_available",
    "reserved": "reserved",
    "sold": "sold",
    "leased": "leased",
}

_syncing = False


@receiver(pre_save, sender="properties.Property")
def capture_property_previous_active_state(sender, instance, **kwargs):
    """Store previous active state so launch detection is precise in post_save."""
    if not instance.pk:
        instance._previous_is_active = None
        return
    from apps.properties.models import Property

    previous = (
        Property.objects.filter(pk=instance.pk)
        .values_list("is_active", flat=True)
        .first()
    )
    instance._previous_is_active = previous


@receiver(post_save, sender="properties.Property")
def trigger_matching_on_property_launch(sender, instance, created, **kwargs):
    """Property launch automation: recompute CRM matches and notify stakeholders."""
    previous = getattr(instance, "_previous_is_active", None)
    launched = (created and instance.is_active) or (previous is False and instance.is_active)
    if not launched:
        return

    def _run():
        from apps.crm.matching import generate_matches_for_property_launch

        generate_matches_for_property_launch(property_obj=instance, actor=None)

    transaction.on_commit(_run)


@receiver(post_save, sender="properties.PropertyInventory")
def sync_inventory_to_unit(sender, instance, **kwargs):
    """Forward sync: PropertyInventory → Unit.status."""
    global _syncing
    if _syncing:
        return

    mapped = _INVENTORY_TO_UNIT_STATUS.get(instance.status)
    if mapped and instance.unit.status != mapped:
        _syncing = True
        try:
            from apps.properties.models import Unit
            Unit.objects.filter(pk=instance.unit_id).update(status=mapped)
        finally:
            _syncing = False


@receiver(post_save, sender="properties.Unit")
def sync_unit_to_inventory(sender, instance, created, **kwargs):
    """
    Reverse sync: Unit.status → PropertyInventory.status.
    Handles CRM writes that set unit.status directly.
    Also auto-creates PropertyInventory for new units.
    """
    global _syncing
    if _syncing:
        return

    from apps.properties.models import PropertyInventory, PropertyInventoryEvent

    _syncing = True
    try:
        if created:
            PropertyInventory.objects.get_or_create(
                unit=instance,
                defaults={
                    "organization_id": instance.organization_id,
                    "status": instance.status,
                    "list_price": instance.asking_price,
                },
            )
            return

        # Update existing inventory if status diverged
        try:
            inv = instance.inventory
        except PropertyInventory.DoesNotExist:
            inv = PropertyInventory.objects.create(
                organization_id=instance.organization_id,
                unit=instance,
                status=instance.status,
                list_price=instance.asking_price,
            )
            return

        mapped = _UNIT_TO_INVENTORY_STATUS.get(instance.status)
        if mapped and inv.status != mapped:
            old_status = inv.status
            inv.status = mapped
            inv.save(update_fields=["status", "updated_at"])

            event_type = _STATUS_EVENT_TYPE.get(mapped, "made_available")
            PropertyInventoryEvent.objects.create(
                organization_id=instance.organization_id,
                inventory=inv,
                event_type=event_type,
                from_status=old_status,
                to_status=mapped,
                actor_name="System",
                notes="Status synced from unit update",
            )
    finally:
        _syncing = False


# ---------------------------------------------------------------------------
# Notification signals (fire after sync signals)
# ---------------------------------------------------------------------------

_INVENTORY_EVENT_MAP = {
    "held": "properties_unit_held",
    "available": "properties_unit_released",
    "sold": "properties_unit_sold_leased",
    "leased": "properties_unit_sold_leased",
}


def _org_admin_users(org):
    from apps.accounts.models import UserProfile

    return [
        p.user
        for p in UserProfile.objects.filter(
            organization=org,
            role="admin",
            user__is_active=True,
        ).select_related("user")
    ]


@receiver(post_save, sender="properties.PropertyInventory")
def on_inventory_notification(sender, instance, created, **kwargs):
    """Dispatch notifications on inventory status changes."""
    if created:
        return

    event_key = _INVENTORY_EVENT_MAP.get(instance.status)
    if not event_key:
        return

    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification, resolve_raci_recipients

    org = instance.organization
    unit = instance.unit

    raci = resolve_raci_recipients(
        organization=org,
        process_key="properties.inventory",
        fallback_users=_org_admin_users(org),
    )

    unit_number = getattr(unit, "unit_number", str(unit))
    property_name = str(unit.property) if unit.property_id else ""

    category = Notification.Category.PROPERTY_STATUS
    severity = Notification.Severity.INFO
    if instance.status in ("sold", "leased"):
        severity = Notification.Severity.WARNING

    dispatch_workflow_notification(
        organization=org,
        event_key=event_key,
        recipients=raci.all,
        context={
            "unit_number": unit_number,
            "property_name": property_name,
            "held_by": instance.held_by or "",
            "new_status": instance.get_status_display() if hasattr(instance, "get_status_display") else instance.status,
            "allocated_to": instance.allocated_to or "",
            "action_url": f"/units/{unit.id}",
        },
        link_url=f"/units/{unit.id}",
        fallback_channels=["in_app"],
        fallback_title=f"Unit Status Updated — {unit_number}",
        fallback_message=(
            f"Unit {unit_number}"
            + (f" at {property_name}" if property_name else "")
            + f" has been updated to {instance.status}."
            + (" The unit is now reserved and removed from available inventory." if instance.status in ("held", "reserved") else "")
            + (" The unit has been released and is now available." if instance.status == "available" else "")
        ),
        fallback_category=category,
        fallback_severity=severity,
    )


@receiver(post_save, sender="properties.WorkOrder")
def on_work_order_notification(sender, instance, created, **kwargs):
    """Alert maintenance team when a high-priority work order is created."""
    if not created:
        return

    priority = getattr(instance, "priority", "")
    if priority not in ("high", "urgent", "critical"):
        return

    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification, resolve_raci_recipients

    org = instance.organization

    raci = resolve_raci_recipients(
        organization=org,
        process_key="properties.maintenance",
        fallback_users=_org_admin_users(org),
    )

    property_name = ""
    if hasattr(instance, "property") and instance.property_id:
        property_name = str(instance.property)

    dispatch_workflow_notification(
        organization=org,
        event_key="properties_work_order_created",
        recipients=raci.all,
        context={
            "work_order_number": getattr(instance, "wo_number", str(instance.pk)),
            "property_name": property_name,
            "priority": priority,
            "description": getattr(instance, "description", "")[:200],
            "action_url": f"/properties/maintenance/work-orders/{instance.id}",
        },
        link_url=f"/properties/maintenance/work-orders/{instance.id}",
        fallback_channels=["in_app", "email"],
        fallback_title=f"High-Priority Work Order Created — {getattr(instance, 'wo_number', instance.pk)}",
        fallback_message=(
            f"A {priority}-priority work order ({getattr(instance, 'wo_number', instance.pk)}) "
            f"has been created"
            + (f" for {property_name}" if property_name else "")
            + ". Immediate attention is required. Please assign a technician and begin resolution."
        ),
        fallback_category=Notification.Category.PROPERTY_MAINT,
        fallback_severity=Notification.Severity.WARNING,
    )


@receiver(post_save, sender="properties.WorkOrder")
def sync_work_order_follow_on_automation(sender, instance, **kwargs):
    """Advance linked schedules and close predictive alerts after work order progress."""

    def _run():
        from apps.properties.maintenance_workflows import sync_follow_on_workflows_for_work_order

        try:
            sync_follow_on_workflows_for_work_order(instance.id)
        except Exception:  # pragma: no cover - keep save path resilient
            logger.exception("Work order workflow sync failed for work order %s", instance.id)

    transaction.on_commit(_run)


@receiver(post_save, sender="properties.AssetComponent")
def sync_asset_workflows_on_save(sender, instance, **kwargs):
    """Keep auto-maintenance and depreciation sync aligned with asset config."""

    def _run():
        from apps.properties.asset_workflows import sync_asset_workflows

        try:
            sync_asset_workflows(instance.id)
        except Exception:  # pragma: no cover - keep save path resilient
            logger.exception("Asset workflow sync failed for asset %s", instance.id)

    transaction.on_commit(_run)
