from django.core.management.base import BaseCommand

from apps.accounts.models import Organization
from apps.settings.scope_defaults import seed_role_scopes_for_org, seed_user_scope_assignments_for_org


class Command(BaseCommand):
    help = "Seed layered access data scopes (role scopes + user scope assignments)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--org",
            type=int,
            help="Seed scopes for a specific organization ID only.",
        )
        parser.add_argument(
            "--reset-role-scopes",
            action="store_true",
            help=(
                "Reset module-level role scopes for seeded modules "
                "(iam, projects) to defaults."
            ),
        )
        parser.add_argument(
            "--reset-user-scopes",
            action="store_true",
            help=(
                "Reset module-level user scope assignments for seeded modules "
                "(iam, projects) to defaults."
            ),
        )
        parser.add_argument(
            "--no-user-scopes",
            action="store_true",
            help="Seed role scopes only and skip user scope assignments.",
        )

    def handle(self, *args, **options):
        org_id = options.get("org")
        reset_role_scopes = options.get("reset_role_scopes", False)
        reset_user_scopes = options.get("reset_user_scopes", False)
        seed_user_scopes = not options.get("no_user_scopes", False)

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

        role_created_total = 0
        role_updated_total = 0
        user_created_total = 0
        user_updated_total = 0

        for org in orgs:
            role_created, role_updated = seed_role_scopes_for_org(
                org,
                reset=reset_role_scopes,
            )
            role_created_total += role_created
            role_updated_total += role_updated

            user_created = 0
            user_updated = 0
            if seed_user_scopes:
                user_created, user_updated = seed_user_scope_assignments_for_org(
                    org,
                    reset=reset_user_scopes,
                )
                user_created_total += user_created
                user_updated_total += user_updated

            message = (
                f"  {org.name}: role scopes +{role_created}"
                + (f", reset {role_updated}" if reset_role_scopes else "")
            )
            if seed_user_scopes:
                message += (
                    f" | user scopes +{user_created}"
                    + (f", reset {user_updated}" if reset_user_scopes else "")
                )
            self.stdout.write(message)

        summary = (
            f"Done. Role scopes created: {role_created_total}"
            + (f", reset: {role_updated_total}" if reset_role_scopes else "")
        )
        if seed_user_scopes:
            summary += (
                f" | User scopes created: {user_created_total}"
                + (f", reset: {user_updated_total}" if reset_user_scopes else "")
            )
        summary += f" across {len(orgs)} org(s)."

        self.stdout.write(self.style.SUCCESS(summary))
