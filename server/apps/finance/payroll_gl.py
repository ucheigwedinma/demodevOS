"""Service layer for posting payroll runs to the general ledger.

This module owns the rules for translating a completed PayrollRun into
a balanced double-entry JournalEntry using the org's PayrollGLMapping
configuration. All write operations are wrapped in a transaction so
posting either fully succeeds or leaves no partial GL state behind.
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.hr.models import PayrollRun

from .models import (
    JournalEntry,
    JournalLine,
    JournalSourceType,
    PayrollGLLineKind,
    PayrollGLMapping,
    PayrollGLPosting,
)

# Tolerance used when checking that debits equal credits.
BALANCE_TOLERANCE = Decimal("0.01")

# Order matters — used to build a stable journal entry across runs.
REQUIRED_KINDS = (
    PayrollGLLineKind.GROSS_SALARY,
    PayrollGLLineKind.EMPLOYEE_DEDUCTIONS,
    PayrollGLLineKind.NET_PAYABLE,
)


def _amount(value) -> Decimal:
    """Coerce a model decimal field to a Decimal, defaulting to 0.00."""
    if value is None:
        return Decimal("0.00")
    return Decimal(value)


def _mappings_for_org(organization) -> dict[str, PayrollGLMapping]:
    """Return a {line_kind: mapping} dict for the org, validating all required kinds exist."""
    mappings = {
        m.line_kind: m
        for m in PayrollGLMapping.objects.select_related("account").filter(organization=organization)
    }
    for kind in REQUIRED_KINDS:
        if kind not in mappings:
            raise ValidationError(f"Missing GL mapping for {kind}")
    return mappings


def _existing_posted(run: PayrollRun) -> PayrollGLPosting | None:
    """Return the existing POSTED posting for this run, if any."""
    posting = getattr(run, "gl_posting", None)
    if posting is None:
        return None
    if posting.status == PayrollGLPosting.Status.POSTED:
        return posting
    return None


def post_payroll_run_to_gl(run: PayrollRun, user) -> PayrollGLPosting:
    """Create a balanced JournalEntry for a completed PayrollRun.

    Returns the resulting PayrollGLPosting row. Raises ValidationError
    when configuration is missing, the run isn't completed, or it's
    already been posted.
    """
    if run.status != PayrollRun.Status.COMPLETED:
        raise ValidationError("Only completed payroll runs can be posted to the GL.")

    if _existing_posted(run) is not None:
        raise ValidationError("Run already posted — use reconcile to repost.")

    organization = run.organization
    mappings = _mappings_for_org(organization)

    gross = _amount(run.total_gross)
    deductions = _amount(run.total_deductions)
    net = _amount(run.total_net)

    entry_date = run.run_date or run.period_end
    description = f"Payroll posting — {run.name}"
    reference = (run.name or "")[:100]

    with transaction.atomic():
        journal = JournalEntry.objects.create(
            organization=organization,
            entry_date=entry_date,
            description=description,
            reference=reference,
            source_type=JournalSourceType.PAYROLL,
            source_id=run.id,
            status=JournalEntry.Status.POSTED,
            posted_at=timezone.now(),
            posted_by=user,
            created_by=user,
        )

        line_number = 1

        # Debit: gross salary expense
        JournalLine.objects.create(
            journal=journal,
            line_number=line_number,
            account=mappings[PayrollGLLineKind.GROSS_SALARY].account,
            debit_amount=gross,
            credit_amount=Decimal("0.00"),
            memo="Gross salary",
        )
        line_number += 1

        # Credit: employee deductions payable (skip when zero)
        if deductions > 0:
            JournalLine.objects.create(
                journal=journal,
                line_number=line_number,
                account=mappings[PayrollGLLineKind.EMPLOYEE_DEDUCTIONS].account,
                debit_amount=Decimal("0.00"),
                credit_amount=deductions,
                memo="Employee deductions",
            )
            line_number += 1

        # Credit: net salary payable
        JournalLine.objects.create(
            journal=journal,
            line_number=line_number,
            account=mappings[PayrollGLLineKind.NET_PAYABLE].account,
            debit_amount=Decimal("0.00"),
            credit_amount=net,
            memo="Net salary payable",
        )

        debit_total = sum(
            (line.debit_amount for line in journal.lines.all()),
            Decimal("0.00"),
        )
        credit_total = sum(
            (line.credit_amount for line in journal.lines.all()),
            Decimal("0.00"),
        )
        if abs(debit_total - credit_total) > BALANCE_TOLERANCE:
            raise ValidationError(
                f"Payroll journal does not balance: debits={debit_total} credits={credit_total}."
            )

        posting, _ = PayrollGLPosting.objects.update_or_create(
            payroll_run=run,
            defaults={
                "organization": organization,
                "journal_entry": journal,
                "status": PayrollGLPosting.Status.POSTED,
                "posted_at": timezone.now(),
                "posted_by": user,
                "error_message": "",
            },
        )

    return posting


def reconcile_payroll_run(run: PayrollRun, user) -> PayrollGLPosting:
    """Reverse an existing posted journal and create a fresh one.

    When no posted entry exists, this is equivalent to a fresh post.
    """
    posting = getattr(run, "gl_posting", None)
    old_entry = (
        posting.journal_entry
        if posting and posting.journal_entry and posting.status == PayrollGLPosting.Status.POSTED
        else None
    )

    if old_entry is not None:
        with transaction.atomic():
            reversal = JournalEntry.objects.create(
                organization=old_entry.organization,
                entry_date=timezone.now().date(),
                description=f"Reversal of {old_entry.journal_number} — {old_entry.description}",
                reference=old_entry.reference,
                source_type=JournalSourceType.PAYROLL,
                source_id=old_entry.source_id,
                status=JournalEntry.Status.POSTED,
                posted_at=timezone.now(),
                posted_by=user,
                created_by=user,
                is_reversal=True,
                reversed_entry=old_entry,
            )

            for idx, line in enumerate(old_entry.lines.all(), start=1):
                JournalLine.objects.create(
                    journal=reversal,
                    line_number=idx,
                    account=line.account,
                    debit_amount=line.credit_amount,
                    credit_amount=line.debit_amount,
                    memo=f"Reversal: {line.memo}" if line.memo else "Reversal",
                    department=line.department,
                    cost_center=line.cost_center,
                )

            old_entry.status = JournalEntry.Status.REVERSED
            old_entry.save(update_fields=["status", "updated_at"])

            posting.status = PayrollGLPosting.Status.REVERSED
            posting.save(update_fields=["status", "updated_at"])

    return post_payroll_run_to_gl(run, user)


def bulk_sync_payroll_runs(organization, user) -> dict:
    """Post every completed PayrollRun in the org that is not yet posted."""
    posted: list[int] = []
    skipped: list[int] = []
    errors: list[dict] = []

    runs = PayrollRun.objects.filter(
        organization=organization,
        status=PayrollRun.Status.COMPLETED,
    ).select_related("organization")

    for run in runs:
        existing = getattr(run, "gl_posting", None)
        if existing and existing.status == PayrollGLPosting.Status.POSTED:
            skipped.append(run.id)
            continue
        try:
            post_payroll_run_to_gl(run, user)
            posted.append(run.id)
        except ValidationError as exc:
            msg = " ".join(exc.messages) if hasattr(exc, "messages") else str(exc)
            errors.append({"run_id": run.id, "error": msg})

    return {"posted": posted, "skipped": skipped, "errors": errors}
