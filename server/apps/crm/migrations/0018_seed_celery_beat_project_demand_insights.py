"""Seed django-celery-beat task for CRM -> Projects demand insight sync."""

from django.db import migrations

TASK_NAME = "CRM Projects Demand Insight Sync"
TASK_PATH = "crm.sync_project_demand_insights"


def create_periodic_task(apps, schema_editor):
    IntervalSchedule = apps.get_model("django_celery_beat", "IntervalSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    schedule, _ = IntervalSchedule.objects.get_or_create(
        every=12,
        period="hours",
    )

    PeriodicTask.objects.get_or_create(
        name=TASK_NAME,
        defaults={
            "task": TASK_PATH,
            "interval": schedule,
            "enabled": True,
            "description": (
                "Sync CRM demand analytics into projects planning insights and trigger "
                "new development alerts for high-demand areas (every 12 hours)."
            ),
        },
    )


def remove_periodic_task(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(name=TASK_NAME).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0017_unitreservation_allocation_letter"),
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [
        migrations.RunPython(create_periodic_task, remove_periodic_task),
    ]
