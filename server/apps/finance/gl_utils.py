from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Sum
from django.utils import timezone

from .models import JournalEntry, LedgerEntry


def _sum_journal_lines(journal: JournalEntry) -> tuple[Decimal, Decimal, int]:
    agg = journal.lines.aggregate(
        total_debit=Sum("debit_amount"),
        total_credit=Sum("credit_amount"),
        line_count=Count("id"),
    )
    debit = agg["total_debit"] or Decimal("0.00")
    credit = agg["total_credit"] or Decimal("0.00")
    line_count = agg["line_count"] or 0
    return debit, credit, line_count


def validate_journal_for_posting(journal: JournalEntry) -> tuple[Decimal, Decimal]:
    debit_total, credit_total, line_count = _sum_journal_lines(journal)

    if line_count < 2:
        raise ValueError("Journal entry must have at least two lines.")
    if debit_total <= 0 or credit_total <= 0:
        raise ValueError("Journal entry must contain both debit and credit values.")
    if debit_total != credit_total:
        raise ValueError(
            f"Journal entry is not balanced: debit {debit_total} != credit {credit_total}."
        )

    return debit_total, credit_total


@transaction.atomic
def post_journal_entry(journal_id: int, user) -> JournalEntry:
    journal = (
        JournalEntry.objects.select_for_update()
        .select_related("organization")
        .prefetch_related("lines")
        .get(id=journal_id)
    )

    if journal.status != JournalEntry.Status.DRAFT:
        raise ValueError("Only draft journal entries can be posted.")

    validate_journal_for_posting(journal)

    posted_at = timezone.now()
    ledger_rows = []

    for line in journal.lines.select_related("account", "department", "cost_center"):
        ledger_rows.append(
            LedgerEntry(
                organization=journal.organization,
                journal_entry=journal,
                journal_line=line,
                account=line.account,
                entry_date=journal.entry_date,
                debit_amount=line.debit_amount,
                credit_amount=line.credit_amount,
                description=line.memo or journal.description,
                source_type=journal.source_type,
                source_id=journal.source_id,
                department=line.department,
                cost_center=line.cost_center,
                posted_at=posted_at,
            )
        )

    LedgerEntry.objects.bulk_create(ledger_rows)

    journal.status = JournalEntry.Status.POSTED
    journal.posted_at = posted_at
    journal.posted_by = user
    journal.save(update_fields=["status", "posted_at", "posted_by", "updated_at"])

    return journal
