from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from .models import (
    ApprovalPolicy,
    UserDelegation,
    WorkflowAuditEvent,
    WorkflowInstance,
    WorkflowStep,
    WorkflowTemplate,
    WorkflowTemplateStep,
)

# ---------------------------------------------------------------------------
# WorkflowTemplate
# ---------------------------------------------------------------------------

class WorkflowTemplateStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowTemplateStep
        fields = [
            "id", "template", "sequence", "name", "step_type",
            "execution_mode", "approver_role_slug", "approver_user",
            "sla_hours", "escalation_role_slug",
            "condition_field", "condition_operator", "condition_value",
            "condition_true_step", "condition_false_step",
            "is_active", "created_at",
        ]
        read_only_fields = ("id", "created_at")


class WorkflowTemplateStepWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowTemplateStep
        fields = [
            "sequence", "name", "step_type", "execution_mode",
            "approver_role_slug", "approver_user",
            "sla_hours", "escalation_role_slug",
            "condition_field", "condition_operator", "condition_value",
            "condition_true_step", "condition_false_step",
            "is_active",
        ]


class WorkflowTemplateListSerializer(serializers.ModelSerializer):
    step_count = serializers.SerializerMethodField()
    applicable_models = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowTemplate
        fields = [
            "id", "code", "name", "description",
            "default_step_mode", "is_default", "is_active",
            "step_count", "applicable_models",
            "created_at", "updated_at",
        ]

    def get_step_count(self, obj):
        return obj.steps.filter(is_active=True).count()

    def get_applicable_models(self, obj):
        return [
            f"{ct.app_label}.{ct.model}"
            for ct in obj.applicable_content_types.all()
        ]


class WorkflowTemplateDetailSerializer(WorkflowTemplateListSerializer):
    steps = WorkflowTemplateStepSerializer(many=True, read_only=True)
    applicable_content_types = serializers.PrimaryKeyRelatedField(
        many=True, read_only=True,
    )

    class Meta(WorkflowTemplateListSerializer.Meta):
        fields = WorkflowTemplateListSerializer.Meta.fields + [
            "steps", "applicable_content_types",
        ]


class WorkflowTemplateWriteSerializer(serializers.ModelSerializer):
    applicable_content_types = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=ContentType.objects.all(),
        required=False,
    )

    class Meta:
        model = WorkflowTemplate
        fields = [
            "code", "name", "description",
            "applicable_content_types", "default_step_mode",
            "is_default", "is_active",
        ]


# ---------------------------------------------------------------------------
# ApprovalPolicy
# ---------------------------------------------------------------------------

class ApprovalPolicyListSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(
        source="template.name", read_only=True,
    )
    content_type_label = serializers.SerializerMethodField()

    class Meta:
        model = ApprovalPolicy
        fields = [
            "id", "name", "policy_type", "content_type",
            "content_type_label", "amount_field",
            "min_amount", "max_amount",
            "template", "template_name", "priority",
            "is_active", "created_at", "updated_at",
        ]

    def get_content_type_label(self, obj):
        return f"{obj.content_type.app_label}.{obj.content_type.model}"


class ApprovalPolicyWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApprovalPolicy
        fields = [
            "name", "policy_type", "content_type",
            "amount_field", "min_amount", "max_amount",
            "template", "priority", "is_active",
        ]


# ---------------------------------------------------------------------------
# UserDelegation
# ---------------------------------------------------------------------------

class UserDelegationListSerializer(serializers.ModelSerializer):
    delegator_name = serializers.SerializerMethodField()
    delegate_name = serializers.SerializerMethodField()
    role_scope_name = serializers.CharField(
        source="role_scope.name", read_only=True, default=None,
    )

    class Meta:
        model = UserDelegation
        fields = [
            "id", "delegator", "delegator_name",
            "delegate", "delegate_name",
            "role_scope", "role_scope_name",
            "content_type_scope",
            "starts_at", "ends_at", "reason", "status",
            "created_at", "revoked_at", "revoked_by",
        ]

    def get_delegator_name(self, obj):
        u = obj.delegator
        return u.get_full_name() or u.username

    def get_delegate_name(self, obj):
        u = obj.delegate
        return u.get_full_name() or u.username


class UserDelegationWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserDelegation
        fields = [
            "delegator", "delegate",
            "role_scope", "content_type_scope",
            "starts_at", "ends_at", "reason",
        ]

    def validate(self, data):
        if data["starts_at"] >= data["ends_at"]:
            raise serializers.ValidationError(
                "ends_at must be after starts_at."
            )
        if data["delegator"] == data["delegate"]:
            raise serializers.ValidationError(
                "A user cannot delegate to themselves."
            )
        return data


# ---------------------------------------------------------------------------
# WorkflowInstance (runtime)
# ---------------------------------------------------------------------------

class WorkflowStepSerializer(serializers.ModelSerializer):
    decided_by_name = serializers.SerializerMethodField()
    on_behalf_of_name = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowStep
        fields = [
            "id", "sequence", "name", "execution_mode",
            "approver_role_slug", "approver_user",
            "decision", "decided_by", "decided_by_name",
            "acting_on_behalf_of", "on_behalf_of_name",
            "comments", "decided_at",
            "sla_deadline", "sla_breached", "escalated_at",
            "created_at", "updated_at",
        ]

    def get_decided_by_name(self, obj):
        if obj.decided_by:
            return obj.decided_by.get_full_name() or obj.decided_by.username
        return None

    def get_on_behalf_of_name(self, obj):
        if obj.acting_on_behalf_of:
            return (
                obj.acting_on_behalf_of.get_full_name()
                or obj.acting_on_behalf_of.username
            )
        return None


class WorkflowInstanceListSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(
        source="template.name", read_only=True,
    )
    submitted_by_name = serializers.SerializerMethodField()
    content_type_label = serializers.SerializerMethodField()
    pending_step = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowInstance
        fields = [
            "id", "content_type", "content_type_label", "object_id",
            "template", "template_name",
            "state", "submitted_by", "submitted_by_name",
            "submitted_at", "completed_at",
            "pending_step",
            "created_at", "updated_at",
        ]

    def get_submitted_by_name(self, obj):
        if obj.submitted_by:
            return obj.submitted_by.get_full_name() or obj.submitted_by.username
        return None

    def get_content_type_label(self, obj):
        return f"{obj.content_type.app_label}.{obj.content_type.model}"

    def get_pending_step(self, obj):
        step = (
            obj.steps
            .filter(decision=WorkflowStep.Decision.PENDING)
            .order_by("sequence")
            .first()
        )
        if step:
            return {"sequence": step.sequence, "name": step.name}
        return None


class WorkflowInstanceDetailSerializer(WorkflowInstanceListSerializer):
    steps = WorkflowStepSerializer(many=True, read_only=True)

    class Meta(WorkflowInstanceListSerializer.Meta):
        fields = WorkflowInstanceListSerializer.Meta.fields + [
            "matched_policy", "steps",
        ]


# ---------------------------------------------------------------------------
# Decision input
# ---------------------------------------------------------------------------

class StepDecisionSerializer(serializers.Serializer):
    step_id = serializers.IntegerField()
    decision = serializers.ChoiceField(choices=["approved", "rejected"])
    comments = serializers.CharField(required=False, allow_blank=True, default="")


# ---------------------------------------------------------------------------
# Audit events
# ---------------------------------------------------------------------------

class WorkflowAuditEventSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowAuditEvent
        fields = [
            "id", "workflow_instance", "event_type",
            "actor", "actor_name", "payload", "created_at",
        ]

    def get_actor_name(self, obj):
        if obj.actor:
            return obj.actor.get_full_name() or obj.actor.username
        return None
