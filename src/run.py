import irc.bot
from irc.bot import IRCDict, Channel
import os
from TwitchChangeTipBot import TwitchChangeTipBot

class TwitchIRCBot(irc.bot.SingleServerIRCBot):
    def __init__(self, botname, server, port=6667,):

        # TODO - Write method for getting oauth token
        oauth = os.getenv("TWITCH_PASS", "fake_oauth_token")

        irc.bot.SingleServerIRCBot.__init__(self, [(server, port, oauth)], botname, botname)

        # TODO - Write method for getting list of twitch changetip users (channels to join)
        channels = ["#tippybot", "#mances14", "#bitcoinsantaclaus"]

        self.channels = IRCDict()
        for channel in channels:
            self.channels[channel] = Channel()
 
    def on_welcome(self, serv, event):
        # TODO - Implement channel join rate limit based on Twitch guidelines, so the bot does not get banned for spam
        for channel in self.channels.keys():
            print("--Joining", channel)
            serv.join(channel)

    def on_pubmsg(self, serv, event):
        message = ''.join(event.arguments)
        author = event.source.nick
        channel = event.target
        print(channel+" "+author+": "+message)

        if message.lower().startswith('!changetip '):
            # TODO - Implement message rate limit based on Twitch guidelines, so the bot does not get banned for spam
            # TODO - Use multi threading so program does not need to wait for ChangeTip responses
            # TODO - Figure out tipping users in the channel besides channel owner
            # TODO - Come up with better usage syntax and replies
            # Submit the tip
            TipBot = TwitchChangeTipBot()
            tip_data = {
                "sender": "%s" % author,
                "receiver": "%s" % (channel.replace("#", "")),
                "message": message[11:],
                "context_uid": TipBot.unique_id(channel+" "+author+": "+message[11:]),
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
                    out += "The tip sent by %s for %s is out for delivery. %s needs to collect by connecting their ChangeTip account to Twitch at %s" % (author, tip["amount_display"], tip["receiver"], TipBot.info_url)
                elif tip["status"] == "finished":
                    out += "The tip by %s has been delivered, %s has been added to %s's ChangeTip wallet." % (author, tip["amount_display"], tip["receiver"])
            print("--Changetip Response: " + str(response))
            serv.privmsg(channel, out)

if __name__ == "__main__":
    botname = os.getenv("TWITCH_BOT", "Changetip")
    bot = TwitchIRCBot(botname, "irc.twitch.tv", 6667)
    bot.start()