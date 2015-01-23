from bot import TwitchBot
import socket
import threading
import re
import os

# Sets variables for connection to twitch chat
botuser = 'tippybot' 
channels = ['tippybot'] #TODO: Figure out a way to get connected accounts to join
server = 'irc.twitch.tv'
password = os.getenv("TWITCH_PASS")

irc = socket.socket()
irc.connect((server, 6667)) # connects to the server

# sends variables for connection to twitch chat
irc.send(bytes('PASS ' + password + '\r\n','UTF-8'))
irc.send(bytes('USER ' + botuser + ' 0 * :' + botuser + '\r\n','UTF-8'))
irc.send(bytes('NICK ' + botuser + '\r\n','UTF-8'))

for channel in channels:
    irc.send(bytes('JOIN #' + channel + '\r\n','UTF-8'))


info_url = "https://www.changetip.com/tip-online/twitch"
get_started = "To send your first tip, login with your slack account on ChangeTip: %s" % info_url


while True:
    msg = irc.recv(1204).decode("UTF-8")

    print(msg)

    if msg.find('PING') != -1:
        irc.send(bytes(msg.replace('PING', 'PONG'),'UTF-8')) #responds to PINGS from the server

    # if contains priv message, attempt to receive message data
    if msg.find('PRIVMSG') != -1:
        mdata = re.search(':(.*)!.* PRIVMSG #(.*) :(.*)', msg).groups()
        msgchannel = mdata[1]
        msguser = mdata[0]
        msgcontent = mdata[2]
        
        print("#" + msgchannel + " " + msguser + ": " + msgcontent)
        
        if msgcontent.startswith('!changetip '):
            ## Submit the tip
            bot = TwitchBot()
            tip_data = {
                "sender": "%s" % (msguser),
                "receiver": "%s" % (msgchannel),
                "message": msgcontent,
                "context_uid": bot.unique_id(msg),
                "meta": {}
            }
            response = bot.send_tip(**tip_data)
            out = ""
            if response.get("error_code") == "invalid_sender":
                out = get_started
            elif response.get("error_code") == "duplicate_context_uid":
                out = "That looks like a duplicate tip."
            elif response.get("error_message"):
                out = response.get("error_message")
            elif response.get("state") in ["ok", "accepted"]:
                tip = response["tip"]
                if tip["status"] == "out for delivery":
                    out += "The tip for %s is out for delivery. %s needs to collect by connecting their ChangeTip account to Twitch at %s" % (tip["amount_display"], tip["receiver"], info_url)
                elif tip["status"] == "finished":
                    out += "The tip has been delivered, %s has been added to %s's ChangeTip wallet." % (tip["amount_display"], tip["receiver"])
            print(response)
