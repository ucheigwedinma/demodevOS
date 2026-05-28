"""Backfill org-scoped employee_id for existing UserProfile records."""

from django.db import migrations


def backfill_employee_ids(apps, schema_editor):
    UserProfile = apps.get_model("accounts", "UserProfile")
    Organization = apps.get_model("accounts", "Organization")

    for org in Organization.objects.all():
        profiles = (
            UserProfile.objects
            .filter(organization=org, employee_id="")
            .order_by("pk")
        )
        # Find the current max EMP-NNN in this org
        existing = (
            UserProfile.objects
            .filter(organization=org)
            .exclude(employee_id="")
            .values_list("employee_id", flat=True)
        )
        max_num = 0
        for eid in existing:
            if eid.startswith("EMP-"):
                try:
                    num = int(eid.split("-", 1)[1])
                    max_num = max(max_num, num)
                except (ValueError, IndexError):
                    pass

        for profile in profiles:
            max_num += 1
            profile.employee_id = f"EMP-{max_num:03d}"
            profile.save(update_fields=["employee_id"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0034_alter_organizationsubscription_status"),
    ]

    operations = [
        migrations.RunPython(backfill_employee_ids, migrations.RunPython.noop),
    ]
