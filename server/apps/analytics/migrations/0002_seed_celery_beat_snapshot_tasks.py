"""Seed Celery Beat periodic tasks for analytics snapshot computation."""

from django.db import migrations


def create_periodic_tasks(apps, schema_editor):
    CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")
    IntervalSchedule = apps.get_model("django_celery_beat", "IntervalSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    # Daily at 2:00 AM UTC — portfolio snapshots
    daily_schedule, _ = CrontabSchedule.objects.get_or_create(
        minute="0",
        hour="2",
        day_of_week="*",
        day_of_month="*",
        month_of_year="*",
        defaults={"timezone": "UTC"},
    )
    PeriodicTask.objects.get_or_create(
        name="Daily Portfolio Snapshot",
        defaults={
            "task": "analytics.compute_daily_portfolio_snapshots",
            "crontab": daily_schedule,
            "enabled": True,
            "description": "Compute portfolio analytics snapshots for all organizations (daily 2 AM UTC)",
        },
    )

    # Every hour — board KPI snapshots
    hourly_schedule, _ = IntervalSchedule.objects.get_or_create(
        every=1,
        period="hours",
    )
    PeriodicTask.objects.get_or_create(
        name="Hourly Board KPI Snapshot",
        defaults={
            "task": "analytics.compute_hourly_board_kpi_snapshots",
            "interval": hourly_schedule,
            "enabled": True,
            "description": "Compute board KPI snapshots for all organizations (hourly)",
        },
    )


def remove_periodic_tasks(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(
        name__in=[
            "Daily Portfolio Snapshot",
            "Hourly Board KPI Snapshot",
        ],
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0001_initial"),
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [
        migrations.RunPython(create_periodic_tasks, remove_periodic_tasks),
    ]
