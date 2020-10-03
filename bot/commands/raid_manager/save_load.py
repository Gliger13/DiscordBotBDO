import json
import logging
import os

from discord.ext import commands
from discord.ext.commands import Context

from commands.raid_manager import raid_list
from instruments import check_input
from instruments.raid.raid import Raid
from messages import command_names, help_text, logger_msgs
from settings.logger import log_template

module_logger = logging.getLogger('my_bot')


class RaidSaveLoad(commands.Cog):
    """
    Cog that responsible for saving and loading raid parameters.
    """
    raid_list = raid_list.RaidList()

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name=command_names.function_command.load_raid, help=help_text.load_raid)
    @commands.guild_only()
    @commands.has_role('Капитан')
    async def load_raid(self, ctx: Context, captain_name: str, time_leaving: str):
        """
        Load raid from locale storage.

        Attributes:
        ----------
        captain_name: str
            Name of the captain that created the raid.
        time_leaving: str or None
            Time when raid leaving. Required to fill if captain has more than one raid.
        """
        # Checking correct input
        await check_input.validation(**locals())

        # Checking save file exists
        file_name = f"saves/{captain_name}_{'-'.join(time_leaving.split(':'))}.json"
        if not os.path.exists(file_name):
            await check_input.not_correct(ctx, 'Файл сохранения не найден')
            return

        # Open file and load information in new Raid
        with open(file_name, 'r', encoding='utf-8') as save_file:
            raid_information = json.load(save_file)
        old_raid = Raid(
            captain_name=raid_information['captain_name'],
            server=raid_information['server'],
            time_leaving=raid_information['time_leaving'],
            time_reservation_open=raid_information['time_reservation_open'],
            guild_id=raid_information['guild_id'],
            channel_id=raid_information['channel_id'],
            reservation_count=int(raid_information['reservation_count']),
        )
        old_raid.raid_time.time_to_display = raid_information['time_to_display']
        old_raid.raid_time.secs_to_display = raid_information['secs_to_display']
        old_raid.member_dict.update(raid_information['members_dict'])
        self.raid_list.append(old_raid)

        await ctx.message.add_reaction('✔')
        log_template.command_success(ctx)

    @commands.command(name=command_names.function_command.save_raids, help=help_text.save_raids)
    @commands.guild_only()
    @commands.has_role('Капитан')
    async def save_raids(self, ctx: Context):
        """
        Save all active raids in locale storage.
        """
        if self.raid_list:
            for some_raid in self.raid_list:
                some_raid.save_raid()

            await ctx.message.add_reaction('✔')
            log_template.command_success(ctx)
        else:
            await ctx.message.add_reaction('❌')
            log_template.command_fail(ctx, logger_msgs.raids_not_found)

    @commands.command(name=command_names.function_command.save_raid, help=help_text.save_raid)
    @commands.guild_only()
    @commands.has_role('Капитан')
    async def save_raid(self, ctx: Context, captain_name: str, time_leaving=''):
        """
        Save active raid by specific captain name and time leaving

        Attributes:
        ----------
        captain_name: str
            Name of the captain that created the raid.
        time_leaving: str or None
            Time when raid leaving. Required to fill if captain has more than one raid.
        """
        # Checking correct input
        await check_input.validation(**locals())

        curr_raid = self.raid_list.find_raid(ctx.guild.id, ctx.channel.id,
                                             captain_name, time_leaving, ignore_channels=True)
        # if not find raid to save
        if not curr_raid:
            await check_input.not_correct(ctx, 'Не нашёл рейд для сохранение.')
            log_template.command_fail(ctx, logger_msgs.raids_not_found)
            return

        curr_raid.save_raid()

        await ctx.message.add_reaction('✔')
        log_template.command_success(ctx)


def setup(bot):
    bot.add_cog(RaidSaveLoad(bot))
    log_template.cog_launched('RaidSaveLoad')
