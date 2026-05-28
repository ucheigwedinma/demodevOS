"""Move Vendor from finance to procurement (state + table rename + new fields)."""

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("procurement", "0001_initial"),
        ("projects", "0001_initial"),
    ]

    operations = [
        # 1. Add Vendor to procurement state WITHOUT creating DB table
        #    (the table already exists as finance_vendor)
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="Vendor",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("name", models.CharField(max_length=255)),
                        ("contact_person", models.CharField(blank=True, max_length=255)),
                        ("email", models.EmailField(blank=True, max_length=254)),
                        ("phone", models.CharField(blank=True, max_length=50)),
                        ("address", models.TextField(blank=True)),
                        ("tax_id", models.CharField(blank=True, max_length=50)),
                        ("notes", models.TextField(blank=True)),
                        ("is_active", models.BooleanField(default=True)),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        ("updated_at", models.DateTimeField(auto_now=True)),
                    ],
                    options={
                        "ordering": ["name"],
                        "db_table": "finance_vendor",
                    },
                ),
            ],
            database_operations=[],
        ),

        # 2. Rename the DB table from finance_vendor → procurement_vendor
        migrations.AlterModelTable(
            name="vendor",
            table=None,  # Use default: procurement_vendor
        ),

        # 3. Update PurchaseOrder.vendor FK to point to local Vendor
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name="purchaseorder",
                    name="vendor",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="purchase_orders",
                        to="procurement.vendor",
                    ),
                ),
            ],
            database_operations=[],
        ),

        # 4. Add new fields — Approved Vendor Profile
        migrations.AddField(
            model_name="vendor",
            name="category",
            field=models.CharField(
                choices=[("materials", "Materials"), ("contractor", "Contractor"), ("consultant", "Consultant"), ("other", "Other")],
                default="other",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="vendor",
            name="bank_name",
            field=models.CharField(blank=True, max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="vendor",
            name="bank_account_number",
            field=models.CharField(blank=True, max_length=100),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="vendor",
            name="bank_branch",
            field=models.CharField(blank=True, max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="vendor",
            name="approved_projects",
            field=models.ManyToManyField(blank=True, related_name="approved_vendors", to="projects.project"),
        ),

        # 5. Add new fields — Vendor Intelligence
        migrations.AddField(
            model_name="vendor",
            name="performance_rating",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=3,
                validators=[
                    django.core.validators.MinValueValidator(0),
                    django.core.validators.MaxValueValidator(5),
                ],
            ),
        ),
        migrations.AddField(
            model_name="vendor",
            name="delivery_timeliness_score",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=5,
                validators=[
                    django.core.validators.MinValueValidator(0),
                    django.core.validators.MaxValueValidator(100),
                ],
            ),
        ),
        migrations.AddField(
            model_name="vendor",
            name="price_competitiveness",
            field=models.CharField(
                choices=[("low", "Low"), ("average", "Average"), ("high", "High"), ("premium", "Premium")],
                default="average",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="vendor",
            name="compliance_status",
            field=models.CharField(
                choices=[("compliant", "Compliant"), ("non_compliant", "Non-Compliant"), ("pending_review", "Pending Review"), ("expired", "Expired")],
                default="pending_review",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="vendor",
            name="is_blacklisted",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="vendor",
            name="blacklist_reason",
            field=models.TextField(blank=True),
            preserve_default=False,
        ),
    ]
