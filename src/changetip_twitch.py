# -*- coding: utf-8 -*-
from changetip.bots.base import BaseBot
import datetime
import hashlib
import os
import requests
import logging
import regex

class ChangeTipTwitch(BaseBot):

    channel = "twitch"
    changetip_api_key = os.getenv("CHANGETIP_API_KEY")
    info_url = "https://www.changetip.com/tip-online/twitch"

    def process_command(self, channel, sender, message):
        logging.info("[Changetip] %s %s: %s", channel, sender, message)

        tip_output = dict()
        tip_output["sender"] = sender
        tip_output["channel"] = channel
        tip_output["message"] = ""
        tip_output["priority"] = "low"

        submit_tip = True

        # Check if the message contains a receiver, if not then assume it is for the channel owner
        receiver = channel.replace("#", "")
        pattern = regex.compile("(?<=^|(?<=[^a-zA-Z0-9-_\.]))@([A-Za-z0-9_]+)")
        tipped = regex.findall(pattern, message)

        if len(tipped) == 1:
            tipped_user = tipped[0].lower()
            if self.is_twitch_user(tipped_user):
                receiver = tipped_user
            else:
                tip_output["message"] = "@%s That user does not exist." % sender.capitalize()
                submit_tip = False
        elif len(tipped) > 1:
            tip_output["message"] = "@%s Too many recipients in your message." % sender.capitalize()
            submit_tip = False

        if submit_tip:
            # Submit a tip
            tip_data = {
                "sender": "%s" % sender,
                "receiver": "%s" % receiver,
                "message": message,
                "context_uid": self.unique_id(channel+" "+sender+": "+message),
                "meta": {"context_url": "twitch.tv/%s" % channel.replace("#", "")}
            }
            response = self.send_tip(**tip_data)
            if response.get("error_code") == "invalid_sender":
                tip_output["message"] = "@%s To send your first tip, login with your Twitch.tv account on ChangeTip: %s" % (sender.capitalize(), self.info_url)
            elif response.get("error_code") == "duplicate_context_uid":
                tip_output["message"] = "@%s That looks like a duplicate tip." % sender.capitalize()
            elif response.get("error_message"):
                tip_output["message"] = "@%s %s" % (sender.capitalize(), response.get("error_message"))
            elif response.get("state") in ["ok", "accepted"]:
                tip = response["tip"]
                if tip["status"] == "out for delivery":
                    tip_output["message"] = "<3 @%s Tip received from @%s for %s. Collect it by connecting your Twitch account here %s %s" % (tip["receiver"].capitalize(), sender.capitalize(), tip["amount_display"], "➔".decode('utf-8'), tip["collect_url_short"])
                    tip_output["priority"] = "high"
                elif tip["status"] == "finished":
                    tip_output["message"] = "<3 @%s Tip received from @%s, %s has been added to your ChangeTip wallet." % (tip["receiver"].capitalize(), sender.capitalize(), tip["amount_display"])
                    tip_output["priority"] = "medium"
            logging.debug("[Changetip] Changetip Response: " + str(response))
        return tip_output

    def unique_id(self, post_data):
        checksum = hashlib.md5()
        checksum.update(str(post_data).encode("utf8"))
        checksum.update(datetime.datetime.now().strftime('%Y-%m-%d:%H:%M:00').encode("utf8"))
        return checksum.hexdigest()[:16]

    def get_users(self, offset=0, limit=200):
        response = requests.get(self.get_api_url("/channels/twitch/users"), params={'offset': offset, 'limit': limit}, headers={'content-type': 'application/json'})
        response = response.json()
        has_next = response.get("meta").get("next") is not None
        users = []
        for user in response["objects"]:
            users.append(user.get("channel_username"))

        if has_next:
            offset += limit+1
            return users.extend(self.get_users(offset))
        else:
            return users

    # TODO Optimize this where ever possible
    def is_twitch_user(self, username):
        response = requests.get("https://api.twitch.tv/kraken/users/"+username, headers={'content-type': 'application/json'})
        if response.status_code == 404:
            return False
        else:
            return True