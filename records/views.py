from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.db.models import Count
from django.views import generic
from django.conf import settings

from records.models import Flood, User, Message, Report, SpamPattern, Spambot

from datetime import datetime, timedelta, date
import pytz
import urllib
import urllib2
import json
import base64

def authorize(func):
	def inner(request, *args, **kwargs):
		#Check if an access token exists in their Session. If it does, check the user type to see if they're Admin/Staff before proceeding. If they don't have an access token, forward them to the Authorization Page.
		if(request.session.get("access_token", False) != False):
			headers = {
				'Client-ID':settings.CLIENT_ID,
				'Accept':'application/vnd.twitchtv.v5+json',
				'Authorization':'OAuth {}'.format(request.session["access_token"]),
			}
			try:
				response = json.loads(urllib2.urlopen(urllib2.Request(url="https://api.twitch.tv/kraken/user", headers=headers)).read())
				if(response.get("type", "") in ["global_mod", "admin", "staff"]):
					#All is well.
					return func(request, *args, **kwargs)
				else:
					return HttpResponse("Your Twitch account does not have access to this page.")
			except urllib2.HTTPError:
				request.session["access_token"] = False
		if(request.session.get("access_token", False) == False):
			parameters = {
				"client_id":settings.CLIENT_ID,
				"redirect_uri":"http://193.111.136.150/records/access/",
				"scope":'+'.join(["user_read"]),
				"state":base64.b64encode(request.build_absolute_uri())
			}
			url = "https://api.twitch.tv/kraken/oauth2/authorize?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}&scope={scope}&state={state}".format(**parameters)
			return HttpResponseRedirect(url)
			#Final redirect should look something like http://localhost/?code=orpnlthisisfakevmntl4q8wlgbqub&scope=user_read
	return inner

def access(request):
	#This is the view the user is forwarded to after authorizing the app via Twitch. It makes an API call with the provided code to get an access token, and saves it in their Session.
	if(request.GET.get("code", False)):
		post_values = {
			"client_id":settings.CLIENT_ID,
			"client_secret":settings.CLIENT_SECRET, #Don't commit with this info in public.
			"grant_type":"authorization_code",
			"redirect_uri":"http://193.111.136.150/records/access/",
			"scope":"user_read",
			"code":request.GET["code"],
		}
		response = json.loads(urllib2.urlopen(urllib2.Request("https://api.twitch.tv/kraken/oauth2/token", urllib.urlencode(post_values))).read())
		request.session["access_token"] = response["access_token"]
		#Response should look something like this: {"access_token":"ulln5dthisisfake47rr4zljn4b78u","refresh_token":"nykye9cqr2nthisisfaker78edme94nm3h6xiybjifzn7wfbju","scope":["user_read"]}

		#This is where I forward them back to the original page they wanted via "state", which then calls the authorize function all over again.
		return HttpResponseRedirect(base64.b64decode(request.GET["state"]))
	else:
		return HttpResponseRedirect("/records/")

# Create your views here.
def index(request):
	#latest_flood_list = Flood.objects.annotate(num_users=Count('users')).filter(num_users__gte=10).order_by('-timestamp')[:5] #5 latest floods with 10 or more users involved.
	latest_flood_list = Flood.objects.filter(timestamp__gte=datetime.now(pytz.utc)-timedelta(days=3)).order_by('-timestamp')
	context = {'latest_flood_list':latest_flood_list}
	return render(request, 'records/index.html', context)

def long_index(request):
	flood_objects = Flood.objects.annotate(user_count=Count('users')).filter(user_count__gte=10, ident_msg=False, timestamp__gte=datetime(2017, 2, 1, 0, 0, 0, 0, pytz.utc)).order_by('-timestamp')
	context = {'latest_flood_list':flood_objects}
	return render(request, 'records/index.html', context)	

def flood(request, flood_id):
	flood = get_object_or_404(Flood, pk=flood_id)
	return render(request, 'records/flood.html', {'flood':flood})

def user(request, user_name):
	user = get_object_or_404(User, username=user_name)
	return render(request, 'records/user.html', {'user':user})

def message(request, message_id):
	message = get_object_or_404(Message, pk=message_id)
	return render(request, 'records/message.html', {'message':message})

def reports_2016(request):
	#Create a list of dictionaries containing all the dates with reports and number of reports for that date, and then turn that list of dictionaries into a sorted list of lists.
	date_data = Report.objects.all().extra({'date_created' : "DATE(created_timestamp)"}).values('date_created').annotate(created_count=Count('id'))
	date_data = map(lambda x: [x['date_created'], x['created_count']], date_data)
	date_data.sort(key=lambda x: x[0])
	#Create a list of dictionaries containing all the hours with reports and the number of reports for that hour, and then turn that list of dictionaries into a sorted list of lists.
	hourly_data = Report.objects.all().extra({'time_created' : "EXTRACT(HOUR FROM created_timestamp)"}).values('time_created').annotate(created_count=Count('id'))
	hourly_data = map(lambda x: [x['time_created'], int(x['created_count'])], hourly_data)
	hourly_data.sort(key=lambda x: x[0])
	context = {'date_data':date_data, 'hourly_data':hourly_data}
	return render(request, 'records/2016report.html', context)

def spamreport(request, start_year, start_month, start_day, end_year, end_month, end_day):
	#Create datetime objects based of URL variables.
	start_date = datetime(year=int(start_year), month=int(start_month), day=int(start_day), tzinfo=pytz.utc)
	end_date = datetime(year=int(end_year), month=int(end_month), day=int(end_day), tzinfo=pytz.utc)

	#Get the SpamPatterns active in between the start and end date.
	spam_patterns = SpamPattern.objects.filter(spambot__timestamp__range=(start_date, end_date)).distinct()
	spam_pattern_names = [spam_pattern.name for spam_pattern in spam_patterns]
	if(spam_pattern_names == []):
		spam_pattern_names.append("None.")
		date_list = [[start_date, ['null']]]
	else:
		#Create a dictionary of all possible date+hour combinations between start and end date by creating a list of lists, each containing the datetime and a list containing number of nulls corresponding with the number of active spampatterns.
		date_dict = dict([[start_date + timedelta(hours=x), ['null']*len(spam_patterns)] for x in range(0, int((end_date-start_date).total_seconds()//3600))])

		#For each SpamPattern, get the hourly spambots and overwrite the dictionary at the relevant positions.
		for i in range(0, len(spam_patterns)):
			#Create a QuerySet that appends the raw Date and the raw Hour based on the timestamp, along with the number of bots for each combination of the two.
			hourly_spambots = Spambot.objects.filter(timestamp__range=(start_date, end_date), pattern=spam_patterns[i].id).extra({'date_created':"DATE(timestamp)", 'hour_created':"EXTRACT(HOUR FROM timestamp)"}).values('date_created', 'hour_created').annotate(created_count=Count('id'))
			#Now overwrite the dictionary by populating it with the data from the Queryset.
			for hourly_spambot in hourly_spambots:
				date_dict[datetime(year=hourly_spambot['date_created'].year, month=hourly_spambot['date_created'].month, day=hourly_spambot['date_created'].day, hour=hourly_spambot['hour_created'], tzinfo=pytz.utc)][i] = hourly_spambot['created_count']

		#Finally, turn the dictionary into a sorted list of key+value combinations.
		date_list = sorted([[key, date_dict[key]] for key in date_dict.keys()])
	context = {'spam_pattern_names':spam_pattern_names, 'date_list':date_list, 'start_date':start_date, 'end_date':end_date}
	return render(request, 'records/spamreport.html', context)

def uniqueusernames(request):
	flood_ids = request.GET.getlist("flood_checkbox")
	usernames = User.objects.distinct().filter(flood__id__in=flood_ids)
	usernames = [user.username for user in usernames]
	return render(request, 'records/uniqueusernames.html', {'usernames':usernames})

def current_year_spam_reports(request):
	start_date = datetime(datetime.now(pytz.utc).year, 01, 01)
	end_date = datetime(datetime.now(pytz.utc).year+1, 01, 01)
	while(start_date.weekday() != 0):
		start_date += timedelta(days=1)
	while(end_date.weekday() != 0):
		end_date += timedelta(days=1)
	list_of_dates = [start_date + timedelta(days=7)*i for i in range(0, (end_date-start_date).days//7)]
	list_of_dates = [[date, date+timedelta(days=7)] for date in list_of_dates]
	return render(request, 'records/current_year_spam_reports.html', {'list_of_dates':list_of_dates})

def spambot_log(request):
	spambot_objects = Spambot.objects.order_by('-timestamp')[:50]
	return render(request, 'records/spambot_log.html', {'spambot_objects':spambot_objects})