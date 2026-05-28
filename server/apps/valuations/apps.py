from django.apps import AppConfig


class ValuationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.valuations"
    verbose_name = "Valuations"

    def ready(self):
        import apps.valuations.signals  # noqa: F401
