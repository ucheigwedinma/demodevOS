from django.core.management.base import BaseCommand

from apps.accounts.models import Organization
from apps.documents.phase2_seed import (
    seed_phase2_document_types,
    seed_phase2_owner_roles,
    seed_phase2_retention_policies,
    seed_phase2_workflow_phases,
)


class Command(BaseCommand):
    help = "Seed all Phase 2 document-control lookup tables (idempotent)."

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

        type_result = seed_phase2_document_types(organization=organization)
        role_result = seed_phase2_owner_roles(organization=organization)
        phase_result = seed_phase2_workflow_phases(organization=organization)
        retention_result = seed_phase2_retention_policies(organization=organization)

        self.stdout.write(self.style.SUCCESS("Phase 2 document-control seeds completed:"))
        self.stdout.write(f"  organization={organization.id} ({organization.name})")
        self.stdout.write(
            f"  document_types={type_result['total']} (created={type_result['created']}, updated={type_result['updated']})"
        )
        self.stdout.write(
            f"  owner_roles={role_result['total']} (created={role_result['created']}, updated={role_result['updated']})"
        )
        self.stdout.write(
            f"  workflow_phases={phase_result['total']} (created={phase_result['created']}, updated={phase_result['updated']})"
        )
        self.stdout.write(
            f"  retention_policies={retention_result['total']} (created={retention_result['created']}, updated={retention_result['updated']})"
        )
