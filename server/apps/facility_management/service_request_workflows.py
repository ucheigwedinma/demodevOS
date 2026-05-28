from __future__ import annotations

import logging
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.utils import timezone

from apps.finance.models import Invoice
from apps.properties.models import ServiceRequest, WorkOrder
from apps.support_desk.models import SupportTicket

logger = logging.getLogger(__name__)


SERVICE_REQUEST_ASSIGNMENT_KEYWORDS = {
    WorkOrder.Category.ELECTRICAL: {"electrical", "electric", "power", "mep", "engineer"},
    WorkOrder.Category.HVAC: {"hvac", "air", "mechanical", "cooling", "ac"},
    WorkOrder.Category.PLUMBING: {"plumbing", "plumber", "water", "pipe"},
    WorkOrder.Category.CLEANING: {"cleaning", "housekeeping", "janitor", "sanitation"},
    WorkOrder.Category.SECURITY: {"security", "guard", "surveillance", "access"},
    WorkOrder.Category.FIRE_SAFETY: {"fire", "safety", "hse"},
    WorkOrder.Category.MECHANICAL: {"mechanical", "machinery", "engineer", "technician"},
    WorkOrder.Category.ELEVATOR: {"elevator", "lift", "vertical"},
    WorkOrder.Category.GENERATOR: {"generator", "power", "diesel"},
    WorkOrder.Category.WATER_SYSTEMS: {"water", "treatment", "pump", "borehole"},
    WorkOrder.Category.STRUCTURAL: {"structural", "building", "civil"},
    WorkOrder.Category.LANDSCAPING: {"landscaping", "grounds", "gardener"},
    WorkOrder.Category.PAINTING: {"painting", "painter", "finishes"},
    WorkOrder.Category.GENERAL: {"maintenance", "facility", "operations", "support"},
}


def _notify_cascade(*, organization, event_key, title, message, severity="info"):
    """Fire a notification for a cascading cross-module action."""
    try:
        from apps.accounts.models import UserProfile
        from apps.notifications.services import Notification, dispatch_workflow_notification

        admins = [
            p.user
            for p in UserProfile.objects.filter(
                organization=organization, role="admin", user__is_active=True
            ).select_related("user")
        ]
        if not admins:
            return
        sev_map = {
            "info": Notification.Severity.INFO,
            "warning": Notification.Severity.WARNING,
            "critical": Notification.Severity.CRITICAL,
        }
        dispatch_workflow_notification(
            organization=organization,
            event_key=event_key,
            recipients=admins,
            fallback_title=title,
            fallback_message=message,
            fallback_category=Notification.Category.SYSTEM,
            fallback_severity=sev_map.get(severity, Notification.Severity.INFO),
        )
    except Exception:
        logger.debug("Cascade notification skipped", exc_info=True)


ACTIVE_SERVICE_REQUEST_STATUSES = {
    ServiceRequest.Status.OPEN,
    ServiceRequest.Status.ACKNOWLEDGED,
    ServiceRequest.Status.IN_PROGRESS,
    ServiceRequest.Status.ESCALATED,
}


def _user_display(user) -> str:
    if not user:
        return ""
    full_name = user.get_full_name().strip()
    return full_name or user.email or user.username


def _service_request_assignment_text(profile) -> str:
    values = [
        getattr(profile.assigned_role, "slug", ""),
        getattr(profile.assigned_role, "name", ""),
        profile.job_title,
        profile.business_unit,
        getattr(profile.department, "name", ""),
        profile.office_location,
    ]
    return " ".join(value.strip().lower() for value in values if value)


def _service_request_assignment_keywords(service_request: ServiceRequest) -> set[str]:
    keywords = {
        "maintenance",
        "facility",
        "facilities",
        "operations",
        "technician",
        "engineer",
        "support",
    }
    keywords.update(SERVICE_REQUEST_ASSIGNMENT_KEYWORDS.get(service_request.category, set()))
    free_text = " ".join(filter(None, [service_request.title, service_request.description])).lower()
    keywords.update(
        keyword
        for keyword in {
            "electrical",
            "power",
            "hvac",
            "air",
            "cooling",
            "plumbing",
            "water",
            "cleaning",
            "security",
            "fire",
            "generator",
            "mechanical",
            "elevator",
        }
        if keyword in free_text
    )
    return keywords


def _service_request_assignment_rank(profile, service_request: ServiceRequest, active_load: dict[int, int]) -> tuple[int, int, int, int, int, int]:
    from apps.accounts.models import UserProfile

    assignment_text = _service_request_assignment_text(profile)
    matched_keywords = sum(1 for keyword in _service_request_assignment_keywords(service_request) if keyword in assignment_text)

    score = matched_keywords * 3
    if any(word in assignment_text for word in {"maintenance", "facility", "operations", "technician", "engineer", "support"}):
        score += 4
    if profile.assigned_role_id:
        score += 1
    if profile.identity_type in {UserProfile.IdentityType.EMPLOYEE, UserProfile.IdentityType.USER}:
        score += 3
    elif profile.identity_type == UserProfile.IdentityType.PARTNER:
        score -= 1
    if profile.role == "member":
        score += 2
    elif profile.role == "admin":
        score -= 1

    return (
        score,
        int(bool(matched_keywords)),
        int(profile.role == "member"),
        int(profile.identity_type in {UserProfile.IdentityType.EMPLOYEE, UserProfile.IdentityType.USER}),
        -active_load.get(profile.user_id, 0),
        -profile.user_id,
    )


def _auto_assign_service_request_agent(service_request: ServiceRequest):
    if service_request.assigned_agent_id or service_request.organization_id is None:
        return None

    from apps.accounts.models import UserProfile

    candidate_qs = (
        UserProfile.objects.filter(
            organization_id=service_request.organization_id,
            user__is_active=True,
            user_status=UserProfile.UserStatus.ACTIVE,
        )
        .exclude(identity_type=UserProfile.IdentityType.SYSTEM_ACCOUNT)
        .select_related("user", "assigned_role", "department")
    )
    if service_request.requester_id:
        candidate_qs = candidate_qs.exclude(user_id=service_request.requester_id)

    candidates = list(candidate_qs)
    if not candidates:
        return None

    active_load = {
        row["assigned_agent"]: row["total"]
        for row in ServiceRequest.objects.filter(
            organization_id=service_request.organization_id,
            assigned_agent__isnull=False,
            status__in=ACTIVE_SERVICE_REQUEST_STATUSES,
        )
        .exclude(pk=service_request.pk)
        .values("assigned_agent")
        .annotate(total=Count("id"))
    }

    best_match = max(
        candidates,
        key=lambda profile: _service_request_assignment_rank(profile, service_request, active_load),
    )
    return best_match.user


def service_request_sla_hours_for(priority: str) -> int:
    mapping = {
        ServiceRequest.Priority.LOW: 72,
        ServiceRequest.Priority.MEDIUM: 24,
        ServiceRequest.Priority.HIGH: 8,
        ServiceRequest.Priority.URGENT: 4,
    }
    return mapping.get(priority, 24)


def service_request_sla_status_for(service_request: ServiceRequest, *, now=None) -> str:
    now = now or timezone.now()
    if service_request.status in {ServiceRequest.Status.RESOLVED, ServiceRequest.Status.CLOSED}:
        return "completed"
    if service_request.sla_due_at is None:
        return "untracked"
    if service_request.sla_due_at <= now:
        return "breached"

    remaining_hours = (service_request.sla_due_at - now).total_seconds() / 3600
    threshold_hours = 4
    if service_request.sla_target_hours:
        threshold_hours = max(1, min(4, round(service_request.sla_target_hours * 0.25)))
    if remaining_hours <= threshold_hours:
        return "at_risk"
    return "on_track"


def _active_work_order_status_for(service_request: ServiceRequest) -> str:
    if service_request.status == ServiceRequest.Status.IN_PROGRESS:
        return WorkOrder.Status.IN_PROGRESS
    if service_request.status == ServiceRequest.Status.ESCALATED:
        return WorkOrder.Status.IN_PROGRESS
    if service_request.assigned_to:
        return WorkOrder.Status.ASSIGNED
    return WorkOrder.Status.OPEN


def ensure_service_request_defaults(service_request: ServiceRequest, *, now=None) -> bool:
    now = now or timezone.now()
    changed = False
    update_fields: list[str] = []

    if service_request.facility_space_id:
        if service_request.facility_id != service_request.facility_space.facility_id:
            service_request.facility = service_request.facility_space.facility
            update_fields.append("facility")
            changed = True
        if service_request.unit_id != service_request.facility_space.unit_id:
            service_request.unit = service_request.facility_space.unit
            update_fields.append("unit")
            changed = True
        if service_request.property_id != service_request.facility_space.facility.property_id:
            service_request.property = service_request.facility_space.facility.property
            update_fields.append("property")
            changed = True
    elif service_request.facility_id and service_request.property_id != service_request.facility.property_id:
        service_request.property = service_request.facility.property
        update_fields.append("property")
        changed = True
    elif service_request.unit_id and service_request.property_id != service_request.unit.property_id:
        service_request.property = service_request.unit.property
        update_fields.append("property")
        changed = True

    if service_request.requester_id and not service_request.requested_by:
        service_request.requested_by = _user_display(service_request.requester)
        update_fields.append("requested_by")
        changed = True

    if not service_request.assigned_agent_id:
        auto_assigned_agent = _auto_assign_service_request_agent(service_request)
        if auto_assigned_agent is not None:
            service_request.assigned_agent = auto_assigned_agent
            update_fields.append("assigned_agent")
            changed = True

    if service_request.assigned_agent_id:
        assigned_label = _user_display(service_request.assigned_agent)
        if service_request.assigned_to != assigned_label:
            service_request.assigned_to = assigned_label
            update_fields.append("assigned_to")
            changed = True
        if service_request.status == ServiceRequest.Status.OPEN:
            service_request.status = ServiceRequest.Status.ACKNOWLEDGED
            update_fields.append("status")
            changed = True

    if service_request.sla_target_hours is None:
        service_request.sla_target_hours = service_request_sla_hours_for(service_request.priority)
        update_fields.append("sla_target_hours")
        changed = True

    if service_request.sla_due_at is None and service_request.status not in {
        ServiceRequest.Status.RESOLVED,
        ServiceRequest.Status.CLOSED,
    }:
        base_time = service_request.created_at or now
        service_request.sla_due_at = base_time + timedelta(hours=service_request.sla_target_hours or 24)
        update_fields.append("sla_due_at")
        changed = True

    if service_request.status in {
        ServiceRequest.Status.ACKNOWLEDGED,
        ServiceRequest.Status.IN_PROGRESS,
        ServiceRequest.Status.ESCALATED,
    } and service_request.first_response_at is None:
        service_request.first_response_at = now
        update_fields.append("first_response_at")
        changed = True

    if service_request.status == ServiceRequest.Status.ESCALATED and service_request.escalated_at is None:
        service_request.escalated_at = now
        update_fields.append("escalated_at")
        changed = True

    if service_request.status in {
        ServiceRequest.Status.RESOLVED,
        ServiceRequest.Status.CLOSED,
    } and service_request.resolved_date is None:
        service_request.resolved_date = timezone.localdate()
        update_fields.append("resolved_date")
        changed = True

    if changed:
        service_request.save(update_fields=list(dict.fromkeys(update_fields + ["updated_at"])))
    return changed


def ensure_service_request_work_order(service_request: ServiceRequest) -> bool:
    ensure_service_request_defaults(service_request)

    if service_request.work_order_id:
        work_order = service_request.work_order
        update_fields: list[str] = []
        desired_status = _active_work_order_status_for(service_request)
        desired_priority = (
            WorkOrder.Priority.HIGH
            if service_request.status == ServiceRequest.Status.ESCALATED and service_request.priority in {
                ServiceRequest.Priority.LOW,
                ServiceRequest.Priority.MEDIUM,
            }
            else service_request.priority
        )

        field_values = {
            "property": service_request.property,
            "facility": service_request.facility,
            "facility_space": service_request.facility_space,
            "unit": service_request.unit,
            "title": service_request.title,
            "description": service_request.description,
            "category": service_request.category,
            "priority": desired_priority,
            "reported_by": service_request.requested_by,
            "assigned_to": service_request.assigned_to,
            "sla_target_hours": service_request.sla_target_hours,
            "sla_due_at": service_request.sla_due_at,
            "due_date": service_request.sla_due_at.date() if service_request.sla_due_at else None,
        }
        if service_request.status in {ServiceRequest.Status.RESOLVED, ServiceRequest.Status.CLOSED}:
            field_values["status"] = WorkOrder.Status.COMPLETED
            field_values["completed_date"] = service_request.resolved_date or timezone.localdate()
        else:
            field_values["status"] = desired_status

        for field_name, value in field_values.items():
            if getattr(work_order, field_name) != value:
                setattr(work_order, field_name, value)
                update_fields.append(field_name)

        if update_fields:
            work_order.save(update_fields=list(dict.fromkeys(update_fields + ["updated_at"])))
        return False

    work_order_status = (
        WorkOrder.Status.COMPLETED
        if service_request.status in {ServiceRequest.Status.RESOLVED, ServiceRequest.Status.CLOSED}
        else _active_work_order_status_for(service_request)
    )
    work_order = WorkOrder.objects.create(
        organization=service_request.organization,
        property=service_request.property,
        facility=service_request.facility,
        facility_space=service_request.facility_space,
        unit=service_request.unit,
        title=service_request.title,
        description=service_request.description,
        maintenance_mode=WorkOrder.MaintenanceMode.CORRECTIVE,
        category=service_request.category,
        priority=service_request.priority,
        status=work_order_status,
        reported_by=service_request.requested_by,
        assigned_to=service_request.assigned_to,
        due_date=service_request.sla_due_at.date() if service_request.sla_due_at else None,
        sla_target_hours=service_request.sla_target_hours,
        sla_due_at=service_request.sla_due_at,
        completed_date=service_request.resolved_date
        if service_request.status in {ServiceRequest.Status.RESOLVED, ServiceRequest.Status.CLOSED}
        else None,
        notes=f"Generated from service request #{service_request.id}.",
    )
    service_request.work_order = work_order
    service_request.save(update_fields=["work_order", "updated_at"])

    _notify_cascade(
        organization=service_request.organization,
        event_key="service_request_work_order_created",
        title=f"Work Order Auto-Created — {work_order.title[:60]}",
        message=(
            f"A corrective work order has been automatically generated from "
            f"service request #{service_request.id} ('{service_request.title[:60]}'). "
            f"Priority: {service_request.priority}. The maintenance team has been notified."
        ),
    )
    return True


def sync_service_request_from_work_order(service_request: ServiceRequest, *, now=None) -> bool:
    if not service_request.work_order_id:
        return False

    now = now or timezone.now()
    work_order = service_request.work_order
    changed = False
    update_fields: list[str] = []

    if work_order.assigned_to and service_request.assigned_to != work_order.assigned_to:
        service_request.assigned_to = work_order.assigned_to
        update_fields.append("assigned_to")
        changed = True

    if work_order.status == WorkOrder.Status.IN_PROGRESS and service_request.status != ServiceRequest.Status.IN_PROGRESS:
        service_request.status = ServiceRequest.Status.IN_PROGRESS
        update_fields.append("status")
        changed = True
    elif work_order.status in {WorkOrder.Status.COMPLETED, WorkOrder.Status.VERIFIED} and service_request.status not in {
        ServiceRequest.Status.RESOLVED,
        ServiceRequest.Status.CLOSED,
    }:
        service_request.status = ServiceRequest.Status.RESOLVED
        service_request.resolved_date = work_order.completed_date or timezone.localdate()
        update_fields.extend(["status", "resolved_date"])
        changed = True
    elif work_order.status == WorkOrder.Status.ASSIGNED and service_request.status == ServiceRequest.Status.OPEN:
        service_request.status = ServiceRequest.Status.ACKNOWLEDGED
        update_fields.append("status")
        changed = True

    if service_request.status in {
        ServiceRequest.Status.ACKNOWLEDGED,
        ServiceRequest.Status.IN_PROGRESS,
        ServiceRequest.Status.ESCALATED,
    } and service_request.first_response_at is None:
        service_request.first_response_at = now
        update_fields.append("first_response_at")
        changed = True

    if changed:
        service_request.save(update_fields=list(dict.fromkeys(update_fields + ["updated_at"])))

        new_status = service_request.get_status_display()
        _notify_cascade(
            organization=service_request.organization,
            event_key="service_request_synced_from_work_order",
            title=f"Service Request Updated — {service_request.title[:50]}",
            message=(
                f"Service request #{service_request.id} ('{service_request.title[:50]}') "
                f"has been automatically updated to {new_status} based on work order progress."
            ),
        )
    return changed


def sync_invoice_collection_status(invoice: Invoice) -> bool:
    previous_status = invoice.status
    today = timezone.localdate()
    paid_total = invoice.payments.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    if paid_total >= invoice.total_amount and invoice.total_amount > 0:
        target_status = Invoice.Status.PAID
    elif invoice.status in {Invoice.Status.DRAFT, Invoice.Status.CANCELLED}:
        target_status = invoice.status
    else:
        target_status = Invoice.Status.OVERDUE if invoice.due_date < today else Invoice.Status.SENT

    if target_status == previous_status:
        return False

    invoice.status = target_status
    invoice.save(update_fields=["status", "updated_at"])

    _notify_cascade(
        organization=invoice.organization,
        event_key="invoice_collection_status_synced",
        title=f"Invoice Status Auto-Updated — #{invoice.invoice_number}",
        message=(
            f"Invoice #{invoice.invoice_number} has been automatically updated from "
            f"{previous_status} to {target_status} following payment activity. "
            + ("The invoice is now fully settled." if target_status == Invoice.Status.PAID else "")
        ),
    )
    return True


def resolve_billing_tickets_for_invoice(invoice: Invoice, *, resolution_note: str = "") -> int:
    tickets = SupportTicket.objects.filter(
        organization=invoice.organization,
        invoice=invoice,
        category=SupportTicket.Category.BILLING,
    ).exclude(status__in=[SupportTicket.Status.RESOLVED, SupportTicket.Status.CLOSED])

    resolved = 0
    now = timezone.now()
    for ticket in tickets:
        notes = ticket.resolution_notes or ""
        if resolution_note and resolution_note not in notes:
            notes = f"{notes}\n{resolution_note}".strip()
        ticket.status = SupportTicket.Status.RESOLVED
        ticket.resolution_notes = notes
        ticket.resolved_at = now
        ticket.save(update_fields=["status", "resolution_notes", "resolved_at", "updated_at"])
        resolved += 1

    if resolved > 0:
        _notify_cascade(
            organization=invoice.organization,
            event_key="billing_tickets_auto_resolved",
            title=f"Billing Tickets Auto-Resolved — Invoice #{invoice.invoice_number}",
            message=(
                f"{resolved} billing ticket(s) linked to invoice #{invoice.invoice_number} "
                f"have been automatically resolved following payment confirmation."
            ),
        )
    return resolved


def run_service_request_helpdesk_automation(organization) -> dict[str, int]:
    now = timezone.now()
    summary = {
        "service_requests_synced": 0,
        "service_requests_escalated": 0,
        "work_orders_created": 0,
        "overdue_invoices_flagged": 0,
        "billing_tickets_synced": 0,
        "billing_tickets_escalated": 0,
        "billing_tickets_resolved": 0,
    }

    service_requests = (
        ServiceRequest.objects.filter(organization=organization)
        .select_related(
            "property",
            "facility",
            "facility_space",
            "facility_space__facility",
            "facility_space__unit",
            "unit",
            "requester",
            "assigned_agent",
            "work_order",
        )
    )

    for service_request in service_requests:
        changed = ensure_service_request_defaults(service_request, now=now)
        created_work_order = ensure_service_request_work_order(service_request)
        if created_work_order:
            summary["work_orders_created"] += 1

        if sync_service_request_from_work_order(service_request, now=now):
            summary["service_requests_synced"] += 1
            changed = True

        if (
            service_request.status in ACTIVE_SERVICE_REQUEST_STATUSES
            and service_request.sla_due_at is not None
            and service_request.sla_due_at <= now
            and service_request.status != ServiceRequest.Status.ESCALATED
        ):
            service_request.status = ServiceRequest.Status.ESCALATED
            service_request.escalated_at = now
            service_request.save(update_fields=["status", "escalated_at", "updated_at"])
            ensure_service_request_work_order(service_request)
            summary["service_requests_escalated"] += 1
        elif changed:
            summary["service_requests_synced"] += 1

    invoices = (
        Invoice.objects.filter(organization=organization)
        .select_related("customer", "property")
    )
    for invoice in invoices:
        if sync_invoice_collection_status(invoice):
            summary["overdue_invoices_flagged"] += 1
        if invoice.status == Invoice.Status.PAID:
            summary["billing_tickets_resolved"] += resolve_billing_tickets_for_invoice(
                invoice,
                resolution_note=f"Auto-resolved after payment for invoice {invoice.invoice_number}.",
            )

    billing_tickets = (
        SupportTicket.objects.filter(
            organization=organization,
            category=SupportTicket.Category.BILLING,
            invoice__isnull=False,
        )
        .exclude(status__in=[SupportTicket.Status.RESOLVED, SupportTicket.Status.CLOSED])
        .select_related("invoice", "assigned_agent", "requester", "customer")
    )
    for ticket in billing_tickets:
        previous_status = ticket.status
        from apps.support_desk.views import _evaluate_ticket_sla

        _evaluate_ticket_sla(ticket, now=now)
        ticket.refresh_from_db(fields=["status", "escalated_at", "updated_at", "sla_deadline"])
        summary["billing_tickets_synced"] += 1
        if previous_status != SupportTicket.Status.ESCALATED and ticket.status == SupportTicket.Status.ESCALATED:
            summary["billing_tickets_escalated"] += 1

    return summary
