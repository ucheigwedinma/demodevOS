from django.contrib import admin

from .models import BackupLog


@admin.register(BackupLog)
class BackupLogAdmin(admin.ModelAdmin):
    list_display = ("backup_type", "status", "file_name", "size_display", "started_at", "completed_at")
    list_filter = ("backup_type", "status")
    search_fields = ("file_name", "b2_path")
    readonly_fields = (
        "backup_type", "status", "file_name", "b2_path", "size_bytes",
        "started_at", "completed_at", "error_message", "metadata",
    )
    ordering = ("-started_at",)

    @admin.display(description="Size")
    def size_display(self, obj):
        if obj.size_bytes is None:
            return "—"
        if obj.size_bytes < 1024:
            return f"{obj.size_bytes} B"
        if obj.size_bytes < 1024 * 1024:
            return f"{obj.size_bytes / 1024:.1f} KB"
        if obj.size_bytes < 1024 * 1024 * 1024:
            return f"{obj.size_bytes / (1024 * 1024):.1f} MB"
        return f"{obj.size_bytes / (1024 * 1024 * 1024):.2f} GB"
