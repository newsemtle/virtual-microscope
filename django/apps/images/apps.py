from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _lazy


class DatabaseConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.images"
    verbose_name = _lazy("Images")
