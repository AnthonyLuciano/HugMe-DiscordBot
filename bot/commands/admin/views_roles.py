import logging
import re
import discord
from discord import ui
from sqlalchemy import select

from bot.database import AsyncSessionLocal
from bot.database.models import GuildConfig
from .utils import check_is_owner, _build_role_config_embed
from .views_base import ConfirmationView

logger = logging.getLogger(__name__)


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

        all_roles = [r for r in guild.roles if not r.managed and r != guild.default_role]

        if filter_time_patterns:
            time_patterns = r'\b(\d+|dia|mês|ano|mes|anos|dias|meses|week|semana|horas?|hour)\b'
            self.roles = [r for r in all_roles if re.search(time_patterns, r.name, re.IGNORECASE)]
        else:
            self.roles = all_roles

        self.update_page()

    def get_page_options(self) -> list:
        start = self.current_page * self.page_size
        end = start + self.page_size
        page_roles = self.roles[start:end]
        return [discord.SelectOption(label=r.name[:25], value=str(r.id)) for r in page_roles]

    def update_page(self):
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

        for item in list(self.children):
            if isinstance(item, ui.Button):
                self.remove_item(item)

        self.add_item(self._create_prev_button())

        total_pages = max(1, (len(self.roles) + self.page_size - 1) // self.page_size)
        page_button = ui.Button(label=f"Página {self.current_page + 1}/{total_pages}", style=discord.ButtonStyle.gray, disabled=True)
        self.add_item(page_button)

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


class TimeRoleModal(ui.Modal, title="Adicionar Cargo por Tempo"):
    threshold = ui.TextInput(
        label="Valor mínimo de apoio",
        placeholder="Ex: 1, 3, 6, 12",
        required=True,
        min_length=1,
        max_length=4
    )

    def __init__(self, bot, time_roles):
        super().__init__()
        self.bot = bot
        self.time_roles = time_roles

    async def on_submit(self, interaction: discord.Interaction):
        try:
            threshold = int(self.threshold.value)
            if threshold <= 0:
                await interaction.response.send_message("❌ Valor deve ser maior que 0.", ephemeral=True)
                return

            view = TimeUnitSelectView(self.bot, self.time_roles, threshold)
            embed = discord.Embed(
                title=f"⏱️ Selecionar Unidade para {threshold}+",
                description="Escolha a unidade de tempo para este limite de apoio.",
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Valor inválido.", ephemeral=True)


class TimeUnitSelectView(ui.View):
    def __init__(self, bot, time_roles, threshold):
        super().__init__()
        self.bot = bot
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
                    description=f"**Ação:** {description}\n\nAs alterações serão salvas automaticamente após a confirmação.\n\nClique em **CONFIRMAR** para prosseguir.",
                    color=discord.Color.orange()
                )
                await inter.response.send_message(embed=embed, view=conf_view, ephemeral=True)

            unit_display = {"days": "dias", "months": "meses", "years": "anos"}.get(unit, unit)
            view = TimeRoleSelectView(
                self.bot, guild, callback,
                self.time_roles, self.threshold, unit,
                title=f"🎯 Selecionar Cargo para {self.threshold} {unit_display}+",
                description="Navegue pelas páginas para encontrar o cargo desejado. Cargos com padrões de tempo aparecem primeiro.",
                filter_time_patterns=False
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
    def __init__(self, bot, guild: discord.Guild, callback, time_roles, threshold, unit, title: str = "", description: str = "", filter_time_patterns: bool = False):
        self.time_roles = time_roles
        self.threshold = threshold
        self.unit = unit
        super().__init__(bot, guild, callback, title, description, filter_time_patterns=filter_time_patterns)

    @staticmethod
    async def _execute_add_role(interaction: discord.Interaction, role: discord.Role, unit: str, threshold: int, time_roles: list):
        try:
            time_roles.append({
                "threshold": threshold,
                "unit": unit,
                "role_id": str(role.id)
            })
            guild = interaction.guild
            if guild:
                guild_id = str(guild.id)
                async with AsyncSessionLocal() as session:
                    result = await session.execute(
                        select(GuildConfig).where(GuildConfig.guild_id == guild_id)
                    )
                    config = result.scalars().first()
                    if not config:
                        config = GuildConfig(guild_id=guild_id)
                        session.add(config)
                    config.cargos_tempo = time_roles
                    await session.commit()

            unit_display = {"days": "dias", "months": "meses", "years": "anos"}.get(unit, unit)
            embed = discord.Embed(
                title="✅ Cargo Adicionado e Salvo",
                color=discord.Color.green(),
                description=f"Cargo **{role.name}** configurado para apoiadores com **{threshold} {unit_display}+** de apoio"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {str(e)}", ephemeral=True)


class TimeRoleConfigView(ui.View):
    def __init__(self, bot, guild: discord.Guild):
        super().__init__()
        self.bot = bot
        self.guild = guild
        self.time_roles = []

    async def _load_time_roles(self):
        try:
            guild_id = str(self.guild.id)
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(GuildConfig).where(GuildConfig.guild_id == guild_id)
                )
                config = result.scalars().first()
                self.time_roles = config.cargos_tempo if config and config.cargos_tempo else []
        except Exception as e:
            logger.error(f"Erro ao carregar cargos de tempo existentes: {e}")
            self.time_roles = []

    @ui.button(label="➕ Adicionar Cargo", style=discord.ButtonStyle.primary)
    async def add_time_role_button(self, interaction: discord.Interaction, button: ui.Button):
        if not check_is_owner(interaction):
            await interaction.response.send_message("❌ Apenas admins podem usar essa função!", ephemeral=True)
            return
        try:
            await self._load_time_roles()
            await interaction.response.send_modal(TimeRoleModal(self.bot, self.time_roles))
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)

    @ui.button(label="📋 Ver Configurados", style=discord.ButtonStyle.secondary)
    async def view_time_roles_button(self, interaction: discord.Interaction, button: ui.Button):
        if not check_is_owner(interaction):
            await interaction.response.send_message("❌ Apenas admins podem usar essa função!", ephemeral=True)
            return
        try:
            await self._load_time_roles()
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
