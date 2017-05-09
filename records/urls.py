from django.conf.urls import url
from django.views.decorators.cache import cache_page

from records import views

urlpatterns = [
	url(r'^$', views.authorize(cache_page(60)(views.flood_index)), name='flood_index'),
	url(r'^long_flood_index/?$', views.authorize(cache_page(60 * 15)(views.long_flood_index)), name='long_flood_index'),
	url(r'^spampattern/?$', views.authorize(views.spampattern_index), name='spampattern_index'),
	url(r'^spampattern/(?P<spampattern_id>\d+)/?$', views.authorize(views.spampattern_detail), name='spampattern_detail'),
	url(r'^flood/(?P<flood_id>\d+)/?$', views.authorize(views.flood_detail), name='flood_detail'),
	url(r'^user/(?P<user_name>[\w\d_]+)/?$', views.authorize(views.user), name='user'),
	url(r'^message/(?P<message_id>\d+)/?$', views.authorize(views.message), name='message'),
	url(r'^spamreport/?$', views.authorize(views.current_year_spam_reports), name='currentyearspamreports'),
	url(r'^spamreport/(?P<start_year>\d{4})(?P<start_month>\d{2})(?P<start_day>\d{2})/(?P<end_year>\d{4})(?P<end_month>\d{2})(?P<end_day>\d{2})/?$', views.authorize(views.spamreport), name='spamreport'),
	url(r'^uniqueusernames/?$', views.authorize(views.uniqueusernames), name='uniqueusernames'),
	url(r'^spambot_log\.log$', views.spambot_log, name='spambot_log'), #Log accessed by 3v's Admin sheet.
	url(r'^access/?$', views.access, name='access'), #Authorization redirect URL
]