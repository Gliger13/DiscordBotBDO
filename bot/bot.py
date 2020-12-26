import logging
import os
import traceback

import discord
from discord.ext import commands

from settings import settings

# Uncomment this to use pyinstaller
from commands import events, base, admin, fun, statistics
from commands.raid_manager import creation, manager, save_load, registration, joining, overview

# Initialization logger
from settings.logger import logger
module_logger = logging.getLogger('my_bot')

intents = discord.Intents(messages=True, guilds=True, reactions=True, members=True)

bot = commands.Bot(command_prefix=settings.PREFIX, intents=intents)

# Load all commands for bot and run bot
# if __name__ == '__main__':
#     for extension in [f.replace('.py', '') for f in os.listdir('commands') if os.path.isfile(os.path.join('commands', f))]:
#         if not extension == '__init__':
#             print(extension)
#             try:
#                 bot.load_extension('commands' + "." + extension)
#             except (discord.ClientException, ModuleNotFoundError):
#                 print(f'Failed to load extension {extension}.')
#                 traceback.print_exc()

# Explicitly loading cogs for pyinstaller
bot.load_extension(f"commands.events")
bot.load_extension(f"commands.base")
bot.load_extension(f"commands.admin")
bot.load_extension(f"commands.fun")
bot.load_extension(f"commands.statistics")
bot.load_extension(f"commands.raid_manager.creation")
bot.load_extension(f"commands.raid_manager.manager")
bot.load_extension(f"commands.raid_manager.save_load")
bot.load_extension(f"commands.raid_manager.registration")
bot.load_extension(f"commands.raid_manager.joining")
bot.load_extension(f"commands.raid_manager.overview")


# Start bot
bot.run(settings.TOKEN)
