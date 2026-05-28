import django.db.models.deletion
from django.db import migrations, models


def populate_organization(apps, schema_editor):
    Organization = apps.get_model("accounts", "Organization")
    org = Organization.objects.first()
    if org is None:
        return
    Property = apps.get_model("properties", "Property")
    Property.objects.filter(organization__isnull=True).update(organization=org)
    PropertyOwnership = apps.get_model("properties", "PropertyOwnership")
    PropertyOwnership.objects.filter(organization__isnull=True).update(organization=org)
    PropertyEncumbrance = apps.get_model("properties", "PropertyEncumbrance")
    PropertyEncumbrance.objects.filter(organization__isnull=True).update(organization=org)
    Unit = apps.get_model("properties", "Unit")
    Unit.objects.filter(organization__isnull=True).update(organization=org)
    PropertyImage = apps.get_model("properties", "PropertyImage")
    PropertyImage.objects.filter(organization__isnull=True).update(organization=org)
    PropertyDocument = apps.get_model("properties", "PropertyDocument")
    PropertyDocument.objects.filter(organization__isnull=True).update(organization=org)
    MaintenanceVendor = apps.get_model("properties", "MaintenanceVendor")
    MaintenanceVendor.objects.filter(organization__isnull=True).update(organization=org)
    AssetComponent = apps.get_model("properties", "AssetComponent")
    AssetComponent.objects.filter(organization__isnull=True).update(organization=org)
    WorkOrder = apps.get_model("properties", "WorkOrder")
    WorkOrder.objects.filter(organization__isnull=True).update(organization=org)
    PreventiveSchedule = apps.get_model("properties", "PreventiveSchedule")
    PreventiveSchedule.objects.filter(organization__isnull=True).update(organization=org)
    Inspection = apps.get_model("properties", "Inspection")
    Inspection.objects.filter(organization__isnull=True).update(organization=org)
    ServiceRequest = apps.get_model("properties", "ServiceRequest")
    ServiceRequest.objects.filter(organization__isnull=True).update(organization=org)
    PropertyValuation = apps.get_model("properties", "PropertyValuation")
    PropertyValuation.objects.filter(organization__isnull=True).update(organization=org)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
        ("properties", "0008_inspection_compliance_status_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="property",
            name="organization",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_properties",
                to="accounts.organization",
            ),
        ),
        migrations.AddField(
            model_name="propertyownership",
            name="organization",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_property_ownerships",
                to="accounts.organization",
            ),
        ),
        migrations.AddField(
            model_name="propertyencumbrance",
            name="organization",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_property_encumbrances",
                to="accounts.organization",
            ),
        ),
        migrations.AddField(
            model_name="unit",
            name="organization",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_units",
                to="accounts.organization",
            ),
        ),
        migrations.AddField(
            model_name="propertyimage",
            name="organization",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_property_images",
                to="accounts.organization",
            ),
        ),
        migrations.AddField(
            model_name="propertydocument",
            name="organization",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_property_documents",
                to="accounts.organization",
            ),
        ),
        migrations.AddField(
            model_name="maintenancevendor",
            name="organization",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_maintenance_vendors",
                to="accounts.organization",
            ),
        ),
        migrations.AddField(
            model_name="assetcomponent",
            name="organization",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_asset_components",
                to="accounts.organization",
            ),
        ),
        migrations.AddField(
            model_name="workorder",
            name="organization",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_work_orders",
                to="accounts.organization",
            ),
        ),
        migrations.AddField(
            model_name="preventiveschedule",
            name="organization",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_preventive_schedules",
                to="accounts.organization",
            ),
        ),
        migrations.AddField(
            model_name="inspection",
            name="organization",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_inspections",
                to="accounts.organization",
            ),
        ),
        migrations.AddField(
            model_name="servicerequest",
            name="organization",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_service_requests",
                to="accounts.organization",
            ),
        ),
        migrations.AddField(
            model_name="propertyvaluation",
            name="organization",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_property_valuations",
                to="accounts.organization",
            ),
        ),
        migrations.RunPython(populate_organization, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="property",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_properties",
                to="accounts.organization",
            ),
        ),
        migrations.AlterField(
            model_name="propertyownership",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_property_ownerships",
                to="accounts.organization",
            ),
        ),
        migrations.AlterField(
            model_name="propertyencumbrance",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_property_encumbrances",
                to="accounts.organization",
            ),
        ),
        migrations.AlterField(
            model_name="unit",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_units",
                to="accounts.organization",
            ),
        ),
        migrations.AlterField(
            model_name="propertyimage",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_property_images",
                to="accounts.organization",
            ),
        ),
        migrations.AlterField(
            model_name="propertydocument",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_property_documents",
                to="accounts.organization",
            ),
        ),
        migrations.AlterField(
            model_name="maintenancevendor",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_maintenance_vendors",
                to="accounts.organization",
            ),
        ),
        migrations.AlterField(
            model_name="assetcomponent",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_asset_components",
                to="accounts.organization",
            ),
        ),
        migrations.AlterField(
            model_name="workorder",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_work_orders",
                to="accounts.organization",
            ),
        ),
        migrations.AlterField(
            model_name="preventiveschedule",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_preventive_schedules",
                to="accounts.organization",
            ),
        ),
        migrations.AlterField(
            model_name="inspection",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_inspections",
                to="accounts.organization",
            ),
        ),
        migrations.AlterField(
            model_name="servicerequest",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_service_requests",
                to="accounts.organization",
            ),
        ),
        migrations.AlterField(
            model_name="propertyvaluation",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_property_valuations",
                to="accounts.organization",
            ),
        ),
    ]
