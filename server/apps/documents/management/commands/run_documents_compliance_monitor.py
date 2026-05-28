import logging
from datetime import date

from django.core.management.base import BaseCommand, CommandError

from apps.accounts.rls import iter_organization_ids, rls_context
from apps.documents.compliance_monitoring import run_expiry_compliance_monitor

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run documents expiry/compliance monitor (Phase 6)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            type=str,
            help="Optional monitor date in YYYY-MM-DD format. Defaults to today (UTC).",
        )
        parser.add_argument(
            "--organization-id",
            type=int,
            help="Run compliance monitor for a single organization id.",
        )

    def handle(self, *args, **options):
        monitor_date = None
        if options.get("date"):
            try:
                monitor_date = date.fromisoformat(options["date"])
            except ValueError as exc:
                raise CommandError("Invalid --date format. Use YYYY-MM-DD.") from exc

        target_organization_id = options.get("organization_id")
        combined = {
            "monitor_date": (monitor_date.isoformat() if monitor_date else date.today().isoformat()),
            "processed": 0,
            "alerts_90_day": 0,
            "alerts_30_day": 0,
            "expired_alerts": 0,
            "escalations": 0,
            "expired_documents": 0,
            "notifications_sent": 0,
            "emails_sent": 0,
            "project_scores_updated": 0,
        }
        organization_ids = (
            [int(target_organization_id)]
            if target_organization_id is not None
            else list(iter_organization_ids())
        )

        for organization_id in organization_ids:
            logger.info(
                "documents.command.expiry_monitor.start organization_id=%s monitor_date=%s",
                organization_id,
                combined["monitor_date"],
            )
            try:
                with rls_context(organization_id, bypass=False):
                    summary = run_expiry_compliance_monitor(reference_date=monitor_date)
            except Exception:
                logger.exception(
                    "documents.command.expiry_monitor.failed organization_id=%s",
                    organization_id,
                )
                raise
            for key in combined:
                if key == "monitor_date":
                    combined[key] = str(summary.get(key) or combined[key])
                    continue
                combined[key] += int(summary.get(key, 0) or 0)
            logger.info(
                "documents.command.expiry_monitor.success organization_id=%s processed=%s notifications=%s emails=%s escalations=%s",
                organization_id,
                int(summary.get("processed", 0) or 0),
                int(summary.get("notifications_sent", 0) or 0),
                int(summary.get("emails_sent", 0) or 0),
                int(summary.get("escalations", 0) or 0),
            )

        logger.info(
            "documents.command.expiry_monitor.complete monitor_date=%s processed=%s notifications=%s emails=%s escalations=%s",
            combined["monitor_date"],
            combined["processed"],
            combined["notifications_sent"],
            combined["emails_sent"],
            combined["escalations"],
        )

        self.stdout.write(self.style.SUCCESS("Documents compliance monitor completed."))
        for key, value in combined.items():
            self.stdout.write(f"  {key}: {value}")
