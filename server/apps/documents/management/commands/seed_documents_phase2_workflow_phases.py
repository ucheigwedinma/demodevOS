from django.core.management.base import BaseCommand

from apps.documents.phase2_seed import seed_phase2_workflow_phases


class Command(BaseCommand):
    help = "Seed Phase 2 document workflow phases (idempotent)."

    def handle(self, *args, **options):
        result = seed_phase2_workflow_phases()
        self.stdout.write(
            self.style.SUCCESS(
                "Phase 2 workflow phases seeded: "
                f"{result['created']} created, "
                f"{result['updated']} updated, "
                f"{result['total']} total"
            )
        )
