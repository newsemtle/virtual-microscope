from django.urls import path

from .views import SessionTimeExtendView, SessionTimeView, PublishersView

urlpatterns = [
    path("session-extend/", SessionTimeExtendView.as_view(), name="session-extend"),
    path("session-time/", SessionTimeView.as_view(), name="session-time"),
    path("publishers/", PublishersView.as_view(), name="publishers"),
]
