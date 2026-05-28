from rest_framework import serializers

from .models import CustomDashboard, RiskAlertAcknowledgement

VALID_WIDGET_TYPES = {
    "board_kpi_card",
    "portfolio_kpi_summary",
    "portfolio_type_distribution",
    "portfolio_classification",
    "portfolio_valuation_history",
    "portfolio_unit_occupancy",
    "portfolio_budget_summary",
    "portfolio_construction_budget_burn",
    "portfolio_property_inventory",
    "portfolio_procurement_commitments",
    "portfolio_rental_occupancy",
    "portfolio_maintenance_backlog",
    "portfolio_cash_flow_forecast",
    "portfolio_top_appreciating",
    "portfolio_top_depreciating",
    "portfolio_encumbrance",
}


class CustomDashboardSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomDashboard
        fields = ["id", "name", "is_default", "layout", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_layout(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Layout must be a list of widget configs.")
        for i, item in enumerate(value):
            if not isinstance(item, dict):
                raise serializers.ValidationError(f"Item {i} must be a dict.")
            if item.get("widget_type") not in VALID_WIDGET_TYPES:
                raise serializers.ValidationError(
                    f"Item {i}: invalid widget_type '{item.get('widget_type')}'."
                )
            pos = item.get("position")
            if not isinstance(pos, dict) or not all(
                k in pos for k in ("x", "y", "w", "h")
            ):
                raise serializers.ValidationError(
                    f"Item {i}: position must have x, y, w, h keys."
                )
        return value


class RiskAlertAcknowledgementSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()

    class Meta:
        model = RiskAlertAcknowledgement
        fields = [
            "alert_id",
            "status",
            "assigned_to",
            "assigned_to_name",
            "note",
            "acknowledged_at",
            "resolved_at",
            "updated_by_name",
            "updated_at",
        ]
        read_only_fields = [
            "alert_id",
            "assigned_to_name",
            "acknowledged_at",
            "resolved_at",
            "updated_by_name",
            "updated_at",
        ]

    def get_assigned_to_name(self, obj):
        user = obj.assigned_to
        if user is None:
            return None
        return user.get_full_name() or user.username or user.email

    def get_updated_by_name(self, obj):
        user = obj.updated_by
        if user is None:
            return None
        return user.get_full_name() or user.username or user.email
