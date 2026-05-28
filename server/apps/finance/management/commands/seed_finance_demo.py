"""
Seed realistic demo data for the Finance dashboard.

Usage:
    python manage.py seed_finance_demo            # uses current user's org
    python manage.py seed_finance_demo --flush    # wipe previous seed data first

This is temporary dev data — safe to delete.
"""

import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import Organization
from apps.finance.models import (
    Account,
    AccountSubType,
    AccountType,
    Bill,
    BillLineItem,
    BillPayment,
    Budget,
    BudgetLineItem,
    Customer,
    Invoice,
    InvoiceLineItem,
    InvoicePayment,
)
from apps.procurement.models import Vendor

DEFAULT_YEAR = date.today().year

# ── Vendors (expense side) ───────────────────────────────────────────────
VENDOR_DATA = [
    ("Al Habtoor Contracting", "contracting"),
    ("Emirates Steel Industries", "materials"),
    ("ALEC Engineering", "contracting"),
    ("National Paints", "materials"),
    ("Gulf Electrical Systems", "subcontractor"),
    ("Desert Landscaping Co.", "subcontractor"),
    ("Consolidated Consultants", "professional"),
    ("RAK Ceramics Supply", "materials"),
]

# ── Customers (income side) ─────────────────────────────────────────────
CUSTOMER_DATA = [
    ("Emaar Properties", "enquiries@emaar.ae"),
    ("Aldar Properties", "accounts@aldar.com"),
    ("DAMAC Group", "finance@damac.com"),
    ("Sobha Realty", "payments@sobha.com"),
    ("Nakheel", "ap@nakheel.com"),
]

# ── Chart of Accounts (minimal set for budgets) ─────────────────────────
ACCOUNT_SEED = [
    ("5000", "Construction Materials", AccountType.EXPENSE, AccountSubType.COST_OF_GOODS_SOLD),
    ("5100", "Subcontractor Services", AccountType.EXPENSE, AccountSubType.COST_OF_GOODS_SOLD),
    ("5200", "Professional Fees", AccountType.EXPENSE, AccountSubType.OPERATING_EXPENSE),
    ("5300", "Equipment & Machinery", AccountType.EXPENSE, AccountSubType.OPERATING_EXPENSE),
    ("5400", "Site Operations", AccountType.EXPENSE, AccountSubType.OPERATING_EXPENSE),
    ("4000", "Property Sales Revenue", AccountType.REVENUE, AccountSubType.OPERATING_REVENUE),
    ("4100", "Management Fee Income", AccountType.REVENUE, AccountSubType.OTHER_REVENUE),
    ("1000", "Operating Cash", AccountType.ASSET, AccountSubType.CURRENT_ASSET),
]

# ── Monthly income/expense targets (makes the chart look alive) ─────────
# Roughly: income ramps up, expenses are steady with seasonal bumps.
MONTHLY_INCOME_TARGETS = [
    38000, 42000, 55000, 61000, 72000, 68000,
    85000, 78000, 91000, 95000, 88000, 102000,
]
MONTHLY_EXPENSE_TARGETS = [
    22000, 19000, 27000, 25000, 31000, 28000,
    34000, 30000, 36000, 33000, 29000, 38000,
]


def _jitter(base: int, pct: float = 0.15) -> Decimal:
    """Add realistic randomness to a target value."""
    factor = 1 + random.uniform(-pct, pct)
    return Decimal(str(round(base * factor, 2)))


class Command(BaseCommand):
    help = "Seed demo finance data for the Intelligence dashboard."

    def add_arguments(self, parser):
        parser.add_argument(
            "--organization-id",
            dest="organization_ids",
            action="append",
            type=int,
            help=(
                "Target a specific organization id. "
                "Repeat the flag to seed multiple organizations. "
                "If omitted, all organizations are seeded."
            ),
        )
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete previously seeded demo data before inserting.",
        )
        parser.add_argument(
            "--year",
            type=int,
            default=DEFAULT_YEAR,
            help="Year to seed data for (default: current year).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        organization_ids = options.get("organization_ids") or []
        org_qs = Organization.objects.order_by("id")
        if organization_ids:
            org_qs = org_qs.filter(id__in=organization_ids)
        orgs = list(org_qs)

        if not orgs:
            self.stderr.write(self.style.ERROR("No Organization found. Create one first."))
            return

        if organization_ids:
            found_ids = {org.id for org in orgs}
            missing_ids = [org_id for org_id in organization_ids if org_id not in found_ids]
            if missing_ids:
                self.stderr.write(
                    self.style.WARNING(
                        f"Skipping unknown organization ids: {', '.join(str(value) for value in missing_ids)}"
                    )
                )

        self.year = options["year"]

        for org in orgs:
            if options["flush"]:
                self._flush(org)

            self.stdout.write(f"Seeding finance demo data for org: {org} (year {self.year}) ...")

            vendors = self._seed_vendors(org)
            customers = self._seed_customers(org)
            accounts = self._seed_accounts(org)
            self._seed_bills_and_payments(org, vendors, accounts)
            self._seed_invoices_and_payments(org, customers)
            self._seed_budget(org, accounts)

        self.stdout.write(self.style.SUCCESS("Done! Navigate to /finance/dashboard to see it."))

    # ── Flush ────────────────────────────────────────────────────────────

    def _flush(self, org):
        self.stdout.write("Flushing previous demo data ...")
        BillPayment.objects.filter(bill__organization=org, bill__notes="[demo-seed]").delete()
        BillLineItem.objects.filter(bill__organization=org, bill__notes="[demo-seed]").delete()
        Bill.objects.filter(organization=org, notes="[demo-seed]").delete()

        InvoicePayment.objects.filter(invoice__organization=org, invoice__notes="[demo-seed]").delete()
        InvoiceLineItem.objects.filter(invoice__organization=org, invoice__notes="[demo-seed]").delete()
        Invoice.objects.filter(organization=org, notes="[demo-seed]").delete()

        BudgetLineItem.objects.filter(budget__organization=org, budget__notes="[demo-seed]").delete()
        Budget.objects.filter(organization=org, notes="[demo-seed]").delete()

        Customer.objects.filter(organization=org, notes="[demo-seed]").delete()
        Vendor.objects.filter(organization=org, notes="[demo-seed]").delete()
        Account.objects.filter(organization=org, description="[demo-seed]").delete()

        self.stdout.write("  Flushed.")

    # ── Vendors ──────────────────────────────────────────────────────────

    def _seed_vendors(self, org):
        vendors = []
        for name, category in VENDOR_DATA:
            v, _ = Vendor.objects.get_or_create(
                organization=org,
                name=name,
                defaults={"notes": "[demo-seed]", "category": category},
            )
            vendors.append(v)
        self.stdout.write(f"  {len(vendors)} vendors ready.")
        return vendors

    # ── Customers ────────────────────────────────────────────────────────

    def _seed_customers(self, org):
        customers = []
        for name, email in CUSTOMER_DATA:
            c, _ = Customer.objects.get_or_create(
                organization=org,
                name=name,
                defaults={"email": email, "notes": "[demo-seed]"},
            )
            customers.append(c)
        self.stdout.write(f"  {len(customers)} customers ready.")
        return customers

    # ── Accounts ─────────────────────────────────────────────────────────

    def _seed_accounts(self, org):
        accounts = {}
        for code, name, acct_type, sub_type in ACCOUNT_SEED:
            a, _ = Account.objects.get_or_create(
                organization=org,
                code=code,
                defaults={
                    "name": name,
                    "account_type": acct_type,
                    "sub_type": sub_type,
                    "description": "[demo-seed]",
                },
            )
            accounts[code] = a
        self.stdout.write(f"  {len(accounts)} GL accounts ready.")
        return accounts

    # ── Bills & Bill Payments ────────────────────────────────────────────

    def _seed_bills_and_payments(self, org, vendors, accounts):
        bill_count = 0
        payment_count = 0
        expense_accounts = [accounts[c] for c in ("5000", "5100", "5200", "5300", "5400")]
        today = date.today()

        for month_idx in range(12):
            month_num = month_idx + 1
            target = MONTHLY_EXPENSE_TARGETS[month_idx]
            month_date = date(self.year, month_num, 1)

            # Skip future months entirely (only applies to current year)
            if self.year == today.year and month_date > today.replace(day=1):
                break

            # 2-4 bills per month
            num_bills = random.randint(2, 4)
            remaining = target
            for j in range(num_bills):
                vendor = random.choice(vendors)
                acct = random.choice(expense_accounts)
                amount = _jitter(remaining // (num_bills - j), 0.25) if j < num_bills - 1 else Decimal(str(remaining))
                amount = max(amount, Decimal("500"))
                remaining -= int(amount)

                issue_day = random.randint(1, 20)
                issue = date(self.year, month_num, min(issue_day, 28))
                due = issue + timedelta(days=random.choice([15, 30, 45]))

                bill = Bill.objects.create(
                    organization=org,
                    vendor=vendor,
                    status=Bill.Status.APPROVED,
                    issue_date=issue,
                    due_date=due,
                    subtotal=amount,
                    total_amount=amount,
                    notes="[demo-seed]",
                )
                BillLineItem.objects.create(
                    bill=bill,
                    description=f"{acct.name} — {vendor.name}",
                    quantity=1,
                    unit_price=amount,
                    amount=amount,
                    account=acct,
                )
                bill_count += 1

                # Payment on a random day in the same month
                pay_day = random.randint(issue_day, 28)
                BillPayment.objects.create(
                    bill=bill,
                    amount=amount,
                    payment_date=date(self.year, month_num, pay_day),
                    payment_method="bank_transfer",
                )
                bill.status = Bill.Status.PAID
                bill.save(update_fields=["status"])
                payment_count += 1

        self.stdout.write(f"  {bill_count} bills, {payment_count} bill payments.")

    # ── Invoices & Invoice Payments ──────────────────────────────────────

    def _seed_invoices_and_payments(self, org, customers):
        inv_count = 0
        pay_count = 0
        today = date.today()

        for month_idx in range(12):
            month_num = month_idx + 1
            target = MONTHLY_INCOME_TARGETS[month_idx]
            month_date = date(self.year, month_num, 1)

            if self.year == today.year and month_date > today.replace(day=1):
                break

            # 2-3 invoices per month
            num_inv = random.randint(2, 3)
            remaining = target
            for j in range(num_inv):
                customer = random.choice(customers)
                amount = _jitter(remaining // (num_inv - j), 0.20) if j < num_inv - 1 else Decimal(str(remaining))
                amount = max(amount, Decimal("1000"))
                remaining -= int(amount)

                issue_day = random.randint(1, 15)
                issue = date(self.year, month_num, min(issue_day, 28))
                due = issue + timedelta(days=30)

                invoice = Invoice.objects.create(
                    organization=org,
                    customer=customer,
                    status=Invoice.Status.SENT,
                    issue_date=issue,
                    due_date=due,
                    subtotal=amount,
                    total_amount=amount,
                    notes="[demo-seed]",
                )
                InvoiceLineItem.objects.create(
                    invoice=invoice,
                    description=f"Property services — {customer.name}",
                    quantity=1,
                    unit_price=amount,
                    amount=amount,
                )
                inv_count += 1

                # Payment a few days after issue
                pay_day = random.randint(issue_day + 3, 28)
                InvoicePayment.objects.create(
                    invoice=invoice,
                    amount=amount,
                    payment_date=date(self.year, month_num, pay_day),
                    payment_method="bank_transfer",
                )
                invoice.status = Invoice.Status.PAID
                invoice.save(update_fields=["status"])
                pay_count += 1

        # Add a few unpaid invoices for receivable balance
        for i in range(3):
            customer = random.choice(customers)
            amount = _jitter(25000, 0.30)
            issue = today - timedelta(days=random.randint(10, 45))
            invoice = Invoice.objects.create(
                organization=org,
                customer=customer,
                status=Invoice.Status.SENT,
                issue_date=issue,
                due_date=issue + timedelta(days=30),
                subtotal=amount,
                total_amount=amount,
                notes="[demo-seed]",
            )
            InvoiceLineItem.objects.create(
                invoice=invoice,
                description=f"Outstanding — {customer.name}",
                quantity=1,
                unit_price=amount,
                amount=amount,
            )
            inv_count += 1

        # Add a few unpaid bills for payable balance
        for i in range(2):
            vendor_names = ["Al Habtoor Contracting", "ALEC Engineering"]
            vendor = Vendor.objects.filter(organization=org, name=vendor_names[i]).first()
            if not vendor:
                continue
            amount = _jitter(15000, 0.25)
            issue = today - timedelta(days=random.randint(5, 30))
            bill = Bill.objects.create(
                organization=org,
                vendor=vendor,
                status=Bill.Status.APPROVED,
                issue_date=issue,
                due_date=issue + timedelta(days=30),
                subtotal=amount,
                total_amount=amount,
                notes="[demo-seed]",
            )
            BillLineItem.objects.create(
                bill=bill,
                description=f"Pending — {vendor.name}",
                quantity=1,
                unit_price=amount,
                amount=amount,
            )

        self.stdout.write(f"  {inv_count} invoices, {pay_count} invoice payments.")

    # ── Budget ───────────────────────────────────────────────────────────

    def _seed_budget(self, org, accounts):
        budget, created = Budget.objects.get_or_create(
            organization=org,
            name=f"Operating Budget {self.year}",
            defaults={
                "status": Budget.Status.ACTIVE,
                "period_type": Budget.PeriodType.ANNUAL,
                "start_date": date(self.year, 1, 1),
                "end_date": date(self.year, 12, 31),
                "total_amount": Decimal("450000"),
                "warning_threshold_pct": Decimal("75"),
                "overspend_tolerance_pct": Decimal("10"),
                "notes": "[demo-seed]",
            },
        )

        if created:
            allocations = [
                ("5000", Decimal("120000")),
                ("5100", Decimal("110000")),
                ("5200", Decimal("65000")),
                ("5300", Decimal("85000")),
                ("5400", Decimal("70000")),
            ]
            for code, budgeted in allocations:
                if code in accounts:
                    BudgetLineItem.objects.create(
                        budget=budget,
                        account=accounts[code],
                        budgeted_amount=budgeted,
                    )
            self.stdout.write(f"  Budget '{budget.name}' created with {len(allocations)} line items.")
        else:
            self.stdout.write(f"  Budget '{budget.name}' already exists, skipped.")
