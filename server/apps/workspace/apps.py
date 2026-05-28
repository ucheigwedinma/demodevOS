from django.apps import AppConfig


class WorkspaceConfig(AppConfig):
    """
    Workspace domain — collaboration teams, internal tasks, calendar, etc.
    Currently scopes only the Teams sub-feature (project pods, initiatives,
    guilds). Internal Tasks and Calendar will land here later or as siblings.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.workspace"
    verbose_name = "Workspace"

    def ready(self):
        # Wire signals (membership notifications, slug auto-gen, owner-leaves-org)
        import apps.workspace.signals  # noqa: F401

        # Register audited models with django-auditlog. Use include_fields so
        # we capture only the user-meaningful changes (skip created_at,
        # updated_at, archived_at — those are bookkeeping).
        from auditlog.registry import auditlog

        from .models import Team, TeamMembership

        auditlog.register(
            Team,
            include_fields=[
                "name",
                "description",
                "purpose",
                "visibility",
                "project",
                "is_archived",
                "emoji",
                "color",
            ],
        )
        auditlog.register(TeamMembership, include_fields=["role"])
