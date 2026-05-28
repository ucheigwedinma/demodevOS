"""Seed the django-celery-beat periodic task for the weekly budget digest.

Runs every Monday at 8:00 AM UTC.
"""
from django.db import migrations


def create_periodic_task(apps, schema_editor):
    CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute="0",
        hour="8",
        day_of_week="1",  # Monday
        day_of_month="*",
        month_of_year="*",
        defaults={"timezone": "UTC"},
    )

    PeriodicTask.objects.get_or_create(
        name="Weekly Budget Digest",
        defaults={
            "task": "finance.send_weekly_budget_digest",
            "crontab": schedule,
            "enabled": True,
            "description": "Send weekly budget summary to all org users (Monday 8 AM UTC)",
        },
    )


def remove_periodic_task(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(name="Weekly Budget Digest").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0008_billlineitem_account_billlineitem_cost_center_and_more"),
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [
        migrations.RunPython(create_periodic_task, remove_periodic_task),
    ]
