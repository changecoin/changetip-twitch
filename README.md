# ChangeTip Twitch.tv Bot

[ChangeTip](https://www.changetip.com) is a micropayment infrastructure for the web, enabling tips to be sent over social media. This code allows users to *tip* eachother with [Twitch.tv](https://twitch.tv/), using [Twitch.tv chat](http://help.twitch.tv/customer/portal/articles/1302780-twitch-irc)

Once a user authorizes their Twitch.tv account on ChangeTip, the bot will join their channel and allow tipping in their chat.

## Tipping
Type `!changetip` at the *beginning* of a message, then mention a @username and an amount (or leave out @username to tip the channel owner directly).

Examples:

```
!changetip Nice win! Have a $5 donation!
```

```
!changetip Give @Kappa a high five for that close match!
```

## Running on your own machine

### Installing dependencies

```
$ pip install -r requirements.txt
```


#### Environment Variables

You must set the following environment variables to run the bot:

```
CHANGETIP_API_KEY
```

To get an API key, contact support@changetip.com


```
TWITCH_BOT
```

This should be your bot's username on Twitch.tv


```
TWITCH_ACCESS_TOKEN
```

Your bot's access token, required to connect to Twitch irc.

You can acquire one easily for development by using the Third Party [Twitch Chat Password Generator app](http://twitchapps.com/tmi/) 

Or you can set up a Twitch app in your account settings and make a request to the following url (with your Twitch app's info in place of the bracketed text)
`https://api.twitch.tv/kraken/oauth2/authorize?response_type=token&client_id=[your client ID]&redirect_uri=[your registered redirect URI]&scope=chat_login`
[For more information read Twitch's authentication documentation.](https://github.com/justintv/Twitch-API/blob/master/authentication.md) 

Once you have this access token it will not expire unless you generate a new access token.

