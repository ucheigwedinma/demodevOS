from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0013_seed_celery_beat_analytics_reporting_tasks"),
    ]

    operations = [
        migrations.AlterField(
            model_name="campaign",
            name="campaign_type",
            field=models.CharField(
                choices=[
                    ("email_blast", "Email Blast"),
                    ("whatsapp_campaign", "WhatsApp Campaign"),
                    ("sms_blast", "SMS Blast"),
                    ("digital_ads", "Digital Ads"),
                    ("drip", "Drip Campaign"),
                    ("follow_up", "Follow-up Sequence"),
                ],
                max_length=25,
            ),
        ),
        migrations.AddField(
            model_name="campaign",
            name="auto_create_lead_type",
            field=models.CharField(
                choices=[("buyer", "Buyer"), ("tenant", "Tenant"), ("investor", "Investor")],
                default="buyer",
                help_text="Lead type assigned to auto-created campaign leads",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="campaign",
            name="auto_create_leads_count",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Number of leads to auto-create on launch",
            ),
        ),
        migrations.AddField(
            model_name="campaign",
            name="auto_create_leads_on_launch",
            field=models.BooleanField(
                default=False,
                help_text="Automatically create campaign leads when launched",
            ),
        ),
        migrations.AddField(
            model_name="campaign",
            name="auto_created_leads_count",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Denormalized count of leads auto-created by this campaign",
            ),
        ),
        migrations.AddField(
            model_name="campaign",
            name="revenue_attributed",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                help_text="Attributed revenue from this campaign",
                max_digits=15,
            ),
        ),
        migrations.AddField(
            model_name="campaign",
            name="spend_amount",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                help_text="Total campaign spend for ROI tracking",
                max_digits=15,
            ),
        ),
        migrations.AddField(
            model_name="campaign",
            name="target_lead_types",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Lead types to target, e.g. ['buyer', 'investor']",
            ),
        ),
    ]
