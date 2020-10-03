import asyncio
import logging
import os

import discord
from discord.ext import commands
from discord.ext.commands import Context

from instruments import check_input, database_process
from messages import command_names, help_text, messages, logger_msgs
from settings import settings
from settings.logger import log_template

module_logger = logging.getLogger('my_bot')


class Base(commands.Cog):
    """
    Cog that responsible for basic bot commands.
    """
    database = database_process.DatabaseManager()

    def __init__(self, bot):
        self.bot = bot
        self.bot.remove_command('help')  # Remove command to create custom help

    @commands.command(name=command_names.function_command.test, help=help_text.test)
    async def test(self, ctx: Context):
        """
        Command witch does nothing. For developer and debugging.
        """
        await check_input.validation(**locals())
        await ctx.message.add_reaction('❌')
        await ctx.message.add_reaction('✔')
        log_template.command_success(ctx)

    async def help_command(self, ctx: Context, command):
        """
        Send command description as message in channel.

        Attributes
        ----------
        command: str
            The name of command for getting the description
        """
        # Get command obj from the name
        command = self.bot.get_command(command)

        if command:
            embed = discord.Embed(
                title=command.name,
                colour=discord.Colour.blue(),
                description=command.help,
            )

            bot_as_user = self.bot.get_user(settings.BOT_ID)
            embed.set_author(
                name=str(bot_as_user),
                icon_url=bot_as_user.avatar_url,
            )
            await ctx.send(embed=embed)

            await ctx.message.add_reaction('✔')
            log_template.command_success(ctx)
        else:
            await ctx.message.add_reaction('❌')
            log_template.command_fail(ctx, logger_msgs.command_not_found)

    @commands.command(name=command_names.function_command.send_logs, help=help_text.send_logs)
    @commands.is_owner()
    async def send_logs(self, ctx: Context):
        """
        Command for admins and developers. Send the bot logs as msg to channel.
        """
        path_to_logs = os.path.join('settings', 'logger', 'logs.log')

        if os.path.exists(path_to_logs):
            await ctx.send(file=discord.File(path_to_logs))
            await ctx.message.add_reaction('✔')
            log_template.command_success(ctx)
        else:
            await ctx.message.add_reaction('❌')
            log_template.command_fail(ctx, logger_msgs.logs_not_found)

    @commands.command(name=command_names.function_command.help, help=help_text.help)
    async def help(self, ctx: Context, command=''):
        """
        Custom help command.

        Attributes
        ----------
        command: str
            The name of command for getting the description
        """
        # If user enter name of command to get description
        if command:
            await self.help_command(ctx, command)
            return

        # Dict of emoji for control custom help
        HELP_EMODJI = ['🔼', '1⃣', '2⃣', '3⃣', '4⃣', '5⃣', '6⃣', '7⃣', '8⃣', '9️⃣']
        pages = {}
        # Cogs witch should not be shown in help
        not_help_cogs = ['Base', 'Events']

        # Get all available commands of the bot
        cogs_commands = {}
        for cog_name in self.bot.cogs:
            if cog_name not in not_help_cogs:
                cogs_commands[messages.cog_names[cog_name]] = self.bot.get_cog(cog_name).get_commands()

        main_embed = discord.Embed(
            title=messages.help_title,
            colour=discord.Colour.blue()
        )

        bot_as_user = self.bot.get_user(settings.BOT_ID)
        main_embed.set_author(
            name=str(bot_as_user),
            icon_url=bot_as_user.avatar_url,
        )

        # Generate pages of cogs with description of all commands in cog
        section_help = messages.section_help.format(emoji=HELP_EMODJI[0])
        for index, (cog_name, bot_commands) in enumerate(cogs_commands.items()):
            section_help += f"**{HELP_EMODJI[1:][index]}  -  {cog_name}**\n"
            page = f"**{cog_name}**:\n"
            for command in bot_commands:
                page += f"**`{settings.PREFIX}{command.name}` - {command.short_doc}**\n"

            embed_page = discord.Embed(
                title=messages.help_title,
                colour=discord.Colour.blue(),
                description=page
            )

            embed_page.set_author(
                name=str(bot_as_user),
                icon_url=bot_as_user.avatar_url,
            )

            pages[HELP_EMODJI[1:][index]] = embed_page

        main_embed.add_field(
            name=messages.section_title,
            value=section_help,
            inline=False
        )

        main_embed.add_field(
            name=messages.author_title,
            value=messages.author_command_description,
            inline=False
        )

        main_embed.add_field(
            name=messages.additional_help_title,
            value=messages.additional_help,
            inline=False
        )

        main_embed.add_field(
            name=messages.help_reaction_title,
            value=messages.help_reaction,
            inline=False
        )

        # Set home page
        pages[HELP_EMODJI[0]] = main_embed

        help_msg = await ctx.send(embed=main_embed)

        log_template.command_success(ctx)

        # Add control emoji for message
        for emoji in HELP_EMODJI:
            await help_msg.add_reaction(emoji)

        def check(reaction, user):
            """
            Only user who use command can use control emoji
            """
            return (
                    user == ctx.message.author and
                    str(reaction.emoji) in HELP_EMODJI
            )

        while True:
            try:
                # Waiting for a click reaction from the user
                reaction, user = await self.bot.wait_for('reaction_add', timeout=600.0, check=check)
            except asyncio.TimeoutError:
                return

            log_template.user_answer(ctx, str(reaction))

            # Switch page
            embed = pages.get(str(reaction))
            if embed:
                await help_msg.edit(embed=embed)

    @commands.command(name=command_names.function_command.turn_off_bot, help=help_text.turn_off_bot)
    @commands.is_owner()
    async def turn_off_bot(self, ctx: Context):
        """
        Disables the bot. Available only to the bot creator.
        """
        log_template.command_success(ctx)
        await self.bot.logout()

    @commands.command(name=command_names.function_command.author_of_bot, help=help_text.author_of_bot)
    async def author_of_bot(self, ctx: Context):
        """
        Send information about creator and bot as message in current channel.
        """
        embed = discord.Embed(
            title=messages.author_title,
            colour=discord.Colour.blue(),
            description=messages.about_author
        )
        await ctx.send(embed=embed)
        log_template.command_success(ctx)


def setup(bot):
    bot.add_cog(Base(bot))
    log_template.cog_launched('Base')
