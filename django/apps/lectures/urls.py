from django.urls import path

from .views import LectureBulletinsView, LectureDatabaseView, LectureView, LectureEditView

app_name = "lectures"

urlpatterns = [
    path("", LectureBulletinsView.as_view(), name="lecture-bulletins"),
    path("database/", LectureDatabaseView.as_view(), name="lecture-database"),
    path("<int:lecture_id>/", LectureView.as_view(), name="lecture-view"),
    path(
        "<int:lecture_id>/edit/", LectureEditView.as_view(), name="lecture-edit"
    ),
]
