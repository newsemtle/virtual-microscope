from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import LectureViewSet, LectureFolderViewSet

router = DefaultRouter()
router.register("lectures", LectureViewSet, "lecture")
router.register("folders", LectureFolderViewSet, "lecture-folder")

urlpatterns = [
    path("", include(router.urls)),
]
