from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import LectureViewSet, LectureFolderViewSet

router = DefaultRouter()
router.register("folders", LectureFolderViewSet, "lecture-folder")
router.register("lectures", LectureViewSet, "lecture")

urlpatterns = [
    path("", include(router.urls)),
]
