import discord
from discord.ext import commands
import re

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
            # Tenta extrair o ID da menção, se necessário
            target_id = self.extract_id_from_mention(target_id)
            
            if is_channel:
                # Verifica se o ID é de um canal
                channel = await ctx.bot.fetch_channel(int(target_id))
                await channel.send(message)
                await ctx.send(f"✅ Mensagem enviada para canal #{channel.name}", ephemeral=True)
            else:
                # Verifica se o ID é de um usuário ou cargo
                if target_id == "everyone":
                    # Mensagem para @everyone
                    await ctx.send(message, allowed_mentions=discord.AllowedMentions(everyone=True))
                elif target_id == "here":
                    # Mensagem para @here
                    await ctx.send(message, allowed_mentions=discord.AllowedMentions(roles=True))
                else:
                    # Caso padrão: pode ser um cargo ou um usuário
                    try:
                        user = await ctx.bot.fetch_user(int(target_id))
                        await user.send(message)
                        await ctx.send(f"✅ Mensagem enviada para {user.name}", ephemeral=True)
                    except discord.NotFound:
                        # Se não for um usuário, tenta encontrar um cargo
                        role = discord.utils.get(ctx.guild.roles, id=int(target_id))
                        if role:
                            await ctx.send(message, allowed_mentions=discord.AllowedMentions(roles=True))
                            await ctx.send(f"✅ Mensagem enviada para o cargo {role.name}", ephemeral=True)
                        else:
                            await ctx.send("❌ ID inválido ou cargo não encontrado", ephemeral=True)
        except ValueError:
            await ctx.send("❌ ID inválido (deve ser numérico ou uma menção válida)", ephemeral=True)
        except discord.NotFound:
            await ctx.send(f"❌ {'Canal' if is_channel else 'Usuário'} não encontrado", ephemeral=True)
        except discord.Forbidden:
            await ctx.send("❌ Sem permissão para enviar mensagem", ephemeral=True)
        except Exception as e:
            await ctx.send(f"❌ Erro: {str(e)}", ephemeral=True)

    def extract_id_from_mention(self, target_id: str) -> str:
        """Extrai o ID de uma menção de usuário, cargo ou canal"""
        user_mention_pattern = r"<@!?(\d+)>"
        channel_mention_pattern = r"<#(\d+)>"
        role_mention_pattern = r"<@&(\d+)>"

        # Tenta extrair menção de usuário
        user_match = re.match(user_mention_pattern, target_id)
        if user_match:
            return user_match.group(1)

        # Tenta extrair menção de canal
        channel_match = re.match(channel_mention_pattern, target_id)
        if channel_match:
            return channel_match.group(1)

        # Tenta extrair menção de cargo
        role_match = re.match(role_mention_pattern, target_id)
        if role_match:
            return role_match.group(1)

        # Se for 'everyone' ou 'here'
        if target_id.lower() == "@everyone":
            return "everyone"
        elif target_id.lower() == "@here":
            return "here"

        # Se não for uma menção válida, assume que o target_id é um ID direto
        return target_id

async def setup(bot):
    await bot.add_cog(DMUserCommands(bot))
