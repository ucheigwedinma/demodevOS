from django.db import models


class BackupLog(models.Model):
    """Tracks every backup operation (full, WAL, media, config)."""

    class BackupType(models.TextChoices):
        FULL = "full", "Full Database Backup"
        WAL = "wal", "WAL Archive"
        MEDIA = "media", "Media Sync"
        CONFIG = "config", "Config Snapshot"

    class Status(models.TextChoices):
        STARTED = "started", "Started"
        UPLOADING = "uploading", "Uploading"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    backup_type = models.CharField(max_length=10, choices=BackupType.choices)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.STARTED)
    file_name = models.CharField(max_length=255)
    b2_path = models.CharField(max_length=512, blank=True)
    size_bytes = models.BigIntegerField(null=True, blank=True)
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-started_at"]
        verbose_name = "Backup log"
        verbose_name_plural = "Backup logs"

    def __str__(self):
        return f"{self.get_backup_type_display()} — {self.file_name} ({self.status})"
