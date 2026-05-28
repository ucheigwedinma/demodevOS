from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0031_org_normalized_name_and_email_domain"),
    ]

    operations = [
        TrigramExtension(),
        migrations.AddIndex(
            model_name="organization",
            index=GinIndex(
                fields=["normalized_name"],
                name="accounts_org_norm_name_trgm",
                opclasses=["gin_trgm_ops"],
            ),
        ),
    ]
