import logging

from instruments.database.db_init import Database
from instruments.tools import MetaSingleton
from settings import settings

module_logger = logging.getLogger('my_bot')


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
