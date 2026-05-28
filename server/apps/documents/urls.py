from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ControlledVocabularyTermViewSet,
    DocumentApprovalViewSet,
    DocumentAuditEventViewSet,
    DocumentBusinessUnitMembershipViewSet,
    DocumentCommentViewSet,
    DocumentDomainViewSet,
    DocumentExpiryViewSet,
    DocumentGenerationGenerateView,
    DocumentGenerationRecordViewSet,
    DocumentGovernanceCharterViewSet,
    DocumentMetadataQueryViewSet,
    DocumentOwnerRoleOptionViewSet,
    DocumentProjectMembershipViewSet,
    DocumentRecordViewSet,
    DocumentRetentionPolicyOptionViewSet,
    DocumentRoleScopeViewSet,
    DocumentSearchIndexRebuildView,
    DocumentSearchIndexViewSet,
    DocumentSearchView,
    DocumentSignatureRequestViewSet,
    DocumentTypeOptionViewSet,
    DocumentVersionViewSet,
    DocumentWorkflowInstanceViewSet,
    DocumentWorkflowPhaseOptionViewSet,
    DocumentWorkflowRuleViewSet,
    DocumentWorkflowTemplateStepViewSet,
    DocumentWorkflowTemplateViewSet,
    PhaseOneGovernanceBlueprintView,
)

charter_router = DefaultRouter()
charter_router.register(r"", DocumentGovernanceCharterViewSet, basename="document-governance-charter")

domain_router = DefaultRouter()
domain_router.register(r"", DocumentDomainViewSet, basename="document-domain")

vocabulary_router = DefaultRouter()
vocabulary_router.register(r"", ControlledVocabularyTermViewSet, basename="controlled-vocabulary-term")

document_type_router = DefaultRouter()
document_type_router.register(r"", DocumentTypeOptionViewSet, basename="document-type-option")

document_owner_role_router = DefaultRouter()
document_owner_role_router.register(r"", DocumentOwnerRoleOptionViewSet, basename="document-owner-role-option")

document_workflow_phase_router = DefaultRouter()
document_workflow_phase_router.register(
    r"",
    DocumentWorkflowPhaseOptionViewSet,
    basename="document-workflow-phase-option",
)

document_retention_policy_router = DefaultRouter()
document_retention_policy_router.register(
    r"",
    DocumentRetentionPolicyOptionViewSet,
    basename="document-retention-policy-option",
)

document_metadata_router = DefaultRouter()
document_metadata_router.register(r"", DocumentMetadataQueryViewSet, basename="document-metadata")

document_record_router = DefaultRouter()
document_record_router.register(r"", DocumentRecordViewSet, basename="document-record")

document_version_router = DefaultRouter()
document_version_router.register(r"", DocumentVersionViewSet, basename="document-version")

document_approval_router = DefaultRouter()
document_approval_router.register(r"", DocumentApprovalViewSet, basename="document-approval")

document_expiry_router = DefaultRouter()
document_expiry_router.register(r"", DocumentExpiryViewSet, basename="document-expiry")

document_comment_router = DefaultRouter()
document_comment_router.register(r"", DocumentCommentViewSet, basename="document-comment")

document_audit_event_router = DefaultRouter()
document_audit_event_router.register(r"", DocumentAuditEventViewSet, basename="document-audit-event")

document_role_scope_router = DefaultRouter()
document_role_scope_router.register(r"", DocumentRoleScopeViewSet, basename="document-role-scope")

document_project_membership_router = DefaultRouter()
document_project_membership_router.register(
    r"",
    DocumentProjectMembershipViewSet,
    basename="document-project-membership",
)

document_business_unit_membership_router = DefaultRouter()
document_business_unit_membership_router.register(
    r"",
    DocumentBusinessUnitMembershipViewSet,
    basename="document-business-unit-membership",
)

workflow_template_router = DefaultRouter()
workflow_template_router.register(r"", DocumentWorkflowTemplateViewSet, basename="document-workflow-template")

workflow_template_step_router = DefaultRouter()
workflow_template_step_router.register(
    r"",
    DocumentWorkflowTemplateStepViewSet,
    basename="document-workflow-template-step",
)

workflow_rule_router = DefaultRouter()
workflow_rule_router.register(r"", DocumentWorkflowRuleViewSet, basename="document-workflow-rule")

workflow_instance_router = DefaultRouter()
workflow_instance_router.register(r"", DocumentWorkflowInstanceViewSet, basename="document-workflow-instance")

search_index_router = DefaultRouter()
search_index_router.register(r"", DocumentSearchIndexViewSet, basename="document-search-index")

signature_request_router = DefaultRouter()
signature_request_router.register(
    r"",
    DocumentSignatureRequestViewSet,
    basename="document-signature-request",
)

generation_record_router = DefaultRouter()
generation_record_router.register(
    r"",
    DocumentGenerationRecordViewSet,
    basename="document-generation-record",
)

urlpatterns = [
    path("phase-1/", PhaseOneGovernanceBlueprintView.as_view(), name="documents-phase-one-blueprint"),
    path("charters/", include(charter_router.urls)),
    path("domains/", include(domain_router.urls)),
    path("vocabulary-terms/", include(vocabulary_router.urls)),
    path("control/lookups/document-types/", include(document_type_router.urls)),
    path("control/lookups/owner-roles/", include(document_owner_role_router.urls)),
    path("control/lookups/workflow-phases/", include(document_workflow_phase_router.urls)),
    path("control/lookups/retention-policies/", include(document_retention_policy_router.urls)),
    path("records/", include(document_metadata_router.urls)),
    path("control/records/", include(document_record_router.urls)),
    path("control/versions/", include(document_version_router.urls)),
    path("control/approvals/", include(document_approval_router.urls)),
    path("control/expiries/", include(document_expiry_router.urls)),
    path("control/comments/", include(document_comment_router.urls)),
    path("control/audit-events/", include(document_audit_event_router.urls)),
    path("control/access/role-scopes/", include(document_role_scope_router.urls)),
    path("control/access/project-memberships/", include(document_project_membership_router.urls)),
    path(
        "control/access/business-unit-memberships/",
        include(document_business_unit_membership_router.urls),
    ),
    path("control/workflow/templates/", include(workflow_template_router.urls)),
    path("control/workflow/template-steps/", include(workflow_template_step_router.urls)),
    path("control/workflow/rules/", include(workflow_rule_router.urls)),
    path("control/workflow/instances/", include(workflow_instance_router.urls)),
    path("search/", DocumentSearchView.as_view(), name="document-search"),
    path("search-index/rebuild/", DocumentSearchIndexRebuildView.as_view(), name="document-search-index-rebuild"),
    path("search-index/", include(search_index_router.urls)),
    path(
        "control/generation/generate/",
        DocumentGenerationGenerateView.as_view(),
        name="document-generation-generate",
    ),
    path("control/signatures/", include(signature_request_router.urls)),
    path("control/generation/", include(generation_record_router.urls)),
]
