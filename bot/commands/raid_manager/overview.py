import logging

import discord
from discord.ext import commands
from discord.ext.commands import Context

from commands.raid_manager import raid_list
from instruments import check_input
from instruments.database.db_manager import DatabaseManager
from messages import command_names, help_text, messages, logger_msgs
from settings.logger import log_template

module_logger = logging.getLogger('my_bot')


class RaidOverview(commands.Cog):
    """
    Cog of raid manager that responsible for raid overviewing.
    """
    database = DatabaseManager()
    raid_list = raid_list.RaidList()

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name=command_names.function_command.show_raids, help=help_text.show_raids)
    async def show_raids(self, ctx: Context, show_all=''):
        """
        Send information about all active raid

        Attributes:
        ----------
        show_all: str
            If not None show all active raids witch created by bot
        """
        log_template.command_success(ctx)

        if not show_all:
            # Check raids exist
            if not self.raid_list:
                await ctx.send(messages.no_active_raids)
                return

            available_raids = [some_raid for some_raid in self.raid_list if ctx.guild.id in some_raid.raid_coll_msgs]
            if not available_raids:
                await ctx.send(messages.no_active_raids)
                return

            # Generate information about active raids and send
            msg_of_raid = messages.active_raids_start
            for curr_raid in self.raid_list:
                if ctx.guild.id not in curr_raid.raid_coll_msgs:
                    continue
                channel = self.bot.get_channel(curr_raid.raid_coll_msgs[ctx.guild.id].channel_id)
                msg_of_raid += messages.active_raid_all.format(
                    channel_name=channel.mention, captain_name=curr_raid.captain_name,
                    server=curr_raid.server, time_leaving=curr_raid.raid_time.time_leaving,
                ) + '\n'
            await ctx.send(msg_of_raid)

        else:
            # Check raids exist
            if not self.raid_list:
                await ctx.send(messages.no_active_raids)
                return

            # Generate information about active raids and send
            msg_of_raid = messages.active_raids_start
            for curr_raid in self.raid_list:
                for raid_coll_msg in curr_raid.raid_coll_msgs.values():
                    guild_name = str(self.bot.get_guild(raid_coll_msg.guild_id))
                    channel_name = str(self.bot.get_channel(raid_coll_msg.channel_id))
                    msg_of_raid += messages.active_raid_hide.format(
                        guild_name=guild_name, channel_name=channel_name,
                        captain_name=curr_raid.captain_name, time_leaving=curr_raid.raid_time.time_leaving,
                    ) + '\n'
            await ctx.send(msg_of_raid)

    @commands.command(name=command_names.function_command.show_text_raids, help=help_text.show_text_raids)
    @commands.guild_only()
    @commands.has_role('Капитан')
    async def show_text_raids(self, ctx: Context, captain_name: str, time_leaving=''):
        """
        Send member list of raid as text

        Attributes:
        ----------
        captain_name: str
            Name of the user that created the raid.
        time_leaving: str or None
            Time when raid leaving. Required to fill if captain has more than one raid.
        """
        # Checking correct inputs arguments
        await check_input.validation(**locals())

        curr_raid = self.raid_list.find_raid(
            ctx.guild.id, ctx.channel.id, captain_name, time_leaving,
            ignore_channels=True
        )

        if curr_raid:
            # If it's first display
            if not curr_raid.table:
                curr_raid.table_path()

            # Generate text member list
            text = curr_raid.table.create_text_table()
            title = text.split('\n')[0]
            embed = discord.Embed(
                title=title,
                colour=discord.Colour.blue(),
                description=text[len(title) + 1:]
            )

            await ctx.send(curr_raid.table.create_text_table())
            await ctx.message.add_reaction('✔')
            log_template.command_success(ctx)
        else:
            await ctx.message.add_reaction('❌')
            log_template.command_fail(ctx, logger_msgs.raid_not_found)

    @commands.command(name=command_names.function_command.show, help=help_text.show)
    @commands.guild_only()
    @commands.has_role('Капитан')
    async def show(self, ctx: Context, captain_name='', time_leaving=''):
        """
        Send member list of raid as image

        Attributes:
        ----------
        captain_name: str
            Name of the user that created the raid.
        time_leaving: str or None
            Time when raid leaving. Required to fill if captain has more than one raid.
        """

        # Checking correct inputs arguments
        await check_input.validation(**locals())

        # Get the name of the captain from db if not specified
        if not captain_name:
            captain_post = await self.database.captain.find_captain_post(str(ctx.author))
            if captain_post:
                captain_name = captain_post['captain_name']
            else:
                return

        curr_raid = self.raid_list.find_raid(
            ctx.guild.id, ctx.channel.id, captain_name, time_leaving,
            ignore_channels=True
        )

        if curr_raid:
            path = curr_raid.table_path()
            curr_raid.save_raid()
            await ctx.send(file=discord.File(path))

            await ctx.message.add_reaction('✔')
            log_template.command_success(ctx)
        else:
            await ctx.message.add_reaction('❌')
            log_template.command_fail(ctx, logger_msgs.raid_not_found)


def setup(bot):
    bot.add_cog(RaidOverview(bot))
    log_template.cog_launched('RaidOverview')
