from django.db import migrations, models

import apps.settings.currency


class Migration(migrations.Migration):

    dependencies = [
        ("hr", "0021_seed_celery_beat_critical_vacancy_alerts"),
    ]

    operations = [
        migrations.AddField(
            model_name="positionbudget",
            name="budget_source",
            field=models.CharField(
                choices=[
                    ("corporate_overhead", "Corporate Overhead (Fixed)"),
                    ("project_funding", "Project Loan / Investor Fund (Variable)"),
                ],
                default="corporate_overhead",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="positionbudget",
            name="currency",
            field=models.CharField(
                default=apps.settings.currency.get_default_currency_code,
                max_length=3,
            ),
        ),
        migrations.AddField(
            model_name="positionbudget",
            name="fiscal_period_label",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
    ]
