import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("settings", "0073_templateschedulesettings"),
    ]

    operations = [
        migrations.CreateModel(
            name="TemplatePlanScenario",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                ("is_baseline", models.BooleanField(default=False)),
                ("duration_scalar_pct", models.DecimalField(decimal_places=1, default=100, max_digits=5)),
                ("material_markup_pct", models.DecimalField(decimal_places=1, default=10, max_digits=5)),
                ("location_factor", models.CharField(default="lagos", max_length=30)),
                ("contingency_pct", models.DecimalField(decimal_places=1, default=10, max_digits=5)),
                ("equipment_daily_rate", models.DecimalField(decimal_places=2, default=50000, max_digits=12)),
                ("fx_rate_usd_ngn", models.DecimalField(decimal_places=2, default=1550, max_digits=10)),
                ("risk_level", models.CharField(choices=[("low", "Low"), ("medium", "Medium"), ("high", "High")], default="medium", max_length=10)),
                ("projected_duration_days", models.PositiveIntegerField(default=0)),
                ("projected_material_cost", models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ("projected_labor_cost", models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ("projected_equipment_cost", models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ("projected_contingency", models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ("projected_total_cost", models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ("sensitivity_fx_10pct_impact", models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ("sensitivity_material_10pct_impact", models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("template", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="plan_scenarios", to="settings.projecttemplate")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_plan_scenarios", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-is_baseline", "-created_at"],
                "indexes": [models.Index(fields=["template", "-created_at"], name="tmpl_scenario_tmpl_idx")],
            },
        ),
    ]
