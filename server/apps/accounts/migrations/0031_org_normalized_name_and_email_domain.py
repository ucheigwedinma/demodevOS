from django.db import migrations, models


def backfill_normalized_names(apps, schema_editor):
    """Backfill normalized_name for all existing organizations."""
    from apps.accounts.org_name_utils import normalize_org_name

    Organization = apps.get_model("accounts", "Organization")
    orgs = Organization.objects.all()
    for org in orgs:
        org.normalized_name = normalize_org_name(org.name)
    Organization.objects.bulk_update(orgs, ["normalized_name"], batch_size=500)


def backfill_email_domains(apps, schema_editor):
    """Backfill email_domain from admin/creator emails."""
    from apps.accounts.org_name_utils import extract_email_domain

    Organization = apps.get_model("accounts", "Organization")
    for org in Organization.objects.filter(email_domain="").select_related("created_by"):
        if org.created_by and org.created_by.email:
            domain = extract_email_domain(org.created_by.email)
            if domain:
                org.email_domain = domain
                org.save(update_fields=["email_domain"])


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ("accounts", "0030_userprofile_require_organization"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="normalized_name",
            field=models.CharField(
                blank=True, db_index=True, editable=False, max_length=200
            ),
        ),
        migrations.AddField(
            model_name="organization",
            name="email_domain",
            field=models.CharField(blank=True, db_index=True, max_length=255),
        ),
        migrations.RunPython(
            backfill_normalized_names,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RunPython(
            backfill_email_domains,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
