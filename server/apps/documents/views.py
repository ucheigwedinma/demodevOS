from django.contrib.postgres.search import SearchQuery, SearchRank
from django.core.files.storage import default_storage
from django.db import connection
from django.db.models import Count, F, FloatField, Prefetch, Q, Value
from django.db.utils import IntegrityError
from django.http import FileResponse
from django.utils import timezone
from django.utils.text import slugify
from django_filters import rest_framework as filters
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.mixins import OrgScopedMixin
from apps.settings.models import DocumentAutomationSettings, ensure_default_document_automation_settings
from apps.settings.permissions import HasRolePermission

from .access_control import (
    ensure_can_create_repository_document,
    ensure_document_in_scope,
    ensure_payload_within_scope,
    filter_queryset_by_scoped_documents,
    scoped_document_queryset_for_user,
)
from .audit import (
    document_metadata_snapshot,
    log_document_audit_event,
    metadata_change_payload,
)
from .compliance_monitoring import run_expiry_compliance_monitor
from .generation_service import generate_branded_document
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
from .search_engine import _resolve_file_path, build_search_index_for_document_id, rebuild_search_index
from .serializers import (
    ControlledVocabularyTermSerializer,
    DocumentApprovalSerializer,
    DocumentAuditEventSerializer,
    DocumentBusinessUnitMembershipSerializer,
    DocumentCommentSerializer,
    DocumentDomainDictionarySerializer,
    DocumentDomainSerializer,
    DocumentExpirySerializer,
    DocumentGenerationRecordSerializer,
    DocumentGenerationRequestSerializer,
    DocumentGovernanceCharterSerializer,
    DocumentMetadataSerializer,
    DocumentOwnerRoleOptionSerializer,
    DocumentProjectMembershipSerializer,
    DocumentRetentionPolicyOptionSerializer,
    DocumentRoleScopeSerializer,
    DocumentSearchIndexContentSerializer,
    DocumentSearchIndexSerializer,
    DocumentSearchResultSerializer,
    DocumentShareRequestSerializer,
    DocumentSignatureDecisionSerializer,
    DocumentSignatureRequestSerializer,
    DocumentTypeOptionSerializer,
    DocumentVersionSerializer,
    DocumentWorkflowInstanceSerializer,
    DocumentWorkflowPhaseOptionSerializer,
    DocumentWorkflowRuleSerializer,
    DocumentWorkflowTemplateSerializer,
    DocumentWorkflowTemplateStepSerializer,
    DocumentWorkflowTemplateWriteSerializer,
    DocumentWriteSerializer,
    WorkflowDecisionSerializer,
)
from .signature_providers import (
    get_signature_provider_adapter,
    signature_provider_options,
)
from .workflow_engine import record_workflow_step_decision, submit_document_for_workflow


class DocumentRBACMixin:
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "documents.all"


def _document_automation_settings_for_user(user):
    profile = getattr(user, "profile", None)
    organization = getattr(profile, "organization", None)

    if organization is None and getattr(user, "is_superuser", False):
        from apps.accounts.models import Organization

        organization = Organization.objects.order_by("id").first()

    if organization is None:
        raise ValueError("No organization context found for this user.")

    ensure_default_document_automation_settings(organization)
    settings_obj, _ = DocumentAutomationSettings.objects.get_or_create(organization=organization)
    return settings_obj


def _persist_uploaded_version_file(*, document: Document, uploaded_file) -> str:
    """Store uploaded file under media/documents and return relative path."""
    extension = ""
    if getattr(uploaded_file, "name", None):
        dot_parts = uploaded_file.name.rsplit(".", 1)
        if len(dot_parts) == 2:
            extension = f".{dot_parts[1].lower()}"

    base_name = slugify((getattr(uploaded_file, "name", "") or "document").rsplit(".", 1)[0])[:80]
    if not base_name:
        base_name = "document"

    stamp = timezone.now().strftime("%Y%m%d%H%M%S%f")
    relative_path = f"documents/{document.id}/versions/{stamp}_{base_name}{extension}"
    return default_storage.save(relative_path, uploaded_file)


class DocumentGovernanceCharterViewSet(OrgScopedMixin, DocumentRBACMixin, viewsets.ModelViewSet):
    queryset = DocumentGovernanceCharter.objects.all()
    serializer_class = DocumentGovernanceCharterSerializer
    search_fields = ["title", "version", "purpose", "scope_notes", "approved_by"]
    filterset_fields = [
        "status",
        "repository_scope",
        "external_portal_access",
        "includes_digital_signature_v1",
    ]
    ordering_fields = ["updated_at", "approved_at", "version", "created_at"]
    ordering = ["-updated_at"]
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "admin_override",
        "update": "admin_override",
        "partial_update": "admin_override",
        "destroy": "admin_override",
    }


class DocumentDomainViewSet(OrgScopedMixin, DocumentRBACMixin, viewsets.ModelViewSet):
    queryset = DocumentDomain.objects.all()
    serializer_class = DocumentDomainSerializer
    search_fields = ["name", "description", "code"]
    filterset_fields = ["code", "is_active"]
    ordering_fields = ["sort_order", "name", "updated_at", "created_at"]
    ordering = ["sort_order", "name"]
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "admin_override",
        "update": "admin_override",
        "partial_update": "admin_override",
        "destroy": "admin_override",
    }

    def get_queryset(self):
        return super().get_queryset().annotate(term_count=Count("vocabulary_terms"))


class ControlledVocabularyTermViewSet(OrgScopedMixin, DocumentRBACMixin, viewsets.ModelViewSet):
    queryset = ControlledVocabularyTerm.objects.all()
    serializer_class = ControlledVocabularyTermSerializer
    search_fields = ["term", "term_key", "definition", "synonyms", "usage_guidance"]
    filterset_fields = ["domain", "status", "is_required"]
    ordering_fields = ["domain__sort_order", "sort_order", "term", "updated_at"]
    ordering = ["domain__sort_order", "sort_order", "term"]
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "admin_override",
        "update": "admin_override",
        "partial_update": "admin_override",
        "destroy": "admin_override",
    }

    def get_queryset(self):
        return super().get_queryset().select_related("domain")


class DocumentTypeOptionViewSet(OrgScopedMixin, DocumentRBACMixin, viewsets.ReadOnlyModelViewSet):
    queryset = DocumentType.objects.all()
    serializer_class = DocumentTypeOptionSerializer
    search_fields = ["name", "code", "category_code", "description"]
    filterset_fields = ["is_active", "category_code"]
    ordering_fields = ["name", "category_code", "created_at"]
    ordering = ["name"]
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
    }


class DocumentOwnerRoleOptionViewSet(OrgScopedMixin, DocumentRBACMixin, viewsets.ReadOnlyModelViewSet):
    queryset = DocumentOwnerRole.objects.all()
    serializer_class = DocumentOwnerRoleOptionSerializer
    search_fields = ["name", "code", "description"]
    filterset_fields = ["is_active"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
    }


class DocumentWorkflowPhaseOptionViewSet(OrgScopedMixin, DocumentRBACMixin, viewsets.ReadOnlyModelViewSet):
    queryset = DocumentWorkflowPhase.objects.all()
    serializer_class = DocumentWorkflowPhaseOptionSerializer
    search_fields = ["name", "code", "numbering_code", "description"]
    filterset_fields = ["is_active"]
    ordering_fields = ["sort_order", "name", "created_at"]
    ordering = ["sort_order", "name"]
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
    }


class DocumentRetentionPolicyOptionViewSet(OrgScopedMixin, DocumentRBACMixin, viewsets.ReadOnlyModelViewSet):
    queryset = DocumentRetentionPolicy.objects.all()
    serializer_class = DocumentRetentionPolicyOptionSerializer
    search_fields = ["name", "code", "description"]
    filterset_fields = ["is_active", "is_indefinite"]
    ordering_fields = ["name", "retention_years", "created_at"]
    ordering = ["name"]
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
    }


class DocumentMetadataFilter(filters.FilterSet):
    project = filters.NumberFilter(field_name="project_id")
    land = filters.NumberFilter(field_name="land_id")
    unit = filters.NumberFilter(field_name="unit_id")
    vendor = filters.NumberFilter(field_name="vendor_id")
    client = filters.NumberFilter(field_name="client_id")
    business_unit_division = filters.NumberFilter(field_name="business_unit_division_id")
    business_unit_department = filters.NumberFilter(field_name="business_unit_department_id")
    contract_value_min = filters.NumberFilter(field_name="contract_value", lookup_expr="gte")
    contract_value_max = filters.NumberFilter(field_name="contract_value", lookup_expr="lte")
    project_risk_rating = filters.CharFilter(field_name="project__risk_rating", lookup_expr="iexact")
    category = filters.CharFilter(field_name="document_type__category_code", lookup_expr="iexact")
    status = filters.CharFilter(field_name="status", lookup_expr="iexact")
    created_from = filters.DateFilter(method="filter_created_from")
    created_to = filters.DateFilter(method="filter_created_to")

    class Meta:
        model = Document
        fields = [
            "project",
            "land",
            "unit",
            "vendor",
            "client",
            "business_unit_division",
            "business_unit_department",
            "contract_value_min",
            "contract_value_max",
            "project_risk_rating",
            "category",
            "status",
            "created_from",
            "created_to",
        ]

    def filter_created_from(self, queryset, name, value):
        return queryset.filter(created_at__date__gte=value)

    def filter_created_to(self, queryset, name, value):
        return queryset.filter(created_at__date__lte=value)


class DocumentMetadataQueryViewSet(OrgScopedMixin, DocumentRBACMixin, viewsets.ReadOnlyModelViewSet):
    """Metadata Query Layer with structured filtering."""

    queryset = Document.objects.all()
    serializer_class = DocumentMetadataSerializer
    filterset_class = DocumentMetadataFilter
    search_fields = ["document_number", "title", "project_code"]
    ordering_fields = ["created_at", "document_number", "status", "sequence_number", "revision_number"]
    ordering = ["-created_at"]
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
    }

    def get_queryset(self):
        base_queryset = (
            Document.objects
            .select_related(
                "project",
                "land",
                "unit",
                "vendor",
                "client",
                "document_type",
                "phase",
                "search_index",
                "business_unit_division",
                "business_unit_department",
            )
        )
        return scoped_document_queryset_for_user(self.request.user, queryset=base_queryset)


class DocumentRecordViewSet(OrgScopedMixin, DocumentRBACMixin, viewsets.ModelViewSet):
    """Document master CRUD with RBAC action mapping and scope enforcement."""

    queryset = Document.objects.all()
    filterset_class = DocumentMetadataFilter
    search_fields = ["document_number", "title", "project_code"]
    ordering_fields = ["created_at", "document_number", "status", "sequence_number", "revision_number"]
    ordering = ["-created_at"]
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "upload_version",
        "update": "upload_version",
        "partial_update": "upload_version",
        "destroy": "admin_override",
        "archive": "archive",
        "supersede": "archive",
        "comment": "comment",
        "upload_version": "upload_version",
        "approve_version": "approve",
        "submit_workflow": "upload_version",
        "download": "view",
        "share": "view",
    }

    def get_queryset(self):
        base_queryset = (
            Document.objects
            .select_related(
                "project",
                "land",
                "unit",
                "vendor",
                "client",
                "document_type",
                "phase",
                "current_version",
                "retention_policy",
                "business_unit_division",
                "business_unit_department",
            )
        )
        return scoped_document_queryset_for_user(self.request.user, queryset=base_queryset)

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return DocumentMetadataSerializer
        return DocumentWriteSerializer

    def _payload_scope_fields(self, serializer):
        instance = serializer.instance
        data = serializer.validated_data

        project = data.get("project", getattr(instance, "project", None))
        division = data.get(
            "business_unit_division",
            getattr(instance, "business_unit_division", None),
        )
        department = data.get(
            "business_unit_department",
            getattr(instance, "business_unit_department", None),
        )
        confidentiality_level = data.get(
            "confidentiality_level",
            getattr(instance, "confidentiality_level", None),
        )
        if confidentiality_level is None:
            confidentiality_level = Document.ConfidentialityLevel.INTERNAL

        return {
            "project_id": project.id if project else None,
            "business_unit_division_id": division.id if division else None,
            "business_unit_department_id": department.id if department else None,
            "confidentiality_level": confidentiality_level,
        }

    def perform_create(self, serializer):
        ensure_can_create_repository_document(self.request.user)
        scope_values = self._payload_scope_fields(serializer)
        ensure_payload_within_scope(self.request.user, **scope_values)
        org = self._resolve_request_org()
        if org is None:
            raise PermissionDenied("Could not determine your organization.")
        document = serializer.save(organization=org)
        log_document_audit_event(
            event_type=DocumentAuditEvent.EventType.DOCUMENT_CREATED,
            request=self.request,
            document=document,
            payload={
                "summary": f"Created document {document.document_number}.",
                "status": document.status,
            },
        )

    def perform_update(self, serializer):
        before = document_metadata_snapshot(serializer.instance)
        scope_values = self._payload_scope_fields(serializer)
        ensure_payload_within_scope(self.request.user, **scope_values)
        document = serializer.save()
        after = document_metadata_snapshot(document)
        changed = metadata_change_payload(before, after)
        if changed:
            log_document_audit_event(
                event_type=DocumentAuditEvent.EventType.METADATA_CHANGED,
                request=self.request,
                document=document,
                payload={
                    "summary": "Updated document metadata.",
                    "changed_fields": changed,
                },
            )

    def perform_destroy(self, instance):
        log_document_audit_event(
            event_type=DocumentAuditEvent.EventType.DOCUMENT_DELETED,
            request=self.request,
            document=instance,
            document_version=instance.current_version,
            payload={
                "summary": f"Deleted document {instance.document_number}.",
                "status": instance.status,
            },
        )
        instance.delete()

    @action(detail=True, methods=["post"], url_path="archive")
    def archive(self, request, pk=None):
        document = self.get_object()
        document.status = Document.Status.ARCHIVED
        document.save(update_fields=["status"])

        active_instances = document.workflow_instances.filter(
            state__in=[
                DocumentWorkflowInstance.State.SUBMITTED,
                DocumentWorkflowInstance.State.UNDER_REVIEW,
            ]
        )
        active_instances.update(state=DocumentWorkflowInstance.State.ARCHIVED)

        log_document_audit_event(
            event_type=DocumentAuditEvent.EventType.DOCUMENT_ARCHIVED,
            request=request,
            document=document,
            document_version=document.current_version,
            payload={"summary": f"Archived document {document.document_number}."},
        )

        serializer = DocumentMetadataSerializer(document, context={"request": request})
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="supersede")
    def supersede(self, request, pk=None):
        document = self.get_object()
        document.status = Document.Status.SUPERSEDED
        document.save(update_fields=["status"])

        active_instances = document.workflow_instances.filter(
            state__in=[
                DocumentWorkflowInstance.State.SUBMITTED,
                DocumentWorkflowInstance.State.UNDER_REVIEW,
            ]
        )
        active_instances.update(state=DocumentWorkflowInstance.State.SUPERSEDED)

        log_document_audit_event(
            event_type=DocumentAuditEvent.EventType.DOCUMENT_SUPERSEDED,
            request=request,
            document=document,
            document_version=document.current_version,
            payload={"summary": f"Marked document {document.document_number} as superseded."},
        )

        serializer = DocumentMetadataSerializer(document, context={"request": request})
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="submit-workflow")
    def submit_workflow(self, request, pk=None):
        document = self.get_object()
        try:
            instance = submit_document_for_workflow(document)
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        log_document_audit_event(
            event_type=DocumentAuditEvent.EventType.WORKFLOW_SUBMITTED,
            request=request,
            document=document,
            document_version=document.current_version,
            payload={
                "summary": f"Submitted document to workflow template '{instance.template.name}'.",
                "workflow_instance_id": instance.id,
                "template": instance.template.name,
            },
        )

        return Response(
            DocumentWorkflowInstanceSerializer(instance, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="comments")
    def comment(self, request, pk=None):
        document = self.get_object()
        payload = request.data.copy()
        payload["document"] = document.id
        serializer = DocumentCommentSerializer(data=payload)
        serializer.is_valid(raise_exception=True)

        document_version = serializer.validated_data.get("document_version")
        if document_version and document_version.document_id != document.id:
            return Response(
                {"detail": "document_version does not belong to this document."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        comment = serializer.save(
            document=document,
            author=request.user,
            organization=document.organization,
        )
        log_document_audit_event(
            event_type=DocumentAuditEvent.EventType.COMMENT_ADDED,
            request=request,
            document=document,
            document_version=document_version,
            payload={
                "summary": "Added document comment.",
                "comment_id": comment.id,
                "comment": comment.comment,
            },
        )
        return Response(
            DocumentCommentSerializer(comment, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="upload-version")
    def upload_version(self, request, pk=None):
        document = self.get_object()
        payload = request.data.copy()
        payload["document"] = document.id
        uploaded_file = request.FILES.get("file")
        if uploaded_file is not None:
            payload["file_path"] = _persist_uploaded_version_file(
                document=document,
                uploaded_file=uploaded_file,
            )
        serializer = DocumentVersionSerializer(data=payload)
        serializer.is_valid(raise_exception=True)

        version = serializer.save(
            document=document,
            uploaded_by=request.user,
            organization=document.organization,
        )
        log_document_audit_event(
            event_type=DocumentAuditEvent.EventType.VERSION_UPLOADED,
            request=request,
            document=document,
            document_version=version,
            payload={
                "summary": f"Uploaded version v{version.version_major}.{version.version_minor}.",
                "change_summary": version.change_summary,
                "file_path": version.file_path,
            },
        )
        return Response(
            DocumentVersionSerializer(version, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="approve-version")
    def approve_version(self, request, pk=None):
        document = self.get_object()

        try:
            document_version_id = int(request.data.get("document_version"))
        except (TypeError, ValueError):
            return Response(
                {"detail": "document_version is required and must be an integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        version = document.versions.filter(pk=document_version_id).first()
        if not version:
            return Response(
                {"detail": "Version not found for this document."},
                status=status.HTTP_404_NOT_FOUND,
            )

        decision = (request.data.get("decision") or "").strip().lower()
        if decision not in {DocumentApproval.Decision.APPROVED, DocumentApproval.Decision.REJECTED}:
            return Response(
                {"detail": "decision must be 'approved' or 'rejected'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        role_id = request.data.get("role")
        role = document.owner_role
        if role_id is not None:
            role = DocumentOwnerRole.objects.filter(pk=role_id).first()
            if role is None:
                return Response(
                    {"detail": "Invalid role."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            approval = DocumentApproval.objects.create(
                document_version=version,
                user=request.user,
                role=role,
                decision=decision,
                comments=request.data.get("comments", ""),
                organization=document.organization,
            )
        except IntegrityError:
            return Response(
                {"detail": "You have already submitted an approval decision for this document version."},
                status=status.HTTP_409_CONFLICT,
            )

        version.approval_status = (
            DocumentVersion.ApprovalStatus.APPROVED
            if decision == DocumentApproval.Decision.APPROVED
            else DocumentVersion.ApprovalStatus.REJECTED
        )
        version.save(update_fields=["approval_status"])

        log_document_audit_event(
            event_type=DocumentAuditEvent.EventType.APPROVAL_DECISION,
            request=request,
            document=document,
            document_version=version,
            payload={
                "summary": f"{role.name} marked {decision}.",
                "decision": decision,
                "role": role.name,
                "comments": approval.comments,
            },
        )

        return Response(
            DocumentApprovalSerializer(approval, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk=None):
        document = self.get_object()
        version_id = request.query_params.get("version_id")

        if version_id:
            try:
                parsed_version_id = int(version_id)
            except ValueError:
                return Response({"detail": "version_id must be an integer."}, status=400)
            version = document.versions.filter(id=parsed_version_id).first()
        else:
            version = document.current_version or document.versions.order_by(
                "-version_major",
                "-version_minor",
                "-uploaded_at",
            ).first()

        if version is None:
            return Response({"detail": "No document version is available for download."}, status=404)

        resolved_path = _resolve_file_path(version.file_path)
        if resolved_path is None:
            return Response({"detail": "File not found on server."}, status=404)

        log_document_audit_event(
            event_type=DocumentAuditEvent.EventType.DOCUMENT_DOWNLOADED,
            request=request,
            document=document,
            document_version=version,
            payload={
                "summary": f"Downloaded version v{version.version_major}.{version.version_minor}.",
                "file_name": resolved_path.name,
            },
        )

        return FileResponse(
            resolved_path.open("rb"),
            as_attachment=True,
            filename=resolved_path.name,
        )

    @action(detail=True, methods=["post"], url_path="share")
    def share(self, request, pk=None):
        document = self.get_object()
        serializer = DocumentShareRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        log_document_audit_event(
            event_type=DocumentAuditEvent.EventType.DOCUMENT_SHARED,
            request=request,
            document=document,
            document_version=document.current_version,
            payload={
                "summary": f"Shared document via {payload.get('channel', 'email')}.",
                "channel": payload.get("channel"),
                "recipient": payload.get("recipient"),
                "recipient_name": payload.get("recipient_name", ""),
                "expires_at": payload.get("expires_at").isoformat() if payload.get("expires_at") else None,
                "allow_download": payload.get("allow_download", True),
                "message": payload.get("message", ""),
            },
        )

        return Response(
            {"detail": "Share event recorded.", "shared_document": document.document_number},
            status=status.HTTP_200_OK,
        )


class DocumentVersionViewSet(
    OrgScopedMixin,
    DocumentRBACMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = DocumentVersion.objects.all()
    serializer_class = DocumentVersionSerializer
    filterset_fields = ["document", "approval_status", "uploaded_by"]
    search_fields = ["document__document_number", "document__title", "file_path", "change_summary"]
    ordering_fields = ["uploaded_at", "version_major", "version_minor"]
    ordering = ["-uploaded_at"]
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "upload_version",
    }

    def get_queryset(self):
        base_queryset = DocumentVersion.objects.select_related("document", "uploaded_by")
        return filter_queryset_by_scoped_documents(
            self.request.user,
            queryset=base_queryset,
            document_lookup="document",
        )

    def perform_create(self, serializer):
        document = serializer.validated_data["document"]
        ensure_document_in_scope(self.request.user, document)
        version = serializer.save(uploaded_by=self.request.user, organization=self._resolve_request_org())
        log_document_audit_event(
            event_type=DocumentAuditEvent.EventType.VERSION_UPLOADED,
            request=self.request,
            document=document,
            document_version=version,
            payload={
                "summary": f"Uploaded version v{version.version_major}.{version.version_minor}.",
                "change_summary": version.change_summary,
                "file_path": version.file_path,
            },
        )


class DocumentApprovalViewSet(
    OrgScopedMixin,
    DocumentRBACMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = DocumentApproval.objects.all()
    serializer_class = DocumentApprovalSerializer
    filterset_fields = ["document_version", "role", "user", "decision"]
    search_fields = [
        "document_version__document__document_number",
        "document_version__document__title",
        "comments",
    ]
    ordering_fields = ["timestamp"]
    ordering = ["-timestamp"]
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "approve",
    }

    def get_queryset(self):
        base_queryset = DocumentApproval.objects.select_related("document_version", "role", "user")
        return filter_queryset_by_scoped_documents(
            self.request.user,
            queryset=base_queryset,
            document_lookup="document_version__document",
        )

    def perform_create(self, serializer):
        version = serializer.validated_data["document_version"]
        ensure_document_in_scope(self.request.user, version.document)
        role = serializer.validated_data.get("role", version.document.owner_role)

        try:
            approval = serializer.save(
                user=self.request.user,
                role=role,
                organization=self._resolve_request_org(),
            )
        except IntegrityError as exc:
            raise ValidationError(
                {"detail": "You have already submitted an approval decision for this document version."}
            ) from exc

        decision = serializer.validated_data.get("decision")
        version.approval_status = (
            DocumentVersion.ApprovalStatus.APPROVED
            if decision == DocumentApproval.Decision.APPROVED
            else DocumentVersion.ApprovalStatus.REJECTED
        )
        version.save(update_fields=["approval_status"])
        log_document_audit_event(
            event_type=DocumentAuditEvent.EventType.APPROVAL_DECISION,
            request=self.request,
            document=version.document,
            document_version=version,
            payload={
                "summary": f"{role.name} marked {decision}.",
                "decision": decision,
                "role": role.name,
                "comments": approval.comments,
            },
        )


class DocumentExpiryViewSet(OrgScopedMixin, DocumentRBACMixin, viewsets.ModelViewSet):
    queryset = DocumentExpiry.objects.all()
    serializer_class = DocumentExpirySerializer
    filterset_fields = [
        "document",
        "trigger_category",
        "expiry_date",
        "alert_90_days",
        "alert_30_days",
        "alert_expired",
    ]
    search_fields = ["document__document_number", "document__title"]
    ordering_fields = ["expiry_date", "last_checked_at", "escalated_at"]
    ordering = ["expiry_date"]
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "archive",
        "update": "archive",
        "partial_update": "archive",
        "destroy": "admin_override",
        "run_monitor": "admin_override",
    }

    def get_queryset(self):
        base_queryset = DocumentExpiry.objects.select_related("document")
        return filter_queryset_by_scoped_documents(
            self.request.user,
            queryset=base_queryset,
            document_lookup="document",
        )

    def perform_create(self, serializer):
        document = serializer.validated_data["document"]
        ensure_document_in_scope(self.request.user, document)
        serializer.save(organization=self._resolve_request_org())

    def perform_update(self, serializer):
        document = serializer.validated_data.get("document", serializer.instance.document)
        ensure_document_in_scope(self.request.user, document)
        serializer.save()

    @action(detail=False, methods=["post"], url_path="run-compliance-monitor")
    def run_monitor(self, request):
        summary = run_expiry_compliance_monitor()
        return Response(summary, status=status.HTTP_200_OK)


class DocumentCommentViewSet(
    OrgScopedMixin,
    DocumentRBACMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = DocumentComment.objects.all()
    serializer_class = DocumentCommentSerializer
    filterset_fields = ["document", "document_version", "author"]
    search_fields = ["document__document_number", "document__title", "comment"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "comment",
    }

    def get_queryset(self):
        base_queryset = DocumentComment.objects.select_related("document", "document_version", "author")
        return filter_queryset_by_scoped_documents(
            self.request.user,
            queryset=base_queryset,
            document_lookup="document",
        )

    def perform_create(self, serializer):
        document = serializer.validated_data["document"]
        ensure_document_in_scope(self.request.user, document)

        document_version = serializer.validated_data.get("document_version")
        if document_version and document_version.document_id != document.id:
            raise ValidationError("document_version does not belong to selected document")

        comment = serializer.save(author=self.request.user, organization=self._resolve_request_org())
        log_document_audit_event(
            event_type=DocumentAuditEvent.EventType.COMMENT_ADDED,
            request=self.request,
            document=document,
            document_version=document_version,
            payload={
                "summary": "Added document comment.",
                "comment_id": comment.id,
                "comment": comment.comment,
            },
        )


class DocumentAuditEventViewSet(OrgScopedMixin, DocumentRBACMixin, viewsets.ReadOnlyModelViewSet):
    queryset = DocumentAuditEvent.objects.all()
    serializer_class = DocumentAuditEventSerializer
    filterset_fields = ["document", "document_version", "event_type", "actor", "actor_role"]
    search_fields = [
        "document_number_snapshot",
        "document_title_snapshot",
        "version_label_snapshot",
        "actor__email",
        "actor__first_name",
        "actor__last_name",
        "actor_role_name",
    ]
    ordering_fields = ["created_at", "event_type"]
    ordering = ["-created_at", "-id"]
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
    }

    def get_queryset(self):
        base_queryset = DocumentAuditEvent.objects.select_related(
            "document",
            "document_version",
            "actor",
            "actor_role",
        )
        document_ids = scoped_document_queryset_for_user(self.request.user).values("id")
        return base_queryset.filter(document_id__in=document_ids)


class DocumentSignatureRequestViewSet(OrgScopedMixin, DocumentRBACMixin, viewsets.ModelViewSet):
    queryset = DocumentSignatureRequest.objects.all()
    serializer_class = DocumentSignatureRequestSerializer
    filterset_fields = ["document", "document_version", "provider", "status", "requested_by"]
    search_fields = ["document__document_number", "document__title", "provider_envelope_id", "subject", "message"]
    ordering_fields = ["requested_at", "sent_at", "completed_at", "updated_at"]
    ordering = ["-requested_at", "-id"]
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "upload_version",
        "update": "upload_version",
        "partial_update": "upload_version",
        "destroy": "admin_override",
        "providers": "view",
        "send_request": "upload_version",
        "complete_request": "approve",
        "cancel_request": "approve",
    }

    def get_queryset(self):
        base_queryset = DocumentSignatureRequest.objects.select_related(
            "document",
            "document_version",
            "requested_by",
        )
        return filter_queryset_by_scoped_documents(
            self.request.user,
            queryset=base_queryset,
            document_lookup="document",
        )

    def perform_create(self, serializer):
        document = serializer.validated_data["document"]
        ensure_document_in_scope(self.request.user, document)
        automation_settings = _document_automation_settings_for_user(self.request.user)
        version = serializer.validated_data.get("document_version")
        if version is None:
            version = document.current_version or document.versions.order_by(
                "-version_major",
                "-version_minor",
                "-uploaded_at",
            ).first()
        enabled_providers = set(automation_settings.enabled_signature_providers or [])
        provider = automation_settings.default_signature_provider
        if provider not in enabled_providers:
            provider = next(iter(enabled_providers), DocumentSignatureRequest.Provider.DOCUSIGN)
        signature_request = serializer.save(
            provider=provider,
            document_version=version,
            requested_by=self.request.user,
            organization=self._resolve_request_org(),
        )
        log_document_audit_event(
            event_type=DocumentAuditEvent.EventType.METADATA_CHANGED,
            request=self.request,
            document=document,
            document_version=signature_request.document_version,
            payload={
                "summary": (
                    f"Created {signature_request.get_provider_display()} signature request "
                    f"({signature_request.get_status_display().lower()})."
                ),
                "signature_request_id": signature_request.id,
                "provider": signature_request.provider,
                "status": signature_request.status,
            },
        )

    @action(detail=False, methods=["get"], url_path="providers")
    def providers(self, request):
        automation_settings = _document_automation_settings_for_user(request.user)
        configured = [
            option
            for option in signature_provider_options()
            if option["key"] in set(automation_settings.enabled_signature_providers or [])
        ]
        if not configured:
            configured = signature_provider_options()
        default_provider = automation_settings.default_signature_provider
        provider_keys = {row["key"] for row in configured}
        if default_provider not in provider_keys:
            default_provider = configured[0]["key"]
        return Response(
            {
                "providers": configured,
                "default_provider": default_provider,
            }
        )

    @action(detail=True, methods=["post"], url_path="send")
    def send_request(self, request, pk=None):
        signature_request = self.get_object()
        if signature_request.status not in {
            DocumentSignatureRequest.Status.DRAFT,
            DocumentSignatureRequest.Status.FAILED,
        }:
            return Response(
                {"detail": "Only draft or failed requests can be sent."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        adapter = get_signature_provider_adapter(signature_request.provider)
        dispatch = adapter.send(signature_request=signature_request)
        signature_request.provider_envelope_id = dispatch.envelope_id
        signature_request.signing_url = dispatch.signing_url
        signature_request.provider_payload = dispatch.payload
        signature_request.status = DocumentSignatureRequest.Status.SENT
        signature_request.sent_at = timezone.now()
        signature_request.cancelled_at = None
        signature_request.save(
            update_fields=[
                "provider_envelope_id",
                "signing_url",
                "provider_payload",
                "status",
                "sent_at",
                "cancelled_at",
                "updated_at",
            ]
        )
        log_document_audit_event(
            event_type=DocumentAuditEvent.EventType.SIGNATURE_REQUEST_SENT,
            request=request,
            document=signature_request.document,
            document_version=signature_request.document_version,
            payload={
                "summary": (
                    f"Sent signature request via {signature_request.get_provider_display()} "
                    f"({signature_request.provider_envelope_id})."
                ),
                "signature_request_id": signature_request.id,
                "provider": signature_request.provider,
                "provider_envelope_id": signature_request.provider_envelope_id,
                "signing_url": signature_request.signing_url,
            },
        )
        return Response(DocumentSignatureRequestSerializer(signature_request, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="complete")
    def complete_request(self, request, pk=None):
        signature_request = self.get_object()
        decision_serializer = DocumentSignatureDecisionSerializer(data=request.data)
        decision_serializer.is_valid(raise_exception=True)

        if signature_request.status not in {
            DocumentSignatureRequest.Status.SENT,
            DocumentSignatureRequest.Status.DECLINED,
        }:
            return Response(
                {"detail": "Only sent or declined requests can be completed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        signed_file = decision_serializer.validated_data.get("signed_file") or request.FILES.get("signed_file")
        new_version = None
        if signed_file is not None:
            document = signature_request.document
            saved_path = _persist_uploaded_version_file(
                document=document,
                uploaded_file=signed_file,
            )
            latest_version = document.versions.order_by(
                "-version_major",
                "-version_minor",
                "-uploaded_at",
            ).first()
            if latest_version:
                major = latest_version.version_major
                minor = latest_version.version_minor + 1
            else:
                major = 1
                minor = 0
            new_version = DocumentVersion.objects.create(
                document=document,
                organization=document.organization,
                version_major=major,
                version_minor=minor,
                file_path=saved_path,
                change_summary=(
                    f"Signed copy uploaded via {signature_request.get_provider_display()}"
                    + (
                        f" - {decision_serializer.validated_data.get('comments', '').strip()}"
                        if decision_serializer.validated_data.get("comments")
                        else "."
                    )
                ),
                uploaded_by=request.user,
                approval_status=DocumentVersion.ApprovalStatus.APPROVED,
            )

        signature_request.status = DocumentSignatureRequest.Status.COMPLETED
        signature_request.completed_at = timezone.now()
        if new_version is not None:
            signature_request.document_version = new_version
        signature_request.save(update_fields=["status", "completed_at", "document_version", "updated_at"])

        log_document_audit_event(
            event_type=DocumentAuditEvent.EventType.SIGNATURE_COMPLETED,
            request=request,
            document=signature_request.document,
            document_version=signature_request.document_version,
            payload={
                "summary": f"Completed signature request via {signature_request.get_provider_display()}.",
                "signature_request_id": signature_request.id,
                "provider": signature_request.provider,
                "has_uploaded_signed_copy": bool(new_version),
                "comments": decision_serializer.validated_data.get("comments", ""),
            },
        )
        return Response(DocumentSignatureRequestSerializer(signature_request, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel_request(self, request, pk=None):
        signature_request = self.get_object()
        if signature_request.status in {
            DocumentSignatureRequest.Status.COMPLETED,
            DocumentSignatureRequest.Status.CANCELLED,
        }:
            return Response(
                {"detail": "Completed or cancelled requests cannot be cancelled again."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        signature_request.status = DocumentSignatureRequest.Status.CANCELLED
        signature_request.cancelled_at = timezone.now()
        signature_request.save(update_fields=["status", "cancelled_at", "updated_at"])
        log_document_audit_event(
            event_type=DocumentAuditEvent.EventType.SIGNATURE_CANCELLED,
            request=request,
            document=signature_request.document,
            document_version=signature_request.document_version,
            payload={
                "summary": f"Cancelled signature request via {signature_request.get_provider_display()}.",
                "signature_request_id": signature_request.id,
                "provider": signature_request.provider,
            },
        )
        return Response(DocumentSignatureRequestSerializer(signature_request, context={"request": request}).data)


class DocumentRoleScopeViewSet(OrgScopedMixin, DocumentRBACMixin, viewsets.ModelViewSet):
    queryset = DocumentRoleScope.objects.all()
    serializer_class = DocumentRoleScopeSerializer
    filterset_fields = ["project_scope", "business_unit_scope", "role"]
    search_fields = ["role__name", "role__slug"]
    ordering_fields = ["updated_at", "created_at"]
    ordering = ["role__name"]
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "admin_override",
        "update": "admin_override",
        "partial_update": "admin_override",
        "destroy": "admin_override",
    }

    def get_queryset(self):
        queryset = DocumentRoleScope.objects.select_related("role")
        if self.request.user.is_superuser:
            return queryset

        profile = getattr(self.request.user, "profile", None)
        org = getattr(profile, "organization", None)
        if not org:
            return queryset.none()
        return queryset.filter(role__organization=org)

    def _validate_role_org(self, role):
        if self.request.user.is_superuser:
            return
        profile = getattr(self.request.user, "profile", None)
        org = getattr(profile, "organization", None)
        if not org or role.organization_id != org.id:
            raise ValidationError("Role must belong to your organization.")

    def perform_create(self, serializer):
        role = serializer.validated_data["role"]
        self._validate_role_org(role)
        serializer.save(organization=self._resolve_request_org())

    def perform_update(self, serializer):
        role = serializer.validated_data.get("role", serializer.instance.role)
        self._validate_role_org(role)
        serializer.save()


class DocumentProjectMembershipViewSet(OrgScopedMixin, DocumentRBACMixin, viewsets.ModelViewSet):
    queryset = DocumentProjectMembership.objects.all()
    serializer_class = DocumentProjectMembershipSerializer
    filterset_fields = ["user", "project"]
    search_fields = ["user__email", "user__first_name", "user__last_name", "project__name"]
    ordering_fields = ["created_at", "project__name"]
    ordering = ["project__name", "user__email"]
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "admin_override",
        "update": "admin_override",
        "partial_update": "admin_override",
        "destroy": "admin_override",
    }

    def get_queryset(self):
        queryset = DocumentProjectMembership.objects.select_related("user", "project")
        if self.request.user.is_superuser:
            return queryset

        profile = getattr(self.request.user, "profile", None)
        org = getattr(profile, "organization", None)
        if not org:
            return queryset.none()

        return queryset.filter(user__profile__organization=org)

    def _validate_membership_org(self, user):
        if self.request.user.is_superuser:
            return
        profile = getattr(self.request.user, "profile", None)
        org = getattr(profile, "organization", None)
        user_org_id = getattr(getattr(user, "profile", None), "organization_id", None)
        if not org or user_org_id != org.id:
            raise ValidationError("Membership user must belong to your organization.")

    def perform_create(self, serializer):
        self._validate_membership_org(serializer.validated_data["user"])
        serializer.save(organization=self._resolve_request_org())

    def perform_update(self, serializer):
        user = serializer.validated_data.get("user", serializer.instance.user)
        self._validate_membership_org(user)
        serializer.save()


class DocumentBusinessUnitMembershipViewSet(OrgScopedMixin, DocumentRBACMixin, viewsets.ModelViewSet):
    queryset = DocumentBusinessUnitMembership.objects.all()
    serializer_class = DocumentBusinessUnitMembershipSerializer
    filterset_fields = ["user", "division", "department"]
    search_fields = [
        "user__email",
        "user__first_name",
        "user__last_name",
        "division__name",
        "department__name",
    ]
    ordering_fields = ["created_at", "user__email", "division__name", "department__name"]
    ordering = ["user__email", "division__name", "department__name"]
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "admin_override",
        "update": "admin_override",
        "partial_update": "admin_override",
        "destroy": "admin_override",
    }

    def get_queryset(self):
        queryset = DocumentBusinessUnitMembership.objects.select_related(
            "user",
            "division",
            "department",
            "department__division",
        )
        if self.request.user.is_superuser:
            return queryset

        profile = getattr(self.request.user, "profile", None)
        org = getattr(profile, "organization", None)
        if not org:
            return queryset.none()

        return queryset.filter(user__profile__organization=org)

    def _validate_membership_org(self, user, division=None, department=None):
        if self.request.user.is_superuser:
            return

        profile = getattr(self.request.user, "profile", None)
        org = getattr(profile, "organization", None)
        user_org_id = getattr(getattr(user, "profile", None), "organization_id", None)
        if not org or user_org_id != org.id:
            raise ValidationError("Membership user must belong to your organization.")

        if division and division.organization_id != org.id:
            raise ValidationError("Division must belong to your organization.")

        if department and department.division.organization_id != org.id:
            raise ValidationError("Department must belong to your organization.")

    def perform_create(self, serializer):
        data = serializer.validated_data
        self._validate_membership_org(
            user=data["user"],
            division=data.get("division"),
            department=data.get("department"),
        )
        serializer.save(organization=self._resolve_request_org())

    def perform_update(self, serializer):
        user = serializer.validated_data.get("user", serializer.instance.user)
        division = serializer.validated_data.get("division", serializer.instance.division)
        department = serializer.validated_data.get("department", serializer.instance.department)
        self._validate_membership_org(
            user=user,
            division=division,
            department=department,
        )
        serializer.save()


class DocumentWorkflowTemplateViewSet(OrgScopedMixin, DocumentRBACMixin, viewsets.ModelViewSet):
    """Approval Template Builder endpoints."""

    queryset = DocumentWorkflowTemplate.objects.all()
    search_fields = ["code", "name", "description"]
    filterset_fields = ["is_default", "is_active"]
    ordering_fields = ["name", "code", "updated_at", "created_at"]
    ordering = ["name"]
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "admin_override",
        "update": "admin_override",
        "partial_update": "admin_override",
        "destroy": "admin_override",
    }

    def get_queryset(self):
        return super().get_queryset().prefetch_related("steps")

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return DocumentWorkflowTemplateSerializer
        return DocumentWorkflowTemplateWriteSerializer

    def _normalize_default_flag(self, serializer):
        if serializer.validated_data.get("is_default", False):
            DocumentWorkflowTemplate.objects.exclude(
                pk=getattr(serializer.instance, "pk", None)
            ).update(is_default=False)

    def perform_create(self, serializer):
        self._normalize_default_flag(serializer)
        serializer.save(organization=self._resolve_request_org())

    def perform_update(self, serializer):
        self._normalize_default_flag(serializer)
        serializer.save()


class DocumentWorkflowTemplateStepViewSet(OrgScopedMixin, DocumentRBACMixin, viewsets.ModelViewSet):
    queryset = DocumentWorkflowTemplateStep.objects.all()
    search_fields = ["template__name", "approver_label", "approver_role_slug"]
    filterset_fields = ["template", "is_active"]
    ordering_fields = ["template__name", "sequence", "created_at"]
    ordering = ["template__name", "sequence"]
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "admin_override",
        "update": "admin_override",
        "partial_update": "admin_override",
        "destroy": "admin_override",
    }
    serializer_class = DocumentWorkflowTemplateStepSerializer

    def get_queryset(self):
        return super().get_queryset().select_related("template")


class DocumentWorkflowRuleViewSet(OrgScopedMixin, DocumentRBACMixin, viewsets.ModelViewSet):
    queryset = DocumentWorkflowRule.objects.all()
    search_fields = ["name", "template__name", "document_type__name"]
    filterset_fields = ["template", "document_type", "is_active", "priority"]
    ordering_fields = ["priority", "name", "updated_at", "created_at"]
    ordering = ["priority", "name"]
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "admin_override",
        "update": "admin_override",
        "partial_update": "admin_override",
        "destroy": "admin_override",
    }
    serializer_class = DocumentWorkflowRuleSerializer

    def get_queryset(self):
        return super().get_queryset().select_related("template", "document_type")


class DocumentWorkflowInstanceViewSet(OrgScopedMixin, DocumentRBACMixin, viewsets.ReadOnlyModelViewSet):
    """Workflow Configuration Engine runtime endpoints."""

    queryset = DocumentWorkflowInstance.objects.all()
    serializer_class = DocumentWorkflowInstanceSerializer
    filterset_fields = ["document", "template", "matched_rule", "state"]
    search_fields = ["document__document_number", "document__title", "template__name"]
    ordering_fields = ["created_at", "submitted_at", "completed_at", "state"]
    ordering = ["-created_at"]
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
        "submit": "upload_version",
        "decide": "approve",
    }

    def get_queryset(self):
        base_queryset = (
            DocumentWorkflowInstance.objects
            .select_related("document", "template", "matched_rule")
            .prefetch_related("steps")
        )
        document_ids = scoped_document_queryset_for_user(self.request.user).values("id")
        return base_queryset.filter(document_id__in=document_ids)

    @action(detail=True, methods=["post"], url_path="submit")
    def submit(self, request, pk=None):
        instance = self.get_object()
        try:
            updated = submit_document_for_workflow(instance.document)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        log_document_audit_event(
            event_type=DocumentAuditEvent.EventType.WORKFLOW_SUBMITTED,
            request=request,
            document=updated.document,
            document_version=updated.document.current_version,
            payload={
                "summary": f"Submitted document to workflow template '{updated.template.name}'.",
                "workflow_instance_id": updated.id,
                "template": updated.template.name,
            },
        )
        return Response(DocumentWorkflowInstanceSerializer(updated, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="decide")
    def decide(self, request, pk=None):
        instance = self.get_object()
        decision_payload = WorkflowDecisionSerializer(data=request.data)
        decision_payload.is_valid(raise_exception=True)

        step = instance.steps.filter(id=decision_payload.validated_data["step_id"]).first()
        if not step:
            return Response({"detail": "Step not found for this workflow instance."}, status=404)
        if step.decision != DocumentWorkflowStep.Decision.PENDING:
            return Response({"detail": "Step has already been decided."}, status=400)

        current_pending = (
            instance.steps
            .filter(decision=DocumentWorkflowStep.Decision.PENDING)
            .order_by("sequence", "id")
            .first()
        )
        if not current_pending or current_pending.id != step.id:
            return Response(
                {"detail": "Only the current pending step can be decided."},
                status=400,
            )

        if step.approver_role_slug:
            if not request.user.is_superuser:
                profile = getattr(request.user, "profile", None)
                assigned_role = getattr(profile, "assigned_role", None)
                if not assigned_role or assigned_role.slug != step.approver_role_slug:
                    return Response(
                        {"detail": f"Decision requires role '{step.approver_role_slug}'."},
                        status=403,
                    )

        try:
            record_workflow_step_decision(
                instance=instance,
                step=step,
                decision=decision_payload.validated_data["decision"],
                decided_by=request.user,
                comments=decision_payload.validated_data.get("comments", ""),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)

        log_document_audit_event(
            event_type=DocumentAuditEvent.EventType.WORKFLOW_STEP_DECISION,
            request=request,
            document=instance.document,
            document_version=instance.document.current_version,
            payload={
                "summary": f"{step.approver_label} marked {step.decision}.",
                "workflow_instance_id": instance.id,
                "step_id": step.id,
                "step_sequence": step.sequence,
                "approver_label": step.approver_label,
                "approver_role_slug": step.approver_role_slug,
                "decision": step.decision,
                "comments": step.comments,
            },
        )
        log_document_audit_event(
            event_type=DocumentAuditEvent.EventType.APPROVAL_DECISION,
            request=request,
            document=instance.document,
            document_version=instance.document.current_version,
            payload={
                "summary": f"{step.approver_label} marked {step.decision}.",
                "decision": step.decision,
                "role": step.approver_label,
                "comments": step.comments,
            },
        )

        instance.refresh_from_db()
        return Response(DocumentWorkflowInstanceSerializer(instance, context={"request": request}).data)


class DocumentSearchView(DocumentRBACMixin, APIView):
    """Search Index Engine endpoint for full-text and clause retrieval."""

    rbac_action = "view"

    def get(self, request):
        base_qs = (
            Document.objects
            .select_related(
                "project",
                "land",
                "unit",
                "vendor",
                "client",
                "document_type",
                "phase",
                "search_index",
                "business_unit_division",
                "business_unit_department",
            )
            .filter(search_index__isnull=False)
        )
        base_qs = scoped_document_queryset_for_user(request.user, queryset=base_qs)

        metadata_filters = DocumentMetadataFilter(request.query_params, queryset=base_qs)
        if not metadata_filters.is_valid():
            return Response(metadata_filters.errors, status=400)

        queryset = metadata_filters.qs
        query_text = (request.query_params.get("q") or "").strip()
        clause_query = (request.query_params.get("clause") or "").strip()

        if query_text:
            if connection.vendor == "postgresql":
                search_query = SearchQuery(query_text, search_type="websearch")
                queryset = (
                    queryset.annotate(
                        search_rank=SearchRank(F("search_index__search_vector"), search_query),
                    )
                    .filter(
                        Q(search_rank__gt=0)
                        | Q(document_number__icontains=query_text)
                        | Q(title__icontains=query_text)
                        | Q(search_index__combined_text__icontains=query_text)
                    )
                    .order_by("-search_rank", "-created_at")
                )
            else:
                queryset = (
                    queryset.annotate(search_rank=Value(0.0, output_field=FloatField()))
                    .filter(
                        Q(document_number__icontains=query_text)
                        | Q(title__icontains=query_text)
                        | Q(search_index__combined_text__icontains=query_text)
                    )
                    .order_by("-created_at")
                )
        else:
            queryset = queryset.annotate(search_rank=Value(0.0, output_field=FloatField()))

        if clause_query:
            queryset = queryset.filter(search_index__clause_text__icontains=clause_query)

        paginator = PageNumberPagination()
        paginator.page_size_query_param = "page_size"
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = DocumentSearchResultSerializer(
            page,
            many=True,
            context={
                "query_text": query_text,
                "clause_query": clause_query,
            },
        )
        return paginator.get_paginated_response(serializer.data)


class DocumentSearchIndexViewSet(OrgScopedMixin, DocumentRBACMixin, viewsets.ReadOnlyModelViewSet):
    queryset = DocumentSearchIndex.objects.all()
    serializer_class = DocumentSearchIndexSerializer
    filterset_fields = ["index_status", "document", "document_version"]
    search_fields = ["document__document_number", "document__title", "error_message"]
    ordering_fields = ["indexed_at", "updated_at"]
    ordering = ["-indexed_at", "-updated_at"]
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
    }

    def get_queryset(self):
        base_queryset = DocumentSearchIndex.objects.select_related("document", "document_version")
        return filter_queryset_by_scoped_documents(
            self.request.user,
            queryset=base_queryset,
            document_lookup="document",
        )

    @action(detail=True, methods=["get"], url_path="content")
    def content(self, request, pk=None):
        index = self.get_object()
        serializer = DocumentSearchIndexContentSerializer(index, context={"request": request})
        return Response(serializer.data)


class DocumentSearchIndexRebuildView(DocumentRBACMixin, APIView):
    """Trigger full or single-document indexing."""

    rbac_action = "admin_override"

    def post(self, request):
        document_id = request.data.get("document_id")
        force = str(request.data.get("force", "true")).lower() in ("1", "true", "yes")

        organization = getattr(request, "organization", None)
        if organization is None:
            # Fallback: resolve from JWT-authenticated user when middleware
            # ran before DRF auth (session expired but JWT still valid).
            profile = getattr(request.user, "profile", None)
            organization = getattr(profile, "organization", None)
        if organization is None:
            return Response(
                {"detail": "Organization context required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if document_id:
            try:
                parsed_id = int(document_id)
            except ValueError:
                return Response({"detail": "document_id must be an integer."}, status=400)

            try:
                document = Document.objects.get(id=parsed_id, organization=organization)
            except Document.DoesNotExist:
                return Response({"detail": "Document not found."}, status=404)

            ensure_document_in_scope(request.user, document)
            index = build_search_index_for_document_id(document_id=parsed_id, force=force)
            return Response({
                "processed": 1,
                "indexed": 1 if index.index_status == DocumentSearchIndex.IndexStatus.INDEXED else 0,
                "failed": 1 if index.index_status == DocumentSearchIndex.IndexStatus.FAILED else 0,
                "document_id": parsed_id,
                "index_status": index.index_status,
                "error_message": index.error_message,
            })

        if not request.user.is_superuser:
            profile = getattr(request.user, "profile", None)
            if not profile or profile.role != "admin":
                return Response(
                    {"detail": "Full index rebuild is restricted to organization admins."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        summary = rebuild_search_index(organization_id=organization.id, force=force)
        return Response(summary)


class DocumentGenerationRecordViewSet(OrgScopedMixin, DocumentRBACMixin, viewsets.ReadOnlyModelViewSet):
    queryset = DocumentGenerationRecord.objects.all()
    serializer_class = DocumentGenerationRecordSerializer
    filterset_fields = ["generation_kind", "document", "document_version", "requested_by"]
    search_fields = ["title", "document__document_number", "document__title", "template_code"]
    ordering_fields = ["created_at", "generation_kind", "title"]
    ordering = ["-created_at", "-id"]
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
    }

    def get_queryset(self):
        base_queryset = DocumentGenerationRecord.objects.select_related(
            "document",
            "document_version",
            "requested_by",
        )
        return filter_queryset_by_scoped_documents(
            self.request.user,
            queryset=base_queryset,
            document_lookup="document",
        )


class DocumentGenerationGenerateView(DocumentRBACMixin, APIView):
    rbac_action = "upload_version"

    def post(self, request):
        ensure_can_create_repository_document(request.user)
        try:
            automation_settings = _document_automation_settings_for_user(request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if (
            automation_settings.default_generation_owner_role_id is None
            or automation_settings.default_generation_phase_id is None
            or automation_settings.default_generation_retention_policy_id is None
        ):
            return Response(
                {
                    "detail": (
                        "Document automation defaults are incomplete. "
                        "Configure owner role, phase, and retention policy in Settings."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = DocumentGenerationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        payload = {
            **payload,
            "owner_role": automation_settings.default_generation_owner_role,
            "phase": automation_settings.default_generation_phase,
            "retention_policy": automation_settings.default_generation_retention_policy,
            "confidentiality_level": automation_settings.default_generation_confidentiality_level,
            "template_code": (
                payload.get("template_code")
                or automation_settings.default_generation_template_code
                or ""
            ),
        }

        scope_values = {
            "project_id": payload.get("project").id if payload.get("project") else None,
            "business_unit_division_id": (
                payload.get("business_unit_division").id if payload.get("business_unit_division") else None
            ),
            "business_unit_department_id": (
                payload.get("business_unit_department").id if payload.get("business_unit_department") else None
            ),
            "confidentiality_level": payload["confidentiality_level"],
        }
        ensure_payload_within_scope(request.user, **scope_values)

        try:
            result = generate_branded_document(
                request=request,
                user=request.user,
                validated_data=payload,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        log_document_audit_event(
            event_type=DocumentAuditEvent.EventType.DOCUMENT_GENERATED,
            request=request,
            document=result.document,
            document_version=result.version,
            payload={
                "summary": (
                    f"Generated branded {result.generation_record.generation_kind} document "
                    f"via template '{result.generation_record.template_code or 'default'}'."
                ),
                "generation_record_id": result.generation_record.id,
                "generation_kind": result.generation_record.generation_kind,
                "template_code": result.generation_record.template_code,
            },
        )
        return Response(
            {
                "generation_record": DocumentGenerationRecordSerializer(
                    result.generation_record,
                    context={"request": request},
                ).data,
                "document": DocumentMetadataSerializer(result.document, context={"request": request}).data,
                "version": DocumentVersionSerializer(result.version, context={"request": request}).data,
            },
            status=status.HTTP_201_CREATED,
        )


class PhaseOneGovernanceBlueprintView(DocumentRBACMixin, APIView):
    """Consolidated Phase 1 governance payload for document control bootstrap."""

    rbac_action = "view"

    def get(self, request):
        charter = (
            DocumentGovernanceCharter.objects
            .order_by("-approved_at", "-updated_at", "-id")
            .first()
        )
        domains = (
            DocumentDomain.objects.filter(is_active=True)
            .order_by("sort_order", "name")
            .prefetch_related(
                Prefetch(
                    "vocabulary_terms",
                    queryset=ControlledVocabularyTerm.objects.filter(
                        status=ControlledVocabularyTerm.Status.ACTIVE
                    ).order_by("sort_order", "term"),
                )
            )
        )
        return Response({
            "phase": "phase_1_governance_blueprint_scope_definition",
            "charter": DocumentGovernanceCharterSerializer(charter).data if charter else None,
            "document_domains": DocumentDomainDictionarySerializer(domains, many=True).data,
        })
