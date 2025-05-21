from django.urls import path

from .views import (
    ProfileView,
    LoginView,
    ProfileEditView,
    PasswordChangeView,
    PasswordChangeDoneView,
)

app_name = "accounts"

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("profile/edit/", ProfileEditView.as_view(), name="profile-edit"),
    path("password_change/", PasswordChangeView.as_view(), name="password_change"),
    path(
        "password_change/done/",
        PasswordChangeDoneView.as_view(),
        name="password_change_done",
    ),
]
