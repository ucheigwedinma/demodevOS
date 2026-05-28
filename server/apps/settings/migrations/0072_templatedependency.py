import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("settings", "0071_tasktemplate_planner_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="TemplateDependency",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("dependency_type", models.CharField(choices=[("fs", "Finish-to-Start"), ("ss", "Start-to-Start"), ("ff", "Finish-to-Finish"), ("sf", "Start-to-Finish")], default="fs", max_length=2)),
                ("lag_hours", models.DecimalField(decimal_places=1, default=0, help_text="Positive = lag/delay, Negative = lead time.", max_digits=7)),
                ("strength", models.CharField(choices=[("hard", "Hard (Physical constraint)"), ("soft", "Soft (Preferred sequence)")], default="hard", max_length=4)),
                ("risk_impact", models.PositiveSmallIntegerField(default=5, help_text="1\u201310 scale of historical delay risk for this dependency.")),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("template", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="dependencies", to="settings.projecttemplate")),
                ("from_activity", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="outgoing_dependencies", to="settings.templateactivity")),
                ("from_task", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="outgoing_dependencies", to="settings.tasktemplate")),
                ("to_activity", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="incoming_dependencies", to="settings.templateactivity")),
                ("to_task", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="incoming_dependencies", to="settings.tasktemplate")),
            ],
            options={
                "ordering": ["created_at"],
                "verbose_name_plural": "template dependencies",
                "indexes": [
                    models.Index(fields=["template", "from_activity"], name="tmpl_dep_from_act_idx"),
                    models.Index(fields=["template", "to_activity"], name="tmpl_dep_to_act_idx"),
                ],
            },
        ),
    ]
