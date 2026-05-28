import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


def _org_admin_recipients(organization):
    from apps.accounts.models import UserProfile

    profiles = UserProfile.objects.filter(
        organization=organization, role="admin", user__is_active=True
    ).select_related("user")
    return [p.user for p in profiles]


@receiver(post_save, sender="compliance.ComplianceViolation")
def on_compliance_violation_change_sync_project_costs(sender, instance, **kwargs):
    """Sync permit-fee costs into project tracking."""
    from apps.finance.cost_tracking_hooks import sync_compliance_permit_fee_cost

    sync_compliance_permit_fee_cost(instance)


@receiver(post_delete, sender="compliance.ComplianceViolation")
def on_compliance_violation_delete_remove_project_costs(sender, instance, **kwargs):
    """Remove hook-generated permit-fee costs when violation is deleted."""
    from apps.finance.cost_tracking_hooks import delete_compliance_permit_fee_cost

    delete_compliance_permit_fee_cost(instance)


@receiver(post_save, sender="compliance.ComplianceViolation")
def notify_compliance_violation(sender, instance, created, **kwargs):
    if not created:
        return
    from apps.notifications.services import Notification, dispatch_workflow_notification

    org = getattr(instance, "organization", None)
    if not org:
        prop_compliance = getattr(instance, "property_compliance", None)
        if prop_compliance:
            prop = getattr(prop_compliance, "property", None)
            org = getattr(prop, "organization", None) if prop else None
    if not org:
        return

    severity = getattr(instance, "severity", "medium")
    description = getattr(instance, "description", "") or ""
    snippet = (description[:100] + "...") if len(description) > 100 else description
    requirement = getattr(instance, "requirement", None)
    req_name = getattr(requirement, "name", "") if requirement else ""

    dispatch_workflow_notification(
        organization=org,
        event_key="compliance_violation_reported",
        recipients=_org_admin_recipients(org),
        context={
            "severity": severity,
            "requirement": req_name,
            "description": snippet,
        },
        fallback_title=f"Compliance Violation — {severity.title()} Severity",
        fallback_message=(
            f"A {severity.lower()}-severity compliance violation has been recorded"
            f"{f' for {req_name}' if req_name else ''}."
            f"{f' {snippet}' if snippet else ''}"
        ),
        fallback_category=Notification.Category.SYSTEM,
        fallback_severity=(
            Notification.Severity.CRITICAL
            if severity in ("high", "critical")
            else Notification.Severity.WARNING
        ),
    )


@receiver(post_save, sender="compliance.ComplianceAudit")
def notify_compliance_audit(sender, instance, created, **kwargs):
    if not created:
        return
    from apps.notifications.services import Notification, dispatch_workflow_notification

    org = getattr(instance, "organization", None)
    if not org:
        return

    audit_type = getattr(instance, "audit_type", "internal").replace("_", " ").title()
    auditor = getattr(instance, "auditor_name", "") or getattr(instance, "auditor", "")
    scheduled_date = getattr(instance, "scheduled_date", None)
    date_text = f" scheduled for {scheduled_date.strftime('%b %d, %Y')}" if scheduled_date else ""

    dispatch_workflow_notification(
        organization=org,
        event_key="compliance_audit_scheduled",
        recipients=_org_admin_recipients(org),
        context={
            "audit_type": audit_type,
            "auditor": str(auditor),
            "scheduled_date": str(scheduled_date) if scheduled_date else "",
        },
        fallback_title=f"{audit_type} Compliance Audit Created",
        fallback_message=(
            f"A new {audit_type.lower()} compliance audit has been created"
            f"{f' by {auditor}' if auditor else ''}{date_text}."
        ),
        fallback_category=Notification.Category.SYSTEM,
    )
