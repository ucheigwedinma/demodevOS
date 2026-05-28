from django.core.management.base import BaseCommand

from apps.documents.phase2_seed import seed_phase2_retention_policies


class Command(BaseCommand):
    help = "Seed Phase 2 document retention policies (idempotent)."

    def handle(self, *args, **options):
        result = seed_phase2_retention_policies()
        self.stdout.write(
            self.style.SUCCESS(
                "Phase 2 retention policies seeded: "
                f"{result['created']} created, "
                f"{result['updated']} updated, "
                f"{result['total']} total"
            )
        )
