from rest_framework import serializers

from apps.crm.models import CommunicationLog
from apps.documents.serializers import DocumentMetadataSerializer


class PortalDocumentVaultSerializer(DocumentMetadataSerializer):
    current_version_id = serializers.IntegerField(source="current_version.id", read_only=True, allow_null=True)
    current_version_file_path = serializers.CharField(
        source="current_version.file_path",
        read_only=True,
        allow_null=True,
    )
    current_version_label = serializers.SerializerMethodField()
    expiry_date = serializers.DateField(source="expiry.expiry_date", read_only=True, allow_null=True)
    expiry_trigger_category = serializers.CharField(
        source="expiry.trigger_category",
        read_only=True,
        allow_null=True,
    )

    class Meta(DocumentMetadataSerializer.Meta):
        fields = DocumentMetadataSerializer.Meta.fields + [
            "current_version_id",
            "current_version_file_path",
            "current_version_label",
            "expiry_date",
            "expiry_trigger_category",
        ]

    def get_current_version_label(self, obj):
        version = getattr(obj, "current_version", None)
        if not version:
            return None
        return f"v{version.version_major}.{version.version_minor}"


class PortalCommunicationSerializer(serializers.ModelSerializer):
    lead_name = serializers.CharField(source="lead.full_name", read_only=True)
    performed_by_name = serializers.CharField(
        source="performed_by.get_full_name",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = CommunicationLog
        fields = [
            "id",
            "lead",
            "lead_name",
            "channel",
            "direction",
            "status",
            "subject",
            "summary",
            "body",
            "from_address",
            "to_address",
            "attachments",
            "performed_by",
            "performed_by_name",
            "communicated_at",
            "created_at",
        ]
        read_only_fields = fields

