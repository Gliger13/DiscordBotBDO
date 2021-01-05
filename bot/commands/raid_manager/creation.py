import asyncio
import logging

import discord
from discord.ext import commands
from discord.ext.commands import Context

from commands.raid_manager import raid_list
from instruments import check_input, tools
from instruments.database.db_manager import DatabaseManager
from instruments.raid.raid import Raid
from instruments.raid.raid_coll_msg import RaidCollMsg
from messages import command_names, help_text, messages, logger_msgs
from settings.logger import log_template

module_logger = logging.getLogger('my_bot')


class RaidCreation(commands.Cog):
    """
    Cog that responsible for creating and removing raids
    """
    database = DatabaseManager()
    raid_list = raid_list.RaidList()

    def __init__(self, bot):
        self.bot = bot

    def captain_raids(self, captain_name: str) -> list or None:
        """
        Return list of all captains Raid's or None.

        Attribute:
        ----------
        captain_name: str
            Nickname of user that drove people

        Return:
        ----------
        list or None if raids of captains not exist
        """
        current_raids = []
        for some_raid in self.raid_list:
            if some_raid.captain_name == captain_name:
                current_raids.append(some_raid)
        return current_raids

    def captain_raids_str(self, captain_name: str) -> str or None:
        """"
        Return list of all captains Raid's or None as text.

        Attribute:
        ----------
        captain_name: str
            Nickname of user that drove people

        Return:
        ----------
        str or None if raids of captains not exist
        """
        current_raids = self.captain_raids(captain_name)

        if not current_raids:
            return

        msg = messages.yours_current_raids_start
        for captain_raid in current_raids:
            for raid_coll_msg in captain_raid.raid_coll_msgs.values():
                guild_name = str(self.bot.get_guild(raid_coll_msg.guild_id))
                channel_name = str(self.bot.get_channel(raid_coll_msg.channel_id))
                msg += (
                    f"**{guild_name}**/**{channel_name}**/"
                    f"**{captain_raid.server}**/**{captain_raid.raid_time.time_leaving}**\n"
                )
        return msg

    async def notify_about_leaving(self, current_raid: Raid):
        """
        Send notification message to all users in raid after notification time.

        Attributes:
        ----------
        current_raid: Raid
            raid to notification
        """

        async def first_notification(member, user):
            was_first_notified = member.get('first_notification')
            if not was_first_notified:
                notification_msg = await user.send(messages.notification_warning)
                await self.database.user.first_notification(str(user))
                await notification_msg.add_reaction('💤')

        # Get secs left to notification
        secs_sleep = current_raid.raid_time.secs_to_notify()

        if not secs_sleep:
            return

        current_raid.raid_time.is_notified = True
        # Sleep before notification time
        sleep_task = asyncio.create_task(asyncio.sleep(secs_sleep))
        current_raid.raid_time.notification_task = sleep_task
        await sleep_task

        users_list = await self.database.user.get_users_id(list(current_raid.member_dict.keys()))
        amount = 0
        # Send notification msg to users
        for member in users_list:
            if member and not member.get('not_notify'):
                user = self.bot.get_user(member.get('discord_id'))

                await user.send(messages.member_notification)
                amount += 1

                await first_notification(member, user)

        # Send notification message to the captain
        captain_post = await self.database.user.user_post_by_name(current_raid.captain_name)
        captain = self.bot.get_user(captain_post.get('discord_id'))
        if not captain_post.get('not_notify'):
            await captain.send(messages.captain_notification)
            amount += 1

            await first_notification(captain_post, captain)

        log_template.notify_success(current_raid.raid_time.time_leaving, amount)

    async def remove_captain_raid(self, ctx: Context):
        captain_name = await self.database.captain.get_captain_name_by_user(str(ctx.author))

        if not captain_name:
            await ctx.message.add_reaction('❌')
            log_template.command_fail(ctx, logger_msgs.captain_not_exist)
            return

        current_raids = self.raid_list.find_raids_by_captain_name(captain_name)

        if not current_raids:
            await ctx.message.add_reaction('❌')
            log_template.command_fail(ctx, logger_msgs.raid_not_found)
            return

        if len(current_raids) == 1:
            choices = {
                '✔': True,
                '❌': False
            }

            def check(reaction, user):
                """Only get answer by author of command and correct reaction"""
                return user == ctx.message.author and str(reaction.emoji in choices.keys())

            current_raid = current_raids[0]

            question_msg = await ctx.send(messages.can_delete_self_raid)
            # Add reaction choices
            [await question_msg.add_reaction(emoji) for emoji in choices.keys()]

            try:
                # Wait for user answer
                reaction, user = await self.bot.wait_for('reaction_add', timeout=300.0, check=check)
            except asyncio.TimeoutError:
                log_template.command_fail(ctx, logger_msgs.user_not_response)
                await ctx.message.add_reaction('❌')
            else:
                emoji = str(reaction.emoji)
                answer = choices[emoji]

                log_template.user_answer(ctx, emoji)

                if answer:
                    current_raid.end_work()
                    self.raid_list.remove(current_raid)

                    await ctx.message.add_reaction('✔')
                    log_template.command_success(ctx)
                else:
                    await ctx.message.add_reaction('❌')

        else:
            choices = {
                '1️⃣': 1, '2️⃣': 2, '3️⃣': 3, '4️⃣️': 4, '5️⃣': 5
            }

            def check(reaction, user):
                """Only get answer by author of command and correct reaction"""
                return user == ctx.message.author and str(reaction.emoji in choices.keys())

            question_msg_content = messages.can_delete_self_raids

            # Create choices message to user with all his raids
            raids_information = []
            for number, some_raid in enumerate(current_raids):
                raids_information.append(
                    messages.raid_parameters.format(
                        number=number + 1, time_leaving=some_raid.raid_time.time_leaving, server=some_raid.server
                    )
                )

            question_msg_content = ''.join((question_msg_content, *raids_information))

            question_msg = await ctx.send(question_msg_content)
            # Add reaction choices
            [await question_msg.add_reaction(emoji) for emoji in list(choices.keys())[:len(current_raids)]]

            try:
                # Wait for user answer
                reaction, user = await self.bot.wait_for('reaction_add', timeout=300.0, check=check)
            except asyncio.TimeoutError:
                log_template.command_fail(ctx, logger_msgs.user_not_response)
                await ctx.message.add_reaction('❌')
            else:
                emoji = str(reaction.emoji)
                answer = choices[emoji]
                current_raid = current_raids[answer - 1]

                log_template.user_answer(ctx, emoji)

                current_raid.end_work()
                self.raid_list.remove(current_raid)

                await ctx.message.add_reaction('✔')
                log_template.command_success(ctx)

    @commands.command(name=command_names.function_command.remove_raid, help=help_text.remove_raid)
    @commands.guild_only()
    @commands.has_role('Капитан')
    async def remove_raid(self, ctx: Context, captain_name='', time_leaving=''):
        """
        Remove available raid

        Attributes:
        ----------
        captain_name: str
            Name of the captain that created the raid.
        time_leaving: str or None
            Time when raid leaving. Required to fill if captain has more than one raid.
        """
        # Checking correct inputs arguments
        await check_input.validation(**locals())

        # If no parameters than try to remove user raid.
        if not captain_name:
            await self.remove_captain_raid(ctx)
            return

        curr_raid = self.raid_list.find_raid(ctx.guild.id, ctx.channel.id, captain_name, time_leaving)
        if curr_raid:
            curr_raid.end_work()
            self.raid_list.remove(curr_raid)

            await ctx.message.add_reaction('✔')
            log_template.command_success(ctx)
        else:
            await ctx.message.add_reaction('❌')
            log_template.command_fail(ctx, logger_msgs.raid_not_found)

    @commands.command(name=command_names.function_command.collection, help=help_text.collection)
    @commands.guild_only()
    @commands.has_role('Капитан')
    async def collection(self, ctx: Context, captain_name='', time_leaving=''):
        """
        Send collection messaged to current channel and
        allowed users to get into the raid by adding reaction on collection message.

        Attributes:
        ----------
        captain_name: str
            Name of the captain that created the raid.
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

        # Try find the raid with this credentials
        curr_raid = self.raid_list.find_raid(
            ctx.guild.id, ctx.channel.id, captain_name, time_leaving, ignore_channels=True
        )

        # Does this captain have a raid with these parameters?
        if not curr_raid:
            await ctx.message.add_reaction('❌')
            log_template.command_fail(ctx, logger_msgs.raid_not_found)
            return

        # Stop async task if such exists for this raid
        guild_id = ctx.guild.id
        if curr_raid.first_collection_task and curr_raid.first_coll_guild_id == guild_id:
            curr_raid.first_collection_task.cancel()

        # Get raid collection msg
        raid_coll_msg = curr_raid.raid_coll_msgs.get(guild_id)

        # Stop async task of collection for this guild
        if raid_coll_msg and raid_coll_msg.coll_sleep_task:
            curr_raid.coll_sleep_task.cancel()

        raid_coll_msg = curr_raid.start_collection(guild_id, ctx.channel.id)

        # Send message about collection
        collection_msg = await raid_coll_msg.send_coll_msg(ctx)
        await collection_msg.add_reaction('❤')

        # Start raid_time_process
        if curr_raid.is_first_collection:
            curr_raid.is_first_collection = False
            asyncio.ensure_future(self.raid_time_process(ctx, curr_raid, raid_coll_msg))

        log_template.command_success(ctx)

    async def raid_time_process(self, ctx: Context, curr_raid: Raid, raid_coll_msg: RaidCollMsg):
        # Remove the time that has already passed
        curr_raid.raid_time.validate_time()

        # Notify user if possible before leaving
        asyncio.ensure_future(self.notify_about_leaving(curr_raid))

        raid_time = curr_raid.raid_time.time_to_display.copy()
        for time_display in raid_time:
            curr_raid.save_raid()

            # Update text msg of start collection Raid
            await curr_raid.update_coll_msgs(self.bot)

            # Wait next time to display raid table
            secs_left = curr_raid.raid_time.secs_left_to_display()
            raid_coll_msg.coll_sleep_task = asyncio.create_task(asyncio.sleep(secs_left))
            await raid_coll_msg.coll_sleep_task

            curr_raid.raid_time.time_passed()

            # Resend new message with raid table if not first time else just send table
            await curr_raid.update_table_msgs(self.bot)

        await self.database.captain.update_captain(str(ctx.author), curr_raid)

        await self.remove_raid(ctx, curr_raid.captain_name, curr_raid.raid_time.time_leaving)

        await curr_raid.send_end_work_msgs(self.bot)

    async def check_captain_registration(self, user: discord.User, captain_name: str):
        """
        Register captain in database if he is not registered yet

        Attributes:
        ----------
        user: discord.User
            discord user that captain
        captain_name: str
            game nickname of user
        """
        nickname = await self.database.user.find_user(str(user))
        if nickname == captain_name:
            return
        else:
            await self.database.user.rereg_user(user.id, str(user), captain_name)

    async def check_raid_exists(self, ctx: Context, captain_name: str, time_leaving=''):
        """
        Check raid exist by this captain. If raid exist ask captain.

        Attributes:
        ----------
        captain_name: str
            Name of the captain that created the raid.
        time_leaving: str or None
            Time when raid leaving. Required to fill if captain has more than one raid.
        """
        # Check captain exists
        captain_post = await self.database.captain.find_captain_post(str(ctx.author))
        if not captain_post:
            await self.database.captain.create_captain(str(ctx.author))

        # Check raid exists of this captain
        captain_raids = self.captain_raids(captain_name)
        if not captain_raids:
            return

        # If raid with this credentials absolutely matched
        for captain_raid in captain_raids:
            if captain_raid.raid_time.time_leaving == time_leaving:
                await ctx.author.send(messages.raid_exist_error)

                await ctx.message.add_reaction('❌')
                log_template.command_fail(ctx, logger_msgs.raid_exist)
                raise commands.errors.UserInputError('Такой рейд уже существует.')

        active_raids = self.captain_raids_str(captain_name)
        message = await ctx.author.send(messages.raid_exist_warning + active_raids)
        await message.add_reaction('✔')
        await message.add_reaction('❌')

        def check(reaction, user):
            """Process answer only by author of command and correct reaction"""
            return user.id == ctx.message.author.id and (str(reaction.emoji) == '✔' or str(reaction.emoji) == '❌')

        # Wait answer of user
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=300.0, check=check)
        except asyncio.TimeoutError:
            log_template.command_fail(ctx, logger_msgs.user_not_response)
            raise commands.errors.UserInputError('Капитан не ответил на вопрос о создании рейда')
        else:
            emoji = str(reaction.emoji)
            log_template.user_answer(ctx, emoji)

            if emoji == '❌':
                raise commands.errors.UserInputError('Капитан отказался создавать новый рейд')

    @commands.command(name=command_names.function_command.captain, help=help_text.captain)
    @commands.guild_only()
    @commands.has_role('Капитан')
    async def captain(self, ctx: Context,
                      captain_name: str, server: str, time_leaving: str, time_reservation_open='', reservation_count=0):
        """
        Create raid. Start process of collection user into the new raid.

        Attributes:
        ----------
        captain_name: str
            Nickname of user who drove people.
        server: str
            Game server where captain will carry.
        time_leaving: str
            Time when raid will sail.
        time_reservation_open: str or None
            Time when bot start collection people in raid.
            If None than start collection after one minute.
        reservation_count: int or 0
            Amount of places which cannot be borrowed
        """
        await check_input.validation(**locals())
        await self.check_raid_exists(ctx, captain_name, time_leaving)
        await self.check_captain_registration(ctx.author, captain_name)

        if not time_reservation_open:
            time_reservation_open = tools.now_time_plus_minute()

        new_raid = Raid(
            captain_name,
            server,
            time_leaving,
            time_reservation_open,
            ctx.guild.id,
            ctx.channel.id,
            reservation_count
        )
        self.raid_list.append(new_raid)
        new_raid.start_collection(ctx.guild.id, ctx.channel.id)

        await ctx.send(messages.raid_created.format(time_reservation_open=time_reservation_open))
        await ctx.message.add_reaction('✔')
        log_template.command_success(ctx)

        # Wait time reservation open
        time_left_sec = tools.get_sec_left(time_reservation_open)
        sleep_task = asyncio.create_task(asyncio.sleep(time_left_sec))
        new_raid.first_collection_task = sleep_task
        await sleep_task

        # Start raid collection
        await self.collection(ctx, captain_name, time_leaving)

    @commands.command(name=command_names.function_command.cap, help=help_text.cap)
    @commands.guild_only()
    @commands.has_role('Капитан')
    async def cap(self, ctx: Context):
        """
        Short version of command captain. In this way user choose old parameters of raid by adding reaction.
        """
        # Dict of controlling emoji
        NUMBER_REACTIONS = {
            '1️⃣': 1, '2️⃣': 2, '3️⃣': 3,
            1: '1️⃣', 2: '2️⃣', 3: '3️⃣'
        }

        user = str(ctx.author)
        captain_post = await self.database.captain.find_captain_post(user)

        # Get parameters of old raids
        if not captain_post:
            await ctx.message.add_reaction('❌')
            await ctx.author.send(messages.new_captain)
            log_template.command_fail(ctx, logger_msgs.captain_not_exist)
            return
        last_raids = captain_post.get('last_raids')

        raids_msg = messages.raid_create_choice_start.format(captain_name=captain_post['captain_name'])

        # Generate list of choices
        for index, last_raid in enumerate(last_raids):
            raids_msg += messages.raid_create_choice_server_time.format(
                index=index + 1, server=last_raid['server'], time_leaving=last_raid['time_leaving']
            )
            if last_raid.get('time_reservation_open'):
                raids_msg += messages.raid_create_choice_res_open.format(
                    time_reservation_open=last_raid['time_reservation_open']
                )
            if last_raid.get('reservation_count') and not last_raid['reservation_count'] == 1:
                raids_msg += messages.raid_create_choice_count.format(reservation_count=last_raid['reservation_count'])
            raids_msg += '.\n'

        # Send list of choices and add controlling reactions
        msg = await ctx.send(raids_msg)
        for number in range(len(last_raids)):
            await msg.add_reaction(NUMBER_REACTIONS[number + 1])

        def check(reaction, user):
            """Only get answer by author of command and correct reaction"""
            return (
                    user == ctx.message.author and
                    (
                            str(reaction.emoji) == '1️⃣' or str(reaction.emoji) == '2️⃣' or str(reaction.emoji) == '3️⃣'
                    )
            )

        try:
            # Wait for user answer
            reaction, user = await self.bot.wait_for('reaction_add', timeout=600.0, check=check)
        except asyncio.TimeoutError:
            log_template.command_fail(ctx, logger_msgs.user_not_response)
            await ctx.message.add_reaction('❌')
        else:
            emoji = str(reaction.emoji)
            log_template.user_answer(ctx, emoji)
            user_choice = NUMBER_REACTIONS[emoji]

            user_raid = last_raids[user_choice - 1]
            await self.captain(
                ctx,
                captain_post.get('captain_name'),
                user_raid.get('server'),
                user_raid.get('time_leaving'),
                user_raid.get('time_reservation_open'),
                user_raid.get('reservation_count'),
            )


def setup(bot):
    bot.add_cog(RaidCreation(bot))
    log_template.cog_launched('RaidCreation')
