""" reloadable module that handles bot commands """

import logging
import asyncio
from datetime import datetime

from model import MyDBModel
import random
import sys, inspect
import discord
import traceback


class AbstractBotCommand:
    available_commands = {}

    def __init__(self, db_model, discord_client):
        """ initializes the bot class with the db model """
        self.model = db_model
        self.client = discord_client


    @staticmethod
    def import_bot_commands(db_model, discord_client):
        """ initializes all bot commands """
        for name, obj in inspect.getmembers(sys.modules[__name__]):
            if inspect.isclass(obj) and "AbstractBotCommand" not in str(obj.__name__ ) and "bot_commands" in str(obj.__module__):
                newobj = obj.__new__(obj)
                newobj.__init__(db_model, discord_client)
                AbstractBotCommand.register_command(newobj.cmd, newobj)


    @staticmethod
    def register_command(cmd, object):
        logging.info("Registered object for command '%s' for obj %s", cmd, object)
        AbstractBotCommand.available_commands[cmd] = object

    @staticmethod
    @asyncio.coroutine
    def handle_msg(message):
        """ parses the msg and dispatches it to the right sub-command """

        msg = str(message.content)


        if not msg.startswith("!"):
            return

        if " " in msg:
            cmd =  msg[msg.find("!"):msg.find(" ")]
            # extract params
            params = msg[msg.find(" ")+1:]
        else: # new line at the end, so we are fine
            cmd =  msg[msg.find("!"):]
            params = ""
        # extract command name
        logging.info("Found command string '%s'", cmd)

        # see if this command is available
        if cmd in AbstractBotCommand.available_commands:
            try:
                # dispatch command to abstract command
                yield from AbstractBotCommand.available_commands[cmd].handle_command(message, cmd, params)
            except Exception as e:
                logging.exception("Unexpected error while dispatching...")
                logging.error(traceback.format_exc())
                yield from AbstractBotCommand.available_commands[cmd].client.send_to_debug_channel(
                    "Unexpected error while dispatching '{}': {}".format(cmd, traceback.format_exc()))
        else:
            logging.info("Command '%s' not found...", cmd)


    @asyncio.coroutine
    def handle_command(self, message, cmd, params):
        logging.error("Abstract method was called... f")
        return



class WhoisBotCommand:
    def __init__(self, db_model, discord_client):
        self.client = discord_client
        self.model = db_model
        self.cmd = "!whois"

    @asyncio.coroutine
    def handle_command(self, message, cmd, params):
        logging.info("in WhoisBotCommand.handle_command()")
        # get parameter, starts with < and ends with >

        if ">" in params and "<@" in params:

            wanted_member_id = params[params.find("<@")+2:params.find(">")]
            print("wanted_id=" + str(wanted_member_id))
            if wanted_member_id in self.client.authed_users:
                char_data = self.model.get_discord_members_character_id(wanted_member_id)
                yield from self.client.send_message(message.channel, "<@" + wanted_member_id + "> is also known as " + str(char_data))
            else:
                yield from self.client.send_message(message.channel, "<@" + str(message.author.id) + "> I am sorry, I do not know this user!")

        else:
            yield from self.client.send_message(message.channel, "<@" + str(message.author.id) + "> What?!?!?")



class WhoamiBotCommand:
    def __init__(self, db_model, discord_client):
        self.client = discord_client
        self.model = db_model
        self.cmd = "!whoami"

    @asyncio.coroutine
    def handle_command(self, message, cmd, params):
        logging.info("in WhoamiBotCommand.handle_command()")

        if message.author.id in self.client.authed_users:
            char_data = self.model.get_discord_members_character_id(message.author.id)
            yield from self.client.send_message(message.channel, "<@" + message.author.id + "> is also known as " + str(char_data))
        else:
            yield from self.client.send_message(message.channel, "<@" + str(message.author.id) + "> I am sorry, I do not know you!")


class CatCommand:
    def __init__(self, db_model, discord_client):
        self.client = discord_client
        self.model = db_model
        self.cmd = "!cat"

    @asyncio.coroutine
    def handle_command(self, message, cmd, params):
        logging.info("in CatCommand.handle_command()")
        yield from self.client.send_message(message.channel, "http://thecatapi.com/api/images/get?format=src&type=gif&time=" + str(random.randint(0, 5000)))


class EveTimeCommand:
    def __init__(self, db_model, discord_client):
        self.client = discord_client
        self.model = db_model
        self.cmd = "!evetime"

    @asyncio.coroutine
    def handle_command(self, message, cmd, params):
        logging.info("in EveTimeCommand.handle_command()")
        yield from self.client.send_message(message.channel, "Current EVE Time " + str(datetime.utcnow()))


class UptimeBotCommand:
    def __init__(self, db_model, discord_client):
        self.client = discord_client
        self.model = db_model
        self.cmd = "!uptime"

    @asyncio.coroutine
    def handle_command(self, message, cmd, params):
        logging.info("in UptimeBotCommand.handle_command()")
        yield from self.client.send_message(message.channel, "I'm up since " + str(self.client.start_time))



class UpdateRolesCommand:
    def __init__(self, db_model, discord_client):
        self.client = discord_client
        self.model = db_model
        self.cmd = "!update_roles"

    @asyncio.coroutine
    def handle_command(self, message, cmd, params):
        logging.info("in UpdateRolesCommand.handle_command()")
        if message.channel == self.client.debug_channel:
            self.client.update_roles(self.client.main_server)
            yield from self.client.send_message(message.channel, self.client.get_roles_str(self.client.main_server))

class SpainCommand:
    def __init__(self, db_model, discord_client):
        self.client = discord_client
        self.model = db_model
        self.cmd = "!spain"

    @asyncio.coroutine
    def handle_command(self, message, cmd, params):
        logging.info("in SpainCommand.handle_command()")
        yield from self.client.send_message(message.channel, "Yes no :es: ")


class PenisCommand:
    def __init__(self, db_model, discord_client):
        self.client = discord_client
        self.model = db_model
        self.cmd = "!penis"

    @asyncio.coroutine
    def handle_command(self, message, cmd, params):
        logging.info("in PenisCommand.handle_command()")
        yield from self.client.send_message(message.channel, "Why????!???")


class PKCommand:
    def __init__(self, db_model, discord_client):
        self.client = discord_client
        self.model = db_model
        self.cmd = "!pk"

    @asyncio.coroutine
    def handle_command(self, message, cmd, params):
        logging.info("in PKCommand.handle_command()")
        yield from self.client.send_message(message.channel, "I heard PK is a :whale:")


class DeathCommand:
    def __init__(self, db_model, discord_client):
        self.client = discord_client
        self.model = db_model
        self.cmd = "!death"

    @asyncio.coroutine
    def handle_command(self, message, cmd, params):
        logging.info("in DeathCommand.handle_command()")
        yield from self.client.send_message(message.channel, "https://www.youtube.com/watch?v=hdcTmpvDO0I")


class WhiteCommand:
    def __init__(self, db_model, discord_client):
        self.client = discord_client
        self.model = db_model
        self.cmd = "!white"

    @asyncio.coroutine
    def handle_command(self, message, cmd, params):
        logging.info("in WhiteCommand.handle_command()")
        yield from self.client.send_message(message.channel, "http://41.media.tumblr.com/tumblr_ls2cgdq2yL1qa04m7o1_500.png")


class CookieBotCommand:
    cookie_messages = ["I think you need a :cookie:", "Have a :cookie:",
                       "Have two :cookie:", "Sorry, I am out of cookies! Oh wait, found one! :cookie:",
                       "C is for :cookie:", "https://www.youtube.com/watch?v=Ye8mB6VsUHw",
                       "https://www.youtube.com/watch?v=-qTIGg3I5y8", "I think you had enough!",
                       "Okay, but only one more :cookie:!", "I like cookies too! :thumbsup:",
                       "C O O K I E", ":cookie: :cookie: :cookie: :cookie: :cookie: :cookie: :cookie: :cookie:",
                       "Cafe?", "Beer?", "Cake?", "One cookie for you. One cookie. I said one! :cookie: ",
                       "All you eat is cookies... ", "All your cookies are belong to us",
                       "http://rack.0.mshcdn.com/media/ZgkyMDEzLzEwLzA3L2JmL0Nvb2tpZU1vbnN0LmE4NjZlLmpwZwpwCXRodW1iCTk1MHg1MzQjCmUJanBn/19941105/9eb/CookieMonster.jpg",
                       "http://orig08.deviantart.net/357b/f/2011/235/d/8/cute_cookie_x3_by_lanahx3-d47lt9o.jpg",
                       "You want cookie? Yes no spain?",
                       "Please wait, while we process your request...", "Free Cookies for everyone! :cookie: :cookie: :cookie: :cookie: :cookie:",
                       "Omnomnomnomnom... You want a :cookie: too?", "Sorry, but Deathwhisper ate all my cookies :(",
                       "Are you sure?", "The cookie is a lie!", "Ofcourse! Here is a :cookie: for you!",
                       "Share your :cookie: with a friend!", "Cookie? :cookie:", "NO!",
                       "http://i4.manchestereveningnews.co.uk/incoming/article10580003.ece/ALTERNATES/s615/JS47622759.jpg",
                       "Waiting on a cookie delivery... :car: ", "Nobody ever gives me cookies :(",
                       "Omnomnomnom sorry, that was the last one! :cry: ",
                       "You want my :cookie:?", "I give you :cookie: "]

    positive_cookie_messages = ["Have a :cookie:!", "I think you need a :cookie:!",
                                "Want a :cookie:?", "Have two :cookie:!"]

    def __init__(self, db_model, discord_client):
        self.client = discord_client
        self.model = db_model
        self.cmd = "!cookie"
        self.stats = {}

    @asyncio.coroutine
    def handle_command(self, message, cmd, params):
        logging.info("in CookieBotCommand.handle_command()")
        author = str(message.author)

        if params == "":
            if author in self.stats:
                self.stats[author] += 1
            else:
                self.stats[author] = 1

            idx = random.randint(0,len(CookieBotCommand.cookie_messages)) % len(CookieBotCommand.cookie_messages)
            yield from self.client.send_message(message.channel, CookieBotCommand.cookie_messages[idx])
        else: # params = username
            if ">" in params and "<@" in params:
                wanted_member_id = params[params.find("<@")+2:params.find(">")]
                idx = random.randint(0,len(CookieBotCommand.positive_cookie_messages)) % len(CookieBotCommand.positive_cookie_messages)

                yield from self.client.send_message(message.channel, "<@" + wanted_member_id + "> " + CookieBotCommand.positive_cookie_messages[idx])
            elif "stats" in params:
                if author in self.stats:
                    cnt = self.stats[author]
                else:
                    cnt = 0

                yield from self.client.send_message(message.channel, "You already got " + str(cnt) + " cookies!")


class WhiskeyBotCommand:
    def __init__(self, db_model, discord_client):
        self.client = discord_client
        self.model = db_model
        self.cmd = "!whiskey"

    @asyncio.coroutine
    def handle_command(self, message, cmd, params):
        logging.info("in WhiskeyBotCommand.handle_command()")
        yield from self.client.send_message(message.channel, "<@" + message.author.id + "> invites everybody to drink a whiskey!")


class ScotchBotCommand:
    def __init__(self, db_model, discord_client):
        self.client = discord_client
        self.model = db_model
        self.cmd = "!scotch"

    @asyncio.coroutine
    def handle_command(self, message, cmd, params):
        logging.info("in ScotchBotCommand.handle_command()")
        yield from self.client.send_message(message.channel, "<@" + message.author.id + "> invites everybody to drink a scotch!")



class CafeBotCommand:
    def __init__(self, db_model, discord_client):
        self.client = discord_client
        self.model = db_model
        self.cmd = "!cafe"

    @asyncio.coroutine
    def handle_command(self, message, cmd, params):
        logging.info("in CafeBotCommand.handle_command()")
        yield from self.client.send_message(message.channel, "<@" + message.author.id + "> hands out coffee!")


class CakeBotCommand:
    def __init__(self, db_model, discord_client):
        self.client = discord_client
        self.model = db_model
        self.cmd = "!cake"

    @asyncio.coroutine
    def handle_command(self, message, cmd, params):
        logging.info("in CakeBotCommand.handle_command()")
        yield from self.client.send_message(message.channel, "The cake is a lie!")



class USABotCommand:
    def __init__(self, db_model, discord_client):
        self.client = discord_client
        self.model = db_model
        self.cmd = "!usa"

    @asyncio.coroutine
    def handle_command(self, message, cmd, params):
        logging.info("in USABotCommand.handle_command()")
        yield from self.client.send_message(message.channel, "USA! USA! U S A! U S A! :us:")



class ModifyPingTimespanCommand:
    def __init__(self, db_model, discord_client):
        self.client = discord_client
        self.model = db_model
        self.cmd = "!pingme"

    @asyncio.coroutine
    def handle_command(self, message, cmd, params):
        logging.info("in ModifyPingTimespanCommand.handle_command()")
        if params == "" or not " " in params:
            start_time = int(self.client.authed_users[message.author.id]['start_hour'])
            stop_time = int(self.client.authed_users[message.author.id]['stop_hour'])

            ping_timeframe = ""
            if start_time == 0 and stop_time == 0:
                ping_timeframe = "24h a day"
            else:
                ping_timeframe = "between " + str(start_time) + ":00 and " + str(stop_time) + ":00 UTC (EVE TIME)"


            yield from self.client.send_message(message.channel,
                                                "<@" + message.author.id + "> Please tell me the timespan you would like to be pinged from in hours (UTC/EVE Time). Example: ``!pingme 8 22`` would send pings between 08:00 and 22:00. ``!pingme 0 24`` will reset it to the full day. At the moment you are pinged " + ping_timeframe + "!")
        else: # parse params: should be something like {int1} {int2}
            data = params.split(" ")
            start_hour = int(data[0])
            stop_hour = int(data[1])

            if start_hour == 0 and stop_hour == 24:
                stop_hour = 0

            if start_hour > 24:
                start_hour = 24

            if stop_hour > 24:
                stop_hour = 24

            self.model.update_ping_start_stop_hour(message.author.id, start_hour, stop_hour)

            yield from self.client.send_message(message.channel,
                                                "<@" + message.author.id + "> Okay, I will ping you between " + str(start_hour) + ":00 and " + str(stop_hour) + ":00 UTC (EVE Time)")
