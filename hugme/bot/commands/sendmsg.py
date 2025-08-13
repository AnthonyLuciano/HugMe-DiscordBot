import discord
from discord.ext import commands

class DMUserCommands(commands.Cog):
    """Comandos para enviar mensagens diretas a usuários/canais específicos"""

    @commands.hybrid_command(name='sendmessage', description="Envia mensagem para usuário/canal (admin only)")
    @discord.app_commands.checks.has_permissions(administrator=True)
    async def sendmessage(
        self,
        ctx: commands.Context,
        target_id: str,
        *,
        message: str,
        is_channel: bool = False
    ):
        """Envia mensagem para um usuário ou canal específico"""
        try:
            if is_channel:
                channel = await ctx.bot.fetch_channel(int(target_id))
                await channel.send(message)
                await ctx.send(f"✅ Mensagem enviada para canal #{channel.name}", ephemeral=True)
            else:
                user = await ctx.bot.fetch_user(int(target_id))
                await user.send(message)
                await ctx.send(f"✅ Mensagem enviada para {user.name}", ephemeral=True)
        except ValueError:
            await ctx.send("❌ ID inválido (deve ser numérico)", ephemeral=True)
        except discord.NotFound:
            await ctx.send(f"❌ {'Canal' if is_channel else 'Usuário'} não encontrado", ephemeral=True)
        except discord.Forbidden:
            await ctx.send("❌ Sem permissão para enviar mensagem", ephemeral=True)
        except Exception as e:
            await ctx.send(f"❌ Erro: {str(e)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(DMUserCommands(bot))