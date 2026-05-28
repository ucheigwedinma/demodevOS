"""Signals for real-time notification broadcasting via WebSocket."""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender="notifications.Notification")
def broadcast_notification_via_ws(sender, instance, created, **kwargs):
    """When a notification is created, push it to the user's WebSocket channel."""
    if not created:
        return

    try:
        from apps.notifications.broadcast import notify_user, update_unread_count
        from apps.notifications.models import Notification

        # Push the notification
        notify_user(
            user_id=instance.recipient_id,
            notification={
                "id": instance.pk,
                "title": instance.title,
                "message": instance.message,
                "severity": instance.severity,
                "category": instance.category,
                "link_url": instance.link_url or "",
                "created_at": instance.created_at.isoformat() if instance.created_at else "",
            },
        )

        # Push updated unread count
        count = Notification.objects.filter(
            recipient=instance.recipient, is_read=False,
        ).count()
        update_unread_count(user_id=instance.recipient_id, count=count)
    except Exception:
        logger.debug("WS broadcast for notification failed", exc_info=True)
