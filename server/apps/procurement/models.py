from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

# Alias builtin — the `property` name is used as a FK field below,
# which would shadow the decorator inside the class body.
cached_property_builtin = property


class VendorCategory(models.Model):
    """Org-configurable vendor category for classification and spend analysis."""

    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.CASCADE, related_name="vendor_categories",
    )
    name = models.CharField(max_length=100)
    code = models.SlugField(max_length=50)
    parent = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="subcategories",
        help_text="Parent category for hierarchical classification (e.g. Materials > Concrete).",
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "name"]
        unique_together = [("organization", "code")]
        verbose_name_plural = "Vendor Categories"

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name


class Vendor(models.Model):
    """Approved vendor profile with intelligence metrics."""

    class Category(models.TextChoices):
        MATERIALS = "materials", "Materials"
        CONTRACTOR = "contractor", "Contractor"
        CONSULTANT = "consultant", "Consultant"
        OTHER = "other", "Other"

    class PriceCompetitiveness(models.TextChoices):
        LOW = "low", "Low"
        AVERAGE = "average", "Average"
        HIGH = "high", "High"
        PREMIUM = "premium", "Premium"

    class ComplianceStatus(models.TextChoices):
        COMPLIANT = "compliant", "Compliant"
        NON_COMPLIANT = "non_compliant", "Non-Compliant"
        PENDING_REVIEW = "pending_review", "Pending Review"
        EXPIRED = "expired", "Expired"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="procurement_vendors",
    )

    # --- Contact info (existing) ---
    name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    tax_id = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    # --- Approved Vendor Profile ---
    category = models.CharField(
        max_length=20, choices=Category.choices, default=Category.OTHER,
        help_text="Legacy fixed category. Use vendor_category for org-configurable classification.",
    )
    vendor_category = models.ForeignKey(
        VendorCategory, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="vendors",
        help_text="Org-configurable category with sub-categories.",
    )
    bank_name = models.CharField(max_length=255, blank=True)
    bank_account_number = models.CharField(max_length=100, blank=True)
    bank_branch = models.CharField(max_length=255, blank=True)
    approved_projects = models.ManyToManyField(
        "projects.Project", blank=True, related_name="approved_vendors"
    )

    # --- Vendor Intelligence ---
    performance_rating = models.DecimalField(
        max_digits=3, decimal_places=2, default=0,
        validators=[MinValueValidator(Decimal("0.00")), MaxValueValidator(Decimal("5.00"))],
    )
    delivery_timeliness_score = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(Decimal("0.00")), MaxValueValidator(Decimal("100.00"))],
    )
    price_competitiveness = models.CharField(
        max_length=20,
        choices=PriceCompetitiveness.choices,
        default=PriceCompetitiveness.AVERAGE,
    )
    compliance_status = models.CharField(
        max_length=20,
        choices=ComplianceStatus.choices,
        default=ComplianceStatus.PENDING_REVIEW,
    )
    is_blacklisted = models.BooleanField(default=False)
    blacklist_reason = models.TextField(blank=True)

    # --- Location & Proximity ---
    city = models.CharField(max_length=100, blank=True)
    state_region = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True, default="Nigeria")
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)

    # --- Pricing History ---
    average_quote_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00"),
        help_text="Running average of quoted amounts across all RFQs.",
    )
    total_rfqs_participated = models.PositiveIntegerField(default=0)
    total_rfqs_won = models.PositiveIntegerField(default=0)
    win_rate_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0.00"),
        help_text="Percentage of RFQs won out of total participated.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="proc_vend_org_created_idx"),
        ]

    def __str__(self):
        return self.name


class PurchaseRequisition(models.Model):
    """A request for materials or services."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"
        RFQ_ISSUED = "rfq_issued", "RFQ Issued"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"
        ORDERED = "ordered", "Ordered"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    class SourceModule(models.TextChoices):
        MANUAL = "manual", "Manual Entry"
        PROJECT = "project", "Project (Task/Milestone)"
        CONSTRUCTION = "construction", "Construction (BOQ/Work Package)"
        FACILITY = "facility", "Facility Management (Maintenance)"
        INVENTORY = "inventory", "Inventory (Reorder Threshold)"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="purchase_requisitions",
    )
    pr_number = models.CharField(max_length=100, unique=True, blank=True)
    title = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    requester = models.CharField(max_length=255)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="purchase_requisitions",
    )
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="purchase_requisitions",
    )
    source_module = models.CharField(
        max_length=20, choices=SourceModule.choices, default=SourceModule.MANUAL,
        help_text="Which module originated this requisition.",
    )
    priority = models.CharField(
        max_length=20, choices=Priority.choices, default=Priority.MEDIUM
    )
    required_date = models.DateField()
    facility_incident = models.ForeignKey(
        "facility_management.FacilityIncident",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="purchase_requisitions",
        help_text="Links to facility incident that triggered this PR.",
    )
    estimated_total = models.DecimalField(
        max_digits=15, decimal_places=2, default=0
    )
    budget_line_item = models.ForeignKey(
        "finance.BudgetLineItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="purchase_requisitions",
    )
    budget_code = models.CharField(max_length=100, blank=True)
    cost_code = models.CharField(max_length=50, blank=True)
    justification = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    approved_by = models.CharField(max_length=255, blank=True)
    approved_date = models.DateField(null=True, blank=True)
    rejected_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"], name="proc_pr_org_status_idx"),
            models.Index(fields=["organization", "-created_at"], name="proc_pr_org_created_idx"),
        ]

    def __str__(self):
        return f"{self.pr_number} — {self.title}"

    def save(self, **kwargs):
        if not self.pr_number:
            self.pr_number = self._generate_pr_number()
        super().save(**kwargs)

    @staticmethod
    def _generate_pr_number() -> str:
        last = (
            PurchaseRequisition.objects.filter(pr_number__startswith="PR-")
            .order_by("-pr_number")
            .values_list("pr_number", flat=True)
            .first()
        )
        if last:
            try:
                seq = int(last.split("-", 1)[1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f"PR-{seq:05d}"

    def recalculate_totals(self):
        agg = self.items.aggregate(total=models.Sum("estimated_amount"))
        self.estimated_total = agg["total"] or Decimal("0.00")
        self.save(update_fields=["estimated_total", "updated_at"])


class PurchaseRequisitionItem(models.Model):
    """Line item on a purchase requisition."""

    requisition = models.ForeignKey(
        PurchaseRequisition, on_delete=models.CASCADE, related_name="items"
    )
    bom_item = models.ForeignKey(
        "inventory.BOMItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requisition_items",
        help_text="Links this PR line item to a specific BOQ item.",
    )
    inventory_item = models.ForeignKey(
        "inventory.InventoryItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requisition_items",
        help_text="Links to a specific inventory item for reorder-triggered PRs.",
    )
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_of_measure = models.CharField(max_length=50, default="ea")
    estimated_unit_price = models.DecimalField(max_digits=15, decimal_places=2)
    estimated_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=0
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order"]

    def save(self, **kwargs):
        self.estimated_amount = self.quantity * self.estimated_unit_price
        super().save(**kwargs)

    def __str__(self):
        return f"{self.requisition.pr_number} — {self.description}"


class PurchaseOrder(models.Model):
    """A purchase order issued to a vendor."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        APPROVED = "approved", "Approved"
        ISSUED = "issued", "Issued"
        PARTIALLY_RECEIVED = "partially_received", "Partially Received"
        RECEIVED = "received", "Received"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="purchase_orders",
    )
    po_number = models.CharField(max_length=100, unique=True, blank=True)
    requisition = models.ForeignKey(
        PurchaseRequisition,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="purchase_orders",
    )
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.CASCADE,
        related_name="purchase_orders",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="purchase_orders",
    )
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="purchase_orders",
    )
    status = models.CharField(
        max_length=25, choices=Status.choices, default=Status.DRAFT
    )
    issue_date = models.DateField()
    expected_delivery_date = models.DateField(null=True, blank=True)
    delivery_address = models.TextField(blank=True)
    budget_line_item = models.ForeignKey(
        "finance.BudgetLineItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="purchase_orders",
    )
    budget_code = models.CharField(max_length=100, blank=True)
    cost_code = models.CharField(max_length=50, blank=True)
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=0
    )
    payment_terms = models.CharField(max_length=255, blank=True, help_text="Free-text summary, e.g. 'Net 30'")

    # Structured payment terms
    class PaymentMethod(models.TextChoices):
        BANK_TRANSFER = "bank_transfer", "Bank Transfer"
        CHEQUE = "cheque", "Cheque"
        CASH = "cash", "Cash"
        LETTER_OF_CREDIT = "letter_of_credit", "Letter of Credit"
        ESCROW = "escrow", "Escrow"
        OTHER = "other", "Other"

    payment_method = models.CharField(
        max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.BANK_TRANSFER,
    )
    payment_due_days = models.PositiveIntegerField(
        default=30, help_text="Number of days after invoice date for payment.",
    )
    advance_payment_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0.00"),
        help_text="Advance payment as % of total (e.g. 20% mobilization).",
    )
    advance_payment_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00"),
        help_text="Calculated or manually set advance amount.",
    )
    retention_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0.00"),
        help_text="Retention % held back per payment (e.g. 5%).",
    )
    early_payment_discount_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0.00"),
        help_text="Discount % for early payment (e.g. 2/10 Net 30 → 2%).",
    )
    early_payment_discount_days = models.PositiveIntegerField(
        default=0, help_text="Days within which early payment discount applies.",
    )

    notes = models.TextField(blank=True)
    approved_by = models.CharField(max_length=255, blank=True)
    approved_date = models.DateField(null=True, blank=True)
    match_status = models.CharField(
        max_length=20, blank=True, default="",
        help_text="3-way match result: full_match, partial_match, variance, mismatch, no_grn, pending",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"], name="proc_po_org_status_idx"),
            models.Index(fields=["organization", "-created_at"], name="proc_po_org_created_idx"),
        ]

    def __str__(self):
        return f"{self.po_number} — {self.vendor.name}"

    def save(self, **kwargs):
        if not self.po_number:
            self.po_number = self._generate_po_number()
        super().save(**kwargs)

    @staticmethod
    def _generate_po_number() -> str:
        last = (
            PurchaseOrder.objects.filter(po_number__startswith="PO-")
            .order_by("-po_number")
            .values_list("po_number", flat=True)
            .first()
        )
        if last:
            try:
                seq = int(last.split("-", 1)[1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f"PO-{seq:05d}"

    @cached_property_builtin
    def received_total(self) -> Decimal:
        from django.db.models import Sum
        total = GoodsReceiptItem.objects.filter(
            goods_receipt__purchase_order=self
        ).aggregate(total=Sum("quantity_accepted"))["total"]
        return total or Decimal("0")

    @cached_property_builtin
    def is_fully_received(self) -> bool:
        for item in self.items.all():
            if item.quantity_remaining > 0:
                return False
        return self.items.exists()

    def recalculate_totals(self):
        agg = self.items.aggregate(total=models.Sum("amount"))
        self.subtotal = agg["total"] or Decimal("0.00")
        self.total_amount = self.subtotal + self.tax_amount
        self.save(update_fields=["subtotal", "total_amount", "updated_at"])

    def update_status_from_receipts(self):
        if not self.items.exists():
            return
        if self.is_fully_received:
            self.status = self.Status.RECEIVED
            self.save(update_fields=["status", "updated_at"])
        elif self.received_total > 0:
            self.status = self.Status.PARTIALLY_RECEIVED
            self.save(update_fields=["status", "updated_at"])


class PurchaseOrderItem(models.Model):
    """Line item on a purchase order."""

    purchase_order = models.ForeignKey(
        PurchaseOrder, on_delete=models.CASCADE, related_name="items"
    )
    bom_item = models.ForeignKey(
        "inventory.BOMItem", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="purchase_order_items",
        help_text="Links this PO line item back to a specific BOQ item for traceability.",
    )
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_of_measure = models.CharField(max_length=50, default="ea")
    unit_price = models.DecimalField(max_digits=15, decimal_places=2)
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order"]

    def save(self, **kwargs):
        self.amount = self.quantity * self.unit_price
        super().save(**kwargs)

    def __str__(self):
        return f"{self.purchase_order.po_number} — {self.description}"

    @cached_property_builtin
    def quantity_received(self) -> Decimal:
        total = self.receipt_items.aggregate(
            total=models.Sum("quantity_accepted")
        )["total"]
        return total or Decimal("0")

    @cached_property_builtin
    def quantity_remaining(self) -> Decimal:
        return self.quantity - self.quantity_received


class GoodsReceipt(models.Model):
    """A goods receipt note (GRN) for a purchase order delivery."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        INSPECTED = "inspected", "Inspected"
        ACCEPTED = "accepted", "Accepted"
        PARTIALLY_ACCEPTED = "partially_accepted", "Partially Accepted"
        REJECTED = "rejected", "Rejected"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="goods_receipts",
    )
    grn_number = models.CharField(max_length=100, unique=True, blank=True)
    purchase_order = models.ForeignKey(
        PurchaseOrder, on_delete=models.CASCADE, related_name="goods_receipts"
    )
    status = models.CharField(
        max_length=25, choices=Status.choices, default=Status.PENDING
    )
    received_date = models.DateField()
    received_by = models.CharField(max_length=255)
    delivery_note_number = models.CharField(max_length=100, blank=True)
    inspection_notes = models.TextField(blank=True)
    facility_incident = models.ForeignKey(
        "facility_management.FacilityIncident",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="goods_receipts",
        help_text="Links delivery to a facility maintenance incident.",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-received_date"]
        indexes = [
            models.Index(fields=["organization", "status"], name="proc_gr_org_status_idx"),
            models.Index(fields=["organization", "-created_at"], name="proc_gr_org_created_idx"),
        ]

    def __str__(self):
        return f"{self.grn_number} — {self.purchase_order.po_number}"

    def save(self, **kwargs):
        if not self.grn_number:
            self.grn_number = self._generate_grn_number()
        super().save(**kwargs)

    @staticmethod
    def _generate_grn_number() -> str:
        last = (
            GoodsReceipt.objects.filter(grn_number__startswith="GRN-")
            .order_by("-grn_number")
            .values_list("grn_number", flat=True)
            .first()
        )
        if last:
            try:
                seq = int(last.split("-", 1)[1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f"GRN-{seq:05d}"


class GoodsReceiptItem(models.Model):
    """Individual item received in a goods receipt."""

    goods_receipt = models.ForeignKey(
        GoodsReceipt, on_delete=models.CASCADE, related_name="items"
    )
    po_item = models.ForeignKey(
        PurchaseOrderItem, on_delete=models.CASCADE, related_name="receipt_items"
    )
    quantity_received = models.DecimalField(max_digits=10, decimal_places=2)
    quantity_accepted = models.DecimalField(max_digits=10, decimal_places=2)
    quantity_rejected = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    rejection_reason = models.TextField(blank=True)

    # Quality inspection
    class QualityStatus(models.TextChoices):
        PENDING = "pending", "Pending Inspection"
        PASSED = "passed", "Passed"
        FAILED = "failed", "Failed"
        CONDITIONAL = "conditional", "Conditional Accept"

    quality_status = models.CharField(
        max_length=20, choices=QualityStatus.choices, default=QualityStatus.PENDING,
    )
    inspected_by = models.CharField(max_length=255, blank=True)
    inspected_date = models.DateField(null=True, blank=True)
    quality_notes = models.TextField(blank=True)

    # Batch tracking
    batch_number = models.CharField(max_length=100, blank=True, help_text="Manufacturer batch/lot number.")
    expiry_date = models.DateField(null=True, blank=True, help_text="Expiry date for perishable materials.")
    storage_location = models.CharField(max_length=255, blank=True, help_text="Warehouse bay or storage location.")
    unit_price = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, help_text="Snapshot of unit price at time of receipt.")

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.goods_receipt.grn_number} — {self.po_item.description}"


def grn_photo_upload_to(instance, filename):
    return f"grn-photos/{instance.goods_receipt.grn_number}/{filename}"


class GoodsReceiptPhoto(models.Model):
    """Photo evidence for goods receipt — delivery condition, damage, material grade tags."""

    goods_receipt = models.ForeignKey(
        GoodsReceipt, on_delete=models.CASCADE, related_name="photos",
    )
    receipt_item = models.ForeignKey(
        GoodsReceiptItem, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="photos",
        help_text="Link photo to a specific line item (optional).",
    )
    image = models.ImageField(upload_to=grn_photo_upload_to)
    caption = models.CharField(max_length=255, blank=True)
    photo_type = models.CharField(
        max_length=20,
        choices=[
            ("delivery", "Proof of Delivery"),
            ("damage", "Damage Evidence"),
            ("grade", "Material Grade Tag"),
            ("label", "Label / Certificate"),
            ("other", "Other"),
        ],
        default="delivery",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.goods_receipt.grn_number} — {self.caption or self.get_photo_type_display()}"


class RequestForQuotation(models.Model):
    """RFQ record used for vendor bidding and tender comparison."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ISSUED = "issued", "Issued"
        EVALUATION = "evaluation", "Under Evaluation"
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"
        CANCELLED = "cancelled", "Cancelled"
        CLOSED = "closed", "Closed"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="rfqs",
    )
    rfq_number = models.CharField(max_length=100, unique=True, blank=True)
    title = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    requisition = models.ForeignKey(
        PurchaseRequisition,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rfqs",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rfqs",
    )
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rfqs",
    )
    issue_date = models.DateField()
    submission_deadline = models.DateField(null=True, blank=True)
    estimated_value = models.DecimalField(
        max_digits=15, decimal_places=2, default=0
    )
    budget_line_item = models.ForeignKey(
        "finance.BudgetLineItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rfqs",
    )
    budget_code = models.CharField(max_length=100, blank=True)
    cost_code = models.CharField(max_length=50, blank=True)
    selected_vendor = models.ForeignKey(
        Vendor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="awarded_rfqs",
    )
    selection_notes = models.TextField(blank=True)
    selection_date = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_rfqs",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"], name="proc_rfq_org_status_idx"),
            models.Index(fields=["organization", "-created_at"], name="proc_rfq_org_created_idx"),
        ]

    def __str__(self):
        return f"{self.rfq_number} — {self.title}"

    def save(self, **kwargs):
        if not self.rfq_number:
            self.rfq_number = self._generate_rfq_number()
        super().save(**kwargs)

    @staticmethod
    def _generate_rfq_number() -> str:
        last = (
            RequestForQuotation.objects.filter(rfq_number__startswith="RFQ-")
            .order_by("-rfq_number")
            .values_list("rfq_number", flat=True)
            .first()
        )
        if last:
            try:
                seq = int(last.split("-", 1)[1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f"RFQ-{seq:05d}"

    def recalculate_estimated_value(self):
        agg = self.quotes.aggregate(total=models.Min("quoted_amount"))
        self.estimated_value = agg["total"] or Decimal("0.00")
        self.save(update_fields=["estimated_value", "updated_at"])


class RequestForQuotationQuote(models.Model):
    """Vendor quotation submitted against an RFQ."""

    class QuoteStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        SHORTLISTED = "shortlisted", "Shortlisted"
        REJECTED = "rejected", "Rejected"
        WINNER = "winner", "Winner"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="rfq_quotes",
    )
    rfq = models.ForeignKey(
        RequestForQuotation,
        on_delete=models.CASCADE,
        related_name="quotes",
    )
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.CASCADE,
        related_name="rfq_quotes",
    )
    quote_number = models.CharField(max_length=100, blank=True)
    quote_date = models.DateField()
    validity_date = models.DateField(null=True, blank=True)
    quoted_amount = models.DecimalField(max_digits=15, decimal_places=2)
    delivery_days = models.PositiveIntegerField(null=True, blank=True)
    warranty_terms = models.CharField(max_length=255, blank=True)
    payment_terms = models.CharField(max_length=255, blank=True)
    compliance_score = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    technical_score = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    commercial_score = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    total_score = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20, choices=QuoteStatus.choices, default=QuoteStatus.PENDING
    )
    notes = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-total_score", "quoted_amount"]
        unique_together = [("rfq", "vendor")]
        indexes = [
            models.Index(fields=["organization", "status"], name="proc_rfqq_org_status_idx"),
            models.Index(fields=["organization", "-submitted_at"], name="proc_rfqq_org_sub_idx"),
        ]

    def __str__(self):
        return f"{self.rfq.rfq_number} — {self.vendor.name}"

    def save(self, **kwargs):
        score_sum = (
            self.compliance_score + self.technical_score + self.commercial_score
        )
        self.total_score = score_sum / Decimal("3")
        super().save(**kwargs)


class RFQLineItem(models.Model):
    """Specific item/scope line within an RFQ for vendor pricing."""

    rfq = models.ForeignKey(
        RequestForQuotation, on_delete=models.CASCADE, related_name="line_items",
    )
    bom_item = models.ForeignKey(
        "inventory.BOMItem", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="rfq_line_items",
        help_text="Links to specific BOQ item for traceability.",
    )
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    unit_of_measure = models.CharField(max_length=50, default="ea")
    estimated_unit_price = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        help_text="Budget estimate rate for comparison.",
    )
    specification = models.TextField(blank=True, help_text="Technical specification or requirement.")
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.rfq.rfq_number} — {self.description}"


class RFQQuoteLineItem(models.Model):
    """Vendor's pricing response for a specific RFQ line item."""

    quote = models.ForeignKey(
        RequestForQuotationQuote, on_delete=models.CASCADE, related_name="line_items",
    )
    rfq_line_item = models.ForeignKey(
        RFQLineItem, on_delete=models.CASCADE, related_name="quote_responses",
    )
    quoted_unit_price = models.DecimalField(max_digits=15, decimal_places=2)
    quoted_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00"),
        help_text="Auto-calculated: rfq_line_item.quantity × quoted_unit_price",
    )
    delivery_days = models.PositiveIntegerField(default=0, help_text="Delivery lead time for this item.")
    notes = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order"]
        unique_together = [("quote", "rfq_line_item")]

    def save(self, **kwargs):
        self.quoted_amount = self.rfq_line_item.quantity * self.quoted_unit_price
        super().save(**kwargs)

    def __str__(self):
        return f"{self.quote.vendor.name} — {self.rfq_line_item.description}"


# ── Contracts & Agreements ───────────────────────────────────────────


class Contract(models.Model):
    """Formal agreement between the organization and a vendor/contractor."""

    class ContractType(models.TextChoices):
        CONSTRUCTION = "construction", "Construction Contract"
        SUPPLY = "supply", "Supply Agreement"
        SERVICE = "service", "Service Agreement"
        FRAMEWORK = "framework", "Framework Agreement"
        CONSULTANCY = "consultancy", "Consultancy Agreement"
        LEASE = "lease", "Equipment Lease"
        SUBCONTRACT = "subcontract", "Subcontract"
        JV = "jv", "Joint Venture Agreement"
        OTHER = "other", "Other"

    class ContractStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        NEGOTIATION = "negotiation", "Under Negotiation"
        PENDING_APPROVAL = "pending_approval", "Pending Approval"
        EXECUTED = "executed", "Executed / Active"
        SUSPENDED = "suspended", "Suspended"
        COMPLETED = "completed", "Completed"
        TERMINATED = "terminated", "Terminated"
        EXPIRED = "expired", "Expired"

    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.CASCADE, related_name="contracts",
    )
    vendor = models.ForeignKey(
        Vendor, on_delete=models.CASCADE, related_name="contracts",
    )
    project = models.ForeignKey(
        "projects.Project", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="contracts",
    )
    purchase_order = models.ForeignKey(
        PurchaseOrder, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="contracts",
        help_text="PO that originated this contract.",
    )

    contract_number = models.CharField(max_length=100, blank=True, unique=True, help_text="Auto-generated as CTR-##### when blank.")
    title = models.CharField(max_length=255)
    contract_type = models.CharField(max_length=20, choices=ContractType.choices, default=ContractType.CONSTRUCTION)
    status = models.CharField(max_length=20, choices=ContractStatus.choices, default=ContractStatus.DRAFT)

    # Value & Pricing
    original_value = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    revised_value = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"), help_text="Original + approved amendments.")
    currency = models.CharField(max_length=3, default="NGN")

    # Pricing Locks (Framework Agreements)
    is_price_locked = models.BooleanField(default=False, help_text="Prices locked for the contract duration.")
    price_escalation_clause = models.TextField(blank=True, help_text="e.g. 'CPI-linked annual escalation of 5% max'.")
    locked_rates = models.JSONField(
        default=list, blank=True,
        help_text='[{"item":"Cement OPC 42.5","unit":"bag","rate":6500,"valid_until":"2027-03-31"}]',
    )

    # Dates
    effective_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    completion_date = models.DateField(null=True, blank=True)
    renewal_date = models.DateField(null=True, blank=True, help_text="Auto-renewal date for framework agreements.")
    notice_period_days = models.PositiveIntegerField(default=30, help_text="Days notice required for termination.")

    # Payment Terms
    payment_terms_summary = models.CharField(max_length=255, blank=True, help_text="e.g. 'Net 30, 5% retention'.")
    advance_payment_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    retention_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    defects_liability_months = models.PositiveIntegerField(default=12)

    # SLA Terms
    sla_response_hours = models.PositiveIntegerField(null=True, blank=True, help_text="Max hours for vendor to respond to issues.")
    sla_resolution_hours = models.PositiveIntegerField(null=True, blank=True, help_text="Max hours for vendor to resolve issues.")
    sla_uptime_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="e.g. 99.5% uptime guarantee.")
    sla_penalty_per_breach = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"), help_text="Penalty amount per SLA breach.")
    sla_notes = models.TextField(blank=True)

    # Insurance & Compliance
    insurance_required = models.BooleanField(default=True)
    insurance_minimum_cover = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    performance_bond_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    liquidated_damages_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0.00"),
        help_text="% of contract value per day/week of delay.",
    )
    liquidated_damages_cap_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("10.00"),
        help_text="Maximum LD as % of contract value.",
    )

    # Execution
    signed_by_org = models.CharField(max_length=255, blank=True)
    signed_by_vendor = models.CharField(max_length=255, blank=True)
    signed_date = models.DateField(null=True, blank=True)
    witness = models.CharField(max_length=255, blank=True)

    # Scope
    scope_of_work = models.TextField(blank=True)
    exclusions = models.TextField(blank=True)
    dispute_resolution = models.TextField(blank=True, help_text="e.g. Arbitration under Lagos Arbitration Law.")
    governing_law = models.CharField(max_length=255, blank=True, default="Laws of the Federal Republic of Nigeria")

    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"], name="proc_ctr_org_status_idx"),
            models.Index(fields=["organization", "contract_type"], name="proc_ctr_org_type_idx"),
        ]

    @property
    def is_active(self):
        from datetime import date as d
        if self.status != "executed":
            return False
        if self.expiry_date and self.expiry_date < d.today():
            return False
        return True

    @property
    def days_until_expiry(self):
        from datetime import date as d
        if not self.expiry_date:
            return None
        return (self.expiry_date - d.today()).days

    @property
    def total_amendments_value(self):
        return sum(a.value_change for a in self.amendments.all())

    def save(self, *args, **kwargs):
        if not self.contract_number:
            last = (
                Contract.objects.filter(contract_number__startswith="CTR-")
                .order_by("-contract_number")
                .values_list("contract_number", flat=True)
                .first()
            )
            seq = 1
            if last:
                try:
                    seq = int(last.split("-")[1]) + 1
                except (IndexError, ValueError):
                    pass
            self.contract_number = f"CTR-{seq:05d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.contract_number} — {self.title}"


class ContractAmendment(models.Model):
    """Formal amendment/variation to an existing contract."""

    class AmendmentType(models.TextChoices):
        SCOPE_CHANGE = "scope_change", "Scope Change"
        PRICE_ADJUSTMENT = "price_adjustment", "Price Adjustment"
        TIME_EXTENSION = "time_extension", "Time Extension"
        TERMS_CHANGE = "terms_change", "Terms & Conditions Change"
        SUPPLEMENTAL = "supplemental", "Supplemental Agreement"

    class AmendmentStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        PROPOSED = "proposed", "Proposed"
        UNDER_REVIEW = "under_review", "Under Review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name="amendments")
    amendment_number = models.CharField(max_length=50, help_text="e.g. AMD-01, AMD-02")
    amendment_type = models.CharField(max_length=20, choices=AmendmentType.choices)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=AmendmentStatus.choices, default=AmendmentStatus.DRAFT)

    # Impact
    value_change = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"), help_text="Positive = increase, negative = decrease.")
    time_extension_days = models.IntegerField(default=0)
    effective_date = models.DateField(null=True, blank=True)

    # Approval
    approved_by = models.CharField(max_length=255, blank=True)
    approved_date = models.DateField(null=True, blank=True)
    reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["amendment_number"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Auto-update contract revised_value when amendment is approved
        if self.status == "approved":
            contract = self.contract
            total = contract.original_value + sum(
                a.value_change for a in contract.amendments.filter(status="approved")
            )
            if contract.revised_value != total:
                contract.revised_value = total
                contract.save(update_fields=["revised_value", "updated_at"])

    def __str__(self):
        return f"{self.contract.contract_number} — {self.amendment_number}"


class ContractClause(models.Model):
    """Specific contractual clause or term within a contract."""

    class ClauseCategory(models.TextChoices):
        PAYMENT = "payment", "Payment Terms"
        PERFORMANCE = "performance", "Performance Requirements"
        WARRANTY = "warranty", "Warranty & Defects"
        INSURANCE = "insurance", "Insurance & Indemnity"
        TERMINATION = "termination", "Termination"
        DISPUTE = "dispute", "Dispute Resolution"
        CONFIDENTIALITY = "confidentiality", "Confidentiality"
        FORCE_MAJEURE = "force_majeure", "Force Majeure"
        VARIATION = "variation", "Variations & Changes"
        COMPLIANCE = "compliance", "Regulatory Compliance"
        HEALTH_SAFETY = "health_safety", "Health & Safety"
        INTELLECTUAL_PROPERTY = "ip", "Intellectual Property"
        OTHER = "other", "Other"

    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name="clauses")
    clause_number = models.CharField(max_length=50, help_text="e.g. 12.1, 15.3")
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=20, choices=ClauseCategory.choices, default=ClauseCategory.OTHER)
    body = models.TextField(help_text="Full clause text.")
    is_critical = models.BooleanField(default=False, help_text="Flags clauses requiring special attention.")
    sort_order = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "clause_number"]

    def __str__(self):
        return f"{self.clause_number} — {self.title}"


class ThreeWayMatchResult(models.Model):
    """Persistent record of a 3-way match (PO vs GRN vs Invoice) for audit trail."""

    class MatchStatus(models.TextChoices):
        FULL_MATCH = "full_match", "Full Match"
        PARTIAL_MATCH = "partial_match", "Partial Match"
        VARIANCE = "variance", "Variance Detected"
        MISMATCH = "mismatch", "Mismatch"
        NO_GRN = "no_grn", "No Goods Receipt"
        PENDING = "pending", "Pending"

    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.CASCADE, related_name="three_way_matches",
    )
    purchase_order = models.ForeignKey(
        PurchaseOrder, on_delete=models.CASCADE, related_name="match_results",
    )
    bill = models.ForeignKey(
        "finance.Bill", on_delete=models.CASCADE, related_name="match_results",
    )
    match_status = models.CharField(max_length=20, choices=MatchStatus.choices, default=MatchStatus.PENDING)
    match_date = models.DateTimeField(auto_now_add=True)

    # Amounts compared
    po_total = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    grn_total = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    invoice_total = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))

    # Variance
    po_invoice_variance_pct = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    grn_invoice_variance_pct = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    tolerance_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("5.00"), help_text="Tolerance % used for this match.")

    # Issues
    issues = models.JSONField(default=list, blank=True, help_text='["PO vs Invoice variance: 7.2%"]')

    # Line-item detail
    line_item_matches = models.JSONField(
        default=list, blank=True,
        help_text='[{"po_item_id","description","po_qty","po_amount","grn_qty","bill_qty","bill_amount","status"}]',
    )

    reviewed_by = models.CharField(max_length=255, blank=True)
    reviewed_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-match_date"]
        indexes = [
            models.Index(fields=["organization", "match_status"], name="proc_3wm_org_status_idx"),
        ]

    def __str__(self):
        return f"{self.purchase_order.po_number} ↔ {self.bill.bill_number} — {self.get_match_status_display()}"


class ProjectProcurementWorkspace(models.Model):
    """Project-level procurement workspace artifacts initialized at project creation."""

    class WorkspaceType(models.TextChoices):
        PROJECT_PROCUREMENT_DASHBOARD = (
            "project_procurement_dashboard",
            "Project Procurement Dashboard",
        )
        VENDOR_ALLOCATION_WORKSPACE = (
            "vendor_allocation_workspace",
            "Vendor Allocation Workspace",
        )

    class MenuGroup(models.TextChoices):
        DASHBOARD = "dashboard", "Dashboard"
        VENDOR_MANAGEMENT = "vendor_management", "Vendor Management"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="project_procurement_workspaces",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="procurement_workspaces",
    )
    workspace_type = models.CharField(
        max_length=48,
        choices=WorkspaceType.choices,
    )
    name = models.CharField(max_length=120)
    menu_path = models.CharField(max_length=255)
    menu_group = models.CharField(
        max_length=32,
        choices=MenuGroup.choices,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["project", "workspace_type"]
        unique_together = [("project", "workspace_type")]
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="proc_pws_org_created_idx"),
            models.Index(fields=["project", "menu_group"], name="proc_pws_proj_group_idx"),
        ]

    def __str__(self):
        return f"{self.project.name} — {self.get_workspace_type_display()}"


class ProcurementDemandInsight(models.Model):
    """CRM-driven procurement demand insight for furnishing/add-on package planning."""

    class SourceModule(models.TextChoices):
        CRM = "crm", "CRM"
        PROCUREMENT = "procurement", "Procurement"
        ANALYTICS = "analytics", "Analytics"

    class InsightType(models.TextChoices):
        BULK_BUYER_DEMAND = "bulk_buyer_demand", "Bulk Buyer Demand"
        FURNISHING_PACKAGE = "furnishing_package", "Furnishing Package Trigger"
        ADD_ON_PACKAGE = "add_on_package", "Add-On Package Trigger"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="procurement_demand_insights",
    )
    source_module = models.CharField(
        max_length=20,
        choices=SourceModule.choices,
        default=SourceModule.CRM,
    )
    insight_type = models.CharField(
        max_length=32,
        choices=InsightType.choices,
        default=InsightType.BULK_BUYER_DEMAND,
    )
    area_name = models.CharField(max_length=200)
    title = models.CharField(max_length=255)
    summary = models.TextField(blank=True)
    demand_share_percent = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    lead_count = models.PositiveIntegerField(default=0)
    qualified_lead_count = models.PositiveIntegerField(default=0)
    won_lead_count = models.PositiveIntegerField(default=0)
    bulk_buyer_lead_count = models.PositiveIntegerField(default=0)
    window_days = models.PositiveIntegerField(default=90)
    threshold_percent = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("25.00"))
    min_bulk_leads = models.PositiveIntegerField(default=3)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    first_triggered_at = models.DateTimeField(null=True, blank=True)
    last_triggered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-demand_share_percent", "-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "insight_type", "area_name"],
                name="unique_org_proc_demand_insight",
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization", "source_module", "insight_type", "is_active"],
                name="proc_di_org_type_act_idx",
            ),
            models.Index(
                fields=["organization", "-updated_at"],
                name="proc_di_org_updated_idx",
            ),
        ]

    def __str__(self):
        return f"{self.get_insight_type_display()}: {self.area_name}"
