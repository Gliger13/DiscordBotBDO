import logging
from datetime import datetime, timedelta

from discord.ext import commands
from discord.ext.commands import Context

from instruments import database_process
from messages import command_names, help_text, messages, logger_msgs
from settings.logger import log_template

module_logger = logging.getLogger('my_bot')


class Admin(commands.Cog):
    """
    Cog for controlling server, channels and messages.
    """
    database = database_process.DatabaseManager()

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name=command_names.function_command.remove_there, help=help_text.remove_there)
    @commands.guild_only()
    @commands.has_role('Капитан')
    async def remove_there(self, ctx: Context):
        """
        Allow the raid creator use command for mass messages remove in current channel.
        """
        guild = ctx.guild
        channel = ctx.channel
        self.database.settings.update_settings(guild.id, str(guild), channel.id, str(channel))

        await ctx.message.add_reaction('✔')
        log_template.command_success(ctx)

    @commands.command(name=command_names.function_command.not_remove_there, help=help_text.not_remove_there)
    @commands.guild_only()
    @commands.has_permissions(administrator=True, manage_messages=True)
    async def not_remove_there(self, ctx: Context):
        """
        Does not allow use command for mass messages remove in current channel.
        """
        guild = ctx.guild
        channel = ctx.channel
        self.database.settings.not_delete_there(guild.id, channel.id)

        await ctx.message.add_reaction('✔')
        log_template.command_success(ctx)

    @commands.command(name=command_names.function_command.remove_msgs, help=help_text.remove_msgs)
    @commands.guild_only()
    @commands.has_role('Капитан')
    async def remove_msgs(self, ctx: Context, amount=100):
        """
        Remove `amount` messages in current channel.

        Attributes
        ----------
        amount: str
            Amount of messages to delete
        """
        guild = ctx.guild
        channel = ctx.channel
        # In this channel can raid creator remove messages by bot?
        if not self.database.settings.can_delete_there(guild.id, channel.id):
            await ctx.message.add_reaction('❌')
            await ctx.author.send(messages.wrong_channel)
            log_template.command_fail(ctx, logger_msgs.wrong_channel)

        messages_to_remove = []
        msg_count = 0
        # Collect all messages in current channel that not older 14 days and not pinned
        async for msg in channel.history(limit=int(amount)):
            is_time_has_passed = datetime.now() - msg.created_at > timedelta(days=14)

            # Warning user if messages older than 14 days
            if not msg.pinned and is_time_has_passed:
                await ctx.author.send(
                    messages.remove_msgs_fail_14.format(msg_count=msg_count, amount=amount)
                )
                break

            if not msg.pinned:
                messages_to_remove.append(msg)
                msg_count += 1

        # Remove messages from channel
        await channel.delete_messages(messages_to_remove)
        log_template.command_success(ctx)


def setup(bot):
    bot.add_cog(Admin(bot))
    log_template.cog_launched('Admin')
