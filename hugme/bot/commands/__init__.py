# This file will contain command definitions for the bot. 
# It can be used to register commands that the bot will respond to.

from bot.commands.tempo import setup as tempo_setup

async def setup_all(bot):
    await tempo_setup(bot)
    # Adicione outros comandos aqui