import discord
from discord.ext import commands
import random

class HugCommands(commands.Cog):
    """Comandos para abraços"""

    def __init__(self, bot):
        self.bot = bot
        self.hug_gifs = [
            "https://media.tenor.com/6jaDm2Pv6dUAAAAi/dare-aggie-dare-aggie-bunny.gif",
            "https://media.tenor.com/dZnXXorasI0AAAAi/hug.gif",
            "https://media.tenor.com/eEltmuPyMHUAAAAi/hugs-hug.gif"
        ]

    @commands.hybrid_command(name='hug', description="Abraça um usuário e mostra um gif de abraço")
    async def hug(self, ctx: commands.Context, user: discord.Member = None):
        """Abraça um usuário com um gif aleatório"""
        try:
            if user is None:
                user = ctx.author  # Abraça a si mesmo se nenhum usuário for mencionado

            if user == ctx.author:
                description = f"{ctx.author.mention} se abraçou! 🤗"
            else:
                description = f"{ctx.author.mention} abraçou {user.mention}! 🤗"

            # Seleciona um gif de abraço aleatório da lista local
            gif_url = random.choice(self.hug_gifs)

            embed = discord.Embed(
                description=description,
                color=discord.Color.pink()
            )
            embed.set_image(url=gif_url)

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Erro: {str(e)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(HugCommands(bot))