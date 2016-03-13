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
            AND m.state = 0
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
            sql = "SELECT user_id from discord_auth WHERE discord_auth_token=%s AND discord_member_id = '' "
            cursor.execute(sql, (auth_code,))
            result = cursor.fetchone()
            print(result)
            cursor.close()
            return True

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
