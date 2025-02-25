from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import FolderViewSet, SlideViewSet, TileView, DZIView

router = DefaultRouter()
router.register(r"folders", FolderViewSet, basename="folder")
router.register(r"slides", SlideViewSet, basename="slide")

urlpatterns = [
    path("", include(router.urls)),
    path("<int:pk>.dzi/", DZIView.as_view(), name="slide-dzi"),
    path(
        "<int:pk>_files/<int:level>/<int:col>_<int:row>.<str:tile_format>/",
        TileView.as_view(),
        name="slide-tiles",
    ),
]
