from django.core.management.base import BaseCommand

from apps.settings.models import ADDON_ONLY_MODULES, Module, PlatformEdition

EDITION_SEED_DATA = [
    {
        "key": "essentials",
        "name": "Essentials",
        "tier_level": 0,
        "is_custom": False,
        "description": "Core property and project management for small teams.",
        "included_modules": sorted([
            Module.PROPERTIES,
            Module.PROJECTS,
            Module.DOCUMENTS,
            Module.IAM,
            Module.SUPPORT_DESK,
            Module.SETTINGS,
        ]),
        "max_users": 8,
        "max_storage_gb": 5,
        "api_rate_limit_rpm": 100,
        "data_retention_days": 365,
        "max_projects": 5,
        "max_properties": 5,
        "max_entity_maps": 1,
        "support_tier": PlatformEdition.SupportTier.COMMUNITY,
        "support_response_hours": None,
        "support_resolution_hours": None,
        "monthly_price": "79.00",
        "annual_price": "840.00",
    },
    {
        "key": "growth",
        "name": "Growth",
        "tier_level": 1,
        "is_custom": False,
        "description": "Full operational suite for growing organisations.",
        "included_modules": sorted([
            Module.PROPERTIES,
            Module.PROJECTS,
            Module.FINANCE,
            Module.PROCUREMENT,
            Module.CONTRACTS,
            Module.DOCUMENTS,
            Module.ANALYTICS,
            Module.COMPLIANCE,
            Module.HR,
            Module.IAM,
            Module.SUPPORT_DESK,
            Module.SETTINGS,
        ]),
        "max_users": 20,
        "max_storage_gb": 50,
        "api_rate_limit_rpm": 500,
        "data_retention_days": 730,
        "max_projects": 15,
        "max_properties": 15,
        "max_entity_maps": 2,
        "support_tier": PlatformEdition.SupportTier.STANDARD,
        "support_response_hours": 24,
        "support_resolution_hours": 72,
        "monthly_price": "189.00",
        "annual_price": "2100.00",
    },
    {
        "key": "scale",
        "name": "Scale",
        "tier_level": 2,
        "is_custom": False,
        "description": "Enterprise-grade platform with unlimited capacity.",
        "included_modules": sorted(m.value for m in Module if m.value not in ADDON_ONLY_MODULES),
        "max_users": None,
        "max_storage_gb": 150,
        "api_rate_limit_rpm": 2000,
        "data_retention_days": None,
        "max_projects": None,
        "max_properties": None,
        "max_entity_maps": 10,
        "support_tier": PlatformEdition.SupportTier.PRIORITY,
        "support_response_hours": 4,
        "support_resolution_hours": 24,
        "monthly_price": "499.00",
        "annual_price": "5400.00",
    },
    {
        "key": "custom",
        "name": "Custom",
        "tier_level": 3,
        "is_custom": True,
        "description": "Bespoke deployment — cloud, on-premise, or white-label.",
        "included_modules": sorted(m.value for m in Module if m.value not in ADDON_ONLY_MODULES),
        "max_users": 20,
        "max_storage_gb": None,
        "api_rate_limit_rpm": None,
        "data_retention_days": None,
        "max_projects": None,
        "max_properties": None,
        "max_entity_maps": None,
        "support_tier": PlatformEdition.SupportTier.DEDICATED,
        "support_response_hours": 1,
        "support_resolution_hours": 8,
        "monthly_price": None,
        "annual_price": None,
    },
]


class Command(BaseCommand):
    help = "Seed platform edition definitions. Idempotent."

    def handle(self, *args, **options):
        created = 0
        updated = 0

        for row in EDITION_SEED_DATA:
            key = row.pop("key")
            _, was_created = PlatformEdition.objects.update_or_create(
                key=key,
                defaults=row,
            )
            row["key"] = key  # restore for re-runs
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Platform editions: {created} created, {updated} updated."
            )
        )
