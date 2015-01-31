import irc.bot
from irc.bot import IRCDict, Channel
import os
import threading
import queue
from TwitchChangeTipBot import TwitchChangeTipBot


class TwitchIRCBot(irc.bot.SingleServerIRCBot):
    def __init__(self, botname, server, port=6667):

        access_token = os.getenv("TWITCH_ACCESS_TOKEN", "fake_access_token")
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port, access_token)], botname, botname)

        self.botname = botname

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
        message = ''.join(event.arguments)
        author = event.source.nick
        channel = event.target
        print(channel+" "+author+": "+message)

        if message.lower().startswith('!changetip '):
            # TODO - Figure out tipping users in the channel besides channel owner
            receiver = channel.replace("#", "")
            threading.Thread(target=self.changetip_sender, args=(serv,channel,author,receiver,message[11:])).start()

    # Thread for sending and receiving data from ChangeTip
    def changetip_sender(self, serv, channel, sender, receiver, message):
        # Submit a tip
        # TODO - Come up with better usage syntax and replies
        TipBot = TwitchChangeTipBot()
        tip_data = {
            "sender": "%s" % sender,
            "receiver": "%s" % receiver,
            "message": message,
            "context_uid": TipBot.unique_id(channel+" "+receiver+": "+message[11:]),
            "meta": {}
        }
        response = TipBot.send_tip(**tip_data)
        out = ""
        if response.get("error_code") == "invalid_sender":
            out = "To send your first tip, login with your slack account on ChangeTip: %s" % TipBot.info_url
        elif response.get("error_code") == "duplicate_context_uid":
            out = "That looks like a duplicate tip."
        elif response.get("error_message"):
            out = response.get("error_message")
        elif response.get("state") in ["ok", "accepted"]:
            tip = response["tip"]
            if tip["status"] == "out for delivery":
                out += "The tip sent by %s for %s is out for delivery. %s needs to collect by connecting their ChangeTip account to Twitch at %s" % (sender, tip["amount_display"], tip["receiver"], TipBot.info_url)
            elif tip["status"] == "finished":
                out += "The tip by %s has been delivered, %s has been added to %s's ChangeTip wallet." % (sender, tip["amount_display"], tip["receiver"])
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