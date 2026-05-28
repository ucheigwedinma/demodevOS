from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.settings.permissions import HasRolePermission

from .engine import cancel_workflow, record_step_decision
from .models import (
    ApprovalPolicy,
    UserDelegation,
    WorkflowAuditEvent,
    WorkflowInstance,
    WorkflowStep,
    WorkflowTemplate,
    WorkflowTemplateStep,
)
from .process_authority import user_has_process_authority_for_step
from .serializers import (
    ApprovalPolicyListSerializer,
    ApprovalPolicyWriteSerializer,
    StepDecisionSerializer,
    UserDelegationListSerializer,
    UserDelegationWriteSerializer,
    WorkflowAuditEventSerializer,
    WorkflowInstanceDetailSerializer,
    WorkflowInstanceListSerializer,
    WorkflowTemplateDetailSerializer,
    WorkflowTemplateListSerializer,
    WorkflowTemplateStepSerializer,
    WorkflowTemplateStepWriteSerializer,
    WorkflowTemplateWriteSerializer,
)


def _user_org(request):
    profile = getattr(request.user, "profile", None)
    return getattr(profile, "organization", None)


def _is_superuser(request):
    return bool(getattr(request.user, "is_superuser", False))


def _requested_org_id(request):
    raw = request.query_params.get("organization_id") or request.query_params.get("org_id")
    if raw in (None, ""):
        return None
    try:
        value = int(str(raw))
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _scope_queryset_for_request(request, queryset, *, org_field: str = "organization"):
    if _is_superuser(request):
        requested_org_id = _requested_org_id(request)
        if requested_org_id:
            org_id_field = org_field if org_field.endswith("_id") else f"{org_field}_id"
            return queryset.filter(**{org_id_field: requested_org_id})
        return queryset

    organization = _user_org(request)
    if organization is None:
        return queryset.none()
    return queryset.filter(**{org_field: organization})


# ---------------------------------------------------------------------------
# Configuration ViewSets
# ---------------------------------------------------------------------------

class WorkflowTemplateViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.workflow_templates"
    search_fields = ["name", "code"]
    filterset_fields = ["is_active", "is_default"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def get_queryset(self):
        return _scope_queryset_for_request(
            self.request,
            WorkflowTemplate.objects.all(),
            org_field="organization",
        ).prefetch_related("steps", "applicable_content_types")

    def get_serializer_class(self):
        if self.action == "list":
            return WorkflowTemplateListSerializer
        if self.action in ("create", "update", "partial_update"):
            return WorkflowTemplateWriteSerializer
        return WorkflowTemplateDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


class WorkflowTemplateStepViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.workflow_templates"
    ordering = ["sequence"]

    def get_queryset(self):
        return _scope_queryset_for_request(
            self.request,
            WorkflowTemplateStep.objects.filter(template_id=self.kwargs["template_pk"]),
            org_field="template__organization",
        )

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return WorkflowTemplateStepWriteSerializer
        return WorkflowTemplateStepSerializer

    def perform_create(self, serializer):
        serializer.save(template_id=self.kwargs["template_pk"])


class ApprovalPolicyViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.approval_policies"
    search_fields = ["name"]
    filterset_fields = ["is_active", "policy_type"]
    ordering_fields = ["priority", "name", "created_at"]
    ordering = ["priority", "name"]

    def get_queryset(self):
        return _scope_queryset_for_request(
            self.request,
            ApprovalPolicy.objects.all(),
            org_field="organization",
        ).select_related("template", "content_type")

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return ApprovalPolicyWriteSerializer
        return ApprovalPolicyListSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


class UserDelegationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.delegations"
    http_method_names = ["get", "post", "patch", "head", "options"]
    filterset_fields = ["status"]
    ordering = ["-starts_at"]

    def get_queryset(self):
        return _scope_queryset_for_request(
            self.request,
            UserDelegation.objects.all(),
            org_field="organization",
        ).select_related("delegator", "delegate", "role_scope")

    def get_serializer_class(self):
        if self.action in ("create", "partial_update"):
            return UserDelegationWriteSerializer
        return UserDelegationListSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))

    @action(detail=True, methods=["post"], url_path="revoke")
    def revoke(self, request, pk=None):
        delegation = self.get_object()
        if delegation.status != UserDelegation.Status.ACTIVE:
            return Response(
                {"detail": "Only active delegations can be revoked."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from django.utils import timezone
        delegation.status = UserDelegation.Status.REVOKED
        delegation.revoked_at = timezone.now()
        delegation.revoked_by = request.user
        delegation.save(update_fields=["status", "revoked_at", "revoked_by"])

        WorkflowAuditEvent.objects.create(
            event_type=WorkflowAuditEvent.EventType.DELEGATION_REVOKED,
            actor=request.user,
            payload={
                "delegation_id": delegation.pk,
                "delegator": delegation.delegator_id,
                "delegate": delegation.delegate_id,
            },
        )

        return Response(
            UserDelegationListSerializer(delegation).data,
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# Runtime ViewSets
# ---------------------------------------------------------------------------

class WorkflowInstanceViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.workflow_templates"
    rbac_action = "view"
    filterset_fields = ["state", "content_type", "object_id"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = (
            _scope_queryset_for_request(
                self.request,
                WorkflowInstance.objects.all(),
                org_field="template__organization",
            )
            .select_related("template", "submitted_by", "content_type")
            .prefetch_related("steps")
        )
        # Support ?model=finance.bill style filtering
        model_label = self.request.query_params.get("model")
        if model_label:
            try:
                app_label, model_name = model_label.split(".")
                ct = ContentType.objects.get(app_label=app_label, model=model_name)
                qs = qs.filter(content_type=ct)
            except (ValueError, ContentType.DoesNotExist):
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == "retrieve":
            return WorkflowInstanceDetailSerializer
        # Use detail serializer when filtering to a specific object
        # (module detail pages need steps data)
        if self.request.query_params.get("object_id"):
            return WorkflowInstanceDetailSerializer
        return WorkflowInstanceListSerializer

    @action(detail=True, methods=["post"], url_path="decide")
    def decide(self, request, pk=None):
        instance = self.get_object()
        serializer = StepDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            step = instance.steps.get(id=serializer.validated_data["step_id"])
        except WorkflowStep.DoesNotExist:
            return Response(
                {"detail": "Step not found on this workflow."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            record_step_decision(
                step=step,
                decision=serializer.validated_data["decision"],
                user=request.user,
                comments=serializer.validated_data.get("comments", ""),
                request=request,
            )
        except (ValueError, PermissionError) as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        instance.refresh_from_db()
        return Response(
            WorkflowInstanceDetailSerializer(instance).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        instance = self.get_object()
        try:
            cancel_workflow(instance, request.user)
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance.refresh_from_db()
        return Response(
            WorkflowInstanceDetailSerializer(instance).data,
            status=status.HTTP_200_OK,
        )


class MyApprovalsView(APIView):
    """Pending approval steps assigned to the current user (or via delegation)."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.approval_policies"
    rbac_action = "view"

    def get(self, request):
        user = request.user
        profile = getattr(user, "profile", None)
        role_slug = ""
        organization = None
        requested_org_id = _requested_org_id(request) if _is_superuser(request) else None
        if profile and profile.assigned_role:
            role_slug = profile.assigned_role.slug
        if profile:
            organization = profile.organization
        if not _is_superuser(request) and organization is None:
            return Response([])

        pending = WorkflowStep.objects.filter(
            decision=WorkflowStep.Decision.PENDING,
            workflow_instance__state__in=[
                WorkflowInstance.State.PENDING,
                WorkflowInstance.State.IN_PROGRESS,
            ],
        )
        if requested_org_id:
            pending = pending.filter(workflow_instance__template__organization_id=requested_org_id)
        elif not _is_superuser(request):
            pending = pending.filter(workflow_instance__template__organization=organization)

        pending = pending.select_related(
            "workflow_instance__template",
            "workflow_instance__content_type",
            "approver_user",
        )

        from django.db.models import Q
        user_or_role = Q(approver_user=user)
        if role_slug:
            user_or_role |= Q(approver_role_slug=role_slug, approver_user__isnull=True)
        delegations = UserDelegation.objects.filter(
            delegate=user,
            status=UserDelegation.Status.ACTIVE,
            starts_at__lte=timezone.now(),
            ends_at__gte=timezone.now(),
        )
        if requested_org_id:
            delegations = delegations.filter(organization_id=requested_org_id)
        elif not _is_superuser(request):
            delegations = delegations.filter(organization=organization)

        delegated_from_ids = list(delegations.values_list("delegator_id", flat=True))
        if delegated_from_ids:
            user_or_role |= Q(approver_user_id__in=delegated_from_ids)

        explicit_step_ids = set(
            pending.filter(user_or_role).values_list("id", flat=True)
        )

        steps = []
        for pending_step in pending.order_by("sla_deadline", "created_at"):
            if pending_step.id in explicit_step_ids:
                steps.append(pending_step)
                continue
            if user_has_process_authority_for_step(pending_step, user):
                steps.append(pending_step)

        results = []
        for step in steps:
            inst = step.workflow_instance
            results.append({
                "step_id": step.pk,
                "step_name": step.name,
                "step_sequence": step.sequence,
                "workflow_instance_id": inst.pk,
                "template_name": inst.template.name,
                "content_type": f"{inst.content_type.app_label}.{inst.content_type.model}",
                "object_id": inst.object_id,
                "state": inst.state,
                "sla_deadline": step.sla_deadline,
                "sla_breached": step.sla_breached,
                "submitted_at": inst.submitted_at,
            })

        return Response(results)


class WorkflowAuditEventViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.audit_compliance"
    rbac_action = "view"
    serializer_class = WorkflowAuditEventSerializer
    filterset_fields = ["event_type", "workflow_instance"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return _scope_queryset_for_request(
            self.request,
            WorkflowAuditEvent.objects.all(),
            org_field="workflow_instance__template__organization",
        ).select_related("actor")


# ---------------------------------------------------------------------------
# Content-type list helper (for frontend dropdowns)
# ---------------------------------------------------------------------------

class ApplicableContentTypesView(APIView):
    """Return content types that can have workflows attached."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.workflow_templates"
    rbac_action = "view"

    WORKFLOW_MODELS = [
        ("finance", "bill"),
        ("finance", "invoice"),
        ("finance", "budget"),
        ("procurement", "purchaseorder"),
        ("procurement", "purchaserequisition"),
        ("procurement", "requestforquotation"),
        ("documents", "document"),
    ]

    def get(self, request):
        results = []
        for app_label, model in self.WORKFLOW_MODELS:
            try:
                ct = ContentType.objects.get(app_label=app_label, model=model)
                results.append({
                    "id": ct.pk,
                    "app_label": ct.app_label,
                    "model": ct.model,
                    "label": f"{ct.app_label}.{ct.model}",
                })
            except ContentType.DoesNotExist:
                pass
        return Response(results)
