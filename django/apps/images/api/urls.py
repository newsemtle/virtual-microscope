from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ImageFolderViewSet,
    SlideViewSet,
    TileAPIView,
    DZIAPIView,
    SlideFileAPIView,
    RebuildAPIView,
)

router = DefaultRouter()
router.register(r"folders", ImageFolderViewSet, basename="image-folder")
router.register(r"slides", SlideViewSet, basename="slide")

urlpatterns = [
    path("", include(router.urls)),
    path("slide/<int:pk>.dzi/", DZIAPIView.as_view(), name="slide-dzi"),
    path(
        "slide/<int:pk>_files/<int:level>/<int:col>_<int:row>.<str:tile_format>/",
        TileAPIView.as_view(),
        name="slide-tiles",
    ),
    path("slide/file/<int:pk>/", SlideFileAPIView.as_view(), name="slide-file"),
    path("slide/<int:pk>/rebuild/", RebuildAPIView.as_view(), name="slide-rebuild"),
]
