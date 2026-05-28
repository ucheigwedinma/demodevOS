import logging

from django.db.models.signals import post_save
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


@receiver(post_save, sender="partners.PartnerOnboardingCase")
def on_case_created(sender, instance, created, **kwargs):
    """Notify onboarding managers when a new partner case is created."""
    if not created:
        return

    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification, resolve_raci_recipients

    org = instance.organization

    raci = resolve_raci_recipients(
        organization=org,
        process_key="partners.onboarding",
        fallback_users=_org_admin_users(org),
    )

    company_name = getattr(instance, "company_name", "") or ""
    case_number = getattr(instance, "case_number", "") or str(instance.pk)

    dispatch_workflow_notification(
        organization=org,
        event_key="partners_case_created",
        recipients=raci.all,
        context={
            "case_number": case_number,
            "partner_type": instance.get_partner_type_display() if hasattr(instance, "get_partner_type_display") else instance.partner_type,
            "company_name": company_name,
            "action_url": f"/partners/onboarding/{instance.id}",
        },
        link_url=f"/partners/onboarding/{instance.id}",
        fallback_channels=["in_app"],
        fallback_title=f"New Partner Onboarding Case — {company_name or case_number}",
        fallback_message=(
            f"A new partner onboarding case ({case_number}) has been created for "
            f"{company_name} ({instance.partner_type}). "
            f"The onboarding workflow has been initiated and is awaiting the first stage review."
        ),
        fallback_category=Notification.Category.PARTNER_ONBOARDING,
        fallback_severity=Notification.Severity.INFO,
    )


@receiver(post_save, sender="partners.PartnerOnboardingStageProgress")
def on_stage_completed(sender, instance, created, **kwargs):
    """Notify stakeholders when an onboarding stage is completed."""
    if instance.status != "completed":
        return

    if created:
        return

    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification, resolve_raci_recipients

    case = instance.case
    org = case.organization

    raci = resolve_raci_recipients(
        organization=org,
        process_key="partners.onboarding",
        fallback_users=_org_admin_users(org),
    )

    recipients = raci.all
    if case.created_by_id and case.created_by not in recipients:
        recipients.append(case.created_by)

    stage_name = (
        instance.template_stage.name
        if instance.template_stage_id and instance.template_stage
        else f"Stage Progress #{instance.id}"
    )

    dispatch_workflow_notification(
        organization=org,
        event_key="partners_stage_completed",
        recipients=recipients,
        context={
            "case_number": getattr(case, "case_number", str(case.pk)),
            "stage_name": stage_name,
            "next_stage": "",
            "action_url": f"/partners/onboarding/{case.id}",
        },
        link_url=f"/partners/onboarding/{case.id}",
        fallback_channels=["in_app"],
        fallback_title=f"Onboarding Stage Completed — {stage_name}",
        fallback_message=(
            f"The '{stage_name}' stage has been completed for onboarding case "
            f"{getattr(case, 'case_number', case.pk)}. "
            f"The next stage in the workflow is now ready for action."
        ),
        fallback_category=Notification.Category.PARTNER_ONBOARDING,
        fallback_severity=Notification.Severity.INFO,
    )
