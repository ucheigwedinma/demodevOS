from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("settings", "0064_task_template_sections"),
    ]

    operations = [
        migrations.AddField(
            model_name="division",
            name="location_region",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name="division",
            name="unit_category",
            field=models.CharField(
                choices=[("profit_center", "Profit Center"), ("cost_center", "Cost Center")],
                default="cost_center",
                max_length=20,
            ),
        ),
    ]
