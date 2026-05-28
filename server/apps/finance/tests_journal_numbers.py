from django.test import TestCase

from apps.accounts.models import Organization
from apps.finance.models import JournalEntry


class JournalNumberGenerationTests(TestCase):
    def test_journal_numbers_increment_within_same_org(self):
        org = Organization.objects.create(name="Journal Seq Org")

        first = JournalEntry.objects.create(
            organization=org,
            description="Opening entry",
        )
        second = JournalEntry.objects.create(
            organization=org,
            description="Adjustment entry",
        )

        self.assertEqual(first.journal_number, "JRN-000001")
        self.assertEqual(second.journal_number, "JRN-000002")

    def test_journal_numbers_are_scoped_per_organization(self):
        org_a = Organization.objects.create(name="Journal Org A")
        org_b = Organization.objects.create(name="Journal Org B")

        a_first = JournalEntry.objects.create(
            organization=org_a,
            description="Org A first entry",
        )
        b_first = JournalEntry.objects.create(
            organization=org_b,
            description="Org B first entry",
        )

        self.assertEqual(a_first.journal_number, "JRN-000001")
        self.assertEqual(b_first.journal_number, "JRN-000001")
