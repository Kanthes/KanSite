# -*- coding: utf-8 -*-

from random_useful_functions import start_daemon_thread

from datetime import datetime, timedelta
import pytz
import re
import urllib2
from urllib import quote, urlencode
from ssl import SSLError
import json
import time
import Queue
import logging
from unidecode import unidecode
import redis
import threading

import records.models as models
from django.utils.timezone import make_aware
from django.conf import settings

seven_days = timedelta(days=7)
default_creation_date = datetime(1990, 1, 1, 0, 0, 0)

class LinkBasedSpamDetector():
	class TrackedUser():
		def __init__(self, current_message, pattern, parent):
			self.username = current_message.username
			self.messages = [current_message]
			self.pattern = pattern
			self.parent = parent
			self.hits = 0 #Hits is set to 0 initially, forcing the script to match the message against the pattern twice in a row if it's a match first, just to make sure it goes through proper procedure at the end if the limit is set to 1.

			self.creation_date = None
			self.staff_or_admin = None
			self.too_old = None

		def get_age_and_type(self):
			response = self.parent.TwitchAPIHandlerC.get_user(self.username)
			while(not self.parent.TwitchAPIHandlerC.is_valid_response(response) or type(response) == type(0)):
				response = self.parent.TwitchAPIHandlerC.get_user(self.username)
			if(response == 422 or response == 404):
				self.creation_date = default_creation_date
			else:
				response = json.loads(response)
				try:
					self.creation_date = datetime.strptime(response["created_at"]+" UTC", "%Y-%m-%dT%H:%M:%SZ %Z")
				except ValueError:
					self.creation_date = datetime.strptime(response["created_at"]+" UTC", "%Y-%m-%dT%H:%M:%SZ %Z")
				#Determines if the account is older than 7 days.
				self.too_old = not(datetime.now() - self.creation_date <= seven_days)
				#Determines if the account is Admin/Staff/Global Mod.
				if(response.get("type", None) in ["global_mod", "admin", "staff"] or response.get("staff", None) == True):
					self.staff_or_admin = True
				else:
					self.staff_or_admin = False

		def check_limit(self):
			if(self.hits == self.pattern.young_limit):
				if(self.creation_date == "Unprocessable"):
					logging.error("User '{0}' is considered unprocessable and was skipped. Fix this sometime!".format(username))
					#del self.tracked_users[username]
					return False
				elif(self.staff_or_admin == False and self.too_old == False):
					return True
			if(self.hits == self.pattern.old_limit):
				if(self.staff_or_admin == False):
					return True

		def record(self):
			user_object = models.User.objects.get_or_create(username=self.username, creation_date=make_aware(self.creation_date))[0]
			user_object.save()
			spambot_object = models.Spambot(timestamp=self.messages[0].timestamp, pattern=self.pattern.model_object, user=user_object)
			spambot_object.save()
			for message in self.messages:
				spambot_object.messages.create(username=user_object, timestamp=message.timestamp, room=message.room, body=message.message.encode('utf-8'))

	def __init__(self, parent, input_queue, apihandler=None):
		self.parent = parent
		self.input_queue = input_queue
		self.link_pattern = re.compile(settings.LINK_REGEX)
		self.spam_pattern_objects = []

		self.redis_connection = redis.StrictRedis(host='localhost', port=6379, db=0)

		self.tracked_users = {}
		self.recently_caught_usernames = []

		self.output_queue = Queue.Queue()
		self.last_message = datetime(1990, 1, 1, 0, 0, 0, 0, pytz.utc)

		if(apihandler == None):
			from TwitchAPIHandler import TwitchAPIHandler
			self.TwitchAPIHandlerC = TwitchAPIHandler(20)
		else:
			self.TwitchAPIHandlerC = apihandler

		for spampattern_model in models.SpamPattern.objects.filter(enabled=True):
			self.spam_pattern_objects.append(spampattern_model.getSpamPattern())
		logging.info("Imported {0} spam pattern(s) from database.".format(len(self.spam_pattern_objects)))		

	def parse_input_queue(self):
		while(True):
			batch = self.input_queue.get()
			user_queues = {}
			for current_message in batch.messages:
				self.last_message = max(self.last_message, current_message.timestamp)
				#Skip message if it's from a recently caught user.
				if(current_message.username in self.recently_caught_usernames):
					continue
				#Find all links in a message and put them in the Message object as a dictionary. The link is the key, and the value is 3ventic's link analysis, to be determined later on.
				current_message.links = {}
				split_links = re.findall(self.link_pattern, current_message.message)
				for individual_link in split_links:
					domain = ""
					for group in individual_link:
						if(group == "http://" or group == "https://" or group == "www"):
							continue
						elif(group[:1] == "/"):
							break
						domain += group
					if(domain not in ["66.media.tumblr.com", "67.media.tumblr.com", "9gag.com", "agar.io", "amazon.com", "amazon.de", "battle.net", "battlefy.com", "battlelog.battlefield.com", "beam.pro", "beta.deadbydaylight.com", "beta.nightbot.tv", "blog.twitch.tv", "branebot.com", "bungie.net", "cdn.discordapp.com", "challengeme.gg", "challonge.com", "change.org", "chrome.google.com", "clips.twitch.tv", "curse.com", "danbooru.donmai.us", "discord.gg", "discordapp.com", "docs.google.com", "docs.nightbot.tv", "donation.wizebot.tv", "donationalerts.ru", "dotabuff.com", "drive.google.com", "dropbox.com", "dubtrack.fm", "ebay.com", "embed.gyazo.com", "en.wikipedia.org", "eu.battle.net", "facebook.com", "faceit.com", "forum.gamer.com.tw", "frankerfacez.com", "futhead.com", "g2a.com", "gamewisp.com", "gaming.youtube.com", "gamingforgood.net", "gfycat.com", "giphy.com", "gitcoin.gg", "github.com", "giveaway.nikolarn.tv", "gleam.io", "gofundme.com", "goodgame.ru", "google.com", "greenmangaming.com", "gspots.ru", "guld.tv", "gyazo.com", "hearthpwn.com", "help.twitch.tv", "hitbox.tv", "hnlbot.com", "i.gyazo.com", "i.hizliresim.com", "i.imgur.com", "i.ytimg.com", "images.akamai.steamusercontent.com", "imgur.com", "instagram.com", "instant-gaming.com", "jackbox.tv", "jaspyshobbyland.com", "kadgar.net", "link.twitch.tv", "m.facebook.com", "m.imgur.com", "m.youtube.com", "manage.betterttv.net", "meatspin.com", "media.giphy.com", "mediafire.com", "mobile.twitter.com", "monster.cat", "multistre.am", "multitwitch.tv", "new.vk.com", "nexusmods.com", "nightbot.tv", "nightdev.com", "oddshot.tv", "open.spotify.com", "osu.ppy.sh", "pastebin.com", "pathofexile.com", "patreon.com", "paypal.com", "paypal.me", "pbs.twimg.com", "pcpartpicker.com", "periscope.tv", "play.eslgaming.com", "play.spotify.com", "plays.tv", "plug.dj", "poe.trade", "poeurl.com", "popflash.site", "pornhub.com", "postimg.org", "pp.vk.me", "prnt.sc", "prntscr.com", "ptt.cc", "puu.sh", "pyx-2.pretendyoure.xyz", "rbtv.to", "reddit.com", "ref.nikolarn.tv", "referralskins.com", "revlo.co", "rewards.tinybuild.com", "robertsspaceindustries.com", "roblox.com", "rollcsgo.ru", "runebet.com", "s-media-cache-ak0.pinimg.com", "sc2replaystats.com", "scr.hu", "scrap.tf", "screenshot.sh", "secure.twitch.tv", "seeingblue.us", "skinspin.gg", "slither.io", "smash.gg", "socialclub.rockstargames.com", "society.gg", "soundcloud.com", "speedrun.com", "speedtest.net", "spoti.fi", "static-cdn.jtvnw.net", "steamcommunity.com", "steamgifts.co", "store.steampowered.com", "strawpoll.de", "strawpoll.me", "streamad.info", "streambot.com", "streampoll.tv", "supermariomakerbookmark.nintendo.net", "teespring.com", "tipeeestream.com", "tosbase.com", "tppvisuals.com", "ts3.digitalthemepark.com", "twitch-dj.ru", "twitch.drycactus.com", "twitch.moobot.tv", "twitch.tv", "twitchalerts.com", "twitter.com", "twitter.nikolarn.tv", "umggaming.com", "upload.wikimedia.org", "us.battle.net", "vignette2.wikia.nocookie.net", "vine.co", "virtus.pro", "virusbot.xyz", "vivbot.com", "vk.com", "waa.ai", "wiki.teamliquid.net", "wizebot.tv", "wn.nr", "wowhead.com", "wreckvge.nikolarn.tv", "xboxdvr.com", "youtu.be", "youtube.com"]):
						link = ''.join(individual_link)
						current_message.links[link] = None

				#Create queues (just lists) for each user containing all of their messages in the current batch. These lists are then parsed through simultaneously later on.
				if(current_message.username not in user_queues):
					user_queues[current_message.username] = []
				user_queues[current_message.username].append(current_message)
			threads = []
			#logging.info("Creating {0} user queues..".format(len(user_queues))) #DEBUG
			for username in user_queues:
				temp_thread = threading.Thread(target=self.parse_user_queue, args=[username, user_queues[username]])
				temp_thread.daemon = True
				threads.append(temp_thread)
			#logging.info("Starting parsing {0} user queues..".format(len(threads))) #DEBUG
			for thread in threads:
				thread.start()
			for thread in threads:
				thread.join()
			#logging.info("Finished parsing {0} user queues.".format(len(threads))) #DEBUG

	def parse_user_queue(self, username, user_queue):
		#This is where the user queue is parsed. It checks whether the user is already tracked and fetches their TrackedUser object if they are. If the user is tracked it checks each message against the SpamPattern object in question, and if the user isn't tracked it checks each message against every SpamPattern object. If a message contains a link, it runs it through redis and then 3ventic's link analyser to populate the dictionary.
		#Determining if the user is already tracked.
		tracked = (username in self.tracked_users)
		if(tracked):
			tracked_user_object = self.tracked_users[username]

		for current_message in user_queue:
			#Populate the link dictionary with 3ventic's link analysis dictionaries.
			for link in current_message.links:
				current_message.links[link] = self.analyse_link(link)
			#If the user isn't tracked, match against all exisating spam pattern objects.
			if(not tracked):
				for spam_pattern in self.spam_pattern_objects:
					match = spam_pattern.match_message(current_message)
					if(match):
						self.tracked_users[username] = self.TrackedUser(current_message, spam_pattern, self)
						tracked = True
						tracked_user_object = self.tracked_users[username]
						tracked_user_object.update_thread = threading.Thread(target=tracked_user_object.get_age_and_type)
						tracked_user_object.update_thread.start()
						logging.info("User '{0}' was matched by a pattern and is being tracked.".format(username))
			#If the user is tracked, use the TrackedUser.pattern.
			if(tracked):
				match = tracked_user_object.pattern.match_message(current_message, check_alt=True)
				if(match):
					tracked_user_object.hits += 1
					tracked_user_object.messages.append(current_message)
					logging.info("User '{0}' matched it's existing pattern. Hits: {1}".format(username, tracked_user_object.hits))
					tracked_user_object.update_thread.join()
					if(tracked_user_object.check_limit()):
						self.confirmed_hit(tracked_user_object)
						logging.info("User '{0}' was confirmed to be a spambot, and action is being taken.".format(username))
						return True
				else:
					logging.info("User '{0}' is no longer tracked, was cleared from suspicion with the following message in room {1}:\n{2}".format(username, current_message.room, current_message.message.encode("utf-8")))
					del self.tracked_users[username]
			return False

	def analyse_link(self, link):
		#logging.info("Starting analysis of link: {0}".format(link)) #DEBUG
		response = self.redis_connection.get(link)
		if(response):
			self.redis_connection.expire(link, 3600)
			return json.loads(response)
		else: #Redis get failed, need to manually get it.
			try:
				link_analysis_page = urllib2.urlopen("https://ohbot.3v.fi/query/urlquery?q={0}".format(quote(link.encode('utf-8'))), timeout=20)
			except urllib2.HTTPError as e:
				if(e.code not in [404, 500]):
					logging.info("Status code: {0}\nReason: {1}\nLink: {2}".format(e.code, e.reason.encode('utf-8'), link.encode('utf-8')))
				return {}
			except SSLError:
				return {}
			link_analysis_text = link_analysis_page.read()
			link_analysis_data = json.loads(link_analysis_text)
			if(link_analysis_data["status"] == 504):
				logging.info("Status code: {0}\nReason: {1}\nLink: {2}".format(link_analysis_data["status"], link_analysis_data["response"], link.encode('utf-8')))
				return {}
			elif(link_analysis_data["status"] == 200):
				response = self.redis_connection.set(link, link_analysis_text)
				if(response):
					self.redis_connection.expire(link, 3600)
				return link_analysis_data
			else:
				logging.error("Unhandled link analysis status code: {0}".format(link_analysis_data["status"]))
				return {}

	def confirmed_hit(self, tracked_user_object):
		tracked_user_object.record()
		username = tracked_user_object.username
		self.recently_caught_usernames.insert(0, username)
		self.recently_caught_usernames = self.recently_caught_usernames[0:100]
		del self.tracked_users[username]