from django.urls import path

from . import views

app_name = "slide_viewer"

urlpatterns = [
    path("<int:slide_id>/", views.SlideView.as_view(), name="slide-view"),
    path("save_annotation/", views.save_annotation, name="save_annotation"),
]
