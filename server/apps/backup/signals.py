import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender="backup.BackupLog")
def notify_backup_status(sender, instance, created, **kwargs):
    if not created:
        return
    from apps.notifications.services import Notification, dispatch_workflow_notification

    org = getattr(instance, "organization", None)
    if not org:
        return

    from apps.accounts.models import UserProfile

    admins = [
        p.user
        for p in UserProfile.objects.filter(
            organization=org, role="admin", user__is_active=True
        ).select_related("user")
    ]
    if not admins:
        return

    status = getattr(instance, "status", "completed")
    backup_type = getattr(instance, "backup_type", "database").replace("_", " ").title()
    file_size = getattr(instance, "file_size_mb", None)
    size_text = f" ({file_size:.1f} MB)" if file_size else ""

    if status in ("failed", "error"):
        error_msg = getattr(instance, "error_message", "") or ""
        snippet = (error_msg[:100] + "...") if len(error_msg) > 100 else error_msg
        dispatch_workflow_notification(
            organization=org,
            event_key="backup_failed",
            recipients=admins,
            context={"backup_type": backup_type, "error": snippet},
            fallback_title=f"{backup_type} Backup Failed",
            fallback_message=(
                f"A scheduled {backup_type.lower()} backup has failed."
                f"{f' Error: {snippet}' if snippet else ' Please investigate immediately.'}"
            ),
            fallback_category=Notification.Category.SYSTEM,
            fallback_severity=Notification.Severity.CRITICAL,
        )
    else:
        dispatch_workflow_notification(
            organization=org,
            event_key="backup_completed",
            recipients=admins,
            context={"backup_type": backup_type, "file_size": str(file_size or "")},
            fallback_title=f"{backup_type} Backup Completed",
            fallback_message=(
                f"A {backup_type.lower()} backup has completed successfully{size_text}."
            ),
            fallback_category=Notification.Category.SYSTEM,
        )
