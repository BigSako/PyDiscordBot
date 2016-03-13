# DISCORD Bot
Requirements: See [requirements.txt](requirements.txt)


## Install
```
git clone https://github.com/BigSako/PyDiscordBot.git
virtualenv -python python3.4 py34env
source py34env/bin/activate
pip install -r requirements.txt
pip install git+https://github.com/Rapptz/discord.py@async
```

Then configure the bot (edit or better copy defaults.cfg), and run it with

```
python runbot.py --config yourcfg.cfg
```
