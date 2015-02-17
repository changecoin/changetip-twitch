import irc.bot
from irc.bot import IRCDict, Channel
import os
import threading
import Queue
from TwitchChangeTipBot import TwitchChangeTipBot
import re
import logging
import requests

logger = logging.getLogger(__name__)
logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', filename='twitch.log', level=logging.INFO)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
logging.getLogger('').addHandler(console)

class TwitchIRCBot(irc.bot.SingleServerIRCBot):
    def __init__(self, botname, server, port=6667):

        access_token = "oauth:"+os.getenv("TWITCH_ACCESS_TOKEN", "fake_access_token")
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port, access_token)], botname, botname)

        # Bot username for reference
        self.botname = botname

        # Changetip set up
        self.TipBot = TwitchChangeTipBot()

        # Channels set up
        self.channels = IRCDict()
        self.channel_join_queue = Queue.Queue()

        # Messages set up
        self.message_send_queue = {
            "high": Queue.Queue(),
            "medium": Queue.Queue(),
            "low": Queue.Queue()
        }
        self.last_message = ""

        logging.info('Bot initialized.')

    def on_welcome(self, serv, event):
        logging.info('Connected to Twitch.tv IRC.')
        # Start channel joining thread
        threading.Thread(target=self.channel_joiner, args=(serv,)).start()
        # Load channel list from Changetip
        threading.Thread(target=self.load_user_list, args=(0,)).start()
        # Start message sending thread
        threading.Thread(target=self.message_sender, args=(serv,)).start()
        # Watch queue size and make sure it does not grow to large, log it if it does
        threading.Timer(300.0, self.monitor_message_queue_size).start()

    def on_pubmsg(self, serv, event):
        message = ''.join(event.arguments).strip()
        author = event.source.nick
        channel = event.target
        # Set default receiver to the channel
        receiver = channel.replace("#", "")

        if message.lower().startswith('!changetip '):
            logging.info(channel+" "+author+": "+message)
            # Check if the message contains a receiver, if not then assume it is for the channel owner
            pattern = re.compile("(?<=^|(?<=[^a-zA-Z0-9-_\.]))@([A-Za-z]+[A-Za-z0-9]+)")
            tipped = re.findall(pattern, message)

            # TODO: Make this less confusing
            if len(tipped) == 0:
                threading.Thread(target=self.changetip_sender, args=(channel, author, receiver, message[11:])).start()
            elif len(tipped) == 1:
                tipped_user = tipped[0].lower()
                if tipped_user in self.channels[channel].users() or tipped_user == receiver or "#"+tipped_user in self.channels:
                    receiver = tipped_user
                    threading.Thread(target=self.changetip_sender, args=(channel, author, receiver, message[11:])).start()
                else:
                    # If can't find user, check if the twitch account at least exists using the twitch api
                    if self.is_twitch_user(tipped_user):
                        receiver = tipped_user
                        threading.Thread(target=self.changetip_sender, args=(channel, author, receiver, message[11:])).start()
                    else:
                        self.message_send_queue["low"].put((channel, "@%s That user doesn't exist." % author.capitalize()))
            else:
                self.message_send_queue["low"].put((channel, "@%s Too many recipients in your message." % author.capitalize()))

    # Thread for sending and receiving data from ChangeTip
    def changetip_sender(self, channel, sender, receiver, message):
        # Submit a tip
        tip_data = {
            "sender": "%s" % sender,
            "receiver": "%s" % receiver,
            "message": message,
            "context_uid": self.TipBot.unique_id(channel+" "+sender+": "+message),
            "meta": {}
        }
        response = self.TipBot.send_tip(**tip_data)
        out = ""
        if response.get("error_code") == "invalid_sender":
            out = "@%s To send your first tip, login with your Twitch.tv account on ChangeTip: %s" % (sender.capitalize(), self.TipBot.info_url)
            self.message_send_queue["low"].put((channel, out))
        elif response.get("error_code") == "duplicate_context_uid":
            out = "@%s That looks like a duplicate tip." % sender.capitalize()
            self.message_send_queue["low"].put((channel, out))
        elif response.get("error_message"):
            out = "@%s %s" % (sender.capitalize(), response.get("error_message"))
            self.message_send_queue["low"].put((channel, out))
        elif response.get("state") in ["ok", "accepted"]:
            tip = response["tip"]
            if tip["status"] == "out for delivery":
                out += "<3 @%s Tip received from @%s for %s. Collect it by connecting your ChangeTip account to Twitch at %s" % (tip["receiver"].capitalize(), sender.capitalize(), tip["amount_display"], tip["collect_url_short"])
                self.message_send_queue["high"].put((channel, out))
            elif tip["status"] == "finished":
                out += "<3 @%s Tip received from @%s, %s has been added to your ChangeTip wallet." % (tip["receiver"].capitalize(), sender.capitalize(), tip["amount_display"])
                self.message_send_queue["medium"].put((channel, out))
        logging.debug("Changetip Response: " + str(response))

    # Thread for getting loading initial list of users, then checks for new users in 5 minute intervals
    def load_user_list(self, offset):
        limit = 50
        logging.info("Updating user list... [%s - %s]" % (offset, offset+limit))
        response = self.TipBot.get_users(offset, limit)
        has_next = response.get("meta").get("next") is not None
        for user in response["objects"]:
            channel = "#"+user.get("channel_username")
            if channel not in self.channels:
                self.channel_join_queue.put(channel)
        if has_next:
            offset += limit+1
            threading.Timer(15.0, self.load_user_list, args=(offset,)).start()
        # If list of users is done loading, then start a thread that only gets new users every x minutes.
        else:
            threading.Timer(300.0, self.load_user_list, args=(offset,)).start()

    # Thread for joining channels, capped at a limit of 50 joins per 15 seconds to follow twitch's restrictions
    # 50 joins / 15 seconds = Join up to 5 channels every 1.5 seconds
    def channel_joiner(self, serv):
        join_count = 0
        join_limit = 5
        while not self.channel_join_queue.empty() and join_count < join_limit:
            channel = self.channel_join_queue.get()
            self.channels[channel] = Channel()
            serv.join(channel)
            logging.info("Joining channel %s" % channel)
            join_count += 1
        threading.Timer(1.5, self.channel_joiner, args=(serv,)).start()

    # Thread for sending messages, capped at a limit of 20 messages per 30 seconds to follow twitch's restrictions
    # 20 messages / 30 seconds = Send 1 message every 1.5 seconds
    # TODO: Make the limit higher if bot is a mod in the channel
    # TODO: Do some clearing if the queue gets way too high
    def message_sender(self, serv):
        high_size = self.message_send_queue["high"].qsize()
        medium_size = self.message_send_queue["medium"].qsize()
        low_size = self.message_send_queue["low"].qsize()
        queue_size = high_size + medium_size + low_size

        if queue_size > 0:
            # Determine priority
            if high_size > 0:
                priority = "high"
            elif medium_size > 0:
                priority = "medium"
            else:
                priority = "low"

            # Get message based on priority
            messagedata = self.message_send_queue[priority].get()
            channel = messagedata[0]
            message = messagedata[1]

            if message != self.last_message:
                serv.privmsg(channel, message)
                self.last_message = message
                logging.info(channel+" "+self.botname+": "+message)
        threading.Timer(1.5, self.message_sender, args=(serv,)).start()

    def monitor_message_queue_size(self,):
        high_size = self.message_send_queue["high"].qsize()
        medium_size = self.message_send_queue["medium"].qsize()
        low_size = self.message_send_queue["low"].qsize()
        queue_size = high_size + medium_size + low_size
        if queue_size > 20:
            logging.warning("Messaging queue is getting too big! HIGH:%s MEDIUM:%s LOW:%s" % (high_size, medium_size, low_size))

    def is_twitch_user(self, username):
        response = requests.get("https://api.twitch.tv/kraken/users/"+username, headers={'content-type': 'application/json'})
        if response.status_code == 404:
                return False
        else:
            return True

if __name__ == "__main__":
    try:
        botname = os.getenv("TWITCH_BOT", "changetip")
        bot = TwitchIRCBot(botname, "irc.twitch.tv", 6667)
        bot.start()
    except KeyboardInterrupt:
        print >> sys.stderr, '\nExiting by user request.\n'
        sys.exit(0)




