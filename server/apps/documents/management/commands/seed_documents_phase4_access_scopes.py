from django.core.management.base import BaseCommand

from apps.accounts.models import Organization
from apps.documents.models import DocumentRoleScope
from apps.settings.models import Role

DEFAULT_SCOPE_MATRIX = {
    "developer-executive": {
        "project_scope": DocumentRoleScope.ProjectScope.ALL_PROJECTS,
        "business_unit_scope": DocumentRoleScope.BusinessUnitScope.ALL_BUSINESS_UNITS,
        "allowed_confidentiality_levels": ["public", "internal", "confidential", "restricted"],
    },
    "project-director": {
        "project_scope": DocumentRoleScope.ProjectScope.ASSIGNED_PROJECTS,
        "business_unit_scope": DocumentRoleScope.BusinessUnitScope.ASSIGNED_BUSINESS_UNITS,
        "allowed_confidentiality_levels": ["public", "internal", "confidential"],
    },
    "sales-manager": {
        "project_scope": DocumentRoleScope.ProjectScope.ASSIGNED_PROJECTS,
        "business_unit_scope": DocumentRoleScope.BusinessUnitScope.ASSIGNED_BUSINESS_UNITS,
        "allowed_confidentiality_levels": ["public", "internal"],
    },
    "finance-controller": {
        "project_scope": DocumentRoleScope.ProjectScope.ASSIGNED_PROJECTS,
        "business_unit_scope": DocumentRoleScope.BusinessUnitScope.ASSIGNED_BUSINESS_UNITS,
        "allowed_confidentiality_levels": ["public", "internal", "confidential"],
    },
    "procurement-officer": {
        "project_scope": DocumentRoleScope.ProjectScope.ASSIGNED_PROJECTS,
        "business_unit_scope": DocumentRoleScope.BusinessUnitScope.ASSIGNED_BUSINESS_UNITS,
        "allowed_confidentiality_levels": ["public", "internal"],
    },
    "governance-officer": {
        "project_scope": DocumentRoleScope.ProjectScope.ALL_PROJECTS,
        "business_unit_scope": DocumentRoleScope.BusinessUnitScope.ALL_BUSINESS_UNITS,
        "allowed_confidentiality_levels": ["public", "internal", "confidential", "restricted"],
    },
    "legal": {
        "project_scope": DocumentRoleScope.ProjectScope.ALL_PROJECTS,
        "business_unit_scope": DocumentRoleScope.BusinessUnitScope.ALL_BUSINESS_UNITS,
        "allowed_confidentiality_levels": ["public", "internal", "confidential", "restricted"],
    },
    "external-consultant": {
        "project_scope": DocumentRoleScope.ProjectScope.ASSIGNED_PROJECTS,
        "business_unit_scope": DocumentRoleScope.BusinessUnitScope.ASSIGNED_BUSINESS_UNITS,
        "allowed_confidentiality_levels": ["public"],
    },
    "auditor": {
        "project_scope": DocumentRoleScope.ProjectScope.ALL_PROJECTS,
        "business_unit_scope": DocumentRoleScope.BusinessUnitScope.ALL_BUSINESS_UNITS,
        "allowed_confidentiality_levels": ["public", "internal", "confidential"],
    },
    "board-viewer": {
        "project_scope": DocumentRoleScope.ProjectScope.ALL_PROJECTS,
        "business_unit_scope": DocumentRoleScope.BusinessUnitScope.ALL_BUSINESS_UNITS,
        "allowed_confidentiality_levels": ["public", "internal"],
    },
}


class Command(BaseCommand):
    help = "Seed DocumentRoleScope defaults for system roles."

    def add_arguments(self, parser):
        parser.add_argument(
            "--org",
            type=int,
            help="Seed scopes for a specific organization ID only.",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Reset existing role scopes to the defaults.",
        )

    def handle(self, *args, **options):
        org_id = options.get("org")
        reset = options.get("reset", False)

        if org_id:
            try:
                orgs = [Organization.objects.get(pk=org_id)]
            except Organization.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Organization {org_id} not found."))
                return
        else:
            orgs = list(Organization.objects.all())

        if not orgs:
            self.stdout.write(self.style.WARNING("No organizations found."))
            return

        created_total = 0
        updated_total = 0

        for org in orgs:
            roles = Role.objects.filter(organization=org, is_system=True)
            org_created = 0
            org_updated = 0

            for role in roles:
                defaults = DEFAULT_SCOPE_MATRIX.get(role.slug)
                if not defaults:
                    continue

                scope, created = DocumentRoleScope.objects.get_or_create(
                    role=role,
                    defaults={**defaults, "organization": org},
                )
                if created:
                    org_created += 1
                    continue

                if scope.organization_id is None:
                    scope.organization = org
                    scope.save(update_fields=["organization"])
                    org_updated += 1

                if reset:
                    scope.project_scope = defaults["project_scope"]
                    scope.business_unit_scope = defaults["business_unit_scope"]
                    scope.allowed_confidentiality_levels = defaults["allowed_confidentiality_levels"]
                    scope.save(update_fields=[
                        "project_scope",
                        "business_unit_scope",
                        "allowed_confidentiality_levels",
                        "updated_at",
                    ])
                    org_updated += 1

            created_total += org_created
            updated_total += org_updated
            self.stdout.write(
                f"  {org.name}: {org_created} scope(s) created"
                + (f", {org_updated} scope(s) reset" if reset else "")
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. {created_total} scope(s) created"
                + (f", {updated_total} scope(s) reset" if reset else "")
                + f" across {len(orgs)} org(s)."
            )
        )
