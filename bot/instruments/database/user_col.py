import logging

from instruments.database.db_init import Database, Error
from instruments.tools import MetaSingleton
from settings import settings

module_logger = logging.getLogger('my_bot')


class UserExists(Error):
    """
    Exception raised when user exist in database

    Attributes:
        expression -- input expression in which the error occurred
    """

    def __init__(self, expression):
        self.expression = expression


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