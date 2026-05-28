"""Seed Celery Beat task for tenant operations workflow automation."""

from django.db import migrations

TASK_NAME = "Tenant Operations Workflow Automation"
TASK_PATH = "tenants.run_scheduled_tenant_operations_workflows"


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
                "Run tenant lease sync, recurring billing, payment reconciliation, "
                "communications, inspection scheduling, document housekeeping, and complaint escalation every 15 minutes."
            ),
        },
    )


def remove_periodic_task(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(name=TASK_NAME).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0004_leaseagreement_leaserenewalrequest_and_more"),
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [
        migrations.RunPython(create_periodic_task, remove_periodic_task),
    ]
