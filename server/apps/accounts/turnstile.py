import logging

from rest_framework import serializers

logger = logging.getLogger(__name__)


class HoneypotMixin:
    """Mixin for DRF serializers that reject submissions with a filled honeypot field."""

    def validate_hp_field(self, value):
        if value:
            logger.warning("Honeypot field filled — likely bot submission.")
            raise serializers.ValidationError("Submission rejected.")
        return value
