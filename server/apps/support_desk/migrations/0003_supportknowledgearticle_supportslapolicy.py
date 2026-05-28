import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("support_desk", "0002_rename_sd_ticket_org_status_created_support_des_organiz_743db3_idx_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SupportKnowledgeArticle",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("slug", models.SlugField(max_length=280)),
                ("summary", models.TextField(blank=True)),
                ("body", models.TextField()),
                ("category", models.CharField(blank=True, max_length=40)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("in_review", "In Review"),
                            ("published", "Published"),
                            ("archived", "Archived"),
                        ],
                        default="draft",
                        max_length=20,
                    ),
                ),
                (
                    "visibility",
                    models.CharField(
                        choices=[
                            ("internal", "Internal"),
                            ("portal", "Partner Portal"),
                            ("public", "Public"),
                        ],
                        default="internal",
                        max_length=20,
                    ),
                ),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("last_reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("next_review_due_at", models.DateField(blank=True, null=True)),
                ("view_count", models.PositiveIntegerField(default=0)),
                ("helpful_votes", models.PositiveIntegerField(default=0)),
                ("not_helpful_votes", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="support_knowledge_articles",
                        to="accounts.organization",
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="support_knowledge_articles_owned",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "reviewer",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="support_knowledge_articles_reviewed",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-updated_at", "-id"],
                "unique_together": {("organization", "slug")},
            },
        ),
        migrations.CreateModel(
            name="SupportSlaPolicy",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("description", models.TextField(blank=True)),
                (
                    "category",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("access", "Access"),
                            ("billing", "Billing"),
                            ("technical", "Technical"),
                            ("workflow", "Workflow"),
                            ("account", "Account"),
                            ("request", "Request"),
                            ("other", "Other"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "priority",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("low", "Low"),
                            ("medium", "Medium"),
                            ("high", "High"),
                            ("critical", "Critical"),
                        ],
                        max_length=10,
                    ),
                ),
                ("response_target_hours", models.PositiveIntegerField(default=4)),
                ("resolution_target_hours", models.PositiveIntegerField(default=24)),
                ("escalate_after_hours", models.PositiveIntegerField(default=2)),
                ("escalation_path", models.JSONField(blank=True, default=list)),
                ("notify_assigned_agent", models.BooleanField(default=True)),
                ("notify_manager", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="support_sla_policies",
                        to="accounts.organization",
                    ),
                ),
            ],
            options={
                "ordering": ["name", "id"],
                "unique_together": {("organization", "name")},
            },
        ),
        migrations.AddIndex(
            model_name="supportknowledgearticle",
            index=models.Index(fields=["organization", "status", "-updated_at"], name="support_des_organiz_79dc59_idx"),
        ),
        migrations.AddIndex(
            model_name="supportknowledgearticle",
            index=models.Index(fields=["organization", "visibility", "-updated_at"], name="support_des_organiz_9df55e_idx"),
        ),
        migrations.AddIndex(
            model_name="supportknowledgearticle",
            index=models.Index(fields=["organization", "category"], name="support_des_organiz_f1f84f_idx"),
        ),
        migrations.AddIndex(
            model_name="supportknowledgearticle",
            index=models.Index(fields=["organization", "next_review_due_at"], name="support_des_organiz_6eab61_idx"),
        ),
        migrations.AddIndex(
            model_name="supportslapolicy",
            index=models.Index(fields=["organization", "is_active"], name="support_des_organiz_d179e8_idx"),
        ),
        migrations.AddIndex(
            model_name="supportslapolicy",
            index=models.Index(fields=["organization", "category", "priority"], name="support_des_organiz_20595f_idx"),
        ),
    ]
