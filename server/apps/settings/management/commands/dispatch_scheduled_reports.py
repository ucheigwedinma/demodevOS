import logging

from django.core.management.base import BaseCommand

from apps.accounts.rls import iter_organization_ids, rls_context
from apps.settings.reporting_dispatch import dispatch_due_scheduled_reports

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Dispatch due scheduled reports by creating centralized report run records."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=500,
            help="Maximum number of active schedules to evaluate.",
        )
        parser.add_argument(
            "--organization-id",
            type=int,
            help="Run dispatch for a single organization id.",
        )

    def handle(self, *args, **options):
        limit = max(1, int(options.get("limit") or 500))
        organization_id = options.get("organization_id")
        combined = {
            "considered": 0,
            "dispatched": 0,
            "skipped_not_due": 0,
            "enqueue_failed": 0,
        }

        if organization_id is not None:
            logger.info(
                "settings.command.dispatch_scheduled_reports.start organization_id=%s limit=%s",
                organization_id,
                limit,
            )
            try:
                with rls_context(organization_id, bypass=False):
                    result = dispatch_due_scheduled_reports(
                        limit=limit,
                        organization_id=organization_id,
                    )
            except Exception:
                logger.exception(
                    "settings.command.dispatch_scheduled_reports.failed organization_id=%s",
                    organization_id,
                )
                raise
            for key in combined:
                combined[key] += int(result.get(key, 0) or 0)
            logger.info(
                "settings.command.dispatch_scheduled_reports.success organization_id=%s considered=%s dispatched=%s skipped_not_due=%s enqueue_failed=%s",
                organization_id,
                int(result.get("considered", 0) or 0),
                int(result.get("dispatched", 0) or 0),
                int(result.get("skipped_not_due", 0) or 0),
                int(result.get("enqueue_failed", 0) or 0),
            )
        else:
            for organization_id in iter_organization_ids():
                logger.info(
                    "settings.command.dispatch_scheduled_reports.start organization_id=%s limit=%s",
                    organization_id,
                    limit,
                )
                try:
                    with rls_context(organization_id, bypass=False):
                        result = dispatch_due_scheduled_reports(
                            limit=limit,
                            organization_id=organization_id,
                        )
                except Exception:
                    logger.exception(
                        "settings.command.dispatch_scheduled_reports.failed organization_id=%s",
                        organization_id,
                    )
                    raise
                for key in combined:
                    combined[key] += int(result.get(key, 0) or 0)
                logger.info(
                    "settings.command.dispatch_scheduled_reports.success organization_id=%s considered=%s dispatched=%s skipped_not_due=%s enqueue_failed=%s",
                    organization_id,
                    int(result.get("considered", 0) or 0),
                    int(result.get("dispatched", 0) or 0),
                    int(result.get("skipped_not_due", 0) or 0),
                    int(result.get("enqueue_failed", 0) or 0),
                )

        logger.info(
            "settings.command.dispatch_scheduled_reports.complete considered=%s dispatched=%s skipped_not_due=%s enqueue_failed=%s",
            combined["considered"],
            combined["dispatched"],
            combined["skipped_not_due"],
            combined["enqueue_failed"],
        )

        self.stdout.write(
            self.style.SUCCESS(

                    f"Done. considered={combined['considered']}, "
                    f"dispatched={combined['dispatched']}, "
                    f"skipped_not_due={combined['skipped_not_due']}, "
                    f"enqueue_failed={combined['enqueue_failed']}"

            )
        )
