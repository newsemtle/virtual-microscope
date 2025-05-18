from django.urls import path

from .views import ImageViewerView

app_name = "viewer"

urlpatterns = [
    path("<int:slide_id>/", ImageViewerView.as_view(), name="image-viewer"),
]
