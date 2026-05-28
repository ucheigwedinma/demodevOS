from django_filters import rest_framework as filters
from rest_framework import viewsets

from apps.accounts.mixins import OrgScopedMixin
from apps.properties.models import PropertyValuation

from .models import ComparableSale, ValuationAppeal
from .serializers import (
    ComparableSaleDetailSerializer,
    ComparableSaleListSerializer,
    ComparableSaleWriteSerializer,
    ValuationAppealDetailSerializer,
    ValuationAppealListSerializer,
    ValuationAppealWriteSerializer,
    ValuationRecordDetailSerializer,
    ValuationRecordListSerializer,
    ValuationRecordWriteSerializer,
)

# ---------------------------------------------------------------------------
# Valuation Records
# ---------------------------------------------------------------------------

class ValuationRecordFilter(filters.FilterSet):
    date_before = filters.DateFilter(field_name="valuation_date", lookup_expr="lte")
    date_after = filters.DateFilter(field_name="valuation_date", lookup_expr="gte")

    class Meta:
        model = PropertyValuation
        fields = ["property", "valuation_type"]


class ValuationRecordViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    filterset_class = ValuationRecordFilter
    search_fields = ["property__name", "appraiser", "notes"]
    ordering_fields = ["valuation_date", "value", "created_at"]
    ordering = ["-valuation_date"]

    def get_queryset(self):
        return super().get_queryset().select_related("property")

    def get_serializer_class(self):
        if self.action == "list":
            return ValuationRecordListSerializer
        if self.action in ("create", "update", "partial_update"):
            return ValuationRecordWriteSerializer
        return ValuationRecordDetailSerializer


# ---------------------------------------------------------------------------
# Comparable Sales
# ---------------------------------------------------------------------------

class ComparableSaleFilter(filters.FilterSet):
    date_before = filters.DateFilter(field_name="sale_date", lookup_expr="lte")
    date_after = filters.DateFilter(field_name="sale_date", lookup_expr="gte")

    class Meta:
        model = ComparableSale
        fields = ["property", "property_type", "source"]


class ComparableSaleViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    filterset_class = ComparableSaleFilter
    search_fields = ["address", "notes"]
    ordering_fields = ["sale_date", "sale_price", "price_per_sqft", "created_at"]
    ordering = ["-sale_date"]

    def get_queryset(self):
        return super().get_queryset().select_related("property")

    def get_serializer_class(self):
        if self.action == "list":
            return ComparableSaleListSerializer
        if self.action in ("create", "update", "partial_update"):
            return ComparableSaleWriteSerializer
        return ComparableSaleDetailSerializer


# ---------------------------------------------------------------------------
# Valuation Appeals
# ---------------------------------------------------------------------------

class ValuationAppealFilter(filters.FilterSet):
    filed_before = filters.DateFilter(field_name="filed_date", lookup_expr="lte")
    filed_after = filters.DateFilter(field_name="filed_date", lookup_expr="gte")

    class Meta:
        model = ValuationAppeal
        fields = ["property", "appeal_type", "status", "outcome"]


class ValuationAppealViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    filterset_class = ValuationAppealFilter
    search_fields = ["property__name", "filing_reference", "representative", "notes"]
    ordering_fields = ["filed_date", "hearing_date", "assessed_value", "created_at"]
    ordering = ["-filed_date"]

    def get_queryset(self):
        return super().get_queryset().select_related("property", "valuation")

    def get_serializer_class(self):
        if self.action == "list":
            return ValuationAppealListSerializer
        if self.action in ("create", "update", "partial_update"):
            return ValuationAppealWriteSerializer
        return ValuationAppealDetailSerializer
