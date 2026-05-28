"""Seed Celery Beat task for utilities and energy workflows."""

from django.db import migrations

TASK_NAME = "Facility Utilities & Energy Workflow Automation"
TASK_PATH = "facility_management.run_scheduled_utility_energy_workflows"


def create_periodic_task(apps, schema_editor):
    IntervalSchedule = apps.get_model("django_celery_beat", "IntervalSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    schedule_15m, _ = IntervalSchedule.objects.get_or_create(
        every=15,
        period="minutes",
    )
    PeriodicTask.objects.get_or_create(
        name=TASK_NAME,
        defaults={
            "task": TASK_PATH,
            "interval": schedule_15m,
            "enabled": True,
            "description": (
                "Normalize utility meters, recalculate meter readings, rebuild energy and water "
                "consumption analytics, sync utility bills, and update finance payables every 15 minutes."
            ),
        },
    )


def remove_periodic_task(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(name=TASK_NAME).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("facility_management", "0007_utilitymeter_utilitybill_utilitymeterreading_and_more"),
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [
        migrations.RunPython(create_periodic_task, remove_periodic_task),
    ]
