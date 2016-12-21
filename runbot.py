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
import logging.handlers
import time
import websockets.exceptions

import pymysql
import pymysql.cursors
import pymysql.connections

import discord

from  discordbot import MyDiscordBotClient

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")

logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
# make sure to log to console and file simultaneously
rootLogger = logging.getLogger()


# Add the log message handler to the logger and configure log rotation
fileHandler = logging.handlers.RotatingFileHandler(
    "logs/discord.log.txt",
    maxBytes=2097152,  # 2 Megabyte
    backupCount=99  # 99 log files allowed
)

fileHandler.setFormatter(logFormatter)
rootLogger.addHandler(fileHandler)



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
            logging.info('Stopping...')
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
        stop = False
        while not stop and i < 1:
            logging.info("Trying to connect bot (run %d)", i)
            client = None
            try:
                logging.info('Init MyDiscordBotClient')
                client = MyDiscordBotClient(self.db,
                                            config.get('Bot', 'debug_channel_name'),
                                            config.get('Bot', 'auth_website'),
                                            config.get('Discord', 'discordserverid'),
                                            config.get('Bot', 'time_dependent_groups'),
                                            config.get('Bot', 'fleetbot_channels'),
                                            config.get('Bot', 'post_expensive_killmails_to'),
                                            run_verify_user_loop=True  # ToDo: set this to true
                                            )
                logging.info("Calling client.run()")
                # use run_until_complete manually, as described in client.run()
                client.loop.run_until_complete(client.start(config.get('Discord', 'discorduser'),
                           config.get('Discord', 'discordpass')))
                # if this finished, the bot either crashed OR user pressed ctrl+c (caught by keyboardinterrupt)

                logging.info("client.run() finished! Trying to stop additional loops")
                client.stop_additional_loops()

                # in case we are continuing: get a new event loop
                logging.info("getting a new event loop")
                client.loop = asyncio.new_event_loop()
            except KeyboardInterrupt:
                logging.info("Got Keyboard Interrupt (loop interruped with CTRL-C), exiting...")
                client.loop.run_until_complete(client.logout())
                stop = True
            except (discord.ClientException, websockets.exceptions.InvalidState, RuntimeError) as e:
                logging.info("Got ClientException while MyDiscordBotClient.run(): " + str(e))
                logging.error(e, exc_info=True)
            except:
                logging.info("Got an unhandled exception while MyDiscordBotClient.run()")
                logging.exception("Exception info")
            finally: # close client connection
                logging.info("In finally: stopping loop etc...")
                if client:
                    client.stop_additional_loops()
                    client.loop.close()

            if not stop:
                logging.error("Bot crashed? Not sure... waiting 60 seconds before doing anything else")
                time.sleep(60) # wait 30 seconds, then reconnect
                i += 1
            else:
                logging.info("Definately stopping bot...")
        logging.info("Gracefully shutting down...")


    def connectToDB(self, args, config):
        """ connect to the database as specified in the config file
        :return the database object
        :rtype pymysql.connections.Connection
        """
        if self.db == None:
            # try connection to the database
            logging.debug("Connecting to database")
            try:
                self.db = pymysql.connect(host=config.get('Database', 'dbhost'),
                                             user=config.get('Database', 'dbuser'),
                                             password=config.get('Database', 'dbpass'),
                                             db=config.get('Database', 'dbname'),
                                             charset='utf8mb4',
                                             cursorclass=pymysql.cursors.DictCursor)
                logging.info("Successfully connected to database")
                return self.db
            except:
                logging.error("Failed to connect to database", exc_info=True)
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
        try:
            app = MyBotApp()
        except:
            logging.error("Unhandled Exception got out...", exc_info=True)

        print("Removing discord.lock")
        os.remove("discord.lock")
    print("closed")
