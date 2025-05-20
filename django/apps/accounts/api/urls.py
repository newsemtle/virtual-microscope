from django.urls import path

from .views import (
    LoginAPIView,
    SessionExtendAPIView,
    SessionTimeAPIView,
    PublishersAPIView,
    LogoutAPIView,
)

urlpatterns = [
    path("login/", LoginAPIView.as_view(), name="login"),
    path("logout/", LogoutAPIView.as_view(), name="logout"),
    path("session_extend/", SessionExtendAPIView.as_view(), name="session-extend"),
    path("session_time/", SessionTimeAPIView.as_view(), name="session-time"),
    path("publishers/", PublishersAPIView.as_view(), name="publishers"),
]
