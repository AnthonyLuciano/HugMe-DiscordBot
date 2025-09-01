# This file will contain command definitions for the bot. 
# It can be used to register commands that the bot will respond to.

from bot.commands.tempo import setup as tempo_setup
from bot.commands.botcheck import setup as botcheck_setup
from bot.commands.doar import setup as doar_setup
from bot.commands.verificarcargo import setup as verificarcargo_setup
from bot.commands.sendmsg import setup as sendmsg_setup
from bot.commands.admin import setup as admin_setup
from bot.commands.deepseekchat import setup as deepseekchat_setup
from bot.commands.rpg_system import setup as rpg_system_setup

async def setup_all(bot):
    await tempo_setup(bot)
    await botcheck_setup(bot)
    await doar_setup(bot)
    await verificarcargo_setup(bot)
    await sendmsg_setup(bot)
    await admin_setup(bot)
    await deepseekchat_setup(bot)
    await rpg_system_setup(bot)
    # Adicione outros comandos aqui