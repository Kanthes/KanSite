from random_useful_functions import start_daemon_thread

import mechanize
import time
import json
import cookielib
import Queue
import urllib2
import threading
from datetime import datetime
import sys
import traceback
import logging

def RateLimited(maxPerSecond):
	minInterval = 1.0 / float(maxPerSecond)
	def decorate(func):
		lastTimeCalled = [0.0]
		def rateLimitedFunction(*args,**kargs):
			elapsed = time.clock() - lastTimeCalled[0]
			leftToWait = minInterval - elapsed
			if leftToWait>0:
				time.sleep(leftToWait)
			ret = func(*args,**kargs)
			lastTimeCalled[0] = time.clock()
			return ret
		return rateLimitedFunction
	return decorate

class MechanizedTwitch():
	def __init__(self, username, password, instances, admin=False, apihandler=None, initialize=False):
		self.username = username
		self.password = password
		self.admin = admin

		self.cookiejar = cookielib.LWPCookieJar()

		self.browsers = []
		self.browser_queue = Queue.Queue()
		for i in range(instances):
			self.browsers.append(mechanize.Browser())
			self.browsers[-1].set_handle_robots(False)
			self.browsers[-1].set_cookiejar(self.cookiejar)
			self.browsers[-1].set_handle_redirect(mechanize.HTTPRedirectHandler)
			self.browser_queue.put(self.browsers[-1])

		self.report_queue = Queue.Queue()
		self.reported_users = set()
		self.session_broken = True
		if(apihandler == None):
			from TwitchAPIHandler import TwitchAPIHandler
			self.TwitchAPIHandlerC = TwitchAPIHandler(20, initialize=True)
		else:
			self.TwitchAPIHandlerC = apihandler

		if(initialize):
			self.start_threading_master()

	def login(self):
		browser = self.browser_queue.get()
		self.browser_queue.task_done()

		try:
			browser.open("http://www.twitch.tv/login")
			browser.select_form(nr=0)
			browser["username"] = self.username
			browser["password"] = self.password
			response = browser.submit()

			#print response.read()

			redirect_json = json.loads(response.read())
			redirect_url = redirect_json["redirect"]
			browser.open(redirect_url)

			#Verifying token if Admin acc.
			if(self.admin):
				browser.select_form(nr=0)
				print str(datetime.now().time())+" - "+"Enter authy token:"
				browser["authy_token"] = raw_input()
				response = browser.submit()

				redirect_json = json.loads(response.read())
				redirect_url = redirect_json["redirect"]
				response = browser.open(redirect_url)

#				logging.info(response.read())
			self.browser_queue.put(browser)
		except:
			error_info = sys.exc_info()
			traceback.print_exception(error_info[0], error_info[1], error_info[2])
			self.browser_queue.put(browser)
			return False

		if(self.is_logged_in(browser)):
			self.session_broken = False
			return True
		else:
			return False

	def start_is_logged_in_loop(self):
		start_daemon_thread(self.is_logged_in_loop)

	def is_logged_in_loop(self):
		while(True):
			time.sleep(120)
			browser = self.browser_queue.get()
			self.browser_queue.task_done()

			is_logged_in_bool = self.is_logged_in(browser)

			self.browser_queue.put(browser)

			if(not is_logged_in_bool):
				print str(datetime.now().time())+" - "+"Session broken. Please login again."
				self.session_broken = True
				break

	def is_logged_in(self, browser):
		for i in range(5):
			try:
				response = browser.open("http://www.twitch.tv/inbox")
#				logging.info(response.geturl())
				if(response.geturl() == "https://www.twitch.tv/messages/inbox"):
					return True
#				if(browser.title() == "Inbox - Twitch"):
#					return True
				else:
					return False
			except:
				time.sleep(30)
		else:
			return False

	def start_threading_master(self):
		start_daemon_thread(self.threading_master)

	def threading_master(self):
		while(True):
			while((self.report_queue.empty()) or self.session_broken or self.browser_queue.empty()):
				time.sleep(0.1)
			browser = self.browser_queue.get()
			self.browser_queue.task_done()
			start_daemon_thread(self.threading_slave, args=[browser])

	def threading_slave(self, browser):
		#The empty queue check is there if I choose to expand the library to multiple actions (send inbox message, for example)
		if(not self.report_queue.empty()):
			report_template = self.report_queue.get()
			self.report_queue.task_done()
			response = self.report_user(report_template["username"], report_template["category"], report_template["description"], browser=browser)
			if(not response):
				self.report_queue.put(report_template)

	@RateLimited(0.2)
	def report_user(self, username, category, description, browser=None):
		#Returns True if the user was succesfully reported, the user is already banned, or if the user doesn't exist (and further reports aren't warranted). 
		#Returns False if otherwise failing (for example connection problems) and a re-report is required.
		if(browser == None):
			browser = self.browser_queue.get()
		try:
			response = self.TwitchAPIHandlerC.get_user(username)
			if(type(response) == type("")):
				response = json.loads(response)
				if(type(response) == type(0)): #This is an uncaught error arising from response being an int and nothing more. Because I don't know what causes it or why, I'm simply returning True to ignore it.
					return True
				if(response.get("type") == "user" or response.get("staff") == False): #Makes sure the script cannot TOS Admin or Staff accounts.
					try:
						browser.open("http://www.twitch.tv/"+username+"/report_form") #?tos_ban=true
						browser.select_form(nr=0)
						browser["reason"] = [category]
						browser["description"] = description #Description shoulds be encoded as utf-8 before being passed to this function.
						#browser.find_control(type="checkbox", id="ip_ban").items[0].selected = False
						#browser.find_control(type="checkbox", id="permanent").items[0].selected = True
						#browser["ip_ban"].selected = True
						#browser["permanent"].selected = True
						response = browser.submit().read()
					except:
						error_info = sys.exc_info()
						traceback.print_exception(error_info[0], error_info[1], error_info[2])
						return False

					if(response == "Thank you for your report."):
						return True
					else:
						print str(datetime.now().time())+" - "+"Session broke during report."
						self.session_broken = True
						return False
				else:
					return True
			else:
				return self.TwitchAPIHandlerC.is_valid_response(response)
		except:
			error_info = sys.exc_info()
			traceback.print_exception(error_info[0], error_info[1], error_info[2])
			return False
		finally:
			self.browser_queue.put(browser)

	@RateLimited(0.2)
	def report_user_object(self, report_object):
		if(browser == None):
			browser = self.browser_queue.get()
			response = self.TwitchAPIHandlerC.get_user(report_object.username)
		try:
			if(type(response) == type("")):
				response = json.loads(response)
				if(type(response) == type(0)): #This is an uncaught error arising from response being an int and nothing more. Because I don't know what causes it or why, I'm simply returning True to ignore it.
					return True
				if(response.get("type") == "user" or response.get("staff") == False): #Makes sure the script cannot TOS Admin or Staff accounts.
					try:
						browser.open("http://www.twitch.tv/{0}/report_form".format(report_object.username))
						browser.select_form(nr=0)
						browser["reason"] = [report_object.category]
						browser["description"] = report_object.description #Description shoulds be encoded as utf-8 before being passed to this function.
						#browser.find_control(type="checkbox", id="ip_ban").items[0].selected = False
						#browser.find_control(type="checkbox", id="permanent").items[0].selected = True
						#browser["ip_ban"].selected = True
						#browser["permanent"].selected = True
						response = browser.submit().read()
					except:
						error_info = sys.exc_info()
						traceback.print_exception(error_info[0], error_info[1], error_info[2])
						return False

					if(response == "Thank you for your report."):
						return True
					else:
						print str(datetime.now().time())+" - "+"Session broke during report."
						self.session_broken = True
						return False
				else:
					return True
			else:
				return self.TwitchAPIHandlerC.is_valid_response(response)
		finally:
			self.browser_queue.put(browser)

	def send_personal_message(self, username, subject, message, browser=None):
		if(browser == None):
			browser = self.browser_queue.get()
			self.browser_queue.task_done()
		browser.open("http://www.twitch.tv/message/compose")

		form_and_controls = {}
		for form in browser.forms():
			form_and_controls[form] = ["type={0}, name={1}".format(control.type, control.name) for control in form.controls]
		print "The available forms and their controls are: {0}".format(form_and_controls)

		#print "The available forms are: {0}".format([i.name for i in browser.forms()])

		browser.select_form(nr=5)

		#form = browser.form
		#print "The available controls are: {0}".format(form.controls)

		browser["to_login"] = username
		browser["message[subject]"] = subject
		browser["message[body]"] = message
		response = browser.submit().read()

		print "Sent code to "+username

		self.browser_queue.put(browser)

	def report_multiple_users(self, report_multiple):
		#Assumes a list of dictionaries (or equivalent json formatted string), all containing valid 'username', 'category', and 'description' strings.
		if(type(report_multiple) == type("")):
			report_multiple = json.loads(report_multiple)
		if(type(report_multiple) == type([])):
			for i in report_multiple:
				if(i["username"] not in self.reported_users):
					self.report_queue.put(i)
					self.reported_users.add(i["username"])
		if(type(report_multiple) == type({})):
			if(report_multiple["username"] not in self.reported_users):
				self.report_queue.put(report_multiple)
				self.reported_users.add(report_multiple["username"])