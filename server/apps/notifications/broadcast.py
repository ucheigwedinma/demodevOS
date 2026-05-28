"""
Broadcast helpers for sending real-time events via Channels.

Usage from anywhere in the backend:

    from apps.notifications.broadcast import (
        notify_user, notify_org, broadcast_data_change,
    )

    # Send a notification to a specific user
    notify_user(user_id=42, notification={
        "id": 123, "title": "New PO", "message": "PO-00045 needs approval",
    })

    # Broadcast a data change to all users in an org
    broadcast_data_change(org_id=1, model="PurchaseOrder", action="created", id=45)
"""

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


def _get_layer():
    try:
        return get_channel_layer()
    except Exception:
        logger.debug("Channel layer not available (likely no Redis)")
        return None


def notify_user(user_id: int, notification: dict):
    """Send a notification event to a specific user's WebSocket."""
    layer = _get_layer()
    if not layer:
        return
    try:
        async_to_sync(layer.group_send)(
            f"user_{user_id}",
            {
                "type": "notification.new",
                "notification": notification,
            },
        )
    except Exception:
        logger.debug(f"Failed to send WS notification to user {user_id}", exc_info=True)


def update_unread_count(user_id: int, count: int):
    """Push an updated unread count to a specific user."""
    layer = _get_layer()
    if not layer:
        return
    try:
        async_to_sync(layer.group_send)(
            f"user_{user_id}",
            {
                "type": "notification.count",
                "count": count,
            },
        )
    except Exception:
        logger.debug(f"Failed to send WS count to user {user_id}", exc_info=True)


def broadcast_data_change(org_id: int, model: str, action: str, id: int = None, summary: str = ""):
    """Broadcast a data change event to all connected users in an org.

    Args:
        org_id: Organization ID
        model: Model name (e.g. "PurchaseOrder", "ProjectPhase")
        action: "created", "updated", or "deleted"
        id: Record primary key
        summary: Human-readable summary (e.g. "PO-00045 approved")
    """
    layer = _get_layer()
    if not layer:
        return
    try:
        async_to_sync(layer.group_send)(
            f"org_{org_id}",
            {
                "type": "data.changed",
                "model": model,
                "action": action,
                "id": id,
                "summary": summary,
            },
        )
    except Exception:
        logger.debug(f"Failed to broadcast data change for org {org_id}", exc_info=True)
