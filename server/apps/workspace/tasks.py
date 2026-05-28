"""
Celery tasks for the workspace teams feature.

`send_team_digests` runs hourly via Celery beat. Each invocation determines
which orgs are currently at 08:00 local time and dispatches digests for the
active memberships in those orgs whose `digest_frequency='daily'`.

The hourly cadence is intentional: it lets us cover all timezones with one
beat schedule. Within an org, digests are bucketed and each membership emits
at most one digest per day (idempotency tracked via the `Notification`
table — we look back 23 hours to avoid double-send on edge cases).
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Iterable, List
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

DIGEST_LOCAL_HOUR = 8  # 08:00 in the org's local timezone
LOOKBACK_WINDOW_HOURS = 24


def _org_local_hour(org) -> int | None:
    """Return the current hour (0-23) in the org's timezone, or None on miss."""
    tz_name = (getattr(org, "timezone", "") or "UTC").strip() or "UTC"
    try:
        tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        logger.warning("Org %s has invalid timezone %r — falling back to UTC", org.id, tz_name)
        tz = ZoneInfo("UTC")
    return timezone.now().astimezone(tz).hour


def _build_ticket_digest(team) -> dict:
    """
    Build the SupportTicket activity slice for one team over the last 24h.
    Returns a dict shaped for the digest email body. Empty when nothing happened.
    """
    try:
        from apps.support_desk.models import SupportTicket
    except Exception:
        return {"opened": [], "resolved_count": 0, "escalated": []}

    cutoff = timezone.now() - timedelta(hours=LOOKBACK_WINDOW_HOURS)
    qs = SupportTicket.objects.filter(team=team)

    opened = list(
        qs.filter(created_at__gte=cutoff).values("id", "ticket_id", "subject", "priority")[:3]
    )
    resolved_count = qs.filter(
        status=SupportTicket.Status.RESOLVED,
        updated_at__gte=cutoff,
    ).count()
    escalated = list(
        qs.filter(
            status=SupportTicket.Status.ESCALATED,
            updated_at__gte=cutoff,
        ).values("id", "ticket_id", "subject")[:3]
    )

    return {
        "opened": opened,
        "opened_count": qs.filter(created_at__gte=cutoff).count(),
        "resolved_count": resolved_count,
        "escalated": escalated,
        "escalated_count": qs.filter(
            status=SupportTicket.Status.ESCALATED,
            updated_at__gte=cutoff,
        ).count(),
    }


def _digest_is_empty(digest: dict) -> bool:
    return (
        not digest.get("opened")
        and digest.get("resolved_count", 0) == 0
        and not digest.get("escalated")
    )


@shared_task(name="workspace.send_team_digests")
def send_team_digests() -> dict:
    """
    Entry point. Iterates every Organization, identifies the ones at 08:00
    local time, and emits one Notification per active daily-digest membership.

    Returns a small summary dict for observability.
    """
    from apps.accounts.models import Organization
    from apps.notifications.models import Notification

    from .models import Team, TeamMembership

    summary = {"orgs_in_window": 0, "memberships_processed": 0, "digests_sent": 0, "skipped_empty": 0}

    for org in Organization.objects.all().iterator():
        local_hour = _org_local_hour(org)
        if local_hour != DIGEST_LOCAL_HOUR:
            continue
        summary["orgs_in_window"] += 1

        memberships = (
            TeamMembership.objects.filter(
                team__organization=org,
                team__is_archived=False,
                digest_frequency=TeamMembership.DigestFrequency.DAILY,
                user__is_active=True,
            )
            .select_related("team", "user")
        )

        for membership in memberships.iterator():
            summary["memberships_processed"] += 1
            digest = _build_ticket_digest(membership.team)
            if _digest_is_empty(digest):
                summary["skipped_empty"] += 1
                continue
            try:
                _send_digest_notification(membership, digest)
                summary["digests_sent"] += 1
            except Exception:
                # Per design: log, don't retry. The next day's digest will
                # cover any missed activity (the user is unlikely to care
                # about yesterday's digest if today's covers the same window).
                logger.exception(
                    "Failed to send digest to user=%s team=%s",
                    membership.user_id,
                    membership.team_id,
                )

    return summary


def _send_digest_notification(membership, digest: dict) -> None:
    """Materialise the digest as an in-app Notification row."""
    from apps.notifications.models import Notification

    parts = []
    if digest.get("opened_count"):
        parts.append(f"{digest['opened_count']} new ticket(s)")
    if digest.get("resolved_count"):
        parts.append(f"{digest['resolved_count']} resolved")
    if digest.get("escalated_count"):
        parts.append(f"{digest['escalated_count']} escalated")
    summary_line = ", ".join(parts) or "Recent activity"

    Notification.objects.create(
        recipient=membership.user,
        organization=membership.team.organization,
        title=f"{membership.team.name} — daily digest",
        message=summary_line,
        category=Notification.Category.SYSTEM,
        severity=Notification.Severity.INFO,
        link_url=f"/teams/{membership.team_id}",
    )
