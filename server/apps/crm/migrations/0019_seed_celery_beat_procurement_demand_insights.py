"""Seed django-celery-beat task for CRM -> Procurement demand insight sync."""

from django.db import migrations

TASK_NAME = "CRM Procurement Demand Insight Sync"
TASK_PATH = "crm.sync_procurement_demand_insights"


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
                "Sync CRM bulk-buyer demand into procurement furnishing/add-on package "
                "insights and trigger procurement alerts for high-signal areas (every 12 hours)."
            ),
        },
    )


def remove_periodic_task(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(name=TASK_NAME).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0018_seed_celery_beat_project_demand_insights"),
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [
        migrations.RunPython(create_periodic_task, remove_periodic_task),
    ]
