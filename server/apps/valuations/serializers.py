from rest_framework import serializers

from apps.properties.models import PropertyValuation

from .models import ComparableSale, ValuationAppeal

# ---------------------------------------------------------------------------
# Valuation Records (PropertyValuation — model lives in apps.properties)
# ---------------------------------------------------------------------------

class ValuationRecordListSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)

    class Meta:
        model = PropertyValuation
        fields = [
            "id", "property", "property_name",
            "valuation_date", "value", "valuation_type",
            "appraiser", "created_at",
        ]


class ValuationRecordDetailSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)

    class Meta:
        model = PropertyValuation
        fields = "__all__"
        read_only_fields = ("id", "created_at")


class ValuationRecordWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyValuation
        fields = [
            "id", "property", "valuation_date", "value",
            "valuation_type", "appraiser", "notes",
        ]
        read_only_fields = ("id",)


# ---------------------------------------------------------------------------
# Comparable Sales
# ---------------------------------------------------------------------------

class ComparableSaleListSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(
        source="property.name", read_only=True, default=None
    )

    class Meta:
        model = ComparableSale
        fields = [
            "id", "property", "property_name",
            "address", "sale_date", "sale_price",
            "property_type", "area_sqft", "price_per_sqft",
            "source", "proximity_km",
            "created_at", "updated_at",
        ]


class ComparableSaleDetailSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(
        source="property.name", read_only=True, default=None
    )

    class Meta:
        model = ComparableSale
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class ComparableSaleWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComparableSale
        fields = [
            "id", "property", "address", "sale_date", "sale_price",
            "property_type", "area_sqft", "price_per_sqft",
            "proximity_km", "source", "notes",
        ]
        read_only_fields = ("id",)


# ---------------------------------------------------------------------------
# Valuation Appeals
# ---------------------------------------------------------------------------

class ValuationAppealListSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)

    class Meta:
        model = ValuationAppeal
        fields = [
            "id", "property", "property_name", "valuation",
            "appeal_type", "status",
            "filed_date", "hearing_date", "decision_date",
            "assessed_value", "requested_value", "decided_value",
            "outcome",
            "created_at", "updated_at",
        ]


class ValuationAppealDetailSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)

    class Meta:
        model = ValuationAppeal
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class ValuationAppealWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ValuationAppeal
        fields = [
            "id", "property", "valuation",
            "appeal_type", "status",
            "filed_date", "hearing_date", "decision_date",
            "assessed_value", "requested_value", "decided_value",
            "filing_reference", "representative", "outcome", "notes",
        ]
        read_only_fields = ("id",)
