from django.urls import include, path

app_name = "api"

urlpatterns = [
    path("lectures/", include("apps.lectures.api.urls")),
    path("database/", include("apps.database.api.urls")),
    path("viewer/", include("apps.slide_viewer.api.urls")),
    # path("accounts/", include("apps.accounts.api.urls")),
]
