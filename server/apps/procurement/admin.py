from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from apps.admin_mixins import OrgScopedAdminMixin

from .models import (
    GoodsReceipt,
    GoodsReceiptItem,
    ProcurementDemandInsight,
    ProjectProcurementWorkspace,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseRequisition,
    PurchaseRequisitionItem,
    RequestForQuotation,
    RequestForQuotationQuote,
    Contract,
    ContractAmendment,
    ContractClause,
    Vendor,
    VendorCategory,
)


@admin.register(Vendor)
class VendorAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "name", "category", "compliance_status",
        "performance_rating", "is_blacklisted", "is_active",
    ]
    list_filter = ["category", "compliance_status", "is_blacklisted", "is_active"]
    search_fields = ["name", "contact_person", "email"]
    fieldsets = (
        ("Contact Information", {
            "fields": ("name", "contact_person", "email", "phone", "address", "tax_id"),
        }),
        ("Classification", {
            "fields": ("category", "is_active", "approved_projects"),
        }),
        ("Banking", {
            "fields": ("bank_name", "bank_account_number", "bank_branch"),
        }),
        ("Vendor Intelligence", {
            "fields": (
                "performance_rating", "delivery_timeliness_score",
                "price_competitiveness", "compliance_status",
                "is_blacklisted", "blacklist_reason",
            ),
        }),
        ("Notes", {
            "fields": ("notes",),
        }),
    )


class PurchaseRequisitionItemInline(TabularInline):
    model = PurchaseRequisitionItem
    extra = 0
    fields = ["description", "quantity", "unit_of_measure", "estimated_unit_price", "estimated_amount", "sort_order"]
    readonly_fields = ["estimated_amount"]


class PurchaseOrderItemInline(TabularInline):
    model = PurchaseOrderItem
    extra = 0
    fields = ["description", "quantity", "unit_of_measure", "unit_price", "amount", "sort_order"]
    readonly_fields = ["amount"]


class GoodsReceiptItemInline(TabularInline):
    model = GoodsReceiptItem
    extra = 0
    fields = ["po_item", "quantity_received", "quantity_accepted", "quantity_rejected", "rejection_reason"]


class RFQQuoteInline(TabularInline):
    model = RequestForQuotationQuote
    extra = 0
    fields = [
        "vendor", "quote_number", "quote_date", "quoted_amount",
        "technical_score", "commercial_score", "compliance_score",
        "total_score", "status",
    ]
    readonly_fields = ["total_score"]


@admin.register(PurchaseRequisition)
class PurchaseRequisitionAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["pr_number", "title", "status", "requester", "priority", "required_date", "estimated_total"]
    list_filter = ["status", "priority"]
    search_fields = ["pr_number", "title", "requester"]
    inlines = [PurchaseRequisitionItemInline]


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["po_number", "vendor", "status", "total_amount", "issue_date", "expected_delivery_date"]
    list_filter = ["status", "vendor"]
    search_fields = ["po_number", "vendor__name", "notes"]
    inlines = [PurchaseOrderItemInline]


@admin.register(GoodsReceipt)
class GoodsReceiptAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["grn_number", "purchase_order", "status", "received_date", "received_by"]
    list_filter = ["status"]
    search_fields = ["grn_number", "purchase_order__po_number"]
    inlines = [GoodsReceiptItemInline]


@admin.register(RequestForQuotation)
class RequestForQuotationAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "rfq_number", "title", "status", "issue_date",
        "submission_deadline", "estimated_value", "selected_vendor",
    ]
    list_filter = ["status", "issue_date", "submission_deadline"]
    search_fields = ["rfq_number", "title", "budget_code", "cost_code"]
    inlines = [RFQQuoteInline]


@admin.register(RequestForQuotationQuote)
class RequestForQuotationQuoteAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "rfq", "vendor", "quote_number", "quoted_amount",
        "total_score", "status", "quote_date",
    ]
    list_filter = ["status", "quote_date"]
    search_fields = ["rfq__rfq_number", "vendor__name", "quote_number"]


@admin.register(ProjectProcurementWorkspace)
class ProjectProcurementWorkspaceAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "project",
        "workspace_type",
        "name",
        "menu_group",
        "menu_path",
        "is_active",
    ]
    list_filter = ["workspace_type", "menu_group", "is_active"]
    search_fields = ["project__name", "name", "menu_path"]


@admin.register(ProcurementDemandInsight)
class ProcurementDemandInsightAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "area_name",
        "insight_type",
        "demand_share_percent",
        "lead_count",
        "bulk_buyer_lead_count",
        "is_active",
        "updated_at",
    ]
    list_filter = ["insight_type", "source_module", "is_active"]
    search_fields = ["area_name", "title", "summary"]


class ContractAmendmentInline(TabularInline):
    model = ContractAmendment
    extra = 0
    fields = ["amendment_number", "amendment_type", "title", "status", "value_change", "time_extension_days"]


class ContractClauseInline(TabularInline):
    model = ContractClause
    extra = 0
    fields = ["clause_number", "title", "category", "is_critical", "sort_order"]


@admin.register(Contract)
class ContractAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["contract_number", "title", "vendor", "contract_type", "status", "original_value", "effective_date", "expiry_date"]
    list_filter = ["contract_type", "status", "is_price_locked"]
    search_fields = ["contract_number", "title", "vendor__name", "scope_of_work"]
    inlines = [ContractAmendmentInline, ContractClauseInline]


@admin.register(VendorCategory)
class VendorCategoryAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["name", "code", "parent", "is_active", "sort_order"]
    list_filter = ["is_active", "parent"]
    search_fields = ["name", "code"]
