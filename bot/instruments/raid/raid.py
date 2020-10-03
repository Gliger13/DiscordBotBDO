import datetime
import json
import os
from datetime import datetime

from raid.raid_coll_msg import RaidCollMsg
from raid.raid_table import RaidTable
from raid.raid_time import RaidTime


class Raid:
    """
    Create Raid Object that contain members amount of members and etc
    """
    def __init__(self, captain_name, server, time_leaving, time_reservation_open,
                 guild_id, channel_id, reservation_count=2):
        # Info about BDO raid
        self.captain_name = captain_name
        self.member_dict = {}
        self.server = server
        self.raid_time = RaidTime(time_leaving, time_reservation_open)
        self.reservation_count = max(int(reservation_count), 1)

        self.table = None

        self.raid_coll_msgs = {}

        self.is_first_collection = True
        self.first_coll_guild_id = guild_id
        self.first_collection_task = None

        current_time = datetime.now()
        self.time_of_creation = f'{current_time.hour}-{current_time.minute}-{current_time.second}'

    def __iadd__(self, name_new_member):
        if self.places_left == 0:
            return False
        self.member_dict.update({name_new_member: self.members_count})
        return self

    def __isub__(self, name_remove_member):
        if self.member_dict.get(name_remove_member):
            del self.member_dict[name_remove_member]
            return self
        else:
            return False

    def __cmp__(self, other):
        if self.members_count > other.members_count:
            return 1
        elif self.members_count == other.members_count:
            return 0
        else:
            return -1

    def __lt__(self, other):
        return self.members_count < other.members_count

    def __gt__(self, other):
        return self.members_count > other.members_count

    def __contains__(self, member_name: str):
        return member_name in self.member_dict.keys()

    @property
    def members_count(self) -> int:
        return self.reservation_count + len(self.member_dict)

    @property
    def places_left(self) -> int:
        return 20 - self.members_count

    @property
    def is_full(self) -> bool:
        if self.places_left <= 0:
            return True
        else:
            return False

    def start_collection(self, guild_id: int, channel_id: int):
        new_raid_collection = RaidCollMsg(self, guild_id, channel_id)
        self.raid_coll_msgs[guild_id] = new_raid_collection
        return new_raid_collection

    async def update_coll_msgs(self, bot):
        [await raid_msg.update_coll_msg(bot) for raid_msg in self.raid_coll_msgs.values()]

    async def update_table_msgs(self, bot):
        [await raid_msg.update_table_msg(bot) for raid_msg in self.raid_coll_msgs.values()]

    async def send_end_work_msgs(self, bot):
        [await raid_msg.send_end_work_msg(bot) for raid_msg in self.raid_coll_msgs.values()]

    def table_path(self) -> str:
        if not self.table:
            self.table = RaidTable(self)
            self.table.create_table()
        else:
            self.table.update_table(self)
        return self.table.table_path

    def end_work(self):
        self.save_raid()

        if self.first_collection_task:
            self.first_collection_task.cancel()

        [raid_msg.coll_sleep_task.cancel() for raid_msg in self.raid_coll_msgs.values() if raid_msg.coll_sleep_task]

        if self.raid_time.notification_task:
            self.raid_time.notification_task.cancel()

    def save_raid(self):
        raid_information = {
            "captain_name": self.captain_name,
            "server": self.server,
            "time_leaving": self.raid_time.time_leaving,
            "time_reservation_open": self.raid_time.time_reservation_open,
            "reservation_count": self.reservation_count,
            "time_to_display": self.raid_time.time_to_display,
            "secs_to_display": self.raid_time.secs_to_display,
            "members_dict": self.member_dict,
            "members_count": self.members_count,
        }
        # Find dir 'saves'. If not - create
        for file in os.listdir(path='.'):
            if file == 'saves':
                break
        else:
            os.mkdir('saves')
        # Save raid in txt file
        file_name = f"saves/{self.captain_name}_{'-'.join(self.raid_time.time_leaving.split(':'))}.json"
        with open(file_name, 'w', encoding='utf-8') as save_file:
            json.dump(raid_information, save_file)
