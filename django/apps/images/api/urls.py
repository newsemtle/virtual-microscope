from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ImageFolderViewSet,
    SlideViewSet,
    SlideTileAPIView,
    SlideDZIAPIView,
    SlideFileAPIView,
    SlideRebuildAPIView,
    SlideDBSearchAPIView,
)

router = DefaultRouter()
router.register(r"folders", ImageFolderViewSet, basename="image-folder")
router.register(r"slides", SlideViewSet, basename="slide")

urlpatterns = [
    path("slides/<int:pk>.dzi/", SlideDZIAPIView.as_view(), name="slide-dzi"),
    path(
        "slides/<int:pk>_files/<int:level>/<int:col>_<int:row>.<str:tile_format>/",
        SlideTileAPIView.as_view(),
        name="slide-tiles",
    ),
    path("slides/<int:pk>/file/", SlideFileAPIView.as_view(), name="slide-file"),
    path(
        "slides/<int:pk>/rebuild/", SlideRebuildAPIView.as_view(), name="slide-rebuild"
    ),
    path("slides/dbsearch/", SlideDBSearchAPIView.as_view(), name="slide-dbsearch"),
    path("", include(router.urls)),
]
