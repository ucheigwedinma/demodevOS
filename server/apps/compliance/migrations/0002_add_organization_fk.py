import django.db.models.deletion
from django.db import migrations, models


def populate_organization(apps, schema_editor):
    Organization = apps.get_model("accounts", "Organization")
    org = Organization.objects.first()
    if org is None:
        return
    ComplianceRequirement = apps.get_model("compliance", "ComplianceRequirement")
    ComplianceRequirement.objects.filter(organization__isnull=True).update(organization=org)
    PropertyCompliance = apps.get_model("compliance", "PropertyCompliance")
    PropertyCompliance.objects.filter(organization__isnull=True).update(organization=org)
    ComplianceViolation = apps.get_model("compliance", "ComplianceViolation")
    ComplianceViolation.objects.filter(organization__isnull=True).update(organization=org)
    ComplianceAudit = apps.get_model("compliance", "ComplianceAudit")
    ComplianceAudit.objects.filter(organization__isnull=True).update(organization=org)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
        ("compliance", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="compliancerequirement",
            name="organization",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_compliance_requirements",
                to="accounts.organization",
            ),
        ),
        migrations.AddField(
            model_name="propertycompliance",
            name="organization",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_property_compliances",
                to="accounts.organization",
            ),
        ),
        migrations.AddField(
            model_name="complianceviolation",
            name="organization",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_compliance_violations",
                to="accounts.organization",
            ),
        ),
        migrations.AddField(
            model_name="complianceaudit",
            name="organization",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_compliance_audits",
                to="accounts.organization",
            ),
        ),
        migrations.RunPython(populate_organization, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="compliancerequirement",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_compliance_requirements",
                to="accounts.organization",
            ),
        ),
        migrations.AlterField(
            model_name="propertycompliance",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_property_compliances",
                to="accounts.organization",
            ),
        ),
        migrations.AlterField(
            model_name="complianceviolation",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_compliance_violations",
                to="accounts.organization",
            ),
        ),
        migrations.AlterField(
            model_name="complianceaudit",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_compliance_audits",
                to="accounts.organization",
            ),
        ),
    ]
