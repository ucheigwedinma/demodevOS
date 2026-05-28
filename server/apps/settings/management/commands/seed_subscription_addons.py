from django.core.management.base import BaseCommand

from apps.settings.models import SubscriptionAddOn

ADDONS = [
    {
        "key": "module_tenants",
        "name": "Tenants",
        "add_on_type": "module",
        "module_key": "tenants",
        "storage_gb": 0,
        "monthly_price": "50.00",
        "description": "Tenant management module for property leasing and rent collection.",
        "sort_order": 1,
    },
    {
        "key": "module_crm",
        "name": "CRM",
        "add_on_type": "module",
        "module_key": "crm",
        "storage_gb": 0,
        "monthly_price": "75.00",
        "description": "Customer relationship management for leads, deals, and client engagement.",
        "sort_order": 2,
    },
    {
        "key": "module_construction",
        "name": "Construction",
        "add_on_type": "module",
        "module_key": "construction",
        "storage_gb": 0,
        "monthly_price": "120.00",
        "description": "Site operations, progress tracking, inspections, and field management.",
        "sort_order": 3,
    },
    {
        "key": "module_facility_management",
        "name": "Facility Management",
        "add_on_type": "module",
        "module_key": "facility_management",
        "storage_gb": 0,
        "monthly_price": "100.00",
        "description": "Facility management module for building operations and maintenance.",
        "sort_order": 4,
    },
    {
        "key": "module_payroll",
        "name": "Payroll",
        "add_on_type": "module",
        "module_key": "payroll",
        "storage_gb": 0,
        "monthly_price": "80.00",
        "description": "Employee payroll processing, disbursements, and tax compliance.",
        "sort_order": 5,
    },
    {
        "key": "module_calendar",
        "name": "Calendar",
        "add_on_type": "module",
        "module_key": "calendar",
        "storage_gb": 0,
        "monthly_price": "25.00",
        "description": "Shared team calendar with scheduling, reminders, and event management.",
        "sort_order": 6,
    },
    {
        "key": "module_mail",
        "name": "Mail",
        "add_on_type": "module",
        "module_key": "mail",
        "storage_gb": 0,
        "monthly_price": "40.00",
        "description": "Integrated email with custom domain support and team mailboxes.",
        "sort_order": 7,
    },
    {
        "key": "storage_10gb",
        "name": "Extra 10 GB",
        "add_on_type": "storage",
        "module_key": "",
        "storage_gb": 10,
        "monthly_price": "10.00",
        "description": "Add 10 GB of additional file storage to your plan.",
        "sort_order": 10,
    },
    {
        "key": "storage_20gb",
        "name": "Extra 20 GB",
        "add_on_type": "storage",
        "module_key": "",
        "storage_gb": 20,
        "monthly_price": "15.00",
        "description": "Add 20 GB of additional file storage to your plan.",
        "sort_order": 11,
    },
    {
        "key": "storage_50gb",
        "name": "Extra 50 GB",
        "add_on_type": "storage",
        "module_key": "",
        "storage_gb": 50,
        "monthly_price": "35.00",
        "description": "Add 50 GB of additional file storage to your plan.",
        "sort_order": 12,
    },
    {
        "key": "storage_100gb",
        "name": "Extra 100 GB",
        "add_on_type": "storage",
        "module_key": "",
        "storage_gb": 100,
        "monthly_price": "70.00",
        "description": "Add 100 GB of additional file storage to your plan.",
        "sort_order": 13,
    },
]


class Command(BaseCommand):
    help = "Seed subscription add-on products (module and storage add-ons)"

    def handle(self, *args, **options):
        created = 0
        updated = 0
        for data in ADDONS:
            key = data.pop("key")
            obj, was_created = SubscriptionAddOn.objects.update_or_create(
                key=key, defaults=data,
            )
            data["key"] = key  # restore for next run
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done — {created} created, {updated} updated."
            )
        )
