from django.core.management.base import BaseCommand

from apps.accounts.models import Organization
from apps.settings.contextual_policy_defaults import seed_contextual_access_policies_for_org


class Command(BaseCommand):
    help = "Seed contextual access policies (access_policies, policy_conditions, policy_actions)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--org",
            type=int,
            help="Seed policies for a specific organization ID only.",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Re-apply defaults and remove extra rows on seeded policies.",
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
            "access_policies": 0,
            "policy_conditions": 0,
            "policy_actions": 0,
            "reset_deleted": 0,
        }

        for org in orgs:
            result = seed_contextual_access_policies_for_org(org, reset=reset)
            for key in totals:
                totals[key] += result.get(key, 0)

            self.stdout.write(

                    f"  {org.name}: policies +{result['access_policies']}, "
                    f"conditions +{result['policy_conditions']}, "
                    f"actions +{result['policy_actions']}"
                    + (
                        f", reset-deleted {result['reset_deleted']}"
                        if reset
                        else ""
                    )

            )

        summary = (
            f"Done across {len(orgs)} org(s). "
            f"access_policies +{totals['access_policies']}, "
            f"policy_conditions +{totals['policy_conditions']}, "
            f"policy_actions +{totals['policy_actions']}"
            + (f", reset-deleted {totals['reset_deleted']}" if reset else "")
        )
        self.stdout.write(self.style.SUCCESS(summary))
