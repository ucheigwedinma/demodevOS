from django.core.management.base import BaseCommand

from apps.accounts.models import Organization
from apps.workflows.process_authority_defaults import seed_process_authority_for_org


class Command(BaseCommand):
    help = "Seed process authority layer (workflow_roles, workflow_steps, approvers, process_authority)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--org",
            type=int,
            help="Seed process authority for a specific organization ID only.",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Re-apply defaults and clean obsolete default authority links.",
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

        totals = {
            "workflow_roles": 0,
            "workflow_steps": 0,
            "approvers": 0,
            "process_authority": 0,
            "reset_deleted": 0,
        }

        for org in orgs:
            result = seed_process_authority_for_org(org, reset=reset)
            for key in totals:
                totals[key] += result.get(key, 0)

            self.stdout.write(

                    f"  {org.name}: roles +{result['workflow_roles']}, "
                    f"steps +{result['workflow_steps']}, "
                    f"approvers +{result['approvers']}, "
                    f"authority +{result['process_authority']}"
                    + (
                        f", reset-deleted {result['reset_deleted']}"
                        if reset
                        else ""
                    )

            )

        summary = (
            f"Done across {len(orgs)} org(s). "
            f"workflow_roles +{totals['workflow_roles']}, "
            f"workflow_steps +{totals['workflow_steps']}, "
            f"approvers +{totals['approvers']}, "
            f"process_authority +{totals['process_authority']}"
            + (f", reset-deleted {totals['reset_deleted']}" if reset else "")
        )
        self.stdout.write(self.style.SUCCESS(summary))
