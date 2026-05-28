"""Seed Celery Beat task for facility service-request and billing workflows."""

from django.db import migrations

TASK_NAME = "Facility Service Request & Billing Workflow Automation"
TASK_PATH = "facility_management.run_scheduled_service_request_helpdesk_workflows"


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
                "Escalate overdue internal facility service requests, sync linked work orders, "
                "refresh invoice collection status, and resolve paid billing helpdesk tickets every 15 minutes."
            ),
        },
    )


def remove_periodic_task(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(name=TASK_NAME).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("facility_management", "0003_seed_celery_beat_maintenance_workflows"),
        ("properties", "0016_servicerequest_assigned_agent_and_more"),
        ("support_desk", "0012_supportticket_invoice_and_more"),
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [
        migrations.RunPython(create_periodic_task, remove_periodic_task),
    ]
