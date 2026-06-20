import logging
from datetime import datetime, timezone

import discord
from discord import ui
from sqlalchemy import select

from bot.database import AsyncSessionLocal
from bot.database.models import Apoiador, GuildConfig, PixConfig
from .utils import check_is_owner, _build_role_config_embed
from .views_base import ConfirmationView
from .views_pix import PIXConfigView
from .views_roles import RoleConfigView
from .views_supporter import ManageSupporterView

logger = logging.getLogger(__name__)


class SupportersPaginationView(ui.View):
    """View para mostrar apoiadores com paginação"""
    def __init__(self, apoiadores, per_page=8):
        super().__init__(timeout=300)
        self.apoiadores = apoiadores
        self.per_page = per_page
        self.current_page = 0
        self.total_pages = max(1, (len(apoiadores) + per_page - 1) // per_page)
        self.update_buttons()

    def update_buttons(self):
        for item in list(self.children):
            if isinstance(item, ui.Button):
                self.remove_item(item)

        prev_button = ui.Button(label="⬅️ Anterior", style=discord.ButtonStyle.primary)
        prev_button.callback = self.prev_page
        prev_button.disabled = self.current_page == 0
        self.add_item(prev_button)

        page_info = ui.Button(
            label=f"Página {self.current_page + 1}/{self.total_pages} ({len(self.apoiadores)} total)",
            style=discord.ButtonStyle.gray,
            disabled=True
        )
        self.add_item(page_info)

        next_button = ui.Button(label="Próximo ➡️", style=discord.ButtonStyle.primary)
        next_button.callback = self.next_page
        next_button.disabled = self.current_page >= self.total_pages - 1
        self.add_item(next_button)

    def get_embed(self):
        start_idx = self.current_page * self.per_page
        end_idx = min(start_idx + self.per_page, len(self.apoiadores))
        page_apoiadores = self.apoiadores[start_idx:end_idx]

        embed = discord.Embed(
            title=f"👥 Apoiadores Ativos - Página {self.current_page + 1}/{self.total_pages}",
            color=discord.Color.gold(),
            timestamp=datetime.now(timezone.utc)
        )

        if not page_apoiadores:
            embed.description = "Nenhum apoiador nesta página."
            return embed

        supporter_list = []
        for apo in page_apoiadores:
            expiry = apo.data_expiracao.strftime("%d/%m/%Y") if apo.data_expiracao else "Permanente"
            inicio = apo.data_inicio.strftime("%d/%m/%Y") if apo.data_inicio else "Desconhecida"
            supporter_list.append(
                f"**<@{apo.discord_id}>**\n"
                f"└ {apo.tipo_apoio} • Nível {apo.nivel} • Início: `{inicio}` • Expira: `{expiry}`"
            )

        embed.description = "\n\n".join(supporter_list)
        embed.set_footer(text=f"Mostrando {start_idx + 1}-{end_idx} de {len(self.apoiadores)} apoiadores")
        return embed

    async def prev_page(self, interaction: discord.Interaction):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_embed(), view=self)

    async def next_page(self, interaction: discord.Interaction):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_embed(), view=self)


class DashboardView(ui.View):
    def __init__(self, bot, cog):
        super().__init__(timeout=None)
        self.bot = bot
        self.cog = cog

    async def check_owner(self, interaction: discord.Interaction) -> bool:
        if not check_is_owner(interaction):
            await interaction.response.send_message(
                "❌ Apenas admins podem usar essa função!",
                ephemeral=True
            )
            return False
        return True

    def _handle_expired(self, interaction: discord.Interaction, e: Exception):
        """Trata erros de interação expirada (10062)."""
        if hasattr(e, 'code') and e.code == 10062:
            async def _send_dm():
                try:
                    await interaction.user.send(
                        "A sessão do painel expirou após 15 minutos. Execute o comando `/dashboard` novamente para uma nova sessão."
                    )
                except discord.Forbidden:
                    logger.warning(f"Não foi possível enviar DM para {interaction.user} sobre expiração da sessão")
            import asyncio
            asyncio.create_task(_send_dm())
        else:
            logger.error(f"Erro inesperado no DashboardView: {e}")

    @ui.button(label="🔄 Atualizar", style=discord.ButtonStyle.primary)
    async def refresh(self, interaction: discord.Interaction, button: ui.Button):
        try:
            if not await self.check_owner(interaction):
                return
            try:
                await interaction.response.defer(ephemeral=True)
                stats = await self.cog._get_dashboard_stats()

                embed = discord.Embed(
                    title="📊 Painel de Controle - HugMe Bot (ATUALIZADO)",
                    color=discord.Color.blue(),
                    timestamp=datetime.now(timezone.utc)
                )
                embed.add_field(name="👥 Apoiadores Ativos", value=f"{stats['total_apoiadores']}", inline=True)
                embed.add_field(name="🆕 Doações Recentes (30d)", value=f"{stats['recentes']}", inline=True)
                embed.add_field(name="💰 Receita Total", value=f"R$ {stats['receita_total']:.2f}", inline=True)
                embed.add_field(name="🏠 Servidores", value=f"{stats['total_servidores']}", inline=True)

                view = DashboardView(self.bot, self.cog)
                await interaction.followup.send(embed=embed, view=view, ephemeral=True)
                logger.info(f"Dashboard atualizado por {interaction.user}")
            except Exception as e:
                await interaction.followup.send(f"❌ Erro ao atualizar: {str(e)}", ephemeral=True)
                logger.error(f"Erro ao atualizar dashboard: {e}")
        except (discord.NotFound, discord.HTTPException) as e:
            self._handle_expired(interaction, e)

    @ui.button(label="👤 Gerenciar Apoiadores", style=discord.ButtonStyle.primary)
    async def manage_supporters(self, interaction: discord.Interaction, button: ui.Button):
        try:
            if not await self.check_owner(interaction):
                return
            try:
                embed = discord.Embed(
                    title="👤 Gerenciar Apoiadores Manualmente",
                    description="Gerencie apoiadores que fazem doações fora do sistema automático "
                                "(como apoia-se).\n\n**Ações disponíveis:**\n"
                                "• **Adicionar**: Cria ou estende apoio manual\n"
                                "• **Pausar**: Interrompe temporariamente o apoio\n"
                                "• **Continuar**: Retoma apoio pausado\n"
                                "• **Remover**: Remove completamente do sistema",
                    color=discord.Color.blue()
                )
                embed.add_field(
                    name="📝 Como usar",
                    value="1. Clique no botão abaixo\n"
                          "2. Digite o ID do usuário ou @menção\n"
                          "3. Escolha a ação\n"
                          "4. Para 'adicionar', especifique os meses\n"
                          "5. Opcional: tipo de apoio (padrão: manual)",
                    inline=False
                )
                view = ManageSupporterView(self.bot, self.cog.role_manager)
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
                logger.info(f"Gerenciamento de apoiadores aberto para {interaction.user}")
            except Exception as e:
                await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)
                logger.error(f"Erro ao abrir gerenciamento de apoiadores: {e}")
        except (discord.NotFound, discord.HTTPException) as e:
            self._handle_expired(interaction, e)

    @ui.button(label="📋 Apoiadores", style=discord.ButtonStyle.secondary)
    async def view_supporters(self, interaction: discord.Interaction, button: ui.Button):
        try:
            if not await self.check_owner(interaction):
                return
            try:
                async with AsyncSessionLocal() as session:
                    result = await session.execute(
                        select(Apoiador).where(Apoiador.ativo == True)
                        .order_by(Apoiador.ultimo_pagamento.desc())
                    )
                    all_apoiadores = result.scalars().all()

                if not all_apoiadores:
                    await interaction.response.send_message("📝 Nenhum apoiador ativo.", ephemeral=True)
                    return

                view = SupportersPaginationView(all_apoiadores)
                embed = view.get_embed()
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)
                logger.error(f"Erro ao listar apoiadores: {e}")
        except (discord.NotFound, discord.HTTPException) as e:
            self._handle_expired(interaction, e)

    @ui.button(label="🏠 Servidores", style=discord.ButtonStyle.secondary)
    async def view_servers(self, interaction: discord.Interaction, button: ui.Button):
        try:
            if not await self.check_owner(interaction):
                return
            try:
                embed = discord.Embed(
                    title="🏠 Servidores do Bot",
                    color=discord.Color.green(),
                    timestamp=datetime.now(timezone.utc)
                )
                server_list = []
                for guild in self.bot.guilds:
                    member_count = guild.member_count or 0
                    server_list.append(f"**{guild.name}** (ID: {guild.id}) - {member_count} membros")

                embed.description = "\n".join(server_list[:15]) if server_list else "Nenhum servidor encontrado."
                embed.set_footer(text=f"Total: {len(self.bot.guilds)} servidores")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                logger.info(f"Lista de servidores exibida para {interaction.user}")
            except Exception as e:
                await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)
                logger.error(f"Erro ao listar servidores: {e}")
        except (discord.NotFound, discord.HTTPException) as e:
            self._handle_expired(interaction, e)

    @ui.button(label="💳 PIX Config", style=discord.ButtonStyle.primary)
    async def pix_config_button(self, interaction: discord.Interaction, button: ui.Button):
        try:
            if not await self.check_owner(interaction):
                return
            try:
                async with AsyncSessionLocal() as session:
                    result = await session.execute(select(PixConfig))
                    config = result.scalars().first()

                if not config:
                    embed = discord.Embed(
                        title="⚠️ Configuração PIX não encontrada",
                        description="Clique em ✏️ Editar para criar uma nova configuração",
                        color=discord.Color.orange()
                    )
                    await interaction.response.send_message(embed=embed, view=PIXConfigView(), ephemeral=True)
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

                await interaction.response.send_message(embed=embed, view=PIXConfigView(), ephemeral=True)
                logger.info(f"PIX config mostrada para {interaction.user}")
            except Exception as e:
                await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)
                logger.error(f"Erro ao mostrar PIX config: {e}")
        except (discord.NotFound, discord.HTTPException) as e:
            self._handle_expired(interaction, e)

    @ui.button(label="⭐ Ver Cargos Configurados", style=discord.ButtonStyle.primary)
    async def view_role_config(self, interaction: discord.Interaction, button: ui.Button):
        try:
            if not await self.check_owner(interaction):
                return
            if not interaction.guild:
                await interaction.response.send_message("❌ Este comando só funciona em um servidor.", ephemeral=True)
                return
            try:
                guild_id = str(interaction.guild.id)
                async with AsyncSessionLocal() as session:
                    result = await session.execute(
                        select(GuildConfig).where(GuildConfig.guild_id == guild_id)
                    )
                    config = result.scalars().first()

                embed = _build_role_config_embed(interaction.guild, config)
                view = RoleConfigView(self.bot, interaction.guild)
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
                logger.info(f"Configuração de cargos mostrada para {interaction.user}")
            except Exception as e:
                await interaction.response.send_message(f"❌ Erro ao mostrar configuração: {str(e)}", ephemeral=True)
                logger.error(f"Erro ao mostrar configuração de cargos: {e}")
        except (discord.NotFound, discord.HTTPException) as e:
            self._handle_expired(interaction, e)

    @ui.button(label="✏️ PIX Modal", style=discord.ButtonStyle.success)
    async def set_qrcode_button(self, interaction: discord.Interaction, button: ui.Button):
        from .modals_pix import SetQRCodeModal
        try:
            if not await self.check_owner(interaction):
                return
            try:
                await interaction.response.send_modal(SetQRCodeModal())
                logger.info(f"Modal PIX aberto para {interaction.user}")
            except Exception as e:
                await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)
                logger.error(f"Erro ao abrir modal PIX: {e}")
        except (discord.NotFound, discord.HTTPException) as e:
            self._handle_expired(interaction, e)
