"""Seed django-celery-beat task for critical vacant positions alert sweep."""

from django.db import migrations


def create_periodic_task(apps, schema_editor):
    CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute="15",
        hour="8",
        day_of_week="*",
        day_of_month="*",
        month_of_year="*",
        defaults={"timezone": "UTC"},
    )

    PeriodicTask.objects.get_or_create(
        name="HR Critical Vacancy Alerts",
        defaults={
            "task": "hr.check_critical_position_vacancy_alerts",
            "crontab": schedule,
            "enabled": True,
            "description": (
                "Daily sweep for critical positions vacant >30 days and "
                "send urgent BU-head alerts."
            ),
        },
    )


def remove_periodic_task(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(name="HR Critical Vacancy Alerts").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("hr", "0020_position_automation_fields"),
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [
        migrations.RunPython(create_periodic_task, remove_periodic_task),
    ]
