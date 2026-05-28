from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db.models import Q, Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.crm.models import CommunicationLog
from apps.documents.models import Document, DocumentApproval, DocumentExpiry, DocumentVersion
from apps.documents.serializers import (
    DocumentApprovalSerializer,
    DocumentExpirySerializer,
    DocumentVersionSerializer,
)
from apps.finance.models import (
    Bill,
    BillPayment,
    CapitalContribution,
    DistributionLineItem,
    Invoice,
    InvoicePayment,
    PaymentInstallment,
    PaymentPlan,
    ProjectInvestor,
    SPVEntity,
)
from apps.finance.serializers import (
    BillListSerializer,
    DistributionLineItemSerializer,
    InvoiceListSerializer,
    PaymentInstallmentSerializer,
    PaymentPlanListSerializer,
    ProjectInvestorSerializer,
)
from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer
from apps.procurement.models import PurchaseOrder, Vendor
from apps.procurement.serializers import POListSerializer
from apps.projects.models import Project, ProjectFieldEscalation, ProjectRiskRegisterEntry, ProjectVariationOrder
from apps.projects.serializers import ProjectFieldEscalationSerializer, ProjectRiskRegisterListSerializer

from .models import (
    PartnerEntitlement,
    PartnerOnboardingApproval,
    PartnerOnboardingCase,
    PartnerPortalLegalAcceptance,
    PortalRole,
)
from .portal_access import resolve_partner_portal_context
from .portal_serializers import PortalCommunicationSerializer, PortalDocumentVaultSerializer
from .serializers import PartnerEntitlementSerializer, PartnerOnboardingCaseListSerializer


class PartnerPortalPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


def _decimal_text(value) -> str:
    if value is None:
        return "0.00"
    return f"{Decimal(value):.2f}"


def _portal_context(request):
    context = getattr(request, "partner_portal_context", None)
    if context is None:
        context = resolve_partner_portal_context(request.user)
        request.partner_portal_context = context
    return context


class IsPartnerPortalUser(BasePermission):
    message = "No active partner portal entitlement found for this user."

    def has_permission(self, request, view):
        context = _portal_context(request)
        if not (context.is_partner_user or context.is_preview_mode):
            self.message = "No active partner portal entitlement found for this user."
            return False

        accepted = PartnerPortalLegalAcceptance.objects.filter(user=request.user).exists()
        if not accepted:
            self.message = "Legal agreement acceptance is required before portal access."
            return False
        return True


def _primary_portal_role(context) -> str | None:
    precedence = {
        PortalRole.LEAD_INVESTOR: 0,
        PortalRole.INVESTOR: 1,
        PortalRole.CONTRACTOR: 2,
        PortalRole.CLIENT: 3,
    }
    if not context.portal_roles:
        return None
    return sorted(context.portal_roles, key=lambda role: precedence.get(role, 99))[0]


def _scoped_projects(context):
    qs = Project.objects.all()
    if context.project_ids:
        return qs.filter(id__in=context.project_ids)
    if context.is_preview_mode:
        return qs
    return qs.none()


def _scoped_documents(context):
    queryset = Document.objects.select_related(
        "project",
        "document_type",
        "phase",
        "land",
        "unit",
        "client",
        "vendor",
        "business_unit_division",
        "business_unit_department",
        "current_version",
    )

    filters = Q()
    if context.project_ids:
        filters |= Q(project_id__in=context.project_ids)
    if context.customer_ids:
        filters |= Q(client_id__in=context.customer_ids)
    if context.vendor_ids:
        filters |= Q(vendor_id__in=context.vendor_ids)

    if filters.children:
        queryset = queryset.filter(filters).distinct()
    elif not context.is_preview_mode:
        return queryset.none()

    if not context.is_preview_mode:
        queryset = queryset.filter(confidentiality_level__in=context.allowed_confidentiality_levels)

    return queryset


def _scoped_communications(context):
    queryset = CommunicationLog.objects.select_related("lead", "performed_by").order_by("-communicated_at")
    if context.organization_id:
        queryset = queryset.filter(organization_id=context.organization_id)

    filters = Q()
    if context.lead_ids:
        filters |= Q(lead_id__in=context.lead_ids)
    for email in context.contact_emails:
        filters |= Q(to_address__icontains=email)
        filters |= Q(from_address__icontains=email)

    if filters.children:
        return queryset.filter(filters).distinct()
    if context.is_preview_mode:
        return queryset
    return queryset.none()


def _build_client_financial_summary(*, context, today):
    plan_qs = PaymentPlan.objects.filter(customer_id__in=context.customer_ids).select_related("project")
    if context.project_ids:
        plan_qs = plan_qs.filter(Q(project_id__in=context.project_ids) | Q(project_id__isnull=True))

    installment_qs = PaymentInstallment.objects.filter(payment_plan__in=plan_qs).select_related("payment_plan")
    open_installments = installment_qs.exclude(
        status__in=[
            PaymentInstallment.Status.PAID,
            PaymentInstallment.Status.WAIVED,
            PaymentInstallment.Status.CANCELLED,
        ]
    )

    outstanding_installment_total = sum(
        (row.amount or Decimal("0.00")) - (row.paid_amount or Decimal("0.00"))
        for row in open_installments
    )
    overdue_count = open_installments.filter(due_date__lt=today).count()
    due_30_count = open_installments.filter(due_date__gte=today, due_date__lte=today + timedelta(days=30)).count()

    invoice_qs = Invoice.objects.filter(customer_id__in=context.customer_ids)
    invoice_total = invoice_qs.aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
    invoice_paid_total = (
        InvoicePayment.objects.filter(invoice__in=invoice_qs).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )
    invoice_balance = invoice_total - invoice_paid_total

    variation_pending = ProjectVariationOrder.objects.filter(
        project_id__in=context.project_ids,
        status__in=[
            ProjectVariationOrder.Status.SUBMITTED,
            ProjectVariationOrder.Status.UNDER_REVIEW,
        ],
    ).count()

    return {
        "summary": {
            "outstanding_installments": _decimal_text(outstanding_installment_total),
            "overdue_installments_count": overdue_count,
            "due_next_30_days_count": due_30_count,
            "invoice_balance_due": _decimal_text(invoice_balance),
            "pending_variation_orders": variation_pending,
        },
        "payment_plans": PaymentPlanListSerializer(plan_qs.order_by("-created_at")[:20], many=True).data,
        "installments": PaymentInstallmentSerializer(open_installments.order_by("due_date")[:30], many=True).data,
        "invoices": InvoiceListSerializer(invoice_qs.order_by("-due_date")[:20], many=True).data,
    }


def _build_contractor_financial_summary(*, context):
    po_qs = PurchaseOrder.objects.filter(vendor_id__in=context.vendor_ids).select_related("project", "vendor")
    if context.project_ids:
        po_qs = po_qs.filter(Q(project_id__in=context.project_ids) | Q(project_id__isnull=True))

    open_po_count = po_qs.exclude(
        status__in=[PurchaseOrder.Status.RECEIVED, PurchaseOrder.Status.CANCELLED]
    ).count()
    delivery_pending_count = po_qs.filter(
        status__in=[
            PurchaseOrder.Status.APPROVED,
            PurchaseOrder.Status.ISSUED,
            PurchaseOrder.Status.PARTIALLY_RECEIVED,
        ]
    ).count()

    bill_qs = Bill.objects.filter(vendor_id__in=context.vendor_ids)
    if context.project_ids:
        bill_qs = bill_qs.filter(Q(purchase_order__project_id__in=context.project_ids) | Q(purchase_order__isnull=True))

    payable_total = bill_qs.aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
    paid_total = BillPayment.objects.filter(bill__in=bill_qs).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    payable_balance = payable_total - paid_total

    return {
        "summary": {
            "open_purchase_orders": open_po_count,
            "delivery_pending_count": delivery_pending_count,
            "payable_balance_due": _decimal_text(payable_balance),
        },
        "purchase_orders": POListSerializer(po_qs.order_by("-issue_date")[:20], many=True).data,
        "bills": BillListSerializer(bill_qs.order_by("-due_date")[:20], many=True).data,
    }


def _build_investor_financial_summary(*, context):
    position_qs = ProjectInvestor.objects.filter(investor_id__in=context.investor_ids).select_related("project", "investor")
    if context.project_ids:
        position_qs = position_qs.filter(project_id__in=context.project_ids)

    contribution_qs = CapitalContribution.objects.filter(project_investor__in=position_qs).select_related(
        "project_investor",
        "project_investor__investor",
    )
    distribution_qs = DistributionLineItem.objects.filter(project_investor__in=position_qs).select_related(
        "distribution",
        "project_investor",
        "project_investor__investor",
    )

    capital_deployed = contribution_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    total_distributed = distribution_qs.aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")

    contribution_rows = [
        {
            "id": row.id,
            "investor_name": row.project_investor.investor.name,
            "project_name": row.project_investor.project.name,
            "amount": _decimal_text(row.amount),
            "contribution_date": row.contribution_date,
            "payment_method": row.payment_method,
            "reference_number": row.reference_number,
        }
        for row in contribution_qs.order_by("-contribution_date")[:30]
    ]

    return {
        "summary": {
            "active_positions": position_qs.count(),
            "invested_projects": position_qs.values("project_id").distinct().count(),
            "capital_deployed": _decimal_text(capital_deployed),
            "distributions_received": _decimal_text(total_distributed),
            "net_cash_position": _decimal_text(total_distributed - capital_deployed),
        },
        "positions": ProjectInvestorSerializer(position_qs.order_by("project__name", "investor__name")[:30], many=True).data,
        "contributions": contribution_rows,
        "distributions": DistributionLineItemSerializer(
            distribution_qs.order_by("-distribution__distribution_date")[:30],
            many=True,
        ).data,
    }


class PartnerPortalContextView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        context = _portal_context(request)
        legal = PartnerPortalLegalAcceptance.objects.filter(user=request.user).first()

        project_rows = list(
            Project.objects.filter(id__in=context.project_ids).values("id", "name").order_by("name")
        )
        spv_rows = list(
            SPVEntity.objects.filter(id__in=context.spv_entity_ids).values("id", "name").order_by("name")
        )
        case_rows = PartnerOnboardingCase.objects.filter(id__in=context.case_ids).order_by("-created_at")
        entitlement_rows = PartnerEntitlement.objects.filter(id__in=context.entitlement_ids).order_by("-created_at")

        return Response(
            {
                "is_partner_user": context.is_partner_user,
                "is_preview_mode": context.is_preview_mode,
                "portal_roles": context.portal_roles,
                "partner_types": context.partner_types,
                "budget_scope": context.budget_scope,
                "permissions": {
                    "can_view_other_investors": context.can_view_other_investors,
                    "can_edit": context.can_edit,
                    "can_approve": context.can_approve,
                    "can_comment": context.can_comment,
                    "can_download_documents": context.can_download_documents,
                },
                "scopes": {
                    "projects": project_rows,
                    "spv_entities": spv_rows,
                    "contract_references": context.contract_references,
                    "investment_vehicle_references": context.investment_vehicle_references,
                    "allowed_confidentiality_levels": context.allowed_confidentiality_levels,
                },
                "linked_record_ids": {
                    "customers": context.customer_ids,
                    "vendors": context.vendor_ids,
                    "investors": context.investor_ids,
                    "leads": context.lead_ids,
                },
                "contact_emails": context.contact_emails,
                "legal": {
                    "accepted": legal is not None,
                    "accepted_at": legal.accepted_at if legal else None,
                    "terms_version": legal.terms_version if legal else "v1",
                    "privacy_version": legal.privacy_version if legal else "v1",
                },
                "cases": PartnerOnboardingCaseListSerializer(case_rows, many=True).data,
                "entitlements": PartnerEntitlementSerializer(entitlement_rows, many=True).data,
            }
        )


class PartnerPortalLegalStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        acceptance = PartnerPortalLegalAcceptance.objects.filter(user=request.user).first()
        return Response(
            {
                "accepted": acceptance is not None,
                "accepted_at": acceptance.accepted_at if acceptance else None,
                "terms_version": acceptance.terms_version if acceptance else "v1",
                "privacy_version": acceptance.privacy_version if acceptance else "v1",
                "requires_acceptance": acceptance is None,
            }
        )


class PartnerPortalLegalAcceptView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        profile = getattr(request.user, "profile", None)
        organization = getattr(profile, "organization", None)
        acceptance = PartnerPortalLegalAcceptance.objects.filter(user=request.user).first()

        if acceptance is None:
            acceptance = PartnerPortalLegalAcceptance.objects.create(
                user=request.user,
                organization=organization,
                terms_version=str(request.data.get("terms_version") or "v1"),
                privacy_version=str(request.data.get("privacy_version") or "v1"),
                ip_address=request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
                or request.META.get("REMOTE_ADDR"),
                user_agent=str(request.META.get("HTTP_USER_AGENT") or "")[:255],
            )
            detail = "Legal agreements accepted successfully."
        else:
            detail = "Legal agreements were already accepted."

        return Response(
            {
                "detail": detail,
                "accepted": True,
                "accepted_at": acceptance.accepted_at,
                "terms_version": acceptance.terms_version,
                "privacy_version": acceptance.privacy_version,
            }
        )


class PartnerPortalDashboardView(APIView):
    permission_classes = [IsAuthenticated, IsPartnerPortalUser]

    def get(self, request):
        context = _portal_context(request)
        today = timezone.localdate()

        project_qs = _scoped_projects(context)
        document_qs = _scoped_documents(context)

        pending_versions_qs = DocumentVersion.objects.filter(
            document__in=document_qs,
            approval_status=DocumentVersion.ApprovalStatus.PENDING,
        ).select_related("document", "uploaded_by")

        expiring_qs = DocumentExpiry.objects.filter(
            document__in=document_qs,
            expiry_date__lte=today + timedelta(days=90),
            expiry_date__gte=today,
        ).select_related("document")

        open_issues_qs = ProjectFieldEscalation.objects.filter(project__in=project_qs).exclude(
            status__in=[ProjectFieldEscalation.Status.RESOLVED, ProjectFieldEscalation.Status.CLOSED]
        )

        primary_role = _primary_portal_role(context)
        role_summary = None
        if primary_role == PortalRole.CLIENT:
            role_summary = _build_client_financial_summary(context=context, today=today)["summary"]
        elif primary_role == PortalRole.CONTRACTOR:
            role_summary = _build_contractor_financial_summary(context=context)["summary"]
        elif primary_role in (PortalRole.INVESTOR, PortalRole.LEAD_INVESTOR):
            role_summary = _build_investor_financial_summary(context=context)["summary"]

        response_payload = {
            "primary_role": primary_role,
            "is_preview_mode": context.is_preview_mode,
            "kpis": [
                {"key": "projects", "label": "Active Projects", "value": project_qs.count()},
                {"key": "documents", "label": "Accessible Documents", "value": document_qs.count()},
                {"key": "pending_approvals", "label": "Pending Sign-offs", "value": pending_versions_qs.count()},
                {"key": "expiring_documents", "label": "Expiring in 90 Days", "value": expiring_qs.count()},
                {"key": "open_issues", "label": "Open Issues", "value": open_issues_qs.count()},
                {
                    "key": "unread_notifications",
                    "label": "Unread Notifications",
                    "value": Notification.objects.filter(recipient=request.user, is_read=False).count(),
                },
            ],
            "role_summary": role_summary or {},
            "recent_documents": PortalDocumentVaultSerializer(document_qs.order_by("-created_at")[:8], many=True).data,
            "upcoming_expiries": DocumentExpirySerializer(expiring_qs.order_by("expiry_date")[:8], many=True).data,
            "pending_signoffs": DocumentVersionSerializer(
                pending_versions_qs.order_by("-uploaded_at")[:8],
                many=True,
            ).data,
        }
        return Response(response_payload)


class PartnerPortalDocumentVaultView(APIView):
    permission_classes = [IsAuthenticated, IsPartnerPortalUser]

    def get(self, request):
        context = _portal_context(request)
        queryset = _scoped_documents(context)

        search_term = (request.query_params.get("q") or "").strip()
        status_value = (request.query_params.get("status") or "").strip()
        project_value = (request.query_params.get("project") or "").strip()
        confidentiality_value = (request.query_params.get("confidentiality") or "").strip()
        ordering = (request.query_params.get("ordering") or "-created_at").strip() or "-created_at"

        if search_term:
            queryset = queryset.filter(
                Q(title__icontains=search_term)
                | Q(document_number__icontains=search_term)
                | Q(document_type__name__icontains=search_term)
            )
        if status_value:
            queryset = queryset.filter(status=status_value)
        if project_value.isdigit():
            queryset = queryset.filter(project_id=int(project_value))
        if confidentiality_value:
            queryset = queryset.filter(confidentiality_level=confidentiality_value)

        allowed_ordering = {"created_at", "-created_at", "title", "-title", "document_number", "-document_number"}
        if ordering not in allowed_ordering:
            ordering = "-created_at"
        queryset = queryset.order_by(ordering, "-id")

        paginator = PartnerPortalPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = PortalDocumentVaultSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class PartnerPortalCommunicationView(APIView):
    permission_classes = [IsAuthenticated, IsPartnerPortalUser]

    def get(self, request):
        context = _portal_context(request)
        queryset = _scoped_communications(context)

        search_term = (request.query_params.get("q") or "").strip()
        channel = (request.query_params.get("channel") or "").strip()
        status_value = (request.query_params.get("status") or "").strip()
        direction = (request.query_params.get("direction") or "").strip()

        if search_term:
            queryset = queryset.filter(
                Q(subject__icontains=search_term)
                | Q(summary__icontains=search_term)
                | Q(body__icontains=search_term)
            )
        if channel:
            queryset = queryset.filter(channel=channel)
        if status_value:
            queryset = queryset.filter(status=status_value)
        if direction:
            queryset = queryset.filter(direction=direction)

        paginator = PartnerPortalPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = PortalCommunicationSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class PartnerPortalApprovalsView(APIView):
    permission_classes = [IsAuthenticated, IsPartnerPortalUser]

    def get(self, request):
        context = _portal_context(request)
        document_qs = _scoped_documents(context)

        pending_versions = (
            DocumentVersion.objects.filter(
                document__in=document_qs,
                approval_status=DocumentVersion.ApprovalStatus.PENDING,
            )
            .select_related("document", "uploaded_by")
            .order_by("-uploaded_at")[:30]
        )
        recent_document_decisions = (
            DocumentApproval.objects.filter(document_version__document__in=document_qs)
            .select_related("document_version", "role", "user")
            .order_by("-timestamp")[:30]
        )
        onboarding_decisions = (
            PartnerOnboardingApproval.objects.filter(case_id__in=context.case_ids)
            .select_related("stage_progress__template_stage", "decided_by")
            .order_by("-decided_at")[:30]
        )

        return Response(
            {
                "can_approve": context.can_approve,
                "pending_count": len(pending_versions),
                "pending_versions": DocumentVersionSerializer(pending_versions, many=True).data,
                "recent_document_decisions": DocumentApprovalSerializer(recent_document_decisions, many=True).data,
                "onboarding_decisions": [
                    {
                        "id": decision.id,
                        "case_id": decision.case_id,
                        "decision": decision.decision,
                        "approver_role_label": decision.approver_role_label,
                        "comments": decision.comments,
                        "stage_code": (
                            decision.stage_progress.template_stage.code
                            if decision.stage_progress_id and decision.stage_progress and decision.stage_progress.template_stage
                            else None
                        ),
                        "stage_name": (
                            decision.stage_progress.template_stage.name
                            if decision.stage_progress_id and decision.stage_progress and decision.stage_progress.template_stage
                            else None
                        ),
                        "decided_by": decision.decided_by.get_full_name() if decision.decided_by else None,
                        "decided_at": decision.decided_at,
                    }
                    for decision in onboarding_decisions
                ],
            }
        )


class PartnerPortalFinancialView(APIView):
    permission_classes = [IsAuthenticated, IsPartnerPortalUser]

    def get(self, request):
        context = _portal_context(request)
        primary_role = _primary_portal_role(context)
        today = timezone.localdate()

        client_payload = None
        if context.customer_ids or context.is_preview_mode:
            client_context = context
            if context.is_preview_mode and not context.customer_ids:
                client_context = resolve_partner_portal_context(request.user)
                client_context.customer_ids = list(
                    PartnerOnboardingCase.objects.filter(id__in=context.case_ids, customer_id__isnull=False).values_list(
                        "customer_id", flat=True
                    )
                )
                client_context.project_ids = context.project_ids
            if client_context.customer_ids:
                client_payload = _build_client_financial_summary(context=client_context, today=today)

        contractor_payload = None
        if context.vendor_ids:
            contractor_payload = _build_contractor_financial_summary(context=context)

        investor_payload = None
        if context.investor_ids:
            investor_payload = _build_investor_financial_summary(context=context)

        return Response(
            {
                "primary_role": primary_role,
                "client": client_payload,
                "contractor": contractor_payload,
                "investor": investor_payload,
            }
        )


class PartnerPortalComplianceView(APIView):
    permission_classes = [IsAuthenticated, IsPartnerPortalUser]

    def get(self, request):
        context = _portal_context(request)
        today = timezone.localdate()
        document_qs = _scoped_documents(context)
        project_qs = _scoped_projects(context)

        expiry_qs = (
            DocumentExpiry.objects.filter(document__in=document_qs)
            .select_related("document")
            .order_by("expiry_date")
        )
        open_risk_qs = ProjectRiskRegisterEntry.objects.filter(project__in=project_qs).filter(
            status__in=[
                ProjectRiskRegisterEntry.Status.OPEN,
                ProjectRiskRegisterEntry.Status.IN_PROGRESS,
            ]
        ).select_related("project", "risk_category", "owner_role", "created_by", "updated_by")
        open_issue_qs = ProjectFieldEscalation.objects.filter(project__in=project_qs).exclude(
            status__in=[ProjectFieldEscalation.Status.RESOLVED, ProjectFieldEscalation.Status.CLOSED]
        ).select_related("project", "source_report")

        vendor_rows = []
        if context.vendor_ids:
            vendor_rows = list(
                Vendor.objects.filter(id__in=context.vendor_ids)
                .values("id", "name", "compliance_status", "performance_rating")
                .order_by("name")
            )

        return Response(
            {
                "summary": {
                    "expired_documents": expiry_qs.filter(expiry_date__lt=today).count(),
                    "documents_expiring_30_days": expiry_qs.filter(
                        expiry_date__gte=today,
                        expiry_date__lte=today + timedelta(days=30),
                    ).count(),
                    "open_risks": open_risk_qs.count(),
                    "open_issues": open_issue_qs.count(),
                },
                "project_compliance": [
                    {
                        "project_id": row.id,
                        "project_name": row.name,
                        "compliance_score": _decimal_text(row.compliance_score),
                        "compliance_status": row.compliance_status,
                        "compliance_last_evaluated_at": row.compliance_last_evaluated_at,
                    }
                    for row in project_qs.order_by("name")
                ],
                "document_expiries": DocumentExpirySerializer(expiry_qs[:30], many=True).data,
                "open_risks_list": ProjectRiskRegisterListSerializer(open_risk_qs[:30], many=True).data,
                "open_issues_list": ProjectFieldEscalationSerializer(open_issue_qs[:30], many=True).data,
                "vendor_compliance": vendor_rows,
            }
        )


class PartnerPortalNotificationsView(APIView):
    permission_classes = [IsAuthenticated, IsPartnerPortalUser]

    def get(self, request):
        queryset = Notification.objects.filter(recipient=request.user).order_by("-created_at")
        is_read_param = (request.query_params.get("is_read") or "").strip().lower()
        if is_read_param in {"true", "false"}:
            queryset = queryset.filter(is_read=(is_read_param == "true"))

        paginator = PartnerPortalPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = NotificationSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class PartnerPortalProfileView(APIView):
    permission_classes = [IsAuthenticated, IsPartnerPortalUser]

    def get(self, request):
        context = _portal_context(request)
        profile = getattr(request.user, "profile", None)
        profile_photo_url = None
        if profile and profile.profile_photo:
            profile_photo_url = request.build_absolute_uri(profile.profile_photo.url)
        case_rows = PartnerOnboardingCase.objects.filter(id__in=context.case_ids).order_by("-created_at")
        entitlement_rows = PartnerEntitlement.objects.filter(id__in=context.entitlement_ids).order_by("-created_at")

        return Response(
            {
                "user": {
                    "id": request.user.id,
                    "full_name": request.user.get_full_name(),
                    "email": request.user.email,
                    "profile_photo_url": profile_photo_url,
                },
                "portal_roles": context.portal_roles,
                "partner_types": context.partner_types,
                "budget_scope": context.budget_scope,
                "permissions": {
                    "can_view_other_investors": context.can_view_other_investors,
                    "can_edit": context.can_edit,
                    "can_approve": context.can_approve,
                    "can_comment": context.can_comment,
                    "can_download_documents": context.can_download_documents,
                },
                "contact_emails": context.contact_emails,
                "contract_references": context.contract_references,
                "investment_vehicle_references": context.investment_vehicle_references,
                "cases": PartnerOnboardingCaseListSerializer(case_rows, many=True).data,
                "entitlements": PartnerEntitlementSerializer(entitlement_rows, many=True).data,
                "legal": {
                    "agreement_acceptance_required": True,
                    "device_fingerprinting_enabled": False,
                },
            }
        )


class PartnerPortalProfilePhotoView(APIView):
    permission_classes = [IsAuthenticated, IsPartnerPortalUser]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        from apps.accounts.models import UserProfile

        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        photo = request.FILES.get("photo")
        if photo is None:
            return Response(
                {"detail": "No photo file was provided. Use the `photo` field."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        content_type = str(getattr(photo, "content_type", "") or "")
        if not content_type.startswith("image/"):
            return Response(
                {"detail": "Only image uploads are allowed for profile photos."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        max_size_bytes = 8 * 1024 * 1024
        if photo.size > max_size_bytes:
            return Response(
                {"detail": "Profile photo exceeds 8MB size limit."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        previous_photo_name = profile.profile_photo.name if profile.profile_photo else None
        profile.profile_photo = photo
        profile.save(update_fields=["profile_photo"])

        if previous_photo_name and previous_photo_name != profile.profile_photo.name:
            profile.profile_photo.storage.delete(previous_photo_name)

        return Response(
            {
                "detail": "Profile photo uploaded successfully.",
                "profile_photo_url": request.build_absolute_uri(profile.profile_photo.url),
            },
            status=status.HTTP_200_OK,
        )

    def delete(self, request):
        from apps.accounts.models import UserProfile

        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        if not profile.profile_photo:
            return Response(
                {"detail": "Profile photo is already empty.", "profile_photo_url": None},
                status=status.HTTP_200_OK,
            )

        profile.profile_photo.delete(save=False)
        profile.profile_photo = None
        profile.save(update_fields=["profile_photo"])
        return Response(
            {"detail": "Profile photo removed successfully.", "profile_photo_url": None},
            status=status.HTTP_200_OK,
        )
