import pymysql
import pymysql.cursors
import pymysql.connections

import logging

class MyDBModel:
    """ Database model which holds several get / set methods"""

    def __init__(self, db):
        self.db = db # the database

    def check_db_connection(self):
        sq = "SELECT NOW()"
        with self.db.cursor() as cursor:
            try:
                cursor.execute( sq )
            except pymysql.Error as e:
                if e.errno == 2006:
                    logging.error("Database connection failed, trying to reconnect")
                    return self.db.connect()
                else:
                    logging.error("Database connection failed... could not connect to database...")
                    return False

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
            if result['cnt_authed'] == 1 or result['cnt_authed'] == "1":
                retval = True
            else:
                logging.error("Auth name not found? cnt_authed=" + str(result['cnt_authed']))
                logging.error("auth_code='" + auth_code + "'")
            cursor.close()
            return retval
        logging.error("is_auth_code_in_table: outside of where we should be...")
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
        self.check_db_connection()

        with self.db.cursor() as cursor:
            # first, delete all "pending auth users"
            sql = """DELETE FROM discord_auth WHERE discord_auth_token = ''"""
            cursor.execute(sql)
            self.db.commit()

            sql = """SELECT user_id, discord_member_id, discord_auth_token,
            ping_start_hour, ping_stop_hour
            FROM discord_auth
            WHERE discord_auth_token <> ''
            AND discord_member_id  IS NOT NULL; """

            cursor.execute(sql)

            authed_users = {}

            for row in cursor:
                authed_users[str(row['discord_member_id'])] = {
                    'user_id': row['user_id'],
                    'auth_token': row['discord_auth_token'],
                    'start_hour': row['ping_start_hour'],
                    'stop_hour': row['ping_stop_hour']
                }
            cursor.close()

            return authed_users
        return {}

    def update_ping_start_stop_hour(self, discord_member_id, start_hour, stop_hour):
        """ updates discord_auth.ping_start_hour and ping_stop_hour """
        with self.db.cursor() as cursor:
            sql = """UPDATE discord_auth SET ping_start_hour = %s, ping_stop_hour = %s
            WHERE discord_member_id = %s"""

            cursor.execute(sql, (str(start_hour), str(stop_hour), str(discord_member_id),))
            cursor.close()

            self.db.commit()

    def get_fleetbot_max_message_id(self):
        """ returns the last max message id from fleetbot messages """
        with self.db.cursor() as cursor:
            sql = """SELECT max(id) as max_id FROM irc_ping_history """
            cursor.execute(sql)

            row = cursor.fetchone()
            max_id = row['max_id']

            return max_id
        return 0


    def find_pos(self, solar_system_id=None):
        """ Returns a list of POSes in that system """

        sql = """select s.typeID, pos_state, d.itemName FROM starbases s,
        eve_staticdata.mapDenormalize d WHERE state=0  AND d.itemID = s.moonID"""

        if solar_system_id != None:
            sql += " AND s.locationID = str(solar_system_id)"

        with self.db.cursor() as cursor:
            number = cursor.execute(sql)
            moon_names = []
            if number > 0:
                for row in cursor:
                    moon_names.append(row['itemName'])
                cursor.close()
                return moon_names
            else:
                return []


    def find_system(self, system_str):
        """ Returns a system and region name based on system_str (partial) """
        system_str = system_str + "%"
        sql = """SELECT regionName, solarSystemID, solarSystemName
            FROM eve_staticdata.mapSolarSystems s, eve_staticdata.mapRegions r
            WHERE r.regionID = s.regionID and `solarSystemName` LIKE %s"""
        with self.db.cursor() as cursor:
            number = cursor.execute(sql, (system_str,))
            if number == 1:
                result = cursor.fetchone()
                cursor.close()
                return {'regionName': result['regionName'], 'solarSystemID': result['solarSystemID'], 'solarSystemName': result['solarSystemName']}
            elif number == 0:
                cursor.close()
                return None
            else:
                system_names = []
                for row in cursor:
                    system_names.append(row['solarSystemName'] + " (" + row['regionName'] + ")")
                cursor.close()
                return system_names


    def get_expensive_killmails(self, last_id=0):
        """ returns the most expensive kill within the last 3 hours """
        sql = """SELECT external_kill_ID
            FROM  `kills_killmails`
            WHERE zkb_total_value > 2000000000 AND external_kill_ID > %s
            AND TIMESTAMPDIFF(HOUR,kill_time, now()) < 3
            ORDER BY kill_time DESC
            LIMIT 0 , 1"""
        with self.db.cursor() as cursor:
            cursor.execute(sql, (str(last_id),))
            try:
                result = cursor.fetchone()
                return result['external_kill_ID']
            except:
                return 0
        return 0


    def get_fleetbot_messages(self, last_id=0):
        """ returns a list of fleetbot messages by group """
        with self.db.cursor() as cursor:
            sql = """SELECT id, from_character, `timestamp`, message, groupname
            FROM irc_ping_history WHERE id > %s ORDER BY `timestamp` ASC """
            cursor.execute(sql, (str(last_id),))

            messages_by_group = {}

            msg_cnt = 0

            for row in cursor:
                group = row['groupname']
                if group not in messages_by_group:
                    messages_by_group[group] = []

                messages_by_group[group].append(
                    {
                        'id': row['id'],
                        'from': row['from_character'],
                        'timestamp': row['timestamp'],
                        'message': row['message'],
                        'forward': True
                    }
                )
                msg_cnt += 1
            # end for
            cursor.close()

            if msg_cnt > 0:
                logging.info("Fleetbot: There are %d message to be sent!", msg_cnt)

            duplicates = 0
            # filter duplicates because fuck spam pings
            for group in messages_by_group.keys():
                msgs = messages_by_group[group]

                last_msg = ""

                for i in range(0, len(msgs)):
                    if msgs[i]['message'] == last_msg:
                        msgs[i]['forward'] = False
                        duplicates += 1

                    last_msg = msgs[i]['message']

            if duplicates > 0:
                logging.info("Fleetbot: Found %d duplicates!", duplicates)

            return messages_by_group
        return {}
