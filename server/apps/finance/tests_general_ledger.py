from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import Organization

from .models import (
    Account,
    AccountSubType,
    AccountType,
    JournalEntry,
    JournalLine,
    LedgerEntry,
)


class GeneralLedgerViewTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Ledger Org")
        self.other_org = Organization.objects.create(name="Other Ledger Org")

        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="ledger-admin@example.com",
            email="ledger-admin@example.com",
            password="Pass123!",
        )
        profile = self.user.profile
        profile.organization = self.org
        profile.role = "admin"
        profile.mfa_enabled = True
        profile.save(update_fields=["organization", "role", "mfa_enabled"])

        self.client.force_authenticate(self.user)

        self.cash_account = self._create_account(self.org, "1000", "Cash")
        self.revenue_account = self._create_account(
            self.org,
            "4000",
            "Revenue",
            account_type=AccountType.REVENUE,
            sub_type=AccountSubType.OPERATING_REVENUE,
        )
        other_account = self._create_account(self.other_org, "1000", "Other Cash")

        self._create_ledger_row(
            organization=self.org,
            account=self.cash_account,
            entry_date=date(2026, 3, 5),
            debit_amount=Decimal("100.00"),
            description="Cash receipt 1",
        )
        self._create_ledger_row(
            organization=self.org,
            account=self.cash_account,
            entry_date=date(2026, 3, 4),
            credit_amount=Decimal("40.00"),
            description="Cash disbursement 1",
        )
        self._create_ledger_row(
            organization=self.org,
            account=self.revenue_account,
            entry_date=date(2026, 3, 3),
            credit_amount=Decimal("60.00"),
            description="Revenue recognition",
        )
        self._create_ledger_row(
            organization=self.org,
            account=self.cash_account,
            entry_date=date(2026, 3, 2),
            debit_amount=Decimal("25.00"),
            description="Cash receipt 2",
        )
        self._create_ledger_row(
            organization=self.org,
            account=self.cash_account,
            entry_date=date(2026, 3, 1),
            credit_amount=Decimal("10.00"),
            description="Cash disbursement 2",
        )

        self._create_ledger_row(
            organization=self.other_org,
            account=other_account,
            entry_date=date(2026, 3, 6),
            debit_amount=Decimal("999.00"),
            description="Other org row",
        )

    def _create_account(
        self,
        organization,
        code,
        name,
        *,
        account_type=AccountType.ASSET,
        sub_type=AccountSubType.CURRENT_ASSET,
    ):
        return Account.objects.create(
            organization=organization,
            code=f"{code}-{organization.id}",
            name=name,
            account_type=account_type,
            sub_type=sub_type,
        )

    def _create_ledger_row(
        self,
        *,
        organization,
        account,
        entry_date,
        debit_amount=Decimal("0.00"),
        credit_amount=Decimal("0.00"),
        description,
        source_type="manual",
    ):
        posted_at = timezone.now()
        journal = JournalEntry.objects.create(
            organization=organization,
            entry_date=entry_date,
            description=description,
            source_type=source_type,
            status=JournalEntry.Status.POSTED,
            posted_at=posted_at,
        )
        line = JournalLine.objects.create(
            journal=journal,
            line_number=1,
            account=account,
            debit_amount=debit_amount,
            credit_amount=credit_amount,
            memo=description,
        )
        return LedgerEntry.objects.create(
            organization=organization,
            journal_entry=journal,
            journal_line=line,
            account=account,
            entry_date=entry_date,
            debit_amount=debit_amount,
            credit_amount=credit_amount,
            description=description,
            source_type=source_type,
            posted_at=posted_at,
        )

    def test_general_ledger_returns_requested_page(self):
        response = self.client.get(
            "/api/finance/reports/general-ledger/",
            {"page": "2", "page_size": "2"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 5)
        self.assertEqual(response.data["page"], 2)
        self.assertEqual(response.data["page_size"], 2)
        self.assertEqual(response.data["total_pages"], 3)
        self.assertEqual(response.data["limit"], 2)
        self.assertEqual(response.data["totals"]["debit"], "125.00")
        self.assertEqual(response.data["totals"]["credit"], "110.00")
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(
            [row["description"] for row in response.data["results"]],
            ["Revenue recognition", "Cash receipt 2"],
        )

    def test_general_ledger_clamps_out_of_range_pages(self):
        response = self.client.get(
            "/api/finance/reports/general-ledger/",
            {"page": "99", "page_size": "2"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["page"], 3)
        self.assertEqual(response.data["total_pages"], 3)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["description"], "Cash disbursement 2")

    def test_general_ledger_filters_before_paginating(self):
        response = self.client.get(
            "/api/finance/reports/general-ledger/",
            {
                "account": str(self.cash_account.id),
                "page": "1",
                "page_size": "2",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 4)
        self.assertEqual(response.data["page"], 1)
        self.assertEqual(response.data["total_pages"], 2)
        self.assertEqual(response.data["totals"]["debit"], "125.00")
        self.assertEqual(response.data["totals"]["credit"], "50.00")
        self.assertEqual(
            [row["description"] for row in response.data["results"]],
            ["Cash receipt 1", "Cash disbursement 1"],
        )
