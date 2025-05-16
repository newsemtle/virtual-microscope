from django.contrib.auth import views as auth_views
from django.urls import path

from .views import ProfileView, LoginView

app_name = "accounts"

urlpatterns = [
    path("profile/", ProfileView.as_view(), name="profile"),
    path("login/", LoginView.as_view(), name="login"),
    # 비밀번호 변경은 Django에 내장된 뷰를 사용하고 있습니다.
    path(
        "password_change/",
        auth_views.PasswordChangeView.as_view(
            template_name="accounts/password_change_form.html",
        ),
        name="password_change",
    ),
    path(
        "password_change/done/",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="accounts/password_change_done.html",
        ),
        name="password_change_done",
    ),
]
