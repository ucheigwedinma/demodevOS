"""
Backfill analytics metric snapshots.

Usage:
    python manage.py backfill_metric_snapshots --type all --days 30
    python manage.py backfill_metric_snapshots --type portfolio --days 7 --organization-id 42
    python manage.py backfill_metric_snapshots --type board --days 1
"""

import logging
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.rls import iter_organization_ids, rls_context
from apps.analytics.computations import (
    compute_full_board_kpis,
    compute_full_portfolio_snapshot,
)
from apps.analytics.models import BoardKpiSnapshot, PortfolioSnapshot

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Backfill analytics metric snapshots for a date range."

    def add_arguments(self, parser):
        parser.add_argument(
            "--type",
            choices=["portfolio", "board", "all"],
            default="all",
            help="Which snapshot type to backfill (default: all).",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Number of days to backfill (default: 30).",
        )
        parser.add_argument(
            "--organization-id",
            type=int,
            help="Backfill for a single organization only.",
        )

    def handle(self, *args, **options):
        snapshot_type = options["type"]
        days = max(1, options["days"])
        single_org_id = options.get("organization_id")
        now = timezone.now()
        today = now.date()

        org_ids = [single_org_id] if single_org_id else list(iter_organization_ids())

        if snapshot_type in ("portfolio", "all"):
            self._backfill_portfolio(org_ids, today, days, now)

        if snapshot_type in ("board", "all"):
            self._backfill_board(org_ids, today, days, now)

        self.stdout.write(self.style.SUCCESS("Backfill complete."))

    def _backfill_portfolio(self, org_ids, today, days, now):
        total = 0
        for org_id in org_ids:
            for offset in range(days):
                target_date = today - timedelta(days=offset)
                try:
                    with rls_context(org_id, bypass=False):
                        data = compute_full_portfolio_snapshot(org_id)
                        PortfolioSnapshot.objects.update_or_create(
                            organization_id=org_id,
                            snapshot_date=target_date,
                            defaults={**data, "computed_at": now},
                        )
                    total += 1
                except Exception:
                    logger.exception(
                        "backfill.portfolio.failed org_id=%s date=%s",
                        org_id, target_date.isoformat(),
                    )
        self.stdout.write(f"  Portfolio snapshots upserted: {total}")

    def _backfill_board(self, org_ids, today, days, now):
        total = 0
        for org_id in org_ids:
            for offset in range(days):
                target_date = today - timedelta(days=offset)
                snapshot_hour = timezone.make_aware(
                    datetime.combine(target_date, datetime.min.time())
                )
                end_date = target_date
                start_date = end_date - timedelta(days=180)
                try:
                    with rls_context(org_id, bypass=False):
                        data = compute_full_board_kpis(org_id, start_date, end_date)
                        BoardKpiSnapshot.objects.update_or_create(
                            organization_id=org_id,
                            snapshot_hour=snapshot_hour,
                            defaults={
                                "procurement_cycle_time_days": data["procurement_cycle_time_days"],
                                "cost_variance_per_project_pct": data["cost_variance_per_project_pct"],
                                "vendor_reliability_score": data["vendor_reliability_score"],
                                "emergency_purchases_pct": data["emergency_purchases_pct"],
                                "budget_overrun_frequency_pct": data["budget_overrun_frequency_pct"],
                                "average_approval_time_hours": data["average_approval_time_hours"],
                                "period_start": data["period_start"],
                                "period_end": data["period_end"],
                                "computed_at": now,
                            },
                        )
                    total += 1
                except Exception:
                    logger.exception(
                        "backfill.board.failed org_id=%s date=%s",
                        org_id, target_date.isoformat(),
                    )
        self.stdout.write(f"  Board KPI snapshots upserted: {total}")
