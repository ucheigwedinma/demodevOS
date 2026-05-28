from django.core.management.base import BaseCommand

from apps.accounts.models import Organization
from apps.settings.rbac_defaults import seed_roles_for_org


class Command(BaseCommand):
    help = "Seed RBAC system roles and default permissions for organizations."

    def add_arguments(self, parser):
        parser.add_argument(
            "--org",
            type=int,
            help="Seed roles for a specific organization ID only.",
        )
        parser.add_argument(
            "--reset-permissions",
            action="store_true",
            help="Re-apply default permissions to existing system roles "
                 "(useful after updating defaults in code).",
        )

    def handle(self, *args, **options):
        org_id = options["org"]
        reset = options["reset_permissions"]

        if org_id:
            try:
                org = Organization.objects.get(pk=org_id)
            except Organization.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Organization {org_id} not found."))
                return

            orgs = [org]
        else:
            orgs = Organization.objects.all()

        if not orgs:
            self.stdout.write(self.style.WARNING("No organizations found."))
            return

        total_created = 0
        total_existing = 0

        for org in orgs:
            created, existing = seed_roles_for_org(org, reset_permissions=reset)
            total_created += created
            total_existing += existing
            self.stdout.write(
                f"  {org.name}: {created} created, {existing} already existed"
                + (" (permissions reset)" if reset and existing else "")
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. {total_created} roles created, "
                f"{total_existing} already existed across {len(orgs)} org(s)."
            )
        )
