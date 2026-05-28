from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import apps.notifications.models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0002_alter_notification_category"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserNotificationPreference",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("channel_in_app_enabled", models.BooleanField(default=True)),
                ("channel_email_enabled", models.BooleanField(default=True)),
                ("channel_push_enabled", models.BooleanField(default=False)),
                ("channel_sms_enabled", models.BooleanField(default=False)),
                ("category_preferences", models.JSONField(blank=True, default=apps.notifications.models.default_user_notification_category_preferences)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notification_preferences",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-updated_at"],
            },
        ),
    ]
