from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.mixins import OrgScopedMixin
from apps.facility_management.models import Facility, FacilityUnitSpace, UtilityBill
from apps.facility_management.service_request_serializers import (
    FacilityServiceRequestListSerializer,
    FacilityServiceRequestWriteSerializer,
)
from apps.facility_management.service_request_workflows import service_request_sla_status_for
from apps.finance.models import Invoice, InvoicePayment, PaymentMethod
from apps.properties.models import Property, ServiceRequest, Unit
from apps.settings.permissions import HasRolePermission

from .models import (
    LeaseAgreement,
    LeaseRenewalRequest,
    LeaseTerminationRequest,
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
from .operations_serializers import (
    LeaseAgreementSerializer,
    LeaseAgreementWriteSerializer,
    LeaseRenewalRequestSerializer,
    LeaseRenewalRequestWriteSerializer,
    LeaseTerminationRequestSerializer,
    LeaseTerminationRequestWriteSerializer,
    OccupancyRecordSerializer,
    OccupancyRecordWriteSerializer,
    RecurringChargeRuleSerializer,
    RecurringChargeRuleWriteSerializer,
    TenantBroadcastSerializer,
    TenantBroadcastWriteSerializer,
    TenantComplaintSerializer,
    TenantComplaintWriteSerializer,
    TenantDocumentRecordSerializer,
    TenantDocumentRecordWriteSerializer,
    TenantInspectionSerializer,
    TenantInspectionWriteSerializer,
)
from .serializers import TenantCommunicationLogSerializer
from .workflows import run_tenant_operations_automation

ZERO_DECIMAL = Decimal("0.00")


def _resolve_user_org(request):
    org = getattr(request, "organization", None)
    if org is not None:
        return org
    profile = getattr(getattr(request, "user", None), "profile", None)
    return getattr(profile, "organization", None)


def _service_request_queryset(org):
    tenant_profiles = TenantProfile.objects.filter(organization=org)
    profile_ids = [profile_id for profile_id in tenant_profiles.values_list("id", flat=True) if profile_id]
    unit_ids = [unit_id for unit_id in tenant_profiles.values_list("unit_id", flat=True) if unit_id]
    facility_space_ids = [
        facility_space_id for facility_space_id in tenant_profiles.values_list("facility_space_id", flat=True) if facility_space_id
    ]
    requester_ids = [user_id for user_id in tenant_profiles.values_list("primary_user_id", flat=True) if user_id]
    if not profile_ids and not unit_ids and not facility_space_ids and not requester_ids:
        return ServiceRequest.objects.none()
    return ServiceRequest.objects.filter(organization=org).filter(
        Q(tenant_profile_id__in=profile_ids)
        | Q(unit_id__in=unit_ids)
        | Q(facility_space_id__in=facility_space_ids)
        | Q(requester_id__in=requester_ids)
    )


def _tenant_invoices_queryset(org):
    customer_ids = [customer_id for customer_id in TenantProfile.objects.filter(organization=org).values_list("customer_id", flat=True) if customer_id]
    if not customer_ids:
        return Invoice.objects.none()
    return Invoice.objects.filter(organization=org, customer_id__in=customer_ids).exclude(status=Invoice.Status.CANCELLED)


def _vacancy_risk_payload(alert: TenantVacancyRiskAlert) -> dict:
    return {
        "id": alert.id,
        "tenant_name": alert.tenant_profile.resolved_display_name,
        "lease_code": alert.lease_agreement.lease_code,
        "property_name": alert.property.name if alert.property_id and alert.property else "",
        "unit_label": alert.unit.unit_number if alert.unit_id and alert.unit else "",
        "status": alert.status,
        "status_display": alert.get_status_display(),
        "risk_level": alert.risk_level,
        "risk_level_display": alert.get_risk_level_display(),
        "risk_score": alert.risk_score,
        "forecasted_vacancy_date": alert.forecasted_vacancy_date.isoformat() if alert.forecasted_vacancy_date else None,
        "days_to_vacancy": alert.days_to_vacancy,
        "notes": alert.notes,
    }


def _deposit_settlement_payload(settlement: TenantDepositSettlement) -> dict:
    return {
        "id": settlement.id,
        "tenant_name": settlement.tenant_profile.resolved_display_name,
        "lease_code": settlement.lease_agreement.lease_code,
        "status": settlement.status,
        "status_display": settlement.get_status_display(),
        "move_out_date": settlement.move_out_date.isoformat() if settlement.move_out_date else None,
        "deposit_amount": f"{settlement.deposit_amount:.2f}",
        "assessed_deductions": f"{settlement.assessed_deductions:.2f}",
        "refundable_amount": f"{settlement.refundable_amount:.2f}",
        "additional_amount_due": f"{settlement.additional_amount_due:.2f}",
        "collection_invoice_number": settlement.collection_invoice.invoice_number if settlement.collection_invoice_id and settlement.collection_invoice else "",
        "notes": settlement.notes,
    }


def _invoice_balance(invoice: Invoice) -> Decimal:
    paid_amount = sum((payment.amount for payment in invoice.payments.all()), ZERO_DECIMAL)
    return max((invoice.total_amount or ZERO_DECIMAL) - paid_amount, ZERO_DECIMAL)


def _month_bounds(value):
    month_start = value.replace(day=1)
    if month_start.month == 12:
        next_month_start = month_start.replace(year=month_start.year + 1, month=1)
    else:
        next_month_start = month_start.replace(month=month_start.month + 1)
    return month_start, next_month_start


def _month_label(value) -> str:
    return value.strftime("%b %Y")


def _add_months(value, months):
    month_index = (value.month - 1) + months
    year = value.year + (month_index // 12)
    month = (month_index % 12) + 1
    return value.replace(year=year, month=month, day=1)


def _simple_invoice_payload(invoice: Invoice) -> dict:
    return {
        "id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "customer_name": invoice.customer.name,
        "property_name": invoice.property.name if invoice.property_id and invoice.property else "",
        "status": invoice.status,
        "status_display": invoice.get_status_display(),
        "issue_date": invoice.issue_date.isoformat(),
        "due_date": invoice.due_date.isoformat(),
        "total_amount": f"{invoice.total_amount:.2f}",
        "balance_due": f"{_invoice_balance(invoice):.2f}",
        "notes": invoice.notes or "",
    }


def _simple_payment_payload(payment: InvoicePayment) -> dict:
    return {
        "id": payment.id,
        "invoice_id": payment.invoice_id,
        "invoice_number": payment.invoice.invoice_number,
        "customer_name": payment.invoice.customer.name,
        "amount": f"{payment.amount:.2f}",
        "payment_date": payment.payment_date.isoformat(),
        "payment_method": payment.payment_method,
        "payment_method_display": payment.get_payment_method_display(),
        "reference_number": payment.reference_number,
        "notes": payment.notes or "",
    }


class TenantModuleSyncView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "tenants.all"
    rbac_action = "edit"
    scopes: set[str] = set()

    def post(self, request):
        org = _resolve_user_org(request)
        if org is None:
            return Response({"detail": "Organization context required."}, status=400)
        summary = run_tenant_operations_automation(org, scopes=self.scopes)
        return Response(summary)


class LeaseOccupancySyncView(TenantModuleSyncView):
    scopes = {"lease_occupancy", "communications", "inspections"}


class BillingSyncView(TenantModuleSyncView):
    scopes = {"billing", "payments", "communications"}


class PaymentsSyncView(TenantModuleSyncView):
    scopes = {"payments", "documents", "communications"}


class ServiceRequestsSyncView(TenantModuleSyncView):
    scopes = {"service_requests", "complaints"}


class CommunicationsSyncView(TenantModuleSyncView):
    scopes = {"communications"}


class DocumentsSyncView(TenantModuleSyncView):
    scopes = {"documents"}


class InspectionsSyncView(TenantModuleSyncView):
    scopes = {"inspections", "documents"}


class ComplaintsSyncView(TenantModuleSyncView):
    scopes = {"complaints", "service_requests"}


class TenantOperationsLookupsView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "tenants.all"
    rbac_action = "view"

    def get(self, request):
        org = _resolve_user_org(request)
        if org is None:
            return Response({"detail": "Organization context required."}, status=400)

        users = request.user.__class__.objects.filter(profile__organization=org, is_active=True).order_by("email")
        profiles = TenantProfile.objects.filter(organization=org).select_related("property", "unit", "facility").order_by("display_name", "id")
        leases = LeaseAgreement.objects.filter(organization=org).order_by("end_date", "tenant_profile__display_name")
        invoices = _tenant_invoices_queryset(org).select_related("customer", "property").order_by("-due_date", "-id")

        return Response(
            {
                "generated_at": timezone.now().isoformat(),
                "tenants": [
                    {
                        "id": profile.id,
                        "label": profile.resolved_display_name,
                        "status": profile.status,
                        "property_name": profile.property.name if profile.property_id and profile.property else "",
                        "unit_label": profile.unit.unit_number if profile.unit_id and profile.unit else (
                            profile.facility_space.space_label if profile.facility_space_id and profile.facility_space else ""
                        ),
                    }
                    for profile in profiles
                ],
                "leases": [
                    {
                        "id": lease.id,
                        "lease_code": lease.lease_code,
                        "tenant_profile": lease.tenant_profile_id,
                        "label": f"{lease.lease_code} - {lease.tenant_profile.resolved_display_name}",
                    }
                    for lease in leases
                ],
                "invoices": [
                    {
                        "id": invoice.id,
                        "label": f"{invoice.invoice_number} - {invoice.customer.name}",
                        "balance_due": f"{_invoice_balance(invoice):.2f}",
                    }
                    for invoice in invoices[:200]
                ],
                "properties": [
                    {
                        "id": property_record.id,
                        "name": property_record.name,
                        "address": property_record.address,
                    }
                    for property_record in Property.objects.filter(organization=org).order_by("name")
                ],
                "units": [
                    {
                        "id": unit.id,
                        "property_id": unit.property_id,
                        "label": f"{unit.property.name} - {unit.unit_number}",
                        "status": unit.status,
                        "status_display": unit.get_status_display(),
                    }
                    for unit in Unit.objects.filter(organization=org).select_related("property").order_by("property__name", "unit_number")
                ],
                "facilities": [
                    {
                        "id": facility.id,
                        "property_id": facility.property_id,
                        "label": f"{facility.property.name} - {facility.facility_code}",
                    }
                    for facility in Facility.objects.filter(organization=org).select_related("property").order_by("property__name", "facility_code")
                ],
                "spaces": [
                    {
                        "id": space.id,
                        "facility_id": space.facility_id,
                        "unit_id": space.unit_id,
                        "label": f"{space.facility.facility_code} - {(space.space_label or space.unit.unit_number)}",
                    }
                    for space in FacilityUnitSpace.objects.filter(organization=org).select_related("facility", "unit").order_by("facility__facility_code", "unit__unit_number")
                ],
                "users": [
                    {
                        "id": user.id,
                        "label": user.get_full_name().strip() or user.email or user.username,
                    }
                    for user in users
                ],
                "payment_methods": [{"value": value, "label": label} for value, label in PaymentMethod.choices],
            }
        )


class TenantLeaseOccupancyOverviewView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "tenants.all"
    rbac_action = "view"

    def get(self, request):
        org = _resolve_user_org(request)
        if org is None:
            return Response({"detail": "Organization context required."}, status=400)
        leases = list(
            LeaseAgreement.objects.filter(organization=org)
            .select_related("tenant_profile", "property", "unit", "facility", "facility_space", "facility_space__unit")
            .order_by("end_date", "tenant_profile__display_name")
        )
        occupancies = list(
            OccupancyRecord.objects.filter(organization=org)
            .select_related("tenant_profile", "lease_agreement", "property", "unit", "facility", "facility_space", "facility_space__unit")
            .order_by("move_out_date", "move_in_date", "-id")
        )
        vacancy_risks = list(
            TenantVacancyRiskAlert.objects.filter(
                organization=org,
                status__in=[TenantVacancyRiskAlert.Status.OPEN, TenantVacancyRiskAlert.Status.MITIGATED],
            )
            .select_related("tenant_profile", "lease_agreement", "property", "unit")
            .order_by("-risk_score", "forecasted_vacancy_date", "-id")
        )
        renewals = LeaseRenewalRequest.objects.filter(organization=org, status=LeaseRenewalRequest.Status.PENDING).count()
        terminations = LeaseTerminationRequest.objects.filter(
            organization=org,
            status__in=[LeaseTerminationRequest.Status.REQUESTED, LeaseTerminationRequest.Status.PENDING_APPROVAL],
        ).count()
        payload = {
            "generated_at": timezone.now().isoformat(),
            "kpis": {
                "active_leases": sum(1 for lease in leases if lease.status == LeaseAgreement.Status.ACTIVE),
                "expiring_soon": sum(1 for lease in leases if lease.status == LeaseAgreement.Status.EXPIRING_SOON),
                "pending_renewals": renewals,
                "termination_queue": terminations,
                "active_occupancies": sum(1 for occupancy in occupancies if occupancy.status == OccupancyRecord.Status.ACTIVE),
                "notice_given": sum(1 for occupancy in occupancies if occupancy.status == OccupancyRecord.Status.NOTICE_GIVEN),
                "vacancy_risks_open": len(vacancy_risks),
            },
            "lease_watchlist": LeaseAgreementSerializer(leases[:8], many=True, context={"request": request}).data,
            "occupancy_watchlist": OccupancyRecordSerializer(occupancies[:8], many=True, context={"request": request}).data,
            "vacancy_risk_watchlist": [_vacancy_risk_payload(alert) for alert in vacancy_risks[:6]],
        }
        return Response(payload)


class TenantBillingOverviewView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "tenants.all"
    rbac_action = "view"

    def get(self, request):
        org = _resolve_user_org(request)
        if org is None:
            return Response({"detail": "Organization context required."}, status=400)
        invoices = list(
            _tenant_invoices_queryset(org)
            .select_related("customer", "property")
            .prefetch_related("payments")
            .order_by("due_date", "-id")
        )
        active_rules = RecurringChargeRule.objects.filter(organization=org, status=RecurringChargeRule.Status.ACTIVE).count()
        outstanding_total = sum((_invoice_balance(invoice) for invoice in invoices), ZERO_DECIMAL)
        utility_property_ids = [property_id for property_id in TenantProfile.objects.filter(organization=org).values_list("property_id", flat=True) if property_id]
        utility_bills = list(
            UtilityBill.objects.filter(organization=org, property_id__in=utility_property_ids)
            .exclude(status=UtilityBill.Status.CANCELLED)
            .select_related("property")
            .order_by("-billing_period_end", "-id")
        )
        payload = {
            "generated_at": timezone.now().isoformat(),
            "kpis": {
                "active_charge_rules": active_rules,
                "draft_or_sent_invoices": sum(1 for invoice in invoices if invoice.status in {Invoice.Status.DRAFT, Invoice.Status.SENT}),
                "overdue_invoices": sum(1 for invoice in invoices if invoice.status == Invoice.Status.OVERDUE),
                "outstanding_total": f"{outstanding_total:.2f}",
                "utility_bills": len(utility_bills),
            },
            "invoice_watchlist": [_simple_invoice_payload(invoice) for invoice in invoices[:10]],
            "utility_watchlist": [
                {
                    "id": bill.id,
                    "bill_number": bill.bill_number,
                    "property_name": bill.property.name,
                    "utility_type": bill.utility_type,
                    "utility_type_display": bill.get_utility_type_display(),
                    "status": bill.status,
                    "status_display": bill.get_status_display(),
                    "due_date": bill.due_date.isoformat(),
                    "total_amount": f"{bill.total_amount:.2f}",
                }
                for bill in utility_bills[:8]
            ],
        }
        return Response(payload)


class TenantPaymentsOverviewView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "tenants.all"
    rbac_action = "view"

    def get(self, request):
        org = _resolve_user_org(request)
        if org is None:
            return Response({"detail": "Organization context required."}, status=400)
        today = timezone.localdate()
        month_start, next_month_start = _month_bounds(today)
        invoices = list(
            _tenant_invoices_queryset(org)
            .select_related("customer", "property")
            .prefetch_related("payments")
        )
        payments = list(
            InvoicePayment.objects.filter(invoice__in=invoices)
            .select_related("invoice", "invoice__customer")
            .order_by("-payment_date", "-id")
        )
        monthly_collections = sum(
            (payment.amount for payment in payments if month_start <= payment.payment_date < next_month_start),
            ZERO_DECIMAL,
        )
        outstanding_total = sum((_invoice_balance(invoice) for invoice in invoices), ZERO_DECIMAL)
        overdue_total = sum((_invoice_balance(invoice) for invoice in invoices if invoice.status == Invoice.Status.OVERDUE), ZERO_DECIMAL)
        payload = {
            "generated_at": timezone.now().isoformat(),
            "kpis": {
                "payments_this_month": f"{monthly_collections:.2f}",
                "outstanding_total": f"{outstanding_total:.2f}",
                "overdue_total": f"{overdue_total:.2f}",
                "paid_invoices": sum(1 for invoice in invoices if invoice.status == Invoice.Status.PAID),
                "receipt_documents": TenantDocumentRecord.objects.filter(
                    organization=org,
                    category=TenantDocumentRecord.Category.PAYMENT_RECEIPT,
                ).count(),
            },
            "recent_payments": [_simple_payment_payload(payment) for payment in payments[:10]],
            "collections_watchlist": [
                _simple_invoice_payload(invoice)
                for invoice in sorted(
                    [invoice for invoice in invoices if _invoice_balance(invoice) > ZERO_DECIMAL],
                    key=lambda item: (item.due_date, item.id),
                )[:8]
            ],
        }
        return Response(payload)


class TenantServiceRequestsOverviewView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "tenants.all"
    rbac_action = "view"

    def get(self, request):
        org = _resolve_user_org(request)
        if org is None:
            return Response({"detail": "Organization context required."}, status=400)
        requests = list(
            _service_request_queryset(org)
            .select_related("property", "facility", "facility_space", "facility_space__unit", "unit", "requester", "assigned_agent", "work_order")
            .order_by("sla_due_at", "-created_at")
        )
        open_requests = [item for item in requests if item.status not in {ServiceRequest.Status.RESOLVED, ServiceRequest.Status.CLOSED}]
        feedback_values = [item.feedback_rating for item in requests if item.feedback_rating is not None]
        payload = {
            "generated_at": timezone.now().isoformat(),
            "kpis": {
                "open_requests": len(open_requests),
                "escalated_requests": sum(1 for item in open_requests if item.status == ServiceRequest.Status.ESCALATED),
                "sla_at_risk": sum(1 for item in open_requests if service_request_sla_status_for(item) in {"at_risk", "breached"}),
                "resolved_requests": sum(1 for item in requests if item.status in {ServiceRequest.Status.RESOLVED, ServiceRequest.Status.CLOSED}),
                "avg_feedback": round(sum(feedback_values) / len(feedback_values), 2) if feedback_values else None,
            },
            "watchlist": FacilityServiceRequestListSerializer(open_requests[:10], many=True, context={"request": request}).data,
        }
        return Response(payload)


class TenantCommunicationsOverviewView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "tenants.all"
    rbac_action = "view"

    def get(self, request):
        org = _resolve_user_org(request)
        if org is None:
            return Response({"detail": "Organization context required."}, status=400)
        since_30 = timezone.now() - timedelta(days=30)
        logs = list(
            TenantCommunicationLog.objects.filter(organization=org)
            .select_related("tenant_profile", "author")
            .order_by("-happened_at", "-id")
        )
        broadcasts = list(TenantBroadcast.objects.filter(organization=org).order_by("-created_at", "-id"))
        payload = {
            "generated_at": timezone.now().isoformat(),
            "kpis": {
                "messages_30_days": sum(1 for log in logs if log.happened_at >= since_30),
                "queued_broadcasts": sum(1 for broadcast in broadcasts if broadcast.status == TenantBroadcast.Status.QUEUED),
                "failed_messages": sum(1 for log in logs if log.status == TenantCommunicationLog.Status.FAILED),
                "reminders_30_days": sum(
                    1 for log in logs if log.interaction_type == TenantCommunicationLog.InteractionType.PAYMENT_REMINDER and log.happened_at >= since_30
                ),
            },
            "recent_logs": TenantCommunicationLogSerializer(logs[:12], many=True).data,
            "broadcasts": TenantBroadcastSerializer(broadcasts[:8], many=True, context={"request": request}).data,
        }
        return Response(payload)


class TenantDocumentsOverviewView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "tenants.all"
    rbac_action = "view"

    def get(self, request):
        org = _resolve_user_org(request)
        if org is None:
            return Response({"detail": "Organization context required."}, status=400)
        documents = list(
            TenantDocumentRecord.objects.filter(organization=org)
            .select_related("tenant_profile", "lease_agreement")
            .order_by("expiry_date", "-created_at")
        )
        payload = {
            "generated_at": timezone.now().isoformat(),
            "kpis": {
                "documents_total": len(documents),
                "pending_signature": sum(1 for doc in documents if doc.status == TenantDocumentRecord.Status.PENDING_SIGNATURE),
                "expired_documents": sum(1 for doc in documents if doc.status == TenantDocumentRecord.Status.EXPIRED),
                "payment_receipts": sum(1 for doc in documents if doc.category == TenantDocumentRecord.Category.PAYMENT_RECEIPT),
            },
            "watchlist": TenantDocumentRecordSerializer(documents[:12], many=True, context={"request": request}).data,
        }
        return Response(payload)


class TenantInspectionsOverviewView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "tenants.all"
    rbac_action = "view"

    def get(self, request):
        org = _resolve_user_org(request)
        if org is None:
            return Response({"detail": "Organization context required."}, status=400)
        since_30 = timezone.localdate() - timedelta(days=30)
        inspections = list(
            TenantInspection.objects.filter(organization=org)
            .select_related("tenant_profile", "lease_agreement", "inspector")
            .order_by("scheduled_date", "-id")
        )
        settlements = list(
            TenantDepositSettlement.objects.filter(organization=org)
            .select_related("tenant_profile", "lease_agreement", "collection_invoice")
            .order_by("status", "move_out_date", "-id")
        )
        payload = {
            "generated_at": timezone.now().isoformat(),
            "kpis": {
                "scheduled": sum(1 for inspection in inspections if inspection.status == TenantInspection.Status.SCHEDULED),
                "completed_30_days": sum(1 for inspection in inspections if inspection.completed_date and inspection.completed_date >= since_30),
                "move_out_pending": sum(
                    1
                    for inspection in inspections
                    if inspection.inspection_type == TenantInspection.InspectionType.MOVE_OUT
                    and inspection.status != TenantInspection.Status.COMPLETED
                ),
                "deposit_deductions": f"{sum((inspection.security_deposit_deduction for inspection in inspections), ZERO_DECIMAL):.2f}",
                "settlement_queue": sum(1 for settlement in settlements if settlement.status != TenantDepositSettlement.Status.SETTLED),
            },
            "watchlist": TenantInspectionSerializer(inspections[:10], many=True, context={"request": request}).data,
            "settlement_watchlist": [_deposit_settlement_payload(settlement) for settlement in settlements[:8]],
        }
        return Response(payload)


class TenantComplaintsOverviewView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "tenants.all"
    rbac_action = "view"

    def get(self, request):
        org = _resolve_user_org(request)
        if org is None:
            return Response({"detail": "Organization context required."}, status=400)
        since_30 = timezone.now() - timedelta(days=30)
        complaints = list(
            TenantComplaint.objects.filter(organization=org)
            .select_related("tenant_profile", "service_request", "assigned_to")
            .order_by("sla_due_at", "-created_at")
        )
        payload = {
            "generated_at": timezone.now().isoformat(),
            "kpis": {
                "open_complaints": sum(1 for complaint in complaints if complaint.status in {TenantComplaint.Status.OPEN, TenantComplaint.Status.ACKNOWLEDGED}),
                "escalated": sum(1 for complaint in complaints if complaint.status == TenantComplaint.Status.ESCALATED),
                "resolved_30_days": sum(1 for complaint in complaints if complaint.resolved_at and complaint.resolved_at >= since_30),
                "linked_service_requests": sum(1 for complaint in complaints if complaint.service_request_id),
            },
            "watchlist": TenantComplaintSerializer(complaints[:10], many=True, context={"request": request}).data,
        }
        return Response(payload)


class TenantReportsOverviewView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "tenants.all"
    rbac_action = "view"

    def get(self, request):
        org = _resolve_user_org(request)
        if org is None:
            return Response({"detail": "Organization context required."}, status=400)

        today = timezone.localdate()
        current_month_start, next_month_start = _month_bounds(today)
        month_starts = [_add_months(current_month_start, offset) for offset in range(-5, 1)]
        profiles = list(TenantProfile.objects.filter(organization=org).select_related("property", "customer").order_by("display_name", "id"))
        active_profiles = [profile for profile in profiles if profile.status == TenantProfile.Status.ACTIVE]
        total_units = Unit.objects.filter(organization=org).count()
        occupied_units = len({profile.unit_id for profile in active_profiles if profile.unit_id})
        occupancy_rate = round((occupied_units / total_units) * 100, 2) if total_units else 0.0

        moved_out_90_days = sum(
            1
            for profile in profiles
            if profile.move_out_date and profile.move_out_date >= today - timedelta(days=90)
        )
        churn_rate = round((moved_out_90_days / max(len(active_profiles), 1)) * 100, 2) if active_profiles else 0.0

        invoices = list(
            _tenant_invoices_queryset(org)
            .select_related("customer", "property")
            .prefetch_related("payments")
        )
        payments = list(
            InvoicePayment.objects.filter(invoice__in=invoices)
            .select_related("invoice", "invoice__customer", "invoice__property")
            .order_by("payment_date", "id")
        )
        collection_months = []
        default_trend = []
        for month_start in month_starts:
            if month_start.month == 12:
                month_end = month_start.replace(year=month_start.year + 1, month=1)
            else:
                month_end = month_start.replace(month=month_start.month + 1)
            month_total = sum((payment.amount for payment in payments if month_start <= payment.payment_date < month_end), ZERO_DECIMAL)
            month_overdue = sum(
                (_invoice_balance(invoice) for invoice in invoices if invoice.status == Invoice.Status.OVERDUE and month_start <= invoice.due_date < month_end),
                ZERO_DECIMAL,
            )
            collection_months.append({"label": _month_label(month_start), "total": f"{month_total:.2f}"})
            default_trend.append({"label": _month_label(month_start), "overdue_total": f"{month_overdue:.2f}"})

        revenue_by_tenant = {}
        for payment in payments:
            revenue_by_tenant[payment.invoice.customer.name] = revenue_by_tenant.get(payment.invoice.customer.name, ZERO_DECIMAL) + payment.amount
        revenue_by_property = {}
        for payment in payments:
            property_name = payment.invoice.property.name if payment.invoice.property_id and payment.invoice.property else "Unassigned"
            revenue_by_property[property_name] = revenue_by_property.get(property_name, ZERO_DECIMAL) + payment.amount

        lease_forecast = []
        for month_start in [current_month_start] + [_add_months(current_month_start, index) for index in range(1, 6)]:
            if month_start.month == 12:
                month_end = month_start.replace(year=month_start.year + 1, month=1)
            else:
                month_end = month_start.replace(month=month_start.month + 1)
            lease_forecast.append(
                {
                    "label": _month_label(month_start),
                    "count": sum(1 for profile in active_profiles if profile.lease_end_date and month_start <= profile.lease_end_date < month_end),
                }
            )

        return Response(
            {
                "generated_at": timezone.now().isoformat(),
                "occupancy": {
                    "occupied_units": occupied_units,
                    "total_units": total_units,
                    "rate": occupancy_rate,
                },
                "tenant_churn": {
                    "moved_out_90_days": moved_out_90_days,
                    "active_tenants": len(active_profiles),
                    "rate": churn_rate,
                },
                "revenue_per_tenant": [
                    {"tenant_name": name, "total_collected": f"{amount:.2f}"}
                    for name, amount in sorted(revenue_by_tenant.items(), key=lambda item: (-item[1], item[0]))[:10]
                ],
                "revenue_per_property": [
                    {"property_name": name, "total_collected": f"{amount:.2f}"}
                    for name, amount in sorted(revenue_by_property.items(), key=lambda item: (-item[1], item[0]))[:10]
                ],
                "payment_default_trend": default_trend,
                "collection_trend": collection_months,
                "lease_expiry_forecast": lease_forecast,
            }
        )


class TenantPaymentsRecordView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "tenants.all"
    rbac_action = "create"

    def post(self, request):
        org = _resolve_user_org(request)
        if org is None:
            return Response({"detail": "Organization context required."}, status=400)
        invoice_id = request.data.get("invoice")
        amount = request.data.get("amount")
        payment_date = request.data.get("payment_date")
        payment_method = request.data.get("payment_method")
        if not invoice_id or not amount or not payment_date or not payment_method:
            return Response({"detail": "invoice, amount, payment_date, and payment_method are required."}, status=400)
        try:
            invoice = _tenant_invoices_queryset(org).select_related("customer", "property").get(pk=invoice_id)
        except Invoice.DoesNotExist:
            return Response({"detail": "Invoice not found."}, status=404)
        try:
            payment_date_value = date.fromisoformat(str(payment_date))
        except ValueError:
            return Response({"detail": "payment_date must be a valid YYYY-MM-DD value."}, status=400)
        try:
            amount_value = Decimal(str(amount))
        except Exception:
            return Response({"detail": "amount must be a valid number."}, status=400)
        payment = InvoicePayment.objects.create(
            invoice=invoice,
            amount=amount_value,
            payment_date=payment_date_value,
            payment_method=payment_method,
            reference_number=request.data.get("reference_number", ""),
            notes=request.data.get("notes", ""),
        )
        summary = run_tenant_operations_automation(org, scopes={"payments", "communications", "documents"})
        return Response(
            {
                "detail": f"Payment recorded for {invoice.invoice_number}.",
                "payment": _simple_payment_payload(payment),
                "workflow": summary,
            },
            status=status.HTTP_201_CREATED,
        )

    def get(self, request):
        org = _resolve_user_org(request)
        if org is None:
            return Response({"detail": "Organization context required."}, status=400)
        payments = list(
            InvoicePayment.objects.filter(invoice__in=_tenant_invoices_queryset(org))
            .select_related("invoice", "invoice__customer")
            .order_by("-payment_date", "-id")
        )
        return Response({"results": [_simple_payment_payload(payment) for payment in payments[:200]]})


class TenantBillingInvoiceListView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "tenants.all"
    rbac_action = "view"

    def get(self, request):
        org = _resolve_user_org(request)
        if org is None:
            return Response({"detail": "Organization context required."}, status=400)
        invoices = list(
            _tenant_invoices_queryset(org)
            .select_related("customer", "property")
            .prefetch_related("payments")
            .order_by("-issue_date", "-id")
        )
        return Response({"results": [_simple_invoice_payload(invoice) for invoice in invoices[:200]]})


class TenantServiceRequestListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "tenants.all"

    def get(self, request):
        org = _resolve_user_org(request)
        if org is None:
            return Response({"detail": "Organization context required."}, status=400)
        queryset = _service_request_queryset(org).select_related(
            "property",
            "facility",
            "facility_space",
            "facility_space__unit",
            "unit",
            "requester",
            "assigned_agent",
            "work_order",
        ).order_by("-created_at")
        return Response(FacilityServiceRequestListSerializer(queryset[:200], many=True, context={"request": request}).data)

    def post(self, request):
        org = _resolve_user_org(request)
        if org is None:
            return Response({"detail": "Organization context required."}, status=400)
        serializer = FacilityServiceRequestWriteSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        service_request = serializer.save(organization=org, requester=request.user if request.user.is_authenticated else None)
        from apps.facility_management.service_request_workflows import (
            ensure_service_request_defaults,
            ensure_service_request_work_order,
        )
        from apps.tenants.workflows import sync_tenant_service_request_resolution_automation

        ensure_service_request_defaults(service_request)
        ensure_service_request_work_order(service_request)
        sync_tenant_service_request_resolution_automation(service_request)
        service_request.refresh_from_db()
        return Response(
            FacilityServiceRequestListSerializer(service_request, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class TenantServiceRequestFeedbackView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "tenants.all"
    rbac_action = "edit"

    def post(self, request, request_id: int):
        org = _resolve_user_org(request)
        if org is None:
            return Response({"detail": "Organization context required."}, status=400)
        service_request = _service_request_queryset(org).filter(pk=request_id).first()
        if service_request is None:
            return Response({"detail": "Service request not found."}, status=404)
        rating = request.data.get("feedback_rating")
        if rating not in {1, 2, 3, 4, 5, "1", "2", "3", "4", "5"}:
            return Response({"detail": "feedback_rating must be between 1 and 5."}, status=400)
        service_request.feedback_rating = int(rating)
        service_request.feedback_comment = request.data.get("feedback_comment", "")
        service_request.feedback_submitted_at = timezone.now()
        service_request.save(update_fields=["feedback_rating", "feedback_comment", "feedback_submitted_at", "updated_at"])
        return Response(FacilityServiceRequestListSerializer(service_request, context={"request": request}).data)


class TenantCommunicationLogListView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "tenants.all"
    rbac_action = "view"

    def get(self, request):
        org = _resolve_user_org(request)
        if org is None:
            return Response({"detail": "Organization context required."}, status=400)
        logs = TenantCommunicationLog.objects.filter(organization=org).select_related("author", "tenant_profile").order_by("-happened_at", "-id")
        return Response(TenantCommunicationLogSerializer(logs[:200], many=True).data)


class TenantScopedModelViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "tenants.all"
    lookup_value_regex = r"\d+"
    http_method_names = ["get", "post", "put", "patch", "head", "options"]
    pagination_class = None
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "create",
        "update": "edit",
        "partial_update": "edit",
    }
    read_serializer_class = None
    write_serializer_class = None

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"} and self.write_serializer_class is not None:
            return self.write_serializer_class
        return self.read_serializer_class


class LeaseAgreementViewSet(TenantScopedModelViewSet):
    queryset = LeaseAgreement.objects.all()
    read_serializer_class = LeaseAgreementSerializer
    write_serializer_class = LeaseAgreementWriteSerializer

    def get_queryset(self):
        return super().get_queryset().select_related("tenant_profile", "property", "unit", "facility", "facility_space", "facility_space__unit")


class OccupancyRecordViewSet(TenantScopedModelViewSet):
    queryset = OccupancyRecord.objects.all()
    read_serializer_class = OccupancyRecordSerializer
    write_serializer_class = OccupancyRecordWriteSerializer

    def get_queryset(self):
        return super().get_queryset().select_related("tenant_profile", "lease_agreement", "property", "unit", "facility", "facility_space", "facility_space__unit")


class LeaseRenewalRequestViewSet(TenantScopedModelViewSet):
    queryset = LeaseRenewalRequest.objects.all()
    read_serializer_class = LeaseRenewalRequestSerializer
    write_serializer_class = LeaseRenewalRequestWriteSerializer

    def get_queryset(self):
        return super().get_queryset().select_related("tenant_profile", "lease_agreement", "requested_by", "decided_by")

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        renewal = self.get_object()
        renewal.status = LeaseRenewalRequest.Status.APPROVED
        renewal.decided_by = request.user
        renewal.decided_at = timezone.now()
        renewal.save(update_fields=["status", "decided_by", "decided_at", "updated_at"])
        workflow = run_tenant_operations_automation(renewal.organization, scopes={"lease_occupancy"})
        return Response(
            {
                "renewal": LeaseRenewalRequestSerializer(renewal, context={"request": request}).data,
                "workflow": workflow,
            }
        )


class LeaseTerminationRequestViewSet(TenantScopedModelViewSet):
    queryset = LeaseTerminationRequest.objects.all()
    read_serializer_class = LeaseTerminationRequestSerializer
    write_serializer_class = LeaseTerminationRequestWriteSerializer

    def get_queryset(self):
        return super().get_queryset().select_related("tenant_profile", "lease_agreement", "requested_by", "approved_by")

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        termination = self.get_object()
        termination.status = LeaseTerminationRequest.Status.APPROVED
        termination.approved_by = request.user
        termination.approved_at = timezone.now()
        termination.effective_date = termination.effective_date or termination.requested_move_out_date
        termination.save(update_fields=["status", "approved_by", "approved_at", "effective_date", "updated_at"])
        lease = termination.lease_agreement
        lease.status = LeaseAgreement.Status.TERMINATION_PENDING
        lease.terminated_on = termination.effective_date
        lease.save(update_fields=["status", "terminated_on", "updated_at"])
        summary = run_tenant_operations_automation(lease.organization, scopes={"lease_occupancy", "inspections"})
        return Response(
            {
                "termination": LeaseTerminationRequestSerializer(termination, context={"request": request}).data,
                "workflow": summary,
            }
        )


class RecurringChargeRuleViewSet(TenantScopedModelViewSet):
    queryset = RecurringChargeRule.objects.all()
    read_serializer_class = RecurringChargeRuleSerializer
    write_serializer_class = RecurringChargeRuleWriteSerializer

    def get_queryset(self):
        return super().get_queryset().select_related("tenant_profile", "lease_agreement", "property", "unit", "facility", "facility_space")


class TenantBroadcastViewSet(TenantScopedModelViewSet):
    queryset = TenantBroadcast.objects.all()
    read_serializer_class = TenantBroadcastSerializer
    write_serializer_class = TenantBroadcastWriteSerializer

    def get_queryset(self):
        return super().get_queryset().select_related("created_by", "property", "facility")

    def perform_create(self, serializer):
        serializer.save(organization=_resolve_user_org(self.request), created_by=self.request.user)


class TenantDocumentRecordViewSet(TenantScopedModelViewSet):
    queryset = TenantDocumentRecord.objects.all()
    read_serializer_class = TenantDocumentRecordSerializer
    write_serializer_class = TenantDocumentRecordWriteSerializer

    def get_queryset(self):
        return super().get_queryset().select_related("tenant_profile", "lease_agreement", "inspection", "invoice", "payment")


class TenantInspectionViewSet(TenantScopedModelViewSet):
    queryset = TenantInspection.objects.all()
    read_serializer_class = TenantInspectionSerializer
    write_serializer_class = TenantInspectionWriteSerializer

    def get_queryset(self):
        return super().get_queryset().select_related("tenant_profile", "lease_agreement", "inspector", "property", "unit", "facility", "facility_space")


class TenantComplaintViewSet(TenantScopedModelViewSet):
    queryset = TenantComplaint.objects.all()
    read_serializer_class = TenantComplaintSerializer
    write_serializer_class = TenantComplaintWriteSerializer

    def get_queryset(self):
        return super().get_queryset().select_related("tenant_profile", "property", "unit", "facility", "facility_space", "service_request", "assigned_to")
