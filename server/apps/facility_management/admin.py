from django.contrib import admin

from apps.admin_mixins import OrgScopedAdminMixin

from .models import (
    Facility,
    FacilityComplianceChecklist,
    FacilityComplianceChecklistItem,
    FacilityDocument,
    FacilityFloor,
    FacilityIncident,
    FacilityRegulatoryDocument,
    FacilitySafetyAuditLog,
    FacilityUnitSpace,
    FacilityZone,
    UtilityBill,
    UtilityConsumption,
    UtilityMeter,
    UtilityMeterReading,
)


@admin.register(UtilityConsumption)
class UtilityConsumptionAdmin(OrgScopedAdminMixin, admin.ModelAdmin):
    list_display = [
        "reading_date",
        "organization",
        "property",
        "electricity_kwh",
        "water_m3",
        "diesel_liters",
        "gas_m3",
    ]
    list_filter = ["organization", "reading_date", "property"]
    search_fields = ["property__name", "notes"]


@admin.register(UtilityMeter)
class UtilityMeterAdmin(OrgScopedAdminMixin, admin.ModelAdmin):
    list_display = [
        "meter_number",
        "utility_type",
        "property",
        "provider_name",
        "is_smart_meter",
        "is_active",
        "organization",
    ]
    list_filter = ["organization", "utility_type", "is_smart_meter", "is_active"]
    search_fields = ["meter_number", "property__name", "provider_name", "location_label"]


@admin.register(UtilityMeterReading)
class UtilityMeterReadingAdmin(OrgScopedAdminMixin, admin.ModelAdmin):
    list_display = [
        "meter",
        "reading_at",
        "reading_value",
        "consumption_delta",
        "is_estimated",
        "is_anomaly",
        "organization",
    ]
    list_filter = ["organization", "is_estimated", "is_anomaly", "meter__utility_type"]
    search_fields = ["meter__meter_number", "meter__property__name", "anomaly_reason", "notes"]


@admin.register(UtilityBill)
class UtilityBillAdmin(OrgScopedAdminMixin, admin.ModelAdmin):
    list_display = [
        "bill_number",
        "utility_type",
        "property",
        "provider_name",
        "due_date",
        "total_amount",
        "status",
        "organization",
    ]
    list_filter = ["organization", "utility_type", "status", "due_date"]
    search_fields = ["bill_number", "property__name", "provider_name", "vendor__name"]


@admin.register(FacilityIncident)
class FacilityIncidentAdmin(OrgScopedAdminMixin, admin.ModelAdmin):
    list_display = [
        "incident_code",
        "title",
        "organization",
        "property",
        "facility",
        "category",
        "severity",
        "status",
        "occurred_at",
    ]
    list_filter = ["organization", "category", "severity", "status"]
    search_fields = [
        "incident_code",
        "title",
        "description",
        "reported_by",
        "assigned_to",
        "property__name",
        "facility__facility_code",
    ]


class FacilityComplianceChecklistItemInline(admin.TabularInline):
    model = FacilityComplianceChecklistItem
    extra = 0


@admin.register(FacilityComplianceChecklist)
class FacilityComplianceChecklistAdmin(OrgScopedAdminMixin, admin.ModelAdmin):
    list_display = [
        "title",
        "property",
        "facility",
        "checklist_type",
        "status",
        "due_date",
        "overall_score",
        "organization",
    ]
    list_filter = ["organization", "checklist_type", "status", "due_date"]
    search_fields = ["title", "property__name", "facility__facility_code", "responsible_person"]
    inlines = [FacilityComplianceChecklistItemInline]


@admin.register(FacilityRegulatoryDocument)
class FacilityRegulatoryDocumentAdmin(OrgScopedAdminMixin, admin.ModelAdmin):
    list_display = [
        "property_document",
        "property",
        "facility",
        "status",
        "expiry_date",
        "review_due_date",
        "organization",
    ]
    list_filter = ["organization", "status", "expiry_date", "review_due_date"]
    search_fields = [
        "property_document__title",
        "reference_number",
        "issuing_authority",
        "property__name",
        "facility__facility_code",
    ]


@admin.register(FacilityDocument)
class FacilityDocumentAdmin(OrgScopedAdminMixin, admin.ModelAdmin):
    list_display = [
        "title",
        "document_type",
        "property",
        "facility",
        "asset_component",
        "status",
        "source",
        "review_due_date",
        "expiry_date",
        "organization",
    ]
    list_filter = ["organization", "document_type", "status", "source"]
    search_fields = [
        "title",
        "reference_number",
        "property__name",
        "facility__facility_code",
        "asset_component__name",
        "linked_work_order__title",
    ]


@admin.register(FacilitySafetyAuditLog)
class FacilitySafetyAuditLogAdmin(OrgScopedAdminMixin, admin.ModelAdmin):
    list_display = [
        "created_at",
        "entity_type",
        "event_type",
        "summary",
        "facility",
        "organization",
    ]
    list_filter = ["organization", "entity_type", "event_type", "created_at"]
    search_fields = ["summary", "property__name", "facility__facility_code"]


@admin.register(Facility)
class FacilityAdmin(OrgScopedAdminMixin, admin.ModelAdmin):
    list_display = [
        "facility_code",
        "property",
        "facility_classification",
        "ownership_type",
        "lease_end_date",
        "organization",
    ]
    list_filter = ["organization", "facility_classification", "ownership_type"]
    search_fields = ["facility_code", "property__name", "property__address", "lease_party_name"]


@admin.register(FacilityFloor)
class FacilityFloorAdmin(OrgScopedAdminMixin, admin.ModelAdmin):
    list_display = [
        "facility",
        "name",
        "floor_number",
        "floor_code",
        "is_active",
        "organization",
    ]
    list_filter = ["organization", "facility", "is_active"]
    search_fields = ["name", "floor_code", "facility__facility_code", "facility__property__name"]


@admin.register(FacilityZone)
class FacilityZoneAdmin(OrgScopedAdminMixin, admin.ModelAdmin):
    list_display = [
        "facility",
        "floor",
        "name",
        "zone_code",
        "zone_type",
        "is_active",
        "organization",
    ]
    list_filter = ["organization", "facility", "floor", "zone_type", "is_active"]
    search_fields = ["name", "zone_code", "facility__facility_code", "facility__property__name"]


@admin.register(FacilityUnitSpace)
class FacilityUnitSpaceAdmin(OrgScopedAdminMixin, admin.ModelAdmin):
    list_display = [
        "facility",
        "zone",
        "unit",
        "space_label",
        "organization",
    ]
    list_filter = ["organization", "facility", "zone"]
    search_fields = ["space_label", "unit__unit_number", "facility__facility_code", "facility__property__name"]
