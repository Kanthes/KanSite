# -*- coding: utf-8 -*-
import logging

import websocket
from datetime import datetime
import pytz
import json
import time
import Queue
import threading

class Message():
	def __init__(self, timestamp, room, username, message, tags):
		self.timestamp = timestamp #datetime object
		self.room = room #string
		self.username = username #string
		self.message = message #string
		self.tags = tags #dict
		
#TODO: Make the rest of the program use MessageBatch.
class MessageBatch():
	batch_size = 1000
	def __init__(self):
		self.messages = []


class ChatFeed():
	def __init__(self):
		self.queues = []
		self.sockets = []
		self.threads = []

		self.current_batch = MessageBatch()
		self.batch_input_lock = threading.RLock()

		self.latest_message = datetime(1990, 1, 1, 0, 0, 0, 0, pytz.utc)

	def add_feed(self, url):
		ws = websocket.WebSocketApp(url, on_message=self.on_message, on_error=self.on_error, on_close=self.on_close)
		ws.on_open = self.on_open
		self.sockets.append(ws)

		thread = threading.Thread(target=ws.run_forever)
		thread.daemon = True
		thread.start()
		self.threads.append(thread)

	def get_queue(self, lifo=False):
		if(lifo):
			queue = Queue.LifoQueue()
		else:
			queue = Queue.Queue()
		self.queues.append(queue)
		return queue

	def message_validity(self, message):
		if("#"+message.username == message.room):
			#logging.debug("User chatted in their own room.") #DEBUG
			return False
		if(message.username in ["moobot", "nightbot", "xanbot", "ackbot", "x20ks5pfq", "pho_test", "eixobu24", "monitorplz", "oshibookie", "dutch1616"]):
			#logging.debug("User is in list of allowed users.") #DEBUG
			return False
		if(message.room in ["#forsenlol", "#anm60forjesus", "#manatails", "#csgoloungetv_ru", "#twitchrallyred", "#twitchrallyblue"]):
			#logging.debug("Message is from one of the ignored rooms.") #DEBUG
			return False
		if(message.tags.get("subscriber") == "1"):
			#logging.debug("User is subscriber.") #DEBUG
			return False
		if(message.tags.get("user-type") == "mod"):
			#logging.debug("User is moderator.") #DEBUG
			return False
		return True

	def on_message(self, ws, message):
		#logging.info(message)
		ws_message = json.loads(message)
		#Filters out feed-specific data as well as commands like "CLEARCHAT".
		if(ws_message["type"] == "msg" and ws_message["data"]["command"] == ""):
			#Splits the "key=value;key2=value2;key3=value3" format into a list of lists.
			tags_data = [item.split("=") for item in ws_message["data"]["tags"].split(";")]
			#Pads all the lists within the tags_data list to len=2, as the tags will sometimes contain no "=" separator.
			tags_data = map(lambda a: (a + [''] * 2)[:2], tags_data)
			tags = dict(tags_data)
			message = Message(datetime.fromtimestamp(float(ws_message["ts"]), pytz.utc), ws_message["data"]["room"], ws_message["data"]["nick"], ws_message["data"]["body"], tags)
			if(self.message_validity(message)):
				with self.batch_input_lock:
					self.current_batch.messages.append(message)
					if(len(self.current_batch.messages) >= MessageBatch.batch_size):
						batch = self.current_batch
						for i in self.queues:
							if(i.qsize() >= 100):
								logging.warning("WARNING, a queue has exceeded 100 entries and has been cleared.")
								while (not i.empty()):
									i.get()
							i.put(batch)
						self.current_batch = MessageBatch()
			self.latest_message = message.timestamp

	def on_error(self, ws, error):
		logging.info(error)

	def on_open(self, ws):
		ws.send("+all")

	def on_close(self, ws):
		logging.info("Chat feed went down.")

#Example data
#{"type":"msg","data":{"command":"","room":"#narkuss_lol","nick":"sansastarkismyfather","target":"","body":"oui c'est pour ça que j'ai ecrit son nom :p","tags":"badges=premium/1;color=#C20000;display-name=;emotes=12:41-42;id=f5e1a4c3-08ac-48e5-93f7-c45f7afb941d;mod=0;room-id=39194732;sent-ts=1480974093323;subscriber=0;tmi-sent-ts=1480974095809;turbo=0;user-id=61485917;user-type="},"ts":1480976044}
#{"type":"msg","data":{"command":"","room":"#therunningmanz","nick":"bountydoge","target":"","body":"FeelsGoodMan Then I can finally go to sleep","tags":"badges=;color=#FFFF00;display-name=BountyDoge;emotes=;id=6d8c83c4-df20-4da1-add8-1753d4796a4a;mod=0;room-id=69824993;sent-ts=1480974092837;subscriber=0;tmi-sent-ts=1480974095838;turbo=0;user-id=51374435;user-type="},"ts":1480976044}
#{"type":"msg","data":{"command":"","room":"#generalmick","nick":"razorxrain","target":"","body":"Heyyyy back. How many wins you guys at?","tags":"badges=;color=;display-name=Razorxrain;emotes=;id=b9917fa5-8aab-4247-9d67-ce34ee99e018;mod=0;room-id=140964460;subscriber=0;tmi-sent-ts=1480974095823;turbo=0;user-id=103369369;user-type="},"ts":1480976044}
#{"type":"msg","data":{"command":"","room":"#fortunagamingtv","nick":"clon1205","target":"","body":"kad ce krenuti gejm","tags":"badges=;color=;display-name=Clon1205;emotes=;id=62d0d06e-9f86-40d7-9214-5f3329b403af;mod=0;room-id=107803559;subscriber=0;tmi-sent-ts=1480974095824;turbo=0;user-id=86308744;user-type="},"ts":1480976044}
#{"type":"msg","data":{"command":"","room":"#dermiep","nick":"erakhul","target":"","body":"das war einfach schmerzhaft","tags":"badges=;color=#0000FF;display-name=erakhul;emotes=;id=f2c000c8-af10-481d-aab0-961715e4f588;mod=0;room-id=112044050;sent-ts=1480974095902;subscriber=0;tmi-sent-ts=1480974095848;turbo=0;user-id=125159144;user-type="},"ts":1480976044}
#{"type":"msg","data":{"command":"","room":"#hastad","nick":"jack_bowln","target":"","body":"@TyrusTg sim hduasuidhasiudha Keepo","tags":"badges=;color=#0000FF;display-name=Jack_bowln;emotes=1902:30-34;id=496a6aeb-9a2e-44b7-8608-6458d01b9575;mod=0;room-id=26857029;sent-ts=1480974094330;subscriber=0;tmi-sent-ts=1480974095826;turbo=0;user-id=58301519;user-type="},"ts":1480976044}
#{"type":"msg","data":{"command":"","room":"#pukanuragan","nick":"ladand3r","target":"","body":"ФХЫЗВХВФЗХЗВЫАФЫВА","tags":"badges=;color=#FF0000;display-name=ladand3r;emotes=;id=15bc2c66-099f-4922-ae53-9288eeba8d80;mod=0;room-id=70698322;sent-ts=1480974097604;subscriber=0;tmi-sent-ts=1480974095804;turbo=0;user-id=127814310;user-type="},"ts":1480976044}
#{"type":"msg","data":{"command":"","room":"#tysegall","nick":"uran_95","target":"","body":"вы о чём? какой кот?","tags":"badges=;color=#D2691E;display-name=uran_95;emotes=;id=c9f01ec9-f371-419d-b3e8-a39ba70b6a3f;mod=0;room-id=35856714;sent-ts=1480974096291;subscriber=0;tmi-sent-ts=1480974095843;turbo=0;user-id=108611929;user-type="},"ts":1480976044}
#{"type":"msg","data":{"command":"","room":"#zer4toul","nick":"nordak21","target":"","body":"et les 2 sont compatible donc je vais accepté les 2 :)","tags":"badges=;color=#FF0000;display-name=Nordak21;emotes=1:52-53;id=ddff195a-58bc-4f09-979f-09e875b97fb6;mod=0;room-id=84982543;sent-ts=1480974093046;subscriber=0;tmi-sent-ts=1480974095846;turbo=0;user-id=79028241;user-type="},"ts":1480976044}
#{"type":"msg","data":{"command":"","room":"#alohadancetv","nick":"bio____","target":"","body":"!donate","tags":"badges=;color=#2E8B57;display-name=Bio____;emotes=;id=0093e0d8-8158-4885-9679-38f69a28e884;mod=0;room-id=46571894;sent-ts=1480974095739;subscriber=0;tmi-sent-ts=1480974095846;turbo=0;user-id=66409722;user-type="},"ts":1480976044}
#{"type":"msg","data":{"command":"","room":"#sergeantmaxlp","nick":"revlobot","target":"","body":"rumseppl has 747 Taler","tags":"badges=moderator/1;color=#1E90FF;display-name=RevloBot;emotes=;id=0f4fe9b7-2e3b-4026-96da-26c77058a1f0;mod=1;room-id=48389321;subscriber=0;tmi-sent-ts=1480974095857;turbo=0;user-id=88713356;user-type=mod"},"ts":1480976044}
#{"type":"msg","data":{"command":"","room":"#rineanime","nick":"ijrfelipe","target":"","body":"es de mex xf","tags":"badges=;color=;display-name=ijrfelipe;emotes=;id=58433ad1-88a9-416d-99a5-c37cbfbcd09a;mod=0;room-id=114958021;subscriber=0;tmi-sent-ts=1480974095858;turbo=0;user-id=131637096;user-type="},"ts":1480976044}
#{"type":"msg","data":{"command":"","room":"#germanminecraftpvp_","nick":"chuqitdown","target":"","body":"er rayt und gleich 5 zuschauer mehr","tags":"badges=;color=#FF69B4;display-name=chuqitdown;emotes=;id=2cc51c37-3cc0-4388-afd7-8f0d08925d9f;mod=0;room-id=119928927;subscriber=0;tmi-sent-ts=1480974095849;turbo=0;user-id=133526279;user-type="},"ts":1480976044}
#{"type":"msg","data":{"command":"","room":"#fenn3r","nick":"manthaknee","target":"","body":"Day jobs FeelsBadMan","tags":"badges=subscriber/0,premium/1;color=#0E8FBE;display-name=ManthaKnee;emotes=;id=f07a482f-4bea-4703-9705-682899601654;mod=0;room-id=9345718;sent-ts=1480974095684;subscriber=1;tmi-sent-ts=1480974095853;turbo=0;user-id=40301332;user-type="},"ts":1480976044}
#{"type":"msg","data":{"command":"","room":"#melonsicle","nick":"mister_miyagi_","target":"","body":"nice PJ's bro","tags":"badges=turbo/1;color=#237FA9;display-name=Mister_Miyagi_;emotes=;id=cbfc7329-57ee-4516-938f-dda219154745;mod=0;room-id=132444231;sent-ts=1480974094252;subscriber=0;tmi-sent-ts=1480974095842;turbo=1;user-id=72734129;user-type="},"ts":1480976044}
#{"type":"msg","data":{"command":"","room":"#summit1g","nick":"twitchnotify","target":"","body":"dillweedtv just subscribed!","tags":""},"ts":1480976044}
#{"type":"msg","data":{"command":"","room":"#stumptgamers","nick":"twitchnotify","target":"","body":"The_voids just subscribed with Twitch Prime!","tags":""},"ts":1480976044}
#{"type":"msg","data":{"command":"","room":"#rinnorii","nick":"twitchnotify","target":"","body":"dillweedtv just subscribed to summit1g!","tags":""},"ts":1480976044}
#{"type":"msg","data":{"command":"","room":"#blazefirer","nick":"twitchnotify","target":"","body":"dillweedtv just subscribed to summit1g!","tags":""},"ts":1480976044}
#{"type":"msg","data":{"command":"","room":"#auxilium_csgo","nick":"twitchnotify","target":"","body":"dillweedtv just subscribed to summit1g!","tags":""},"ts":1480976044}
#{"type":"msg","data":{"command":"","room":"#xdrothenerd","nick":"twitchnotify","target":"","body":"dillweedtv just subscribed to summit1g!","tags":""},"ts":1480976044}
#{"type":"msg","data":{"command":"","room":"#mentalarea","nick":"twitchnotify","target":"","body":"dillweedtv just subscribed to summit1g!","tags":""},"ts":1480976044}
#{"type":"msg","data":{"command":"","room":"#dewic","nick":"twitchnotify","target":"","body":"dillweedtv just subscribed to summit1g!","tags":""},"ts":1480976044}
#{"type":"msg","data":{"command":"","room":"#rtxx","nick":"twitchnotify","target":"","body":"dillweedtv just subscribed to summit1g!","tags":""},"ts":1480976044}
#{"type":"msg","data":{"command":"","room":"#ironmaiden333","nick":"twitchnotify","target":"","body":"dillweedtv just subscribed to summit1g!","tags":""},"ts":1480976044}
#{"type":"msg","data":{"command":"","room":"#mib709394","nick":"twitchnotify","target":"","body":"dillweedtv just subscribed to summit1g!","tags":""},"ts":1480976044}
#{"type":"msg","data":{"command":"","room":"#macromichael","nick":"twitchnotify","target":"","body":"dillweedtv just subscribed to summit1g!","tags":""},"ts":1480976044}
#{"type":"msg","data":{"command":"","room":"#ilussionistul","nick":"twitchnotify","target":"","body":"dillweedtv just subscribed to summit1g!","tags":""},"ts":1480976044}
#{"type":"msg","data":{"command":"","room":"#mrdeecoe","nick":"twitchnotify","target":"","body":"dillweedtv just subscribed to summit1g!","tags":""},"ts":1480976044}
#{"type":"msg","data":{"command":"","room":"#bluenadzz","nick":"twitchnotify","target":"","body":"dillweedtv just subscribed to summit1g!","tags":""},"ts":1480976044}
#{"type":"msg","data":{"command":"","room":"#verstrat","nick":"twitchnotify","target":"","body":"dillweedtv just subscribed to summit1g!","tags":""},"ts":1480976044}