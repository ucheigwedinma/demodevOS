"""Celery tasks for the finance module."""
import logging
from decimal import Decimal

from celery import shared_task
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags

from apps.accounts.rls import iter_organization_ids, rls_context

logger = logging.getLogger(__name__)


def _send_weekly_budget_digest_for_org(*, organization_id: int, today):
    from apps.accounts.models import UserProfile
    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification

    from .budget_utils import get_actual_spent
    from .models import Budget

    active_budgets = list(
        Budget.objects.filter(
            organization_id=organization_id,
            status="active",
            start_date__lte=today,
            end_date__gte=today,
        ).prefetch_related("line_items__account", "organization")
    )
    if not active_budgets:
        return 0, 0, False

    digest_items = []
    for budget in active_budgets:
        lines = budget.line_items.select_related(
            "account", "department", "cost_center"
        )
        line_summaries = []
        total_budgeted = Decimal("0")
        total_spent = Decimal("0")
        warning_count = 0
        exceeded_count = 0

        for bli in lines:
            actual = get_actual_spent(bli)
            pct = (
                (actual / bli.budgeted_amount * Decimal("100"))
                if bli.budgeted_amount > 0
                else Decimal("0")
            )
            total_budgeted += bli.budgeted_amount
            total_spent += actual

            status_label = "ok"
            tolerance = Decimal("100") + budget.overspend_tolerance_pct
            if pct >= tolerance:
                status_label = "exceeded"
                exceeded_count += 1
            elif pct >= budget.warning_threshold_pct:
                status_label = "warning"
                warning_count += 1

            line_summaries.append({
                "account_code": bli.account.code,
                "account_name": bli.account.name,
                "department": bli.department.name if bli.department else "",
                "budgeted": bli.budgeted_amount,
                "actual": actual,
                "pct": pct,
                "status": status_label,
            })

        overall_pct = (
            (total_spent / total_budgeted * Decimal("100"))
            if total_budgeted > 0
            else Decimal("0")
        )
        digest_items.append({
            "budget": budget,
            "total_budgeted": total_budgeted,
            "total_spent": total_spent,
            "overall_pct": overall_pct,
            "warning_count": warning_count,
            "exceeded_count": exceeded_count,
            "lines": line_summaries,
        })

    profiles = UserProfile.objects.filter(
        organization_id=organization_id,
        user__is_active=True,
    ).select_related("user")
    recipients = [profile.user for profile in profiles]
    if not recipients:
        return 0, 0, True

    context = {
        "digest_items": digest_items,
        "digest_date": today,
        "frontend_url": getattr(settings, "FRONTEND_URL", ""),
    }
    html_body = render_to_string("emails/budget_digest.html", context)
    plain_body = strip_tags(html_body)

    dispatch_result = dispatch_workflow_notification(
        organization=active_budgets[0].organization,
        event_key="finance_weekly_budget_digest",
        recipients=recipients,
        context={
            "digest_date": today.strftime("%B %d, %Y"),
            "action_url": "/finance/budgets",
            "digest_text": plain_body,
            "digest_html": html_body,
        },
        link_url="/finance/budgets",
        fallback_channels=["in_app", "email"],
        fallback_title=f"Weekly Budget Digest — {today.strftime('%B %d, %Y')}",
        fallback_message=plain_body,
        fallback_category=Notification.Category.BUDGET_DIGEST,
        fallback_severity=Notification.Severity.INFO,
    )
    return (
        dispatch_result["notifications_sent"],
        dispatch_result["emails_sent"],
        True,
    )


@shared_task(name="finance.send_weekly_budget_digest")
def send_weekly_budget_digest():
    """Weekly digest: summarise active budgets and flag warning/exceeded lines.

    Sends digest notifications using centralized workflow templates.
    Scheduled every Monday 8 AM UTC via django-celery-beat.
    """
    today = timezone.now().date()
    notifications_created = 0
    emails_sent = 0
    orgs_with_data = 0

    for organization_id in iter_organization_ids():
        logger.info(
            "finance.weekly_budget_digest.start organization_id=%s date=%s",
            organization_id,
            today.isoformat(),
        )
        try:
            with rls_context(organization_id, bypass=False):
                sent_notifications, sent_emails, had_data = _send_weekly_budget_digest_for_org(
                    organization_id=organization_id,
                    today=today,
                )
        except Exception:
            logger.exception(
                "finance.weekly_budget_digest.failed organization_id=%s",
                organization_id,
            )
            raise

        notifications_created += sent_notifications
        emails_sent += sent_emails
        if had_data:
            orgs_with_data += 1
        logger.info(
            "finance.weekly_budget_digest.success organization_id=%s notifications=%s emails=%s had_data=%s",
            organization_id,
            sent_notifications,
            sent_emails,
            had_data,
        )

    if orgs_with_data == 0:
        logger.info("finance.weekly_budget_digest.no_data date=%s", today.isoformat())
        return "No active budgets — skipped."

    logger.info(
        "finance.weekly_budget_digest.complete date=%s orgs_with_data=%s notifications=%s emails=%s",
        today.isoformat(),
        orgs_with_data,
        notifications_created,
        emails_sent,
    )
    return (
        f"Digest sent: {notifications_created} notifications, "
        f"{emails_sent} emails across {orgs_with_data} organization(s)."
    )
