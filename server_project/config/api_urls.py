from django.urls import include, path

app_name = "api"

urlpatterns = [
    path("accounts/", include("apps.accounts.api.urls")),
    path("database/", include("apps.database.api.urls")),
    path("lectures/", include("apps.lectures.api.urls")),
    path("viewer/", include("apps.slide_viewer.api.urls")),
]
