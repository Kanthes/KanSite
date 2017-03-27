from random_useful_functions import start_daemon_thread

from ChatFeed import *
from TwitchAPIHandler import *
from FloodDetector import *
from LinkbasedSpambotDetector import *
from MechanizedTwitch2 import *

import threading
from datetime import datetime
import ConfigParser
import os

from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
	help = "Runs the entire spam & floodbot detection script."

	def handle(self, *args, **options):
		logging.basicConfig(level=logging.INFO)

		logging.info("Loading config..")
		config = ConfigParser.RawConfigParser()
		__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
		config.readfp(open(os.path.join(__location__, 'settings.cfg')))
		logging.info("Done.")

		logging.info("Starting Chat feed container..")
		self.ChatFeedC = ChatFeed()
		#self.ChatFeedC.add_feed(config.get("feed", "normal"))
		self.ChatFeedC.add_feed(config.get("feed", "ws"))
		logging.info("Done.")

		logging.info("Starting API fetcher..")
		self.TwitchAPIHandlerC = TwitchAPIHandler(50, redis_host='localhost', initialize=True, client_id=config.get("twitch", "client_id"))
		logging.info("Done.")

		logging.info("Starting ban cannon..")
		self.MechanizedTwitchC = MechanizedTwitch(config.get("twitch", "login"), config.get("twitch", "password"), 10, admin=True, apihandler=self.TwitchAPIHandlerC, initialize=True)
		logging.info("Done.")

		logging.info("Starting flood bot detector..")
		self.FloodDetector = FloodDetectorMain(self, self.ChatFeedC.get_queue(), apihandler=self.TwitchAPIHandlerC, reporthandler=self.MechanizedTwitchC)
		start_daemon_thread(self.FloodDetector.parse_input_queue)
		logging.info("Done.")

		logging.info("Starting link based spam bot detector..")
		self.LinkBasedSpamDetector = LinkBasedSpamDetector(self, self.ChatFeedC.get_queue(lifo=True), apihandler=self.TwitchAPIHandlerC, reporthandler=self.MechanizedTwitchC)
		start_daemon_thread(self.LinkBasedSpamDetector.parse_input_queue)
		logging.info("Done.")
		
		self.parse_input()

	def parse_input(self):
		while(True):
			self.status()
			print "1. Review flood bots."
			print "4. Manually TOS input."
			if(self.MechanizedTwitchC.session_broken):
				print "5. Login to Authy."
			input_message = raw_input()
			if(input_message == "1"):
				self.FloodDetector.review_output()
			elif(input_message == "4"):
				print "Entering manual TOS mode. Keep entering manual TOS dictionaries until you're finished, and then enter 'quit'."
				while(True):
					raw_tos_data = raw_input()
					if(raw_tos_data == "quit"):
						break
					self.MechanizedTwitchC.report_multiple_users(raw_tos_data)
			elif(input_message == "5"):
				self.MechanizedTwitchC.login()
				self.MechanizedTwitchC.start_is_logged_in_loop()
			elif(input_message == "exit"):
				break

#Spits out something like this:
#Detector        Output queue    Input queue     Last parsed message
#Flood           0               0               11:45:38
#Spam            0               0               00:00:00
#LinkSpam        0               0               00:00:00
	def status(self):
		response = "{0:<16}{1:<16}{2:<16}{3}\n{4:<16}{5:<16}{6:<16}{7:%H:%M:%S}\n{8:<16}{9:<16}{10:<16}{11:%H:%M:%S}"
		values = [
			"Detector",
			"Output queue",
			"Input queue",
			"Last parsed message",
			"Flood",
			self.FloodDetector.output_queue.qsize(),
			self.FloodDetector.input_queue.qsize(),
			self.FloodDetector.last_message,
			"LinkSpam",
			self.LinkBasedSpamDetector.output_queue.qsize(),
			self.LinkBasedSpamDetector.input_queue.qsize(),
			self.LinkBasedSpamDetector.last_message,
		]
		print response.format(*values)
		print "Users in report queue: "+str(self.MechanizedTwitchC.report_queue.qsize())
		print "API calls in handler queue: "+str(self.TwitchAPIHandlerC.passive_request_queue.qsize())
		print "Latest message received: "+str(self.ChatFeedC.latest_message)