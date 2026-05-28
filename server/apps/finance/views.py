import hashlib
from decimal import Decimal

from django.core.cache import cache
from django.db.models import Count, F, Q, Sum
from django.db.models.functions import Coalesce, TruncMonth
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from django_filters import rest_framework as filters
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.settings.permissions import HasRolePermission

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
    Investor,
    Invoice,
    InvoiceLineItem,
    InvoicePayment,
    JournalEntry,
    LedgerEntry,
    PaymentInstallment,
    PaymentPlan,
    PaymentReceipt,
    PaymentRun,
    PaymentVoucher,
    PayrollGLMapping,
    PayrollGLPosting,
    ProjectInvestor,
    ReforecastSuggestion,
    SPVEntity,
    WaterfallDistribution,
)
from .serializers import (
    AccountDetailSerializer,
    AccountListSerializer,
    AccountWriteSerializer,
    BankAccountDetailSerializer,
    BankAccountListSerializer,
    BankAccountWriteSerializer,
    BankReconciliationDetailSerializer,
    BankReconciliationListSerializer,
    BankReconciliationWriteSerializer,
    BankTransactionDetailSerializer,
    BankTransactionListSerializer,
    BankTransactionWriteSerializer,
    BillDetailSerializer,
    BillLineItemSerializer,
    BillListSerializer,
    BillPaymentSerializer,
    BillWriteSerializer,
    BudgetDetailSerializer,
    BudgetLineItemSerializer,
    BudgetLineItemWriteSerializer,
    BudgetListSerializer,
    BudgetWriteSerializer,
    CustomerDetailSerializer,
    CustomerListSerializer,
    CustomerWriteSerializer,
    InvestorDetailSerializer,
    InvestorListSerializer,
    InvestorWriteSerializer,
    InvoiceDetailSerializer,
    InvoiceLineItemSerializer,
    InvoiceListSerializer,
    InvoicePaymentSerializer,
    InvoiceWriteSerializer,
    JournalEntryDetailSerializer,
    JournalEntryListSerializer,
    JournalEntryWriteSerializer,
    LedgerEntrySerializer,
    PaymentInstallmentSerializer,
    PaymentInstallmentWriteSerializer,
    PaymentPlanDetailSerializer,
    PaymentPlanListSerializer,
    PaymentPlanWriteSerializer,
    PaymentReceiptDetailSerializer,
    PaymentReceiptListSerializer,
    PaymentReceiptWriteSerializer,
    PaymentRunDetailSerializer,
    PaymentRunListSerializer,
    PaymentRunWriteSerializer,
    PaymentVoucherDetailSerializer,
    PaymentVoucherListSerializer,
    PaymentVoucherWriteSerializer,
    PayrollGLMappingSerializer,
    PayrollGLPostingSerializer,
    ProjectInvestorSerializer,
    ProjectInvestorWriteSerializer,
    ReforecastSuggestionSerializer,
    SPVEntityDetailSerializer,
    SPVEntityListSerializer,
    SPVEntityWriteSerializer,
    WaterfallDistributionCreateSerializer,
    WaterfallDistributionDetailSerializer,
    WaterfallDistributionListSerializer,
)


def _user_org(request):
    return request.user.profile.organization


def _is_superuser(request):
    return request.user.is_superuser


def _scope_queryset_for_request(request, queryset, *, org_field: str = "organization"):
    """Filter a queryset to the caller's organization, or .none() if no org.
    Superusers see all rows (or scope to ?organization_id=X if provided)."""
    if _is_superuser(request):
        raw = request.query_params.get("organization_id") or request.query_params.get("org_id")
        if raw:
            try:
                org_id = int(str(raw))
                if org_id > 0:
                    org_id_field = org_field if org_field.endswith("_id") else f"{org_field}_id"
                    return queryset.filter(**{org_id_field: org_id})
            except (TypeError, ValueError):
                pass
        return queryset
    org = _user_org(request) if hasattr(request.user, "profile") else None
    if org is None:
        return queryset.none()
    return queryset.filter(**{org_field: org})


def _scoped_bill_queryset(request):
    return Bill.objects.filter(organization=_user_org(request))


def _scoped_invoice_queryset(request):
    return Invoice.objects.filter(organization=_user_org(request))


def _scoped_budget_queryset(request):
    return Budget.objects.filter(organization=_user_org(request))


def _scoped_payment_plan_queryset(request):
    return PaymentPlan.objects.filter(organization=_user_org(request))


def _scoped_payment_voucher_queryset(request):
    return PaymentVoucher.objects.filter(organization=_user_org(request))


FINANCE_DASHBOARD_CACHE_TTL_SECONDS = 120


def _sorted_query_hash(query_params) -> str:
    normalized = []
    for key in sorted(query_params.keys()):
        values = sorted(str(value) for value in query_params.getlist(key))
        normalized.extend(f"{key}={value}" for value in values)
    if not normalized:
        return "noquery"
    return hashlib.sha1("&".join(normalized).encode("utf-8")).hexdigest()[:16]


def _finance_dashboard_cache_key(request, scope: str) -> str:
    org_id = 0
    if not _is_superuser(request):
        org = _user_org(request)
        org_id = getattr(org, "id", 0) or 0
    query_hash = _sorted_query_hash(request.query_params)
    return (
        f"finance:dashboard:{scope}:u:{request.user.id}:"
        f"org:{org_id}:super:{int(_is_superuser(request))}:q:{query_hash}"
    )


# --- Filters ---

class BillFilter(filters.FilterSet):
    due_after = filters.DateFilter(field_name="due_date", lookup_expr="gte")
    due_before = filters.DateFilter(field_name="due_date", lookup_expr="lte")
    issued_after = filters.DateFilter(field_name="issue_date", lookup_expr="gte")
    issued_before = filters.DateFilter(field_name="issue_date", lookup_expr="lte")

    class Meta:
        model = Bill
        fields = ["status", "vendor", "property"]


class InvoiceFilter(filters.FilterSet):
    due_after = filters.DateFilter(field_name="due_date", lookup_expr="gte")
    due_before = filters.DateFilter(field_name="due_date", lookup_expr="lte")
    issued_after = filters.DateFilter(field_name="issue_date", lookup_expr="gte")
    issued_before = filters.DateFilter(field_name="issue_date", lookup_expr="lte")

    class Meta:
        model = Invoice
        fields = ["status", "customer", "property"]


class JournalEntryFilter(filters.FilterSet):
    entry_date_after = filters.DateFilter(field_name="entry_date", lookup_expr="gte")
    entry_date_before = filters.DateFilter(field_name="entry_date", lookup_expr="lte")
    posted_after = filters.DateTimeFilter(field_name="posted_at", lookup_expr="gte")
    posted_before = filters.DateTimeFilter(field_name="posted_at", lookup_expr="lte")

    class Meta:
        model = JournalEntry
        fields = ["status", "source_type", "entry_date"]


class PaymentVoucherFilter(filters.FilterSet):
    issued_after = filters.DateFilter(field_name="issue_date", lookup_expr="gte")
    issued_before = filters.DateFilter(field_name="issue_date", lookup_expr="lte")
    property = filters.NumberFilter(field_name="bill__property_id")

    class Meta:
        model = PaymentVoucher
        fields = ["status", "vendor", "priority"]


# --- Action Map ---

_FINANCE_ACTION_MAP = {
    "list": "view", "retrieve": "view", "create": "create",
    "update": "edit", "partial_update": "edit", "destroy": "delete",
    "submit_approval": "approve", "post_journal": "approve",
    "generate_reforecast": "edit", "list_reforecasts": "view",
    "returns": "view", "calculate": "edit", "approve": "approve",
    "preview": "view", "pause": "edit", "activate": "edit",
    "record_payment": "edit",
}


# --- ViewSets ---

class CustomerViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "finance.customers"
    search_fields = ["name", "contact_person"]
    filterset_fields = ["is_active"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def get_queryset(self):
        return Customer.objects.filter(
            organization=_user_org(self.request),
        ).annotate(invoice_count=Count("invoices"))

    def get_serializer_class(self):
        if self.action == "list":
            return CustomerListSerializer
        if self.action in ("create", "update", "partial_update"):
            return CustomerWriteSerializer
        return CustomerDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


class BillViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "finance.bills"
    rbac_action_map = _FINANCE_ACTION_MAP
    filterset_class = BillFilter
    search_fields = ["bill_number", "vendor__name", "notes"]
    ordering_fields = ["bill_number", "due_date", "total_amount", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = _scoped_bill_queryset(self.request)
        return qs.select_related("vendor", "property")

    def get_serializer_class(self):
        if self.action == "list":
            return BillListSerializer
        if self.action in ("create", "update", "partial_update"):
            return BillWriteSerializer
        return BillDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))

    @action(detail=True, methods=["post"], url_path="submit-approval")
    def submit_approval(self, request, pk=None):
        from apps.workflows.engine import submit_for_approval
        bill = self.get_object()
        if bill.status != Bill.Status.DRAFT:
            return Response(
                {"detail": "Only draft bills can be submitted for approval."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            instance = submit_for_approval(bill, request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {"detail": "Submitted for approval.", "workflow_instance_id": instance.pk},
            status=status.HTTP_201_CREATED,
        )


class InvoiceViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "finance.invoices"
    rbac_action_map = _FINANCE_ACTION_MAP
    filterset_class = InvoiceFilter
    search_fields = ["invoice_number", "customer__name", "notes"]
    ordering_fields = ["invoice_number", "due_date", "total_amount", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = _scoped_invoice_queryset(self.request)
        return qs.select_related("customer", "property")

    def get_serializer_class(self):
        if self.action == "list":
            return InvoiceListSerializer
        if self.action in ("create", "update", "partial_update"):
            return InvoiceWriteSerializer
        return InvoiceDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))

    @action(detail=True, methods=["post"], url_path="submit-approval")
    def submit_approval(self, request, pk=None):
        from apps.workflows.engine import submit_for_approval
        invoice = self.get_object()
        if invoice.status != Invoice.Status.DRAFT:
            return Response(
                {"detail": "Only draft invoices can be submitted for approval."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            instance = submit_for_approval(invoice, request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {"detail": "Submitted for approval.", "workflow_instance_id": instance.pk},
            status=status.HTTP_201_CREATED,
        )


class BillLineItemViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "finance.bills"
    serializer_class = BillLineItemSerializer

    def _get_bill(self):
        return get_object_or_404(_scoped_bill_queryset(self.request), pk=self.kwargs["bill_pk"])

    def get_queryset(self):
        bill = self._get_bill()
        return BillLineItem.objects.filter(bill=bill)

    def perform_create(self, serializer):
        item = serializer.save(bill=self._get_bill())
        item.bill.recalculate_totals()

    def perform_update(self, serializer):
        item = serializer.save()
        item.bill.recalculate_totals()

    def perform_destroy(self, instance):
        bill = instance.bill
        instance.delete()
        bill.recalculate_totals()


class BillPaymentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "finance.payments"
    serializer_class = BillPaymentSerializer

    def _get_bill(self):
        return get_object_or_404(_scoped_bill_queryset(self.request), pk=self.kwargs["bill_pk"])

    def get_queryset(self):
        return BillPayment.objects.filter(bill=self._get_bill())

    def perform_create(self, serializer):
        payment = serializer.save(bill=self._get_bill())
        payment.bill.update_status_from_payments()

    def perform_update(self, serializer):
        payment = serializer.save()
        payment.bill.update_status_from_payments()

    def perform_destroy(self, instance):
        bill = instance.bill
        instance.delete()
        bill.update_status_from_payments()


class InvoiceLineItemViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "finance.invoices"
    serializer_class = InvoiceLineItemSerializer

    def _get_invoice(self):
        return get_object_or_404(
            _scoped_invoice_queryset(self.request),
            pk=self.kwargs["invoice_pk"],
        )

    def get_queryset(self):
        return InvoiceLineItem.objects.filter(invoice=self._get_invoice())

    def perform_create(self, serializer):
        item = serializer.save(invoice=self._get_invoice())
        item.invoice.recalculate_totals()

    def perform_update(self, serializer):
        item = serializer.save()
        item.invoice.recalculate_totals()

    def perform_destroy(self, instance):
        invoice = instance.invoice
        instance.delete()
        invoice.recalculate_totals()


class InvoicePaymentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "finance.payments"
    serializer_class = InvoicePaymentSerializer

    def _get_invoice(self):
        return get_object_or_404(
            _scoped_invoice_queryset(self.request),
            pk=self.kwargs["invoice_pk"],
        )

    def get_queryset(self):
        return InvoicePayment.objects.filter(invoice=self._get_invoice())

    def perform_create(self, serializer):
        payment = serializer.save(invoice=self._get_invoice())
        payment.invoice.update_status_from_payments()

    def perform_update(self, serializer):
        payment = serializer.save()
        payment.invoice.update_status_from_payments()

    def perform_destroy(self, instance):
        invoice = instance.invoice
        instance.delete()
        invoice.update_status_from_payments()


# --- Chart of Accounts ---


class AccountViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "finance.accounts"
    search_fields = ["code", "name", "description"]
    filterset_fields = ["account_type", "sub_type", "is_active", "is_system"]
    ordering_fields = ["code", "name", "account_type", "created_at"]
    ordering = ["code"]

    def get_queryset(self):
        return Account.objects.filter(
            organization=_user_org(self.request),
        ).select_related("parent")

    def get_serializer_class(self):
        if self.action == "list":
            return AccountListSerializer
        if self.action in ("create", "update", "partial_update"):
            return AccountWriteSerializer
        return AccountDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))

    def perform_destroy(self, instance):
        if instance.is_system:
            from rest_framework.exceptions import ValidationError

            raise ValidationError("System accounts cannot be deleted.")
        instance.delete()


# --- Journals & General Ledger ---


class JournalEntryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "finance.accounts"
    rbac_action_map = _FINANCE_ACTION_MAP
    filterset_class = JournalEntryFilter
    search_fields = ["journal_number", "description", "reference"]
    ordering_fields = ["journal_number", "entry_date", "status", "posted_at", "created_at"]
    ordering = ["-entry_date", "-created_at"]

    def get_queryset(self):
        return JournalEntry.objects.filter(
            organization=_user_org(self.request),
        ).select_related("organization", "posted_by", "created_by").prefetch_related(
            "lines__account", "lines__department", "lines__cost_center"
        )

    def get_serializer_class(self):
        if self.action == "list":
            return JournalEntryListSerializer
        if self.action in ("create", "update", "partial_update"):
            return JournalEntryWriteSerializer
        return JournalEntryDetailSerializer

    def perform_create(self, serializer):
        serializer.save(
            organization=_user_org(self.request),
            created_by=self.request.user,
        )

    def perform_destroy(self, instance):
        from rest_framework.exceptions import ValidationError

        if instance.status != JournalEntry.Status.DRAFT:
            raise ValidationError("Only draft journal entries can be deleted.")
        if instance.ledger_entries.exists():
            raise ValidationError("Posted journals with ledger entries cannot be deleted.")
        instance.delete()

    @action(detail=True, methods=["post"], url_path="post")
    def post_journal(self, request, pk=None):
        from .gl_utils import post_journal_entry

        journal = self.get_object()
        try:
            journal = post_journal_entry(journal.id, request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = JournalEntryDetailSerializer(journal)
        return Response(serializer.data, status=status.HTTP_200_OK)


class GeneralLedgerView(APIView):
    """General ledger activity feed with account/date filters."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "finance.reports"
    rbac_action = "view"

    def get(self, request):
        org = _user_org(request)
        qs = LedgerEntry.objects.filter(
            organization=org,
        ).select_related(
            "journal_entry",
            "journal_line",
            "account",
            "department",
            "cost_center",
            "organization",
        )

        account_id = request.query_params.get("account")
        if account_id:
            qs = qs.filter(account_id=account_id)

        date_from = request.query_params.get("date_from")
        if date_from:
            parsed_from = parse_date(date_from)
            if parsed_from:
                qs = qs.filter(entry_date__gte=parsed_from)

        date_to = request.query_params.get("date_to")
        if date_to:
            parsed_to = parse_date(date_to)
            if parsed_to:
                qs = qs.filter(entry_date__lte=parsed_to)

        source_type = request.query_params.get("source_type")
        if source_type:
            qs = qs.filter(source_type=source_type)

        page = 1
        try:
            requested_page = int(request.query_params.get("page", "1"))
            page = max(requested_page, 1)
        except (TypeError, ValueError):
            pass

        page_size = 200
        try:
            requested_page_size = int(
                request.query_params.get(
                    "page_size",
                    request.query_params.get("limit", "200"),
                )
            )
            page_size = min(max(requested_page_size, 1), 1000)
        except (TypeError, ValueError):
            pass

        total_count = qs.count()
        total_pages = max(1, (total_count + page_size - 1) // page_size)
        page = min(page, total_pages)
        offset = (page - 1) * page_size

        totals = qs.aggregate(
            total_debit=Sum("debit_amount"),
            total_credit=Sum("credit_amount"),
        )
        entries = qs.order_by("-entry_date", "-id")[offset: offset + page_size]

        return Response(
            {
                "count": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "limit": page_size,
                "totals": {
                    "debit": str(totals["total_debit"] or Decimal("0.00")),
                    "credit": str(totals["total_credit"] or Decimal("0.00")),
                },
                "results": LedgerEntrySerializer(entries, many=True).data,
            }
        )


class TrialBalanceView(APIView):
    """Trial balance snapshot computed from posted ledger entries."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "finance.reports"
    rbac_action = "view"

    def get(self, request):
        as_of_raw = request.query_params.get("as_of")
        as_of = parse_date(as_of_raw) if as_of_raw else timezone.localdate()
        if as_of is None:
            as_of = timezone.localdate()

        org = _user_org(request)
        ledger_qs = LedgerEntry.objects.filter(
            organization=org, entry_date__lte=as_of,
        ).select_related("account")

        grouped = (
            ledger_qs.values(
                "account_id",
                "account__code",
                "account__name",
                "account__account_type",
            )
            .annotate(
                total_debit=Sum("debit_amount"),
                total_credit=Sum("credit_amount"),
            )
            .order_by("account__code")
        )

        rows = []
        total_debit_balance = Decimal("0.00")
        total_credit_balance = Decimal("0.00")
        debit_normal_types = {"asset", "expense"}

        for row in grouped:
            movement_debit = row["total_debit"] or Decimal("0.00")
            movement_credit = row["total_credit"] or Decimal("0.00")
            normal_debit = row["account__account_type"] in debit_normal_types
            net = (
                movement_debit - movement_credit
                if normal_debit
                else movement_credit - movement_debit
            )

            debit_balance = net if net >= 0 else Decimal("0.00")
            credit_balance = -net if net < 0 else Decimal("0.00")

            total_debit_balance += debit_balance
            total_credit_balance += credit_balance

            rows.append(
                {
                    "account_id": row["account_id"],
                    "account_code": row["account__code"],
                    "account_name": row["account__name"],
                    "account_type": row["account__account_type"],
                    "movement_debit": str(movement_debit),
                    "movement_credit": str(movement_credit),
                    "debit_balance": str(debit_balance),
                    "credit_balance": str(credit_balance),
                }
            )

        draft_qs = JournalEntry.objects.filter(
            status=JournalEntry.Status.DRAFT, organization=org,
        )

        return Response(
            {
                "as_of": as_of.isoformat(),
                "rows": rows,
                "totals": {
                    "debit": str(total_debit_balance),
                    "credit": str(total_credit_balance),
                    "difference": str(total_debit_balance - total_credit_balance),
                },
                "draft_journal_count": draft_qs.count(),
                "row_count": len(rows),
            }
        )


# --- Overview ---

class FinanceOverviewView(APIView):
    """Aggregated finance dashboard data."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "finance.reports"
    rbac_action = "view"

    def get(self, request):
        cache_key = _finance_dashboard_cache_key(request, "overview")
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        from datetime import date

        today = date.today()
        org = _user_org(request)

        # Bills aggregation
        bill_qs = Bill.objects.filter(organization=org)
        unpaid_bills = bill_qs.exclude(
            status__in=[Bill.Status.PAID, Bill.Status.CANCELLED]
        )
        bill_totals = unpaid_bills.aggregate(
            total=Sum("total_amount"),
            payment_total=Sum("payments__amount"),
        )
        total_payable_raw = (bill_totals["total"] or 0) - (bill_totals["payment_total"] or 0)

        overdue_bills = unpaid_bills.filter(due_date__lt=today)
        overdue_bill_agg = overdue_bills.aggregate(
            count=Count("id"),
            total=Sum("total_amount"),
            payment_total=Sum("payments__amount"),
        )
        overdue_payable_amount = (overdue_bill_agg["total"] or 0) - (overdue_bill_agg["payment_total"] or 0)

        # Invoices aggregation
        inv_qs = Invoice.objects.filter(organization=org)
        unpaid_invoices = inv_qs.exclude(
            status__in=[Invoice.Status.PAID, Invoice.Status.CANCELLED]
        )
        inv_totals = unpaid_invoices.aggregate(
            total=Sum("total_amount"),
            payment_total=Sum("payments__amount"),
        )
        total_receivable_raw = (inv_totals["total"] or 0) - (inv_totals["payment_total"] or 0)

        overdue_invoices = unpaid_invoices.filter(due_date__lt=today)
        overdue_inv_agg = overdue_invoices.aggregate(
            count=Count("id"),
            total=Sum("total_amount"),
            payment_total=Sum("payments__amount"),
        )
        overdue_receivable_amount = (overdue_inv_agg["total"] or 0) - (overdue_inv_agg["payment_total"] or 0)

        # Status distributions
        bills_by_status = list(
            bill_qs.values("status")
            .annotate(count=Count("id"))
            .order_by("status")
        )
        invoices_by_status = list(
            inv_qs.values("status")
            .annotate(count=Count("id"))
            .order_by("status")
        )

        # Recent items
        recent_bills = bill_qs.select_related("vendor", "property").order_by("-created_at")[:5]
        recent_invoices = inv_qs.select_related("customer", "property").order_by("-created_at")[:5]

        payload = {
            "total_payable": str(total_payable_raw),
            "total_receivable": str(total_receivable_raw),
            "overdue_payable_count": overdue_bill_agg["count"] or 0,
            "overdue_payable_amount": str(overdue_payable_amount),
            "overdue_receivable_count": overdue_inv_agg["count"] or 0,
            "overdue_receivable_amount": str(overdue_receivable_amount),
            "recent_bills": BillListSerializer(recent_bills, many=True).data,
            "recent_invoices": InvoiceListSerializer(recent_invoices, many=True).data,
            "bills_by_status": bills_by_status,
            "invoices_by_status": invoices_by_status,
        }
        cache.set(cache_key, payload, timeout=FINANCE_DASHBOARD_CACHE_TTL_SECONDS)
        return Response(payload)


class FinanceCashFlowView(APIView):
    """Monthly cash-flow analytics for the finance dashboard."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "finance.reports"
    rbac_action = "view"

    MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    def get(self, request):
        from datetime import date

        cache_key = _finance_dashboard_cache_key(request, "cash-flow")
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        year_param = request.query_params.get("year")
        year = int(year_param) if year_param and year_param.isdigit() else date.today().year

        org = _user_org(request)

        # --- Net balance (receivable - payable) ---
        bill_qs = Bill.objects.filter(organization=org).exclude(
            status__in=[Bill.Status.PAID, Bill.Status.CANCELLED],
        )
        inv_qs = Invoice.objects.filter(organization=org).exclude(
            status__in=[Invoice.Status.PAID, Invoice.Status.CANCELLED],
        )

        bill_agg = bill_qs.aggregate(
            total=Coalesce(Sum("total_amount"), Decimal("0")),
            paid=Coalesce(Sum("payments__amount"), Decimal("0")),
        )
        inv_agg = inv_qs.aggregate(
            total=Coalesce(Sum("total_amount"), Decimal("0")),
            paid=Coalesce(Sum("payments__amount"), Decimal("0")),
        )
        total_payable = bill_agg["total"] - bill_agg["paid"]
        total_receivable = inv_agg["total"] - inv_agg["paid"]
        net_balance = total_receivable - total_payable

        # --- Year totals & monthly flow ---
        bp_filter = {"bill__organization": org}
        ip_filter = {"invoice__organization": org}

        expense_monthly = dict(
            BillPayment.objects.filter(
                payment_date__year=year, **bp_filter
            ).annotate(
                month=TruncMonth("payment_date")
            ).values("month").annotate(
                total=Coalesce(Sum("amount"), Decimal("0"))
            ).values_list("month", "total")
        )

        income_monthly = dict(
            InvoicePayment.objects.filter(
                payment_date__year=year, **ip_filter
            ).annotate(
                month=TruncMonth("payment_date")
            ).values("month").annotate(
                total=Coalesce(Sum("amount"), Decimal("0"))
            ).values_list("month", "total")
        )

        total_income = Decimal("0")
        total_expenses = Decimal("0")
        monthly_flow = []
        for m in range(1, 13):
            month_date = date(year, m, 1)
            inc = income_monthly.get(month_date, Decimal("0"))
            exp = expense_monthly.get(month_date, Decimal("0"))
            total_income += inc
            total_expenses += exp
            monthly_flow.append({
                "month": self.MONTH_LABELS[m - 1],
                "income": str(inc),
                "expenses": str(exp),
            })

        # --- Top vendors by expense ---
        expense_by_vendor = list(
            BillPayment.objects.filter(
                payment_date__year=year, **bp_filter
            ).values(
                label=F("bill__vendor__name")
            ).annotate(
                value=Coalesce(Sum("amount"), Decimal("0"))
            ).order_by("-value")[:5]
        )
        for item in expense_by_vendor:
            item["value"] = str(item["value"])

        # --- Top customers by income ---
        income_by_customer = list(
            InvoicePayment.objects.filter(
                payment_date__year=year, **ip_filter
            ).values(
                label=F("invoice__customer__name")
            ).annotate(
                value=Coalesce(Sum("amount"), Decimal("0"))
            ).order_by("-value")[:5]
        )
        for item in income_by_customer:
            item["value"] = str(item["value"])

        # --- Budget utilization ---
        from .budget_utils import get_actual_spent

        budget_qs = Budget.objects.filter(status=Budget.Status.ACTIVE, organization=org)

        total_budgeted = Decimal("0")
        total_spent = Decimal("0")
        for budget in budget_qs.prefetch_related("line_items__account"):
            for bli in budget.line_items.all():
                total_budgeted += bli.budgeted_amount
                total_spent += get_actual_spent(bli)

        budget_pct_remaining = (
            round(float((total_budgeted - total_spent) / total_budgeted * 100), 1)
            if total_budgeted > 0
            else 100.0
        )

        payload = {
            "year": year,
            "net_balance": str(net_balance),
            "total_income": str(total_income),
            "total_expenses": str(total_expenses),
            "monthly_flow": monthly_flow,
            "expense_by_vendor": expense_by_vendor,
            "income_by_customer": income_by_customer,
            "budget_pct_remaining": budget_pct_remaining,
        }
        cache.set(cache_key, payload, timeout=FINANCE_DASHBOARD_CACHE_TTL_SECONDS)
        return Response(payload)


# --- Budgets ---


class BudgetViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "finance.budgets"
    rbac_action_map = _FINANCE_ACTION_MAP
    search_fields = ["name"]
    filterset_fields = ["status", "period_type"]
    ordering_fields = ["name", "start_date", "end_date", "total_amount", "created_at"]
    ordering = ["-start_date"]

    def get_queryset(self):
        qs = _scoped_budget_queryset(self.request)
        return qs.prefetch_related("line_items__account")

    def get_serializer_class(self):
        if self.action == "list":
            return BudgetListSerializer
        if self.action in ("create", "update", "partial_update"):
            return BudgetWriteSerializer
        return BudgetDetailSerializer

    def perform_create(self, serializer):
        serializer.save(
            organization=_user_org(self.request),
            created_by=self.request.user,
        )

    def perform_destroy(self, instance):
        if instance.status != Budget.Status.DRAFT:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Only draft budgets can be deleted.")
        instance.delete()

    @action(detail=True, methods=["post"], url_path="reforecast")
    def generate_reforecast(self, request, pk=None):
        from .budget_utils import generate_reforecast
        budget = self.get_object()
        if budget.status != Budget.Status.ACTIVE:
            return Response(
                {"detail": "Reforecast is only available for active budgets."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        suggestion = generate_reforecast(budget.id)
        if suggestion is None:
            return Response(
                {"detail": "Budget has no line items to reforecast."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            ReforecastSuggestionSerializer(suggestion).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"], url_path="reforecasts")
    def list_reforecasts(self, request, pk=None):
        budget = self.get_object()
        reforecasts = budget.reforecasts.prefetch_related(
            "line_items__budget_line_item__account"
        )
        return Response(
            ReforecastSuggestionSerializer(reforecasts, many=True).data
        )


class BudgetLineItemViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "finance.budgets"

    def _get_budget(self):
        return get_object_or_404(
            _scoped_budget_queryset(self.request),
            pk=self.kwargs["budget_pk"],
        )

    def get_queryset(self):
        budget = self._get_budget()
        return BudgetLineItem.objects.filter(
            budget=budget
        ).select_related("account", "department", "cost_center")

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return BudgetLineItemWriteSerializer
        return BudgetLineItemSerializer

    def perform_create(self, serializer):
        serializer.save(budget=self._get_budget())


class ReforecastActionView(APIView):
    """Approve or reject a reforecast suggestion."""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "finance.budgets"
    rbac_action = "approve"

    def post(self, request, budget_pk, reforecast_pk, action_type):
        suggestion = ReforecastSuggestion.objects.select_related("budget").get(
            id=reforecast_pk, budget_id=budget_pk
        )
        if suggestion.status != ReforecastSuggestion.Status.PENDING:
            return Response(
                {"detail": "This reforecast has already been reviewed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if action_type == "approve":
            for item in suggestion.line_items.select_related("budget_line_item"):
                bli = item.budget_line_item
                bli.budgeted_amount = item.suggested_amount
                bli.save(update_fields=["budgeted_amount"])
            suggestion.status = ReforecastSuggestion.Status.APPROVED
        else:
            suggestion.status = ReforecastSuggestion.Status.REJECTED

        suggestion.reviewed_by = request.user
        suggestion.reviewed_at = timezone.now()
        suggestion.save(update_fields=["status", "reviewed_by", "reviewed_at"])
        return Response(ReforecastSuggestionSerializer(suggestion).data)


class BudgetOverviewView(APIView):
    """Dashboard KPIs for budgets."""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "finance.reports"
    rbac_action = "view"

    def get(self, request):
        cache_key = _finance_dashboard_cache_key(request, "budget-overview")
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        from .budget_utils import get_actual_spent

        org = _user_org(request)
        qs = Budget.objects.filter(organization=org)

        total_count = qs.count()
        total_budgeted = Decimal("0")
        total_spent = Decimal("0")
        warning_count = 0
        exceeded_count = 0

        for budget in qs.prefetch_related("line_items__account"):
            total_budgeted += budget.total_amount
            budget_spent = Decimal("0")
            for bli in budget.line_items.all():
                budget_spent += get_actual_spent(bli)
            total_spent += budget_spent
            if budget.total_amount > 0:
                pct = budget_spent / budget.total_amount * Decimal("100")
                tolerance = Decimal("100") + budget.overspend_tolerance_pct
                if pct >= tolerance:
                    exceeded_count += 1
                elif pct >= budget.warning_threshold_pct:
                    warning_count += 1

        pct_used = (
            round(float(total_spent / total_budgeted * 100), 1)
            if total_budgeted > 0
            else 0
        )

        payload = {
            "active_budgets": total_count,
            "total_budgeted": str(total_budgeted),
            "total_spent": str(total_spent),
            "pct_used": pct_used,
            "warning_count": warning_count,
            "exceeded_count": exceeded_count,
        }
        cache.set(cache_key, payload, timeout=FINANCE_DASHBOARD_CACHE_TTL_SECONDS)
        return Response(payload)


# --- Investor & Waterfall ViewSets ---

class InvestorViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "finance.payments"
    search_fields = ["name", "contact_person", "email"]
    filterset_fields = ["investor_type", "is_active"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def get_queryset(self):
        return Investor.objects.filter(
            organization=_user_org(self.request),
        ).annotate(
            investment_count=Count("project_investments"),
            total_invested=Coalesce(
                Sum("project_investments__capital_contributed"),
                Decimal("0.00"),
            ),
        )

    def get_serializer_class(self):
        if self.action == "list":
            return InvestorListSerializer
        if self.action in ("create", "update", "partial_update"):
            return InvestorWriteSerializer
        return InvestorDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


class ProjectInvestorViewSet(viewsets.ModelViewSet):
    """Manage project cap table (investor assignments)."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "finance.payments"
    rbac_action_map = _FINANCE_ACTION_MAP
    filterset_fields = ["project", "investor"]
    ordering_fields = ["sort_order", "ownership_percentage"]
    ordering = ["project", "sort_order"]

    def get_queryset(self):
        return ProjectInvestor.objects.filter(
            organization=_user_org(self.request),
        ).select_related("investor", "project")

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return ProjectInvestorWriteSerializer
        return ProjectInvestorSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))

    @action(detail=True, methods=["get"])
    def returns(self, request, pk=None):
        """Get returns metrics for this investor in this project."""
        from .returns_utils import calculate_investor_returns

        project_investor = self.get_object()
        returns = calculate_investor_returns(project_investor.id)

        return Response({
            "investor_name": returns.investor_name,
            "capital_contributed": str(returns.capital_contributed),
            "capital_returned": str(returns.capital_returned),
            "unreturned_capital": str(returns.unreturned_capital),
            "profit_distributed": str(returns.profit_distributed),
            "total_distributed": str(returns.total_distributed),
            "equity_multiple": str(returns.equity_multiple) if returns.equity_multiple else None,
            "cash_flows": [
                {"date": cf.date.isoformat(), "amount": str(cf.amount)}
                for cf in returns.cash_flows
            ],
        })


class WaterfallDistributionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "finance.payments"
    rbac_action_map = _FINANCE_ACTION_MAP
    filterset_fields = ["project", "status"]
    search_fields = ["distribution_number", "notes"]
    ordering_fields = ["distribution_date", "total_amount", "created_at"]
    ordering = ["-distribution_date"]

    def get_queryset(self):
        return WaterfallDistribution.objects.filter(
            organization=_user_org(self.request),
        ).select_related("project")

    def get_serializer_class(self):
        if self.action == "list":
            return WaterfallDistributionListSerializer
        if self.action == "create":
            return WaterfallDistributionCreateSerializer
        return WaterfallDistributionDetailSerializer

    def create(self, request, *args, **kwargs):
        """Create and calculate a new distribution."""
        from .waterfall_utils import create_distribution

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        distribution = create_distribution(
            project_id=serializer.validated_data["project"].id,
            distribution_amount=serializer.validated_data["total_amount"],
            distribution_date=serializer.validated_data["distribution_date"],
            notes=serializer.validated_data.get("notes", ""),
            created_by_user=request.user,
            organization=_user_org(request),
        )

        detail_serializer = WaterfallDistributionDetailSerializer(distribution)
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def calculate(self, request, pk=None):
        """Recalculate waterfall for draft distribution."""
        from .models import DistributionLineItem
        from .waterfall_utils import calculate_waterfall

        distribution = self.get_object()

        if distribution.status != WaterfallDistribution.Status.DRAFT:
            return Response(
                {"error": "Can only recalculate DRAFT distributions"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Delete old line items
        distribution.line_items.all().delete()

        # Recalculate
        calc = calculate_waterfall(
            distribution.project_id,
            distribution.total_amount,
        )

        # Update distribution
        distribution.tier1_capital_returned = calc.tier1_total
        distribution.tier2_profit_split = calc.tier2_total
        distribution.sponsor_amount = calc.sponsor_amount
        distribution.status = WaterfallDistribution.Status.CALCULATED
        distribution.save()

        # Create new line items
        for i, alloc in enumerate(calc.allocations):
            DistributionLineItem.objects.create(
                distribution=distribution,
                project_investor_id=alloc.project_investor_id,
                tier1_capital_amount=alloc.tier1_capital_amount,
                tier2_profit_amount=alloc.tier2_profit_amount,
                total_amount=alloc.total_amount,
                capital_returned_to_date=alloc.capital_returned_to_date,
                profit_distributed_to_date=alloc.profit_distributed_to_date,
                sort_order=i,
            )

        serializer = WaterfallDistributionDetailSerializer(distribution)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Approve distribution and update investor balances."""
        from .waterfall_utils import approve_distribution

        distribution = self.get_object()

        try:
            approved_dist = approve_distribution(distribution.id, request.user)
            serializer = WaterfallDistributionDetailSerializer(approved_dist)
            return Response(serializer.data)
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=["get"])
    def preview(self, request, pk=None):
        """Preview waterfall calculation without saving."""
        from .waterfall_utils import calculate_waterfall

        distribution = self.get_object()

        calc = calculate_waterfall(
            distribution.project_id,
            distribution.total_amount,
        )

        return Response({
            "total_amount": str(calc.total_amount),
            "tier1_total": str(calc.tier1_total),
            "tier2_total": str(calc.tier2_total),
            "sponsor_amount": str(calc.sponsor_amount),
            "allocations": [
                {
                    "investor_name": alloc.investor_name,
                    "ownership_pct": str(alloc.ownership_pct),
                    "unreturned_capital": str(alloc.unreturned_capital),
                    "tier1_capital_amount": str(alloc.tier1_capital_amount),
                    "tier2_profit_amount": str(alloc.tier2_profit_amount),
                    "total_amount": str(alloc.total_amount),
                }
                for alloc in calc.allocations
            ],
            "summary": calc.calculation_summary,
        })


# ---------------------------------------------------------------------------
# SPV Entity
# ---------------------------------------------------------------------------


class SPVEntityViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "finance.payments"
    search_fields = ["name", "registration_number", "jurisdiction"]
    filterset_fields = ["entity_type", "status", "is_active"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def get_queryset(self):
        return SPVEntity.objects.filter(
            organization=_user_org(self.request),
        ).select_related("parent_entity")

    def get_serializer_class(self):
        if self.action == "list":
            return SPVEntityListSerializer
        if self.action in ("create", "update", "partial_update"):
            return SPVEntityWriteSerializer
        return SPVEntityDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


# ---------------------------------------------------------------------------
# Payment Plan
# ---------------------------------------------------------------------------


class PaymentPlanViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "finance.payments"
    rbac_action_map = _FINANCE_ACTION_MAP
    search_fields = ["plan_number", "title"]
    filterset_fields = ["status", "direction", "plan_type", "frequency"]
    ordering_fields = ["plan_number", "title", "total_amount", "start_date", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = _scoped_payment_plan_queryset(self.request)
        return qs.select_related(
            "customer", "vendor", "investor", "project", "spv_entity",
        ).annotate(
            _paid_amount=Coalesce(Sum("installments__paid_amount"), Decimal("0.00")),
            _installment_count=Count("installments"),
        )

    def get_serializer_class(self):
        if self.action == "list":
            return PaymentPlanListSerializer
        if self.action in ("create", "update", "partial_update"):
            return PaymentPlanWriteSerializer
        return PaymentPlanDetailSerializer

    def perform_create(self, serializer):
        serializer.save(
            organization=_user_org(self.request),
            created_by=self.request.user,
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        plan = self.get_object()
        if plan.status != PaymentPlan.Status.DRAFT:
            return Response(
                {"error": "Only draft plans can be approved."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        plan.status = PaymentPlan.Status.ACTIVE
        plan.approved_by = request.user
        plan.approved_at = timezone.now()
        plan.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
        return Response(PaymentPlanDetailSerializer(plan).data)

    @action(detail=True, methods=["post"])
    def pause(self, request, pk=None):
        plan = self.get_object()
        if plan.status != PaymentPlan.Status.ACTIVE:
            return Response(
                {"error": "Only active plans can be paused."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        plan.status = PaymentPlan.Status.PAUSED
        plan.save(update_fields=["status", "updated_at"])
        return Response(PaymentPlanDetailSerializer(plan).data)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        plan = self.get_object()
        if plan.status not in (PaymentPlan.Status.DRAFT, PaymentPlan.Status.PAUSED):
            return Response(
                {"error": "Only draft or paused plans can be activated."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        plan.status = PaymentPlan.Status.ACTIVE
        plan.save(update_fields=["status", "updated_at"])
        return Response(PaymentPlanDetailSerializer(plan).data)


# ---------------------------------------------------------------------------
# Payment Installment (nested under PaymentPlan)
# ---------------------------------------------------------------------------


class PaymentInstallmentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "finance.payments"
    rbac_action_map = _FINANCE_ACTION_MAP
    ordering = ["installment_number"]

    def _get_payment_plan(self):
        return get_object_or_404(
            _scoped_payment_plan_queryset(self.request),
            pk=self.kwargs["plan_pk"],
        )

    def get_queryset(self):
        plan = self._get_payment_plan()
        return PaymentInstallment.objects.filter(
            payment_plan=plan,
        ).select_related("milestone")

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return PaymentInstallmentWriteSerializer
        return PaymentInstallmentSerializer

    def perform_create(self, serializer):
        serializer.save(payment_plan=self._get_payment_plan())

    @action(detail=True, methods=["post"])
    def record_payment(self, request, plan_pk=None, pk=None):
        installment = self.get_object()
        amount = Decimal(str(request.data.get("amount", 0)))
        if amount <= 0:
            return Response(
                {"error": "Payment amount must be positive."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        installment.paid_amount += amount
        if installment.paid_amount >= installment.amount:
            installment.status = PaymentInstallment.Status.PAID
            installment.paid_date = timezone.now().date()
        else:
            installment.status = PaymentInstallment.Status.PARTIALLY_PAID

        if request.data.get("payment_method"):
            installment.payment_method = request.data["payment_method"]
        if request.data.get("reference_number"):
            installment.reference_number = request.data["reference_number"]

        installment.save()
        return Response(PaymentInstallmentSerializer(installment).data)


# ---------------------------------------------------------------------------
# Unified Transactions Feed
# ---------------------------------------------------------------------------


class FinanceTransactionsView(APIView):
    """Unified paginated feed of all finance transactions."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "finance.reports"
    rbac_action = "view"

    VALID_SORT_FIELDS = {"date", "amount", "reference", "counterparty", "type"}

    def get(self, request):

        org = _user_org(request)

        # --- Query params ---
        search = request.query_params.get("search", "").strip()
        type_filter = request.query_params.get("type", "")
        status_filter = request.query_params.get("status", "")
        ordering = request.query_params.get("ordering", "-date")

        try:
            page = max(int(request.query_params.get("page", "1")), 1)
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = min(max(int(request.query_params.get("page_size", "25")), 1), 100)
        except (TypeError, ValueError):
            page_size = 25

        # --- Parse sort ---
        desc = ordering.startswith("-")
        sort_key = ordering.lstrip("-")
        if sort_key not in self.VALID_SORT_FIELDS:
            sort_key = "date"
            desc = True

        # --- Build rows from each model ---
        rows: list[dict] = []
        wanted_types = [t.strip() for t in type_filter.split(",") if t.strip()] if type_filter else []

        if not wanted_types or "bill" in wanted_types:
            bill_qs = Bill.objects.filter(organization=org).select_related("vendor")
            if status_filter:
                bill_qs = bill_qs.filter(status=status_filter)
            if search:
                bill_qs = bill_qs.filter(
                    Q(bill_number__icontains=search) | Q(vendor__name__icontains=search)
                )
            for b in bill_qs.iterator():
                rows.append({
                    "id": f"bill-{b.pk}",
                    "type": "bill",
                    "reference": b.bill_number or f"BILL-{b.pk}",
                    "counterparty": b.vendor.name if b.vendor else "\u2014",
                    "date": (b.issue_date or b.created_at.date()).isoformat(),
                    "amount": str(b.total_amount),
                    "status": b.status,
                    "direction": "outgoing",
                })

        if not wanted_types or "invoice" in wanted_types:
            inv_qs = Invoice.objects.filter(organization=org).select_related("customer")
            if status_filter:
                inv_qs = inv_qs.filter(status=status_filter)
            if search:
                inv_qs = inv_qs.filter(
                    Q(invoice_number__icontains=search) | Q(customer__name__icontains=search)
                )
            for inv in inv_qs.iterator():
                rows.append({
                    "id": f"inv-{inv.pk}",
                    "type": "invoice",
                    "reference": inv.invoice_number or f"INV-{inv.pk}",
                    "counterparty": inv.customer.name if inv.customer else "\u2014",
                    "date": (inv.issue_date or inv.created_at.date()).isoformat(),
                    "amount": str(inv.total_amount),
                    "status": inv.status,
                    "direction": "incoming",
                })

        if not wanted_types or "bill_payment" in wanted_types:
            bp_qs = BillPayment.objects.filter(bill__organization=org).select_related("bill__vendor")
            if search:
                bp_qs = bp_qs.filter(
                    Q(bill__bill_number__icontains=search) | Q(bill__vendor__name__icontains=search)
                )
            if not status_filter or status_filter == "completed":
                for bp in bp_qs.iterator():
                    rows.append({
                        "id": f"bp-{bp.pk}",
                        "type": "bill_payment",
                        "reference": bp.bill.bill_number or f"BILL-{bp.bill_id}",
                        "counterparty": bp.bill.vendor.name if bp.bill.vendor else "\u2014",
                        "date": bp.payment_date.isoformat(),
                        "amount": str(bp.amount),
                        "status": "completed",
                        "direction": "outgoing",
                    })

        if not wanted_types or "invoice_payment" in wanted_types:
            ip_qs = InvoicePayment.objects.filter(invoice__organization=org).select_related("invoice__customer")
            if search:
                ip_qs = ip_qs.filter(
                    Q(invoice__invoice_number__icontains=search) | Q(invoice__customer__name__icontains=search)
                )
            if not status_filter or status_filter == "completed":
                for ip in ip_qs.iterator():
                    rows.append({
                        "id": f"ip-{ip.pk}",
                        "type": "invoice_payment",
                        "reference": ip.invoice.invoice_number or f"INV-{ip.invoice_id}",
                        "counterparty": ip.invoice.customer.name if ip.invoice.customer else "\u2014",
                        "date": ip.payment_date.isoformat(),
                        "amount": str(ip.amount),
                        "status": "completed",
                        "direction": "incoming",
                    })

        # --- Sort ---
        reverse = desc
        if sort_key == "amount":
            rows.sort(key=lambda r: Decimal(r["amount"]), reverse=reverse)
        else:
            rows.sort(key=lambda r: r.get(sort_key, ""), reverse=reverse)

        # --- Paginate ---
        total = len(rows)
        start = (page - 1) * page_size
        end = start + page_size
        page_rows = rows[start:end]

        # --- Summary counts ---
        type_counts = {}
        for r in rows:
            type_counts[r["type"]] = type_counts.get(r["type"], 0) + 1

        return Response({
            "count": total,
            "page": page,
            "page_size": page_size,
            "type_counts": type_counts,
            "results": page_rows,
        })


# ---------------------------------------------------------------------------
# Payment Voucher
# ---------------------------------------------------------------------------


class PaymentVoucherViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "finance.bills"
    rbac_action_map = _FINANCE_ACTION_MAP
    filterset_class = PaymentVoucherFilter
    search_fields = ["voucher_number", "vendor__name", "description", "notes"]
    ordering_fields = ["voucher_number", "issue_date", "amount", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return _scoped_payment_voucher_queryset(self.request).select_related("vendor", "bill", "bill__property", "approved_by")

    def get_serializer_class(self):
        if self.action == "list":
            return PaymentVoucherListSerializer
        if self.action in ("create", "update", "partial_update"):
            return PaymentVoucherWriteSerializer
        return PaymentVoucherDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        voucher = self.get_object()
        if voucher.status not in (PaymentVoucher.Status.DRAFT, PaymentVoucher.Status.PENDING):
            return Response(
                {"detail": "Only draft or pending vouchers can be approved."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        voucher.status = PaymentVoucher.Status.APPROVED
        voucher.approved_by = request.user
        voucher.approved_at = timezone.now()
        voucher.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
        return Response(PaymentVoucherDetailSerializer(voucher).data)

    @action(detail=True, methods=["post"])
    def void(self, request, pk=None):
        voucher = self.get_object()
        if voucher.status in (PaymentVoucher.Status.VOIDED, PaymentVoucher.Status.PAID):
            return Response(
                {"detail": "This voucher cannot be voided."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        voucher.status = PaymentVoucher.Status.VOIDED
        voucher.save(update_fields=["status", "updated_at"])
        return Response(PaymentVoucherDetailSerializer(voucher).data)

    @action(detail=True, methods=["post"])
    def dispute(self, request, pk=None):
        voucher = self.get_object()
        if voucher.status in (PaymentVoucher.Status.PAID, PaymentVoucher.Status.VOIDED):
            return Response(
                {"detail": "This voucher cannot be disputed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        reason = request.data.get("reason", "")
        voucher.status = PaymentVoucher.Status.DISPUTED
        if reason:
            voucher.notes = (voucher.notes + f"\nDispute reason: {reason}").strip()
        voucher.save(update_fields=["status", "notes", "updated_at"])
        return Response(PaymentVoucherDetailSerializer(voucher).data)


# ---------------------------------------------------------------------------
# Payment Runs
# ---------------------------------------------------------------------------

class PaymentRunFilter(filters.FilterSet):
    scheduled_after = filters.DateFilter(field_name="scheduled_date", lookup_expr="gte")
    scheduled_before = filters.DateFilter(field_name="scheduled_date", lookup_expr="lte")

    class Meta:
        model = PaymentRun
        fields = ["status"]


class PaymentRunViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "finance.bills"
    rbac_action_map = _FINANCE_ACTION_MAP
    filterset_class = PaymentRunFilter
    search_fields = ["batch_id", "funding_account_label", "notes"]
    ordering_fields = ["batch_id", "scheduled_date", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return (
            _scope_queryset_for_request(self.request, PaymentRun.objects.all())
            .select_related("funding_account", "created_by", "executed_by")
            .annotate(
                total_value_ann=Coalesce(Sum("vouchers__amount"), Decimal("0")),
                payment_count_ann=Count("vouchers"),
            )
        )

    def get_serializer_class(self):
        if self.action == "list":
            return PaymentRunListSerializer
        if self.action in ("create", "update", "partial_update"):
            return PaymentRunWriteSerializer
        return PaymentRunDetailSerializer

    def perform_create(self, serializer):
        serializer.save(
            organization=_user_org(self.request),
            created_by=self.request.user,
        )

    @action(detail=True, methods=["post"])
    def execute(self, request, pk=None):
        run = self.get_object()
        if run.status not in (PaymentRun.Status.DRAFT, PaymentRun.Status.SCHEDULED):
            return Response(
                {"detail": "Only draft or scheduled runs can be executed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if run.payment_count == 0:
            return Response(
                {"detail": "Cannot execute a run with no vouchers."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        run.status = PaymentRun.Status.PROCESSING
        run.executed_by = request.user
        run.executed_at = timezone.now()
        run.save(update_fields=["status", "executed_by", "executed_at", "updated_at"])

        # Mark all vouchers as paid
        run.vouchers.filter(status=PaymentVoucher.Status.APPROVED).update(
            status=PaymentVoucher.Status.PAID,
            paid_at=timezone.now(),
        )

        run.status = PaymentRun.Status.COMPLETED
        run.save(update_fields=["status", "updated_at"])
        return Response(PaymentRunDetailSerializer(run).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        run = self.get_object()
        if run.status in (PaymentRun.Status.COMPLETED, PaymentRun.Status.CANCELLED):
            return Response(
                {"detail": "This run cannot be cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        run.status = PaymentRun.Status.CANCELLED
        run.save(update_fields=["status", "updated_at"])
        return Response(PaymentRunDetailSerializer(run).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Finance Lead / Director sign-off on a payment run."""
        run = self.get_object()
        if run.status not in (PaymentRun.Status.DRAFT, PaymentRun.Status.SCHEDULED):
            return Response(
                {"detail": "Only draft or scheduled runs can be approved."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if run.payment_count == 0:
            return Response(
                {"detail": "Cannot approve a run with no vouchers."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        funding_balance = request.data.get("funding_balance")
        run.approved_by = request.user
        run.approved_at = timezone.now()
        run.status = PaymentRun.Status.SCHEDULED
        update_fields = ["approved_by", "approved_at", "status", "updated_at"]
        if funding_balance is not None:
            run.funding_balance = funding_balance
            update_fields.append("funding_balance")
        run.save(update_fields=update_fields)
        return Response(PaymentRunDetailSerializer(run).data)

    @action(detail=True, methods=["get"], url_path="export-csv")
    def export_csv(self, request, pk=None):
        """Export batch as CSV for bank portal upload."""
        import csv

        from django.http import HttpResponse

        run = self.get_object()
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{run.batch_id}.csv"'

        writer = csv.writer(response)
        writer.writerow([
            "Voucher Ref", "Payee", "Bank Name", "Account Number",
            "Amount", "Payment Method", "Description",
        ])

        for v in run.vouchers.select_related("vendor").all():
            writer.writerow([
                v.voucher_number,
                v.vendor.name if v.vendor_id else "",
                v.vendor.bank_name if v.vendor_id else "",
                v.vendor.bank_account_number if v.vendor_id else "",
                str(v.amount),
                v.get_payment_method_display(),
                v.description[:200] if v.description else "",
            ])

        return response

    @action(detail=True, methods=["post"], url_path="remove-voucher")
    def remove_voucher(self, request, pk=None):
        """Remove a single voucher from a draft/scheduled run."""
        run = self.get_object()
        if run.status not in (PaymentRun.Status.DRAFT, PaymentRun.Status.SCHEDULED):
            return Response(
                {"detail": "Can only modify draft or scheduled runs."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        voucher_id = request.data.get("voucher_id")
        if not voucher_id:
            return Response(
                {"detail": "voucher_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        run.vouchers.remove(voucher_id)
        return Response(PaymentRunDetailSerializer(run).data)


# ---------------------------------------------------------------------------
# Payment Receipts
# ---------------------------------------------------------------------------

class PaymentReceiptFilter(filters.FilterSet):
    date_from = filters.DateFilter(field_name="payment_date", lookup_expr="gte")
    date_to = filters.DateFilter(field_name="payment_date", lookup_expr="lte")

    class Meta:
        model = PaymentReceipt
        fields = ["status", "vendor", "payment_method"]


class PaymentReceiptViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "finance.bills"
    rbac_action_map = _FINANCE_ACTION_MAP
    filterset_class = PaymentReceiptFilter
    search_fields = ["receipt_number", "transaction_reference", "vendor__name", "description"]
    ordering_fields = ["receipt_number", "payment_date", "amount", "created_at"]
    ordering = ["-payment_date"]

    def get_queryset(self):
        return (
            _scope_queryset_for_request(self.request, PaymentReceipt.objects.all())
            .select_related("vendor", "voucher", "payment_run", "created_by")
        )

    def get_serializer_class(self):
        if self.action == "list":
            return PaymentReceiptListSerializer
        if self.action in ("create", "update", "partial_update"):
            return PaymentReceiptWriteSerializer
        return PaymentReceiptDetailSerializer

    def perform_create(self, serializer):
        serializer.save(
            organization=_user_org(self.request),
            created_by=self.request.user,
        )


# ---------------------------------------------------------------------------
# Banking
# ---------------------------------------------------------------------------

class BankLiquidityView(APIView):
    """Aggregated liquidity overview across all active bank accounts."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        org = _user_org(request)
        active_accounts = BankAccount.objects.filter(organization=org, status="active")

        total_cash = active_accounts.aggregate(
            total=Coalesce(Sum("current_balance"), Decimal("0"))
        )["total"]

        # Primary operations account = highest balance
        primary = active_accounts.order_by("-current_balance").first()

        # Pending outflow = total of approved (not yet executed) payment runs
        from .models import PaymentRun
        pending_runs = PaymentRun.objects.filter(
            organization=org,
            status__in=["draft", "scheduled"],
        )
        pending_outflow = Decimal("0")
        for run in pending_runs:
            pending_outflow += run.total_value

        return Response({
            "total_cash_on_hand": str(total_cash),
            "account_count": active_accounts.count(),
            "primary_account": {
                "id": primary.id,
                "account_name": primary.account_name,
                "bank_name": primary.bank_name,
                "current_balance": str(primary.current_balance),
            } if primary else None,
            "pending_outflow": str(pending_outflow),
            "pending_run_count": pending_runs.count(),
        })


class BankAccountFilter(filters.FilterSet):
    class Meta:
        model = BankAccount
        fields = ["status", "account_type", "currency"]


class BankAccountViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "finance.bills"
    rbac_action_map = _FINANCE_ACTION_MAP
    filterset_class = BankAccountFilter
    search_fields = ["account_name", "bank_name", "account_number", "branch"]
    ordering_fields = ["account_name", "bank_name", "current_balance", "created_at"]
    ordering = ["bank_name", "account_name"]

    def get_queryset(self):
        return _scope_queryset_for_request(self.request, BankAccount.objects.all()).select_related("gl_account")

    def get_serializer_class(self):
        if self.action == "list":
            return BankAccountListSerializer
        if self.action in ("create", "update", "partial_update"):
            return BankAccountWriteSerializer
        return BankAccountDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


class BankTransactionSummaryView(APIView):
    """Aggregated transaction intelligence for the header."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        org = _user_org(request)
        qs = BankTransaction.objects.filter(organization=org)

        # Apply same filters as the list
        bank_account = request.query_params.get("bank_account")
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        if bank_account:
            qs = qs.filter(bank_account_id=bank_account)
        if date_from:
            qs = qs.filter(transaction_date__gte=date_from)
        if date_to:
            qs = qs.filter(transaction_date__lte=date_to)

        total_inflow = qs.filter(transaction_type="credit").aggregate(
            total=Coalesce(Sum("amount"), Decimal("0"))
        )["total"]
        total_outflow = qs.filter(transaction_type="debit").aggregate(
            total=Coalesce(Sum("amount"), Decimal("0"))
        )["total"]

        total_count = qs.count()
        reconciled_count = qs.filter(status="reconciled").count()

        return Response({
            "total_inflow": str(total_inflow),
            "total_outflow": str(total_outflow),
            "total_count": total_count,
            "reconciled_count": reconciled_count,
            "reconciliation_pct": round((reconciled_count / total_count * 100) if total_count > 0 else 0, 1),
        })


class BankTransactionMatchView(APIView):
    """Suggest internal vouchers/receipts that could match a bank transaction."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        org = _user_org(request)
        txn = get_object_or_404(BankTransaction, pk=pk, organization=org)

        # Find vouchers with matching amount or date
        voucher_qs = PaymentVoucher.objects.filter(
            organization=org,
            status__in=["approved", "paid"],
        ).select_related("vendor")

        # Exact amount matches first, then same-date
        exact_amount = list(voucher_qs.filter(amount=txn.amount)[:5])
        same_date = list(
            voucher_qs.filter(issue_date=txn.transaction_date)
            .exclude(id__in=[v.id for v in exact_amount])[:5]
        )

        suggestions = []
        for v in exact_amount:
            suggestions.append({
                "id": v.id, "type": "voucher",
                "number": v.voucher_number,
                "counterparty": v.vendor.name if v.vendor_id else "",
                "amount": str(v.amount),
                "date": str(v.issue_date),
                "match_reason": "amount",
            })
        for v in same_date:
            suggestions.append({
                "id": v.id, "type": "voucher",
                "number": v.voucher_number,
                "counterparty": v.vendor.name if v.vendor_id else "",
                "amount": str(v.amount),
                "date": str(v.issue_date),
                "match_reason": "date",
            })

        return Response({"suggestions": suggestions})


class BankTransactionLinkView(APIView):
    """Link a bank transaction to a voucher and mark as reconciled."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        org = _user_org(request)
        txn = get_object_or_404(BankTransaction, pk=pk, organization=org)

        voucher_id = request.data.get("voucher_id")
        gl_account_id = request.data.get("gl_account_id")

        if voucher_id:
            voucher = get_object_or_404(PaymentVoucher, pk=voucher_id, organization=org)
            txn.voucher = voucher
            txn.status = BankTransaction.Status.RECONCILED
            if voucher.status == "approved":
                voucher.status = PaymentVoucher.Status.PAID
                voucher.paid_at = timezone.now()
                voucher.save(update_fields=["status", "paid_at", "updated_at"])
            txn.save(update_fields=["voucher", "status", "updated_at"])
            return Response(BankTransactionDetailSerializer(txn).data)

        if gl_account_id:
            # Categorize as internal — mark reconciled without voucher link
            txn.status = BankTransaction.Status.RECONCILED
            txn.notes = (txn.notes + f"\nCategorized to GL #{gl_account_id}").strip()
            txn.save(update_fields=["status", "notes", "updated_at"])
            return Response(BankTransactionDetailSerializer(txn).data)

        return Response(
            {"detail": "voucher_id or gl_account_id is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )


class BankTransactionFilter(filters.FilterSet):
    date_from = filters.DateFilter(field_name="transaction_date", lookup_expr="gte")
    date_to = filters.DateFilter(field_name="transaction_date", lookup_expr="lte")
    amount_min = filters.NumberFilter(field_name="amount", lookup_expr="gte")
    amount_max = filters.NumberFilter(field_name="amount", lookup_expr="lte")

    class Meta:
        model = BankTransaction
        fields = ["bank_account", "transaction_type", "status"]


class BankTransactionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "finance.bills"
    rbac_action_map = _FINANCE_ACTION_MAP
    filterset_class = BankTransactionFilter
    search_fields = ["reference", "description", "counterparty"]
    ordering_fields = ["transaction_date", "amount", "created_at"]
    ordering = ["-transaction_date"]

    def get_queryset(self):
        return (
            _scope_queryset_for_request(self.request, BankTransaction.objects.all())
            .select_related("bank_account", "receipt", "voucher")
        )

    def get_serializer_class(self):
        if self.action == "list":
            return BankTransactionListSerializer
        if self.action in ("create", "update", "partial_update"):
            return BankTransactionWriteSerializer
        return BankTransactionDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


class AgingReportView(APIView):
    """Aging report for accounts payable — categorizes unpaid vouchers by age."""
    permission_classes = [IsAuthenticated]

    def get(self, request):

        org = _user_org(request)

        # Optional as-of date
        as_of = request.query_params.get("as_of_date")
        if as_of:
            today = parse_date(as_of) or timezone.now().date()
        else:
            today = timezone.now().date()

        unpaid = PaymentVoucher.objects.filter(
            organization=org,
            status__in=["draft", "pending", "approved", "disputed"],
            issue_date__lte=today,
        ).select_related("vendor", "bill", "bill__property")

        # Optional project/property filter
        property_id = request.query_params.get("property")
        if property_id:
            unpaid = unpaid.filter(bill__property_id=property_id)

        buckets = {
            "current": {"label": "0–30 Days", "min": 0, "max": 30, "total": Decimal("0"), "count": 0, "items": []},
            "overdue_30": {"label": "31–60 Days", "min": 31, "max": 60, "total": Decimal("0"), "count": 0, "items": []},
            "overdue_60": {"label": "61–90 Days", "min": 61, "max": 90, "total": Decimal("0"), "count": 0, "items": []},
            "overdue_90": {"label": "91+ Days", "min": 91, "max": 999999, "total": Decimal("0"), "count": 0, "items": []},
        }

        total_outstanding = Decimal("0")
        total_days = 0
        voucher_count = 0

        for v in unpaid:
            days = (today - v.issue_date).days
            total_outstanding += v.amount
            total_days += days
            voucher_count += 1

            item = {
                "id": v.id,
                "voucher_number": v.voucher_number,
                "vendor_name": v.vendor.name if v.vendor_id else "",
                "property_name": v.bill.property.name if v.bill_id and v.bill.property_id else None,
                "amount": str(v.amount),
                "issue_date": str(v.issue_date),
                "days_outstanding": days,
                "status": v.status,
                "priority": getattr(v, "priority", "standard"),
            }

            for key, bucket in buckets.items():
                if bucket["min"] <= days <= bucket["max"]:
                    bucket["total"] += v.amount
                    bucket["count"] += 1
                    bucket["items"].append(item)
                    break

        avg_days = round(total_days / voucher_count) if voucher_count > 0 else 0

        # Serialize bucket totals
        result_buckets = {}
        for key, bucket in buckets.items():
            result_buckets[key] = {
                "label": bucket["label"],
                "total": str(bucket["total"]),
                "count": bucket["count"],
                "items": bucket["items"],
            }

        return Response({
            "total_outstanding": str(total_outstanding),
            "voucher_count": voucher_count,
            "avg_days_to_pay": avg_days,
            "buckets": result_buckets,
        })


class BankTransactionAutoMatchView(APIView):
    """Auto-match unreconciled transactions to vouchers by amount + 3-day window."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        org = _user_org(request)
        bank_account_id = request.data.get("bank_account_id")
        if not bank_account_id:
            return Response({"detail": "bank_account_id required."}, status=status.HTTP_400_BAD_REQUEST)

        unmatched = BankTransaction.objects.filter(
            organization=org, bank_account_id=bank_account_id,
        ).exclude(status="reconciled").select_related("bank_account")

        matched_count = 0
        for txn in unmatched:
            # Find voucher with same amount within 3-day window
            from datetime import timedelta
            date_from = txn.transaction_date - timedelta(days=3)
            date_to = txn.transaction_date + timedelta(days=3)

            voucher = PaymentVoucher.objects.filter(
                organization=org,
                amount=txn.amount,
                status="approved",
                issue_date__gte=date_from,
                issue_date__lte=date_to,
            ).first()

            if voucher:
                txn.voucher = voucher
                txn.status = BankTransaction.Status.RECONCILED
                txn.save(update_fields=["voucher", "status", "updated_at"])
                voucher.status = PaymentVoucher.Status.PAID
                voucher.paid_at = timezone.now()
                voucher.save(update_fields=["status", "paid_at", "updated_at"])
                matched_count += 1

        return Response({
            "matched_count": matched_count,
            "message": f"Auto-matched {matched_count} transaction{'s' if matched_count != 1 else ''}.",
        })


class BankTransactionSplitLinkView(APIView):
    """Link a single bank transaction to multiple vouchers (split match)."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        org = _user_org(request)
        txn = get_object_or_404(BankTransaction, pk=pk, organization=org)
        voucher_ids = request.data.get("voucher_ids", [])

        if not voucher_ids:
            return Response({"detail": "voucher_ids required."}, status=status.HTTP_400_BAD_REQUEST)

        vouchers = PaymentVoucher.objects.filter(id__in=voucher_ids, organization=org, status="approved")
        total = sum(v.amount for v in vouchers)

        if abs(total - txn.amount) > Decimal("0.01"):
            return Response({
                "detail": f"Voucher total ({total}) does not match transaction amount ({txn.amount}). Difference: {abs(total - txn.amount)}",
                "voucher_total": str(total),
                "transaction_amount": str(txn.amount),
            }, status=status.HTTP_400_BAD_REQUEST)

        # Link first voucher to FK, mark all as paid
        txn.voucher = vouchers.first()
        txn.status = BankTransaction.Status.RECONCILED
        txn.notes = (txn.notes + f"\nSplit match: {', '.join(v.voucher_number for v in vouchers)}").strip()
        txn.save(update_fields=["voucher", "status", "notes", "updated_at"])

        for v in vouchers:
            v.status = PaymentVoucher.Status.PAID
            v.paid_at = timezone.now()
            v.save(update_fields=["status", "paid_at", "updated_at"])

        return Response(BankTransactionDetailSerializer(txn).data)


class ReconciliationOverviewView(APIView):
    """Aggregated reconciliation overview across all accounts."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        org = _user_org(request)

        # Book balance = sum of all active bank account current_balance
        book_balance = BankAccount.objects.filter(
            organization=org, status="active"
        ).aggregate(total=Coalesce(Sum("current_balance"), Decimal("0")))["total"]

        # Bank balance = sum of latest reconciliation statement_balance per account
        from django.db.models import OuterRef, Subquery
        latest_recon = (
            BankReconciliation.objects.filter(
                organization=org, bank_account=OuterRef("pk"), status="completed"
            ).order_by("-period_end").values("statement_balance")[:1]
        )
        bank_balance = Decimal("0")
        active_accounts = BankAccount.objects.filter(organization=org, status="active").annotate(
            latest_statement=Subquery(latest_recon)
        )
        for acct in active_accounts:
            if acct.latest_statement:
                bank_balance += acct.latest_statement

        # Unreconciled = transactions not yet reconciled
        unreconciled = BankTransaction.objects.filter(
            organization=org
        ).exclude(status="reconciled").count()

        # Active reconciliations in progress
        in_progress = BankReconciliation.objects.filter(
            organization=org, status="in_progress"
        ).count()

        difference = book_balance - bank_balance

        return Response({
            "book_balance": str(book_balance),
            "bank_balance": str(bank_balance),
            "difference": str(difference),
            "is_balanced": abs(difference) < Decimal("0.01"),
            "unreconciled_count": unreconciled,
            "in_progress_count": in_progress,
        })


class BankReconciliationFilter(filters.FilterSet):
    class Meta:
        model = BankReconciliation
        fields = ["bank_account", "status"]


class BankReconciliationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "finance.bills"
    rbac_action_map = _FINANCE_ACTION_MAP
    filterset_class = BankReconciliationFilter
    search_fields = ["notes"]
    ordering_fields = ["period_end", "created_at"]
    ordering = ["-period_end"]

    def get_queryset(self):
        return (
            _scope_queryset_for_request(self.request, BankReconciliation.objects.all())
            .select_related("bank_account", "created_by", "completed_by")
        )

    def get_serializer_class(self):
        if self.action == "list":
            return BankReconciliationListSerializer
        if self.action in ("create", "update", "partial_update"):
            return BankReconciliationWriteSerializer
        return BankReconciliationDetailSerializer

    def perform_create(self, serializer):
        serializer.save(
            organization=_user_org(self.request),
            created_by=self.request.user,
        )

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        recon = self.get_object()
        if recon.status != BankReconciliation.Status.IN_PROGRESS:
            return Response(
                {"detail": "Only in-progress reconciliations can be completed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        recon.status = BankReconciliation.Status.COMPLETED
        recon.completed_by = request.user
        recon.completed_at = timezone.now()
        recon.save(update_fields=["status", "completed_by", "completed_at", "updated_at"])
        return Response(BankReconciliationDetailSerializer(recon).data)


# --- Payroll → GL bridge viewsets ---


class PayrollGLMappingViewSet(viewsets.ModelViewSet):
    """CRUD for per-org payroll GL line-kind → account mappings.

    POST is idempotent on (organization, line_kind) — repeated POSTs update
    the existing mapping rather than creating duplicates.
    """

    serializer_class = PayrollGLMappingSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.payroll"
    ordering = ["line_kind"]

    def get_queryset(self):
        qs = PayrollGLMapping.objects.select_related("account").order_by("line_kind")
        org = _user_org(self.request)
        if not _is_superuser(self.request):
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs

    def perform_create(self, serializer):
        org = _user_org(self.request)
        kind = serializer.validated_data["line_kind"]
        account = serializer.validated_data["account"]
        instance, _ = PayrollGLMapping.objects.update_or_create(
            organization=org,
            line_kind=kind,
            defaults={"account": account},
        )
        serializer.instance = instance

    def perform_update(self, serializer):
        serializer.save()


class PayrollGLPostingViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only listing of payroll → GL postings for the current org."""

    serializer_class = PayrollGLPostingSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "hr.payroll"
    ordering = ["-posted_at", "-created_at"]
    filterset_fields = ["status", "payroll_run"]

    def get_queryset(self):
        qs = PayrollGLPosting.objects.select_related(
            "payroll_run", "journal_entry", "posted_by"
        ).order_by("-posted_at", "-created_at")
        org = _user_org(self.request)
        if not _is_superuser(self.request):
            if org:
                qs = qs.filter(organization=org)
            else:
                qs = qs.none()
        return qs
