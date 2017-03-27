from django.conf.urls import include, url
from django.contrib import admin

urlpatterns = [
    url(r'^records/', include('records.urls', namespace="records")),
    url(r'^admin/', include(admin.site.urls)),
]