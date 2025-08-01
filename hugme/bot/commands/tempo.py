import discord
from discord.ext import commands
from datetime import datetime, timezone, timedelta
from bot.servicos.VerificacaoMembro import VerificacaoMembro

class TempoCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.verificador = VerificacaoMembro(bot)

    @commands.hybrid_command(
        name='tempo',
        description="Mostra há quanto tempo um membro está no servidor")
    async def check_member_time(self,ctx: commands.Context,member: discord.Member = commands.parameter(default=None,description="Membro para consultar (opcional)")):
        """Mostra há quanto tempo um membro está no servidor"""
        member = member or ctx.author
        tempo = await self.verificador.tempo_servidor(member)
        await ctx.send(f"⏳ **{member.display_name}** está no servidor há **{tempo}**")

async def setup(bot):
    await bot.add_cog(TempoCommand(bot))