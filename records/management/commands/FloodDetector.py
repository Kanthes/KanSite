import json
from datetime import datetime, timedelta
import pytz
import uuid
import Queue
import threading
import re
from unidecode import unidecode
import logging
import time

import records.models as models
from django.utils.timezone import make_aware
from django.conf import settings

ten_seconds = timedelta(seconds=10)
one_hour = timedelta(hours=1)
one_day = timedelta(days=1)
seven_days = timedelta(days=7)
default_creation_date = datetime(1990, 1, 1, 0, 0, 0)

def checkEqual(iterator):
    iterator = iter(iterator)
    try:
        first = next(iterator)
    except StopIteration:
        return True
    return all(first == rest for rest in iterator)

class FloodDetectorMain():
#----------------------------------------------------------------------------------------------------------------
	class Pattern():
		def __init__(self, key, parent, current_message):
			self.key = key
			self.room = current_message.room
			self.example_message = current_message.message
			
			#Only gets updated when Flood is created.
			self.first_message = current_message.timestamp
			#Gets updated with every new message.
			self.last_message = current_message.timestamp

			self.messages = []
			self.users = {}
			self.parent = parent
			self.suspect = False
			self.uuid = None
			self.timestamp = current_message.timestamp

			self.add_message(current_message)

		def add_message(self, current_message):
			#Update latest message if necessary.
			self.last_message = max(self.last_message, current_message.timestamp)

			#Add message to flood.
			self.messages.append(current_message)
			#Add message to user, or add user if it doesn't already exist.
			if(current_message.username not in self.users):
				self.add_user(current_message)
			else:
				self.users[current_message.username].add_message(current_message)
			#Check if flood is suspect.
			if(len(self.messages) == 10):
				self.suspect = True
				for username in self.users:
					self.parent.TwitchAPIHandlerC.add_request(username, self.add_creation_date_from_api)

		def add_user(self, current_message):
			self.users[current_message.username] = FloodDetectorMain.User(current_message)
			if(self.suspect):
				self.parent.TwitchAPIHandlerC.add_request(current_message.username, self.add_creation_date_from_api)

		def add_creation_date_from_api(self, username, json_raw):
			if(self.parent.TwitchAPIHandlerC.is_valid_response(json_raw)):
				if(json_raw == 422 or json_raw == 404):
					self.users[username].creation_date = default_creation_date #This causes conflict with is_missing_creation_date() since it looks for default creation date.
				else:
					json_data = json.loads(json_raw)
					if(type(json_data) != type(0)):
						try:
							self.users[username].creation_date = datetime.strptime(json_data["created_at"]+" UTC", "%Y-%m-%dT%H:%M:%SZ %Z")
						except ValueError:
							self.users[username].creation_date = datetime.strptime(json_data["created_at"]+" UTC", "%Y-%m-%dT%H:%M:%SZ %Z")
						except AttributeError:
							self.parent.TwitchAPIHandlerC.add_request(username, self.add_creation_date_from_api)
					else:
						self.parent.TwitchAPIHandlerC.add_request(username, self.add_creation_date_from_api)
			else:
				self.parent.TwitchAPIHandlerC.add_request(username, self.add_creation_date_from_api)
#----------------------------------------------------------------------------------------------------------------
		def positive_handler(self):
			while(self.is_missing_creation_dates()):
				time.sleep(1)

			self.groups_of_creation_dates = self.create_creation_date_grouping(self.get_all_creation_dates())

			confirmed = self.is_groups_of_creation_dates_suspect(self.groups_of_creation_dates)
			if(confirmed):
				#Create unique identifier, save to confirmed floods, and attach to output queue.
				self.uuid = uuid.uuid4()
				self.parent.confirmed_floods[int(self.uuid)] = self
				self.parent.output_queue.put(int(self.uuid))
				self.record()
			print self.get_output_message(confirmed)
#----------------------------------------------------------------------------------------------------------------
		def is_missing_creation_dates(self):
			for username in self.users:
				if(self.users[username].creation_date == default_creation_date):
					return True
			else:
				return False

		def get_all_creation_dates(self):
			creation_dates = sorted([self.users[username].creation_date for username in self.users])
			creation_dates = filter(lambda a: a != default_creation_date, creation_dates)
			return creation_dates

		def create_creation_date_grouping(self, creation_dates):
			groups_of_creation_dates = []
			groups_of_creation_dates.append([creation_dates[0]])
			for j in creation_dates[1:]:
				if(j - groups_of_creation_dates[-1][0] <= one_day):
					groups_of_creation_dates[-1].append(j)
				else:
					groups_of_creation_dates.append([j])
			return groups_of_creation_dates

		def is_groups_of_creation_dates_suspect(self, groups_of_creation_dates):
			if(len(groups_of_creation_dates) <= 2):
				for i in groups_of_creation_dates:
					if(len(i) == 1):
						if(datetime.now() - i[0] <= seven_days):
							if(len(self.example_message) > 5):
								continue
						return False
				else:
					return True
			else:
				return False
#----------------------------------------------------------------------------------------------------------------
		def get_output_message(self, confirmed):
			response = "{0:%H:%M:%S} - {1:<5}\t{2:%Y-%m-%d %H:%M:%S} to {3:%Y-%m-%d %H:%M:%S}\t{4:<4} msg\t{5:<3} user(s)\t{6:<20}\t{7}"
			response_values = [
				datetime.now(),
				str(confirmed),
				self.groups_of_creation_dates[0][0],
				self.groups_of_creation_dates[-1][-1],
				len(self.messages),
				len(self.users),
				self.room,
				self.example_message.encode('UTF-8', 'replace')
			]
			return response.format(*response_values)

		def record(self):
			flood_object = models.Flood(pattern=self.key, timestamp=self.timestamp, room=self.room, ident_msg=checkEqual([message.message for message in self.messages]))
			flood_object.save()
			for username in self.users:
				user = self.users[username]
				#Uses get_or_create because user could exist in database since before. For some reason Django thinks the datetime passed here is naive, so I'm making it aware to be sure.
				user_object = models.User.objects.get_or_create(username=user.username, creation_date=make_aware(user.creation_date))[0]
				user_object.save()
				flood_object.users.add(user_object)
				for message in user.messages:
					#Message is created no matter what since it's always going to be new.
					message_object = flood_object.messages.create(username=user_object, timestamp=message.timestamp, room=message.room, body=message.message.encode('utf-8'))
#----------------------------------------------------------------------------------------------------------------
	class User():
		def __init__(self, current_message):
			self.username = current_message.username
			self.messages = [current_message]
			self.creation_date = default_creation_date

		def add_message(self, current_message):
			self.messages.append(current_message)

	def __init__(self, parent, input_queue, apihandler=None):
		self.parent = parent

		self.patterns = {}
		self.confirmed_floods = {}
		self.input_queue = input_queue
		self.output_queue = Queue.Queue()
		self.last_message = datetime(1990, 1, 1, 0, 0, 0, 0, pytz.utc)

		if(apihandler == None):
			from TwitchAPIHandler import TwitchAPIHandler
			self.TwitchAPIHandlerC = TwitchAPIHandler(20)
		else:
			self.TwitchAPIHandlerC = apihandler

	def parse_input_queue(self):
		while(True):
			batch = self.input_queue.get()
			expired_patterns = []
			for current_message in batch.messages:
				self.last_message = max(self.last_message, current_message.timestamp)
				key = self.create_key(current_message)

				#Add each message to it's respective flood, or create a new one if none exist.
				if(key not in self.patterns):
					self.patterns[key] = self.Pattern(key, self, current_message)
				else:
					#If the pattern already exists, but is expired, add it to a list of expired floods to be checked at the end of the batch.
					pattern = self.patterns[key]
					if((self.last_message - pattern.last_message) > ten_seconds):
						expired_patterns.append(pattern)
						self.patterns[key] = self.Pattern(key, self, current_message)
					else:
						self.patterns[key].add_message(current_message)
			#Expire old floods.
			keys_to_be_removed = []
			for key in self.patterns:
				pattern = self.patterns[key]
				#If the latest message is more than 10 seconds old, or the first message is over an hour old.
				if((self.last_message - pattern.last_message) > ten_seconds or (self.last_message - pattern.first_message > one_hour)):
					keys_to_be_removed.append(pattern.key)
			#Remove expired floods from patterns and add to checking list.
			for key in keys_to_be_removed:
				expired_patterns.append(self.patterns[key])
				del self.patterns[key]
			#Check expired floods if suspect and discard rest.
			for pattern in expired_patterns:
				if(pattern.suspect):
					temp_thread = threading.Thread(target=pattern.positive_handler)
					temp_thread.daemon = True
					temp_thread.start()

	standard_emotes_regex = re.compile(settings.EMOTE_STRING)
	link_regex = re.compile(settings.LINK_REGEX)
	alphanumerical_regex = re.compile(ur"\w+(\d[A-Za-z]|[A-Za-z]\d)\w+")
	digit_regex = re.compile(ur"\d+")
	alpha_char_regex = re.compile(ur"[A-Za-z]")
	special_char_regex = re.compile(ur"""[\]\[!"#\$%&'()\*\+,\./:;<=>\?\\\^_`\{\|\}~-]""")
	asian_character_ranges = [
		ur'\p{IsHan}',
		ur'\p{IsHira}',
		ur'\p{IsKana}',
		ur'\p{IsHang}',
		ur'\p{IsHrkt}',
		ur'\uAC00-\uD7AF', #Hangul Syllables
		ur'\u3100-\u312F', #Bopo (IsBopo will match 'o')
		ur'\u31A0-\u31BF', #Bopo Extended
	]
	asian_characters_regex = re.compile('('+'|'.join(asian_character_ranges)+')', re.UNICODE)

	def create_key(self, current_message):
		message = current_message.message
		room = current_message.room

		message_key = self.string_to_key(message)
		key = room+";"+message_key
		return key

	def string_to_key(self, message):
		asian_char_split = re.split(self.asian_characters_regex, message)
		key = ""
		for piece in asian_char_split:
			if(not re.match(self.asian_characters_regex, piece)):
				#Getting rid of all accents with unidecode.
				piece = unidecode(piece)
				#Splitting the message into a list of all words.
				piece = piece.split()
				pattern_words = []
				for word in piece:
					#If the word is a link, represent it as LINK
					if(re.match(self.link_regex, word)):
						pattern_words.append("LINK")
					#If the word contains letters and numbers, represent it as a single @.
					if(re.search(self.alpha_char_regex, word) and re.search(self.digit_regex, word)):
						pattern_words.append("@")
					#If the word is a standard emote, represent it as EMOTE.
					elif(re.match(self.standard_emotes_regex, word)):
						pattern_words.append("EMOTE")
					#Otherwise, replace letters with a, numbers with 0, and special characters with -.
					else:
						word = re.sub(self.digit_regex, "0", word)
						word = re.sub(self.special_char_regex, "-", word)
						word = re.sub(self.alpha_char_regex, "a", word)
						pattern_words.append(word)
				key += " ".join(pattern_words)
			else:
				key += piece
		return key