from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, F, Q, Sum
from django.utils import timezone
from django.utils.dateparse import parse_date
from django_filters import rest_framework as filters
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.mixins import OrgScopedMixin
from apps.finance.models import Budget, BudgetLineItem
from apps.settings.permissions import HasRolePermission

from .models import (
    BillOfMaterials,
    BoqTaskMapping,
    InventoryItem,
    InventoryStock,
    InventoryTransaction,
    Warehouse,
)
from .serializers import (
    BOMDetailSerializer,
    BOMListSerializer,
    BOMWriteSerializer,
    BoqTaskMappingSerializer,
    BoqTaskMappingWriteSerializer,
    InventoryItemDetailSerializer,
    InventoryItemListSerializer,
    InventoryItemWriteSerializer,
    InventoryStockSerializer,
    InventoryTransactionListSerializer,
    InventoryTransactionWriteSerializer,
    MaterialMasterDetailSerializer,
    MaterialMasterListSerializer,
    MaterialMasterWriteSerializer,
    WarehouseSerializer,
)
from .services import (
    INBOUND_TRANSACTION_TYPES,
    OUTBOUND_TRANSACTION_TYPES,
    recalculate_stock,
)


class InventoryItemFilter(filters.FilterSet):
    class Meta:
        model = InventoryItem
        fields = ["category", "is_active", "preferred_vendor", "expense_account", "cost_center"]


class InventoryStockFilter(filters.FilterSet):
    low_stock = filters.BooleanFilter(method="filter_low_stock")

    class Meta:
        model = InventoryStock
        fields = ["warehouse", "item", "item__category"]

    def filter_low_stock(self, queryset, name, value):
        if value is True:
            return queryset.filter(quantity_on_hand__lte=F("item__reorder_level"))
        if value is False:
            return queryset.exclude(quantity_on_hand__lte=F("item__reorder_level"))
        return queryset


class InventoryTransactionFilter(filters.FilterSet):
    date_from = filters.DateFilter(field_name="transaction_date", lookup_expr="gte")
    date_to = filters.DateFilter(field_name="transaction_date", lookup_expr="lte")

    class Meta:
        model = InventoryTransaction
        fields = [
            "transaction_type",
            "warehouse",
            "item",
            "project",
            "purchase_order",
            "goods_receipt",
        ]


class WarehouseViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    queryset = Warehouse.objects.select_related("project")
    serializer_class = WarehouseSerializer
    search_fields = ["code", "name", "location", "project__name"]
    ordering_fields = ["code", "name", "created_at", "updated_at"]
    ordering = ["name"]


class InventoryItemViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    filterset_class = InventoryItemFilter
    search_fields = ["sku", "name", "description"]
    ordering_fields = ["sku", "name", "category", "created_at", "updated_at"]
    ordering = ["name"]

    def get_queryset(self):
        return super().get_queryset().select_related(
            "preferred_vendor",
            "expense_account",
            "cost_center",
        )

    def get_serializer_class(self):
        if self.action == "list":
            return InventoryItemListSerializer
        if self.action in ("create", "update", "partial_update"):
            return InventoryItemWriteSerializer
        return InventoryItemDetailSerializer


# ---------------------------------------------------------------------------
# Material Master Database
# ---------------------------------------------------------------------------


class MaterialMasterFilter(filters.FilterSet):
    class Meta:
        model = InventoryItem
        fields = ["category", "is_active", "preferred_vendor"]


class MaterialMasterViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    filterset_class = MaterialMasterFilter
    search_fields = ["sku", "name", "description", "subcategory", "material_grade", "hs_code"]
    ordering_fields = ["sku", "name", "category", "default_unit_cost", "lead_time_days", "created_at", "updated_at"]
    ordering = ["name"]

    def get_queryset(self):
        return super().get_queryset().select_related(
            "preferred_vendor",
            "expense_account",
            "cost_center",
        )

    def get_serializer_class(self):
        if self.action == "list":
            return MaterialMasterListSerializer
        if self.action in ("create", "update", "partial_update"):
            return MaterialMasterWriteSerializer
        return MaterialMasterDetailSerializer


class InventoryStockViewSet(OrgScopedMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = InventoryStockSerializer
    filterset_class = InventoryStockFilter
    search_fields = ["item__sku", "item__name", "warehouse__code", "warehouse__name"]
    ordering_fields = ["quantity_on_hand", "average_unit_cost", "updated_at", "item__name"]
    ordering = ["warehouse__name", "item__name"]

    def get_queryset(self):
        return super().get_queryset().select_related("warehouse", "item")


class InventoryTransactionViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    filterset_class = InventoryTransactionFilter
    search_fields = [
        "item__sku",
        "item__name",
        "warehouse__code",
        "warehouse__name",
        "project__name",
        "purchase_order__po_number",
        "goods_receipt__grn_number",
        "source_reference",
        "notes",
    ]
    ordering_fields = ["transaction_date", "created_at", "quantity", "total_cost"]
    ordering = ["-transaction_date", "-created_at", "-id"]

    def get_queryset(self):
        return super().get_queryset().select_related(
            "warehouse",
            "item",
            "project",
            "purchase_order",
            "goods_receipt",
            "performed_by",
        )

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return InventoryTransactionWriteSerializer
        return InventoryTransactionListSerializer

    def perform_create(self, serializer):
        transaction = serializer.save(performed_by=self.request.user)
        recalculate_stock(transaction.item_id, transaction.warehouse_id)

    def perform_update(self, serializer):
        instance = self.get_object()
        old_pair = (instance.item_id, instance.warehouse_id)
        transaction = serializer.save()
        recalculate_stock(transaction.item_id, transaction.warehouse_id)
        if old_pair != (transaction.item_id, transaction.warehouse_id):
            recalculate_stock(old_pair[0], old_pair[1])

    def perform_destroy(self, instance):
        item_id = instance.item_id
        warehouse_id = instance.warehouse_id
        instance.delete()
        recalculate_stock(item_id, warehouse_id)


class InventoryOverviewView(APIView):
    """Cross-module inventory dashboard metrics."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "procurement.receipts"
    rbac_action = "view"

    def get(self, request):
        profile = getattr(request.user, "profile", None)
        org = getattr(profile, "organization", None)
        if org is None:
            return Response(
                {"detail": "Organization context required."},
                status=400,
            )

        today = request.query_params.get("date")
        if today:
            as_of = parse_date(today) or timezone.localdate()
        else:
            as_of = timezone.localdate()

        window_start = as_of - timedelta(days=30)

        stock_qs = InventoryStock.objects.filter(
            item__organization=org,
        ).select_related(
            "item",
            "warehouse",
        )
        low_stock_qs = stock_qs.filter(
            item__is_active=True,
            quantity_on_hand__lte=F("item__reorder_level"),
        )

        stock_value_total = Decimal("0.00")
        for stock in stock_qs:
            stock_value_total += (stock.quantity_on_hand or Decimal("0")) * (
                stock.average_unit_cost or Decimal("0.00")
            )

        tx_qs = InventoryTransaction.objects.filter(
            organization=org,
        ).select_related(
            "item",
            "item__expense_account",
            "item__cost_center",
            "warehouse",
            "project",
        )
        tx_30d = tx_qs.filter(transaction_date__gte=window_start, transaction_date__lte=as_of)
        inbound_30d = tx_30d.filter(transaction_type__in=INBOUND_TRANSACTION_TYPES)
        outbound_30d = tx_30d.filter(transaction_type__in=OUTBOUND_TRANSACTION_TYPES)

        receipts_30d_value = inbound_30d.aggregate(total=Sum("total_cost"))["total"] or Decimal("0.00")
        issues_30d_value = outbound_30d.aggregate(total=Sum("total_cost"))["total"] or Decimal("0.00")

        active_budget_lines = BudgetLineItem.objects.filter(
            budget__status=Budget.Status.ACTIVE,
            budget__organization=org,
        ).values("account_id", "cost_center_id")
        budget_map: dict[int, set[int | None]] = {}
        for line in active_budget_lines:
            account_id = line["account_id"]
            if account_id is None:
                continue
            budget_map.setdefault(account_id, set()).add(line["cost_center_id"])

        budget_covered_issue_value = Decimal("0.00")
        unbudgeted_issue_value = Decimal("0.00")
        for tx in outbound_30d:
            account_id = tx.item.expense_account_id
            cost_center_id = tx.item.cost_center_id
            if account_id is None:
                unbudgeted_issue_value += tx.total_cost or Decimal("0.00")
                continue

            configured = budget_map.get(account_id, set())
            if not configured:
                unbudgeted_issue_value += tx.total_cost or Decimal("0.00")
            elif (None in configured) or (cost_center_id in configured):
                budget_covered_issue_value += tx.total_cost or Decimal("0.00")
            else:
                unbudgeted_issue_value += tx.total_cost or Decimal("0.00")

        recent_transactions = tx_qs.order_by("-transaction_date", "-created_at")[:10]
        project_consumption = (
            outbound_30d.filter(project__isnull=False)
            .values("project_id", "project__name")
            .annotate(total_cost=Sum("total_cost"), movement_count=Count("id"))
            .order_by("-total_cost", "project__name")[:8]
        )

        return Response(
            {
                "as_of_date": as_of.isoformat(),
                "active_items_count": InventoryItem.objects.filter(organization=org, is_active=True).count(),
                "warehouse_count": Warehouse.objects.filter(organization=org, is_active=True).count(),
                "stock_records_count": stock_qs.count(),
                "low_stock_count": low_stock_qs.count(),
                "stock_value_total": str(stock_value_total),
                "receipts_30d_value": str(receipts_30d_value),
                "issues_30d_value": str(issues_30d_value),
                "procurement_linked_receipts": inbound_30d.filter(
                    goods_receipt_item__isnull=False
                ).count(),
                "project_linked_issues": outbound_30d.filter(project__isnull=False).count(),
                "budget_covered_issue_value": str(budget_covered_issue_value),
                "unbudgeted_issue_value": str(unbudgeted_issue_value),
                "low_stock_items": [
                    {
                        "stock_id": row.id,
                        "warehouse_id": row.warehouse_id,
                        "warehouse_name": row.warehouse.name,
                        "item_id": row.item_id,
                        "item_sku": row.item.sku,
                        "item_name": row.item.name,
                        "quantity_on_hand": str(row.quantity_on_hand),
                        "reorder_level": str(row.item.reorder_level),
                        "shortfall": str(
                            (row.item.reorder_level or Decimal("0"))
                            - (row.quantity_on_hand or Decimal("0"))
                        ),
                    }
                    for row in low_stock_qs.order_by("item__name", "warehouse__name")[:12]
                ],
                "recent_transactions": [
                    {
                        "id": tx.id,
                        "transaction_type": tx.transaction_type,
                        "transaction_type_display": tx.get_transaction_type_display(),
                        "transaction_date": tx.transaction_date.isoformat(),
                        "item_sku": tx.item.sku,
                        "item_name": tx.item.name,
                        "warehouse_name": tx.warehouse.name,
                        "project_name": tx.project.name if tx.project else None,
                        "quantity": str(tx.quantity),
                        "total_cost": str(tx.total_cost),
                        "source_module": tx.source_module,
                        "source_reference": tx.source_reference,
                    }
                    for tx in recent_transactions
                ],
                "project_consumption_30d": [
                    {
                        "project_id": row["project_id"],
                        "project_name": row["project__name"],
                        "total_cost": str(row["total_cost"] or Decimal("0.00")),
                        "movement_count": row["movement_count"],
                    }
                    for row in project_consumption
                ],
            }
        )


# ---------------------------------------------------------------------------
# Bill of Materials
# ---------------------------------------------------------------------------


class BOMViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    """CRUD for Bills of Materials with nested items."""

    search_fields = ["bom_number", "name", "project__name", "unit_type"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = (
            BillOfMaterials.objects.filter(organization=self._resolve_request_org())
            .select_related("project", "created_by")
            .prefetch_related("items", "items__inventory_item")
            .annotate(item_count=Count("items"))
            .order_by("-created_at")
        )
        search = self.request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(bom_number__icontains=search)
                | Q(name__icontains=search)
                | Q(project__name__icontains=search)
                | Q(unit_type__icontains=search)
            )
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return BOMListSerializer
        if self.action == "retrieve":
            return BOMDetailSerializer
        return BOMWriteSerializer

    def perform_create(self, serializer):
        serializer.save(
            organization=self._resolve_request_org(),
            created_by=self.request.user,
        )

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["organization"] = self._resolve_request_org()
        return ctx

    @action(detail=True, methods=["post"])
    def clone(self, request, pk=None):
        from rest_framework import status as http_status
        original = self.get_object()
        new_bom = BillOfMaterials.objects.create(
            organization=original.organization,
            name=f"{original.name} (v{original.version + 1})",
            description=original.description, project=original.project,
            unit_type=original.unit_type, quantity_of_units=original.quantity_of_units,
            status="draft", version=original.version + 1, parent_version=original,
            confidence_pct=original.confidence_pct, margin_pct=original.margin_pct,
            vat_pct=original.vat_pct, site_location=original.site_location,
            created_by=request.user,
        )
        from .models import BOMItem
        for item in original.items.all():
            BOMItem.objects.create(
                bom=new_bom, inventory_item=item.inventory_item,
                material_name=item.material_name, category=item.category,
                quantity=item.quantity, unit_of_measure=item.unit_of_measure,
                unit_cost=item.unit_cost, notes=item.notes, sort_order=item.sort_order,
                supplier=item.supplier, is_approved=False,
                price_volatile=item.price_volatile, original_unit_cost=item.unit_cost,
            )
        new_bom.recalculate_total()
        return Response(BOMDetailSerializer(new_bom).data, status=http_status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="expand-bom")
    def expand_bom(self, request, pk=None):
        from .models import BOMItem
        from django.db import models as db_models
        target = self.get_object()
        source_bom_id = request.data.get("source_bom_id")
        multiplier = int(request.data.get("multiplier", 1))
        section_name = request.data.get("section", "")
        if not source_bom_id:
            return Response({"detail": "source_bom_id is required."}, status=400)
        try:
            source = BillOfMaterials.objects.get(pk=source_bom_id, organization=target.organization)
        except BillOfMaterials.DoesNotExist:
            return Response({"detail": "Source BOM not found."}, status=404)
        max_sort = target.items.aggregate(m=db_models.Max("sort_order"))["m"] or 0
        for idx, item in enumerate(source.items.all()):
            BOMItem.objects.create(
                bom=target, inventory_item=item.inventory_item,
                material_name=item.material_name, category=item.category,
                quantity=item.quantity * multiplier, unit_of_measure=item.unit_of_measure,
                unit_cost=item.unit_cost, notes=item.notes, sort_order=max_sort + idx + 1,
                supplier=item.supplier, original_unit_cost=item.unit_cost,
                source_bom=source, section=section_name or source.name,
            )
        target.recalculate_total()
        return Response(BOMDetailSerializer(target).data)

    @action(detail=True, methods=["post"], url_path="apply-fx")
    def apply_fx(self, request, pk=None):
        from .models import BOMItem
        boq = self.get_object()
        new_rate = request.data.get("fx_rate")
        if new_rate is not None:
            boq.fx_rate_usd_ngn = new_rate
            boq.save(update_fields=["fx_rate_usd_ngn"])
        updated = 0
        for item in boq.items.filter(is_fx_linked=True):
            if item.unit_cost_usd and item.unit_cost_usd > 0:
                item.unit_cost = item.unit_cost_usd * boq.fx_rate_usd_ngn
                item.save(update_fields=["unit_cost", "line_total"])
                updated += 1
        boq.recalculate_total()
        return Response({"detail": f"{updated} FX-linked items recalculated.", "bom": BOMDetailSerializer(boq).data})

    @action(detail=False, methods=["get"], url_path="catalog")
    def catalog(self, request):
        org = self._resolve_request_org()
        items = InventoryItem.objects.filter(organization=org).values(
            "id", "name", "category", "unit_of_measure", "default_unit_cost",
        )[:200]
        bom_list = BillOfMaterials.objects.filter(organization=org).values(
            "id", "bom_number", "name", "total_estimated_cost",
        ).annotate(item_count=Count("items"))[:100]
        from apps.procurement.models import Vendor
        vendors = Vendor.objects.filter(
            organization=org, is_active=True, is_blacklisted=False,
        ).values("id", "name", "category", "contact_person")[:200]
        return Response({
            "inventory_items": list(items),
            "bom_templates": list(bom_list),
            "vendors": list(vendors),
        })


    @action(detail=True, methods=["post"], url_path="import-csv")
    def import_csv(self, request, pk=None):
        """12.1: Import BOM items from a CSV/spreadsheet upload."""
        import csv
        import io
        from decimal import Decimal, InvalidOperation

        bom = self.get_object()
        file = request.FILES.get("file")
        if not file:
            return Response({"detail": "No file uploaded."}, status=400)

        try:
            decoded = file.read().decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(decoded))
        except Exception:
            return Response({"detail": "Could not parse CSV file."}, status=400)

        from .models import BOMItem
        created = 0
        errors = []
        max_sort = bom.items.aggregate(m=Count("id"))["m"] or 0

        for idx, row in enumerate(reader, start=2):
            # Normalize column headers (case-insensitive, strip whitespace)
            row = {k.strip().lower().replace(" ", "_"): v.strip() for k, v in row.items() if k}

            name = row.get("description") or row.get("material_name") or row.get("item") or row.get("name", "")
            if not name:
                errors.append(f"Row {idx}: missing description/name")
                continue

            try:
                qty = Decimal(str(row.get("quantity") or row.get("qty") or "1"))
            except (InvalidOperation, ValueError):
                qty = Decimal("1")

            try:
                unit_cost = Decimal(str(row.get("unit_rate") or row.get("unit_cost") or row.get("rate") or "0"))
            except (InvalidOperation, ValueError):
                unit_cost = Decimal("0")

            BOMItem.objects.create(
                bom=bom,
                material_name=name,
                category=row.get("category") or row.get("section") or "",
                quantity=qty,
                unit_of_measure=row.get("unit") or row.get("uom") or row.get("unit_of_measure") or "ea",
                unit_cost=unit_cost,
                notes=row.get("notes") or row.get("remarks") or "",
                sort_order=max_sort + created,
                section=row.get("section") or row.get("location") or "",
            )
            created += 1

        bom.recalculate_total()

        return Response({
            "detail": f"{created} item(s) imported successfully.",
            "created": created,
            "errors": errors[:20],
        })


class BOMItemViewSet(viewsets.ModelViewSet):
    """CRUD for individual BOM line items."""
    from .serializers import BOMItemSerializer
    serializer_class = BOMItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from .models import BOMItem
        return BOMItem.objects.filter(bom_id=self.kwargs["bom_pk"]).select_related("inventory_item", "supplier_vendor")

    def perform_create(self, serializer):
        bom = BillOfMaterials.objects.get(pk=self.kwargs["bom_pk"])
        serializer.save(bom=bom)


# ── BOQ Category Mapping ──────────────────────────────────────────────

from .models import BoqCategoryMapping
from .serializers import BoqCategoryMappingSerializer


class BoqCategoryMappingViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    serializer_class = BoqCategoryMappingSerializer
    search_fields = ["boq_category"]

    def get_queryset(self):
        return BoqCategoryMapping.objects.filter(
            organization=self._resolve_request_org(),
        ).select_related("template_phase", "template_phase__template").order_by("sort_order")

    def perform_create(self, serializer):
        serializer.save(organization=self._resolve_request_org())


# ── Rate Library ─────────────────────────────────────────────────────

from .models import RateBook, RateItem, RateCompositeComponent, RateHistory
from .serializers import (
    RateBookListSerializer, RateBookWriteSerializer,
    RateItemListSerializer, RateItemDetailSerializer, RateItemWriteSerializer,
    RateCompositeComponentSerializer,
)


class RateBookViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    search_fields = ["name"]

    def get_queryset(self):
        return RateBook.objects.filter(organization=self._resolve_request_org()).annotate(item_count=Count("items")).order_by("-is_active", "-updated_at")

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return RateBookWriteSerializer
        return RateBookListSerializer

    def perform_create(self, serializer):
        serializer.save(organization=self._resolve_request_org(), created_by=self.request.user)

    @action(detail=True, methods=["post"], url_path="bulk-adjust")
    def bulk_adjust(self, request, pk=None):
        from decimal import Decimal
        book = self.get_object()
        category = request.data.get("category", "")
        adjust_pct = Decimal(str(request.data.get("adjust_pct", 0)))
        qs = book.items.all()
        if category:
            qs = qs.filter(category=category)
        updated = 0
        for item in qs:
            item.base_rate = item.base_rate * (1 + adjust_pct / 100)
            item.save(update_fields=["base_rate", "updated_at"])
            RateHistory.objects.create(rate_item=item, rate=item.base_rate, changed_by=request.user, notes=f"Bulk adjust {adjust_pct:+.1f}%")
            updated += 1
        return Response({"detail": f"{updated} rates adjusted by {adjust_pct:+.1f}%."})


class RateItemViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    search_fields = ["item_code", "description", "location"]
    filterset_fields = ["category", "status", "is_composite", "is_fx_linked"]

    def get_queryset(self):
        return RateItem.objects.filter(rate_book_id=self.kwargs["book_pk"]).select_related("supplier_vendor").prefetch_related("components__component_rate", "history")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return RateItemDetailSerializer
        if self.action in ("create", "update", "partial_update"):
            return RateItemWriteSerializer
        return RateItemListSerializer

    def perform_create(self, serializer):
        book = RateBook.objects.get(pk=self.kwargs["book_pk"])
        instance = serializer.save(rate_book=book, updated_by=self.request.user)
        RateHistory.objects.create(rate_item=instance, rate=instance.base_rate, changed_by=self.request.user, notes="Created")

    def perform_update(self, serializer):
        old_rate = serializer.instance.base_rate
        instance = serializer.save(updated_by=self.request.user)
        if instance.base_rate != old_rate:
            RateHistory.objects.create(rate_item=instance, rate=instance.base_rate, changed_by=self.request.user, notes="Rate updated")


class RateCompositeComponentViewSet(viewsets.ModelViewSet):
    serializer_class = RateCompositeComponentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return RateCompositeComponent.objects.filter(composite_rate_id=self.kwargs["rate_pk"]).select_related("component_rate")

    def perform_create(self, serializer):
        rate = RateItem.objects.get(pk=self.kwargs["rate_pk"])
        serializer.save(composite_rate=rate)


# ── BoQ → Schedule Mapping ───────────────────────────────────────────


class BoqTaskMappingViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "inventory.inventory"
    rbac_action_map = {
        "list": "view", "retrieve": "view",
        "create": "edit", "update": "edit", "partial_update": "edit", "destroy": "edit",
    }
    filterset_fields = ["bom", "project", "phase", "task", "material_status"]
    search_fields = ["bom_item__material_name", "notes"]
    ordering = ["bom", "bom_item__sort_order"]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return BoqTaskMappingWriteSerializer
        return BoqTaskMappingSerializer

    def get_queryset(self):
        return (
            BoqTaskMapping.objects.filter(organization=self._resolve_request_org())
            .select_related("bom", "bom_item", "bom_item__section", "project", "phase", "task")
        )

    def perform_create(self, serializer):
        serializer.save(organization=self._resolve_request_org())


# ── Material Requisition (Site Requests) ─────────────────────────────

from .models import MaterialRequisition, MaterialRequisitionLine, MaterialRequisitionComment, MaterialRequisitionAuditLog
from .serializers import (
    MaterialRequisitionListSerializer, MaterialRequisitionDetailSerializer,
    MaterialRequisitionWriteSerializer, MaterialRequisitionLineSerializer,
    MaterialRequisitionCommentSerializer,
)


class MaterialRequisitionViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    search_fields = ["requisition_id", "project__name", "site_location", "justification"]
    filterset_fields = ["project", "phase", "status", "urgency", "current_step"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return (
            MaterialRequisition.objects.filter(organization=self._resolve_request_org())
            .select_related("project", "phase", "created_by")
            .annotate(line_count=Count("lines"))
        )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return MaterialRequisitionDetailSerializer
        if self.action in ("create", "update", "partial_update"):
            return MaterialRequisitionWriteSerializer
        return MaterialRequisitionListSerializer

    def perform_create(self, serializer):
        instance = serializer.save(
            organization=self._resolve_request_org(),
            created_by=self.request.user,
        )
        MaterialRequisitionAuditLog.objects.create(
            requisition=instance, action="created",
            performed_by=self.request.user, notes="Requisition created",
        )

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        """Submit requisition for approval workflow."""
        req = self.get_object()
        if req.status not in ("draft", "needs_revision"):
            return Response({"detail": "Only draft or needs-revision requisitions can be submitted."}, status=400)
        if not req.lines.exists():
            return Response({"detail": "Add at least one material line before submitting."}, status=400)

        from django.utils import timezone as tz
        req.status = "pending_pm"
        req.current_step = "project_manager"
        req.submitted_at = tz.now()
        req.save(update_fields=["status", "current_step", "submitted_at", "updated_at"])

        MaterialRequisitionAuditLog.objects.create(
            requisition=req, action="submitted", field_changed="status",
            old_value="draft", new_value="pending_pm",
            performed_by=request.user, notes="Submitted for PM approval",
        )

        try:
            from apps.notifications.services import dispatch_workflow_notification
            from apps.notifications.models import Notification
            from apps.accounts.models import UserProfile
            admins = [p.user for p in UserProfile.objects.filter(
                organization=req.organization, role__in=["admin", "manager"], user__is_active=True,
            ).select_related("user")]
            dispatch_workflow_notification(
                organization=req.organization,
                event_key="material_requisition_submitted",
                recipients=admins,
                link_url="/material-management/requisitions",
                fallback_channels=["in_app"],
                fallback_title=f"Material Requisition — {req.requisition_id}",
                fallback_message=f"Material requisition '{req.requisition_id}' for project '{req.project.name}' submitted. {req.lines.count()} line(s), urgency: {req.get_urgency_display()}.",
                fallback_category=Notification.Category.PROCUREMENT_ORDER,
                fallback_severity=Notification.Severity.WARNING if req.urgency in ("high", "critical") else Notification.Severity.INFO,
            )
        except Exception:
            pass

        return Response(MaterialRequisitionDetailSerializer(req).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Approve at the current workflow step."""
        req = self.get_object()
        user_name = request.user.get_full_name() or request.user.email
        from django.utils import timezone as tz

        transitions = {
            "pending_pm": ("approved_by_pm", "approved_by_pm_at", "pending_proc", "procurement"),
            "pending_proc": ("approved_by_proc", "approved_by_proc_at", "pending_store", "store"),
        }
        if req.status not in transitions:
            return Response({"detail": f"Cannot approve in status '{req.status}'."}, status=400)

        field_name, field_date, next_status, next_step = transitions[req.status]
        old_status = req.status
        setattr(req, field_name, user_name)
        setattr(req, field_date, tz.now())
        req.status = next_status
        req.current_step = next_step
        req.save(update_fields=[field_name, field_date, "status", "current_step", "updated_at"])

        MaterialRequisitionAuditLog.objects.create(
            requisition=req, action="approved", field_changed="status",
            old_value=old_status, new_value=next_status,
            performed_by=request.user, notes=f"Approved by {user_name}",
        )
        return Response(MaterialRequisitionDetailSerializer(req).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Reject the requisition."""
        req = self.get_object()
        reason = request.data.get("reason", "")
        from django.utils import timezone as tz
        old_status = req.status
        req.status = "rejected"
        req.rejected_by = request.user.get_full_name() or request.user.email
        req.rejected_at = tz.now()
        req.rejection_reason = reason
        req.save(update_fields=["status", "rejected_by", "rejected_at", "rejection_reason", "updated_at"])

        MaterialRequisitionAuditLog.objects.create(
            requisition=req, action="rejected", field_changed="status",
            old_value=old_status, new_value="rejected",
            performed_by=request.user, notes=f"Rejected: {reason[:200]}",
        )
        return Response(MaterialRequisitionDetailSerializer(req).data)

    @action(detail=True, methods=["post"], url_path="request-revision")
    def request_revision(self, request, pk=None):
        """Send back to submitter for revision."""
        req = self.get_object()
        reason = request.data.get("reason", "")
        old_status = req.status
        req.status = "needs_revision"
        req.current_step = "site_engineer"
        req.save(update_fields=["status", "current_step", "updated_at"])

        MaterialRequisitionAuditLog.objects.create(
            requisition=req, action="revision_requested", field_changed="status",
            old_value=old_status, new_value="needs_revision",
            performed_by=request.user, notes=f"Revision requested: {reason[:200]}",
        )
        return Response(MaterialRequisitionDetailSerializer(req).data)

    @action(detail=True, methods=["post"], url_path="fulfil-line")
    def fulfil_line(self, request, pk=None):
        """Store officer issues materials for a specific line."""
        req = self.get_object()
        line_id = request.data.get("line_id")
        issued_qty = request.data.get("issued_quantity")
        if not line_id or issued_qty is None:
            return Response({"detail": "line_id and issued_quantity required."}, status=400)
        try:
            line = req.lines.get(pk=line_id)
        except MaterialRequisitionLine.DoesNotExist:
            return Response({"detail": "Line not found."}, status=404)

        from decimal import Decimal as D
        from django.utils import timezone as tz
        line.issued_quantity = D(str(issued_qty))
        line.issued_at = tz.now()
        line.issued_by = request.user.get_full_name() or request.user.email
        line.save(update_fields=["issued_quantity", "issued_at", "issued_by"])

        all_lines = req.lines.all()
        total_req = sum(float(l.quantity) for l in all_lines)
        total_issued = sum(float(l.issued_quantity) for l in all_lines)
        if total_issued >= total_req:
            req.status = "fulfilled"
            req.fulfilled_by_store = request.user.get_full_name() or request.user.email
            req.fulfilled_at = tz.now()
        elif total_issued > 0:
            req.status = "partially_fulfilled"
        req.save(update_fields=["status", "fulfilled_by_store", "fulfilled_at", "updated_at"])

        MaterialRequisitionAuditLog.objects.create(
            requisition=req, action="line_fulfilled",
            field_changed=f"line_{line_id}.issued_quantity",
            old_value="0", new_value=str(issued_qty),
            performed_by=request.user, notes=f"Issued {issued_qty} {line.unit_of_measure} of {line.material_name}",
        )
        return Response(MaterialRequisitionDetailSerializer(req).data)


class MaterialRequisitionLineViewSet(viewsets.ModelViewSet):
    serializer_class = MaterialRequisitionLineSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return MaterialRequisitionLine.objects.filter(
            requisition_id=self.kwargs["requisition_pk"],
        ).select_related("material", "issued_from_warehouse")

    def perform_create(self, serializer):
        serializer.save(requisition_id=self.kwargs["requisition_pk"])


class MaterialRequisitionCommentViewSet(viewsets.ModelViewSet):
    serializer_class = MaterialRequisitionCommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return MaterialRequisitionComment.objects.filter(
            requisition_id=self.kwargs["requisition_pk"],
        ).select_related("author")

    def perform_create(self, serializer):
        serializer.save(
            requisition_id=self.kwargs["requisition_pk"],
            author=self.request.user,
        )


# ── Procurement Integration Pipeline View ────────────────────────────


class ProcurementIntegrationView(APIView):
    """
    Aggregates the full material-to-purchase pipeline:
    Material Requisition → Purchase Requisition → RFQ → Vendor Selection → PO
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.accounts.mixins import OrgScopedMixin
        from apps.procurement.models import PurchaseRequisition, RequestForQuotation, PurchaseOrder

        org = request.user.profile.organization

        # Material Requisitions
        mat_reqs = MaterialRequisition.objects.filter(organization=org).values("status").annotate(count=Count("id"))
        mat_req_by_status = {r["status"]: r["count"] for r in mat_reqs}
        mat_req_total = MaterialRequisition.objects.filter(organization=org).count()

        # Purchase Requisitions
        prs = PurchaseRequisition.objects.filter(organization=org).values("status").annotate(count=Count("id"))
        pr_by_status = {r["status"]: r["count"] for r in prs}
        pr_total = PurchaseRequisition.objects.filter(organization=org).count()

        # RFQs
        rfqs = RequestForQuotation.objects.filter(organization=org).values("status").annotate(count=Count("id"))
        rfq_by_status = {r["status"]: r["count"] for r in rfqs}
        rfq_total = RequestForQuotation.objects.filter(organization=org).count()

        # POs
        pos = PurchaseOrder.objects.filter(organization=org).values("status").annotate(count=Count("id"))
        po_by_status = {r["status"]: r["count"] for r in pos}
        po_total = PurchaseOrder.objects.filter(organization=org).count()

        # Pipeline records — recent items across stages
        from django.db.models import CharField, Value
        from itertools import chain

        pipeline_items = []

        # Material Requisitions in progress
        active_mat_reqs = MaterialRequisition.objects.filter(
            organization=org,
        ).exclude(status__in=["fulfilled", "rejected", "cancelled"]).select_related("project", "created_by").order_by("-created_at")[:20]

        for mr in active_mat_reqs:
            # Find linked PR (if any)
            linked_pr = PurchaseRequisition.objects.filter(
                organization=org, project=mr.project,
                title__icontains=mr.requisition_id,
            ).first()

            linked_rfq = None
            linked_po = None
            if linked_pr:
                linked_rfq = RequestForQuotation.objects.filter(requisition=linked_pr).first()
                linked_po = PurchaseOrder.objects.filter(requisition=linked_pr).first()

            # Determine pipeline stage
            if linked_po:
                stage = "purchase_order"
                stage_status = linked_po.status
            elif linked_rfq:
                stage = "rfq"
                stage_status = linked_rfq.status
            elif linked_pr:
                stage = "purchase_requisition"
                stage_status = linked_pr.status
            else:
                stage = "material_requisition"
                stage_status = mr.status

            pipeline_items.append({
                "id": mr.id,
                "requisition_id": mr.requisition_id,
                "project_name": mr.project.name if mr.project_id else "",
                "urgency": mr.urgency,
                "created_at": mr.created_at.isoformat(),
                "stage": stage,
                "stage_status": stage_status,
                "mat_req_status": mr.status,
                "pr_number": linked_pr.pr_number if linked_pr else None,
                "pr_status": linked_pr.status if linked_pr else None,
                "rfq_number": linked_rfq.rfq_number if linked_rfq else None,
                "rfq_status": linked_rfq.status if linked_rfq else None,
                "po_number": linked_po.po_number if linked_po else None,
                "po_status": linked_po.status if linked_po else None,
                "estimated_total": str(mr.estimated_total),
                "line_count": mr.lines.count(),
            })

        return Response({
            "summary": {
                "material_requisitions": {"total": mat_req_total, "by_status": mat_req_by_status},
                "purchase_requisitions": {"total": pr_total, "by_status": pr_by_status},
                "rfqs": {"total": rfq_total, "by_status": rfq_by_status},
                "purchase_orders": {"total": po_total, "by_status": po_by_status},
            },
            "pipeline": pipeline_items,
        })


class ProcurementBridgeView(APIView):
    """
    The 'Procurement Bridge' — returns approved material requisition lines
    ready for conversion into Purchase Requests. Supports bulk PR creation
    and requisition merging.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return all approved/pending_proc requisition lines not yet linked to a PR."""
        org = request.user.profile.organization
        from django.utils import timezone as tz

        today = tz.localdate()

        # Get approved requisitions pending procurement action
        pending_reqs = MaterialRequisition.objects.filter(
            organization=org,
            status__in=["pending_proc", "pending_store"],
        ).select_related("project", "phase", "created_by").prefetch_related("lines__material")

        bridge_items = []
        for req in pending_reqs:
            for line in req.lines.all():
                days_until = (line.required_by_date - today).days if line.required_by_date else 999
                bridge_items.append({
                    "req_id": req.id,
                    "requisition_id": req.requisition_id,
                    "line_id": line.id,
                    "project_id": req.project_id,
                    "project_name": req.project.name if req.project_id else "",
                    "phase_name": req.phase.name if req.phase_id else "",
                    "site_location": req.site_location,
                    "urgency": req.urgency,
                    "material_id": line.material_id,
                    "material_name": line.material_name,
                    "material_code": line.material.sku if line.material_id else "",
                    "material_category": line.material.category if line.material_id else "",
                    "quantity": str(line.quantity),
                    "unit_of_measure": line.unit_of_measure,
                    "unit_cost": str(line.unit_cost),
                    "estimated_cost": str(line.estimated_cost),
                    "available_stock": str(line.available_stock),
                    "stock_sufficient": float(line.available_stock) >= float(line.quantity),
                    "required_by_date": str(line.required_by_date) if line.required_by_date else None,
                    "days_until_required": days_until,
                    "date_urgency": "critical" if days_until < 7 else "warning" if days_until < 14 else "normal",
                    "created_by": req.created_by.get_full_name() if req.created_by else "",
                    "created_at": req.created_at.isoformat(),
                })

        return Response({
            "items": bridge_items,
            "total_count": len(bridge_items),
            "critical_count": sum(1 for i in bridge_items if i["date_urgency"] == "critical"),
            "stock_sufficient_count": sum(1 for i in bridge_items if i["stock_sufficient"]),
            "total_value": str(sum(float(i["estimated_cost"]) for i in bridge_items)),
        })

    def post(self, request):
        """
        Bulk create Purchase Requests from selected bridge items.
        Supports merging: group multiple requisition lines into one PR.
        """
        org = request.user.profile.organization
        line_ids = request.data.get("line_ids", [])
        merge = request.data.get("merge", False)

        if not line_ids:
            return Response({"detail": "No line_ids provided."}, status=400)

        from apps.procurement.models import PurchaseRequisition, PurchaseRequisitionItem
        from django.utils import timezone as tz

        lines = MaterialRequisitionLine.objects.filter(
            id__in=line_ids,
            requisition__organization=org,
            requisition__status__in=["pending_proc", "pending_store"],
        ).select_related("requisition__project", "material")

        if not lines.exists():
            return Response({"detail": "No valid lines found."}, status=404)

        created_prs = []

        if merge:
            # Group all lines into one PR
            first_req = lines[0].requisition
            pr = PurchaseRequisition.objects.create(
                organization=org,
                title=f"Merged PR — {len(lines)} items from {len(set(l.requisition_id for l in lines))} requisitions",
                requester=request.user.get_full_name() or "System",
                project=first_req.project,
                priority="high" if any(l.requisition.urgency in ("high", "critical") for l in lines) else "medium",
                required_date=min(
                    (l.required_by_date for l in lines if l.required_by_date),
                    default=tz.localdate() + tz.timedelta(days=14),
                ),
                justification=f"Merged from material requisitions: {', '.join(set(l.requisition.requisition_id for l in lines))}.",
            )
            for idx, line in enumerate(lines):
                PurchaseRequisitionItem.objects.create(
                    requisition=pr,
                    description=line.material_name,
                    quantity=line.quantity,
                    unit_of_measure=line.unit_of_measure,
                    estimated_unit_price=line.unit_cost,
                    sort_order=idx,
                )
            pr.recalculate_totals()
            created_prs.append({"pr_number": pr.pr_number, "item_count": lines.count(), "total": str(pr.estimated_total)})
        else:
            # One PR per requisition
            reqs_grouped = {}
            for line in lines:
                reqs_grouped.setdefault(line.requisition_id, []).append(line)

            for req_id, req_lines in reqs_grouped.items():
                req = req_lines[0].requisition
                pr = PurchaseRequisition.objects.create(
                    organization=org,
                    title=f"PR from {req.requisition_id}",
                    requester=request.user.get_full_name() or "System",
                    project=req.project,
                    priority=req.urgency if req.urgency in ("high", "critical") else "medium",
                    required_date=req.requested_delivery_date or (tz.localdate() + tz.timedelta(days=14)),
                    justification=f"Auto-generated from material requisition {req.requisition_id}. {req.justification}",
                )
                for idx, line in enumerate(req_lines):
                    PurchaseRequisitionItem.objects.create(
                        requisition=pr,
                        description=line.material_name,
                        quantity=line.quantity,
                        unit_of_measure=line.unit_of_measure,
                        estimated_unit_price=line.unit_cost,
                        sort_order=idx,
                    )
                pr.recalculate_totals()
                created_prs.append({"pr_number": pr.pr_number, "item_count": len(req_lines), "total": str(pr.estimated_total)})

        # Update requisition statuses
        affected_req_ids = set(l.requisition_id for l in lines)
        MaterialRequisition.objects.filter(id__in=affected_req_ids).update(status="pending_store")

        return Response({
            "detail": f"{len(created_prs)} Purchase Request(s) created.",
            "created": created_prs,
        }, status=201)


# ── Goods Receipt Dashboard ──────────────────────────────────────────


class GoodsReceiptPOLookupView(APIView):
    """Lookup a PO by number — returns vendor, items, and expected quantities for arrival logging."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.procurement.models import PurchaseOrder, PurchaseOrderItem, GoodsReceiptItem
        from django.db.models import Sum as DbSum

        org = request.user.profile.organization
        po_number = request.query_params.get("po_number", "").strip()
        po_id = request.query_params.get("po_id", "")

        if not po_number and not po_id:
            return Response({"detail": "po_number or po_id is required."}, status=400)

        try:
            if po_id:
                po = PurchaseOrder.objects.select_related("vendor", "project").get(pk=po_id, organization=org)
            else:
                po = PurchaseOrder.objects.select_related("vendor", "project").get(po_number__iexact=po_number, organization=org)
        except PurchaseOrder.DoesNotExist:
            return Response({"detail": "PO not found."}, status=404)

        # Get items with received-so-far quantities
        items = []
        for item in po.items.all().order_by("sort_order"):
            already_received = GoodsReceiptItem.objects.filter(
                po_item=item,
            ).aggregate(total=DbSum("quantity_received"))["total"] or 0
            remaining = max(0, float(item.quantity) - float(already_received))

            items.append({
                "po_item_id": item.id,
                "description": item.description,
                "ordered_quantity": str(item.quantity),
                "unit_of_measure": item.unit_of_measure,
                "unit_price": str(item.unit_price),
                "already_received": str(already_received),
                "remaining": str(remaining),
                "fully_received": remaining <= 0,
            })

        return Response({
            "po_id": po.id,
            "po_number": po.po_number,
            "vendor_id": po.vendor_id,
            "vendor_name": po.vendor.name if po.vendor_id else "",
            "project_name": po.project.name if po.project_id else "",
            "status": po.status,
            "expected_delivery_date": str(po.expected_delivery_date) if po.expected_delivery_date else None,
            "total_amount": str(po.total_amount or 0),
            "items": items,
            "all_received": all(i["fully_received"] for i in items),
        })


class GoodsReceiptLogArrivalView(APIView):
    """Log a material arrival — creates GRN with line items, supports partial receipt."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from apps.procurement.models import GoodsReceipt, GoodsReceiptItem, PurchaseOrder, PurchaseOrderItem
        from django.utils import timezone as tz

        org = request.user.profile.organization
        po_id = request.data.get("po_id")
        received_by = request.data.get("received_by", request.user.get_full_name() or request.user.email)
        delivery_note = request.data.get("delivery_note_number", "")
        notes = request.data.get("notes", "")
        line_items = request.data.get("items", [])

        if not po_id:
            return Response({"detail": "po_id is required."}, status=400)
        if not line_items:
            return Response({"detail": "At least one item is required."}, status=400)

        try:
            po = PurchaseOrder.objects.get(pk=po_id, organization=org)
        except PurchaseOrder.DoesNotExist:
            return Response({"detail": "PO not found."}, status=404)

        grn = GoodsReceipt.objects.create(
            organization=org,
            purchase_order=po,
            status="pending",
            received_date=tz.localdate(),
            received_by=received_by,
            delivery_note_number=delivery_note,
            notes=notes,
        )

        created_items = 0
        for item_data in line_items:
            po_item_id = item_data.get("po_item_id")
            qty_received = item_data.get("quantity_received", 0)

            if not po_item_id or float(qty_received) <= 0:
                continue

            try:
                po_item = PurchaseOrderItem.objects.get(pk=po_item_id, purchase_order=po)
            except PurchaseOrderItem.DoesNotExist:
                continue

            from decimal import Decimal as D
            GoodsReceiptItem.objects.create(
                goods_receipt=grn,
                po_item=po_item,
                quantity_received=D(str(qty_received)),
                quantity_accepted=D(str(qty_received)),  # Default: all accepted pending QC
                batch_number=item_data.get("batch_number", ""),
                expiry_date=item_data.get("expiry_date") or None,
                storage_location=item_data.get("storage_location", ""),
                notes=item_data.get("notes", ""),
            )
            created_items += 1

        # Update PO status
        po.update_status_from_receipts()

        return Response({
            "grn_id": grn.id,
            "grn_number": grn.grn_number,
            "items_received": created_items,
            "detail": f"GRN {grn.grn_number} created with {created_items} item(s).",
        }, status=201)


class GoodsReceiptInspectView(APIView):
    """Quality Inspection — update GRN item status (pass/fail/conditional) with notes."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get GRN detail with items for inspection."""
        from apps.procurement.models import GoodsReceipt, GoodsReceiptItem

        org = request.user.profile.organization
        grn_id = request.query_params.get("grn_id")
        if not grn_id:
            return Response({"detail": "grn_id is required."}, status=400)

        try:
            grn = GoodsReceipt.objects.select_related(
                "purchase_order__vendor", "purchase_order__project",
            ).get(pk=grn_id, organization=org)
        except GoodsReceipt.DoesNotExist:
            return Response({"detail": "GRN not found."}, status=404)

        items = []
        for item in grn.items.select_related("po_item").all():
            items.append({
                "id": item.id,
                "description": item.po_item.description,
                "ordered_quantity": str(item.po_item.quantity),
                "unit_of_measure": item.po_item.unit_of_measure,
                "quantity_received": str(item.quantity_received),
                "quantity_accepted": str(item.quantity_accepted),
                "quantity_rejected": str(item.quantity_rejected),
                "quality_status": item.quality_status,
                "inspected_by": item.inspected_by,
                "inspected_date": str(item.inspected_date) if item.inspected_date else None,
                "quality_notes": item.quality_notes,
                "rejection_reason": item.rejection_reason,
                "batch_number": item.batch_number,
                "expiry_date": str(item.expiry_date) if item.expiry_date else None,
                "storage_location": item.storage_location,
            })

        return Response({
            "grn_id": grn.id,
            "grn_number": grn.grn_number,
            "status": grn.status,
            "received_date": str(grn.received_date),
            "received_by": grn.received_by,
            "po_number": grn.purchase_order.po_number,
            "vendor_name": grn.purchase_order.vendor.name if grn.purchase_order.vendor_id else "",
            "project_name": grn.purchase_order.project.name if grn.purchase_order.project_id else "",
            "inspection_notes": grn.inspection_notes,
            "items": items,
        })

    def post(self, request):
        """Submit inspection results for GRN items."""
        from apps.procurement.models import GoodsReceipt, GoodsReceiptItem
        from django.utils import timezone as tz
        from decimal import Decimal as D

        org = request.user.profile.organization
        grn_id = request.data.get("grn_id")
        inspection_notes = request.data.get("inspection_notes", "")
        item_inspections = request.data.get("items", [])

        if not grn_id:
            return Response({"detail": "grn_id is required."}, status=400)

        try:
            grn = GoodsReceipt.objects.get(pk=grn_id, organization=org)
        except GoodsReceipt.DoesNotExist:
            return Response({"detail": "GRN not found."}, status=404)

        inspector_name = request.user.get_full_name() or request.user.email
        today = tz.localdate()
        updated = 0

        for item_data in item_inspections:
            item_id = item_data.get("id")
            quality_status = item_data.get("quality_status", "pending")
            quality_notes = item_data.get("quality_notes", "")
            quantity_accepted = item_data.get("quantity_accepted")
            quantity_rejected = item_data.get("quantity_rejected", 0)
            rejection_reason = item_data.get("rejection_reason", "")

            try:
                item = GoodsReceiptItem.objects.get(pk=item_id, goods_receipt=grn)
            except GoodsReceiptItem.DoesNotExist:
                continue

            item.quality_status = quality_status
            item.quality_notes = quality_notes
            item.inspected_by = inspector_name
            item.inspected_date = today
            if quantity_accepted is not None:
                item.quantity_accepted = D(str(quantity_accepted))
            if quantity_rejected:
                item.quantity_rejected = D(str(quantity_rejected))
            if rejection_reason:
                item.rejection_reason = rejection_reason
            item.save()
            updated += 1

        # Update GRN status based on item inspections
        all_items = grn.items.all()
        all_statuses = [i.quality_status for i in all_items]
        if all(s == "passed" for s in all_statuses):
            grn.status = "accepted"
        elif all(s == "failed" for s in all_statuses):
            grn.status = "rejected"
        elif any(s in ("passed", "conditional") for s in all_statuses) and any(s == "failed" for s in all_statuses):
            grn.status = "partially_accepted"
        elif any(s in ("passed", "conditional") for s in all_statuses):
            grn.status = "inspected"
        grn.inspection_notes = inspection_notes
        grn.save(update_fields=["status", "inspection_notes", "updated_at"] if hasattr(grn, "updated_at") else ["status", "inspection_notes"])

        return Response({
            "detail": f"{updated} item(s) inspected. GRN status: {grn.get_status_display()}.",
            "grn_status": grn.status,
        })


class WarehouseDashboardView(APIView):
    """Logistics overview — warehouse metrics, capacity alerts, stock distribution."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Sum as DbSum, Count as DbCount, Value, CharField
        from decimal import Decimal as D

        org = request.user.profile.organization

        warehouses = Warehouse.objects.filter(organization=org, is_active=True)
        total_locations = warehouses.count()

        # Per-warehouse stock data
        warehouse_data = []
        capacity_alert_count = 0
        total_stock_value = D("0")

        for wh in warehouses:
            stocks = InventoryStock.objects.filter(warehouse=wh)
            item_count = stocks.count()
            total_qty = stocks.aggregate(total=DbSum("quantity_on_hand"))["total"] or D("0")

            # Calculate value: qty × item default_unit_cost
            stock_value = D("0")
            for s in stocks.select_related("item"):
                stock_value += (s.quantity_on_hand or D("0")) * (s.item.default_unit_cost or D("0"))
            total_stock_value += stock_value

            # Capacity check
            capacity_pct = 0
            if wh.storage_capacity_units and wh.storage_capacity_units > 0:
                capacity_pct = round(float(total_qty) / wh.storage_capacity_units * 100)
            if capacity_pct > 90:
                capacity_alert_count += 1

            # Top 3 materials by quantity
            top_materials = list(
                stocks.select_related("item").order_by("-quantity_on_hand")[:3].values(
                    "item__name", "item__category", "quantity_on_hand",
                )
            )
            top_mats = [
                {"name": m["item__name"], "category": m["item__category"], "qty": str(m["quantity_on_hand"])}
                for m in top_materials
            ]

            warehouse_data.append({
                "id": wh.id,
                "code": wh.code,
                "name": wh.name,
                "location": wh.location,
                "warehouse_type": wh.warehouse_type,
                "project_name": wh.project.name if wh.project_id else "",
                "is_default": wh.is_default,
                "contact_person": wh.contact_person,
                "contact_phone": wh.contact_phone,
                "gps_coordinates": wh.gps_coordinates,
                "storage_capacity": wh.storage_capacity_units,
                "item_count": item_count,
                "total_quantity": str(total_qty),
                "stock_value": str(round(stock_value, 2)),
                "capacity_pct": capacity_pct,
                "capacity_alert": capacity_pct > 90,
                "top_materials": top_mats,
            })

        # In-transit value (issued POs not yet fully received)
        from apps.procurement.models import PurchaseOrder
        in_transit = PurchaseOrder.objects.filter(
            organization=org,
            status="issued",
        ).aggregate(total=DbSum("total_amount"))["total"] or D("0")

        return Response({
            "total_locations": total_locations,
            "capacity_alert_count": capacity_alert_count,
            "in_transit_value": str(in_transit),
            "total_stock_value": str(round(total_stock_value, 2)),
            "warehouses": warehouse_data,
        })


class GoodsReceiptPhotoUploadView(APIView):
    """Upload/list photos for a GRN — supports multipart file upload."""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        from apps.procurement.models import GoodsReceiptPhoto
        from apps.procurement.serializers import GoodsReceiptPhotoSerializer

        org = request.user.profile.organization
        grn_id = request.query_params.get("grn_id")
        if not grn_id:
            return Response({"detail": "grn_id is required."}, status=400)

        photos = GoodsReceiptPhoto.objects.filter(
            goods_receipt_id=grn_id, goods_receipt__organization=org,
        ).select_related("uploaded_by").order_by("-created_at")

        return Response({
            "photos": GoodsReceiptPhotoSerializer(photos, many=True, context={"request": request}).data,
        })

    def post(self, request):
        from apps.procurement.models import GoodsReceipt, GoodsReceiptPhoto

        org = request.user.profile.organization
        grn_id = request.data.get("grn_id")
        if not grn_id:
            return Response({"detail": "grn_id is required."}, status=400)

        try:
            grn = GoodsReceipt.objects.get(pk=grn_id, organization=org)
        except GoodsReceipt.DoesNotExist:
            return Response({"detail": "GRN not found."}, status=404)

        image = request.FILES.get("image")
        if not image:
            return Response({"detail": "No image file provided."}, status=400)

        photo = GoodsReceiptPhoto.objects.create(
            goods_receipt=grn,
            receipt_item_id=request.data.get("receipt_item_id") or None,
            image=image,
            caption=request.data.get("caption", ""),
            photo_type=request.data.get("photo_type", "delivery"),
            uploaded_by=request.user,
        )

        from apps.procurement.serializers import GoodsReceiptPhotoSerializer
        return Response(
            GoodsReceiptPhotoSerializer(photo, context={"request": request}).data,
            status=201,
        )

    def delete(self, request):
        from apps.procurement.models import GoodsReceiptPhoto

        org = request.user.profile.organization
        photo_id = request.query_params.get("photo_id")
        if not photo_id:
            return Response({"detail": "photo_id is required."}, status=400)

        try:
            photo = GoodsReceiptPhoto.objects.get(pk=photo_id, goods_receipt__organization=org)
        except GoodsReceiptPhoto.DoesNotExist:
            return Response({"detail": "Photo not found."}, status=404)

        photo.image.delete(save=False)
        photo.delete()
        return Response(status=204)


class GoodsReceiptDocumentView(APIView):
    """Returns structured GRN document data for PDF preview/print."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.procurement.models import GoodsReceipt

        org = request.user.profile.organization
        grn_id = request.query_params.get("grn_id")
        if not grn_id:
            return Response({"detail": "grn_id is required."}, status=400)

        try:
            grn = GoodsReceipt.objects.select_related(
                "purchase_order__vendor", "purchase_order__project",
            ).get(pk=grn_id, organization=org)
        except GoodsReceipt.DoesNotExist:
            return Response({"detail": "GRN not found."}, status=404)

        po = grn.purchase_order
        items = []
        total_value = 0
        for item in grn.items.select_related("po_item").all():
            line_value = float(item.quantity_accepted) * float(item.po_item.unit_price)
            total_value += line_value
            items.append({
                "description": item.po_item.description,
                "unit": item.po_item.unit_of_measure,
                "ordered_qty": str(item.po_item.quantity),
                "received_qty": str(item.quantity_received),
                "accepted_qty": str(item.quantity_accepted),
                "rejected_qty": str(item.quantity_rejected),
                "unit_price": str(item.po_item.unit_price),
                "line_value": str(round(line_value, 2)),
                "quality_status": item.quality_status,
                "batch_number": item.batch_number,
                "expiry_date": str(item.expiry_date) if item.expiry_date else "",
                "storage_location": item.storage_location,
                "rejection_reason": item.rejection_reason,
            })

        return Response({
            "grn_number": grn.grn_number,
            "status": grn.status,
            "status_display": grn.get_status_display(),
            "received_date": str(grn.received_date),
            "received_by": grn.received_by,
            "delivery_note_number": grn.delivery_note_number,
            "inspection_notes": grn.inspection_notes,
            "po_number": po.po_number,
            "po_date": str(po.issue_date) if po.issue_date else "",
            "vendor_name": po.vendor.name if po.vendor_id else "",
            "vendor_address": po.vendor.address if po.vendor_id and hasattr(po.vendor, "address") else "",
            "project_name": po.project.name if po.project_id else "",
            "delivery_address": po.delivery_address or "",
            "org_name": org.name,
            "items": items,
            "total_value": str(round(total_value, 2)),
            "item_count": len(items),
        })


class GoodsReceiptDashboardView(APIView):
    """
    Incoming Shipments dashboard — active/expected deliveries,
    pending inspections, and rejected items.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.procurement.models import GoodsReceipt, GoodsReceiptItem, PurchaseOrder
        from django.utils import timezone as tz
        from django.db.models import Sum as DbSum, F

        org = request.user.profile.organization
        today = tz.localdate()

        grn_qs = GoodsReceipt.objects.filter(organization=org)
        po_qs = PurchaseOrder.objects.filter(organization=org)

        # Summary counts
        pending_inspection = grn_qs.filter(status="pending").count()
        inspected = grn_qs.filter(status="inspected").count()
        accepted = grn_qs.filter(status__in=["accepted", "partially_accepted"]).count()
        rejected = grn_qs.filter(status="rejected").count()

        # In-transit: POs that are issued but have no GRN yet, due today or earlier
        in_transit_today = po_qs.filter(
            status="issued",
            expected_delivery_date__lte=today,
        ).exclude(
            goods_receipts__isnull=False,
        ).count()

        # Expected deliveries (all issued POs with delivery dates)
        expected_deliveries = list(
            po_qs.filter(
                status="issued",
                expected_delivery_date__isnull=False,
            ).select_related("vendor", "project").order_by("expected_delivery_date")[:20].values(
                "id", "po_number", "vendor__name", "project__name",
                "expected_delivery_date", "total_amount",
            )
        )
        for d in expected_deliveries:
            d["vendor_name"] = d.pop("vendor__name", "")
            d["project_name"] = d.pop("project__name", "")
            d["days_until"] = (d["expected_delivery_date"] - today).days
            d["is_overdue"] = d["days_until"] < 0
            d["total_amount"] = str(d["total_amount"] or 0)

        # Recent GRNs
        recent_grns = list(
            grn_qs.select_related("purchase_order__vendor", "purchase_order__project")
            .order_by("-received_date")[:15]
            .values(
                "id", "grn_number", "status", "received_date", "received_by",
                "delivery_note_number",
                "purchase_order__po_number", "purchase_order__vendor__name",
                "purchase_order__project__name", "purchase_order__total_amount",
            )
        )
        for g in recent_grns:
            g["po_number"] = g.pop("purchase_order__po_number", "")
            g["vendor_name"] = g.pop("purchase_order__vendor__name", "")
            g["project_name"] = g.pop("purchase_order__project__name", "")
            g["po_amount"] = str(g.pop("purchase_order__total_amount", 0) or 0)

        # Rejected items needing attention
        rejected_grns = list(
            grn_qs.filter(status="rejected")
            .select_related("purchase_order__vendor", "purchase_order__project")
            .order_by("-received_date")[:10]
            .values(
                "id", "grn_number", "received_date", "inspection_notes",
                "purchase_order__po_number", "purchase_order__vendor__name",
                "purchase_order__project__name",
            )
        )
        for r in rejected_grns:
            r["po_number"] = r.pop("purchase_order__po_number", "")
            r["vendor_name"] = r.pop("purchase_order__vendor__name", "")
            r["project_name"] = r.pop("purchase_order__project__name", "")

        return Response({
            "summary": {
                "in_transit_today": in_transit_today,
                "pending_inspection": pending_inspection,
                "inspected": inspected,
                "accepted": accepted,
                "rejected": rejected,
            },
            "expected_deliveries": expected_deliveries,
            "recent_grns": recent_grns,
            "rejected_grns": rejected_grns,
        })


# ── Material Issue to Construction ───────────────────────────────────

from .models import MaterialIssue, MaterialIssueLine
from .serializers import (
    MaterialIssueListSerializer, MaterialIssueDetailSerializer,
    MaterialIssueWriteSerializer, MaterialIssueLineSerializer,
)


class MaterialIssueDashboardView(APIView):
    """Issue Command Center — daily consumption metrics and alerts."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.utils import timezone as tz
        from django.db.models import Sum as DbSum

        org = request.user.profile.organization
        today = tz.localdate()

        # Daily issue volume (issued today)
        daily_issued = InventoryTransaction.objects.filter(
            organization=org,
            transaction_type="issue",
            transaction_date=today,
        ).aggregate(
            total_value=DbSum("total_cost"),
            total_qty=DbSum("quantity"),
            count=Count("id"),
        )

        # Open requests awaiting approval
        open_requests = MaterialIssue.objects.filter(
            organization=org,
            status="requested",
        ).count()

        # Top consumed category (last 7 days)
        from datetime import timedelta
        week_ago = today - timedelta(days=7)
        top_categories = list(
            InventoryTransaction.objects.filter(
                organization=org,
                transaction_type="issue",
                transaction_date__gte=week_ago,
            ).values("item__category").annotate(
                total_qty=DbSum("quantity"),
                total_value=DbSum("total_cost"),
            ).order_by("-total_value")[:5]
        )
        top_cat = top_categories[0] if top_categories else None

        # Inventory health: items that hit reorder after recent issues
        reorder_alerts = list(
            InventoryStock.objects.filter(
                item__organization=org,
                item__is_active=True,
                quantity_on_hand__lte=F("item__reorder_level"),
                item__reorder_level__gt=0,
            ).select_related("item", "warehouse").values(
                "item__name", "item__sku", "warehouse__name",
                "quantity_on_hand", "item__reorder_level",
            )[:8]
        )

        # Recent issues
        recent_issues = list(
            MaterialIssue.objects.filter(organization=org)
            .select_related("project", "phase", "warehouse", "requested_by")
            .annotate(line_count=Count("lines"))
            .order_by("-created_at")[:10]
        )
        recent_data = MaterialIssueListSerializer(recent_issues, many=True).data

        return Response({
            "daily_issue_value": str(daily_issued["total_value"] or 0),
            "daily_issue_qty": str(daily_issued["total_qty"] or 0),
            "daily_issue_count": daily_issued["count"] or 0,
            "open_requests": open_requests,
            "top_consumed_category": {
                "category": top_cat["item__category"] if top_cat else "",
                "total_qty": str(top_cat["total_qty"]) if top_cat else "0",
                "total_value": str(top_cat["total_value"]) if top_cat else "0",
            } if top_cat else None,
            "category_breakdown": [
                {"category": c["item__category"], "total_qty": str(c["total_qty"]), "total_value": str(c["total_value"])}
                for c in top_categories
            ],
            "reorder_alerts": [
                {
                    "item_name": a["item__name"], "item_sku": a["item__sku"],
                    "warehouse": a["warehouse__name"],
                    "on_hand": str(a["quantity_on_hand"]),
                    "reorder_level": str(a["item__reorder_level"]),
                }
                for a in reorder_alerts
            ],
            "recent_issues": recent_data,
            "wastage_alerts": _compute_wastage_alerts(org),
            "crew_efficiency": _compute_crew_efficiency(org),
        })


class ConsumptionTrackingDashboardView(APIView):
    """Material Consumption Tracking — audit engine comparing issued vs BoQ."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Sum as DbSum
        from apps.inventory.models import BOMItem, BillOfMaterials
        from apps.projects.models import ProjectWorkforceLog
        from decimal import Decimal as D

        org = request.user.profile.organization

        # Total issued across all projects
        total_issued = InventoryTransaction.objects.filter(
            organization=org, transaction_type="issue",
        ).aggregate(
            total_value=DbSum("total_cost"),
            total_qty=DbSum("quantity"),
        )
        issued_value = float(total_issued["total_value"] or 0)

        # Total BoQ baseline
        boq_baseline = 0
        active_boms = BillOfMaterials.objects.filter(
            organization=org, status__in=["approved", "execution", "contract"],
        )
        for bom in active_boms:
            boq_baseline += float(bom.total_estimated_cost or 0)

        # Overall variance
        variance_pct = round((issued_value - boq_baseline) / boq_baseline * 100, 1) if boq_baseline > 0 else 0
        wastage_value = max(0, issued_value - boq_baseline)

        # Per-material variance (find highest)
        material_variances = []
        issued_by_item = dict(
            InventoryTransaction.objects.filter(
                organization=org, transaction_type="issue",
            ).values("item__name", "item__category").annotate(
                issued_total=DbSum("total_cost"),
                issued_qty=DbSum("quantity"),
            ).values_list("item__name", "issued_total")
        )

        boq_by_item = {}
        for bom in active_boms:
            for bi in bom.items.all():
                key = bi.material_name
                boq_by_item[key] = boq_by_item.get(key, 0) + float(bi.line_total or 0)

        for item_name, issued_val in issued_by_item.items():
            boq_val = boq_by_item.get(item_name, 0)
            if boq_val > 0:
                var_pct = round((float(issued_val) - boq_val) / boq_val * 100, 1)
                material_variances.append({
                    "material": item_name,
                    "boq_value": str(round(boq_val)),
                    "issued_value": str(round(float(issued_val))),
                    "variance_pct": var_pct,
                    "variance_amount": str(round(float(issued_val) - boq_val)),
                    "status": "over" if var_pct > 5 else "under" if var_pct < -5 else "on_track",
                })

        material_variances.sort(key=lambda x: -abs(x["variance_pct"]))
        high_risk = material_variances[0] if material_variances else None

        # Per-category consumption breakdown
        category_consumption = list(
            InventoryTransaction.objects.filter(
                organization=org, transaction_type="issue",
            ).values("item__category").annotate(
                total_value=DbSum("total_cost"),
                total_qty=DbSum("quantity"),
                count=Count("id"),
            ).order_by("-total_value")
        )

        # Productivity score: material value consumed per man-hour
        total_man_hours = float(
            ProjectWorkforceLog.objects.filter(organization=org).aggregate(
                total=DbSum("overtime_hours"),
            )["total"] or 0
        )
        # Add standard 8h per log entry as baseline
        total_logs = ProjectWorkforceLog.objects.filter(organization=org).count()
        total_man_hours += total_logs * 8
        productivity_score = round(issued_value / total_man_hours, 2) if total_man_hours > 0 else 0

        # Per-project consumption
        project_consumption = list(
            InventoryTransaction.objects.filter(
                organization=org, transaction_type="issue", project__isnull=False,
            ).values("project__id", "project__name").annotate(
                total_value=DbSum("total_cost"),
                total_qty=DbSum("quantity"),
                tx_count=Count("id"),
            ).order_by("-total_value")[:10]
        )
        for pc in project_consumption:
            pc["project_name"] = pc.pop("project__name", "")
            pc["project_id"] = pc.pop("project__id", 0)
            pc["total_value"] = str(pc["total_value"] or 0)
            pc["total_qty"] = str(pc["total_qty"] or 0)

        # Recent consumption transactions
        recent_txs = list(
            InventoryTransaction.objects.filter(
                organization=org, transaction_type="issue",
            ).select_related("item", "warehouse", "project")
            .order_by("-transaction_date", "-created_at")[:15]
            .values(
                "id", "item__name", "item__category", "warehouse__name",
                "project__name", "quantity", "total_cost", "transaction_date",
                "reference_number", "notes",
            )
        )
        for tx in recent_txs:
            tx["item_name"] = tx.pop("item__name", "")
            tx["item_category"] = tx.pop("item__category", "")
            tx["warehouse_name"] = tx.pop("warehouse__name", "")
            tx["project_name"] = tx.pop("project__name", "")
            tx["quantity"] = str(tx["quantity"] or 0)
            tx["total_cost"] = str(tx["total_cost"] or 0)
            tx["transaction_date"] = str(tx["transaction_date"])

        return Response({
            "overall_variance_pct": variance_pct,
            "wastage_value": str(round(wastage_value)),
            "total_issued": str(round(issued_value)),
            "boq_baseline": str(round(boq_baseline)),
            "high_risk_material": high_risk,
            "productivity_score": productivity_score,
            "material_variances": material_variances[:15],
            "category_consumption": [
                {"category": c["item__category"], "total_value": str(c["total_value"] or 0), "total_qty": str(c["total_qty"] or 0), "count": c["count"]}
                for c in category_consumption
            ],
            "project_consumption": project_consumption,
            "recent_transactions": recent_txs,
            "pva_ledger": _compute_pva_ledger(org),
            "crew_leaderboard": _compute_crew_leaderboard(org),
        })


def _compute_crew_leaderboard(org):
    """Compare crew material efficiency — who uses less material for the same output."""
    from apps.inventory.models import MaterialIssue, MaterialIssueLine
    from apps.projects.models import ProjectWorkforceLog
    from django.db.models import Sum as DbSum, Count as DbCount, F

    # Group material issues by requesting crew (using purpose as work type proxy)
    crew_issues = (
        MaterialIssue.objects.filter(
            organization=org,
            status__in=["issued", "partially_issued"],
        )
        .values("requested_by__first_name", "requested_by__last_name")
        .annotate(
            issue_count=DbCount("id"),
        )
        .order_by("-issue_count")[:10]
    )

    leaderboard = []
    all_crew_costs = []

    for crew in crew_issues:
        name = f"{crew['requested_by__first_name'] or ''} {crew['requested_by__last_name'] or ''}".strip() or "Unknown Crew"

        # Total material value consumed by this crew
        total_issued_value = MaterialIssueLine.objects.filter(
            issue__organization=org,
            issue__status__in=["issued", "partially_issued"],
            issue__requested_by__first_name=crew["requested_by__first_name"],
            issue__requested_by__last_name=crew["requested_by__last_name"],
        ).aggregate(
            total_value=DbSum(F("issued_quantity") * F("unit_cost")),
            total_qty=DbSum("issued_quantity"),
            line_count=DbCount("id"),
        )

        value = float(total_issued_value["total_value"] or 0)
        qty = float(total_issued_value["total_qty"] or 0)
        issues = crew["issue_count"]

        # Material per issue (efficiency metric)
        cost_per_issue = round(value / issues, 2) if issues > 0 else 0
        all_crew_costs.append(cost_per_issue)

        # Top materials consumed
        top_mats = list(
            MaterialIssueLine.objects.filter(
                issue__organization=org,
                issue__status__in=["issued", "partially_issued"],
                issue__requested_by__first_name=crew["requested_by__first_name"],
                issue__requested_by__last_name=crew["requested_by__last_name"],
            ).values("item__name").annotate(
                total_qty=DbSum("issued_quantity"),
            ).order_by("-total_qty")[:3]
        )

        leaderboard.append({
            "crew": name,
            "issue_count": issues,
            "total_value": str(round(value)),
            "total_qty": str(round(qty, 1)),
            "cost_per_issue": cost_per_issue,
            "top_materials": [{"name": m["item__name"], "qty": str(m["total_qty"])} for m in top_mats],
        })

    # Calculate efficiency ranking (lower cost_per_issue = more efficient)
    if all_crew_costs:
        avg_cost = sum(all_crew_costs) / len(all_crew_costs)
        for entry in leaderboard:
            if avg_cost > 0:
                efficiency = round((1 - (entry["cost_per_issue"] - avg_cost) / avg_cost) * 100)
                entry["efficiency_score"] = min(100, max(0, efficiency))
                entry["rating"] = "highly_productive" if entry["cost_per_issue"] < avg_cost * 0.9 else "productive" if entry["cost_per_issue"] <= avg_cost * 1.05 else "needs_improvement"
            else:
                entry["efficiency_score"] = 50
                entry["rating"] = "productive"

    # Sort by efficiency score descending
    leaderboard.sort(key=lambda x: -x.get("efficiency_score", 0))

    # Yield calculations (actual output per unit of material)
    yields = []
    material_groups = (
        MaterialIssueLine.objects.filter(
            issue__organization=org,
            issue__status__in=["issued", "partially_issued"],
        ).values("item__name", "item__category").annotate(
            total_issued=DbSum("issued_quantity"),
            total_value=DbSum(F("issued_quantity") * F("unit_cost")),
            issue_count=DbCount("issue", distinct=True),
        ).order_by("-total_issued")[:10]
    )

    for mg in material_groups:
        total_issued = float(mg["total_issued"] or 0)
        issue_count = mg["issue_count"]
        if issue_count > 0 and total_issued > 0:
            yield_per_issue = round(total_issued / issue_count, 1)
            yields.append({
                "material": mg["item__name"],
                "category": mg["item__category"],
                "total_issued": str(round(total_issued, 1)),
                "issue_count": issue_count,
                "yield_per_issue": yield_per_issue,
                "total_value": str(round(float(mg["total_value"] or 0))),
            })

    return {
        "leaderboard": leaderboard,
        "yields": yields,
    }


class VarianceInvestigationViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    search_fields = ["material_name", "work_package", "supervisor_notes"]
    filterset_fields = ["project", "root_cause", "severity", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        from .models import VarianceInvestigation
        return VarianceInvestigation.objects.filter(
            organization=self._resolve_request_org(),
        ).select_related("project", "investigated_by").prefetch_related("photos")

    def get_serializer_class(self):
        from .serializers import VarianceInvestigationSerializer, VarianceInvestigationWriteSerializer
        if self.action in ("create", "update", "partial_update"):
            return VarianceInvestigationWriteSerializer
        return VarianceInvestigationSerializer

    def perform_create(self, serializer):
        serializer.save(organization=self._resolve_request_org(), investigated_by=self.request.user)

    @action(detail=True, methods=["post"], url_path="upload-photo")
    def upload_photo(self, request, pk=None):
        from .models import VarianceInvestigationPhoto
        from .serializers import VariancePhotoSerializer

        investigation = self.get_object()
        image = request.FILES.get("image")
        if not image:
            return Response({"detail": "No image provided."}, status=400)

        photo = VarianceInvestigationPhoto.objects.create(
            investigation=investigation,
            image=image,
            caption=request.data.get("caption", ""),
            uploaded_by=request.user,
        )
        return Response(VariancePhotoSerializer(photo, context={"request": request}).data, status=201)


def _compute_pva_ledger(org):
    """Build Planned vs Actual ledger — quantity-based comparison per material per work package."""
    from apps.inventory.models import BOMItem, BillOfMaterials, InventoryTransaction
    from apps.projects.models import ProjectWorkPackage
    from django.db.models import Sum as DbSum

    ledger = []

    active_boms = BillOfMaterials.objects.filter(
        organization=org, status__in=["approved", "execution", "contract"],
        project__isnull=False,
    ).select_related("project")

    for bom in active_boms[:5]:
        # BOQ items as planned quantities
        boq_items = BOMItem.objects.filter(bom=bom).order_by("sort_order")

        for bi in boq_items:
            planned_qty = float(bi.quantity or 0)
            planned_unit = bi.unit_of_measure or "ea"

            # Find matching issued transactions for this item in the project
            actual = InventoryTransaction.objects.filter(
                organization=org,
                project=bom.project,
                transaction_type="issue",
                item__name__icontains=bi.material_name.split(" ")[0] if bi.material_name else "",
            ).aggregate(
                actual_qty=DbSum("quantity"),
                actual_value=DbSum("total_cost"),
            )
            actual_qty = float(actual["actual_qty"] or 0)

            variance_qty = actual_qty - planned_qty
            variance_pct = round(variance_qty / planned_qty * 100, 1) if planned_qty > 0 else 0

            if variance_pct > 10:
                status = "investigate"
            elif variance_pct > 5:
                status = "at_risk"
            elif variance_pct < -5:
                status = "optimized"
            else:
                status = "on_track"

            ledger.append({
                "material": bi.material_name,
                "work_package": bi.category or bi.section or "General",
                "project": bom.project.name,
                "planned_qty": str(planned_qty),
                "actual_qty": str(actual_qty),
                "unit": planned_unit,
                "variance_qty": str(round(variance_qty, 2)),
                "variance_pct": variance_pct,
                "planned_value": str(round(float(bi.line_total or 0))),
                "actual_value": str(round(float(actual["actual_value"] or 0))),
                "status": status,
            })

    # Sort by worst variance first
    ledger.sort(key=lambda x: -abs(x["variance_pct"]))
    return ledger[:30]


def _compute_wastage_alerts(org):
    """Compare issued quantities against BoQ estimates per phase to detect over-consumption."""
    from apps.projects.models import ProjectPhase
    from apps.inventory.models import InventoryTransaction, BOMItem, BillOfMaterials
    from django.db.models import Sum as DbSum

    alerts = []

    # Get all active projects with BOMs
    boms = BillOfMaterials.objects.filter(
        organization=org,
        status__in=["approved", "execution", "contract"],
    ).select_related("project")

    for bom in boms[:10]:  # Limit to avoid heavy queries
        if not bom.project_id:
            continue

        # Get BOQ items grouped by category
        boq_items = BOMItem.objects.filter(bom=bom).values("category").annotate(
            boq_total_cost=DbSum("line_total"),
        )
        boq_by_cat = {b["category"]: float(b["boq_total_cost"] or 0) for b in boq_items}

        # Get issued transactions for this project grouped by category
        issued = InventoryTransaction.objects.filter(
            organization=org,
            project=bom.project,
            transaction_type="issue",
        ).values("item__category").annotate(
            issued_total=DbSum("total_cost"),
        )

        for iss in issued:
            cat = iss["item__category"]
            issued_val = float(iss["issued_total"] or 0)
            boq_val = boq_by_cat.get(cat, 0)

            if boq_val > 0 and issued_val > boq_val:
                over_pct = round((issued_val - boq_val) / boq_val * 100)
                if over_pct >= 5:  # Only alert for 5%+ overruns
                    alerts.append({
                        "project": bom.project.name,
                        "category": cat or "General",
                        "boq_estimate": str(round(boq_val)),
                        "issued_total": str(round(issued_val)),
                        "over_pct": over_pct,
                        "severity": "critical" if over_pct > 20 else "warning",
                    })

    return sorted(alerts, key=lambda x: -x["over_pct"])[:10]


def _compute_crew_efficiency(org):
    """Compute issue-to-completion ratio by requesting user (crew proxy)."""
    from apps.inventory.models import MaterialIssue
    from django.db.models import Sum as DbSum, Count as DbCount, Avg as DbAvg

    # Group issues by requesting user
    crew_data = (
        MaterialIssue.objects.filter(
            organization=org,
            status__in=["issued", "partially_issued"],
        )
        .values("requested_by__first_name", "requested_by__last_name")
        .annotate(
            total_issues=DbCount("id"),
            total_lines=DbCount("lines"),
        )
        .order_by("-total_issues")[:8]
    )

    results = []
    for c in crew_data:
        name = f"{c['requested_by__first_name'] or ''} {c['requested_by__last_name'] or ''}".strip() or "Unknown"
        total = c["total_issues"]
        # Efficiency = completed issues / total issues
        completed = MaterialIssue.objects.filter(
            organization=org,
            status="issued",
            requested_by__first_name=c["requested_by__first_name"],
            requested_by__last_name=c["requested_by__last_name"],
        ).count()
        efficiency = round(completed / total * 100) if total > 0 else 0

        results.append({
            "crew": name,
            "total_issues": total,
            "completed": completed,
            "efficiency_pct": efficiency,
        })

    return sorted(results, key=lambda x: -x["efficiency_pct"])


class MaterialIssueViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    search_fields = ["issue_number", "project__name", "purpose"]
    filterset_fields = ["project", "phase", "warehouse", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return (
            MaterialIssue.objects.filter(organization=self._resolve_request_org())
            .select_related("project", "phase", "warehouse", "requested_by")
            .annotate(line_count=Count("lines"))
        )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return MaterialIssueDetailSerializer
        if self.action in ("create", "update", "partial_update"):
            return MaterialIssueWriteSerializer
        return MaterialIssueListSerializer

    def perform_create(self, serializer):
        serializer.save(organization=self._resolve_request_org(), requested_by=self.request.user)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        issue = self.get_object()
        if issue.status != "requested":
            return Response({"detail": "Only requested issues can be approved."}, status=400)
        from django.utils import timezone as tz
        issue.status = "approved"
        issue.approved_by = request.user.get_full_name() or request.user.email
        issue.approved_date = tz.localdate()
        issue.save(update_fields=["status", "approved_by", "approved_date", "updated_at"])
        return Response(MaterialIssueDetailSerializer(issue).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        issue = self.get_object()
        issue.status = "rejected"
        issue.notes = request.data.get("reason", issue.notes)
        issue.save(update_fields=["status", "notes", "updated_at"])
        return Response(MaterialIssueDetailSerializer(issue).data)

    @action(detail=True, methods=["post"], url_path="issue-materials")
    def issue_materials(self, request, pk=None):
        """Actually issue materials — deducts from stock, creates transactions."""
        issue = self.get_object()
        if issue.status not in ("approved", "partially_issued"):
            return Response({"detail": "Issue must be approved first."}, status=400)

        from django.utils import timezone as tz
        from decimal import Decimal as D

        issued_count = 0
        for line in issue.lines.all():
            qty_to_issue = line.requested_quantity - line.issued_quantity
            if qty_to_issue <= 0:
                continue

            # Check stock
            stock = InventoryStock.objects.filter(warehouse=issue.warehouse, item=line.item).first()
            if not stock or stock.quantity_on_hand < qty_to_issue:
                qty_to_issue = stock.quantity_on_hand if stock else D("0")

            if qty_to_issue <= 0:
                continue

            # Create issue transaction
            InventoryTransaction.objects.create(
                organization=issue.organization,
                warehouse=issue.warehouse,
                item=line.item,
                project=issue.project,
                transaction_type="issue",
                quantity=qty_to_issue,
                unit_cost=line.unit_cost or line.item.default_unit_cost or D("0"),
                total_cost=qty_to_issue * (line.unit_cost or line.item.default_unit_cost or D("0")),
                transaction_date=tz.localdate(),
                reference_number=issue.issue_number,
                notes=f"Issued to {issue.project.name}: {line.purpose or issue.purpose}",
            )

            # Deduct stock
            stock.quantity_on_hand = max(D("0"), stock.quantity_on_hand - qty_to_issue)
            stock.last_transaction_at = tz.now()
            stock.save(update_fields=["quantity_on_hand", "last_transaction_at", "updated_at"])

            # Update line
            line.issued_quantity = line.issued_quantity + qty_to_issue
            line.save(update_fields=["issued_quantity"])
            issued_count += 1

        # Update issue status
        all_lines = issue.lines.all()
        fully_issued = all(l.issued_quantity >= l.requested_quantity for l in all_lines)
        issue.status = "issued" if fully_issued else "partially_issued"
        issue.issued_by = request.user.get_full_name() or request.user.email
        issue.issued_date = tz.localdate()
        issue.save(update_fields=["status", "issued_by", "issued_date", "updated_at"])

        return Response({
            "detail": f"{issued_count} line(s) issued. Status: {issue.get_status_display()}.",
            "issue": MaterialIssueDetailSerializer(issue).data,
        })


class MaterialIssueLineViewSet(viewsets.ModelViewSet):
    serializer_class = MaterialIssueLineSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return MaterialIssueLine.objects.filter(
            issue_id=self.kwargs["issue_pk"],
        ).select_related("item")

    def perform_create(self, serializer):
        serializer.save(issue_id=self.kwargs["issue_pk"])


# ── Material Transfers ───────────────────────────────────────────────

from .models import MaterialTransfer, MaterialTransferLine
from .serializers import (
    MaterialTransferListSerializer, MaterialTransferDetailSerializer,
    MaterialTransferWriteSerializer, MaterialTransferLineSerializer,
)


class MaterialTransferDashboardView(APIView):
    """Logistics Control Tower — value in motion, pending receipts, fleet efficiency."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Sum as DbSum
        from django.utils import timezone as tz

        org = request.user.profile.organization
        today = tz.localdate()

        transfers = MaterialTransfer.objects.filter(organization=org)

        # Materials in transit (value)
        in_transit = transfers.filter(status="in_transit")
        transit_value = 0
        for t in in_transit.prefetch_related("lines"):
            transit_value += sum(float(l.quantity * l.unit_cost) for l in t.lines.all())

        # Pending receipts (delivered but not confirmed)
        pending_receipts = transfers.filter(status__in=["delivered", "partially_received"]).count()

        # Fleet efficiency (scheduled today)
        todays_transfers = transfers.filter(scheduled_date=today).count()
        active_in_transit = in_transit.count()

        # Recent transfers
        recent = list(
            transfers.select_related("source_warehouse", "destination_warehouse", "project", "requested_by")
            .annotate(line_count=Count("lines"))
            .order_by("-created_at")[:12]
        )

        # Route data for heatmap
        routes = list(
            in_transit.values(
                "source_warehouse__name", "source_warehouse__location",
                "destination_warehouse__name", "destination_warehouse__location",
            )
        )
        route_data = [
            {
                "source": r["source_warehouse__name"],
                "source_location": r["source_warehouse__location"],
                "destination": r["destination_warehouse__name"],
                "dest_location": r["destination_warehouse__location"],
            }
            for r in routes
        ]

        # Status breakdown
        status_counts = dict(transfers.values("status").annotate(count=Count("id")).values_list("status", "count"))

        return Response({
            "in_transit_value": str(round(transit_value)),
            "in_transit_count": active_in_transit,
            "pending_receipts": pending_receipts,
            "todays_transfers": todays_transfers,
            "status_counts": status_counts,
            "active_routes": route_data,
            "recent_transfers": MaterialTransferListSerializer(recent, many=True).data,
        })


class MaterialTransferViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    search_fields = ["transfer_number", "source_warehouse__name", "destination_warehouse__name", "reason"]
    filterset_fields = ["source_warehouse", "destination_warehouse", "project", "status", "priority"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return (
            MaterialTransfer.objects.filter(organization=self._resolve_request_org())
            .select_related("source_warehouse", "destination_warehouse", "project", "requested_by")
            .annotate(line_count=Count("lines"))
        )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return MaterialTransferDetailSerializer
        if self.action in ("create", "update", "partial_update"):
            return MaterialTransferWriteSerializer
        return MaterialTransferListSerializer

    def perform_create(self, serializer):
        serializer.save(organization=self._resolve_request_org(), requested_by=self.request.user)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        transfer = self.get_object()
        if transfer.status != "requested":
            return Response({"detail": "Only requested transfers can be approved."}, status=400)
        transfer.status = "approved"
        transfer.approved_by = request.user.get_full_name() or request.user.email
        transfer.save(update_fields=["status", "approved_by", "updated_at"])
        _notify_transfer(transfer, "approved", request.user)
        return Response(MaterialTransferDetailSerializer(transfer).data)

    @action(detail=True, methods=["post"])
    def dispatch(self, request, pk=None):
        """Mark transfer as dispatched — deducts source stock."""
        transfer = self.get_object()
        if transfer.status != "approved":
            return Response({"detail": "Only approved transfers can be dispatched."}, status=400)

        from django.utils import timezone as tz
        from decimal import Decimal as D

        # Deduct from source warehouse
        for line in transfer.lines.all():
            stock = InventoryStock.objects.filter(warehouse=transfer.source_warehouse, item=line.item).first()
            if stock:
                stock.quantity_on_hand = max(D("0"), stock.quantity_on_hand - line.quantity)
                stock.last_transaction_at = tz.now()
                stock.save(update_fields=["quantity_on_hand", "last_transaction_at", "updated_at"])

            # Create transfer_out transaction
            InventoryTransaction.objects.create(
                organization=transfer.organization,
                warehouse=transfer.source_warehouse,
                item=line.item,
                project=transfer.project,
                transaction_type="transfer_out",
                quantity=line.quantity,
                unit_cost=line.unit_cost,
                total_cost=line.quantity * line.unit_cost,
                transaction_date=tz.localdate(),
                reference_number=transfer.transfer_number,
                notes=f"Transfer to {transfer.destination_warehouse.name}",
            )

        transfer.status = "in_transit"
        transfer.dispatched_date = tz.localdate()
        transfer.dispatched_by = request.user.get_full_name() or request.user.email
        transfer.vehicle_details = request.data.get("vehicle_details", transfer.vehicle_details)
        transfer.waybill_number = request.data.get("waybill_number", transfer.waybill_number)
        transfer.save(update_fields=["status", "dispatched_date", "dispatched_by", "vehicle_details", "waybill_number", "updated_at"])
        _notify_transfer(transfer, "dispatched", request.user)
        return Response(MaterialTransferDetailSerializer(transfer).data)

    @action(detail=True, methods=["post"], url_path="confirm-receipt")
    def confirm_receipt(self, request, pk=None):
        """Receiver confirms delivery — adds to destination stock."""
        transfer = self.get_object()
        if transfer.status not in ("in_transit", "delivered", "partially_received"):
            return Response({"detail": "Transfer must be in transit or delivered."}, status=400)

        from django.utils import timezone as tz
        from decimal import Decimal as D

        line_receipts = request.data.get("lines", [])

        for lr in line_receipts:
            line_id = lr.get("line_id")
            received_qty = D(str(lr.get("received_quantity", 0)))
            try:
                line = transfer.lines.get(pk=line_id)
            except MaterialTransferLine.DoesNotExist:
                continue

            line.received_quantity = received_qty
            line.save(update_fields=["received_quantity"])

            if received_qty > 0:
                # Add to destination stock
                stock, _ = InventoryStock.objects.get_or_create(
                    warehouse=transfer.destination_warehouse,
                    item=line.item,
                    defaults={"organization": transfer.organization, "average_unit_cost": line.unit_cost},
                )
                stock.quantity_on_hand = (stock.quantity_on_hand or D("0")) + received_qty
                stock.last_transaction_at = tz.now()
                stock.save(update_fields=["quantity_on_hand", "last_transaction_at", "updated_at"])

                # Create transfer_in transaction
                InventoryTransaction.objects.create(
                    organization=transfer.organization,
                    warehouse=transfer.destination_warehouse,
                    item=line.item,
                    project=transfer.project,
                    transaction_type="transfer_in",
                    quantity=received_qty,
                    unit_cost=line.unit_cost,
                    total_cost=received_qty * line.unit_cost,
                    transaction_date=tz.localdate(),
                    reference_number=transfer.transfer_number,
                    notes=f"Transfer from {transfer.source_warehouse.name}",
                )

        # Update transfer status
        all_lines = transfer.lines.all()
        fully_received = all(l.received_quantity >= l.quantity for l in all_lines)
        any_received = any(l.received_quantity > 0 for l in all_lines)

        if fully_received:
            transfer.status = "received"
        elif any_received:
            transfer.status = "partially_received"
        else:
            transfer.status = "delivered"

        transfer.confirmed_date = tz.localdate()
        transfer.received_by = request.user.get_full_name() or request.user.email
        transfer.save(update_fields=["status", "confirmed_date", "received_by", "updated_at"])
        _notify_transfer(transfer, "received", request.user)
        return Response(MaterialTransferDetailSerializer(transfer).data)


class MaterialTransferLineViewSet(viewsets.ModelViewSet):
    serializer_class = MaterialTransferLineSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return MaterialTransferLine.objects.filter(
            transfer_id=self.kwargs["transfer_pk"],
        ).select_related("item")

    def perform_create(self, serializer):
        serializer.save(transfer_id=self.kwargs["transfer_pk"])


# ── Returns Management ────────────────────────────────────────────────

from .models import MaterialReturn, MaterialReturnLine
from .serializers import (
    MaterialReturnListSerializer, MaterialReturnDetailSerializer,
    MaterialReturnWriteSerializer, MaterialReturnLineSerializer,
)


class MaterialReturnDashboardView(APIView):
    """Returns Command Center — recoverable value, velocity, top reasons."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Sum as DbSum
        from django.utils import timezone as tz

        org = request.user.profile.organization
        returns = MaterialReturn.objects.filter(organization=org)

        # Total pending value
        pending_qs = returns.filter(status__in=["requested", "approved", "in_transit"])
        pending_value = 0
        for r in pending_qs.prefetch_related("lines"):
            pending_value += sum(float(l.quantity * l.unit_cost) for l in r.lines.all())

        # Credit memo status
        credit_pending = returns.filter(status="credit_pending").count()
        credit_received = returns.filter(status="credit_received").count()
        total_credits = float(returns.filter(status="credit_received").aggregate(total=DbSum("credit_amount"))["total"] or 0)

        # Top return reason
        reason_counts = dict(returns.exclude(status__in=["cancelled", "draft"]).values("reason").annotate(count=Count("id")).order_by("-count").values_list("reason", "count")[:1])
        top_reason = list(reason_counts.keys())[0] if reason_counts else ""
        top_reason_count = list(reason_counts.values())[0] if reason_counts else 0

        # Status breakdown
        status_counts = dict(returns.values("status").annotate(count=Count("id")).values_list("status", "count"))

        # Return velocity (last 30 days)
        from datetime import timedelta
        thirty_ago = tz.localdate() - timedelta(days=30)
        recent_completed = returns.filter(status__in=["received", "credit_received"], received_date__gte=thirty_ago).count()

        # Recent returns
        recent = list(
            returns.select_related("project", "source_warehouse", "destination_warehouse", "vendor", "requested_by")
            .annotate(line_count=Count("lines"))
            .order_by("-created_at")[:12]
        )

        return Response({
            "pending_value": str(round(pending_value)),
            "pending_count": pending_qs.count(),
            "credit_pending": credit_pending,
            "credit_received_count": credit_received,
            "total_credits_received": str(round(total_credits)),
            "top_reason": top_reason,
            "top_reason_count": top_reason_count,
            "return_velocity_30d": recent_completed,
            "status_counts": status_counts,
            "recent_returns": MaterialReturnListSerializer(recent, many=True).data,
        })


class MaterialReturnViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    search_fields = ["return_number", "reason_detail", "source_warehouse__name"]
    filterset_fields = ["project", "return_type", "status", "reason", "vendor"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return (
            MaterialReturn.objects.filter(organization=self._resolve_request_org())
            .select_related("project", "source_warehouse", "destination_warehouse", "vendor", "requested_by")
            .annotate(line_count=Count("lines"))
        )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return MaterialReturnDetailSerializer
        if self.action in ("create", "update", "partial_update"):
            return MaterialReturnWriteSerializer
        return MaterialReturnListSerializer

    def perform_create(self, serializer):
        serializer.save(organization=self._resolve_request_org(), requested_by=self.request.user, status="requested")

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        ret = self.get_object()
        if ret.status != "requested":
            return Response({"detail": "Only requested returns can be approved."}, status=400)
        from django.utils import timezone as tz
        ret.status = "approved"
        ret.approved_by = request.user.get_full_name() or request.user.email
        ret.approved_date = tz.localdate()
        ret.save(update_fields=["status", "approved_by", "approved_date", "updated_at"])
        _notify_return(ret, "approved")
        return Response(MaterialReturnDetailSerializer(ret).data)

    @action(detail=True, methods=["post"], url_path="receive-return")
    def receive_return(self, request, pk=None):
        """Receive returned materials — restock warehouse or mark for vendor credit."""
        ret = self.get_object()
        if ret.status not in ("approved", "in_transit"):
            return Response({"detail": "Return must be approved or in transit."}, status=400)

        from django.utils import timezone as tz
        from decimal import Decimal as D

        if ret.return_type == "to_warehouse" and ret.destination_warehouse_id:
            # Restock destination warehouse
            for line in ret.lines.all():
                stock, _ = InventoryStock.objects.get_or_create(
                    warehouse=ret.destination_warehouse, item=line.item,
                    defaults={"organization": ret.organization, "average_unit_cost": line.unit_cost},
                )
                stock.quantity_on_hand = (stock.quantity_on_hand or D("0")) + line.quantity
                stock.last_transaction_at = tz.now()
                stock.save(update_fields=["quantity_on_hand", "last_transaction_at", "updated_at"])
                line.received_quantity = line.quantity
                line.save(update_fields=["received_quantity"])

                InventoryTransaction.objects.create(
                    organization=ret.organization, warehouse=ret.destination_warehouse, item=line.item,
                    project=ret.project, transaction_type="transfer_in",
                    quantity=line.quantity, unit_cost=line.unit_cost, total_cost=line.quantity * line.unit_cost,
                    transaction_date=tz.localdate(), reference_number=ret.return_number,
                    notes=f"Return received: {ret.get_reason_display()}",
                )
            ret.status = "received"

            # Credit the project cost
            if ret.project_id:
                from apps.projects.models import ProjectCostEntry
                ProjectCostEntry.objects.create(
                    organization=ret.organization, project=ret.project, category="materials",
                    description=f"Return credit: {ret.return_number} ({ret.get_reason_display()})",
                    amount=-(ret.total_value), entry_date=tz.localdate(),
                    source_reference=f"return-{ret.return_number}",
                )
        else:
            ret.status = "credit_pending"

        ret.received_date = tz.localdate()
        ret.save(update_fields=["status", "received_date", "updated_at"])
        _notify_return(ret, "received")
        return Response(MaterialReturnDetailSerializer(ret).data)

    @action(detail=True, methods=["post"], url_path="record-credit")
    def record_credit(self, request, pk=None):
        """Record vendor credit memo received."""
        ret = self.get_object()
        if ret.status != "credit_pending":
            return Response({"detail": "Return must be in credit pending status."}, status=400)
        from django.utils import timezone as tz
        ret.credit_memo_number = request.data.get("credit_memo_number", "")
        ret.credit_amount = request.data.get("credit_amount", ret.total_value)
        ret.credit_received_date = tz.localdate()
        ret.status = "credit_received"
        ret.save(update_fields=["status", "credit_memo_number", "credit_amount", "credit_received_date", "updated_at"])
        _notify_return(ret, "credit_received")
        return Response(MaterialReturnDetailSerializer(ret).data)


class MaterialReturnLineViewSet(viewsets.ModelViewSet):
    serializer_class = MaterialReturnLineSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return MaterialReturnLine.objects.filter(return_order_id=self.kwargs["return_pk"]).select_related("item")

    def perform_create(self, serializer):
        serializer.save(return_order_id=self.kwargs["return_pk"])


def _notify_return(ret, action):
    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification
        from apps.accounts.models import UserProfile
        org = ret.organization
        admins = [p.user for p in UserProfile.objects.filter(organization=org, role__in=["admin", "manager"], user__is_active=True).select_related("user")]
        msgs = {
            "approved": f"Return {ret.return_number} approved. {ret.get_reason_display()}. Ready for dispatch.",
            "received": f"Return {ret.return_number} received and {'restocked' if ret.return_type == 'to_warehouse' else 'vendor credit pending'}.",
            "credit_received": f"Vendor credit received for return {ret.return_number}: ₦{ret.credit_amount:,.2f}.",
        }
        dispatch_workflow_notification(
            organization=org, event_key=f"material_return_{action}", recipients=admins,
            link_url="/material-management/returns", fallback_channels=["in_app"],
            fallback_title=f"Return {action.replace('_', ' ').title()} — {ret.return_number}",
            fallback_message=msgs.get(action, f"Return {ret.return_number}: {action}"),
            fallback_category=Notification.Category.PROCUREMENT_ORDER,
            fallback_severity=Notification.Severity.INFO,
        )
    except Exception:
        pass


class MaterialTransferWaybillView(APIView):
    """Generate waybill document data for a transfer order."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        org = request.user.profile.organization
        transfer_id = request.query_params.get("transfer_id")
        if not transfer_id:
            return Response({"detail": "transfer_id is required."}, status=400)

        try:
            transfer = MaterialTransfer.objects.select_related(
                "source_warehouse", "destination_warehouse", "project", "requested_by",
            ).get(pk=transfer_id, organization=org)
        except MaterialTransfer.DoesNotExist:
            return Response({"detail": "Transfer not found."}, status=404)

        items = []
        total_value = 0
        total_qty = 0
        for line in transfer.lines.select_related("item").all():
            line_val = float(line.quantity) * float(line.unit_cost)
            total_value += line_val
            total_qty += float(line.quantity)
            items.append({
                "description": line.item.name,
                "sku": line.item.sku,
                "quantity": str(line.quantity),
                "unit": line.unit_of_measure,
                "unit_cost": str(line.unit_cost),
                "line_value": str(round(line_val, 2)),
            })

        import hashlib
        qr_data = f"TO:{transfer.transfer_number}|FROM:{transfer.source_warehouse.name}|TO:{transfer.destination_warehouse.name}|VAL:{round(total_value)}|DATE:{transfer.dispatched_date or transfer.scheduled_date}"
        qr_hash = hashlib.md5(qr_data.encode()).hexdigest()[:12].upper()

        return Response({
            "transfer_number": transfer.transfer_number,
            "status": transfer.status,
            "source_warehouse": transfer.source_warehouse.name,
            "source_location": transfer.source_warehouse.location,
            "destination_warehouse": transfer.destination_warehouse.name,
            "destination_location": transfer.destination_warehouse.location,
            "project_name": transfer.project.name if transfer.project_id else "",
            "org_name": org.name,
            "priority": transfer.priority,
            "reason": transfer.reason,
            "scheduled_date": str(transfer.scheduled_date) if transfer.scheduled_date else "",
            "dispatched_date": str(transfer.dispatched_date) if transfer.dispatched_date else "",
            "vehicle_details": transfer.vehicle_details,
            "waybill_number": transfer.waybill_number or transfer.transfer_number,
            "requested_by": transfer.requested_by.get_full_name() if transfer.requested_by else "",
            "approved_by": transfer.approved_by,
            "dispatched_by": transfer.dispatched_by,
            "items": items,
            "total_value": str(round(total_value, 2)),
            "total_qty": str(round(total_qty, 2)),
            "item_count": len(items),
            "qr_data": qr_data,
            "qr_hash": qr_hash,
        })


def _notify_transfer(transfer, action, user):
    """Send notification for transfer status changes."""
    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification
        from apps.accounts.models import UserProfile

        org = transfer.organization
        admins = [p.user for p in UserProfile.objects.filter(organization=org, role__in=["admin", "manager"], user__is_active=True).select_related("user")]

        messages = {
            "approved": f"Transfer {transfer.transfer_number} approved: {transfer.source_warehouse.name} → {transfer.destination_warehouse.name}.",
            "dispatched": f"Transfer {transfer.transfer_number} dispatched. Vehicle: {transfer.vehicle_details or 'TBD'}. Materials are now in transit.",
            "received": f"Transfer {transfer.transfer_number} received and confirmed at {transfer.destination_warehouse.name}. Stock updated.",
        }
        dispatch_workflow_notification(
            organization=org,
            event_key=f"material_transfer_{action}",
            recipients=admins,
            link_url="/material-management/transfers",
            fallback_channels=["in_app"],
            fallback_title=f"Transfer {action.title()} — {transfer.transfer_number}",
            fallback_message=messages.get(action, f"Transfer {transfer.transfer_number} status: {action}"),
            fallback_category=Notification.Category.PROCUREMENT_ORDER,
            fallback_severity=Notification.Severity.INFO,
        )
    except Exception:
        pass
