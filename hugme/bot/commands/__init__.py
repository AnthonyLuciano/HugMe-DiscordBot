# This file will contain command definitions for the bot. 
# It can be used to register commands that the bot will respond to.

from bot.commands.tempo import setup as tempo_setup
from bot.commands.botcheck import setup as botcheck_setup
from bot.commands.doar import setup as doar_setup
from bot.commands.verificarcargo import setup as verificarcargo_setup

async def setup_all(bot):
    await tempo_setup(bot)
    await botcheck_setup(bot)
    await doar_setup(bot)
    await verificarcargo_setup(bot)
    # Adicione outros comandos aqui