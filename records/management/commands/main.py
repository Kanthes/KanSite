from random_useful_functions import start_daemon_thread

from ChatFeed import *
from TwitchAPIHandler import *
from FloodDetector import *
from LinkbasedSpambotDetector import *

import threading
from datetime import datetime
import os

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

class Command(BaseCommand):
	help = "Runs the entire spam & floodbot detection script."

	def handle(self, *args, **options):
		logging.basicConfig(level=logging.INFO)

		logging.info("Starting Chat feed container..")
		self.ChatFeedC = ChatFeed()
		self.ChatFeedC.add_feed(settings.FEED)
		logging.info("Done.")

		logging.info("Starting API fetcher..")
		self.TwitchAPIHandlerC = TwitchAPIHandler(50, redis_host='localhost', initialize=True, client_id=settings.CLIENT_ID)
		logging.info("Done.")

		logging.info("Starting flood bot detector..")
		self.FloodDetector = FloodDetectorMain(self, self.ChatFeedC.get_queue(), apihandler=self.TwitchAPIHandlerC)
		start_daemon_thread(self.FloodDetector.parse_input_queue)
		logging.info("Done.")

		logging.info("Starting link based spam bot detector..")
		self.LinkBasedSpamDetector = LinkBasedSpamDetector(self, self.ChatFeedC.get_queue(lifo=True), apihandler=self.TwitchAPIHandlerC)
		start_daemon_thread(self.LinkBasedSpamDetector.parse_input_queue)
		logging.info("Done.")
		
		self.parse_input()

	def parse_input(self):
		while(True):
			self.status()
			input_message = raw_input()
			if(input_message == "exit"):
				break

#Spits out something like this:
#Detector        Output queue    Input queue     Last parsed message             Cache size
#Flood           0               0               00:00:00                        0
#LinkSpam        0               0               00:00:00                        0
	def status(self):
		response = "{:<16}{:<16}{:<16}{:<32}{:<16}\n{:<16}{:<16}{:<16}{:<32}{:<16}\n{:<16}{:<16}{:<16}{:<32}{:<16}"
		values = [
			"Detector",
			"Output queue",
			"Input queue",
			"Last parsed message",
			"Cache size",
			"Flood",
			self.FloodDetector.output_queue.qsize(),
			self.FloodDetector.input_queue.qsize(),
			"{:%H:%M:%S}".format(self.FloodDetector.last_message),
			len(self.FloodDetector.patterns),
			"LinkSpam",
			self.LinkBasedSpamDetector.output_queue.qsize(),
			self.LinkBasedSpamDetector.input_queue.qsize(),
			"{:%H:%M:%S}".format(self.LinkBasedSpamDetector.last_message),
			len(self.LinkBasedSpamDetector.tracked_users),
		]
		print response.format(*values)
		print "API calls in handler queue: "+str(self.TwitchAPIHandlerC.passive_request_queue.qsize())
		print "Latest message received: "+str(self.ChatFeedC.latest_message)