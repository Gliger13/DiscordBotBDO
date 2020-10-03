import discord
from discord.errors import NotFound

from messages import messages


class RaidCollMsg:
    def __init__(self, raid, guild_id, channel_id):
        self.raid = raid

        self.collection_msg_id = None
        self.table_msg_id = None

        self.guild_id = guild_id
        self.channel_id = channel_id

        self.coll_sleep_task = None

    @property
    def collection_text(self):
        return messages.collection_start.format(
            captain_name=self.raid.captain_name, time_leaving=self.raid.raid_time.time_leaving,
            server=self.raid.server, places_left=self.raid.places_left,
            display_table_time=self.raid.raid_time.next_time_to_display
        )

    async def _get_msg(self, bot, msg_id: int):
        channel = bot.get_channel(self.channel_id)
        message = await channel.fetch_message(msg_id)
        return message

    async def _send_table_msg(self, bot):
        channel = bot.get_channel(self.channel_id)
        return await channel.send(file=discord.File(self.raid.table_path()))

    async def send_coll_msg(self, ctx):
        collection_msg = await ctx.send(self.collection_text)
        self.collection_msg_id = collection_msg.id
        return collection_msg

    async def update_coll_msg(self, bot):
        if self.collection_msg_id:
            collection_msg = await self._get_msg(bot, self.collection_msg_id)
            await collection_msg.edit(content=self.collection_text)

    async def update_table_msg(self, bot):
        if not self.table_msg_id:
            table_msg = await self._send_table_msg(bot)
        else:
            try:
                table_msg = await self._get_msg(bot, self.table_msg_id)
                await table_msg.delete()
            except NotFound:
                pass
            table_msg = await self._send_table_msg(bot)
        self.table_msg_id = table_msg.id

    async def send_end_work_msg(self, bot):
        channel = bot.get_channel(self.channel_id)
        await channel.send(messages.collection_end.format(server=self.raid.server, captain_name=self.raid.captain_name))
