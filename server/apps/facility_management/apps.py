from django.apps import AppConfig


class FacilityManagementConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.facility_management"
    verbose_name = "Facility Management"

    def ready(self):
        import apps.facility_management.signals  # noqa: F401
