import django.db.models.deletion
from django.db import migrations, models


def populate_organization(apps, schema_editor):
    Organization = apps.get_model("accounts", "Organization")
    org = Organization.objects.first()
    if org is None:
        return
    ComparableSale = apps.get_model("valuations", "ComparableSale")
    ComparableSale.objects.filter(organization__isnull=True).update(organization=org)
    ValuationAppeal = apps.get_model("valuations", "ValuationAppeal")
    ValuationAppeal.objects.filter(organization__isnull=True).update(organization=org)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
        ("valuations", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="comparablesale",
            name="organization",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_comparable_sales",
                to="accounts.organization",
            ),
        ),
        migrations.AddField(
            model_name="valuationappeal",
            name="organization",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_valuation_appeals",
                to="accounts.organization",
            ),
        ),
        migrations.RunPython(populate_organization, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="comparablesale",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_comparable_sales",
                to="accounts.organization",
            ),
        ),
        migrations.AlterField(
            model_name="valuationappeal",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_valuation_appeals",
                to="accounts.organization",
            ),
        ),
    ]
