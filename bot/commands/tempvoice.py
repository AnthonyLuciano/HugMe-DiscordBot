import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)

class TempVoice(commands.Cog): 
    def __init__(self, bot):
        self.bot = bot
        self.create_channel_name = "Entre Aqui Para Criar Canal"
        self.temp_channels = {}
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before, after):
        if after.channel and after.channel.name == self.create_channel_name:
            guild = member.guild
            category = after.channel.category
            
            try:
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(
                    view_channel=False,
                    connect=False
                ),
                    member: discord.PermissionOverwrite(
                    view_channel=True,
                    connect=True,
                    manage_channels=True,
                    mute_members=True,
                    move_members=True
                ),
                guild.me: discord.PermissionOverwrite(  # Permissões do bot
                    view_channel=True,
                    connect=True,
                    manage_channels=True,
                    move_members=True
                )
                }

                temp_channel = await guild.create_voice_channel(
                    name=f"{member.display_name} 💬",
                    category=category,
                    overwrites=overwrites
                )

                self.temp_channels[temp_channel.id] = member.id

                await member.move_to(temp_channel)
                logger.info(f"Canal temporário criado: {temp_channel.name}")

            except Exception as e:
                logger.error(f"Erro ao criar canal temporário: {e}")
        
        if before.channel:
            channel = before.channel
            
            if channel.id in self.temp_channels and len(channel.members) == 0:
                try:
                    await channel.delete()
                    logger.info(f"Canal temporário deletado: {channel.name}")
                    del self.temp_channels[channel.id]
                except Exception as e:
                    logger.error(f"Erro ao deletar canal temporário: {e}")

async def setup(bot):
    await bot.add_cog(TempVoice(bot))