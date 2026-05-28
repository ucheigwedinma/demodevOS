import logging

from django.core.management.base import BaseCommand, CommandError

from apps.accounts.rls import iter_organization_ids, rls_context
from apps.documents.search_engine import (
    build_search_index_for_document_id,
    rebuild_search_index,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Rebuild Document Search Index Engine for all documents or a specific document."

    def add_arguments(self, parser):
        parser.add_argument("--document-id", type=int, help="Rebuild index for a single document ID.")
        parser.add_argument(
            "--organization-id",
            type=int,
            help="Restrict rebuild to a single organization. Without this, all organizations are processed.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force re-indexing even when content hash is unchanged.",
        )

    def handle(self, *args, **options):
        document_id = options.get("document_id")
        target_organization_id = options.get("organization_id")
        force = bool(options.get("force"))

        if document_id:
            try:
                index = build_search_index_for_document_id(document_id=document_id, force=force)
            except Exception as exc:
                raise CommandError(str(exc)) from exc

            self.stdout.write(
                self.style.SUCCESS(
                    f"Document {document_id} indexed with status={index.index_status}"
                )
            )
            if index.error_message:
                self.stdout.write(f"  note={index.error_message}")
            return

        organization_ids = (
            [int(target_organization_id)]
            if target_organization_id is not None
            else list(iter_organization_ids())
        )

        combined = {"processed": 0, "indexed": 0, "failed": 0}

        for organization_id in organization_ids:
            logger.info(
                "documents.command.rebuild_search_index.start organization_id=%s",
                organization_id,
            )
            with rls_context(organization_id, bypass=False):
                summary = rebuild_search_index(organization_id=organization_id, force=force)

            for key in combined:
                combined[key] += summary.get(key, 0)

            logger.info(
                "documents.command.rebuild_search_index.success organization_id=%s processed=%s indexed=%s failed=%s",
                organization_id,
                summary["processed"],
                summary["indexed"],
                summary["failed"],
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Search index rebuild complete: processed={combined['processed']}, "
                f"indexed={combined['indexed']}, failed={combined['failed']}"
            )
        )
