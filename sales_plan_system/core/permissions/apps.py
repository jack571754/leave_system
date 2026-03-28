from django.apps import AppConfig


class PermissionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.permissions'
    verbose_name = 'Permissions'

    def ready(self):
        from . import signals  # noqa: F401
