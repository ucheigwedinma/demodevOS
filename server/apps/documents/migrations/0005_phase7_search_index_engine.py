import django.contrib.postgres.indexes
import django.contrib.postgres.search
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0004_rename_documents_d_status_7ebe10_idx_documents_d_status_511254_idx"),
    ]

    operations = [
        migrations.CreateModel(
            name="DocumentSearchIndex",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("extracted_text", models.TextField(blank=True)),
                ("ocr_text", models.TextField(blank=True)),
                ("clause_text", models.TextField(blank=True)),
                ("indexed_clauses", models.JSONField(blank=True, default=list)),
                ("combined_text", models.TextField(blank=True)),
                ("search_vector", django.contrib.postgres.search.SearchVectorField(blank=True, null=True)),
                ("content_hash", models.CharField(blank=True, max_length=64)),
                (
                    "index_status",
                    models.CharField(
                        choices=[("pending", "Pending"), ("indexed", "Indexed"), ("failed", "Failed")],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("indexed_at", models.DateTimeField(blank=True, null=True)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "document",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="search_index",
                        to="documents.document",
                    ),
                ),
                (
                    "document_version",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="search_indexes",
                        to="documents.documentversion",
                    ),
                ),
            ],
            options={
                "ordering": ["-indexed_at", "-updated_at"],
                "indexes": [
                    django.contrib.postgres.indexes.GinIndex(fields=["search_vector"], name="documents_search_vector_gin"),
                    models.Index(fields=["index_status", "updated_at"], name="documents_d_index_s_98c1ec_idx"),
                ],
            },
        ),
    ]
