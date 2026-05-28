"""Seed Celery Beat periodic tasks for workflow SLA checks and delegation expiry."""

from django.db import migrations


def create_periodic_tasks(apps, schema_editor):
    IntervalSchedule = apps.get_model("django_celery_beat", "IntervalSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    # Every 15 minutes — SLA breach detection
    schedule_15m, _ = IntervalSchedule.objects.get_or_create(
        every=15,
        period="minutes",
    )
    PeriodicTask.objects.get_or_create(
        name="Workflow SLA Breach Check",
        defaults={
            "task": "workflows.check_sla_breaches",
            "interval": schedule_15m,
            "enabled": True,
            "description": "Detect overdue workflow steps and escalate (every 15 min)",
        },
    )

    # Every 30 minutes — SLA warning notifications
    schedule_30m, _ = IntervalSchedule.objects.get_or_create(
        every=30,
        period="minutes",
    )
    PeriodicTask.objects.get_or_create(
        name="Workflow SLA Warning Notifications",
        defaults={
            "task": "workflows.sla_warning_notifications",
            "interval": schedule_30m,
            "enabled": True,
            "description": "Send warnings for steps approaching SLA deadline (every 30 min)",
        },
    )

    # Every hour — delegation expiry
    schedule_1h, _ = IntervalSchedule.objects.get_or_create(
        every=1,
        period="hours",
    )
    PeriodicTask.objects.get_or_create(
        name="Workflow Delegation Expiry",
        defaults={
            "task": "workflows.expire_delegations",
            "interval": schedule_1h,
            "enabled": True,
            "description": "Mark expired delegations (hourly)",
        },
    )


def remove_periodic_tasks(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(
        name__in=[
            "Workflow SLA Breach Check",
            "Workflow SLA Warning Notifications",
            "Workflow Delegation Expiry",
        ],
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("workflows", "0001_initial"),
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [
        migrations.RunPython(create_periodic_tasks, remove_periodic_tasks),
    ]
