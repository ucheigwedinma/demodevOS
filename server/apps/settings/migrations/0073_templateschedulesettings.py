import django.db.models.deletion
from django.db import migrations, models

import apps.settings.models


class Migration(migrations.Migration):

    dependencies = [
        ("settings", "0072_templatedependency"),
    ]

    operations = [
        migrations.CreateModel(
            name="TemplateScheduleSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("work_days", models.JSONField(default=apps.settings.models.default_work_days)),
                ("shift_start", models.TimeField(default="08:00")),
                ("shift_end", models.TimeField(default="17:00")),
                ("hours_per_day", models.DecimalField(decimal_places=1, default=9, max_digits=4)),
                ("public_holidays", models.JSONField(default=apps.settings.models.default_nigerian_holidays)),
                ("custom_holidays", models.JSONField(blank=True, default=list)),
                ("rainy_season_buffer_enabled", models.BooleanField(default=False)),
                ("rainy_season_buffer_pct", models.DecimalField(decimal_places=1, default=15, max_digits=5)),
                ("rainy_season_months", models.JSONField(default=list)),
                ("outdoor_task_categories", models.JSONField(default=list)),
                ("resource_roles", models.JSONField(default=apps.settings.models.default_resource_roles)),
                ("travel_buffer_hours", models.DecimalField(decimal_places=1, default=0, max_digits=5)),
                ("duration_scalar_pct", models.DecimalField(decimal_places=1, default=100, max_digits=5)),
                ("milestone_anchors", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("template", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="schedule_settings", to="settings.projecttemplate")),
            ],
            options={
                "verbose_name": "Template Schedule Settings",
                "verbose_name_plural": "Template Schedule Settings",
            },
        ),
    ]
