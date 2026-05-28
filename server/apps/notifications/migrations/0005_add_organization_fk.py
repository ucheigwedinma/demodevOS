from django.db import migrations, models
import django.db.models.deletion


def populate_organization(apps, schema_editor):
    Organization = apps.get_model("accounts", "Organization")
    org = Organization.objects.first()
    if org is None:
        return
    Notification = apps.get_model("notifications", "Notification")
    Notification.objects.filter(organization__isnull=True).update(organization=org)
    UserNotificationPreference = apps.get_model("notifications", "UserNotificationPreference")
    UserNotificationPreference.objects.filter(organization__isnull=True).update(organization=org)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
        ("notifications", "0004_alter_notification_category_reports_ready"),
    ]

    operations = [
        migrations.AddField(
            model_name="notification",
            name="organization",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_notifications",
                to="accounts.organization",
            ),
        ),
        migrations.AddField(
            model_name="usernotificationpreference",
            name="organization",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="org_notification_preferences",
                to="accounts.organization",
            ),
        ),
        migrations.RunPython(populate_organization, migrations.RunPython.noop),
    ]
