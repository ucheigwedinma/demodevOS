import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("facility_management", "0002_facility_facilityfloor_facilityzone_and_more"),
        ("properties", "0013_unit_category_backfill"),
    ]

    operations = [
        migrations.AddField(
            model_name="assetcomponent",
            name="acquisition_cost",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True),
        ),
        migrations.AddField(
            model_name="assetcomponent",
            name="amc_amount",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name="assetcomponent",
            name="amc_end_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="assetcomponent",
            name="amc_notes",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="assetcomponent",
            name="amc_reference",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="assetcomponent",
            name="amc_start_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="assetcomponent",
            name="amc_vendor",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="amc_assets", to="properties.maintenancevendor"),
        ),
        migrations.AddField(
            model_name="assetcomponent",
            name="auto_schedule_maintenance",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="assetcomponent",
            name="commissioned_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="assetcomponent",
            name="depreciation_enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="assetcomponent",
            name="depreciation_method",
            field=models.CharField(choices=[("straight_line", "Straight Line")], default="straight_line", max_length=20),
        ),
        migrations.AddField(
            model_name="assetcomponent",
            name="depreciation_start_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="assetcomponent",
            name="facility",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assets", to="facility_management.facility"),
        ),
        migrations.AddField(
            model_name="assetcomponent",
            name="facility_space",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assets", to="facility_management.facilityunitspace"),
        ),
        migrations.AddField(
            model_name="assetcomponent",
            name="iot_device_id",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="assetcomponent",
            name="iot_last_seen_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="assetcomponent",
            name="iot_status",
            field=models.CharField(choices=[("not_connected", "Not Connected"), ("connected", "Connected"), ("offline", "Offline"), ("fault", "Fault")], default="not_connected", max_length=20),
        ),
        migrations.AddField(
            model_name="assetcomponent",
            name="is_iot_enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="assetcomponent",
            name="last_depreciation_sync_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="assetcomponent",
            name="lifecycle_stage",
            field=models.CharField(choices=[("install", "Install"), ("operate", "Operate"), ("maintain", "Maintain"), ("retire", "Retire")], default="operate", max_length=10),
        ),
        migrations.AddField(
            model_name="assetcomponent",
            name="maintenance_frequency",
            field=models.CharField(blank=True, choices=[("daily", "Daily"), ("weekly", "Weekly"), ("biweekly", "Bi-Weekly"), ("monthly", "Monthly"), ("quarterly", "Quarterly"), ("semi_annual", "Semi-Annual"), ("annual", "Annual")], max_length=15),
        ),
        migrations.AddField(
            model_name="assetcomponent",
            name="maintenance_next_due_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="assetcomponent",
            name="retired_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="assetcomponent",
            name="salvage_value",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True),
        ),
        migrations.AddField(
            model_name="assetcomponent",
            name="vendor",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="asset_components", to="properties.maintenancevendor"),
        ),
        migrations.AddField(
            model_name="preventiveschedule",
            name="auto_generated",
            field=models.BooleanField(default=False),
        ),
        migrations.AddIndex(
            model_name="assetcomponent",
            index=models.Index(fields=["organization", "facility"], name="prop_ac_org_facility_idx"),
        ),
        migrations.AddIndex(
            model_name="assetcomponent",
            index=models.Index(fields=["organization", "lifecycle_stage"], name="prop_ac_org_lifecycle_idx"),
        ),
        migrations.AddIndex(
            model_name="assetcomponent",
            index=models.Index(fields=["organization", "maintenance_next_due_date"], name="prop_ac_org_maint_due_idx"),
        ),
    ]
