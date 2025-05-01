from django.urls import path

from .views import HomeView

app_name = "common"

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
]
