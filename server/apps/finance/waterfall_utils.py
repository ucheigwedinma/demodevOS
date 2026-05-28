"""
Equity waterfall calculation utilities for project-level distributions.
"""
from decimal import Decimal
from typing import NamedTuple

from django.db import transaction
from django.utils import timezone


class InvestorAllocation(NamedTuple):
    """Result of waterfall calculation for a single investor."""

    project_investor_id: int
    investor_name: str
    ownership_pct: Decimal

    # Tier 1: Return of Capital
    unreturned_capital: Decimal  # Before this distribution
    tier1_capital_amount: Decimal  # This distribution

    # Tier 2: Profit Split
    profit_split_pct: Decimal  # Investor's share of Tier 2
    tier2_profit_amount: Decimal  # This distribution

    # Totals
    total_amount: Decimal
    capital_returned_to_date: Decimal  # After this distribution
    profit_distributed_to_date: Decimal  # After this distribution


class WaterfallCalculation(NamedTuple):
    """Complete waterfall calculation result."""

    total_amount: Decimal

    # Tier breakdown
    tier1_total: Decimal
    tier2_total: Decimal
    sponsor_amount: Decimal

    # Per-investor allocations
    allocations: list[InvestorAllocation]

    # Metadata
    calculation_summary: str


def calculate_waterfall(
    project_id: int,
    distribution_amount: Decimal,
) -> WaterfallCalculation:
    """
    Calculate 2-tier waterfall distribution for a project.

    Algorithm:
    1. Tier 1: Return unreturned capital pro-rata by ownership %
    2. Tier 2: Split remaining profits per waterfall config

    Args:
        project_id: Project ID
        distribution_amount: Total amount to distribute

    Returns:
        WaterfallCalculation with tier breakdown and investor allocations
    """
    from apps.projects.models import Project

    from .models import ProjectInvestor, WaterfallConfig

    project = Project.objects.get(id=project_id)

    # Get waterfall config (create default if doesn't exist)
    config, _ = WaterfallConfig.objects.get_or_create(
        project=project,
        defaults={
            "investor_profit_split_pct": Decimal("80.00"),
            "sponsor_profit_split_pct": Decimal("20.00"),
        },
    )

    # Get all active investors for this project
    project_investors = list(
        ProjectInvestor.objects.filter(project=project)
        .select_related("investor")
        .order_by("sort_order", "investor__name")
    )

    if not project_investors:
        raise ValueError(f"No investors found for project {project.name}")

    # Validate ownership sums to ~100%
    total_ownership = sum(pi.ownership_percentage for pi in project_investors)
    if not (Decimal("99.99") <= total_ownership <= Decimal("100.01")):
        raise ValueError(
            f"Investor ownership must sum to 100%, got {total_ownership}%"
        )

    remaining_pool = distribution_amount
    allocations = []

    # --- TIER 1: Return of Capital ---
    total_unreturned_capital = sum(pi.unreturned_capital for pi in project_investors)
    tier1_total = min(remaining_pool, total_unreturned_capital)

    for pi in project_investors:
        if pi.unreturned_capital <= 0 or tier1_total <= 0:
            tier1_amount = Decimal("0.00")
        else:
            # Pro-rata by unreturned capital
            weight = pi.unreturned_capital / total_unreturned_capital
            tier1_amount = (tier1_total * weight).quantize(Decimal("0.01"))

        # Can't return more than unreturned
        tier1_amount = min(tier1_amount, pi.unreturned_capital)

        allocations.append(
            {
                "project_investor": pi,
                "tier1_amount": tier1_amount,
                "tier2_amount": Decimal("0.00"),  # Filled in Tier 2
            }
        )

    remaining_pool -= tier1_total

    # --- TIER 2: Profit Split ---
    tier2_total = remaining_pool
    investor_tier2_pool = (
        tier2_total * config.investor_profit_split_pct / Decimal("100")
    ).quantize(Decimal("0.01"))
    sponsor_amount = tier2_total - investor_tier2_pool

    for i, pi in enumerate(project_investors):
        # Use custom split or project default
        profit_split_pct = (
            pi.custom_profit_split_pct
            if pi.custom_profit_split_pct is not None
            else config.investor_profit_split_pct
        )

        # Pro-rata by ownership percentage
        weight = pi.ownership_percentage / total_ownership
        tier2_amount = (investor_tier2_pool * weight).quantize(Decimal("0.01"))

        allocations[i]["tier2_amount"] = tier2_amount

    # Build final allocations
    final_allocations = []
    for alloc in allocations:
        pi = alloc["project_investor"]
        tier1 = alloc["tier1_amount"]
        tier2 = alloc["tier2_amount"]

        profit_split_pct = (
            pi.custom_profit_split_pct
            if pi.custom_profit_split_pct is not None
            else config.investor_profit_split_pct
        )

        final_allocations.append(
            InvestorAllocation(
                project_investor_id=pi.id,
                investor_name=pi.investor.name,
                ownership_pct=pi.ownership_percentage,
                unreturned_capital=pi.unreturned_capital,
                tier1_capital_amount=tier1,
                profit_split_pct=profit_split_pct,
                tier2_profit_amount=tier2,
                total_amount=tier1 + tier2,
                capital_returned_to_date=pi.total_capital_returned + tier1,
                profit_distributed_to_date=pi.total_profit_distributed + tier2,
            )
        )

    summary_lines = [
        f"Total Distribution: {distribution_amount:,.2f}",
        f"Tier 1 (Return of Capital): {tier1_total:,.2f}",
        f"Tier 2 (Profit Split): {tier2_total:,.2f}",
        f"  - To Investors ({config.investor_profit_split_pct}%): {investor_tier2_pool:,.2f}",
        f"  - To Sponsor ({config.sponsor_profit_split_pct}%): {sponsor_amount:,.2f}",
    ]

    return WaterfallCalculation(
        total_amount=distribution_amount,
        tier1_total=tier1_total,
        tier2_total=tier2_total,
        sponsor_amount=sponsor_amount,
        allocations=final_allocations,
        calculation_summary="\n".join(summary_lines),
    )


@transaction.atomic
def create_distribution(
    project_id: int,
    distribution_amount: Decimal,
    distribution_date,
    notes: str = "",
    created_by_user=None,
    organization=None,
):
    """
    Create a distribution record with calculated waterfall allocations.

    Returns:
        WaterfallDistribution instance with line items
    """
    from .models import DistributionLineItem, WaterfallDistribution

    # Calculate waterfall
    calc = calculate_waterfall(project_id, distribution_amount)

    # Create distribution header
    distribution = WaterfallDistribution.objects.create(
        project_id=project_id,
        organization=organization,
        total_amount=distribution_amount,
        distribution_date=distribution_date,
        tier1_capital_returned=calc.tier1_total,
        tier2_profit_split=calc.tier2_total,
        sponsor_amount=calc.sponsor_amount,
        status=WaterfallDistribution.Status.CALCULATED,
        notes=notes,
        created_by=created_by_user,
    )

    # Create line items
    for i, alloc in enumerate(calc.allocations):
        DistributionLineItem.objects.create(
            distribution=distribution,
            project_investor_id=alloc.project_investor_id,
            tier1_capital_amount=alloc.tier1_capital_amount,
            tier2_profit_amount=alloc.tier2_profit_amount,
            total_amount=alloc.total_amount,
            capital_returned_to_date=alloc.capital_returned_to_date,
            profit_distributed_to_date=alloc.profit_distributed_to_date,
            sort_order=i,
        )

    return distribution


@transaction.atomic
def approve_distribution(distribution_id: int, approved_by_user):
    """
    Approve a distribution and update investor cumulative totals.
    """
    from .models import WaterfallDistribution

    distribution = WaterfallDistribution.objects.get(id=distribution_id)

    if distribution.status != WaterfallDistribution.Status.CALCULATED:
        raise ValueError(
            f"Can only approve distributions in CALCULATED status, "
            f"got {distribution.status}"
        )

    # Update ProjectInvestor cumulative totals
    for line_item in distribution.line_items.select_related("project_investor"):
        pi = line_item.project_investor
        pi.total_capital_returned = line_item.capital_returned_to_date
        pi.total_profit_distributed = line_item.profit_distributed_to_date
        pi.save(
            update_fields=[
                "total_capital_returned",
                "total_profit_distributed",
                "updated_at",
            ]
        )

    # Mark distribution as approved
    distribution.status = WaterfallDistribution.Status.APPROVED
    distribution.approved_by = approved_by_user
    distribution.approved_at = timezone.now()
    distribution.save(
        update_fields=["status", "approved_by", "approved_at", "updated_at"]
    )

    return distribution
