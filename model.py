import pymysql
import pymysql.cursors
import pymysql.connections

import logging

class MyDBModel:
    """ Database model which holds several get / set methods"""

    def __init__(self, db):
        self.db = db # the database

    def set_discord_member_id_for_auth_code(self, auth_code, member_id):
        """ establish relation ship between discord member and auth token"""
        logging.debug("set_discord_member_id_for_auth_code({}, {})". format(auth_code, member_id))

        with self.db.cursor() as cursor:
            # Read a single record
            sql = "UPDATE discord_auth SET discord_member_id = %s WHERE discord_auth_token=%s AND discord_member_id = '' "
            cursor.execute(sql, (member_id, auth_code,))
            cursor.close()
            self.db.commit()


    def get_roles_for_member(self, member_id):
        """ returns an array of discord group IDs for a certain member """
        with self.db.cursor() as cursor:
            sql = """SELECT discord_group_id
            FROM groups g, group_membership m, discord_auth a
            WHERE a.discord_member_id=%s AND g.group_id = m.group_id
            AND m.state <= 1
            AND m.user_id = a.user_id AND g.discord_group_id != 0"""
            cursor.execute(sql, (member_id,))

            roles = []
            for row in cursor:
                role_group_id = str(row['discord_group_id'])
                roles.append(role_group_id)
            cursor.close()
            return roles
        return []


    def is_auth_code_in_table(self, auth_code):
        with self.db.cursor() as cursor:
            # Read a single record
            sql = "SELECT COUNT(*) as cnt_authed from discord_auth WHERE discord_auth_token=%s AND discord_member_id = '' "
            cursor.execute(sql, (auth_code,))
            result = cursor.fetchone()
            retval = False
            if result['cnt_authed'] == 1:
                retval = True
            cursor.close()
            return retval

        return False


    def get_discord_members_character_id(self, member_id):
        """ returns characters name, corporation name, character id based on the member id"""
        with self.db.cursor() as cursor:
            sql = """SELECT c.corp_name, c.character_name, c.character_id from discord_auth a, auth_users b, api_characters c
            WHERE a.user_id = b.user_id AND b.user_id = c.user_id AND c.character_id = b.has_regged_main
            AND a.discord_member_id = %s"""

            cursor.execute(sql, (member_id,))
            row = cursor.fetchone()
            cursor.close()

            return row['character_name'], row['corp_name'], row['character_id']
        return "Unknown", -1, -1


    def get_all_authed_members(self):
        """ returns a list of all authed members as dictionaries """
        with self.db.cursor() as cursor:
            # first, delete all "pending auth users"
            sql = """DELETE FROM discord_auth WHERE discord_auth_token = ''"""
            cursor.execute(sql)
            self.db.commit()

            sql = """SELECT user_id, discord_member_id, discord_auth_token
            FROM discord_auth
            WHERE discord_auth_token <> ''
            AND discord_member_id  IS NOT NULL; """

            cursor.execute(sql)

            authed_users = {}

            for row in cursor:
                authed_users[str(row['discord_member_id'])] = {
                    'user_id': row['user_id'],
                    'auth_token': row['discord_auth_token']
                }
            cursor.close()

            return authed_users
        return {}

    def get_fleetbot_max_message_id(self):
        """ returns the last max message id from fleetbot messages """
        with self.db.cursor() as cursor:
            sql = """SELECT max(id) as max_id FROM irc_ping_history """
            cursor.execute(sql)

            row = cursor.fetchone()
            max_id = row['max_id']

            return max_id
        return 0



    def get_fleetbot_messages(self, last_id=0):
        """ returns a list of fleetbot messages by group """
        with self.db.cursor() as cursor:
            sql = """SELECT id, from_character, `timestamp`, message, groupname
            FROM irc_ping_history WHERE id > %s ORDER BY `timestamp` ASC """
            cursor.execute(sql, {str(last_id),})

            messages_by_group = {}

            for row in cursor:
                group = row['groupname']
                if group not in messages_by_group:
                    messages_by_group[group] = []

                messages_by_group[group].append(
                    {
                        'from': row['from_character'],
                        'timestamp': row['timestamp'],
                        'message': row['message'],
                        'forward': True
                    }
                )
            cursor.close()

            # filter duplicates because fuck spam pings
            for group in messages_by_group.keys():
                msgs = messages_by_group[group]

                last_msg = ""

                for i in range(0, len(msgs)):
                    if msgs[i]['message'] == last_msg:
                        msgs[i]['forward'] = False

                    last_msg = msgs[i]['message']

            return messages_by_group
        return {}
