from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    FolderViewSet,
    SlideViewSet,
    TileView,
    DZIView,
    SlideFileView,
    RebuildView,
)

router = DefaultRouter()
router.register(r"folders", FolderViewSet, basename="folder")
router.register(r"slides", SlideViewSet, basename="slide")

urlpatterns = [
    path("", include(router.urls)),
    path("slide/<int:pk>.dzi/", DZIView.as_view(), name="slide-dzi"),
    path(
        "slide/<int:pk>_files/<int:level>/<int:col>_<int:row>.<str:tile_format>/",
        TileView.as_view(),
        name="slide-tiles",
    ),
    path("slide/file/<int:pk>/", SlideFileView.as_view(), name="slide-file"),
    path("slide/<int:pk>/rebuild/", RebuildView.as_view(), name="slide-rebuild"),
]
