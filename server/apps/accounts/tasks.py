import logging
import secrets
import string
from datetime import timedelta

from celery import shared_task
from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


def _generate_password(length: int = 14) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


@shared_task(bind=True, max_retries=2, acks_late=True)
def provision_demo_org_task(self, demo_request_id: int):
    from apps.settings.models import PlatformEdition

    from .models import DemoRequest, Organization, OrganizationSubscription, UserProfile

    demo_request = DemoRequest.objects.get(pk=demo_request_id)
    demo_request.status = DemoRequest.Status.PROVISIONING
    demo_request.save(update_fields=["status"])

    try:
        password = _generate_password()

        with transaction.atomic():
            # 1. Create Organization
            org = Organization.objects.create(
                name=f"{demo_request.company_name} (Demo)",
                size=demo_request.company_size,
                subscription_tier=Organization.SubscriptionTier.SCALE,
            )

            # 2. Create OrganizationSubscription (14-day trial)
            now = timezone.now()
            edition = PlatformEdition.objects.filter(key="scale").first()
            if edition is None:
                edition = PlatformEdition.objects.order_by("-tier_level").first()

            OrganizationSubscription.objects.create(
                organization=org,
                edition=edition,
                status=OrganizationSubscription.Status.TRIALING,
                trial_start=now,
                trial_end=now + timedelta(days=14),
                current_period_start=now,
                current_period_end=now + timedelta(days=14),
            )

            # 3. Create User
            name_parts = demo_request.full_name.strip().split(None, 1)
            first_name = name_parts[0] if name_parts else "Demo"
            last_name = name_parts[1] if len(name_parts) > 1 else ""

            user = User.objects.create_user(
                username=demo_request.email,
                email=demo_request.email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                is_active=True,
            )

            # 4. Set up UserProfile
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.organization = org
            profile.role = "admin"
            profile.is_demo_account = True
            profile.has_completed_tour = False
            profile.has_completed_onboarding = False
            profile.save()

            # 5. Link demo request
            demo_request.provisioned_organization = org
            demo_request.provisioned_user = user
            demo_request.status = DemoRequest.Status.PROVISIONED
            demo_request.provisioned_at = timezone.now()
            demo_request.save(update_fields=[
                "provisioned_organization",
                "provisioned_user",
                "status",
                "provisioned_at",
            ])

        # 6. Run seed commands (outside transaction — idempotent)
        #    Global seeds first, then org-scoped seeds targeting the new demo org.
        oid = [org.id]
        seed_commands = [
            # Global / system-wide
            ("seed_rbac", {}),
            ("seed_feature_flags", {}),
            ("seed_platform_editions", {}),
            # Org-scoped demo data
            ("seed_finance_demo", {"year": 2025}),
            ("seed_finance_demo", {}),
            ("seed_crm_demo", {"leads": 96, "organization_ids": oid}),
            ("seed_properties_demo", {"org_ids": oid}),
            ("seed_projects_demo", {"org_ids": oid}),
            ("seed_procurement_demo", {"org_ids": oid}),
            ("seed_partner_onboarding_templates", {"organization_id": org.id}),
            ("seed_partners_demo", {"org_ids": oid}),
        ]
        for cmd, kwargs in seed_commands:
            try:
                call_command(cmd, **kwargs)
            except Exception:
                logger.warning(
                    "demo_provision.seed_command_failed cmd=%s demo_request_id=%s",
                    cmd, demo_request_id, exc_info=True,
                )

        # 7. Send credentials email
        from .emails import send_demo_credentials_email

        trial_end = now + timedelta(days=14)
        send_demo_credentials_email(user, password, trial_end)

        logger.info(
            "demo_provision.success demo_request_id=%s org_id=%s user_id=%s",
            demo_request_id, org.id, user.id,
        )

    except Exception as exc:
        demo_request.status = DemoRequest.Status.FAILED
        demo_request.error_message = str(exc)[:4000]
        demo_request.save(update_fields=["status", "error_message"])

        logger.exception(
            "demo_provision.failed demo_request_id=%s", demo_request_id,
        )

        countdown = min(30 * (2 ** self.request.retries), 300)
        raise self.retry(exc=exc, countdown=countdown) from exc


@shared_task
def sweep_expired_access_grants():
    """Clear UserProfile.assigned_role on profiles whose
    assigned_role_valid_until is in the past, and mark the corresponding
    AccessRequest (if any) as REVOKED with an auto-expired note.

    Called daily by Celery Beat (CELERY_BEAT_SCHEDULE entry
    "iam-sweep-expired-access-grants"). Also safe to run on demand:
        python manage.py shell -c "from apps.accounts.tasks import sweep_expired_access_grants; sweep_expired_access_grants()"
    """
    from .models import AccessRequest, UserProfile

    now = timezone.now()
    expired_profiles = list(
        UserProfile.objects.filter(
            assigned_role__isnull=False,
            assigned_role_valid_until__isnull=False,
            assigned_role_valid_until__lte=now,
        ).select_related("user")
    )

    cleared = 0
    request_revocations = 0

    from .audit import audit_emit
    from .models import UserSecurityEvent

    for profile in expired_profiles:
        prior_role_id = profile.assigned_role_id
        audit_emit(
            event_type=UserSecurityEvent.EventType.ACCESS_GRANT_AUTO_REVOKED,
            user=profile.user,
            organization=profile.organization,
            status=UserSecurityEvent.Status.INFO,
            severity=UserSecurityEvent.Severity.MEDIUM,
            target_type="role",
            target_id=str(prior_role_id) if prior_role_id else "",
            detail="Temporary access window expired; assigned role cleared by sweeper.",
            metadata={"valid_until": profile.assigned_role_valid_until.isoformat() if profile.assigned_role_valid_until else None},
        )
        profile.assigned_role = None
        profile.assigned_role_valid_until = None
        profile.save(update_fields=["assigned_role", "assigned_role_valid_until"])
        cleared += 1

        # Mark related approved access requests as auto-revoked so the
        # audit trail and UI reflect the expiry.
        related = AccessRequest.objects.filter(
            requester=profile.user,
            organization=profile.organization,
            status=AccessRequest.Status.APPROVED,
            requested_role_id=prior_role_id,
            granted_valid_until__lte=now,
        )
        for ar in related:
            note = f"Auto-revoked at {now.isoformat()}: grant window expired."
            ar.status = AccessRequest.Status.REVOKED
            ar.approval_notes = (
                (ar.approval_notes + "\n---\n" if ar.approval_notes else "") + note
            )
            ar.save(update_fields=["status", "approval_notes", "updated_at"])
            request_revocations += 1

    logger.info(
        "iam.sweep_expired_access_grants cleared=%d revoked_requests=%d",
        cleared, request_revocations,
    )
    return {"cleared": cleared, "revoked_requests": request_revocations}


@shared_task(
    bind=True,
    max_retries=5,
    acks_late=True,
    autoretry_for=(Exception,),
    retry_backoff=True,        # 2, 4, 8, 16, 32 seconds
    retry_backoff_max=600,
    retry_jitter=True,
)
def deliver_webhook(self, webhook_id: int, event_name: str, payload: dict):
    """Deliver one event to one webhook with HMAC signing + retry.

    Each attempt records (or updates) a WebhookDelivery row so the UI
    can show full history. The task itself retries on any exception
    (network errors, non-2xx responses, timeouts) with exponential
    backoff up to 5 attempts.
    """
    import hashlib
    import hmac
    import json as _json
    import requests
    from .models import Webhook, WebhookDelivery

    try:
        webhook = Webhook.objects.get(id=webhook_id, is_active=True)
    except Webhook.DoesNotExist:
        logger.info("deliver_webhook: webhook_id=%s not found / inactive — skip", webhook_id)
        return {"skipped": True}

    body = _json.dumps(payload).encode("utf-8")
    signature = hmac.new(
        (webhook.secret or "").encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest() if webhook.secret else ""

    attempt = (self.request.retries or 0) + 1
    delivery = WebhookDelivery.objects.create(
        webhook=webhook,
        event_name=event_name,
        payload=payload,
        status=WebhookDelivery.Status.PENDING,
        attempt_number=attempt,
    )

    try:
        resp = requests.post(
            webhook.url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "X-DeveloperOS-Event": event_name,
                "X-DeveloperOS-Signature": f"sha256={signature}",
                "X-DeveloperOS-Delivery": str(delivery.id),
                "X-DeveloperOS-Attempt": str(attempt),
                "User-Agent": "DeveloperOS-Webhook/1.0",
            },
            timeout=10,
        )
        ok = 200 <= resp.status_code < 300
        delivery.response_code = resp.status_code
        delivery.response_body = (resp.text or "")[:2000]
        delivery.status = WebhookDelivery.Status.DELIVERED if ok else WebhookDelivery.Status.FAILED
        delivery.delivered_at = timezone.now() if ok else None
        delivery.save()

        webhook.last_delivery_at = timezone.now()
        webhook.last_delivery_status = "delivered" if ok else "failed"
        webhook.last_delivery_message = f"HTTP {resp.status_code}"
        webhook.delivery_count = (webhook.delivery_count or 0) + 1
        if not ok:
            webhook.failure_count = (webhook.failure_count or 0) + 1
        webhook.save(update_fields=[
            "last_delivery_at", "last_delivery_status",
            "last_delivery_message", "delivery_count", "failure_count",
            "updated_at",
        ])

        if not ok:
            # Trigger retry by raising; Celery handles backoff.
            raise RuntimeError(f"Webhook returned non-2xx: {resp.status_code}")

        logger.info("deliver_webhook: webhook_id=%s event=%s ok=%s code=%s", webhook_id, event_name, ok, resp.status_code)
        return {"ok": True, "response_code": resp.status_code}

    except requests.exceptions.RequestException as exc:
        # Network errors — record + re-raise for retry
        err = str(exc)[:500]
        delivery.status = WebhookDelivery.Status.FAILED
        delivery.error_message = err
        delivery.save(update_fields=["status", "error_message"])

        webhook.last_delivery_at = timezone.now()
        webhook.last_delivery_status = "failed"
        webhook.last_delivery_message = err[:200]
        webhook.delivery_count = (webhook.delivery_count or 0) + 1
        webhook.failure_count = (webhook.failure_count or 0) + 1
        webhook.save(update_fields=[
            "last_delivery_at", "last_delivery_status",
            "last_delivery_message", "delivery_count", "failure_count",
            "updated_at",
        ])
        raise
