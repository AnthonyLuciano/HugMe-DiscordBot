import discord
from discord.ext import commands

class CheckCommands(commands.Cog):
    """Comandos básicos do bot."""

    @commands.hybrid_command(name='check', description="Verifica se o bot está online")
    async def ping(self, ctx: commands.Context):
        """Responde com 'bot esta online! pronto para ajudar :D'."""
        await ctx.send('bot esta online! pronto para ajudar :D')

async def setup(bot):
    await bot.add_cog(CheckCommands())
