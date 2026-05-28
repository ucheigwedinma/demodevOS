import logging
from decimal import Decimal

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


def _org_admin_users(org):
    """Return active admin users for the given organization."""
    from apps.accounts.models import UserProfile

    return [
        p.user
        for p in UserProfile.objects.filter(
            organization=org,
            role="admin",
            user__is_active=True,
        ).select_related("user")
    ]


@receiver(post_save, sender="procurement.PurchaseRequisition")
def on_pr_submitted(sender, instance, created, **kwargs):
    """Notify approvers when a purchase requisition is submitted."""
    if not created:
        return

    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification, resolve_raci_recipients

    org = instance.organization

    raci = resolve_raci_recipients(
        organization=org,
        process_key="procurement.approval",
        fallback_users=_org_admin_users(org),
    )

    dispatch_workflow_notification(
        organization=org,
        event_key="procurement_pr_submitted",
        recipients=raci.all,
        context={
            "pr_number": instance.pr_number,
            "requester": instance.requester,
            "total_amount": str(instance.estimated_total or ""),
            "action_url": f"/procurement/requisitions/{instance.id}",
        },
        link_url=f"/procurement/requisitions/{instance.id}",
        fallback_channels=["in_app", "email"],
        fallback_title=f"Purchase Requisition Submitted — {instance.pr_number}",
        fallback_message=(
            f"Purchase requisition {instance.pr_number} has been submitted by {instance.requester}"
            + (f" totalling ₦{instance.estimated_total:,.2f}" if instance.estimated_total else "")
            + ". It is now pending approval before a purchase order can be raised."
        ),
        fallback_category=Notification.Category.PROCUREMENT_ORDER,
        fallback_severity=Notification.Severity.INFO,
    )


@receiver(post_save, sender="procurement.PurchaseOrder")
def on_po_status_change(sender, instance, created, **kwargs):
    """Notify stakeholders when a PO is approved or rejected."""
    if created:
        return

    update_fields = kwargs.get("update_fields")
    if update_fields and "status" not in update_fields:
        return

    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification, resolve_raci_recipients

    org = instance.organization

    if instance.status == "approved":
        raci = resolve_raci_recipients(
            organization=org,
            process_key="procurement.approval",
            fallback_users=_org_admin_users(org),
        )
        recipients = raci.all
        dispatch_workflow_notification(
            organization=org,
            event_key="procurement_po_approved",
            recipients=recipients,
            context={
                "po_number": instance.po_number,
                "vendor_name": str(instance.vendor) if instance.vendor_id else "",
                "total_amount": str(instance.total_amount or ""),
                "action_url": f"/procurement/purchase-orders/{instance.id}",
            },
            link_url=f"/procurement/purchase-orders/{instance.id}",
            fallback_channels=["in_app", "email"],
            fallback_title=f"Purchase Order Approved — {instance.po_number}",
            fallback_message=(
                f"Purchase order {instance.po_number} has been approved"
                + (f" for {instance.vendor}" if instance.vendor_id else "")
                + (f" totalling ₦{instance.total_amount:,.2f}" if instance.total_amount else "")
                + ". The vendor can now be notified and delivery scheduling may proceed."
            ),
            fallback_category=Notification.Category.PROCUREMENT_ORDER,
            fallback_severity=Notification.Severity.INFO,
        )

    elif instance.status in ("rejected", "cancelled"):
        recipients = list(_org_admin_users(org))
        if recipients:
            dispatch_workflow_notification(
                organization=org,
                event_key="procurement_po_rejected",
                recipients=recipients,
                context={
                    "po_number": instance.po_number,
                    "vendor_name": str(instance.vendor) if instance.vendor_id else "",
                    "action_url": f"/procurement/purchase-orders/{instance.id}",
                },
                link_url=f"/procurement/purchase-orders/{instance.id}",
                fallback_channels=["in_app"],
                fallback_title=f"Purchase Order Rejected — {instance.po_number}",
                fallback_message=(
                    f"Purchase order {instance.po_number}"
                    + (f" for {instance.vendor}" if instance.vendor_id else "")
                    + " has been rejected. Please review the feedback and resubmit with corrections if applicable."
                ),
                fallback_category=Notification.Category.PROCUREMENT_ORDER,
                fallback_severity=Notification.Severity.WARNING,
            )


@receiver(post_save, sender="procurement.PurchaseOrder")
def sync_po_cost_tracking_hook(sender, instance, **kwargs):
    """Sync project cost tracking when purchase order values change."""
    from apps.finance.cost_tracking_hooks import sync_procurement_purchase_order_cost

    sync_procurement_purchase_order_cost(instance)


@receiver(post_delete, sender="procurement.PurchaseOrder")
def delete_po_cost_tracking_hook(sender, instance, **kwargs):
    """Remove hook-generated project cost tracking when PO is deleted."""
    from apps.finance.cost_tracking_hooks import delete_procurement_purchase_order_cost

    delete_procurement_purchase_order_cost(instance)


@receiver(post_save, sender="procurement.PurchaseOrder")
def sync_po_site_mobilization_hook(sender, instance, **kwargs):
    """Sync project site mobilization when PO contractor context changes."""
    from apps.projects.site_mobilization import sync_site_mobilization_from_purchase_order

    sync_site_mobilization_from_purchase_order(instance)


@receiver(post_delete, sender="procurement.PurchaseOrder")
def delete_po_site_mobilization_hook(sender, instance, **kwargs):
    """Resync project site mobilization when PO is deleted."""
    from apps.projects.site_mobilization import sync_site_mobilization_from_purchase_order

    sync_site_mobilization_from_purchase_order(instance)


@receiver(post_save, sender="procurement.GoodsReceipt")
def on_grn_created(sender, instance, created, **kwargs):
    """Notify procurement and finance when goods are received."""
    if not created:
        return

    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification, resolve_raci_recipients

    org = instance.organization

    raci = resolve_raci_recipients(
        organization=org,
        process_key="procurement.receiving",
        fallback_users=_org_admin_users(org),
    )

    po_number = ""
    if instance.purchase_order_id:
        po_number = instance.purchase_order.po_number

    dispatch_workflow_notification(
        organization=org,
        event_key="procurement_grn_received",
        recipients=raci.all,
        context={
            "grn_number": instance.grn_number,
            "po_number": po_number,
            "vendor_name": str(instance.vendor) if hasattr(instance, "vendor") and instance.vendor_id else "",
            "action_url": f"/procurement/goods-receipts/{instance.id}",
        },
        link_url=f"/procurement/goods-receipts/{instance.id}",
        fallback_channels=["in_app"],
        fallback_title=f"Goods Receipt Logged — {instance.grn_number}",
        fallback_message=(
            f"Goods receipt {instance.grn_number} has been logged"
            + (f" against purchase order {po_number}" if po_number else "")
            + ". Received items have been recorded and inventory levels updated. "
            + "Please verify quantities and quality before confirming acceptance."
        ),
        fallback_category=Notification.Category.PROCUREMENT_GRN,
        fallback_severity=Notification.Severity.INFO,
    )


@receiver(post_save, sender="procurement.GoodsReceipt")
def sync_grn_site_mobilization_hook(sender, instance, **kwargs):
    """Sync project site mobilization when material receipts change."""
    from apps.projects.site_mobilization import sync_site_mobilization_from_goods_receipt

    sync_site_mobilization_from_goods_receipt(instance)


@receiver(post_delete, sender="procurement.GoodsReceipt")
def delete_grn_site_mobilization_hook(sender, instance, **kwargs):
    """Resync project site mobilization when a goods receipt is deleted."""
    from apps.projects.site_mobilization import sync_site_mobilization_from_goods_receipt

    sync_site_mobilization_from_goods_receipt(instance)


# ═══════════════════════════════════════════════════════════════════════
# GROUP C — PROCUREMENT AUTOMATION
# ═══════════════════════════════════════════════════════════════════════


# ── 16. PR Approval → RFQ Generation ─────────────────────────────────


@receiver(pre_save, sender="procurement.PurchaseRequisition")
def capture_pr_previous_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._prev_pr_status = sender.objects.get(pk=instance.pk).status
        except sender.DoesNotExist:
            instance._prev_pr_status = None
    else:
        instance._prev_pr_status = None


@receiver(post_save, sender="procurement.PurchaseRequisition")
def on_pr_approved_create_rfq(sender, instance, created, **kwargs):
    """When a PR is approved, auto-create an RFQ linked to it."""
    if created:
        return
    prev = getattr(instance, "_prev_pr_status", None)
    if prev == instance.status or instance.status != "approved":
        return

    from .models import RequestForQuotation
    from django.utils import timezone as tz

    # Don't duplicate — check if an RFQ already exists for this PR
    if RequestForQuotation.objects.filter(requisition=instance).exists():
        return

    org = instance.organization
    rfq = RequestForQuotation.objects.create(
        organization=org,
        title=f"RFQ — {instance.title}",
        status="draft",
        requisition=instance,
        project=instance.project,
        property=instance.property,
        issue_date=tz.localdate(),
        submission_deadline=instance.required_date,
        estimated_value=instance.estimated_total or Decimal("0"),
        budget_code=instance.budget_code,
        cost_code=instance.cost_code,
    )

    # Update PR status to rfq_issued if that status exists
    if hasattr(instance, "Status") and hasattr(instance.Status, "RFQ_ISSUED"):
        instance.status = "rfq_issued"
        instance.save(update_fields=["status", "updated_at"])

    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification

        dispatch_workflow_notification(
            organization=org,
            event_key="pr_approved_rfq_created",
            recipients=_org_admin_users(org),
            link_url="/procurement/rfqs",
            fallback_channels=["in_app"],
            fallback_title=f"RFQ Auto-Created — {rfq.rfq_number}",
            fallback_message=(
                f"Purchase requisition '{instance.pr_number}' has been approved. "
                f"RFQ '{rfq.rfq_number}' has been automatically created. "
                f"Estimated value: ₦{instance.estimated_total:,.2f}. "
                f"Please invite vendors and issue the RFQ."
            ),
            fallback_category=Notification.Category.PROCUREMENT_ORDER,
            fallback_severity=Notification.Severity.INFO,
        )
    except Exception:
        logger.debug("PR→RFQ notification skipped", exc_info=True)


# ── 18. Vendor Selection → PO Creation ───────────────────────────────


@receiver(pre_save, sender="procurement.RequestForQuotation")
def capture_rfq_previous_vendor(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            instance._prev_selected_vendor = old.selected_vendor_id
        except sender.DoesNotExist:
            instance._prev_selected_vendor = None
    else:
        instance._prev_selected_vendor = None


@receiver(post_save, sender="procurement.RequestForQuotation")
def on_vendor_selected_create_po(sender, instance, created, **kwargs):
    """When a vendor is selected on an RFQ, auto-create a draft PO."""
    if created:
        return
    prev_vendor = getattr(instance, "_prev_selected_vendor", None)
    if not instance.selected_vendor_id or instance.selected_vendor_id == prev_vendor:
        return

    from .models import PurchaseOrder, PurchaseOrderItem
    from django.utils import timezone as tz

    # Don't duplicate — check if a PO already exists for this RFQ's requisition + vendor
    existing = PurchaseOrder.objects.filter(
        requisition=instance.requisition,
        vendor=instance.selected_vendor,
    ).exists() if instance.requisition_id else False

    if existing:
        return

    org = instance.organization

    # Get the winning quote amount
    winning_quote = instance.quotes.filter(status="winner").first()
    quote_amount = winning_quote.quoted_amount if winning_quote else instance.estimated_value

    po = PurchaseOrder.objects.create(
        organization=org,
        requisition=instance.requisition,
        vendor=instance.selected_vendor,
        project=instance.project,
        property=instance.property,
        status="draft",
        issue_date=tz.localdate(),
        expected_delivery_date=instance.submission_deadline,
        total_amount=quote_amount or Decimal("0"),
        notes=f"Auto-generated from RFQ {instance.rfq_number}. Vendor: {instance.selected_vendor.name}.",
    )

    # Copy PR items to PO items if requisition exists
    if instance.requisition_id:
        for pr_item in instance.requisition.items.all():
            unit_price = pr_item.estimated_unit_price
            # Use quote pricing if available
            if winning_quote and pr_item.estimated_unit_price:
                ratio = float(quote_amount or 0) / float(instance.estimated_value or 1) if instance.estimated_value else 1
                unit_price = pr_item.estimated_unit_price * Decimal(str(ratio))

            PurchaseOrderItem.objects.create(
                purchase_order=po,
                description=pr_item.description,
                quantity=pr_item.quantity,
                unit_of_measure=pr_item.unit_of_measure,
                unit_price=unit_price,
                sort_order=pr_item.sort_order,
            )
        po.recalculate_totals()

    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification

        dispatch_workflow_notification(
            organization=org,
            event_key="vendor_selected_po_created",
            recipients=_org_admin_users(org),
            link_url=f"/procurement/purchase-orders/{po.id}",
            fallback_channels=["in_app"],
            fallback_title=f"PO Auto-Created — {po.po_number}",
            fallback_message=(
                f"Vendor '{instance.selected_vendor.name}' selected on RFQ '{instance.rfq_number}'. "
                f"Purchase Order '{po.po_number}' has been auto-created as draft. "
                f"Amount: ₦{po.total_amount:,.2f}. Please review and approve."
            ),
            fallback_category=Notification.Category.PROCUREMENT_ORDER,
            fallback_severity=Notification.Severity.INFO,
        )
    except Exception:
        logger.debug("Vendor→PO notification skipped", exc_info=True)


# ── 19. PO Approval → Budget Commitment ──────────────────────────────


@receiver(pre_save, sender="procurement.PurchaseOrder")
def capture_po_previous_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._prev_po_status = sender.objects.get(pk=instance.pk).status
        except sender.DoesNotExist:
            instance._prev_po_status = None
    else:
        instance._prev_po_status = None


@receiver(post_save, sender="procurement.PurchaseOrder")
def on_po_approved_commit_budget(sender, instance, created, **kwargs):
    """When a PO is approved, deduct from project budget allocation."""
    if created:
        return
    prev = getattr(instance, "_prev_po_status", None)
    if prev == instance.status or instance.status != "approved":
        return

    if not instance.project_id or not instance.total_amount:
        return

    org = instance.organization
    project = instance.project

    # Update project budget committed amount
    from django.db.models import Sum
    total_committed = PurchaseOrder.objects.filter(
        project=project,
        status__in=["approved", "issued", "partially_received"],
    ).aggregate(total=Sum("total_amount"))["total"] or Decimal("0")

    # Update the project's budget field if committed exceeds a threshold
    budget = project.budget or Decimal("0")
    if budget > 0:
        pct = float(total_committed / budget * 100)
        severity = "info"
        if pct > 90:
            severity = "critical"
        elif pct > 75:
            severity = "warning"

        try:
            from apps.notifications.models import Notification
            from apps.notifications.services import dispatch_workflow_notification

            dispatch_workflow_notification(
                organization=org,
                event_key="po_budget_commitment",
                recipients=_org_admin_users(org),
                link_url=f"/projects/{project.id}",
                fallback_channels=["in_app"],
                fallback_title=f"Budget Commitment — {instance.po_number}",
                fallback_message=(
                    f"PO '{instance.po_number}' approved for ₦{instance.total_amount:,.2f}. "
                    f"Total committed: ₦{total_committed:,.2f} of ₦{budget:,.2f} budget ({pct:.0f}%). "
                    f"Project: '{project.name}'."
                ),
                fallback_category=Notification.Category.PROCUREMENT_ORDER,
                fallback_severity=getattr(Notification.Severity, severity.upper(), Notification.Severity.INFO),
            )
        except Exception:
            logger.debug("PO budget commitment notification skipped", exc_info=True)


# ── 21. Delivery Confirmation → Invoice Matching (3-Way Match) ───────


@receiver(post_save, sender="finance.Bill")
def on_bill_created_three_way_match(sender, instance, created, **kwargs):
    """
    When a bill is created/updated with a PO link, perform 3-way match:
    PO amount vs GRN received value vs Invoice amount.
    Persists result to ThreeWayMatchResult and updates match_status on Bill + PO.
    """
    if not instance.purchase_order_id:
        return

    po = instance.purchase_order
    org = instance.organization

    # Check if 3-way matching is enabled
    tolerance_pct = Decimal("5.00")
    try:
        from apps.settings.models import FunctionalControl
        controls = FunctionalControl.objects.filter(organization=org).first()
        if controls:
            if not controls.three_way_match_enabled:
                return
            tolerance_pct = controls.three_way_match_tolerance_pct
    except Exception:
        pass

    from .models import GoodsReceipt, ThreeWayMatchResult

    # Gather amounts
    po_amount = po.total_amount or Decimal("0")
    invoice_amount = instance.total_amount or Decimal("0")

    grns = GoodsReceipt.objects.filter(purchase_order=po)
    grn_total = Decimal("0")
    for grn in grns:
        for item in grn.items.all():
            grn_total += (item.quantity_received or Decimal("0")) * (item.po_item.unit_price or Decimal("0"))

    # Calculate variances
    po_inv_var = Decimal("0")
    grn_inv_var = Decimal("0")
    if po_amount > 0:
        po_inv_var = abs(invoice_amount - po_amount) / po_amount * 100
    if grn_total > 0:
        grn_inv_var = abs(invoice_amount - grn_total) / grn_total * 100

    # Determine match status
    issues = []
    match_status = "full_match"

    if not grns.exists():
        issues.append("No goods receipt found — invoice before delivery")
        match_status = "no_grn"
    else:
        if po_amount > 0 and po_inv_var > tolerance_pct:
            issues.append(f"PO vs Invoice variance: {po_inv_var:.1f}% (tolerance: {tolerance_pct}%)")
            match_status = "variance"
        if grn_total > 0 and grn_inv_var > tolerance_pct:
            issues.append(f"GRN vs Invoice variance: {grn_inv_var:.1f}% (tolerance: {tolerance_pct}%)")
            match_status = "variance"

    if not issues and grns.exists():
        # Check line-item level if possible
        if po_amount > 0 and po_inv_var > 0 and po_inv_var <= tolerance_pct:
            match_status = "partial_match"
        else:
            match_status = "full_match"

    # Build line-item match detail
    line_matches = []
    for po_item in po.items.all():
        grn_qty = sum(
            ri.quantity_accepted for ri in po_item.receipt_items.all()
        )
        bill_lines = po_item.bill_line_items.all() if hasattr(po_item, "bill_line_items") else []
        bill_qty = sum(bl.quantity for bl in bill_lines)
        bill_amt = sum(bl.amount for bl in bill_lines)
        line_matches.append({
            "po_item_id": po_item.id,
            "description": po_item.description,
            "po_qty": str(po_item.quantity),
            "po_amount": str(po_item.amount),
            "grn_qty": str(grn_qty),
            "bill_qty": str(bill_qty),
            "bill_amount": str(bill_amt),
            "status": "match" if grn_qty == po_item.quantity and bill_qty == po_item.quantity else "variance",
        })

    # Persist result
    match_record, _ = ThreeWayMatchResult.objects.update_or_create(
        organization=org,
        purchase_order=po,
        bill=instance,
        defaults={
            "match_status": match_status,
            "po_total": po_amount,
            "grn_total": grn_total,
            "invoice_total": invoice_amount,
            "po_invoice_variance_pct": po_inv_var,
            "grn_invoice_variance_pct": grn_inv_var,
            "tolerance_pct": tolerance_pct,
            "issues": issues,
            "line_item_matches": line_matches,
        },
    )

    # Update match_status on Bill and PO
    if instance.match_status != match_status:
        instance.match_status = match_status
        instance.save(update_fields=["match_status", "updated_at"])
    if po.match_status != match_status:
        po.match_status = match_status
        po.save(update_fields=["match_status", "updated_at"])

    # Notifications
    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification

        if issues:
            dispatch_workflow_notification(
                organization=org,
                event_key="invoice_match_variance",
                recipients=_org_admin_users(org),
                link_url=f"/procurement/purchase-orders/{po.id}",
                fallback_channels=["in_app"],
                fallback_title=f"Invoice Match Issue — {instance.bill_number}",
                fallback_message=(
                    f"3-way match for bill '{instance.bill_number}' (PO: {po.po_number}) found issues: "
                    + "; ".join(issues)
                    + ". Please review before approving payment."
                ),
                fallback_category=Notification.Category.PROCUREMENT_ORDER,
                fallback_severity=Notification.Severity.WARNING,
            )
        else:
            dispatch_workflow_notification(
                organization=org,
                event_key="invoice_match_success",
                recipients=_org_admin_users(org),
                link_url=f"/finance/bills",
                fallback_channels=["in_app"],
                fallback_title=f"Invoice Matched — {instance.bill_number}",
                fallback_message=(
                    f"3-way match for bill '{instance.bill_number}' (PO: {po.po_number}) passed. "
                    f"PO: ₦{po_amount:,.2f}, GRN: ₦{grn_total:,.2f}, Invoice: ₦{invoice_amount:,.2f}. "
                    f"Invoice is ready for payment approval."
                ),
                fallback_category=Notification.Category.PROCUREMENT_ORDER,
                fallback_severity=Notification.Severity.INFO,
            )
    except Exception:
        logger.debug("Invoice match notification skipped", exc_info=True)


# ── GRN Downstream Signals ───────────────────────────────────────────


@receiver(post_save, sender="procurement.GoodsReceiptItem")
def grn_item_downstream_updates(sender, instance, created, **kwargs):
    """When a GRN item is saved, trigger all downstream updates."""
    if not created:
        return

    grn = instance.goods_receipt
    po = grn.purchase_order
    po_item = instance.po_item

    # 1. Auto-update PO status from receipts
    try:
        po.update_status_from_receipts()
    except Exception:
        logger.debug("PO status update from GRN failed", exc_info=True)

    # 2. Update Inventory stock (quantity_on_hand)
    try:
        if po_item.bom_item and po_item.bom_item.inventory_item:
            inv_item = po_item.bom_item.inventory_item
            from apps.inventory.models import InventoryStock
            # Find or create stock record for the item's default warehouse
            stock = InventoryStock.objects.filter(item=inv_item).first()
            if stock:
                stock.quantity_on_hand += instance.quantity_accepted
                stock.save(update_fields=["quantity_on_hand"])
                logger.info(
                    f"GRN {grn.grn_number}: Updated stock for {inv_item.name} "
                    f"(+{instance.quantity_accepted})"
                )
    except Exception:
        logger.debug("Inventory stock update from GRN failed", exc_info=True)

    # 3. Update BoqTaskMapping consumed_quantity (construction progress)
    try:
        if po_item.bom_item and po:
            from apps.inventory.models import BoqTaskMapping
            mappings = BoqTaskMapping.objects.filter(
                bom_item=po_item.bom_item,
                project=po.project,
            )
            for mapping in mappings:
                mapping.sync_consumed_quantity()
    except Exception:
        logger.debug("Construction progress update from GRN failed", exc_info=True)


@receiver(post_save, sender="procurement.GoodsReceipt")
def grn_auto_set_po_status(sender, instance, **kwargs):
    """Fallback: when a GRN is saved (e.g. status change), re-sync PO status."""
    try:
        instance.purchase_order.update_status_from_receipts()
    except Exception:
        logger.debug("PO status sync from GRN save failed", exc_info=True)


# ═══════════════════════════════════════════════════════════════════════
# CONTRACT NOTIFICATIONS
# ═══════════════════════════════════════════════════════════════════════


@receiver(pre_save, sender="procurement.Contract")
def capture_contract_previous_status(sender, instance, **kwargs):
    """Capture previous contract status for change detection."""
    if instance.pk:
        try:
            instance._prev_contract_status = sender.objects.get(pk=instance.pk).status
        except sender.DoesNotExist:
            instance._prev_contract_status = None
    else:
        instance._prev_contract_status = None


@receiver(post_save, sender="procurement.Contract")
def on_contract_status_change(sender, instance, created, **kwargs):
    """Notify admins when a contract is executed or expires."""
    if created:
        return

    prev = getattr(instance, "_prev_contract_status", None)
    if prev == instance.status:
        return
    if instance.status not in ("executed", "expired"):
        return

    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification

        org = instance.organization

        if instance.status == "executed":
            title = f"Contract Executed — {instance.contract_number}"
            message = (
                f"Contract '{instance.contract_number}' ({instance.title}) with "
                f"{instance.vendor} has been executed and is now active."
            )
            severity = Notification.Severity.INFO
        else:
            title = f"Contract Expired — {instance.contract_number}"
            message = (
                f"Contract '{instance.contract_number}' ({instance.title}) with "
                f"{instance.vendor} has expired. Please review for renewal or closure."
            )
            severity = Notification.Severity.WARNING

        dispatch_workflow_notification(
            organization=org,
            event_key="contract_status_change",
            recipients=_org_admin_users(org),
            link_url="/procurement/contracts",
            fallback_channels=["in_app"],
            fallback_title=title,
            fallback_message=message,
            fallback_category=Notification.Category.PROCUREMENT_ORDER,
            fallback_severity=severity,
        )
    except Exception:
        logger.debug("Contract status change notification skipped", exc_info=True)
