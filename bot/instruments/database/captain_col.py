import datetime
import logging

from instruments import tools
from instruments.database.db_init import Database
from instruments.database.user_col import UserCollection
from instruments.raid.raid import Raid
from instruments.tools import MetaSingleton
from settings import settings

module_logger = logging.getLogger('my_bot')


class CaptainCollection(metaclass=MetaSingleton):
    _collection = None

    @property
    def collection(self):
        if not self._collection:
            self._collection = Database().database[settings.CAPTAIN_COLLECTION]
            module_logger.debug(f'Collection {settings.CAPTAIN_COLLECTION} connected.')
        return self._collection

    def create_captain(self, user: str):
        captain_name = UserCollection().find_user(user)
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