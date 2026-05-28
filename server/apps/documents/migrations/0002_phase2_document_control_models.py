from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0001_initial"),
        ("projects", "0002_project_project_manager_projectphase_and_more"),
        ("properties", "0005_property_classification_property_gps_latitude_and_more"),
        ("finance", "0005_remove_vendor"),
        ("procurement", "0002_vendor"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DocumentOwnerRole",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.SlugField(max_length=60, unique=True)),
                ("name", models.CharField(max_length=120, unique=True)),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="DocumentRetentionPolicy",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.SlugField(max_length=60, unique=True)),
                ("name", models.CharField(max_length=120, unique=True)),
                (
                    "retention_years",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="Leave empty if policy is indefinite.",
                        null=True,
                    ),
                ),
                ("is_indefinite", models.BooleanField(default=False)),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="DocumentType",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.SlugField(max_length=60, unique=True)),
                ("name", models.CharField(max_length=120, unique=True)),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="DocumentWorkflowPhase",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.SlugField(max_length=60, unique=True)),
                ("name", models.CharField(max_length=120, unique=True)),
                ("description", models.TextField(blank=True)),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["sort_order", "name"]},
        ),
        migrations.CreateModel(
            name="Document",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("document_number", models.CharField(max_length=100, unique=True)),
                (
                    "confidentiality_level",
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
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("active", "Active"),
                            ("on_hold", "On Hold"),
                            ("archived", "Archived"),
                            ("retired", "Retired"),
                        ],
                        default="draft",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "client",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.deletion.SET_NULL,
                        related_name="documents",
                        to="finance.customer",
                    ),
                ),
                (
                    "document_type",
                    models.ForeignKey(
                        on_delete=models.deletion.PROTECT,
                        related_name="documents",
                        to="documents.documenttype",
                    ),
                ),
                (
                    "land",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.deletion.SET_NULL,
                        related_name="land_documents",
                        to="properties.property",
                    ),
                ),
                (
                    "owner_role",
                    models.ForeignKey(
                        on_delete=models.deletion.PROTECT,
                        related_name="owned_documents",
                        to="documents.documentownerrole",
                    ),
                ),
                (
                    "phase",
                    models.ForeignKey(
                        on_delete=models.deletion.PROTECT,
                        related_name="documents",
                        to="documents.documentworkflowphase",
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.deletion.SET_NULL,
                        related_name="documents",
                        to="projects.project",
                    ),
                ),
                (
                    "retention_policy",
                    models.ForeignKey(
                        on_delete=models.deletion.PROTECT,
                        related_name="documents",
                        to="documents.documentretentionpolicy",
                    ),
                ),
                (
                    "unit",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.deletion.SET_NULL,
                        related_name="documents",
                        to="properties.unit",
                    ),
                ),
                (
                    "vendor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.deletion.SET_NULL,
                        related_name="documents",
                        to="procurement.vendor",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="DocumentExpiry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("expiry_date", models.DateField()),
                ("alert_90_days", models.BooleanField(default=True)),
                ("alert_30_days", models.BooleanField(default=True)),
                ("alert_expired", models.BooleanField(default=True)),
                (
                    "document",
                    models.OneToOneField(
                        on_delete=models.deletion.CASCADE,
                        related_name="expiry",
                        to="documents.document",
                    ),
                ),
            ],
            options={"ordering": ["expiry_date"]},
        ),
        migrations.CreateModel(
            name="DocumentVersion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("version_major", models.PositiveIntegerField()),
                ("version_minor", models.PositiveIntegerField(default=0)),
                ("file_path", models.CharField(max_length=500)),
                ("change_summary", models.TextField(blank=True)),
                (
                    "approval_status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("approved", "Approved"),
                            ("rejected", "Rejected"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="versions",
                        to="documents.document",
                    ),
                ),
                (
                    "uploaded_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.deletion.SET_NULL,
                        related_name="uploaded_document_versions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-version_major", "-version_minor", "-uploaded_at"]},
        ),
        migrations.AddField(
            model_name="document",
            name="current_version",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.SET_NULL,
                related_name="+",
                to="documents.documentversion",
            ),
        ),
        migrations.CreateModel(
            name="DocumentApproval",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "decision",
                    models.CharField(
                        choices=[("approved", "Approved"), ("rejected", "Rejected")],
                        max_length=20,
                    ),
                ),
                ("comments", models.TextField(blank=True)),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                (
                    "document_version",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="approvals",
                        to="documents.documentversion",
                    ),
                ),
                (
                    "role",
                    models.ForeignKey(
                        on_delete=models.deletion.PROTECT,
                        related_name="document_approvals",
                        to="documents.documentownerrole",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=models.deletion.PROTECT,
                        related_name="document_approvals",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-timestamp"]},
        ),
        migrations.AddIndex(
            model_name="document",
            index=models.Index(fields=["status", "confidentiality_level"], name="documents_d_status_7ebe10_idx"),
        ),
        migrations.AddConstraint(
            model_name="documentapproval",
            constraint=models.UniqueConstraint(
                fields=("document_version", "user"),
                name="documents_unique_document_version_user_approval",
            ),
        ),
        migrations.AddConstraint(
            model_name="documentversion",
            constraint=models.UniqueConstraint(
                fields=("document", "version_major", "version_minor"),
                name="documents_unique_document_version_number",
            ),
        ),
    ]
