"""IAM audit-event emission helper.

Centralised producer for the org-scoped audit feed surfaced under
client/src/routes/settings/audit/*. All emits land in
``UserSecurityEvent``; the consumer side (frontend pages, list endpoint)
filters that table by ``event_type``, ``severity``, and date.

Why a single helper:
  - Easy to grep for emit sites.
  - Easy to add cross-cutting behaviour later (Celery dispatch,
    structured-logging shadow, retention enforcement) without
    touching every call site.

Use from any view / serializer / task:

    from apps.accounts.audit import audit_emit
    from apps.accounts.models import UserSecurityEvent

    audit_emit(
        event_type=UserSecurityEvent.EventType.PASSWORD_POLICY_CHANGED,
        request=request,
        target_type="organization",
        target_id=str(org.id),
        detail="Min length raised from 10 to 14",
    )

The helper extracts ip / user_agent / user / organization from the
request when given one; you can also pass them explicitly for callers
without a request (e.g. Celery tasks).

In addition to writing the audit row, the helper queues outbound
webhook deliveries for any matching subscriptions (see Webhook model).
That dispatch runs through Celery — the audit emit is never blocked
by webhook latency.
"""

from __future__ import annotations

from typing import Any, Optional

from django.contrib.auth import get_user_model

from apps.accounts.security import extract_client_ip, extract_user_agent

User = get_user_model()


def audit_emit(
    *,
    event_type: str,
    user=None,
    organization=None,
    principal: str = "",
    status: str = "info",
    severity: str = "low",
    provider: str = "",
    request=None,
    target_type: str = "",
    target_id: str = "",
    detail: str = "",
    metadata: Optional[dict[str, Any]] = None,
):
    """Create a UserSecurityEvent row.

    Returns the created instance. Always best-effort: callers do not
    need to wrap in try/except — exceptions are logged but not
    re-raised, since failing to emit an audit event must never break
    the originating action.
    """
    from apps.accounts.models import UserSecurityEvent
    import logging

    logger = logging.getLogger(__name__)

    try:
        # Default user / organization from the request if available
        if request is not None:
            if user is None and getattr(request, "user", None) and request.user.is_authenticated:
                user = request.user
            if organization is None and user is not None:
                profile = getattr(user, "profile", None)
                organization = getattr(profile, "organization", None) if profile else None

        ip = extract_client_ip(request) if request is not None else None
        ua = extract_user_agent(request) if request is not None else ""

        evt = UserSecurityEvent.objects.create(
            user=user,
            organization=organization,
            principal=principal or (user.email if user and getattr(user, "email", None) else ""),
            event_type=event_type,
            status=status,
            severity=severity,
            provider=provider,
            ip_address=ip,
            user_agent=ua or "",
            target_type=target_type,
            target_id=str(target_id) if target_id else "",
            detail=detail,
            metadata=metadata or {},
        )

        # Fan out to any matching webhooks. Best-effort: dispatch
        # failures are logged but never block the audit emit.
        if organization is not None:
            try:
                _dispatch_webhooks(organization, event_type, evt)
            except Exception:
                logger.exception("audit_emit: webhook dispatch failed for event_type=%s", event_type)

        return evt
    except Exception:
        logger.exception("audit_emit failed: event_type=%s target=%s/%s", event_type, target_type, target_id)
        return None


def _dispatch_webhooks(organization, event_type: str, event_row) -> None:
    """Find webhooks subscribed to this event_type (or all events) and
    queue Celery deliver tasks for each."""
    from apps.accounts.models import Webhook
    from apps.accounts.tasks import deliver_webhook

    qs = Webhook.objects.filter(organization=organization, is_active=True)

    matching = []
    for w in qs:
        events = w.events or []
        if not events:  # empty subscription = subscribe to all events
            matching.append(w)
            continue
        if event_type in events:
            matching.append(w)
            continue
        # Wildcard prefix match: "access_request.*" matches "access_request_approved", etc.
        for pattern in events:
            if pattern.endswith(".*") and event_type.startswith(pattern[:-2]):
                matching.append(w)
                break

    if not matching:
        return

    payload = {
        "event": event_type,
        "audit_event_id": event_row.id,
        "organization_id": organization.id,
        "occurred_at": event_row.occurred_at.isoformat(),
        "actor": {
            "id": event_row.user_id,
            "email": event_row.user.email if event_row.user_id and event_row.user else None,
            "principal": event_row.principal,
        },
        "target": {
            "type": event_row.target_type,
            "id": event_row.target_id,
        },
        "detail": event_row.detail,
        "metadata": event_row.metadata or {},
        "severity": event_row.severity,
        "status": event_row.status,
    }

    for w in matching:
        try:
            deliver_webhook.delay(w.id, event_type, payload)
        except Exception:
            logger.exception("audit_emit: deliver_webhook.delay failed for webhook_id=%s", w.id)
