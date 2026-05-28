from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hr", "0022_positionbudget_budget_framework_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="positionbudget",
            name="allowances_rate",
            field=models.DecimalField(
                decimal_places=2,
                default=10.0,
                help_text="Allowance burden percentage applied on base salary.",
                max_digits=5,
                validators=[MinValueValidator(0), MaxValueValidator(100)],
            ),
        ),
        migrations.AddField(
            model_name="positionbudget",
            name="fte",
            field=models.DecimalField(
                decimal_places=2,
                default=1.0,
                help_text="Full-time equivalent allocation for this position budget row.",
                max_digits=4,
                validators=[MinValueValidator(0.1), MaxValueValidator(2.0)],
            ),
        ),
        migrations.AddField(
            model_name="positionbudget",
            name="statutory_benefits_rate",
            field=models.DecimalField(
                decimal_places=2,
                default=15.0,
                help_text="Statutory burden percentage applied on base salary.",
                max_digits=5,
                validators=[MinValueValidator(0), MaxValueValidator(100)],
            ),
        ),
    ]
