from decimal import Decimal

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("settings", "0069_notificationchannelsettings_category_overrides"),
    ]

    operations = [
        migrations.CreateModel(
            name="TemplateActivity",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("estimated_duration_days", models.PositiveIntegerField(blank=True, help_text="Estimated duration in calendar days", null=True)),
                ("estimated_effort_hours", models.DecimalField(blank=True, decimal_places=1, help_text="Total estimated effort in hours", max_digits=8, null=True)),
                ("wbs_code", models.CharField(blank=True, help_text="WBS numbering (e.g., 1.2, 2.3) — auto-generated if blank", max_length=50)),
                ("phase", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="activities", to="settings.templatephase")),
            ],
            options={
                "ordering": ["sort_order"],
                "verbose_name_plural": "template activities",
            },
        ),
        migrations.AddField(
            model_name="tasktemplate",
            name="activity",
            field=models.ForeignKey(blank=True, help_text="WBS activity this task belongs to.", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="task_templates", to="settings.templateactivity"),
        ),
    ]
