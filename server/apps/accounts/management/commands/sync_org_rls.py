from django.core.management.base import BaseCommand

from apps.accounts.rls import disable_org_rls_policies, sync_org_rls_policies


class Command(BaseCommand):
    help = "Synchronize PostgreSQL RLS org-isolation policies for organization-scoped tables."

    def add_arguments(self, parser):
        parser.add_argument(
            "--disable",
            action="store_true",
            help="Drop org RLS policy and disable RLS on affected tables.",
        )

    def handle(self, *args, **options):
        if options["disable"]:
            count = disable_org_rls_policies()
            self.stdout.write(
                self.style.WARNING(
                    f"Disabled organization RLS policy on {count} table(s)."
                )
            )
            return

        count = sync_org_rls_policies()
        self.stdout.write(
            self.style.SUCCESS(
                f"Synchronized organization RLS policy on {count} table(s)."
            )
        )
