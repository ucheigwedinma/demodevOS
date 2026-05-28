from decimal import Decimal

from rest_framework import serializers

from .models import (
    BillOfMaterials,
    BOMItem,
    BoqTaskMapping,
    InventoryItem,
    InventoryStock,
    InventoryTransaction,
    Warehouse,
)

OUTBOUND_TYPES = {
    InventoryTransaction.TransactionType.ISSUE,
    InventoryTransaction.TransactionType.ADJUSTMENT_OUT,
    InventoryTransaction.TransactionType.TRANSFER_OUT,
}


class WarehouseSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True, default=None)

    class Meta:
        model = Warehouse
        fields = [
            "id",
            "code",
            "name",
            "location",
            "project",
            "project_name",
            "is_active",
            "is_default",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at", "project_name")


class InventoryItemListSerializer(serializers.ModelSerializer):
    preferred_vendor_name = serializers.CharField(
        source="preferred_vendor.name",
        read_only=True,
        allow_null=True,
    )
    expense_account_code = serializers.CharField(
        source="expense_account.code",
        read_only=True,
        allow_null=True,
    )
    expense_account_name = serializers.CharField(
        source="expense_account.name",
        read_only=True,
        allow_null=True,
    )
    cost_center_name = serializers.CharField(
        source="cost_center.name",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = InventoryItem
        fields = [
            "id",
            "sku",
            "name",
            "category",
            "unit_of_measure",
            "reorder_level",
            "target_stock_level",
            "default_unit_cost",
            "preferred_vendor",
            "preferred_vendor_name",
            "expense_account",
            "expense_account_code",
            "expense_account_name",
            "cost_center",
            "cost_center_name",
            "is_active",
            "created_at",
            "updated_at",
        ]


class InventoryItemDetailSerializer(InventoryItemListSerializer):
    class Meta(InventoryItemListSerializer.Meta):
        fields = InventoryItemListSerializer.Meta.fields + ["description"]


class InventoryItemWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = [
            "sku",
            "name",
            "description",
            "category",
            "unit_of_measure",
            "reorder_level",
            "target_stock_level",
            "default_unit_cost",
            "preferred_vendor",
            "expense_account",
            "cost_center",
            "is_active",
        ]


# ---------------------------------------------------------------------------
# Material Master Database serializers
# ---------------------------------------------------------------------------

MATERIAL_MASTER_SHARED_FIELDS = [
    "id",
    "sku",
    "name",
    "category",
    "subcategory",
    "unit_of_measure",
    "default_unit_cost",
    "preferred_vendor",
    "preferred_vendor_name",
    "lead_time_days",
    "target_stock_level",
    "reorder_level",
    "storage_requirements",
    "quality_specification",
    "material_grade",
    "alternative_materials",
    "hs_code",
    "compliance_requirements",
    "expense_account",
    "expense_account_code",
    "expense_account_name",
    "cost_center",
    "cost_center_name",
    "is_active",
    "created_at",
    "updated_at",
]


class MaterialMasterListSerializer(serializers.ModelSerializer):
    preferred_vendor_name = serializers.CharField(
        source="preferred_vendor.name", read_only=True, allow_null=True,
    )
    expense_account_code = serializers.CharField(
        source="expense_account.code", read_only=True, allow_null=True,
    )
    expense_account_name = serializers.CharField(
        source="expense_account.name", read_only=True, allow_null=True,
    )
    cost_center_name = serializers.CharField(
        source="cost_center.name", read_only=True, allow_null=True,
    )

    class Meta:
        model = InventoryItem
        fields = MATERIAL_MASTER_SHARED_FIELDS


class MaterialMasterDetailSerializer(MaterialMasterListSerializer):
    class Meta(MaterialMasterListSerializer.Meta):
        fields = MaterialMasterListSerializer.Meta.fields + ["description"]


class MaterialMasterWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = [
            "sku",
            "name",
            "description",
            "category",
            "subcategory",
            "unit_of_measure",
            "default_unit_cost",
            "preferred_vendor",
            "lead_time_days",
            "target_stock_level",
            "reorder_level",
            "storage_requirements",
            "quality_specification",
            "material_grade",
            "alternative_materials",
            "hs_code",
            "compliance_requirements",
            "expense_account",
            "cost_center",
            "is_active",
        ]
        extra_kwargs = {
            "description": {"required": False, "allow_blank": True},
            "subcategory": {"required": False, "allow_blank": True},
            "material_grade": {"required": False, "allow_blank": True},
            "lead_time_days": {"required": False, "allow_null": True},
            "storage_requirements": {"required": False, "allow_blank": True},
            "quality_specification": {"required": False, "allow_blank": True},
            "alternative_materials": {"required": False, "allow_blank": True},
            "hs_code": {"required": False, "allow_blank": True},
            "compliance_requirements": {"required": False, "allow_blank": True},
            "preferred_vendor": {"required": False, "allow_null": True},
            "expense_account": {"required": False, "allow_null": True},
            "cost_center": {"required": False, "allow_null": True},
        }


class InventoryStockSerializer(serializers.ModelSerializer):
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    warehouse_code = serializers.CharField(source="warehouse.code", read_only=True)
    item_sku = serializers.CharField(source="item.sku", read_only=True)
    item_name = serializers.CharField(source="item.name", read_only=True)
    item_category = serializers.CharField(source="item.category", read_only=True)
    reorder_level = serializers.DecimalField(
        source="item.reorder_level",
        max_digits=14,
        decimal_places=3,
        read_only=True,
    )
    target_stock_level = serializers.DecimalField(
        source="item.target_stock_level",
        max_digits=14,
        decimal_places=3,
        read_only=True,
    )
    available_quantity = serializers.SerializerMethodField()
    is_low_stock = serializers.SerializerMethodField()

    class Meta:
        model = InventoryStock
        fields = [
            "id",
            "warehouse",
            "warehouse_name",
            "warehouse_code",
            "item",
            "item_sku",
            "item_name",
            "item_category",
            "reorder_level",
            "target_stock_level",
            "quantity_on_hand",
            "quantity_reserved",
            "available_quantity",
            "average_unit_cost",
            "is_low_stock",
            "last_transaction_at",
            "updated_at",
        ]

    def get_available_quantity(self, obj):
        return obj.available_quantity

    def get_is_low_stock(self, obj):
        return obj.quantity_on_hand <= (obj.item.reorder_level or Decimal("0"))


class InventoryTransactionListSerializer(serializers.ModelSerializer):
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    warehouse_code = serializers.CharField(source="warehouse.code", read_only=True)
    item_sku = serializers.CharField(source="item.sku", read_only=True)
    item_name = serializers.CharField(source="item.name", read_only=True)
    item_uom = serializers.CharField(source="item.unit_of_measure", read_only=True)
    project_name = serializers.CharField(source="project.name", read_only=True, default=None)
    purchase_order_number = serializers.CharField(
        source="purchase_order.po_number",
        read_only=True,
        default=None,
    )
    goods_receipt_number = serializers.CharField(
        source="goods_receipt.grn_number",
        read_only=True,
        default=None,
    )
    performed_by_name = serializers.CharField(
        source="performed_by.get_full_name",
        read_only=True,
        default="",
    )
    transaction_type_display = serializers.CharField(
        source="get_transaction_type_display",
        read_only=True,
    )

    class Meta:
        model = InventoryTransaction
        fields = [
            "id",
            "transaction_type",
            "transaction_type_display",
            "warehouse",
            "warehouse_name",
            "warehouse_code",
            "item",
            "item_sku",
            "item_name",
            "item_uom",
            "project",
            "project_name",
            "purchase_order",
            "purchase_order_number",
            "goods_receipt",
            "goods_receipt_number",
            "goods_receipt_item",
            "quantity",
            "unit_cost",
            "total_cost",
            "transaction_date",
            "source_module",
            "source_reference",
            "notes",
            "performed_by",
            "performed_by_name",
            "created_at",
        ]
        read_only_fields = ("performed_by", "created_at")


class InventoryTransactionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryTransaction
        fields = [
            "transaction_type",
            "warehouse",
            "item",
            "project",
            "purchase_order",
            "goods_receipt",
            "goods_receipt_item",
            "quantity",
            "unit_cost",
            "total_cost",
            "transaction_date",
            "source_module",
            "source_reference",
            "notes",
        ]
        extra_kwargs = {
            "project": {"required": False, "allow_null": True},
            "purchase_order": {"required": False, "allow_null": True},
            "goods_receipt": {"required": False, "allow_null": True},
            "goods_receipt_item": {"required": False, "allow_null": True},
            "unit_cost": {"required": False, "allow_null": True},
            "total_cost": {"required": False},
            "source_module": {"required": False, "allow_blank": True},
            "source_reference": {"required": False, "allow_blank": True},
            "notes": {"required": False, "allow_blank": True},
        }

    def validate(self, attrs):
        attrs = super().validate(attrs)
        transaction_type = attrs.get(
            "transaction_type",
            getattr(self.instance, "transaction_type", None),
        )
        purchase_order = attrs.get(
            "purchase_order",
            getattr(self.instance, "purchase_order", None),
        )
        goods_receipt = attrs.get(
            "goods_receipt",
            getattr(self.instance, "goods_receipt", None),
        )
        goods_receipt_item = attrs.get(
            "goods_receipt_item",
            getattr(self.instance, "goods_receipt_item", None),
        )
        quantity = attrs.get("quantity", getattr(self.instance, "quantity", None))
        unit_cost = attrs.get("unit_cost", getattr(self.instance, "unit_cost", None))

        if goods_receipt and purchase_order and goods_receipt.purchase_order_id != purchase_order.id:
            raise serializers.ValidationError(
                {"goods_receipt": "Selected goods receipt does not belong to selected purchase order."}
            )

        if goods_receipt_item and goods_receipt and goods_receipt_item.goods_receipt_id != goods_receipt.id:
            raise serializers.ValidationError(
                {"goods_receipt_item": "Selected receipt item does not belong to selected goods receipt."}
            )

        if transaction_type == InventoryTransaction.TransactionType.RECEIPT and goods_receipt is None:
            raise serializers.ValidationError(
                {"goods_receipt": "Receipt transactions should be linked to a goods receipt."}
            )

        if quantity is not None and quantity <= 0:
            raise serializers.ValidationError({"quantity": "Quantity must be greater than zero."})

        if unit_cost is not None and unit_cost < 0:
            raise serializers.ValidationError({"unit_cost": "Unit cost cannot be negative."})

        if unit_cost is not None and quantity is not None:
            attrs["total_cost"] = unit_cost * quantity
        elif unit_cost is None and attrs.get("total_cost") is None:
            attrs["total_cost"] = Decimal("0.00")

        if (
            transaction_type in OUTBOUND_TYPES
            and not attrs.get("project")
            and not attrs.get("notes")
        ):
            raise serializers.ValidationError(
                {"notes": "Provide usage context or link the issue to a project."}
            )

        return attrs


# ---------------------------------------------------------------------------
# Bill of Materials serializers
# ---------------------------------------------------------------------------


class BOMItemSerializer(serializers.ModelSerializer):
    inventory_item_name = serializers.CharField(
        source="inventory_item.name", read_only=True, default=None,
    )
    supplier_vendor_name = serializers.CharField(
        source="supplier_vendor.name", read_only=True, default=None,
    )
    price_drift_pct = serializers.SerializerMethodField()
    effective_quantity = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    effective_line_total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = BOMItem
        fields = [
            "id", "inventory_item", "inventory_item_name",
            "material_name", "category", "quantity", "unit_of_measure",
            "unit_cost", "line_total", "notes", "sort_order",
            "supplier", "supplier_vendor", "supplier_vendor_name",
            "is_approved", "price_volatile", "original_unit_cost", "price_drift_pct",
            "price_source", "waste_factor_pct", "item_markup_pct",
            "lead_time_days", "source_bom", "section", "quantity_formula",
            "is_fx_linked", "unit_cost_usd",
            "effective_quantity", "effective_line_total",
        ]
        read_only_fields = ("id", "line_total", "price_drift_pct", "supplier_vendor_name", "effective_quantity", "effective_line_total")

    def get_price_drift_pct(self, obj):
        if obj.original_unit_cost and obj.original_unit_cost != 0:
            from decimal import Decimal
            drift = (obj.unit_cost - obj.original_unit_cost) / obj.original_unit_cost * 100
            return float(drift.quantize(Decimal("0.01")))
        return None


class BOMItemWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = BOMItem
        fields = [
            "inventory_item", "material_name", "category",
            "quantity", "unit_of_measure", "unit_cost", "notes", "sort_order",
            "supplier", "supplier_vendor", "is_approved", "price_volatile",
            "original_unit_cost", "price_source", "waste_factor_pct",
            "item_markup_pct", "lead_time_days", "source_bom", "section",
            "quantity_formula", "is_fx_linked", "unit_cost_usd",
        ]
        extra_kwargs = {
            "inventory_item": {"required": False, "allow_null": True},
            "category": {"required": False, "allow_blank": True},
            "notes": {"required": False, "allow_blank": True},
            "sort_order": {"required": False},
            "supplier": {"required": False, "allow_blank": True},
            "supplier_vendor": {"required": False, "allow_null": True},
            "is_approved": {"required": False},
            "price_volatile": {"required": False},
            "original_unit_cost": {"required": False, "allow_null": True},
            "price_source": {"required": False},
            "waste_factor_pct": {"required": False},
            "item_markup_pct": {"required": False},
            "lead_time_days": {"required": False},
            "source_bom": {"required": False, "allow_null": True},
            "section": {"required": False, "allow_blank": True},
            "quantity_formula": {"required": False, "allow_blank": True},
            "is_fx_linked": {"required": False},
            "unit_cost_usd": {"required": False},
        }


class BOMListSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(
        source="project.name", read_only=True, default=None,
    )
    created_by_name = serializers.SerializerMethodField()
    item_count = serializers.IntegerField(read_only=True)
    subtotal = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    vat_amount = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    margin_amount = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    grand_total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = BillOfMaterials
        fields = [
            "id",
            "bom_number",
            "name",
            "project",
            "project_name",
            "unit_type",
            "quantity_of_units",
            "status",
            "total_estimated_cost",
            "version",
            "parent_version",
            "confidence_pct",
            "margin_pct",
            "vat_pct",
            "site_location",
            "project_variables",
            "fx_rate_usd_ngn",
            "revision_reason",
            "is_baseline",
            "subtotal",
            "vat_amount",
            "margin_amount",
            "grand_total",
            "item_count",
            "created_at",
            "updated_at",
            "created_by",
            "created_by_name",
        ]

    def get_created_by_name(self, obj):
        u = obj.created_by
        if u:
            return f"{u.first_name} {u.last_name}".strip() or u.email
        return None


class BOMDetailSerializer(BOMListSerializer):
    items = BOMItemSerializer(many=True, read_only=True)

    class Meta(BOMListSerializer.Meta):
        fields = BOMListSerializer.Meta.fields + ["description", "items"]


class BOMWriteSerializer(serializers.ModelSerializer):
    items = BOMItemWriteSerializer(many=True, required=False)

    class Meta:
        model = BillOfMaterials
        fields = [
            "name",
            "description",
            "project",
            "unit_type",
            "quantity_of_units",
            "status",
            "confidence_pct",
            "margin_pct",
            "vat_pct",
            "site_location",
            "project_variables",
            "fx_rate_usd_ngn",
            "revision_reason",
            "is_baseline",
            "items",
        ]
        extra_kwargs = {
            "description": {"required": False, "allow_blank": True},
            "project": {"required": False, "allow_null": True},
            "unit_type": {"required": False, "allow_blank": True},
            "quantity_of_units": {"required": False},
            "status": {"required": False},
            "confidence_pct": {"required": False},
            "margin_pct": {"required": False},
            "vat_pct": {"required": False},
            "site_location": {"required": False, "allow_blank": True},
            "revision_reason": {"required": False, "allow_blank": True},
            "is_baseline": {"required": False},
        }

    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        bom = BillOfMaterials.objects.create(**validated_data)
        for idx, item_data in enumerate(items_data):
            item_data.setdefault("sort_order", idx)
            BOMItem.objects.create(bom=bom, **item_data)
        bom.recalculate_total()
        bom.refresh_from_db()
        return bom

    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if items_data is not None:
            instance.items.all().delete()
            for idx, item_data in enumerate(items_data):
                item_data.setdefault("sort_order", idx)
                BOMItem.objects.create(bom=instance, **item_data)
            instance.recalculate_total()
            instance.refresh_from_db()
        return instance


# ── BoQ → Schedule Mapping ───────────────────────────────────────────


class BoqTaskMappingSerializer(serializers.ModelSerializer):
    bom_item_name = serializers.CharField(source="bom_item.material_name", read_only=True)
    bom_item_unit = serializers.CharField(source="bom_item.unit_of_measure", read_only=True)
    bom_item_unit_cost = serializers.DecimalField(
        source="bom_item.unit_cost", max_digits=12, decimal_places=2, read_only=True,
    )
    bom_item_lead_time = serializers.IntegerField(
        source="bom_item.lead_time_days", read_only=True, default=0,
    )
    bom_item_section = serializers.CharField(
        source="bom_item.section.title", read_only=True, default="",
    )
    project_name = serializers.CharField(source="project.name", read_only=True)
    phase_name = serializers.CharField(source="phase.name", read_only=True, default=None)
    task_name = serializers.CharField(source="task.title", read_only=True, default=None)
    task_start_date = serializers.DateField(source="task.start_date", read_only=True, default=None)

    class Meta:
        model = BoqTaskMapping
        fields = (
            "id", "bom", "bom_item", "bom_item_name", "bom_item_unit",
            "bom_item_unit_cost", "bom_item_lead_time", "bom_item_section",
            "project", "project_name",
            "phase", "phase_name",
            "task", "task_name", "task_start_date",
            "allocated_quantity", "allocated_cost",
            "delivery_deadline", "material_status", "has_lead_time_conflict",
            "notes", "created_at", "updated_at",
        )
        read_only_fields = ("id", "allocated_cost", "has_lead_time_conflict", "created_at", "updated_at")


class BoqTaskMappingWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = BoqTaskMapping
        fields = (
            "bom", "bom_item", "project", "phase", "task",
            "allocated_quantity", "delivery_deadline", "material_status", "notes",
        )


# ── BOQ Category → Planning Template Mapping ─────────────────────────

from apps.inventory.models import BoqCategoryMapping


class BoqCategoryMappingSerializer(serializers.ModelSerializer):
    template_phase_name = serializers.CharField(source="template_phase.name", read_only=True)
    template_name = serializers.CharField(source="template_phase.template.name", read_only=True)

    class Meta:
        model = BoqCategoryMapping
        fields = (
            "id", "boq_category", "template_phase", "template_phase_name",
            "template_name", "default_production_rate", "split_threshold",
            "sort_order", "created_at",
        )
        extra_kwargs = {"template_phase": {"required": True}}


# ── Rate Library ─────────────────────────────────────────────────────

from apps.inventory.models import RateBook, RateItem, RateCompositeComponent, RateHistory


class RateHistorySerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(source="changed_by.get_full_name", read_only=True, default="")

    class Meta:
        model = RateHistory
        fields = ("id", "rate", "recorded_at", "changed_by", "changed_by_name", "notes")


class RateCompositeComponentSerializer(serializers.ModelSerializer):
    component_code = serializers.CharField(source="component_rate.item_code", read_only=True)
    component_description = serializers.CharField(source="component_rate.description", read_only=True)
    component_unit = serializers.CharField(source="component_rate.unit", read_only=True)
    component_base_rate = serializers.DecimalField(source="component_rate.base_rate", max_digits=14, decimal_places=2, read_only=True)
    line_cost = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = RateCompositeComponent
        fields = (
            "id", "composite_rate", "component_rate", "quantity",
            "component_code", "component_description", "component_unit", "component_base_rate", "line_cost",
        )
        extra_kwargs = {"composite_rate": {"read_only": True}}


class RateBookListSerializer(serializers.ModelSerializer):
    item_count = serializers.IntegerField(read_only=True, default=0)
    created_by_name = serializers.CharField(source="created_by.get_full_name", read_only=True, default="")

    class Meta:
        model = RateBook
        fields = (
            "id", "name", "description", "is_active", "fx_rate_usd_ngn",
            "last_synced_at", "item_count", "created_by", "created_by_name",
            "created_at", "updated_at",
        )


class RateBookWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = RateBook
        fields = ("name", "description", "is_active", "fx_rate_usd_ngn")


class RateItemListSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier_vendor.name", read_only=True, default="")
    is_stale = serializers.BooleanField(read_only=True)
    total_landed_cost = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = RateItem
        fields = (
            "id", "item_code", "description", "unit", "base_rate", "base_rate_usd",
            "is_fx_linked", "location", "category", "status",
            "purchase_price", "shipping_cost", "handling_fee", "duty_pct",
            "supplier_vendor", "supplier_name", "is_composite", "is_stale",
            "total_landed_cost", "last_verified_at", "created_at", "updated_at",
        )


class RateItemDetailSerializer(RateItemListSerializer):
    components = RateCompositeComponentSerializer(many=True, read_only=True)
    history = RateHistorySerializer(many=True, read_only=True)

    class Meta(RateItemListSerializer.Meta):
        fields = RateItemListSerializer.Meta.fields + ("notes", "components", "history")


class RateItemWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = RateItem
        fields = (
            "item_code", "description", "unit", "base_rate", "base_rate_usd",
            "is_fx_linked", "location", "category", "status",
            "purchase_price", "shipping_cost", "handling_fee", "duty_pct",
            "supplier_vendor", "is_composite", "notes",
        )
        extra_kwargs = {"supplier_vendor": {"required": False, "allow_null": True}}


# ── Material Requisition (Site Requests) ─────────────────────────────

from .models import MaterialRequisition, MaterialRequisitionLine, MaterialRequisitionComment, MaterialRequisitionAuditLog


class MaterialRequisitionLineSerializer(serializers.ModelSerializer):
    material_name_display = serializers.CharField(source="material.name", read_only=True, default="")

    class Meta:
        model = MaterialRequisitionLine
        fields = (
            "id", "requisition", "material", "material_name", "material_name_display",
            "quantity", "unit_of_measure", "required_by_date", "phase_area",
            "line_justification", "unit_cost", "estimated_cost", "available_stock",
            "issued_quantity", "issued_from_warehouse", "issued_at", "issued_by",
            "sort_order", "notes",
        )
        extra_kwargs = {
            "requisition": {"read_only": True},
            "estimated_cost": {"read_only": True},
            "available_stock": {"read_only": True},
        }


class MaterialRequisitionCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.get_full_name", read_only=True, default="")

    class Meta:
        model = MaterialRequisitionComment
        fields = ("id", "requisition", "author", "author_name", "author_role", "message", "created_at")
        extra_kwargs = {"requisition": {"read_only": True}, "author": {"read_only": True}}


class MaterialRequisitionAuditLogSerializer(serializers.ModelSerializer):
    performed_by_name = serializers.CharField(source="performed_by.get_full_name", read_only=True, default="")

    class Meta:
        model = MaterialRequisitionAuditLog
        fields = ("id", "action", "field_changed", "old_value", "new_value", "performed_by", "performed_by_name", "performed_at", "notes")


class MaterialRequisitionListSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True, default="")
    phase_name = serializers.CharField(source="phase.name", read_only=True, default="")
    created_by_name = serializers.CharField(source="created_by.get_full_name", read_only=True, default="")
    line_count = serializers.IntegerField(read_only=True, default=0)
    estimated_total = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    fulfilment_pct = serializers.IntegerField(read_only=True)

    class Meta:
        model = MaterialRequisition
        fields = (
            "id", "requisition_id", "project", "project_name", "phase", "phase_name",
            "status", "urgency", "site_location", "requested_delivery_date",
            "justification", "cost_code", "current_step",
            "line_count", "estimated_total", "fulfilment_pct",
            "created_by", "created_by_name", "created_at", "updated_at",
        )


class MaterialRequisitionDetailSerializer(MaterialRequisitionListSerializer):
    lines = MaterialRequisitionLineSerializer(many=True, read_only=True)
    comments = MaterialRequisitionCommentSerializer(many=True, read_only=True)
    audit_logs = MaterialRequisitionAuditLogSerializer(many=True, read_only=True)

    class Meta(MaterialRequisitionListSerializer.Meta):
        fields = MaterialRequisitionListSerializer.Meta.fields + (
            "delivery_instructions",
            "submitted_at", "approved_by_se", "approved_by_se_at",
            "approved_by_pm", "approved_by_pm_at",
            "approved_by_proc", "approved_by_proc_at",
            "fulfilled_by_store", "fulfilled_at",
            "rejected_by", "rejected_at", "rejection_reason",
            "lines", "comments", "audit_logs",
        )


class MaterialRequisitionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialRequisition
        fields = (
            "project", "phase", "urgency", "site_location",
            "requested_delivery_date", "justification", "cost_code",
            "delivery_instructions",
        )


# ── Material Issue to Construction ───────────────────────────────────

from .models import MaterialIssue, MaterialIssueLine


class MaterialIssueLineSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True, default="")
    item_sku = serializers.CharField(source="item.sku", read_only=True, default="")
    item_category = serializers.CharField(source="item.category", read_only=True, default="")
    line_value = serializers.SerializerMethodField()

    class Meta:
        model = MaterialIssueLine
        fields = (
            "id", "issue", "item", "item_name", "item_sku", "item_category",
            "requested_quantity", "issued_quantity", "unit_of_measure",
            "unit_cost", "line_value", "purpose", "sort_order",
        )
        extra_kwargs = {"issue": {"read_only": True}}

    def get_line_value(self, obj):
        return str((obj.issued_quantity or 0) * (obj.unit_cost or 0))


class MaterialIssueListSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True, default="")
    phase_name = serializers.CharField(source="phase.name", read_only=True, default="")
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True, default="")
    requested_by_name = serializers.CharField(source="requested_by.get_full_name", read_only=True, default="")
    line_count = serializers.IntegerField(read_only=True, default=0)
    total_value = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)

    class Meta:
        model = MaterialIssue
        fields = (
            "id", "issue_number", "project", "project_name", "phase", "phase_name",
            "warehouse", "warehouse_name", "status",
            "requested_by", "requested_by_name", "requested_date",
            "approved_by", "approved_date", "issued_by", "issued_date",
            "purpose", "cost_code", "line_count", "total_value",
            "created_at", "updated_at",
        )


class MaterialIssueDetailSerializer(MaterialIssueListSerializer):
    lines = MaterialIssueLineSerializer(many=True, read_only=True)

    class Meta(MaterialIssueListSerializer.Meta):
        fields = MaterialIssueListSerializer.Meta.fields + ("notes", "lines",)


class MaterialIssueWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialIssue
        fields = ("project", "phase", "warehouse", "purpose", "cost_code", "notes")


# ── Variance Investigation ───────────────────────────────────────────

from .models import VarianceInvestigation, VarianceInvestigationPhoto


class VariancePhotoSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = VarianceInvestigationPhoto
        fields = ("id", "image", "image_url", "caption", "created_at")

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get("request")
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None


class VarianceInvestigationSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True, default="")
    investigated_by_name = serializers.CharField(source="investigated_by.get_full_name", read_only=True, default="")
    photos = VariancePhotoSerializer(many=True, read_only=True)

    class Meta:
        model = VarianceInvestigation
        fields = (
            "id", "project", "project_name", "material_name", "work_package",
            "root_cause", "severity", "status",
            "planned_quantity", "actual_quantity", "variance_quantity", "variance_pct", "unit",
            "supervisor_notes", "corrective_action", "financial_impact",
            "investigated_by", "investigated_by_name", "photos",
            "created_at", "updated_at",
        )
        extra_kwargs = {"investigated_by": {"read_only": True}}


class VarianceInvestigationWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = VarianceInvestigation
        fields = (
            "project", "material_name", "work_package", "root_cause", "severity",
            "planned_quantity", "actual_quantity", "variance_quantity", "variance_pct", "unit",
            "supervisor_notes", "corrective_action", "financial_impact",
        )


# ── Material Transfers ───────────────────────────────────────────────

from .models import MaterialTransfer, MaterialTransferLine


class MaterialTransferLineSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True, default="")
    item_sku = serializers.CharField(source="item.sku", read_only=True, default="")
    line_value = serializers.SerializerMethodField()

    class Meta:
        model = MaterialTransferLine
        fields = ("id", "transfer", "item", "item_name", "item_sku", "quantity", "received_quantity", "unit_of_measure", "unit_cost", "line_value", "sort_order", "notes")
        extra_kwargs = {"transfer": {"read_only": True}}

    def get_line_value(self, obj):
        return str((obj.quantity or 0) * (obj.unit_cost or 0))


class MaterialTransferListSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source="source_warehouse.name", read_only=True, default="")
    destination_name = serializers.CharField(source="destination_warehouse.name", read_only=True, default="")
    project_name = serializers.CharField(source="project.name", read_only=True, default="")
    requested_by_name = serializers.CharField(source="requested_by.get_full_name", read_only=True, default="")
    line_count = serializers.IntegerField(read_only=True, default=0)
    total_value = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)

    class Meta:
        model = MaterialTransfer
        fields = (
            "id", "transfer_number", "source_warehouse", "source_name",
            "destination_warehouse", "destination_name", "project", "project_name",
            "status", "priority", "reason", "scheduled_date",
            "dispatched_date", "delivered_date", "confirmed_date",
            "dispatched_by", "received_by", "vehicle_details", "waybill_number",
            "requested_by", "requested_by_name", "approved_by",
            "line_count", "total_value", "created_at", "updated_at",
        )


# ── Returns Management ───────────────────────────────────────────────

from .models import MaterialReturn, MaterialReturnLine


class MaterialReturnLineSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True, default="")
    item_sku = serializers.CharField(source="item.sku", read_only=True, default="")
    line_value = serializers.SerializerMethodField()

    class Meta:
        model = MaterialReturnLine
        fields = ("id", "return_order", "item", "item_name", "item_sku", "quantity", "received_quantity", "unit_of_measure", "unit_cost", "line_value", "condition", "sort_order", "notes")
        extra_kwargs = {"return_order": {"read_only": True}}

    def get_line_value(self, obj):
        return str((obj.quantity or 0) * (obj.unit_cost or 0))


class MaterialReturnListSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True, default="")
    source_name = serializers.CharField(source="source_warehouse.name", read_only=True, default="")
    destination_name = serializers.CharField(source="destination_warehouse.name", read_only=True, default="")
    vendor_name = serializers.CharField(source="vendor.name", read_only=True, default="")
    requested_by_name = serializers.CharField(source="requested_by.get_full_name", read_only=True, default="")
    line_count = serializers.IntegerField(read_only=True, default=0)
    total_value = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)

    class Meta:
        model = MaterialReturn
        fields = (
            "id", "return_number", "return_type", "project", "project_name",
            "source_warehouse", "source_name", "destination_warehouse", "destination_name",
            "vendor", "vendor_name", "status", "reason", "reason_detail",
            "requested_by", "requested_by_name", "approved_by", "approved_date",
            "dispatched_date", "received_date",
            "credit_memo_number", "credit_amount", "credit_received_date",
            "line_count", "total_value", "created_at", "updated_at",
        )


class MaterialReturnDetailSerializer(MaterialReturnListSerializer):
    lines = MaterialReturnLineSerializer(many=True, read_only=True)

    class Meta(MaterialReturnListSerializer.Meta):
        fields = MaterialReturnListSerializer.Meta.fields + ("notes", "lines",)


class MaterialReturnWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialReturn
        fields = ("return_type", "project", "source_warehouse", "destination_warehouse", "vendor", "reason", "reason_detail", "notes")


class MaterialTransferDetailSerializer(MaterialTransferListSerializer):
    lines = MaterialTransferLineSerializer(many=True, read_only=True)

    class Meta(MaterialTransferListSerializer.Meta):
        fields = MaterialTransferListSerializer.Meta.fields + ("notes", "lines",)


class MaterialTransferWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialTransfer
        fields = ("source_warehouse", "destination_warehouse", "project", "priority", "reason", "scheduled_date", "vehicle_details", "waybill_number", "notes")
