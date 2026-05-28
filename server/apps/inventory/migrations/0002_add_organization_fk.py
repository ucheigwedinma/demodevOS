from django.db import migrations, models
import django.db.models.deletion


def populate_organization(apps, schema_editor):
    Organization = apps.get_model("accounts", "Organization")
    org = Organization.objects.first()
    if org is None:
        return
    Warehouse = apps.get_model("inventory", "Warehouse")
    Warehouse.objects.filter(organization__isnull=True).update(organization=org)
    InventoryItem = apps.get_model("inventory", "InventoryItem")
    InventoryItem.objects.filter(organization__isnull=True).update(organization=org)
    InventoryStock = apps.get_model("inventory", "InventoryStock")
    InventoryStock.objects.filter(organization__isnull=True).update(organization=org)
    InventoryTransaction = apps.get_model("inventory", "InventoryTransaction")
    InventoryTransaction.objects.filter(organization__isnull=True).update(organization=org)
    ProcurementItemMapping = apps.get_model("inventory", "ProcurementItemMapping")
    ProcurementItemMapping.objects.filter(organization__isnull=True).update(organization=org)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
        ("inventory", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="warehouse",
            name="organization",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_warehouses",
                to="accounts.organization",
            ),
        ),
        migrations.AddField(
            model_name="inventoryitem",
            name="organization",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_inventory_items",
                to="accounts.organization",
            ),
        ),
        migrations.AddField(
            model_name="inventorystock",
            name="organization",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_inventory_stocks",
                to="accounts.organization",
            ),
        ),
        migrations.AddField(
            model_name="inventorytransaction",
            name="organization",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_inventory_transactions",
                to="accounts.organization",
            ),
        ),
        migrations.AddField(
            model_name="procurementitemmapping",
            name="organization",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_procurement_item_mappings",
                to="accounts.organization",
            ),
        ),
        migrations.RunPython(populate_organization, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="warehouse",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_warehouses",
                to="accounts.organization",
            ),
        ),
        migrations.AlterField(
            model_name="inventoryitem",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_inventory_items",
                to="accounts.organization",
            ),
        ),
        migrations.AlterField(
            model_name="inventorystock",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_inventory_stocks",
                to="accounts.organization",
            ),
        ),
        migrations.AlterField(
            model_name="inventorytransaction",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_inventory_transactions",
                to="accounts.organization",
            ),
        ),
        migrations.AlterField(
            model_name="procurementitemmapping",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_procurement_item_mappings",
                to="accounts.organization",
            ),
        ),
    ]
