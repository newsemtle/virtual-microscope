from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _lazy


class SlideViewerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.viewer"
    verbose_name = _lazy("Viewer")
