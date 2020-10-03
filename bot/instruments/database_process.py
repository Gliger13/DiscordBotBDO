import datetime
import logging

from pymongo import MongoClient

from instruments import tools
from instruments.raid import Raid
from instruments.tools import MetaSingleton
from settings import settings

module_logger = logging.getLogger('my_bot')


class Error(Exception):
    """Base class for exceptions in this module."""
    pass


class UserExists(Error):
    """
    Exception raised when user exist in database

    Attributes:
        expression -- input expression in which the error occurred
    """

    def __init__(self, expression):
        self.expression = expression


class Database(metaclass=MetaSingleton):
    """
    Connect with Mongo Database
    """
    _cluster = None

    def _connect(self):
        if not self._cluster:
            module_logger.debug('Initialisation database.')
            self._cluster = MongoClient(settings.BD_STRING)[settings.CLUSTER_NAME]
            module_logger.debug('Database connected.')
        return self._cluster

    @property
    def database(self):
        return self._connect()


class UserCollection(metaclass=MetaSingleton):
    _collection = None

    @property
    def collection(self):
        if not self._collection:
            self._collection = Database().database[settings.USER_COLLECTION]
            module_logger.debug(f'Collection {settings.USER_COLLECTION} connected.')
        return self._collection

    def reg_user(self, discord_id: int, discord_user: str, nickname: str):
        user_post = self.find_user_post(discord_user)
        if not user_post:
            post = {
                'discord_user': str(discord_user),
                'discord_id': discord_id,
                'nickname': str(nickname),
                'entries': 0,
            }
            self.collection.insert_one(post)
        else:
            raise UserExists('A user with these credentials already exists')

    def rereg_user(self, discord_id: int, discord_user: str, nickname: str):
        user_post = self.find_user_post(discord_user)
        if user_post:
            post = {
                'discord_user': str(discord_user),
                'discord_id': discord_id,
                'nickname': str(nickname),
                'entries': int(user_post['entries'])
            }
            self.collection.update(user_post, post)
        else:
            self.reg_user(discord_id, discord_user, nickname)

    def find_user_post(self, user: str) -> str or None:
        post = self.collection.find_one({
            "discord_user": str(user)
        })
        return post

    def find_user(self, user: str) -> str or None:
        post = self.find_user_post(user)
        return post['nickname'] if post else None

    def find_user_post_by_name(self, name: str):
        return self.collection.find_one(
            {
                'nickname': name
            }
        )

    def user_joined_raid(self, user: str):
        self.collection.find_one_and_update(
            {
                'discord_user': str(user)
            },
            {
                '$inc': {
                    'entries': 1
                }
            }
        )

    def user_leave_raid(self, user: str):
        self.collection.find_one_and_update(
            {
                'discord_user': str(user)
            },
            {
                '$inc': {
                    'entries': -1
                }
            }
        )

    def user_post_by_name(self, name: str):
        return self.collection.find_one({
            'nickname': name
        })

    def notify_off(self, user: str):
        self.collection.find_one_and_update(
            {
                'discord_user': str(user)
            },
            {
                '$set': {
                    'not_notify': True
                }
            }
        )

    def notify_on(self, user: str):
        self.collection.find_one_and_update(
            {
                'discord_user': str(user)
            },
            {
                '$set': {
                    'not_notify': False
                }
            }
        )

    def notify_status(self, user: str):
        return self.find_user_post(user).get('notify')

    def first_notification(self, user: str):
        self.collection.find_one_and_update(
            {
                'discord_user': str(user)
            },
            {
                '$set': {
                    'first_notification': True
                }
            }
        )

    def first_notification_status(self, user: str):
        return self.find_user_post(user).get('first_notification')

    def get_users_id(self, user_list):
        post = self.collection.find(
            {
                'nickname': {
                    '$in': user_list
                }
            },
            {
                'discord_id': 1,
                'not_notify': 1,
                'first_notification': 1,
                '_id': 0,
            }
        )
        return list(post)


class CaptainCollection(metaclass=MetaSingleton):
    _collection = None

    @property
    def collection(self):
        if not self._collection:
            self._collection = Database().database[settings.CAPTAIN_COLLECTION]
            module_logger.debug(f'Collection {settings.CAPTAIN_COLLECTION} connected.')
        return self._collection

    def create_captain(self, user: str):
        captain_name = DatabaseManager().user.find_user(user)
        post = {
            "discord_user": user,
            "captain_name": captain_name,
            "raids_created": 0,
            "drove_people": 0,
            "last_created": datetime.datetime.now().strftime('%H:%M %d.%m.%y'),
            "last_raids": []
        }
        self.collection.insert_one(post)
        return post

    def update_captain(self, user: str, raid: Raid):
        captain_post = self.find_captain_post(user)
        if not captain_post:
            self.create_captain(user)

        # update last raids
        last_raids = captain_post['last_raids']

        # Get time normal time reservation open
        difference = tools.get_time_difference(raid.raid_time.time_reservation_open, raid.raid_time.time_leaving)
        if difference < 70:
            time_reservation_open = ''
        else:
            time_reservation_open = raid.raid_time.time_reservation_open

        # is last raid with that credentials exists?
        is_raid_exists = False
        for last_raid in last_raids:
            is_raid_exists = (
                    last_raid['server'] == raid.server and
                    last_raid['time_leaving'] == raid.raid_time.time_leaving and
                    last_raid['time_reservation_open'] == time_reservation_open and
                    last_raid['reservation_count'] == raid.reservation_count
            )
            if is_raid_exists:
                break

        if not is_raid_exists:
            if len(last_raids) >= 3:
                last_raids.pop(0)

            last_raids.append(
                {
                    'server': raid.server,
                    'time_leaving': raid.raid_time.time_leaving,
                    'time_reservation_open': time_reservation_open,
                    'reservation_count': raid.reservation_count,
                }
            )

        self.collection.find_one_and_update(
            {
                'discord_user': user
            },
            {
                '$inc': {
                    'raids_created': 1,
                    'drove_people': len(raid.member_dict)
                },
                '$set': {
                    'last_created': datetime.datetime.now().strftime('%H:%M %d.%m.%y'),
                    'last_raids': last_raids
                },
            }
        )

    def find_captain_post(self, user: str):
        return self.collection.find_one({
                'discord_user': user
        })

    def get_last_raids(self, user: str):
        captain_post = self.find_captain_post(user)
        return captain_post.get('last_raids')

    def get_captain_name_by_user(self, user: str) -> str or None:
        return self.find_captain_post(user).get('captain_name')


class SettingsCollection(metaclass=MetaSingleton):
    _collection = None

    @property
    def collection(self):
        if not self._collection:
            self._collection = Database().database[settings.SETTINGS_COLLECTION]
            module_logger.debug(f'Collection {settings.SETTINGS_COLLECTION} connected.')
        return self._collection

    def find_settings_post(self, guild_id: int) -> dict:
        return self.collection.find_one(
            {
                'guild_id': guild_id,
            }
        )

    def new_settings(self, guild_id: int, guild: str) -> dict:
        new_post = {
            'guild_id': guild_id,
            'guild': guild
        }
        self.collection.insert_one(new_post)
        return new_post

    def find_or_new(self, guild_id: int, guild: str) -> dict:
        post = self.find_settings_post(guild_id)
        if post:
            return post
        else:
            return self.new_settings(guild_id, guild)

    def update_settings(self, guild_id: int, guild: str, channel_id: int, channel: str):
        post = self.find_settings_post(guild_id)
        if not post:
            post = self.new_settings(guild_id, guild)
            allowed_channels = {
                str(channel_id): channel
            }
        else:
            allowed_channels = post.get('can_remove_in_channels')
            if allowed_channels:
                allowed_channels.update({
                    str(channel_id): channel
                })
            else:
                allowed_channels = {
                    str(channel_id): channel
                }

        update_post = {
            '$set': {
                'can_remove_in_channels': allowed_channels
            }
        }
        self.collection.find_one_and_update(
            {
                'guild_id': guild_id
            },
            update_post
        )

    def can_delete_there(self, guild_id: int, channel_id: int):
        post = self.find_settings_post(guild_id)
        if not post:
            return False
        if str(channel_id) in post.get('can_remove_in_channels'):
            return True

    def not_delete_there(self, guild_id: int, channel_id: int):
        old_post = self.find_settings_post(guild_id)
        if old_post:
            allowed_channel = old_post.get('can_remove_in_channels').get(str(channel_id))
            if allowed_channel:
                new_allowed_channels = old_post['can_remove_in_channels'].copy()
                new_allowed_channels.pop(str(channel_id))
                new_post = {
                    '$set': {
                        'can_remove_in_channels': new_allowed_channels
                    }
                }
                self.collection.update_one(old_post, new_post)

    def set_reaction_by_role(self, guild_id: int, guild: str, message_id: int, reaction_id: str, role_id: int):
        old_post = self.find_or_new(guild_id, guild)

        role_from_reaction = old_post.get('role_from_reaction')
        if role_from_reaction:
            old_reaction_role = role_from_reaction.get('reaction_role')

            new_reaction_role = {reaction_id: role_id}
            new_reaction_role.update(old_reaction_role)

            update_post = {
                '$set': {
                    'role_from_reaction': {
                        'message_id': message_id,
                        'reaction_role': new_reaction_role,
                    }
                }
            }
        else:
            update_post = {
                '$set': {
                    'role_from_reaction': {
                        'message_id': message_id,
                        'reaction_role':
                            {
                                reaction_id: role_id
                            }
                    }
                }
            }

        self.collection.find_one_and_update(
            {
                'guild_id': guild_id
            },
            update_post
        )

    def remove_reaction_from_role(self, guild_id: int, reaction_id: int):
        post = self.find_settings_post(guild_id)
        if not post:
            return

        role_from_reaction = post.get('role_from_reaction')
        if not role_from_reaction:
            return

        reaction_role = role_from_reaction.get('reaction_role')
        if reaction_id in reaction_role:
            reaction_role.pop(reaction_id)
        else:
            return

        update_post = {
            '$set': {
                'role_from_reaction': {
                    'message_id': role_from_reaction.get('message_id'),
                    'reaction_role': reaction_role,
                }
            }
        }

        self.collection.find_one_and_update(
            {
                'guild_id': guild_id
            },
            update_post
        )

        return True


class DatabaseManager:
    def __init__(self):
        self.user = UserCollection()
        self.captain = CaptainCollection()
        self.settings = SettingsCollection()
