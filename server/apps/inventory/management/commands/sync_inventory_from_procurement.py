import logging

from django.core.management.base import BaseCommand

from apps.accounts.rls import iter_organization_ids, rls_context
from apps.inventory.services import bulk_sync_goods_receipt_items
from apps.procurement.models import GoodsReceiptItem

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Backfill inventory transactions and stock from existing procurement GRN items."

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
                "inventory.command.sync_from_procurement.start organization_id=%s",
                organization_id,
            )
            try:
                with rls_context(organization_id, bypass=False):
                    items = GoodsReceiptItem.objects.filter(
                        organization_id=organization_id
                    ).select_related(
                        "goods_receipt__purchase_order__project",
                        "goods_receipt__purchase_order__vendor",
                        "po_item__purchase_order__vendor",
                    )
                    org_count = bulk_sync_goods_receipt_items(items)
                    count += org_count
            except Exception:
                logger.exception(
                    "inventory.command.sync_from_procurement.failed organization_id=%s",
                    organization_id,
                )
                raise
            logger.info(
                "inventory.command.sync_from_procurement.success organization_id=%s synchronized=%s",
                organization_id,
                org_count,
            )

        logger.info(
            "inventory.command.sync_from_procurement.complete synchronized=%s",
            count,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Synchronized {count} goods receipt items into inventory transactions."
            )
        )
