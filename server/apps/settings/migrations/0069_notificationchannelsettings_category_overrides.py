from django.db import migrations, models

import apps.settings.models


class Migration(migrations.Migration):

    dependencies = [
        ("settings", "0068_subscriptionaddon_alter_featureflagdefinition_module_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="notificationchannelsettings",
            name="category_overrides",
            field=models.JSONField(
                blank=True,
                default=apps.settings.models.default_notification_category_overrides,
                help_text="Per-category org-level enable/disable and channel overrides.",
            ),
        ),
        migrations.AddField(
            model_name="notificationchannelsettings",
            name="muted_event_keys",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="List of event_key strings to mute org-wide (e.g. 'project_cost_sync').",
            ),
        ),
    ]
