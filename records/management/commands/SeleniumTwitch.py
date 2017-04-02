from selenium import webdriver
from bs4 import BeautifulSoup
import time

browser = webdriver.PhantomJS(service_args=['--ignore-ssl-errors=true', '--ssl-protocol=any'], desired_capabilities=dcap)
browser.set_page_load_timeout(10)
print "Browser created."
browser.get("http://www.twitch.tv/login")
print "Loaded initial site."

soup = BeautifulSoup(browser.page_source, 'html.parser')
print [input_element['name'] for input_element in soup.find_all('input')]

element = browser.find_element_by_name("username")
element.send_keys("kanthes")
element = browser.find_element_by_name("password")
element.send_keys("") #Be sure to remove password before committing.
time.sleep(1)
element.submit()
print "Entered password."
time.sleep(1)
try:
	element = browser.find_element_by_name("authy_token")
except:
	soup = BeautifulSoup(browser.page_source, 'html.parser')
	print [input_element['name'] for input_element in soup.find_all('input')]
	print browser.current_url
	print soup.prettify()
element.send_keys(raw_input("Please enter the 6-digit code:"))
element.submit()
print "Entered authy token."
print "Logged in."