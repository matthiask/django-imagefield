from __future__ import unicode_literals

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin


try:
    from django.urls import re_path
except ImportError:
    from django.conf.urls import url as re_path


# from testapp import views


urlpatterns = [
    re_path(r"^admin/", admin.site.urls),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
