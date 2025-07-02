from discord.ext import commands

class CheckCommands(commands.Cog):
    """Comandos básicos do bot."""

    @commands.command(name='check')
    async def ping(self, ctx):
        """Responde com 'bot esta online! pronto para ajudar :D'."""
        await ctx.send('bot esta online! pronto para ajudar :D')

async def setup(bot):
    await bot.add_cog(CheckCommands())
