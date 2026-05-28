import logging

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


def _org_admin_users(org):
    from apps.accounts.models import UserProfile

    return [
        p.user
        for p in UserProfile.objects.filter(
            organization=org, role="admin", user__is_active=True
        ).select_related("user")
    ]


# ── 11D: BOQ Change → Auto-recalculate linked blueprints ─────────────


@receiver(post_save, sender="inventory.BOMItem")
def on_bom_item_change_recalculate_blueprints(sender, instance, **kwargs):
    """
    When a BOM item is updated and the org has auto_recalculate_on_boq_change
    enabled, regenerate any linked blueprint's tasks.
    """
    bom = instance.bom
    org = bom.organization

    # Check org setting
    try:
        from apps.settings.models import ProjectGovernanceSettings
        governance = ProjectGovernanceSettings.objects.filter(organization=org).first()
        if not governance or not governance.auto_recalculate_on_boq_change:
            return
    except Exception:
        return

    # Find blueprints linked to this BOM
    from apps.projects.blueprint_models import ProjectBlueprint
    linked_blueprints = ProjectBlueprint.objects.filter(
        source_bom=bom,
        status="draft",  # Only recalculate drafts, not committed ones
    )

    if not linked_blueprints.exists():
        return

    from .boq_planning_engine import generate_blueprint_from_boq
    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification

    for blueprint in linked_blueprints:
        try:
            # Delete existing phases/activities/tasks and regenerate
            blueprint.phases.all().delete()
            new_bp, summary = generate_blueprint_from_boq(bom, user=None)
            # Copy generated phases to existing blueprint instead of creating new
            # Actually, the engine created a new blueprint — move its phases to the original
            from apps.projects.blueprint_models import BlueprintPhase
            BlueprintPhase.objects.filter(blueprint=new_bp).update(blueprint=blueprint)
            new_bp.delete()

            dispatch_workflow_notification(
                organization=org,
                event_key="blueprint_auto_recalculated",
                recipients=_org_admin_users(org),
                context={"blueprint_name": blueprint.name, "bom_name": bom.name},
                link_url=f"/project-planning?blueprint={blueprint.id}",
                fallback_channels=["in_app"],
                fallback_title=f"Blueprint Recalculated — {blueprint.name}",
                fallback_message=(
                    f"Blueprint '{blueprint.name}' has been automatically recalculated "
                    f"because BOM '{bom.name}' was modified. "
                    f"{summary['tasks_created']} tasks regenerated."
                ),
                fallback_category=Notification.Category.PROJECT_UPDATE,
                fallback_severity=Notification.Severity.INFO,
            )
        except Exception:
            logger.debug("Blueprint auto-recalculation failed for %s", blueprint.pk, exc_info=True)


@receiver(post_save, sender="inventory.InventoryTransaction")
def on_inventory_transaction_change_sync_project_costs(sender, instance, **kwargs):
    """Sync material usage transactions into project cost tracking."""
    from apps.finance.cost_tracking_hooks import sync_inventory_material_usage_cost

    sync_inventory_material_usage_cost(instance)


@receiver(post_delete, sender="inventory.InventoryTransaction")
def on_inventory_transaction_delete_remove_project_costs(sender, instance, **kwargs):
    """Remove hook-generated material usage costs when transaction is deleted."""
    from apps.finance.cost_tracking_hooks import delete_inventory_material_usage_cost

    delete_inventory_material_usage_cost(instance)


@receiver(post_save, sender="inventory.InventoryTransaction")
def on_inventory_transaction_notification(sender, instance, created, **kwargs):
    """Notify admins on new inventory transactions."""
    if not created:
        return

    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification

    org = instance.organization
    txn_type = instance.get_transaction_type_display() if hasattr(instance, "get_transaction_type_display") else "Transaction"
    item_name = str(instance.item) if hasattr(instance, "item") and instance.item_id else "Unknown item"
    qty = getattr(instance, "quantity", "")

    dispatch_workflow_notification(
        organization=org,
        event_key="inventory_transaction_created",
        recipients=_org_admin_users(org),
        context={
            "transaction_type": txn_type,
            "item_name": item_name,
            "quantity": str(qty),
            "action_url": "/inventory",
        },
        link_url="/inventory",
        fallback_channels=["in_app"],
        fallback_title=f"Inventory {txn_type} — {item_name}",
        fallback_message=(
            f"An inventory {txn_type.lower()} of {qty} unit(s) has been recorded for {item_name}. "
            f"Stock levels have been updated accordingly."
        ),
        fallback_category=Notification.Category.SYSTEM,
        fallback_severity=Notification.Severity.INFO,
    )


@receiver(post_save, sender="inventory.InventoryStock")
def auto_reorder_requisition(sender, instance, **kwargs):
    """When stock drops below reorder level, auto-create a purchase requisition."""
    from decimal import Decimal as D

    item = instance.item
    if not item.reorder_level or item.reorder_level <= 0:
        return
    if instance.quantity_on_hand >= item.reorder_level:
        return

    # Check functional control
    org = item.organization
    try:
        from apps.settings.models import FunctionalControl
        controls = FunctionalControl.objects.filter(organization=org).first()
        if controls and not controls.procurement_requisitions:
            return
    except Exception:
        pass

    # Avoid duplicate: don't create if there's already an open PR for this item
    from apps.procurement.models import PurchaseRequisition, PurchaseRequisitionItem
    existing = PurchaseRequisitionItem.objects.filter(
        inventory_item=item,
        requisition__organization=org,
        requisition__status__in=("draft", "submitted", "approved"),
    ).exists()
    if existing:
        return

    # Calculate order quantity
    target = item.target_stock_level if item.target_stock_level > 0 else item.reorder_level * 2
    order_qty = max(target - instance.quantity_on_hand, D("1"))

    from django.utils import timezone
    pr = PurchaseRequisition.objects.create(
        organization=org,
        title=f"Auto-Reorder: {item.name}",
        status=PurchaseRequisition.Status.DRAFT,
        source_module=PurchaseRequisition.SourceModule.INVENTORY,
        requester="System (Auto-Reorder)",
        required_date=timezone.localdate() + timezone.timedelta(days=item.lead_time_days or 7),
        priority=PurchaseRequisition.Priority.HIGH,
        justification=f"Stock for '{item.name}' dropped to {instance.quantity_on_hand} (reorder level: {item.reorder_level}).",
    )
    PurchaseRequisitionItem.objects.create(
        requisition=pr,
        inventory_item=item,
        description=item.name,
        quantity=order_qty,
        unit_of_measure=item.unit_of_measure or "ea",
        estimated_unit_price=item.default_unit_cost or D("0"),
    )
    logger.info(f"Auto-reorder PR created: {pr.pr_number} for {item.name} (qty: {order_qty})")


# ── Inter-Project Billing on Material Transfer ────────────────────────


@receiver(pre_save, sender="inventory.MaterialTransfer")
def capture_transfer_previous_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._prev_transfer_status = sender.objects.get(pk=instance.pk).status
        except sender.DoesNotExist:
            instance._prev_transfer_status = None
    else:
        instance._prev_transfer_status = None


@receiver(post_save, sender="inventory.MaterialTransfer")
def on_transfer_received_create_billing(sender, instance, created, **kwargs):
    """
    When a transfer is confirmed (received), create inter-project billing:
    - Credit entry for source project's budget
    - Debit entry for destination project's cost control
    """
    if created:
        return
    prev = getattr(instance, "_prev_transfer_status", None)
    if prev == instance.status:
        return
    if instance.status not in ("received", "partially_received"):
        return

    from decimal import Decimal as D

    # Calculate transfer value
    total_value = D("0")
    for line in instance.lines.all():
        total_value += (line.received_quantity or D("0")) * (line.unit_cost or D("0"))

    if total_value <= 0:
        return

    org = instance.organization
    source_project = None
    dest_project = instance.project

    # Find source project from warehouse
    if instance.source_warehouse.project_id:
        source_project_obj = instance.source_warehouse.project
        source_project = source_project_obj

    # Create cost entries for inter-project billing
    from apps.projects.models import ProjectCostEntry

    # Debit: destination project receives material cost
    if dest_project:
        ProjectCostEntry.objects.create(
            organization=org,
            project=dest_project,
            category="materials",
            description=f"Transfer received from {instance.source_warehouse.name} ({instance.transfer_number})",
            amount=total_value,
            entry_date=instance.confirmed_date or instance.dispatched_date,
            source_reference=f"transfer-in-{instance.transfer_number}",
        )

    # Credit: source project gets budget relief (negative cost entry)
    if source_project:
        ProjectCostEntry.objects.create(
            organization=org,
            project=source_project,
            category="materials",
            description=f"Transfer out to {instance.destination_warehouse.name} ({instance.transfer_number})",
            amount=-total_value,
            entry_date=instance.confirmed_date or instance.dispatched_date,
            source_reference=f"transfer-out-{instance.transfer_number}",
        )

    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification

        dispatch_workflow_notification(
            organization=org,
            event_key="transfer_billing_created",
            recipients=_org_admin_users(org),
            link_url="/material-management/transfers",
            fallback_channels=["in_app"],
            fallback_title=f"Inter-Project Billing — {instance.transfer_number}",
            fallback_message=(
                f"Transfer {instance.transfer_number} confirmed. "
                f"₦{total_value:,.2f} debited to {dest_project.name if dest_project else 'N/A'}"
                + (f", credited to {source_project.name}" if source_project else "")
                + "."
            ),
            fallback_category=Notification.Category.BUDGET_WARNING,
            fallback_severity=Notification.Severity.INFO,
        )
    except Exception:
        logger.debug("Transfer billing notification skipped", exc_info=True)


# ── Material Requisition Approved ─────────────────────────────────────


@receiver(pre_save, sender="inventory.MaterialRequisition")
def capture_requisition_previous_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._prev_req_status = sender.objects.get(pk=instance.pk).status
        except sender.DoesNotExist:
            instance._prev_req_status = None
    else:
        instance._prev_req_status = None


@receiver(post_save, sender="inventory.MaterialRequisition")
def on_material_requisition_approved(sender, instance, created, **kwargs):
    """Notify when a material requisition is approved."""
    if created:
        return
    prev = getattr(instance, "_prev_req_status", None)
    if prev == instance.status or instance.status != "approved":
        return

    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification

        org = instance.organization
        req_number = getattr(instance, "requisition_number", "") or f"MR-{instance.pk}"
        project_name = instance.project.name if hasattr(instance, "project") and instance.project else ""

        dispatch_workflow_notification(
            organization=org,
            event_key="material_requisition_approved",
            recipients=_org_admin_users(org),
            link_url="/material-management/requisitions",
            fallback_channels=["in_app"],
            fallback_title=f"Material Requisition Approved — {req_number}",
            fallback_message=(
                f"Material requisition {req_number} has been approved"
                + (f" for project {project_name}" if project_name else "")
                + ". Items are ready for procurement."
            ),
            fallback_category=Notification.Category.SYSTEM,
            fallback_severity=Notification.Severity.INFO,
        )
    except Exception:
        logger.debug("Material requisition approved notification skipped", exc_info=True)


# ── Stock Transfer Completed ──────────────────────────────────────────


@receiver(post_save, sender="inventory.MaterialTransfer")
def on_transfer_completed(sender, instance, created, **kwargs):
    """Notify when a material transfer is completed."""
    if created:
        return
    prev = getattr(instance, "_prev_transfer_status", None)
    if prev == instance.status or instance.status != "completed":
        return

    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification

        org = instance.organization
        ref = getattr(instance, "transfer_number", "") or f"MT-{instance.pk}"
        source = getattr(instance.source_warehouse, "name", "N/A") if hasattr(instance, "source_warehouse") else "N/A"
        dest = getattr(instance.destination_warehouse, "name", "N/A") if hasattr(instance, "destination_warehouse") else "N/A"

        dispatch_workflow_notification(
            organization=org,
            event_key="material_transfer_completed",
            recipients=_org_admin_users(org),
            link_url="/material-management/transfers",
            fallback_channels=["in_app"],
            fallback_title=f"Stock Transfer Completed — {ref}",
            fallback_message=f"Transfer {ref} from {source} to {dest} has been completed. Stock levels updated.",
            fallback_category=Notification.Category.SYSTEM,
            fallback_severity=Notification.Severity.INFO,
        )
    except Exception:
        logger.debug("Transfer completed notification skipped", exc_info=True)


@receiver(pre_save, sender="inventory.MaterialTransfer")
def capture_transfer_previous_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._prev_transfer_status = sender.objects.get(pk=instance.pk).status
        except sender.DoesNotExist:
            instance._prev_transfer_status = None
    else:
        instance._prev_transfer_status = None
