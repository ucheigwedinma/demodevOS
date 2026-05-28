from datetime import date
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction

from apps.settings.currency import get_default_currency_code

# Alias builtin — the `property` name is used as a FK field below,
# which would shadow the decorator inside the class body.
cached_property_builtin = property


class PaymentMethod(models.TextChoices):
    BANK_TRANSFER = "bank_transfer", "Bank Transfer"
    CHECK = "check", "Check"
    CASH = "cash", "Cash"
    CREDIT_CARD = "credit_card", "Credit Card"
    OTHER = "other", "Other"


class Bill(models.Model):
    """An invoice from a vendor — what we owe (accounts payable)."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        APPROVED = "approved", "Approved"
        PAID = "paid", "Paid"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="bills",
    )
    vendor = models.ForeignKey(
        "procurement.Vendor", on_delete=models.CASCADE, related_name="bills"
    )
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bills",
    )
    purchase_order = models.ForeignKey(
        "procurement.PurchaseOrder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bills",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bills",
        help_text="Links bill to a project for cost tracking.",
    )
    bill_number = models.CharField(max_length=100, unique=True, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    issue_date = models.DateField()
    due_date = models.DateField()
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    match_status = models.CharField(
        max_length=20, blank=True, default="",
        help_text="3-way match result: full_match, partial_match, variance, mismatch, no_grn, pending",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-due_date"]
        indexes = [
            models.Index(fields=["organization", "status"], name="fin_bill_org_status_idx"),
            models.Index(fields=["organization", "-created_at"], name="fin_bill_org_created_idx"),
        ]

    def __str__(self):
        return f"{self.bill_number} — {self.vendor.name}"

    def save(self, **kwargs):
        if not self.bill_number:
            self.bill_number = self._generate_bill_number()
        super().save(**kwargs)

    @staticmethod
    def _generate_bill_number() -> str:
        last = (
            Bill.objects.filter(bill_number__startswith="BILL-")
            .order_by("-bill_number")
            .values_list("bill_number", flat=True)
            .first()
        )
        if last:
            try:
                seq = int(last.split("-", 1)[1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f"BILL-{seq:05d}"

    @cached_property_builtin
    def paid_amount(self) -> Decimal:
        total = self.payments.aggregate(total=models.Sum("amount"))["total"]
        return total or Decimal("0.00")

    @cached_property_builtin
    def balance_due(self) -> Decimal:
        return self.total_amount - self.paid_amount

    @cached_property_builtin
    def is_overdue(self) -> bool:
        if self.status in (self.Status.PAID, self.Status.CANCELLED):
            return False
        return self.due_date < date.today()

    @cached_property_builtin
    def days_overdue(self) -> int:
        if not self.is_overdue:
            return 0
        return (date.today() - self.due_date).days

    def recalculate_totals(self):
        agg = self.line_items.aggregate(total=models.Sum("amount"))
        self.subtotal = agg["total"] or Decimal("0.00")
        self.total_amount = self.subtotal + self.tax_amount
        self.save(update_fields=["subtotal", "total_amount", "updated_at"])

    def update_status_from_payments(self):
        if self.paid_amount >= self.total_amount and self.total_amount > 0:
            self.status = self.Status.PAID
            self.save(update_fields=["status", "updated_at"])


class BillLineItem(models.Model):
    """Individual line item on a bill."""

    bill = models.ForeignKey(
        Bill, on_delete=models.CASCADE, related_name="line_items"
    )
    po_item = models.ForeignKey(
        "procurement.PurchaseOrderItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bill_line_items",
        help_text="Links this bill line to a specific PO line item for 3-way matching.",
    )
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=15, decimal_places=2)
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    sort_order = models.PositiveIntegerField(default=0)
    # GL coding — optional, enables budget tracking
    account = models.ForeignKey(
        "Account",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bill_line_items",
        help_text="GL account this expense is coded to",
    )
    department = models.ForeignKey(
        "settings.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bill_line_items",
    )
    cost_center = models.ForeignKey(
        "settings.CostCenter",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bill_line_items",
    )
    # BOQ traceability
    bom_item = models.ForeignKey(
        "inventory.BOMItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bill_line_items",
        help_text="Links this bill line to a specific BOQ item.",
    )
    cost_code_budget = models.ForeignKey(
        "projects.CostCodeBudget",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bill_line_items",
        help_text="Links this expense to a project cost code for actual cost tracking.",
    )

    class Meta:
        ordering = ["sort_order"]

    def save(self, **kwargs):
        self.amount = self.quantity * self.unit_price
        super().save(**kwargs)

    def __str__(self):
        return f"{self.bill.bill_number} — {self.description}"


class BillPayment(models.Model):
    """Payment record against a bill."""

    bill = models.ForeignKey(
        Bill, on_delete=models.CASCADE, related_name="payments"
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    payment_date = models.DateField()
    payment_method = models.CharField(
        max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.BANK_TRANSFER
    )
    reference_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-payment_date"]

    def __str__(self):
        return f"{self.bill.bill_number} — {self.amount} on {self.payment_date}"


class Customer(models.Model):
    """Contact info for receivables (accounts receivable)."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="customers",
    )
    name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    tax_id = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    support_ticketing_enabled = models.BooleanField(
        default=False,
        help_text="Enabled automatically after customer onboarding completes.",
    )
    support_ticketing_enabled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="fin_cust_org_created_idx"),
        ]

    def __str__(self):
        return self.name


class Invoice(models.Model):
    """An invoice to a customer — what they owe us (accounts receivable)."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        PAID = "paid", "Paid"
        OVERDUE = "overdue", "Overdue"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="invoices",
    )
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="invoices"
    )
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices",
    )
    invoice_number = models.CharField(max_length=100, unique=True, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    issue_date = models.DateField()
    due_date = models.DateField()
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-due_date"]
        indexes = [
            models.Index(fields=["organization", "status"], name="fin_inv_org_status_idx"),
            models.Index(fields=["organization", "-created_at"], name="fin_inv_org_created_idx"),
        ]

    def __str__(self):
        return f"{self.invoice_number} — {self.customer.name}"

    def save(self, **kwargs):
        if not self.invoice_number:
            self.invoice_number = self._generate_invoice_number()
        super().save(**kwargs)

    @staticmethod
    def _generate_invoice_number() -> str:
        import re
        last_numbers = (
            Invoice.objects.filter(invoice_number__regex=r"^INV-\d+$")
            .values_list("invoice_number", flat=True)
        )
        max_seq = 0
        for num in last_numbers:
            match = re.search(r"INV-(\d+)$", num)
            if match:
                max_seq = max(max_seq, int(match.group(1)))
        return f"INV-{max_seq + 1:05d}"

    @cached_property_builtin
    def paid_amount(self) -> Decimal:
        total = self.payments.aggregate(total=models.Sum("amount"))["total"]
        return total or Decimal("0.00")

    @cached_property_builtin
    def balance_due(self) -> Decimal:
        return self.total_amount - self.paid_amount

    @cached_property_builtin
    def is_overdue(self) -> bool:
        if self.status in (self.Status.PAID, self.Status.CANCELLED):
            return False
        return self.due_date < date.today()

    @cached_property_builtin
    def days_overdue(self) -> int:
        if not self.is_overdue:
            return 0
        return (date.today() - self.due_date).days

    def recalculate_totals(self):
        agg = self.line_items.aggregate(total=models.Sum("amount"))
        self.subtotal = agg["total"] or Decimal("0.00")
        self.total_amount = self.subtotal + self.tax_amount
        self.save(update_fields=["subtotal", "total_amount", "updated_at"])

    def update_status_from_payments(self):
        if self.paid_amount >= self.total_amount and self.total_amount > 0:
            self.status = self.Status.PAID
            self.save(update_fields=["status", "updated_at"])


class InvoiceLineItem(models.Model):
    """Individual line item on an invoice."""

    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="line_items"
    )
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=15, decimal_places=2)
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order"]

    def save(self, **kwargs):
        self.amount = self.quantity * self.unit_price
        super().save(**kwargs)

    def __str__(self):
        return f"{self.invoice.invoice_number} — {self.description}"


class InvoicePayment(models.Model):
    """Payment record against an invoice."""

    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="payments"
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    payment_date = models.DateField()
    payment_method = models.CharField(
        max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.BANK_TRANSFER
    )
    reference_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-payment_date"]

    def __str__(self):
        return f"{self.invoice.invoice_number} — {self.amount} on {self.payment_date}"


# ---------------------------------------------------------------------------
# Chart of Accounts
# ---------------------------------------------------------------------------


class AccountType(models.TextChoices):
    ASSET = "asset", "Asset"
    LIABILITY = "liability", "Liability"
    EQUITY = "equity", "Equity"
    REVENUE = "revenue", "Revenue"
    EXPENSE = "expense", "Expense"


class AccountSubType(models.TextChoices):
    # Asset
    CURRENT_ASSET = "current_asset", "Current Asset"
    FIXED_ASSET = "fixed_asset", "Fixed Asset"
    OTHER_ASSET = "other_asset", "Other Asset"
    # Liability
    CURRENT_LIABILITY = "current_liability", "Current Liability"
    LONG_TERM_LIABILITY = "long_term_liability", "Long-Term Liability"
    # Equity
    OWNERS_EQUITY = "owners_equity", "Owner's Equity"
    RETAINED_EARNINGS = "retained_earnings", "Retained Earnings"
    # Revenue
    OPERATING_REVENUE = "operating_revenue", "Operating Revenue"
    OTHER_REVENUE = "other_revenue", "Other Revenue"
    # Expense
    OPERATING_EXPENSE = "operating_expense", "Operating Expense"
    COST_OF_GOODS_SOLD = "cost_of_goods_sold", "Cost of Goods Sold"
    OTHER_EXPENSE = "other_expense", "Other Expense"


class Account(models.Model):
    """Chart of Accounts entry — org-scoped general ledger account."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="gl_accounts",
    )
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=255)
    account_type = models.CharField(max_length=20, choices=AccountType.choices)
    sub_type = models.CharField(max_length=30, choices=AccountSubType.choices)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    is_system = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]
        unique_together = [("organization", "code")]
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="fin_acct_org_created_idx"),
        ]

    def __str__(self):
        return f"{self.code} — {self.name}"


# ---------------------------------------------------------------------------
# General Ledger & Journals
# ---------------------------------------------------------------------------


class JournalSourceType(models.TextChoices):
    MANUAL = "manual", "Manual"
    BILL = "bill", "Bill"
    INVOICE = "invoice", "Invoice"
    PAYMENT = "payment", "Payment"
    ADJUSTMENT = "adjustment", "Adjustment"
    CLOSING = "closing", "Closing Entry"
    OPENING = "opening", "Opening Balance"
    PAYROLL = "payroll", "Payroll"


class JournalEntry(models.Model):
    """Journal header record for double-entry accounting."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        POSTED = "posted", "Posted"
        REVERSED = "reversed", "Reversed"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="journal_entries",
    )
    journal_number = models.CharField(max_length=100, blank=True)
    entry_date = models.DateField(default=date.today)
    description = models.CharField(max_length=500)
    reference = models.CharField(max_length=100, blank=True)
    source_type = models.CharField(
        max_length=20,
        choices=JournalSourceType.choices,
        default=JournalSourceType.MANUAL,
    )
    source_id = models.PositiveBigIntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    posted_at = models.DateTimeField(null=True, blank=True)
    posted_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posted_journal_entries",
    )
    created_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_journal_entries",
    )
    reversed_entry = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reversal_entries",
    )
    is_reversal = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-entry_date", "-created_at"]
        unique_together = [("organization", "journal_number")]
        indexes = [
            models.Index(fields=["organization", "status", "entry_date"]),
            models.Index(fields=["organization", "source_type", "source_id"]),
        ]

    def __str__(self):
        return f"{self.journal_number} ({self.entry_date})"

    def clean(self):
        if self.reversed_entry_id and self.reversed_entry_id == self.id:
            raise ValidationError("A journal entry cannot reverse itself.")

    def save(self, **kwargs):
        if self.pk or self.journal_number:
            super().save(**kwargs)
            return

        # Generate org-scoped journal numbers and retry on unique collisions.
        for _ in range(5):
            self.journal_number = self._generate_journal_number()
            try:
                with transaction.atomic():
                    super().save(**kwargs)
                return
            except IntegrityError as exc:
                if "journal_number" not in str(exc):
                    raise
                self.journal_number = ""
                continue

        raise IntegrityError("Could not allocate a unique journal number after 5 attempts.")

    def _generate_journal_number(self) -> str:
        prefix = "JRN-"
        qs = JournalEntry.objects.filter(journal_number__startswith=prefix)
        if self.organization_id:
            qs = qs.filter(organization_id=self.organization_id)
        last = qs.order_by("-journal_number").values_list("journal_number", flat=True).first()
        if last:
            try:
                seq = int(last.split("-", 1)[1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f"{prefix}{seq:06d}"


class JournalLine(models.Model):
    """Line-level debit or credit in a journal entry."""

    journal = models.ForeignKey(
        JournalEntry, on_delete=models.CASCADE, related_name="lines"
    )
    line_number = models.PositiveIntegerField(default=1)
    account = models.ForeignKey(
        Account, on_delete=models.PROTECT, related_name="journal_lines"
    )
    debit_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    credit_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    memo = models.CharField(max_length=255, blank=True)
    department = models.ForeignKey(
        "settings.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="journal_lines",
    )
    cost_center = models.ForeignKey(
        "settings.CostCenter",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="journal_lines",
    )

    class Meta:
        ordering = ["line_number", "id"]
        unique_together = [("journal", "line_number")]

    def __str__(self):
        return f"{self.journal.journal_number} #{self.line_number}"

    def clean(self):
        if self.debit_amount < 0 or self.credit_amount < 0:
            raise ValidationError("Debit and credit cannot be negative.")
        if self.debit_amount > 0 and self.credit_amount > 0:
            raise ValidationError("A journal line cannot have both debit and credit amounts.")
        if self.debit_amount <= 0 and self.credit_amount <= 0:
            raise ValidationError("A journal line must have either a debit or a credit amount.")

    def save(self, **kwargs):
        if not self.line_number:
            last = (
                JournalLine.objects.filter(journal_id=self.journal_id)
                .order_by("-line_number")
                .values_list("line_number", flat=True)
                .first()
            )
            self.line_number = (last or 0) + 1
        self.full_clean()
        super().save(**kwargs)


class LedgerEntry(models.Model):
    """Immutable posted ledger rows created from journal lines."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="ledger_entries",
    )
    journal_entry = models.ForeignKey(
        JournalEntry, on_delete=models.PROTECT, related_name="ledger_entries"
    )
    journal_line = models.ForeignKey(
        JournalLine, on_delete=models.PROTECT, related_name="ledger_entries"
    )
    account = models.ForeignKey(
        Account, on_delete=models.PROTECT, related_name="ledger_entries"
    )
    entry_date = models.DateField()
    debit_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    credit_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    description = models.CharField(max_length=500, blank=True)
    source_type = models.CharField(
        max_length=20,
        choices=JournalSourceType.choices,
        default=JournalSourceType.MANUAL,
    )
    source_id = models.PositiveBigIntegerField(null=True, blank=True)
    department = models.ForeignKey(
        "settings.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ledger_entries",
    )
    cost_center = models.ForeignKey(
        "settings.CostCenter",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ledger_entries",
    )
    posted_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-entry_date", "-id"]
        indexes = [
            models.Index(fields=["organization", "entry_date"]),
            models.Index(fields=["organization", "account", "entry_date"]),
            models.Index(fields=["journal_entry", "account"]),
        ]

    def __str__(self):
        return f"{self.journal_entry.journal_number} — {self.account.code}"


# ---------------------------------------------------------------------------
# Budget Tracker
# ---------------------------------------------------------------------------


class Budget(models.Model):
    """Financial budget container for a fiscal period (org-wide or project-scoped)."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        CLOSED = "closed", "Closed"

    class PeriodType(models.TextChoices):
        ANNUAL = "annual", "Annual"
        QUARTERLY = "quarterly", "Quarterly"
        MONTHLY = "monthly", "Monthly"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="budgets",
    )
    project = models.OneToOneField(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="budget_container",
        null=True,
        blank=True,
        help_text="Linked project when this budget is a project budget container.",
    )
    name = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    period_type = models.CharField(
        max_length=20, choices=PeriodType.choices, default=PeriodType.ANNUAL
    )
    start_date = models.DateField()
    end_date = models.DateField()
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    overspend_tolerance_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Percentage above budget before critical alert (e.g. 10.00 = 10%)",
    )
    warning_threshold_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=80,
        help_text="Percentage of budget consumed before warning alert (e.g. 80.00 = 80%)",
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_budgets",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date"]
        unique_together = [("organization", "name")]
        indexes = [
            models.Index(fields=["organization", "status"], name="fin_budg_org_status_idx"),
        ]

    def __str__(self):
        return self.name


class BudgetLineItem(models.Model):
    """Budget allocation per GL account, optionally scoped to department/cost center."""

    budget = models.ForeignKey(
        Budget, on_delete=models.CASCADE, related_name="line_items"
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="budget_lines",
        help_text="GL account this budget line allocates funds to",
    )
    department = models.ForeignKey(
        "settings.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="budget_lines",
    )
    cost_center = models.ForeignKey(
        "settings.CostCenter",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="budget_lines",
    )
    budgeted_amount = models.DecimalField(max_digits=15, decimal_places=2)
    notes = models.CharField(max_length=500, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "account__code"]
        unique_together = [("budget", "account", "department", "cost_center")]

    def __str__(self):
        return f"{self.budget.name} — {self.account.code}"


class ReforecastSuggestion(models.Model):
    """A generated redistribution suggestion for a budget."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending Review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    budget = models.ForeignKey(
        Budget, on_delete=models.CASCADE, related_name="reforecasts"
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    reason = models.TextField(
        blank=True,
        help_text="Auto-generated explanation of why reforecast was suggested",
    )
    generated_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-generated_at"]

    def __str__(self):
        return f"Reforecast for {self.budget.name} ({self.status})"


class ReforecastLineItem(models.Model):
    """Individual line-level change in a reforecast suggestion."""

    reforecast = models.ForeignKey(
        ReforecastSuggestion, on_delete=models.CASCADE, related_name="line_items"
    )
    budget_line_item = models.ForeignKey(
        BudgetLineItem, on_delete=models.CASCADE, related_name="reforecast_items"
    )
    current_amount = models.DecimalField(max_digits=15, decimal_places=2)
    suggested_amount = models.DecimalField(max_digits=15, decimal_places=2)
    actual_spent = models.DecimalField(max_digits=15, decimal_places=2)
    delta = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="suggested_amount - current_amount",
    )

    class Meta:
        ordering = ["budget_line_item__sort_order"]

    def __str__(self):
        return f"{self.budget_line_item.account.code}: {self.current_amount} → {self.suggested_amount}"


# =======================
# Equity Waterfall Models
# =======================


class Investor(models.Model):
    """External investor entity that can invest in multiple projects."""

    class InvestorType(models.TextChoices):
        INDIVIDUAL = "individual", "Individual"
        INSTITUTIONAL = "institutional", "Institutional"
        FAMILY_OFFICE = "family_office", "Family Office"
        FUND = "fund", "Fund"
        CORPORATE = "corporate", "Corporate"
        JV_PARTNER = "jv_partner", "JV Partner"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="investors",
    )
    name = models.CharField(max_length=255)
    investor_type = models.CharField(
        max_length=20,
        choices=InvestorType.choices,
        default=InvestorType.INDIVIDUAL,
    )

    # Contact information
    contact_person = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    tax_id = models.CharField(max_length=100, blank=True)

    # Entity details
    entity_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Legal entity name if different from investor name",
    )
    registration_number = models.CharField(max_length=100, blank=True)

    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        unique_together = [("organization", "name")]
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="fin_invr_org_created_idx"),
        ]

    def __str__(self):
        return self.name


class ProjectInvestor(models.Model):
    """Links an investor to a project with ownership % and contribution tracking."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="project_investors",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="investors",
    )
    investor = models.ForeignKey(
        Investor,
        on_delete=models.PROTECT,
        related_name="project_investments",
    )

    # Ownership
    ownership_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Ownership percentage (0.00 - 100.00)",
    )

    # Capital tracking
    capital_committed = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Total capital committed by investor",
    )
    capital_contributed = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Actual capital contributed to date",
    )

    # Cumulative distribution tracking (for waterfall calculation)
    total_capital_returned = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Cumulative capital distributions received",
    )
    total_profit_distributed = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Cumulative profit distributions received",
    )

    # Waterfall configuration (project-specific overrides)
    custom_profit_split_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Override profit split % for this investor (if different from project default)",
    )

    sort_order = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["project", "sort_order", "investor__name"]
        unique_together = [("project", "investor")]
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="fin_pinv_org_created_idx"),
        ]

    def __str__(self):
        return f"{self.project.name} - {self.investor.name} ({self.ownership_percentage}%)"

    @cached_property_builtin
    def unreturned_capital(self) -> Decimal:
        """Capital contributed but not yet returned."""
        return max(self.capital_contributed - self.total_capital_returned, Decimal("0.00"))


class ProjectLedger(models.Model):
    """Project-scoped ledger container, separate from organization support ledgers."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="project_ledgers",
    )
    project = models.OneToOneField(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="project_ledger",
    )
    code = models.CharField(max_length=40)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]
        unique_together = [("organization", "code")]
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="fin_pldg_org_created_idx"),
        ]

    def __str__(self):
        return f"{self.code} — {self.name}"


class ProjectCostCenter(models.Model):
    """Project-specific cost center, distinct from organization support cost centers."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="project_cost_centers",
    )
    project = models.OneToOneField(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="project_cost_center",
    )
    code = models.CharField(max_length=40)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]
        unique_together = [("organization", "code")]
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="fin_pcc_org_created_idx"),
        ]

    def __str__(self):
        return f"{self.code} — {self.name}"


class ProjectRevenueCenter(models.Model):
    """Project-specific revenue center, distinct from organization support centers."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="project_revenue_centers",
    )
    project = models.OneToOneField(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="project_revenue_center",
    )
    code = models.CharField(max_length=40)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]
        unique_together = [("organization", "code")]
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="fin_prc_org_created_idx"),
        ]

    def __str__(self):
        return f"{self.code} — {self.name}"


class ProjectAccountMapping(models.Model):
    """Project-level mapping of financial workflows to chart-of-accounts entries."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="project_account_mappings",
    )
    project = models.OneToOneField(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="chart_of_accounts_mapping",
    )
    construction_cost_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="project_construction_cost_mappings",
    )
    capex_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="project_capex_mappings",
    )
    development_expense_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="project_development_expense_mappings",
    )
    sales_revenue_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="project_sales_revenue_mappings",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["project"]
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="fin_pam_org_created_idx"),
        ]

    def __str__(self):
        return f"COA Mapping — {self.project.name}"


class ProjectFinanceArtifact(models.Model):
    """Project-level finance artifacts that must exist at initialization."""

    class ArtifactType(models.TextChoices):
        PROJECT_BUDGET_DASHBOARD = "project_budget_dashboard", "Project Budget Dashboard"
        CASHFLOW_FORECAST = "cashflow_forecast", "Cashflow Forecast"
        COST_TRACKER = "cost_tracker", "Cost Tracker"
        VARIANCE_ANALYSIS = "variance_analysis", "Variance Analysis"

    class MenuGroup(models.TextChoices):
        BUDGET = "budget", "Budget"
        FORECAST = "forecast", "Forecast"
        COST = "cost", "Cost"
        ANALYTICS = "analytics", "Analytics"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="project_finance_artifacts",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="finance_artifacts",
    )
    artifact_type = models.CharField(
        max_length=40,
        choices=ArtifactType.choices,
    )
    name = models.CharField(max_length=120)
    menu_path = models.CharField(max_length=255)
    menu_group = models.CharField(
        max_length=20,
        choices=MenuGroup.choices,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["project", "artifact_type"]
        unique_together = [("project", "artifact_type")]
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="fin_pfa_org_created_idx"),
            models.Index(fields=["project", "menu_group"], name="fin_pfa_proj_group_idx"),
        ]

    def __str__(self):
        return f"{self.project.name} — {self.get_artifact_type_display()}"


class CapitalContribution(models.Model):
    """Tracks individual capital contribution events from investors."""

    project_investor = models.ForeignKey(
        ProjectInvestor,
        on_delete=models.PROTECT,
        related_name="contributions",
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    contribution_date = models.DateField()
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.BANK_TRANSFER,
    )
    reference_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-contribution_date"]

    def __str__(self):
        return f"{self.project_investor.investor.name} - {self.amount} on {self.contribution_date}"


class WaterfallConfig(models.Model):
    """Project-level waterfall structure configuration."""

    project = models.OneToOneField(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="waterfall_config",
    )

    # Tier 2 profit split configuration
    investor_profit_split_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("80.00"),
        help_text="Percentage of Tier 2 profits to investors (e.g., 80.00 for 80/20 split)",
    )
    sponsor_profit_split_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("20.00"),
        help_text="Percentage of Tier 2 profits to sponsor/GP",
    )

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Waterfall: {self.project.name}"

    def save(self, *args, **kwargs):
        # Validate that split percentages sum to 100
        from django.core.exceptions import ValidationError

        total = self.investor_profit_split_pct + self.sponsor_profit_split_pct
        if total != Decimal("100.00"):
            raise ValidationError(
                f"Profit split percentages must sum to 100.00, got {total}"
            )
        super().save(*args, **kwargs)


class WaterfallDistribution(models.Model):
    """Parent record for a distribution event applying the waterfall."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        CALCULATED = "calculated", "Calculated"
        APPROVED = "approved", "Approved"
        DISTRIBUTED = "distributed", "Distributed"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="waterfall_distributions",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.PROTECT,
        related_name="distributions",
    )
    distribution_number = models.CharField(max_length=100, unique=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    # Distribution details
    distribution_date = models.DateField()
    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Total amount available for distribution",
    )

    # Calculated breakdown
    tier1_capital_returned = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Amount allocated to Tier 1 (return of capital)",
    )
    tier2_profit_split = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Amount allocated to Tier 2 (profit split)",
    )
    sponsor_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Amount to sponsor/GP (from Tier 2)",
    )

    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_distributions",
    )
    approved_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_distributions",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-distribution_date"]
        indexes = [
            models.Index(fields=["project", "status", "distribution_date"]),
            models.Index(fields=["organization", "status"], name="fin_wfall_org_status_idx"),
        ]

    def __str__(self):
        return f"{self.distribution_number} - {self.project.name} - {self.total_amount}"

    def save(self, *args, **kwargs):
        if not self.distribution_number:
            self.distribution_number = self._generate_distribution_number()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_distribution_number() -> str:
        last = (
            WaterfallDistribution.objects.filter(
                distribution_number__startswith="DIST-"
            )
            .order_by("-distribution_number")
            .values_list("distribution_number", flat=True)
            .first()
        )
        if last:
            try:
                seq = int(last.split("-", 1)[1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f"DIST-{seq:05d}"


class DistributionLineItem(models.Model):
    """Calculated distribution amount for a specific investor."""

    distribution = models.ForeignKey(
        WaterfallDistribution,
        on_delete=models.CASCADE,
        related_name="line_items",
    )
    project_investor = models.ForeignKey(
        ProjectInvestor,
        on_delete=models.PROTECT,
        related_name="distributions",
    )

    # Breakdown by tier
    tier1_capital_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Tier 1: Return of capital",
    )
    tier2_profit_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Tier 2: Profit split",
    )
    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Total for this investor (tier1 + tier2)",
    )

    # State after this distribution
    capital_returned_to_date = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Cumulative capital returned after this distribution",
    )
    profit_distributed_to_date = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Cumulative profit distributed after this distribution",
    )

    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["distribution", "sort_order"]
        unique_together = [("distribution", "project_investor")]
        indexes = [
            models.Index(fields=["distribution", "project_investor"]),
        ]

    def __str__(self):
        return f"{self.distribution.distribution_number} - {self.project_investor.investor.name} - {self.total_amount}"


# ---------------------------------------------------------------------------
# SPV Entity
# ---------------------------------------------------------------------------


class SPVEntity(models.Model):
    """Special Purpose Vehicle — a legal entity created for a specific project or purpose."""

    class EntityType(models.TextChoices):
        COMPANY = "company", "Company"
        LLP = "llp", "Limited Liability Partnership"
        TRUST = "trust", "Trust"
        FUND = "fund", "Fund"
        LLC = "llc", "Limited Liability Company"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        DORMANT = "dormant", "Dormant"
        DISSOLVED = "dissolved", "Dissolved"
        UNDER_FORMATION = "under_formation", "Under Formation"

    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.CASCADE, related_name="spv_entities"
    )
    name = models.CharField(max_length=255)
    entity_type = models.CharField(
        max_length=20, choices=EntityType.choices, default=EntityType.COMPANY
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    registration_number = models.CharField(max_length=100, blank=True)
    registration_date = models.DateField(null=True, blank=True)
    registered_address = models.TextField(blank=True)
    tax_id = models.CharField(max_length=100, blank=True)
    jurisdiction = models.CharField(max_length=200, blank=True)
    authorized_capital = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )
    paid_up_capital = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )
    purpose = models.TextField(blank=True, help_text="Purpose/objective of the SPV")
    parent_entity = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="subsidiaries"
    )
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        unique_together = [("organization", "name")]
        verbose_name = "SPV Entity"
        verbose_name_plural = "SPV Entities"
        indexes = [
            models.Index(fields=["organization", "status"], name="fin_spv_org_status_idx"),
            models.Index(fields=["organization", "-created_at"], name="fin_spv_org_created_idx"),
        ]

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# Payment Plan
# ---------------------------------------------------------------------------


class PaymentPlan(models.Model):
    """Scheduled payment plan — either receivable (customer owes us) or payable (we owe vendor)."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    class PlanType(models.TextChoices):
        FIXED_INSTALLMENT = "fixed_installment", "Fixed Installment"
        MILESTONE_BASED = "milestone_based", "Milestone-Based"
        PERCENTAGE_BASED = "percentage_based", "Percentage-Based"
        CUSTOM = "custom", "Custom Schedule"

    class Frequency(models.TextChoices):
        WEEKLY = "weekly", "Weekly"
        BIWEEKLY = "biweekly", "Bi-Weekly"
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        SEMI_ANNUAL = "semi_annual", "Semi-Annual"
        ANNUAL = "annual", "Annual"
        ONE_TIME = "one_time", "One-Time"

    class Direction(models.TextChoices):
        RECEIVABLE = "receivable", "Receivable (Customer owes us)"
        PAYABLE = "payable", "Payable (We owe vendor)"

    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.CASCADE, related_name="payment_plans"
    )
    plan_number = models.CharField(max_length=100, unique=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    plan_type = models.CharField(
        max_length=20, choices=PlanType.choices, default=PlanType.FIXED_INSTALLMENT
    )
    direction = models.CharField(
        max_length=15, choices=Direction.choices, default=Direction.RECEIVABLE
    )
    frequency = models.CharField(
        max_length=15, choices=Frequency.choices, default=Frequency.MONTHLY
    )

    # Counterparty (one of these)
    customer = models.ForeignKey(
        "finance.Customer", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="payment_plans",
    )
    vendor = models.ForeignKey(
        "procurement.Vendor", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="payment_plans",
    )
    investor = models.ForeignKey(
        "finance.Investor", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="payment_plans",
    )

    # Context
    project = models.ForeignKey(
        "projects.Project", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="payment_plans",
    )
    unit = models.ForeignKey(
        "properties.Unit", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="payment_plans",
    )
    spv_entity = models.ForeignKey(
        SPVEntity, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="payment_plans",
    )

    # Financial summary
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3, default=get_default_currency_code)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    number_of_installments = models.PositiveIntegerField(default=1)

    # Tracking
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="created_payment_plans",
    )
    approved_by = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="approved_payment_plans",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Payment Plan"
        indexes = [
            models.Index(fields=["organization", "status"], name="fin_pplan_org_status_idx"),
            models.Index(fields=["organization", "-created_at"], name="fin_pplan_org_created_idx"),
        ]

    def __str__(self):
        return f"{self.plan_number} — {self.title}"

    def save(self, **kwargs):
        if not self.plan_number:
            self.plan_number = self._generate_plan_number()
        super().save(**kwargs)

    @staticmethod
    def _generate_plan_number() -> str:
        last = (
            PaymentPlan.objects.filter(plan_number__startswith="PP-")
            .order_by("-plan_number")
            .values_list("plan_number", flat=True)
            .first()
        )
        if last:
            try:
                seq = int(last.split("-", 1)[1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f"PP-{seq:05d}"

    @cached_property_builtin
    def paid_amount(self):
        return self.installments.aggregate(total=models.Sum("paid_amount"))["total"] or Decimal("0.00")

    @cached_property_builtin
    def balance_due(self):
        return self.total_amount - self.paid_amount

    @cached_property_builtin
    def installment_count(self):
        return self.installments.count()


# ---------------------------------------------------------------------------
# Payment Installment
# ---------------------------------------------------------------------------


class PaymentInstallment(models.Model):
    """A single scheduled payment within a PaymentPlan."""

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        DUE = "due", "Due"
        PAID = "paid", "Paid"
        PARTIALLY_PAID = "partially_paid", "Partially Paid"
        OVERDUE = "overdue", "Overdue"
        WAIVED = "waived", "Waived"
        CANCELLED = "cancelled", "Cancelled"

    payment_plan = models.ForeignKey(
        PaymentPlan, on_delete=models.CASCADE, related_name="installments"
    )
    installment_number = models.PositiveIntegerField()
    label = models.CharField(max_length=200, blank=True)

    # Amounts
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # Dates
    scheduled_date = models.DateField()
    due_date = models.DateField()
    paid_date = models.DateField(null=True, blank=True)

    # Conditions
    milestone = models.ForeignKey(
        "projects.ProjectMilestone", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="installments",
    )
    percentage_of_total = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.SCHEDULED
    )
    payment_method = models.CharField(
        max_length=20, choices=PaymentMethod.choices, blank=True
    )
    reference_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["payment_plan", "installment_number"]
        unique_together = [("payment_plan", "installment_number")]
        verbose_name = "Payment Installment"

    def __str__(self):
        return f"#{self.installment_number} — {self.payment_plan.plan_number}"

    @cached_property_builtin
    def balance_due(self):
        return self.amount - self.paid_amount

    @cached_property_builtin
    def is_overdue(self):
        return (
            self.status not in (self.Status.PAID, self.Status.WAIVED, self.Status.CANCELLED)
            and self.due_date < date.today()
        )


class PaymentVoucher(models.Model):
    """Authorization document to disburse payment to a vendor."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        PAID = "paid", "Paid"
        VOIDED = "voided", "Voided"
        CANCELLED = "cancelled", "Cancelled"
        DISPUTED = "disputed", "Disputed"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="payment_vouchers",
    )
    voucher_number = models.CharField(max_length=100, unique=True, blank=True)
    vendor = models.ForeignKey(
        "procurement.Vendor",
        on_delete=models.CASCADE,
        related_name="payment_vouchers",
    )
    bill = models.ForeignKey(
        Bill,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_vouchers",
    )
    class Priority(models.TextChoices):
        STANDARD = "standard", "Standard"
        HIGH = "high", "High"

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    priority = models.CharField(
        max_length=10, choices=Priority.choices, default=Priority.STANDARD
    )
    issue_date = models.DateField()
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    payment_method = models.CharField(
        max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.BANK_TRANSFER
    )
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_vouchers",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"], name="fin_pv_org_status_idx"),
            models.Index(fields=["organization", "-created_at"], name="fin_pv_org_created_idx"),
        ]

    def __str__(self):
        return f"{self.voucher_number} — {self.vendor.name}"

    def save(self, **kwargs):
        if not self.voucher_number:
            self.voucher_number = self._generate_voucher_number()
        super().save(**kwargs)

    @staticmethod
    def _generate_voucher_number() -> str:
        last = (
            PaymentVoucher.objects.filter(voucher_number__startswith="PV-")
            .order_by("-voucher_number")
            .values_list("voucher_number", flat=True)
            .first()
        )
        if last:
            try:
                seq = int(last.split("-", 1)[1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f"PV-{seq:05d}"


class PaymentRun(models.Model):
    """
    A batch of approved payment vouchers grouped for simultaneous execution.
    Manages volume disbursement, liquidity checks, and bank integration.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SCHEDULED = "scheduled", "Scheduled"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="payment_runs",
    )
    batch_id = models.CharField(max_length=100, unique=True, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    vouchers = models.ManyToManyField(
        PaymentVoucher,
        related_name="payment_runs",
        blank=True,
    )
    funding_account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_runs",
        help_text="GL account from which funds will be drawn",
    )
    funding_account_label = models.CharField(
        max_length=200,
        blank=True,
        help_text="Display label, e.g. 'Main Operations - Zenith Bank'",
    )
    scheduled_date = models.DateField(null=True, blank=True)
    executed_at = models.DateTimeField(null=True, blank=True)
    executed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="executed_payment_runs",
    )
    notes = models.TextField(blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_payment_runs",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    funding_balance = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        help_text="Snapshot of funding account balance at time of review",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_payment_runs",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"], name="fin_pr_org_status_idx"),
            models.Index(fields=["organization", "-created_at"], name="fin_pr_org_created_idx"),
        ]

    def __str__(self):
        return self.batch_id or f"Run #{self.pk}"

    @property
    def total_value(self):
        return self.vouchers.aggregate(total=models.Sum("amount"))["total"] or 0

    @property
    def payment_count(self):
        return self.vouchers.count()

    def save(self, **kwargs):
        if not self.batch_id:
            self.batch_id = self._generate_batch_id()
        super().save(**kwargs)

    def _generate_batch_id(self) -> str:
        from django.utils import timezone

        today = timezone.now().strftime("%Y-%m-%d")
        prefix = f"RUN-{today}-"
        last = (
            PaymentRun.objects.filter(batch_id__startswith=prefix)
            .order_by("-batch_id")
            .values_list("batch_id", flat=True)
            .first()
        )
        if last:
            try:
                seq = int(last.rsplit("-", 1)[1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f"{prefix}{seq:02d}"


class PaymentReceipt(models.Model):
    """
    Proof of Payment record for a completed transaction.
    Shared with vendors or project stakeholders as final confirmation.
    """

    class Status(models.TextChoices):
        SUCCESSFUL = "successful", "Successful"
        SETTLED = "settled", "Settled"
        REVERSED = "reversed", "Reversed"
        FAILED = "failed", "Failed"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="payment_receipts",
    )
    receipt_number = models.CharField(max_length=100, unique=True, blank=True)
    transaction_reference = models.CharField(
        max_length=200, blank=True,
        help_text="Bank NIP or internal transfer reference",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.SUCCESSFUL
    )
    payment_date = models.DateTimeField()
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    payment_method = models.CharField(
        max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.BANK_TRANSFER
    )
    vendor = models.ForeignKey(
        "procurement.Vendor",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="payment_receipts",
    )
    voucher = models.ForeignKey(
        PaymentVoucher,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="receipts",
    )
    vouchers = models.ManyToManyField(
        PaymentVoucher,
        related_name="receipt_allocations",
        blank=True,
        help_text="All vouchers covered by this receipt",
    )
    payment_run = models.ForeignKey(
        PaymentRun,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="receipts",
    )
    payer_account = models.CharField(max_length=200, blank=True, help_text="Funding bank account used")
    payee_account = models.CharField(max_length=200, blank=True, help_text="Vendor bank account credited")
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="created_receipts",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-payment_date"]
        indexes = [
            models.Index(fields=["organization", "status"], name="fin_rcpt_org_status_idx"),
            models.Index(fields=["organization", "-payment_date"], name="fin_rcpt_org_date_idx"),
        ]

    def __str__(self):
        return self.receipt_number or f"Receipt #{self.pk}"

    def save(self, **kwargs):
        if not self.receipt_number:
            self.receipt_number = self._generate_receipt_number()
        super().save(**kwargs)

    @staticmethod
    def _generate_receipt_number() -> str:
        from django.utils import timezone

        year = timezone.now().strftime("%Y")
        prefix = f"REC-{year}-"
        last = (
            PaymentReceipt.objects.filter(receipt_number__startswith=prefix)
            .order_by("-receipt_number")
            .values_list("receipt_number", flat=True)
            .first()
        )
        if last:
            try:
                seq = int(last.rsplit("-", 1)[1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f"{prefix}{seq:04d}"


class BankAccount(models.Model):
    """Company bank account for treasury and reconciliation."""

    class AccountType(models.TextChoices):
        CURRENT = "current", "Current"
        SAVINGS = "savings", "Savings"
        DOMICILIARY = "domiciliary", "Domiciliary"
        FIXED_DEPOSIT = "fixed_deposit", "Fixed Deposit"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        CLOSED = "closed", "Closed"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="bank_accounts",
    )
    account_name = models.CharField(max_length=200)
    bank_name = models.CharField(max_length=200)
    account_number = models.CharField(max_length=50)
    account_type = models.CharField(
        max_length=20, choices=AccountType.choices, default=AccountType.CURRENT
    )
    currency = models.CharField(max_length=3, default="NGN")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    opening_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    current_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    gl_account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="bank_accounts",
        help_text="Linked GL account",
    )
    branch = models.CharField(max_length=200, blank=True)
    swift_code = models.CharField(max_length=20, blank=True)
    sort_code = models.CharField(max_length=20, blank=True)
    # Security & configuration
    daily_transfer_limit = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        help_text="Maximum daily outflow for payment runs",
    )
    authorized_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="authorized_bank_accounts",
        blank=True,
        help_text="Users with transfer permissions on this account",
    )
    webhook_url = models.URLField(max_length=500, blank=True, help_text="Real-time balance webhook (Mono, Flutterwave)")
    api_provider = models.CharField(
        max_length=30, blank=True,
        help_text="Integration provider: mono, flutterwave, manual",
    )
    api_key_ref = models.CharField(
        max_length=200, blank=True,
        help_text="Reference to stored API key (do not store key directly)",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["bank_name", "account_name"]
        indexes = [
            models.Index(fields=["organization", "status"], name="fin_ba_org_status_idx"),
        ]

    def __str__(self):
        return f"{self.account_name} — {self.bank_name}"


class BankTransaction(models.Model):
    """Individual bank transaction record for reconciliation."""

    class TransactionType(models.TextChoices):
        CREDIT = "credit", "Credit"
        DEBIT = "debit", "Debit"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CLEARED = "cleared", "Cleared"
        RECONCILED = "reconciled", "Reconciled"
        VOIDED = "voided", "Voided"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="bank_transactions",
    )
    bank_account = models.ForeignKey(
        BankAccount,
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    transaction_date = models.DateField()
    value_date = models.DateField(null=True, blank=True)
    transaction_type = models.CharField(
        max_length=10, choices=TransactionType.choices
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    reference = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    counterparty = models.CharField(max_length=200, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    receipt = models.ForeignKey(
        PaymentReceipt,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="bank_transactions",
    )
    voucher = models.ForeignKey(
        PaymentVoucher,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="bank_transactions",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-transaction_date", "-created_at"]
        indexes = [
            models.Index(fields=["organization", "bank_account", "-transaction_date"], name="fin_bt_org_acct_date_idx"),
            models.Index(fields=["organization", "status"], name="fin_bt_org_status_idx"),
        ]

    def __str__(self):
        return f"{self.transaction_type} {self.amount} — {self.reference or self.pk}"


class BankReconciliation(models.Model):
    """Reconciliation session matching bank statements to internal records."""

    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="bank_reconciliations",
    )
    bank_account = models.ForeignKey(
        BankAccount,
        on_delete=models.CASCADE,
        related_name="reconciliations",
    )
    period_start = models.DateField()
    period_end = models.DateField()
    statement_balance = models.DecimalField(max_digits=15, decimal_places=2)
    book_balance = models.DecimalField(max_digits=15, decimal_places=2)
    difference = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    reconciled_count = models.IntegerField(default=0)
    unreconciled_count = models.IntegerField(default=0)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.IN_PROGRESS
    )
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="completed_reconciliations",
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="created_reconciliations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-period_end"]
        indexes = [
            models.Index(fields=["organization", "bank_account", "-period_end"], name="fin_br_org_acct_period_idx"),
        ]

    def __str__(self):
        return f"Reconciliation {self.bank_account} ({self.period_start} — {self.period_end})"


# ---------------------------------------------------------------------------
# Payroll → General Ledger bridge
# ---------------------------------------------------------------------------


class PayrollGLLineKind(models.TextChoices):
    GROSS_SALARY = "gross_salary", "Gross Salary Expense"
    EMPLOYEE_DEDUCTIONS = "employee_deductions", "Employee Deductions Payable"
    NET_PAYABLE = "net_payable", "Net Salary Payable"


class PayrollGLMapping(models.Model):
    """Per-org mapping between a payroll line kind and a GL Account."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="payroll_gl_mappings",
    )
    line_kind = models.CharField(max_length=32, choices=PayrollGLLineKind.choices)
    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="payroll_gl_mappings",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("organization", "line_kind")]
        ordering = ["line_kind"]

    def __str__(self):
        return f"{self.line_kind} → {self.account.code}"

    def clean(self):
        # account must belong to the same organization
        if self.account_id and self.organization_id and self.account.organization_id != self.organization_id:
            raise ValidationError("Account must belong to the same organization.")


class PayrollGLPosting(models.Model):
    """Links a PayrollRun to its posted JournalEntry."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        POSTED = "posted", "Posted"
        REVERSED = "reversed", "Reversed"
        FAILED = "failed", "Failed"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="payroll_gl_postings",
    )
    payroll_run = models.OneToOneField(
        "hr.PayrollRun",
        on_delete=models.CASCADE,
        related_name="gl_posting",
    )
    journal_entry = models.ForeignKey(
        JournalEntry,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payroll_postings",
    )
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    posted_at = models.DateTimeField(null=True, blank=True)
    posted_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posted_payroll_gl_postings",
    )
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-posted_at", "-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"], name="fin_pgp_org_status_idx"),
        ]

    def __str__(self):
        return f"GL posting for run #{self.payroll_run_id} ({self.status})"
