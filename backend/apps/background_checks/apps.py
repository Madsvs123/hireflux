from django.apps import AppConfig


class BackgroundChecksConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.background_checks"
    label = "background_checks"
    verbose_name = "Background Checks"
