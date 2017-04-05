from django.conf.urls import url

from records import views

urlpatterns = [
	url(r'^$', views.index, name='index'),
	url(r'^flood/(?P<flood_id>\d+)/?$', views.flood, name='flood'),
	url(r'^user/(?P<user_name>[\w\d_]+)/?$', views.user, name='user'),
	url(r'^message/(?P<message_id>\d+)/?$', views.message, name='message'),
	url(r'^2016report/?$', views.reports_2016, name='2016report'),
	url(r'^spamreport/?$', views.current_year_spam_reports, name='currentyearspamreports'),
	url(r'^spamreport/(?P<start_year>\d{4})(?P<start_month>\d{2})(?P<start_day>\d{2})/(?P<end_year>\d{4})(?P<end_month>\d{2})(?P<end_day>\d{2})/?$', views.spamreport, name='spamreport'),
	url(r'^uniqueusernames/?$', views.uniqueusernames, name='uniqueusernames'),
	url(r'^twitch_login/?$', views.twitch_login, name='twitch_login'),
]