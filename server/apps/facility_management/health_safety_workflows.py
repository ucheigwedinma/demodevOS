from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from apps.compliance.models import ComplianceRequirement, ComplianceViolation, PropertyCompliance
from apps.properties.models import Inspection, WorkOrder

from .models import FacilityComplianceChecklist, FacilityIncident, FacilityRegulatoryDocument, FacilitySafetyAuditLog

OPEN_VIOLATION_STATUSES = {
    ComplianceViolation.Status.OPEN,
    ComplianceViolation.Status.UNDER_REVIEW,
    ComplianceViolation.Status.REMEDIATION,
    ComplianceViolation.Status.APPEALED,
}


def _user_display(user) -> str:
    if not user:
        return ""
    full_name = user.get_full_name().strip()
    return full_name or user.email or user.username


def _facility_for_property(property_obj):
    return getattr(property_obj, "facility_registry", None) if property_obj else None


def _space_for_unit(unit):
    return getattr(unit, "facility_space", None) if unit else None


def _space_label(space) -> str:
    if not space:
        return ""
    return space.space_label or space.unit.unit_number


def _checklist_interval_days(frequency: str) -> int | None:
    mapping = {
        FacilityComplianceChecklist.Frequency.DAILY: 1,
        FacilityComplianceChecklist.Frequency.WEEKLY: 7,
        FacilityComplianceChecklist.Frequency.MONTHLY: 30,
        FacilityComplianceChecklist.Frequency.QUARTERLY: 90,
        FacilityComplianceChecklist.Frequency.ANNUAL: 365,
    }
    return mapping.get(frequency)


def _severity_priority_for_incident(incident: FacilityIncident) -> tuple[str, int]:
    if incident.severity == FacilityIncident.Severity.CRITICAL:
        return WorkOrder.Priority.CRITICAL, 4
    if incident.severity == FacilityIncident.Severity.HIGH:
        return WorkOrder.Priority.HIGH, 8
    if incident.severity == FacilityIncident.Severity.LOW:
        return WorkOrder.Priority.LOW, 72
    return WorkOrder.Priority.MEDIUM, 24


def _work_order_category_for_incident(incident: FacilityIncident) -> str:
    mapping = {
        FacilityIncident.Category.FIRE: WorkOrder.Category.FIRE_SAFETY,
        FacilityIncident.Category.SECURITY: WorkOrder.Category.SECURITY,
        FacilityIncident.Category.SAFETY: WorkOrder.Category.GENERAL,
        FacilityIncident.Category.ENVIRONMENTAL: WorkOrder.Category.GENERAL,
        FacilityIncident.Category.HEALTH: WorkOrder.Category.GENERAL,
    }
    return mapping.get(incident.category, WorkOrder.Category.GENERAL)


def _inspection_type_for_incident(incident: FacilityIncident) -> str:
    if incident.category == FacilityIncident.Category.FIRE:
        return Inspection.InspectionType.FIRE_SAFETY
    if incident.category == FacilityIncident.Category.ENVIRONMENTAL:
        return Inspection.InspectionType.ENVIRONMENTAL_AUDIT
    if incident.category == FacilityIncident.Category.HEALTH:
        return Inspection.InspectionType.HEALTH_SAFETY
    return Inspection.InspectionType.POST_INCIDENT


def _inspection_type_for_checklist(checklist: FacilityComplianceChecklist) -> str:
    mapping = {
        FacilityComplianceChecklist.ChecklistType.FIRE_SAFETY: Inspection.InspectionType.FIRE_SAFETY,
        FacilityComplianceChecklist.ChecklistType.ELECTRICAL: Inspection.InspectionType.ELECTRICAL,
        FacilityComplianceChecklist.ChecklistType.ENVIRONMENTAL: Inspection.InspectionType.ENVIRONMENTAL_AUDIT,
        FacilityComplianceChecklist.ChecklistType.REGULATORY: Inspection.InspectionType.COMPLIANCE,
        FacilityComplianceChecklist.ChecklistType.OCCUPATIONAL_HEALTH: Inspection.InspectionType.HEALTH_SAFETY,
        FacilityComplianceChecklist.ChecklistType.INCIDENT_FOLLOW_UP: Inspection.InspectionType.POST_INCIDENT,
    }
    return mapping.get(checklist.checklist_type, Inspection.InspectionType.SAFETY)


def _compliance_category_for_checklist(checklist: FacilityComplianceChecklist) -> str:
    mapping = {
        FacilityComplianceChecklist.ChecklistType.SAFETY: ComplianceRequirement.Category.SAFETY,
        FacilityComplianceChecklist.ChecklistType.FIRE_SAFETY: ComplianceRequirement.Category.FIRE_SAFETY,
        FacilityComplianceChecklist.ChecklistType.ELECTRICAL: ComplianceRequirement.Category.BUILDING_CODE,
        FacilityComplianceChecklist.ChecklistType.ENVIRONMENTAL: ComplianceRequirement.Category.ENVIRONMENTAL,
        FacilityComplianceChecklist.ChecklistType.OCCUPATIONAL_HEALTH: ComplianceRequirement.Category.OCCUPATIONAL_HEALTH,
        FacilityComplianceChecklist.ChecklistType.REGULATORY: ComplianceRequirement.Category.REGULATORY,
        FacilityComplianceChecklist.ChecklistType.HOUSEKEEPING: ComplianceRequirement.Category.SAFETY,
        FacilityComplianceChecklist.ChecklistType.INCIDENT_FOLLOW_UP: ComplianceRequirement.Category.SAFETY,
    }
    return mapping.get(checklist.checklist_type, ComplianceRequirement.Category.SAFETY)


def _compliance_category_for_inspection(inspection: Inspection) -> str:
    mapping = {
        Inspection.InspectionType.FIRE_SAFETY: ComplianceRequirement.Category.FIRE_SAFETY,
        Inspection.InspectionType.ELECTRICAL: ComplianceRequirement.Category.BUILDING_CODE,
        Inspection.InspectionType.ENVIRONMENTAL_AUDIT: ComplianceRequirement.Category.ENVIRONMENTAL,
        Inspection.InspectionType.COMPLIANCE: ComplianceRequirement.Category.REGULATORY,
        Inspection.InspectionType.HEALTH_SAFETY: ComplianceRequirement.Category.OCCUPATIONAL_HEALTH,
        Inspection.InspectionType.POST_INCIDENT: ComplianceRequirement.Category.SAFETY,
    }
    return mapping.get(inspection.inspection_type, ComplianceRequirement.Category.SAFETY)


def _violation_severity_for_risk(risk_level: str) -> str:
    mapping = {
        Inspection.RiskLevel.LOW: ComplianceViolation.Severity.MINOR,
        Inspection.RiskLevel.MEDIUM: ComplianceViolation.Severity.MODERATE,
        Inspection.RiskLevel.HIGH: ComplianceViolation.Severity.MAJOR,
        Inspection.RiskLevel.CRITICAL: ComplianceViolation.Severity.CRITICAL,
    }
    return mapping.get(risk_level, ComplianceViolation.Severity.MODERATE)


def _violation_due_date_for_severity(severity: str, *, today=None):
    today = today or timezone.localdate()
    if severity == ComplianceViolation.Severity.CRITICAL:
        return today + timedelta(days=1)
    if severity == ComplianceViolation.Severity.MAJOR:
        return today + timedelta(days=3)
    if severity == ComplianceViolation.Severity.MINOR:
        return today + timedelta(days=14)
    return today + timedelta(days=7)


def _create_audit_log(
    *,
    organization,
    property_obj=None,
    facility=None,
    entity_type: str,
    event_type: str,
    entity_id: int | None = None,
    actor=None,
    summary: str,
    details: dict | None = None,
):
    return FacilitySafetyAuditLog.objects.create(
        organization=organization,
        property=property_obj,
        facility=facility,
        entity_type=entity_type,
        event_type=event_type,
        entity_id=entity_id,
        actor=actor,
        summary=summary,
        details=details or {},
    )


def _open_violation_for(property_obj, title: str):
    return (
        ComplianceViolation.objects.filter(
            organization=property_obj.organization,
            property=property_obj,
            title=title,
            status__in=OPEN_VIOLATION_STATUSES,
        )
        .order_by("-updated_at", "-id")
        .first()
    )


def _resolve_open_violation(property_obj, title: str, *, resolution_note: str = "") -> bool:
    violation = _open_violation_for(property_obj, title)
    if violation is None:
        return False
    notes = violation.notes or ""
    if resolution_note and resolution_note not in notes:
        notes = f"{notes}\n{resolution_note}".strip()
    violation.status = ComplianceViolation.Status.RESOLVED
    violation.resolved_date = timezone.localdate()
    violation.notes = notes
    violation.save(update_fields=["status", "resolved_date", "notes", "updated_at"])
    return True


def incident_requires_regulatory_reporting(incident: FacilityIncident) -> bool:
    return incident.severity in {
        FacilityIncident.Severity.HIGH,
        FacilityIncident.Severity.CRITICAL,
    } or incident.category in {
        FacilityIncident.Category.FIRE,
        FacilityIncident.Category.ENVIRONMENTAL,
        FacilityIncident.Category.HEALTH,
    }


def ensure_incident_defaults(incident: FacilityIncident, *, actor=None, now=None) -> bool:
    now = now or timezone.now()
    changed = False
    update_fields: list[str] = []

    if incident.facility_space_id:
        if incident.facility_id != incident.facility_space.facility_id:
            incident.facility = incident.facility_space.facility
            update_fields.append("facility")
            changed = True
        if incident.property_id != incident.facility_space.facility.property_id:
            incident.property = incident.facility_space.facility.property
            update_fields.append("property")
            changed = True
    elif incident.facility_id:
        if incident.property_id != incident.facility.property_id:
            incident.property = incident.facility.property
            update_fields.append("property")
            changed = True
    elif incident.work_order_id:
        work_order = incident.work_order
        if incident.property_id != work_order.property_id:
            incident.property = work_order.property
            update_fields.append("property")
            changed = True
        if work_order.facility_id and incident.facility_id != work_order.facility_id:
            incident.facility = work_order.facility
            update_fields.append("facility")
            changed = True
        if work_order.facility_space_id and incident.facility_space_id != work_order.facility_space_id:
            incident.facility_space = work_order.facility_space
            update_fields.append("facility_space")
            changed = True
    elif incident.property_id:
        facility = _facility_for_property(incident.property)
        if facility and incident.facility_id != facility.id:
            incident.facility = facility
            update_fields.append("facility")
            changed = True

    if not incident.reported_by and actor:
        incident.reported_by = _user_display(actor)
        update_fields.append("reported_by")
        changed = True

    if incident.work_order_id and incident.work_order.assigned_to and not incident.assigned_to:
        incident.assigned_to = incident.work_order.assigned_to
        update_fields.append("assigned_to")
        changed = True

    if incident.pk and not incident.incident_code:
        incident.incident_code = f"INC-{incident.pk:05d}"
        update_fields.append("incident_code")
        changed = True

    if incident_requires_regulatory_reporting(incident) and not incident.requires_regulatory_report:
        incident.requires_regulatory_report = True
        update_fields.append("requires_regulatory_report")
        changed = True

    if incident.status in {FacilityIncident.Status.RESOLVED, FacilityIncident.Status.CLOSED} and incident.resolved_at is None:
        incident.resolved_at = now
        update_fields.append("resolved_at")
        changed = True

    if changed:
        incident.save(update_fields=[*dict.fromkeys([*update_fields, "updated_at"])])
    return changed


def ensure_follow_up_inspection_for_incident(incident: FacilityIncident, *, actor=None, now=None) -> bool:
    now = now or timezone.now()
    if incident.follow_up_inspection_id is not None:
        return False
    if not (
        incident.severity in {FacilityIncident.Severity.HIGH, FacilityIncident.Severity.CRITICAL}
        or incident.requires_regulatory_report
    ):
        return False

    unit = incident.facility_space.unit if incident.facility_space_id else None
    inspection = Inspection.objects.create(
        organization=incident.organization,
        property=incident.property or incident.facility.property,
        unit=unit,
        title=f"Post-Incident Inspection - {incident.incident_code or incident.title}",
        inspection_type=_inspection_type_for_incident(incident),
        status=Inspection.Status.SCHEDULED,
        scheduled_date=timezone.localdate(now) + timedelta(days=0 if incident.severity == FacilityIncident.Severity.CRITICAL else 1),
        inspector=incident.assigned_to,
        notes=f"Auto-created follow-up for facility incident #{incident.id}.",
    )
    incident.follow_up_inspection = inspection
    incident.save(update_fields=["follow_up_inspection", "updated_at"])
    _create_audit_log(
        organization=incident.organization,
        property_obj=incident.property,
        facility=incident.facility or _facility_for_property(incident.property),
        entity_type=FacilitySafetyAuditLog.EntityType.INSPECTION,
        event_type=FacilitySafetyAuditLog.EventType.FOLLOW_UP_INSPECTION_CREATED,
        entity_id=inspection.id,
        actor=actor,
        summary=f"Created follow-up inspection for incident {incident.incident_code or incident.id}.",
        details={
            "incident_id": incident.id,
            "incident_code": incident.incident_code,
            "inspection_id": inspection.id,
        },
    )
    return True


def ensure_corrective_work_order_for_incident(incident: FacilityIncident, *, actor=None, now=None) -> bool:
    now = now or timezone.now()
    if incident.status in {FacilityIncident.Status.RESOLVED, FacilityIncident.Status.CLOSED} and incident.work_order_id is None:
        return False

    priority, sla_hours = _severity_priority_for_incident(incident)
    work_order_status = WorkOrder.Status.OPEN
    if incident.status == FacilityIncident.Status.INVESTIGATING:
        work_order_status = WorkOrder.Status.IN_PROGRESS
    elif incident.assigned_to:
        work_order_status = WorkOrder.Status.ASSIGNED
    if incident.status in {FacilityIncident.Status.RESOLVED, FacilityIncident.Status.CLOSED}:
        work_order_status = WorkOrder.Status.COMPLETED

    unit = incident.facility_space.unit if incident.facility_space_id else None
    common_fields = {
        "property": incident.property or incident.facility.property,
        "facility": incident.facility or _facility_for_property(incident.property),
        "facility_space": incident.facility_space,
        "unit": unit,
        "title": f"Incident response - {incident.title}",
        "description": incident.description,
        "maintenance_mode": WorkOrder.MaintenanceMode.CORRECTIVE,
        "category": _work_order_category_for_incident(incident),
        "priority": priority,
        "status": work_order_status,
        "reported_by": incident.reported_by,
        "assigned_to": incident.assigned_to,
        "due_date": timezone.localdate(now) + timedelta(days=max(1, sla_hours // 8)),
        "sla_target_hours": sla_hours,
        "sla_due_at": now + timedelta(hours=sla_hours),
        "is_breakdown": incident.severity in {FacilityIncident.Severity.HIGH, FacilityIncident.Severity.CRITICAL},
        "notes": f"Generated from facility incident #{incident.id}.",
    }
    if incident.status in {FacilityIncident.Status.RESOLVED, FacilityIncident.Status.CLOSED}:
        common_fields["completed_date"] = timezone.localdate(incident.resolved_at or now)

    if incident.work_order_id:
        work_order = incident.work_order
        update_fields: list[str] = []
        for field_name, value in common_fields.items():
            if getattr(work_order, field_name) != value:
                setattr(work_order, field_name, value)
                update_fields.append(field_name)
        if update_fields:
            work_order.save(update_fields=[*dict.fromkeys([*update_fields, "updated_at"])])
        return False

    work_order = WorkOrder.objects.create(
        organization=incident.organization,
        **common_fields,
    )
    incident.work_order = work_order
    incident.save(update_fields=["work_order", "updated_at"])
    _create_audit_log(
        organization=incident.organization,
        property_obj=incident.property,
        facility=incident.facility or _facility_for_property(incident.property),
        entity_type=FacilitySafetyAuditLog.EntityType.INCIDENT,
        event_type=FacilitySafetyAuditLog.EventType.CORRECTIVE_WORK_ORDER_CREATED,
        entity_id=incident.id,
        actor=actor,
        summary=f"Created corrective work order for incident {incident.incident_code or incident.id}.",
        details={"incident_id": incident.id, "work_order_id": work_order.id},
    )
    return True


def inspection_is_clear_for_incident_resolution(inspection: Inspection) -> bool:
    if inspection.status != Inspection.Status.COMPLETED:
        return False
    if inspection.rating == Inspection.Rating.FAIL:
        return False
    if inspection.compliance_status == Inspection.ComplianceStatus.NON_COMPLIANT:
        return False
    if inspection.risk_level in {Inspection.RiskLevel.HIGH, Inspection.RiskLevel.CRITICAL}:
        return False
    if inspection.corrective_action_required:
        return False
    return True


def sync_incident_from_related_records(incident: FacilityIncident, *, actor=None, now=None) -> bool:
    now = now or timezone.now()
    changed = False
    update_fields: list[str] = []
    before_status = incident.status

    if (
        incident.work_order_id
        and incident.work_order.status == WorkOrder.Status.IN_PROGRESS
        and incident.status == FacilityIncident.Status.OPEN
    ):
        incident.status = FacilityIncident.Status.INVESTIGATING
        update_fields.append("status")
        changed = True

    work_order_done = incident.work_order_id and incident.work_order.status in {
        WorkOrder.Status.COMPLETED,
        WorkOrder.Status.VERIFIED,
    }
    inspection_clear = (
        incident.follow_up_inspection_id is None
        or inspection_is_clear_for_incident_resolution(incident.follow_up_inspection)
    )

    if (
        incident.status not in {FacilityIncident.Status.RESOLVED, FacilityIncident.Status.CLOSED}
        and work_order_done
        and inspection_clear
    ):
        incident.status = FacilityIncident.Status.RESOLVED
        incident.resolved_at = incident.resolved_at or now
        update_fields.extend(["status", "resolved_at"])
        changed = True

    if changed:
        incident.save(update_fields=[*dict.fromkeys([*update_fields, "updated_at"])])
        if before_status != incident.status and incident.status == FacilityIncident.Status.RESOLVED:
            _create_audit_log(
                organization=incident.organization,
                property_obj=incident.property,
                facility=incident.facility or _facility_for_property(incident.property),
                entity_type=FacilitySafetyAuditLog.EntityType.INCIDENT,
                event_type=FacilitySafetyAuditLog.EventType.INCIDENT_RESOLVED,
                entity_id=incident.id,
                actor=actor,
                summary=f"Resolved incident {incident.incident_code or incident.id}.",
                details={"incident_id": incident.id},
            )
    return changed


def ensure_health_safety_inspection_defaults(inspection: Inspection, *, actor=None, now=None) -> bool:
    now = now or timezone.now()
    changed = False
    update_fields: list[str] = []

    if inspection.unit_id and inspection.property_id != inspection.unit.property_id:
        inspection.property = inspection.unit.property
        update_fields.append("property")
        changed = True

    if inspection.status == Inspection.Status.COMPLETED and inspection.completed_date is None:
        inspection.completed_date = timezone.localdate(now)
        update_fields.append("completed_date")
        changed = True

    if inspection.status == Inspection.Status.COMPLETED:
        if not inspection.compliance_status:
            if inspection.rating == Inspection.Rating.FAIL:
                inspection.compliance_status = Inspection.ComplianceStatus.NON_COMPLIANT
            elif inspection.rating == Inspection.Rating.CONDITIONAL:
                inspection.compliance_status = Inspection.ComplianceStatus.PARTIALLY_COMPLIANT
            else:
                inspection.compliance_status = Inspection.ComplianceStatus.COMPLIANT
            update_fields.append("compliance_status")
            changed = True

        if not inspection.risk_level:
            if inspection.rating == Inspection.Rating.FAIL or inspection.compliance_status == Inspection.ComplianceStatus.NON_COMPLIANT:
                inspection.risk_level = Inspection.RiskLevel.HIGH
            elif inspection.rating == Inspection.Rating.CONDITIONAL:
                inspection.risk_level = Inspection.RiskLevel.MEDIUM
            else:
                inspection.risk_level = Inspection.RiskLevel.LOW
            update_fields.append("risk_level")
            changed = True

        if not inspection.corrective_action_required and (
            inspection.rating == Inspection.Rating.FAIL
            or inspection.compliance_status in {
                Inspection.ComplianceStatus.NON_COMPLIANT,
                Inspection.ComplianceStatus.PARTIALLY_COMPLIANT,
            }
            or inspection.risk_level in {Inspection.RiskLevel.HIGH, Inspection.RiskLevel.CRITICAL}
        ):
            inspection.corrective_action_required = True
            update_fields.append("corrective_action_required")
            changed = True

        if not inspection.follow_up_required and (
            inspection.rating == Inspection.Rating.CONDITIONAL
            or inspection.risk_level in {Inspection.RiskLevel.HIGH, Inspection.RiskLevel.CRITICAL}
        ):
            inspection.follow_up_required = True
            update_fields.append("follow_up_required")
            changed = True

    if changed:
        inspection.save(update_fields=[*dict.fromkeys([*update_fields, "updated_at"])])
    return changed


def sync_violation_for_inspection(inspection: Inspection, *, actor=None, now=None) -> int:
    now = now or timezone.now()
    title = f"Inspection finding: {inspection.title}"
    should_raise = (
        inspection.status == Inspection.Status.COMPLETED
        and (
            inspection.corrective_action_required
            or inspection.rating == Inspection.Rating.FAIL
            or inspection.compliance_status in {
                Inspection.ComplianceStatus.NON_COMPLIANT,
                Inspection.ComplianceStatus.PARTIALLY_COMPLIANT,
            }
            or inspection.risk_level in {Inspection.RiskLevel.HIGH, Inspection.RiskLevel.CRITICAL}
        )
    )

    if not should_raise:
        _resolve_open_violation(
            inspection.property,
            title,
            resolution_note="Inspection outcome no longer requires corrective compliance action.",
        )
        return 0

    existing = _open_violation_for(inspection.property, title)
    severity = _violation_severity_for_risk(inspection.risk_level)
    due_date = _violation_due_date_for_severity(severity)
    if existing is not None:
        update_fields: list[str] = []
        if existing.severity != severity:
            existing.severity = severity
            update_fields.append("severity")
        if existing.due_date != due_date:
            existing.due_date = due_date
            update_fields.append("due_date")
        if inspection.findings and existing.description != inspection.findings:
            existing.description = inspection.findings
            update_fields.append("description")
        if inspection.follow_up_notes and existing.corrective_action != inspection.follow_up_notes:
            existing.corrective_action = inspection.follow_up_notes
            update_fields.append("corrective_action")
        if update_fields:
            existing.save(update_fields=[*dict.fromkeys([*update_fields, "updated_at"])])
        return 0

    violation = ComplianceViolation.objects.create(
        organization=inspection.organization,
        property=inspection.property,
        title=title,
        description=inspection.findings,
        violation_type=_compliance_category_for_inspection(inspection),
        severity=severity,
        status=ComplianceViolation.Status.OPEN,
        reported_date=inspection.completed_date or timezone.localdate(now),
        due_date=due_date,
        corrective_action=inspection.follow_up_notes,
        assigned_to=inspection.inspector,
        notes=f"Auto-created from inspection #{inspection.id}.",
    )
    _create_audit_log(
        organization=inspection.organization,
        property_obj=inspection.property,
        facility=_facility_for_property(inspection.property),
        entity_type=FacilitySafetyAuditLog.EntityType.INSPECTION,
        event_type=FacilitySafetyAuditLog.EventType.VIOLATION_CREATED,
        entity_id=inspection.id,
        actor=actor,
        summary=f"Created compliance violation from inspection {inspection.title}.",
        details={"inspection_id": inspection.id, "violation_id": violation.id},
    )
    return 1


def sync_incident_from_inspection(inspection: Inspection, *, actor=None, now=None) -> bool:
    incident = (
        FacilityIncident.objects.filter(follow_up_inspection=inspection)
        .select_related("property", "facility", "facility_space", "work_order", "follow_up_inspection")
        .first()
    )
    if incident is None:
        return False
    return sync_incident_from_related_records(incident, actor=actor, now=now)


def _checklist_metrics(checklist: FacilityComplianceChecklist):
    items = list(checklist.items.all())
    total_items = len(items)
    answered_items = sum(1 for item in items if item.is_compliant is not None)
    compliant_items = sum(1 for item in items if item.is_compliant is True)
    mandatory_failures = sum(1 for item in items if item.is_mandatory and item.is_compliant is False)
    score = round((compliant_items / total_items) * 100, 2) if total_items else 0
    return {
        "total_items": total_items,
        "answered_items": answered_items,
        "compliant_items": compliant_items,
        "mandatory_failures": mandatory_failures,
        "score": score,
    }


def ensure_checklist_defaults(checklist: FacilityComplianceChecklist, *, actor=None, now=None) -> bool:
    now = now or timezone.now()
    today = timezone.localdate(now)
    changed = False
    update_fields: list[str] = []

    if checklist.facility_space_id:
        if checklist.facility_id != checklist.facility_space.facility_id:
            checklist.facility = checklist.facility_space.facility
            update_fields.append("facility")
            changed = True
        if checklist.property_id != checklist.facility_space.facility.property_id:
            checklist.property = checklist.facility_space.facility.property
            update_fields.append("property")
            changed = True
    elif checklist.facility_id and checklist.property_id != checklist.facility.property_id:
        checklist.property = checklist.facility.property
        update_fields.append("property")
        changed = True
    elif checklist.linked_incident_id:
        incident = checklist.linked_incident
        if checklist.property_id != incident.property_id:
            checklist.property = incident.property
            update_fields.append("property")
            changed = True
        if incident.facility_id and checklist.facility_id != incident.facility_id:
            checklist.facility = incident.facility
            update_fields.append("facility")
            changed = True
        if incident.facility_space_id and checklist.facility_space_id != incident.facility_space_id:
            checklist.facility_space = incident.facility_space
            update_fields.append("facility_space")
            changed = True
    elif checklist.linked_inspection_id:
        inspection = checklist.linked_inspection
        if checklist.property_id != inspection.property_id:
            checklist.property = inspection.property
            update_fields.append("property")
            changed = True
        inspection_space = _space_for_unit(inspection.unit)
        inspection_facility = _facility_for_property(inspection.property)
        if inspection_facility and checklist.facility_id != inspection_facility.id:
            checklist.facility = inspection_facility
            update_fields.append("facility")
            changed = True
        if inspection_space and checklist.facility_space_id != inspection_space.id:
            checklist.facility_space = inspection_space
            update_fields.append("facility_space")
            changed = True

    metrics = _checklist_metrics(checklist)
    if checklist.total_items_count != metrics["total_items"]:
        checklist.total_items_count = metrics["total_items"]
        update_fields.append("total_items_count")
        changed = True
    if checklist.compliant_items_count != metrics["compliant_items"]:
        checklist.compliant_items_count = metrics["compliant_items"]
        update_fields.append("compliant_items_count")
        changed = True
    if float(checklist.overall_score) != float(metrics["score"]):
        checklist.overall_score = metrics["score"]
        update_fields.append("overall_score")
        changed = True

    target_status = checklist.status
    if checklist.status != FacilityComplianceChecklist.Status.CANCELLED:
        if metrics["total_items"] and metrics["answered_items"] >= metrics["total_items"]:
            target_status = FacilityComplianceChecklist.Status.COMPLETED
        elif metrics["answered_items"] > 0:
            target_status = FacilityComplianceChecklist.Status.IN_PROGRESS
        elif checklist.status == FacilityComplianceChecklist.Status.DRAFT:
            target_status = FacilityComplianceChecklist.Status.DRAFT
        elif checklist.due_date < today:
            target_status = FacilityComplianceChecklist.Status.OVERDUE
        else:
            target_status = FacilityComplianceChecklist.Status.ACTIVE

    if checklist.status != target_status:
        checklist.status = target_status
        update_fields.append("status")
        changed = True

    if target_status == FacilityComplianceChecklist.Status.COMPLETED:
        if checklist.completed_at is None:
            checklist.completed_at = now
            update_fields.append("completed_at")
            changed = True
        completion_date = timezone.localdate(checklist.completed_at or now)
        if checklist.last_completed_date != completion_date:
            checklist.last_completed_date = completion_date
            update_fields.append("last_completed_date")
            changed = True
        interval_days = _checklist_interval_days(checklist.frequency)
        target_next_due = completion_date + timedelta(days=interval_days) if interval_days else None
        if checklist.next_due_date != target_next_due:
            checklist.next_due_date = target_next_due
            update_fields.append("next_due_date")
            changed = True

    if changed:
        checklist.save(update_fields=[*dict.fromkeys([*update_fields, "updated_at"])])
    return changed


def sync_property_compliance_for_checklist(checklist: FacilityComplianceChecklist, *, actor=None) -> int:
    if checklist.compliance_requirement_id is None:
        return 0

    metrics = _checklist_metrics(checklist)
    target_status = PropertyCompliance.Status.PENDING_REVIEW
    if metrics["mandatory_failures"] > 0:
        target_status = PropertyCompliance.Status.NON_COMPLIANT
    elif checklist.status == FacilityComplianceChecklist.Status.COMPLETED:
        target_status = PropertyCompliance.Status.COMPLIANT

    record, created = PropertyCompliance.objects.get_or_create(
        organization=checklist.organization,
        property=checklist.property,
        requirement=checklist.compliance_requirement,
        defaults={"status": target_status},
    )

    changed = created
    update_fields: list[str] = []
    field_values = {
        "status": target_status,
        "last_reviewed_date": checklist.last_completed_date,
        "next_review_date": checklist.next_due_date or checklist.due_date,
        "responsible_person": checklist.responsible_person,
        "notes": f"Synced from facility checklist #{checklist.id}.",
    }
    for field_name, value in field_values.items():
        if getattr(record, field_name) != value:
            setattr(record, field_name, value)
            update_fields.append(field_name)
            changed = True

    if update_fields:
        record.save(update_fields=[*dict.fromkeys([*update_fields, "updated_at"])])

    if changed:
        _create_audit_log(
            organization=checklist.organization,
            property_obj=checklist.property,
            facility=checklist.facility or _facility_for_property(checklist.property),
            entity_type=FacilitySafetyAuditLog.EntityType.COMPLIANCE,
            event_type=FacilitySafetyAuditLog.EventType.COMPLIANCE_SYNCED,
            entity_id=record.id,
            actor=actor,
            summary=f"Synced compliance record for checklist {checklist.title}.",
            details={"checklist_id": checklist.id, "compliance_id": record.id},
        )
    return 1 if changed else 0


def sync_violation_for_checklist(checklist: FacilityComplianceChecklist, *, actor=None) -> int:
    metrics = _checklist_metrics(checklist)
    title = f"Checklist failure: {checklist.title}"

    if not checklist.auto_create_violation or metrics["mandatory_failures"] == 0:
        _resolve_open_violation(
            checklist.property,
            title,
            resolution_note="Checklist responses are now compliant.",
        )
        return 0

    existing = _open_violation_for(checklist.property, title)
    severity = (
        ComplianceViolation.Severity.MAJOR
        if metrics["mandatory_failures"] > 1
        else ComplianceViolation.Severity.MODERATE
    )
    due_date = _violation_due_date_for_severity(severity)
    corrective_actions = "\n".join(
        item.corrective_action
        for item in checklist.items.filter(is_compliant=False)
        if item.corrective_action
    ).strip()

    if existing is not None:
        update_fields: list[str] = []
        if existing.severity != severity:
            existing.severity = severity
            update_fields.append("severity")
        if existing.due_date != due_date:
            existing.due_date = due_date
            update_fields.append("due_date")
        if corrective_actions and existing.corrective_action != corrective_actions:
            existing.corrective_action = corrective_actions
            update_fields.append("corrective_action")
        if update_fields:
            existing.save(update_fields=[*dict.fromkeys([*update_fields, "updated_at"])])
        return 0

    violation = ComplianceViolation.objects.create(
        organization=checklist.organization,
        property=checklist.property,
        compliance_item=(
            PropertyCompliance.objects.filter(
                organization=checklist.organization,
                property=checklist.property,
                requirement=checklist.compliance_requirement,
            ).first()
            if checklist.compliance_requirement_id
            else None
        ),
        title=title,
        description=f"Mandatory checklist items failed for {checklist.title}.",
        violation_type=(
            checklist.compliance_requirement.category
            if checklist.compliance_requirement_id
            else _compliance_category_for_checklist(checklist)
        ),
        severity=severity,
        status=ComplianceViolation.Status.OPEN,
        reported_date=timezone.localdate(),
        due_date=due_date,
        corrective_action=corrective_actions,
        assigned_to=checklist.responsible_person,
        notes=f"Auto-created from facility checklist #{checklist.id}.",
    )
    _create_audit_log(
        organization=checklist.organization,
        property_obj=checklist.property,
        facility=checklist.facility or _facility_for_property(checklist.property),
        entity_type=FacilitySafetyAuditLog.EntityType.CHECKLIST,
        event_type=FacilitySafetyAuditLog.EventType.VIOLATION_CREATED,
        entity_id=checklist.id,
        actor=actor,
        summary=f"Created compliance violation for checklist {checklist.title}.",
        details={"checklist_id": checklist.id, "violation_id": violation.id},
    )
    return 1


def ensure_follow_up_inspection_for_checklist(checklist: FacilityComplianceChecklist, *, actor=None, now=None) -> bool:
    now = now or timezone.now()
    metrics = _checklist_metrics(checklist)
    if not checklist.auto_create_follow_up_inspection or metrics["mandatory_failures"] == 0:
        return False
    if checklist.linked_inspection_id is not None:
        return False

    unit = checklist.facility_space.unit if checklist.facility_space_id else None
    inspection = Inspection.objects.create(
        organization=checklist.organization,
        property=checklist.property,
        unit=unit,
        title=f"Follow-up Inspection - {checklist.title}",
        inspection_type=_inspection_type_for_checklist(checklist),
        status=Inspection.Status.SCHEDULED,
        scheduled_date=timezone.localdate(now) + timedelta(days=1),
        inspector=checklist.responsible_person,
        notes=f"Auto-created from compliance checklist #{checklist.id}.",
    )
    checklist.linked_inspection = inspection
    checklist.save(update_fields=["linked_inspection", "updated_at"])
    _create_audit_log(
        organization=checklist.organization,
        property_obj=checklist.property,
        facility=checklist.facility or _facility_for_property(checklist.property),
        entity_type=FacilitySafetyAuditLog.EntityType.CHECKLIST,
        event_type=FacilitySafetyAuditLog.EventType.INSPECTION_SCHEDULED,
        entity_id=checklist.id,
        actor=actor,
        summary=f"Scheduled follow-up inspection for checklist {checklist.title}.",
        details={"checklist_id": checklist.id, "inspection_id": inspection.id},
    )
    return True


def regulatory_document_status_for(document: FacilityRegulatoryDocument, *, today=None) -> str:
    today = today or timezone.localdate()
    if document.status == FacilityRegulatoryDocument.Status.SUPERSEDED:
        return FacilityRegulatoryDocument.Status.SUPERSEDED
    if document.expiry_date and document.expiry_date < today:
        return FacilityRegulatoryDocument.Status.EXPIRED
    if document.expiry_date and document.expiry_date <= today + timedelta(days=30):
        return FacilityRegulatoryDocument.Status.EXPIRING_SOON
    if document.property_document_id:
        return FacilityRegulatoryDocument.Status.VALID
    return FacilityRegulatoryDocument.Status.PENDING_REVIEW


def ensure_regulatory_document_defaults(document: FacilityRegulatoryDocument, *, actor=None, today=None) -> bool:
    today = today or timezone.localdate()
    changed = False
    update_fields: list[str] = []

    if document.facility_id and document.property_id != document.facility.property_id:
        document.property = document.facility.property
        update_fields.append("property")
        changed = True
    elif document.property_document_id and document.property_id != document.property_document.property_id:
        document.property = document.property_document.property
        update_fields.append("property")
        changed = True

    if document.property_id:
        facility = _facility_for_property(document.property)
        if facility and document.facility_id != facility.id:
            document.facility = facility
            update_fields.append("facility")
            changed = True

    if document.uploaded_by_id is None and actor:
        document.uploaded_by = actor
        update_fields.append("uploaded_by")
        changed = True

    target_status = regulatory_document_status_for(document, today=today)
    if document.status != target_status:
        document.status = target_status
        update_fields.append("status")
        changed = True

    if document.property_document.organization_id != document.organization_id:
        document.property_document.organization = document.organization
        document.property_document.save(update_fields=["organization"])
    if document.property_document.property_id != document.property_id:
        document.property_document.property = document.property
        document.property_document.save(update_fields=["property"])

    if changed:
        document.save(update_fields=[*dict.fromkeys([*update_fields, "updated_at"])])
    return changed


def sync_property_compliance_for_regulatory_document(document: FacilityRegulatoryDocument, *, actor=None) -> int:
    if document.compliance_requirement_id is None:
        return 0

    target_status = PropertyCompliance.Status.PENDING_REVIEW
    if document.status == FacilityRegulatoryDocument.Status.EXPIRED:
        target_status = PropertyCompliance.Status.EXPIRED
    elif document.status in {
        FacilityRegulatoryDocument.Status.VALID,
        FacilityRegulatoryDocument.Status.EXPIRING_SOON,
    }:
        target_status = PropertyCompliance.Status.COMPLIANT

    record, created = PropertyCompliance.objects.get_or_create(
        organization=document.organization,
        property=document.property,
        requirement=document.compliance_requirement,
        defaults={"status": target_status},
    )

    changed = created
    update_fields: list[str] = []
    review_date = timezone.localdate()
    field_values = {
        "status": target_status,
        "certificate_number": document.reference_number,
        "issuing_authority": document.issuing_authority,
        "issue_date": document.issue_date,
        "expiry_date": document.expiry_date,
        "last_reviewed_date": review_date,
        "next_review_date": document.review_due_date or document.expiry_date,
        "notes": f"Synced from facility regulatory document #{document.id}.",
    }
    for field_name, value in field_values.items():
        if getattr(record, field_name) != value:
            setattr(record, field_name, value)
            update_fields.append(field_name)
            changed = True

    if update_fields:
        record.save(update_fields=[*dict.fromkeys([*update_fields, "updated_at"])])

    if changed:
        _create_audit_log(
            organization=document.organization,
            property_obj=document.property,
            facility=document.facility or _facility_for_property(document.property),
            entity_type=FacilitySafetyAuditLog.EntityType.COMPLIANCE,
            event_type=FacilitySafetyAuditLog.EventType.COMPLIANCE_SYNCED,
            entity_id=record.id,
            actor=actor,
            summary=f"Synced compliance record for document {document.property_document.title}.",
            details={"document_id": document.id, "compliance_id": record.id},
        )
    return 1 if changed else 0


def sync_violation_for_regulatory_document(document: FacilityRegulatoryDocument, *, actor=None) -> int:
    title = f"Expired regulatory document: {document.property_document.title}"
    if document.status != FacilityRegulatoryDocument.Status.EXPIRED:
        _resolve_open_violation(
            document.property,
            title,
            resolution_note="Regulatory document status is no longer expired.",
        )
        return 0

    existing = _open_violation_for(document.property, title)
    if existing is not None:
        return 0

    violation = ComplianceViolation.objects.create(
        organization=document.organization,
        property=document.property,
        compliance_item=(
            PropertyCompliance.objects.filter(
                organization=document.organization,
                property=document.property,
                requirement=document.compliance_requirement,
            ).first()
            if document.compliance_requirement_id
            else None
        ),
        title=title,
        description=f"Regulatory document {document.property_document.title} has expired.",
        violation_type=(
            document.compliance_requirement.category
            if document.compliance_requirement_id
            else ComplianceRequirement.Category.REGULATORY
        ),
        severity=ComplianceViolation.Severity.MAJOR,
        status=ComplianceViolation.Status.OPEN,
        reported_date=timezone.localdate(),
        due_date=document.review_due_date or timezone.localdate() + timedelta(days=3),
        corrective_action="Renew or replace the expired regulatory document.",
        assigned_to=_user_display(document.uploaded_by),
        notes=f"Auto-created from facility regulatory document #{document.id}.",
    )
    _create_audit_log(
        organization=document.organization,
        property_obj=document.property,
        facility=document.facility or _facility_for_property(document.property),
        entity_type=FacilitySafetyAuditLog.EntityType.DOCUMENT,
        event_type=FacilitySafetyAuditLog.EventType.REGULATORY_DOCUMENT_FLAGGED,
        entity_id=document.id,
        actor=actor,
        summary=f"Flagged expired regulatory document {document.property_document.title}.",
        details={"document_id": document.id, "violation_id": violation.id},
    )
    return 1


def run_health_safety_compliance_automation(organization, *, actor=None) -> dict[str, int]:
    now = timezone.now()
    summary = {
        "incidents_synced": 0,
        "incidents_resolved": 0,
        "follow_up_inspections_created": 0,
        "corrective_work_orders_created": 0,
        "inspections_synced": 0,
        "checklists_synced": 0,
        "checklist_failures": 0,
        "compliance_records_synced": 0,
        "violations_created": 0,
        "regulatory_documents_synced": 0,
        "expired_documents_flagged": 0,
        "audit_logs_created": 0,
    }

    incidents = (
        FacilityIncident.objects.filter(organization=organization)
        .select_related(
            "property",
            "facility",
            "facility_space",
            "facility_space__unit",
            "work_order",
            "follow_up_inspection",
        )
        .order_by("-occurred_at", "-id")
    )
    for incident in incidents:
        before_status = incident.status
        if ensure_incident_defaults(incident, actor=actor, now=now):
            summary["incidents_synced"] += 1
        if ensure_follow_up_inspection_for_incident(incident, actor=actor, now=now):
            summary["follow_up_inspections_created"] += 1
        if ensure_corrective_work_order_for_incident(incident, actor=actor, now=now):
            summary["corrective_work_orders_created"] += 1
        if sync_incident_from_related_records(incident, actor=actor, now=now):
            summary["incidents_synced"] += 1
        incident.refresh_from_db()
        if before_status != incident.status and incident.status == FacilityIncident.Status.RESOLVED:
            summary["incidents_resolved"] += 1

    inspections = (
        Inspection.objects.filter(organization=organization, property__facility_registry__isnull=False)
        .select_related("property", "unit", "unit__facility_space", "unit__facility_space__facility")
        .order_by("scheduled_date", "id")
    )
    for inspection in inspections:
        if ensure_health_safety_inspection_defaults(inspection, actor=actor, now=now):
            summary["inspections_synced"] += 1
        summary["violations_created"] += sync_violation_for_inspection(inspection, actor=actor, now=now)
        if sync_incident_from_inspection(inspection, actor=actor, now=now):
            summary["incidents_resolved"] += 1

    checklists = (
        FacilityComplianceChecklist.objects.filter(organization=organization)
        .select_related(
            "property",
            "facility",
            "facility_space",
            "facility_space__unit",
            "linked_incident",
            "linked_inspection",
            "compliance_requirement",
        )
        .prefetch_related("items")
        .order_by("due_date", "id")
    )
    for checklist in checklists:
        if ensure_checklist_defaults(checklist, actor=actor, now=now):
            summary["checklists_synced"] += 1
        metrics = _checklist_metrics(checklist)
        summary["checklist_failures"] += metrics["mandatory_failures"]
        summary["compliance_records_synced"] += sync_property_compliance_for_checklist(checklist, actor=actor)
        summary["violations_created"] += sync_violation_for_checklist(checklist, actor=actor)
        if ensure_follow_up_inspection_for_checklist(checklist, actor=actor, now=now):
            summary["follow_up_inspections_created"] += 1

    documents = (
        FacilityRegulatoryDocument.objects.filter(organization=organization)
        .select_related("property", "facility", "property_document", "uploaded_by", "compliance_requirement")
        .order_by("expiry_date", "-id")
    )
    for document in documents:
        previous_status = document.status
        if ensure_regulatory_document_defaults(document, actor=actor):
            summary["regulatory_documents_synced"] += 1
        summary["compliance_records_synced"] += sync_property_compliance_for_regulatory_document(document, actor=actor)
        created_violations = sync_violation_for_regulatory_document(document, actor=actor)
        summary["violations_created"] += created_violations
        if previous_status != FacilityRegulatoryDocument.Status.EXPIRED and document.status == FacilityRegulatoryDocument.Status.EXPIRED:
            summary["expired_documents_flagged"] += 1

    _create_audit_log(
        organization=organization,
        entity_type=FacilitySafetyAuditLog.EntityType.WORKFLOW,
        event_type=FacilitySafetyAuditLog.EventType.WORKFLOW_SYNCED,
        actor=actor,
        summary="Ran health, safety, and compliance workflow automation.",
        details=summary,
    )
    summary["audit_logs_created"] += 1
    return summary
