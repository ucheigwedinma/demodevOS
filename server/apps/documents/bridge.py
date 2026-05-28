"""
Document Repository Auto-Bridge
================================
Creates Document + DocumentVersion records when files are uploaded
in other modules (projects, HR, properties, etc.).

All upload sources call ``bridge_file_to_repository()`` which handles
idempotency, lookup resolution, and audit logging.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from django.db import transaction

from .models import (
    Document,
    DocumentOwnerRole,
    DocumentRetentionPolicy,
    DocumentType,
    DocumentVersion,
    DocumentWorkflowPhase,
)

logger = logging.getLogger(__name__)


@dataclass
class BridgeDefaults:
    """Mapping defaults for a given upload source."""

    document_type_code: str = "other"
    owner_role_code: str = "project_management"
    phase_code: str = "construction"
    retention_policy_code: str = "project_7_years"
    confidentiality_level: str = "internal"


_LOOKUP_MAP = {
    "document_type": DocumentType,
    "owner_role": DocumentOwnerRole,
    "phase": DocumentWorkflowPhase,
    "retention_policy": DocumentRetentionPolicy,
}


def _resolve_lookups(defaults: BridgeDefaults) -> dict | None:
    """Fetch the four required FK objects by code. Returns None on any miss."""
    codes = {
        "document_type": defaults.document_type_code,
        "owner_role": defaults.owner_role_code,
        "phase": defaults.phase_code,
        "retention_policy": defaults.retention_policy_code,
    }
    resolved = {}
    missing = []
    for key, code in codes.items():
        model_class = _LOOKUP_MAP[key]
        try:
            resolved[key] = model_class.objects.get(code=code)
        except model_class.DoesNotExist:
            missing.append(f"{model_class.__name__}(code={code!r})")

    if missing:
        return None, missing
    return resolved, []


def bridge_file_to_repository(
    *,
    organization,
    title: str,
    file_path: str,
    defaults: BridgeDefaults,
    source_app_label: str,
    source_model_name: str,
    source_object_id: int,
    project=None,
    land=None,
    unit=None,
    client=None,
    vendor=None,
    uploaded_by=None,
    project_code: str = "",
) -> Document | None:
    """
    Create a Document + DocumentVersion record bridging a source file
    into the central document repository.

    Returns the Document instance, or None if lookups are missing or
    the bridge already exists (idempotent).
    """
    # Idempotency guard
    if Document.objects.filter(
        source_app_label=source_app_label,
        source_model_name=source_model_name,
        source_object_id=source_object_id,
    ).exists():
        return None

    resolved, missing = _resolve_lookups(defaults)
    if missing:
        logger.warning(
            "Skipping document bridge for %s.%s #%s: missing %s. "
            "Run 'manage.py seed_documents_phase2_all' to seed.",
            source_app_label,
            source_model_name,
            source_object_id,
            ", ".join(missing),
        )
        return None

    with transaction.atomic():
        doc = Document(
            organization=organization,
            title=title,
            document_type=resolved["document_type"],
            owner_role=resolved["owner_role"],
            phase=resolved["phase"],
            retention_policy=resolved["retention_policy"],
            confidentiality_level=defaults.confidentiality_level,
            project=project,
            land=land,
            unit=unit,
            client=client,
            vendor=vendor,
            project_code=project_code,
            source_app_label=source_app_label,
            source_model_name=source_model_name,
            source_object_id=source_object_id,
            status=Document.Status.APPROVED,
        )
        doc.save()  # triggers auto-numbering

        version = DocumentVersion(
            organization=organization,
            document=doc,
            version_major=1,
            version_minor=0,
            file_path=file_path,
            change_summary=f"Auto-bridged from {source_app_label}.{source_model_name}",
            uploaded_by=uploaded_by,
        )
        version.save()  # triggers current_version update on Document

    return doc


def cleanup_bridged_document(
    source_app_label: str,
    source_model_name: str,
    source_object_id: int,
) -> None:
    """Delete the bridged Document when its source record is deleted."""
    Document.objects.filter(
        source_app_label=source_app_label,
        source_model_name=source_model_name,
        source_object_id=source_object_id,
    ).delete()
