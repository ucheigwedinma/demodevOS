from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hr", "0023_positionbudget_position_financials"),
    ]

    operations = [
        migrations.AddField(
            model_name="positionbudget",
            name="insurance_rate",
            field=models.DecimalField(
                decimal_places=2,
                default=0.0,
                help_text="Insurance burden percentage applied on base salary.",
                max_digits=5,
                validators=[MinValueValidator(0), MaxValueValidator(100)],
            ),
        ),
        migrations.AddField(
            model_name="positionbudget",
            name="local_tax_rate",
            field=models.DecimalField(
                decimal_places=2,
                default=0.0,
                help_text="Local payroll tax burden percentage applied on base salary.",
                max_digits=5,
                validators=[MinValueValidator(0), MaxValueValidator(100)],
            ),
        ),
        migrations.CreateModel(
            name="PositionBudgetRevision",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("revision_number", models.PositiveIntegerField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending_approval", "Pending Approval"),
                            ("approved", "Approved"),
                            ("rejected", "Rejected"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="pending_approval",
                        max_length=20,
                    ),
                ),
                ("reason", models.TextField()),
                ("proposed_changes", models.JSONField(blank=True, default=dict)),
                ("snapshot_before", models.JSONField(blank=True, default=dict)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("review_notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "budget",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="revisions",
                        to="hr.positionbudget",
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="position_budget_revisions",
                        to="accounts.organization",
                    ),
                ),
                (
                    "requested_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.SET_NULL,
                        related_name="requested_position_budget_revisions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.SET_NULL,
                        related_name="reviewed_position_budget_revisions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "unique_together": {("budget", "revision_number")},
            },
        ),
        migrations.AddIndex(
            model_name="positionbudgetrevision",
            index=models.Index(fields=["organization", "status"], name="hr_pbr_org_status_idx"),
        ),
        migrations.AddIndex(
            model_name="positionbudgetrevision",
            index=models.Index(fields=["organization", "-created_at"], name="hr_pbr_org_created_idx"),
        ),
    ]
