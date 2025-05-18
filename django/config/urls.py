"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.i18n import JavaScriptCatalog, set_language

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    # app에 할당된 url
    path("", include("apps.core.urls")),
    path("viewer/", include("apps.viewer.urls")),
    path("images/", include("apps.images.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("lectures/", include("apps.lectures.urls")),
    path("api/", include("config.api_urls")),
    # 언어 설정
    path("i18n/setlang/", set_language, name="set_language"),
    # js 번역을 위한 url. base.html에 포함됨.
    path("jsi18n/", JavaScriptCatalog.as_view(), name="javascript-catalog"),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
