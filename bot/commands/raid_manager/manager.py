import logging

from discord.ext import commands
from discord.ext.commands import Context

from commands.raid_manager import raid_list
from instruments import check_input, database_process
from messages import command_names, help_text, logger_msgs
from settings.logger import log_template

module_logger = logging.getLogger('my_bot')


class RaidManager(commands.Cog):
    """
    Cog that responsible for management raids
    """
    database = database_process.DatabaseManager()
    raid_list = raid_list.RaidList()

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name=command_names.function_command.close_reservation, help=help_text.close_reservation)
    @commands.guild_only()
    @commands.has_role('Капитан')
    async def close_reservation(self, ctx: Context, places: int, captain_name='', time_leaving=''):
        """
        Close places for joining in the raid

        Attributes:
        ----------
        captain_name: str
            Name of the captain that created the raid.
        time_leaving: str or None
            Time when raid leaving. Required to fill if captain has more than one raid.
        """
        # Checking correct input
        await check_input.validation(**locals())

        if not (20 > places > 0):
            await ctx.message.add_reaction('❌')
            return

        # Get the name of the captain from db if not specified
        if not captain_name:
            captain_post = self.database.captain.find_captain_post(str(ctx.author))
            if captain_post:
                captain_name = captain_post['captain_name']
            else:
                return

        # Try find the raid with this credentials
        current_raid = self.raid_list.find_raid(
            ctx.guild.id, ctx.channel.id, captain_name, time_leaving, ignore_channels=True
        )

        # Does this captain have a raid with these parameters?
        if not current_raid:
            await ctx.message.add_reaction('❌')
            log_template.command_fail(ctx, logger_msgs.raid_not_found)
            return

        # Is bad try to reserve places
        if places > current_raid.places_left:
            await ctx.message.add_reaction('❌')
            log_template.command_fail(ctx, logger_msgs.wrong_places)
            return

        current_raid.reservation_count += places
        await current_raid.update_coll_msgs(self.bot)

        await ctx.message.add_reaction('✔')
        log_template.command_success(ctx)

    @commands.command(name=command_names.function_command.open_reservation, help=help_text.open_reservation)
    @commands.guild_only()
    @commands.has_role('Капитан')
    async def open_reservation(self, ctx: Context, places: int, captain_name='', time_leaving=''):
        """
        Remove available raid

        Attributes:
        ----------
        captain_name: str
            Name of the captain that created the raid.
        time_leaving: str or None
            Time when raid leaving. Required to fill if captain has more than one raid.
        """
        # Checking correct input
        await check_input.validation(**locals())

        if not (20 > places > 0):
            await ctx.message.add_reaction('❌')
            return

        # Get the name of the captain from db if not specified
        if not captain_name:
            captain_post = self.database.captain.find_captain_post(str(ctx.author))
            if captain_post:
                captain_name = captain_post['captain_name']
            else:
                return

        # Try find the raid with this credentials
        current_raid = self.raid_list.find_raid(
            ctx.guild.id, ctx.channel.id, captain_name, time_leaving, ignore_channels=True
        )

        # Does this captain have a raid with these parameters?
        if not current_raid:
            await ctx.message.add_reaction('❌')
            log_template.command_fail(ctx, logger_msgs.raid_not_found)
            return

        # Is bad try to reserve places
        if places >= current_raid.reservation_count:
            await ctx.message.add_reaction('❌')
            log_template.command_fail(ctx, logger_msgs.raid_not_found)
            return

        current_raid.reservation_count -= places
        await current_raid.update_coll_msgs(self.bot)

        await ctx.message.add_reaction('✔')
        log_template.command_success(ctx)


def setup(bot):
    bot.add_cog(RaidManager(bot))
    log_template.cog_launched('RaidManager')
