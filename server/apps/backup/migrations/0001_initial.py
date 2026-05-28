from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="BackupLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("backup_type", models.CharField(choices=[("full", "Full Database Backup"), ("wal", "WAL Archive"), ("media", "Media Sync"), ("config", "Config Snapshot")], max_length=10)),
                ("status", models.CharField(choices=[("started", "Started"), ("uploading", "Uploading"), ("completed", "Completed"), ("failed", "Failed")], default="started", max_length=12)),
                ("file_name", models.CharField(max_length=255)),
                ("b2_path", models.CharField(blank=True, max_length=512)),
                ("size_bytes", models.BigIntegerField(blank=True, null=True)),
                ("started_at", models.DateTimeField()),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("error_message", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
            ],
            options={
                "verbose_name": "Backup log",
                "verbose_name_plural": "Backup logs",
                "ordering": ["-started_at"],
            },
        ),
    ]
