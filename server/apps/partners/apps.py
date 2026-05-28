from django.apps import AppConfig


class PartnersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.partners"
    verbose_name = "Partner Gateway"

    def ready(self):
        import apps.partners.signals  # noqa: F401
