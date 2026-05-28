from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from apps.admin_mixins import OrgScopedAdminMixin

from .models import (
    ApprovalPolicy,
    Approver,
    ProcessAuthority,
    ProcessWorkflowStep,
    UserDelegation,
    WorkflowAuditEvent,
    WorkflowInstance,
    WorkflowRole,
    WorkflowStep,
    WorkflowTemplate,
    WorkflowTemplateStep,
)


class WorkflowTemplateStepInline(TabularInline):
    model = WorkflowTemplateStep
    extra = 0
    fields = (
        "sequence", "name", "step_type", "execution_mode",
        "approver_role_slug", "approver_user", "sla_hours", "is_active",
    )
    ordering = ("sequence",)


@admin.register(WorkflowTemplate)
class WorkflowTemplateAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("name", "code", "organization", "default_step_mode", "is_default", "is_active", "created_at")
    list_filter = ("is_active", "is_default", "default_step_mode", "organization")
    search_fields = ("name", "code")
    inlines = [WorkflowTemplateStepInline]


@admin.register(ApprovalPolicy)
class ApprovalPolicyAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("name", "organization", "policy_type", "content_type", "min_amount", "max_amount", "template", "priority", "is_active")
    list_filter = ("is_active", "policy_type", "organization")
    search_fields = ("name",)


class WorkflowStepInline(TabularInline):
    model = WorkflowStep
    extra = 0
    fields = (
        "sequence", "name", "execution_mode", "approver_role_slug",
        "decision", "decided_by", "decided_at", "sla_breached",
    )
    readonly_fields = ("decided_by", "decided_at")
    ordering = ("sequence",)


@admin.register(WorkflowInstance)
class WorkflowInstanceAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("__str__", "state", "submitted_by", "submitted_at", "completed_at", "created_at")
    list_filter = ("state",)
    search_fields = ("template__name",)
    readonly_fields = ("content_type", "object_id", "template", "submitted_by", "submitted_at", "completed_at", "created_at", "updated_at")
    inlines = [WorkflowStepInline]


@admin.register(WorkflowRole)
class WorkflowRoleAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("name", "code", "organization", "responsibility", "is_active", "updated_at")
    list_filter = ("organization", "responsibility", "is_active")
    search_fields = ("name", "code")


@admin.register(ProcessWorkflowStep)
class ProcessWorkflowStepAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("name", "process_key", "sequence", "organization", "template", "template_step", "is_active")
    list_filter = ("organization", "process_key", "is_active")
    search_fields = ("name", "code", "process_key")


@admin.register(Approver)
class ApproverAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("id", "organization", "user", "role", "workflow_role", "is_active", "updated_at")
    list_filter = ("organization", "is_active", "workflow_role")
    search_fields = ("user__email", "user__first_name", "user__last_name", "role__name")


@admin.register(ProcessAuthority)
class ProcessAuthorityAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("workflow_step", "workflow_role", "approver", "authority_type", "sort_order", "is_active")
    list_filter = ("organization", "authority_type", "is_active")
    search_fields = ("workflow_step__name", "workflow_role__name", "approver__role__name")


@admin.register(UserDelegation)
class UserDelegationAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("delegator", "delegate", "organization", "status", "starts_at", "ends_at")
    list_filter = ("status", "organization")
    search_fields = ("delegator__username", "delegate__username")


@admin.register(WorkflowAuditEvent)
class WorkflowAuditEventAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("event_type", "workflow_instance", "actor", "created_at")
    list_filter = ("event_type",)
    readonly_fields = ("workflow_instance", "event_type", "actor", "payload", "created_at")

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
