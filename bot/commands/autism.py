import discord
from discord.ext import commands

class autism(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.hybrid_command(name="autismo", description="the creature")
    async def autismo(self, ctx: commands.Context):
        emoji = discord.utils.get(ctx.guild.emojis, name="thecreature")

        if emoji:
            await ctx.send(str(emoji))
        else:
            await ctx.send("❓")
async def setup(bot):
    await bot.add_cog(autism(bot))