# DISCORD Bot
This is a DISCORD Bot developed by [BigSako](http://evewho.com/pilot/BigSako), which uses
[discord.py](https://github.com/Rapptz/discord.py) and Python 3.4 asyncio.


## Requirements (Pre-Install)
 * git
 * python-virtualenv
 * python3.4 (!!!)

E.g., on Ubuntu/Debian:
```
sudo apt-get install python-virtualenv python3.4
sudo apt-get install git
```


## Install
Python requirements: see [requirements.txt](requirements.txt)


```
git clone https://github.com/BigSako/PyDiscordBot.git
cd PyDiscordBot
virtualenv -p python3.4 virtualenv
source virtualenv/bin/activate
pip install git+https://github.com/Rapptz/discord.py@async
pip install -r requirements.txt
```

Then configure the bot (edit or better copy defaults.cfg)
```
[Database]
dbhost:localhost
dbuser:nouser
dbpass:nopass
dbname:nodb

[Discord]
discorduser:nouser
discordpass:nopass

[Bot]
debug_channel_name:bot_debug
auth_website:http://localhost

```

and run it with

```
python runbot.py --config yourcfg.cfg
```
