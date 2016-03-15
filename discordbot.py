"""A simple discord.py program to log in and receive and post messages"""

import asyncio
import logging
import datetime
import random

import discord
from model import MyDBModel



# TODO: Remove these static names and put them into a config
fleetbot_ncdot_channel_name = "fleetbot_ncdot"
fleetbot_sm3ll_channel_name = "fleetbot_sm3ll"
fleetbot_supers_channel_name = "fleetbot_supers"


cookie_messages = ["I think you need a :cookie:", "Have a :cookie:",
                   "Have two :cookie:", "Sorry, I am out of cookies! Oh wait, found one! :cookie:",
                   "C is for :cookie:", "https://www.youtube.com/watch?v=Ye8mB6VsUHw",
                   "https://www.youtube.com/watch?v=-qTIGg3I5y8"]


# Create a subclass of Client that defines our own event handlers
# Another option is just to write functions decorated with @client.async_event
class MyDiscordBotClient(discord.Client):
    """ Creates a discord client application based on discord.Client, which
    handles authentication with a pre-defined EvE Online auth database """
    def __init__(self, db, debug_channel_name, auth_website):
        self.db = db # the database
        self.debug_channel_name = debug_channel_name
        self.auth_website = auth_website

        self.model = MyDBModel(self.db)

        self.authed_users = {}

        # Store a couple of destinations for messages
        self.debug_channel = None

        self.group_channels = {}

        self.currently_online_members = {} # a list of online users
        self.roles = {}
        self.everyone_group = None

        # call super class init
        super(MyDiscordBotClient, self).__init__()

    @asyncio.coroutine
    def on_ready(self):
        """Asynchronous event handler for when we are fully ready to interact
        with the server"""
        logging.info("OnReady: Logged in as %s (id: %d)",
                     self.user.name, self.user.id)

        for serv in self.servers:
            print(dir(serv))
            main_server = serv

        # Enumerate the channels. This works over all servers the user is participating in
        print('Channels')
        for channel in self.get_all_channels():
            print(' ', channel.server, channel.name, channel.type)
            if channel.name == self.debug_channel_name:
                logging.info("Found debug channel '%s'", self.debug_channel_name)
                self.debug_channel = channel
            elif channel.name == fleetbot_ncdot_channel_name:
                logging.info("Found fleetbot ncdot channel '%s'", fleetbot_ncdot_channel_name)
                self.group_channels['BC/NORTHERN_COALITION'] = channel
            elif channel.name == fleetbot_sm3ll_channel_name:
                logging.info("Found fleetbot sm3ll channel '%s'", fleetbot_sm3ll_channel_name)
                self.group_channels['BC/BURNING_NAPALM'] = channel

        print("Roles=")
        for role in main_server.roles:
            print(role, role.id, role.name)
            self.roles[role.id] = role

        self.everyone_group = main_server.default_role

        # Send a message to a destination
        yield from self.send_to_debug_channel("I am back {}!".format(str(datetime.datetime.now())))

        # verify users, run this until the end
        loop = asyncio.get_event_loop()
        yield from self.run_my_loop(loop)


    @asyncio.coroutine
    def handle_auth_token(self, author, auth_token):
        """ handles an auth token sent by author """

        logging.info("Verifying auth token '%s'", auth_token)
        if self.model.is_auth_code_in_table(auth_token):
            logging.info("Token is valid!")
            # update member_id for auth_code
            self.model.set_discord_member_id_for_auth_code(auth_token, str(author.id))

            char_data = self.model.get_discord_members_character_id(str(author.id))
            character_name, corp_name, character_id = char_data

            yield from self.send_message(author, "Hello {}! Your corp is {}!".format(character_name, corp_name))
            yield from self.send_to_debug_channel("User {} just authed as {} (corp {}, char id {}) ".format(str(author.name), character_name, corp_name, character_id))

            # assign roles for this user
            tmproles = self.model.get_roles_for_member(str(author.id))
            logging.info("Member %s will be assigned the following roles: %s", author.name, str(tmproles))

            new_roles = [self.roles[str(f)] for f in tmproles]

            # get member based on message.author.id
            member = self.currently_online_members[author.id]
            print(member)

            yield from self.add_roles(member, *new_roles)

        else:
            yield from self.send_message(author, "Sorry, I did not recognize the auth code you sent me!")

    @asyncio.coroutine
    def on_message(self, message):
        """Asynchronous event handler that's called every time a message is
        seen by this client (both, private as well as in channel)"""

        if message.author.id != self.user.id: # message must not come from yourself
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
                logging.info("Message received in channel '" + str(message.channel) + "' from '" + str(message.author) + "': '" + str(message.content) + "'")
                msg = str(message.content)
                if str(message.channel) == "just_cookies":
                    idx = random.randint() % len(cookie_messages)
                    yield from self.send_message(message.channel, cookie_messages[idx])
                elif msg.startswith("!"):
                    # this is most likely a command
                    if msg.startswith("!whoami"):
                        # see who this user is
                        if str(message.author.id) in self.authed_users:
                            # authed
                            char_data = self.model.get_discord_members_character_id(str(message.author.id))
                            yield from self.send_message(message.channel, "@" + str(message.author.name) + " is also known as " + str(char_data))
                        else:
                            yield from self.send_message(message.channel, "@" + str(message.author.name) + " I am sorry, I do not know you!")

        else:
            logging.debug("Ignoring message, because its from ourselves...")

    @asyncio.coroutine
    def verify_member_roles(self, member, member_id):
        """ checks the roles of a single member, and adds or removes them as needed """

        # which roles should this member have
        should_have_roles = self.model.get_roles_for_member(member_id)

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


        roles_to_add = []
        # anything left in should_have_roles should be assigned
        for role_id in should_have_roles:
            role = self.roles[role_id]
            logging.info("Member {} is missing role {} (ID: {}), adding it now".format(member.name, role.name, role.id))
            roles_to_add.append(role)

        if len(roles_to_add) > 0:
            yield from self.add_roles(member, *roles_to_add)


    @asyncio.coroutine
    def run_my_loop(self, loop):
        logging.info("Starting run_my_loop...")

        # store the highest fleetbot message id
        last_fleetbot_msg_id = self.model.get_fleetbot_max_message_id()

        while True:
            # execute verify users
            yield from self.verify_users()
            # execute fleetbot message forwarding
            yield from self.forward_fleetbot_messages(last_fleetbot_msg_id)

            # update highest fleetbot message id
            last_fleetbot_msg_id = self.model.get_fleetbot_max_message_id()

            yield from asyncio.sleep(30)

    @asyncio.coroutine
    def forward_fleetbot_messages(self, last_fleetbot_msg_id):
        """ Method for forwarding messages to fleetbot channels """
        # get up2date messages from database
        messages = self.model.get_fleetbot_messages(last_fleetbot_msg_id)
        # go over all groups
        for group in messages.keys():
            if group in self.group_channels.keys():
                msgs = messages[group]
                logging.info("There are %d messages available for group %s", len(msgs), group)

                for i in range(0, len(msgs)):
                    if msgs[i]['forward']:
                        new_msg = "@everyone " + msgs[i]['message']
                        yield from self.send_to_fleetbot_channel(group, new_msg)
            else:
                logging.info("Error: Could not find group with name '%s' to forward ...", group)


    @asyncio.coroutine
    def verify_users(self):
        # update list of authed members from database
        self.authed_users = self.model.get_all_authed_members()

        newOnlineMembers = {}
        allOnlineMembers = {}

        number_authed_users = 0

        logging.info("Checking all members that are connected on server...")


        # iterate over all members:
        for member in self.get_all_members():
            if member.id == self.user.id:
                continue # ship yourself

            if str(member.status) == 'offline':
                continue # no need to process offline members for now

            member_id = str(member.id)

            # store in all online members
            allOnlineMembers[member_id] = member

            # if this user already known/authed?
            if member_id in self.authed_users:
                number_authed_users += 1

                if member_id not in self.currently_online_members:
                    logging.info("User {} just connected, already authed!".format(member.name))
                    self.send_to_debug_channel("User {} just connected, already authed!".format(member.name))
                    newOnlineMembers[member_id] = member

                # else: we already know this user, user is authed. check for any role updates
                yield from self.verify_member_roles(member, member_id)

            else: # we do not know this user
                # make sure this user has no roles (other than everyone)
                if len(member.roles) > 1:
                    logging.info("Found non-authed member {} with roles {}, removing them...".format(member.name, member.roles))
                    roles_to_remove = []
                    for role in member.roles:
                        if role != self.everyone_group:
                            roles_to_remove.append(role)
                    # remove those roles
                    yield from self.remove_roles(member, *roles_to_remove)


                if member_id not in self.currently_online_members:
                    logging.info("A new user connected to the server: Name='{}', Status='{}', ID='{}', Server='{}'".format(member.name, member.status, member_id, member.server))
                    newOnlineMembers[member_id] = member

                    # this user just got online and is not authed! ask this user to auth
                    yield from self.send_message(member,
                        """Hi! You need to authenticate to be able to use this Discord server.
                        Please go to {} to obtain your authorization token, and then just message it to me!""".format( self.auth_website))
                    self.send_to_debug_channel("User {} just connected, asking user to auth...".format(member.name))
                else:
                    # this user has been online for some time, no need to ask to auth again (I guess)
                    logging.info("Waiting on auth for user: Name='{}', Status='{}', ID='{}', Server='{}'".format(member.name, member.status, member_id, member.server))

        # now each member that has been in currently_online_members needs to be checked if still online
        for member_id in self.currently_online_members.keys():
            if member_id not in allOnlineMembers:
                member = self.currently_online_members[member_id]
                logging.info("Member %s went offline!", member.name)

        self.currently_online_members = allOnlineMembers
    # end everify users


    @asyncio.coroutine
    def send_to_debug_channel(self, msg):
        """ sends a message to the debug channel """
        yield from self.send_message(self.debug_channel, "DEBUG: " + msg)


    @asyncio.coroutine
    def send_to_fleetbot_channel(self, group, msg):
        """ sends a message to a fleetbot channel """
        if group in self.group_channels.keys():
            yield from self.send_message(self.group_channels[group], msg)
