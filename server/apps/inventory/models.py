from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Warehouse(models.Model):
    """Storage location for inventory stock."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_warehouses",
    )
    code = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.SET_NULL,
        related_name="inventory_warehouses",
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    storage_capacity_units = models.PositiveIntegerField(default=0, help_text="Max storage capacity in abstract units (pallets, m³, etc.).")
    warehouse_type = models.CharField(
        max_length=20,
        choices=[("central", "Central Warehouse"), ("site", "Site Store"), ("transit", "Transit Hub"), ("bonded", "Bonded Store")],
        default="site",
    )
    contact_person = models.CharField(max_length=255, blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    gps_coordinates = models.CharField(max_length=100, blank=True, help_text="Lat,Lng")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="inv_wh_org_created_idx"),
        ]

    def __str__(self):
        return f"{self.code} — {self.name}"

    def save(self, **kwargs):
        super().save(**kwargs)
        if self.is_default:
            Warehouse.objects.exclude(pk=self.pk).filter(is_default=True).update(
                is_default=False,
            )


class InventoryItem(models.Model):
    """Master record for stocked materials/items."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_inventory_items",
    )

    class Category(models.TextChoices):
        STRUCTURAL = "structural", "Structural"
        FINISHING = "finishing", "Finishing"
        MEP = "mep", "MEP"
        ELECTRICAL = "electrical", "Electrical"
        PLUMBING = "plumbing", "Plumbing"
        SAFETY = "safety", "Safety"
        CONSUMABLE = "consumable", "Consumable"
        SPARE = "spare", "Spare"
        EQUIPMENT = "equipment", "Equipment"
        OTHER = "other", "Other"

    sku = models.CharField(max_length=80, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.OTHER,
    )
    unit_of_measure = models.CharField(max_length=30, default="ea")
    reorder_level = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    target_stock_level = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    default_unit_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    preferred_vendor = models.ForeignKey(
        "procurement.Vendor",
        on_delete=models.SET_NULL,
        related_name="inventory_items",
        null=True,
        blank=True,
    )
    expense_account = models.ForeignKey(
        "finance.Account",
        on_delete=models.SET_NULL,
        related_name="inventory_items",
        null=True,
        blank=True,
    )
    cost_center = models.ForeignKey(
        "settings.CostCenter",
        on_delete=models.SET_NULL,
        related_name="inventory_items",
        null=True,
        blank=True,
    )
    # --- Material master extended fields ---
    subcategory = models.CharField(max_length=100, blank=True)
    material_grade = models.CharField(max_length=100, blank=True)
    lead_time_days = models.PositiveIntegerField(
        null=True, blank=True, help_text="Typical lead time in days from order to delivery.",
    )
    storage_requirements = models.TextField(
        blank=True, help_text="E.g. 'Dry store, avoid moisture', 'Keep below 25°C'.",
    )
    quality_specification = models.TextField(
        blank=True, help_text="Quality or technical specification reference.",
    )
    alternative_materials = models.TextField(
        blank=True, help_text="Comma-separated list of substitute material names or SKUs.",
    )
    hs_code = models.CharField(
        max_length=20, blank=True, verbose_name="HS Code",
        help_text="Harmonized System code for import/export classification.",
    )
    compliance_requirements = models.TextField(
        blank=True, help_text="Regulatory or compliance notes for this material.",
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["category", "is_active"]),
            models.Index(fields=["organization", "-created_at"], name="inv_item_org_created_idx"),
        ]

    def __str__(self):
        return f"{self.sku} — {self.name}"


class InventoryStock(models.Model):
    """Current stock snapshot for a given item per warehouse."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_inventory_stocks",
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="stocks",
    )
    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.CASCADE,
        related_name="stocks",
    )
    quantity_on_hand = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("0"),
    )
    quantity_reserved = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    average_unit_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    last_transaction_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["warehouse__name", "item__name"]
        unique_together = [("warehouse", "item")]
        indexes = [
            models.Index(fields=["warehouse", "item"]),
        ]

    def __str__(self):
        return f"{self.warehouse.code} — {self.item.sku}"

    @property
    def available_quantity(self):
        return (self.quantity_on_hand or Decimal("0")) - (
            self.quantity_reserved or Decimal("0")
        )


class InventoryTransaction(models.Model):
    """Atomic movement record that drives stock balances."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_inventory_transactions",
    )

    class TransactionType(models.TextChoices):
        RECEIPT = "receipt", "Receipt"
        ISSUE = "issue", "Issue"
        ADJUSTMENT_IN = "adjustment_in", "Adjustment In"
        ADJUSTMENT_OUT = "adjustment_out", "Adjustment Out"
        TRANSFER_IN = "transfer_in", "Transfer In"
        TRANSFER_OUT = "transfer_out", "Transfer Out"

    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.SET_NULL,
        related_name="inventory_transactions",
        null=True,
        blank=True,
    )
    purchase_order = models.ForeignKey(
        "procurement.PurchaseOrder",
        on_delete=models.SET_NULL,
        related_name="inventory_transactions",
        null=True,
        blank=True,
    )
    goods_receipt = models.ForeignKey(
        "procurement.GoodsReceipt",
        on_delete=models.SET_NULL,
        related_name="inventory_transactions",
        null=True,
        blank=True,
    )
    goods_receipt_item = models.ForeignKey(
        "procurement.GoodsReceiptItem",
        on_delete=models.SET_NULL,
        related_name="inventory_transactions",
        null=True,
        blank=True,
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices,
    )
    quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )
    unit_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    total_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    transaction_date = models.DateField(default=timezone.localdate)
    source_module = models.CharField(max_length=60, blank=True)
    source_reference = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="inventory_transactions",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-transaction_date", "-created_at", "-id"]
        indexes = [
            models.Index(fields=["transaction_type", "transaction_date"]),
            models.Index(fields=["item", "warehouse", "transaction_date"]),
            models.Index(fields=["project", "transaction_type", "transaction_date"]),
            models.Index(fields=["source_module", "source_reference"]),
            models.Index(fields=["organization", "-created_at"], name="inv_txn_org_created_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["goods_receipt_item", "transaction_type"],
                condition=models.Q(goods_receipt_item__isnull=False),
                name="uniq_inventory_grn_item_txn_type",
            ),
        ]

    def __str__(self):
        return (
            f"{self.get_transaction_type_display()} {self.quantity} {self.item.sku}"
            f" @ {self.warehouse.code}"
        )

    def save(self, **kwargs):
        if self.unit_cost is not None:
            self.total_cost = (self.unit_cost or Decimal("0.00")) * (
                self.quantity or Decimal("0")
            )
        super().save(**kwargs)


class ProcurementItemMapping(models.Model):
    """Mapping from procurement PO items to reusable inventory item records."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_procurement_item_mappings",
    )
    po_item = models.OneToOneField(
        "procurement.PurchaseOrderItem",
        on_delete=models.CASCADE,
        related_name="inventory_mapping",
    )
    inventory_item = models.ForeignKey(
        InventoryItem,
        on_delete=models.CASCADE,
        related_name="procurement_mappings",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="inv_pim_org_created_idx"),
        ]

    def __str__(self):
        return f"PO item {self.po_item_id} -> {self.inventory_item.sku}"


class BillOfMaterials(models.Model):
    """Bill of Materials for a construction project or building component."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        IN_REVIEW = "in_review", "In Review"
        PENDING_APPROVAL = "pending_approval", "Pending Approval"
        APPROVED = "approved", "Approved"
        # 5-phase lifecycle states
        ESTIMATE = "estimate", "Master Estimate"
        TENDER = "tender", "Issued for Tender"
        CONTRACT = "contract", "Contract BOQ (Agreed)"
        EXECUTION = "execution", "Execution (Live Tracking)"
        FINANCIAL_CONTROL = "financial_control", "Financial Control"
        ARCHIVED = "archived", "Archived"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_boms",
    )
    bom_number = models.CharField(max_length=20, unique=True, blank=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.SET_NULL,
        related_name="bills_of_materials",
        null=True,
        blank=True,
    )
    unit_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="e.g. Residential Unit, Villa, Floor",
    )
    quantity_of_units = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    total_estimated_cost = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    version = models.PositiveSmallIntegerField(default=1)
    parent_version = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="child_versions",
    )
    confidence_pct = models.PositiveSmallIntegerField(default=0)
    margin_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("10.00"))
    vat_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("7.50"))
    site_location = models.CharField(max_length=255, blank=True)
    fx_rate_usd_ngn = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("1550.00"))
    project_variables = models.JSONField(default=dict, blank=True)
    revision_reason = models.TextField(blank=True)
    is_baseline = models.BooleanField(default=False)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_boms",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Bill of Materials"
        verbose_name_plural = "Bills of Materials"
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="inv_bom_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.bom_number} — {self.name}"

    def save(self, **kwargs):
        if not self.bom_number:
            self.bom_number = self._generate_bom_number()
        super().save(**kwargs)

    @staticmethod
    def _generate_bom_number() -> str:
        last = (
            BillOfMaterials.objects.filter(bom_number__startswith="BOM-")
            .order_by("-bom_number")
            .values_list("bom_number", flat=True)
            .first()
        )
        if last:
            try:
                seq = int(last.split("-", 1)[1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f"BOM-{seq:05d}"

    def recalculate_total(self):
        from django.db.models import Sum

        total = self.items.aggregate(total=Sum("line_total"))["total"] or Decimal(
            "0.00"
        )
        BillOfMaterials.objects.filter(pk=self.pk).update(
            total_estimated_cost=total,
        )
        self.total_estimated_cost = total

    @property
    def subtotal(self):
        return self.total_estimated_cost

    @property
    def vat_amount(self):
        return self.subtotal * self.vat_pct / 100

    @property
    def margin_amount(self):
        return self.subtotal * self.margin_pct / 100

    @property
    def grand_total(self):
        return self.subtotal + self.vat_amount + self.margin_amount


class BOMItem(models.Model):
    """A single material line inside a Bill of Materials."""

    bom = models.ForeignKey(
        BillOfMaterials,
        on_delete=models.CASCADE,
        related_name="items",
    )
    inventory_item = models.ForeignKey(
        InventoryItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bom_usages",
    )
    material_name = models.CharField(max_length=255)
    category = models.CharField(max_length=100, blank=True)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    unit_of_measure = models.CharField(max_length=50)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2)
    line_total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    notes = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    supplier = models.CharField(max_length=255, blank=True)
    supplier_vendor = models.ForeignKey(
        "procurement.Vendor", on_delete=models.SET_NULL, null=True, blank=True, related_name="boq_items",
    )
    is_approved = models.BooleanField(default=False)
    price_volatile = models.BooleanField(default=False)
    original_unit_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    contracted_rate = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Rate agreed in the contract (from PO/tender). Differs from unit_cost (estimate).",
    )
    actual_rate = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Actual rate paid (from bills/invoices). May differ from contracted_rate due to variations.",
    )

    class PriceSource(models.TextChoices):
        WAREHOUSE = "warehouse", "Warehouse Price"
        MANUAL = "manual", "Manual Override"
        QUOTE = "quote", "Supplier Quote"

    price_source = models.CharField(max_length=10, choices=PriceSource.choices, default=PriceSource.MANUAL)
    waste_factor_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    item_markup_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    lead_time_days = models.PositiveSmallIntegerField(default=0)
    source_bom = models.ForeignKey(
        BillOfMaterials, on_delete=models.SET_NULL, null=True, blank=True, related_name="derived_boq_items",
    )
    section = models.CharField(max_length=100, blank=True)
    quantity_formula = models.CharField(max_length=255, blank=True)
    is_fx_linked = models.BooleanField(default=False)
    unit_cost_usd = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        ordering = ["sort_order", "pk"]

    def __str__(self):
        return f"{self.material_name} ({self.quantity} {self.unit_of_measure})"

    @property
    def effective_quantity(self):
        return self.quantity * (1 + self.waste_factor_pct / 100)

    @property
    def effective_line_total(self):
        base = self.effective_quantity * self.unit_cost
        return base * (1 + self.item_markup_pct / 100)

    def save(self, **kwargs):
        self.line_total = self.quantity * self.unit_cost
        super().save(**kwargs)
        self.bom.recalculate_total()

    def delete(self, **kwargs):
        bom = self.bom
        super().delete(**kwargs)
        bom.recalculate_total()


# ---------------------------------------------------------------------------
# Rate Library
# ---------------------------------------------------------------------------


class RateBook(models.Model):
    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="rate_books")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    fx_rate_usd_ngn = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("1550.00"))
    last_synced_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="created_rate_books")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_active", "-updated_at"]

    def __str__(self):
        return self.name


class RateItem(models.Model):
    class Category(models.TextChoices):
        EQUIPMENT = "equipment", "Equipment"
        LABOR = "labor", "Labor"
        MACHINERY = "machinery", "Machinery"
        CONSUMABLES = "consumables", "Consumables"
        LOGISTICS = "logistics", "Logistics"
        FEES = "fees", "Fees & Permits"
        PRELIMINARIES = "preliminaries", "Preliminaries"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        VERIFIED = "verified", "Verified"
        FLOATING = "floating", "Floating"
        EXPIRED = "expired", "Expired"

    rate_book = models.ForeignKey(RateBook, on_delete=models.CASCADE, related_name="items")
    item_code = models.CharField(max_length=30)
    description = models.CharField(max_length=500)
    unit = models.CharField(max_length=50)
    base_rate = models.DecimalField(max_digits=14, decimal_places=2)
    base_rate_usd = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    is_fx_linked = models.BooleanField(default=False)
    location = models.CharField(max_length=100, blank=True)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.FLOATING)
    purchase_price = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    shipping_cost = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    handling_fee = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    duty_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    supplier_vendor = models.ForeignKey("procurement.Vendor", on_delete=models.SET_NULL, null=True, blank=True, related_name="rate_items")
    is_composite = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    last_verified_at = models.DateTimeField(null=True, blank=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "item_code"]
        unique_together = [("rate_book", "item_code")]

    def __str__(self):
        return f"{self.item_code} — {self.description}"

    @property
    def is_stale(self):
        if not self.last_verified_at:
            return True
        return (timezone.now() - self.last_verified_at).days > 30

    @property
    def total_landed_cost(self):
        base = self.purchase_price + self.shipping_cost + self.handling_fee
        return base * (1 + self.duty_pct / 100)


class RateCompositeComponent(models.Model):
    composite_rate = models.ForeignKey(RateItem, on_delete=models.CASCADE, related_name="components")
    component_rate = models.ForeignKey(RateItem, on_delete=models.CASCADE, related_name="used_in_composites")
    quantity = models.DecimalField(max_digits=10, decimal_places=4, default=Decimal("1.0000"))

    class Meta:
        ordering = ["pk"]

    def __str__(self):
        return f"{self.quantity}x {self.component_rate.item_code}"

    @property
    def line_cost(self):
        return self.quantity * self.component_rate.base_rate


class RateHistory(models.Model):
    rate_item = models.ForeignKey(RateItem, on_delete=models.CASCADE, related_name="history")
    rate = models.DecimalField(max_digits=14, decimal_places=2)
    recorded_at = models.DateTimeField(auto_now_add=True)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-recorded_at"]

    def __str__(self):
        return f"{self.rate_item.item_code}: {self.rate} @ {self.recorded_at}"


# ---------------------------------------------------------------------------
# BoQ Category → Planning Template Mapping
# ---------------------------------------------------------------------------


class BoqCategoryMapping(models.Model):
    """
    Maps a BOQ item category to a planning template (phase + activities).
    Used by the BOQ-driven WBS auto-generation engine.
    """
    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.CASCADE,
        related_name="boq_category_mappings",
    )
    boq_category = models.CharField(
        max_length=100,
        help_text="BOQ item category to match (e.g. 'Concrete', 'Electrical', 'Excavation').",
    )
    template_phase = models.ForeignKey(
        "settings.TemplatePhase", on_delete=models.CASCADE,
        related_name="boq_category_mappings",
        help_text="Template phase that handles this BOQ category.",
    )
    default_production_rate = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Fallback production rate (units/day) if task template has none.",
    )
    split_threshold = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="If BOQ quantity exceeds this, split into multiple tasks by zone/location.",
    )
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "boq_category"]
        unique_together = [("organization", "boq_category")]

    def __str__(self):
        return f"{self.boq_category} → {self.template_phase}"


# ---------------------------------------------------------------------------
# BoQ → Schedule Mapping
# ---------------------------------------------------------------------------


class BoqTaskMapping(models.Model):
    class MaterialStatus(models.TextChoices):
        AWAITING = "awaiting", "Awaiting Order"
        IN_TRANSIT = "in_transit", "In Transit"
        IN_WAREHOUSE = "in_warehouse", "In Warehouse"

    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="boq_mappings")
    bom = models.ForeignKey(BillOfMaterials, on_delete=models.CASCADE, related_name="task_mappings")
    bom_item = models.ForeignKey(BOMItem, on_delete=models.CASCADE, related_name="task_mappings")
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="boq_mappings")
    phase = models.ForeignKey("projects.ProjectPhase", on_delete=models.SET_NULL, null=True, blank=True, related_name="boq_mappings")
    task = models.ForeignKey("projects.ProjectTask", on_delete=models.SET_NULL, null=True, blank=True, related_name="boq_mappings")
    cost_code_budget = models.ForeignKey(
        "projects.CostCodeBudget", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="boq_mappings", help_text="Links this BOQ allocation to a formal budget line.",
    )
    allocated_quantity = models.DecimalField(max_digits=12, decimal_places=2)
    consumed_quantity = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00"),
        help_text="Aggregated from DailyReportMaterialUsage. Updated by sync.",
    )
    allocated_cost = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    delivery_deadline = models.DateField(null=True, blank=True)
    material_status = models.CharField(max_length=15, choices=MaterialStatus.choices, default=MaterialStatus.AWAITING)
    has_lead_time_conflict = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["bom", "bom_item__sort_order"]

    @property
    def quantity_remaining(self):
        return self.allocated_quantity - self.consumed_quantity

    @property
    def consumption_pct(self):
        if self.allocated_quantity > 0:
            return round(float(self.consumed_quantity) / float(self.allocated_quantity) * 100, 1)
        return 0

    def sync_consumed_quantity(self):
        """Aggregate consumed quantity from DailyReportMaterialUsage records."""
        from projects.models import DailyReportMaterialUsage
        total = DailyReportMaterialUsage.objects.filter(
            bom_item=self.bom_item,
            report__project=self.project,
        ).aggregate(total=models.Sum("quantity_used"))["total"] or Decimal("0")
        if total != self.consumed_quantity:
            self.consumed_quantity = total
            self.save(update_fields=["consumed_quantity", "updated_at"])

    def __str__(self):
        return f"{self.bom_item.material_name} → {self.task or self.phase}"

    def save(self, **kwargs):
        self.allocated_cost = self.allocated_quantity * self.bom_item.unit_cost
        if self.delivery_deadline and self.bom_item.lead_time_days > 0:
            from datetime import timedelta
            order_date = self.delivery_deadline - timedelta(days=self.bom_item.lead_time_days)
            self.has_lead_time_conflict = order_date < timezone.now().date()
        super().save(**kwargs)


# ---------------------------------------------------------------------------
# Material Requisition (Site Requests)
# ---------------------------------------------------------------------------


class MaterialRequisition(models.Model):
    """Site material request routed through approval workflow."""

    class ReqStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING_SE = "pending_se", "Pending Site Engineer"
        PENDING_PM = "pending_pm", "Pending Project Manager"
        PENDING_PROC = "pending_proc", "Pending Procurement"
        PENDING_STORE = "pending_store", "Pending Store"
        PARTIALLY_FULFILLED = "partially_fulfilled", "Partially Fulfilled"
        FULFILLED = "fulfilled", "Fulfilled"
        NEEDS_REVISION = "needs_revision", "Needs Revision"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    class Urgency(models.TextChoices):
        LOW = "low", "Low"
        NORMAL = "normal", "Normal"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.CASCADE,
        related_name="material_requisitions",
    )
    requisition_id = models.CharField(max_length=100, unique=True, blank=True)
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE,
        related_name="material_requisitions",
    )
    phase = models.ForeignKey(
        "projects.ProjectPhase", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="material_requisitions",
    )
    status = models.CharField(max_length=25, choices=ReqStatus.choices, default=ReqStatus.DRAFT)
    urgency = models.CharField(max_length=10, choices=Urgency.choices, default=Urgency.NORMAL)

    site_location = models.CharField(max_length=255, blank=True)
    requested_delivery_date = models.DateField(null=True, blank=True)
    justification = models.TextField(blank=True)
    cost_code = models.CharField(max_length=100, blank=True)
    delivery_instructions = models.TextField(blank=True)

    # Workflow tracking
    current_step = models.CharField(max_length=30, default="site_engineer")
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_by_se = models.CharField(max_length=255, blank=True)
    approved_by_se_at = models.DateTimeField(null=True, blank=True)
    approved_by_pm = models.CharField(max_length=255, blank=True)
    approved_by_pm_at = models.DateTimeField(null=True, blank=True)
    approved_by_proc = models.CharField(max_length=255, blank=True)
    approved_by_proc_at = models.DateTimeField(null=True, blank=True)
    fulfilled_by_store = models.CharField(max_length=255, blank=True)
    fulfilled_at = models.DateTimeField(null=True, blank=True)
    rejected_by = models.CharField(max_length=255, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="created_material_requisitions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"], name="matreq_org_status_idx"),
            models.Index(fields=["organization", "project", "-created_at"], name="matreq_org_proj_idx"),
        ]

    def save(self, *args, **kwargs):
        if not self.requisition_id:
            last = (
                MaterialRequisition.objects.filter(requisition_id__startswith="MR-")
                .order_by("-requisition_id")
                .values_list("requisition_id", flat=True)
                .first()
            )
            seq = int(last.split("-")[1]) + 1 if last else 1
            self.requisition_id = f"MR-{seq:05d}"
        super().save(*args, **kwargs)

    @property
    def estimated_total(self):
        return sum(
            (line.estimated_cost or Decimal("0"))
            for line in self.lines.all()
        )

    @property
    def fulfilment_pct(self):
        lines = self.lines.all()
        if not lines:
            return 0
        total_req = sum(float(l.quantity) for l in lines)
        total_issued = sum(float(l.issued_quantity) for l in lines)
        return round(total_issued / total_req * 100) if total_req > 0 else 0

    def __str__(self):
        return f"{self.requisition_id} — {self.project.name}"


class MaterialRequisitionLine(models.Model):
    """Individual material line on a site requisition."""

    requisition = models.ForeignKey(
        MaterialRequisition, on_delete=models.CASCADE, related_name="lines",
    )
    material = models.ForeignKey(
        InventoryItem, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="requisition_lines",
    )
    material_name = models.CharField(max_length=255, help_text="Description if not linked to master.")
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    unit_of_measure = models.CharField(max_length=50, default="ea")
    required_by_date = models.DateField(null=True, blank=True)
    phase_area = models.CharField(max_length=100, blank=True, help_text="Zone or work area for this line.")
    line_justification = models.TextField(blank=True)

    # Pricing
    unit_cost = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    estimated_cost = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    # Stock info (populated on save/submission)
    available_stock = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    # Fulfilment
    issued_quantity = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    issued_from_warehouse = models.ForeignKey(
        Warehouse, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="material_requisition_issues",
    )
    issued_at = models.DateTimeField(null=True, blank=True)
    issued_by = models.CharField(max_length=255, blank=True)

    sort_order = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["sort_order"]

    def save(self, *args, **kwargs):
        self.estimated_cost = self.quantity * self.unit_cost
        # Auto-fill unit cost from material master if available
        if self.material_id and self.unit_cost == Decimal("0.00") and self.material.default_unit_cost:
            self.unit_cost = self.material.default_unit_cost
            self.estimated_cost = self.quantity * self.unit_cost
        # Auto-fill available stock
        if self.material_id:
            total_stock = InventoryStock.objects.filter(
                item=self.material,
            ).aggregate(total=models.Sum("quantity_on_hand"))["total"] or Decimal("0")
            self.available_stock = total_stock
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.material_name} × {self.quantity}"


class MaterialRequisitionComment(models.Model):
    """Discussion thread on a material requisition."""

    requisition = models.ForeignKey(
        MaterialRequisition, on_delete=models.CASCADE, related_name="comments",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name="+",
    )
    author_role = models.CharField(max_length=50, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.author} — {self.message[:50]}"


class MaterialRequisitionAuditLog(models.Model):
    """Audit trail for every change to a material requisition."""

    requisition = models.ForeignKey(
        MaterialRequisition, on_delete=models.CASCADE, related_name="audit_logs",
    )
    action = models.CharField(max_length=50)
    field_changed = models.CharField(max_length=100, blank=True)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name="+",
    )
    performed_at = models.DateTimeField(auto_now_add=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-performed_at"]

    def __str__(self):
        return f"{self.action} by {self.performed_by} at {self.performed_at}"


# ---------------------------------------------------------------------------
# Material Issue to Construction
# ---------------------------------------------------------------------------


class MaterialIssue(models.Model):
    """Records material issued from warehouse to a construction project/phase."""

    class IssueStatus(models.TextChoices):
        REQUESTED = "requested", "Requested"
        APPROVED = "approved", "Approved"
        ISSUED = "issued", "Issued"
        PARTIALLY_ISSUED = "partially_issued", "Partially Issued"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="material_issues")
    issue_number = models.CharField(max_length=100, unique=True, blank=True)
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="material_issues")
    phase = models.ForeignKey("projects.ProjectPhase", on_delete=models.SET_NULL, null=True, blank=True, related_name="material_issues")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name="material_issues")
    status = models.CharField(max_length=20, choices=IssueStatus.choices, default=IssueStatus.REQUESTED)

    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="requested_material_issues")
    requested_date = models.DateField(auto_now_add=True)
    approved_by = models.CharField(max_length=255, blank=True)
    approved_date = models.DateField(null=True, blank=True)
    issued_by = models.CharField(max_length=255, blank=True)
    issued_date = models.DateField(null=True, blank=True)

    purpose = models.TextField(blank=True, help_text="Work activity or task requiring these materials.")
    cost_code = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"], name="matissue_org_status_idx"),
        ]

    def save(self, *args, **kwargs):
        if not self.issue_number:
            last = MaterialIssue.objects.filter(issue_number__startswith="MI-").order_by("-issue_number").values_list("issue_number", flat=True).first()
            seq = int(last.split("-")[1]) + 1 if last else 1
            self.issue_number = f"MI-{seq:05d}"
        super().save(*args, **kwargs)

    @property
    def total_value(self):
        return sum((line.issued_quantity or Decimal("0")) * (line.unit_cost or Decimal("0")) for line in self.lines.all())

    def __str__(self):
        return f"{self.issue_number} — {self.project.name}"


class MaterialIssueLine(models.Model):
    """Individual material line in an issue request."""

    issue = models.ForeignKey(MaterialIssue, on_delete=models.CASCADE, related_name="lines")
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name="issue_lines")
    requested_quantity = models.DecimalField(max_digits=12, decimal_places=2)
    issued_quantity = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    unit_of_measure = models.CharField(max_length=50, default="ea")
    unit_cost = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    purpose = models.CharField(max_length=255, blank=True, help_text="Specific task or activity.")
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order"]

    def save(self, *args, **kwargs):
        if not self.unit_cost and self.item_id and self.item.default_unit_cost:
            self.unit_cost = self.item.default_unit_cost
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.item.name} × {self.requested_quantity}"


# ---------------------------------------------------------------------------
# Variance Investigation
# ---------------------------------------------------------------------------


def variance_photo_upload_to(instance, filename):
    return f"variance-investigations/{instance.investigation.id}/{filename}"


class VarianceInvestigation(models.Model):
    """Root cause analysis for material over-consumption variance."""

    class RootCause(models.TextChoices):
        THEFT = "theft", "Theft / Pilferage"
        POOR_WORKMANSHIP = "poor_workmanship", "Poor Workmanship"
        DESIGN_CHANGE = "design_change", "Design Change"
        SPILLAGE = "spillage", "Spillage / Breakage"
        MEASUREMENT_ERROR = "measurement_error", "Measurement Error"
        SOIL_CONDITIONS = "soil_conditions", "Unexpected Soil/Site Conditions"
        REWORK = "rework", "Rework / Remedial"
        WEATHER = "weather", "Weather Damage"
        OTHER = "other", "Other"

    class Severity(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        UNDER_REVIEW = "under_review", "Under Review"
        RESOLVED = "resolved", "Resolved"
        ESCALATED = "escalated", "Escalated"

    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="variance_investigations")
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="variance_investigations")
    material_name = models.CharField(max_length=255)
    work_package = models.CharField(max_length=255, blank=True)
    root_cause = models.CharField(max_length=30, choices=RootCause.choices, default=RootCause.OTHER)
    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.MEDIUM)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.OPEN)

    planned_quantity = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    actual_quantity = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    variance_quantity = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    variance_pct = models.DecimalField(max_digits=6, decimal_places=1, default=Decimal("0"))
    unit = models.CharField(max_length=50, default="ea")

    supervisor_notes = models.TextField(blank=True, help_text="Site engineer justification for over-consumption.")
    corrective_action = models.TextField(blank=True)
    financial_impact = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))

    investigated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.material_name} — {self.get_root_cause_display()}"


class VarianceInvestigationPhoto(models.Model):
    """Photo evidence for a variance investigation."""

    investigation = models.ForeignKey(VarianceInvestigation, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to=variance_photo_upload_to)
    caption = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.investigation.material_name} — {self.caption or 'Photo'}"


# ---------------------------------------------------------------------------
# Material Transfers (Inter-Warehouse / Inter-Site)
# ---------------------------------------------------------------------------


class MaterialTransfer(models.Model):
    """Transfer order for moving materials between warehouses/sites."""

    class TransferStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        REQUESTED = "requested", "Requested"
        APPROVED = "approved", "Approved"
        IN_TRANSIT = "in_transit", "In Transit"
        DELIVERED = "delivered", "Delivered"
        RECEIVED = "received", "Received & Confirmed"
        PARTIALLY_RECEIVED = "partially_received", "Partially Received"
        CANCELLED = "cancelled", "Cancelled"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        NORMAL = "normal", "Normal"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="material_transfers")
    transfer_number = models.CharField(max_length=100, unique=True, blank=True)
    source_warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name="outbound_transfers")
    destination_warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name="inbound_transfers")
    project = models.ForeignKey("projects.Project", on_delete=models.SET_NULL, null=True, blank=True, related_name="material_transfers")
    status = models.CharField(max_length=25, choices=TransferStatus.choices, default=TransferStatus.DRAFT)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.NORMAL)

    reason = models.TextField(blank=True, help_text="Why this transfer is needed.")
    scheduled_date = models.DateField(null=True, blank=True)
    dispatched_date = models.DateField(null=True, blank=True)
    delivered_date = models.DateField(null=True, blank=True)
    confirmed_date = models.DateField(null=True, blank=True)

    dispatched_by = models.CharField(max_length=255, blank=True)
    received_by = models.CharField(max_length=255, blank=True)
    vehicle_details = models.CharField(max_length=255, blank=True, help_text="Truck plate, driver name.")
    waybill_number = models.CharField(max_length=100, blank=True)

    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="requested_transfers")
    approved_by = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"], name="mattrans_org_status_idx"),
        ]

    def save(self, *args, **kwargs):
        if not self.transfer_number:
            last = MaterialTransfer.objects.filter(transfer_number__startswith="TO-").order_by("-transfer_number").values_list("transfer_number", flat=True).first()
            seq = int(last.split("-")[1]) + 1 if last else 1
            self.transfer_number = f"TO-{seq:05d}"
        super().save(*args, **kwargs)

    @property
    def total_value(self):
        return sum((line.quantity or Decimal("0")) * (line.unit_cost or Decimal("0")) for line in self.lines.all())

    def __str__(self):
        return f"{self.transfer_number}: {self.source_warehouse.name} → {self.destination_warehouse.name}"


class MaterialTransferLine(models.Model):
    """Individual material line in a transfer order."""

    transfer = models.ForeignKey(MaterialTransfer, on_delete=models.CASCADE, related_name="lines")
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name="transfer_lines")
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    received_quantity = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    unit_of_measure = models.CharField(max_length=50, default="ea")
    unit_cost = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    sort_order = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["sort_order"]

    def save(self, *args, **kwargs):
        if not self.unit_cost and self.item_id and self.item.default_unit_cost:
            self.unit_cost = self.item.default_unit_cost
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.item.name} × {self.quantity}"


# ---------------------------------------------------------------------------
# Returns Management (Reverse Logistics)
# ---------------------------------------------------------------------------


class MaterialReturn(models.Model):
    """Return order for sending materials back to warehouse or vendor."""

    class ReturnType(models.TextChoices):
        TO_WAREHOUSE = "to_warehouse", "Return to Warehouse"
        TO_VENDOR = "to_vendor", "Return to Vendor"

    class ReturnStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        REQUESTED = "requested", "Requested"
        APPROVED = "approved", "Approved"
        IN_TRANSIT = "in_transit", "In Transit"
        RECEIVED = "received", "Received & Restocked"
        CREDIT_PENDING = "credit_pending", "Credit Memo Pending"
        CREDIT_RECEIVED = "credit_received", "Credit Received"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    class ReturnReason(models.TextChoices):
        EXCESS = "excess", "Excess / Surplus"
        DEFECTIVE = "defective", "Defective / Damaged"
        WRONG_SPECIFICATION = "wrong_spec", "Wrong Specification"
        PROJECT_CLOSURE = "project_closure", "Project Closure"
        DESIGN_CHANGE = "design_change", "Design Change"
        EXPIRED = "expired", "Expired / Shelf Life"
        OTHER = "other", "Other"

    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="material_returns")
    return_number = models.CharField(max_length=100, unique=True, blank=True)
    return_type = models.CharField(max_length=15, choices=ReturnType.choices, default=ReturnType.TO_WAREHOUSE)
    project = models.ForeignKey("projects.Project", on_delete=models.SET_NULL, null=True, blank=True, related_name="material_returns")
    source_warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name="outbound_returns", help_text="Where the material currently is (site store).")
    destination_warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, blank=True, related_name="inbound_returns", help_text="Central warehouse receiving the return.")
    vendor = models.ForeignKey("procurement.Vendor", on_delete=models.SET_NULL, null=True, blank=True, related_name="material_returns")
    status = models.CharField(max_length=20, choices=ReturnStatus.choices, default=ReturnStatus.DRAFT)
    reason = models.CharField(max_length=20, choices=ReturnReason.choices, default=ReturnReason.EXCESS)
    reason_detail = models.TextField(blank=True)

    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="requested_returns")
    approved_by = models.CharField(max_length=255, blank=True)
    approved_date = models.DateField(null=True, blank=True)
    dispatched_date = models.DateField(null=True, blank=True)
    received_date = models.DateField(null=True, blank=True)

    # Credit tracking (for vendor returns)
    credit_memo_number = models.CharField(max_length=100, blank=True)
    credit_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    credit_received_date = models.DateField(null=True, blank=True)

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["organization", "status"], name="matreturn_org_status_idx")]

    def save(self, *args, **kwargs):
        if not self.return_number:
            last = MaterialReturn.objects.filter(return_number__startswith="RET-").order_by("-return_number").values_list("return_number", flat=True).first()
            seq = int(last.split("-")[1]) + 1 if last else 1
            self.return_number = f"RET-{seq:05d}"
        super().save(*args, **kwargs)

    @property
    def total_value(self):
        return sum((l.quantity or Decimal("0")) * (l.unit_cost or Decimal("0")) for l in self.lines.all())

    def __str__(self):
        return f"{self.return_number} — {self.get_reason_display()}"


class MaterialReturnLine(models.Model):
    """Individual material line in a return order."""

    return_order = models.ForeignKey(MaterialReturn, on_delete=models.CASCADE, related_name="lines")
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name="return_lines")
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    received_quantity = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    unit_of_measure = models.CharField(max_length=50, default="ea")
    unit_cost = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    condition = models.CharField(max_length=20, choices=[("good", "Good"), ("damaged", "Damaged"), ("expired", "Expired")], default="good")
    sort_order = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["sort_order"]

    def save(self, *args, **kwargs):
        if not self.unit_cost and self.item_id and self.item.default_unit_cost:
            self.unit_cost = self.item.default_unit_cost
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.item.name} × {self.quantity}"
