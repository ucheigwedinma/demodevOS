"""WebSocket consumers for real-time notifications, live data, and presence."""

import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from rest_framework_simplejwt.tokens import AccessToken

logger = logging.getLogger(__name__)


@database_sync_to_async
def get_user_from_token(token_str):
    """Validate JWT and return the user."""
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        token = AccessToken(token_str)
        return User.objects.get(pk=token["user_id"])
    except Exception:
        return None


@database_sync_to_async
def get_user_org_id(user):
    """Get the user's organization ID."""
    profile = getattr(user, "profile", None)
    org = getattr(profile, "organization", None)
    return org.pk if org else None


@database_sync_to_async
def get_user_info(user):
    """Get user display info for presence."""
    profile = getattr(user, "profile", None)
    return {
        "user_id": user.pk,
        "name": user.get_full_name() or user.username,
        "email": user.email,
        "avatar_url": getattr(profile, "avatar_url", "") if profile else "",
        "role": getattr(profile, "role", "") if profile else "",
    }


@database_sync_to_async
def get_unread_count(user):
    from apps.notifications.models import Notification
    return Notification.objects.filter(recipient=user, is_read=False).count()


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    """
    Personal notification channel per user.

    Frontend connects with: ws://host/ws/notifications/?token=<jwt>

    Receives:
      - notification.new    — new notification created
      - notification.count  — updated unread count
      - data.changed        — a model was created/updated/deleted
      - presence.update      — who's online and where
    """

    async def connect(self):
        query = self.scope.get("query_string", b"").decode()
        params = dict(p.split("=", 1) for p in query.split("&") if "=" in p)
        token_str = params.get("token", "")

        self.user = await get_user_from_token(token_str)
        if not self.user:
            await self.close()
            return

        self.org_id = await get_user_org_id(self.user)
        self.user_info = await get_user_info(self.user)
        self.current_page = ""

        # Personal channel
        self.user_group = f"user_{self.user.pk}"
        await self.channel_layer.group_add(self.user_group, self.channel_name)

        # Org-wide channel
        if self.org_id:
            self.org_group = f"org_{self.org_id}"
            await self.channel_layer.group_add(self.org_group, self.channel_name)

            # Presence channel (separate so presence events don't flood the main channel)
            self.presence_group = f"presence_{self.org_id}"
            await self.channel_layer.group_add(self.presence_group, self.channel_name)
        else:
            self.org_group = None
            self.presence_group = None

        await self.accept()

        # Send initial unread count
        count = await get_unread_count(self.user)
        await self.send_json({
            "type": "notification.count",
            "count": count,
        })

        # Announce presence to org
        if self.presence_group:
            await self._update_presence_in_redis("online")
            await self.channel_layer.group_send(
                self.presence_group,
                {
                    "type": "presence.update",
                    "user": self.user_info,
                    "status": "online",
                    "page": "",
                },
            )
            # Send current online users to the newly connected user
            online = await self._get_online_users()
            await self.send_json({
                "type": "presence.roster",
                "users": online,
            })

    async def disconnect(self, close_code):
        # Clear all editing locks held by this user
        if hasattr(self, "org_id") and self.org_id and hasattr(self, "user"):
            await self._clear_all_editing_locks()

        # Announce departure
        if hasattr(self, "presence_group") and self.presence_group:
            await self._update_presence_in_redis("offline")
            await self.channel_layer.group_send(
                self.presence_group,
                {
                    "type": "presence.update",
                    "user": self.user_info if hasattr(self, "user_info") else {},
                    "status": "offline",
                    "page": "",
                },
            )
            await self.channel_layer.group_discard(self.presence_group, self.channel_name)

        if hasattr(self, "user_group"):
            await self.channel_layer.group_discard(self.user_group, self.channel_name)
        if hasattr(self, "org_group") and self.org_group:
            await self.channel_layer.group_discard(self.org_group, self.channel_name)

    async def receive_json(self, content):
        """Handle messages from the client."""
        msg_type = content.get("type")

        if msg_type == "mark_read":
            notification_id = content.get("id")
            if notification_id:
                await self._mark_read(notification_id)
                count = await get_unread_count(self.user)
                await self.send_json({
                    "type": "notification.count",
                    "count": count,
                })

        elif msg_type == "presence.page":
            page = content.get("page", "")
            self.current_page = page
            if self.presence_group:
                await self._update_presence_in_redis("online", page)
                await self.channel_layer.group_send(
                    self.presence_group,
                    {
                        "type": "presence.update",
                        "user": self.user_info,
                        "status": "online",
                        "page": page,
                    },
                )

        elif msg_type == "editing.start":
            # User started editing a record
            model = content.get("model", "")
            record_id = content.get("record_id")
            if model and record_id and self.org_group:
                await self._set_editing_lock(model, record_id)
                await self.channel_layer.group_send(
                    self.org_group,
                    {
                        "type": "editing.update",
                        "user": self.user_info,
                        "model": model,
                        "record_id": record_id,
                        "action": "started",
                    },
                )

        elif msg_type == "editing.stop":
            # User stopped editing a record
            model = content.get("model", "")
            record_id = content.get("record_id")
            if model and record_id and self.org_group:
                await self._clear_editing_lock(model, record_id)
                await self.channel_layer.group_send(
                    self.org_group,
                    {
                        "type": "editing.update",
                        "user": self.user_info,
                        "model": model,
                        "record_id": record_id,
                        "action": "stopped",
                    },
                )

        elif msg_type == "editing.check":
            # Check who's editing a specific record
            model = content.get("model", "")
            record_id = content.get("record_id")
            if model and record_id:
                editor = await self._get_editing_lock(model, record_id)
                await self.send_json({
                    "type": "editing.status",
                    "model": model,
                    "record_id": record_id,
                    "editor": editor,
                })

    # ── Redis presence storage ────────────────────────────────────────

    async def _update_presence_in_redis(self, status, page=""):
        """Store presence in Redis with TTL for auto-cleanup."""
        try:
            import redis.asyncio as aioredis
            import os
            r = aioredis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/2"))
            key = f"presence:{self.org_id}:{self.user.pk}"
            if status == "offline":
                await r.delete(key)
            else:
                import json as json_mod
                await r.setex(
                    key,
                    300,  # 5 min TTL — auto-cleanup if disconnect isn't received
                    json_mod.dumps({
                        **self.user_info,
                        "status": status,
                        "page": page,
                    }),
                )
            await r.aclose()
        except Exception:
            pass  # Presence is best-effort, never break the connection

    async def _get_online_users(self):
        """Get all online users for this org from Redis."""
        try:
            import redis.asyncio as aioredis
            import os
            r = aioredis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/2"))
            pattern = f"presence:{self.org_id}:*"
            users = []
            async for key in r.scan_iter(match=pattern):
                data = await r.get(key)
                if data:
                    import json as json_mod
                    users.append(json_mod.loads(data))
            await r.aclose()
            return users
        except Exception:
            return []

    # ── Helpers ────────────────────────────────────────────────────────

    @database_sync_to_async
    def _mark_read(self, notification_id):
        from apps.notifications.models import Notification
        Notification.objects.filter(pk=notification_id, recipient=self.user).update(is_read=True)

    # ── Group message handlers ────────────────────────────────────────

    async def notification_new(self, event):
        await self.send_json({
            "type": "notification.new",
            "notification": event["notification"],
        })

    async def notification_count(self, event):
        await self.send_json({
            "type": "notification.count",
            "count": event["count"],
        })

    async def data_changed(self, event):
        await self.send_json({
            "type": "data.changed",
            "model": event.get("model"),
            "action": event.get("action"),
            "id": event.get("id"),
            "summary": event.get("summary", ""),
        })

    async def presence_update(self, event):
        """Forward presence update to the client."""
        user_data = event.get("user", {})
        if user_data.get("user_id") == self.user.pk:
            return
        await self.send_json({
            "type": "presence.update",
            "user": user_data,
            "status": event.get("status"),
            "page": event.get("page", ""),
        })

    async def editing_update(self, event):
        """Forward editing awareness to the client."""
        user_data = event.get("user", {})
        if user_data.get("user_id") == self.user.pk:
            return
        await self.send_json({
            "type": "editing.update",
            "user": user_data,
            "model": event.get("model"),
            "record_id": event.get("record_id"),
            "action": event.get("action"),
        })

    # ── Redis editing locks ───────────────────────────────────────────

    async def _get_redis(self):
        import redis.asyncio as aioredis
        import os
        return aioredis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/2"))

    async def _set_editing_lock(self, model, record_id):
        """Mark a record as being edited by this user. TTL 120s for auto-cleanup."""
        try:
            import json as json_mod
            r = await self._get_redis()
            key = f"editing:{self.org_id}:{model}:{record_id}"
            await r.setex(key, 120, json_mod.dumps(self.user_info))
            # Also track which records this user is editing (for disconnect cleanup)
            user_locks_key = f"editing_user:{self.org_id}:{self.user.pk}"
            await r.sadd(user_locks_key, f"{model}:{record_id}")
            await r.expire(user_locks_key, 300)
            await r.aclose()
        except Exception:
            pass

    async def _clear_editing_lock(self, model, record_id):
        """Remove editing lock for a specific record."""
        try:
            r = await self._get_redis()
            key = f"editing:{self.org_id}:{model}:{record_id}"
            await r.delete(key)
            user_locks_key = f"editing_user:{self.org_id}:{self.user.pk}"
            await r.srem(user_locks_key, f"{model}:{record_id}")
            await r.aclose()
        except Exception:
            pass

    async def _get_editing_lock(self, model, record_id):
        """Check who's editing a specific record. Returns user info dict or None."""
        try:
            import json as json_mod
            r = await self._get_redis()
            key = f"editing:{self.org_id}:{model}:{record_id}"
            data = await r.get(key)
            await r.aclose()
            if data:
                return json_mod.loads(data)
            return None
        except Exception:
            return None

    async def _clear_all_editing_locks(self):
        """Clear all editing locks held by this user (called on disconnect)."""
        try:
            r = await self._get_redis()
            user_locks_key = f"editing_user:{self.org_id}:{self.user.pk}"
            locks = await r.smembers(user_locks_key)
            for lock in locks:
                lock_str = lock.decode() if isinstance(lock, bytes) else lock
                key = f"editing:{self.org_id}:{lock_str}"
                await r.delete(key)
                # Broadcast that editing stopped
                parts = lock_str.split(":", 1)
                if len(parts) == 2 and self.org_group:
                    await self.channel_layer.group_send(
                        self.org_group,
                        {
                            "type": "editing.update",
                            "user": self.user_info,
                            "model": parts[0],
                            "record_id": int(parts[1]) if parts[1].isdigit() else parts[1],
                            "action": "stopped",
                        },
                    )
            await r.delete(user_locks_key)
            await r.aclose()
        except Exception:
            pass
