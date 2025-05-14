from django.urls import path

from . import views

app_name = "images"

urlpatterns = [
    path("database/", views.ImageDatabaseView.as_view(), name="image-database"),
]
