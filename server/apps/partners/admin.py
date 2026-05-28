from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from apps.admin_mixins import OrgScopedAdminMixin

from .models import (
    OnboardingTemplate,
    OnboardingTemplateDocumentRequirement,
    OnboardingTemplateStage,
    PartnerEntitlement,
    PartnerOnboardingApproval,
    PartnerOnboardingAuditLog,
    PartnerOnboardingCase,
    PartnerOnboardingIntakeDocument,
    PartnerOnboardingStageProgress,
)


class OnboardingTemplateStageInline(TabularInline):
    model = OnboardingTemplateStage
    extra = 0
    fields = [
        "sequence",
        "code",
        "name",
        "is_required",
        "approval_required",
        "approval_role_label",
        "sla_hours",
        "auto_complete",
    ]
    ordering = ["sequence"]


class OnboardingTemplateDocumentRequirementInline(TabularInline):
    model = OnboardingTemplateDocumentRequirement
    extra = 0
    fields = [
        "sequence",
        "code",
        "name",
        "is_required",
        "applies_to_stage",
        "accepted_sources",
        "allowed_extensions",
    ]
    ordering = ["sequence", "id"]


@admin.register(OnboardingTemplate)
class OnboardingTemplateAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "name",
        "code",
        "partner_type",
        "organization",
        "version",
        "is_default",
        "is_active",
    ]
    list_filter = ["partner_type", "is_default", "is_active"]
    search_fields = ["name", "code", "description"]
    inlines = [OnboardingTemplateStageInline, OnboardingTemplateDocumentRequirementInline]


class PartnerOnboardingStageProgressInline(TabularInline):
    model = PartnerOnboardingStageProgress
    extra = 0
    fields = [
        "template_stage",
        "status",
        "is_required",
        "started_at",
        "completed_at",
        "completed_by",
    ]
    readonly_fields = ["started_at", "completed_at", "completed_by"]


class PartnerEntitlementInline(TabularInline):
    model = PartnerEntitlement
    extra = 0
    fields = [
        "portal_role",
        "project",
        "spv_entity",
        "contract_reference",
        "investment_vehicle_reference",
        "budget_scope",
        "can_view_other_investors",
        "can_edit",
        "can_approve",
        "is_active",
    ]


class PartnerOnboardingIntakeDocumentInline(TabularInline):
    model = PartnerOnboardingIntakeDocument
    extra = 0
    fields = [
        "requirement",
        "document_name",
        "source_channel",
        "status",
        "received_at",
        "reviewed_by",
        "reviewed_at",
        "linked_repository_document",
    ]
    readonly_fields = ["received_at", "reviewed_by", "reviewed_at"]


@admin.register(PartnerOnboardingCase)
class PartnerOnboardingCaseAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "title",
        "partner_type",
        "status",
        "organization",
        "project",
        "spv_entity",
        "portal_access_granted",
        "created_at",
    ]
    list_filter = [
        "partner_type",
        "status",
        "portal_access_granted",
        "organization",
    ]
    search_fields = [
        "title",
        "contact_name",
        "contact_email",
        "contract_reference",
        "investment_vehicle_reference",
    ]
    inlines = [
        PartnerOnboardingStageProgressInline,
        PartnerEntitlementInline,
        PartnerOnboardingIntakeDocumentInline,
    ]


@admin.register(PartnerOnboardingApproval)
class PartnerOnboardingApprovalAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "case",
        "decision",
        "approver_role_label",
        "decided_by",
        "decided_at",
    ]
    list_filter = ["decision", "decided_at"]
    search_fields = ["case__title", "approver_role_label", "comments"]


@admin.register(PartnerEntitlement)
class PartnerEntitlementAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "case",
        "portal_role",
        "organization",
        "project",
        "spv_entity",
        "budget_scope",
        "is_active",
        "effective_from",
        "expires_at",
    ]
    list_filter = ["portal_role", "budget_scope", "is_active", "organization"]
    search_fields = ["case__title", "contract_reference", "investment_vehicle_reference"]


@admin.register(PartnerOnboardingAuditLog)
class PartnerOnboardingAuditLogAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "case",
        "event_type",
        "actor",
        "actor_role_label",
        "created_at",
    ]
    list_filter = ["event_type", "created_at"]
    search_fields = ["case__title", "message", "actor_role_label"]
    readonly_fields = [
        "case",
        "event_type",
        "actor",
        "actor_role_label",
        "ip_address",
        "message",
        "payload",
        "created_at",
    ]


@admin.register(OnboardingTemplateDocumentRequirement)
class OnboardingTemplateDocumentRequirementAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "name",
        "code",
        "template",
        "is_required",
        "applies_to_stage",
        "sequence",
    ]
    list_filter = ["template__partner_type", "is_required"]
    search_fields = ["name", "code", "description", "template__name"]


@admin.register(PartnerOnboardingIntakeDocument)
class PartnerOnboardingIntakeDocumentAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "document_name",
        "case",
        "requirement",
        "source_channel",
        "status",
        "received_at",
        "reviewed_by",
    ]
    list_filter = ["status", "source_channel", "case__partner_type"]
    search_fields = [
        "document_name",
        "document_code",
        "external_reference_number",
        "case__title",
        "case__contact_name",
        "case__contact_email",
    ]
    readonly_fields = ["submitted_by", "reviewed_by", "reviewed_at", "created_at", "updated_at"]
