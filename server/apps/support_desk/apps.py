from django.apps import AppConfig


class SupportDeskConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.support_desk"
    verbose_name = "Support Desk"

    def ready(self):
        from auditlog.registry import auditlog

        import apps.support_desk.signals  # noqa: F401

        from .models import (
            SupportKnowledgeArticle,
            SupportSlaPolicy,
            SupportTicket,
            SupportTicketAttachment,
            SupportTicketComment,
        )

        for model in (
            SupportTicket,
            SupportTicketComment,
            SupportTicketAttachment,
            SupportKnowledgeArticle,
            SupportSlaPolicy,
        ):
            auditlog.register(model)
