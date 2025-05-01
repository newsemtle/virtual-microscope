from django.urls import path

from . import views

app_name = "viewer"

urlpatterns = [
    path("<int:slide_id>/", views.ImageViewerView.as_view(), name="image-viewer"),
]
