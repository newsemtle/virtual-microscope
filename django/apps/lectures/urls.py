from django.urls import path

from . import views

app_name = "lectures"

urlpatterns = [
    path("", views.LectureBulletinsView.as_view(), name="lecture-bulletins"),
    path("database/", views.LectureDatabaseView.as_view(), name="lecture-database"),
    path("<int:lecture_id>/", views.LectureView.as_view(), name="lecture-view"),
    path(
        "<int:lecture_id>/edit/", views.LectureEditView.as_view(), name="lecture-edit"
    ),
]
