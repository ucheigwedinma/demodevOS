from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id", "title", "message", "severity", "category",
            "is_read", "link_url", "created_at", "read_at",
        ]
        read_only_fields = fields


class NotificationAdminSerializer(serializers.ModelSerializer):
    """Includes recipient details for admin/org-wide views."""

    recipient_email = serializers.EmailField(source="recipient.email", read_only=True)
    recipient_name = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            "id", "title", "message", "severity", "category",
            "is_read", "link_url", "created_at", "read_at",
            "recipient_email", "recipient_name",
        ]
        read_only_fields = fields

    def get_recipient_name(self, obj) -> str:
        return obj.recipient.get_full_name() or obj.recipient.email
