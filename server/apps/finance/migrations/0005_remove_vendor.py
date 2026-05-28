"""Remove Vendor from finance state (moved to procurement) + update Bill FK."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0004_bill_purchase_order"),
        ("procurement", "0002_vendor"),
    ]

    operations = [
        # 1. Update Bill.vendor FK to point to procurement.Vendor
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name="bill",
                    name="vendor",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="bills",
                        to="procurement.vendor",
                    ),
                ),
            ],
            database_operations=[],
        ),

        # 2. Remove Vendor from finance state (table already moved)
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name="Vendor"),
            ],
            database_operations=[],
        ),
    ]
