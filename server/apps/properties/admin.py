from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from apps.admin_mixins import OrgScopedAdminMixin

from .models import (
    Property,
    PropertyDocument,
    PropertyEncumbrance,
    PropertyImage,
    PropertyOwnership,
    PropertyValuation,
    Unit,
)


class UnitInline(TabularInline):
    model = Unit
    extra = 0
    fields = ["unit_number", "floor", "area_sqft", "bedrooms", "bathrooms", "asking_price", "status"]


class PropertyImageInline(TabularInline):
    model = PropertyImage
    extra = 0


class PropertyOwnershipInline(TabularInline):
    model = PropertyOwnership
    extra = 0
    fields = [
        "legal_owner_name", "ownership_structure",
        "ownership_percentage", "title_deed_number",
        "registration_authority", "date_of_registration", "deed_expiry",
    ]


class PropertyEncumbranceInline(TabularInline):
    model = PropertyEncumbrance
    extra = 0
    fields = [
        "encumbrance_type", "title", "amount",
        "status", "date_filed", "date_resolved", "reference_number",
    ]


@admin.register(Property)
class PropertyAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["name", "property_type", "classification", "is_active", "current_value", "created_at"]
    list_filter = ["property_type", "classification", "is_active"]
    search_fields = ["name", "address", "plot_number"]
    inlines = [UnitInline, PropertyImageInline, PropertyOwnershipInline, PropertyEncumbranceInline]


@admin.register(Unit)
class UnitAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["unit_number", "property", "status", "asking_price"]
    list_filter = ["status"]
    search_fields = ["unit_number"]


@admin.register(PropertyImage)
class PropertyImageAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["property", "caption", "is_primary", "uploaded_at"]
    list_filter = ["is_primary"]


@admin.register(PropertyDocument)
class PropertyDocumentAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["property", "title", "document_type", "uploaded_at"]
    list_filter = ["document_type"]
    search_fields = ["title"]


@admin.register(PropertyValuation)
class PropertyValuationAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["property", "valuation_date", "value", "valuation_type"]
    list_filter = ["valuation_type"]


@admin.register(PropertyOwnership)
class PropertyOwnershipAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "property", "legal_owner_name", "ownership_structure",
        "ownership_percentage", "title_deed_number",
    ]
    list_filter = ["ownership_structure"]
    search_fields = ["legal_owner_name", "title_deed_number"]


@admin.register(PropertyEncumbrance)
class PropertyEncumbranceAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "property", "title", "encumbrance_type",
        "status", "amount", "date_filed",
    ]
    list_filter = ["encumbrance_type", "status"]
    search_fields = ["title", "reference_number"]
