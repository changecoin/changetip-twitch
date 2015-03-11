from changetip_twitch import ChangeTipTwitch
from chat_worker import TwitchIRCBot
from message_center import MessageCenter
import os
import logging
import threading

logger = logging.getLogger(__name__)
logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', filename='twitch.log', level=logging.INFO)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
logging.getLogger('').addHandler(console)


class TwitchMaster(object):

    def __init__(self):
        self.bot_name = os.getenv("TWITCH_BOT", "ChangeTip")
        self.access_token = "oauth:"+os.getenv("TWITCH_ACCESS_TOKEN", "")
        self.irc_address = "irc.twitch.tv"

        # Connections and Proxies
        self.proxies = []
        proxy_list = os.getenv("TWITCH_PROXIES", None)
        if proxy_list is not None:
            proxy_list = os.getenv("TWITCH_PROXIES", "").split(",")
            for proxy in proxy_list:
                proxy_info = proxy.split(":")
                print proxy_info
                self.proxies.append({"address": proxy_info[0], "port": int(proxy_info[1])})

        # Change Tip
        self.ChangeTip = ChangeTipTwitch()

        # Get list of users
        logging.info('[Master] Fetching user list from ChangeTip...')
        self.users_list = self.ChangeTip.get_users()

        # Create chat workers
        logging.info('[Master] Creating chat worker bots...')
        self.chat_bots = {}
        worker_num = 1
        worker_name = "%s:Worker" % worker_num
        # Create first worker on local ip/connection
        self.chat_bots[worker_name] = TwitchIRCBot(self, worker_name, self.bot_name, self.irc_address, self.access_token, 6667)
        threading.Thread(target=self.chat_bots[worker_name].start).start()
        # Create subsequent workers on proxy ip/connections
        for proxy in self.proxies:
            worker_num += 1
            worker_name = "%s:Worker" % worker_num
            self.chat_bots[worker_name] = TwitchIRCBot(self, worker_name, self.bot_name, self.irc_address, self.access_token, 6667, proxy)
            threading.Thread(target=self.chat_bots[worker_name].start).start()

        # Initialize Message Queue
        logging.info('[Master] Initializing messaging queue...')
        self.message_center = MessageCenter(self.chat_bots.keys())

        # Tell workers to join channels
        # TODO: Intelligently split up channels between IPs, based on typical channel usage
        logging.info('[Master] Starting channel joins...')
        worker_name = "%s:Worker" % 1
        self.join_channels(worker_name, self.users_list)

        # Start a thread to periodically fetch new users from ChangeTip
        threading.Timer(300.0, self.check_new_users).start()


    def join_channels(self, worker_name, channels):
        for user in channels:
            self.chat_bots[worker_name].channel_join_queue.put("#"+user)

    def process_message(self, worker_name, channel, sender, message):
        changetip_out = self.ChangeTip.process_command(channel, sender, message)
        self.message_center.add_message(worker_name, changetip_out["sender"], changetip_out["channel"], changetip_out["message"])

    # Periodically checks for new users from ChangeTip and joins their channels
    def check_new_users(self):
        logging.info('[Master] Checking for new users from ChangeTip...')
        new_users_list = self.ChangeTip.get_users(len(self.users_list))
        worker_num = 0
        for new_user in new_users_list:
            worker_name = self.chat_bots.keys()[worker_num]
            self.chat_bots[worker_name].channel_join_queue.put("#"+new_user)
            if worker_name < len(self.chat_bots.keys()):
                worker_num += 1
            else:
                worker_num = 0
        threading.Timer(300.0, self.check_new_users).start()