from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from apps.properties.models import Inspection, WorkOrder

from .models import FacilityDocument


def _facility_for_property(property_obj):
    return getattr(property_obj, "facility_registry", None) if property_obj else None


def _space_for_unit(unit):
    return getattr(unit, "facility_space", None) if unit else None


def _work_order_facility(work_order: WorkOrder):
    if not work_order:
        return None
    return work_order.facility or _facility_for_property(work_order.property)


def _inspection_facility(inspection: Inspection):
    if not inspection:
        return None
    return _facility_for_property(inspection.property)


def document_status_for(document: FacilityDocument, *, today=None) -> str:
    today = today or timezone.localdate()
    if document.status == FacilityDocument.Status.ARCHIVED:
        return FacilityDocument.Status.ARCHIVED
    if document.expiry_date and document.expiry_date < today:
        return FacilityDocument.Status.EXPIRED
    if document.review_due_date and document.review_due_date <= today:
        return FacilityDocument.Status.REVIEW_DUE
    if document.expiry_date and document.expiry_date <= today + timedelta(days=30):
        return FacilityDocument.Status.REVIEW_DUE
    if document.review_due_date and document.review_due_date <= today + timedelta(days=14):
        return FacilityDocument.Status.REVIEW_DUE
    return FacilityDocument.Status.ACTIVE


def maintenance_log_summary_for_work_order(work_order: WorkOrder) -> str:
    lines = [
        f"Work Order: WO-{work_order.id} {work_order.title}",
        f"Status: {work_order.get_status_display()}",
        f"Category: {work_order.get_category_display()}",
        f"Priority: {work_order.get_priority_display()}",
    ]
    if work_order.reported_by:
        lines.append(f"Reported By: {work_order.reported_by}")
    if work_order.assigned_to:
        lines.append(f"Assigned To: {work_order.assigned_to}")
    if work_order.completed_date:
        lines.append(f"Completed Date: {work_order.completed_date.isoformat()}")
    if work_order.description:
        lines.append(f"Description: {work_order.description}")
    if work_order.root_cause:
        lines.append(f"Root Cause: {work_order.root_cause}")
    if work_order.verification_notes:
        lines.append(f"Verification Notes: {work_order.verification_notes}")
    if work_order.notes:
        lines.append(f"Notes: {work_order.notes}")
    return "\n".join(lines)


def ensure_facility_document_defaults(document: FacilityDocument, *, actor=None, today=None) -> bool:
    today = today or timezone.localdate()
    changed = False
    update_fields: list[str] = []

    asset = document.asset_component if document.asset_component_id else None
    work_order = document.linked_work_order if document.linked_work_order_id else None
    inspection = document.linked_inspection if document.linked_inspection_id else None
    facility_space = document.facility_space if document.facility_space_id else None
    facility = document.facility if document.facility_id else None

    property_candidate = None
    facility_candidate = None
    facility_space_candidate = None

    if asset:
        property_candidate = asset.property
        facility_candidate = asset.facility or _facility_for_property(asset.property)
        facility_space_candidate = asset.facility_space or _space_for_unit(asset.unit)

    if work_order:
        property_candidate = property_candidate or work_order.property
        facility_candidate = facility_candidate or _work_order_facility(work_order)
        facility_space_candidate = facility_space_candidate or work_order.facility_space
        if work_order.asset_component_id and document.asset_component_id != work_order.asset_component_id:
            document.asset_component = work_order.asset_component
            update_fields.append("asset_component")
            changed = True

    if inspection:
        property_candidate = property_candidate or inspection.property
        facility_candidate = facility_candidate or _inspection_facility(inspection)
        facility_space_candidate = facility_space_candidate or _space_for_unit(inspection.unit)

    if facility_space:
        facility_candidate = facility_candidate or facility_space.facility
        property_candidate = property_candidate or facility_space.facility.property
        facility_space_candidate = facility_space_candidate or facility_space

    if facility:
        facility_candidate = facility_candidate or facility
        property_candidate = property_candidate or facility.property

    if property_candidate and document.property_id != property_candidate.id:
        document.property = property_candidate
        update_fields.append("property")
        changed = True

    if facility_candidate and document.facility_id != facility_candidate.id:
        document.facility = facility_candidate
        update_fields.append("facility")
        changed = True

    if facility_space_candidate and document.facility_space_id != facility_space_candidate.id:
        document.facility_space = facility_space_candidate
        update_fields.append("facility_space")
        changed = True

    if document.uploaded_by_id is None and actor:
        document.uploaded_by = actor
        update_fields.append("uploaded_by")
        changed = True

    if not document.review_due_date:
        base_date = document.expiry_date or document.issued_date
        if base_date:
            interval_days = 365
            if document.document_type == FacilityDocument.DocumentType.COMPLIANCE_CERTIFICATE:
                interval_days = 30
            elif document.document_type in {
                FacilityDocument.DocumentType.BLUEPRINT,
                FacilityDocument.DocumentType.DRAWING,
            }:
                interval_days = 180
            document.review_due_date = base_date if document.expiry_date else base_date + timedelta(days=interval_days)
            update_fields.append("review_due_date")
            changed = True

    if (
        document.document_type == FacilityDocument.DocumentType.MAINTENANCE_LOG
        and document.source == FacilityDocument.Source.GENERATED
        and document.linked_work_order_id
    ):
        generated_summary = maintenance_log_summary_for_work_order(document.linked_work_order)
        if document.generated_summary != generated_summary:
            document.generated_summary = generated_summary
            update_fields.append("generated_summary")
            changed = True
        if not document.issued_date and document.linked_work_order.completed_date:
            document.issued_date = document.linked_work_order.completed_date
            update_fields.append("issued_date")
            changed = True

    target_status = document_status_for(document, today=today)
    if document.status != target_status:
        document.status = target_status
        update_fields.append("status")
        changed = True

    if changed:
        document.save(update_fields=[*dict.fromkeys([*update_fields, "updated_at"])])
    return changed


def ensure_generated_maintenance_log_for_work_order(work_order: WorkOrder) -> bool:
    if work_order.status not in {WorkOrder.Status.COMPLETED, WorkOrder.Status.VERIFIED}:
        return False
    if not (work_order.facility_id or work_order.facility_space_id or _facility_for_property(work_order.property)):
        return False

    facility = _work_order_facility(work_order)
    defaults = {
        "organization": work_order.organization,
        "property": work_order.property,
        "facility": facility,
        "facility_space": work_order.facility_space,
        "asset_component": work_order.asset_component,
        "title": f"Maintenance Log - WO-{work_order.id}",
        "document_type": FacilityDocument.DocumentType.MAINTENANCE_LOG,
        "description": f"Generated maintenance record for work order {work_order.title}.",
        "version_label": "v1",
        "reference_number": f"WO-{work_order.id}",
        "issued_date": work_order.completed_date,
        "review_due_date": (work_order.completed_date or timezone.localdate()) + timedelta(days=365),
        "status": FacilityDocument.Status.ACTIVE,
        "source": FacilityDocument.Source.GENERATED,
        "generated_summary": maintenance_log_summary_for_work_order(work_order),
        "notes": "Auto-generated from completed facility work order.",
    }
    document, created = FacilityDocument.objects.get_or_create(
        organization=work_order.organization,
        linked_work_order=work_order,
        defaults=defaults,
    )

    if created:
        return True

    changed = False
    update_fields: list[str] = []
    for field_name, value in defaults.items():
        if getattr(document, field_name) != value:
            setattr(document, field_name, value)
            update_fields.append(field_name)
            changed = True
    if changed:
        document.save(update_fields=[*dict.fromkeys([*update_fields, "updated_at"])])
    return changed


def run_documents_drawings_automation(organization) -> dict[str, int]:
    today = timezone.localdate()
    summary = {
        "documents_synced": 0,
        "maintenance_logs_generated": 0,
        "review_due_documents": 0,
        "expired_documents": 0,
        "compliance_certificates_flagged": 0,
    }

    documents = (
        FacilityDocument.objects.filter(organization=organization)
        .select_related(
            "property",
            "facility",
            "facility_space",
            "asset_component",
            "linked_work_order",
            "linked_inspection",
            "uploaded_by",
        )
        .order_by("document_type", "title", "-created_at")
    )
    for document in documents:
        previous_status = document.status
        if ensure_facility_document_defaults(document, today=today):
            summary["documents_synced"] += 1
        if document.status == FacilityDocument.Status.REVIEW_DUE:
            summary["review_due_documents"] += 1
        if document.status == FacilityDocument.Status.EXPIRED:
            summary["expired_documents"] += 1
        if (
            document.document_type == FacilityDocument.DocumentType.COMPLIANCE_CERTIFICATE
            and previous_status != FacilityDocument.Status.EXPIRED
            and document.status == FacilityDocument.Status.EXPIRED
        ):
            summary["compliance_certificates_flagged"] += 1

    completed_work_orders = (
        WorkOrder.objects.filter(
            organization=organization,
            property__facility_registry__isnull=False,
            status__in=[WorkOrder.Status.COMPLETED, WorkOrder.Status.VERIFIED],
        )
        .select_related("property", "facility", "facility_space", "asset_component")
        .order_by("-completed_date", "-id")
    )
    for work_order in completed_work_orders:
        if ensure_generated_maintenance_log_for_work_order(work_order):
            summary["maintenance_logs_generated"] += 1

    return summary
