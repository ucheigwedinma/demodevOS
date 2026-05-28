from django.db.models import Count, Min, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters import rest_framework as filters
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.inventory.services import delete_goods_receipt_item_transaction, sync_goods_receipt_item
from apps.settings.permissions import HasRolePermission

from .models import (
    Contract,
    ContractAmendment,
    ContractClause,
    GoodsReceipt,
    VendorCategory,
    GoodsReceiptItem,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseRequisition,
    PurchaseRequisitionItem,
    RequestForQuotation,
    RequestForQuotationQuote,
    Vendor,
)
from .serializers import (
    GRNDetailSerializer,
    GRNItemSerializer,
    GRNListSerializer,
    GRNWriteSerializer,
    PODetailSerializer,
    POItemSerializer,
    POListSerializer,
    POWriteSerializer,
    PRDetailSerializer,
    PRItemSerializer,
    PRListSerializer,
    PRWriteSerializer,
    RFQDetailSerializer,
    RFQListSerializer,
    RFQQuoteDetailSerializer,
    RFQQuoteListSerializer,
    RFQQuoteWriteSerializer,
    RFQWriteSerializer,
    VendorDetailSerializer,
    VendorListSerializer,
    VendorWriteSerializer,
    ContractAmendmentSerializer,
    ContractClauseSerializer,
    ContractDetailSerializer,
    ContractListSerializer,
    ContractWriteSerializer,
    VendorCategorySerializer,
)


def _user_org(request):
    profile = getattr(request.user, "profile", None)
    return getattr(profile, "organization", None)


def _is_superuser(request):
    return request.user.is_superuser


def _scoped_requisition_queryset(request):
    qs = PurchaseRequisition.objects.select_related(
        "project", "property", "budget_line_item"
    ).annotate(item_count=Count("items"))
    if _is_superuser(request):
        return qs
    org = _user_org(request)
    if not org:
        return qs.none()
    return qs.filter(
        Q(organization=org)
        | Q(organization__isnull=True, project__organization=org)
        | Q(organization__isnull=True, property__organization=org)
    ).distinct()


def _scoped_purchase_order_queryset(request):
    qs = PurchaseOrder.objects.select_related(
        "vendor", "requisition", "project", "property", "budget_line_item"
    ).annotate(item_count=Count("items"))
    if _is_superuser(request):
        return qs
    org = _user_org(request)
    if not org:
        return qs.none()
    return qs.filter(
        Q(organization=org)
        | Q(organization__isnull=True, project__organization=org)
        | Q(organization__isnull=True, property__organization=org)
        | Q(organization__isnull=True, requisition__organization=org)
    ).distinct()


def _scoped_goods_receipt_queryset(request, purchase_order_id=None):
    qs = GoodsReceipt.objects.select_related(
        "purchase_order__vendor"
    ).annotate(item_count=Count("items"))
    if purchase_order_id is not None:
        qs = qs.filter(purchase_order_id=purchase_order_id)
    if _is_superuser(request):
        return qs
    org = _user_org(request)
    if not org:
        return qs.none()
    return qs.filter(
        Q(organization=org)
        | Q(organization__isnull=True, purchase_order__organization=org)
    ).distinct()


# --- Filters ---


class PRFilter(filters.FilterSet):
    required_after = filters.DateFilter(field_name="required_date", lookup_expr="gte")
    required_before = filters.DateFilter(field_name="required_date", lookup_expr="lte")
    created_after = filters.DateFilter(field_name="created_at", lookup_expr="gte")
    created_before = filters.DateFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = PurchaseRequisition
        fields = [
            "status",
            "priority",
            "project",
            "property",
            "budget_line_item",
            "cost_code",
        ]


class POFilter(filters.FilterSet):
    issued_after = filters.DateFilter(field_name="issue_date", lookup_expr="gte")
    issued_before = filters.DateFilter(field_name="issue_date", lookup_expr="lte")
    delivery_after = filters.DateFilter(field_name="expected_delivery_date", lookup_expr="gte")
    delivery_before = filters.DateFilter(field_name="expected_delivery_date", lookup_expr="lte")

    class Meta:
        model = PurchaseOrder
        fields = [
            "status",
            "vendor",
            "project",
            "property",
            "budget_line_item",
            "cost_code",
        ]


class RFQFilter(filters.FilterSet):
    issue_after = filters.DateFilter(field_name="issue_date", lookup_expr="gte")
    issue_before = filters.DateFilter(field_name="issue_date", lookup_expr="lte")
    deadline_after = filters.DateFilter(field_name="submission_deadline", lookup_expr="gte")
    deadline_before = filters.DateFilter(field_name="submission_deadline", lookup_expr="lte")

    class Meta:
        model = RequestForQuotation
        fields = [
            "status",
            "project",
            "property",
            "requisition",
            "selected_vendor",
            "budget_line_item",
            "cost_code",
        ]


# --- Action Map ---

_PROCUREMENT_ACTION_MAP = {
    "list": "view", "retrieve": "view", "create": "create",
    "update": "edit", "partial_update": "edit", "destroy": "delete",
    "submit_approval": "approve", "select_vendor": "edit",
    "comparison": "view",
}


# --- ViewSets ---


class VendorCategoryViewSet(viewsets.ModelViewSet):
    """CRUD for org-configurable vendor categories."""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "procurement.vendors"
    rbac_action_map = _PROCUREMENT_ACTION_MAP
    serializer_class = VendorCategorySerializer
    search_fields = ["name", "code", "description"]
    filterset_fields = ["is_active", "parent"]
    ordering = ["sort_order", "name"]

    def get_queryset(self):
        qs = VendorCategory.objects.select_related("parent").annotate(
            vendor_count=Count("vendors"),
        )
        org = _user_org(self.request)
        if _is_superuser(self.request) and not org:
            return qs
        return qs.filter(organization=org) if org else qs.none()

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


class VendorViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "procurement.vendors"

    search_fields = ["name", "contact_person"]
    filterset_fields = ["is_active", "category", "compliance_status", "is_blacklisted"]
    ordering_fields = ["name", "performance_rating", "created_at"]
    ordering = ["name"]

    def get_queryset(self):
        qs = Vendor.objects.annotate(
            po_count=Count("purchase_orders"),
            total_po_value=Sum("purchase_orders__total_amount"),
        )
        org = _user_org(self.request)
        if not org:
            return qs.none()
        return qs.filter(
            Q(organization=org)
            | Q(organization__isnull=True, approved_projects__organization=org)
            | Q(organization__isnull=True, purchase_orders__organization=org)
        ).distinct()

    def get_serializer_class(self):
        if self.action == "list":
            return VendorListSerializer
        if self.action in ("create", "update", "partial_update"):
            return VendorWriteSerializer
        return VendorDetailSerializer

    def perform_create(self, serializer):
        org = _user_org(self.request)
        serializer.save(organization=org)


class PurchaseRequisitionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "procurement.requisitions"
    rbac_action_map = _PROCUREMENT_ACTION_MAP

    filterset_class = PRFilter
    search_fields = ["pr_number", "title", "requester", "budget_code", "cost_code"]
    ordering_fields = ["pr_number", "required_date", "estimated_total", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return _scoped_requisition_queryset(self.request)

    def get_serializer_class(self):
        if self.action == "list":
            return PRListSerializer
        if self.action in ("create", "update", "partial_update"):
            return PRWriteSerializer
        return PRDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))

    @action(detail=True, methods=["post"], url_path="submit-approval")
    def submit_approval(self, request, pk=None):
        from apps.workflows.engine import submit_for_approval

        pr = self.get_object()
        if pr.status != PurchaseRequisition.Status.DRAFT:
            return Response(
                {"detail": "Only draft requisitions can be submitted for approval."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            instance = submit_for_approval(pr, request.user)
            pr.status = PurchaseRequisition.Status.SUBMITTED
            pr.save(update_fields=["status", "updated_at"])
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {"detail": "Submitted for approval.", "workflow_instance_id": instance.pk},
            status=status.HTTP_201_CREATED,
        )


class PRItemViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "procurement.requisitions"

    serializer_class = PRItemSerializer

    def _get_requisition(self):
        return get_object_or_404(
            _scoped_requisition_queryset(self.request),
            pk=self.kwargs["pr_pk"],
        )

    def get_queryset(self):
        return PurchaseRequisitionItem.objects.filter(requisition=self._get_requisition())

    def perform_create(self, serializer):
        item = serializer.save(requisition=self._get_requisition())
        item.requisition.recalculate_totals()

    def perform_update(self, serializer):
        item = serializer.save()
        item.requisition.recalculate_totals()

    def perform_destroy(self, instance):
        requisition = instance.requisition
        instance.delete()
        requisition.recalculate_totals()


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "procurement.orders"
    rbac_action_map = _PROCUREMENT_ACTION_MAP

    filterset_class = POFilter
    search_fields = ["po_number", "vendor__name", "notes", "cost_code"]
    ordering_fields = ["po_number", "issue_date", "total_amount", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return _scoped_purchase_order_queryset(self.request)

    def get_serializer_class(self):
        if self.action == "list":
            return POListSerializer
        if self.action in ("create", "update", "partial_update"):
            return POWriteSerializer
        return PODetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))

    @action(detail=True, methods=["post"], url_path="submit-approval")
    def submit_approval(self, request, pk=None):
        from apps.workflows.engine import submit_for_approval

        po = self.get_object()
        if po.status != PurchaseOrder.Status.DRAFT:
            return Response(
                {"detail": "Only draft purchase orders can be submitted for approval."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            instance = submit_for_approval(po, request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {"detail": "Submitted for approval.", "workflow_instance_id": instance.pk},
            status=status.HTTP_201_CREATED,
        )


class POItemViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "procurement.orders"

    serializer_class = POItemSerializer

    def _get_purchase_order(self):
        return get_object_or_404(
            _scoped_purchase_order_queryset(self.request),
            pk=self.kwargs["po_pk"],
        )

    def get_queryset(self):
        return PurchaseOrderItem.objects.filter(purchase_order=self._get_purchase_order())

    def perform_create(self, serializer):
        item = serializer.save(purchase_order=self._get_purchase_order())
        item.purchase_order.recalculate_totals()

    def perform_update(self, serializer):
        item = serializer.save()
        item.purchase_order.recalculate_totals()

    def perform_destroy(self, instance):
        po = instance.purchase_order
        instance.delete()
        po.recalculate_totals()


class GoodsReceiptViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "procurement.receipts"

    search_fields = ["grn_number", "received_by"]
    filterset_fields = ["status"]
    ordering = ["-received_date"]

    def _get_purchase_order(self):
        return get_object_or_404(
            _scoped_purchase_order_queryset(self.request),
            pk=self.kwargs["po_pk"],
        )

    def get_queryset(self):
        purchase_order = self._get_purchase_order()
        return _scoped_goods_receipt_queryset(
            self.request,
            purchase_order_id=purchase_order.pk,
        )

    def get_serializer_class(self):
        if self.action == "list":
            return GRNListSerializer
        if self.action in ("create", "update", "partial_update"):
            return GRNWriteSerializer
        return GRNDetailSerializer

    def perform_create(self, serializer):
        po = self._get_purchase_order()
        grn = serializer.save(
            purchase_order=po,
            organization=po.organization,
        )
        grn.purchase_order.update_status_from_receipts()

    def perform_update(self, serializer):
        grn = serializer.save()
        grn.purchase_order.update_status_from_receipts()


class GoodsReceiptItemViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "procurement.receipts"

    serializer_class = GRNItemSerializer

    def _get_goods_receipt(self):
        purchase_order = get_object_or_404(
            _scoped_purchase_order_queryset(self.request),
            pk=self.kwargs["po_pk"],
        )
        return get_object_or_404(
            _scoped_goods_receipt_queryset(
                self.request,
                purchase_order_id=purchase_order.pk,
            ),
            pk=self.kwargs["grn_pk"],
        )

    def get_queryset(self):
        return GoodsReceiptItem.objects.filter(
            goods_receipt=self._get_goods_receipt()
        ).select_related("po_item")

    def perform_create(self, serializer):
        item = serializer.save(goods_receipt=self._get_goods_receipt())
        item.goods_receipt.purchase_order.update_status_from_receipts()
        sync_goods_receipt_item(item, performed_by=self.request.user)

    def perform_update(self, serializer):
        item = serializer.save()
        item.goods_receipt.purchase_order.update_status_from_receipts()
        sync_goods_receipt_item(item, performed_by=self.request.user)

    def perform_destroy(self, instance):
        po = instance.goods_receipt.purchase_order
        grn_item_id = instance.id
        instance.delete()
        po.update_status_from_receipts()
        delete_goods_receipt_item_transaction(grn_item_id)


class GoodsReceiptFlatViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Flat (non-nested) read-only view of all goods receipts."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "procurement.receipts"

    search_fields = ["grn_number", "purchase_order__po_number", "received_by"]
    filterset_fields = ["status"]
    ordering_fields = ["grn_number", "received_date", "created_at"]
    ordering = ["-received_date"]

    def get_queryset(self):
        qs = GoodsReceipt.objects.select_related(
            "purchase_order__vendor"
        ).annotate(item_count=Count("items"))

        if _is_superuser(self.request):
            return qs
        org = _user_org(self.request)
        if not org:
            return qs.none()
        return qs.filter(
            Q(organization=org)
            | Q(organization__isnull=True, purchase_order__organization=org)
        ).distinct()

    def get_serializer_class(self):
        if self.action == "list":
            return GRNListSerializer
        return GRNDetailSerializer


class RequestForQuotationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "procurement.rfqs"
    rbac_action_map = _PROCUREMENT_ACTION_MAP

    filterset_class = RFQFilter
    search_fields = ["rfq_number", "title", "budget_code", "cost_code"]
    ordering_fields = ["rfq_number", "issue_date", "submission_deadline", "estimated_value", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = RequestForQuotation.objects.select_related(
            "requisition",
            "project",
            "property",
            "selected_vendor",
            "budget_line_item",
        ).annotate(
            quote_count=Count("quotes", distinct=True),
            lowest_quote=Min("quotes__quoted_amount"),
        )
        if _is_superuser(self.request):
            return qs
        org = _user_org(self.request)
        if not org:
            return qs.none()
        return qs.filter(
            Q(organization=org)
            | Q(organization__isnull=True, project__organization=org)
            | Q(organization__isnull=True, property__organization=org)
            | Q(organization__isnull=True, requisition__organization=org)
        ).distinct()

    def get_serializer_class(self):
        if self.action == "list":
            return RFQListSerializer
        if self.action in ("create", "update", "partial_update"):
            return RFQWriteSerializer
        return RFQDetailSerializer

    def perform_create(self, serializer):
        serializer.save(
            organization=_user_org(self.request),
            created_by=self.request.user,
        )

    @action(detail=True, methods=["post"], url_path="submit-approval")
    def submit_approval(self, request, pk=None):
        from apps.workflows.engine import submit_for_approval

        rfq = self.get_object()
        if rfq.status not in (
            RequestForQuotation.Status.DRAFT,
            RequestForQuotation.Status.ISSUED,
            RequestForQuotation.Status.EVALUATION,
        ):
            return Response(
                {"detail": "Only draft, issued, or evaluation RFQs can be submitted for approval."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            instance = submit_for_approval(rfq, request.user)
            rfq.status = RequestForQuotation.Status.SUBMITTED
            rfq.save(update_fields=["status", "updated_at"])
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {"detail": "Submitted for approval.", "workflow_instance_id": instance.pk},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="select-vendor")
    def select_vendor(self, request, pk=None):
        rfq = self.get_object()
        quote_id = request.data.get("quote_id")
        notes = request.data.get("selection_notes", "")
        if not quote_id:
            return Response({"detail": "quote_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        quote = rfq.quotes.filter(pk=quote_id).select_related("vendor").first()
        if not quote:
            return Response({"detail": "Quote not found for this RFQ."}, status=status.HTTP_404_NOT_FOUND)

        rfq.quotes.exclude(pk=quote.pk).filter(status=RequestForQuotationQuote.QuoteStatus.WINNER).update(
            status=RequestForQuotationQuote.QuoteStatus.SHORTLISTED,
            updated_at=timezone.now(),
        )
        quote.status = RequestForQuotationQuote.QuoteStatus.WINNER
        quote.save(update_fields=["status", "updated_at"])

        rfq.selected_vendor = quote.vendor
        rfq.selection_notes = notes
        rfq.selection_date = timezone.now()
        rfq.status = RequestForQuotation.Status.EVALUATION
        rfq.save(update_fields=["selected_vendor", "selection_notes", "selection_date", "status", "updated_at"])

        return Response(
            {
                "detail": "Vendor selected successfully.",
                "selected_vendor": quote.vendor.name,
                "quote_id": quote.pk,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"], url_path="comparison")
    def comparison(self, request, pk=None):
        rfq = self.get_object()
        quotes = list(
            rfq.quotes.select_related("vendor").order_by("-total_score", "quoted_amount")
        )
        results = []
        for idx, quote in enumerate(quotes, start=1):
            data = RFQQuoteListSerializer(quote).data
            data["rank"] = idx
            results.append(data)
        return Response(
            {
                "rfq_id": rfq.pk,
                "rfq_number": rfq.rfq_number,
                "title": rfq.title,
                "status": rfq.status,
                "selected_vendor": rfq.selected_vendor.name if rfq.selected_vendor else None,
                "quotes": results,
            }
        )

    @action(detail=True, methods=["get"], url_path="recommend-vendors")
    def recommend_vendors(self, request, pk=None):
        """Auto-recommend vendors for this RFQ based on performance, pricing, and proximity.

        Scoring weights:
          - Performance rating (0-5)  → 30%
          - Delivery timeliness (0-100) → 25%
          - Price competitiveness     → 20%
          - Win rate                  → 15%
          - Proximity (if coords)     → 10%
        """
        from math import radians, sin, cos, sqrt, atan2

        rfq = self.get_object()
        org = rfq.organization or _user_org(request)
        if not org:
            return Response({"detail": "No organization context."}, status=status.HTTP_400_BAD_REQUEST)

        vendors = Vendor.objects.filter(
            organization=org, is_active=True, is_blacklisted=False,
            compliance_status__in=("compliant", "pending_review"),
        ).exclude(pk__in=rfq.quotes.values_list("vendor_id", flat=True))

        # Get project location for proximity scoring
        project_lat, project_lng = None, None
        if rfq.project:
            # Try to get from project's land acquisition or site location
            pass  # Proximity scoring uses vendor coords only for now

        price_comp_map = {"low": 100, "average": 70, "high": 40, "premium": 20}

        scored = []
        for v in vendors:
            # Performance: 0-5 → 0-100
            perf_score = float(v.performance_rating) / 5 * 100 if v.performance_rating else 0
            # Timeliness: already 0-100
            time_score = float(v.delivery_timeliness_score) if v.delivery_timeliness_score else 0
            # Price: mapped from enum
            price_score = price_comp_map.get(v.price_competitiveness, 50)
            # Win rate: 0-100
            win_score = float(v.win_rate_pct) if v.win_rate_pct else 0
            # Proximity: placeholder (100 if has coords, 50 if not)
            prox_score = 70 if (v.latitude and v.longitude) else 50

            total = (
                perf_score * 0.30 +
                time_score * 0.25 +
                price_score * 0.20 +
                win_score * 0.15 +
                prox_score * 0.10
            )

            scored.append({
                "vendor_id": v.pk,
                "vendor_name": v.name,
                "category": v.category,
                "city": v.city,
                "state_region": v.state_region,
                "performance_rating": str(v.performance_rating),
                "delivery_timeliness_score": str(v.delivery_timeliness_score),
                "price_competitiveness": v.price_competitiveness,
                "win_rate_pct": str(v.win_rate_pct),
                "total_rfqs_participated": v.total_rfqs_participated,
                "total_rfqs_won": v.total_rfqs_won,
                "recommendation_score": round(total, 1),
            })

        scored.sort(key=lambda x: x["recommendation_score"], reverse=True)
        for idx, s in enumerate(scored, start=1):
            s["rank"] = idx

        return Response({
            "rfq_id": rfq.pk,
            "rfq_number": rfq.rfq_number,
            "recommended_vendors": scored[:10],
            "total_eligible": len(scored),
        })


class RFQQuoteViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "procurement.tenders"

    search_fields = ["vendor__name", "quote_number", "notes"]
    filterset_fields = ["status", "vendor"]
    ordering_fields = ["submitted_at", "quoted_amount", "total_score", "quote_date"]
    ordering = ["-submitted_at"]

    def get_queryset(self):
        qs = RequestForQuotationQuote.objects.filter(
            rfq_id=self.kwargs["rfq_pk"]
        ).select_related("vendor", "rfq")

        if _is_superuser(self.request):
            return qs
        org = _user_org(self.request)
        if not org:
            return qs.none()
        return qs.filter(
            Q(organization=org)
            | Q(organization__isnull=True, rfq__organization=org)
        ).distinct()

    def get_serializer_class(self):
        if self.action == "list":
            return RFQQuoteListSerializer
        if self.action in ("create", "update", "partial_update"):
            return RFQQuoteWriteSerializer
        return RFQQuoteDetailSerializer

    def perform_create(self, serializer):
        rfq = RequestForQuotation.objects.get(pk=self.kwargs["rfq_pk"])
        quote = serializer.save(rfq_id=self.kwargs["rfq_pk"], organization=rfq.organization)
        quote.rfq.recalculate_estimated_value()

        # Notify procurement team of new quote
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification, resolve_raci_recipients

        org = rfq.organization
        raci = resolve_raci_recipients(
            organization=org,
            process_key="procurement.rfq",
        )
        recipients = raci.all
        if not recipients:
            from apps.accounts.models import UserProfile

            recipients = [
                p.user
                for p in UserProfile.objects.filter(
                    organization=org,
                    role="admin",
                    user__is_active=True,
                ).select_related("user")
            ]
        if recipients:
            vendor_name = str(quote.vendor) if hasattr(quote, "vendor") and quote.vendor_id else ""
            dispatch_workflow_notification(
                organization=org,
                event_key="procurement_rfq_quote_received",
                recipients=recipients,
                context={
                    "rfq_number": rfq.rfq_number,
                    "vendor_name": vendor_name,
                    "quoted_amount": str(getattr(quote, "total_amount", "") or ""),
                    "action_url": f"/procurement/rfqs/{rfq.id}",
                },
                link_url=f"/procurement/rfqs/{rfq.id}",
                fallback_channels=["in_app"],
                fallback_title=f"Quote received for {rfq.rfq_number}",
                fallback_message=(
                    f"A vendor quote has been submitted for RFQ {rfq.rfq_number}"
                    f"{f' by {vendor_name}' if vendor_name else ''}."
                ),
                fallback_category=Notification.Category.PROCUREMENT_ORDER,
                fallback_severity=Notification.Severity.INFO,
            )

    def perform_update(self, serializer):
        quote = serializer.save()
        quote.rfq.recalculate_estimated_value()

    def perform_destroy(self, instance):
        rfq = instance.rfq
        instance.delete()
        rfq.recalculate_estimated_value()


# --- Overview ---


class ProcurementOverviewView(APIView):
    """Aggregated procurement dashboard data."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "procurement.requisitions"
    rbac_action = "view"

    def get(self, request):
        pr_qs = PurchaseRequisition.objects.all()
        po_qs = PurchaseOrder.objects.all()
        rfq_qs = RequestForQuotation.objects.all()

        if not _is_superuser(request):
            org = _user_org(request)
            if not org:
                return Response(
                    {
                        "open_requisitions_count": 0,
                        "open_requisitions_value": "0",
                        "pending_approval_count": 0,
                        "active_po_count": 0,
                        "active_po_value": "0",
                        "pending_delivery_count": 0,
                        "recent_requisitions": [],
                        "recent_purchase_orders": [],
                        "prs_by_status": [],
                        "pos_by_status": [],
                        "rfq_open_count": 0,
                        "rfq_submitted_count": 0,
                    }
                )
            pr_qs = pr_qs.filter(
                Q(organization=org)
                | Q(organization__isnull=True, project__organization=org)
                | Q(organization__isnull=True, property__organization=org)
            ).distinct()
            po_qs = po_qs.filter(
                Q(organization=org)
                | Q(organization__isnull=True, project__organization=org)
                | Q(organization__isnull=True, property__organization=org)
                | Q(organization__isnull=True, requisition__organization=org)
            ).distinct()
            rfq_qs = rfq_qs.filter(
                Q(organization=org)
                | Q(organization__isnull=True, project__organization=org)
                | Q(organization__isnull=True, property__organization=org)
                | Q(organization__isnull=True, requisition__organization=org)
            ).distinct()

        # PRs: open = not cancelled/ordered
        open_prs = pr_qs.exclude(
            status__in=[
                PurchaseRequisition.Status.CANCELLED,
                PurchaseRequisition.Status.ORDERED,
            ]
        )
        open_pr_agg = open_prs.aggregate(
            count=Count("id"),
            value=Sum("estimated_total"),
        )

        pending_approval = pr_qs.filter(
            status=PurchaseRequisition.Status.SUBMITTED
        ).count()

        # POs: active = not cancelled/received
        active_pos = po_qs.exclude(
            status__in=[
                PurchaseOrder.Status.CANCELLED,
                PurchaseOrder.Status.RECEIVED,
            ]
        )
        active_po_agg = active_pos.aggregate(
            count=Count("id"),
            value=Sum("total_amount"),
        )

        pending_delivery = po_qs.filter(
            status=PurchaseOrder.Status.ISSUED
        ).count()

        # Status distributions
        prs_by_status = list(
            pr_qs.values("status")
            .annotate(count=Count("id"))
            .order_by("status")
        )
        pos_by_status = list(
            po_qs.values("status")
            .annotate(count=Count("id"))
            .order_by("status")
        )

        # Recent items
        recent_prs = pr_qs.select_related(
            "project", "property"
        ).annotate(item_count=Count("items")).order_by("-created_at")[:5]

        recent_pos = po_qs.select_related(
            "vendor", "requisition", "project", "property"
        ).annotate(item_count=Count("items")).order_by("-created_at")[:5]

        rfq_open_count = rfq_qs.exclude(
            status__in=[RequestForQuotation.Status.CANCELLED, RequestForQuotation.Status.CLOSED]
        ).count()
        rfq_submitted_count = rfq_qs.filter(status=RequestForQuotation.Status.SUBMITTED).count()

        # --- Delayed deliveries ---
        from django.utils import timezone as tz
        today = tz.localdate()
        delayed_pos = po_qs.filter(
            status=PurchaseOrder.Status.ISSUED,
            expected_delivery_date__lt=today,
            expected_delivery_date__isnull=False,
        ).select_related("vendor", "project").order_by("expected_delivery_date")[:10]
        delayed_deliveries = [
            {
                "id": po.id,
                "po_number": po.po_number,
                "vendor_name": po.vendor.name if po.vendor else "—",
                "project_name": po.project.name if po.project else "—",
                "expected_date": str(po.expected_delivery_date),
                "days_overdue": (today - po.expected_delivery_date).days,
                "total_amount": str(po.total_amount or 0),
            }
            for po in delayed_pos
        ]
        delayed_count = po_qs.filter(
            status=PurchaseOrder.Status.ISSUED,
            expected_delivery_date__lt=today,
            expected_delivery_date__isnull=False,
        ).count()

        # --- Vendor performance alerts ---
        org = _user_org(request) if not _is_superuser(request) else None
        vendor_qs = Vendor.objects.filter(is_active=True)
        if org:
            vendor_qs = vendor_qs.filter(organization=org)
        low_perf_vendors = vendor_qs.filter(
            performance_rating__lt=3,
            performance_rating__gt=0,
        ).values("id", "name", "category", "performance_rating").order_by("performance_rating")[:5]
        blacklisted_vendors = vendor_qs.filter(is_blacklisted=True).values("id", "name", "category")[:5]
        vendor_alerts = []
        for v in low_perf_vendors:
            vendor_alerts.append({
                "vendor_id": v["id"],
                "vendor_name": v["name"],
                "category": v["category"],
                "type": "low_performance",
                "severity": "critical" if float(v["performance_rating"]) < 2 else "warning",
                "message": f"{v['name']} rated {v['performance_rating']}/5 — review engagement",
            })
        for v in blacklisted_vendors:
            vendor_alerts.append({
                "vendor_id": v["id"],
                "vendor_name": v["name"],
                "category": v["category"],
                "type": "blacklisted",
                "severity": "critical",
                "message": f"{v['name']} is blacklisted — active POs should be reviewed",
            })

        # --- Budget consumption by project ---
        project_spend = list(
            po_qs.exclude(status=PurchaseOrder.Status.CANCELLED)
            .filter(project__isnull=False)
            .values("project__id", "project__name", "project__budget")
            .annotate(
                total_committed=Sum("total_amount"),
                po_count=Count("id"),
            )
            .order_by("-total_committed")[:10]
        )
        budget_consumption = []
        for ps in project_spend:
            budget = float(ps["project__budget"] or 0)
            committed = float(ps["total_committed"] or 0)
            pct = round(committed / budget * 100) if budget > 0 else 0
            budget_consumption.append({
                "project_id": ps["project__id"],
                "project_name": ps["project__name"],
                "budget": budget,
                "committed": committed,
                "consumption_pct": pct,
                "po_count": ps["po_count"],
                "status": "critical" if pct > 90 else "warning" if pct > 75 else "on_track",
            })

        return Response({
            "open_requisitions_count": open_pr_agg["count"] or 0,
            "open_requisitions_value": str(open_pr_agg["value"] or 0),
            "pending_approval_count": pending_approval,
            "active_po_count": active_po_agg["count"] or 0,
            "active_po_value": str(active_po_agg["value"] or 0),
            "pending_delivery_count": pending_delivery,
            "delayed_delivery_count": delayed_count,
            "delayed_deliveries": delayed_deliveries,
            "vendor_alerts": vendor_alerts,
            "budget_consumption": budget_consumption,
            "recent_requisitions": PRListSerializer(recent_prs, many=True).data,
            "recent_purchase_orders": POListSerializer(recent_pos, many=True).data,
            "prs_by_status": prs_by_status,
            "pos_by_status": pos_by_status,
            "rfq_open_count": rfq_open_count,
            "rfq_submitted_count": rfq_submitted_count,
        })


# ── Spend Analytics ───────────────────────────────────────────────────


class SpendAnalyticsView(APIView):
    """Strategic spend analytics: by vendor, category, project, and time period."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "procurement.requisitions"
    rbac_action = "view"

    def get(self, request):
        org = _user_org(request)
        if not org and not _is_superuser(request):
            return Response({})

        # Date filters
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        project_id = request.query_params.get("project")

        # Base querysets — committed (POs) and actual (Bills)
        po_qs = PurchaseOrder.objects.filter(
            status__in=("approved", "issued", "partially_received", "received"),
        )
        from apps.finance.models import Bill
        bill_qs = Bill.objects.filter(status__in=("approved", "paid"))

        if not _is_superuser(request):
            po_qs = po_qs.filter(organization=org)
            bill_qs = bill_qs.filter(organization=org)

        if start_date:
            po_qs = po_qs.filter(issue_date__gte=start_date)
            bill_qs = bill_qs.filter(issue_date__gte=start_date)
        if end_date:
            po_qs = po_qs.filter(issue_date__lte=end_date)
            bill_qs = bill_qs.filter(issue_date__lte=end_date)
        if project_id:
            po_qs = po_qs.filter(project_id=project_id)
            bill_qs = bill_qs.filter(project_id=project_id)

        # ── Totals ────────────────────────────────────────────────
        total_committed = po_qs.aggregate(t=Sum("total_amount"))["t"] or Decimal("0")
        total_paid = bill_qs.aggregate(t=Sum("total_amount"))["t"] or Decimal("0")
        po_count = po_qs.count()
        bill_count = bill_qs.count()

        # ── Spend by Vendor ───────────────────────────────────────
        by_vendor_committed = list(
            po_qs.values("vendor__id", "vendor__name", "vendor__category")
            .annotate(
                committed=Sum("total_amount"),
                po_count=Count("id"),
            )
            .order_by("-committed")[:15]
        )
        by_vendor_paid = {
            row["purchase_order__vendor__id"]: row["paid"]
            for row in bill_qs.filter(purchase_order__isnull=False)
            .values("purchase_order__vendor__id")
            .annotate(paid=Sum("total_amount"))
        }
        spend_by_vendor = []
        for v in by_vendor_committed:
            vid = v["vendor__id"]
            spend_by_vendor.append({
                "vendor_id": vid,
                "vendor_name": v["vendor__name"],
                "category": v["vendor__category"],
                "committed": str(v["committed"]),
                "paid": str(by_vendor_paid.get(vid, Decimal("0"))),
                "po_count": v["po_count"],
            })

        # ── Spend by Category ────────────────────────────────────
        spend_by_category = list(
            po_qs.values("vendor__category")
            .annotate(
                committed=Sum("total_amount"),
                po_count=Count("id"),
            )
            .order_by("-committed")
        )
        category_labels = dict(Vendor.Category.choices)
        for entry in spend_by_category:
            entry["category_display"] = category_labels.get(entry["vendor__category"], entry["vendor__category"])
            entry["committed"] = str(entry["committed"])

        # ── Spend by Project ─────────────────────────────────────
        spend_by_project = list(
            po_qs.filter(project__isnull=False)
            .values("project__id", "project__name")
            .annotate(
                committed=Sum("total_amount"),
                po_count=Count("id"),
            )
            .order_by("-committed")[:15]
        )
        for entry in spend_by_project:
            entry["committed"] = str(entry["committed"])

        # ── Monthly Trend ────────────────────────────────────────
        from django.db.models.functions import TruncMonth
        monthly_trend = list(
            po_qs.annotate(month=TruncMonth("issue_date"))
            .values("month")
            .annotate(committed=Sum("total_amount"), count=Count("id"))
            .order_by("month")
        )
        for entry in monthly_trend:
            entry["month"] = entry["month"].isoformat() if entry["month"] else None
            entry["committed"] = str(entry["committed"])

        # ── Top Vendors by Spend ─────────────────────────────────
        top_vendors = spend_by_vendor[:10]

        return Response({
            "total_committed": str(total_committed),
            "total_paid": str(total_paid),
            "po_count": po_count,
            "bill_count": bill_count,
            "spend_by_vendor": spend_by_vendor,
            "spend_by_category": spend_by_category,
            "spend_by_project": spend_by_project,
            "monthly_trend": monthly_trend,
            "top_vendors": top_vendors,
        })


# ── Contracts & Agreements ───────────────────────────────────────────


class ContractViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "procurement.purchase_orders"
    rbac_action_map = _PROCUREMENT_ACTION_MAP
    search_fields = ["contract_number", "title", "scope_of_work", "vendor__name"]
    filterset_fields = ["vendor", "project", "contract_type", "status", "is_price_locked"]
    ordering_fields = ["created_at", "effective_date", "expiry_date", "original_value", "status"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return ContractListSerializer
        if self.action in ("create", "update", "partial_update"):
            return ContractWriteSerializer
        return ContractDetailSerializer

    def get_queryset(self):
        qs = (
            Contract.objects.select_related("vendor", "project", "purchase_order", "created_by")
            .prefetch_related("amendments", "clauses")
            .annotate(amendment_count=Count("amendments"))
        )
        if _is_superuser(self.request):
            return qs
        org = _user_org(self.request)
        return qs.filter(organization=org) if org else qs.none()

    def perform_create(self, serializer):
        serializer.save(
            organization=_user_org(self.request),
            created_by=self.request.user,
        )

    @action(detail=False, methods=["get"])
    def summary(self, request):
        org = _user_org(request)
        if not org:
            return Response({})
        from datetime import date, timedelta
        qs = Contract.objects.filter(organization=org)
        today = date.today()
        active = qs.filter(status="executed")
        return Response({
            "total": qs.count(),
            "active": active.count(),
            "draft_negotiation": qs.filter(status__in=["draft", "negotiation", "pending_approval"]).count(),
            "completed": qs.filter(status="completed").count(),
            "expired": qs.filter(status="expired").count(),
            "expiring_30d": active.filter(expiry_date__lte=today + timedelta(days=30), expiry_date__gte=today).count(),
            "total_value": str(active.aggregate(t=Sum("revised_value"))["t"] or 0),
            "framework_agreements": active.filter(contract_type="framework").count(),
            "price_locked": active.filter(is_price_locked=True).count(),
        })


class ContractAmendmentViewSet(viewsets.ModelViewSet):
    """Nested under /contracts/<pk>/amendments/"""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "procurement.purchase_orders"
    rbac_action_map = _PROCUREMENT_ACTION_MAP
    serializer_class = ContractAmendmentSerializer
    ordering = ["amendment_number"]

    def get_queryset(self):
        return ContractAmendment.objects.filter(contract_id=self.kwargs.get("contract_pk"))

    def perform_create(self, serializer):
        serializer.save(contract_id=self.kwargs["contract_pk"])


class ContractClauseViewSet(viewsets.ModelViewSet):
    """Nested under /contracts/<pk>/clauses/"""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "procurement.purchase_orders"
    rbac_action_map = _PROCUREMENT_ACTION_MAP
    serializer_class = ContractClauseSerializer
    ordering = ["sort_order", "clause_number"]

    def get_queryset(self):
        return ContractClause.objects.filter(contract_id=self.kwargs.get("contract_pk"))

    def perform_create(self, serializer):
        serializer.save(contract_id=self.kwargs["contract_pk"])
