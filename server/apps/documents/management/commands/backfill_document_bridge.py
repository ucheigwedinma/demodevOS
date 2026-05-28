"""
Backfill bridged Document records for existing file uploads.

Usage:
    python manage.py backfill_document_bridge                # all sources
    python manage.py backfill_document_bridge --app projects  # just projects
    python manage.py backfill_document_bridge --dry-run       # preview only
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.documents.bridge import BridgeDefaults, bridge_file_to_repository
from apps.documents.models import Document


class Command(BaseCommand):
    help = "Backfill document repository bridge for existing file uploads."

    def add_arguments(self, parser):
        parser.add_argument(
            "--app",
            type=str,
            default="all",
            help="Limit to a single app: projects (more coming in future phases).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview what would be created without writing to the database.",
        )

    def handle(self, *args, **options):
        app = options["app"]
        dry_run = options["dry_run"]
        total = 0

        if app in ("all", "projects"):
            total += self._backfill_project_photos(dry_run)
            total += self._backfill_project_attachments(dry_run)

        prefix = "[DRY RUN] " if dry_run else ""
        self.stdout.write(
            self.style.SUCCESS(f"{prefix}Done. {total} document(s) would be bridged.")
            if dry_run
            else self.style.SUCCESS(f"Done. {total} document(s) bridged.")
        )

    def _already_bridged(self, app_label, model_name):
        return set(
            Document.objects.filter(
                source_app_label=app_label,
                source_model_name=model_name,
            ).values_list("source_object_id", flat=True)
        )

    def _backfill_project_photos(self, dry_run):
        from apps.projects.models import ProjectDailySiteReportPhoto

        bridged = self._already_bridged("projects", "ProjectDailySiteReportPhoto")
        photos = (
            ProjectDailySiteReportPhoto.objects
            .exclude(image="")
            .exclude(pk__in=bridged)
            .select_related("report__project__organization", "report__project__property")
        )

        count = 0
        for photo in photos:
            report = photo.report
            project = report.project
            self.stdout.write(
                f"  Photo #{photo.pk} → project '{project.name}' "
                f"(report {report.report_date})"
            )
            if not dry_run:
                bridge_file_to_repository(
                    organization=project.organization,
                    title=photo.caption or f"Site Photo - {report.report_date}",
                    file_path=photo.image.name,
                    defaults=BridgeDefaults(
                        document_type_code="other",
                        owner_role_code="project_management",
                        phase_code="construction",
                        retention_policy_code="project_7_years",
                    ),
                    source_app_label="projects",
                    source_model_name="ProjectDailySiteReportPhoto",
                    source_object_id=photo.pk,
                    project=project,
                    land=project.property,
                    uploaded_by=photo.uploaded_by,
                )
            count += 1

        self.stdout.write(f"  {count} site report photo(s) found.")
        return count

    def _backfill_project_attachments(self, dry_run):
        from apps.documents.bridge_signals import _ATTACHMENT_CONTEXT_DOC_TYPE
        from apps.projects.models import ProjectSupportingAttachment

        bridged = self._already_bridged("projects", "ProjectSupportingAttachment")
        attachments = (
            ProjectSupportingAttachment.objects
            .exclude(file="")
            .exclude(pk__in=bridged)
            .select_related("project__organization", "project__property")
        )

        count = 0
        for att in attachments:
            project = att.project
            doc_type_code = "other"
            for fk_attr, type_code in _ATTACHMENT_CONTEXT_DOC_TYPE.items():
                if getattr(att, fk_attr, None):
                    doc_type_code = type_code
                    break

            self.stdout.write(
                f"  Attachment #{att.pk} → project '{project.name}' "
                f"(type={doc_type_code})"
            )
            if not dry_run:
                bridge_file_to_repository(
                    organization=att.organization,
                    title=att.caption or f"Attachment - {project.name}",
                    file_path=att.file.name,
                    defaults=BridgeDefaults(
                        document_type_code=doc_type_code,
                        owner_role_code="project_management",
                        phase_code="construction",
                        retention_policy_code="project_7_years",
                    ),
                    source_app_label="projects",
                    source_model_name="ProjectSupportingAttachment",
                    source_object_id=att.pk,
                    project=project,
                    land=project.property,
                    uploaded_by=att.uploaded_by,
                )
            count += 1

        self.stdout.write(f"  {count} supporting attachment(s) found.")
        return count
