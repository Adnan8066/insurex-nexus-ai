from django.apps import AppConfig


class AuditlogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.auditlog'
    label = 'auditlog'
    verbose_name = 'Audit log'

    def ready(self):
        from . import signals  # noqa: F401
