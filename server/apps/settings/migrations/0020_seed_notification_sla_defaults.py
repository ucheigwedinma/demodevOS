from django.db import migrations


def seed_notification_sla_defaults(apps, schema_editor):
    Organization = apps.get_model("accounts", "Organization")
    NotificationChannelSettings = apps.get_model("settings", "NotificationChannelSettings")
    SlaSeverityTier = apps.get_model("settings", "SlaSeverityTier")
    NotificationTemplate = apps.get_model("settings", "NotificationTemplate")

    tiers = [
        {
            "level": "info",
            "sort_order": 10,
            "response_time_hours": 24,
            "escalation_path": ["team_lead"],
            "notification_channels": ["in_app", "email"],
        },
        {
            "level": "review",
            "sort_order": 20,
            "response_time_hours": 8,
            "escalation_path": ["manager"],
            "notification_channels": ["in_app", "email"],
        },
        {
            "level": "action_required",
            "sort_order": 30,
            "response_time_hours": 2,
            "escalation_path": ["manager", "operations_head"],
            "notification_channels": ["in_app", "email", "push"],
        },
        {
            "level": "escalation",
            "sort_order": 40,
            "response_time_hours": 1,
            "escalation_path": ["operations_head", "executive_team"],
            "notification_channels": ["in_app", "email", "push", "sms"],
        },
    ]

    for org in Organization.objects.all().iterator():
        NotificationChannelSettings.objects.get_or_create(
            organization_id=org.id,
            defaults={
                "email_enabled": True,
                "in_app_enabled": True,
                "sms_enabled": False,
                "push_enabled": False,
            },
        )

        for tier in tiers:
            SlaSeverityTier.objects.get_or_create(
                organization_id=org.id,
                level=tier["level"],
                defaults=tier,
            )

        # Seed starter templates only if no system templates exist yet.
        if not NotificationTemplate.objects.filter(
            organization_id=org.id,
            is_system=True,
        ).exists():
            NotificationTemplate.objects.bulk_create(
                [
                    NotificationTemplate(
                        organization_id=org.id,
                        code="workflow_pending_email",
                        name="Workflow Pending (Email)",
                        description="Default email template for pending approvals.",
                        channel="email",
                        event_key="workflow_pending",
                        severity_tier="review",
                        subject="Approval required: {{document_title}}",
                        body_text=(
                            "Hello {{assignee_name}},\n\n"
                            "A new item requires your review: {{document_title}}.\n"
                            "Due: {{due_at}}.\n\n"
                            "Open item: {{action_url}}"
                        ),
                        body_html=(
                            "<p>Hello {{assignee_name}},</p>"
                            "<p>A new item requires your review: <strong>{{document_title}}</strong>.</p>"
                            "<p>Due: {{due_at}}</p>"
                            "<p><a href=\"{{action_url}}\">Open item</a></p>"
                        ),
                        variables=["assignee_name", "document_title", "due_at", "action_url"],
                        is_active=True,
                        is_system=True,
                    ),
                    NotificationTemplate(
                        organization_id=org.id,
                        code="workflow_pending_in_app",
                        name="Workflow Pending (In-App)",
                        description="Default in-app notification for pending approvals.",
                        channel="in_app",
                        event_key="workflow_pending",
                        severity_tier="review",
                        subject="",
                        body_text="Approval required for {{document_title}}. Due {{due_at}}.",
                        body_html="",
                        variables=["document_title", "due_at"],
                        is_active=True,
                        is_system=True,
                    ),
                    NotificationTemplate(
                        organization_id=org.id,
                        code="sla_escalation_sms",
                        name="SLA Escalation (SMS)",
                        description="Default SMS escalation message.",
                        channel="sms",
                        event_key="sla_escalation",
                        severity_tier="escalation",
                        subject="",
                        body_text="Escalation: {{document_title}} overdue. Owner: {{assignee_name}}.",
                        body_html="",
                        variables=["document_title", "assignee_name"],
                        is_active=True,
                        is_system=True,
                    ),
                    NotificationTemplate(
                        organization_id=org.id,
                        code="sla_escalation_push",
                        name="SLA Escalation (Push)",
                        description="Default push escalation alert.",
                        channel="push",
                        event_key="sla_escalation",
                        severity_tier="escalation",
                        subject="SLA Escalation",
                        body_text="{{document_title}} exceeded SLA. Immediate action required.",
                        body_html="",
                        variables=["document_title"],
                        is_active=True,
                        is_system=True,
                    ),
                ]
            )


def reverse_seed_notification_sla_defaults(apps, schema_editor):
    NotificationTemplate = apps.get_model("settings", "NotificationTemplate")
    NotificationTemplate.objects.filter(
        code__in=[
            "workflow_pending_email",
            "workflow_pending_in_app",
            "sla_escalation_sms",
            "sla_escalation_push",
        ],
        is_system=True,
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("settings", "0019_notificationchannelsettings_notificationtemplate_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_notification_sla_defaults, reverse_seed_notification_sla_defaults),
    ]
