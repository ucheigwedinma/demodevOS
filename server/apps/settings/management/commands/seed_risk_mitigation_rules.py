from django.core.management.base import BaseCommand

from apps.accounts.models import Organization
from apps.settings.models import RiskCategory, RiskMitigationRule, Role

RULE_SEED_DATA = [
    {
        "category_name": "Market Risk",
        "category_type": RiskCategory.CategoryType.MARKET,
        "category_description": "Demand fluctuations, pricing pressure, and absorption risk.",
        "severity": RiskMitigationRule.Severity.MEDIUM,
        "role_slug": "sales-manager",
        "escalation_required": False,
        "response_time_hours": 72,
    },
    {
        "category_name": "Construction Delay Risk",
        "category_type": RiskCategory.CategoryType.CONSTRUCTION,
        "category_description": "Schedule overruns, contractor delays, and critical path slippage.",
        "severity": RiskMitigationRule.Severity.HIGH,
        "role_slug": "project-director",
        "escalation_required": True,
        "response_time_hours": 24,
    },
    {
        "category_name": "Cost Overrun Risk",
        "category_type": RiskCategory.CategoryType.FINANCIAL,
        "category_description": "Budget overruns due to scope growth, inflation, or procurement variance.",
        "severity": RiskMitigationRule.Severity.HIGH,
        "role_slug": "finance-controller",
        "escalation_required": True,
        "response_time_hours": 24,
    },
    {
        "category_name": "Regulatory Approval Risk",
        "category_type": RiskCategory.CategoryType.REGULATORY,
        "category_description": "Permit delays, approval rejection, and authority compliance gaps.",
        "severity": RiskMitigationRule.Severity.HIGH,
        "role_slug": "governance-officer",
        "escalation_required": True,
        "response_time_hours": 24,
    },
    {
        "category_name": "Environmental Compliance Risk",
        "category_type": RiskCategory.CategoryType.ENVIRONMENTAL,
        "category_description": "EIA non-compliance, environmental incidents, and enforcement penalties.",
        "severity": RiskMitigationRule.Severity.CRITICAL,
        "role_slug": "governance-officer",
        "escalation_required": True,
        "response_time_hours": 12,
    },
    {
        "category_name": "Financing Risk",
        "category_type": RiskCategory.CategoryType.FINANCIAL,
        "category_description": "Funding shortfall, covenant breach, or refinancing risk.",
        "severity": RiskMitigationRule.Severity.CRITICAL,
        "role_slug": "finance-controller",
        "escalation_required": True,
        "response_time_hours": 12,
    },
    {
        "category_name": "Legal & Title Risk",
        "category_type": RiskCategory.CategoryType.LEGAL,
        "category_description": "Title disputes, encumbrances, and contractual/legal exposure.",
        "severity": RiskMitigationRule.Severity.HIGH,
        "role_slug": "legal",
        "escalation_required": True,
        "response_time_hours": 24,
    },
    {
        "category_name": "Design Change Risk",
        "category_type": RiskCategory.CategoryType.TECHNICAL,
        "category_description": "Late design variations causing rework and execution disruption.",
        "severity": RiskMitigationRule.Severity.MEDIUM,
        "role_slug": "project-director",
        "escalation_required": False,
        "response_time_hours": 48,
    },
    {
        "category_name": "Safety Incident Risk",
        "category_type": RiskCategory.CategoryType.OPERATIONAL,
        "category_description": "Site HSE incidents, lost-time injuries, and regulatory safety exposure.",
        "severity": RiskMitigationRule.Severity.CRITICAL,
        "role_slug": "project-director",
        "escalation_required": True,
        "response_time_hours": 8,
    },
    {
        "category_name": "Quality Defect Risk",
        "category_type": RiskCategory.CategoryType.CONSTRUCTION,
        "category_description": "Defective works, failed inspections, and handover quality issues.",
        "severity": RiskMitigationRule.Severity.MEDIUM,
        "role_slug": "project-director",
        "escalation_required": False,
        "response_time_hours": 36,
    },
]


class Command(BaseCommand):
    help = "Seed 10 default risk mitigation rules per organization (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--org",
            type=int,
            help="Seed for a specific organization ID only.",
        )

    def handle(self, *args, **options):
        org_id = options.get("org")

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

        total_created = 0
        total_updated = 0
        total_categories_created = 0

        for org in orgs:
            created, updated, categories_created = self._seed_for_org(org)
            total_created += created
            total_updated += updated
            total_categories_created += categories_created
            self.stdout.write(
                f"  {org.name}: {created} created, {updated} updated, "
                f"{categories_created} categories created"
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. Rules created={total_created}, updated={total_updated}, "
                f"categories created={total_categories_created} across {len(orgs)} org(s)."
            )
        )

    def _seed_for_org(self, org):
        role_slugs = {item["role_slug"] for item in RULE_SEED_DATA}
        role_by_slug = {
            role.slug: role
            for role in Role.objects.filter(organization=org, slug__in=role_slugs)
        }

        created_count = 0
        updated_count = 0
        categories_created = 0

        for row in RULE_SEED_DATA:
            category, category_created = RiskCategory.objects.get_or_create(
                organization=org,
                name=row["category_name"],
                defaults={
                    "category_type": row["category_type"],
                    "description": row["category_description"],
                    "is_active": True,
                },
            )
            if category_created:
                categories_created += 1
            else:
                needs_update = (
                    category.category_type != row["category_type"]
                    or category.description != row["category_description"]
                    or not category.is_active
                )
                if needs_update:
                    category.category_type = row["category_type"]
                    category.description = row["category_description"]
                    category.is_active = True
                    category.save(
                        update_fields=["category_type", "description", "is_active", "updated_at"]
                    )

            assigned_role = role_by_slug.get(row["role_slug"])
            if assigned_role is None:
                self.stdout.write(
                    self.style.WARNING(
                        f"  [{org.name}] role '{row['role_slug']}' not found. "
                        f"Rule for '{row['category_name']}' will be unassigned."
                    )
                )

            _, created = RiskMitigationRule.objects.update_or_create(
                organization=org,
                risk_category=category,
                severity=row["severity"],
                defaults={
                    "assign_to_role": assigned_role,
                    "escalation_required": row["escalation_required"],
                    "response_time_hours": row["response_time_hours"],
                    "is_active": True,
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        return created_count, updated_count, categories_created
