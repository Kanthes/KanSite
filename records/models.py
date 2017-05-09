from django.db import models
from django.conf import settings

import re
import json

# Create your models here.
class User(models.Model):
	username = models.CharField(max_length=40)
	creation_date = models.DateTimeField()

	def __str__(self):
		return self.username

class Message(models.Model):
	username = models.ForeignKey(User)
	timestamp = models.DateTimeField()
	room = models.CharField(max_length=40)
	body = models.CharField(max_length=1000)

	def __str__(self):
		return "{timestamp:%Y-%m-%d %H:%M:%S}\t{room}\t{username}\t{body}".format(timestamp=self.timestamp, room=self.room, username=self.username, body=self.body.encode('utf-8'))

class Flood(models.Model):
	pattern = models.CharField(max_length=5000)
	timestamp = models.DateTimeField()
	room = models.CharField(max_length=40)
	users = models.ManyToManyField(User)
	messages = models.ManyToManyField(Message)
	ident_msg = models.BooleanField(default=None)

	def __str__(self):
		return str(self.id)

class Report(models.Model):
	status = models.CharField(max_length=40, choices=[
			('crtd', 'Created'),
			('sent', 'Sent'),
		])
	from_username = models.CharField(max_length=40)
	target_username = models.CharField(max_length=40)
	target_id = models.IntegerField()
	tos_ban = models.BooleanField(default=False)
	ip_ban = models.NullBooleanField(default=None)
	permanent_ban = models.NullBooleanField(default=None)
	category = models.CharField(max_length=200)
	description = models.CharField(max_length=5000)
	created_timestamp = models.DateTimeField()
	updated_timestamp = models.DateTimeField()

class SpamPattern(models.Model):
	#Remember to escape any \ used for regex with an additional \, as they're loaded via json.loads which also uses \ for escaping.
	enabled = models.BooleanField(default=True)
	name = models.CharField(max_length=100)
	initial_text_pattern = models.CharField(max_length=5000, default="", blank=True)
	alt_text_pattern = models.CharField(max_length=5000, default="", blank=True)
	link_patterns = models.CharField(max_length=5000, default="", blank=True)
	young_limit = models.IntegerField(default=5)
	old_limit = models.IntegerField(default=10)

	def __str__(self):
		return self.name

	class SpamPattern():
		def __init__(self, SpamPattern_object):
			self.name = SpamPattern_object.name
			self.initial_text_pattern = re.compile(re.sub("\{emote_string\}", settings.EMOTE_STRING, SpamPattern_object.initial_text_pattern)) if SpamPattern_object.initial_text_pattern != "" else None
			self.alt_text_pattern = json.loads(re.sub("'", '"', SpamPattern_object.link_patterns)) if SpamPattern_object.link_patterns != "" else {}
			self.link_patterns = json.loads(re.sub("'", '"', SpamPattern_object.link_patterns)) if SpamPattern_object.link_patterns != "" else {}
			for key in self.link_patterns.keys():
				self.link_patterns[key] = re.compile(self.link_patterns[key])
			self.young_limit = SpamPattern_object.young_limit
			self.old_limit = SpamPattern_object.old_limit
			self.model_object = SpamPattern_object

		#Required links to have been analysed
		def match_message(self, current_message, check_alt=False):
			if(self.initial_text_pattern):
				if(re.match(self.initial_text_pattern, current_message.message)):
					return True
			if(check_alt):
				for pattern in self.alt_text_pattern:
					if(re.match(pattern, current_message.message)):
						return True
			for link in current_message.links:
				#Sometimes the link directory will end up being completely empty if it's a invalid link. In this case, we simply skip analyzing the link.
				if(current_message.links[link] == {}):
					continue
				for key in self.link_patterns:
					#'key' in this case is the keys in 3ventics link analysis, meaning it's used to find the correct pattern to use and the right string to match it to.
					pattern = self.link_patterns[key]
					try:
						target = current_message.links[link][key]
					except KeyError:
						continue
					else:
						if(re.match(pattern, target)):
							return True
			return False

	def getSpamPattern(self):
		return self.SpamPattern(self)

class Spambot(models.Model):
	timestamp = models.DateTimeField()
	pattern = models.ForeignKey(SpamPattern)
	user = models.ForeignKey(User)
	messages = models.ManyToManyField(Message)
	reports = models.ManyToManyField(Report)