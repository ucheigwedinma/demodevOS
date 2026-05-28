import django.db.models.deletion
from django.conf import settings
from django.core import validators
from django.db import migrations, models

import apps.support_desk.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("accounts", "0024_rename_accounts_us_user_id_fb1424_idx_accounts_us_user_id_7d84e2_idx_and_more"),
        ("settings", "0046_alter_masterdataentry_category_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SupportTicket",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ticket_id", models.CharField(blank=True, db_index=True, max_length=24, unique=True)),
                ("subject", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("access", "Access"),
                            ("billing", "Billing"),
                            ("technical", "Technical"),
                            ("workflow", "Workflow"),
                            ("account", "Account"),
                            ("request", "Request"),
                            ("other", "Other"),
                        ],
                        default="other",
                        max_length=20,
                    ),
                ),
                (
                    "priority",
                    models.CharField(
                        choices=[
                            ("low", "Low"),
                            ("medium", "Medium"),
                            ("high", "High"),
                            ("critical", "Critical"),
                        ],
                        default="medium",
                        max_length=10,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("open", "Open"),
                            ("in_progress", "In Progress"),
                            ("pending_requester", "Pending Customer"),
                            ("escalated", "Escalated"),
                            ("resolved", "Resolved"),
                            ("closed", "Closed"),
                        ],
                        default="open",
                        max_length=20,
                    ),
                ),
                ("sla_deadline", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("first_response_at", models.DateTimeField(blank=True, null=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("closed_at", models.DateTimeField(blank=True, null=True)),
                ("escalated_at", models.DateTimeField(blank=True, null=True)),
                ("resolution_notes", models.TextField(blank=True)),
                (
                    "customer_satisfaction_score",
                    models.PositiveSmallIntegerField(
                        blank=True,
                        null=True,
                        validators=[validators.MinValueValidator(1), validators.MaxValueValidator(5)],
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "assigned_agent",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="support_tickets_assigned",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "department",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="support_tickets",
                        to="settings.department",
                    ),
                ),
                (
                    "linked_tickets",
                    models.ManyToManyField(blank=True, to="support_desk.supportticket"),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="support_tickets",
                        to="accounts.organization",
                    ),
                ),
                (
                    "requester",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="support_tickets_requested",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="SupportTicketComment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "comment_type",
                    models.CharField(
                        choices=[
                            ("internal_note", "Internal Note"),
                            ("requester_reply", "Reply to Requester"),
                        ],
                        max_length=20,
                    ),
                ),
                ("body", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "author",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="support_ticket_comments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "ticket",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="comments",
                        to="support_desk.supportticket",
                    ),
                ),
            ],
            options={
                "ordering": ["created_at", "id"],
            },
        ),
        migrations.CreateModel(
            name="SupportTicketAttachment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("label", models.CharField(blank=True, max_length=255)),
                ("file", models.FileField(upload_to=apps.support_desk.models.support_ticket_attachment_upload_to)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "ticket",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attachments",
                        to="support_desk.supportticket",
                    ),
                ),
                (
                    "uploaded_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="support_ticket_attachments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.AddIndex(
            model_name="supportticket",
            index=models.Index(fields=["organization", "status", "-created_at"], name="sd_ticket_org_status_created"),
        ),
        migrations.AddIndex(
            model_name="supportticket",
            index=models.Index(fields=["organization", "priority", "-created_at"], name="sd_ticket_org_priority_created"),
        ),
        migrations.AddIndex(
            model_name="supportticket",
            index=models.Index(fields=["organization", "assigned_agent", "status"], name="sd_ticket_org_agent_status"),
        ),
        migrations.AddIndex(
            model_name="supportticket",
            index=models.Index(fields=["organization", "sla_deadline"], name="sd_ticket_org_sla"),
        ),
        migrations.AddIndex(
            model_name="supportticketcomment",
            index=models.Index(fields=["ticket", "comment_type", "created_at"], name="sd_comment_ticket_type_created"),
        ),
    ]
