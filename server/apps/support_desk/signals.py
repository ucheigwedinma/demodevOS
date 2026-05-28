import logging

from django.db.models.signals import post_save
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


# ---------------------------------------------------------------------------
# Support Ticket notifications
# ---------------------------------------------------------------------------

@receiver(post_save, sender="support_desk.SupportTicket")
def on_ticket_created(sender, instance, created, **kwargs):
    """Notify admins and assigned agent when a ticket is created."""
    if not created:
        return

    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification

    org = instance.organization
    ticket_num = getattr(instance, "ticket_number", str(instance.pk))
    subject = getattr(instance, "subject", "") or getattr(instance, "title", "") or str(instance)

    recipients = []
    if instance.assigned_agent_id:
        recipients.append(instance.assigned_agent)
    recipients.extend(u for u in _org_admin_users(org) if u not in recipients)

    dispatch_workflow_notification(
        organization=org,
        event_key="support_ticket_created",
        recipients=recipients,
        context={
            "ticket_number": ticket_num,
            "subject": subject[:100],
            "priority": instance.get_priority_display() if hasattr(instance, "get_priority_display") else "",
            "action_url": f"/support/{instance.id}",
        },
        link_url=f"/support/{instance.id}",
        fallback_channels=["in_app"],
        fallback_title=f"New Support Ticket — {ticket_num}",
        fallback_message=(
            f"Support ticket {ticket_num} has been created: '{subject[:80]}'. "
            f"Please review and respond within the applicable SLA window."
        ),
        fallback_category=Notification.Category.SYSTEM,
        fallback_severity=Notification.Severity.INFO,
    )


@receiver(post_save, sender="support_desk.SupportTicket")
def on_ticket_status_changed(sender, instance, created, **kwargs):
    """Notify when a ticket status changes."""
    if created:
        return
    update_fields = kwargs.get("update_fields")
    if update_fields and "status" not in update_fields:
        return

    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification

    org = instance.organization
    ticket_num = getattr(instance, "ticket_number", str(instance.pk))
    status_label = instance.get_status_display()
    subject = getattr(instance, "subject", "") or getattr(instance, "title", "") or str(instance)

    recipients = []
    if instance.requester_id:
        recipients.append(instance.requester)
    if instance.assigned_agent_id and instance.assigned_agent not in recipients:
        recipients.append(instance.assigned_agent)
    if not recipients:
        recipients = _org_admin_users(org)

    dispatch_workflow_notification(
        organization=org,
        event_key="support_ticket_status_changed",
        recipients=recipients,
        context={
            "ticket_number": ticket_num,
            "subject": subject[:100],
            "new_status": status_label,
            "action_url": f"/support/{instance.id}",
        },
        link_url=f"/support/{instance.id}",
        fallback_channels=["in_app"],
        fallback_title=f"Support Ticket {status_label} — {ticket_num}",
        fallback_message=(
            f"Support ticket {ticket_num} ('{subject[:60]}') has been updated to {status_label}."
            + (" The issue has been resolved and the ticket is now closed." if status_label.lower() in ("resolved", "closed") else "")
        ),
        fallback_category=Notification.Category.SYSTEM,
        fallback_severity=Notification.Severity.INFO,
    )


@receiver(post_save, sender="support_desk.SupportTicket")
def on_ticket_assigned(sender, instance, created, **kwargs):
    """Notify agent when a ticket is assigned to them."""
    if created or not instance.assigned_agent_id:
        return
    update_fields = kwargs.get("update_fields")
    if update_fields and "assigned_agent_id" not in update_fields:
        return

    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification

    org = instance.organization
    ticket_num = getattr(instance, "ticket_number", str(instance.pk))
    subject = getattr(instance, "subject", "") or getattr(instance, "title", "") or str(instance)

    dispatch_workflow_notification(
        organization=org,
        event_key="support_ticket_assigned",
        recipients=[instance.assigned_agent],
        context={
            "ticket_number": ticket_num,
            "subject": subject[:100],
            "action_url": f"/support/{instance.id}",
        },
        link_url=f"/support/{instance.id}",
        fallback_channels=["in_app"],
        fallback_title=f"Support Ticket Assigned — {ticket_num}",
        fallback_message=(
            f"Support ticket {ticket_num} ('{subject[:60]}') has been assigned to you. "
            f"Please review the details and begin resolution."
        ),
        fallback_category=Notification.Category.SYSTEM,
        fallback_severity=Notification.Severity.INFO,
    )


# ---------------------------------------------------------------------------
# Support Ticket Comment notifications
# ---------------------------------------------------------------------------

@receiver(post_save, sender="support_desk.SupportTicketComment")
def on_ticket_comment_created(sender, instance, created, **kwargs):
    """Notify ticket participants when a comment is added."""
    if not created:
        return

    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification

    ticket = instance.ticket
    org = ticket.organization
    ticket_num = getattr(ticket, "ticket_number", str(ticket.pk))
    subject = getattr(ticket, "subject", "") or getattr(ticket, "title", "") or str(ticket)

    recipients = []
    if ticket.requester_id:
        recipients.append(ticket.requester)
    if ticket.assigned_agent_id and ticket.assigned_agent not in recipients:
        recipients.append(ticket.assigned_agent)
    # Don't notify the comment author
    author = instance.author
    recipients = [r for r in recipients if r != author]
    if not recipients:
        return

    dispatch_workflow_notification(
        organization=org,
        event_key="support_ticket_reply_posted",
        recipients=recipients,
        context={
            "ticket_number": ticket_num,
            "subject": subject[:100],
            "action_url": f"/support/{ticket.id}",
        },
        link_url=f"/support/{ticket.id}",
        fallback_channels=["in_app"],
        fallback_title=f"New Reply on Support Ticket — {ticket_num}",
        fallback_message=(
            f"A new reply has been posted on support ticket {ticket_num} ('{subject[:60]}'). "
            f"Please review and respond if further action is needed."
        ),
        fallback_category=Notification.Category.SYSTEM,
        fallback_severity=Notification.Severity.INFO,
    )
