from django.conf.urls import patterns, include, url
from django.contrib import admin

urlpatterns = patterns('',
    url(r'^records/', include('records.urls', namespace="records")),
    url(r'^admin/', include(admin.site.urls)),
)