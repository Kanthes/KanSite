from django.db import models

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
	enabled = models.BooleanField(default=True)
	name = models.CharField(max_length=100)
	initial_text_pattern = models.CharField(max_length=5000, default="", blank=True)
	alt_text_pattern = models.CharField(max_length=5000, default="", blank=True)
	link_patterns = models.CharField(max_length=5000, default="", blank=True)
	young_limit = models.IntegerField(default=5)
	old_limit = models.IntegerField(default=10)

	def __str__(self):
		return self.name

class Spambot(models.Model):
	timestamp = models.DateTimeField()
	pattern = models.ForeignKey(SpamPattern)
	user = models.ForeignKey(User)
	messages = models.ManyToManyField(Message)
	reports = models.ManyToManyField(Report)