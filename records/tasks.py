from KanCompDetector_site.celery import app

import ConfigParser
import os
from selenium import webdriver
from bs4 import BeautifulSoup
import time

#class AddTask(app.Task):
#	def __init__(self):
#		self.number = 0
		#
#	def run(self, x):
#		self.number += x
#		return self.number
#
#add = app.register_task(AddTask())

class BrowserTask(app.Task):
	def __init__(self):
		#Open config file and read login and password.
		config = ConfigParser.RawConfigParser()
		__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
		config.readfp(open(os.path.join(__location__, 'settings.cfg')))
		self.username = config.get("twitch", "login")
		self.password = config.get("twitch", "password")

		#Create browser and set it up.
		self.browser = webdriver.PhantomJS(service_args=['--ignore-ssl-errors=true', '--ssl-protocol=any'], service_log_path=os.path.devnull)
		self.browser.set_page_load_timeout(10)

		#Load the intitial page to get page source (and captcha)
		self.browser.get("https://www.twitch.tv/login")

@app.task(base=BrowserTask)
def login():
	return login.browser.page_source

#	soup = BeautifulSoup(browser.page_source, 'html.parser')
#	print [input_element['name'] for input_element in soup.find_all('input')]
#
#	element = browser.find_element_by_name("username")
#	element.send_keys(login.username)
#	element = browser.find_element_by_name("password")
#	element.send_keys(login.password) #Be sure to remove password before committing.
#	time.sleep(1)
#	element.submit()
#	print "Entered password."
#	time.sleep(1)
#	try:
#		element = browser.find_element_by_name("authy_token")
#	except:
#		soup = BeautifulSoup(browser.page_source, 'html.parser')
#		print [input_element['name'] for input_element in soup.find_all('input')]
#		print browser.current_url
#		print soup.prettify()
#	element.send_keys(raw_input("Please enter the 6-digit code:"))
#	element.submit()
#	print "Entered authy token."
#	print "Logged in."
#	return True