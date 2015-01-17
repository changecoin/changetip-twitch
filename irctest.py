import socket
import threading
import re

#sets variables for connection to twitch chat
bot_owner = 'tippybot'
nick = 'tippybot' 
channel = '#tippybot'
server = 'irc.twitch.tv'
password = 'OAUTHHERE'

queue = 13 #sets variable for anti-spam queue functionality

irc = socket.socket()
irc.connect((server, 6667)) #connects to the server

#sends variables for connection to twitch chat
irc.send(bytes('PASS ' + password + '\r\n','UTF-8'))
irc.send(bytes('USER ' + nick + ' 0 * :' + bot_owner + '\r\n','UTF-8'))
irc.send(bytes('NICK ' + nick + '\r\n','UTF-8'))
irc.send(bytes('JOIN ' + channel + '\r\n','UTF-8'))


while True:
    msg = irc.recv(1204).decode("UTF-8")

    print(msg)

    if msg.find('PING') != -1:
        irc.send(bytes(msg.replace('PING', 'PONG'),'UTF-8')) #responds to PINGS from the server

    #if contains priv message, attempt to receive message data
    if msg.find('PRIVMSG') != -1:
        mdata = re.search(':(.*)!.* PRIVMSG #(.*) :(.*)', msg).groups()
        msgchannel = mdata[1]
        msguser = mdata[0]
        msgcontent = mdata[2]
        
        print ("#" + msgchannel + " " + msguser + ": " + msgcontent)
        
        if msgcontent.startswith('!changetip '):
            #just test sending a faked reply, implement changetip bot portion later
            if msgcontent.find('$1') != -1: #send tip
                tipmsg = msgchannel + ", " + msguser + "  wants to send you a Bitcoin tip for $1.00. Collect it: http://changetip.com"
                irc.send(bytes('PRIVMSG ' + channel + ' :' + tipmsg + '\r\n','UTF-8'))
            else: #invalid message
                irc.send(bytes('PRIVMSG ' + channel + ' :' + msguser + ", the command you entered was not recognized. FAQ: http://changetip.com" + '\r\n','UTF-8'))
