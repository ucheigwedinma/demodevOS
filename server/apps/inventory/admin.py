from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from apps.admin_mixins import OrgScopedAdminMixin

from .models import (
    BillOfMaterials,
    BOMItem,
    InventoryItem,
    InventoryStock,
    InventoryTransaction,
    ProcurementItemMapping,
    Warehouse,
)


@admin.register(Warehouse)
class WarehouseAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["code", "name", "project", "is_active", "is_default", "updated_at"]
    list_filter = ["is_active", "is_default"]
    search_fields = ["code", "name", "project__name", "location"]


@admin.register(InventoryItem)
class InventoryItemAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "sku",
        "name",
        "category",
        "subcategory",
        "unit_of_measure",
        "material_grade",
        "reorder_level",
        "default_unit_cost",
        "lead_time_days",
        "is_active",
    ]
    list_filter = ["category", "is_active", "material_grade"]
    search_fields = ["sku", "name", "description", "subcategory", "hs_code"]


@admin.register(InventoryStock)
class InventoryStockAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "warehouse",
        "item",
        "quantity_on_hand",
        "quantity_reserved",
        "average_unit_cost",
        "last_transaction_at",
    ]
    list_filter = ["warehouse", "item__category"]
    search_fields = ["warehouse__name", "warehouse__code", "item__sku", "item__name"]


@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "transaction_date",
        "transaction_type",
        "item",
        "warehouse",
        "project",
        "quantity",
        "total_cost",
    ]
    list_filter = ["transaction_type", "warehouse", "project"]
    search_fields = [
        "item__sku",
        "item__name",
        "warehouse__code",
        "project__name",
        "source_reference",
    ]


@admin.register(ProcurementItemMapping)
class ProcurementItemMappingAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["po_item", "inventory_item", "created_at"]
    search_fields = ["po_item__description", "inventory_item__sku", "inventory_item__name"]


class BOMItemInline(TabularInline):
    model = BOMItem
    fk_name = "bom"
    fields = ["material_name", "category", "quantity", "unit_of_measure", "unit_cost", "line_total", "sort_order"]
    readonly_fields = ["line_total"]
    extra = 1


@admin.register(BillOfMaterials)
class BillOfMaterialsAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "bom_number",
        "name",
        "project",
        "unit_type",
        "status",
        "total_estimated_cost",
        "created_at",
    ]
    list_filter = ["status"]
    search_fields = ["bom_number", "name", "project__name", "unit_type"]
    inlines = [BOMItemInline]

