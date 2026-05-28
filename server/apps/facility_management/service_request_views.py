from __future__ import annotations

from decimal import Decimal

from django.db.models import Q
from django.utils import timezone
from django_filters import rest_framework as filters
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.mixins import OrgScopedMixin
from apps.finance.models import Invoice, InvoicePayment
from apps.properties.models import ServiceRequest
from apps.settings.permissions import HasRolePermission
from apps.support_desk.models import SupportTicket

from .service_request_serializers import (
    FacilityBillingTicketDetailSerializer,
    FacilityBillingTicketListSerializer,
    FacilityBillingTicketWriteSerializer,
    FacilityInvoiceListSerializer,
    FacilityInvoicePaymentWriteSerializer,
    FacilityServiceRequestDetailSerializer,
    FacilityServiceRequestEscalateSerializer,
    FacilityServiceRequestFeedbackSerializer,
    FacilityServiceRequestListSerializer,
    FacilityServiceRequestWriteSerializer,
)
from .service_request_workflows import (
    ACTIVE_SERVICE_REQUEST_STATUSES,
    ensure_service_request_defaults,
    ensure_service_request_work_order,
    resolve_billing_tickets_for_invoice,
    run_service_request_helpdesk_automation,
    service_request_sla_status_for,
    sync_invoice_collection_status,
)


def _resolve_user_org(request):
    org = getattr(request, "organization", None)
    if org is not None:
        return org
    profile = getattr(request.user, "profile", None)
    return getattr(profile, "organization", None)


def _facility_property_filter() -> Q:
    return Q(property__facility_registry__isnull=False) | Q(facility__isnull=False) | Q(facility_space__isnull=False)


class FacilityServiceRequestFilter(filters.FilterSet):
    requested_after = filters.DateFilter(field_name="requested_date", lookup_expr="gte")
    requested_before = filters.DateFilter(field_name="requested_date", lookup_expr="lte")
    sla_due_before = filters.IsoDateTimeFilter(field_name="sla_due_at", lookup_expr="lte")
    sla_due_after = filters.IsoDateTimeFilter(field_name="sla_due_at", lookup_expr="gte")

    class Meta:
        model = ServiceRequest
        fields = [
            "property",
            "facility",
            "facility_space",
            "unit",
            "category",
            "priority",
            "status",
            "source_channel",
            "requester",
            "assigned_agent",
        ]


class FacilityBillingTicketFilter(filters.FilterSet):
    created_after = filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_before = filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = SupportTicket
        fields = [
            "invoice",
            "customer",
            "assigned_agent",
            "priority",
            "status",
        ]


class FacilityServiceRequestsOverviewView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    rbac_action = "view"

    def get(self, request):
        org = _resolve_user_org(request)
        if org is None:
            return Response({"detail": "Organization context required."}, status=400)
        today = timezone.localdate()
        now = timezone.now()

        requests = list(
            ServiceRequest.objects.filter(organization=org)
            .filter(_facility_property_filter())
            .select_related(
                "property",
                "facility",
                "facility_space",
                "facility_space__unit",
                "unit",
                "requester",
                "assigned_agent",
                "work_order",
            )
        )
        billing_tickets = list(
            SupportTicket.objects.filter(
                organization=org,
                category=SupportTicket.Category.BILLING,
                invoice__isnull=False,
            )
            .select_related("invoice", "invoice__property", "customer", "assigned_agent", "requester")
            .order_by("sla_deadline", "-created_at")
        )
        invoices = list(
            Invoice.objects.filter(organization=org, property__facility_registry__isnull=False)
            .select_related("customer", "property")
            .order_by("due_date", "-created_at")
        )

        active_requests = [item for item in requests if item.status in ACTIVE_SERVICE_REQUEST_STATUSES]
        escalated_requests = [item for item in requests if item.status == ServiceRequest.Status.ESCALATED]
        at_risk_requests = [
            item for item in active_requests if service_request_sla_status_for(item) in {"at_risk", "breached"}
        ]
        feedback_values = [item.feedback_rating for item in requests if item.feedback_rating is not None]
        avg_feedback = round(sum(feedback_values) / len(feedback_values), 2) if feedback_values else None

        open_billing_tickets = [
            ticket for ticket in billing_tickets if ticket.status not in {SupportTicket.Status.RESOLVED, SupportTicket.Status.CLOSED}
        ]
        overdue_invoices = [
            invoice for invoice in invoices if invoice.status == Invoice.Status.OVERDUE or (
                invoice.status not in {Invoice.Status.PAID, Invoice.Status.CANCELLED}
                and invoice.due_date < today
            )
        ]
        outstanding_balance = sum((invoice.balance_due for invoice in invoices), Decimal("0.00"))

        payload = {
            "generated_at": now.isoformat(),
            "kpis": {
                "open_requests": len(active_requests),
                "escalated_requests": len(escalated_requests),
                "sla_at_risk": len(at_risk_requests),
                "avg_feedback_rating": avg_feedback,
                "open_billing_tickets": len(open_billing_tickets),
                "overdue_invoices": len(overdue_invoices),
                "outstanding_balance": f"{outstanding_balance:.2f}",
            },
            "service_request_watchlist": FacilityServiceRequestListSerializer(
                sorted(
                    active_requests,
                    key=lambda item: (
                        item.status != ServiceRequest.Status.ESCALATED,
                        item.sla_due_at or item.created_at,
                    ),
                )[:8],
                many=True,
                context={"request": request},
            ).data,
            "billing_watchlist": FacilityBillingTicketListSerializer(
                open_billing_tickets[:8],
                many=True,
                context={"request": request},
            ).data,
            "overdue_invoice_watchlist": FacilityInvoiceListSerializer(
                overdue_invoices[:8],
                many=True,
                context={"request": request},
            ).data,
        }
        return Response(payload)


class FacilityServiceRequestsLookupsView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    rbac_action = "view"

    def get(self, request):
        org = _resolve_user_org(request)
        if org is None:
            return Response({"detail": "Organization context required."}, status=400)

        User = request.user.__class__
        users = User.objects.filter(profile__organization=org, is_active=True).select_related("profile").order_by(
            "first_name",
            "last_name",
            "email",
        )
        from apps.finance.models import Customer

        from .models import Facility, FacilityUnitSpace

        facilities = Facility.objects.filter(organization=org).select_related("property").order_by("facility_code")
        spaces = FacilityUnitSpace.objects.filter(organization=org).select_related(
            "facility",
            "zone",
            "zone__floor",
            "unit",
            "unit__property",
        ).order_by("facility__facility_code", "zone__floor__floor_number", "zone__name", "unit__unit_number")
        customers = Customer.objects.filter(organization=org).order_by("name")
        invoices = Invoice.objects.filter(
            organization=org,
            property__facility_registry__isnull=False,
        ).select_related("customer", "property").order_by("due_date", "-created_at")

        payload = {
            "users": [
                {
                    "id": user.id,
                    "label": user.get_full_name().strip() or user.email or user.username,
                    "email": user.email or "",
                }
                for user in users[:200]
            ],
            "facilities": [
                {
                    "id": facility.id,
                    "facility_code": facility.facility_code,
                    "property_name": facility.property.name,
                }
                for facility in facilities[:200]
            ],
            "spaces": [
                {
                    "id": space.id,
                    "facility": space.facility_id,
                    "facility_code": space.facility.facility_code,
                    "zone_code": space.zone.zone_code,
                    "zone_name": space.zone.name,
                    "unit_number": space.unit.unit_number,
                    "space_label": space.space_label,
                    "property_name": space.unit.property.name,
                }
                for space in spaces[:500]
            ],
            "customers": [
                {
                    "id": customer.id,
                    "label": customer.name,
                    "email": customer.email or "",
                    "phone": customer.phone or "",
                }
                for customer in customers[:200]
            ],
            "invoices": FacilityInvoiceListSerializer(invoices[:300], many=True, context={"request": request}).data,
        }
        return Response(payload)


class FacilityServiceRequestViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "create",
        "update": "edit",
        "partial_update": "edit",
        "destroy": "delete",
        "record_feedback": "edit",
        "escalate": "edit",
    }
    filterset_class = FacilityServiceRequestFilter
    search_fields = ["title", "description", "requested_by", "assigned_to"]
    ordering_fields = ["created_at", "requested_date", "priority", "status", "sla_due_at"]
    ordering = ["-created_at"]
    queryset = ServiceRequest.objects.all()

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(_facility_property_filter())
            .select_related(
                "property",
                "facility",
                "facility_space",
                "facility_space__unit",
                "unit",
                "requester",
                "assigned_agent",
                "work_order",
            )
        )

    def get_serializer_class(self):
        if self.action == "list":
            return FacilityServiceRequestListSerializer
        if self.action == "retrieve":
            return FacilityServiceRequestDetailSerializer
        if self.action in {"create", "update", "partial_update"}:
            return FacilityServiceRequestWriteSerializer
        return FacilityServiceRequestDetailSerializer

    def perform_create(self, serializer):
        service_request = serializer.save(organization=self._resolve_request_org())
        ensure_service_request_defaults(service_request)
        ensure_service_request_work_order(service_request)

    def perform_update(self, serializer):
        service_request = serializer.save()
        ensure_service_request_defaults(service_request)
        ensure_service_request_work_order(service_request)

    @action(detail=True, methods=["post"], url_path="feedback")
    def record_feedback(self, request, pk=None):
        service_request = self.get_object()
        serializer = FacilityServiceRequestFeedbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if service_request.status not in {ServiceRequest.Status.RESOLVED, ServiceRequest.Status.CLOSED}:
            return Response(
                {"detail": "Feedback can only be recorded after the request is resolved or closed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        service_request.feedback_rating = serializer.validated_data["feedback_rating"]
        service_request.feedback_comment = serializer.validated_data["feedback_comment"]
        service_request.feedback_submitted_at = timezone.now()
        service_request.save(update_fields=["feedback_rating", "feedback_comment", "feedback_submitted_at", "updated_at"])
        return Response(FacilityServiceRequestDetailSerializer(service_request, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="escalate")
    def escalate(self, request, pk=None):
        service_request = self.get_object()
        serializer = FacilityServiceRequestEscalateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        note = serializer.validated_data["note"].strip()
        if note:
            combined = service_request.notes.strip()
            service_request.notes = f"{combined}\nEscalation note: {note}".strip()
        service_request.status = ServiceRequest.Status.ESCALATED
        service_request.escalated_at = timezone.now()
        service_request.save(update_fields=["status", "escalated_at", "notes", "updated_at"])
        ensure_service_request_defaults(service_request)
        ensure_service_request_work_order(service_request)
        return Response(FacilityServiceRequestDetailSerializer(service_request, context={"request": request}).data)


class FacilityBillingTicketViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "create",
        "update": "edit",
        "partial_update": "edit",
        "destroy": "delete",
    }
    filterset_class = FacilityBillingTicketFilter
    search_fields = ["ticket_id", "subject", "description", "customer__name", "invoice__invoice_number"]
    ordering_fields = ["created_at", "updated_at", "priority", "status", "sla_deadline"]
    ordering = ["sla_deadline", "-created_at"]
    queryset = SupportTicket.objects.all()

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(category=SupportTicket.Category.BILLING, invoice__isnull=False, invoice__property__facility_registry__isnull=False)
            .select_related("invoice", "invoice__property", "customer", "requester", "assigned_agent")
        )

    def get_serializer_class(self):
        if self.action == "list":
            return FacilityBillingTicketListSerializer
        if self.action == "retrieve":
            return FacilityBillingTicketDetailSerializer
        if self.action in {"create", "update", "partial_update"}:
            return FacilityBillingTicketWriteSerializer
        return FacilityBillingTicketDetailSerializer

    def _run_ticket_automation_for_facility(self, ticket: SupportTicket, *, previous_status: str | None = None):
        from apps.support_desk.models import SupportAutomationRule
        from apps.support_desk.views import _evaluate_ticket_sla, _notify_user, _run_ticket_automation

        _evaluate_ticket_sla(ticket)
        if previous_status is None and ticket.assigned_agent_id:
            _notify_user(
                recipient=ticket.assigned_agent,
                event_key="support_ticket_assigned",
                title=f"Assigned ticket {ticket.ticket_id}",
                message=f"You have been assigned support ticket {ticket.ticket_id}: {ticket.subject}",
                template_context={
                    "ticket_id": ticket.ticket_id,
                    "ticket_subject": ticket.subject,
                    "requester_name": ticket.requester.get_full_name().strip()
                    if ticket.requester_id
                    else "",
                    "action_url": "/support-desk/tickets",
                },
                link_url="/support-desk/tickets",
            )
            _run_ticket_automation(
                ticket,
                trigger_type=SupportAutomationRule.TriggerType.TICKET_CREATED,
                actor=self.request.user,
                trigger_context={"previous_status": ticket.status},
            )
            return

        _run_ticket_automation(
            ticket,
            trigger_type=SupportAutomationRule.TriggerType.TICKET_UPDATED,
            actor=self.request.user,
            trigger_context={"previous_status": previous_status or ticket.status},
        )
        if previous_status is not None and previous_status != ticket.status:
            _run_ticket_automation(
                ticket,
                trigger_type=SupportAutomationRule.TriggerType.STATUS_CHANGED,
                actor=self.request.user,
                trigger_context={"previous_status": previous_status},
            )

    def perform_create(self, serializer):
        ticket = serializer.save(organization=self._resolve_request_org(), category=SupportTicket.Category.BILLING)
        self._run_ticket_automation_for_facility(ticket)

    def perform_update(self, serializer):
        previous_status = serializer.instance.status
        ticket = serializer.save()
        self._run_ticket_automation_for_facility(ticket, previous_status=previous_status)


class FacilityInvoiceViewSet(OrgScopedMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
        "record_payment": "edit",
    }
    serializer_class = FacilityInvoiceListSerializer
    ordering_fields = ["invoice_number", "due_date", "created_at", "total_amount", "status"]
    ordering = ["due_date", "-created_at"]
    queryset = Invoice.objects.all()

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(property__facility_registry__isnull=False)
            .select_related("customer", "property")
        )

    @action(detail=True, methods=["post"], url_path="record-payment")
    def record_payment(self, request, pk=None):
        invoice = self.get_object()
        serializer = FacilityInvoicePaymentWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if invoice.status in {Invoice.Status.PAID, Invoice.Status.CANCELLED}:
            return Response({"detail": "Payments cannot be recorded for paid or cancelled invoices."}, status=status.HTTP_400_BAD_REQUEST)

        InvoicePayment.objects.create(invoice=invoice, **serializer.validated_data)
        invoice.refresh_from_db()
        sync_invoice_collection_status(invoice)
        resolved_count = resolve_billing_tickets_for_invoice(
            invoice,
            resolution_note=f"Auto-resolved after payment for invoice {invoice.invoice_number}.",
        )
        invoice.refresh_from_db()
        payload = {
            "detail": "Payment recorded successfully.",
            "billing_tickets_resolved": resolved_count,
            "invoice": FacilityInvoiceListSerializer(invoice, context={"request": request}).data,
        }
        return Response(payload, status=status.HTTP_201_CREATED)


class FacilityServiceRequestWorkflowView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    rbac_action = "edit"

    def post(self, request):
        org = _resolve_user_org(request)
        if org is None:
            return Response({"detail": "Organization context required."}, status=400)
        return Response(run_service_request_helpdesk_automation(org), status=status.HTTP_200_OK)
