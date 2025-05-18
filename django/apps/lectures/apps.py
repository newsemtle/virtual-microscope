from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _lazy


class LecturesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.lectures"
    verbose_name = _lazy("Lectures")
