import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0017_alter_documentauditevent_event_type_and_more"),
        ("settings", "0027_escalation_matrix"),
    ]

    operations = [
        migrations.CreateModel(
            name="DocumentAutomationSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "default_signature_provider",
                    models.CharField(
                        choices=[
                            ("docusign", "DocuSign"),
                            ("adobe_acrobat_sign", "Adobe Acrobat Sign"),
                            ("dropbox_sign", "Dropbox Sign"),
                            ("signnow", "SignNow"),
                        ],
                        default="docusign",
                        max_length=40,
                    ),
                ),
                (
                    "enabled_signature_providers",
                    models.JSONField(
                        blank=True,
                        default=[
                            "docusign",
                            "adobe_acrobat_sign",
                            "dropbox_sign",
                            "signnow",
                        ],
                        help_text="Allowed provider keys for e-signature workflows.",
                    ),
                ),
                (
                    "default_generation_confidentiality_level",
                    models.CharField(
                        choices=[
                            ("public", "Public"),
                            ("internal", "Internal"),
                            ("confidential", "Confidential"),
                            ("restricted", "Restricted"),
                        ],
                        default="internal",
                        max_length=20,
                    ),
                ),
                ("default_generation_template_code", models.CharField(blank=True, max_length=120)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "default_generation_owner_role",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="default_for_document_automation_settings",
                        to="documents.documentownerrole",
                    ),
                ),
                (
                    "default_generation_phase",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="default_for_document_automation_settings",
                        to="documents.documentworkflowphase",
                    ),
                ),
                (
                    "default_generation_retention_policy",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="default_for_document_automation_settings",
                        to="documents.documentretentionpolicy",
                    ),
                ),
                (
                    "organization",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="document_automation_settings",
                        to="accounts.organization",
                    ),
                ),
            ],
            options={
                "verbose_name": "Document Automation Settings",
                "verbose_name_plural": "Document Automation Settings",
            },
        ),
    ]
