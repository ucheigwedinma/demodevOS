"""
Budget utility functions: actual spend computation, threshold checking,
and reforecast generation.
"""
from datetime import timedelta
from decimal import Decimal

from django.db.models import Q, Sum
from django.utils import timezone


def get_actual_spent(budget_line_item):
    """Sum of approved/paid BillLineItem amounts matching this budget line's
    account (and optionally department/cost_center) within the budget date range."""
    from .models import BillLineItem

    budget = budget_line_item.budget
    filters = Q(
        account=budget_line_item.account,
        bill__issue_date__gte=budget.start_date,
        bill__issue_date__lte=budget.end_date,
        bill__status__in=["approved", "paid"],
    )
    if budget_line_item.department_id:
        filters &= Q(department=budget_line_item.department)
    if budget_line_item.cost_center_id:
        filters &= Q(cost_center=budget_line_item.cost_center)

    result = BillLineItem.objects.filter(filters).aggregate(total=Sum("amount"))
    return result["total"] or Decimal("0.00")


def check_budget_thresholds(bill_line_item):
    """Check if any active budget thresholds are crossed by this bill line item.
    Creates notifications for relevant users when thresholds are breached."""
    from apps.accounts.models import UserProfile
    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification

    from .models import BudgetLineItem

    account = bill_line_item.account
    if not account:
        return

    bill = bill_line_item.bill
    org = account.organization

    # Find matching budget line items in active budgets covering this bill's date
    budget_lines = BudgetLineItem.objects.filter(
        budget__status="active",
        budget__start_date__lte=bill.issue_date,
        budget__end_date__gte=bill.issue_date,
        account=account,
        budget__organization=org,
    ).select_related("budget")

    if bill_line_item.department_id:
        budget_lines = budget_lines.filter(
            Q(department=bill_line_item.department) | Q(department__isnull=True)
        )
    if bill_line_item.cost_center_id:
        budget_lines = budget_lines.filter(
            Q(cost_center=bill_line_item.cost_center) | Q(cost_center__isnull=True)
        )

    for bli in budget_lines:
        if bli.budgeted_amount <= 0:
            continue

        actual = get_actual_spent(bli)
        pct_used = (actual / bli.budgeted_amount * Decimal("100"))
        tolerance_threshold = Decimal("100") + bli.budget.overspend_tolerance_pct

        if pct_used >= tolerance_threshold:
            severity = Notification.Severity.CRITICAL
            category = Notification.Category.BUDGET_EXCEEDED
            event_key = "finance_budget_threshold_exceeded"
            title = f"Budget Threshold Exceeded — {account.code} {account.name}"
            message = (
                f"Spending on account {account.code} ({account.name}) has reached "
                f"{pct_used:.1f}% of the budgeted ₦{bli.budgeted_amount:,.2f} "
                f"in budget '{bli.budget.name}'. "
                f"Actual spend: ₦{actual:,.2f}. Immediate review and corrective action is required."
            )
        elif pct_used >= bli.budget.warning_threshold_pct:
            severity = Notification.Severity.WARNING
            category = Notification.Category.BUDGET_WARNING
            event_key = "finance_budget_threshold_warning"
            title = f"Budget Warning — {account.code} {account.name}"
            message = (
                f"Spending on account {account.code} ({account.name}) has reached "
                f"{pct_used:.1f}% of the budgeted ₦{bli.budgeted_amount:,.2f} "
                f"in budget '{bli.budget.name}'. "
                f"Actual spend: ₦{actual:,.2f}. Please monitor and plan expenditures accordingly."
            )
        else:
            continue

        link_url = f"/finance/budgets/{bli.budget.id}"

        # Dedup: skip if same notification exists in last 24h
        recent_cutoff = timezone.now() - timedelta(hours=24)

        # Get recipients: users in the org (all active users for now)
        profiles = UserProfile.objects.filter(
            organization=org,
            user__is_active=True,
        ).select_related("user")

        recipients_to_notify = []
        for profile in profiles:
            exists = Notification.objects.filter(
                recipient=profile.user,
                category=category,
                link_url=link_url,
                created_at__gte=recent_cutoff,
            ).exists()
            if not exists:
                recipients_to_notify.append(profile.user)

        if recipients_to_notify:
            dispatch_workflow_notification(
                organization=org,
                event_key=event_key,
                recipients=recipients_to_notify,
                context={
                    "account_code": account.code,
                    "account_name": account.name,
                    "percent_used": f"{pct_used:.1f}",
                    "budgeted_amount": f"{bli.budgeted_amount:,.2f}",
                    "actual_amount": f"{actual:,.2f}",
                    "budget_name": bli.budget.name,
                    "action_url": link_url,
                },
                link_url=link_url,
                fallback_channels=["in_app"],
                fallback_title=title,
                fallback_message=message,
                fallback_category=category,
                fallback_severity=severity,
            )


def generate_reforecast(budget_id):
    """Generate a proportional reforecast suggestion.

    Algorithm:
    1. For each budget line, compute actual_spent
    2. Lines where actual >= budgeted are 'locked' (keep at actual)
    3. Remaining budget = total_budget - sum(locked_actuals)
    4. Unlocked lines redistribute proportionally by original weight
    """
    from .models import Budget, ReforecastLineItem, ReforecastSuggestion

    budget = Budget.objects.get(id=budget_id)
    line_items = list(budget.line_items.select_related("account"))

    if not line_items:
        return None

    total_budget = budget.total_amount
    locked_total = Decimal("0")
    unlocked_lines = []
    line_data = []

    for bli in line_items:
        actual = get_actual_spent(bli)
        if actual >= bli.budgeted_amount:
            locked_total += actual
            line_data.append((bli, actual, actual))
        else:
            unlocked_lines.append((bli, actual))
            line_data.append((bli, actual, None))

    remaining_pool = max(total_budget - locked_total, Decimal("0"))
    total_unlocked_budgeted = sum(
        bli.budgeted_amount for bli, _ in unlocked_lines
    )

    locked_count = len(line_items) - len(unlocked_lines)
    reforecast = ReforecastSuggestion.objects.create(
        budget=budget,
        reason=(
            f"Auto-generated proportional redistribution. "
            f"{locked_count} line(s) at or over budget. "
            f"Remaining pool: {remaining_pool:,.2f}."
        ),
    )

    for bli, actual, suggested in line_data:
        if suggested is not None:
            ReforecastLineItem.objects.create(
                reforecast=reforecast,
                budget_line_item=bli,
                current_amount=bli.budgeted_amount,
                suggested_amount=suggested,
                actual_spent=actual,
                delta=suggested - bli.budgeted_amount,
            )
        else:
            weight = (
                bli.budgeted_amount / total_unlocked_budgeted
                if total_unlocked_budgeted > 0
                else Decimal("0")
            )
            new_amount = (remaining_pool * weight).quantize(Decimal("0.01"))
            ReforecastLineItem.objects.create(
                reforecast=reforecast,
                budget_line_item=bli,
                current_amount=bli.budgeted_amount,
                suggested_amount=new_amount,
                actual_spent=actual,
                delta=new_amount - bli.budgeted_amount,
            )

    return reforecast
