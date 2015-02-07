import irc.bot
from irc.bot import IRCDict, Channel
import os
import threading
import queue
from TwitchChangeTipBot import TwitchChangeTipBot
import re

class TwitchIRCBot(irc.bot.SingleServerIRCBot):
    def __init__(self, botname, server, port=6667):

        access_token = os.getenv("TWITCH_ACCESS_TOKEN", "fake_access_token")
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port, access_token)], botname, botname)

        #Bot username
        self.botname = botname

        #Changetip set up
        self.TipBot = TwitchChangeTipBot()

        # TODO - Write method for getting list of twitch changetip users (channels to join)
        channels = ["#tippybot", "#mances14", "#bitcoinsantaclaus"]

        # Channels set up
        self.channels = IRCDict()
        self.channel_join_queue = queue.Queue()
        self.channel_join_limiter = 0

        for channel in channels:
            self.channel_join_queue.put(channel)

        # Messages set up
        self.message_send_queue = queue.Queue()
        self.message_send_limiter = 0

        print("Initialized...attempting to connect.")

    def on_welcome(self, serv, event):
        print("Connected.")
        # Start channel joining thread
        threading.Thread(target=self.channel_joiner, args=(serv,)).start()
        # Start message sending thread
        threading.Thread(target=self.message_sender, args=(serv,)).start()

    def on_pubmsg(self, serv, event):
        message = ''.join(event.arguments).strip()
        author = event.source.nick
        channel = event.target
        receiver = channel.replace("#", "") #set default receiver to the channel

        print(channel+" "+author+": "+message)

        if message.lower().startswith('!changetip '):
            # Check if the message contains a receiver, if not then assume it is for the channel owner
            pattern = re.compile("(?<=^|(?<=[^a-zA-Z0-9-_\.]))@([A-Za-z]+[A-Za-z0-9]+)")
            tipped = re.findall(pattern, message)
            if len(tipped) == 0:
                threading.Thread(target=self.changetip_sender, args=(channel, author, receiver, message[11:])).start()
            elif len(tipped) == 1:
                tipped_user = tipped[0].lower()
                if tipped_user in self.channels[channel].users() or tipped_user == receiver:
                    receiver = tipped_user
                    threading.Thread(target=self.changetip_sender, args=(channel, author, receiver, message[11:])).start()
                else:
                    self.message_send_queue.put((channel, "@%s I don't see that user in this channel." % author.capitalize()))
            else:
                self.message_send_queue.put((channel, "@%s Too many recipients in your message." % author.capitalize()))

    # Thread for sending and receiving data from ChangeTip
    def changetip_sender(self, channel, sender, receiver, message):
        # Submit a tip
        tip_data = {
            "sender": "%s" % sender,
            "receiver": "%s" % receiver,
            "message": message,
            "context_uid": self.TipBot.unique_id(channel+" "+receiver+": "+message[11:]),
            "meta": {}
        }
        response = self.TipBot.send_tip(**tip_data)
        out = ""
        if response.get("error_code") == "invalid_sender":
            out = "@%s To send your first tip, login with your Twitch.tv account on ChangeTip: %s" % (sender.capitalize(), self.TipBot.info_url)
        elif response.get("error_code") == "duplicate_context_uid":
            out = "@%s That looks like a duplicate tip." % sender.capitalize()
        elif response.get("error_message"):
            out = "@%s %s" % (sender.capitalize(), response.get("error_message"))
        elif response.get("state") in ["ok", "accepted"]:
            tip = response["tip"]
            if tip["status"] == "out for delivery":
                out += "<3 @%s Tip received from @%s for %s. Collect it by connecting your ChangeTip account to Twitch at %s" % (tip["receiver"], sender.capitalize(), tip["amount_display"], self.TipBot.info_url)
            elif tip["status"] == "finished":
                out += "<3 @%s Tip received from @%s, %s has been added to your ChangeTip wallet." % (tip["receiver"].capitalize(), sender.capitalize(), tip["amount_display"])
        print("--Changetip Response: " + str(response))
        self.message_send_queue.put((channel, out))

    # Thread for joining channels, capped at a limit of 50 joins per 15 seconds to follow twitch's restrictions
    def channel_joiner(self, serv):
        limit = 50
        seconds = 15.0
        while True:
            if not self.channel_join_queue.empty() and self.channel_join_limiter < limit:
                channel = self.channel_join_queue.get()
                print("--Joining", channel)
                self.channels[channel] = Channel()
                serv.join(channel)
                self.channel_join_limiter += 1
                threading.Timer(seconds, self.channel_unlimit)

    def channel_unlimit(self):
        self.channel_join_limiter -= 1

    # Thread for sending messages, capped at a limit of 20 messages per 30 seconds to follow twitch's restrictions
    def message_sender(self, serv):
        limit = 20
        seconds = 30.0
        while True:
            if not self.message_send_queue.empty() and self.message_send_limiter < limit:
                messagedata = self.message_send_queue.get()
                channel = messagedata[0]
                message = messagedata[1]
                print(channel+" "+self.botname+": "+message)
                serv.privmsg(channel, message)
                self.message_send_limiter += 1
                threading.Timer(seconds, self.message_unlimit)

    def message_unlimit(self):
        self.message_send_limiter -= 1

if __name__ == "__main__":
    botname = os.getenv("TWITCH_BOT", "changetip")
    bot = TwitchIRCBot(botname, "irc.twitch.tv", 6667)
    bot.start()