from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from apps.admin_mixins import OrgScopedAdminMixin

from .models import (
    Account,
    Bill,
    BillLineItem,
    BillPayment,
    Budget,
    BudgetLineItem,
    CapitalContribution,
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
    PaymentVoucher,
    ProjectAccountMapping,
    ProjectCostCenter,
    ProjectInvestor,
    ProjectLedger,
    ProjectRevenueCenter,
    SPVEntity,
    WaterfallConfig,
    WaterfallDistribution,
)


class BillLineItemInline(TabularInline):
    model = BillLineItem
    extra = 0
    fields = ["description", "quantity", "unit_price", "amount", "sort_order"]
    readonly_fields = ["amount"]


class BillPaymentInline(TabularInline):
    model = BillPayment
    extra = 0
    fields = ["amount", "payment_date", "payment_method", "reference_number", "notes"]


class InvoiceLineItemInline(TabularInline):
    model = InvoiceLineItem
    extra = 0
    fields = ["description", "quantity", "unit_price", "amount", "sort_order"]
    readonly_fields = ["amount"]


class InvoicePaymentInline(TabularInline):
    model = InvoicePayment
    extra = 0
    fields = ["amount", "payment_date", "payment_method", "reference_number", "notes"]


@admin.register(Customer)
class CustomerAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["name", "contact_person", "email", "phone", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name", "contact_person", "email"]


@admin.register(Bill)
class BillAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["bill_number", "vendor", "status", "total_amount", "due_date", "created_at"]
    list_filter = ["status", "vendor"]
    search_fields = ["bill_number", "vendor__name", "notes"]
    inlines = [BillLineItemInline, BillPaymentInline]


@admin.register(Invoice)
class InvoiceAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["invoice_number", "customer", "status", "total_amount", "due_date", "created_at"]
    list_filter = ["status", "customer"]
    search_fields = ["invoice_number", "customer__name", "notes"]
    inlines = [InvoiceLineItemInline, InvoicePaymentInline]


@admin.register(Account)
class AccountAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["code", "name", "organization", "account_type", "sub_type", "is_active", "is_system"]
    list_filter = ["account_type", "sub_type", "is_active", "is_system", "organization"]
    search_fields = ["code", "name"]
    readonly_fields = ["created_at", "updated_at"]


class JournalLineInline(TabularInline):
    model = JournalLine
    extra = 0
    fields = [
        "line_number", "account", "debit_amount", "credit_amount",
        "memo", "department", "cost_center",
    ]
    ordering = ["line_number"]


@admin.register(JournalEntry)
class JournalEntryAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "journal_number", "organization", "entry_date", "status",
        "source_type", "posted_at", "created_at",
    ]
    list_filter = ["organization", "status", "source_type", "entry_date"]
    search_fields = ["journal_number", "description", "reference"]
    readonly_fields = ["journal_number", "posted_at", "created_at", "updated_at"]
    inlines = [JournalLineInline]


@admin.register(LedgerEntry)
class LedgerEntryAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "entry_date", "organization", "account", "journal_entry",
        "debit_amount", "credit_amount", "posted_at",
    ]
    list_filter = ["organization", "account", "entry_date", "source_type"]
    search_fields = ["journal_entry__journal_number", "account__code", "account__name", "description"]
    readonly_fields = [
        "organization", "journal_entry", "journal_line", "account",
        "entry_date", "debit_amount", "credit_amount",
        "description", "source_type", "source_id",
        "department", "cost_center", "posted_at", "created_at",
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class BudgetLineItemInline(TabularInline):
    model = BudgetLineItem
    extra = 0
    fields = ["account", "department", "cost_center", "budgeted_amount", "notes", "sort_order"]


@admin.register(Budget)
class BudgetAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["name", "organization", "status", "period_type", "start_date", "end_date", "total_amount"]
    list_filter = ["status", "period_type", "organization"]
    search_fields = ["name"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [BudgetLineItemInline]


# --- Investor & Waterfall Admin ---

@admin.register(Investor)
class InvestorAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["name", "investor_type", "contact_person", "email", "is_active", "created_at"]
    list_filter = ["investor_type", "is_active", "organization"]
    search_fields = ["name", "contact_person", "email"]
    readonly_fields = ["created_at", "updated_at"]


class CapitalContributionInline(TabularInline):
    model = CapitalContribution
    extra = 0
    fields = ["amount", "contribution_date", "payment_method", "reference_number", "notes"]


@admin.register(ProjectInvestor)
class ProjectInvestorAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["project", "investor", "ownership_percentage", "capital_contributed", "unreturned_capital"]
    list_filter = ["project", "investor"]
    search_fields = ["project__name", "investor__name"]
    readonly_fields = ["total_capital_returned", "total_profit_distributed", "created_at", "updated_at"]
    inlines = [CapitalContributionInline]


@admin.register(ProjectLedger)
class ProjectLedgerAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["code", "name", "organization", "project", "is_active", "created_at"]
    list_filter = ["organization", "is_active"]
    search_fields = ["code", "name", "project__name"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(ProjectCostCenter)
class ProjectCostCenterAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["code", "name", "organization", "project", "is_active", "created_at"]
    list_filter = ["organization", "is_active"]
    search_fields = ["code", "name", "project__name"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(ProjectRevenueCenter)
class ProjectRevenueCenterAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["code", "name", "organization", "project", "is_active", "created_at"]
    list_filter = ["organization", "is_active"]
    search_fields = ["code", "name", "project__name"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(ProjectAccountMapping)
class ProjectAccountMappingAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "project",
        "organization",
        "construction_cost_account",
        "capex_account",
        "development_expense_account",
        "sales_revenue_account",
        "created_at",
    ]
    list_filter = ["organization"]
    search_fields = [
        "project__name",
        "construction_cost_account__code",
        "capex_account__code",
        "development_expense_account__code",
        "sales_revenue_account__code",
    ]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(WaterfallConfig)
class WaterfallConfigAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["project", "investor_profit_split_pct", "sponsor_profit_split_pct"]
    readonly_fields = ["created_at", "updated_at"]


class DistributionLineItemInline(TabularInline):
    model = DistributionLineItem
    extra = 0
    fields = ["project_investor", "tier1_capital_amount", "tier2_profit_amount", "total_amount"]
    readonly_fields = ["tier1_capital_amount", "tier2_profit_amount", "total_amount", "capital_returned_to_date", "profit_distributed_to_date"]


@admin.register(WaterfallDistribution)
class WaterfallDistributionAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["distribution_number", "project", "status", "distribution_date", "total_amount", "created_at"]
    list_filter = ["status", "project"]
    search_fields = ["distribution_number", "project__name", "notes"]
    readonly_fields = ["distribution_number", "tier1_capital_returned", "tier2_profit_split", "sponsor_amount", "approved_at", "created_at", "updated_at"]
    inlines = [DistributionLineItemInline]


# --- SPV & Payment Plans ---

@admin.register(SPVEntity)
class SPVEntityAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["name", "organization", "entity_type", "status", "jurisdiction", "is_active", "created_at"]
    list_filter = ["entity_type", "status", "is_active", "organization"]
    search_fields = ["name", "registration_number", "jurisdiction"]
    readonly_fields = ["created_at", "updated_at"]


class PaymentInstallmentInline(TabularInline):
    model = PaymentInstallment
    extra = 0
    fields = ["installment_number", "label", "amount", "paid_amount", "scheduled_date", "due_date", "status"]
    readonly_fields = ["paid_amount"]


@admin.register(PaymentPlan)
class PaymentPlanAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["plan_number", "title", "organization", "status", "direction", "total_amount", "start_date", "created_at"]
    list_filter = ["status", "direction", "plan_type", "organization"]
    search_fields = ["plan_number", "title"]
    readonly_fields = ["plan_number", "approved_at", "created_at", "updated_at"]
    inlines = [PaymentInstallmentInline]


@admin.register(PaymentVoucher)
class PaymentVoucherAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["voucher_number", "vendor", "status", "amount", "issue_date", "payment_method", "created_at"]
    list_filter = ["status", "payment_method", "vendor"]
    search_fields = ["voucher_number", "vendor__name", "description", "notes"]
    readonly_fields = ["voucher_number", "approved_by", "approved_at", "paid_at", "created_at", "updated_at"]
