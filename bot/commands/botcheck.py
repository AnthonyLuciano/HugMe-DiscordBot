import discord
from discord.ext import commands

class CheckCommands(commands.Cog):
    """Comandos básicos do bot."""

    @commands.hybrid_command(name='check', description="Verifica se o bot está online")
    async def check(self, ctx: commands.Context):
        """Responde com 'bot esta online! pronto para ajudar :D'."""
        await ctx.send('Bot está online! Pronto para ajudar :D')

    @commands.hybrid_command(name='ajuda', description="Mostra os comandos disponíveis")
    async def help(self, ctx: commands.Context):
        """Mostra uma lista de comandos disponíveis."""
        embed = discord.Embed(
            title="📚 Comandos do Bot",
            description="Aqui estão os comandos disponíveis:",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="🛠️ Básicos",
            value="`/check` - Verifica se o bot está online\n`!ajuda` - Mostra esta mensagem",
            inline=False
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(CheckCommands(bot))