import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.notifications.services import Notification, dispatch_workflow_notification

logger = logging.getLogger(__name__)


def _org_admin_recipients(organization):
    from apps.accounts.models import UserProfile

    profiles = UserProfile.objects.filter(
        organization=organization, role="admin", user__is_active=True
    ).select_related("user")
    return [p.user for p in profiles]


@receiver(post_save, sender="valuations.ComparableSale")
def notify_comparable_sale_created(sender, instance, created, **kwargs):
    if not created:
        return
    org = getattr(instance, "organization", None)
    if not org:
        return
    prop = getattr(instance, "property", None)
    prop_name = getattr(prop, "name", "") if prop else ""
    sale_price = getattr(instance, "sale_price", None)
    sale_date = getattr(instance, "sale_date", None)

    price_text = f" for {sale_price:,.2f}" if sale_price else ""
    date_text = f" on {sale_date.strftime('%b %d, %Y')}" if sale_date else ""

    dispatch_workflow_notification(
        organization=org,
        event_key="valuation_comparable_added",
        recipients=_org_admin_recipients(org),
        context={
            "property_name": prop_name,
            "sale_price": str(sale_price) if sale_price else "",
        },
        fallback_title="Comparable Sale Recorded",
        fallback_message=(
            f"A new comparable sale has been recorded"
            f"{f' for {prop_name}' if prop_name else ''}"
            f"{price_text}{date_text}. "
            f"This data will be used in future property valuations."
        ),
        fallback_category=Notification.Category.SYSTEM,
    )


@receiver(post_save, sender="valuations.ValuationAppeal")
def notify_valuation_appeal_created(sender, instance, created, **kwargs):
    if not created:
        return
    org = getattr(instance, "organization", None)
    if not org:
        return
    reason = getattr(instance, "reason", "") or ""
    status = getattr(instance, "status", "pending")
    snippet = (reason[:100] + "...") if len(reason) > 100 else reason

    dispatch_workflow_notification(
        organization=org,
        event_key="valuation_appeal_filed",
        recipients=_org_admin_recipients(org),
        context={
            "appeal_reason": snippet,
            "status": status,
        },
        fallback_title="Valuation Appeal Filed",
        fallback_message=(
            f"A valuation appeal has been filed and is pending review."
            f"{f' Reason: {snippet}' if snippet else ''}"
        ),
        fallback_category=Notification.Category.SYSTEM,
        fallback_severity=Notification.Severity.WARNING,
    )
