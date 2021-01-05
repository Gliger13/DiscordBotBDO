import logging

import discord
from discord.ext import commands
from discord.ext.commands import Context

from instruments.database.db_manager import DatabaseManager
from messages import command_names, help_text, messages
from settings.logger import log_template

module_logger = logging.getLogger('my_bot')


class Statistics(commands.Cog):
    """
    Cog that provides all collected statistics.
    """
    database = DatabaseManager()

    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def user_stat_msg(user, user_info: dict, captain_info: dict) -> discord.Embed:
        """
        Return all information that bot knows about user to current channel as message.

        Attributes:
        ----------
        user: discord.User
            User for getting information about him
        user_info: dict
            All user information collected by bot from database
        captain_info: dict
            All user information that drove people collected by bot

        Returns:
        --------
        :discord.Embed
            All information about user as embed
        """

        text_message = messages.no_data
        if user_info:
            # Choose a title whichever user drove or not people
            if captain_info and captain_info.get('raids_created'):
                text_message = messages.captain_title
            else:
                text_message = messages.member_title

            # Add the user game nickname
            text_message += (
                f"**{user_info.get('nickname')}**.\n"
            )

            # Add information about whether the user joined raids or not
            if user_info.get('entries'):
                text_message += messages.raids_joined.format(
                    entries=user_info.get('entries')
                )
            else:
                text_message += messages.no_raids_joined

            # Add information about whether the user drove people or not.
            if captain_info and captain_info.get('raids_created'):
                raids_created = captain_info.get('raids_created')
                drove_people = captain_info.get('drove_people')
                if raids_created < 5:
                    text_message += messages.drove_raids_l5.format(
                        raids_created=raids_created
                    )
                else:
                    text_message += messages.drove_raids_g5.format(
                        raids_created=raids_created
                    )
                if drove_people < 5:
                    text_message += messages.drove_people_l5.format(
                        drove_people=captain_info.get('drove_people')
                    )
                else:
                    text_message += messages.drove_people_g5.format(
                        drove_people=captain_info.get('drove_people')
                    )
                text_message += messages.last_time_drove.format(
                    last_created=captain_info.get('last_created')
                )

        embed = discord.Embed(
            title=messages.statistics_user_title,
            colour=discord.Colour.blue(),
            description=text_message
        )
        # Add avatar
        if user:
            embed.set_author(
                name=str(user),
                icon_url=user.avatar_url,
            )
        return embed

    @commands.command(name=command_names.function_command.user_statistics, help=help_text.user_statistics)
    async def user_statistics(self, ctx: Context, nickname=''):
        """
        Send all information about the user collected by bot as message in current channel.

        Attributes:
        ----------
        nickname: str
            information about specific user else about author of command
        """
        user = None
        # Check specific user
        if nickname:
            # Try to find user in db
            user_info = await self.database.user.find_user_post_by_name(nickname)
            # If user exist try to find captain activity in db
            if user_info:
                captain_info = await self.database.captain.find_captain_post(user_info['discord_user'])
                user = self.bot.get_user(user_info['discord_id'])
            else:
                captain_info = None
        else:
            # If specific user not exist get current user
            user = ctx.author
            user_info = await self.database.user.find_user_post(str(user))
            captain_info = await self.database.captain.find_captain_post(str(user))

        embed = self.user_stat_msg(user, user_info, captain_info)
        await ctx.send(embed=embed)
        log_template.command_success(ctx)

    @commands.command(name=command_names.function_command.guild_statistics, help=help_text.guild_statistics)
    @commands.has_permissions(administrator=True, manage_messages=True)
    async def guild_statistics(self, ctx: Context):
        """
        Send all information about the current server collected by bot as message in current channel.
        """
        guild = ctx.guild
        user = ctx.author
        guild_info = await self.database.settings.find_settings_post(guild.id)

        # Collect all information from db

        if guild_info:
            text_message = ''

            # Information about getting role from clicking reaction
            role_from_reaction = guild_info.get('role_from_reaction')
            if role_from_reaction:
                text_message = messages.can_get_role_from.format(
                    message_id=role_from_reaction.get('message_id')
                )
                for emoji, role_id in role_from_reaction.get('reaction_role').items():
                    role = discord.utils.get(guild.roles, id=role_id)
                    text_message += messages.reaction_role.format(
                        role=role, emoji=emoji
                    )

            # Information about ability to remove channels
            if guild_info and guild_info.get('can_remove_in_channels'):
                text_message += messages.can_remove_msgs_in
                for channel_id, channel in guild_info.get('can_remove_in_channels').items():
                    text_message += f" - *#{channel}*\n"
        else:
            text_message = messages.no_data

        embed = discord.Embed(
            title=messages.statistics_guild_title,
            colour=discord.Colour.blue(),
            description=text_message
        )

        embed.set_author(
            name=str(guild),
            icon_url=user.guild.icon_url,
        )

        await ctx.send(embed=embed)
        log_template.command_success(ctx)


def setup(bot):
    bot.add_cog(Statistics(bot))
    log_template.cog_launched('Statistics')
