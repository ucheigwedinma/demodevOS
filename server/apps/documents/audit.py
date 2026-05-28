from __future__ import annotations

from typing import Any

from .models import Document, DocumentAuditEvent, DocumentVersion


def _client_ip_from_request(request) -> str | None:
    if request is None:
        return None

    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _actor_role(user):
    if not user or not getattr(user, "is_authenticated", False):
        return None, "System"

    if getattr(user, "is_superuser", False):
        return None, "Superuser"

    profile = getattr(user, "profile", None)
    assigned_role = getattr(profile, "assigned_role", None)
    if assigned_role:
        return assigned_role, assigned_role.name

    profile_role = getattr(profile, "role", "")
    if profile_role == "admin":
        return None, "Organization Admin"
    if profile_role:
        return None, str(profile_role).replace("_", " ").title()
    return None, ""


def _event_summary(event: DocumentAuditEvent) -> str:
    payload = event.payload or {}
    if "summary" in payload:
        return str(payload["summary"])

    if event.event_type == DocumentAuditEvent.EventType.VERSION_UPLOADED:
        return f"Uploaded {event.version_label_snapshot or 'new version'}."
    if event.event_type == DocumentAuditEvent.EventType.DOCUMENT_GENERATED:
        return "Generated branded document."
    if event.event_type == DocumentAuditEvent.EventType.METADATA_CHANGED:
        return "Updated document metadata."
    if event.event_type == DocumentAuditEvent.EventType.APPROVAL_DECISION:
        decision = payload.get("decision", "unknown")
        return f"Recorded approval decision: {decision}."
    if event.event_type == DocumentAuditEvent.EventType.WORKFLOW_SUBMITTED:
        return "Submitted document for workflow review."
    if event.event_type == DocumentAuditEvent.EventType.WORKFLOW_STEP_DECISION:
        return "Workflow step decision recorded."
    if event.event_type == DocumentAuditEvent.EventType.COMMENT_ADDED:
        return "Added document comment."
    if event.event_type == DocumentAuditEvent.EventType.DOCUMENT_DOWNLOADED:
        return "Downloaded document file."
    if event.event_type == DocumentAuditEvent.EventType.DOCUMENT_SHARED:
        return "Shared document."
    if event.event_type == DocumentAuditEvent.EventType.SIGNATURE_REQUEST_SENT:
        return "Sent signature request."
    if event.event_type == DocumentAuditEvent.EventType.SIGNATURE_COMPLETED:
        return "Completed signature request."
    if event.event_type == DocumentAuditEvent.EventType.SIGNATURE_CANCELLED:
        return "Cancelled signature request."
    if event.event_type == DocumentAuditEvent.EventType.DOCUMENT_ARCHIVED:
        return "Archived document."
    if event.event_type == DocumentAuditEvent.EventType.DOCUMENT_SUPERSEDED:
        return "Marked document as superseded."
    if event.event_type == DocumentAuditEvent.EventType.DOCUMENT_DELETED:
        return "Deleted document."
    if event.event_type == DocumentAuditEvent.EventType.DOCUMENT_CREATED:
        return "Created document."
    return event.get_event_type_display()


def document_metadata_snapshot(document: Document) -> dict[str, Any]:
    return {
        "title": document.title,
        "document_number": document.document_number,
        "status": document.status,
        "confidentiality_level": document.confidentiality_level,
        "document_type_id": document.document_type_id,
        "owner_role_id": document.owner_role_id,
        "project_id": document.project_id,
        "land_id": document.land_id,
        "unit_id": document.unit_id,
        "client_id": document.client_id,
        "vendor_id": document.vendor_id,
        "phase_id": document.phase_id,
        "retention_policy_id": document.retention_policy_id,
        "contract_value": str(document.contract_value),
        "business_unit_division_id": document.business_unit_division_id,
        "business_unit_department_id": document.business_unit_department_id,
    }


def metadata_change_payload(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed: dict[str, dict[str, Any]] = {}
    for key, old_value in before.items():
        new_value = after.get(key)
        if old_value != new_value:
            changed[key] = {"from": old_value, "to": new_value}
    return changed


def log_document_audit_event(
    *,
    event_type: str,
    request=None,
    user=None,
    document: Document | None = None,
    document_version: DocumentVersion | None = None,
    payload: dict[str, Any] | None = None,
) -> DocumentAuditEvent:
    actor = user
    if actor is None and request is not None:
        actor = request.user

    if document is None and document_version is not None:
        document = document_version.document

    actor_role, actor_role_name = _actor_role(actor)
    version_label = ""
    if document_version is not None:
        version_label = f"v{document_version.version_major}.{document_version.version_minor}"

    organization = getattr(document, "organization", None)
    if organization is None and document is not None:
        organization = document.organization

    event = DocumentAuditEvent.objects.create(
        organization=organization,
        document=document,
        document_version=document_version,
        event_type=event_type,
        payload=payload or {},
        actor=actor if actor and actor.is_authenticated else None,
        actor_role=actor_role,
        actor_role_name=actor_role_name,
        ip_address=_client_ip_from_request(request),
        document_number_snapshot=document.document_number if document else "",
        document_title_snapshot=document.title if document else "",
        version_label_snapshot=version_label,
    )
    return event


def event_summary(event: DocumentAuditEvent) -> str:
    return _event_summary(event)
