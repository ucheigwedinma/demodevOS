from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.accounts.models import Organization
from apps.finance.models import (
    Account,
    AccountSubType,
    AccountType,
    JournalEntry,
    JournalSourceType,
    PayrollGLLineKind,
    PayrollGLMapping,
    PayrollGLPosting,
)
from apps.finance.payroll_gl import (
    bulk_sync_payroll_runs,
    post_payroll_run_to_gl,
    reconcile_payroll_run,
)
from apps.hr.models import PayrollRun


def _make_account(org, code, name, *, account_type=AccountType.EXPENSE,
                  sub_type=AccountSubType.OPERATING_EXPENSE):
    return Account.objects.create(
        organization=org,
        code=code,
        name=name,
        account_type=account_type,
        sub_type=sub_type,
    )


def _make_run(
    org,
    *,
    name="May Payroll",
    gross=Decimal("100000.00"),
    deductions=Decimal("20000.00"),
    net=Decimal("80000.00"),
    status=PayrollRun.Status.COMPLETED,
    period_start=date(2026, 5, 1),
    period_end=date(2026, 5, 31),
    run_date=None,
):
    return PayrollRun.objects.create(
        organization=org,
        name=name,
        period_start=period_start,
        period_end=period_end,
        run_date=run_date,
        status=status,
        total_gross=gross,
        total_deductions=deductions,
        total_net=net,
    )


class PayrollGLServiceTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Payroll GL Org")
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="gl-admin@example.com",
            email="gl-admin@example.com",
            password="Pass123!",
        )
        # CoA — three accounts the mappings will point at.
        self.salary_expense = _make_account(
            self.org, "6100", "Salaries Expense",
            account_type=AccountType.EXPENSE,
            sub_type=AccountSubType.OPERATING_EXPENSE,
        )
        self.deductions_payable = _make_account(
            self.org, "2110", "Employee Deductions Payable",
            account_type=AccountType.LIABILITY,
            sub_type=AccountSubType.CURRENT_LIABILITY,
        )
        self.net_payable = _make_account(
            self.org, "2120", "Net Salary Payable",
            account_type=AccountType.LIABILITY,
            sub_type=AccountSubType.CURRENT_LIABILITY,
        )

    def _seed_mappings(self):
        PayrollGLMapping.objects.create(
            organization=self.org,
            line_kind=PayrollGLLineKind.GROSS_SALARY,
            account=self.salary_expense,
        )
        PayrollGLMapping.objects.create(
            organization=self.org,
            line_kind=PayrollGLLineKind.EMPLOYEE_DEDUCTIONS,
            account=self.deductions_payable,
        )
        PayrollGLMapping.objects.create(
            organization=self.org,
            line_kind=PayrollGLLineKind.NET_PAYABLE,
            account=self.net_payable,
        )

    # ------------------------------------------------------------------
    # Posting behavior
    # ------------------------------------------------------------------

    def test_post_requires_all_mappings(self):
        # Only seed one of the three required kinds.
        PayrollGLMapping.objects.create(
            organization=self.org,
            line_kind=PayrollGLLineKind.GROSS_SALARY,
            account=self.salary_expense,
        )
        run = _make_run(self.org)
        with self.assertRaises(ValidationError) as cm:
            post_payroll_run_to_gl(run, self.user)
        msg = " ".join(cm.exception.messages) if hasattr(cm.exception, "messages") else str(cm.exception)
        self.assertIn("Missing GL mapping", msg)

    def test_post_creates_balanced_journal_entry(self):
        self._seed_mappings()
        run = _make_run(self.org)

        posting = post_payroll_run_to_gl(run, self.user)

        self.assertEqual(posting.status, PayrollGLPosting.Status.POSTED)
        journal = posting.journal_entry
        self.assertIsNotNone(journal)
        self.assertEqual(journal.source_type, JournalSourceType.PAYROLL)
        self.assertEqual(journal.source_id, run.id)
        self.assertEqual(journal.status, JournalEntry.Status.POSTED)

        lines = list(journal.lines.all())
        self.assertEqual(len(lines), 3)

        debits = sum((line.debit_amount for line in lines), Decimal("0.00"))
        credits = sum((line.credit_amount for line in lines), Decimal("0.00"))
        self.assertEqual(debits, Decimal("100000.00"))
        self.assertEqual(credits, Decimal("100000.00"))

        # First line is the expense debit
        first = lines[0]
        self.assertEqual(first.account_id, self.salary_expense.id)
        self.assertEqual(first.debit_amount, Decimal("100000.00"))
        self.assertEqual(first.credit_amount, Decimal("0.00"))

    def test_post_skips_deductions_line_when_zero(self):
        self._seed_mappings()
        run = _make_run(
            self.org,
            gross=Decimal("50000.00"),
            deductions=Decimal("0.00"),
            net=Decimal("50000.00"),
        )

        posting = post_payroll_run_to_gl(run, self.user)

        lines = list(posting.journal_entry.lines.all())
        self.assertEqual(len(lines), 2)
        account_ids = {line.account_id for line in lines}
        self.assertIn(self.salary_expense.id, account_ids)
        self.assertIn(self.net_payable.id, account_ids)
        self.assertNotIn(self.deductions_payable.id, account_ids)

    def test_post_requires_completed_run(self):
        self._seed_mappings()
        run = _make_run(self.org, status=PayrollRun.Status.DRAFT)
        with self.assertRaises(ValidationError):
            post_payroll_run_to_gl(run, self.user)

    def test_double_post_is_rejected(self):
        self._seed_mappings()
        run = _make_run(self.org)
        post_payroll_run_to_gl(run, self.user)

        with self.assertRaises(ValidationError) as cm:
            post_payroll_run_to_gl(run, self.user)
        msg = " ".join(cm.exception.messages) if hasattr(cm.exception, "messages") else str(cm.exception)
        self.assertIn("already posted", msg)

    # ------------------------------------------------------------------
    # Reconcile / reversal
    # ------------------------------------------------------------------

    def test_reconcile_creates_reversal_and_reposts(self):
        self._seed_mappings()
        run = _make_run(self.org)
        original = post_payroll_run_to_gl(run, self.user)
        original_entry_id = original.journal_entry_id

        new_posting = reconcile_payroll_run(run, self.user)

        # Old entry must be REVERSED, and there should be a reversal entry
        # that points back to it.
        original_entry = JournalEntry.objects.get(pk=original_entry_id)
        self.assertEqual(original_entry.status, JournalEntry.Status.REVERSED)
        reversal = JournalEntry.objects.filter(
            reversed_entry=original_entry, is_reversal=True
        ).first()
        self.assertIsNotNone(reversal)

        # New posting must point at a fresh, balanced journal entry.
        self.assertEqual(new_posting.status, PayrollGLPosting.Status.POSTED)
        self.assertNotEqual(new_posting.journal_entry_id, original_entry_id)
        new_entry = new_posting.journal_entry
        debits = sum((line.debit_amount for line in new_entry.lines.all()), Decimal("0.00"))
        credits = sum((line.credit_amount for line in new_entry.lines.all()), Decimal("0.00"))
        self.assertEqual(debits, credits)

    # ------------------------------------------------------------------
    # Bulk sync
    # ------------------------------------------------------------------

    def test_bulk_sync_posts_only_unposted_completed_runs(self):
        self._seed_mappings()

        already_posted = _make_run(self.org, name="Run A")
        post_payroll_run_to_gl(already_posted, self.user)

        unposted_b = _make_run(self.org, name="Run B")
        unposted_c = _make_run(self.org, name="Run C")

        result = bulk_sync_payroll_runs(self.org, self.user)

        self.assertEqual(sorted(result["posted"]), sorted([unposted_b.id, unposted_c.id]))
        self.assertIn(already_posted.id, result["skipped"])
        self.assertEqual(result["errors"], [])

    # ------------------------------------------------------------------
    # Cross-org safety on mappings
    # ------------------------------------------------------------------

    def test_mapping_account_must_be_same_org(self):
        other_org = Organization.objects.create(name="Other Org")
        foreign_account = _make_account(other_org, "6100", "Foreign Salaries")

        mapping = PayrollGLMapping(
            organization=self.org,
            line_kind=PayrollGLLineKind.GROSS_SALARY,
            account=foreign_account,
        )
        with self.assertRaises(ValidationError):
            mapping.clean()
