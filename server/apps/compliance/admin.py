from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.admin_mixins import OrgScopedAdminMixin

from .models import ComplianceAudit, ComplianceRequirement, ComplianceViolation, PropertyCompliance


@admin.register(ComplianceRequirement)
class ComplianceRequirementAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("name", "category", "renewal_frequency", "is_mandatory", "is_active")
    list_filter = ("category", "renewal_frequency", "is_mandatory", "is_active")
    search_fields = ("name", "regulatory_reference")


@admin.register(PropertyCompliance)
class PropertyComplianceAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("property", "requirement", "status", "expiry_date", "responsible_person")
    list_filter = ("status",)
    search_fields = ("certificate_number", "issuing_authority", "responsible_person")
    raw_id_fields = ("property", "requirement")


@admin.register(ComplianceViolation)
class ComplianceViolationAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("title", "property", "violation_type", "severity", "status", "reported_date")
    list_filter = ("violation_type", "severity", "status")
    search_fields = ("title", "assigned_to")
    raw_id_fields = ("property", "compliance_item")


@admin.register(ComplianceAudit)
class ComplianceAuditAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("title", "property", "audit_type", "status", "scheduled_date", "overall_rating")
    list_filter = ("audit_type", "status", "overall_rating", "follow_up_required")
    search_fields = ("title", "auditor")
    raw_id_fields = ("property",)
