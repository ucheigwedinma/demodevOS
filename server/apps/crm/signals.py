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


def _lead_name(instance):
    name = ""
    if hasattr(instance, "first_name"):
        name = f"{instance.first_name or ''} {instance.last_name or ''}".strip()
    return name or str(instance)


# ---------------------------------------------------------------------------
# Lead notifications
# ---------------------------------------------------------------------------

@receiver(post_save, sender="crm.Lead")
def on_lead_assigned(sender, instance, created, **kwargs):
    """Notify a sales user when a lead is assigned to them."""
    if not instance.assigned_to_id:
        return
    update_fields = kwargs.get("update_fields")
    if not created and update_fields and "assigned_to_id" not in update_fields:
        return

    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification

    org = instance.organization if hasattr(instance, "organization") else None
    if not org:
        return

    lead_name = _lead_name(instance)
    company = getattr(instance, "company_name", "") or ""
    source = getattr(instance, "source", "") or ""
    source_text = f" (Source: {source.replace('_', ' ').title()})" if source else ""

    dispatch_workflow_notification(
        organization=org,
        event_key="crm_lead_assigned",
        recipients=[instance.assigned_to],
        context={
            "lead_name": lead_name,
            "company_name": company,
            "assigned_by": "",
            "action_url": f"/crm/leads/{instance.id}",
        },
        link_url=f"/crm/leads/{instance.id}",
        fallback_channels=["in_app"],
        fallback_title=f"New Lead Assignment — {lead_name}",
        fallback_message=(
            f"You have been assigned the lead \"{lead_name}\""
            f"{f' from {company}' if company else ''}{source_text}. "
            f"Please review and initiate contact within your SLA window."
        ),
        fallback_category=Notification.Category.CRM_LEAD,
        fallback_severity=Notification.Severity.INFO,
    )


@receiver(post_save, sender="crm.Lead")
def on_lead_stage_changed(sender, instance, created, **kwargs):
    """Notify when a lead moves through the pipeline."""
    if created:
        return
    update_fields = kwargs.get("update_fields")
    if update_fields and "pipeline_stage" not in update_fields:
        return

    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification

    org = instance.organization if hasattr(instance, "organization") else None
    if not org:
        return

    lead_name = _lead_name(instance)
    stage_label = instance.get_pipeline_stage_display()
    assigned = instance.assigned_to.get_full_name() if instance.assigned_to_id else "Unassigned"

    recipients = []
    if instance.assigned_to_id:
        recipients.append(instance.assigned_to)
    recipients.extend(u for u in _org_admin_users(org) if u not in recipients)

    dispatch_workflow_notification(
        organization=org,
        event_key="crm_lead_stage_changed",
        recipients=recipients,
        context={
            "lead_name": lead_name,
            "new_stage": stage_label,
            "action_url": f"/crm/leads/{instance.id}",
        },
        link_url=f"/crm/leads/{instance.id}",
        fallback_channels=["in_app"],
        fallback_title=f"Pipeline Update — {lead_name}",
        fallback_message=(
            f"Lead \"{lead_name}\" has progressed to the {stage_label} stage. "
            f"Assigned to: {assigned}."
        ),
        fallback_category=Notification.Category.CRM_LEAD,
        fallback_severity=Notification.Severity.INFO,
    )


@receiver(post_save, sender="crm.Lead")
def on_lead_created(sender, instance, created, **kwargs):
    """Notify admins when a new lead is created."""
    if not created:
        return

    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification

    org = instance.organization if hasattr(instance, "organization") else None
    if not org:
        return

    lead_name = _lead_name(instance)
    company = getattr(instance, "company_name", "") or ""
    source = getattr(instance, "source", "") or ""
    email = getattr(instance, "email", "") or ""
    phone = getattr(instance, "phone", "") or ""
    source_text = source.replace("_", " ").title() if source else "Manual entry"

    dispatch_workflow_notification(
        organization=org,
        event_key="crm_lead_created",
        recipients=_org_admin_users(org),
        context={
            "lead_name": lead_name,
            "action_url": f"/crm/leads/{instance.id}",
        },
        link_url=f"/crm/leads/{instance.id}",
        fallback_channels=["in_app"],
        fallback_title=f"New Lead — {lead_name}",
        fallback_message=(
            f"A new lead has been captured: {lead_name}"
            f"{f' ({company})' if company else ''}. "
            f"Source: {source_text}."
            f"{f' Contact: {email}' if email else f' Phone: {phone}' if phone else ''}"
        ),
        fallback_category=Notification.Category.CRM_LEAD,
        fallback_severity=Notification.Severity.INFO,
    )


# ---------------------------------------------------------------------------
# Reservation notifications
# ---------------------------------------------------------------------------

@receiver(post_save, sender="crm.UnitReservation")
def on_reservation_status_changed(sender, instance, created, **kwargs):
    """Notify when a reservation is created or its status changes."""
    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification

    org = instance.organization if hasattr(instance, "organization") else None
    if not org:
        return

    status_label = instance.get_status_display()
    unit_label = str(instance.unit) if instance.unit_id else "Unknown unit"
    reservation_number = getattr(instance, "reservation_number", "") or ""
    lead = getattr(instance, "lead", None)
    lead_name = _lead_name(lead) if lead else ""
    deposit = getattr(instance, "deposit_amount", None)
    deposit_text = f" Deposit: ₦{deposit:,.2f}." if deposit else ""

    if created:
        title = f"New Reservation — {reservation_number or unit_label}"
        message = (
            f"A reservation has been created for {unit_label}"
            f"{f' by {lead_name}' if lead_name else ''}."
            f"{deposit_text}"
        )
    else:
        update_fields = kwargs.get("update_fields")
        if update_fields and "status" not in update_fields:
            return
        title = f"Reservation {status_label} — {reservation_number or unit_label}"
        message = (
            f"Reservation {reservation_number} for {unit_label} "
            f"has been updated to {status_label}."
            f"{f' Lead: {lead_name}.' if lead_name else ''}"
        )

    dispatch_workflow_notification(
        organization=org,
        event_key="crm_reservation_status_changed",
        recipients=_org_admin_users(org),
        context={
            "unit_label": unit_label,
            "new_status": status_label,
            "action_url": f"/crm/reservations/{instance.id}",
        },
        link_url=f"/crm/reservations/{instance.id}",
        fallback_channels=["in_app"],
        fallback_title=title,
        fallback_message=message,
        fallback_category=Notification.Category.CRM_RESERVATION,
        fallback_severity=(
            Notification.Severity.WARNING
            if instance.status in ("cancelled", "expired")
            else Notification.Severity.INFO
        ),
    )


# ---------------------------------------------------------------------------
# Contact Account notifications
# ---------------------------------------------------------------------------

@receiver(post_save, sender="crm.ContactAccount")
def on_contact_created(sender, instance, created, **kwargs):
    """Notify admins when a new contact account is created."""
    if not created:
        return

    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification

    org = instance.organization if hasattr(instance, "organization") else None
    if not org:
        return

    contact_name = getattr(instance, "display_name", "") or str(instance)
    contact_type = getattr(instance, "account_type", "") or ""
    email = getattr(instance, "email", "") or ""
    company = getattr(instance, "company_name", "") or ""
    type_text = contact_type.replace("_", " ").title() if contact_type else "Contact"

    dispatch_workflow_notification(
        organization=org,
        event_key="crm_contact_created",
        recipients=_org_admin_users(org),
        context={
            "contact_name": contact_name,
            "action_url": f"/crm/contacts/{instance.id}",
        },
        link_url=f"/crm/contacts/{instance.id}",
        fallback_channels=["in_app"],
        fallback_title=f"New {type_text} — {contact_name}",
        fallback_message=(
            f"A new {type_text.lower()} has been added: {contact_name}"
            f"{f' ({company})' if company else ''}."
            f"{f' Email: {email}.' if email else ''}"
        ),
        fallback_category=Notification.Category.CRM_LEAD,
        fallback_severity=Notification.Severity.INFO,
    )


# ── Deal Won/Lost ────────────────────────────────────────────────────


@receiver(pre_save, sender="crm.ContactDealLink")
def capture_deal_previous_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._prev_deal_status = sender.objects.get(pk=instance.pk).status
        except sender.DoesNotExist:
            instance._prev_deal_status = None
    else:
        instance._prev_deal_status = None


@receiver(post_save, sender="crm.ContactDealLink")
def on_deal_won_or_lost(sender, instance, created, **kwargs):
    if created:
        return
    prev = getattr(instance, "_prev_deal_status", None)
    if prev == instance.status or instance.status not in ("won", "lost"):
        return
    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification
        org = instance.organization if hasattr(instance, "organization") else getattr(getattr(instance, "contact", None), "organization", None)
        if not org:
            return
        contact_name = str(instance.contact) if instance.contact else "Unknown"
        deal_name = getattr(instance, "deal_name", "") or getattr(instance, "title", "") or f"Deal #{instance.pk}"
        if instance.status == "won":
            title, message, severity = f"Deal Won — {deal_name}", f"Deal '{deal_name}' with {contact_name} has been won. Congratulations!", Notification.Severity.INFO
        else:
            title, message, severity = f"Deal Lost — {deal_name}", f"Deal '{deal_name}' with {contact_name} has been lost. Review pipeline for follow-up.", Notification.Severity.WARNING
        dispatch_workflow_notification(organization=org, event_key="deal_status_change", recipients=_org_admin_users(org), link_url="/crm/opportunities", fallback_channels=["in_app"], fallback_title=title, fallback_message=message, fallback_category=Notification.Category.CRM_LEAD, fallback_severity=severity)
    except Exception:
        logger.debug("Deal status notification skipped", exc_info=True)


# ── Lead Won/Lost ────────────────────────────────────────────────────


@receiver(pre_save, sender="crm.Lead")
def capture_lead_previous_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._prev_lead_status = sender.objects.get(pk=instance.pk).status
        except sender.DoesNotExist:
            instance._prev_lead_status = None
    else:
        instance._prev_lead_status = None


@receiver(post_save, sender="crm.Lead")
def on_lead_converted(sender, instance, created, **kwargs):
    if created:
        return
    prev = getattr(instance, "_prev_lead_status", None)
    if prev == instance.status or instance.status not in ("won", "lost"):
        return
    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification
        org = instance.organization
        lead_name = getattr(instance, "full_name", "") or getattr(instance, "name", "") or str(instance)
        if instance.status == "won":
            title, message = f"Lead Converted — {lead_name}", f"Lead '{lead_name}' has been converted to a customer. Proceed with reservation and SPA."
        else:
            title, message = f"Lead Lost — {lead_name}", f"Lead '{lead_name}' has been marked as lost."
        dispatch_workflow_notification(organization=org, event_key="lead_status_change", recipients=_org_admin_users(org), link_url="/crm/leads", fallback_channels=["in_app"], fallback_title=title, fallback_message=message, fallback_category=Notification.Category.CRM_LEAD, fallback_severity=Notification.Severity.INFO if instance.status == "won" else Notification.Severity.WARNING)
    except Exception:
        logger.debug("Lead converted notification skipped", exc_info=True)
