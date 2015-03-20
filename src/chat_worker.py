from irc.bot import IRCDict, Channel, SingleServerIRCBot
import Queue
import threading
import logging
import socks
import socket


class TwitchIRCBot(SingleServerIRCBot):

    def __init__(self, master, worker_name, bot_name, server, access_token, port=6667, proxy=None):
        self.master = master
        self.worker_name = worker_name
        self.command = "!"+self.master.bot_name
        self.started = False

        if proxy is not None:
            logging.info('[%s] Proxy set: %s:%s', self.worker_name, proxy["address"], proxy["port"])
            socks.set_default_proxy(socks.HTTP, proxy["address"], proxy["port"])
            socket.socket = socks.socksocket

        SingleServerIRCBot.__init__(self, [(server, port, access_token)], bot_name, bot_name)

        # Channels set up
        self.channels = IRCDict()
        self.channel_join_queue = Queue.Queue()
        self.channel_list = []

        # Messages set up
        self.user_message_queue = Queue.Queue()

        logging.info('[%s] Chat worker bot initialized.', self.worker_name)

    def on_welcome(self, serv, event):
        if not self.started:
            logging.info('[%s] Connected to Twitch.tv IRC.', self.worker_name)
            # Start channel joining thread
            threading.Thread(target=self.channel_joiner, args=(serv,)).start()
            # Start message sending thread
            threading.Thread(target=self.message_sender, args=(serv,)).start()
            self.started = True
        # Welcome is a reconnect, rejoin all channels
        else:
            logging.info('[%s] Reconnected to Twitch.tv IRC.', self.worker_name)
            for channel in self.channel_list:
                self.channel_join_queue.put(channel)

    def on_disconnect(self, serv, event):
        logging.warning('[%s] Lost connection to Twitch.tv IRC. Attempting to reconnect...', self.worker_name)

    def on_pubmsg(self, serv, event):
        message = ''.join(event.arguments).strip()
        author = event.source.nick
        channel = event.target

        if message.startswith(self.command+" ") or message == self.command:
            self.master.process_message(self.worker_name, channel, author, message[len(self.command):].strip())

    # Thread for joining channels, capped at a limit of 50 joins per 15 seconds to follow twitch's restrictions
    # 50 joins / 15 seconds = Join up to 5 channels every 1.5 seconds
    def channel_joiner(self, serv):
        join_count = 0
        join_limit = 5
        while not self.channel_join_queue.empty() and join_count < join_limit:
            channel = self.channel_join_queue.get()
            self.channels[channel] = Channel()
            self.channel_list.append(channel)
            serv.join(channel)
            logging.info("[%s] Joining channel %s", self.worker_name, channel)
            join_count += 1
        threading.Timer(1.5, self.channel_joiner, args=(serv,)).start()

    # Thread for sending messages, capped at a limit of 20 messages per 30 seconds to follow twitch's restrictions
    # 20 messages / 30 seconds = Send 1 message every 1.5 seconds
    def message_sender(self, serv):

        if self.master.message_center.has_message(self.worker_name):
            mdata = self.master.message_center.get_message(self.worker_name)
            message = mdata["message"]
            channel = mdata["channel"]

            if message != self.master.message_center.last_message: # Do not send the same message twice
                serv.privmsg(channel, message)
                self.master.message_center.last_message = message
                logging.info("[%s] %s %s: %s", self.worker_name, channel, self.master.bot_name, message)

        threading.Timer(1.5, self.message_sender, args=(serv,)).start()