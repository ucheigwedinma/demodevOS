"""
Investment returns metrics calculation (IRR, multiples, etc.)
"""
from datetime import date
from decimal import Decimal
from typing import NamedTuple


class CashFlow(NamedTuple):
    """Dated cash flow for IRR calculation."""

    date: date
    amount: Decimal  # Negative = investment, Positive = return


class InvestorReturns(NamedTuple):
    """Calculated returns metrics for an investor."""

    investor_name: str

    # Capital metrics
    capital_contributed: Decimal
    capital_returned: Decimal
    unreturned_capital: Decimal

    # Profit metrics
    profit_distributed: Decimal
    total_distributed: Decimal

    # Return multiples
    equity_multiple: Decimal | None  # Total distributed / contributed

    # Cash flows
    cash_flows: list[CashFlow]


def calculate_investor_returns(project_investor_id: int) -> InvestorReturns:
    """
    Calculate return metrics for a project investor.
    """
    from .models import ProjectInvestor

    pi = ProjectInvestor.objects.select_related("investor", "project").get(
        id=project_investor_id
    )

    # Get all cash flows (contributions + distributions)
    cash_flows = []

    # Contributions (negative cash flows)
    for contrib in pi.contributions.order_by("contribution_date"):
        cash_flows.append(
            CashFlow(
                date=contrib.contribution_date,
                amount=-contrib.amount,  # Negative = outflow
            )
        )

    # Distributions (positive cash flows)
    for dist in (
        pi.distributions.filter(distribution__status__in=["approved", "distributed"])
        .select_related("distribution")
        .order_by("distribution__distribution_date")
    ):
        cash_flows.append(
            CashFlow(
                date=dist.distribution.distribution_date,
                amount=dist.total_amount,  # Positive = inflow
            )
        )

    # Calculate equity multiple
    equity_multiple = None
    if pi.capital_contributed > 0:
        total_distributed = pi.total_capital_returned + pi.total_profit_distributed
        equity_multiple = (total_distributed / pi.capital_contributed).quantize(
            Decimal("0.01")
        )

    return InvestorReturns(
        investor_name=pi.investor.name,
        capital_contributed=pi.capital_contributed,
        capital_returned=pi.total_capital_returned,
        unreturned_capital=pi.unreturned_capital,
        profit_distributed=pi.total_profit_distributed,
        total_distributed=pi.total_capital_returned + pi.total_profit_distributed,
        equity_multiple=equity_multiple,
        cash_flows=cash_flows,
    )
