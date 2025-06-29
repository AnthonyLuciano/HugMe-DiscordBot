# This file will contain command definitions for the bot. 
# It can be used to register commands that the bot will respond to.

from discord.ext import commands

class BasicCommands(commands.Cog):
    """Comandos básicos do bot."""

    @commands.command(name='ping')
    async def ping(self, ctx):
        """Responde com 'Pong!'."""
        await ctx.send('Pong!')

async def setup(bot):
    await bot.add_cog(BasicCommands())