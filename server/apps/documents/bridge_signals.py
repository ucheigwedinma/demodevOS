"""
Post-save / post-delete signal handlers that bridge file uploads
from other modules into the central document repository.

Phase 1: Projects (ProjectDailySiteReportPhoto, ProjectSupportingAttachment)
"""

from __future__ import annotations

import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


# ── Projects: Daily Site Report Photos ───────────────────────────────

@receiver(post_save, sender="projects.ProjectDailySiteReportPhoto")
def bridge_daily_site_report_photo(sender, instance, created, **kwargs):
    if not created or not instance.image:
        return

    from .bridge import BridgeDefaults, bridge_file_to_repository

    report = instance.report
    project = report.project

    bridge_file_to_repository(
        organization=project.organization,
        title=instance.caption or f"Site Photo - {report.report_date}",
        file_path=instance.image.name,
        defaults=BridgeDefaults(
            document_type_code="other",
            owner_role_code="project_management",
            phase_code="construction",
            retention_policy_code="project_7_years",
        ),
        source_app_label="projects",
        source_model_name="ProjectDailySiteReportPhoto",
        source_object_id=instance.pk,
        project=project,
        land=project.property,
        uploaded_by=instance.uploaded_by,
    )


@receiver(post_delete, sender="projects.ProjectDailySiteReportPhoto")
def cleanup_daily_site_report_photo(sender, instance, **kwargs):
    from .bridge import cleanup_bridged_document

    cleanup_bridged_document("projects", "ProjectDailySiteReportPhoto", instance.pk)


# ── Projects: Supporting Attachments ─────────────────────────────────

_ATTACHMENT_CONTEXT_DOC_TYPE = {
    "variation_id": "variation_order",
    "quality_inspection_id": "compliance_certificate",
    "cost_entry_id": "payment_certificate",
}


@receiver(post_save, sender="projects.ProjectSupportingAttachment")
def bridge_supporting_attachment(sender, instance, created, **kwargs):
    if not created or not instance.file:
        return

    from .bridge import BridgeDefaults, bridge_file_to_repository

    # Determine document type from attachment context
    doc_type_code = "other"
    for fk_attr, type_code in _ATTACHMENT_CONTEXT_DOC_TYPE.items():
        if getattr(instance, fk_attr, None):
            doc_type_code = type_code
            break

    project = instance.project

    bridge_file_to_repository(
        organization=instance.organization,
        title=instance.caption or f"Attachment - {project.name}",
        file_path=instance.file.name,
        defaults=BridgeDefaults(
            document_type_code=doc_type_code,
            owner_role_code="project_management",
            phase_code="construction",
            retention_policy_code="project_7_years",
        ),
        source_app_label="projects",
        source_model_name="ProjectSupportingAttachment",
        source_object_id=instance.pk,
        project=project,
        land=project.property,
        uploaded_by=instance.uploaded_by,
    )


@receiver(post_delete, sender="projects.ProjectSupportingAttachment")
def cleanup_supporting_attachment(sender, instance, **kwargs):
    from .bridge import cleanup_bridged_document

    cleanup_bridged_document("projects", "ProjectSupportingAttachment", instance.pk)
