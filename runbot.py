#!/usr/bin/env python3
""" This is the main file for the discord bot. Please read README.md"""

# using https://github.com/Rapptz/discord.py
# install:
# sudo apt-get install python-virtualenv
#
# 1. create virtual environment for python 3.4
#  virtualenv --python=python3.4 .
# 2. activate it
#  source bin/activate
# 3. run pip install git+https://github.com/Rapptz/discord.py@async
# 4. put this file in
# 5. python test.py
# 6. ????
# 7. profit


import configparser, argparse
import sys, os
import string
import asyncio
import logging
import time

import pymysql
import pymysql.cursors
import pymysql.connections

import discord

from  discordbot import MyDiscordBotClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')


class MyBotApp:
    """ The Main Bot Application, which reads the config files (defaults.cfg),
    establishes a database connection (using pymysql) and starts the discord
    client (defined in discordbot) """
    def __init__(self):
        """ Initialize by parsing the commandline arguments and processing the
        config files """
        args = self.parseArguments()
        config = self.processConfigFiles(args)


        self.db = None # type: pymysql.connections.Connection
        if self.connectToDB(args, config) == None:
            return # could not connect to DB, exiting...

        # start bot, close with ctrl-c
        self.startBot(args, config, self.db)



    def __del__(self):
        """ destruct the app - disconnect from DB """
        logging.info("Stopping bot app")
        if self.db != None:
            self.db = None


    def startBot(self, args, config, db):
        """ Run the client in a blocking call that logs in and runs the event loop, exists on Ctrl-C"""

        logging.info("Starting bot now (stop with CTRL-C)...")


        i=0
        while True:
            logging.info("Trying to connect bot (run %d)", i)
            try:
                client = MyDiscordBotClient(self.db,
                                            config.get('Bot', 'debug_channel_name'),
                                            config.get('Bot', 'auth_website'),
                                            config.get('Discord', 'discordserverid'))
                client.run(config.get('Discord', 'discorduser'),
                           config.get('Discord', 'discordpass'))
            except (discord.ClientException, websockets.exceptions.InvalidState) as e:
                logging.exception("Got Exception: ")

            logging.info("Bot crashed? Not sure... waiting 30 seconds before doing anything else")
            time.sleep(30) # wait 30 seconds, then reconnect
            i += 1



    def connectToDB(self, args, config):
        """ connect to the database as specified in the config file
        :return the database object
        :rtype pymysql.connections.Connection
        """
        if self.db == None:
            # try connection to the database
            logging.info("Connecting to database")
            try:
                self.db = pymysql.connect(host=config.get('Database', 'dbhost'),
                                             user=config.get('Database', 'dbuser'),
                                             password=config.get('Database', 'dbpass'),
                                             db=config.get('Database', 'dbname'),
                                             charset='utf8mb4',
                                             cursorclass=pymysql.cursors.DictCursor)

                return self.db
            except:
                logging.error("Failed to connect to database")
                return None
        else: # oh we already have it, fine
            return self.db


    def parseArguments(self):
        """ Parses arguments using argparse.ArgumentParser and returns a list"""
        parser = argparse.ArgumentParser(description="BigSakos Discord Bot")

        parser.add_argument('--config', help='Specify the config file to use',
                            default='defaults.cfg')


        return parser.parse_args()

    def processConfigFiles(self, args):
        """ opens the config file from args.config (--config) """
        # open config file (first defaults, then the specified one)
        logging.info("Reading defaults.cfg config file first")

        config = configparser.ConfigParser()
        config.readfp(open('defaults.cfg'))

        if args.config != "defaults.cfg":
            logging.info("Using config file {}".format(args.config))
            config.readfp(open('local.cfg'))
        return config



# main
if __name__ == "__main__":
    # check for lock file
    if os.path.isfile("discord.lock"):
        print("Lock file discord.lock exists, exiting...")
        exit(-2)
    else:
        fp = open("discord.lock", "w")
        fp.write("running")
        fp.close()
        app = MyBotApp()

        os.remove("discord.lock")
