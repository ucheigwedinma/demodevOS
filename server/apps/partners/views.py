from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

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
from .serializers import (
    OnboardingTemplateDocumentRequirementSerializer,
    OnboardingTemplateSerializer,
    OnboardingTemplateStageSerializer,
    PartnerEntitlementSerializer,
    PartnerOnboardingApprovalSerializer,
    PartnerOnboardingAuditLogSerializer,
    PartnerOnboardingCaseDetailSerializer,
    PartnerOnboardingCaseListSerializer,
    PartnerOnboardingCaseWriteSerializer,
    PartnerOnboardingIntakeDocumentSerializer,
)
from .services import (
    create_erp_entity,
    evaluate_intake_gate,
    grant_portal_access,
    initialize_case_stages,
    log_audit_event,
    mark_stage_progress,
    provision_entitlement,
    record_approval,
    resolve_default_template,
    sync_stage_kyc_gate_from_intake_documents,
)


def _user_org(request):
    profile = getattr(request.user, "profile", None)
    return getattr(profile, "organization", None)


def _is_superuser(request):
    return request.user.is_superuser


def _is_org_admin(request):
    profile = getattr(request.user, "profile", None)
    return getattr(profile, "role", None) == "admin"


class IsOrgAdminOrSuperuser(BasePermission):
    """Only org admins and superusers can manage onboarding governance resources."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and (_is_superuser(request) or _is_org_admin(request)))


class MarkStageSerializer(serializers.Serializer):
    stage_progress_id = serializers.IntegerField(required=False)
    stage_code = serializers.CharField(required=False, allow_blank=False)
    status = serializers.ChoiceField(choices=PartnerOnboardingStageProgress.Status.choices)
    notes = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        if not attrs.get("stage_progress_id") and not attrs.get("stage_code"):
            raise serializers.ValidationError("Provide stage_progress_id or stage_code.")
        return attrs


class ApprovalDecisionInputSerializer(serializers.Serializer):
    stage_progress_id = serializers.IntegerField(required=False)
    decision = serializers.ChoiceField(choices=PartnerOnboardingApproval.Decision.choices)
    approver_role_label = serializers.CharField(required=False, allow_blank=True, default="")
    comments = serializers.CharField(required=False, allow_blank=True, default="")
    metadata = serializers.JSONField(required=False)


class ProvisionEntitlementInputSerializer(serializers.Serializer):
    portal_role = serializers.ChoiceField(
        choices=PartnerEntitlement._meta.get_field("portal_role").choices,
        required=False,
    )
    project = serializers.IntegerField(required=False)
    spv_entity = serializers.IntegerField(required=False)
    contract_reference = serializers.CharField(required=False, allow_blank=True)
    investment_vehicle_reference = serializers.CharField(required=False, allow_blank=True)


class OnboardingTemplateViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsOrgAdminOrSuperuser]
    serializer_class = OnboardingTemplateSerializer
    search_fields = ["name", "code", "description"]
    filterset_fields = ["partner_type", "is_default", "is_active", "organization"]
    ordering_fields = ["partner_type", "name", "version", "created_at", "updated_at"]
    ordering = ["partner_type", "name"]

    def get_queryset(self):
        queryset = OnboardingTemplate.objects.prefetch_related("stages")
        if _is_superuser(self.request):
            return queryset
        organization = _user_org(self.request)
        if not organization:
            return queryset.filter(organization__isnull=True)
        return queryset.filter(Q(organization=organization) | Q(organization__isnull=True))

    def perform_create(self, serializer):
        organization = _user_org(self.request)
        if not organization and not _is_superuser(self.request):
            raise serializers.ValidationError("Organization context is required.")

        serializer.save(
            organization=organization,
            created_by=self.request.user,
            updated_by=self.request.user,
        )

    def perform_update(self, serializer):
        template = self.get_object()
        if not _is_superuser(self.request):
            organization = _user_org(self.request)
            if template.organization_id != organization.id:
                raise serializers.ValidationError("You can only edit templates owned by your organization.")
        serializer.save(updated_by=self.request.user)


class OnboardingTemplateStageViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsOrgAdminOrSuperuser]
    serializer_class = OnboardingTemplateStageSerializer
    search_fields = ["name", "code", "description", "approval_role_label"]
    filterset_fields = ["template", "is_required", "approval_required", "auto_complete"]
    ordering_fields = ["sequence", "created_at", "updated_at"]
    ordering = ["sequence"]

    def get_queryset(self):
        queryset = OnboardingTemplateStage.objects.select_related("template", "template__organization")
        template_pk = self.kwargs.get("template_pk")
        if template_pk:
            queryset = queryset.filter(template_id=template_pk)

        if _is_superuser(self.request):
            return queryset

        organization = _user_org(self.request)
        if not organization:
            return queryset.filter(template__organization__isnull=True)
        return queryset.filter(
            Q(template__organization=organization) | Q(template__organization__isnull=True)
        )

    def perform_create(self, serializer):
        template_pk = self.kwargs.get("template_pk")
        if template_pk:
            template = get_object_or_404(OnboardingTemplate, pk=template_pk)
        else:
            template = serializer.validated_data["template"]

        if not _is_superuser(self.request):
            organization = _user_org(self.request)
            if not organization or template.organization_id != organization.id:
                raise serializers.ValidationError("Cannot create stages for a template outside your organization.")

        serializer.save(template=template)


class OnboardingTemplateDocumentRequirementViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsOrgAdminOrSuperuser]
    serializer_class = OnboardingTemplateDocumentRequirementSerializer
    search_fields = ["name", "code", "description"]
    filterset_fields = ["template", "is_required", "applies_to_stage"]
    ordering_fields = ["sequence", "created_at", "updated_at", "name"]
    ordering = ["sequence", "id"]

    def get_queryset(self):
        queryset = OnboardingTemplateDocumentRequirement.objects.select_related(
            "template",
            "template__organization",
            "applies_to_stage",
        )
        template_pk = self.kwargs.get("template_pk")
        if template_pk:
            queryset = queryset.filter(template_id=template_pk)

        if _is_superuser(self.request):
            return queryset

        organization = _user_org(self.request)
        if not organization:
            return queryset.filter(template__organization__isnull=True)
        return queryset.filter(
            Q(template__organization=organization) | Q(template__organization__isnull=True)
        )

    def perform_create(self, serializer):
        template_pk = self.kwargs.get("template_pk")
        if template_pk:
            template = get_object_or_404(OnboardingTemplate, pk=template_pk)
        else:
            template = serializer.validated_data["template"]

        if not _is_superuser(self.request):
            organization = _user_org(self.request)
            if not organization or template.organization_id != organization.id:
                raise serializers.ValidationError(
                    "Cannot create document requirements for a template outside your organization."
                )

        serializer.save(template=template)


class PartnerOnboardingIntakeDocumentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsOrgAdminOrSuperuser]
    serializer_class = PartnerOnboardingIntakeDocumentSerializer
    search_fields = [
        "document_name",
        "document_code",
        "external_reference_url",
        "external_reference_number",
        "case__title",
        "requirement__name",
        "requirement__code",
    ]
    filterset_fields = [
        "case",
        "requirement",
        "template_stage",
        "source_channel",
        "status",
        "linked_repository_document",
    ]
    ordering_fields = ["received_at", "created_at", "updated_at", "document_name", "status"]
    ordering = ["-received_at", "-id"]

    def get_queryset(self):
        queryset = PartnerOnboardingIntakeDocument.objects.select_related(
            "case",
            "case__organization",
            "case__template",
            "requirement",
            "template_stage",
            "submitted_by",
            "reviewed_by",
            "linked_repository_document",
        )

        case_pk = self.kwargs.get("case_pk")
        if case_pk:
            queryset = queryset.filter(case_id=case_pk)

        if _is_superuser(self.request):
            return queryset

        organization = _user_org(self.request)
        if not organization:
            return queryset.none()
        return queryset.filter(case__organization=organization)

    def _resolve_case(self, serializer):
        case_pk = self.kwargs.get("case_pk")
        if case_pk:
            return get_object_or_404(PartnerOnboardingCase, pk=case_pk)
        return serializer.validated_data["case"]

    def _enforce_case_scope(self, *, case):
        if _is_superuser(self.request):
            return
        organization = _user_org(self.request)
        if not organization or case.organization_id != organization.id:
            raise serializers.ValidationError("Cannot modify intake documents outside your organization.")

    def _apply_review_metadata(self, *, instance, status_value, actor):
        reviewed_statuses = [
            PartnerOnboardingIntakeDocument.ReviewStatus.APPROVED,
            PartnerOnboardingIntakeDocument.ReviewStatus.REJECTED,
            PartnerOnboardingIntakeDocument.ReviewStatus.WAIVED,
        ]
        if status_value in reviewed_statuses:
            instance.reviewed_by = actor
            instance.reviewed_at = timezone.now()
        elif status_value in [
            PartnerOnboardingIntakeDocument.ReviewStatus.RECEIVED,
            PartnerOnboardingIntakeDocument.ReviewStatus.UNDER_REVIEW,
        ]:
            instance.reviewed_by = None
            instance.reviewed_at = None

    def perform_create(self, serializer):
        case = self._resolve_case(serializer)
        self._enforce_case_scope(case=case)

        requirement = serializer.validated_data.get("requirement")
        if requirement and case.template_id and requirement.template_id != case.template_id:
            raise serializers.ValidationError(
                {"requirement": "Requirement must belong to the selected onboarding case template."}
            )

        template_stage = serializer.validated_data.get("template_stage")
        if template_stage and case.template_id and template_stage.template_id != case.template_id:
            raise serializers.ValidationError(
                {"template_stage": "Template stage must belong to the selected onboarding case template."}
            )

        status_value = serializer.validated_data.get(
            "status",
            PartnerOnboardingIntakeDocument.ReviewStatus.RECEIVED,
        )

        instance = serializer.save(
            case=case,
            submitted_by=self.request.user,
        )
        self._apply_review_metadata(instance=instance, status_value=status_value, actor=self.request.user)
        instance.save(update_fields=["reviewed_by", "reviewed_at", "updated_at"])

        log_audit_event(
            case=case,
            event_type=PartnerOnboardingAuditLog.EventType.STAGE_STATUS_CHANGED,
            message=f"Intake document logged: {instance.document_name} ({instance.status}).",
            actor=self.request.user,
            request=self.request,
            payload={
                "intake_document_id": instance.id,
                "document_code": instance.document_code,
                "status": instance.status,
                "source_channel": instance.source_channel,
            },
        )
        sync_stage_kyc_gate_from_intake_documents(
            case=case,
            actor=self.request.user,
            request=self.request,
        )

    def perform_update(self, serializer):
        instance = self.get_object()
        self._enforce_case_scope(case=instance.case)
        old_status = instance.status
        updated = serializer.save()
        self._apply_review_metadata(instance=updated, status_value=updated.status, actor=self.request.user)
        updated.save(update_fields=["reviewed_by", "reviewed_at", "updated_at"])

        if old_status != updated.status:
            log_audit_event(
                case=updated.case,
                event_type=PartnerOnboardingAuditLog.EventType.STAGE_STATUS_CHANGED,
                message=f"Intake document '{updated.document_name}' status changed from {old_status} to {updated.status}.",
                actor=self.request.user,
                request=self.request,
                payload={
                    "intake_document_id": updated.id,
                    "old_status": old_status,
                    "new_status": updated.status,
                },
            )
        sync_stage_kyc_gate_from_intake_documents(
            case=updated.case,
            actor=self.request.user,
            request=self.request,
        )


class PartnerOnboardingCaseViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsOrgAdminOrSuperuser]
    search_fields = [
        "title",
        "contact_name",
        "contact_email",
        "contract_reference",
        "investment_vehicle_reference",
        "lead__first_name",
        "lead__last_name",
        "vendor__name",
        "investor__name",
    ]
    filterset_fields = [
        "partner_type",
        "status",
        "template",
        "project",
        "spv_entity",
        "portal_access_granted",
        "assigned_owner",
    ]
    ordering_fields = ["created_at", "updated_at", "status", "partner_type", "title"]
    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = (
            PartnerOnboardingCase.objects.select_related(
                "organization",
                "template",
                "lead",
                "vendor",
                "investor",
                "customer",
                "project",
                "spv_entity",
                "current_stage",
                "assigned_owner",
                "created_by",
                "updated_by",
            )
            .prefetch_related(
                "stage_progress__template_stage",
                "approvals",
                "entitlements",
                "audit_events",
                "template__document_requirements__applies_to_stage",
                "intake_documents__requirement",
                "intake_documents__template_stage",
            )
        )
        if _is_superuser(self.request):
            return queryset
        organization = _user_org(self.request)
        if not organization:
            return queryset.none()
        return queryset.filter(organization=organization)

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return PartnerOnboardingCaseWriteSerializer
        if self.action == "list":
            return PartnerOnboardingCaseListSerializer
        return PartnerOnboardingCaseDetailSerializer

    @transaction.atomic
    def perform_create(self, serializer):
        organization = _user_org(self.request)
        if not organization and not _is_superuser(self.request):
            raise serializers.ValidationError("Organization context is required.")

        case = serializer.save(
            organization=organization,
            created_by=self.request.user,
            updated_by=self.request.user,
        )

        if not case.template_id:
            template = resolve_default_template(
                organization=organization,
                partner_type=case.partner_type,
            )
            if template:
                case.template = template
                case.save(update_fields=["template", "updated_at"])

        log_audit_event(
            case=case,
            event_type=PartnerOnboardingAuditLog.EventType.CASE_CREATED,
            message="Partner onboarding case created.",
            actor=self.request.user,
            request=self.request,
            payload={
                "partner_type": case.partner_type,
                "status": case.status,
                "template_id": case.template_id,
            },
        )

        initialize_case_stages(case=case, actor=self.request.user, request=self.request)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(detail=True, methods=["post"], url_path="mark-stage")
    def mark_stage(self, request, pk=None):
        case = self.get_object()
        sync_stage_kyc_gate_from_intake_documents(
            case=case,
            actor=request.user,
            request=request,
        )
        serializer = MarkStageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        stage_progress = None
        if serializer.validated_data.get("stage_progress_id"):
            stage_progress = get_object_or_404(
                PartnerOnboardingStageProgress,
                pk=serializer.validated_data["stage_progress_id"],
                case=case,
            )
        else:
            stage_progress = get_object_or_404(
                PartnerOnboardingStageProgress,
                case=case,
                template_stage__code=serializer.validated_data["stage_code"],
            )

        mark_stage_progress(
            case=case,
            progress=stage_progress,
            status_value=serializer.validated_data["status"],
            notes=serializer.validated_data.get("notes", ""),
            actor=request.user,
            request=request,
        )

        return Response(PartnerOnboardingCaseDetailSerializer(case, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="submit-review")
    def submit_review(self, request, pk=None):
        case = self.get_object()
        sync_stage_kyc_gate_from_intake_documents(
            case=case,
            actor=request.user,
            request=request,
        )
        required_qs = case.stage_progress.filter(is_required=True)
        total_required = required_qs.count()
        completed_required = required_qs.filter(
            status__in=[
                PartnerOnboardingStageProgress.Status.COMPLETED,
                PartnerOnboardingStageProgress.Status.WAIVED,
            ]
        ).count()

        if total_required == 0 or completed_required < total_required:
            return Response(
                {
                    "detail": "All required stages must be completed or waived before review submission.",
                    "required_total": total_required,
                    "required_completed": completed_required,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        intake_gate = evaluate_intake_gate(case=case)
        if not intake_gate.ok:
            return Response(
                {
                    "detail": intake_gate.reason,
                    "required_document_total": intake_gate.required_total,
                    "approved_document_total": intake_gate.approved_total,
                    "missing_required_documents": intake_gate.missing_requirements or [],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_status = case.status
        case.status = PartnerOnboardingCase.Status.UNDER_REVIEW
        case.save(update_fields=["status", "updated_at"])

        log_audit_event(
            case=case,
            event_type=PartnerOnboardingAuditLog.EventType.CASE_STATUS_CHANGED,
            message="Case submitted for review.",
            actor=request.user,
            request=request,
            payload={"old_status": old_status, "new_status": case.status},
        )

        # Notify approvers that case needs review
        from apps.notifications.models import Notification
        from apps.notifications.services import (
            dispatch_workflow_notification,
            resolve_raci_recipients,
        )

        raci = resolve_raci_recipients(
            organization=case.organization,
            process_key="partners.onboarding",
        )
        approver_recipients = raci.decision_makers or raci.all
        if not approver_recipients:
            from apps.accounts.models import UserProfile

            approver_recipients = [
                p.user
                for p in UserProfile.objects.filter(
                    organization=case.organization,
                    role="admin",
                    user__is_active=True,
                ).select_related("user")
            ]
        if approver_recipients:
            case_number = getattr(case, "case_number", str(case.pk))
            dispatch_workflow_notification(
                organization=case.organization,
                event_key="partners_approval_needed",
                recipients=approver_recipients,
                context={
                    "case_number": case_number,
                    "stage_name": "Review",
                    "partner_type": case.partner_type,
                    "action_url": f"/partners/onboarding/{case.id}",
                },
                link_url=f"/partners/onboarding/{case.id}",
                fallback_channels=["in_app", "email"],
                fallback_title=f"Partner review needed: {case_number}",
                fallback_message=(
                    f"Partner onboarding case {case_number} has been submitted for review."
                ),
                fallback_category=Notification.Category.WORKFLOW_PENDING,
                fallback_severity=Notification.Severity.WARNING,
            )

        return Response(PartnerOnboardingCaseDetailSerializer(case, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="record-approval")
    def add_approval(self, request, pk=None):
        case = self.get_object()
        serializer = ApprovalDecisionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        stage_progress = None
        stage_progress_id = serializer.validated_data.get("stage_progress_id")
        if stage_progress_id:
            stage_progress = get_object_or_404(
                PartnerOnboardingStageProgress,
                pk=stage_progress_id,
                case=case,
            )

        approval = record_approval(
            case=case,
            decision=serializer.validated_data["decision"],
            actor=request.user,
            stage_progress=stage_progress,
            approver_role_label=serializer.validated_data.get("approver_role_label", ""),
            comments=serializer.validated_data.get("comments", ""),
            metadata=serializer.validated_data.get("metadata") or {},
            request=request,
        )

        # Notify case creator if case is now approved/active
        case.refresh_from_db()
        if case.status in (
            PartnerOnboardingCase.Status.APPROVED,
            PartnerOnboardingCase.Status.ACTIVE,
        ) and case.created_by_id:
            from apps.notifications.models import Notification
            from apps.notifications.services import dispatch_workflow_notification

            case_number = getattr(case, "case_number", str(case.pk))
            dispatch_workflow_notification(
                organization=case.organization,
                event_key="partners_case_approved",
                recipients=[case.created_by],
                context={
                    "case_number": case_number,
                    "company_name": getattr(case, "company_name", "") or "",
                    "action_url": f"/partners/onboarding/{case.id}",
                },
                link_url=f"/partners/onboarding/{case.id}",
                fallback_channels=["in_app", "email"],
                fallback_title=f"Partner case approved: {case_number}",
                fallback_message=f"Partner onboarding case {case_number} has been approved.",
                fallback_category=Notification.Category.PARTNER_ONBOARDING,
                fallback_severity=Notification.Severity.INFO,
            )

        return Response(
            {
                "approval": PartnerOnboardingApprovalSerializer(approval).data,
                "case": PartnerOnboardingCaseDetailSerializer(case, context={"request": request}).data,
            }
        )

    @action(detail=True, methods=["post"], url_path="provision-entitlement")
    def add_entitlement(self, request, pk=None):
        case = self.get_object()
        serializer = ProvisionEntitlementInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        entitlement = provision_entitlement(
            case=case,
            actor=request.user,
            portal_role=serializer.validated_data.get("portal_role"),
            project_id=serializer.validated_data.get("project"),
            spv_entity_id=serializer.validated_data.get("spv_entity"),
            contract_reference=serializer.validated_data.get("contract_reference"),
            investment_vehicle_reference=serializer.validated_data.get("investment_vehicle_reference"),
            request=request,
        )

        return Response(PartnerEntitlementSerializer(entitlement).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="grant-portal-access")
    def access_grant(self, request, pk=None):
        case = self.get_object()
        result = grant_portal_access(case=case, actor=request.user, request=request)
        if not result.ok:
            return Response({"detail": result.reason}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "detail": result.reason,
                "case": PartnerOnboardingCaseDetailSerializer(case, context={"request": request}).data,
            }
        )

    @action(detail=True, methods=["get"], url_path="timeline")
    def timeline(self, request, pk=None):
        case = self.get_object()
        events = case.audit_events.select_related("actor").order_by("-created_at", "-id")
        return Response(PartnerOnboardingAuditLogSerializer(events, many=True).data)

    @action(detail=True, methods=["get"], url_path="intake-readiness")
    def intake_readiness(self, request, pk=None):
        case = self.get_object()
        gate = evaluate_intake_gate(case=case)
        return Response(
            {
                "ready": gate.ok,
                "detail": gate.reason,
                "required_document_total": gate.required_total,
                "approved_document_total": gate.approved_total,
                "missing_required_documents": gate.missing_requirements or [],
            }
        )

    @action(detail=True, methods=["post"], url_path="create-erp-entity")
    def create_entity(self, request, pk=None):
        case = self.get_object()
        result = create_erp_entity(case=case, actor=request.user, request=request)
        if not result.ok:
            return Response({"detail": result.reason}, status=status.HTTP_400_BAD_REQUEST)

        case.refresh_from_db()
        return Response(
            {
                "detail": result.reason,
                "entity_type": result.entity_type,
                "entity_id": result.entity.id if result.entity else None,
                "case": PartnerOnboardingCaseDetailSerializer(case, context={"request": request}).data,
            },
            status=status.HTTP_201_CREATED,
        )


class PartnerEntitlementViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsOrgAdminOrSuperuser]
    serializer_class = PartnerEntitlementSerializer
    search_fields = [
        "case__title",
        "contract_reference",
        "investment_vehicle_reference",
    ]
    filterset_fields = [
        "case",
        "portal_role",
        "project",
        "spv_entity",
        "budget_scope",
        "is_active",
    ]
    ordering_fields = ["created_at", "updated_at", "effective_from", "expires_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = PartnerEntitlement.objects.select_related(
            "case",
            "organization",
            "project",
            "spv_entity",
            "created_by",
        )
        if _is_superuser(self.request):
            return queryset
        organization = _user_org(self.request)
        if not organization:
            return queryset.none()
        return queryset.filter(organization=organization)

    def perform_create(self, serializer):
        case = serializer.validated_data["case"]
        organization = _user_org(self.request)
        if not _is_superuser(self.request):
            if not organization or case.organization_id != organization.id:
                raise serializers.ValidationError("Cannot create entitlements for a case outside your organization.")

        entitlement = serializer.save(
            organization=case.organization,
            created_by=self.request.user,
        )
        log_audit_event(
            case=case,
            event_type=PartnerOnboardingAuditLog.EventType.ENTITLEMENT_PROVISIONED,
            message="Entitlement created manually.",
            actor=self.request.user,
            request=self.request,
            payload={
                "entitlement_id": entitlement.id,
                "portal_role": entitlement.portal_role,
            },
        )


class PartnerOnboardingAuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated, IsOrgAdminOrSuperuser]
    serializer_class = PartnerOnboardingAuditLogSerializer
    search_fields = ["message", "payload", "actor_role_label"]
    filterset_fields = ["case", "event_type", "actor"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at", "-id"]

    def get_queryset(self):
        queryset = PartnerOnboardingAuditLog.objects.select_related("case", "actor", "case__organization")
        if _is_superuser(self.request):
            return queryset
        organization = _user_org(self.request)
        if not organization:
            return queryset.none()
        return queryset.filter(case__organization=organization)


class PartnerOnboardingOverviewView(APIView):
    permission_classes = [IsAuthenticated, IsOrgAdminOrSuperuser]

    def get(self, request):
        qs = PartnerOnboardingCase.objects.all()
        if not _is_superuser(request):
            organization = _user_org(request)
            if not organization:
                qs = qs.none()
            else:
                qs = qs.filter(organization=organization)

        status_counts = {}
        for s in PartnerOnboardingCase.Status.values:
            status_counts[s] = qs.filter(status=s).count()

        by_partner_type = {}
        for pt in ["client", "contractor", "investor"]:
            by_partner_type[pt] = qs.filter(partner_type=pt).count()

        active_qs = qs.filter(
            status__in=[
                PartnerOnboardingCase.Status.IN_PROGRESS,
                PartnerOnboardingCase.Status.UNDER_REVIEW,
                PartnerOnboardingCase.Status.APPROVED,
                PartnerOnboardingCase.Status.ACTIVE,
            ]
        )
        avg_completion = 0
        if active_qs.exists():
            completions = []
            for case in active_qs.prefetch_related("stage_progress"):
                total = case.stage_progress.filter(is_required=True).count()
                if total > 0:
                    done = case.stage_progress.filter(
                        is_required=True,
                        status__in=[
                            PartnerOnboardingStageProgress.Status.COMPLETED,
                            PartnerOnboardingStageProgress.Status.WAIVED,
                        ],
                    ).count()
                    completions.append(round((done / total) * 100, 2))
            if completions:
                avg_completion = round(sum(completions) / len(completions), 2)

        return Response({
            "total_cases": qs.count(),
            **status_counts,
            "by_partner_type": by_partner_type,
            "portal_access_granted": qs.filter(portal_access_granted=True).count(),
            "avg_completion_percent": avg_completion,
        })
