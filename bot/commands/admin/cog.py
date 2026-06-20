import logging
from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands
from sqlalchemy import select, func

from bot.database import AsyncSessionLocal
from bot.database.models import Apoiador, GuildConfig, PixConfig
from bot.servicos.SupporterRoleManager import SupporterRoleManager

from .utils import check_is_owner, _build_role_config_embed
from .views_base import ConfirmationView
from .views_dashboard import DashboardView
from .views_pix import PIXConfigView
from .views_roles import DefaultRoleSelectView, TimeRoleConfigView, RoleConfigView
from .views_supporter import ManageSupporterView

logger = logging.getLogger(__name__)


class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.role_manager = SupporterRoleManager(bot)

    async def _get_dashboard_stats(self):
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(func.count(Apoiador.id)).where(Apoiador.ativo == True)
            )
            total_apoiadores = result.scalar()

            thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
            result = await session.execute(
                select(func.count(Apoiador.id)).where(
                    Apoiador.ultimo_pagamento >= thirty_days_ago,
                    Apoiador.ativo == True
                )
            )
            recentes = result.scalar()

            result = await session.execute(
                select(func.sum(Apoiador.valor_doacao)).where(Apoiador.ativo == True)
            )
            receita_total = (result.scalar() or 0) / 100
            total_servidores = len(self.bot.guilds)

        return {
            'total_apoiadores': total_apoiadores,
            'recentes': recentes,
            'receita_total': receita_total,
            'total_servidores': total_servidores
        }

    async def _manage_supporter_action(
        self,
        interaction: discord.Interaction,
        discord_id: str,
        action: str,
        months: int = None,
        tipo_apoio: str = "manual",
        already_deferred: bool = False
    ):
        """Função auxiliar para gerenciar apoiadores.

        Se already_deferred=True, usa followup.send() em vez de response.send_message().
        """
        from datetime import datetime
        from dateutil.relativedelta import relativedelta

        guild_id = str(interaction.guild.id)

        async def reply(content=None, embed=None, ephemeral=True):
            if already_deferred:
                await interaction.followup.send(content=content, embed=embed, ephemeral=ephemeral)
            else:
                await interaction.response.send_message(content=content, embed=embed, ephemeral=ephemeral)

        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(Apoiador).where(
                        Apoiador.discord_id == discord_id,
                        Apoiador.guild_id == guild_id
                    )
                )
                apoiador = result.scalars().first()
                now = datetime.now(timezone.utc)

                if action == 'adicionar':
                    if not apoiador:
                        data_inicio = now - relativedelta(months=months)
                        data_expiracao = now
                        apoiador = Apoiador(
                            discord_id=discord_id,
                            guild_id=guild_id,
                            tipo_apoio=tipo_apoio,
                            duracao_meses=months,
                            data_inicio=data_inicio,
                            ultimo_pagamento=now,
                            ativo=True,
                            data_expiracao=data_expiracao,
                            cargo_atribuido=False,
                            ja_pago=True
                        )
                        session.add(apoiador)
                        message = f"✅ Apoiador criado com {months} meses retroativos e expira em 1 mês"
                    else:
                        if apoiador.ativo:
                            if apoiador.data_expiracao:
                                apoiador.data_expiracao += relativedelta(months=months)
                            else:
                                apoiador.data_expiracao = now + relativedelta(months=months)
                            apoiador.duracao_meses = (apoiador.duracao_meses or 0) + months
                            apoiador.ultimo_pagamento = now
                            message = f"✅ Apoiador estendido: +{months} meses (total: {apoiador.duracao_meses} meses)"
                        else:
                            apoiador.ativo = True
                            apoiador.data_expiracao = now + relativedelta(months=months)
                            apoiador.duracao_meses = months
                            apoiador.ultimo_pagamento = now
                            message = f"✅ Apoiador reativado: {months} meses de {tipo_apoio}"

                elif action == 'pausar':
                    if not apoiador or not apoiador.ativo:
                        await reply(content="❌ Apoiador não encontrado ou já inativo.")
                        return False
                    apoiador.ativo = False
                    message = "✅ Apoiador pausado (doações interrompidas)"

                elif action == 'continuar':
                    if not apoiador:
                        await reply(content="❌ Apoiador não encontrado.")
                        return False
                    if apoiador.ativo:
                        await reply(content="❌ Apoiador já está ativo.")
                        return False
                    apoiador.ativo = True
                    apoiador.ultimo_pagamento = now
                    message = "✅ Apoiador reativado (doações continuadas)"

                elif action == 'remover':
                    if not apoiador:
                        await reply(content="❌ Apoiador não encontrado.")
                        return False
                    await session.delete(apoiador)
                    message = "✅ Apoiador removido do sistema"

                await session.commit()

            try:
                member = interaction.guild.get_member(int(discord_id))
                if member:
                    if action in ['adicionar', 'continuar']:
                        await self.role_manager.assign_default_supporter_role(member)
                        await self.role_manager.update_member_time_based_roles(member)
                    else:
                        config = await self.role_manager.get_guild_config(guild_id)
                        if config and config.cargo_apoiador_default:
                            role = interaction.guild.get_role(int(config.cargo_apoiador_default))
                            if role and role in member.roles:
                                await member.remove_roles(role)
            except Exception as e:
                logger.error(f"Erro ao atualizar cargos: {e}")

            embed = discord.Embed(
                title="✅ Apoiador Gerenciado",
                color=discord.Color.green(),
                description=message
            )
            embed.add_field(name="Usuário", value=f"<@{discord_id}>", inline=True)
            embed.add_field(name="Ação", value=action.title(), inline=True)
            if months:
                embed.add_field(name="Meses", value=str(months), inline=True)

            await reply(embed=embed)
            logger.info(f"Apoiador gerenciado por {interaction.user}: {discord_id} - {action}")
            return True

        except Exception as e:
            await reply(content=f"❌ Erro: {str(e)}")
            logger.error(f"Erro ao gerenciar apoiador: {e}")
            return False

    # ==================== SLASH COMMANDS ====================

    @discord.app_commands.command(name="add_supporter", description="[ADMIN] Adicionar ou estender apoio de um usuário")
    async def add_supporter(self, interaction: discord.Interaction, user: discord.User, months: int, type: str = "manual"):
        if not check_is_owner(interaction):
            await interaction.response.send_message("❌ Apenas admins podem usar esse comando!", ephemeral=True)
            return
        if months <= 0:
            await interaction.response.send_message("❌ O número de meses deve ser maior que 0.", ephemeral=True)
            return
        await self._manage_supporter_action(interaction, str(user.id), 'adicionar', months=months, tipo_apoio=type)

    @discord.app_commands.command(name="pause_supporter", description="[ADMIN] Pausar apoio de um usuário")
    async def pause_supporter(self, interaction: discord.Interaction, user: discord.User):
        if not check_is_owner(interaction):
            await interaction.response.send_message("❌ Apenas admins podem usar esse comando!", ephemeral=True)
            return
        await self._manage_supporter_action(interaction, str(user.id), 'pausar')

    @discord.app_commands.command(name="resume_supporter", description="[ADMIN] Retomar apoio de um usuário")
    async def resume_supporter(self, interaction: discord.Interaction, user: discord.User):
        if not check_is_owner(interaction):
            await interaction.response.send_message("❌ Apenas admins podem usar esse comando!", ephemeral=True)
            return
        await self._manage_supporter_action(interaction, str(user.id), 'continuar')

    @discord.app_commands.command(name="remove_supporter", description="[ADMIN] Remover apoio de um usuário")
    async def remove_supporter(self, interaction: discord.Interaction, user: discord.User):
        if not check_is_owner(interaction):
            await interaction.response.send_message("❌ Apenas admins podem usar esse comando!", ephemeral=True)
            return
        await self._manage_supporter_action(interaction, str(user.id), 'remover')

    @commands.hybrid_command(name="dashboard", description="[ADMIN] Mostra o painel de controle com estatísticas dos apoiadores")
    async def dashboard(self, ctx: commands.Context):
        if not check_is_owner(ctx.interaction if hasattr(ctx, 'interaction') else ctx):
            ephemeral = bool(ctx.interaction)
            await ctx.send("❌ Apenas admins podem usar esse comando!", ephemeral=ephemeral)
            return
        try:
            if ctx.interaction:
                await ctx.interaction.response.defer(ephemeral=True)

            stats = await self._get_dashboard_stats()

            embed = discord.Embed(
                title="📊 Painel de Controle - HugMe Bot",
                color=discord.Color.blue(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="👥 Apoiadores Ativos", value=f"{stats['total_apoiadores'] or 0}", inline=True)
            embed.add_field(name="🆕 Doações Recentes (30d)", value=f"{stats['recentes'] or 0}", inline=True)
            embed.add_field(name="💰 Receita Total", value=f"R$ {stats['receita_total']:.2f}", inline=True)
            embed.add_field(name="🏠 Servidores", value=f"{stats['total_servidores']}", inline=True)
            embed.set_footer(text="Clique nos botões abaixo para gerenciar tudo!")

            view = DashboardView(self.bot, self)
            if ctx.interaction:
                await ctx.interaction.followup.send(embed=embed, view=view, ephemeral=True)
            else:
                await ctx.send(embed=embed, view=view)
            logger.info(f"Dashboard exibido para {ctx.author}")
        except Exception as e:
            ephemeral = bool(ctx.interaction)
            if ctx.interaction:
                await ctx.interaction.followup.send(f"❌ Erro ao carregar dashboard: {str(e)}", ephemeral=ephemeral)
            else:
                await ctx.send(f"❌ Erro ao carregar dashboard: {str(e)}")
            logger.error(f"Erro no dashboard: {e}")

    @commands.hybrid_command(name="servers", description="[ADMIN] Lista todos os servidores onde o bot está presente")
    async def servers(self, ctx: commands.Context):
        if not check_is_owner(ctx.interaction if hasattr(ctx, 'interaction') else ctx):
            ephemeral = bool(ctx.interaction)
            await ctx.send("❌ Apenas admins podem usar esse comando!", ephemeral=ephemeral)
            return
        try:
            embed = discord.Embed(
                title="🏠 Servidores do Bot",
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc)
            )
            server_list = [
                f"**{guild.name}** (ID: {guild.id}) - {guild.member_count or 0} membros"
                for guild in self.bot.guilds
            ]
            embed.description = "\n".join(server_list) if server_list else "Nenhum servidor encontrado."
            embed.set_footer(text=f"Total: {len(self.bot.guilds)} servidores")
            await ctx.send(embed=embed, ephemeral=True)
            logger.info(f"Lista de servidores exibida para {ctx.author}")
        except Exception as e:
            await ctx.send(f"❌ Erro ao listar servidores: {str(e)}", ephemeral=True)
            logger.error(f"Erro na listagem de servidores: {e}")

    @commands.hybrid_command(name="configure_role", description="[ADMIN] Configura cargos de apoiador para um servidor")
    async def configure_role(self, ctx: commands.Context):
        if not check_is_owner(ctx.interaction if hasattr(ctx, 'interaction') else ctx):
            ephemeral = bool(ctx.interaction)
            await ctx.send("❌ Apenas admins podem usar esse comando!", ephemeral=ephemeral)
            return
        embed = discord.Embed(
            title="ℹ️ Comando Descontinuado",
            description="Use `/set_supporter_role` para configurar cargos de apoiador",
            color=discord.Color.orange()
        )
        ephemeral = bool(ctx.interaction)
        await ctx.send(embed=embed, ephemeral=ephemeral)

    @commands.hybrid_command(name="set_default_supporter_role", description="[ADMIN] Define o cargo padrão que todos os apoiadores terão")
    async def set_default_supporter_role(self, ctx: commands.Context):
        if not check_is_owner(ctx.interaction if hasattr(ctx, 'interaction') else ctx):
            ephemeral = bool(ctx.interaction)
            await ctx.send("❌ Apenas admins podem usar esse comando!", ephemeral=ephemeral)
            return
        if not ctx.guild:
            ephemeral = bool(ctx.interaction)
            await ctx.send("❌ Este comando só funciona em um servidor.", ephemeral=ephemeral)
            return
        try:
            view = DefaultRoleSelectView(self.bot, ctx.guild)
            embed = discord.Embed(
                title="⭐ Selecione o Cargo Padrão de Apoiador",
                description="Este cargo será atribuído automaticamente a todos os apoiadores do servidor",
                color=discord.Color.gold()
            )
            ephemeral = bool(ctx.interaction)
            await ctx.send(embed=embed, view=view, ephemeral=ephemeral)
            logger.info(f"Select de cargo padrão aberto para {ctx.author}")
        except Exception as e:
            ephemeral = bool(ctx.interaction)
            await ctx.send(f"❌ Erro ao abrir seletor: {str(e)}", ephemeral=ephemeral)
            logger.error(f"Erro ao abrir seletor de cargo padrão: {e}")

    @commands.hybrid_command(name="configure_time_roles", description="[ADMIN] Configura cargos baseados no tempo de apoio")
    async def configure_time_roles(self, ctx: commands.Context):
        if not check_is_owner(ctx.interaction if hasattr(ctx, 'interaction') else ctx):
            ephemeral = bool(ctx.interaction)
            await ctx.send("❌ Apenas admins podem usar esse comando!", ephemeral=ephemeral)
            return
        if not ctx.guild:
            ephemeral = bool(ctx.interaction)
            await ctx.send("❌ Este comando só funciona em um servidor.", ephemeral=ephemeral)
            return
        try:
            view = TimeRoleConfigView(self.bot, ctx.guild)
            embed = discord.Embed(
                title="⏳ Configurar Cargos por Tempo de Apoio",
                description="Configure cargos especiais baseados no tempo total de apoio dos membros",
                color=discord.Color.blue()
            )
            ephemeral = bool(ctx.interaction)
            await ctx.send(embed=embed, view=view, ephemeral=ephemeral)
            logger.info(f"Configuração de cargos de tempo aberta para {ctx.author}")
        except Exception as e:
            ephemeral = bool(ctx.interaction)
            await ctx.send(f"❌ Erro ao abrir configuração: {str(e)}", ephemeral=ephemeral)
            logger.error(f"Erro ao abrir configuração de cargos de tempo: {e}")

    @commands.hybrid_command(name="pix_config", description="[ADMIN] Mostra a configuração atual do PIX")
    async def pix_config(self, ctx: commands.Context):
        if not check_is_owner(ctx.interaction if hasattr(ctx, 'interaction') else ctx):
            ephemeral = bool(ctx.interaction)
            await ctx.send("❌ Apenas admins podem usar esse comando!", ephemeral=ephemeral)
            return
        try:
            if ctx.interaction:
                await ctx.interaction.response.defer(ephemeral=True)

            async with AsyncSessionLocal() as session:
                result = await session.execute(select(PixConfig))
                config = result.scalars().first()

            if not config:
                embed = discord.Embed(
                    title="⚠️ Configuração PIX não encontrada",
                    description="Clique em ✏️ Editar para criar uma nova configuração",
                    color=discord.Color.orange()
                )
                ephemeral = bool(ctx.interaction)
                await ctx.send(embed=embed, view=PIXConfigView(), ephemeral=ephemeral)
                return

            embed = discord.Embed(
                title="💳 Configuração PIX",
                color=discord.Color.purple(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="Chave PIX", value=config.chave, inline=False)
            embed.add_field(name="Nome do Titular", value=config.nome_titular, inline=True)
            embed.add_field(name="Cidade", value=config.cidade, inline=True)
            if config.static_qr_url:
                embed.add_field(name="QR Code", value=f"[Ver QR Code]({config.static_qr_url})", inline=False)
            embed.add_field(name="Atualizado em", value=config.atualizado_em.strftime("%d/%m/%Y %H:%M"), inline=True)
            embed.add_field(name="Atualizado por", value=config.atualizado_por or "Desconhecido", inline=True)

            ephemeral = bool(ctx.interaction)
            await ctx.send(embed=embed, view=PIXConfigView(), ephemeral=ephemeral)
            logger.info(f"PIX config mostrada para {ctx.author}")
        except Exception as e:
            ephemeral = bool(ctx.interaction)
            await ctx.send(f"❌ Erro ao mostrar configuração PIX: {str(e)}", ephemeral=ephemeral)
            logger.error(f"Erro ao mostrar PIX config: {e}")

    @commands.hybrid_command(name="manage_supporter", description="[ADMIN] Gerencia apoiadores manualmente")
    async def manage_supporter(self, ctx: commands.Context):
        if not check_is_owner(ctx.interaction if hasattr(ctx, 'interaction') else ctx):
            ephemeral = bool(ctx.interaction)
            await ctx.send("❌ Apenas admins podem usar esse comando!", ephemeral=ephemeral)
            return
        try:
            embed = discord.Embed(
                title="👤 Gerenciar Apoiador Manualmente",
                description="Use o botão abaixo para abrir o formulário de gerenciamento de apoiadores.\n\n"
                            "**Ações disponíveis:**\n"
                            "• **Adicionar**: Cria ou estende apoio manual\n"
                            "• **Pausar**: Interrompe temporariamente o apoio\n"
                            "• **Continuar**: Retoma apoio pausado\n"
                            "• **Remover**: Remove completamente do sistema",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="📝 Como usar",
                value="1. Clique no botão\n2. Digite o ID do usuário ou @menção\n"
                      "3. Escolha a ação\n4. Para 'adicionar', especifique os meses\n"
                      "5. Opcional: tipo de apoio (padrão: manual)",
                inline=False
            )
            view = ManageSupporterView(self.bot, self.role_manager)
            ephemeral = bool(ctx.interaction)
            await ctx.send(embed=embed, view=view, ephemeral=ephemeral)
            logger.info(f"Gerenciamento de apoiador aberto para {ctx.author}")
        except Exception as e:
            ephemeral = bool(ctx.interaction)
            await ctx.send(f"❌ Erro ao abrir gerenciamento: {str(e)}", ephemeral=ephemeral)
            logger.error(f"Erro ao abrir gerenciamento de apoiador: {e}")


async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
