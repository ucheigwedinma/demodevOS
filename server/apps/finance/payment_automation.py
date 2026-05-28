from __future__ import annotations

from decimal import Decimal

from .gl_utils import post_journal_entry
from .models import (
    Account,
    AccountSubType,
    AccountType,
    BankAccount,
    InvoicePayment,
    JournalEntry,
    JournalLine,
    JournalSourceType,
    PaymentMethod,
)
from .seed_defaults import seed_accounts_for_org

ZERO_DECIMAL = Decimal("0.00")


def _active_accounts(org):
    return Account.objects.filter(organization=org, is_active=True)


def _resolve_receivable_account(org) -> Account:
    account = (
        _active_accounts(org).filter(code="1100").first()
        or _active_accounts(org).filter(name__iexact="Accounts Receivable").first()
        or _active_accounts(org).filter(code="1200").first()
        or _active_accounts(org).filter(name__iexact="Rent Receivable").first()
    )
    if account:
        return account

    seed_accounts_for_org(org)
    account = _active_accounts(org).filter(code="1100").first() or _active_accounts(org).filter(code="1200").first()
    if account:
        return account
    raise ValueError("Could not resolve a receivables account for payment posting.")


def _resolve_cash_equivalent_account(org) -> Account:
    account = (
        _active_accounts(org).filter(code="1000").first()
        or _active_accounts(org).filter(name__iexact="Cash and Cash Equivalents").first()
        or _active_accounts(org)
        .filter(account_type=AccountType.ASSET, sub_type=AccountSubType.CURRENT_ASSET)
        .order_by("code")
        .first()
    )
    if account:
        return account

    seed_accounts_for_org(org)
    account = _active_accounts(org).filter(code="1000").first()
    if account:
        return account
    raise ValueError("Could not resolve a cash-equivalent account for payment posting.")


def _resolve_debit_account(payment: InvoicePayment) -> Account:
    org = payment.invoice.organization
    if payment.payment_method == PaymentMethod.BANK_TRANSFER:
        bank_account = (
            BankAccount.objects.filter(
                organization=org,
                status=BankAccount.Status.ACTIVE,
                gl_account__isnull=False,
            )
            .select_related("gl_account")
            .order_by("id")
            .first()
        )
        if bank_account and bank_account.gl_account_id:
            return bank_account.gl_account
    return _resolve_cash_equivalent_account(org)


def ensure_payment_journal_posted(payment: InvoicePayment, *, user=None) -> tuple[JournalEntry, bool]:
    invoice = payment.invoice
    organization = invoice.organization
    existing = (
        JournalEntry.objects.filter(
            organization=organization,
            source_type=JournalSourceType.PAYMENT,
            source_id=payment.id,
        )
        .prefetch_related("lines", "ledger_entries")
        .first()
    )

    if existing and existing.status == JournalEntry.Status.POSTED:
        return existing, False

    debit_account = _resolve_debit_account(payment)
    credit_account = _resolve_receivable_account(organization)
    description = f"Payment received for invoice {invoice.invoice_number}"
    reference = payment.reference_number or invoice.invoice_number

    if existing is None:
        journal = JournalEntry.objects.create(
            organization=organization,
            entry_date=payment.payment_date,
            description=description,
            reference=reference,
            source_type=JournalSourceType.PAYMENT,
            source_id=payment.id,
            created_by=user,
        )
    else:
        journal = existing
        if journal.status != JournalEntry.Status.DRAFT:
            return journal, False
        journal.entry_date = payment.payment_date
        journal.description = description
        journal.reference = reference
        if user and journal.created_by_id is None:
            journal.created_by = user
            journal.save(update_fields=["entry_date", "description", "reference", "created_by", "updated_at"])
        else:
            journal.save(update_fields=["entry_date", "description", "reference", "updated_at"])
        journal.lines.all().delete()

    JournalLine.objects.create(
        journal=journal,
        line_number=1,
        account=debit_account,
        debit_amount=payment.amount,
        credit_amount=ZERO_DECIMAL,
        memo=f"Cash received for invoice {invoice.invoice_number}",
    )
    JournalLine.objects.create(
        journal=journal,
        line_number=2,
        account=credit_account,
        debit_amount=ZERO_DECIMAL,
        credit_amount=payment.amount,
        memo=f"Receivable settled for invoice {invoice.invoice_number}",
    )
    return post_journal_entry(journal.id, user), True
