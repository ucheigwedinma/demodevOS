from django.apps import AppConfig


class InternalTasksConfig(AppConfig):
    """
    Internal Tasks — lightweight personal + team todos that don't fit a
    specific business process (project / CRM pipeline / HR onboarding).
    Coexists with operational task models (ProjectTask, FollowUpTask, etc.)
    via a read-only overlay endpoint.

    See docs/workspace-internal-tasks-design.md.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.internal_tasks"
    label = "internal_tasks"
    verbose_name = "Internal Tasks"

    def ready(self):
        # Wire signals (notification fan-out for assign, comments, mentions, status)
        import apps.internal_tasks.signals  # noqa: F401

        # Register audited models per design §11. Description + checklist
        # are intentionally excluded — too noisy for compliance audit.
        from auditlog.registry import auditlog

        from .models import Task, TaskComment

        auditlog.register(
            Task,
            include_fields=[
                "title",
                "status",
                "priority",
                "visibility",
                "due_date",
                "assignee",
                "team",
                "completed_at",
                "tags",
            ],
        )
        # Comments are short — log the full record.
        auditlog.register(TaskComment)
