import uuid

from django.contrib.auth import get_user_model
from django.db.backends.signals import connection_created
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Organization, UserProfile
from .org_name_utils import normalize_org_name
from .rls import reset_rls_context

User = get_user_model()


def _bootstrap_org_name_for_user(user: User) -> str:
    return f"Workspace-{user.pk}"


def _get_or_create_bootstrap_org_for_user(user: User) -> Organization:
    if user.is_superuser:
        # Assign superusers to the platform org
        platform_org = Organization.get_platform_org()
        if platform_org:
            return platform_org
        # Fallback: create platform org if it doesn't exist
        org, _ = Organization.objects.get_or_create(
            name="developerOS",
            defaults={"created_by": user, "is_platform_org": True},
        )
        return org

    bootstrap_name = _bootstrap_org_name_for_user(user)
    existing_owned = (
        Organization.objects
        .filter(created_by=user, name__startswith=bootstrap_name)
        .order_by("id")
        .first()
    )
    if existing_owned is not None:
        return existing_owned

    if not Organization.objects.filter(name=bootstrap_name).exists():
        return Organization.objects.create(name=bootstrap_name, created_by=user)

    # Name collision guard: ensure a fresh bootstrap org is created for this user
    # instead of attaching to a pre-existing workspace from unrelated data.
    while True:
        candidate = f"{bootstrap_name}-{uuid.uuid4().hex[:6]}"
        if not Organization.objects.filter(name=candidate).exists():
            return Organization.objects.create(name=candidate, created_by=user)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        organization = _get_or_create_bootstrap_org_for_user(instance)
        UserProfile.objects.get_or_create(
            user=instance,
            defaults={"organization": organization},
        )


@receiver(pre_save, sender=Organization)
def populate_normalized_name(sender, instance, **kwargs):
    instance.normalized_name = normalize_org_name(instance.name)


@receiver(pre_save, sender=UserProfile)
def ensure_user_profile_organization(sender, instance, **kwargs):
    """
    Guardrail: never persist a UserProfile without organization context.
    """
    if instance.organization_id is not None or instance.user_id is None:
        return
    user = instance.user if getattr(instance, "user", None) else User.objects.filter(pk=instance.user_id).first()
    if user is None:
        return
    instance.organization = _get_or_create_bootstrap_org_for_user(user)


@receiver(pre_save, sender=UserProfile)
def auto_generate_employee_id(sender, instance, **kwargs):
    """Auto-generate org-scoped employee_id (EMP-001, EMP-002, …) if blank."""
    if instance.employee_id or not instance.organization_id:
        return
    last = (
        UserProfile.objects
        .filter(organization_id=instance.organization_id)
        .exclude(employee_id="")
        .order_by("-employee_id")
        .values_list("employee_id", flat=True)
        .first()
    )
    if last and last.startswith("EMP-"):
        try:
            next_num = int(last.split("-", 1)[1]) + 1
        except (ValueError, IndexError):
            next_num = 1
    else:
        next_num = (
            UserProfile.objects
            .filter(organization_id=instance.organization_id)
            .exclude(pk=instance.pk)
            .count() + 1
        )
    instance.employee_id = f"EMP-{next_num:03d}"


@receiver(connection_created)
def initialize_rls_session(sender, connection, **kwargs):
    """
    Initialize per-connection RLS session vars for PostgreSQL connections.

    Request middleware switches this into strict tenant mode for regular users.
    """
    reset_rls_context(using=connection.alias, bypass=True)


# ---------------------------------------------------------------------------
# Notification signals
# ---------------------------------------------------------------------------

def _org_admin_recipients(organization):
    profiles = UserProfile.objects.filter(
        organization=organization, role="admin", user__is_active=True
    ).select_related("user")
    return [p.user for p in profiles]


@receiver(post_save, sender="accounts.Invitation")
def notify_invitation_sent(sender, instance, created, **kwargs):
    if not created:
        return
    from apps.notifications.services import Notification, dispatch_workflow_notification

    org = getattr(instance, "organization", None)
    if not org:
        return
    invitee_email = getattr(instance, "email", "")
    role = getattr(instance, "role_label", "") or getattr(instance, "job_title", "") or "team member"
    invited_by = getattr(instance, "invited_by", None)
    invited_by_name = invited_by.get_full_name() if invited_by else "An administrator"

    dispatch_workflow_notification(
        organization=org,
        event_key="invitation_sent",
        recipients=_org_admin_recipients(org),
        context={
            "invitee_email": invitee_email,
            "invited_by": invited_by_name,
            "role": role,
        },
        fallback_title="Team Invitation Sent",
        fallback_message=(
            f"{invited_by_name} has invited {invitee_email} to join the organization as a {role}."
        ),
        fallback_category=Notification.Category.SYSTEM,
    )


@receiver(post_save, sender="accounts.UserProfile")
def notify_user_joined_org(sender, instance, created, **kwargs):
    """Notify admins when a user's org changes from a bootstrap workspace to a real org."""
    if created:
        return
    from apps.notifications.services import Notification, dispatch_workflow_notification

    org = getattr(instance, "organization", None)
    if not org or org.name.startswith("Workspace-"):
        return
    user = getattr(instance, "user", None)
    if not user:
        return

    # Only fire if role just became 'member' or was recently set (new joiner)
    prev_role = getattr(instance, "_previous_role", None)
    if prev_role is not None:
        return  # Not a new join, just a role change

    # Skip notifying about the admin themselves
    admins = [a for a in _org_admin_recipients(org) if a.pk != user.pk]
    if not admins:
        return

    dispatch_workflow_notification(
        organization=org,
        event_key="user_joined_organization",
        recipients=admins,
        context={
            "user_name": user.get_full_name() or user.email,
            "user_email": user.email,
            "role": instance.role,
        },
        fallback_title="New Team Member Joined",
        fallback_message=(
            f"{user.get_full_name() or user.email} has joined the organization as {instance.role}."
        ),
        fallback_category=Notification.Category.SYSTEM,
    )


@receiver(post_save, sender="accounts.OrganizationSubscription")
def notify_subscription_change(sender, instance, created, **kwargs):
    from apps.notifications.services import Notification, dispatch_workflow_notification

    org = getattr(instance, "organization", None)
    if not org:
        return
    plan = getattr(instance, "plan_name", "") or getattr(instance, "plan_code", "") or "subscription"
    status = getattr(instance, "status", "")

    if created:
        title = "Subscription Activated"
        message = f"Your organization has been subscribed to the {plan} plan."
    else:
        title = "Subscription Updated"
        status_text = status.replace("_", " ").title() if status else "updated"
        message = f"Your {plan} subscription status has changed to {status_text}."

    dispatch_workflow_notification(
        organization=org,
        event_key="subscription_changed",
        recipients=_org_admin_recipients(org),
        context={"plan_name": plan, "status": status},
        fallback_title=title,
        fallback_message=message,
        fallback_category=Notification.Category.SYSTEM,
        fallback_severity=(
            Notification.Severity.WARNING
            if status in ("cancelled", "past_due", "expired")
            else Notification.Severity.INFO
        ),
    )


@receiver(post_save, sender="accounts.UserSecurityEvent")
def notify_critical_security_event(sender, instance, created, **kwargs):
    """Only notify on suspicious/critical security events, not every login."""
    if not created:
        return
    from apps.notifications.services import Notification, dispatch_workflow_notification

    event_type = getattr(instance, "event_type", "")
    status = getattr(instance, "status", "")

    # Only notify on failed events or suspicious patterns
    if status not in ("failed", "blocked"):
        return
    if event_type not in ("login_failed", "token_abuse", "privilege_escalation", "account_locked"):
        return

    user = getattr(instance, "user", None)
    org = None
    if user:
        profile = getattr(user, "profile", None)
        org = getattr(profile, "organization", None) if profile else None
    if not org:
        return

    detail = getattr(instance, "detail", "") or ""
    ip_address = getattr(instance, "ip_address", "") or "unknown IP"

    dispatch_workflow_notification(
        organization=org,
        event_key="security_alert",
        recipients=_org_admin_recipients(org),
        context={
            "event_type": event_type.replace("_", " ").title(),
            "user_email": user.email if user else "Unknown",
            "ip_address": ip_address,
        },
        fallback_title=f"Security Alert — {event_type.replace('_', ' ').title()}",
        fallback_message=(
            f"A {event_type.replace('_', ' ')} event was detected for "
            f"{user.email if user else 'an unknown user'} from {ip_address}."
            f"{f' {detail}' if detail else ''}"
        ),
        fallback_category=Notification.Category.SYSTEM,
        fallback_severity=Notification.Severity.CRITICAL,
    )
