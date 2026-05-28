from django.db import migrations, models
import django.db.models.deletion


def populate_organization(apps, schema_editor):
    Organization = apps.get_model("accounts", "Organization")
    org = Organization.objects.first()
    if org is None:
        return
    Bill = apps.get_model("finance", "Bill")
    Bill.objects.filter(organization__isnull=True).update(organization=org)
    Customer = apps.get_model("finance", "Customer")
    Customer.objects.filter(organization__isnull=True).update(organization=org)
    Invoice = apps.get_model("finance", "Invoice")
    Invoice.objects.filter(organization__isnull=True).update(organization=org)
    ProjectInvestor = apps.get_model("finance", "ProjectInvestor")
    ProjectInvestor.objects.filter(organization__isnull=True).update(organization=org)
    WaterfallDistribution = apps.get_model("finance", "WaterfallDistribution")
    WaterfallDistribution.objects.filter(organization__isnull=True).update(organization=org)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
        ("finance", "0014_alter_paymentplan_currency"),
    ]

    operations = [
        # Step 1: Add nullable FK to all 5 models
        migrations.AddField(
            model_name="bill",
            name="organization",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="bills",
                to="accounts.organization",
            ),
        ),
        migrations.AddField(
            model_name="customer",
            name="organization",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="customers",
                to="accounts.organization",
            ),
        ),
        migrations.AddField(
            model_name="invoice",
            name="organization",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="invoices",
                to="accounts.organization",
            ),
        ),
        migrations.AddField(
            model_name="projectinvestor",
            name="organization",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="project_investors",
                to="accounts.organization",
            ),
        ),
        migrations.AddField(
            model_name="waterfalldistribution",
            name="organization",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="waterfall_distributions",
                to="accounts.organization",
            ),
        ),
        # Step 2: Populate from first organization
        migrations.RunPython(populate_organization, migrations.RunPython.noop),
        # Step 3: Make non-nullable
        migrations.AlterField(
            model_name="bill",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="bills",
                to="accounts.organization",
            ),
        ),
        migrations.AlterField(
            model_name="customer",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="customers",
                to="accounts.organization",
            ),
        ),
        migrations.AlterField(
            model_name="invoice",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="invoices",
                to="accounts.organization",
            ),
        ),
        migrations.AlterField(
            model_name="projectinvestor",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="project_investors",
                to="accounts.organization",
            ),
        ),
        migrations.AlterField(
            model_name="waterfalldistribution",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="waterfall_distributions",
                to="accounts.organization",
            ),
        ),
    ]
