import logging

from django.core.management.base import BaseCommand

from apps.accounts.rls import iter_organization_ids, rls_context
from apps.inventory.services import sync_project_cost_entry
from apps.projects.models import ProjectCostEntry

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Backfill inventory issue movements from project material cost entries "
        "(expects SKU in reference_number)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--organization-id",
            type=int,
            help="Backfill for a single organization id.",
        )

    def handle(self, *args, **options):
        target_organization_id = options.get("organization_id")
        organization_ids = (
            [int(target_organization_id)]
            if target_organization_id is not None
            else list(iter_organization_ids())
        )

        count = 0
        for organization_id in organization_ids:
            logger.info(
                "inventory.command.sync_from_project_costs.start organization_id=%s",
                organization_id,
            )
            try:
                with rls_context(organization_id, bypass=False):
                    entries = ProjectCostEntry.objects.filter(
                        organization_id=organization_id,
                        category="materials",
                    ).select_related("phase__project")
                    org_count = 0
                    for entry in entries:
                        tx = sync_project_cost_entry(entry)
                        if tx is not None:
                            org_count += 1
                            count += 1
            except Exception:
                logger.exception(
                    "inventory.command.sync_from_project_costs.failed organization_id=%s",
                    organization_id,
                )
                raise
            logger.info(
                "inventory.command.sync_from_project_costs.success organization_id=%s synchronized=%s",
                organization_id,
                org_count,
            )

        logger.info(
            "inventory.command.sync_from_project_costs.complete synchronized=%s",
            count,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Synchronized {count} project material cost entries to inventory movements."
            )
        )
