"""Seed django-celery-beat tasks for CRM analytics and reporting automations."""

from django.db import migrations

WEEKLY_TASK_NAME = "CRM Weekly Analytics Report"
WEEKLY_TASK_PATH = "crm.send_weekly_analytics_report"
PIPELINE_DROP_TASK_NAME = "CRM Pipeline Drop Monitor"
PIPELINE_DROP_TASK_PATH = "crm.check_pipeline_drop"


def create_periodic_tasks(apps, schema_editor):
    CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")
    IntervalSchedule = apps.get_model("django_celery_beat", "IntervalSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    weekly_schedule, _ = CrontabSchedule.objects.get_or_create(
        minute="0",
        hour="8",
        day_of_week="1",
        day_of_month="*",
        month_of_year="*",
        defaults={"timezone": "UTC"},
    )

    PeriodicTask.objects.get_or_create(
        name=WEEKLY_TASK_NAME,
        defaults={
            "task": WEEKLY_TASK_PATH,
            "crontab": weekly_schedule,
            "enabled": True,
            "description": "Auto-send weekly CRM analytics report to management (Monday 8 AM UTC).",
        },
    )

    pipeline_drop_schedule, _ = IntervalSchedule.objects.get_or_create(
        every=6,
        period="hours",
    )
    PeriodicTask.objects.get_or_create(
        name=PIPELINE_DROP_TASK_NAME,
        defaults={
            "task": PIPELINE_DROP_TASK_PATH,
            "interval": pipeline_drop_schedule,
            "enabled": True,
            "description": "Monitor CRM pipeline drop trends and trigger management alerts (every 6 hours).",
        },
    )


def remove_periodic_tasks(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(
        name__in=[WEEKLY_TASK_NAME, PIPELINE_DROP_TASK_NAME],
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0012_seed_celery_beat_missed_activity_sweep"),
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [
        migrations.RunPython(create_periodic_tasks, remove_periodic_tasks),
    ]
