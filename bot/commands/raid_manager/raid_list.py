import logging

from instruments.raid.raid import Raid
from instruments.tools import MetaSingleton

module_logger = logging.getLogger('my_bot')


class RaidList(metaclass=MetaSingleton):
    """
    Realise general namespace for active raids for all files
    """
    active_raids = []

    def __iter__(self):
        return iter(self.active_raids)

    def __getitem__(self, item):
        return self.active_raids[item]

    def __bool__(self):
        return bool(len(self.active_raids))

    @staticmethod
    def is_raid(item) -> bool:
        if not isinstance(item, Raid):
            raise TypeError(f"{item} is not Raid object")
        return True

    def append(self, item):
        if self.is_raid(item):
            self.active_raids.append(item)

    def remove(self, item):
        if self.is_raid(item):
            self.active_raids.remove(item)

    def find_raids_by_guild(self, name: str, guild_id: int) -> list:
        """
        Return list of active raids by specific discord guild.

        Attributes:
        ----------
        name: str
            Nickname of user.
        guild_id: int
            Get raids only created in specific discord guild.

        Returns:
        ----------
        :list
            List of active raids by specific discord guild.
        """
        available_raids = []
        entered_raids = self._find_raids_by_nickname(name)
        for some_raid in self.active_raids:
            if guild_id not in some_raid.raid_coll_msgs or some_raid.is_full or name in some_raid:
                continue
            for entered_raid in entered_raids:
                if some_raid.raid_time.time_leaving == entered_raid.raid_time.time_leaving:
                    break
            else:
                available_raids.append(some_raid)
        return available_raids

    def find_raid(self, guild_id: int, channel_id: int, captain_name='', time_leaving='',
                  ignore_channels=False) -> Raid or None:
        """
        Return list of raids by specific discord guild and channel, captain name and time leaving.

        Attributes:
        ----------
        guild_id: int
            Get raid list only created in specific discord guild.
        channel_id: int
            Get raid list only created in specific discord channel.
        captain_name: str
            Get raid list only created by this captain.
        time_leaving: str
            Time when raid leaving. Required to fill if captain has more than one raid.
        ignore_channels: bool
            If true return all active raids.

        Returns:
        ----------
        :list
            List of active raids by specific discord guild.
        :None
            If no raids found.

        Need to refactor!
        """
        raids_found = []
        # if require raids only by captain_name
        if not captain_name:
            for some_raid in self.active_raids:
                if some_raid.captain_name == captain_name:
                    raids_found.append(some_raid)
            return raids_found

        for some_raid in self.active_raids:
            for raid_msg in some_raid.raid_coll_msgs.values():
                if (
                        ignore_channels or
                        raid_msg.guild_id == guild_id and raid_msg.channel_id == channel_id
                ):
                    if captain_name and time_leaving:
                        if some_raid.captain_name == captain_name and some_raid.raid_time.time_leaving == time_leaving:
                            raids_found.append(some_raid)
                            break
                    else:
                        if some_raid.captain_name == captain_name:
                            raids_found.append(some_raid)

        if not len(raids_found) == 1:
            return
        return raids_found.pop()

    def find_raids_by_captain_name(self, captain_name: str) -> list:
        """
        Return all Raid's as list by captain_name
        """
        raids_found = [some_raid for some_raid in self.active_raids if some_raid.captain_name == captain_name]
        return raids_found

    def is_correct_join(self, nickname: str, time_leaving: str) -> bool:
        """
        Checking the necessary conditions for joining the raid.

        Attributes:
        ----------
        nickname: str
            Game nickname of user that want join the raid.
        time_leaving: str
            Time leaving of raid that user try to join.

        Returns:
        ----------
        :bool
        """
        raids_found = self._find_raids_by_nickname(nickname)

        if len(raids_found) == 0:
            return True
        for some_raid in raids_found:
            if some_raid.raid_time.time_leaving == time_leaving:
                return False
        return True

    def _find_raids_by_nickname(self, nickname: str) -> list:
        """
        Return list of raids of which the user is in.

        Attributes:
        ----------
        nickname: str
            Game nickname of user.
        """
        raids_find = []
        for some_raid in self.active_raids:
            if nickname in some_raid:
                raids_find.append(some_raid)
        return raids_find

    def find_raid_by_nickname(self, nickname: str) -> Raid or None:
        """
        Return raid of which the user is in or None if are many raids.

        Attributes:
        ----------
        nickname: str
            Game nickname of user.
        """
        raids_find = self._find_raids_by_nickname(nickname)
        if len(raids_find) == 1:
            return raids_find.pop()

    def find_raid_by_coll_id(self, guild_id, collection_msg_id: int) -> list or None:
        """
        Return raid by discord collection message id.

        Attributes:
        ----------
        collection_msg_id: int
            Discord id of collection message in which collect in a raid.
        """
        for some_raid in self.active_raids:
            raid_coll_msg = some_raid.raid_coll_msgs.get(guild_id)
            if (
                    raid_coll_msg and
                    raid_coll_msg.collection_msg_id and raid_coll_msg.collection_msg_id == collection_msg_id
            ):
                return some_raid
