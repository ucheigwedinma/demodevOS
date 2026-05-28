from django.db import migrations, models

CHANNEL_CHOICES = [
    ("email", "Email"),
    ("whatsapp", "WhatsApp"),
    ("sms", "SMS"),
    ("in_app", "In-App"),
    ("phone", "Phone Call"),
    ("video_call", "Video Call"),
    ("in_person", "In-Person"),
    ("other", "Other"),
]


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0015_seed_celery_beat_payment_reminders"),
    ]

    operations = [
        migrations.AlterField(
            model_name="campaign",
            name="channel",
            field=models.CharField(choices=CHANNEL_CHOICES, max_length=20),
        ),
        migrations.AlterField(
            model_name="communicationlog",
            name="channel",
            field=models.CharField(choices=CHANNEL_CHOICES, max_length=20),
        ),
        migrations.AlterField(
            model_name="leaddocumentevent",
            name="delivered_via",
            field=models.CharField(blank=True, choices=CHANNEL_CHOICES, max_length=20),
        ),
    ]
