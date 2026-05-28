"""Seed Celery Beat periodic tasks for automated backups."""

from django.db import migrations


def create_periodic_tasks(apps, schema_editor):
    CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")
    IntervalSchedule = apps.get_model("django_celery_beat", "IntervalSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    # Daily at 3:00 AM UTC — full database backup
    daily_3am, _ = CrontabSchedule.objects.get_or_create(
        minute="0",
        hour="3",
        day_of_week="*",
        day_of_month="*",
        month_of_year="*",
        defaults={"timezone": "UTC"},
    )
    PeriodicTask.objects.get_or_create(
        name="Daily Full Database Backup",
        defaults={
            "task": "apps.backup.tasks.run_full_backup",
            "crontab": daily_3am,
            "enabled": True,
            "description": "pg_dump full backup, gzipped, uploaded to B2 (daily 3 AM UTC)",
        },
    )

    # Every 1 hour — WAL archive upload
    hourly, _ = IntervalSchedule.objects.get_or_create(
        every=1,
        period="hours",
    )
    PeriodicTask.objects.get_or_create(
        name="Hourly WAL Archive Upload",
        defaults={
            "task": "apps.backup.tasks.upload_wal_archives",
            "interval": hourly,
            "enabled": True,
            "description": "Upload accumulated WAL segments to B2 (hourly)",
        },
    )

    # Daily at 3:30 AM UTC — media sync
    daily_330am, _ = CrontabSchedule.objects.get_or_create(
        minute="30",
        hour="3",
        day_of_week="*",
        day_of_month="*",
        month_of_year="*",
        defaults={"timezone": "UTC"},
    )
    PeriodicTask.objects.get_or_create(
        name="Daily Media Sync Backup",
        defaults={
            "task": "apps.backup.tasks.sync_media_backup",
            "crontab": daily_330am,
            "enabled": True,
            "description": "Sync user media uploads to B2 (daily 3:30 AM UTC)",
        },
    )

    # Daily at 4:00 AM UTC — encrypted config backup
    daily_4am, _ = CrontabSchedule.objects.get_or_create(
        minute="0",
        hour="4",
        day_of_week="*",
        day_of_month="*",
        month_of_year="*",
        defaults={"timezone": "UTC"},
    )
    PeriodicTask.objects.get_or_create(
        name="Daily Config Snapshot Backup",
        defaults={
            "task": "apps.backup.tasks.backup_config",
            "crontab": daily_4am,
            "enabled": True,
            "description": "AES-encrypted snapshot of secrets and env config to B2 (daily 4 AM UTC)",
        },
    )

    # Weekly Sunday 4:00 AM UTC — cleanup old backups
    weekly_sun_4am, _ = CrontabSchedule.objects.get_or_create(
        minute="0",
        hour="4",
        day_of_week="0",
        day_of_month="*",
        month_of_year="*",
        defaults={"timezone": "UTC"},
    )
    PeriodicTask.objects.get_or_create(
        name="Weekly Backup Cleanup",
        defaults={
            "task": "apps.backup.tasks.cleanup_old_backups",
            "crontab": weekly_sun_4am,
            "enabled": True,
            "description": "Delete expired backups from B2 (Sunday 4 AM UTC)",
        },
    )


def remove_periodic_tasks(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(
        name__in=[
            "Daily Full Database Backup",
            "Hourly WAL Archive Upload",
            "Daily Media Sync Backup",
            "Daily Config Snapshot Backup",
            "Weekly Backup Cleanup",
        ],
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("backup", "0001_initial"),
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [
        migrations.RunPython(create_periodic_tasks, remove_periodic_tasks),
    ]
