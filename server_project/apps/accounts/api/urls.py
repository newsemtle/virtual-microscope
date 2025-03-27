from django.urls import path

from .views import ExtendSessionTime, GetSessionTime

urlpatterns = [
    path("session-extend/", ExtendSessionTime.as_view(), name="session-extend"),
    path("session-time/", GetSessionTime.as_view(), name="session-time"),
]
