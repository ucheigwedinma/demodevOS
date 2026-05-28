import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from apps.accounts.rls import iter_organization_ids, rls_context

from .computations import compute_full_board_kpis, compute_full_portfolio_snapshot
from .models import BoardKpiSnapshot, PortfolioSnapshot

logger = logging.getLogger(__name__)


@shared_task(name="analytics.compute_daily_portfolio_snapshots")
def compute_daily_portfolio_snapshots():
    """Daily: compute portfolio analytics for every organization and upsert snapshots."""
    today = timezone.now().date()
    now = timezone.now()
    orgs_processed = 0
    errors = 0

    for organization_id in iter_organization_ids():
        try:
            with rls_context(organization_id, bypass=False):
                data = compute_full_portfolio_snapshot(organization_id)
                PortfolioSnapshot.objects.update_or_create(
                    organization_id=organization_id,
                    snapshot_date=today,
                    defaults={**data, "computed_at": now},
                )
            orgs_processed += 1
        except Exception:
            errors += 1
            logger.exception(
                "analytics.portfolio_snapshot.failed organization_id=%s",
                organization_id,
            )

    logger.info(
        "analytics.portfolio_snapshot.complete date=%s orgs_processed=%s errors=%s",
        today.isoformat(), orgs_processed, errors,
    )
    return {"snapshot_date": today.isoformat(), "orgs_processed": orgs_processed, "errors": errors}


@shared_task(name="analytics.compute_hourly_board_kpi_snapshots")
def compute_hourly_board_kpi_snapshots():
    """Hourly: compute board KPIs for every organization and upsert snapshots."""
    now = timezone.now()
    snapshot_hour = now.replace(minute=0, second=0, microsecond=0)
    end_date = now.date()
    start_date = end_date - timedelta(days=180)
    orgs_processed = 0
    errors = 0

    for organization_id in iter_organization_ids():
        try:
            with rls_context(organization_id, bypass=False):
                data = compute_full_board_kpis(organization_id, start_date, end_date)
                BoardKpiSnapshot.objects.update_or_create(
                    organization_id=organization_id,
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
            orgs_processed += 1
        except Exception:
            errors += 1
            logger.exception(
                "analytics.board_kpi_snapshot.failed organization_id=%s",
                organization_id,
            )

    logger.info(
        "analytics.board_kpi_snapshot.complete hour=%s orgs_processed=%s errors=%s",
        snapshot_hour.isoformat(), orgs_processed, errors,
    )
    return {"snapshot_hour": snapshot_hour.isoformat(), "orgs_processed": orgs_processed, "errors": errors}
