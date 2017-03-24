from random_useful_functions import start_daemon_thread

import Queue
import threading
import urllib2
import time
import datetime

class TwitchAPIHandler():
	def __init__(self, instances, redis_host=None, redis_port=None, initialize=False, client_id=""):
		self.thread_limit = threading.Semaphore(instances)
		self.client_id = client_id

		self.passive_request_queue = Queue.Queue()

		if(redis_host != None):
			import redis
			self.using_redis = True
			self.redis_connection = redis.StrictRedis(host=redis_host, port=6379 if redis_port == None else redis_port, db=0)
		else:
			self.using_redis = False

		if(initialize):
			self.start_threading_master()
#----------------------------------------------------------------------------------------------------------------
	def get_url(self, url):
		#If it encounters an error, returns an int with the HTTP error code.
		#If successful, returns a string of the json response.
		request = urllib2.Request(url=url, headers={'Client-ID':self.client_id})
		try:
			response = urllib2.urlopen(request).read()
			response_code = 200
		except urllib2.HTTPError, e:
			response = int(e.code)
			response_code = int(e.code)
		except:
			#Probably a timeout, if anything.
			response = 0
			response_code = 0
		return response

	#Checks if response is 'valid', meaning it doesn't need to be looked up again due to server or connection errors. This is only the case if the response was a string, a banned/deleted account, or a non-existent account.
	def is_valid_response(self, response):
		if(type(response) == type("string")):
			return True
		elif(response == 422):
			return True
		elif(response == 404):
			return True
		else:
			return False
#----------------------------------------------------------------------------------------------------------------
	def redis_get_key(self, key):
		response = self.redis_connection.get(key)
		if(response != None):
			self.redis_connection.expire(key, 3600)
		return response

	def redis_set_key(self, key, value):
		if(self.is_valid_response(value)):
			response = self.redis_connection.set(key, value)
			if(response): #Redis responds True if the key was successfully set.
				self.redis_connection.expire(key, 3600)
			return response
#----------------------------------------------------------------------------------------------------------------
	def get_level_url(self, url):
		self.thread_limit.acquire()
		response = self.get_url(url)
		self.thread_limit.release()
		return response

	def get_level_redis(self, url, redis_key):
		self.thread_limit.acquire()
		response = self.redis_get_key(redis_key)
		if(response == None):
			response = self.get_url(url)
			self.redis_set_key(redis_key, response)
		self.thread_limit.release()
		return response
#----------------------------------------------------------------------------------------------------------------
	def get_user(self, username):
		url = "https://api.twitch.tv/kraken/users/"+username
		if(self.using_redis):
			redis_key = username+" users"
			return self.get_level_redis(url, redis_key)
		else:
			return self.get_level_url(url)

	def get_channel(self, username):
		url = "https://api.twitch.tv/kraken/channels/"+username
		if(self.using_redis):
			redis_key = username+" channels"
			return self.get_level_redis(url, redis_key)
		else:
			return self.get_level_url(url)

	def get_stream(self, username):
		url = "https://api.twitch.tv/kraken/streams/"+username
		if(self.using_redis):
			redis_key = username+" streams"
			return self.get_level_redis(url, redis_key)
		else:
			return self.get_level_url(url)
#----------------------------------------------------------------------------------------------------------------
	def start_threading_master(self):
		start_daemon_thread(self.threading_master)

	def threading_master(self):
		while(True):
			while(self.passive_request_queue.empty()):
				time.sleep(0.1)
			self.thread_limit.acquire() #Acquire the semaphore token BEFORE creation, to make it impossible to exceed instance limit.
			start_daemon_thread(self.threading_slave)

	def threading_slave(self):
		#The empty queue check is there if I choose to expand the library to multiple actions.
		try:
			if(not self.passive_request_queue.empty()):
				request_template = self.passive_request_queue.get()
				self.passive_request_queue.task_done()

				if(request_template["target_api"] == "user"):
					response = self.get_user(request_template["username"])
				elif(request_template["target_api"] == "channel"):
					response = self.get_channel(request_template["username"])
				elif(request_template["target_api"] == "streams"):
					response = self.get_streams(request_template["username"])

				temp_thread = threading.Thread(target=request_template["target_function"], args=[request_template["username"], response])
				temp_thread.daemon = True
				temp_thread.start()
		finally:
			self.thread_limit.release()

	def add_request(self, username, target_function, target_api="user"):
		self.passive_request_queue.put({"username":username, "target_function":target_function, "target_api":target_api})