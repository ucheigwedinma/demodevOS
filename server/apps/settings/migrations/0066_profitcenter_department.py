import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("settings", "0065_division_operational_metadata"),
    ]

    operations = [
        migrations.AddField(
            model_name="profitcenter",
            name="department",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="profit_centers",
                to="settings.department",
            ),
        ),
    ]
