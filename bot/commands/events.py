import logging
import sys
import traceback

import discord
from discord.ext import commands

from instruments.database.db_manager import DatabaseManager
from messages import messages, logger_msgs
from settings import settings
from settings.logger import log_template

module_logger = logging.getLogger('my_bot')


class Events(commands.Cog):
    """
    Cog that responsible for various events.
    """
    database = DatabaseManager()

    def __init__(self, bot):
        self.bot = bot
        # Needed to track unplanned bot reboots
        self.is_bot_ready = False

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """
        Send msg to new user on server.
        """
        # Send only in main guild
        if member.guild.id == settings.MAIN_GUILD_ID:
            await member.send(messages.hello_new_member)

    @commands.Cog.listener()
    async def on_ready(self):
        """
        Runs after bot initialization.
        """
        # Track unplanned bot reboot
        if not self.is_bot_ready:
            module_logger.info(logger_msgs.bot_ready)
            self.is_bot_ready = True
        else:
            log_template.bot_restarted()

        # Set custom status
        custom_status = 'Покоряем мир и людишек'
        await self.bot.change_presence(status=discord.Status.online, activity=discord.Game(custom_status))

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """
        Handle and process all errors
        """
        if isinstance(error, commands.errors.BadArgument):
            await ctx.message.add_reaction('❔')
        elif isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.message.add_reaction('❔')
        elif isinstance(error, commands.errors.CommandNotFound):
            await ctx.message.add_reaction('❓')
        elif isinstance(error, commands.errors.PrivateMessageOnly):
            await ctx.message.author.send(messages.private_msg_only)
            await ctx.message.add_reaction('❓')
        elif isinstance(error, commands.errors.NoPrivateMessage):
            await ctx.message.author.send(messages.no_private_msg)
            await ctx.message.add_reaction('❓')
        elif isinstance(error, commands.errors.BotMissingPermissions):
            await ctx.message.author.send(messages.missing_perms.format(missing_perms='.'.join(error.missing_perms)))
            await ctx.message.add_reaction('❓')
        elif isinstance(error, commands.errors.UserInputError):
            await ctx.message.add_reaction('❓')
        elif isinstance(error, commands.errors.MissingRole):
            await ctx.message.add_reaction('⛔')
        else:
            # If this is an unknown error
            log_template.unknown_command_error(ctx, error)
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
            return
        log_template.command_error(ctx, error)

    async def add_role_from_reaction(self, payload: discord.RawReactionActionEvent):
        """
        Give user a role by clicking reaction on message
        """
        guild_settings = await self.database.settings.find_settings_post(payload.guild_id)

        if not guild_settings:
            return

        role_from_reaction = guild_settings.get('role_from_reaction')

        if not role_from_reaction:
            return

        reaction = str(payload.emoji)
        reaction_role = role_from_reaction.get('reaction_role')

        if (
            payload.message_id == role_from_reaction.get('message_id') and
            reaction in reaction_role
        ):
            guild = self.bot.get_guild(payload.guild_id)
            member = payload.member

            role = discord.utils.get(guild.roles, id=reaction_role[reaction])
            await member.add_roles(role)

            log_template.role_add_from_reaction(guild, member, role, reaction)

    async def remove_role_from_reaction(self, payload: discord.RawReactionActionEvent):
        """
        Remove the role of user by clicking reaction on message.
        """

        guild_settings = await self.database.settings.find_settings_post(payload.guild_id)

        if not guild_settings:
            return

        role_from_reaction = guild_settings.get('role_from_reaction')

        if not role_from_reaction:
            return

        reaction = str(payload.emoji)
        reaction_role = role_from_reaction.get('reaction_role')

        if (
                payload.message_id == role_from_reaction.get('message_id') and
                reaction in reaction_role
        ):
            guild = self.bot.get_guild(payload.guild_id)
            member = guild.get_member(payload.user_id)

            role = discord.utils.get(guild.roles, id=reaction_role[reaction])
            await member.remove_roles(role)

            log_template.role_remove_from_reaction(guild, member, role, reaction)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """
        Process all reaction that added by user.
        """
        if payload.user_id == settings.BOT_ID:
            return

        # Check if is reaction for get role
        await self.add_role_from_reaction(payload)

        user = self.bot.get_user(payload.user_id)
        emoji = str(payload.emoji)
        channel = self.bot.get_channel(payload.channel_id)

        # If user react in dm channel
        if isinstance(channel, discord.channel.DMChannel):
            if emoji == '💤':
                await self.not_notify_me(user)
        else:  # If user react in text channel on server
            message = await channel.fetch_message(payload.message_id)

            # Check if is reaction for get in raid
            joining = self.bot.get_cog('RaidJoining')
            await joining.raid_reaction_add(message, payload.emoji, user)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        """
        Process all reaction that removed by user.
        """
        if payload.user_id == settings.BOT_ID:
            return

        # Check if is reaction for get role
        await self.remove_role_from_reaction(payload)

        user = self.bot.get_user(payload.user_id)
        emoji = str(payload.emoji)
        channel = self.bot.get_channel(payload.channel_id)

        # If user react in dm channel
        if isinstance(channel, discord.channel.DMChannel):
            if emoji == '💤':
                await self.notify_me(user)
        else:  # If user react in text channel on server
            message = await channel.fetch_message(payload.message_id)

            # Check if is reaction for get in raid
            joining = self.bot.get_cog('RaidJoining')
            await joining.raid_reaction_remove(message, payload.emoji, user)

    async def not_notify_me(self, user):
        nickname = await self.database.user.find_user(str(user))

        if not nickname:
            return

        await self.database.user.notify_off(str(user))

        await user.send(messages.notification_off)
        log_template.user_notification_on(user)

    async def notify_me(self, user):
        nickname = await self.database.user.find_user(str(user))

        if not nickname:
            return

        await self.database.user.notify_on(str(user))
        await user.send(messages.notification_on)
        log_template.user_notification_off(user)


def setup(bot):
    bot.add_cog(Events(bot))
    log_template.cog_launched('Events')
