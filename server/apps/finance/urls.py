from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AccountViewSet,
    AgingReportView,
    BankAccountViewSet,
    BankLiquidityView,
    BankReconciliationViewSet,
    BankTransactionAutoMatchView,
    BankTransactionLinkView,
    BankTransactionMatchView,
    BankTransactionSplitLinkView,
    BankTransactionSummaryView,
    BankTransactionViewSet,
    BillLineItemViewSet,
    BillPaymentViewSet,
    BillViewSet,
    BudgetLineItemViewSet,
    BudgetOverviewView,
    BudgetViewSet,
    CustomerViewSet,
    FinanceCashFlowView,
    FinanceOverviewView,
    FinanceTransactionsView,
    GeneralLedgerView,
    InvestorViewSet,
    InvoiceLineItemViewSet,
    InvoicePaymentViewSet,
    InvoiceViewSet,
    JournalEntryViewSet,
    PaymentInstallmentViewSet,
    PaymentPlanViewSet,
    PaymentReceiptViewSet,
    PaymentRunViewSet,
    PaymentVoucherViewSet,
    PayrollGLMappingViewSet,
    PayrollGLPostingViewSet,
    ProjectInvestorViewSet,
    ReconciliationOverviewView,
    ReforecastActionView,
    SPVEntityViewSet,
    TrialBalanceView,
    WaterfallDistributionViewSet,
)

customer_router = DefaultRouter()
customer_router.register(r"", CustomerViewSet, basename="customer")

bill_router = DefaultRouter()
bill_router.register(r"", BillViewSet, basename="bill")

bill_line_item_router = DefaultRouter()
bill_line_item_router.register(r"", BillLineItemViewSet, basename="bill-line-item")

bill_payment_router = DefaultRouter()
bill_payment_router.register(r"", BillPaymentViewSet, basename="bill-payment")

invoice_router = DefaultRouter()
invoice_router.register(r"", InvoiceViewSet, basename="invoice")

invoice_line_item_router = DefaultRouter()
invoice_line_item_router.register(r"", InvoiceLineItemViewSet, basename="invoice-line-item")

invoice_payment_router = DefaultRouter()
invoice_payment_router.register(r"", InvoicePaymentViewSet, basename="invoice-payment")

account_router = DefaultRouter()
account_router.register(r"", AccountViewSet, basename="account")

journal_router = DefaultRouter()
journal_router.register(r"", JournalEntryViewSet, basename="journal")

budget_router = DefaultRouter()
budget_router.register(r"", BudgetViewSet, basename="budget")

budget_line_item_router = DefaultRouter()
budget_line_item_router.register(r"", BudgetLineItemViewSet, basename="budget-line-item")

investor_router = DefaultRouter()
investor_router.register(r"", InvestorViewSet, basename="investor")

project_investor_router = DefaultRouter()
project_investor_router.register(r"", ProjectInvestorViewSet, basename="project-investor")

distribution_router = DefaultRouter()
distribution_router.register(r"", WaterfallDistributionViewSet, basename="distribution")

spv_router = DefaultRouter()
spv_router.register(r"", SPVEntityViewSet, basename="spv-entity")

payment_plan_router = DefaultRouter()
payment_plan_router.register(r"", PaymentPlanViewSet, basename="payment-plan")

installment_router = DefaultRouter()
installment_router.register(r"", PaymentInstallmentViewSet, basename="payment-installment")

voucher_router = DefaultRouter()
voucher_router.register(r"", PaymentVoucherViewSet, basename="payment-voucher")

payment_run_router = DefaultRouter()
payment_run_router.register(r"", PaymentRunViewSet, basename="payment-run")

receipt_router = DefaultRouter()
receipt_router.register(r"", PaymentReceiptViewSet, basename="payment-receipt")

bank_account_router = DefaultRouter()
bank_account_router.register(r"", BankAccountViewSet, basename="bank-account")

bank_transaction_router = DefaultRouter()
bank_transaction_router.register(r"", BankTransactionViewSet, basename="bank-transaction")

bank_reconciliation_router = DefaultRouter()
bank_reconciliation_router.register(r"", BankReconciliationViewSet, basename="bank-reconciliation")

payroll_gl_mapping_router = DefaultRouter()
payroll_gl_mapping_router.register(r"", PayrollGLMappingViewSet, basename="payroll-gl-mapping")

payroll_gl_posting_router = DefaultRouter()
payroll_gl_posting_router.register(r"", PayrollGLPostingViewSet, basename="payroll-gl-posting")

urlpatterns = [
    path("overview/", FinanceOverviewView.as_view(), name="finance-overview"),
    path("cash-flow/", FinanceCashFlowView.as_view(), name="finance-cash-flow"),
    path("transactions/", FinanceTransactionsView.as_view(), name="finance-transactions"),
    path("accounts/", include(account_router.urls)),
    path("journals/", include(journal_router.urls)),
    path("customers/", include(customer_router.urls)),
    path("bills/", include(bill_router.urls)),
    path("bills/<int:bill_pk>/line-items/", include(bill_line_item_router.urls)),
    path("bills/<int:bill_pk>/payments/", include(bill_payment_router.urls)),
    path("invoices/", include(invoice_router.urls)),
    path("invoices/<int:invoice_pk>/line-items/", include(invoice_line_item_router.urls)),
    path("invoices/<int:invoice_pk>/payments/", include(invoice_payment_router.urls)),
    # Budgets
    path("budgets/overview/", BudgetOverviewView.as_view(), name="budget-overview"),
    path("budgets/", include(budget_router.urls)),
    path("budgets/<int:budget_pk>/line-items/", include(budget_line_item_router.urls)),
    path(
        "budgets/<int:budget_pk>/reforecasts/<int:reforecast_pk>/approve/",
        ReforecastActionView.as_view(),
        {"action_type": "approve"},
        name="reforecast-approve",
    ),
    path(
        "budgets/<int:budget_pk>/reforecasts/<int:reforecast_pk>/reject/",
        ReforecastActionView.as_view(),
        {"action_type": "reject"},
        name="reforecast-reject",
    ),
    # Investors & Waterfall
    path("investors/", include(investor_router.urls)),
    path("project-investors/", include(project_investor_router.urls)),
    path("distributions/", include(distribution_router.urls)),
    # SPV & Payment Plans
    path("spv-entities/", include(spv_router.urls)),
    path("payment-plans/", include(payment_plan_router.urls)),
    path("payment-plans/<int:plan_pk>/installments/", include(installment_router.urls)),
    # Aging Report
    path("aging-report/", AgingReportView.as_view(), name="aging-report"),
    # Payment Vouchers & Runs
    path("payment-vouchers/", include(voucher_router.urls)),
    path("payment-runs/", include(payment_run_router.urls)),
    path("payment-receipts/", include(receipt_router.urls)),
    # Banking
    path("bank-accounts/liquidity/", BankLiquidityView.as_view(), name="bank-liquidity"),
    path("bank-accounts/", include(bank_account_router.urls)),
    path("bank-transactions/summary/", BankTransactionSummaryView.as_view(), name="bank-transaction-summary"),
    path("bank-transactions/<int:pk>/matches/", BankTransactionMatchView.as_view(), name="bank-transaction-matches"),
    path("bank-transactions/<int:pk>/link/", BankTransactionLinkView.as_view(), name="bank-transaction-link"),
    path("bank-transactions/<int:pk>/split-link/", BankTransactionSplitLinkView.as_view(), name="bank-transaction-split-link"),
    path("bank-transactions/auto-match/", BankTransactionAutoMatchView.as_view(), name="bank-transaction-auto-match"),
    path("bank-transactions/", include(bank_transaction_router.urls)),
    path("bank-reconciliations/overview/", ReconciliationOverviewView.as_view(), name="reconciliation-overview"),
    path("bank-reconciliations/", include(bank_reconciliation_router.urls)),
    # Reports
    path("reports/general-ledger/", GeneralLedgerView.as_view(), name="general-ledger-report"),
    path("reports/trial-balance/", TrialBalanceView.as_view(), name="trial-balance-report"),
    # Payroll → GL bridge
    path("payroll-gl-mappings/", include(payroll_gl_mapping_router.urls)),
    path("payroll-gl-postings/", include(payroll_gl_posting_router.urls)),
]
