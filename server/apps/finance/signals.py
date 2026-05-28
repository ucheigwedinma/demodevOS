import logging

from decimal import Decimal

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.accounts.models import Organization

logger = logging.getLogger(__name__)


def _org_admin_users(org):
    from apps.accounts.models import UserProfile

    return [
        p.user
        for p in UserProfile.objects.filter(
            organization=org, role="admin", user__is_active=True
        ).select_related("user")
    ]


@receiver(post_save, sender=Organization)
def create_default_accounts(sender, instance, created, **kwargs):
    """Seed the default chart of accounts when a new organization is created."""
    if created:
        from .seed_defaults import seed_accounts_for_org

        seed_accounts_for_org(instance)


@receiver(post_save, sender="finance.BillLineItem")
def on_bill_line_item_save(sender, instance, **kwargs):
    """Check budget thresholds when a bill line item is coded to a GL account."""
    if instance.account_id:
        from .budget_utils import check_budget_thresholds

        check_budget_thresholds(instance)


# ---------------------------------------------------------------------------
# Bill notifications
# ---------------------------------------------------------------------------

@receiver(post_save, sender="finance.Bill")
def on_bill_created(sender, instance, created, **kwargs):
    """Notify admins when a new bill is created."""
    if not created:
        return
    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification

    org = instance.organization
    vendor_name = str(instance.vendor) if instance.vendor_id else "Unknown"
    dispatch_workflow_notification(
        organization=org,
        event_key="finance_bill_created",
        recipients=_org_admin_users(org),
        context={
            "bill_number": getattr(instance, "bill_number", str(instance.pk)),
            "vendor_name": vendor_name,
            "total_amount": str(instance.total_amount or ""),
            "action_url": f"/finance/bills/{instance.id}",
        },
        link_url=f"/finance/bills/{instance.id}",
        fallback_channels=["in_app"],
        fallback_title=f"New Bill Received — {vendor_name}",
        fallback_message=(
            f"A new bill has been received from {vendor_name}"
            f"{f' (₦{instance.total_amount:,.2f})' if instance.total_amount else ''}. "
            f"It is pending review and approval."
        ),
        fallback_category=Notification.Category.BUDGET_WARNING,
        fallback_severity=Notification.Severity.INFO,
    )


@receiver(post_save, sender="finance.Bill")
def on_bill_status_changed(sender, instance, created, **kwargs):
    """Notify admins when a bill status changes."""
    if created:
        return
    update_fields = kwargs.get("update_fields")
    if update_fields and "status" not in update_fields:
        return

    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification

    org = instance.organization
    status_label = instance.get_status_display()
    vendor_name = str(instance.vendor) if instance.vendor_id else "Unknown"
    dispatch_workflow_notification(
        organization=org,
        event_key="finance_bill_status_changed",
        recipients=_org_admin_users(org),
        context={
            "bill_number": getattr(instance, "bill_number", str(instance.pk)),
            "vendor_name": vendor_name,
            "new_status": status_label,
            "action_url": f"/finance/bills/{instance.id}",
        },
        link_url=f"/finance/bills/{instance.id}",
        fallback_channels=["in_app"],
        fallback_title=f"Bill Status Updated — {status_label}",
        fallback_message=(
            f"The bill from {vendor_name} has been marked as {status_label}. "
            f"{'Payment can now be scheduled.' if status_label.lower() == 'approved' else 'Please review for next steps.'}"
        ),
        fallback_category=Notification.Category.BUDGET_WARNING,
        fallback_severity=Notification.Severity.INFO,
    )


# ---------------------------------------------------------------------------
# Invoice notifications
# ---------------------------------------------------------------------------

@receiver(post_save, sender="finance.Invoice")
def on_invoice_created(sender, instance, created, **kwargs):
    """Notify admins when a new invoice is created."""
    if not created:
        return
    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification

    org = instance.organization
    customer_name = str(instance.customer) if instance.customer_id else "Unknown"
    dispatch_workflow_notification(
        organization=org,
        event_key="finance_invoice_created",
        recipients=_org_admin_users(org),
        context={
            "invoice_number": getattr(instance, "invoice_number", str(instance.pk)),
            "customer_name": customer_name,
            "total_amount": str(instance.total_amount or ""),
            "action_url": f"/finance/invoices/{instance.id}",
        },
        link_url=f"/finance/invoices/{instance.id}",
        fallback_channels=["in_app"],
        fallback_title=f"New Invoice Created — {customer_name}",
        fallback_message=(
            f"Invoice #{getattr(instance, 'invoice_number', instance.pk)} has been created for {customer_name}"
            f"{f' totalling ₦{instance.total_amount:,.2f}' if instance.total_amount else ''}. "
            f"It is ready to be reviewed and sent to the customer."
        ),
        fallback_category=Notification.Category.BUDGET_WARNING,
        fallback_severity=Notification.Severity.INFO,
    )


@receiver(post_save, sender="finance.Invoice")
def on_invoice_status_changed(sender, instance, created, **kwargs):
    """Notify admins when an invoice status changes."""
    if created:
        return
    update_fields = kwargs.get("update_fields")
    if update_fields and "status" not in update_fields:
        return

    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification

    org = instance.organization
    status_label = instance.get_status_display()
    customer_name = str(instance.customer) if instance.customer_id else "Unknown"
    dispatch_workflow_notification(
        organization=org,
        event_key="finance_invoice_status_changed",
        recipients=_org_admin_users(org),
        context={
            "invoice_number": getattr(instance, "invoice_number", str(instance.pk)),
            "customer_name": customer_name,
            "new_status": status_label,
            "action_url": f"/finance/invoices/{instance.id}",
        },
        link_url=f"/finance/invoices/{instance.id}",
        fallback_channels=["in_app"],
        fallback_title=f"Invoice Status Updated — {status_label}",
        fallback_message=(
            f"Invoice #{getattr(instance, 'invoice_number', instance.pk)} for {customer_name} "
            f"has been updated to {status_label}."
            f"{'Payment has been received.' if status_label.lower() == 'paid' else ''}"
        ),
        fallback_category=Notification.Category.BUDGET_WARNING,
        fallback_severity=Notification.Severity.INFO,
    )


@receiver(post_save, sender="finance.InvoicePayment")
def on_invoice_payment_recorded(sender, instance, created, **kwargs):
    """Update invoice status and post payments into the general ledger."""
    instance.invoice.update_status_from_payments()
    if not created:
        return

    from .payment_automation import ensure_payment_journal_posted

    ensure_payment_journal_posted(instance)


# ---------------------------------------------------------------------------
# Payment Voucher notifications
# ---------------------------------------------------------------------------

@receiver(post_save, sender="finance.PaymentVoucher")
def on_payment_voucher_status_changed(sender, instance, created, **kwargs):
    """Notify admins when a payment voucher is created or its status changes."""
    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification

    org = instance.organization
    vendor_name = str(instance.vendor) if instance.vendor_id else "Unknown"
    voucher_num = getattr(instance, "voucher_number", str(instance.pk))

    if created:
        amount = getattr(instance, "amount", None)
        title = f"New Payment Voucher Created — {voucher_num}"
        message = (
            f"Payment voucher {voucher_num} has been created for {vendor_name}"
            f"{f' totalling ₦{amount:,.2f}' if amount else ''}. "
            f"It is pending review and approval before disbursement."
        )
    else:
        update_fields = kwargs.get("update_fields")
        if update_fields and "status" not in update_fields:
            return
        status_label = instance.get_status_display()
        title = f"Payment Voucher {status_label} — {voucher_num}"
        message = (
            f"Payment voucher {voucher_num} for {vendor_name} has been updated to {status_label}."
            f"{'This voucher is now cleared for payment processing.' if status_label.lower() == 'approved' else ''}"
        )

    dispatch_workflow_notification(
        organization=org,
        event_key="finance_voucher_status_changed",
        recipients=_org_admin_users(org),
        context={
            "voucher_number": voucher_num,
            "vendor_name": vendor_name,
            "new_status": instance.get_status_display(),
            "action_url": f"/finance/payment-vouchers/{instance.id}",
        },
        link_url=f"/finance/payment-vouchers/{instance.id}",
        fallback_channels=["in_app"],
        fallback_title=title,
        fallback_message=message,
        fallback_category=Notification.Category.BUDGET_WARNING,
        fallback_severity=Notification.Severity.INFO,
    )


# ---------------------------------------------------------------------------
# Journal Entry notifications
# ---------------------------------------------------------------------------

@receiver(post_save, sender="finance.JournalEntry")
def on_journal_entry_posted(sender, instance, created, **kwargs):
    """Notify admins when a journal entry is posted."""
    if created:
        return
    update_fields = kwargs.get("update_fields")
    if update_fields and "status" not in update_fields:
        return
    if instance.status != "posted":
        return

    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification

    org = instance.organization
    journal_num = getattr(instance, "journal_number", str(instance.pk))
    dispatch_workflow_notification(
        organization=org,
        event_key="finance_journal_posted",
        recipients=_org_admin_users(org),
        context={
            "journal_number": journal_num,
            "description": (instance.description or "")[:100],
            "action_url": f"/finance/journal-entries/{instance.id}",
        },
        link_url=f"/finance/journal-entries/{instance.id}",
        fallback_channels=["in_app"],
        fallback_title=f"Journal Entry Posted — {journal_num}",
        fallback_message=(
            f"Journal entry {journal_num} has been posted to the general ledger. "
            + (f"Description: {instance.description[:80]}. " if instance.description else "")
            + "All associated accounts have been updated."
        ),
        fallback_category=Notification.Category.BUDGET_WARNING,
        fallback_severity=Notification.Severity.INFO,
    )


# ═══════════════════════════════════════════════════════════════════════
# GROUP F — FINANCE & PAYMENTS AUTOMATION
# ═══════════════════════════════════════════════════════════════════════


# ── 40. Payment Approval → Disbursement (Ledger + Cash Flow) ─────────


@receiver(pre_save, sender="finance.Bill")
def capture_bill_previous_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._prev_bill_status = sender.objects.get(pk=instance.pk).status
        except sender.DoesNotExist:
            instance._prev_bill_status = None
    else:
        instance._prev_bill_status = None


@receiver(post_save, sender="finance.Bill")
def on_bill_paid_update_ledger(sender, instance, created, **kwargs):
    """When a bill is marked as paid, update the contractor ledger and notify."""
    if created:
        return
    prev = getattr(instance, "_prev_bill_status", None)
    if prev == instance.status or instance.status != "paid":
        return

    org = instance.organization
    from django.db.models import Sum as DbSum
    total_paid = instance.payments.aggregate(total=DbSum("amount"))["total"] or Decimal("0")

    try:
        dispatch_workflow_notification(
            organization=org,
            event_key="bill_paid_ledger_updated",
            recipients=_org_admin_users(org),
            link_url="/finance/bills",
            fallback_channels=["in_app"],
            fallback_title=f"Bill Paid — {instance.bill_number}",
            fallback_message=(
                f"Bill '{instance.bill_number}' to vendor '{instance.vendor.name}' fully paid. "
                f"Total disbursed: ₦{total_paid:,.2f}. "
                + (f"Project: '{instance.project.name}'. " if instance.project_id else "")
                + "Contractor ledger and cash flow updated."
            ),
            fallback_category=Notification.Category.BUDGET_WARNING,
            fallback_severity=Notification.Severity.INFO,
        )
    except Exception:
        logger.debug("Bill payment notification skipped", exc_info=True)


# ── 42. Cost Reporting → Forecast Update ─────────────────────────────


@receiver(post_save, sender="projects.ProjectCostEntry")
def on_cost_entry_update_forecast(sender, instance, **kwargs):
    """When a project cost entry is saved, roll up to CostCodeBudget forecast."""
    if not instance.project_id:
        return

    from apps.projects.models import CostCodeBudget, ProjectCostEntry
    from django.db.models import Sum as DbSum

    project = instance.project
    cost_code = getattr(instance, "cost_code", "") or ""
    if not cost_code:
        return

    try:
        ccb = CostCodeBudget.objects.get(project=project, cost_code=cost_code)
    except CostCodeBudget.DoesNotExist:
        return

    total_actual = ProjectCostEntry.objects.filter(
        project=project, cost_code=cost_code,
    ).aggregate(total=DbSum("amount"))["total"] or Decimal("0")

    changed = False
    if ccb.actual_cost != total_actual:
        ccb.actual_cost = total_actual
        changed = True

    revised = ccb.original_budget + ccb.approved_changes
    new_ftc = max(Decimal("0"), revised - total_actual)
    if ccb.forecast_to_complete != new_ftc:
        ccb.forecast_to_complete = new_ftc
        changed = True

    if changed:
        ccb.save(update_fields=["actual_cost", "forecast_to_complete", "updated_at"])
