"""A simple discord.py program to log in and receive and post messages"""

import sys
import asyncio
import logging
import random
from datetime import datetime
import traceback

from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

import discord
from model import MyDBModel

import bot_commands
from bot_commands import AbstractBotCommand

import importlib


cookie_messages = ["I think you need a :cookie:", "Have a :cookie:",
                   "Have two :cookie:", "Sorry, I am out of cookies! Oh wait, found one! :cookie:",
                   "C is for :cookie:", "https://www.youtube.com/watch?v=Ye8mB6VsUHw",
                   "https://www.youtube.com/watch?v=-qTIGg3I5y8", "I think you had enough!",
                   "Okay, but only one more :cookie:!", "I like cookies too! :thumbsup:",
                   "Please wait, while we process your request...", "Free Cookies for everyone! :cookie: :cookie: :cookie: :cookie: :cookie:",
                   "Omnomnomnomnom... You want a :cookie: too?", "Sorry, but Deathwhisper ate all my cookies :(",
                   "Are you sure?", "The cookie is a lie!", "Ofcourse! Here is a :cookie: for you!",
                   "Share your :cookie: with a friend!", "Cookie? :cookie:", "NO!",
                   "http://i4.manchestereveningnews.co.uk/incoming/article10580003.ece/ALTERNATES/s615/JS47622759.jpg",
                   "Waiting on a cookie delivery...", "Nobody ever gives me cookies :(",
                   "Omnomnomnom sorry, that was the last one!"]

# Create a subclass of Client that defines our own event handlers
# Another option is just to write functions decorated with @client.async_event
class MyDiscordBotClient(discord.Client):
    """ Creates a discord client application based on discord.Client, which
    handles authentication with a pre-defined EvE Online auth database """
    def __init__(self, db, debug_channel_name, auth_website, main_server_id,
                 time_dep_groups, fleetbot_channels, post_expensive_killmails_to,
                 run_verify_user_loop=True):
        self.db = db # the database
        self.debug_channel_name = debug_channel_name
        self.auth_website = auth_website

        # store the database model
        self.model = MyDBModel(self.db)

        self.authed_users = {}

        # Store a couple of destinations for messages
        self.debug_channel = None

        self.group_channels = {}

        self.post_expensive_killmails_to = post_expensive_killmails_to
        self.post_expensive_killmails_channel = None

        self.currently_online_members = {} # a list of online users
        self.roles = {}
        self.everyone_group = None

        self.main_server_id = main_server_id
        self.main_server = None

        # store the time when the bot started
        self.start_time = datetime.now()

        self.timedep_group_assignment = {}
        self.fleetbot_channels = {}

        self.verify_users_loop = None
        self.forward_fleetbot_loop = None
        self.forward_zkill_loop = None

        self.do_verify_users = run_verify_user_loop


        if time_dep_groups != "":
            logging.info("Parsing time_dep_groups=" + time_dep_groups)
            # parse time dependent groups
            assignments = time_dep_groups.split(",")
            for ass in assignments:
                tmpgroups = ass.split('->')
                groupid1 = tmpgroups[0]
                groupid2 = tmpgroups[1]
                if groupid2 != "0":
                    self.timedep_group_assignment[groupid1] = groupid2

        if fleetbot_channels != "":
            logging.info("Parsing fleetbot_channels=" + fleetbot_channels)
            assignments = fleetbot_channels.split(",")
            for ass in assignments:
                tmpchannels = ass.split('->')
                # fleetbot_ncdot->BC/NORTHERN_COALITION
                channel_name = tmpchannels[0]
                broadcast_name = tmpchannels[1]
                # e.g. fleetbot_supers->BC/SUPERCARRIERS; TITANS
                if channel_name not in self.fleetbot_channels:
                    self.fleetbot_channels[channel_name] = [ broadcast_name ]
                else:
                    self.fleetbot_channels[channel_name].append(broadcast_name)


        # call super class init
        super(MyDiscordBotClient, self).__init__()

    @asyncio.coroutine
    def on_ready(self):
        """Asynchronous event handler for when we are fully ready to interact
        with the server"""
        logging.info("OnReady: Logged in as %s (id: %s)",
                     self.user.name, self.user.id)

        logging.info("Checking which servers we are connected to")
        for serv in self.servers:
            if serv.id == self.main_server_id:
                self.main_server = serv
                print("Found main server! ", serv)
            else:
                print("skipping server ", serv)

        # update list of available channels
        self.update_channels(self.main_server)

        # update list of available roles
        self.update_roles(self.main_server)

        # Send a message to a destination
        yield from self.send_to_debug_channel("I am back {}!".format(str(datetime.now())))

        AbstractBotCommand.import_bot_commands(self.model, self)

        # verify users, run this until the end
        logging.info("starting async loops...")
        loop = asyncio.get_event_loop()
        self.verify_users_loop = asyncio.async(self.verify_users(self.main_server))
        if len(self.fleetbot_channels) > 0:
            logging.info("Starting new fleetbot loop, checking old loop before")
            logging.info(self.forward_fleetbot_loop)

            self.forward_fleetbot_loop = asyncio.async(self.forward_fleetbot_messages())

        # start forward zkill loop
        if self.forward_zkillboard_expensive_killmails != "":
            self.forward_zkill_loop = asyncio.async(self.forward_zkillboard_expensive_killmails())

    def stop_additional_loops(self):
        """ stops verify users loop and forward fleetbot loop """
        if self.verify_users_loop:
            logging.info("stopping verify user loop")
            self.verify_users_loop.cancel()
        if self.forward_fleetbot_loop:
            logging.info("stopping forward fleetbot loop")
            self.forward_fleetbot_loop.cancel()
        if self.forward_zkill_loop:
            logging.info("stopping forward zkill loop")
            self.forward_zkill_loop.cancel()


    def update_channels(self, server):
        """ Updates the list of channels """
        logging.info("Updating channel list")

        for channel in server.channels:
            logging.info("Found channel " + str(channel.server) + "," + str(channel.name) + "," + str(channel.type))

            if channel.name == self.debug_channel_name:
                logging.info("Found debug channel '%s'", self.debug_channel_name)
                self.debug_channel = channel
            elif channel.name in self.fleetbot_channels:
                bckeys = self.fleetbot_channels[channel.name]
                for bckey in bckeys:
                    logging.info("Found Fleetbot Channel '%s', assigning to broadcast key '%s'", channel.name, bckey)
                    if bckey not in self.group_channels:
                        self.group_channels[bckey] = [ channel ]
                    else:
                        self.group_channels[bckey].append(channel)
            if channel.name == self.post_expensive_killmails_to:
                self.post_expensive_killmails_channel = channel


    def update_roles(self, server):
        """ Update the list of roles """
        self.roles.clear()

        for role in server.roles:
            logging.info("Found role %s (id: %s, name: %s)", role, role.id, role.name)
            self.roles[role.id] = role

        self.everyone_group = server.default_role


    def get_roles_str(self, server):
        """ Returns a list of roles as a string """
        retstr = ""
        for role in self.roles:
            retstr = retstr + str(role) + " " + str(self.roles[role].name)  + ", "

        return retstr

    def clear_online_members(self):
        """ clears the list of online members - mainly for debug purpose """
        self.currently_online_members.clear()


    @asyncio.coroutine
    def handle_auth_token(self, author, auth_token):
        """ handles an auth token sent by author """

        logging.info("Verifying auth token '%s' for user %s", auth_token, str(author.name))
        if self.model.is_auth_code_in_table(auth_token):
            logging.info("Token is valid!")
            # update member_id for auth_code
            self.model.set_discord_member_id_for_auth_code(auth_token, str(author.id))

            char_data = self.model.get_discord_members_character_id(str(author.id))
            character_name, corp_name, character_id = char_data

            yield from self.send_message(author, "Hello {}! You are now authed, your corp is {}!".format(character_name, corp_name))
            yield from self.send_to_debug_channel("User {} just authed as {} (corp {}, char id {}) ".format(str(author.name), character_name, corp_name, character_id))

            # assign roles for this user
            tmproles = self.model.get_roles_for_member(str(author.id))
            logging.info("Member %s will be assigned the following roles: %s", author.name, str(tmproles))

            new_roles = [self.roles[str(f)] for f in tmproles]

            # get member based on message.author.id
            member = self.currently_online_members[author.id]

            yield from self.add_roles(member, *new_roles)
        else:
            logging.error("Could not find token '%s' in database...", auth_token)
            yield from self.send_message(author, "Sorry, I did not recognize the auth code you sent me!")
            yield from self.send_to_debug_channel("User {} entered auth key {}, but I could not find it in database".format(author.name, auth_token))

    @asyncio.coroutine
    def on_message(self, message):
        """Asynchronous event handler that's called every time a message is
        seen by this client (both, private as well as in channel)"""

        if message.author.id != self.user.id:  # message must not come from yourself
            if "Direct Message" in str(message.channel):
                logging.info("Private message received from user '%s': '%s'",
                             str(message.author), str(message.content))
                # auth token always start with "auth="
                if str(message.content).startswith("auth="):
                    # check that this user is not already authed
                    if str(message.author.id) in self.authed_users:
                        logging.error("User %s (id=%s) tried to auth, but is already authed!",
                                      message.author.name, str(message.author.id))

                        yield from self.send_message(message.author,
                                                     "ERROR: You are trying to auth, but you already authed before...")
                        yield from self.send_to_debug_channel("ERROR User {} (id: {}) tried to auth twice...".format(message.author, message.author.id))
                    else:
                        logging.info("Auth token received from user '%s' (ID: %s): '%s'", str(message.author), str(message.author.id), str(message.content))
                        # remove "auth=" from that string"
                        auth_code = str(message.content).replace("auth=", "")

                        yield from self.send_to_debug_channel("User {} just entered an auth token, verifying...".format(message.author))

                        yield from self.handle_auth_token(message.author, auth_code)
                else:
                    yield from self.send_message(message.author,
                                                 "I am sorry, I did not understand what you said.")
            else:
                #logging.info("Message received in channel '" + str(message.channel) + "' from '" + str(message.author) + "': '" + str(message.content) + "'")
                msg = str(message.content)
                if str(message.channel) == "just_cookies":
                    idx = random.randint(0,len(cookie_messages)) % len(cookie_messages)
                    yield from self.send_message(message.channel, cookie_messages[idx])
                elif msg.startswith("!reload_commands") and message.channel == self.debug_channel:
                    logging.info("trying to reload bot commands...")
                    importlib.reload(bot_commands)
                    AbstractBotCommand.import_bot_commands(self.model, self)
                    avail_cmds = " ".join(AbstractBotCommand.available_commands.keys())
                    yield from self.send_to_debug_channel("Commands reloaded! Available commands: " + avail_cmds)
                elif msg.startswith("!restart") and message.channel == self.debug_channel:
                    logging.info("restarting the bot...")
                    raise KeyboardInterrupt
                elif msg.startswith("!clear_online_members") and message.channel == self.debug_channel:
                    logging.info("Trying to clear online users...")
                    self.clear_online_members()
                    yield from self.send_to_debug_channel("Cleared currently online members")
                elif "I LOVE" in msg.upper():
                    yield from self.send_message(message.channel, "I am sure you do ;) :panda_face: ")
                elif "I HATE" in msg.upper():
                    yield from self.send_message(message.channel, "Haters gonna hate!")
                elif "I DISLIKE" in msg.upper():
                    yield from self.send_message(message.channel, "I guess that's a valid opionion!")
                elif "L0L" in msg.upper():
                    yield from self.send_message(message.channel, ":laughing: :laughing: :laughing: :laughing: :laughing: ")
                elif msg.startswith("!"):
                    yield from AbstractBotCommand.handle_msg(message)
        # else:
        #    logging.debug("Ignoring message, because its from ourselves...")

    @asyncio.coroutine
    def verify_member_roles(self, member, member_id):
        """ checks the roles of a single member, and adds or removes them as needed """
        try:
            # which roles should this member have
            should_have_roles = self.model.get_roles_for_member(member_id)

            ping_start_hour = int(self.authed_users[member_id]['start_hour'])
            ping_stop_hour = int(self.authed_users[member_id]['stop_hour'])

            cur_hour = datetime.utcnow().hour

            do_time_dep_roles = False

            # case 0: user does not care about any time dependency
            if ping_start_hour == 0 and ping_stop_hour == 0:
                do_time_dep_roles = True # always assign
            else:
                # case 1: ping_start_hour < ping_stop_hour, e.g., between 8 and 22 hours
                if ping_start_hour < ping_stop_hour and cur_hour >= ping_start_hour and cur_hour < ping_stop_hour:
                    do_time_dep_roles = True

                # case 2: ping_start_hour > ping_stop_hour, e.g., between 16 and 4 hours
                if ping_start_hour > ping_stop_hour and (cur_hour >= ping_start_hour or cur_hour < ping_stop_hour):
                    do_time_dep_roles = True


            if do_time_dep_roles:
                for role in should_have_roles:
                    if role in self.timedep_group_assignment:
                        should_have_roles.append(self.timedep_group_assignment[role])

            # check if there are any roles that we need to remove
            roles_to_remove = []

            for role in member.roles:
                # needs to keep the everyone group
                if role == self.everyone_group:
                    continue
                if str(role.id) not in should_have_roles:
                    logging.info("Member {} has role {} (ID: {}), but should not have it... removing".format(member.name, role.name, role.id))
                    roles_to_remove.append(role)
                else:
                    should_have_roles.remove(role.id)

            # remove those roles if neccessary
            if len(roles_to_remove) > 0:
                yield from self.remove_roles(member, *roles_to_remove)
                yield from asyncio.sleep(0.5)


            roles_to_add = []
            # anything left in should_have_roles should be assigned
            for role_id in should_have_roles:
                if role_id in self.roles:
                    role = self.roles[role_id]
                    logging.info("Member {} is missing role {} (ID: {}), adding it now".format(member.name, role.name, role.id))
                    roles_to_add.append(role)
                else:
                    logging.error("Member %s is missing role %s, tried to add it but I dont know that role...", member.name, role_id)

            if len(roles_to_add) > 0:
                yield from self.add_roles(member, *roles_to_add)
                yield from asyncio.sleep(0.5)
        except:
            logging.info("Caught an exception in verify_member_roles... Probably rate limited?")
            tb = traceback.format_exc()
            logging.info(str(sys.exc_info()[0]))
            logging.info(tb)
            yield from asyncio.sleep(3)


    @asyncio.coroutine
    def post_killmail_to_chan(self, external_kill_ID):
        """ Method for forwarding a zkill link to post_expensive_killmails_channel"""
        if self.post_expensive_killmails_channel != None and external_kill_ID != 0:
            yield from self.send_message(self.post_expensive_killmails_channel, "https://zkillboard.com/kill/" + str(external_kill_ID) + "/")

    def forward_zkillboard_expensive_killmails(self):
        logging.info("starting zkillboard forward loop")

        last_id = 0

        while True:
            if self.post_expensive_killmails_channel != None:
                killmail_id = self.model.get_expensive_killmails(last_id)
                if killmail_id != 0:
                    logging.info("returned killmail_id=" + str(killmail_id))
                    yield from self.post_killmail_to_chan(killmail_id)
                    last_id = killmail_id

            yield from asyncio.sleep(30)


    def forward_fleetbot_messages(self):
        """ Method for forwarding messages to fleetbot channels """
        logging.info("starting forward_fleetbot_messages loop")
        try:

            # store the highest fleetbot message id
            last_fleetbot_msg_id = self.model.get_fleetbot_max_message_id()

            while True:
                logging.info("Checking if there are new messages to forward for fleetbot")
                # get up2date messages from database
                messages = self.model.get_fleetbot_messages(last_fleetbot_msg_id)
                logging.info("Found %d messages with the following keys: %s", len(messages.keys()), str(messages.keys()))

                # go over all groups
                for group in messages.keys():
                    logging.info("In for loop: group='%s'", group)
                    if group in self.group_channels.keys():
                        # get messages for group
                        msgs = messages[group]
                        logging.info("There are %d messages available for group '%s'", len(msgs), group)

                        for i in range(0, len(msgs)):
                            if msgs[i]['forward']:
                                new_msg = "@everyone " + msgs[i]['from'] + ": " + msgs[i]['message']
                                logging.info("Fleetbot(%s): %s", group, new_msg)
                                try:
                                    yield from self.send_to_fleetbot_channel(group, new_msg)
                                except:
                                    logging.error("Caught exception while forwarding: " + str(sys.exc_info()[0]))
                    else:
                        logging.info("Error: Could not find group with name '%s' to forward ...", group)

                # update highest fleetbot message id
                last_fleetbot_msg_id = self.model.get_fleetbot_max_message_id()
                logging.info("Last Fleetbot message id = " + str(last_fleetbot_msg_id))

                yield from asyncio.sleep(30)
            # end while
        except:
            tb = traceback.format_exc()
            logging.info(str(sys.exc_info()[0]))
            logging.info(tb)

            yield from self.send_to_debug_channel("An error happened: " + str(sys.exc_info()[0]) + "\n" + str(tb))


            # also forward this to the debug channel
    # end def forward_fleetbot_messages


    def verify_users(self, server):
        """ verify that groups of all users currently online are valid"""
        logging.info("Start loop: Verifying roles of users")

        while self.do_verify_users:
            # update list of authed members from database
            self.authed_users = self.model.get_all_authed_members()
            #logging.info("Received %s authed users from database", len(self.authed_users))

            newOnlineMembers = {}
            allOnlineMembers = {}

            number_authed_users = 0

            logging.info("Checking all members that are connected on server...")


            # iterate over all members:
            for member in server.members:
                if member.id == self.user.id:
                    continue # ship yourself

                #if str(member.status) == 'offline':
                #    continue # no need to process offline members for now

                member_id = str(member.id)

                # store in all online members
                allOnlineMembers[member_id] = member

                # if this user already known/authed?
                if member_id in self.authed_users:
                    number_authed_users += 1

                    if member_id not in self.currently_online_members:
                        logging.info("User %s just connected, already authed!", member.name)
                        newOnlineMembers[member_id] = member

                    # else: we already know this user, user is authed. check for any role updates
                    yield from self.verify_member_roles(member, member_id)

                else: # we do not know this user
                    # make sure this user has no roles (other than everyone)
                    if len(member.roles) > 1:
                        logging.info("Found non-authed member %s with roles %s, removing them...", member.name, member.roles)
                        roles_to_remove = []
                        for role in member.roles:
                            if role != self.everyone_group:
                                roles_to_remove.append(role)
                        # remove those roles
                        yield from self.remove_roles(member, *roles_to_remove)

                    # no need to go any further with offline users
                    if str(member.status) == 'offline':
                        continue

                    if member_id not in self.currently_online_members:
                        logging.info("A new user connected to the server: Name='{}', Status='{}', ID='{}', Server='{}'".format(member.name, member.status, member_id, member.server))
                        newOnlineMembers[member_id] = member

                        # this user just got online and is not authed! ask this user to auth
                        try:
                            yield from self.send_message(member,
                                                     """Hi! You need to authenticate to be able to use this Discord server. Please go to {} to obtain your authorization token (starting with auth=), and then just message the full token (including auth=) to me!""".format(self.auth_website))
                        except:
                            logging.info("Got an error while sending message to new user: " + sys.exc_info()[0])


                        yield from self.send_to_debug_channel("Non authed user {} just connected, asking user to auth...".format(member.name))
                    else:
                        # this user has been online for some time, no need to ask to auth again (I guess)
                        logging.info("Waiting on auth for user: Name='%s', Status='%s', ID='%s', Server='%s'",member.name, member.status, member_id, member.server)

            # now each member that has been in currently_online_members needs to be checked if still online
            for member_id in self.currently_online_members.keys():
                if member_id not in allOnlineMembers:
                    member = self.currently_online_members[member_id]
                    logging.info("Member %s went offline!", member.name)

            self.currently_online_members = allOnlineMembers

            yield from asyncio.sleep(30)
        # end while
    # end everify users


    @asyncio.coroutine
    def send_to_debug_channel(self, msg):
        """ sends a message to the debug channel """
        yield from self.send_message(self.debug_channel, "DEBUG: " + msg)


    @asyncio.coroutine
    def send_to_fleetbot_channel(self, group, msg):
        """ sends a message to a fleetbot channel """
        if group in self.group_channels:
            logging.info("send_to_fleetbot_channel: Sending to the following channels: " + str(self.group_channels[group]))
            for channel in self.group_channels[group]:
                logging.info("send_to_fleetbot_channel(" + str(group) + ", msg): channel = " + str(channel))
                yield from self.send_message(channel, msg)
