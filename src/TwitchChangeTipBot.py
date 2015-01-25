from changetip.bots.base import BaseBot
import datetime
import hashlib
import os

class TwitchChangeTipBot(BaseBot):

    channel = "twitch"
    changetip_api_key = os.getenv("CHANGETIP_API_KEY")
    info_url = "https://www.changetip.com/tip-online/twitch"

    #Just copied from the slack bot for the time being, change later
    def unique_id(self, post_data):
        # Generatee a special id to prevent duplicates.
        checksum = hashlib.md5()
        checksum.update(str(post_data).encode("utf8"))
        checksum.update(datetime.datetime.now().strftime('%Y-%m-%d:%H:%M:00').encode("utf8"))

        return checksum.hexdigest()[:16]
