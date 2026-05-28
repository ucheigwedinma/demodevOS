from decimal import Decimal

from django.db.models import Sum
from rest_framework import serializers

from apps.finance.serializers import BillListSerializer

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

# --- Vendor serializers ---

class ApprovedProjectSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()


class VendorCategorySerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source="parent.name", read_only=True, default=None)
    vendor_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = VendorCategory
        fields = (
            "id", "name", "code", "parent", "parent_name",
            "description", "is_active", "sort_order",
            "vendor_count", "created_at",
        )
        read_only_fields = ("id", "created_at")


class VendorListSerializer(serializers.ModelSerializer):
    po_count = serializers.IntegerField(read_only=True)
    total_po_value = serializers.DecimalField(
        max_digits=15, decimal_places=2, read_only=True
    )

    class Meta:
        model = Vendor
        fields = [
            "id", "name", "contact_person", "email", "phone",
            "category", "is_active", "is_blacklisted",
            "performance_rating", "compliance_status",
            "created_at", "updated_at", "po_count", "total_po_value",
        ]


class VendorDetailSerializer(serializers.ModelSerializer):
    po_count = serializers.IntegerField(read_only=True)
    total_po_value = serializers.DecimalField(
        max_digits=15, decimal_places=2, read_only=True
    )
    approved_projects_detail = ApprovedProjectSerializer(
        source="approved_projects", many=True, read_only=True
    )

    class Meta:
        model = Vendor
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class VendorWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = [
            "name", "contact_person", "email", "phone",
            "address", "tax_id", "notes", "is_active",
            "category", "bank_name", "bank_account_number", "bank_branch",
            "approved_projects",
            "performance_rating", "delivery_timeliness_score",
            "price_competitiveness", "compliance_status",
            "is_blacklisted", "blacklist_reason",
        ]


# --- Purchase Requisition serializers ---

class PRItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseRequisitionItem
        fields = "__all__"
        read_only_fields = ("id", "requisition", "estimated_amount")


class PRListSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True, default=None)
    property_name = serializers.CharField(source="property.name", read_only=True, default=None)
    item_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = PurchaseRequisition
        fields = [
            "id", "pr_number", "title", "status", "requester",
            "project", "project_name", "property", "property_name",
            "priority", "required_date", "estimated_total",
            "budget_line_item", "budget_code", "cost_code",
            "item_count",
            "created_at", "updated_at",
        ]


class PRDetailSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True, default=None)
    property_name = serializers.CharField(source="property.name", read_only=True, default=None)
    items = PRItemSerializer(many=True, read_only=True)
    item_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = PurchaseRequisition
        fields = "__all__"
        read_only_fields = ("id", "estimated_total", "created_at", "updated_at")


class PRWriteSerializer(serializers.ModelSerializer):
    pr_number = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = PurchaseRequisition
        fields = [
            "pr_number", "title", "status", "requester",
            "project", "property", "priority", "required_date",
            "budget_line_item", "budget_code", "cost_code",
            "justification", "notes",
            "approved_by", "approved_date", "rejected_reason",
        ]


# --- Purchase Order serializers ---

class POItemSerializer(serializers.ModelSerializer):
    quantity_received = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    quantity_remaining = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = PurchaseOrderItem
        fields = "__all__"
        read_only_fields = ("id", "purchase_order", "amount")


class GRNItemSerializer(serializers.ModelSerializer):
    po_item_description = serializers.CharField(
        source="po_item.description", read_only=True
    )

    class Meta:
        model = GoodsReceiptItem
        fields = "__all__"
        read_only_fields = ("id", "goods_receipt")


class GRNListSerializer(serializers.ModelSerializer):
    po_number = serializers.CharField(
        source="purchase_order.po_number", read_only=True
    )
    vendor_name = serializers.CharField(
        source="purchase_order.vendor.name", read_only=True
    )
    item_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = GoodsReceipt
        fields = [
            "id", "grn_number", "purchase_order", "po_number",
            "vendor_name", "status", "received_date", "received_by",
            "delivery_note_number", "item_count", "created_at",
        ]


class GRNDetailSerializer(serializers.ModelSerializer):
    po_number = serializers.CharField(
        source="purchase_order.po_number", read_only=True
    )
    vendor_name = serializers.CharField(
        source="purchase_order.vendor.name", read_only=True
    )
    items = GRNItemSerializer(many=True, read_only=True)

    class Meta:
        model = GoodsReceipt
        fields = "__all__"
        read_only_fields = ("id", "created_at")


class GRNWriteSerializer(serializers.ModelSerializer):
    grn_number = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = GoodsReceipt
        fields = [
            "grn_number", "purchase_order", "status",
            "received_date", "received_by",
            "delivery_note_number", "inspection_notes", "notes",
        ]


class POListSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)
    project_name = serializers.CharField(source="project.name", read_only=True, default=None)
    property_name = serializers.CharField(source="property.name", read_only=True, default=None)
    requisition_number = serializers.CharField(
        source="requisition.pr_number", read_only=True, default=None
    )
    is_fully_received = serializers.BooleanField(read_only=True)
    item_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            "id", "po_number", "vendor", "vendor_name",
            "project", "project_name", "property", "property_name",
            "requisition", "requisition_number",
            "status", "issue_date", "expected_delivery_date",
            "budget_line_item", "budget_code", "cost_code",
            "total_amount", "is_fully_received", "item_count",
            "created_at", "updated_at",
        ]


class PODetailSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)
    project_name = serializers.CharField(source="project.name", read_only=True, default=None)
    property_name = serializers.CharField(source="property.name", read_only=True, default=None)
    requisition_number = serializers.CharField(
        source="requisition.pr_number", read_only=True, default=None
    )
    items = POItemSerializer(many=True, read_only=True)
    goods_receipts = GRNListSerializer(many=True, read_only=True)
    bills = BillListSerializer(many=True, read_only=True)
    is_fully_received = serializers.BooleanField(read_only=True)
    three_way_match = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseOrder
        fields = "__all__"
        read_only_fields = ("id", "subtotal", "total_amount", "created_at", "updated_at")

    def get_three_way_match(self, obj):
        po_total = obj.total_amount or Decimal("0.00")

        # GRN accepted total (sum of accepted qty × unit_price)
        grn_accepted_total = Decimal("0.00")
        for item in obj.items.all():
            accepted_qty = item.receipt_items.aggregate(
                total=Sum("quantity_accepted")
            )["total"] or Decimal("0")
            grn_accepted_total += accepted_qty * item.unit_price

        # Invoice total (sum of linked bills)
        invoice_total = Decimal("0.00")
        for bill in obj.bills.all():
            invoice_total += bill.total_amount or Decimal("0.00")

        qty_match = grn_accepted_total == po_total if po_total > 0 else False
        amount_match = invoice_total == po_total if po_total > 0 else False

        if po_total == 0:
            status = "pending"
        elif qty_match and amount_match:
            status = "full_match"
        elif grn_accepted_total == 0 and invoice_total == 0:
            status = "pending"
        elif qty_match or amount_match:
            status = "partial_match"
        else:
            status = "mismatch"

        return {
            "po_total": str(po_total),
            "grn_accepted_total": str(grn_accepted_total),
            "invoice_total": str(invoice_total),
            "qty_match": qty_match,
            "amount_match": amount_match,
            "status": status,
        }


class POWriteSerializer(serializers.ModelSerializer):
    po_number = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            "po_number", "requisition", "vendor",
            "project", "property", "status",
            "issue_date", "expected_delivery_date",
            "delivery_address", "budget_line_item", "budget_code", "cost_code",
            "tax_amount", "payment_terms", "notes",
            "approved_by", "approved_date",
        ]


# --- Request for Quotation (RFQ) serializers ---

class RFQQuoteListSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)

    class Meta:
        model = RequestForQuotationQuote
        fields = [
            "id", "rfq", "vendor", "vendor_name", "quote_number", "quote_date",
            "validity_date", "quoted_amount", "delivery_days", "warranty_terms",
            "payment_terms", "compliance_score", "technical_score",
            "commercial_score", "total_score", "status", "notes",
            "submitted_at", "updated_at",
        ]


class RFQQuoteDetailSerializer(RFQQuoteListSerializer):
    class Meta(RFQQuoteListSerializer.Meta):
        fields = "__all__"
        read_only_fields = ("id", "submitted_at", "updated_at", "total_score")


class RFQQuoteWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestForQuotationQuote
        fields = [
            "rfq", "vendor", "quote_number", "quote_date", "validity_date",
            "quoted_amount", "delivery_days", "warranty_terms", "payment_terms",
            "compliance_score", "technical_score", "commercial_score",
            "status", "notes",
        ]


class RFQListSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True, default=None)
    property_name = serializers.CharField(source="property.name", read_only=True, default=None)
    requisition_number = serializers.CharField(
        source="requisition.pr_number", read_only=True, default=None
    )
    selected_vendor_name = serializers.CharField(
        source="selected_vendor.name", read_only=True, default=None
    )
    quote_count = serializers.IntegerField(read_only=True)
    lowest_quote = serializers.DecimalField(
        max_digits=15, decimal_places=2, read_only=True, allow_null=True
    )

    class Meta:
        model = RequestForQuotation
        fields = [
            "id", "rfq_number", "title", "status",
            "requisition", "requisition_number",
            "project", "project_name", "property", "property_name",
            "issue_date", "submission_deadline",
            "estimated_value", "budget_line_item", "budget_code", "cost_code",
            "selected_vendor", "selected_vendor_name",
            "quote_count", "lowest_quote",
            "created_at", "updated_at",
        ]


class RFQDetailSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True, default=None)
    property_name = serializers.CharField(source="property.name", read_only=True, default=None)
    requisition_number = serializers.CharField(
        source="requisition.pr_number", read_only=True, default=None
    )
    selected_vendor_name = serializers.CharField(
        source="selected_vendor.name", read_only=True, default=None
    )
    quotes = RFQQuoteListSerializer(many=True, read_only=True)

    class Meta:
        model = RequestForQuotation
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "selection_date")


class RFQWriteSerializer(serializers.ModelSerializer):
    rfq_number = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = RequestForQuotation
        fields = [
            "rfq_number", "title", "status", "requisition",
            "project", "property", "issue_date", "submission_deadline",
            "estimated_value", "budget_line_item", "budget_code", "cost_code",
            "selected_vendor", "selection_notes", "notes",
        ]


# ── Contracts & Agreements ───────────────────────────────────────────


class ContractClauseSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = ContractClause
        fields = (
            "id", "contract", "clause_number", "title", "category", "category_display",
            "body", "is_critical", "sort_order", "notes", "created_at",
        )
        read_only_fields = ("id", "contract", "created_at")


class ContractAmendmentSerializer(serializers.ModelSerializer):
    amendment_type_display = serializers.CharField(source="get_amendment_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = ContractAmendment
        fields = (
            "id", "contract", "amendment_number", "amendment_type", "amendment_type_display",
            "title", "description", "status", "status_display",
            "value_change", "time_extension_days", "effective_date",
            "approved_by", "approved_date", "reason", "notes", "created_at",
        )
        read_only_fields = ("id", "contract", "created_at")


class ContractListSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)
    project_name = serializers.CharField(source="project.name", read_only=True, default=None)
    contract_type_display = serializers.CharField(source="get_contract_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)
    amendment_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Contract
        fields = (
            "id", "contract_number", "title", "vendor", "vendor_name",
            "project", "project_name",
            "contract_type", "contract_type_display",
            "status", "status_display", "is_active",
            "original_value", "revised_value", "currency",
            "is_price_locked",
            "effective_date", "expiry_date", "days_until_expiry",
            "payment_terms_summary", "retention_pct",
            "amendment_count",
            "created_at", "updated_at",
        )


class ContractDetailSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)
    project_name = serializers.CharField(source="project.name", read_only=True, default=None)
    contract_type_display = serializers.CharField(source="get_contract_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)
    total_amendments_value = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    amendments = ContractAmendmentSerializer(many=True, read_only=True)
    clauses = ContractClauseSerializer(many=True, read_only=True)

    class Meta:
        model = Contract
        fields = "__all__"
        read_only_fields = ("id", "contract_number", "organization", "created_by", "created_at", "updated_at")


class ContractWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contract
        fields = (
            "vendor", "project", "purchase_order",
            "title", "contract_type", "status",
            "original_value", "revised_value", "currency",
            "is_price_locked", "price_escalation_clause", "locked_rates",
            "effective_date", "expiry_date", "completion_date",
            "renewal_date", "notice_period_days",
            "payment_terms_summary", "advance_payment_pct", "retention_pct",
            "defects_liability_months",
            "sla_response_hours", "sla_resolution_hours", "sla_uptime_pct",
            "sla_penalty_per_breach", "sla_notes",
            "insurance_required", "insurance_minimum_cover",
            "performance_bond_pct", "liquidated_damages_rate", "liquidated_damages_cap_pct",
            "signed_by_org", "signed_by_vendor", "signed_date", "witness",
            "scope_of_work", "exclusions", "dispute_resolution", "governing_law",
            "notes",
        )


# ── GRN Photo ────────────────────────────────────────────────────────

from .models import GoodsReceiptPhoto


class GoodsReceiptPhotoSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source="uploaded_by.get_full_name", read_only=True, default="")
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = GoodsReceiptPhoto
        fields = (
            "id", "goods_receipt", "receipt_item", "image", "image_url",
            "caption", "photo_type", "uploaded_by", "uploaded_by_name", "created_at",
        )
        extra_kwargs = {
            "goods_receipt": {"read_only": True},
            "uploaded_by": {"read_only": True},
        }

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None
