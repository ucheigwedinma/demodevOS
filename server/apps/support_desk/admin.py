from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from apps.admin_mixins import OrgScopedAdminMixin

from .models import (
    SupportAutomationRule,
    SupportAutomationRun,
    SupportCommunicationLog,
    SupportKnowledgeArticle,
    SupportSlaPolicy,
    SupportTicket,
    SupportTicketAttachment,
    SupportTicketComment,
)


class SupportTicketCommentInline(TabularInline):
    model = SupportTicketComment
    extra = 0
    readonly_fields = ("created_at",)


class SupportTicketAttachmentInline(TabularInline):
    model = SupportTicketAttachment
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(SupportTicket)
class SupportTicketAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = (
        "ticket_id",
        "subject",
        "organization",
        "category",
        "priority",
        "status",
        "assigned_agent",
        "created_at",
        "sla_deadline",
    )
    list_filter = ("organization", "category", "priority", "status")
    search_fields = ("ticket_id", "subject", "description", "requester__email", "assigned_agent__email")
    autocomplete_fields = ("requester", "assigned_agent", "department", "linked_tickets")
    inlines = (SupportTicketCommentInline, SupportTicketAttachmentInline)


@admin.register(SupportTicketComment)
class SupportTicketCommentAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("ticket", "comment_type", "author", "created_at")
    list_filter = ("comment_type",)
    search_fields = ("ticket__ticket_id", "body", "author__email")
    autocomplete_fields = ("ticket", "author")


@admin.register(SupportTicketAttachment)
class SupportTicketAttachmentAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("ticket", "label", "uploaded_by", "created_at")
    search_fields = ("ticket__ticket_id", "label", "uploaded_by__email")
    autocomplete_fields = ("ticket", "uploaded_by")


@admin.register(SupportKnowledgeArticle)
class SupportKnowledgeArticleAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = (
        "title",
        "organization",
        "status",
        "visibility",
        "category",
        "owner",
        "updated_at",
    )
    list_filter = ("organization", "status", "visibility", "category")
    search_fields = ("title", "slug", "summary", "body")
    autocomplete_fields = ("owner", "reviewer")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(SupportSlaPolicy)
class SupportSlaPolicyAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = (
        "name",
        "organization",
        "category",
        "priority",
        "response_target_hours",
        "resolution_target_hours",
        "escalate_after_hours",
        "is_active",
    )
    list_filter = ("organization", "category", "priority", "is_active")
    search_fields = ("name", "description")


@admin.register(SupportCommunicationLog)
class SupportCommunicationLogAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = (
        "id",
        "organization",
        "ticket",
        "interaction_type",
        "channel",
        "direction",
        "author",
        "happened_at",
    )
    list_filter = ("organization", "interaction_type", "channel", "direction")
    search_fields = (
        "ticket__ticket_id",
        "ticket__subject",
        "subject",
        "message",
        "transcript",
        "external_message_id",
    )
    autocomplete_fields = ("ticket", "author")


@admin.register(SupportAutomationRule)
class SupportAutomationRuleAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = (
        "name",
        "organization",
        "trigger_type",
        "priority",
        "run_once_per_ticket",
        "is_active",
        "updated_at",
    )
    list_filter = ("organization", "trigger_type", "is_active", "run_once_per_ticket")
    search_fields = ("name", "description")
    autocomplete_fields = ("created_by",)


@admin.register(SupportAutomationRun)
class SupportAutomationRunAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = (
        "id",
        "organization",
        "rule",
        "ticket",
        "trigger_type",
        "status",
        "created_at",
    )
    list_filter = ("organization", "trigger_type", "status")
    search_fields = ("rule__name", "ticket__ticket_id", "summary")
    autocomplete_fields = ("rule", "ticket")
