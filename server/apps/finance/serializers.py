from decimal import Decimal

from django.db.models import Sum
from rest_framework import serializers

from apps.projects.models import Project

from .models import (
    Account,
    BankAccount,
    BankReconciliation,
    BankTransaction,
    Bill,
    BillLineItem,
    BillPayment,
    Budget,
    BudgetLineItem,
    Customer,
    DistributionLineItem,
    Investor,
    Invoice,
    InvoiceLineItem,
    InvoicePayment,
    JournalEntry,
    JournalLine,
    LedgerEntry,
    PaymentInstallment,
    PaymentPlan,
    PaymentReceipt,
    PaymentRun,
    PaymentVoucher,
    PayrollGLMapping,
    PayrollGLPosting,
    ProjectInvestor,
    ReforecastLineItem,
    ReforecastSuggestion,
    SPVEntity,
    WaterfallDistribution,
)

# --- Bill serializers ---

class BillLineItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillLineItem
        fields = "__all__"
        read_only_fields = ("id", "bill", "amount")


class BillPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillPayment
        fields = "__all__"
        read_only_fields = ("id", "bill", "created_at")


class BillListSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)
    property_name = serializers.CharField(source="property.name", read_only=True, default=None)
    paid_amount = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    balance_due = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    days_overdue = serializers.IntegerField(read_only=True)

    class Meta:
        model = Bill
        fields = [
            "id", "bill_number", "vendor", "vendor_name",
            "property", "property_name", "purchase_order", "status",
            "issue_date", "due_date", "total_amount",
            "paid_amount", "balance_due", "is_overdue", "days_overdue",
            "created_at", "updated_at",
        ]


class BillDetailSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)
    property_name = serializers.CharField(source="property.name", read_only=True, default=None)
    line_items = BillLineItemSerializer(many=True, read_only=True)
    payments = BillPaymentSerializer(many=True, read_only=True)
    paid_amount = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    balance_due = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    days_overdue = serializers.IntegerField(read_only=True)

    class Meta:
        model = Bill
        fields = "__all__"
        read_only_fields = ("id", "subtotal", "total_amount", "created_at", "updated_at")


class BillWriteSerializer(serializers.ModelSerializer):
    bill_number = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Bill
        fields = [
            "vendor", "property", "purchase_order", "bill_number", "status",
            "issue_date", "due_date", "tax_amount", "notes",
        ]


# --- Customer serializers ---

class CustomerListSerializer(serializers.ModelSerializer):
    invoice_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Customer
        fields = [
            "id", "name", "contact_person", "email", "phone",
            "is_active", "created_at", "updated_at", "invoice_count",
        ]


class CustomerDetailSerializer(serializers.ModelSerializer):
    invoice_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Customer
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class CustomerWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = [
            "name", "contact_person", "email", "phone",
            "address", "tax_id", "notes", "is_active",
        ]


# --- Invoice serializers ---

class InvoiceLineItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceLineItem
        fields = "__all__"
        read_only_fields = ("id", "invoice", "amount")


class InvoicePaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoicePayment
        fields = "__all__"
        read_only_fields = ("id", "invoice", "created_at")


class InvoiceListSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    property_name = serializers.CharField(source="property.name", read_only=True, default=None)
    paid_amount = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    balance_due = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    days_overdue = serializers.IntegerField(read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id", "invoice_number", "customer", "customer_name",
            "property", "property_name", "status",
            "issue_date", "due_date", "total_amount",
            "paid_amount", "balance_due", "is_overdue", "days_overdue",
            "created_at", "updated_at",
        ]


class InvoiceDetailSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    property_name = serializers.CharField(source="property.name", read_only=True, default=None)
    line_items = InvoiceLineItemSerializer(many=True, read_only=True)
    payments = InvoicePaymentSerializer(many=True, read_only=True)
    paid_amount = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    balance_due = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    days_overdue = serializers.IntegerField(read_only=True)

    class Meta:
        model = Invoice
        fields = "__all__"
        read_only_fields = ("id", "subtotal", "total_amount", "created_at", "updated_at")


class InvoiceWriteSerializer(serializers.ModelSerializer):
    invoice_number = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Invoice
        fields = [
            "customer", "property", "invoice_number", "status",
            "issue_date", "due_date", "tax_amount", "notes",
        ]


# --- Account serializers (Chart of Accounts) ---


class AccountListSerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(
        source="parent.name", read_only=True, default=None
    )

    class Meta:
        model = Account
        fields = [
            "id", "code", "name", "account_type", "sub_type",
            "parent", "parent_name", "is_active", "is_system",
            "created_at", "updated_at",
        ]


class AccountDetailSerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(
        source="parent.name", read_only=True, default=None
    )

    class Meta:
        model = Account
        fields = "__all__"
        read_only_fields = ("id", "organization", "created_at", "updated_at")


class AccountWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = [
            "code", "name", "account_type", "sub_type",
            "parent", "description", "is_active",
        ]


# --- Journal & Ledger serializers ---


class JournalLineSerializer(serializers.ModelSerializer):
    account_code = serializers.CharField(source="account.code", read_only=True)
    account_name = serializers.CharField(source="account.name", read_only=True)
    department_name = serializers.CharField(
        source="department.name", read_only=True, default=None
    )
    cost_center_name = serializers.CharField(
        source="cost_center.name", read_only=True, default=None
    )

    class Meta:
        model = JournalLine
        fields = [
            "id", "journal", "line_number",
            "account", "account_code", "account_name",
            "debit_amount", "credit_amount",
            "memo",
            "department", "department_name",
            "cost_center", "cost_center_name",
        ]
        read_only_fields = ("id", "journal", "line_number")

    def validate(self, data):
        debit = data.get("debit_amount", Decimal("0"))
        credit = data.get("credit_amount", Decimal("0"))

        if debit < 0 or credit < 0:
            raise serializers.ValidationError(
                "Debit and credit cannot be negative."
            )
        if debit > 0 and credit > 0:
            raise serializers.ValidationError(
                "A line cannot have both debit and credit values."
            )
        if debit <= 0 and credit <= 0:
            raise serializers.ValidationError(
                "A line must include either debit or credit value."
            )
        return data


class JournalEntryListSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True, default=None
    )
    posted_by_name = serializers.CharField(
        source="posted_by.get_full_name", read_only=True, default=None
    )
    line_count = serializers.SerializerMethodField()
    total_debit = serializers.SerializerMethodField()
    total_credit = serializers.SerializerMethodField()

    class Meta:
        model = JournalEntry
        fields = [
            "id", "journal_number", "entry_date", "description", "reference",
            "source_type", "source_id", "status",
            "line_count", "total_debit", "total_credit",
            "posted_at", "posted_by", "posted_by_name",
            "created_by", "created_by_name",
            "created_at", "updated_at",
        ]

    def _totals(self, obj):
        if not hasattr(obj, "_journal_totals"):
            agg = obj.lines.aggregate(
                debit_total=Sum("debit_amount"),
                credit_total=Sum("credit_amount"),
            )
            obj._journal_totals = (
                agg["debit_total"] or Decimal("0.00"),
                agg["credit_total"] or Decimal("0.00"),
            )
        return obj._journal_totals

    def get_line_count(self, obj):
        return obj.lines.count()

    def get_total_debit(self, obj):
        debit, _ = self._totals(obj)
        return str(debit)

    def get_total_credit(self, obj):
        _, credit = self._totals(obj)
        return str(credit)


class JournalEntryDetailSerializer(JournalEntryListSerializer):
    lines = JournalLineSerializer(many=True, read_only=True)

    class Meta(JournalEntryListSerializer.Meta):
        fields = JournalEntryListSerializer.Meta.fields + [
            "organization", "reversed_entry", "is_reversal", "lines",
        ]


class JournalEntryWriteSerializer(serializers.ModelSerializer):
    lines = JournalLineSerializer(many=True, required=False)

    class Meta:
        model = JournalEntry
        fields = [
            "entry_date", "description", "reference",
            "source_type", "source_id", "lines",
        ]

    def _validate_balanced_lines(self, lines):
        if len(lines) < 2:
            raise serializers.ValidationError(
                {"lines": "Journal entry must have at least two lines."}
            )

        debit_total = Decimal("0.00")
        credit_total = Decimal("0.00")
        for line in lines:
            debit_total += line.get("debit_amount", Decimal("0.00"))
            credit_total += line.get("credit_amount", Decimal("0.00"))

        if debit_total <= 0 or credit_total <= 0:
            raise serializers.ValidationError(
                {"lines": "Journal entry must contain both debit and credit values."}
            )

        if debit_total != credit_total:
            raise serializers.ValidationError(
                {"lines": f"Journal is not balanced: debit {debit_total} != credit {credit_total}."}
            )

    def validate(self, data):
        lines = data.get("lines")
        if self.instance is None:
            if not lines:
                raise serializers.ValidationError(
                    {"lines": "Journal entry must include at least two lines."}
                )
            self._validate_balanced_lines(lines)
        elif lines is not None:
            self._validate_balanced_lines(lines)
        return data

    def create(self, validated_data):
        lines_data = validated_data.pop("lines", [])
        journal = JournalEntry.objects.create(**validated_data)
        for idx, line_data in enumerate(lines_data, start=1):
            JournalLine.objects.create(
                journal=journal,
                line_number=line_data.get("line_number") or idx,
                account=line_data["account"],
                debit_amount=line_data.get("debit_amount", Decimal("0.00")),
                credit_amount=line_data.get("credit_amount", Decimal("0.00")),
                memo=line_data.get("memo", ""),
                department=line_data.get("department"),
                cost_center=line_data.get("cost_center"),
            )
        return journal

    def update(self, instance, validated_data):
        if instance.status != JournalEntry.Status.DRAFT:
            raise serializers.ValidationError(
                "Only draft journal entries can be modified."
            )

        lines_data = validated_data.pop("lines", None)
        for field in ["entry_date", "description", "reference", "source_type", "source_id"]:
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        instance.save()

        if lines_data is not None:
            instance.lines.all().delete()
            for idx, line_data in enumerate(lines_data, start=1):
                JournalLine.objects.create(
                    journal=instance,
                    line_number=line_data.get("line_number") or idx,
                    account=line_data["account"],
                    debit_amount=line_data.get("debit_amount", Decimal("0.00")),
                    credit_amount=line_data.get("credit_amount", Decimal("0.00")),
                    memo=line_data.get("memo", ""),
                    department=line_data.get("department"),
                    cost_center=line_data.get("cost_center"),
                )
        return instance


class LedgerEntrySerializer(serializers.ModelSerializer):
    journal_number = serializers.CharField(
        source="journal_entry.journal_number", read_only=True
    )
    account_code = serializers.CharField(source="account.code", read_only=True)
    account_name = serializers.CharField(source="account.name", read_only=True)
    department_name = serializers.CharField(
        source="department.name", read_only=True, default=None
    )
    cost_center_name = serializers.CharField(
        source="cost_center.name", read_only=True, default=None
    )

    class Meta:
        model = LedgerEntry
        fields = [
            "id", "organization",
            "journal_entry", "journal_number",
            "journal_line",
            "account", "account_code", "account_name",
            "entry_date", "debit_amount", "credit_amount",
            "description", "source_type", "source_id",
            "department", "department_name",
            "cost_center", "cost_center_name",
            "posted_at", "created_at",
        ]
        read_only_fields = fields


# --- Budget serializers ---


class BudgetLineItemSerializer(serializers.ModelSerializer):
    account_code = serializers.CharField(source="account.code", read_only=True)
    account_name = serializers.CharField(source="account.name", read_only=True)
    department_name = serializers.CharField(
        source="department.name", read_only=True, default=None
    )
    cost_center_name = serializers.CharField(
        source="cost_center.name", read_only=True, default=None
    )
    actual_spent = serializers.SerializerMethodField()
    pct_used = serializers.SerializerMethodField()

    class Meta:
        model = BudgetLineItem
        fields = [
            "id", "account", "account_code", "account_name",
            "department", "department_name",
            "cost_center", "cost_center_name",
            "budgeted_amount", "actual_spent", "pct_used",
            "notes", "sort_order",
        ]
        read_only_fields = ("id",)

    def get_actual_spent(self, obj):
        from .budget_utils import get_actual_spent
        return str(get_actual_spent(obj))

    def get_pct_used(self, obj):
        from decimal import Decimal

        from .budget_utils import get_actual_spent
        if obj.budgeted_amount <= 0:
            return 0
        actual = get_actual_spent(obj)
        return round(float(actual / obj.budgeted_amount * Decimal("100")), 1)


class BudgetLineItemWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = BudgetLineItem
        fields = [
            "account", "department", "cost_center",
            "budgeted_amount", "notes", "sort_order",
        ]


class BudgetListSerializer(serializers.ModelSerializer):
    total_spent = serializers.SerializerMethodField()
    pct_used = serializers.SerializerMethodField()
    line_item_count = serializers.SerializerMethodField()

    class Meta:
        model = Budget
        fields = [
            "id", "name", "status", "period_type",
            "start_date", "end_date", "total_amount",
            "total_spent", "pct_used", "line_item_count",
            "warning_threshold_pct", "overspend_tolerance_pct",
            "created_at", "updated_at",
        ]

    def _compute_totals(self, obj):
        if not hasattr(obj, "_cached_totals"):
            from decimal import Decimal

            from .budget_utils import get_actual_spent
            total = Decimal("0")
            for bli in obj.line_items.select_related("account"):
                total += get_actual_spent(bli)
            obj._cached_totals = total
        return obj._cached_totals

    def get_total_spent(self, obj):
        return str(self._compute_totals(obj))

    def get_pct_used(self, obj):
        if obj.total_amount <= 0:
            return 0
        return round(float(self._compute_totals(obj) / obj.total_amount * 100), 1)

    def get_line_item_count(self, obj):
        return obj.line_items.count()


class BudgetDetailSerializer(BudgetListSerializer):
    line_items = BudgetLineItemSerializer(many=True, read_only=True)

    class Meta(BudgetListSerializer.Meta):
        fields = BudgetListSerializer.Meta.fields + [
            "notes", "created_by", "line_items",
        ]


class BudgetWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Budget
        fields = [
            "name", "status", "period_type",
            "start_date", "end_date", "total_amount",
            "overspend_tolerance_pct", "warning_threshold_pct", "notes",
        ]


# --- Reforecast serializers ---


class ReforecastLineItemSerializer(serializers.ModelSerializer):
    account_code = serializers.CharField(
        source="budget_line_item.account.code", read_only=True
    )
    account_name = serializers.CharField(
        source="budget_line_item.account.name", read_only=True
    )

    class Meta:
        model = ReforecastLineItem
        fields = [
            "id", "budget_line_item", "account_code", "account_name",
            "current_amount", "suggested_amount", "actual_spent", "delta",
        ]
        read_only_fields = fields


class ReforecastSuggestionSerializer(serializers.ModelSerializer):
    line_items = ReforecastLineItemSerializer(many=True, read_only=True)

    class Meta:
        model = ReforecastSuggestion
        fields = [
            "id", "budget", "status", "reason",
            "generated_at", "reviewed_by", "reviewed_at",
            "line_items",
        ]
        read_only_fields = fields


# --- Investor serializers ---

class InvestorListSerializer(serializers.ModelSerializer):
    investment_count = serializers.IntegerField(read_only=True)
    total_invested = serializers.DecimalField(
        max_digits=15, decimal_places=2, read_only=True
    )

    class Meta:
        model = Investor
        fields = [
            "id", "name", "investor_type", "contact_person", "email", "phone",
            "is_active", "created_at", "updated_at",
            "investment_count", "total_invested",
        ]


class InvestorDetailSerializer(serializers.ModelSerializer):
    investment_count = serializers.IntegerField(read_only=True)
    total_invested = serializers.DecimalField(
        max_digits=15, decimal_places=2, read_only=True
    )

    class Meta:
        model = Investor
        fields = "__all__"
        read_only_fields = ("id", "organization", "created_at", "updated_at")


class InvestorWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Investor
        fields = [
            "id", "name", "investor_type", "contact_person", "email", "phone",
            "address", "tax_id", "entity_name", "registration_number",
            "notes", "is_active",
        ]
        read_only_fields = ("id",)


# --- Project investor (cap table) serializers ---

class ProjectInvestorSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    investor_name = serializers.CharField(source="investor.name", read_only=True)
    unreturned_capital = serializers.DecimalField(
        max_digits=15, decimal_places=2, read_only=True
    )

    class Meta:
        model = ProjectInvestor
        fields = [
            "id", "project", "project_name", "investor", "investor_name", "ownership_percentage",
            "capital_committed", "capital_contributed",
            "total_capital_returned", "total_profit_distributed",
            "unreturned_capital", "custom_profit_split_pct",
            "sort_order", "notes", "created_at", "updated_at",
        ]
        read_only_fields = (
            "id", "total_capital_returned", "total_profit_distributed",
            "created_at", "updated_at",
        )


class ProjectInvestorWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectInvestor
        fields = [
            "project", "investor", "ownership_percentage", "capital_committed",
            "capital_contributed", "custom_profit_split_pct",
            "sort_order", "notes",
        ]

    def validate(self, data):
        # Ensure ownership % is valid
        ownership = data.get("ownership_percentage")
        if ownership is not None and not (0 < ownership <= 100):
            raise serializers.ValidationError(
                "Ownership percentage must be between 0 and 100"
            )
        return data


# --- Waterfall distribution serializers ---

class DistributionLineItemSerializer(serializers.ModelSerializer):
    investor_name = serializers.CharField(
        source="project_investor.investor.name", read_only=True
    )
    ownership_pct = serializers.DecimalField(
        source="project_investor.ownership_percentage",
        max_digits=5, decimal_places=2, read_only=True
    )

    class Meta:
        model = DistributionLineItem
        fields = [
            "id", "project_investor", "investor_name", "ownership_pct",
            "tier1_capital_amount", "tier2_profit_amount", "total_amount",
            "capital_returned_to_date", "profit_distributed_to_date",
        ]
        read_only_fields = fields


class WaterfallDistributionListSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    investor_count = serializers.SerializerMethodField()

    class Meta:
        model = WaterfallDistribution
        fields = [
            "id", "distribution_number", "project", "project_name",
            "status", "distribution_date", "total_amount",
            "tier1_capital_returned", "tier2_profit_split", "sponsor_amount",
            "investor_count", "created_at", "updated_at",
        ]

    def get_investor_count(self, obj):
        return obj.line_items.count()


class WaterfallDistributionDetailSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    line_items = DistributionLineItemSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True, default=None
    )
    approved_by_name = serializers.CharField(
        source="approved_by.get_full_name", read_only=True, default=None
    )

    class Meta:
        model = WaterfallDistribution
        fields = "__all__"
        read_only_fields = (
            "id", "distribution_number", "tier1_capital_returned",
            "tier2_profit_split", "sponsor_amount", "approved_at",
            "created_at", "updated_at",
        )


class WaterfallDistributionCreateSerializer(serializers.Serializer):
    """Serializer for creating/calculating a distribution."""

    project = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all()
    )
    distribution_date = serializers.DateField()
    total_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate_total_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Distribution amount must be positive")
        return value


# ---------------------------------------------------------------------------
# SPV Entity serializers
# ---------------------------------------------------------------------------


class SPVEntityListSerializer(serializers.ModelSerializer):
    subsidiary_count = serializers.SerializerMethodField()
    project_count = serializers.SerializerMethodField()

    class Meta:
        model = SPVEntity
        fields = [
            "id", "name", "entity_type", "status", "registration_number",
            "jurisdiction", "authorized_capital", "paid_up_capital",
            "is_active", "subsidiary_count", "project_count",
            "created_at", "updated_at",
        ]

    def get_subsidiary_count(self, obj):
        return obj.subsidiaries.count()

    def get_project_count(self, obj):
        return obj.projects.count()


class SPVEntityDetailSerializer(serializers.ModelSerializer):
    parent_entity_name = serializers.CharField(
        source="parent_entity.name", read_only=True, default=None
    )

    class Meta:
        model = SPVEntity
        fields = "__all__"
        read_only_fields = ("id", "organization", "created_at", "updated_at")


class SPVEntityWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = SPVEntity
        fields = "__all__"
        read_only_fields = ("id", "organization", "created_at", "updated_at")


# ---------------------------------------------------------------------------
# Payment Plan serializers
# ---------------------------------------------------------------------------


class PaymentInstallmentSerializer(serializers.ModelSerializer):
    balance_due = serializers.DecimalField(
        max_digits=15, decimal_places=2, read_only=True
    )
    is_overdue = serializers.BooleanField(read_only=True)
    milestone_name = serializers.CharField(
        source="milestone.name", read_only=True, default=None
    )

    class Meta:
        model = PaymentInstallment
        fields = [
            "id", "installment_number", "label", "amount", "paid_amount",
            "balance_due", "scheduled_date", "due_date", "paid_date",
            "milestone", "milestone_name", "percentage_of_total",
            "status", "payment_method", "reference_number", "notes",
            "is_overdue", "created_at", "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")


class PaymentInstallmentWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentInstallment
        fields = [
            "installment_number", "label", "amount", "paid_amount",
            "scheduled_date", "due_date", "paid_date", "milestone",
            "percentage_of_total", "status", "payment_method",
            "reference_number", "notes",
        ]


class PaymentPlanListSerializer(serializers.ModelSerializer):
    paid_amount = serializers.DecimalField(
        max_digits=15, decimal_places=2, read_only=True
    )
    balance_due = serializers.DecimalField(
        max_digits=15, decimal_places=2, read_only=True
    )
    installment_count = serializers.IntegerField(read_only=True)
    customer_name = serializers.CharField(
        source="customer.name", read_only=True, default=None
    )
    vendor_name = serializers.CharField(
        source="vendor.name", read_only=True, default=None
    )
    investor_name = serializers.CharField(
        source="investor.name", read_only=True, default=None
    )
    project_name = serializers.CharField(
        source="project.name", read_only=True, default=None
    )
    spv_name = serializers.CharField(
        source="spv_entity.name", read_only=True, default=None
    )

    class Meta:
        model = PaymentPlan
        fields = [
            "id", "plan_number", "title", "status", "plan_type",
            "direction", "frequency", "total_amount", "currency",
            "paid_amount", "balance_due", "installment_count",
            "start_date", "end_date", "number_of_installments",
            "customer", "customer_name", "vendor", "vendor_name",
            "investor", "investor_name", "project", "project_name",
            "spv_entity", "spv_name",
            "created_at", "updated_at",
        ]


class PaymentPlanDetailSerializer(serializers.ModelSerializer):
    installments = PaymentInstallmentSerializer(many=True, read_only=True)
    paid_amount = serializers.DecimalField(
        max_digits=15, decimal_places=2, read_only=True
    )
    balance_due = serializers.DecimalField(
        max_digits=15, decimal_places=2, read_only=True
    )
    installment_count = serializers.IntegerField(read_only=True)
    customer_name = serializers.CharField(
        source="customer.name", read_only=True, default=None
    )
    vendor_name = serializers.CharField(
        source="vendor.name", read_only=True, default=None
    )
    investor_name = serializers.CharField(
        source="investor.name", read_only=True, default=None
    )
    project_name = serializers.CharField(
        source="project.name", read_only=True, default=None
    )
    spv_name = serializers.CharField(
        source="spv_entity.name", read_only=True, default=None
    )
    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True, default=None
    )
    approved_by_name = serializers.CharField(
        source="approved_by.get_full_name", read_only=True, default=None
    )

    class Meta:
        model = PaymentPlan
        fields = "__all__"
        read_only_fields = (
            "id", "plan_number", "organization", "approved_at",
            "created_at", "updated_at",
        )


class PaymentPlanWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentPlan
        fields = "__all__"
        read_only_fields = (
            "id", "plan_number", "organization", "approved_by",
            "approved_at", "created_by", "created_at", "updated_at",
        )

    def validate_total_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Total amount must be positive.")
        return value


# --- Payment Voucher serializers ---


class PaymentVoucherListSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)
    bill_number = serializers.CharField(source="bill.bill_number", read_only=True, default=None)
    property_id = serializers.IntegerField(source="bill.property_id", read_only=True, default=None)
    property_name = serializers.CharField(source="bill.property.name", read_only=True, default=None)

    class Meta:
        model = PaymentVoucher
        fields = [
            "id", "voucher_number", "vendor", "vendor_name",
            "bill", "bill_number", "property_id", "property_name",
            "status", "priority", "issue_date",
            "amount", "payment_method", "created_at",
        ]


class _VoucherVendorSerializer(serializers.ModelSerializer):
    """Inline vendor snapshot for voucher detail view."""

    class Meta:
        from apps.procurement.models import Vendor
        model = Vendor
        fields = [
            "id", "name", "contact_person", "email", "phone",
            "bank_name", "bank_account_number", "bank_branch",
        ]


class PaymentVoucherDetailSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)
    bill_number = serializers.CharField(source="bill.bill_number", read_only=True, default=None)
    vendor_detail = _VoucherVendorSerializer(source="vendor", read_only=True)
    approved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = PaymentVoucher
        fields = "__all__"
        read_only_fields = ("id", "organization", "approved_by", "approved_at", "paid_at", "created_at", "updated_at")

    def get_approved_by_name(self, obj):
        if obj.approved_by:
            return obj.approved_by.get_full_name() or obj.approved_by.email
        return None


class PaymentVoucherWriteSerializer(serializers.ModelSerializer):
    voucher_number = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = PaymentVoucher
        fields = [
            "vendor", "bill", "voucher_number", "status", "priority",
            "issue_date", "amount", "payment_method",
            "description", "notes",
        ]


# --- Payment Run serializers ---


class _RunVoucherSummarySerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)
    bank_name = serializers.CharField(source="vendor.bank_name", read_only=True, default="")
    bank_account_number = serializers.CharField(source="vendor.bank_account_number", read_only=True, default="")

    class Meta:
        model = PaymentVoucher
        fields = [
            "id", "voucher_number", "vendor_name", "amount", "status",
            "priority", "bank_name", "bank_account_number",
        ]


class PaymentRunListSerializer(serializers.ModelSerializer):
    total_value = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True, source="total_value_ann")
    payment_count = serializers.IntegerField(read_only=True, source="payment_count_ann")
    funding_account_name = serializers.CharField(
        source="funding_account.name", read_only=True, default=None
    )
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = PaymentRun
        fields = [
            "id", "batch_id", "status", "total_value", "payment_count",
            "funding_account", "funding_account_name", "funding_account_label",
            "scheduled_date", "executed_at", "created_at", "created_by_name",
        ]

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.email
        return None


class PaymentRunDetailSerializer(serializers.ModelSerializer):
    total_value = serializers.SerializerMethodField()
    payment_count = serializers.SerializerMethodField()
    funding_account_name = serializers.CharField(
        source="funding_account.name", read_only=True, default=None
    )
    voucher_items = _RunVoucherSummarySerializer(source="vouchers", many=True, read_only=True)
    created_by_name = serializers.SerializerMethodField()
    executed_by_name = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = PaymentRun
        fields = "__all__"
        read_only_fields = (
            "id", "organization", "executed_at", "executed_by",
            "approved_by", "approved_at", "funding_balance",
            "created_by", "created_at", "updated_at",
        )

    def get_total_value(self, obj):
        return str(obj.total_value)

    def get_payment_count(self, obj):
        return obj.payment_count

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.email
        return None

    def get_executed_by_name(self, obj):
        if obj.executed_by:
            return obj.executed_by.get_full_name() or obj.executed_by.email
        return None

    def get_approved_by_name(self, obj):
        if obj.approved_by:
            return obj.approved_by.get_full_name() or obj.approved_by.email
        return None


class PaymentRunWriteSerializer(serializers.ModelSerializer):
    batch_id = serializers.CharField(required=False, allow_blank=True)
    voucher_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False, default=list
    )

    class Meta:
        model = PaymentRun
        fields = [
            "batch_id", "status", "funding_account",
            "funding_account_label", "scheduled_date", "notes",
            "voucher_ids",
        ]

    def create(self, validated_data):
        voucher_ids = validated_data.pop("voucher_ids", [])
        run = super().create(validated_data)
        if voucher_ids:
            org = run.organization
            vouchers = PaymentVoucher.objects.filter(
                id__in=voucher_ids, organization=org, status="approved"
            )
            run.vouchers.set(vouchers)
        return run

    def update(self, instance, validated_data):
        voucher_ids = validated_data.pop("voucher_ids", None)
        instance = super().update(instance, validated_data)
        if voucher_ids is not None:
            org = instance.organization
            vouchers = PaymentVoucher.objects.filter(
                id__in=voucher_ids, organization=org, status="approved"
            )
            instance.vouchers.set(vouchers)
        return instance


# --- Payment Receipt serializers ---


class PaymentReceiptListSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.name", read_only=True, default=None)
    voucher_number = serializers.CharField(source="voucher.voucher_number", read_only=True, default=None)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = PaymentReceipt
        fields = [
            "id", "receipt_number", "transaction_reference", "status",
            "payment_date", "amount", "payment_method",
            "vendor", "vendor_name", "voucher", "voucher_number",
            "created_at", "created_by_name",
        ]

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.email
        return None


class _ReceiptAllocationItemSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.name", read_only=True, default="")
    property_name = serializers.CharField(source="bill.property.name", read_only=True, default=None)

    class Meta:
        model = PaymentVoucher
        fields = [
            "id", "voucher_number", "vendor_name", "property_name",
            "description", "amount",
        ]


class PaymentReceiptDetailSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.name", read_only=True, default=None)
    voucher_number = serializers.CharField(source="voucher.voucher_number", read_only=True, default=None)
    payment_run_batch_id = serializers.CharField(source="payment_run.batch_id", read_only=True, default=None)
    created_by_name = serializers.SerializerMethodField()
    allocation_items = serializers.SerializerMethodField()

    class Meta:
        model = PaymentReceipt
        fields = "__all__"
        read_only_fields = ("id", "organization", "created_by", "created_at", "updated_at")

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.email
        return None

    def get_allocation_items(self, obj):
        qs = obj.vouchers.select_related("vendor", "bill", "bill__property").all()
        if not qs.exists() and obj.voucher_id:
            qs = PaymentVoucher.objects.filter(pk=obj.voucher_id).select_related(
                "vendor", "bill", "bill__property"
            )
        return _ReceiptAllocationItemSerializer(qs, many=True).data


class PaymentReceiptWriteSerializer(serializers.ModelSerializer):
    receipt_number = serializers.CharField(required=False, allow_blank=True)
    voucher_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False, default=list
    )

    class Meta:
        model = PaymentReceipt
        fields = [
            "receipt_number", "transaction_reference", "status",
            "payment_date", "amount", "payment_method",
            "vendor", "voucher", "payment_run",
            "payer_account", "payee_account",
            "description", "notes", "voucher_ids",
        ]

    def create(self, validated_data):
        voucher_ids = validated_data.pop("voucher_ids", [])
        receipt = super().create(validated_data)
        if voucher_ids:
            org = receipt.organization
            vouchers = PaymentVoucher.objects.filter(id__in=voucher_ids, organization=org)
            receipt.vouchers.set(vouchers)
        return receipt


# --- Bank Account serializers ---


class BankAccountListSerializer(serializers.ModelSerializer):
    gl_account_name = serializers.CharField(source="gl_account.name", read_only=True, default=None)

    class Meta:
        model = BankAccount
        fields = [
            "id", "account_name", "bank_name", "account_number",
            "account_type", "currency", "status",
            "current_balance", "gl_account", "gl_account_name",
            "branch", "created_at",
        ]


class _AuthorizedUserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.email


class BankAccountDetailSerializer(serializers.ModelSerializer):
    gl_account_name = serializers.CharField(source="gl_account.name", read_only=True, default=None)
    authorized_user_list = serializers.SerializerMethodField()

    class Meta:
        model = BankAccount
        fields = "__all__"
        read_only_fields = ("id", "organization", "created_at", "updated_at")

    def get_authorized_user_list(self, obj):
        users = obj.authorized_users.all()
        return _AuthorizedUserSerializer(users, many=True).data


class BankAccountWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = [
            "account_name", "bank_name", "account_number",
            "account_type", "currency", "status",
            "opening_balance", "current_balance", "gl_account",
            "branch", "swift_code", "sort_code",
            "daily_transfer_limit", "webhook_url", "api_provider", "api_key_ref",
            "notes",
        ]


# --- Bank Transaction serializers ---


class BankTransactionListSerializer(serializers.ModelSerializer):
    bank_account_name = serializers.CharField(source="bank_account.account_name", read_only=True)
    bank_name = serializers.CharField(source="bank_account.bank_name", read_only=True)

    class Meta:
        model = BankTransaction
        fields = [
            "id", "bank_account", "bank_account_name", "bank_name",
            "transaction_date", "transaction_type", "amount",
            "reference", "counterparty", "status", "created_at",
        ]


class BankTransactionDetailSerializer(serializers.ModelSerializer):
    bank_account_name = serializers.CharField(source="bank_account.account_name", read_only=True)
    bank_name = serializers.CharField(source="bank_account.bank_name", read_only=True)
    receipt_number = serializers.CharField(source="receipt.receipt_number", read_only=True, default=None)
    voucher_number = serializers.CharField(source="voucher.voucher_number", read_only=True, default=None)

    class Meta:
        model = BankTransaction
        fields = "__all__"
        read_only_fields = ("id", "organization", "created_at", "updated_at")


class BankTransactionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankTransaction
        fields = [
            "bank_account", "transaction_date", "value_date",
            "transaction_type", "amount", "reference",
            "description", "counterparty", "status",
            "receipt", "voucher", "notes",
        ]


# --- Bank Reconciliation serializers ---


class BankReconciliationListSerializer(serializers.ModelSerializer):
    bank_account_name = serializers.CharField(source="bank_account.account_name", read_only=True)
    bank_name = serializers.CharField(source="bank_account.bank_name", read_only=True)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = BankReconciliation
        fields = [
            "id", "bank_account", "bank_account_name", "bank_name",
            "period_start", "period_end",
            "statement_balance", "book_balance", "difference",
            "reconciled_count", "unreconciled_count",
            "status", "created_at", "created_by_name",
        ]

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.email
        return None


class BankReconciliationDetailSerializer(serializers.ModelSerializer):
    bank_account_name = serializers.CharField(source="bank_account.account_name", read_only=True)
    bank_name = serializers.CharField(source="bank_account.bank_name", read_only=True)
    created_by_name = serializers.SerializerMethodField()
    completed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = BankReconciliation
        fields = "__all__"
        read_only_fields = (
            "id", "organization", "completed_by", "completed_at",
            "created_by", "created_at", "updated_at",
        )

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.email
        return None

    def get_completed_by_name(self, obj):
        if obj.completed_by:
            return obj.completed_by.get_full_name() or obj.completed_by.email
        return None


class BankReconciliationWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankReconciliation
        fields = [
            "bank_account", "period_start", "period_end",
            "statement_balance", "book_balance", "difference",
            "reconciled_count", "unreconciled_count",
            "status", "notes",
        ]


# --- Payroll → GL bridge serializers ---


class PayrollGLMappingSerializer(serializers.ModelSerializer):
    line_kind_display = serializers.SerializerMethodField()
    account_code = serializers.SerializerMethodField()
    account_name = serializers.SerializerMethodField()

    class Meta:
        model = PayrollGLMapping
        fields = [
            "id",
            "line_kind",
            "line_kind_display",
            "account",
            "account_code",
            "account_name",
            "updated_at",
        ]
        read_only_fields = ("id", "updated_at")

    def get_line_kind_display(self, obj):
        return obj.get_line_kind_display()

    def get_account_code(self, obj):
        return obj.account.code if obj.account_id else None

    def get_account_name(self, obj):
        return obj.account.name if obj.account_id else None

    def validate(self, attrs):
        request = self.context.get("request") if hasattr(self, "context") else None
        account = attrs.get("account") or getattr(self.instance, "account", None)
        if request is not None and account is not None:
            user_org = getattr(getattr(request.user, "profile", None), "organization", None)
            if user_org is not None and account.organization_id != user_org.id and not request.user.is_superuser:
                raise serializers.ValidationError(
                    {"account": "Account must belong to your organization."}
                )
        return attrs


class PayrollGLPostingSerializer(serializers.ModelSerializer):
    payroll_run_name = serializers.SerializerMethodField()
    journal_number = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    posted_by_name = serializers.SerializerMethodField()

    class Meta:
        model = PayrollGLPosting
        fields = [
            "id",
            "payroll_run",
            "payroll_run_name",
            "journal_entry",
            "journal_number",
            "status",
            "status_display",
            "posted_at",
            "posted_by",
            "posted_by_name",
            "error_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_payroll_run_name(self, obj):
        return obj.payroll_run.name if obj.payroll_run_id else None

    def get_journal_number(self, obj):
        return obj.journal_entry.journal_number if obj.journal_entry_id else None

    def get_status_display(self, obj):
        return obj.get_status_display()

    def get_posted_by_name(self, obj):
        if obj.posted_by_id is None:
            return None
        return obj.posted_by.get_full_name() or obj.posted_by.email or obj.posted_by.username


class PayrollGLBulkSyncResultSerializer(serializers.Serializer):
    posted = serializers.ListField(child=serializers.IntegerField())
    skipped = serializers.ListField(child=serializers.IntegerField())
    errors = serializers.ListField(child=serializers.DictField())
