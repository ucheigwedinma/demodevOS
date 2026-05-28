from django.core.management.base import BaseCommand

from apps.documents.phase2_seed import seed_phase2_owner_roles


class Command(BaseCommand):
    help = "Seed Phase 2 document owner roles (idempotent)."

    def handle(self, *args, **options):
        result = seed_phase2_owner_roles()
        self.stdout.write(
            self.style.SUCCESS(
                "Phase 2 owner roles seeded: "
                f"{result['created']} created, "
                f"{result['updated']} updated, "
                f"{result['total']} total"
            )
        )
