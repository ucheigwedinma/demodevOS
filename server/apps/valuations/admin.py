from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.admin_mixins import OrgScopedAdminMixin

from .models import ComparableSale, ValuationAppeal


@admin.register(ComparableSale)
class ComparableSaleAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("address", "sale_date", "sale_price", "property_type", "source")
    list_filter = ("property_type", "source")
    search_fields = ("address",)
    raw_id_fields = ("property",)


@admin.register(ValuationAppeal)
class ValuationAppealAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = (
        "property", "appeal_type", "status", "filed_date",
        "assessed_value", "requested_value", "outcome",
    )
    list_filter = ("appeal_type", "status", "outcome")
    search_fields = ("filing_reference", "representative")
    raw_id_fields = ("property", "valuation")
