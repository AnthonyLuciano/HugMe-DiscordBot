import discord
from discord.ext import commands

class CheckCommands(commands.Cog):
    """Comandos básicos do bot."""

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name='check', description="Verifica se o bot está online")
    async def check(self, ctx: commands.Context):
        """Responde com 'bot esta online! pronto para ajudar :D'."""
        await ctx.defer()  # Garante os 15 min de janela para responder
        await ctx.send('Bot está online! Pronto para ajudar :D')

    @commands.hybrid_command(name='ajuda', description="Mostra os comandos disponíveis")
    async def help(self, ctx: commands.Context):
        """Mostra uma lista de comandos disponíveis."""
        await ctx.defer()  # Idem

        embed = discord.Embed(
            title="📚 Comandos do Bot",
            description="Aqui estão todos os comandos disponíveis:",
            color=discord.Color.blue()
        )

        for cog_name, cog in self.bot.cogs.items():
            cog_commands = []
            for command in cog.get_commands():
                if not command.hidden:
                    cog_commands.append(f"`/{command.name}` - {command.description or 'Sem descrição'}")
            if cog_commands:
                embed.add_field(
                    name=f"🔧 {cog_name}",
                    value="\n".join(cog_commands),
                    inline=False
                )

        uncategorized_commands = []
        for command in self.bot.commands:
            if not command.cog and not command.hidden:
                uncategorized_commands.append(f"`/{command.name}` - {command.description or 'Sem descrição'}")
        if uncategorized_commands:
            embed.add_field(
                name="🔧 Comandos Gerais",
                value="\n".join(uncategorized_commands),
                inline=False
            )

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(CheckCommands(bot))