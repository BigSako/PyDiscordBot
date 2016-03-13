# DISCORD Bot

## Requirements (Pre-Install)
 * git
 * python-virtualenv
 * python3.4 (!!!)

E.g., on Ubuntu/Debian:
```
sudo apt-get install python-virtualenv
sudo apt-get install git
```


## Install
Python requirements: see [requirements.txt](requirements.txt)


```
git clone https://github.com/BigSako/PyDiscordBot.git
virtualenv -python python3.4 py34env
source py34env/bin/activate
cd PyDiscordBot
pip install git+https://github.com/Rapptz/discord.py@async
pip install -r requirements.txt
```

Then configure the bot (edit or better copy defaults.cfg), and run it with

```
python runbot.py --config yourcfg.cfg
```
