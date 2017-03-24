# -*- coding: utf-8 -*-

from random_useful_functions import start_daemon_thread

from datetime import datetime, timedelta
import re
import urllib2
import json
import time
import Queue
import webbrowser
import logging
from unidecode import unidecode

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "KanCompDetector_site.settings")
import records.models as models
import django
django.setup()

seven_days = timedelta(days=7)
default_creation_date = datetime(1990, 1, 1, 0, 0, 0)

class SpamDetectorMain():
	class User():
		def __init__(self, current_message, pattern, parent):
			self.username = current_message.username
			self.messages = [current_message]
			self.creation_date = default_creation_date
			self.pattern = pattern
			self.parent = parent

			self.too_old = None
			self.staff_or_admin = None

		def print_caught_message(self):
			additional_info = ""
			if(self.staff_or_admin == True):
				additional_info = " (Admin/Staff)"
			print str(datetime.now().time())+" - "+"'"+self.username+"' was caught. Counter: "+str(len(self.messages))+additional_info

		def check_message(self, current_message):
			if(re.match(self.pattern["pattern"], current_message.message)):
				self.messages.append(current_message)
				return True
			else:
				alt_patterns = self.pattern.get("alt_patterns")
				if(alt_patterns != None):
					for i in alt_patterns:
						if(re.match(i, current_message.message)):
							self.messages.append(current_message)
							return True
				return False

		def check_counters(self):
			if(len(self.messages) == self.pattern["young_limit"]):
				self.get_age_and_type()
				if(self.creation_date != "Unprocessable"):
					if(self.staff_or_admin == False and self.too_old == False):
						self.confirmed_spambot()
					if(self.too_old):
						print str(datetime.now().time())+" - "+"'"+self.username+"' is too old to be a likely spambot."
			if(len(self.messages) == self.pattern["old_limit"]):
				if(self.creation_date != "Unprocessable"):
					if(self.staff_or_admin == False and self.too_old == True):
						self.confirmed_spambot()

		#Gets API data about when the account was created, and whether they're Staff/Admin.
		def get_age_and_type(self):
			response = self.parent.TwitchAPIHandlerC.get_user(self.username)
			while(not self.parent.TwitchAPIHandlerC.is_valid_response(response) or type(response) == type(0)):
				response = self.parent.TwitchAPIHandlerC.get_user(self.username)
			if(response == 422 or response == 404):
				self.creation_date = default_creation_date
			else:
				response = json.loads(response)
				self.creation_date = datetime.strptime(response["created_at"], "%Y-%m-%dT%H:%M:%SZ")
				#Determines if the account is older than 7 days.
				self.too_old = not(datetime.now() - self.creation_date <= seven_days)
				#Determines if the account is Admin/Staff/Global Mod.
				if(response.get("type", None) in ["global_mod", "admin", "staff"] or response.get("staff", None) == True):
					self.staff_or_admin = True
				else:
					self.staff_or_admin = False

		def confirmed_spambot(self):
			self.parent.caught_users[self.username] = self
			self.record()
			del self.parent.users[self.username]

			if(self.pattern["action"] == "list"):
				self.parent.output_queue.put(self)
				print str(datetime.now().time())+" - "+"'"+self.username+"' was confirmed to be a spambot. Position: "+str(self.parent.output_queue.qsize())
			elif(self.pattern["action"] == "TOS"):
				if(self.parent.MechanizedTwitchC == False):
					print "No report handler connected."
				else:
					report_list = [{"username":self.username, "category":"spam", "description":"Content: chat\nDetailed Reason: spam_bots\nIP Block: false\nSuspension: indefinite\n----------------------------------------\n\nspam bot\n\n"+self.messages[0].message}]
					self.parent.MechanizedTwitchC.report_multiple_users(report_list)
				print str(datetime.now().time())+" - "+"'"+self.username+"' was confirmed to be a spambot. Action is set to TOS and the user has been added to the queue."
			
		def record(self):
			#This line apparently prevents the 'MySQL server has gone away.' error by forcing Django to close an old connection before accessing the MySQL server, forcing it to get a new one. Ideally I'd check if the MySQL server has gone away before calling it, but I don't know how to do that yet.
			django.db.close_old_connections()
			
			user_object = models.User.objects.get_or_create(username=self.username, creation_date=self.creation_date)[0]
			user_object.save()
			regexspambot_obj = models.RegexSpambot(pattern=self.pattern["pattern"].pattern[:4999], timestamp=self.messages[0].timestamp, user=user_object) #The char limit is a shortgap fix for the truncating issue.
			regexspambot_obj.save()
			for message in self.messages:
				message_object = regexspambot_obj.messages.create(username=user_object, timestamp=message.timestamp, room=message.room, body=message.message)

	def __init__(self, parent, input_queue, apihandler=None, reporthandler=None):
		self.parent = parent
		self.input_queue = input_queue

		#Obtained via https://api.twitch.tv/kraken/chat/emoticon_images?emotesets=0
		emote_string = "(4Head|[oO](_|\.)[oO]|\>\;\(|\<\;3|\:-?(o|O)|\:-?(p|P)|\:-?[\\/]|\:-?[z|Z|\|]|\:-?\(|\:-?\)|\:-?D|\;-?(p|P)|\;-?\)|AMPEnergy|AMPEnergyCherry|AMPTropPunch|ANELE|ArgieB8|ArsonNoSexy|AsianGlow|AthenaPMS|B-?\)|BabyRage|BatChest|BCouch|BCWarrior|BibleThump|BiersDerp|BigBrother|BlargNaut|bleedPurple|BloodTrail|BORT|BrainSlug|BrokeBack|BudBlast|BuddhaBar|BudStar|ChefFrank|cmonBruh|CoolCat|CorgiDerp|DAESuppy|DansGame|DatSheffy|DBstyle|deIlluminati|DendiFace|DogFace|DOOMGuy|DoritosChip|duDudu|DxAbomb|DxCat|EagleEye|EleGiggle|FailFish|FPSMarksman|FrankerZ|FreakinStinkin|FUNgineer|FunRun|FutureMan|GingerPower|GrammarKing|HassaanChop|HassanChop|HeyGuys|HotPokket|HumbleLife|ItsBoshyTime|Jebaited|JKanStyle|JonCarnage|KAPOW|Kappa|KappaClaus|KappaPride|KappaRoss|KappaWealth|Keepo|KevinTurtle|Kippa|Kreygasm|Mau5|mcaT|MikeHogu|MingLee|MKXRaiden|MKXScorpion|MrDestructoid|MVGame|NervousMonkey|NinjaTroll|NomNom|NoNoSpot|NotATK|NotLikeThis|OhMyDog|OMGScoots|OneHand|OpieOP|OptimizePrime|OSfrog|OSkomodo|OSsloth|panicBasket|PanicVis|PartyTime|PeoplesChamp|PermaSmug|PeteZaroll|PeteZarollTie|PipeHype|PJSalt|PJSugar|PMSTwin|PogChamp|Poooound|PraiseIt|PRChase|PunchTrees|PuppeyFace|R-?\)|RaccAttack|RalpherZ|RedCoat|ResidentSleeper|riPepperonis|RitzMitz|RuleFive|SeemsGood|ShadyLulu|ShazBotstix|SmoocherZ|SMOrc|SMSkull|SoBayed|SoonerLater|SSSsss|StinkyCheese|StoneLightning|StrawBeary|SuperVinlin|SwiftRage|TBCheesePull|TBTacoLeft|TBTacoRight|TF2John|TheRinger|TheTarFu|TheThing|ThunBeast|TinyFace|TooSpicy|TriHard|TTours|twitchRaid|TwitchRPG|UleetBackup|UncleNox|UnSane|VaultBoy|VoHiYo|VoteNay|VoteYea|WholeWheat|WTRuck|WutFace|YouWHY)"

		self.spam_pattern_dicts = []
		#{"action":("list" or "TOS"), "young_limit": 2, "old_limit":10, "pattern":<compiled re pattern>}
		#vine4you
		#self.spam_pattern_dicts.append({"action":"list", "young_limit":2, "old_limit":10, "pattern":"^(you wont regret to |you must |you need to |you should |you have to |you better |you can't miss | )(open up|see|browse|look up|watch|check out|open) .*( I lol'd| I laughed so hard, I pooped a little| so funny| such funny, very joke| too funny| must see| very funny| I cannot breathe| I nearly died because of the laughing| I laughed so hard I pooped a little| better than games| )( haha| rofl| xdxd| xd| :d:d| :d| x'd| lol| )$"})
		#vine4you
		#self.spam_pattern_dicts.append({"action":"list", "young_limit":2, "old_limit":10, "pattern":"(holy|omg|omfg|no way,|wow|oh my god|jesus|wtf|whta the hell!|wth|lmfao|woah|what the|jeez).*\w{2,25}.*(you.*see this|how does this exist\?|its op as hell|crazy|this is amazing|its mental|you seen|anyone send you this).*((http|https)\:\/\/www\.youtube\.com\/watch\?|\*\*\*).*(someone.*figured it out(\.\.\.|)|patched.*|everyone was talking about it on reddit|pretty nuts|cant believe it\.\.\. insanity|kinda crazy|reddit went (nuts|crazy) about it|how (did|do) they (do|done) this\?|insanely cool|riot will have to stop it soon i guess| $)"})
		#Goldmine.
		#self.spam_pattern_dicts.append({"action":"list", "young_limit":2, "old_limit":10, "pattern":"^(Gamers! If You Haven't Checked Out G2A's Goldmine Program You Can Now :\)|Gamers! Like Twitch Streamers You Can Earn Money Telling Friends about Games :\)|Gamers! Like Youtubers\/Streamers You Can Earn With G2A's Goldmine Program :\)|Like Streamers You Can Tell your Friends\/Followers About Gaming Deals & Earn Money! |Gaming Fans! Like PewDiePie You Can Earn Money Sharing Games With Friends\/Followers :\)|Like PewDiePie You Can Share Gaming Deals With Friends & Earn Money :\)|Now Everyone Can Join G2A & Earn Money Informing Friends about Game Deals\/Offers!|EARN Gaming!Gamers GoldMine!|EARN Money Like Streamers!|Earn Like PEWDIEPIE!|You Can Share Gaming Deals with your Friends\/Followers & Make Money Doing So :\)|Like Youtubers & Streamers, You Can Make Money By Sharing Games With Friends!|Inform Your Friends \& Followers about Gaming Deals & Earn While Doing So!|Everyone Can Earn Money Informing Friends about Game Offers!|Make Money Sharing Games!|Share Games with Friends & Make Money Doin So :\)|Inform Friends about Gaming Deals & Earn!|Like Streamers You Can Tell your Friends\/Followers About Gaming Deals & Earn Money!) +.*\..*$"})
		#Goldmine. Causes occasional false positives, but generally never for more than 1 message at a time.
		#self.spam_pattern_dicts.append({"action":"TOS", "young_limit":10, "old_limit":10, "pattern":"^(why )?(don'?t )?(you |ya' )?(should )?(put a banner(ino)? for |use |be (one of the |a )).*(\(\))?(kinda (awesome|nice) (freebie cash|income) for (streamers|streamerinos) |i meant G2A's shit, just in case, )?(lol |xD |lmao )?(\(\))?(https?:\/\/)?([-a-zA-Z0-9@:%_\\+~#=]+\.)+([a-z]{2,6})([-a-zA-Z0-9@:%_\\+.~#?&//=]*)(\(\))?( in case you don't know what it is (lol|xD|lmao))?(\(\))?$", "alt_patterns":["^(ayy|ayy lmao|Kappa|Kapparino|lol|rekt|rekterino|sandstorm|sup bro\?|sup\?)$", "^"+emote_string+"$"]})
		#Goldmine.
		#self.spam_pattern_dicts.append({"action":"TOS", "young_limit":10, "old_limit":10, "pattern":"^(why don't you put a banner for Goldmine\? you miss out a lot of income lol \((https?:\/\/)?([-a-zA-Z0-9@:%_\\+~#=]+\.)+([a-z]{2,6})([-a-zA-Z0-9@:%_\\+.~#?&//=]*)\)|Hi, if you are interrested in making money while playing games, check out g2a's new project and sign up through this link: https://www\.g2a\.com/r/moneyforgame)$", "alt_patterns":["^(ayy|ayy lmao|Kappa|Kapparino|lol|rekt|rekterino|sandstorm|sup bro\?|sup\?|ALLAHU AKBAR|Gib us Hafu nudes Kappa)$", "^"+emote_string+"$"]})
		#NatusVincere
		#self.spam_pattern_dicts.append({"action":"TOS", "young_limit":10, "old_limit":10, "pattern":"^(try out Na`Vi Dendi pudge minigame\!\! Really good game\! natusvincere\.co\.nf|did anyone play Na.Vi meathook trainer\?\?( I can't understand how to upgrade my hook| I won a DC hook, but how can I get it\?\?) :\( GUYS help PLS natusvincere\.co\.nf( NOT A SPAM|\.)?\s*)$", "alt_patterns":[]})
		#Asian guys poll: http://strawpoll.me/5746603
		#j.mp
		self.spam_pattern_dicts.append({"action":"TOS", "young_limit":10, "old_limit":10, "pattern":"^[\w\d\-]+\.[\w\d\-]+\/(image|screenshot|img|screen|tif|sreenshot|shortcut|Iamge|Screean|imag)_?\d{1,10}(\.\w+)?( [\S]+)$", "alt_patterns":[]})
		#self.spam_pattern_dicts.append({"action":"TOS", "young_limit":10, "old_limit":10, "pattern":"^(I want it|I win cool item|OMG steam update|steam upd[ae]te\.+|thats incredible|this is something amazing|(Well, )?why I so lucky|who can do (that|this guys)|Anyone else seen that|Are you wanted (this|that)|check(ed)? (that|this)|I am the master|just look at it|Laughter and tears|Learn kids|LOL|that incredible|why I so lucky|I wining cool items|I want) (https?:\/\/)?([-a-zA-Z0-9@:%_\\+~#=]+\.)+([a-z]{2,6})([-a-zA-Z0-9@:%_\\+.~#?&//=]*) (:D( :\))?|D:|nice game bro TTours|thanks( :D)?|<3|No way|xD|Kapp|why\? WutFace|nice girls HeyGuys AthenaPMS PMSTwin|I lucky bastard|("+emote_string+" ?)+)$", "alt_patterns":["^(https?://(ark\.intel\.com|www\.apple\.com|www\.microsoftstore\.com|mini\.webmoney\.ru|twitter\.com|www\.google\.com|www\.youtube\.com)/?|\d+)$"]})
		#TwitchWarwick. VERY TEMPORARY, LIKELY HAS FALSE POSITIVES.
		#self.spam_pattern_dicts.append({"action":"TOS", "young_limit":10, "old_limit":10, "pattern":"^\w+( [\,\-\*\+\!\=\#\_\^\.\)\(\&\>\<\\\/\@\|\%\$]{1,3})? (https?:\/\/)?([-a-zA-Z0-9@:%_\\+~#=]+\.)+([a-z]{2,6})([-a-zA-Z0-9@:%_\\+.~#?&//=]*)$", "alt_patterns":[]})
		#ifyouplaycgo - New type?
		#self.spam_pattern_dicts.append({"action":"TOS", "young_limit":10, "old_limit":10, "pattern":"^(free sk+in+s |free cs:?go sk+in+s |this free sk+ins+ |cs:?go sk+in+s |this made my day |cs:?go giveaway |Giveaway Cs:?go )?(syn\.su/[\w\d]+|ool\.io/[\w\d]+) ?(if u playi+ng cs:?go|if u (buddy )?(play|likes) cs:?go|if u buddy play+ cs:?go|cs:?go|For cs:?go players)?\.*$", "alt_patterns":[]})
		#GG
		#self.spam_pattern_dicts.append({"action":"TOS", "young_limit":10, "old_limit":10, "pattern":"^(<3 a bit of fantasy <3|<3 some amazing stuff <3|A bit of fantasy <3|A bit of my dream <3|After you|and so i reached the summit|any more question\?|anything but this|as I understand it AIUI|be back later BBL|believe it or not BION|bring your own beer BYOB|cmon dude you can t prove it DansGame|come and get it|come back and say ho|DansGame jesus this teammates|DansGame make it fast, dude|focken magic <3|Follow this link, you'll be|(fuck|\*\*\*) this (shit|\*\*\*) im out SeemsGood|gaben showed me the truth|haha you better learn some KappaRoss|Heh,that happened to me|HeyGuys join our squad Kappa|How interesting\.\.\.|I completely succeed|i love that smile <3|I VE JUST DONE IT|is a dildo in his hand\?|is that a threat\?|is this real WutFace|It doesn't matter\)\)\)|IT FINALLY HAPPENED|Kappa focking dumbs again|keep that in mind kinds|lest roll Kappa|lmao Kappa|LOOKING this inventory|made my day|NASA scientists have found the woman on Mars|Nice gameplay dude Kappa|no point, really|Not again SwiftRage SwiftRage|not this (shit|\*\*\*) again Kappa|nothing more to teach|Oh lol, normal dubbing\.|Oh my God, it's just hard|omg you again WutFace|only 4 tru|Preorders drive more sadness than anticipation \- Adobe|pretty much made my day|push the tempo|rip pvp \-|Scopely hires chief people officer Jessica Neal|so that`s how its done|stop ruin my games SwiftRage|such simple minds|tell ur friends about this (shit|\*\*\*)|Thank you anyway|that meme is so danky Kappa|that seems to be new meta|the truth has been spoken|TheKing with the lights out FunRun|this makes me mad SwiftRage SwiftRage|This way, please|ty gaben <3|Where is this world coming to\?|Where the galactic police to catch the idiots\?|why I so lucky|why s he even trying\?|xD my (fucking|\*\*\*) g spot|You arent smart enough to play this|you kiddin me\?\?) (https?:\/\/)?([-a-zA-Z0-9@:%_\\+~#=]+\.)+([a-z]{2,6})([-a-zA-Z0-9@:%_\\+.~#?&//=]*)( <3| Face| here s how u do it| I would be happy if the boys do the job\.| is obligatory foe you| its less dangerous| KAPOW gamurz| obligatory foe you| stunned| swedes made my day| what what| xD)( "+emote_string+")*$", "alt_patterns":[]})
		#VaultBoy spam.
		#self.spam_pattern_dicts.append({"action":"TOS", "young_limit":10, "old_limit":10, "pattern":"^Hello [\w\d_]{1,40} You can download my new config \(Incluyed resolution(, video)?, cfg, viewmodels, etc\!\) here: (https?:\/\/)?([-a-zA-Z0-9@:%_\\+~#=]+\.)+([a-z]{2,6})([-a-zA-Z0-9@:%_\\+.~#?&//=]*)$", "alt_patterns":[]})
		#Teamspeak spam.
		#self.spam_pattern_dicts.append({"action":"TOS", "young_limit":10, "old_limit":10, "pattern":"^(LOL|FAIL|Ahaha) streamer showed your (teamspeak_\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}|\*\*\*)$", "alt_patterns":[]})
		#CSGOSkins
		#self.spam_pattern_dicts.append({"action":"TOS", "young_limit":10, "old_limit":10, "pattern":"^CS:GO (skin|\*\*\*) for watching ads (.*skin.*4.*ads.*|(https?:\/\/)?([-a-zA-Z0-9@:%_\\+~#=]+\.)+([a-z]{2,6})([-a-zA-Z0-9@:%_\\+.~#?&//=]*))$", "alt_patterns":[]})
		#self.spam_pattern_dicts.append({"action":"TOS", "young_limit":10, "old_limit":10, "pattern":"^.ACTION win (AK-47 Vulcan|AWP Asiimov|Bayonet Tiger Tooth|Karambit Damascus Steel|M4A4 Poseidon|M9 Bayonet Fade) on the site op-skins org.$", "alt_patterns":[]})
		#CSGOegg
		#self.spam_pattern_dicts.append({"action":"TOS", "young_limit":3, "old_limit":5, "pattern":"^.*((https?://)?goo\.gl/(99l9VN|YQADwg|m5ffh4|BfGK7N|NgYBfE|YYKRTZ|WecM5s|B7Wkfv|bk0ykA|yk2gAU|H8JcKR|OHFpWq|Qu0wzP|UPh1rU|rLgP8T|4bHX8f|6c1uYv|bTLUn8|TScW5C|KB9KFD|jTt0eb|LD1Wkc|Xj55gq|Aa0CyV|X4DWo9|baWdw1|wVte70|U53OCd|prklYS|Wy2nn4|3L63Tf|6Zn0Kp|ROJpY9|zu6Okd)|(https:\/\/)?youtu\.be\/(\-yWcbj2Ej7I|GZYgAZahCyI)).*$", "alt_patterns":[]})
		#Russian spambots.
		#self.spam_pattern_dicts.append({"action":"TOS", "young_limit":3, "old_limit":5, "pattern":u"^(Смотри и богатей Kreygasm Kreygasm https://goo\.gl/wCT9XM|Вот это поворот HeyGuys http://bit\.ly/1M6uZlQ|Найди, посмотри и стань богаче, введи на ютубе \"Махинация века 2015\" Kreygasm|Ты такого еще точно не видел !! http://bit\.ly/1PqD60k|Вот это капец ахах введи на ютубе \"Новая фича стим\" Kreygasm|3аpaбaтывaй на проекте hfix\. ru и зарабатывaй за день от 1500 рублей за простые дeйcтвия: cтaвь лайки, пиши коммeнтарии, вступай в паблики\.)$", "alt_patterns":[]})
		#Navi Teamspeak spam.
		#self.spam_pattern_dicts.append({"action":"TOS", "young_limit":3, "old_limit":5, "pattern":"^(Dude Free Distribution Skins , go TeamSpeak NaVi|Free Distribution Skins , go TeamSpeak NaVi|Man Free Distribution Skins , go TeamSpeak NaVi|Steam Free give - Key , Game , Items , Skins , Knife , go|Hi I want to trade my new knife with you Check my offer at screenshot) - ((\d+|\.| )+|(https?:\/\/)?([-a-zA-Z0-9@:%_\\+~#=]+\.)+([a-z]{2,6})([-a-zA-Z0-9@:%_\\+.~#?&//=]*))\s*$", "alt_patterns":["^{Hi$"]})
		#self.spam_pattern_dicts.append({"action":"TOS", "young_limit":5, "old_limit":5, "pattern":"^(notvirus\.click/image\d+\.png|printcsr\.pw/bs3xx9k|prtscr.click/image\d+\.png)\.?$", "alt_patterns":[]})
		#Smileyface
		self.spam_pattern_dicts.append({"action":"TOS", "young_limit":5, "old_limit":5, "pattern":"^(3cm\.kz|3utilities\.com|55555\.ru|5z8\.info|8b\.kz|\w+\.ga|\w+\.ml|\w+\.tk|adres\.club|bit\.ly|bitb\.ee|bitly\.com|bounceme\.net|c2y\.me|ddns\.net|elek\.ru|exci\.se|fw\.gg|gg\.gg|goo\.gl(?!/forms)|gotdns\.ch|gotv\.co|gu\.ma|heh\.xyz|hoc\.xyz|hopto\.org|hria\.org|http:gg\.gg|ibvu\.gu\.ma|imx\.tw|is\.gd|iurl\.guru|j\.mp|kos\.su|link\.limo|ly2\.ru|make\.my|mbcurl\.me|miu\.tw|mni\.su|mobmas\.rus|myvnc\.com|noip\.com|oi\.ma|ool\.io|otset\.ee|ow\.ly|redirectme\.net|servebeer\.com|serveblog\.net|skin4ads\.\w+|sn\.im|snip\.bz|surfe\.be|sytes\.net|t\.co|tiny\.cc|tiny\.ph|tiny\.pl|tllg\.net|tr\.im|ur\.qa|url\.ie|urlbox\.eu|vzturl\.com|w\.atch\.me|webhop\.me|wte\.su|youl\.ink|shr\.ooo)/[\w\d]+ (lol|:\)|lol2|xD)$", "alt_patterns":[]})
		#Oldtimer.
		#self.spam_pattern_dicts.append({"action":"TOS", "young_limit":5, "old_limit":5, "pattern":"^(<3( majestic)?|a bit of fantasy \<3|always makes me smile|and so i reached the summit|another one Kreygasm|another unnecessary nonsense|any more questions\?|Anyone else seen that\??\)?|anything but this|at last! i've dont it!|bastard|beautiful girl, good day|best girl ever|best player ever|boys, let's get acquainted\. i'm not a fake, that's my photo|btches aint sh1t Kappa|bye bye swedistan|camel caramel toe Kappa|can u do this\? omg|can't expect this issue|cant touch me|chicks always fall for it|come here coward DansGame|cringe is real 4Head|curved on my sis ss KappaRoss|dark and scary Kappa|dat grill Kreygasm|deadpool penis|did you see that\? not for children, pregnant women and the faint of heart\.|dis nutz lmao xD|do u know this pornstar\?|don'?t disturb( me)?|don'?t touch|dont try this at home kids EleGiggle|dont understand( u)?|dummy girl xD <3|EleGiggle hold my fluete EleGiggle|even if it looks good FailFish|every time i see i cry|explain to someone what's she doing|ez skins cougarhunt|Failed with a date but EleGiggle|fap isnt always good 4Head|fast attack|fckin hangover :\(|for real, guys\?|forever alone :\(|forsenGasm she made it|fukbois aint do this|game over|get me to the fouckin moon 4Head|get some drink nerds 4Head|get stomped biiiiiiitch 4Head|get to the oil Kappa|girl for the first time play|girl knows her business|girl knows what to dogirl\-|god bless gaben elegiggle|golden bo0ty 4Head|gonna get her <3|good for you|good pump i ve got there 4Head|greetings, traveler|grill made my day|guys do not get bored\. write to me in pm\. here are my photos|guys please send my friends private photo of my ex|haha dont worry kids <3 heres grill Kappa|hardly a challenge 4Head|have to deal with her sometimes EleGiggle|heh,that happened to me( xd)?|hello boys, i am looking for in (england|germany|usa), here are my photos|help me with this|hey girls and boys\. see how i lost weight by the summer|heyguys hallo jungs\. bewerten sie meine fotos|heyguys my name is maria|heyguys my name is maria\. i need a guy from germany who can stay|hi boyshi boys\. i am looking for a man from 19 to 24 years\. here are my photos|hi guys\. i am looking for someone to talk to on skype|hi guys\. i want to love, here are my photos|hi, i've got a friend took a photo 18\+|hi,see photo, who like in private plz|holy moly those kids FailFish|honey i ll be late 4Head Kappa|hot babes here|how is it even possible\?|how is this possible\?|how to enlarge the penis with herb|huge pvp change|i am a handsome boy from germany|i cry every time( i see)?|i found it hard|i like this girl, the best one|i like this woman, she's hot|i told u|i tried!|i ve just done it|id call that sweet chicks|in grill we trust|in the north of europe killed chupacabra\. photos of dead females|incredibly hot Kreygasm|is a dildo in her hand\?|is she hot HeyGuys|is that something\?|isnt she pretty <3|it cant be more adorable <3 HeyGuys|it finally happened|it'?s a trap|it's done!|its been a while|its done|ive just met her KappaRoss|jagex removing deadman mode|just girly trick Kappa|just look at it|just plebby thing huh OppieOp|kapow new game of thrones|keeping her close Kappa arent we Kreygasm|King met his queen dildo|Kreygasm cousin gachi Kreygasm|ku ku, let's get acquainted , my photos here|laughter and tears|learn kids|let her just try it <3|let's get acquainted boys|let's golook at this one|lets go|look what i've done|look\. i'm not fat\?|looking for a guy ,here is my picture, private messages pliz|looking for love, love to play, here are photos( , anyone interested private message)?|m'lady Kappa|made my daymy favorite bug from recent update|marathon 24 hours|minions your master needs help 4Head|my dreams|my little sunny <3|my medicine :\( <3|nailed it|naked emma watson\. cutting out a scene from the movie \"colonia\"|naughty grill Kreygasm|never give up|new skill( in rs)?|nice 34 keepo|nice boss|nice place for\.\.\.|nope nope nope WutFace|oh baby shes got it( oh my)?|oh dont mind my gf guys EleGiggle|oh my|oh noes not again|oh shiiii 4Head|oh well kappa|oi dont wanna ruin your nonfap KappaRoss|penis with herbs|pls go back|pls wait|really not bad|really( guys)? WutFace|rekt in pepperonni 4Head|rip g\.e( \-)?|rip grand exchange \-|rip pvprip rs3\-|rip wildy \-|rub you nips like this grill Kappa|scared me to death|schoolgirl missing :0 4Head|she had been doing great 4Head|she is so tasty <3|shot from cutting out the sex scenes of emma watson and daniel bruhl, from the film \"colonia\"|show you dare\?|soda n popz 4Head|sodipop girls EleGiggle|some girl from tx KappaRoss|some hot stuff inthere|somehow I reached it|stupid system!!!|such curious( babes)?!?|such fascinating!|such simple minds|that cuttie ;D|that escalated quickly|that seems to be new meta|that was unexpectable!|that was unexpected!|that's beautiful|that's how i('ve)? do(n|v)e it!?|that's how we roll|that's my girl|that's what i'm talking about|that('|`)s what i call? chemistry|the best girl i've ever seen|the meme pwer 4Head|this baby|this girl knows her business|this girl made my day|this girl not know|this girl tasted like corn 4Head|this hips are pretty hop KappaRoss|this is a nice day|this moments cougarhunt|time to prove myself at papa johns KappaPride|took so much care of her FeelsBadMan|u gotta watch and learn|u have a problem, i dont|unstoppable|waifu destroys everyting DansGame|watch with a girl i met at twitchwhat i've done\?!|what a bo0tie 4Head|what a sweetie <3|what if she drills me out|what is it!\?|what is she takes in a hand\?|what many remember about her\?\)|what this girl doing|what was that WutFace|what's happen with this achievement|what's it|whats with ur face\?|whats your name|who did that\? can u tell\?|who have problem|whoaa perfect shape <3|why don't ya monetize yo channel with rektmine\? lmao why hes even trying\?|why i so lucky\?\)\)|why is she always so widely open mouth\?\?\?|why s he even trying\?|win of my life|woopsie <3|would you imagine the same girl\? then push|wow this dude just ate my pizza :D|wtf is she WutFace|WutFace what was that|you are welcome plebs) (https?:\/\/)?([-a-zA-Z0-9@:%_\\+~#=]+\.)+([a-z]{2,6})([-a-zA-Z0-9@:%_\\+.~#?&//=]*)( (, nur 18\+|18\+ only|18\+, private messages|4head|:\)|d:|dogface|elegiggle|failfis|heyguys|how?|kapow|kappa|lol|look, we can meet ,private messages|minglee|omg|only 18\+|seemsgood|that`s unfortunate|wutface)|(,|, anyone interested private message|\)))?$", "alt_patterns":[]})
		#Cometome
		#self.spam_pattern_dicts.append({"action":"TOS", "young_limit":5, "old_limit":5, "pattern":"^(cometome\.gq (4Head|HeyGuys|Kreygasm|SwiftRage)|HeyGuys cometome\.gq( HeyGuys)?|Kreygasm cometome\.gq Kreygasm|Sponsored link (cometome\.gq Kappa|Kappa cometome\.gq))$", "alt_patterns":[]})
		#self.spam_pattern_dicts.append({"action":"TOS", "young_limit":5, "old_limit":5, "pattern":"^Enjoy a good game on itgood zone [^\s]+ in great battles$", "alt_patterns":[]})
		#self.spam_pattern_dicts.append({"action":"TOS", "young_limit":1, "old_limit":5, "pattern":"^Get up to 450 more viewers RIGHT NOW by using https\://streambot\.com/ - Start gaining popularity immediately\!$", "alt_patterns":[]})
		#self.spam_pattern_dicts.append({"action":"TOS", "young_limit":2, "old_limit":2, "pattern":"^(just google streambot m8|i like your stream, why not try streambot though)$", "alt_patterns":["^lol yeah m8 Kappa$"]})
		#sexyladys
		self.spam_pattern_dicts.append({"action":"TOS", "young_limit":5, "old_limit":5, "pattern":"^.*((FU.K|\*\*\*) MY (ASS|\*\*\*)(,LOOK)? MI SITE ON PAGE.?|(FUCK|\*\*\*) ME BOYS,(\S\S\S)? IF WAN\S?N\S?A SEX,LOOKING SI\S?TE|(MY )+BES\S( \S\S)? S\S{1,3}X*\?*( FOTO AND)? VIDEO( \S\S)? ON SI\SE(\S\S)?( IN PROFILE|\. FREE REGIS\SRA\SION)|BOYS! WHERE.? AR. YOU\? COME TO (FUCK.?|\*\*\*) ME TODAY, LOOK SITE|BOYS\.\.\.COME TO FUCK ME TODAY\.\.\.LOOK PAGE|C.ME TO (FUCK\S?|\*\*\*) ME(fdd|\S)?, MY (ASS|\*\*\*) WANT(\S\S)? YOU! LOOK SITE|COME TO MY PAGE\.LOOK SITE|Come( \S\S)? to ME BO+YS! IF YOU WANNA SEX(\S\S)?! LO.Ks? MY SITE ON PAGE|COMEs? TO (FUCKs?|\*\*\*) ME(fdd)? B\S{1,3}YS\S?!(trt)? WAITING ON MY SITE ON PAGE|DO YOU W(A|\S\S)NNA HARD SE\S+\? I M WAITING YOU ON SITE|DO YOU WA\S?\S?NNA HA.{1,3}D SE\S{1,4} TODAY\?\? LO.K MY SITE|DO YOU WANNA HARD (SEX+|\*\*\*)( \S\S)? TODAY\?\? LOOK(\S\S)? MY SITE|DO YOU WANT HARDs? AND HOT SEX\?\?\? LOOK MY SITE ON PAGE|DO YOU( \S\S)? WANT SEXx?\? CO+MEs? TO MY SITE|GOING( \S\S)? TO MY SITE( \S\S)? ON P\S{1,3}GE, I WANT SE\S?X\S*|GUYS!! WHO WANTS TO (FUCK|\*\*\*) MY (ASS|\*\*\*)\?\?\? LOOK MY PAGE AND SITE|GUYS!!! I NEEDs? S+E+X+!!! LOOKs? MY SITE ON PROFILEs?!|GUYS\.\.\.MY (PUSSY|\*\*\*) WANT HARD SEX!! LOOK SITE ON PAGE|HELLO GUYS!! LO+K MY PAGE AND SITE IF WANNA s?SEX(\S\S)? WITH ME!!|HELLO!! DO YOU WA+N+A+( hth)? S\S*X+\S*\? LOOK MY SITE\)\)\)|HELLO( \S\S)? BOYSx?! I WAN+A SE(\S\S)?X! LOOKs? MY SITE ON PAGE|HI BOYS!! COME TO MY PROFILE! LOOK SITE I WAANNNA HARD SEX!|HUY GUYS! I WANT SU\SK\S? YOUR (PENIS\S?|\*\*\*), LOOKING?(\S\S)? MY SITE ON PAGE|I WANT BOYS TODAY! LOOKING MY SITE ON PAGE|I WANT GOOD BOYS, WAITING ON SITE, LOOK PROFILE|I WANT HARDs? SEX+! LOOKs? \SY PAGE AND WRITEs? ME ON SITE\.?|i want sex, and you\? L[0o]+k+ my page,( \S\S)? write me on site|I WANT TO FIND TO MYSELF THE YOUNG GUY FOR SEX WITHOUT LIABILITIES \(MY LOGIN - SCARLET FLOWER\)|I WANT TO SUCK[sd]? (DICx?K|\*\*\*)! WRITEs? \SE ON MY SITE|LOOK MY PA\S?GE, COME TO\S* SITE, MY (PUSSY|\*\*\*) WNAT SE\S*X|LOOK MY SITE ON PRO\S?FILE\S?,\S* IF WANNAe? HARD SEXxx TODAY!|LOOK PAGE\S? A\S?ND SITE\S* IF WA.?NTS* SEX\S*|MY B\SDY WA\S{0,3}NTS(\S\S)? S\S+X+! COM\S?E\S? TO ME ON SITE|MY BEST PORNOVIDEO(\S\S)? ON SITE\. LOOK PAGE|S.W M. (PUSSY?.?.?|\*\*\*) IN MY SITE! LOOK.? PROFILE NOW|WANT TO MEET ME\? L\S+K SITE.? ON PROFILE|Who WANTS SEXx?\?\? LOOK MY PAGE|YOU WANT HARDs AND HOT SEXx\?\?\? LOOK MY SITE ON PAGE|YOU WANT THE GIRL FOR THE EVENING\? FREE REGISTRATION|YOU WANTS I WILL SUCK OFF FREE OF CHARGE\? FREE REGISTRATION \(MY LOGIN - THE FIERY MOON\)|YOU WANTS WE WILL COMMUNICATE ON A WEBKAM\? AND IF I AM NAKED\?\) FIND ME HERE|SEX\S\S HERE)( |\.| . )(https?:\/\/)?([-a-zA-Z0-9@:%_\\+~#=]+\.)+( ?[a-z]{2,6})([-a-zA-Z0-9@:%_\\+.~#?&//=]*).*$", "alt_patterns":[]})
		self.spam_pattern_dicts.append({"action":"TOS", "young_limit":5, "old_limit":5, "pattern":"^(https?:\/\/)?([-a-zA-Z0-9@:%_\\+~#=]+\.)+([a-z]{2,6})([-a-zA-Z0-9@:%_\\+.~#?&//=]*)( (((ha)+h? |omg |LOL )?((that|this)( sick| cute)? |best )(g(i?r|ri)l+[sz]?|1v\d)( tho+| cute)?|((ha)+h? )(that )?made my day|haha girl[s$] over \$\$\$\$|jebany|LOL( this girl)?|omg 1v2 thooo|omg best of 2k16|omg shes so (cute+|nice)|perfect 10|this( twitch)? (girl|gril+)( wtf)?|wha+t ps 5\?+|wtf|xD+( this grill)?|l+o+l+|(hah?)+))+( (XD+|:P+|D+|o\.O|8>|omg|LMAO|LOLZ?)( ?\\?| ?'?))+$", "alt_patterns":["lol"]})
		self.spam_pattern_dicts.append({"action":"TOS", "young_limit":20, "old_limit":20, "pattern":"^http://ow\.ly/[\w\d]+$", "alt_patterns":["^(l+o+l+|wtf|wfsd|no+|monster|x+D+|\?|(ha)+)$"]})
		self.spam_pattern_dicts.append({"action":"TOS", "young_limit":5, "old_limit":5, "pattern":"^(Sponsored link )?("+emote_string+" )?((kappaGame|kappaPride)\.\w{2}|\S+\.tk)( "+emote_string+")?$", "alt_patterns":["^(("+emote_string+" ?)+|This game NotLikeThis)$"]})
		self.spam_pattern_dicts.append({"action":"TOS", "young_limit":5, "old_limit":5, "pattern":"^ıf you have 80 gold quest whisper me$", "alt_patterns":[]})
		#self.spam_pattern_dicts.append({"action":"TOS", "young_limit":10, "old_limit":10, "pattern":"^.*\S+\.(stream|vodka)/(image|screenshot|img|screen|tif|sreenshot|shortcut|Iamge|Screean|imag)_?\d{1,10}.*$", "alt_patterns":[]})
		


		for i in range(0, len(self.spam_pattern_dicts)):
			self.spam_pattern_dicts[i]["pattern"] = re.compile(self.spam_pattern_dicts[i]["pattern"], re.IGNORECASE)
			if(self.spam_pattern_dicts[i].get("alt_patterns") != None):
				for i2 in range(0, len(self.spam_pattern_dicts[i]["alt_patterns"])):
					self.spam_pattern_dicts[i]["alt_patterns"][i2] = re.compile(self.spam_pattern_dicts[i]["alt_patterns"][i2], re.IGNORECASE)

		self.users = {}
		self.caught_users = {}

		self.output_queue = Queue.Queue()
		self.last_message = datetime(1990, 1, 1)

		if(apihandler == None):
			from TwitchAPIHandler import TwitchAPIHandler
			self.TwitchAPIHandlerC = TwitchAPIHandler(20)
		else:
			self.TwitchAPIHandlerC = apihandler

		if(reporthandler == None):
			self.MechanizedTwitchC = False
		else:
			self.MechanizedTwitchC = reporthandler

	def parse_input_queue(self):
		while(True):
			batch = self.input_queue.get()
			for current_message in batch.messages:
				self.last_message = max(self.last_message, current_message.timestamp)
				if(current_message.username not in self.caught_users and current_message.username != current_message.room):
					if(current_message.username in self.users):
						if(self.users[current_message.username].check_message(current_message)):
							self.users[current_message.username].print_caught_message()
							self.users[current_message.username].check_counters()
						else:
							del self.users[current_message.username]
							print str(datetime.now().time())+" - '"+current_message.username+"' was cleared from suspicion with message:\n"+unidecode(current_message.message).encode('ascii')
					else:
						for i in range(0, len(self.spam_pattern_dicts)):
							if(re.match(self.spam_pattern_dicts[i]["pattern"], current_message.message)):
								self.users[current_message.username] = self.User(current_message, self.spam_pattern_dicts[i], self)
								self.users[current_message.username].print_caught_message()
								self.users[current_message.username].check_counters()

	def review_output(self, number):
		for i in range(0, number):
			if(self.output_queue.empty()):
				print "Spam bot output queue is empty."
				break
			user = self.output_queue.get()
			self.output_queue.task_done()
			url = "https://twitch-chatlogs.rootonline.de/?room=&username={0}&message=&table={1}_{2}_{3}".format(user.username, user.messages[0].timestamp.year, user.messages[0].timestamp.month, user.messages[0].timestamp.day)
			#webbrowser.open(url, new=2) #Cannot open webbrowsers in Ubuntu on server.
			print url #Printing the URL's instead for pasting and opening somewhere, or something.
		else:
			print str(self.output_queue.qsize())+" links left in output queue."