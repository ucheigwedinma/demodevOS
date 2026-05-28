import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.notifications.services import Notification, dispatch_workflow_notification

logger = logging.getLogger(__name__)


def _org_admin_recipients(organization):
    from apps.accounts.models import UserProfile

    profiles = UserProfile.objects.filter(
        organization=organization, role="admin", user__is_active=True
    ).select_related("user")
    return [p.user for p in profiles]


@receiver(pre_save, sender="workflows.WorkflowInstance")
def capture_workflow_previous_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_status = None
        return
    from apps.workflows.models import WorkflowInstance

    instance._previous_status = (
        WorkflowInstance.objects.filter(pk=instance.pk)
        .values_list("state", flat=True)
        .first()
    )


@receiver(post_save, sender="workflows.WorkflowInstance")
def notify_workflow_status_changed(sender, instance, created, **kwargs):
    if created:
        return
    prev = getattr(instance, "_previous_status", None)
    if prev is None or prev == instance.state:
        return
    org = getattr(instance, "organization", None)
    if not org:
        return

    initiator = getattr(instance, "initiated_by", None)
    recipients = [initiator] if initiator and initiator.is_active else _org_admin_recipients(org)
    content_type = getattr(instance, "content_type", None)
    model_name = content_type.model.replace("_", " ").title() if content_type else "Record"

    new_status = instance.state.replace("_", " ").title()
    old_status = prev.replace("_", " ").title()

    dispatch_workflow_notification(
        organization=org,
        event_key="workflow_status_changed",
        recipients=recipients,
        context={
            "workflow_name": str(instance),
            "old_status": old_status,
            "new_status": new_status,
            "model_name": model_name,
        },
        fallback_title=f"Approval Workflow {new_status}",
        fallback_message=(
            f"The approval workflow for {model_name.lower()} has moved from "
            f"'{old_status}' to '{new_status}'."
        ),
        fallback_category=Notification.Category.SYSTEM,
        fallback_severity=(
            Notification.Severity.WARNING
            if instance.state in ("rejected", "cancelled")
            else Notification.Severity.INFO
        ),
    )


@receiver(post_save, sender="workflows.WorkflowStep")
def notify_workflow_step_action(sender, instance, created, **kwargs):
    if created:
        return
    if instance.state not in ("approved", "rejected"):
        return
    workflow = getattr(instance, "workflow", None)
    if not workflow:
        return
    org = getattr(workflow, "organization", None)
    if not org:
        return

    initiator = getattr(workflow, "initiated_by", None)
    recipients = [initiator] if initiator and initiator.is_active else _org_admin_recipients(org)

    decided_by = getattr(instance, "decided_by", None)
    decided_by_name = decided_by.get_full_name() if decided_by else "System"
    decision = "approved" if instance.state == "approved" else "rejected"

    dispatch_workflow_notification(
        organization=org,
        event_key="workflow_step_decision",
        recipients=recipients,
        context={
            "workflow_name": str(workflow),
            "step_name": instance.name,
            "decision": decision,
            "decided_by": decided_by_name,
        },
        fallback_title=f"Approval Step {decision.title()}",
        fallback_message=(
            f"'{instance.name}' in the approval workflow for '{workflow}' "
            f"has been {decision} by {decided_by_name}."
        ),
        fallback_category=Notification.Category.SYSTEM,
        fallback_severity=(
            Notification.Severity.WARNING
            if decision == "rejected"
            else Notification.Severity.INFO
        ),
    )
