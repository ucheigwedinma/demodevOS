import logging

from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.notifications.services import Notification, dispatch_workflow_notification

logger = logging.getLogger(__name__)


def _org_admin_recipients(organization):
    """Get admin users for the org."""
    from apps.accounts.models import UserProfile

    profiles = UserProfile.objects.filter(
        organization=organization, role="admin", user__is_active=True
    ).select_related("user")
    return [p.user for p in profiles]


def _resolve_facility_org(instance):
    """Walk up the facility → property → organization chain."""
    org = getattr(instance, "organization", None)
    if org:
        return org
    prop = getattr(instance, "property", None)
    return getattr(prop, "organization", None) if prop else None


def _resolve_child_org(instance):
    """Walk up from a child model (floor/zone/space) → facility → org."""
    facility = getattr(instance, "facility", None)
    if not facility:
        return None, None
    return facility, _resolve_facility_org(facility)


@receiver(post_save, sender="facility_management.Facility")
def notify_facility_created(sender, instance, created, **kwargs):
    if not created:
        return
    org = _resolve_facility_org(instance)
    if not org:
        return
    prop = getattr(instance, "property", None)
    prop_name = getattr(prop, "name", "Unknown Property") if prop else "Unknown Property"
    classification = getattr(instance, "facility_classification", "").replace("_", " ").title()
    ownership = getattr(instance, "ownership_type", "").replace("_", " ").title()

    dispatch_workflow_notification(
        organization=org,
        event_key="facility_created",
        recipients=_org_admin_recipients(org),
        context={
            "facility_code": instance.facility_code,
            "property_name": prop_name,
            "classification": classification,
        },
        fallback_title="New Facility Registered",
        fallback_message=(
            f"A new {classification.lower() or 'facility'} ({instance.facility_code}) "
            f"has been registered under {prop_name}. "
            f"Ownership type: {ownership or 'Not specified'}."
        ),
        fallback_category=Notification.Category.SYSTEM,
    )


@receiver(post_save, sender="facility_management.FacilityFloor")
def notify_floor_created(sender, instance, created, **kwargs):
    if not created:
        return
    facility, org = _resolve_child_org(instance)
    if not org:
        return
    usage = getattr(instance, "usage_type", "") or "general"
    area = getattr(instance, "gross_area_sqft", None)
    area_text = f" ({area:,.0f} sqft)" if area else ""

    dispatch_workflow_notification(
        organization=org,
        event_key="facility_floor_created",
        recipients=_org_admin_recipients(org),
        context={
            "floor_name": instance.name,
            "facility_code": facility.facility_code,
            "usage_type": usage,
        },
        fallback_title="New Floor Added to Facility",
        fallback_message=(
            f"'{instance.name}' has been added to facility {facility.facility_code}. "
            f"Usage: {usage.replace('_', ' ').title()}{area_text}."
        ),
        fallback_category=Notification.Category.SYSTEM,
    )


@receiver(post_save, sender="facility_management.FacilityZone")
def notify_zone_created(sender, instance, created, **kwargs):
    if not created:
        return
    facility, org = _resolve_child_org(instance)
    if not org:
        return
    zone_type = getattr(instance, "zone_type", "").replace("_", " ").title() or "General"
    zone_code = getattr(instance, "zone_code", "") or ""

    dispatch_workflow_notification(
        organization=org,
        event_key="facility_zone_created",
        recipients=_org_admin_recipients(org),
        context={
            "zone_name": instance.name,
            "zone_code": zone_code,
            "facility_code": facility.facility_code,
            "zone_type": zone_type,
        },
        fallback_title="New Zone Created",
        fallback_message=(
            f"{zone_type} zone '{instance.name}'"
            f"{f' ({zone_code})' if zone_code else ''} "
            f"has been created in facility {facility.facility_code}."
        ),
        fallback_category=Notification.Category.SYSTEM,
    )


@receiver(post_save, sender="facility_management.FacilityUnitSpace")
def notify_space_created(sender, instance, created, **kwargs):
    if not created:
        return
    facility, org = _resolve_child_org(instance)
    if not org:
        return
    zone = getattr(instance, "zone", None)
    zone_name = getattr(zone, "name", None) if zone else None

    dispatch_workflow_notification(
        organization=org,
        event_key="facility_space_created",
        recipients=_org_admin_recipients(org),
        context={
            "space_label": instance.space_label,
            "facility_code": facility.facility_code,
        },
        fallback_title="New Space Registered",
        fallback_message=(
            f"Space '{instance.space_label}' has been registered in "
            f"facility {facility.facility_code}"
            f"{f', zone {zone_name}' if zone_name else ''}."
        ),
        fallback_category=Notification.Category.SYSTEM,
    )


@receiver(post_save, sender="facility_management.FacilityUnitSpace")
def sync_space_profile_defaults(sender, instance, **kwargs):
    """Ensure occupancy metadata exists whenever a facility space is saved."""

    def _run():
        from apps.facility_management.space_occupancy_workflows import ensure_space_profile_defaults

        try:
            ensure_space_profile_defaults(instance)
        except Exception:  # pragma: no cover - keep save path resilient
            logger.exception("Space occupancy profile sync failed for facility space %s", instance.id)

    transaction.on_commit(_run)


@receiver(post_save, sender="facility_management.FacilityIncident")
def notify_incident_created(sender, instance, created, **kwargs):
    if not created:
        return
    facility, org = _resolve_child_org(instance)
    if not org:
        return
    severity = getattr(instance, "severity", "medium")
    description = getattr(instance, "description", "") or ""
    snippet = (description[:80] + "...") if len(description) > 80 else description

    dispatch_workflow_notification(
        organization=org,
        event_key="facility_incident_reported",
        recipients=_org_admin_recipients(org),
        context={
            "facility_code": facility.facility_code,
            "severity": severity,
            "description": snippet,
        },
        fallback_title=f"Facility Incident — {severity.title()} Priority",
        fallback_message=(
            f"A {severity.lower()}-priority incident has been reported at "
            f"facility {facility.facility_code}."
            f"{f' Details: {snippet}' if snippet else ''}"
        ),
        fallback_category=Notification.Category.SYSTEM,
        fallback_severity=Notification.Severity.WARNING if severity in ("high", "critical") else Notification.Severity.INFO,
    )


@receiver(post_save, sender="properties.ServiceRequest")
def sync_service_request_automation(sender, instance, **kwargs):
    """Keep internal facility service requests aligned with work-order workflows."""

    def _run():
        from apps.facility_management.service_request_workflows import (
            ensure_service_request_defaults,
            ensure_service_request_work_order,
        )
        from apps.tenants.workflows import sync_tenant_service_request_resolution_automation

        try:
            ensure_service_request_defaults(instance)
            ensure_service_request_work_order(instance)
            sync_tenant_service_request_resolution_automation(instance)
        except Exception:  # pragma: no cover - keep save path resilient
            logger.exception("Service request automation sync failed for request %s", instance.id)

    transaction.on_commit(_run)


@receiver(post_save, sender="facility_management.SpaceAllocation")
def sync_space_allocation_automation(sender, instance, **kwargs):
    """Apply allocation status, tenant sync, and inventory sync on save."""

    def _run():
        from apps.facility_management.space_occupancy_workflows import (
            ensure_allocation_defaults,
            sync_inventory_for_tenant_allocation,
            sync_tenant_profile_for_allocation,
        )

        try:
            ensure_allocation_defaults(instance)
            sync_tenant_profile_for_allocation(instance)
            sync_inventory_for_tenant_allocation(instance)
        except Exception:  # pragma: no cover - keep save path resilient
            logger.exception("Space allocation automation sync failed for allocation %s", instance.id)

    transaction.on_commit(_run)


@receiver(post_save, sender="facility_management.SpaceBooking")
def sync_space_booking_automation(sender, instance, **kwargs):
    """Apply booking approval/check-in/no-show completion logic on save."""

    def _run():
        from apps.facility_management.space_occupancy_workflows import ensure_booking_defaults

        try:
            ensure_booking_defaults(instance)
        except Exception:  # pragma: no cover - keep save path resilient
            logger.exception("Space booking automation sync failed for booking %s", instance.id)

    transaction.on_commit(_run)


@receiver(post_save, sender="properties.WorkOrder")
def sync_service_requests_from_work_order(sender, instance, **kwargs):
    """Push work-order lifecycle updates back into linked service requests."""

    def _run():
        from apps.facility_management.service_request_workflows import sync_service_request_from_work_order

        try:
            for service_request in instance.service_requests.select_related("work_order").all():
                sync_service_request_from_work_order(service_request)
        except Exception:  # pragma: no cover - keep save path resilient
            logger.exception("Work-order-to-service-request sync failed for work order %s", instance.id)

    transaction.on_commit(_run)


@receiver(post_save, sender="finance.InvoicePayment")
def sync_billing_ticket_resolution(sender, instance, created, **kwargs):
    """Resolve invoice-linked billing tickets as soon as payments are posted."""
    if not created:
        return

    def _run():
        from apps.facility_management.service_request_workflows import (
            resolve_billing_tickets_for_invoice,
            sync_invoice_collection_status,
        )

        try:
            invoice = instance.invoice
            sync_invoice_collection_status(invoice)
            resolve_billing_tickets_for_invoice(
                invoice,
                resolution_note=f"Auto-resolved after payment for invoice {invoice.invoice_number}.",
            )
        except Exception:  # pragma: no cover - keep save path resilient
            logger.exception("Invoice payment automation sync failed for invoice %s", instance.invoice_id)

    transaction.on_commit(_run)


# ── Facility Incident Resolved ────────────────────────────────────────


def _org_admin_users(org):
    from apps.accounts.models import UserProfile
    return [p.user for p in UserProfile.objects.filter(organization=org, role="admin", user__is_active=True).select_related("user")]


@receiver(pre_save, sender="facility_management.FacilityIncident")
def capture_incident_previous_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._prev_incident_status = sender.objects.get(pk=instance.pk).status
        except sender.DoesNotExist:
            instance._prev_incident_status = None
    else:
        instance._prev_incident_status = None


@receiver(post_save, sender="facility_management.FacilityIncident")
def on_facility_incident_resolved(sender, instance, created, **kwargs):
    if created:
        return
    prev = getattr(instance, "_prev_incident_status", None)
    if prev == instance.status or instance.status != "resolved":
        return
    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification
        org = instance.organization
        ref = getattr(instance, "incident_number", "") or f"INC-{instance.pk}"
        title_text = getattr(instance, "title", "") or getattr(instance, "description", "")[:60] or ref
        dispatch_workflow_notification(
            organization=org, event_key="facility_incident_resolved", recipients=_org_admin_users(org),
            link_url="/facility-management/health-safety", fallback_channels=["in_app"],
            fallback_title=f"Facility Incident Resolved — {ref}",
            fallback_message=f"Incident {ref} ({title_text}) has been resolved and closed.",
            fallback_category=Notification.Category.SYSTEM, fallback_severity=Notification.Severity.INFO,
        )
    except Exception:
        logger.debug("Facility incident resolved notification skipped", exc_info=True)


# ── Compliance Checklist Failed ───────────────────────────────────────


@receiver(post_save, sender="facility_management.FacilityComplianceChecklist")
def on_compliance_checklist_failed(sender, instance, created, **kwargs):
    if created:
        return
    status = getattr(instance, "status", "") or getattr(instance, "overall_status", "")
    if status not in ("failed", "non_compliant", "overdue"):
        return
    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification
        org = instance.organization
        checklist_name = getattr(instance, "name", "") or getattr(instance, "title", "") or f"Checklist #{instance.pk}"
        facility_name = str(instance.facility) if hasattr(instance, "facility") and instance.facility else ""
        dispatch_workflow_notification(
            organization=org, event_key="compliance_checklist_failed", recipients=_org_admin_users(org),
            link_url="/facility-management/health-safety", fallback_channels=["in_app"],
            fallback_title=f"Compliance Check Failed — {checklist_name}",
            fallback_message=(
                f"Compliance checklist '{checklist_name}'"
                + (f" for {facility_name}" if facility_name else "")
                + f" has been marked as {status.replace('_', ' ')}. Immediate attention required."
            ),
            fallback_category=Notification.Category.SYSTEM, fallback_severity=Notification.Severity.CRITICAL,
        )
    except Exception:
        logger.debug("Compliance checklist notification skipped", exc_info=True)
