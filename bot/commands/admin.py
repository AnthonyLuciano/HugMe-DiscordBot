import discord
import logging
import os
import re
from datetime import datetime, timedelta, timezone

from discord import ui
from discord.ext import commands
from sqlalchemy import select, func

from bot.database import AsyncSessionLocal
from bot.database.models import PixConfig, Apoiador, GuildConfig
from bot.servicos.SupporterRoleManager import SupporterRoleManager

logger = logging.getLogger(__name__)

# ==================== UTILITY FUNCTIONS ====================

def check_is_owner(ctx_or_interaction) -> bool:
    """Verifica se o usuário é owner - funciona com Context ou Interaction"""
    mod_id = os.getenv('TRUSTED_MOD_ID')
    dev_id = os.getenv('DEV_ID')

    if hasattr(ctx_or_interaction, 'user'):
        user_id = ctx_or_interaction.user.id
    elif hasattr(ctx_or_interaction, 'author'):
        user_id = ctx_or_interaction.author.id
    else:
        return False

    allowed_ids = []
    if dev_id:
        allowed_ids.append(int(dev_id))
    if mod_id:
        allowed_ids.append(int(mod_id))
    return user_id in allowed_ids

# ==================== MODALS ====================

class SetQRCodeModal(ui.Modal, title="Configurar PIX QR Code"):
    qr_url = ui.TextInput(
        label="URL do QR Code",
        placeholder="https://example.com/qrcode.png",
        required=True,
        min_length=10,
        max_length=500
    )
    pix_key = ui.TextInput(
        label="Chave PIX (opcional)",
        placeholder="email@example.com ou CPF",
        required=False,
        max_length=100
    )
    nome_titular = ui.TextInput(
        label="Nome do Titular",
        placeholder="Seu Nome",
        default="HugMe Bot",
        max_length=100
    )
    cidade = ui.TextInput(
        label="Cidade",
        placeholder="São Paulo",
        default="São Paulo",
        max_length=50
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            url = str(self.qr_url)
            if not url.startswith(('http://', 'https://')):
                await interaction.response.send_message(
                    "❌ URL deve começar com http:// ou https://",
                    ephemeral=True
                )
                return

            chave_display = str(self.pix_key) if self.pix_key else "manter atual"
            description = f"Configurar PIX com QR Code, chave: {chave_display}, titular: {str(self.nome_titular)}"

            view = ConfirmationView(
                action_description=description,
                confirm_callback=lambda i: self._execute_pix_config(i, url),
            )

            embed = discord.Embed(
                title="⚠️ Confirmar Ação",
                description=f"**Ação:** {description}\n\nClique em **CONFIRMAR** para prosseguir.",
                color=discord.Color.orange()
            )

            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)
            logger.error(f"Erro ao preparar configuração PIX: {e}")

    async def _execute_pix_config(self, interaction: discord.Interaction, url: str):
        # interaction já foi deferida pela ConfirmationView — usar apenas followup
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(select(PixConfig))
                config = result.scalars().first()
                if not config:
                    config = PixConfig(
                        static_qr_url=url,
                        chave=str(self.pix_key) if self.pix_key else "hugmebotdev@gmail.com",
                        nome_titular=str(self.nome_titular),
                        cidade=str(self.cidade),
                        atualizado_por=str(interaction.user.id)
                    )
                else:
                    config.static_qr_url = url
                    if self.pix_key:
                        config.chave = str(self.pix_key)
                    config.nome_titular = str(self.nome_titular)
                    config.cidade = str(self.cidade)
                    config.atualizado_por = str(interaction.user.id)

                session.add(config)
                await session.commit()

            embed = discord.Embed(
                title="✅ PIX Configurado com Sucesso",
                color=discord.Color.green()
            )
            embed.add_field(name="URL do QR Code", value=url[:50] + "...", inline=False)
            embed.add_field(name="Chave PIX", value=str(self.pix_key) if self.pix_key else "Não alterada", inline=False)
            embed.add_field(name="Titular", value=str(self.nome_titular), inline=True)
            embed.add_field(name="Cidade", value=str(self.cidade), inline=True)

            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"PIX configurado por {interaction.user}: {url}")
        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao configurar PIX: {str(e)}", ephemeral=True)
            logger.error(f"Erro ao configurar PIX: {e}")


class ConfigureRoleModal(ui.Modal, title="Configurar Cargo de Apoiador"):
    guild_id = ui.TextInput(
        label="ID do Servidor",
        placeholder="123456789",
        required=True,
        max_length=20
    )
    level = ui.TextInput(
        label="Nível do Apoiador",
        placeholder="1",
        required=True,
        max_length=2
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()


class ConfirmationModal(ui.Modal, title="Confirmar Ação"):
    confirm_text = ui.TextInput(
        label="Digite 'CONFIRMAR' para prosseguir",
        placeholder="CONFIRMAR",
        required=True,
        max_length=10
    )

    def __init__(self, action_description: str, confirm_callback, cancel_callback=None):
        super().__init__()
        self.action_description = action_description
        self.confirm_callback = confirm_callback
        self.cancel_callback = cancel_callback

    async def on_submit(self, interaction: discord.Interaction):
        if str(self.confirm_text).strip().upper() == "CONFIRMAR":
            await self.confirm_callback(interaction)
        else:
            embed = discord.Embed(
                title="❌ Confirmação Incorreta",
                description="Ação cancelada. Digite exatamente 'CONFIRMAR' para confirmar.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            if self.cancel_callback:
                await self.cancel_callback(interaction)


# ==================== VIEWS ====================

class ConfirmView(ui.View):
    def __init__(self, timeout=180):
        super().__init__(timeout=timeout)
        self.confirmed = None

    @ui.button(label="✅ Confirmar", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: ui.Button):
        self.confirmed = True
        self.stop()
        await interaction.response.defer()

    @ui.button(label="❌ Cancelar", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        self.confirmed = False
        self.stop()
        await interaction.response.defer()


class ConfirmationView(ui.View):
    """View para confirmar ações administrativas com callback."""

    def __init__(self, action_description: str, confirm_callback, cancel_callback=None, timeout=180):
        super().__init__(timeout=timeout)
        self.action_description = action_description
        self.confirm_callback = confirm_callback
        self.cancel_callback = cancel_callback

    @ui.button(label="✅ CONFIRMAR", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: ui.Button):
        # ✅ FIX: defer ANTES de qualquer operação assíncrona longa.
        # Isso garante que o webhook permaneça válido para followup.send().
        await interaction.response.defer(ephemeral=True)
        try:
            await self.confirm_callback(interaction)
        except Exception as e:
            logger.error(f"Erro no confirm_callback: {e}")
            try:
                await interaction.followup.send(f"❌ Erro ao executar ação: {str(e)}", ephemeral=True)
            except Exception as fe:
                logger.error(f"Falha ao enviar mensagem de erro via followup: {fe}")

    @ui.button(label="❌ Cancelar", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        if self.cancel_callback:
            try:
                await self.cancel_callback(interaction)
                return
            except Exception:
                pass
        embed = discord.Embed(
            title="❌ Ação Cancelada",
            description="A ação foi cancelada pelo usuário.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class DashboardView(ui.View):
    def __init__(self, bot, cog):
        super().__init__()
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

    @ui.button(label="🔄 Atualizar", style=discord.ButtonStyle.primary)
    async def refresh(self, interaction: discord.Interaction, button: ui.Button):
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

    @ui.button(label="👤 Gerenciar Apoiadores", style=discord.ButtonStyle.primary)
    async def manage_supporters(self, interaction: discord.Interaction, button: ui.Button):
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

    @ui.button(label="📋 Apoiadores", style=discord.ButtonStyle.secondary)
    async def view_supporters(self, interaction: discord.Interaction, button: ui.Button):
        if not await self.check_owner(interaction):
            return
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(Apoiador).where(Apoiador.ativo == True).limit(10)
                )
                apoiadores = result.scalars().all()

            if not apoiadores:
                await interaction.response.send_message("📝 Nenhum apoiador ativo.", ephemeral=True)
                return

            embed = discord.Embed(title="👥 Últimos 10 Apoiadores", color=discord.Color.gold())
            supporter_list = []
            for apo in apoiadores:
                expiry = apo.data_expiracao.strftime("%d/%m/%Y") if apo.data_expiracao else "Permanente"
                supporter_list.append(f"**{apo.discord_id}** - {apo.tipo_apoio} Nível {apo.nivel} (Expira: {expiry})")

            embed.description = "\n".join(supporter_list)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)
            logger.error(f"Erro ao listar apoiadores: {e}")

    @ui.button(label="🏠 Servidores", style=discord.ButtonStyle.secondary)
    async def view_servers(self, interaction: discord.Interaction, button: ui.Button):
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

    @ui.button(label="💳 PIX Config", style=discord.ButtonStyle.primary)
    async def pix_config_button(self, interaction: discord.Interaction, button: ui.Button):
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

    @ui.button(label="⭐ Ver Cargos Configurados", style=discord.ButtonStyle.primary)
    async def view_role_config(self, interaction: discord.Interaction, button: ui.Button):
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

    @ui.button(label="✏️ PIX Modal", style=discord.ButtonStyle.success)
    async def set_qrcode_button(self, interaction: discord.Interaction, button: ui.Button):
        if not await self.check_owner(interaction):
            return
        try:
            await interaction.response.send_modal(SetQRCodeModal())
            logger.info(f"Modal PIX aberto para {interaction.user}")
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)
            logger.error(f"Erro ao abrir modal PIX: {e}")


# ==================== HELPERS ====================

def _build_role_config_embed(guild: discord.Guild, config) -> discord.Embed:
    """Constrói o embed de configuração de cargos (reutilizável)."""
    embed = discord.Embed(
        title="⭐ Configuração de Cargos de Apoiador",
        color=discord.Color.gold(),
        description=f"Configurações para **{guild.name}**"
    )

    if not config:
        embed.add_field(
            name="⚠️ Nenhuma Configuração",
            value="Nenhum cargo de apoiador configurado ainda.\nUse os botões abaixo para configurar.",
            inline=False
        )
        return embed

    if config.cargo_apoiador_default:
        role = guild.get_role(int(config.cargo_apoiador_default))
        value = role.mention if role else f"ID: {config.cargo_apoiador_default} (cargo não encontrado)"
        embed.add_field(
            name="⭐ Cargo Padrão",
            value=f"{value}\n*Atribuído automaticamente a todos os apoiadores*",
            inline=False
        )
    else:
        embed.add_field(name="⭐ Cargo Padrão", value="Não configurado", inline=False)

    if config.cargos_tempo and isinstance(config.cargos_tempo, list):
        unit_map = {"days": "dias", "months": "meses", "years": "anos"}
        time_roles = []
        for item in sorted(config.cargos_tempo, key=lambda x: (x.get('unit', 'days'), x.get('threshold', 0))):
            threshold = item.get('threshold', 0)
            unit = item.get('unit', 'days')
            role_id = item.get('role_id')
            role = guild.get_role(int(role_id)) if role_id else None
            role_name = role.mention if role else f"ID: {role_id}"
            time_roles.append(f"**{threshold} {unit_map.get(unit, unit)}+**: {role_name}")

        embed.add_field(
            name="⏳ Cargos por Tempo de Apoio",
            value="\n".join(time_roles) if time_roles else "Nenhum configurado",
            inline=False
        )
    else:
        embed.add_field(name="⏳ Cargos por Tempo de Apoio", value="Nenhum configurado", inline=False)

    return embed


# ==================== ROLE CONFIG VIEWS ====================

class PaginatedRoleSelectView(ui.View):
    """Seleção de cargo com paginação para suportar 100+ cargos"""
    def __init__(self, bot, guild: discord.Guild, callback, title: str, description: str, filter_time_patterns: bool = False):
        super().__init__()
        self.bot = bot
        self.guild = guild
        self.callback = callback
        self.title = title
        self.description = description
        self.filter_time_patterns = filter_time_patterns
        self.current_page = 0
        self.page_size = 25
        
        # Filtrar cargos
        all_roles = [r for r in guild.roles if not r.managed and r != guild.default_role]
        
        # Se filter_time_patterns, apenas mostra cargos com padrões de tempo
        if filter_time_patterns:
            time_patterns = r'\b(\d+|dia|mês|ano|mes|anos|dias|meses|week|semana|horas?|hour)\b'
            self.roles = [r for r in all_roles if re.search(time_patterns, r.name, re.IGNORECASE)]
        else:
            self.roles = all_roles
        
        self.update_page()
    
    def get_page_options(self) -> list:
        """Retorna opções para a página atual"""
        start = self.current_page * self.page_size
        end = start + self.page_size
        page_roles = self.roles[start:end]
        
        options = [
            discord.SelectOption(label=r.name[:25], value=str(r.id))
            for r in page_roles
        ]
        return options
    
    def update_page(self):
        """Atualiza o menu de seleção e botões de navegação"""
        # Remove dropdown anterior se existir
        for item in list(self.children):
            if isinstance(item, ui.Select):
                self.remove_item(item)
        
        options = self.get_page_options()
        
        if not options:
            options = [discord.SelectOption(label="Nenhum cargo nesta página", value="none", emoji="❌")]
        
        select_menu = ui.Select(
            placeholder="Selecione um cargo",
            min_values=1, max_values=1, options=options,
            disabled=len(options) == 0 or options[0].value == "none"
        )
        select_menu.callback = self.role_selected
        self.add_item(select_menu)
        
        # Atualizar botões de navegação
        for item in list(self.children):
            if isinstance(item, ui.Button):
                self.remove_item(item)
        
        # Botão anterior
        self.add_item(self._create_prev_button())
        
        # Información de página
        total_pages = (len(self.roles) + self.page_size - 1) // self.page_size
        page_label = f"Página {self.current_page + 1}/{total_pages}"
        page_button = ui.Button(label=page_label, style=discord.ButtonStyle.gray, disabled=True)
        self.add_item(page_button)
        
        # Botão próximo
        self.add_item(self._create_next_button())
    
    def _create_prev_button(self) -> ui.Button:
        button = ui.Button(label="⬅️ Anterior", style=discord.ButtonStyle.primary)
        button.callback = self.prev_page
        button.disabled = self.current_page == 0
        return button
    
    def _create_next_button(self) -> ui.Button:
        total_pages = (len(self.roles) + self.page_size - 1) // self.page_size
        button = ui.Button(label="Próximo ➡️", style=discord.ButtonStyle.primary)
        button.callback = self.next_page
        button.disabled = self.current_page >= total_pages - 1
        return button
    
    async def prev_page(self, interaction: discord.Interaction):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_page()
            await interaction.response.edit_message(view=self)
        else:
            await interaction.response.defer()
    
    async def next_page(self, interaction: discord.Interaction):
        total_pages = (len(self.roles) + self.page_size - 1) // self.page_size
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self.update_page()
            await interaction.response.edit_message(view=self)
        else:
            await interaction.response.defer()
    
    async def role_selected(self, interaction: discord.Interaction):
        try:
            for item in self.children:
                if isinstance(item, ui.Select):
                    role_id = item.values[0]
                    break
            
            role = self.guild.get_role(int(role_id))
            if not role:
                await interaction.response.send_message("❌ Cargo não encontrado.", ephemeral=True)
                return
            
            await self.callback(interaction, role, self)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)
            logger.error(f"Erro ao selecionar cargo: {e}")


class DefaultRoleSelectView(PaginatedRoleSelectView):
    def __init__(self, bot, guild: discord.Guild):
        async def callback(interaction, role, view):
            description = f"Definir **{role.name}** como cargo padrão para TODOS os apoiadores de {guild.name}"
            conf_view = ConfirmationView(
                action_description=description,
                confirm_callback=lambda i: view._execute_set_default_role(i, role),
            )
            embed = discord.Embed(
                title="⚠️ Confirmar Ação",
                description=f"**Ação:** {description}\n\nClique em **CONFIRMAR** para prosseguir.",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, view=conf_view, ephemeral=True)
        
        super().__init__(
            bot, guild, callback,
            title="⭐ Selecione o Cargo Padrão de Apoiador",
            description="Este cargo será atribuído automaticamente a todos os apoiadores",
            filter_time_patterns=False
        )
    
    async def _execute_set_default_role(self, interaction: discord.Interaction, role: discord.Role):
        try:
            guild_id = str(self.guild.id)
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(GuildConfig).where(GuildConfig.guild_id == guild_id)
                )
                config = result.scalars().first()
                if not config:
                    config = GuildConfig(guild_id=guild_id)
                    session.add(config)
                config.cargo_apoiador_default = str(role.id)
                await session.commit()

            embed = discord.Embed(
                title="✅ Cargo Padrão Configurado",
                color=discord.Color.green(),
                description=f"Todos os apoiadores receberão automaticamente: {role.mention}"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"Cargo padrão definido por {interaction.user}: {role.id} em {guild_id}")
        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao definir cargo padrão: {str(e)}", ephemeral=True)
            logger.error(f"Erro ao definir cargo padrão: {e}")

    async def _execute_set_default_role(self, interaction: discord.Interaction, role: discord.Role):
        # interaction já deferida — usar apenas followup
        try:
            guild_id = str(self.guild.id)
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(GuildConfig).where(GuildConfig.guild_id == guild_id)
                )
                config = result.scalars().first()
                if not config:
                    config = GuildConfig(guild_id=guild_id)
                    session.add(config)
                config.cargo_apoiador_default = str(role.id)
                await session.commit()

            embed = discord.Embed(
                title="✅ Cargo Padrão Configurado",
                color=discord.Color.green(),
                description=f"Todos os apoiadores receberão automaticamente: {role.mention}"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"Cargo padrão definido por {interaction.user}: {role.id} em {guild_id}")
        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao definir cargo padrão: {str(e)}", ephemeral=True)
            logger.error(f"Erro ao definir cargo padrão: {e}")


class TimeRoleConfigView(ui.View):
    def __init__(self, bot, guild: discord.Guild):
        super().__init__()
        self.bot = bot
        self.guild = guild
        self.time_roles = []

    @ui.button(label="➕ Adicionar Cargo", style=discord.ButtonStyle.primary)
    async def add_time_role_button(self, interaction: discord.Interaction, button: ui.Button):
        if not check_is_owner(interaction):
            await interaction.response.send_message("❌ Apenas admins podem usar essa função!", ephemeral=True)
            return
        try:
            await interaction.response.send_modal(TimeRoleModal(self.time_roles))
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)

    @ui.button(label="📋 Ver Configurados", style=discord.ButtonStyle.secondary)
    async def view_time_roles_button(self, interaction: discord.Interaction, button: ui.Button):
        if not check_is_owner(interaction):
            await interaction.response.send_message("❌ Apenas admins podem usar essa função!", ephemeral=True)
            return
        try:
            if not self.time_roles:
                embed = discord.Embed(
                    title="📋 Cargos de Tempo Configurados",
                    description="Nenhum cargo de tempo configurado ainda.",
                    color=discord.Color.orange()
                )
            else:
                embed = discord.Embed(title="📋 Cargos de Tempo Configurados", color=discord.Color.blue())
                unit_map = {"days": "dias", "months": "meses", "years": "anos"}
                role_list = []
                for item in sorted(self.time_roles, key=lambda x: (x['unit'], x['threshold'])):
                    role = self.guild.get_role(int(item['role_id']))
                    role_name = role.name if role else f"ID: {item['role_id']} (não encontrado)"
                    role_list.append(f"**{item['threshold']} {unit_map.get(item['unit'], item['unit'])}+**: {role_name}")
                embed.description = "\n".join(role_list)

            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)

    @ui.button(label="💾 Salvar Configuração", style=discord.ButtonStyle.success)
    async def save_time_config_button(self, interaction: discord.Interaction, button: ui.Button):
        if not check_is_owner(interaction):
            await interaction.response.send_message("❌ Apenas admins podem usar essa função!", ephemeral=True)
            return
        try:
            num_roles = len(self.time_roles)
            description = f"Salvar configuração de {num_roles} cargo(s) baseado(s) no tempo de apoio para {self.guild.name}"
            view = ConfirmationView(
                action_description=description,
                confirm_callback=lambda i: self._execute_save_config(i),
            )
            embed = discord.Embed(
                title="⚠️ Confirmar Ação",
                description=f"**Ação:** {description}\n\nClique em **CONFIRMAR** para prosseguir.",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)
            logger.error(f"Erro ao preparar salvamento de cargos de tempo: {e}")

    async def _execute_save_config(self, interaction: discord.Interaction):
        # interaction já deferida — usar apenas followup
        try:
            guild_id = str(self.guild.id)
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(GuildConfig).where(GuildConfig.guild_id == guild_id)
                )
                config = result.scalars().first()
                if not config:
                    config = GuildConfig(guild_id=guild_id)
                    session.add(config)
                config.cargos_tempo = self.time_roles
                await session.commit()

            embed = discord.Embed(
                title="✅ Configuração Salva",
                color=discord.Color.green(),
                description=f"Configurados {len(self.time_roles)} cargos baseados no tempo de apoio"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"Cargos de tempo salvos por {interaction.user}: {self.time_roles}")
        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao salvar: {str(e)}", ephemeral=True)
            logger.error(f"Erro ao salvar cargos de tempo: {e}")


class TimeRoleModal(ui.Modal, title="Adicionar Cargo por Tempo"):
    threshold = ui.TextInput(
        label="Valor mínimo de apoio",
        placeholder="Ex: 1, 3, 6, 12",
        required=True,
        min_length=1,
        max_length=4
    )

    def __init__(self, time_roles):
        super().__init__()
        self.time_roles = time_roles

    async def on_submit(self, interaction: discord.Interaction):
        try:
            threshold = int(self.threshold.value)
            if threshold <= 0:
                await interaction.response.send_message("❌ Valor deve ser maior que 0.", ephemeral=True)
                return

            view = TimeUnitSelectView(self.time_roles, threshold)
            embed = discord.Embed(
                title=f"⏱️ Selecionar Unidade para {threshold}+",
                description="Escolha a unidade de tempo para este limite de apoio.",
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Valor inválido.", ephemeral=True)


class TimeUnitSelectView(ui.View):
    def __init__(self, time_roles, threshold):
        super().__init__()
        self.time_roles = time_roles
        self.threshold = threshold

    @ui.button(label="📅 Dias", style=discord.ButtonStyle.primary)
    async def select_days(self, interaction: discord.Interaction, button: ui.Button):
        await self._select_unit(interaction, "days")

    @ui.button(label="📆 Meses", style=discord.ButtonStyle.primary)
    async def select_months(self, interaction: discord.Interaction, button: ui.Button):
        await self._select_unit(interaction, "months")

    @ui.button(label="📈 Anos", style=discord.ButtonStyle.primary)
    async def select_years(self, interaction: discord.Interaction, button: ui.Button):
        await self._select_unit(interaction, "years")

    async def _select_unit(self, interaction: discord.Interaction, unit: str):
        try:
            guild = interaction.guild
            
            async def callback(inter, role, view):
                unit_display = {"days": "dias", "months": "meses", "years": "anos"}.get(unit, unit)
                description = f"Adicionar cargo **{role.name}** para apoiadores com **{self.threshold} {unit_display}+** de apoio"
                conf_view = ConfirmationView(
                    action_description=description,
                    confirm_callback=lambda i: view._execute_add_role(i, role, unit, self.threshold, self.time_roles),
                )
                embed = discord.Embed(
                    title="⚠️ Confirmar Ação",
                    description=f"**Ação:** {description}\n\nLembre de Salvar as Alterações no Botão de Salvar 💾\n\nClique em **CONFIRMAR** para prosseguir.",
                    color=discord.Color.orange()
                )
                await inter.response.send_message(embed=embed, view=conf_view, ephemeral=True)
            
            unit_display = {"days": "dias", "months": "meses", "years": "anos"}.get(unit, unit)
            view = TimeRoleSelectView(
                self.bot, guild, callback,
                title=f"🎯 Selecionar Cargo para {self.threshold} {unit_display}+",
                description="Escolha o cargo que será atribuído aos apoiadores com este tempo de apoio.",
                time_roles=self.time_roles,
                threshold=self.threshold,
                unit=unit
            )
            embed = discord.Embed(
                title=f"🎯 Selecionar Cargo para {self.threshold} {unit_display}+",
                description="Navegue pelas páginas para encontrar o cargo desejado. Cargos com padrões de tempo aparecem primeiro.",
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)
            logger.error(f"Erro ao selecionar unidade: {e}")


class TimeRoleSelectView(PaginatedRoleSelectView):
    def __init__(self, bot, guild: discord.Guild, callback, title: str, description: str, time_roles, threshold, unit):
        self.time_roles = time_roles
        self.threshold = threshold
        self.unit = unit
        super().__init__(bot, guild, callback, title, description, filter_time_patterns=True)
    
    @staticmethod
    async def _execute_add_role(interaction: discord.Interaction, role: discord.Role, unit: str, threshold: int, time_roles: list):
        try:
            time_roles.append({
                "threshold": threshold,
                "unit": unit,
                "role_id": str(role.id)
            })
            unit_display = {"days": "dias", "months": "meses", "years": "anos"}.get(unit, unit)
            embed = discord.Embed(
                title="✅ Cargo Adicionado",
                color=discord.Color.green(),
                description=f"Cargo **{role.name}** configurado para apoiadores com **{threshold} {unit_display}+** de apoio"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {str(e)}", ephemeral=True)


class PIXConfigView(ui.View):
    def __init__(self):
        super().__init__()

    @ui.button(label="✏️ Editar", style=discord.ButtonStyle.primary)
    async def edit(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(SetQRCodeModal())

    @ui.button(label="❌ Limpar Config", style=discord.ButtonStyle.danger)
    async def clear_config(self, interaction: discord.Interaction, button: ui.Button):
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(select(PixConfig))
                config = result.scalars().first()

            if not config:
                await interaction.response.send_message("⚠️ Nenhuma configuração para remover", ephemeral=True)
                return

            description = "REMOVER TODA a configuração PIX (QR Code, chave PIX, dados do titular)"
            view = ConfirmationView(
                action_description=description,
                confirm_callback=lambda i: self._execute_clear_config(i),
            )
            embed = discord.Embed(
                title="⚠️ Confirmar Ação",
                description=f"**Ação:** {description}\n\nClique em **CONFIRMAR** para prosseguir.",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)
            logger.error(f"Erro ao preparar limpeza PIX config: {e}")

    async def _execute_clear_config(self, interaction: discord.Interaction):
        # interaction já deferida — usar apenas followup
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(select(PixConfig))
                config = result.scalars().first()
                if config:
                    await session.delete(config)
                    await session.commit()
                    await interaction.followup.send("✅ Configuração PIX removida completamente", ephemeral=True)
                else:
                    await interaction.followup.send("⚠️ Configuração já foi removida", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao limpar configuração: {str(e)}", ephemeral=True)
            logger.error(f"Erro ao limpar PIX config: {e}")


class RoleConfigView(ui.View):
    def __init__(self, bot, guild: discord.Guild):
        super().__init__()
        self.bot = bot
        self.guild = guild

    @ui.button(label="⭐ Definir Cargo Padrão", style=discord.ButtonStyle.primary)
    async def set_default_role(self, interaction: discord.Interaction, button: ui.Button):
        if not check_is_owner(interaction):
            await interaction.response.send_message("❌ Apenas admins podem usar essa função!", ephemeral=True)
            return
        try:
            view = DefaultRoleSelectView(self.bot, self.guild)
            embed = discord.Embed(
                title="⭐ Selecione o Cargo Padrão de Apoiador",
                description="Este cargo será atribuído automaticamente a todos os apoiadores do servidor",
                color=discord.Color.gold()
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)

    @ui.button(label="⏳ Configurar Cargos por Tempo", style=discord.ButtonStyle.secondary)
    async def configure_time_roles(self, interaction: discord.Interaction, button: ui.Button):
        if not check_is_owner(interaction):
            await interaction.response.send_message("❌ Apenas admins podem usar essa função!", ephemeral=True)
            return
        try:
            view = TimeRoleConfigView(self.bot, self.guild)
            embed = discord.Embed(
                title="⏳ Configurar Cargos por Tempo de Apoio",
                description="Configure cargos especiais baseados no tempo total de apoio dos membros",
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)

    @ui.button(label="🔄 Atualizar Visualização", style=discord.ButtonStyle.gray)
    async def refresh_config(self, interaction: discord.Interaction, button: ui.Button):
        if not check_is_owner(interaction):
            await interaction.response.send_message("❌ Apenas admins podem usar essa função!", ephemeral=True)
            return
        try:
            guild_id = str(self.guild.id)
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(GuildConfig).where(GuildConfig.guild_id == guild_id)
                )
                config = result.scalars().first()

            embed = _build_role_config_embed(self.guild, config)
            view = RoleConfigView(self.bot, self.guild)
            await interaction.response.edit_message(embed=embed, view=view)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro ao atualizar: {str(e)}", ephemeral=True)


# ==================== COG ====================

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
        guild_id = str(interaction.guild.id)

        async def reply(content=None, embed=None, ephemeral=True):
            """Envia resposta usando o método correto conforme estado da interação."""
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
                        data_expiracao = now + timedelta(days=months * 30)
                        apoiador = Apoiador(
                            discord_id=discord_id,
                            guild_id=guild_id,
                            tipo_apoio=tipo_apoio,
                            duracao_meses=months,
                            data_inicio=now,
                            ultimo_pagamento=now,
                            ativo=True,
                            data_expiracao=data_expiracao,
                            cargo_atribuido=False,
                            ja_pago=True
                        )
                        session.add(apoiador)
                        message = f"✅ Apoiador criado: {months} meses de {tipo_apoio}"
                    else:
                        if apoiador.ativo:
                            if apoiador.data_expiracao:
                                apoiador.data_expiracao += timedelta(days=months * 30)
                            else:
                                apoiador.data_expiracao = now + timedelta(days=months * 30)
                            apoiador.duracao_meses = (apoiador.duracao_meses or 0) + months
                            apoiador.ultimo_pagamento = now
                            message = f"✅ Apoiador estendido: +{months} meses (total: {apoiador.duracao_meses} meses)"
                        else:
                            apoiador.ativo = True
                            apoiador.data_expiracao = now + timedelta(days=months * 30)
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
            await ctx.send("❌ Apenas admins podem usar esse comando!", ephemeral=True)
            return
        try:
            stats = await self._get_dashboard_stats()

            embed = discord.Embed(
                title="📊 Painel de Controle - HugMe Bot",
                color=discord.Color.blue(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="👥 Apoiadores Ativos", value=f"{stats['total_apoiadores']}", inline=True)
            embed.add_field(name="🆕 Doações Recentes (30d)", value=f"{stats['recentes']}", inline=True)
            embed.add_field(name="💰 Receita Total", value=f"R$ {stats['receita_total']:.2f}", inline=True)
            embed.add_field(name="🏠 Servidores", value=f"{stats['total_servidores']}", inline=True)
            embed.set_footer(text="Clique nos botões abaixo para gerenciar tudo!")

            view = DashboardView(self.bot, self)
            if ctx.interaction:
                await ctx.interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            else:
                await ctx.send(embed=embed, view=view)
            logger.info(f"Dashboard exibido para {ctx.author}")
        except Exception as e:
            if ctx.interaction:
                await ctx.interaction.response.send_message(f"❌ Erro ao carregar dashboard: {str(e)}", ephemeral=True)
            else:
                await ctx.send(f"❌ Erro ao carregar dashboard: {str(e)}")
            logger.error(f"Erro no dashboard: {e}")

    @commands.hybrid_command(name="servers", description="[ADMIN] Lista todos os servidores onde o bot está presente")
    async def servers(self, ctx: commands.Context):
        if not check_is_owner(ctx.interaction if hasattr(ctx, 'interaction') else ctx):
            await ctx.send("❌ Apenas admins podem usar esse comando!", ephemeral=True)
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
            await ctx.send("❌ Apenas admins podem usar esse comando!", ephemeral=True)
            return
        embed = discord.Embed(
            title="ℹ️ Comando Descontinuado",
            description="Use `/set_supporter_role` para configurar cargos de apoiador",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed, ephemeral=True)

    @commands.hybrid_command(name="set_default_supporter_role", description="[ADMIN] Define o cargo padrão que todos os apoiadores terão")
    async def set_default_supporter_role(self, ctx: commands.Context):
        if not check_is_owner(ctx.interaction if hasattr(ctx, 'interaction') else ctx):
            await ctx.send("❌ Apenas admins podem usar esse comando!", ephemeral=True)
            return
        if not ctx.guild:
            await ctx.send("❌ Este comando só funciona em um servidor.", ephemeral=True)
            return
        try:
            view = DefaultRoleSelectView(self.bot, ctx.guild)
            embed = discord.Embed(
                title="⭐ Selecione o Cargo Padrão de Apoiador",
                description="Este cargo será atribuído automaticamente a todos os apoiadores do servidor",
                color=discord.Color.gold()
            )
            await ctx.send(embed=embed, view=view, ephemeral=True)
            logger.info(f"Select de cargo padrão aberto para {ctx.author}")
        except Exception as e:
            await ctx.send(f"❌ Erro ao abrir seletor: {str(e)}", ephemeral=True)
            logger.error(f"Erro ao abrir seletor de cargo padrão: {e}")

    @commands.hybrid_command(name="configure_time_roles", description="[ADMIN] Configura cargos baseados no tempo de apoio")
    async def configure_time_roles(self, ctx: commands.Context):
        if not check_is_owner(ctx.interaction if hasattr(ctx, 'interaction') else ctx):
            await ctx.send("❌ Apenas admins podem usar esse comando!", ephemeral=True)
            return
        if not ctx.guild:
            await ctx.send("❌ Este comando só funciona em um servidor.", ephemeral=True)
            return
        try:
            view = TimeRoleConfigView(self.bot, ctx.guild)
            embed = discord.Embed(
                title="⏳ Configurar Cargos por Tempo de Apoio",
                description="Configure cargos especiais baseados no tempo total de apoio dos membros",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed, view=view, ephemeral=True)
            logger.info(f"Configuração de cargos de tempo aberta para {ctx.author}")
        except Exception as e:
            await ctx.send(f"❌ Erro ao abrir configuração: {str(e)}", ephemeral=True)
            logger.error(f"Erro ao abrir configuração de cargos de tempo: {e}")

    @commands.hybrid_command(name="pix_config", description="[ADMIN] Mostra a configuração atual do PIX")
    async def pix_config(self, ctx: commands.Context):
        if not check_is_owner(ctx.interaction if hasattr(ctx, 'interaction') else ctx):
            await ctx.send("❌ Apenas admins podem usar esse comando!", ephemeral=True)
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
                await ctx.send(embed=embed, view=PIXConfigView(), ephemeral=True)
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

            await ctx.send(embed=embed, view=PIXConfigView(), ephemeral=True)
            logger.info(f"PIX config mostrada para {ctx.author}")
        except Exception as e:
            await ctx.send(f"❌ Erro ao mostrar configuração PIX: {str(e)}", ephemeral=True)
            logger.error(f"Erro ao mostrar PIX config: {e}")

    @commands.hybrid_command(name="manage_supporter", description="[ADMIN] Gerencia apoiadores manualmente")
    async def manage_supporter(self, ctx: commands.Context):
        if not check_is_owner(ctx.interaction if hasattr(ctx, 'interaction') else ctx):
            await ctx.send("❌ Apenas admins podem usar esse comando!", ephemeral=True)
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
            await ctx.send(embed=embed, view=view, ephemeral=True)
            logger.info(f"Gerenciamento de apoiador aberto para {ctx.author}")
        except Exception as e:
            await ctx.send(f"❌ Erro ao abrir gerenciamento: {str(e)}", ephemeral=True)
            logger.error(f"Erro ao abrir gerenciamento de apoiador: {e}")


# ==================== SUPPORTER MANAGEMENT VIEWS ====================

class SupporterActionModal(ui.Modal):
    usuario = ui.TextInput(
        label="ID do Usuário ou @menção",
        placeholder="123456789 ou @usuario",
        required=True,
        max_length=50
    )
    meses = ui.TextInput(
        label="Meses (apenas para adicionar)",
        placeholder="5",
        required=False,
        max_length=3
    )
    tipo = ui.TextInput(
        label="Tipo de Apoio (opcional)",
        placeholder="apoia-se, pix, manual",
        default="manual",
        required=False,
        max_length=20
    )

    def __init__(self, role_manager, action: str, title: str):
        self.role_manager = role_manager
        self.action = action
        super().__init__(title=title)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            user_input = str(self.usuario).strip()
            if user_input.startswith('<@') and user_input.endswith('>'):
                user_id = user_input.replace('<@', '').replace('>', '').replace('!', '')
            else:
                user_id = user_input

            try:
                discord_id = str(int(user_id))
            except ValueError:
                await interaction.response.send_message("❌ ID de usuário inválido.", ephemeral=True)
                return

            action = self.action
            months = None
            if action == 'adicionar':
                if not self.meses.value:
                    await interaction.response.send_message("❌ Para adicionar, informe os meses.", ephemeral=True)
                    return
                try:
                    months = int(str(self.meses).strip())
                    if months <= 0:
                        await interaction.response.send_message("❌ Meses deve ser maior que 0.", ephemeral=True)
                        return
                except ValueError:
                    await interaction.response.send_message("❌ Número de meses inválido.", ephemeral=True)
                    return

            tipo_apoio = str(self.tipo).strip() or "manual"

            action_descriptions = {
                'adicionar': f"Adicionar/estender apoio de <@{discord_id}> por {months} meses (tipo: {tipo_apoio})",
                'pausar': f"Pausar apoio de <@{discord_id}> (interromper doações)",
                'continuar': f"Continuar apoio de <@{discord_id}> (retomar doações)",
                'remover': f"REMOVER COMPLETAMENTE o apoio de <@{discord_id}> do sistema"
            }

            description = action_descriptions.get(action, f"Executar ação '{action}' para <@{discord_id}>")

            view = ConfirmationView(
                action_description=description,
                confirm_callback=lambda i: self._execute_action(i, discord_id, action, months, tipo_apoio),
            )

            embed = discord.Embed(
                title="⚠️ Confirmar Ação",
                description=f"**Ação:** {description}\n\nClique em **CONFIRMAR** para prosseguir.",
                color=discord.Color.orange()
            )

            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)
            logger.error(f"Erro ao processar ação de apoiador: {e}")

    async def _execute_action(self, interaction: discord.Interaction, discord_id: str, action: str, months: int = None, tipo_apoio: str = "manual"):
        # interaction já deferida pela ConfirmationView — usar apenas followup
        try:
            guild_id = str(interaction.guild.id)

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
                        apoiador = Apoiador(
                            discord_id=discord_id,
                            guild_id=guild_id,
                            tipo_apoio=tipo_apoio,
                            duracao_meses=months,
                            data_inicio=now,
                            ultimo_pagamento=now,
                            ativo=True,
                            data_expiracao=now + timedelta(days=months * 30),
                            cargo_atribuido=False,
                            ja_pago=True
                        )
                        session.add(apoiador)
                        message = f"✅ Apoiador criado: {months} meses de {tipo_apoio}"
                    else:
                        if apoiador.ativo:
                            if apoiador.data_expiracao:
                                apoiador.data_expiracao += timedelta(days=months * 30)
                            else:
                                apoiador.data_expiracao = now + timedelta(days=months * 30)
                            apoiador.duracao_meses = (apoiador.duracao_meses or 0) + months
                            apoiador.ultimo_pagamento = now
                            message = f"✅ Apoiador estendido: +{months} meses (total: {apoiador.duracao_meses} meses)"
                        else:
                            apoiador.ativo = True
                            apoiador.data_expiracao = now + timedelta(days=months * 30)
                            apoiador.duracao_meses = months
                            apoiador.ultimo_pagamento = now
                            message = f"✅ Apoiador reativado: {months} meses de {tipo_apoio}"

                elif action == 'pausar':
                    if not apoiador or not apoiador.ativo:
                        await interaction.followup.send("❌ Apoiador não encontrado ou já inativo.", ephemeral=True)
                        return
                    apoiador.ativo = False
                    message = "✅ Apoiador pausado (doações interrompidas)"

                elif action == 'continuar':
                    if not apoiador:
                        await interaction.followup.send("❌ Apoiador não encontrado.", ephemeral=True)
                        return
                    if apoiador.ativo:
                        await interaction.followup.send("❌ Apoiador já está ativo.", ephemeral=True)
                        return
                    apoiador.ativo = True
                    apoiador.ultimo_pagamento = now
                    message = "✅ Apoiador reativado (doações continuadas)"

                elif action == 'remover':
                    if not apoiador:
                        await interaction.followup.send("❌ Apoiador não encontrado.", ephemeral=True)
                        return
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

            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"Apoiador gerenciado por {interaction.user}: {discord_id} - {action}")

        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao executar ação: {str(e)}", ephemeral=True)
            logger.error(f"Erro ao executar ação de apoiador: {e}")


class ManageSupporterActionView(ui.View):
    def __init__(self, role_manager):
        super().__init__()
        self.role_manager = role_manager

    async def _open_modal(self, interaction: discord.Interaction, action: str, title: str):
        await interaction.response.send_modal(SupporterActionModal(self.role_manager, action, title))

    @ui.button(label="➕ Adicionar", style=discord.ButtonStyle.success)
    async def add_supporter(self, interaction: discord.Interaction, button: ui.Button):
        if not check_is_owner(interaction):
            await interaction.response.send_message("❌ Apenas admins podem usar essa função!", ephemeral=True)
            return
        await self._open_modal(interaction, 'adicionar', 'Adicionar Apoiador')

    @ui.button(label="⏸️ Pausar", style=discord.ButtonStyle.secondary)
    async def pause_supporter(self, interaction: discord.Interaction, button: ui.Button):
        if not check_is_owner(interaction):
            await interaction.response.send_message("❌ Apenas admins podem usar essa função!", ephemeral=True)
            return
        await self._open_modal(interaction, 'pausar', 'Pausar Apoiador')

    @ui.button(label="▶️ Continuar", style=discord.ButtonStyle.primary)
    async def continue_supporter(self, interaction: discord.Interaction, button: ui.Button):
        if not check_is_owner(interaction):
            await interaction.response.send_message("❌ Apenas admins podem usar essa função!", ephemeral=True)
            return
        await self._open_modal(interaction, 'continuar', 'Continuar Apoiador')

    @ui.button(label="🗑️ Remover", style=discord.ButtonStyle.danger)
    async def remove_supporter(self, interaction: discord.Interaction, button: ui.Button):
        if not check_is_owner(interaction):
            await interaction.response.send_message("❌ Apenas admins podem usar essa função!", ephemeral=True)
            return
        await self._open_modal(interaction, 'remover', 'Remover Apoiador')


class ManageSupporterView(ui.View):
    def __init__(self, bot, role_manager):
        super().__init__()
        self.bot = bot
        self.role_manager = role_manager

    @ui.button(label="👤 Gerenciar Apoiador", style=discord.ButtonStyle.primary)
    async def manage_supporter_button(self, interaction: discord.Interaction, button: ui.Button):
        if not check_is_owner(interaction):
            await interaction.response.send_message("❌ Apenas admins podem usar essa função!", ephemeral=True)
            return
        try:
            view = ManageSupporterActionView(self.role_manager)
            await interaction.response.send_message(
                "Selecione a ação desejada e, em seguida, preencha apenas os campos necessários.",
                view=view,
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(AdminCommands(bot))