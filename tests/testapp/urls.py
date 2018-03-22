from django.conf.urls import url
from django.contrib import admin


# from testapp import views


urlpatterns = [
    url(r'^admin/', admin.site.urls),
]
