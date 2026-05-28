from __future__ import annotations

import calendar
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Avg, Count, Max
from django.utils import timezone

from apps.facility_management.models import SpaceAllocation, UtilityBill, UtilityMeter
from apps.facility_management.service_request_workflows import (
    ensure_service_request_defaults,
    ensure_service_request_work_order,
    resolve_billing_tickets_for_invoice,
    run_service_request_helpdesk_automation,
)
from apps.finance.models import Invoice, InvoiceLineItem, InvoicePayment
from apps.finance.payment_automation import ensure_payment_journal_posted
from apps.properties.models import ServiceRequest, WorkOrder
from apps.support_desk.models import SupportTicket
from apps.support_desk.whatsapp_providers import get_whatsapp_provider_adapter

from .models import (
    LeaseAccessProvisioning,
    LeaseAgreement,
    LeaseRenewalRequest,
    LeaseTerminationRequest,
    LeaseUtilityTracking,
    OccupancyRecord,
    RecurringChargeRule,
    TenantBroadcast,
    TenantCommunicationLog,
    TenantComplaint,
    TenantDepositSettlement,
    TenantDocumentRecord,
    TenantInspection,
    TenantProfile,
    TenantVacancyRiskAlert,
)

ZERO_DECIMAL = Decimal("0.00")
TWO_PLACES = Decimal("0.01")
OVERDUE_PENALTY_GRACE_DAYS = 7
OVERDUE_BILLING_TICKET_DAYS = 14
OVERDUE_ESCALATION_DAYS = 30
OVERDUE_PENALTY_RATE = Decimal("0.05")
OVERDUE_PENALTY_MINIMUM = Decimal("1000.00")
SERVICE_REQUEST_RESOLUTION_LOOKBACK_DAYS = 30


def _user_display(user) -> str:
    if not user:
        return ""
    full_name = user.get_full_name().strip()
    return full_name or user.email or user.username


def _profile_contact_email(profile: TenantProfile) -> str:
    if profile.primary_user_id and profile.primary_user and profile.primary_user.email:
        return profile.primary_user.email.strip()
    if profile.customer_id and profile.customer and profile.customer.email:
        return profile.customer.email.strip()
    if profile.contact_account_id and profile.contact_account and profile.contact_account.email:
        return profile.contact_account.email.strip()
    return ""


def _profile_contact_phone(profile: TenantProfile) -> str:
    if profile.customer_id and profile.customer and profile.customer.phone:
        return profile.customer.phone.strip()
    if profile.contact_account_id and profile.contact_account:
        if profile.contact_account.phone:
            return profile.contact_account.phone.strip()
        if profile.contact_account.secondary_phone:
            return profile.contact_account.secondary_phone.strip()
    return ""


def _profile_context(profile: TenantProfile | None) -> dict:
    if profile is None:
        return {
            "property": None,
            "unit": None,
            "facility": None,
            "facility_space": None,
        }
    property_record = profile.property
    unit = profile.unit
    facility = profile.facility
    facility_space = profile.facility_space
    if facility_space:
        unit = facility_space.unit
        facility = facility_space.facility
        property_record = facility_space.facility.property
    elif unit:
        property_record = unit.property
        linked_space = getattr(unit, "facility_space", None)
        if linked_space and linked_space.organization_id == profile.organization_id:
            facility_space = linked_space
            facility = linked_space.facility
    elif facility:
        property_record = facility.property
    return {
        "property": property_record,
        "unit": unit,
        "facility": facility,
        "facility_space": facility_space,
    }


def _effective_lease_end_date(lease: LeaseAgreement):
    return lease.terminated_on or lease.end_date


def _frequency_months(frequency: str) -> int:
    mapping = {
        LeaseAgreement.PaymentFrequency.MONTHLY: 1,
        LeaseAgreement.PaymentFrequency.QUARTERLY: 3,
        LeaseAgreement.PaymentFrequency.BIANNUAL: 6,
        LeaseAgreement.PaymentFrequency.ANNUAL: 12,
        RecurringChargeRule.Frequency.MONTHLY: 1,
        RecurringChargeRule.Frequency.QUARTERLY: 3,
        RecurringChargeRule.Frequency.BIANNUAL: 6,
        RecurringChargeRule.Frequency.ANNUAL: 12,
        RecurringChargeRule.Frequency.ONCE: 0,
    }
    return mapping.get(frequency, 1)


def _add_months(value, months):
    month_index = (value.month - 1) + months
    year = value.year + (month_index // 12)
    month = (month_index % 12) + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def _quantize(value: Decimal) -> Decimal:
    return Decimal(value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _tenant_status_priority(profile: TenantProfile) -> int:
    order = {
        TenantProfile.Status.ACTIVE: 0,
        TenantProfile.Status.PENDING_MOVE_IN: 1,
        TenantProfile.Status.INACTIVE: 2,
        TenantProfile.Status.MOVED_OUT: 3,
    }
    return order.get(profile.status, 9)


def _best_tenant_profile_match(queryset):
    profiles = list(
        queryset.select_related("property", "unit", "facility", "facility_space")
        .order_by("id")
    )
    if not profiles:
        return None
    return min(
        profiles,
        key=lambda profile: (
            _tenant_status_priority(profile),
            0 if profile.move_out_date is None else 1,
            -(profile.move_in_date.toordinal() if profile.move_in_date else 0),
            -profile.id,
        ),
    )


def _resolve_service_request_tenant_profile(service_request: ServiceRequest):
    if service_request.tenant_profile_id:
        return service_request.tenant_profile

    linked_complaint = getattr(service_request, "tenant_complaints", None)
    if linked_complaint is not None:
        complaint = linked_complaint.select_related("tenant_profile").order_by("id").first()
        if complaint and complaint.tenant_profile_id:
            return complaint.tenant_profile

    profiles = TenantProfile.objects.filter(organization_id=service_request.organization_id)
    scoped_profiles = profiles
    if service_request.facility_space_id:
        scoped_profiles = scoped_profiles.filter(facility_space_id=service_request.facility_space_id)
    elif service_request.unit_id:
        scoped_profiles = scoped_profiles.filter(unit_id=service_request.unit_id)
    elif service_request.property_id:
        scoped_profiles = scoped_profiles.filter(property_id=service_request.property_id)

    if service_request.requester_id:
        requester_match = _best_tenant_profile_match(scoped_profiles.filter(primary_user_id=service_request.requester_id))
        if requester_match is not None:
            return requester_match

        fallback_requester_match = _best_tenant_profile_match(profiles.filter(primary_user_id=service_request.requester_id))
        if fallback_requester_match is not None:
            return fallback_requester_match

    return _best_tenant_profile_match(scoped_profiles)


def _ensure_service_request_tenant_profile(service_request: ServiceRequest):
    profile = _resolve_service_request_tenant_profile(service_request)
    if profile is None:
        return None, 0
    if service_request.tenant_profile_id == profile.id:
        return profile, 0

    ServiceRequest.objects.filter(pk=service_request.pk).update(
        tenant_profile_id=profile.id,
        updated_at=timezone.now(),
    )
    service_request.tenant_profile = profile
    return profile, 1


def refresh_tenant_satisfaction_score(profile: TenantProfile) -> int:
    aggregate = ServiceRequest.objects.filter(
        organization=profile.organization,
        tenant_profile=profile,
        feedback_rating__isnull=False,
    ).aggregate(
        average_rating=Avg("feedback_rating"),
        response_count=Count("id"),
        last_feedback_at=Max("feedback_submitted_at"),
    )

    average_rating = aggregate["average_rating"]
    response_count = aggregate["response_count"] or 0
    desired_score = _quantize(Decimal(str(average_rating))) if average_rating is not None else None
    desired_last_feedback_at = aggregate["last_feedback_at"]

    update_fields: list[str] = []
    if profile.satisfaction_score != desired_score:
        profile.satisfaction_score = desired_score
        update_fields.append("satisfaction_score")
    if profile.satisfaction_response_count != response_count:
        profile.satisfaction_response_count = response_count
        update_fields.append("satisfaction_response_count")
    if profile.last_satisfaction_feedback_at != desired_last_feedback_at:
        profile.last_satisfaction_feedback_at = desired_last_feedback_at
        update_fields.append("last_satisfaction_feedback_at")

    if update_fields:
        profile.save(update_fields=update_fields + ["updated_at"])
        return 1
    return 0


def _record_log(
    profile: TenantProfile,
    *,
    interaction_type,
    channel,
    direction,
    status,
    subject,
    message,
    metadata=None,
    author=None,
):
    return TenantCommunicationLog.objects.create(
        organization=profile.organization,
        tenant_profile=profile,
        author=author,
        interaction_type=interaction_type,
        channel=channel,
        direction=direction,
        status=status,
        subject=subject,
        message=message,
        metadata=metadata or {},
    )


def _recent_subject_exists(profile: TenantProfile, subject_prefix: str, *, days: int = 7) -> bool:
    since = timezone.now() - timedelta(days=days)
    return profile.communication_logs.filter(subject__istartswith=subject_prefix, happened_at__gte=since).exists()


def _org_admin_users(organization):
    from apps.accounts.models import UserProfile

    return [
        profile.user
        for profile in UserProfile.objects.filter(
            organization=organization,
            role="admin",
            user__is_active=True,
        ).select_related("user")
    ]


def _vacancy_risk_level(score: int) -> str:
    if score >= 80:
        return TenantVacancyRiskAlert.RiskLevel.CRITICAL
    if score >= 60:
        return TenantVacancyRiskAlert.RiskLevel.HIGH
    if score >= 40:
        return TenantVacancyRiskAlert.RiskLevel.MEDIUM
    return TenantVacancyRiskAlert.RiskLevel.LOW


def _lease_vacancy_risk_snapshot(lease: LeaseAgreement, today=None) -> dict:
    today = today or timezone.localdate()
    profile = lease.tenant_profile
    forecasted_vacancy_date = profile.move_out_date or lease.terminated_on or lease.end_date
    pending_or_approved = lease.renewal_requests.exclude(status=LeaseRenewalRequest.Status.REJECTED)
    has_pending_renewal = pending_or_approved.filter(status=LeaseRenewalRequest.Status.PENDING).exists()
    has_approved_renewal = pending_or_approved.filter(status=LeaseRenewalRequest.Status.APPROVED).exists()
    approaching_horizon = today + timedelta(days=max(60, lease.notice_period_days))

    if forecasted_vacancy_date is None:
        return {
            "active": False,
            "status": TenantVacancyRiskAlert.Status.RESOLVED,
            "notes": "No forecasted vacancy date is available.",
        }

    if lease.status in {
        LeaseAgreement.Status.RENEWED,
        LeaseAgreement.Status.ARCHIVED,
        LeaseAgreement.Status.EXPIRED,
        LeaseAgreement.Status.TERMINATED,
    } or has_approved_renewal:
        return {
            "active": False,
            "status": TenantVacancyRiskAlert.Status.RESOLVED,
            "forecasted_vacancy_date": forecasted_vacancy_date,
            "days_to_vacancy": (forecasted_vacancy_date - today).days,
            "notes": "The lease has already been renewed, expired, or completed.",
        }

    approaching = (
        today <= forecasted_vacancy_date <= approaching_horizon
        or lease.status in {
            LeaseAgreement.Status.EXPIRING_SOON,
            LeaseAgreement.Status.NOTICE_GIVEN,
            LeaseAgreement.Status.TERMINATION_PENDING,
        }
    )
    if not approaching:
        return {
            "active": False,
            "status": TenantVacancyRiskAlert.Status.RESOLVED,
            "forecasted_vacancy_date": forecasted_vacancy_date,
            "days_to_vacancy": (forecasted_vacancy_date - today).days,
            "notes": "The lease is outside the configured vacancy-risk horizon.",
        }

    days_to_vacancy = (forecasted_vacancy_date - today).days
    score = 25
    if days_to_vacancy <= 60:
        score += 15
    if days_to_vacancy <= 45:
        score += 10
    if days_to_vacancy <= 30:
        score += 15
    if days_to_vacancy <= 14:
        score += 15
    if lease.status == LeaseAgreement.Status.EXPIRING_SOON:
        score += 10
    if lease.status == LeaseAgreement.Status.NOTICE_GIVEN:
        score += 20
    if lease.status == LeaseAgreement.Status.TERMINATION_PENDING:
        score += 25
    if profile.move_out_date:
        score += 15
    if not lease.renewal_option:
        score += 10
    if has_pending_renewal:
        score -= 10
    else:
        score += 10
    score = max(5, min(100, score))

    reasons = []
    if lease.status == LeaseAgreement.Status.EXPIRING_SOON:
        reasons.append("Lease is approaching expiry.")
    if lease.status == LeaseAgreement.Status.NOTICE_GIVEN:
        reasons.append("Notice has been given.")
    if lease.status == LeaseAgreement.Status.TERMINATION_PENDING:
        reasons.append("Termination is pending approval.")
    if profile.move_out_date:
        reasons.append(f"Move-out is targeted for {profile.move_out_date.isoformat()}.")
    if has_pending_renewal:
        reasons.append("Renewal is in progress.")
    else:
        reasons.append("No active renewal approval is on file.")

    alert_status = TenantVacancyRiskAlert.Status.MITIGATED if has_pending_renewal else TenantVacancyRiskAlert.Status.OPEN
    return {
        "active": True,
        "status": alert_status,
        "risk_score": score,
        "risk_level": _vacancy_risk_level(score),
        "forecasted_vacancy_date": forecasted_vacancy_date,
        "days_to_vacancy": days_to_vacancy,
        "notes": " ".join(reasons),
    }


def _sync_vacancy_risk_alert(lease: LeaseAgreement, today=None) -> dict[str, int]:
    today = today or timezone.localdate()
    snapshot = _lease_vacancy_risk_snapshot(lease, today)
    alert = getattr(lease, "vacancy_risk_alert", None)
    summary = {
        "vacancy_risks_created": 0,
        "vacancy_risks_updated": 0,
        "vacancy_risks_resolved": 0,
        "vacancy_risks_open": 0,
    }

    if not snapshot["active"]:
        if alert and alert.status != TenantVacancyRiskAlert.Status.RESOLVED:
            alert.status = TenantVacancyRiskAlert.Status.RESOLVED
            alert.risk_level = TenantVacancyRiskAlert.RiskLevel.LOW
            alert.risk_score = 0
            alert.forecasted_vacancy_date = snapshot.get("forecasted_vacancy_date")
            alert.days_to_vacancy = snapshot.get("days_to_vacancy", 0)
            alert.notes = snapshot.get("notes", "")
            alert.save(
                update_fields=[
                    "status",
                    "risk_level",
                    "risk_score",
                    "forecasted_vacancy_date",
                    "days_to_vacancy",
                    "notes",
                    "resolved_at",
                    "updated_at",
                ]
            )
            summary["vacancy_risks_resolved"] = 1
        return summary

    defaults = {
        "organization": lease.organization,
        "tenant_profile": lease.tenant_profile,
        "property": lease.property,
        "unit": lease.unit,
        "facility": lease.facility,
        "facility_space": lease.facility_space,
        "status": snapshot["status"],
        "risk_level": snapshot["risk_level"],
        "risk_score": snapshot["risk_score"],
        "forecasted_vacancy_date": snapshot["forecasted_vacancy_date"],
        "days_to_vacancy": snapshot["days_to_vacancy"],
        "notes": snapshot["notes"],
    }

    if alert is None:
        TenantVacancyRiskAlert.objects.create(
            lease_agreement=lease,
            **defaults,
        )
        summary["vacancy_risks_created"] = 1
        summary["vacancy_risks_open"] = 1
        return summary

    update_fields = []
    for field_name, value in defaults.items():
        if getattr(alert, field_name) != value:
            setattr(alert, field_name, value)
            update_fields.append(field_name)
    if update_fields:
        alert.save(update_fields=update_fields + ["resolved_at", "updated_at"])
        summary["vacancy_risks_updated"] = 1
    if alert.status != TenantVacancyRiskAlert.Status.RESOLVED:
        summary["vacancy_risks_open"] = 1
    return summary


def _stop_lease_billing_if_terminated(lease: LeaseAgreement, today=None) -> dict[str, int]:
    today = today or timezone.localdate()
    effective_end = _effective_lease_end_date(lease)
    summary = {"billing_rules_stopped": 0}
    if effective_end is None or effective_end > today:
        return summary

    update_fields = []
    if lease.next_billing_date is not None:
        lease.next_billing_date = None
        update_fields.append("next_billing_date")
    if update_fields:
        lease.save(update_fields=update_fields + ["updated_at"])

    rules = RecurringChargeRule.objects.filter(
        organization=lease.organization,
        lease_agreement=lease,
    ).exclude(status=RecurringChargeRule.Status.ENDED, next_invoice_date__isnull=True, end_date=effective_end)
    for rule in rules:
        changed = False
        fields = []
        if rule.status != RecurringChargeRule.Status.ENDED:
            rule.status = RecurringChargeRule.Status.ENDED
            fields.append("status")
            changed = True
        if rule.end_date != effective_end:
            rule.end_date = effective_end
            fields.append("end_date")
            changed = True
        if rule.next_invoice_date is not None:
            rule.next_invoice_date = None
            fields.append("next_invoice_date")
            changed = True
        if changed:
            rule.save(update_fields=fields + ["updated_at"])
            summary["billing_rules_stopped"] += 1
    return summary


def _notify_move_out_inspection_required(lease: LeaseAgreement, inspection: TenantInspection) -> int:
    profile = lease.tenant_profile
    recipients = _org_admin_users(lease.organization)
    if not recipients:
        return 0

    subject_prefix = f"Move-out inspection required - {lease.lease_code}"
    if _recent_subject_exists(profile, subject_prefix, days=10):
        return 0

    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification

    facility_label = lease.facility.facility_code if lease.facility_id and lease.facility else ""
    property_name = lease.property.name if lease.property_id and lease.property else ""
    unit_label = lease.unit.unit_number if lease.unit_id and lease.unit else ""
    message = (
        f"Move-out inspection has been scheduled for {profile.resolved_display_name} on "
        f"{inspection.scheduled_date.isoformat()} at {property_name or 'the assigned property'}"
        + (f" / {facility_label}" if facility_label else "")
        + (f" / {unit_label}" if unit_label else "")
        + "."
    )
    dispatch_result = dispatch_workflow_notification(
        organization=lease.organization,
        event_key="tenant_move_out_inspection_required",
        recipients=recipients,
        context={
            "tenant_name": profile.resolved_display_name,
            "lease_code": lease.lease_code,
            "property_name": property_name,
            "facility_code": facility_label,
            "unit_label": unit_label,
            "scheduled_date": inspection.scheduled_date.isoformat(),
            "action_url": "/tenants/inspections",
        },
        link_url="/tenants/inspections",
        fallback_channels=("in_app", "email"),
        fallback_title=f"Move-Out Inspection Required - {lease.lease_code}",
        fallback_message=message,
        fallback_category=Notification.Category.PROPERTY_MAINT,
        fallback_severity=Notification.Severity.WARNING,
    )
    if dispatch_result["notifications_sent"] or dispatch_result["emails_sent"]:
        _record_log(
            profile,
            interaction_type=TenantCommunicationLog.InteractionType.SYSTEM,
            channel=TenantCommunicationLog.Channel.SYSTEM,
            direction=TenantCommunicationLog.Direction.INTERNAL,
            status=TenantCommunicationLog.Status.RECORDED,
            subject=subject_prefix,
            message=message,
            metadata={
                "inspection_id": inspection.id,
                "notifications_sent": dispatch_result["notifications_sent"],
                "emails_sent": dispatch_result["emails_sent"],
            },
        )
        return 1
    return 0


def _sync_deposit_settlement_for_lease(lease: LeaseAgreement, today=None) -> dict[str, int]:
    today = today or timezone.localdate()
    effective_end = _effective_lease_end_date(lease)
    summary = {
        "deposit_settlements_created": 0,
        "deposit_settlements_updated": 0,
        "deposit_settlements_ready": 0,
        "deposit_collection_invoices_created": 0,
    }
    if effective_end is None:
        return summary

    inspection = (
        lease.inspections.filter(inspection_type=TenantInspection.InspectionType.MOVE_OUT)
        .order_by("-completed_date", "-scheduled_date", "-id")
        .first()
    )
    completed_inspection = inspection if inspection and inspection.status == TenantInspection.Status.COMPLETED else None

    deposit_amount = _quantize(lease.security_deposit or ZERO_DECIMAL)
    assessed_deductions = _quantize(completed_inspection.security_deposit_deduction if completed_inspection else ZERO_DECIMAL)
    refundable_amount = max(deposit_amount - assessed_deductions, ZERO_DECIMAL)
    additional_amount_due = max(assessed_deductions - deposit_amount, ZERO_DECIMAL)

    if completed_inspection is None:
        target_status = TenantDepositSettlement.Status.PENDING_INSPECTION
        notes = "Awaiting completed move-out inspection before final settlement."
    elif additional_amount_due > ZERO_DECIMAL:
        target_status = TenantDepositSettlement.Status.PENDING_COLLECTION
        notes = "Damage assessment exceeded the security deposit. Collection is required for the balance."
    elif refundable_amount > ZERO_DECIMAL:
        target_status = TenantDepositSettlement.Status.PENDING_REFUND
        notes = "Security deposit is ready for refund after deductions."
    else:
        target_status = TenantDepositSettlement.Status.SETTLED
        notes = "Security deposit is fully consumed by approved deductions. No further settlement action is required."

    settlement, created = TenantDepositSettlement.objects.get_or_create(
        organization=lease.organization,
        lease_agreement=lease,
        defaults={
            "tenant_profile": lease.tenant_profile,
            "inspection": completed_inspection,
            "property": lease.property,
            "unit": lease.unit,
            "facility": lease.facility,
            "facility_space": lease.facility_space,
            "move_out_date": effective_end,
            "deposit_amount": deposit_amount,
            "assessed_deductions": assessed_deductions,
            "refundable_amount": refundable_amount,
            "additional_amount_due": additional_amount_due,
            "status": target_status,
            "notes": notes,
        },
    )
    if created:
        summary["deposit_settlements_created"] += 1

    update_fields = []
    for field_name, value in {
        "tenant_profile": lease.tenant_profile,
        "inspection": completed_inspection,
        "property": lease.property,
        "unit": lease.unit,
        "facility": lease.facility,
        "facility_space": lease.facility_space,
        "move_out_date": effective_end,
        "deposit_amount": deposit_amount,
        "assessed_deductions": assessed_deductions,
        "refundable_amount": refundable_amount,
        "additional_amount_due": additional_amount_due,
        "status": target_status,
        "notes": notes,
    }.items():
        if getattr(settlement, field_name) != value:
            setattr(settlement, field_name, value)
            update_fields.append(field_name)

    if (
        target_status == TenantDepositSettlement.Status.PENDING_COLLECTION
        and settlement.collection_invoice_id is None
        and lease.tenant_profile.customer_id
    ):
        marker = f"[deposit-settlement:{settlement.id}]"
        collection_invoice = Invoice.objects.create(
            organization=lease.organization,
            customer=lease.tenant_profile.customer,
            property=lease.property or lease.tenant_profile.property,
            status=Invoice.Status.DRAFT,
            issue_date=completed_inspection.completed_date or today,
            due_date=(completed_inspection.completed_date or today) + timedelta(days=7),
            notes=f"Security deposit settlement balance. {marker}",
        )
        InvoiceLineItem.objects.create(
            invoice=collection_invoice,
            description=f"Security deposit settlement balance - {lease.lease_code}",
            quantity=Decimal("1.00"),
            unit_price=additional_amount_due,
            sort_order=1,
        )
        collection_invoice.recalculate_totals()
        settlement.collection_invoice = collection_invoice
        update_fields.append("collection_invoice")
        summary["deposit_collection_invoices_created"] += 1

    if update_fields:
        settlement.save(update_fields=update_fields + ["ready_at", "settled_at", "updated_at"])
        if not created:
            summary["deposit_settlements_updated"] += 1

    if settlement.status != TenantDepositSettlement.Status.PENDING_INSPECTION:
        summary["deposit_settlements_ready"] += 1
    return summary


def _sync_unit_status(unit):
    if unit is None:
        return
    active_exists = TenantProfile.objects.filter(
        organization=unit.organization,
        unit=unit,
        status=TenantProfile.Status.ACTIVE,
    ).exists()
    pending_exists = TenantProfile.objects.filter(
        organization=unit.organization,
        unit=unit,
        status=TenantProfile.Status.PENDING_MOVE_IN,
    ).exists()

    target_status = unit.UnitStatus.AVAILABLE
    if active_exists:
        target_status = unit.UnitStatus.LEASED
    elif pending_exists:
        target_status = unit.UnitStatus.RESERVED

    if unit.status != target_status:
        unit.status = target_status
        unit.save(update_fields=["status", "updated_at"])


def lease_status_for(lease: LeaseAgreement, today=None) -> str:
    today = today or timezone.localdate()
    if lease.status == LeaseAgreement.Status.ARCHIVED:
        return LeaseAgreement.Status.ARCHIVED
    if lease.terminated_on and lease.terminated_on <= today:
        return LeaseAgreement.Status.TERMINATED
    if lease.end_date < today:
        return LeaseAgreement.Status.EXPIRED
    if lease.start_date > today:
        return LeaseAgreement.Status.DRAFT
    if lease.terminated_on and lease.terminated_on > today:
        return LeaseAgreement.Status.TERMINATION_PENDING
    if lease.end_date <= today + timedelta(days=max(lease.notice_period_days, 30)):
        return LeaseAgreement.Status.EXPIRING_SOON
    return LeaseAgreement.Status.ACTIVE


def occupancy_status_for(record: OccupancyRecord, today=None) -> str:
    today = today or timezone.localdate()
    if record.vacated_on:
        return OccupancyRecord.Status.VACATED
    if record.move_out_date and record.move_out_date <= today:
        return OccupancyRecord.Status.VACATED
    if record.notice_date and record.notice_date <= today:
        return OccupancyRecord.Status.NOTICE_GIVEN
    if record.move_in_date > today:
        return OccupancyRecord.Status.UPCOMING
    return OccupancyRecord.Status.ACTIVE


def _sync_space_allocation(lease: LeaseAgreement, occupancy: OccupancyRecord):
    if not lease.facility_space_id:
        return False
    profile = lease.tenant_profile
    allocation, created = SpaceAllocation.objects.get_or_create(
        organization=lease.organization,
        facility_space=lease.facility_space,
        allocation_type=SpaceAllocation.AllocationType.TENANT,
        tenant_customer=profile.customer,
        defaults={
            "tenant_contact_account": profile.contact_account,
            "occupant_count": occupancy.occupant_count or profile.occupant_count or 1,
            "start_date": occupancy.move_in_date,
            "end_date": occupancy.move_out_date,
            "status": SpaceAllocation.Status.ACTIVE if occupancy.status == OccupancyRecord.Status.ACTIVE else SpaceAllocation.Status.PENDING,
        },
    )
    changed = created
    update_fields = []
    target_status = SpaceAllocation.Status.ACTIVE
    if occupancy.status == OccupancyRecord.Status.UPCOMING:
        target_status = SpaceAllocation.Status.PENDING
    elif occupancy.status == OccupancyRecord.Status.NOTICE_GIVEN:
        target_status = SpaceAllocation.Status.ENDING_SOON
    elif occupancy.status == OccupancyRecord.Status.VACATED:
        target_status = SpaceAllocation.Status.ENDED
    field_values = {
        "tenant_contact_account": profile.contact_account,
        "occupant_count": occupancy.occupant_count or profile.occupant_count or 1,
        "start_date": occupancy.move_in_date,
        "end_date": occupancy.move_out_date,
        "status": target_status,
    }
    for field_name, value in field_values.items():
        if getattr(allocation, field_name) != value:
            setattr(allocation, field_name, value)
            update_fields.append(field_name)
            changed = True
    if target_status == SpaceAllocation.Status.ENDED and allocation.released_at is None:
        allocation.released_at = timezone.now()
        update_fields.append("released_at")
        changed = True
    if update_fields:
        allocation.save(update_fields=list(dict.fromkeys(update_fields + ["updated_at"])))
    return changed


def _apply_lease_escalation(lease: LeaseAgreement, today) -> bool:
    if lease.escalation_rule == LeaseAgreement.EscalationRule.NONE:
        return False
    reference_date = lease.last_escalation_date or lease.start_date
    next_escalation_date = _add_months(reference_date, max(lease.escalation_frequency_months, 1))
    if next_escalation_date > today:
        return False

    def escalated_amount(amount: Decimal) -> Decimal:
        if lease.escalation_rule == LeaseAgreement.EscalationRule.FIXED:
            return _quantize(amount + (lease.escalation_value or ZERO_DECIMAL))
        percentage = (lease.escalation_value or ZERO_DECIMAL) / Decimal("100")
        return _quantize(amount + (amount * percentage))

    lease.rent_amount = escalated_amount(lease.rent_amount or ZERO_DECIMAL)
    lease.service_charge_amount = escalated_amount(lease.service_charge_amount or ZERO_DECIMAL)
    lease.last_escalation_date = today
    lease.save(update_fields=["rent_amount", "service_charge_amount", "last_escalation_date", "updated_at"])

    for rule in RecurringChargeRule.objects.filter(
        organization=lease.organization,
        lease_agreement=lease,
        charge_type__in=[RecurringChargeRule.ChargeType.RENT, RecurringChargeRule.ChargeType.SERVICE_CHARGE],
        status=RecurringChargeRule.Status.ACTIVE,
    ):
        target_amount = lease.rent_amount if rule.charge_type == RecurringChargeRule.ChargeType.RENT else lease.service_charge_amount
        if rule.amount != target_amount:
            rule.amount = target_amount
            rule.save(update_fields=["amount", "updated_at"])
    return True


def _sync_lease_assignment(lease: LeaseAgreement, today=None) -> dict[str, int]:
    today = today or timezone.localdate()
    summary = {
        "leases_synced": 0,
        "occupancies_synced": 0,
        "allocations_synced": 0,
        "access_records_synced": 0,
        "utility_tracking_records_synced": 0,
        "utility_tracking_activated": 0,
    }
    changed = False
    update_fields = []
    context = _profile_context(lease.tenant_profile)
    for field_name, value in {
        "property": lease.property or context["property"],
        "unit": lease.unit or context["unit"],
        "facility": lease.facility or context["facility"],
        "facility_space": lease.facility_space or context["facility_space"],
    }.items():
        if value is not None and getattr(lease, field_name) != value:
            setattr(lease, field_name, value)
            update_fields.append(field_name)
            changed = True

    target_status = lease_status_for(lease, today)
    if lease.status != target_status:
        lease.status = target_status
        update_fields.append("status")
        changed = True
    if lease.auto_generate_billing and lease.next_billing_date is None:
        lease.next_billing_date = lease.start_date
        update_fields.append("next_billing_date")
        changed = True
    if changed:
        lease.save(update_fields=list(dict.fromkeys(update_fields + ["updated_at"])))
        summary["leases_synced"] += 1

    profile = lease.tenant_profile
    profile_updates = []
    desired_profile_status = TenantProfile.Status.PENDING_MOVE_IN
    if today >= lease.start_date:
        desired_profile_status = TenantProfile.Status.ACTIVE
    if target_status in {LeaseAgreement.Status.EXPIRED, LeaseAgreement.Status.TERMINATED}:
        desired_profile_status = TenantProfile.Status.MOVED_OUT
    for field_name, value in {
        "property": lease.property,
        "unit": lease.unit,
        "facility": lease.facility,
        "facility_space": lease.facility_space,
        "lease_start_date": lease.start_date,
        "lease_end_date": lease.end_date,
        "move_in_date": profile.move_in_date or lease.start_date,
        "status": desired_profile_status,
    }.items():
        if value is not None and getattr(profile, field_name) != value:
            setattr(profile, field_name, value)
            profile_updates.append(field_name)
    if target_status in {LeaseAgreement.Status.EXPIRED, LeaseAgreement.Status.TERMINATED}:
        move_out_target = profile.move_out_date or lease.terminated_on or lease.end_date
        if profile.move_out_date != move_out_target:
            profile.move_out_date = move_out_target
            profile_updates.append("move_out_date")
    if profile_updates:
        profile.save(update_fields=list(dict.fromkeys(profile_updates + ["updated_at"])))
        summary["occupancies_synced"] += 1
    _sync_unit_status(profile.unit)

    occupancy, created = OccupancyRecord.objects.get_or_create(
        organization=lease.organization,
        tenant_profile=profile,
        lease_agreement=lease,
        defaults={
            "property": lease.property,
            "unit": lease.unit,
            "facility": lease.facility,
            "facility_space": lease.facility_space,
            "status": OccupancyRecord.Status.UPCOMING,
            "move_in_date": profile.move_in_date or lease.start_date,
            "move_out_date": profile.move_out_date,
            "occupant_count": profile.occupant_count or 1,
        },
    )
    occ_updates = []
    if created:
        summary["occupancies_synced"] += 1
    for field_name, value in {
        "property": lease.property,
        "unit": lease.unit,
        "facility": lease.facility,
        "facility_space": lease.facility_space,
        "move_in_date": profile.move_in_date or lease.start_date,
        "move_out_date": profile.move_out_date,
        "occupant_count": profile.occupant_count or 1,
    }.items():
        if getattr(occupancy, field_name) != value:
            setattr(occupancy, field_name, value)
            occ_updates.append(field_name)
    if target_status in {LeaseAgreement.Status.NOTICE_GIVEN, LeaseAgreement.Status.EXPIRING_SOON, LeaseAgreement.Status.TERMINATION_PENDING}:
        notice_date = profile.move_out_date or lease.terminated_on or lease.end_date
        if occupancy.notice_date != notice_date:
            occupancy.notice_date = notice_date
            occ_updates.append("notice_date")
    if target_status in {LeaseAgreement.Status.EXPIRED, LeaseAgreement.Status.TERMINATED}:
        vacated_on = profile.move_out_date or lease.terminated_on or lease.end_date
        if occupancy.vacated_on != vacated_on:
            occupancy.vacated_on = vacated_on
            occ_updates.append("vacated_on")
    occ_status = occupancy_status_for(occupancy, today)
    if occupancy.status != occ_status:
        occupancy.status = occ_status
        occ_updates.append("status")
    if occ_updates:
        occupancy.save(update_fields=list(dict.fromkeys(occ_updates + ["updated_at"])))
        summary["occupancies_synced"] += 1
    if _sync_space_allocation(lease, occupancy):
        summary["allocations_synced"] += 1
    access_summary = ensure_lease_access_activation(lease, today=today)
    summary["access_records_synced"] += access_summary.get("access_records_created", 0)
    utility_summary = ensure_lease_utility_tracking(lease, today=today)
    for key, value in utility_summary.items():
        summary[key] += value
    if target_status in {LeaseAgreement.Status.EXPIRED, LeaseAgreement.Status.TERMINATED}:
        billing_summary = _stop_lease_billing_if_terminated(lease, today)
        for key, value in billing_summary.items():
            summary[key] = summary.get(key, 0) + value
    return summary


def _upsert_lease_charge_rule(lease: LeaseAgreement, *, charge_type: str, amount: Decimal, title: str) -> int:
    amount = _quantize(amount or ZERO_DECIMAL)
    existing = (
        RecurringChargeRule.objects.filter(
            organization=lease.organization,
            lease_agreement=lease,
            charge_type=charge_type,
        )
        .order_by("id")
        .first()
    )
    if amount <= ZERO_DECIMAL:
        if existing and existing.status != RecurringChargeRule.Status.ENDED:
            existing.status = RecurringChargeRule.Status.ENDED
            existing.end_date = lease.end_date
            existing.save(update_fields=["status", "end_date", "updated_at"])
            return 1
        return 0

    next_invoice_date = lease.next_billing_date or lease.start_date
    field_values = {
        "tenant_profile": lease.tenant_profile,
        "property": lease.property,
        "unit": lease.unit,
        "facility": lease.facility,
        "facility_space": lease.facility_space,
        "title": title,
        "status": RecurringChargeRule.Status.ACTIVE,
        "amount": amount,
        "currency": lease.currency,
        "frequency": lease.payment_frequency,
        "start_date": lease.start_date,
        "end_date": lease.end_date,
        "next_invoice_date": next_invoice_date,
        "applies_mid_period_proration": lease.payment_frequency == LeaseAgreement.PaymentFrequency.MONTHLY,
        "auto_invoice": lease.auto_generate_billing,
        "notes": f"Auto-generated from lease {lease.lease_code}.",
    }
    if existing is None:
        RecurringChargeRule.objects.create(
            organization=lease.organization,
            lease_agreement=lease,
            charge_type=charge_type,
            **field_values,
        )
        return 1

    update_fields = []
    for field_name, value in field_values.items():
        if getattr(existing, field_name) != value:
            setattr(existing, field_name, value)
            update_fields.append(field_name)
    if update_fields:
        existing.save(update_fields=list(dict.fromkeys(update_fields + ["updated_at"])))
        return 1
    return 0


def ensure_lease_billing_setup(lease: LeaseAgreement) -> dict[str, int]:
    return {
        "billing_schedule_rules_created": (
            _upsert_lease_charge_rule(
                lease,
                charge_type=RecurringChargeRule.ChargeType.RENT,
                amount=lease.rent_amount,
                title=f"{lease.lease_code} rent",
            )
            + _upsert_lease_charge_rule(
                lease,
                charge_type=RecurringChargeRule.ChargeType.SERVICE_CHARGE,
                amount=lease.service_charge_amount,
                title=f"{lease.lease_code} service charge",
            )
        )
    }


def sync_lease_occupancy_automation(organization) -> dict[str, int]:
    today = timezone.localdate()
    summary = {
        "leases_synced": 0,
        "occupancies_synced": 0,
        "renewals_created": 0,
        "terminations_created": 0,
        "allocations_synced": 0,
        "access_records_synced": 0,
        "utility_tracking_records_synced": 0,
        "utility_tracking_activated": 0,
        "rent_escalations_applied": 0,
        "billing_rules_stopped": 0,
        "vacancy_risks_created": 0,
        "vacancy_risks_updated": 0,
        "vacancy_risks_resolved": 0,
        "vacancy_risks_open": 0,
        "access_records_synced": 0,
        "utility_tracking_records_synced": 0,
        "utility_tracking_activated": 0,
    }

    leases = LeaseAgreement.objects.filter(organization=organization).select_related(
        "tenant_profile",
        "tenant_profile__customer",
        "tenant_profile__contact_account",
        "tenant_profile__primary_user",
        "property",
        "unit",
        "facility",
        "facility_space",
        "facility_space__facility",
        "facility_space__unit",
    )

    for lease in leases:
        changed = False
        update_fields = []
        context = _profile_context(lease.tenant_profile)
        for field_name, value in {
            "property": lease.property or context["property"],
            "unit": lease.unit or context["unit"],
            "facility": lease.facility or context["facility"],
            "facility_space": lease.facility_space or context["facility_space"],
        }.items():
            if value is not None and getattr(lease, field_name) != value:
                setattr(lease, field_name, value)
                update_fields.append(field_name)
                changed = True

        target_status = lease_status_for(lease, today)
        open_termination = lease.termination_requests.exclude(status__in=[
            LeaseTerminationRequest.Status.REJECTED,
            LeaseTerminationRequest.Status.COMPLETED,
        ]).exists()
        if open_termination and target_status not in {LeaseAgreement.Status.TERMINATED, LeaseAgreement.Status.EXPIRED}:
            target_status = LeaseAgreement.Status.TERMINATION_PENDING
        if lease.status != target_status:
            lease.status = target_status
            update_fields.append("status")
            changed = True
        if lease.auto_generate_billing and lease.next_billing_date is None:
            lease.next_billing_date = lease.start_date
            update_fields.append("next_billing_date")
            changed = True
        if changed:
            lease.save(update_fields=list(dict.fromkeys(update_fields + ["updated_at"])))
            summary["leases_synced"] += 1

        if _apply_lease_escalation(lease, today):
            summary["rent_escalations_applied"] += 1

        profile = lease.tenant_profile
        profile_updates = []
        desired_profile_status = TenantProfile.Status.PENDING_MOVE_IN
        if today >= lease.start_date:
            desired_profile_status = TenantProfile.Status.ACTIVE
        if target_status in {LeaseAgreement.Status.EXPIRED, LeaseAgreement.Status.TERMINATED}:
            desired_profile_status = TenantProfile.Status.MOVED_OUT
        for field_name, value in {
            "property": lease.property,
            "unit": lease.unit,
            "facility": lease.facility,
            "facility_space": lease.facility_space,
            "lease_start_date": lease.start_date,
            "lease_end_date": lease.end_date,
            "move_in_date": profile.move_in_date or lease.start_date,
            "status": desired_profile_status,
        }.items():
            if value is not None and getattr(profile, field_name) != value:
                setattr(profile, field_name, value)
                profile_updates.append(field_name)
        if target_status in {LeaseAgreement.Status.EXPIRED, LeaseAgreement.Status.TERMINATED}:
            move_out_target = profile.move_out_date or lease.terminated_on or lease.end_date
            if profile.move_out_date != move_out_target:
                profile.move_out_date = move_out_target
                profile_updates.append("move_out_date")
        if profile_updates:
            profile.save(update_fields=list(dict.fromkeys(profile_updates + ["updated_at"])))
            summary["occupancies_synced"] += 1
        _sync_unit_status(profile.unit)

        occupancy, created = OccupancyRecord.objects.get_or_create(
            organization=organization,
            tenant_profile=profile,
            lease_agreement=lease,
            defaults={
                "property": lease.property,
                "unit": lease.unit,
                "facility": lease.facility,
                "facility_space": lease.facility_space,
                "status": OccupancyRecord.Status.UPCOMING,
                "move_in_date": profile.move_in_date or lease.start_date,
                "move_out_date": profile.move_out_date,
                "occupant_count": profile.occupant_count or 1,
            },
        )
        occ_updates = []
        if created:
            summary["occupancies_synced"] += 1
        for field_name, value in {
            "property": lease.property,
            "unit": lease.unit,
            "facility": lease.facility,
            "facility_space": lease.facility_space,
            "move_in_date": profile.move_in_date or lease.start_date,
            "move_out_date": profile.move_out_date,
            "occupant_count": profile.occupant_count or 1,
        }.items():
            if getattr(occupancy, field_name) != value:
                setattr(occupancy, field_name, value)
                occ_updates.append(field_name)
        if target_status in {LeaseAgreement.Status.NOTICE_GIVEN, LeaseAgreement.Status.EXPIRING_SOON, LeaseAgreement.Status.TERMINATION_PENDING}:
            notice_date = profile.move_out_date or lease.terminated_on or lease.end_date
            if occupancy.notice_date != notice_date:
                occupancy.notice_date = notice_date
                occ_updates.append("notice_date")
        if target_status in {LeaseAgreement.Status.EXPIRED, LeaseAgreement.Status.TERMINATED}:
            vacated_on = profile.move_out_date or lease.terminated_on or lease.end_date
            if occupancy.vacated_on != vacated_on:
                occupancy.vacated_on = vacated_on
                occ_updates.append("vacated_on")
        occ_status = occupancy_status_for(occupancy, today)
        if occupancy.status != occ_status:
            occupancy.status = occ_status
            occ_updates.append("status")
        if occ_updates:
            occupancy.save(update_fields=list(dict.fromkeys(occ_updates + ["updated_at"])))
            summary["occupancies_synced"] += 1
        if _sync_space_allocation(lease, occupancy):
            summary["allocations_synced"] += 1
        access_summary = ensure_lease_access_activation(lease, today=today)
        summary["access_records_synced"] += access_summary.get("access_records_created", 0)
        utility_summary = ensure_lease_utility_tracking(lease, today=today)
        for key, value in utility_summary.items():
            summary[key] += value
        if target_status in {LeaseAgreement.Status.EXPIRED, LeaseAgreement.Status.TERMINATED}:
            billing_summary = _stop_lease_billing_if_terminated(lease, today)
            for key, value in billing_summary.items():
                summary[key] += value

        if (
            lease.renewal_option
            and lease.end_date >= today
            and lease.end_date <= today + timedelta(days=max(45, lease.notice_period_days))
            and not lease.renewal_requests.exclude(status=LeaseRenewalRequest.Status.REJECTED).exists()
        ):
            LeaseRenewalRequest.objects.create(
                organization=organization,
                tenant_profile=profile,
                lease_agreement=lease,
                proposed_start_date=lease.end_date + timedelta(days=1),
                proposed_end_date=_add_months(lease.end_date + timedelta(days=1), 12),
                proposed_rent_amount=lease.rent_amount,
                proposed_service_charge_amount=lease.service_charge_amount,
                generated_automatically=True,
                notes="Auto-generated because the lease is approaching expiry.",
            )
            summary["renewals_created"] += 1

        if (
            (profile.move_out_date or target_status in {LeaseAgreement.Status.EXPIRED, LeaseAgreement.Status.TERMINATION_PENDING})
            and not lease.termination_requests.exclude(status=LeaseTerminationRequest.Status.REJECTED).exists()
        ):
            LeaseTerminationRequest.objects.create(
                organization=organization,
                tenant_profile=profile,
                lease_agreement=lease,
                status=LeaseTerminationRequest.Status.PENDING_APPROVAL,
                requested_move_out_date=profile.move_out_date or lease.end_date,
                notice_period_days=lease.notice_period_days,
                generated_automatically=True,
                reason="Auto-generated from lease notice/expiry tracking.",
                notes="Created by tenant workflow automation.",
            )
            summary["terminations_created"] += 1

        risk_summary = _sync_vacancy_risk_alert(lease, today)
        for key, value in risk_summary.items():
            summary[key] += value

    return summary


def _charge_invoice_amount(rule: RecurringChargeRule, issue_date) -> Decimal:
    amount = rule.amount or ZERO_DECIMAL
    if (
        rule.applies_mid_period_proration
        and rule.frequency == RecurringChargeRule.Frequency.MONTHLY
        and rule.last_invoiced_date is None
        and rule.start_date.year == issue_date.year
        and rule.start_date.month == issue_date.month
        and rule.start_date.day > 1
    ):
        total_days = Decimal(calendar.monthrange(issue_date.year, issue_date.month)[1])
        remaining_days = Decimal(total_days - Decimal(rule.start_date.day) + Decimal("1"))
        amount = _quantize((amount * remaining_days) / total_days)
    if rule.charge_type in {RecurringChargeRule.ChargeType.DISCOUNT, RecurringChargeRule.ChargeType.CONCESSION}:
        amount = amount * Decimal("-1")
    return _quantize(amount)


def _invoice_exists_for_rule(rule: RecurringChargeRule, issue_date) -> bool:
    marker = f"[charge-rule:{rule.id}]"
    return Invoice.objects.filter(
        organization=rule.organization,
        customer=rule.tenant_profile.customer,
        issue_date=issue_date,
        notes__icontains=marker,
    ).exists()


def _advance_charge_rule_after_invoice(rule: RecurringChargeRule, issue_date) -> None:
    months = _frequency_months(rule.frequency)
    if months == 0:
        rule.status = RecurringChargeRule.Status.ENDED
        rule.next_invoice_date = None
    else:
        rule.next_invoice_date = _add_months(issue_date, months)
    rule.last_invoiced_date = issue_date
    rule.save(update_fields=["status", "last_invoiced_date", "next_invoice_date", "updated_at"])


def _create_invoice_for_charge_rule(rule: RecurringChargeRule) -> tuple[bool, str]:
    profile = rule.tenant_profile
    if not profile.customer_id or rule.next_invoice_date is None:
        return False, "missing_customer"
    if _invoice_exists_for_rule(rule, rule.next_invoice_date):
        _advance_charge_rule_after_invoice(rule, rule.next_invoice_date)
        return False, "duplicate"

    issue_date = rule.next_invoice_date
    due_date = issue_date + timedelta(days=7)
    amount = _charge_invoice_amount(rule, issue_date)
    charge_type_label = rule.get_charge_type_display()
    description = f"{charge_type_label} - {rule.title}"
    note_marker = f"[charge-rule:{rule.id}]"
    property_name = ""
    if rule.property_id and rule.property:
        property_name = rule.property.name
    elif profile.property_id and profile.property:
        property_name = profile.property.name

    with transaction.atomic():
        invoice = Invoice.objects.create(
            organization=rule.organization,
            customer=profile.customer,
            property=rule.property or profile.property,
            status=Invoice.Status.SENT,
            issue_date=issue_date,
            due_date=due_date,
            notes=f"Auto-generated recurring charge. {note_marker}",
        )
        InvoiceLineItem.objects.create(
            invoice=invoice,
            description=description,
            quantity=Decimal("1.00"),
            unit_price=amount,
            sort_order=1,
        )
        invoice.recalculate_totals()
        _advance_charge_rule_after_invoice(rule, issue_date)
        _record_log(
            profile,
            interaction_type=TenantCommunicationLog.InteractionType.INVOICE_GENERATED,
            channel=TenantCommunicationLog.Channel.SYSTEM,
            direction=TenantCommunicationLog.Direction.INTERNAL,
            status=TenantCommunicationLog.Status.RECORDED,
            subject=f"Invoice generated - {invoice.invoice_number}",
            message=f"Automated recurring billing generated invoice {invoice.invoice_number} for {description}.",
            metadata={"invoice_id": invoice.id, "charge_rule_id": rule.id},
        )
        notification_message = (
            f"Dear {profile.resolved_display_name},\n\n"
            f"A new {charge_type_label.lower()} invoice ({invoice.invoice_number}) has been issued"
            f"{f' for {property_name}' if property_name else ''}.\n"
            f"Amount due: NGN {invoice.total_amount:.2f}\n"
            f"Due date: {due_date.isoformat()}\n\n"
            "Please review and settle it on or before the due date.\n"
        )
        transaction.on_commit(
            lambda profile=profile, invoice_number=invoice.invoice_number, message=notification_message, charge_type_label=charge_type_label: _dispatch_message(
                profile,
                subject=f"{charge_type_label} invoice {invoice_number}",
                message=message,
                interaction_type=TenantCommunicationLog.InteractionType.INVOICE_GENERATED,
            )
        )
    return True, "created"


def generate_due_lease_invoices(lease: LeaseAgreement, *, today=None) -> dict[str, int]:
    today = today or timezone.localdate()
    summary = {"invoices_created": 0, "rules_skipped": 0}
    rules = RecurringChargeRule.objects.filter(
        organization=lease.organization,
        lease_agreement=lease,
        status=RecurringChargeRule.Status.ACTIVE,
        auto_invoice=True,
        next_invoice_date__isnull=False,
        next_invoice_date__lte=today,
    ).select_related(
        "tenant_profile",
        "tenant_profile__customer",
        "tenant_profile__contact_account",
        "tenant_profile__primary_user",
        "property",
        "unit",
        "facility",
        "facility_space",
        "lease_agreement",
    )
    for rule in rules:
        created, reason = _create_invoice_for_charge_rule(rule)
        if created:
            summary["invoices_created"] += 1
        elif reason in {"duplicate", "missing_customer"}:
            summary["rules_skipped"] += 1
    return summary


def sync_billing_charges_automation(organization) -> dict[str, int]:
    today = timezone.localdate()
    summary = {
        "invoices_created": 0,
        "rules_skipped": 0,
        "utility_bills_visible": 0,
    }

    rules = RecurringChargeRule.objects.filter(
        organization=organization,
        status=RecurringChargeRule.Status.ACTIVE,
        auto_invoice=True,
        next_invoice_date__isnull=False,
        next_invoice_date__lte=today,
    ).select_related(
        "tenant_profile",
        "tenant_profile__customer",
        "tenant_profile__contact_account",
        "tenant_profile__primary_user",
        "property",
        "unit",
        "facility",
        "facility_space",
        "lease_agreement",
    )

    for rule in rules:
        created, reason = _create_invoice_for_charge_rule(rule)
        if created:
            summary["invoices_created"] += 1
        elif reason in {"duplicate", "missing_customer"}:
            summary["rules_skipped"] += 1

    property_ids = {
        property_id
        for property_id in TenantProfile.objects.filter(organization=organization).values_list("property_id", flat=True)
        if property_id
    }
    summary["utility_bills_visible"] = UtilityBill.objects.filter(
        organization=organization,
        property_id__in=property_ids,
    ).exclude(status=UtilityBill.Status.CANCELLED).count()
    return summary


def ensure_lease_access_activation(lease: LeaseAgreement, *, today=None) -> dict[str, int]:
    today = today or timezone.localdate()
    profile = lease.tenant_profile
    move_in_target = profile.move_in_date or lease.start_date
    target_status = (
        LeaseAccessProvisioning.Status.ACTIVE
        if move_in_target <= today and lease.status not in {
            LeaseAgreement.Status.EXPIRED,
            LeaseAgreement.Status.TERMINATED,
            LeaseAgreement.Status.ARCHIVED,
        }
        else LeaseAccessProvisioning.Status.QUEUED
    )
    field_values = {
        "tenant_profile": profile,
        "property": lease.property,
        "unit": lease.unit,
        "facility": lease.facility,
        "facility_space": lease.facility_space,
        "status": target_status,
        "facility_access_active": target_status == LeaseAccessProvisioning.Status.ACTIVE,
        "security_access_active": target_status == LeaseAccessProvisioning.Status.ACTIVE and bool(lease.facility_id),
        "portal_access_active": target_status == LeaseAccessProvisioning.Status.ACTIVE and bool(profile.primary_user_id),
        "notes": (
            "Auto-activated from tenant move-in lifecycle."
            if target_status == LeaseAccessProvisioning.Status.ACTIVE
            else "Queued for activation when the lease becomes active."
        ),
    }
    record, created = LeaseAccessProvisioning.objects.get_or_create(
        organization=lease.organization,
        lease_agreement=lease,
        defaults=field_values,
    )
    changed = created
    update_fields = []
    if not created:
        for field_name, value in field_values.items():
            if getattr(record, field_name) != value:
                setattr(record, field_name, value)
                update_fields.append(field_name)
                changed = True
        if update_fields:
            record.save(update_fields=list(dict.fromkeys(update_fields + ["updated_at"])))

    subject_prefix = (
        f"Access activated - {lease.lease_code}"
        if target_status == LeaseAccessProvisioning.Status.ACTIVE
        else f"Access queued - {lease.lease_code}"
    )
    if changed and not _recent_subject_exists(profile, subject_prefix, days=14):
        _record_log(
            profile,
            interaction_type=TenantCommunicationLog.InteractionType.SYSTEM,
            channel=TenantCommunicationLog.Channel.SYSTEM,
            direction=TenantCommunicationLog.Direction.INTERNAL,
            status=TenantCommunicationLog.Status.RECORDED,
            subject=subject_prefix,
            message=(
                f"Lease access provisioning for {lease.lease_code} is "
                f"{'active' if target_status == LeaseAccessProvisioning.Status.ACTIVE else 'queued'}."
            ),
            metadata={
                "lease_id": lease.id,
                "access_provisioning_id": record.id,
                "status": record.status,
                "facility_access_active": record.facility_access_active,
                "security_access_active": record.security_access_active,
                "portal_access_active": record.portal_access_active,
            },
        )
    return {
        "access_records_created": 1 if changed else 0,
        "access_records_synced": 1 if changed else 0,
    }


def ensure_lease_utility_tracking(lease: LeaseAgreement, *, today=None) -> dict[str, int]:
    today = today or timezone.localdate()
    profile = lease.tenant_profile
    move_in_target = profile.move_in_date or lease.start_date
    property_record = lease.property or profile.property

    if lease.status in {
        LeaseAgreement.Status.EXPIRED,
        LeaseAgreement.Status.TERMINATED,
        LeaseAgreement.Status.ARCHIVED,
    }:
        target_status = LeaseUtilityTracking.Status.INACTIVE
    elif move_in_target <= today:
        target_status = LeaseUtilityTracking.Status.ACTIVE
    else:
        target_status = LeaseUtilityTracking.Status.QUEUED

    tracked_meters = UtilityMeter.objects.none()
    visible_bill_count = 0
    tracked_types: list[str] = []
    if property_record is not None:
        tracked_meters = UtilityMeter.objects.filter(
            organization=lease.organization,
            property=property_record,
            is_active=True,
        ).order_by("utility_type", "id")
        tracked_types = list(tracked_meters.values_list("utility_type", flat=True).distinct())
        visible_bill_count = UtilityBill.objects.filter(
            organization=lease.organization,
            property=property_record,
        ).exclude(status=UtilityBill.Status.CANCELLED).count()

    field_values = {
        "tenant_profile": profile,
        "property": property_record,
        "unit": lease.unit or profile.unit,
        "facility": lease.facility or profile.facility,
        "facility_space": lease.facility_space or profile.facility_space,
        "status": target_status,
        "utility_tracking_active": target_status == LeaseUtilityTracking.Status.ACTIVE,
        "tracked_utility_types": tracked_types,
        "tracked_meter_count": tracked_meters.count(),
        "visible_utility_bill_count": visible_bill_count,
        "notes": (
            "Utility tracking activated from tenant move-in lifecycle."
            if target_status == LeaseUtilityTracking.Status.ACTIVE
            else (
                "Queued for activation when the tenant moves in."
                if target_status == LeaseUtilityTracking.Status.QUEUED
                else "Utility tracking has been deactivated because the lease is no longer active."
            )
        ),
    }
    record, created = LeaseUtilityTracking.objects.get_or_create(
        organization=lease.organization,
        lease_agreement=lease,
        defaults=field_values,
    )
    changed = created
    update_fields: list[str] = []
    if not created:
        for field_name, value in field_values.items():
            if getattr(record, field_name) != value:
                setattr(record, field_name, value)
                update_fields.append(field_name)
                changed = True
        if update_fields:
            record.save(update_fields=list(dict.fromkeys(update_fields + ["updated_at"])))

    subject_prefix = (
        f"Utility tracking activated - {lease.lease_code}"
        if target_status == LeaseUtilityTracking.Status.ACTIVE
        else (
            f"Utility tracking queued - {lease.lease_code}"
            if target_status == LeaseUtilityTracking.Status.QUEUED
            else f"Utility tracking inactive - {lease.lease_code}"
        )
    )
    if changed and not _recent_subject_exists(profile, subject_prefix, days=14):
        _record_log(
            profile,
            interaction_type=TenantCommunicationLog.InteractionType.SYSTEM,
            channel=TenantCommunicationLog.Channel.SYSTEM,
            direction=TenantCommunicationLog.Direction.INTERNAL,
            status=TenantCommunicationLog.Status.RECORDED,
            subject=subject_prefix,
            message=(
                f"Utility tracking for {lease.lease_code} is "
                f"{target_status.replace('_', ' ')} with {field_values['tracked_meter_count']} active meter(s)."
            ),
            metadata={
                "lease_id": lease.id,
                "utility_tracking_id": record.id,
                "status": record.status,
                "tracked_utility_types": tracked_types,
                "tracked_meter_count": field_values["tracked_meter_count"],
                "visible_utility_bill_count": visible_bill_count,
            },
        )

    return {
        "utility_tracking_records_synced": 1 if changed else 0,
        "utility_tracking_activated": 1 if changed and target_status == LeaseUtilityTracking.Status.ACTIVE else 0,
    }


def run_lease_created_automation(lease: LeaseAgreement) -> dict[str, int]:
    today = timezone.localdate()
    summary = {
        "leases_synced": 0,
        "occupancies_synced": 0,
        "allocations_synced": 0,
        "billing_schedule_rules_created": 0,
        "invoices_created": 0,
        "rules_skipped": 0,
        "access_records_created": 0,
        "utility_tracking_records_synced": 0,
        "utility_tracking_activated": 0,
    }
    for section in (
        _sync_lease_assignment(lease, today=today),
        ensure_lease_billing_setup(lease),
        generate_due_lease_invoices(lease, today=today),
    ):
        for key, value in section.items():
            summary[key] = summary.get(key, 0) + value
    return summary


def _sync_invoice_status(invoice: Invoice, today) -> bool:
    if invoice.status == Invoice.Status.CANCELLED:
        return False
    paid_amount = sum((payment.amount for payment in invoice.payments.all()), ZERO_DECIMAL)
    target_status = invoice.status
    if invoice.total_amount > ZERO_DECIMAL and paid_amount >= invoice.total_amount:
        target_status = Invoice.Status.PAID
    elif invoice.due_date < today:
        target_status = Invoice.Status.OVERDUE
    elif invoice.status == Invoice.Status.DRAFT and invoice.issue_date <= today:
        target_status = Invoice.Status.SENT
    elif invoice.status not in {Invoice.Status.SENT, Invoice.Status.DRAFT, Invoice.Status.OVERDUE, Invoice.Status.PAID}:
        target_status = Invoice.Status.SENT
    if target_status != invoice.status:
        invoice.status = target_status
        invoice.save(update_fields=["status", "updated_at"])
        return True
    return False


def sync_payments_collections_automation(organization) -> dict[str, int]:
    today = timezone.localdate()
    summary = {
        "payments_reconciled": 0,
        "overdue_invoices_flagged": 0,
        "late_payment_penalties_applied": 0,
        "payment_journals_posted": 0,
        "receipts_created": 0,
        "billing_tickets_synced": 0,
        "billing_tickets_escalated": 0,
        "billing_tickets_resolved": 0,
    }
    customer_ids = [
        customer_id
        for customer_id in TenantProfile.objects.filter(organization=organization).values_list("customer_id", flat=True)
        if customer_id
    ]
    invoices = Invoice.objects.filter(
        organization=organization,
        customer_id__in=customer_ids,
    ).exclude(status=Invoice.Status.CANCELLED).select_related("customer", "property").prefetch_related("payments")

    profile_by_customer = {
        profile.customer_id: profile
        for profile in TenantProfile.objects.filter(organization=organization, customer_id__in=customer_ids)
        .select_related("customer", "contact_account", "primary_user")
    }

    for invoice in invoices:
        previous_status = invoice.status
        if _sync_invoice_status(invoice, today):
            summary["payments_reconciled"] += 1
            if previous_status != Invoice.Status.OVERDUE and invoice.status == Invoice.Status.OVERDUE:
                summary["overdue_invoices_flagged"] += 1
        profile = profile_by_customer.get(invoice.customer_id)
        if invoice.status == Invoice.Status.OVERDUE:
            summary["late_payment_penalties_applied"] += _apply_overdue_penalty(invoice, profile, today=today)
            ticket_summary = _sync_overdue_billing_ticket(invoice, profile, today=today)
            for key, value in ticket_summary.items():
                summary[key] = summary.get(key, 0) + value
        if invoice.status == Invoice.Status.PAID:
            summary["billing_tickets_resolved"] += resolve_billing_tickets_for_invoice(
                invoice,
                resolution_note=f"Auto-resolved after settlement of invoice {invoice.invoice_number}.",
            )

    payments = InvoicePayment.objects.filter(invoice__organization=organization, invoice__customer_id__in=customer_ids).select_related(
        "invoice",
        "invoice__customer",
    )
    for payment in payments:
        _, created = ensure_payment_journal_posted(payment)
        if created:
            summary["payment_journals_posted"] += 1
        if TenantDocumentRecord.objects.filter(organization=organization, payment=payment).exists():
            continue
        profile = profile_by_customer.get(payment.invoice.customer_id)
        if profile is None:
            continue
        TenantDocumentRecord.objects.create(
            organization=organization,
            tenant_profile=profile,
            invoice=payment.invoice,
            payment=payment,
            title=f"Receipt {payment.invoice.invoice_number} / {payment.id}",
            category=TenantDocumentRecord.Category.PAYMENT_RECEIPT,
            status=TenantDocumentRecord.Status.ACTIVE,
            reference_number=payment.reference_number or f"PAY-{payment.id}",
            issue_date=payment.payment_date,
            is_signed=False,
            notes="Auto-generated from payment reconciliation.",
        )
        _record_log(
            profile,
            interaction_type=TenantCommunicationLog.InteractionType.SYSTEM,
            channel=TenantCommunicationLog.Channel.SYSTEM,
            direction=TenantCommunicationLog.Direction.INTERNAL,
            status=TenantCommunicationLog.Status.RECORDED,
            subject=f"Payment reconciled - {payment.invoice.invoice_number}",
            message=f"Payment of {payment.amount} was reconciled for invoice {payment.invoice.invoice_number}.",
            metadata={"payment_id": payment.id, "invoice_id": payment.invoice_id},
        )
        summary["receipts_created"] += 1

    return summary


def _dispatch_message(profile: TenantProfile, *, subject: str, message: str, interaction_type: str, email_only=False):
    contact_email = _profile_contact_email(profile)
    contact_phone = _profile_contact_phone(profile)
    delivered = 0
    if contact_email:
        try:
            sent_count = send_mail(subject, message, None, [contact_email])
            delivered += 1 if sent_count else 0
            _record_log(
                profile,
                interaction_type=interaction_type,
                channel=TenantCommunicationLog.Channel.EMAIL,
                direction=TenantCommunicationLog.Direction.OUTBOUND,
                status=TenantCommunicationLog.Status.SENT if sent_count else TenantCommunicationLog.Status.QUEUED,
                subject=subject,
                message=message,
                metadata={"recipient_email": contact_email},
            )
        except Exception as exc:  # pragma: no cover - runtime adapter path
            _record_log(
                profile,
                interaction_type=interaction_type,
                channel=TenantCommunicationLog.Channel.EMAIL,
                direction=TenantCommunicationLog.Direction.OUTBOUND,
                status=TenantCommunicationLog.Status.FAILED,
                subject=subject,
                message=message,
                metadata={"recipient_email": contact_email, "error": str(exc)},
            )
    if not email_only and contact_phone:
        try:
            adapter_result = get_whatsapp_provider_adapter().send_message(
                recipient_phone=contact_phone,
                message=message,
                metadata={"tenant_profile_id": profile.id, "subject": subject},
            )
            delivered += 1 if adapter_result.status in {"queued", "sent"} else 0
            _record_log(
                profile,
                interaction_type=interaction_type,
                channel=TenantCommunicationLog.Channel.WHATSAPP,
                direction=TenantCommunicationLog.Direction.OUTBOUND,
                status=TenantCommunicationLog.Status.SENT if adapter_result.status == "sent" else (
                    TenantCommunicationLog.Status.QUEUED if adapter_result.status == "queued" else TenantCommunicationLog.Status.FAILED
                ),
                subject=subject,
                message=message,
                metadata={"recipient_phone": contact_phone, "provider": adapter_result.provider_key},
            )
        except Exception as exc:  # pragma: no cover - runtime adapter path
            _record_log(
                profile,
                interaction_type=interaction_type,
                channel=TenantCommunicationLog.Channel.WHATSAPP,
                direction=TenantCommunicationLog.Direction.OUTBOUND,
                status=TenantCommunicationLog.Status.FAILED,
                subject=subject,
                message=message,
                metadata={"recipient_phone": contact_phone, "error": str(exc)},
            )
    return delivered


def sync_tenant_service_request_resolution_automation(service_request: ServiceRequest) -> dict[str, int]:
    summary = {
        "tenant_profiles_linked": 0,
        "resolution_notifications_sent": 0,
        "feedback_requests_sent": 0,
        "satisfaction_scores_updated": 0,
    }

    profile, linked_count = _ensure_service_request_tenant_profile(service_request)
    summary["tenant_profiles_linked"] += linked_count
    if profile is None:
        return summary

    if service_request.feedback_rating is not None:
        summary["satisfaction_scores_updated"] += refresh_tenant_satisfaction_score(profile)

    if service_request.status not in {ServiceRequest.Status.RESOLVED, ServiceRequest.Status.CLOSED}:
        return summary

    property_name = service_request.property.name if service_request.property_id and service_request.property else "your assigned property"
    facility_label = service_request.facility.facility_code if service_request.facility_id and service_request.facility else ""
    unit_label = service_request.unit.unit_number if service_request.unit_id and service_request.unit else ""
    location_suffix = ""
    location_parts = [part for part in [property_name, facility_label, unit_label] if part]
    if location_parts:
        location_suffix = " at " + " / ".join(location_parts)

    resolved_subject = f"Issue resolved - SR-{service_request.id}"
    if not _recent_subject_exists(profile, resolved_subject, days=SERVICE_REQUEST_RESOLUTION_LOOKBACK_DAYS):
        resolution_note = service_request.resolution_notes.strip() if service_request.resolution_notes else ""
        resolved_message = (
            f"Dear {profile.resolved_display_name},\n\n"
            f"Your service request \"{service_request.title}\" has been marked resolved{location_suffix}.\n"
            f"Resolved on: {(service_request.resolved_date or timezone.localdate()).isoformat()}\n"
            + (f"Resolution note: {resolution_note}\n" if resolution_note else "")
            + "\nIf the issue persists, please log a follow-up request in the tenant app.\n"
        )
        if _dispatch_message(
            profile,
            subject=resolved_subject,
            message=resolved_message,
            interaction_type=TenantCommunicationLog.InteractionType.SYSTEM,
        ):
            summary["resolution_notifications_sent"] += 1

    feedback_subject = f"Feedback request - SR-{service_request.id}"
    if service_request.feedback_submitted_at is None and not _recent_subject_exists(
        profile,
        feedback_subject,
        days=SERVICE_REQUEST_RESOLUTION_LOOKBACK_DAYS,
    ):
        feedback_message = (
            f"Dear {profile.resolved_display_name},\n\n"
            f"We've resolved your issue \"{service_request.title}\"{location_suffix}.\n"
            "Please rate the experience from 1 to 5 in the tenant app so we can keep improving our response quality.\n"
        )
        if _dispatch_message(
            profile,
            subject=feedback_subject,
            message=feedback_message,
            interaction_type=TenantCommunicationLog.InteractionType.SYSTEM,
        ):
            summary["feedback_requests_sent"] += 1

    return summary


def _overdue_penalty_marker(invoice: Invoice) -> str:
    return f"[overdue-penalty:invoice:{invoice.id}]"


def _apply_overdue_penalty(invoice: Invoice, profile: TenantProfile | None, *, today=None) -> int:
    today = today or timezone.localdate()
    if invoice.status != Invoice.Status.OVERDUE or invoice.balance_due <= ZERO_DECIMAL:
        return 0
    if invoice.days_overdue < OVERDUE_PENALTY_GRACE_DAYS:
        return 0

    marker = _overdue_penalty_marker(invoice)
    if Invoice.objects.filter(
        organization=invoice.organization,
        customer=invoice.customer,
        notes__icontains=marker,
    ).exists():
        return 0

    penalty_amount = _quantize(max(invoice.balance_due * OVERDUE_PENALTY_RATE, OVERDUE_PENALTY_MINIMUM))
    if penalty_amount <= ZERO_DECIMAL:
        return 0

    penalty_invoice = None
    with transaction.atomic():
        penalty_invoice = Invoice.objects.create(
            organization=invoice.organization,
            customer=invoice.customer,
            property=invoice.property,
            status=Invoice.Status.SENT,
            issue_date=today,
            due_date=today + timedelta(days=7),
            notes=f"Auto-generated late payment penalty for invoice {invoice.invoice_number}. {marker}",
        )
        InvoiceLineItem.objects.create(
            invoice=penalty_invoice,
            description=f"Late payment penalty for invoice {invoice.invoice_number}",
            quantity=Decimal("1.00"),
            unit_price=penalty_amount,
            sort_order=1,
        )
        penalty_invoice.recalculate_totals()

    if profile is not None:
        _record_log(
            profile,
            interaction_type=TenantCommunicationLog.InteractionType.INVOICE_GENERATED,
            channel=TenantCommunicationLog.Channel.SYSTEM,
            direction=TenantCommunicationLog.Direction.INTERNAL,
            status=TenantCommunicationLog.Status.RECORDED,
            subject=f"Late payment penalty applied - {penalty_invoice.invoice_number}",
            message=(
                f"Late payment penalty invoice {penalty_invoice.invoice_number} was created for "
                f"source invoice {invoice.invoice_number}."
            ),
            metadata={
                "source_invoice_id": invoice.id,
                "penalty_invoice_id": penalty_invoice.id,
                "days_overdue": invoice.days_overdue,
                "penalty_amount": f"{penalty_amount:.2f}",
            },
        )
        penalty_message = (
            f"Dear {profile.resolved_display_name},\n\n"
            f"Your invoice {invoice.invoice_number} is now {invoice.days_overdue} day(s) overdue.\n"
            f"A late payment penalty invoice ({penalty_invoice.invoice_number}) has been applied.\n"
            f"Penalty amount: NGN {penalty_amount:.2f}\n"
            f"Please settle the outstanding balance promptly to avoid further escalation.\n"
        )
        transaction.on_commit(
            lambda profile=profile, penalty_invoice=penalty_invoice, penalty_message=penalty_message: _dispatch_message(
                profile,
                subject=f"Late payment penalty - {penalty_invoice.invoice_number}",
                message=penalty_message,
                interaction_type=TenantCommunicationLog.InteractionType.INVOICE_GENERATED,
            )
        )

    return 1


def _sync_overdue_billing_ticket(invoice: Invoice, profile: TenantProfile | None, *, today=None) -> dict[str, int]:
    today = today or timezone.localdate()
    summary = {
        "billing_tickets_synced": 0,
        "billing_tickets_escalated": 0,
    }
    if invoice.status != Invoice.Status.OVERDUE or invoice.balance_due <= ZERO_DECIMAL:
        return summary
    if invoice.days_overdue < OVERDUE_BILLING_TICKET_DAYS:
        return summary

    ticket = (
        SupportTicket.objects.filter(
            organization=invoice.organization,
            invoice=invoice,
            category=SupportTicket.Category.BILLING,
        )
        .exclude(status__in=[SupportTicket.Status.RESOLVED, SupportTicket.Status.CLOSED])
        .order_by("id")
        .first()
    )

    escalated = invoice.days_overdue >= OVERDUE_ESCALATION_DAYS
    priority = (
        SupportTicket.Priority.CRITICAL
        if escalated
        else SupportTicket.Priority.HIGH
    )
    property_name = invoice.property.name if invoice.property_id and invoice.property else "the assigned property"
    description = (
        f"Invoice {invoice.invoice_number} for {property_name} is overdue by {invoice.days_overdue} day(s). "
        f"Outstanding balance: NGN {invoice.balance_due:.2f}."
    )

    if ticket is None:
        ticket = SupportTicket.objects.create(
            organization=invoice.organization,
            subject=f"Overdue invoice follow-up - {invoice.invoice_number}",
            description=description,
            requester=profile.primary_user if profile and profile.primary_user_id else None,
            customer=invoice.customer,
            contact_account=profile.contact_account if profile and profile.contact_account_id else None,
            invoice=invoice,
            category=SupportTicket.Category.BILLING,
            priority=priority,
            status=SupportTicket.Status.ESCALATED if escalated else SupportTicket.Status.OPEN,
        )
        summary["billing_tickets_synced"] += 1
        if escalated:
            summary["billing_tickets_escalated"] += 1
    else:
        update_fields: list[str] = []
        if ticket.priority != priority:
            ticket.priority = priority
            update_fields.append("priority")
        if description not in (ticket.description or ""):
            ticket.description = description
            update_fields.append("description")
        if escalated and ticket.status != SupportTicket.Status.ESCALATED:
            ticket.status = SupportTicket.Status.ESCALATED
            update_fields.append("status")
        if update_fields:
            ticket.save(update_fields=list(dict.fromkeys(update_fields + ["escalated_at", "updated_at"])))
            summary["billing_tickets_synced"] += 1
            if "status" in update_fields:
                summary["billing_tickets_escalated"] += 1

    if profile is not None and escalated:
        subject_prefix = f"Delinquency escalation - {invoice.invoice_number}"
        if not _recent_subject_exists(profile, subject_prefix, days=14):
            _record_log(
                profile,
                interaction_type=TenantCommunicationLog.InteractionType.SYSTEM,
                channel=TenantCommunicationLog.Channel.SYSTEM,
                direction=TenantCommunicationLog.Direction.INTERNAL,
                status=TenantCommunicationLog.Status.RECORDED,
                subject=subject_prefix,
                message=(
                    f"Billing ticket {ticket.ticket_id} was escalated after invoice {invoice.invoice_number} "
                    f"remained overdue for {invoice.days_overdue} day(s)."
                ),
                metadata={
                    "invoice_id": invoice.id,
                    "ticket_id": ticket.id,
                    "days_overdue": invoice.days_overdue,
                },
            )

    return summary


def _broadcast_recipients(broadcast: TenantBroadcast):
    qs = TenantProfile.objects.filter(organization=broadcast.organization).select_related(
        "customer",
        "contact_account",
        "primary_user",
        "facility",
        "property",
    )
    if broadcast.audience_type == TenantBroadcast.AudienceType.PROPERTY and broadcast.property_id:
        qs = qs.filter(property_id=broadcast.property_id)
    elif broadcast.audience_type == TenantBroadcast.AudienceType.FACILITY and broadcast.facility_id:
        qs = qs.filter(facility_id=broadcast.facility_id)
    elif broadcast.audience_type == TenantBroadcast.AudienceType.TENANT_TYPE and broadcast.tenant_type_filter:
        qs = qs.filter(tenant_type=broadcast.tenant_type_filter)
    elif broadcast.audience_type == TenantBroadcast.AudienceType.DELINQUENT:
        qs = qs.filter(customer__invoices__status=Invoice.Status.OVERDUE).distinct()
    elif broadcast.audience_type == TenantBroadcast.AudienceType.LEASE_EXPIRY:
        horizon = timezone.localdate() + timedelta(days=45)
        qs = qs.filter(lease_end_date__isnull=False, lease_end_date__lte=horizon, lease_end_date__gte=timezone.localdate())
    return list(qs.order_by("display_name", "id"))


def sync_communications_automation(organization) -> dict[str, int]:
    today = timezone.localdate()
    summary = {
        "rent_reminders_sent": 0,
        "lease_notices_sent": 0,
        "admin_expiry_alerts_sent": 0,
        "broadcasts_processed": 0,
    }
    admin_recipients = _org_admin_users(organization)
    profiles = list(
        TenantProfile.objects.filter(organization=organization)
        .select_related("customer", "contact_account", "primary_user", "property")
        .order_by("display_name", "id")
    )
    profile_by_customer = {profile.customer_id: profile for profile in profiles if profile.customer_id}

    invoices = Invoice.objects.filter(
        organization=organization,
        customer_id__in=list(profile_by_customer.keys()),
    ).exclude(status__in=[Invoice.Status.PAID, Invoice.Status.CANCELLED]).prefetch_related("payments")
    for invoice in invoices:
        if invoice.status not in {Invoice.Status.SENT, Invoice.Status.OVERDUE}:
            continue
        profile = profile_by_customer.get(invoice.customer_id)
        if profile is None:
            continue
        subject_prefix = f"Payment reminder - {invoice.invoice_number}"
        if _recent_subject_exists(profile, subject_prefix, days=3):
            continue
        if invoice.status == Invoice.Status.OVERDUE or invoice.due_date <= today + timedelta(days=5):
            message = (
                f"Dear {profile.resolved_display_name},\n\n"
                f"Invoice {invoice.invoice_number} for your tenancy is "
                f"{'overdue' if invoice.status == Invoice.Status.OVERDUE else 'due soon'}.\n"
                f"Due date: {invoice.due_date.isoformat()}\n"
                f"Amount due: NGN {invoice.balance_due:.2f}\n"
            )
            delivered = _dispatch_message(
                profile,
                subject=subject_prefix,
                message=message,
                interaction_type=TenantCommunicationLog.InteractionType.PAYMENT_REMINDER,
            )
            if delivered:
                summary["rent_reminders_sent"] += 1

    leases = LeaseAgreement.objects.filter(organization=organization).select_related(
        "tenant_profile",
        "tenant_profile__customer",
        "tenant_profile__contact_account",
        "tenant_profile__primary_user",
    )
    for lease in leases:
        if lease.end_date < today:
            continue
        if lease.end_date > today + timedelta(days=max(lease.notice_period_days, 30)):
            continue
        profile = lease.tenant_profile
        alert = getattr(lease, "vacancy_risk_alert", None)
        subject_prefix = f"Lease expiry notice - {lease.lease_code}"
        admin_subject_prefix = f"Lease expiry admin alert - {lease.lease_code}"
        if not _recent_subject_exists(profile, subject_prefix, days=10):
            message = (
                f"Dear {profile.resolved_display_name},\n\n"
                f"This is a reminder that lease {lease.lease_code} is due to expire on {lease.end_date.isoformat()}.\n"
                f"Please contact management if a renewal should be prepared.\n"
            )
            delivered = _dispatch_message(
                profile,
                subject=subject_prefix,
                message=message,
                interaction_type=TenantCommunicationLog.InteractionType.SYSTEM,
                email_only=True,
            )
            if delivered:
                summary["lease_notices_sent"] += 1
                if alert is not None and alert.tenant_notified_at is None:
                    alert.tenant_notified_at = timezone.now()
                    alert.save(update_fields=["tenant_notified_at", "updated_at"])

        if admin_recipients and not _recent_subject_exists(profile, admin_subject_prefix, days=10):
            from apps.notifications.models import Notification
            from apps.notifications.services import dispatch_workflow_notification

            admin_message = (
                f"{profile.resolved_display_name} has a lease due to expire on {lease.end_date.isoformat()} "
                f"for {lease.property.name if lease.property_id and lease.property else 'the assigned property'}."
            )
            dispatch_result = dispatch_workflow_notification(
                organization=organization,
                event_key="tenant_lease_expiry_approaching",
                recipients=admin_recipients,
                context={
                    "tenant_name": profile.resolved_display_name,
                    "lease_code": lease.lease_code,
                    "property_name": lease.property.name if lease.property_id and lease.property else "",
                    "unit_label": lease.unit.unit_number if lease.unit_id and lease.unit else "",
                    "expiry_date": lease.end_date.isoformat(),
                    "action_url": "/tenants/lease-occupancy",
                },
                link_url="/tenants/lease-occupancy",
                fallback_channels=("in_app", "email"),
                fallback_title=f"Lease Expiry Approaching - {lease.lease_code}",
                fallback_message=admin_message,
                fallback_category=Notification.Category.SYSTEM,
                fallback_severity=Notification.Severity.WARNING,
            )
            if dispatch_result["notifications_sent"] or dispatch_result["emails_sent"]:
                _record_log(
                    profile,
                    interaction_type=TenantCommunicationLog.InteractionType.SYSTEM,
                    channel=TenantCommunicationLog.Channel.SYSTEM,
                    direction=TenantCommunicationLog.Direction.INTERNAL,
                    status=TenantCommunicationLog.Status.RECORDED,
                    subject=admin_subject_prefix,
                    message=admin_message,
                    metadata={
                        "notifications_sent": dispatch_result["notifications_sent"],
                        "emails_sent": dispatch_result["emails_sent"],
                        "recipient_count": len(admin_recipients),
                    },
                )
                summary["admin_expiry_alerts_sent"] += 1
                if alert is not None and alert.admin_notified_at is None:
                    alert.admin_notified_at = timezone.now()
                    alert.save(update_fields=["admin_notified_at", "updated_at"])

    broadcasts = TenantBroadcast.objects.filter(
        organization=organization,
        status__in=[TenantBroadcast.Status.QUEUED, TenantBroadcast.Status.DRAFT],
    ).select_related("property", "facility", "created_by")
    for broadcast in broadcasts:
        recipients = _broadcast_recipients(broadcast)
        delivered_count = 0
        for profile in recipients:
            delivered_count += _dispatch_message(
                profile,
                subject=broadcast.subject,
                message=broadcast.message,
                interaction_type=TenantCommunicationLog.InteractionType.SYSTEM,
                email_only=not broadcast.send_whatsapp,
            )
            if broadcast.send_in_app:
                _record_log(
                    profile,
                    interaction_type=TenantCommunicationLog.InteractionType.SYSTEM,
                    channel=TenantCommunicationLog.Channel.SYSTEM,
                    direction=TenantCommunicationLog.Direction.OUTBOUND,
                    status=TenantCommunicationLog.Status.RECORDED,
                    subject=broadcast.subject,
                    message=broadcast.message,
                    metadata={"broadcast_id": broadcast.id},
                    author=broadcast.created_by,
                )
        broadcast.recipient_count = len(recipients)
        broadcast.delivered_count = delivered_count
        broadcast.sent_at = timezone.now()
        if delivered_count == 0 and recipients:
            broadcast.status = TenantBroadcast.Status.FAILED
        elif delivered_count < len(recipients):
            broadcast.status = TenantBroadcast.Status.PARTIAL
        else:
            broadcast.status = TenantBroadcast.Status.SENT
        broadcast.save(update_fields=["recipient_count", "delivered_count", "sent_at", "status", "updated_at"])
        summary["broadcasts_processed"] += 1
    return summary


def sync_documents_automation(organization) -> dict[str, int]:
    today = timezone.localdate()
    summary = {
        "documents_created": 0,
        "documents_expired": 0,
    }
    leases = LeaseAgreement.objects.filter(organization=organization).select_related("tenant_profile")
    for lease in leases:
        status = TenantDocumentRecord.Status.PENDING_SIGNATURE if not lease.signed_on else TenantDocumentRecord.Status.ACTIVE
        doc, created = TenantDocumentRecord.objects.get_or_create(
            organization=organization,
            tenant_profile=lease.tenant_profile,
            lease_agreement=lease,
            category=TenantDocumentRecord.Category.LEASE_AGREEMENT,
            defaults={
                "title": f"Lease agreement {lease.lease_code}",
                "status": status,
                "reference_number": lease.lease_code,
                "issue_date": lease.start_date,
                "expiry_date": lease.end_date,
                "is_signed": bool(lease.signed_on),
                "signed_at": timezone.make_aware(datetime.combine(lease.signed_on, datetime.min.time())) if lease.signed_on else None,
                "notes": "Auto-generated from lease setup.",
            },
        )
        if created:
            summary["documents_created"] += 1
        elif doc.status != status or doc.expiry_date != lease.end_date or doc.is_signed != bool(lease.signed_on):
            doc.status = status
            doc.expiry_date = lease.end_date
            doc.is_signed = bool(lease.signed_on)
            doc.save(update_fields=["status", "expiry_date", "is_signed", "updated_at"])

    inspections = TenantInspection.objects.filter(
        organization=organization,
        status=TenantInspection.Status.COMPLETED,
    ).select_related("tenant_profile")
    for inspection in inspections:
        if TenantDocumentRecord.objects.filter(organization=organization, inspection=inspection).exists():
            continue
        TenantDocumentRecord.objects.create(
            organization=organization,
            tenant_profile=inspection.tenant_profile,
            inspection=inspection,
            lease_agreement=inspection.lease_agreement,
            title=f"Inspection report - {inspection.title}",
            category=TenantDocumentRecord.Category.INSPECTION_REPORT,
            status=TenantDocumentRecord.Status.ACTIVE,
            issue_date=inspection.completed_date or inspection.scheduled_date,
            notes="Auto-generated from completed tenant inspection.",
        )
        summary["documents_created"] += 1

    expired_docs = TenantDocumentRecord.objects.filter(
        organization=organization,
        expiry_date__lt=today,
    ).exclude(status=TenantDocumentRecord.Status.EXPIRED)
    expired_count = expired_docs.count()
    expired_docs.update(status=TenantDocumentRecord.Status.EXPIRED, updated_at=timezone.now())
    summary["documents_expired"] = expired_count
    return summary


def sync_inspections_automation(organization) -> dict[str, int]:
    today = timezone.localdate()
    summary = {
        "inspections_created": 0,
        "deposit_deductions_logged": 0,
        "facility_inspection_alerts_sent": 0,
        "deposit_settlements_created": 0,
        "deposit_settlements_updated": 0,
        "deposit_settlements_ready": 0,
        "deposit_collection_invoices_created": 0,
    }
    leases = LeaseAgreement.objects.filter(
        organization=organization,
        status__in=[
            LeaseAgreement.Status.ACTIVE,
            LeaseAgreement.Status.EXPIRING_SOON,
            LeaseAgreement.Status.TERMINATION_PENDING,
            LeaseAgreement.Status.TERMINATED,
        ],
    ).select_related("tenant_profile", "tenant_profile__customer")

    for lease in leases:
        profile = lease.tenant_profile
        move_in_target = profile.move_in_date or lease.start_date
        if today <= move_in_target <= today + timedelta(days=7) and not lease.inspections.filter(
            inspection_type=TenantInspection.InspectionType.MOVE_IN
        ).exists():
            TenantInspection.objects.create(
                organization=organization,
                tenant_profile=profile,
                lease_agreement=lease,
                property=lease.property,
                unit=lease.unit,
                facility=lease.facility,
                facility_space=lease.facility_space,
                inspection_type=TenantInspection.InspectionType.MOVE_IN,
                title=f"Move-in inspection - {profile.resolved_display_name}",
                scheduled_date=move_in_target,
            )
            summary["inspections_created"] += 1

        move_out_target = profile.move_out_date or lease.terminated_on or lease.end_date
        if move_out_target and today <= move_out_target <= today + timedelta(days=7) and not lease.inspections.filter(
            inspection_type=TenantInspection.InspectionType.MOVE_OUT
        ).exists():
            inspection = TenantInspection.objects.create(
                organization=organization,
                tenant_profile=profile,
                lease_agreement=lease,
                property=lease.property,
                unit=lease.unit,
                facility=lease.facility,
                facility_space=lease.facility_space,
                inspection_type=TenantInspection.InspectionType.MOVE_OUT,
                title=f"Move-out inspection - {profile.resolved_display_name}",
                scheduled_date=move_out_target,
            )
            summary["inspections_created"] += 1
            summary["facility_inspection_alerts_sent"] += _notify_move_out_inspection_required(lease, inspection)

        if lease.terminated_on:
            settlement_summary = _sync_deposit_settlement_for_lease(lease, today)
            for key, value in settlement_summary.items():
                summary[key] += value

    inspections = TenantInspection.objects.filter(
        organization=organization,
        status=TenantInspection.Status.COMPLETED,
        inspection_type=TenantInspection.InspectionType.MOVE_OUT,
        security_deposit_deduction__gt=ZERO_DECIMAL,
    )
    summary["deposit_deductions_logged"] = inspections.count()
    return summary


def sync_complaints_automation(organization) -> dict[str, int]:
    now = timezone.now()
    summary = {
        "complaints_escalated": 0,
        "service_requests_created": 0,
        "complaints_resolved": 0,
    }
    complaints = TenantComplaint.objects.filter(organization=organization).select_related(
        "tenant_profile",
        "tenant_profile__customer",
        "tenant_profile__contact_account",
        "tenant_profile__primary_user",
        "service_request",
    )
    for complaint in complaints:
        updates = []
        if complaint.sla_due_at is None and complaint.status in {
            TenantComplaint.Status.OPEN,
            TenantComplaint.Status.ACKNOWLEDGED,
        }:
            hours = complaint.sla_target_hours or 24
            complaint.sla_due_at = now + timedelta(hours=hours)
            updates.append("sla_due_at")

        if complaint.category == TenantComplaint.Category.MAINTENANCE and complaint.service_request_id is None:
            profile = complaint.tenant_profile
            service_request = ServiceRequest.objects.create(
                organization=organization,
                tenant_profile=profile,
                property=complaint.property or profile.property,
                facility=complaint.facility or profile.facility,
                facility_space=complaint.facility_space or profile.facility_space,
                unit=complaint.unit or profile.unit,
                title=complaint.subject,
                description=complaint.description,
                category=WorkOrder.Category.GENERAL,
                priority=ServiceRequest.Priority.HIGH if complaint.priority in {
                    TenantComplaint.Priority.HIGH,
                    TenantComplaint.Priority.CRITICAL,
                } else ServiceRequest.Priority.MEDIUM,
                status=ServiceRequest.Status.OPEN,
                requester=profile.primary_user,
                requested_by=profile.resolved_display_name,
            )
            ensure_service_request_defaults(service_request)
            ensure_service_request_work_order(service_request)
            complaint.service_request = service_request
            updates.append("service_request")
            summary["service_requests_created"] += 1

        if complaint.service_request_id and complaint.service_request:
            if complaint.service_request.status in {ServiceRequest.Status.RESOLVED, ServiceRequest.Status.CLOSED} and complaint.status not in {
                TenantComplaint.Status.RESOLVED,
                TenantComplaint.Status.CLOSED,
            }:
                complaint.status = TenantComplaint.Status.RESOLVED
                complaint.resolved_at = now
                updates.extend(["status", "resolved_at"])
                summary["complaints_resolved"] += 1

        if complaint.sla_due_at and complaint.sla_due_at <= now and complaint.status not in {
            TenantComplaint.Status.ESCALATED,
            TenantComplaint.Status.RESOLVED,
            TenantComplaint.Status.CLOSED,
        }:
            complaint.status = TenantComplaint.Status.ESCALATED
            complaint.escalated_at = now
            updates.extend(["status", "escalated_at"])
            summary["complaints_escalated"] += 1

        if updates:
            complaint.save(update_fields=list(dict.fromkeys(updates + ["updated_at"])))
    return summary


def sync_service_requests_automation(organization) -> dict[str, int]:
    return run_service_request_helpdesk_automation(organization)


def run_tenant_operations_automation(organization, *, scopes: set[str] | None = None) -> dict[str, int]:
    ordered_scopes = (
        "lease_occupancy",
        "billing",
        "payments",
        "service_requests",
        "communications",
        "documents",
        "inspections",
        "complaints",
    )
    scopes = scopes or set(ordered_scopes)
    summary = {
        "leases_synced": 0,
        "occupancies_synced": 0,
        "renewals_created": 0,
        "terminations_created": 0,
        "allocations_synced": 0,
        "rent_escalations_applied": 0,
        "billing_rules_stopped": 0,
        "vacancy_risks_created": 0,
        "vacancy_risks_updated": 0,
        "vacancy_risks_resolved": 0,
        "vacancy_risks_open": 0,
        "invoices_created": 0,
        "rules_skipped": 0,
        "utility_bills_visible": 0,
        "payments_reconciled": 0,
        "late_payment_penalties_applied": 0,
        "payment_journals_posted": 0,
        "receipts_created": 0,
        "billing_tickets_resolved": 0,
        "service_requests_synced": 0,
        "service_requests_escalated": 0,
        "work_orders_created": 0,
        "overdue_invoices_flagged": 0,
        "billing_tickets_synced": 0,
        "billing_tickets_escalated": 0,
        "rent_reminders_sent": 0,
        "lease_notices_sent": 0,
        "admin_expiry_alerts_sent": 0,
        "broadcasts_processed": 0,
        "documents_created": 0,
        "documents_expired": 0,
        "inspections_created": 0,
        "facility_inspection_alerts_sent": 0,
        "deposit_deductions_logged": 0,
        "deposit_settlements_created": 0,
        "deposit_settlements_updated": 0,
        "deposit_settlements_ready": 0,
        "deposit_collection_invoices_created": 0,
        "complaints_escalated": 0,
        "service_requests_created": 0,
        "complaints_resolved": 0,
    }
    runners = {
        "lease_occupancy": sync_lease_occupancy_automation,
        "billing": sync_billing_charges_automation,
        "payments": sync_payments_collections_automation,
        "service_requests": sync_service_requests_automation,
        "communications": sync_communications_automation,
        "documents": sync_documents_automation,
        "inspections": sync_inspections_automation,
        "complaints": sync_complaints_automation,
    }
    for scope in ordered_scopes:
        if scope not in scopes:
            continue
        result = runners[scope](organization)
        for key, value in result.items():
            summary[key] = summary.get(key, 0) + value
    return summary
