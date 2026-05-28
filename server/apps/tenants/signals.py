import logging

from django.db.models.signals import post_save, pre_save
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


@receiver(post_save, sender="tenants.TenantProfile")
def notify_tenant_created(sender, instance, created, **kwargs):
    if not created:
        return

    from apps.notifications.services import Notification, dispatch_workflow_notification

    org = getattr(instance, "organization", None)
    if not org:
        return

    display_name = instance.resolved_display_name
    tenant_type = instance.get_tenant_type_display()
    unit = instance.unit
    unit_label = str(unit) if unit else None
    prop = getattr(instance, "property", None)
    prop_name = str(prop) if prop else None

    dispatch_workflow_notification(
        organization=org,
        event_key="tenant_created",
        recipients=_org_admin_users(org),
        context={
            "tenant_name": display_name,
            "tenant_type": tenant_type,
            "unit": unit_label or "",
        },
        fallback_title=f"New Tenant Registered — {display_name}",
        fallback_message=(
            f"A new {tenant_type.lower()} tenant '{display_name}' has been registered"
            + (f" for unit {unit_label}" if unit_label else "")
            + (f" at {prop_name}" if prop_name else "")
            + ". Lease details and move-in preparations can now be configured."
        ),
        fallback_category=Notification.Category.SYSTEM,
    )


@receiver(post_save, sender="tenants.LeaseAgreement")
def run_lease_created_event_automation(sender, instance, created, **kwargs):
    if not created:
        return
    if getattr(instance, "_skip_created_automation", False):
        return

    from apps.tenants.workflows import run_lease_created_automation

    try:
        summary = run_lease_created_automation(instance)
        logger.info(
            "tenants.lease_created_automation.success lease_id=%s charge_rules=%s invoices=%s access_records=%s utility_tracking=%s",
            instance.id,
            summary.get("billing_schedule_rules_created", 0),
            summary.get("invoices_created", 0),
            summary.get("access_records_created", 0),
            summary.get("utility_tracking_records_synced", 0),
        )
    except Exception:
        logger.exception("tenants.lease_created_automation.failed lease_id=%s", instance.id)


@receiver(pre_save, sender="tenants.TenantProfile")
def capture_tenant_previous_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_status = None
        return
    from apps.tenants.models import TenantProfile

    instance._previous_status = (
        TenantProfile.objects.filter(pk=instance.pk)
        .values_list("status", flat=True)
        .first()
    )


@receiver(post_save, sender="tenants.TenantProfile")
def notify_tenant_status_changed(sender, instance, created, **kwargs):
    if created:
        return
    prev = getattr(instance, "_previous_status", None)
    if prev is None or prev == instance.status:
        return

    from apps.notifications.services import Notification, dispatch_workflow_notification

    org = getattr(instance, "organization", None)
    if not org:
        return

    display_name = instance.resolved_display_name
    new_status = instance.get_status_display()
    old_status = dict(instance.Status.choices).get(prev, prev)

    status_context = {
        "active": "The tenant is now active and occupying the premises.",
        "moved_out": "The tenant has moved out. Please initiate unit turnover and deposit reconciliation.",
        "inactive": "The tenant profile has been deactivated.",
        "pending_move_in": "The tenant is awaiting move-in. Please ensure all preparations are in order.",
    }

    dispatch_workflow_notification(
        organization=org,
        event_key="tenant_status_changed",
        recipients=_org_admin_users(org),
        context={
            "tenant_name": display_name,
            "old_status": old_status,
            "new_status": new_status,
        },
        fallback_title=f"Tenant Status Updated — {display_name}",
        fallback_message=(
            f"Tenant '{display_name}' has moved from {old_status} to {new_status}. "
            + status_context.get(instance.status, "")
        ),
        fallback_category=Notification.Category.SYSTEM,
        fallback_severity=(
            Notification.Severity.WARNING
            if instance.status in ("moved_out", "inactive")
            else Notification.Severity.INFO
        ),
    )


# ── Lease Renewal Request ─────────────────────────────────────────────


@receiver(post_save, sender="tenants.LeaseRenewalRequest")
def on_lease_renewal_requested(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification
        org = instance.organization if hasattr(instance, "organization") else (instance.lease.organization if hasattr(instance, "lease") and instance.lease else None)
        if not org:
            return
        tenant_name = str(instance.lease.tenant) if hasattr(instance, "lease") and instance.lease and hasattr(instance.lease, "tenant") else "Unknown"
        lease_ref = getattr(instance.lease, "lease_number", "") if hasattr(instance, "lease") and instance.lease else ""
        dispatch_workflow_notification(
            organization=org, event_key="lease_renewal_request", recipients=_org_admin_users(org),
            link_url="/tenants/leases", fallback_channels=["in_app"],
            fallback_title=f"Lease Renewal Requested — {tenant_name}",
            fallback_message=f"Tenant {tenant_name} has requested renewal of lease {lease_ref}. Please review and respond.",
            fallback_category=Notification.Category.SYSTEM, fallback_severity=Notification.Severity.WARNING,
        )
    except Exception:
        logger.debug("Lease renewal notification skipped", exc_info=True)


# ── Lease Termination Request ─────────────────────────────────────────


@receiver(post_save, sender="tenants.LeaseTerminationRequest")
def on_lease_termination_requested(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification
        org = instance.organization if hasattr(instance, "organization") else (instance.lease.organization if hasattr(instance, "lease") and instance.lease else None)
        if not org:
            return
        tenant_name = str(instance.lease.tenant) if hasattr(instance, "lease") and instance.lease and hasattr(instance.lease, "tenant") else "Unknown"
        lease_ref = getattr(instance.lease, "lease_number", "") if hasattr(instance, "lease") and instance.lease else ""
        reason = getattr(instance, "reason", "")[:80] or "No reason provided"
        dispatch_workflow_notification(
            organization=org, event_key="lease_termination_request", recipients=_org_admin_users(org),
            link_url="/tenants/leases", fallback_channels=["in_app"],
            fallback_title=f"Lease Termination Requested — {tenant_name}",
            fallback_message=f"Tenant {tenant_name} has requested termination of lease {lease_ref}. Reason: {reason}.",
            fallback_category=Notification.Category.SYSTEM, fallback_severity=Notification.Severity.CRITICAL,
        )
    except Exception:
        logger.debug("Lease termination notification skipped", exc_info=True)
