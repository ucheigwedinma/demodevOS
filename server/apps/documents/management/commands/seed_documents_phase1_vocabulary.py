from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import Organization
from apps.documents.phase1_seed import seed_phase1_vocabulary


class Command(BaseCommand):
    help = "Seed Phase 1 controlled vocabulary dictionary terms (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--org",
            type=int,
            help="Seed for a specific organization ID. Defaults to first organization.",
        )

    def handle(self, *args, **options):
        org_id = options.get("org")
        if org_id:
            organization = Organization.objects.filter(pk=org_id).first()
            if organization is None:
                self.stderr.write(self.style.ERROR(f"Organization {org_id} not found."))
                return
        else:
            organization = Organization.objects.order_by("id").first()
            if organization is None:
                self.stderr.write(self.style.ERROR("No organizations found."))
                return

        try:
            result = seed_phase1_vocabulary(organization=organization)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                "Phase 1 vocabulary seeded: "
                f"{result['created']} created, "
                f"{result['updated']} updated, "
                f"{result['total']} total "
                f"(org={organization.id})"
            )
        )
