from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db.models import Case, IntegerField, Q, Value, When
from django.utils import timezone


def as_float_hours(value) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def format_sla_target_hours(value) -> str:
    hours = as_float_hours(value)

    if hours <= 0:
        return "0m"

    if hours < 1:
        return f"{int(round(hours * 60))}m"

    if hours % 24 == 0:
        days = int(hours // 24)
        return f"{days}d"

    whole_hours = int(hours)
    minutes = int(round((hours - whole_hours) * 60))

    if minutes == 0:
        return f"{whole_hours}h"
    if whole_hours == 0:
        return f"{minutes}m"
    return f"{whole_hours}h {minutes}m"


def select_ticket_sla_policy(ticket):
    from .models import SupportSlaPolicy

    category = getattr(ticket, "category", "") or ""
    priority = getattr(ticket, "priority", "") or ""

    queryset = SupportSlaPolicy.objects.filter(
        organization=ticket.organization,
        is_active=True,
    )

    queryset = queryset.filter(Q(category="") | Q(category=category))
    queryset = queryset.filter(Q(priority="") | Q(priority=priority))

    return (
        queryset
        .annotate(
            category_match=Case(
                When(category=category, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            ),
            priority_match=Case(
                When(priority=priority, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            ),
        )
        .order_by("-priority_match", "-category_match", "id")
        .first()
    )


def get_ticket_sla_targets(ticket):
    from .models import default_first_response_hours_for_priority, default_sla_hours_for_priority

    policy = select_ticket_sla_policy(ticket)

    if policy is None:
        return {
            "policy": None,
            "response_hours": float(
                default_first_response_hours_for_priority(ticket.priority),
            ),
            "resolution_hours": float(default_sla_hours_for_priority(ticket.priority)),
        }

    response_hours = as_float_hours(policy.response_target_hours)
    resolution_hours = as_float_hours(policy.resolution_target_hours)

    if response_hours <= 0:
        response_hours = float(default_first_response_hours_for_priority(ticket.priority))
    if resolution_hours <= 0:
        resolution_hours = float(default_sla_hours_for_priority(ticket.priority))

    return {
        "policy": policy,
        "response_hours": response_hours,
        "resolution_hours": resolution_hours,
    }


def sla_progress_percent(start_at, deadline_at, now=None) -> float:
    now = now or timezone.now()

    if deadline_at <= start_at:
        return 100.0

    elapsed_seconds = (now - start_at).total_seconds()
    total_seconds = (deadline_at - start_at).total_seconds()
    if total_seconds <= 0:
        return 100.0

    return round(max(0.0, (elapsed_seconds / total_seconds) * 100), 2)


def get_ticket_sla_timeline(ticket, *, now=None, targets=None):
    now = now or timezone.now()
    targets = targets or get_ticket_sla_targets(ticket)

    base_time = ticket.created_at or now
    response_deadline_at = base_time + timedelta(hours=targets["response_hours"])
    resolution_deadline_at = ticket.sla_deadline or (
        base_time + timedelta(hours=targets["resolution_hours"])
    )

    first_response_completed = ticket.first_response_at is not None
    if first_response_completed:
        response_progress_percent = 100.0
        first_response_breached = ticket.first_response_at > response_deadline_at
    else:
        response_progress_percent = sla_progress_percent(base_time, response_deadline_at, now)
        first_response_breached = now > response_deadline_at

    resolved_or_closed = ticket.status in {
        ticket.Status.RESOLVED,
        ticket.Status.CLOSED,
    }

    if resolved_or_closed:
        resolution_progress_percent = 100.0
        resolution_completed_at = ticket.resolved_at or ticket.closed_at or now
        resolution_breached = resolution_completed_at > resolution_deadline_at
    else:
        resolution_progress_percent = sla_progress_percent(base_time, resolution_deadline_at, now)
        resolution_breached = now > resolution_deadline_at

    return {
        "base_time": base_time,
        "response_deadline_at": response_deadline_at,
        "resolution_deadline_at": resolution_deadline_at,
        "response_progress_percent": response_progress_percent,
        "resolution_progress_percent": resolution_progress_percent,
        "first_response_breached": first_response_breached,
        "resolution_breached": resolution_breached,
    }
