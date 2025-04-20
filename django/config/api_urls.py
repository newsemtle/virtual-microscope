from django.urls import include, path

app_name = "api"

urlpatterns = [
    path("accounts/", include("apps.accounts.api.urls")),
    path("images/", include("apps.images.api.urls")),
    path("lectures/", include("apps.lectures.api.urls")),
    path("viewer/", include("apps.viewer.api.urls")),
]
