from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.admin_mixins import OrgScopedAdminMixin

from .models import (
    ControlledVocabularyTerm,
    Document,
    DocumentApproval,
    DocumentAuditEvent,
    DocumentBusinessUnitMembership,
    DocumentComment,
    DocumentDomain,
    DocumentExpiry,
    DocumentGenerationRecord,
    DocumentGovernanceCharter,
    DocumentOwnerRole,
    DocumentProjectMembership,
    DocumentRetentionPolicy,
    DocumentRoleScope,
    DocumentSearchIndex,
    DocumentSignatureRequest,
    DocumentType,
    DocumentVersion,
    DocumentWorkflowInstance,
    DocumentWorkflowPhase,
    DocumentWorkflowRule,
    DocumentWorkflowStep,
    DocumentWorkflowTemplate,
    DocumentWorkflowTemplateStep,
)


@admin.register(DocumentGovernanceCharter)
class DocumentGovernanceCharterAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "title",
        "version",
        "status",
        "repository_scope",
        "external_portal_access",
        "includes_digital_signature_v1",
        "approved_at",
        "review_due_at",
    ]
    list_filter = [
        "status",
        "repository_scope",
        "external_portal_access",
        "includes_digital_signature_v1",
    ]
    search_fields = ["title", "version", "purpose", "scope_notes", "approved_by"]


@admin.register(DocumentDomain)
class DocumentDomainAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["name", "code", "sort_order", "is_active", "updated_at"]
    list_filter = ["code", "is_active"]
    ordering = ["sort_order", "name"]
    search_fields = ["name", "description", "code"]


@admin.register(ControlledVocabularyTerm)
class ControlledVocabularyTermAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["term", "term_key", "domain", "status", "is_required", "sort_order", "updated_at"]
    list_filter = ["domain", "status", "is_required"]
    ordering = ["domain__sort_order", "sort_order", "term"]
    search_fields = ["term", "term_key", "definition", "synonyms", "usage_guidance"]


@admin.register(DocumentType)
class DocumentTypeAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["name", "code", "category_code", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name", "code", "description"]


@admin.register(DocumentOwnerRole)
class DocumentOwnerRoleAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["name", "code", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name", "code", "description"]


@admin.register(DocumentWorkflowPhase)
class DocumentWorkflowPhaseAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["name", "code", "numbering_code", "sort_order", "is_active", "created_at"]
    list_filter = ["is_active"]
    ordering = ["sort_order", "name"]
    search_fields = ["name", "code", "description"]


@admin.register(DocumentRetentionPolicy)
class DocumentRetentionPolicyAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["name", "code", "retention_years", "is_indefinite", "is_active", "created_at"]
    list_filter = ["is_indefinite", "is_active"]
    search_fields = ["name", "code", "description"]


@admin.register(Document)
class DocumentAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "document_number",
        "project_code",
        "sequence_number",
        "revision_number",
        "title",
        "document_type",
        "status",
        "contract_value",
        "confidentiality_level",
        "phase",
        "owner_role",
        "created_at",
    ]
    list_filter = ["status", "confidentiality_level", "phase", "document_type", "owner_role"]
    search_fields = ["document_number", "title"]


@admin.register(DocumentVersion)
class DocumentVersionAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "document",
        "version_major",
        "version_minor",
        "approval_status",
        "uploaded_by",
        "uploaded_at",
    ]
    list_filter = ["approval_status"]
    search_fields = ["document__document_number", "document__title", "file_path", "change_summary"]

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(DocumentApproval)
class DocumentApprovalAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["document_version", "decision", "role", "user", "timestamp"]
    list_filter = ["decision", "role"]
    search_fields = ["document_version__document__document_number", "user__username", "comments"]

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(DocumentExpiry)
class DocumentExpiryAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "document",
        "trigger_category",
        "expiry_date",
        "alert_90_days",
        "alert_30_days",
        "alert_expired",
        "alert_90_days_sent_at",
        "alert_30_days_sent_at",
        "expired_alert_sent_at",
        "escalated_at",
    ]
    list_filter = [
        "trigger_category",
        "alert_90_days",
        "alert_30_days",
        "alert_expired",
    ]
    search_fields = ["document__document_number", "document__title"]


@admin.register(DocumentSearchIndex)
class DocumentSearchIndexAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "document",
        "document_version",
        "index_status",
        "indexed_at",
        "updated_at",
    ]
    list_filter = ["index_status"]
    search_fields = ["document__document_number", "document__title", "error_message"]


@admin.register(DocumentComment)
class DocumentCommentAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["document", "document_version", "author", "created_at"]
    search_fields = ["document__document_number", "author__username", "comment"]

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(DocumentAuditEvent)
class DocumentAuditEventAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "created_at",
        "event_type",
        "document_number_snapshot",
        "actor",
        "actor_role_name",
        "ip_address",
    ]
    list_filter = ["event_type", "actor_role_name", "created_at"]
    search_fields = [
        "document_number_snapshot",
        "document_title_snapshot",
        "version_label_snapshot",
        "actor__email",
        "actor__username",
        "actor_role_name",
    ]
    readonly_fields = [field.name for field in DocumentAuditEvent._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(DocumentRoleScope)
class DocumentRoleScopeAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["role", "project_scope", "business_unit_scope", "updated_at"]
    search_fields = ["role__name", "role__slug"]


@admin.register(DocumentProjectMembership)
class DocumentProjectMembershipAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["user", "project", "created_at"]
    search_fields = ["user__username", "user__email", "project__name"]


@admin.register(DocumentBusinessUnitMembership)
class DocumentBusinessUnitMembershipAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["user", "division", "department", "created_at"]
    search_fields = [
        "user__username",
        "user__email",
        "division__name",
        "department__name",
    ]


@admin.register(DocumentWorkflowTemplate)
class DocumentWorkflowTemplateAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["code", "name", "is_default", "is_active", "updated_at"]
    list_filter = ["is_default", "is_active"]
    search_fields = ["code", "name", "description"]


@admin.register(DocumentWorkflowTemplateStep)
class DocumentWorkflowTemplateStepAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["template", "sequence", "approver_label", "approver_role_slug", "is_active"]
    list_filter = ["is_active", "template"]
    search_fields = ["template__name", "approver_label", "approver_role_slug"]


@admin.register(DocumentWorkflowRule)
class DocumentWorkflowRuleAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "name",
        "template",
        "document_type",
        "min_contract_value",
        "max_contract_value",
        "priority",
        "is_active",
    ]
    list_filter = ["is_active", "template", "document_type"]
    search_fields = ["name", "template__name", "document_type__name"]


@admin.register(DocumentWorkflowInstance)
class DocumentWorkflowInstanceAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["document", "template", "state", "submitted_at", "completed_at", "created_at"]
    list_filter = ["state", "template"]
    search_fields = ["document__document_number", "document__title", "template__name"]


@admin.register(DocumentWorkflowStep)
class DocumentWorkflowStepAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "workflow_instance",
        "sequence",
        "approver_label",
        "decision",
        "decided_by",
        "decided_at",
    ]
    list_filter = ["decision", "approver_label"]
    search_fields = ["workflow_instance__document__document_number", "approver_label", "approver_role_slug"]


@admin.register(DocumentSignatureRequest)
class DocumentSignatureRequestAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "document",
        "document_version",
        "provider",
        "status",
        "provider_envelope_id",
        "requested_by",
        "requested_at",
        "sent_at",
        "completed_at",
    ]
    list_filter = ["provider", "status"]
    search_fields = [
        "document__document_number",
        "document__title",
        "provider_envelope_id",
        "requested_by__email",
    ]


@admin.register(DocumentGenerationRecord)
class DocumentGenerationRecordAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "generation_kind",
        "title",
        "document",
        "document_version",
        "template_code",
        "requested_by",
        "created_at",
    ]
    list_filter = ["generation_kind", "template_code"]
    search_fields = ["title", "document__document_number", "template_code", "requested_by__email"]
