from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"

    def ready(self):
        import apps.notifications.signals  # noqa: F401
        from apps.notifications.data_broadcast import register_all_broadcasters
        register_all_broadcasters()
