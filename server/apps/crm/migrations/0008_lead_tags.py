from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0007_broker_crm_brkr_org_status_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="lead",
            name="tags",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='Lead labels, e.g. ["high net worth", "mortgage needed"]',
            ),
        ),
    ]
