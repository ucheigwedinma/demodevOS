from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.admin_mixins import OrgScopedAdminMixin

from .models import Notification, UserNotificationPreference


@admin.register(Notification)
class NotificationAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["recipient", "title", "severity", "category", "is_read", "created_at"]
    list_filter = ["severity", "category", "is_read"]
    search_fields = ["title", "message", "recipient__email"]
    readonly_fields = ["created_at", "read_at"]


@admin.register(UserNotificationPreference)
class UserNotificationPreferenceAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "user",
        "channel_in_app_enabled",
        "channel_email_enabled",
        "channel_push_enabled",
        "channel_sms_enabled",
        "updated_at",
    ]
    search_fields = ["user__email", "user__username"]
    readonly_fields = ["created_at", "updated_at"]
