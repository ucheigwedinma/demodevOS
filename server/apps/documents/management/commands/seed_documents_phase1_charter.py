from django.core.management.base import BaseCommand

from apps.accounts.models import Organization
from apps.documents.phase1_seed import seed_phase1_charter


class Command(BaseCommand):
    help = "Seed Phase 1 document governance charter (idempotent)."

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

        charter, created = seed_phase1_charter(organization=organization)
        action = "created" if created else "updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"Phase 1 charter {action}: {charter.title} {charter.version} "
                f"(org={organization.id})"
            )
        )
