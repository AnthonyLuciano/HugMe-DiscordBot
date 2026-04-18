import discord
import logging
import os
from discord.ext import commands
from discord import ui
from bot.database.models import PixConfig, Apoiador, GuildConfig
from bot.servicos.SupporterRoleManager import SupporterRoleManager
from sqlalchemy import select, func
from bot.database import AsyncSessionLocal
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

def check_is_owner(ctx_or_interaction) -> bool:
    """Verifica se o usuário é owner - funciona com Context ou Interaction"""
    mod_id = os.getenv('TRUSTED_MOD_ID')
    dev_id = os.getenv('DEV_ID')
    
    # Funciona tanto com discord.Interaction quanto commands.Context
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

# ============== MODALS ==============
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

            await interaction.response.send_message(embed=embed, ephemeral=True)
            logger.info(f"PIX configurado por {interaction.user}: {url}")
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)
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
        # Placeholder - será usado com role selection depois
        await interaction.response.defer()


class ConfirmView(ui.View):
    """View simples com botões Confirmar/Cancelar"""
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


class DashboardView(ui.View):
    """Dashboard principal com acesso a todas as funções"""
    def __init__(self, bot, cog):
        super().__init__()
        self.bot = bot
        self.cog = cog

    async def check_owner(self, interaction: discord.Interaction) -> bool:
        """Verifica se é owner antes de executar"""
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
                receita_total = result.scalar() or 0
                receita_total /= 100

                total_servidores = len(self.bot.guilds)

            embed = discord.Embed(
                title="📊 Painel de Controle - HugMe Bot (ATUALIZADO)",
                color=discord.Color.blue(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="👥 Apoiadores Ativos", value=f"{total_apoiadores}", inline=True)
            embed.add_field(name="🆕 Doações Recentes (30d)", value=f"{recentes}", inline=True)
            embed.add_field(name="💰 Receita Total", value=f"R$ {receita_total:.2f}", inline=True)
            embed.add_field(name="🏠 Servidores", value=f"{total_servidores}", inline=True)

            view = DashboardView(self.bot, self.cog)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            logger.info(f"Dashboard atualizado por {interaction.user}")
        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao atualizar: {str(e)}", ephemeral=True)
            logger.error(f"Erro ao atualizar dashboard: {e}")

    @ui.button(label="� Gerenciar Apoiadores", style=discord.ButtonStyle.primary)
    async def manage_supporters(self, interaction: discord.Interaction, button: ui.Button):
        if not await self.check_owner(interaction):
            return
        try:
            embed = discord.Embed(
                title="👤 Gerenciar Apoiadores Manualmente",
                description="Gerencie apoiadores que fazem doações fora do sistema automático (como apoia-se).\n\n**Ações disponíveis:**\n• **Adicionar**: Cria ou estende apoio manual\n• **Pausar**: Interrompe temporariamente o apoio\n• **Continuar**: Retoma apoio pausado\n• **Remover**: Remove completamente do sistema",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="📝 Como usar",
                value="1. Clique no botão abaixo\n2. Digite o ID do usuário ou @menção\n3. Escolha a ação\n4. Para 'adicionar', especifique os meses\n5. Opcional: tipo de apoio (padrão: manual)",
                inline=False
            )

            view = ManageSupporterView(self.bot, self.cog.role_manager)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            logger.info(f"Gerenciamento de apoiadores aberto para {interaction.user}")
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)
            logger.error(f"Erro ao abrir gerenciamento de apoiadores: {e}")

    @ui.button(label="�📋 Apoiadores", style=discord.ButtonStyle.secondary)
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

            embed = discord.Embed(
                title="👥 Últimos 10 Apoiadores",
                color=discord.Color.gold()
            )
            supporter_list = []
            for apo in apoiadores:
                tipo = apo.tipo_apoio
                nivel = apo.nivel
                expiry = apo.data_expiracao.strftime("%d/%m/%Y") if apo.data_expiracao else "Permanente"
                supporter_list.append(f"**{apo.discord_id}** - {tipo} Nível {nivel} (Expira: {expiry})")

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

            if server_list:
                # Limita a 15 servidores por página
                embed.description = "\n".join(server_list[:15])
            else:
                embed.description = "Nenhum servidor encontrado."

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
                view = PIXConfigView()
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
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

            view = PIXConfigView()
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
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

            embed = discord.Embed(
                title="⭐ Configuração de Cargos de Apoiador",
                color=discord.Color.gold(),
                description=f"Configurações para **{interaction.guild.name}**"
            )

            if not config:
                embed.add_field(
                    name="⚠️ Nenhuma Configuração",
                    value="Nenhum cargo de apoiador configurado ainda.\nUse os botões abaixo para configurar.",
                    inline=False
                )
            else:
                # Cargo padrão
                if config.cargo_apoiador_default:
                    role = interaction.guild.get_role(int(config.cargo_apoiador_default))
                    if role:
                        embed.add_field(
                            name="⭐ Cargo Padrão",
                            value=f"{role.mention}\n*Atribuído automaticamente a todos os apoiadores*",
                            inline=False
                        )
                    else:
                        embed.add_field(
                            name="⭐ Cargo Padrão",
                            value=f"ID: {config.cargo_apoiador_default} (cargo não encontrado)",
                            inline=False
                        )
                else:
                    embed.add_field(
                        name="⭐ Cargo Padrão",
                        value="Não configurado",
                        inline=False
                    )

                # Cargos baseados no tempo
                if config.cargos_tempo and isinstance(config.cargos_tempo, dict):
                    time_roles = []
                    for days_str, role_id in sorted(config.cargos_tempo.items(), key=lambda x: int(x[0])):
                        days = int(days_str)
                        role = interaction.guild.get_role(int(role_id))
                        role_name = role.mention if role else f"ID: {role_id}"
                        time_roles.append(f"**{days} dias+**: {role_name}")

                    if time_roles:
                        embed.add_field(
                            name="⏳ Cargos por Tempo de Apoio",
                            value="\n".join(time_roles),
                            inline=False
                        )
                    else:
                        embed.add_field(
                            name="⏳ Cargos por Tempo de Apoio",
                            value="Nenhum configurado",
                            inline=False
                        )
                else:
                    embed.add_field(
                        name="⏳ Cargos por Tempo de Apoio",
                        value="Nenhum configurado",
                        inline=False
                    )

            # Adiciona botões para editar
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
            modal = SetQRCodeModal()
            await interaction.response.send_modal(modal)
            logger.info(f"Modal PIX aberto para {interaction.user}")
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)
            logger.error(f"Erro ao abrir modal PIX: {e}")



class DefaultRoleSelectView(ui.View):
    """View para selecionar cargo padrão de apoiador"""
    def __init__(self, bot, guild: discord.Guild):
        super().__init__()
        self.bot = bot
        self.guild = guild

        # Obtém os roles
        roles = [r for r in guild.roles if not r.managed and r != guild.default_role]
        options = [discord.SelectOption(label=r.name[:25], value=str(r.id)) for r in roles[:25]]

        if options:
            self.select_menu = ui.Select(
                placeholder="Selecione o cargo padrão de apoiador",
                min_values=1,
                max_values=1,
                options=options
            )
        else:
            self.select_menu = ui.Select(
                placeholder="Sem cargos disponíveis",
                disabled=True,
                options=[discord.SelectOption(label="Nenhum cargo", value="none")]
            )

        self.select_menu.callback = self.role_selected
        self.add_item(self.select_menu)

    async def role_selected(self, interaction: discord.Interaction):
        """Callback quando um role é selecionado"""
        try:
            role_id = self.select_menu.values[0]
            role = self.guild.get_role(int(role_id))

            if not role:
                await interaction.response.send_message("❌ Cargo não encontrado.", ephemeral=True)
                return

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
            await interaction.response.send_message(embed=embed, ephemeral=True)
            logger.info(f"Cargo padrão definido por {interaction.user}: {role.id} em {guild_id}")
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)
            logger.error(f"Erro ao configurar cargo padrão: {e}")


class TimeRoleConfigView(ui.View):
    """View para configurar cargos baseados no tempo de apoio"""
    def __init__(self, bot, guild: discord.Guild):
        super().__init__()
        self.bot = bot
        self.guild = guild
        self.time_roles = {}  # {dias: role_id}

    @ui.button(label="➕ Adicionar Cargo", style=discord.ButtonStyle.primary)
    async def add_time_role_button(self, interaction: discord.Interaction, button: ui.Button):
        """Adiciona um novo cargo de tempo"""
        if not check_is_owner(interaction):
            await interaction.response.send_message("❌ Apenas admins podem usar essa função!", ephemeral=True)
            return
        try:
            modal = TimeRoleModal(self.time_roles)
            await interaction.response.send_modal(modal)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)

    @ui.button(label="📋 Ver Configurados", style=discord.ButtonStyle.secondary)
    async def view_time_roles_button(self, interaction: discord.Interaction, button: ui.Button):
        """Mostra cargos de tempo configurados"""
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
                embed = discord.Embed(
                    title="📋 Cargos de Tempo Configurados",
                    color=discord.Color.blue()
                )
                role_list = []
                for days, role_id in sorted(self.time_roles.items()):
                    role = self.guild.get_role(int(role_id))
                    role_name = role.name if role else f"ID: {role_id} (não encontrado)"
                    role_list.append(f"**{days} dias+**: {role_name}")
                embed.description = "\n".join(role_list)

            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)

    @ui.button(label="💾 Salvar Configuração", style=discord.ButtonStyle.success)
    async def save_time_config_button(self, interaction: discord.Interaction, button: ui.Button):
        """Salva a configuração de cargos de tempo"""
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
            await interaction.response.send_message(embed=embed, ephemeral=True)
            logger.info(f"Cargos de tempo salvos por {interaction.user}: {self.time_roles}")
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro ao salvar: {str(e)}", ephemeral=True)
            logger.error(f"Erro ao salvar cargos de tempo: {e}")


class TimeRoleModal(ui.Modal, title="Adicionar Cargo por Tempo"):
    dias = ui.TextInput(
        label="Dias mínimos de apoio",
        placeholder="Ex: 30, 90, 180, 365",
        required=True,
        min_length=1,
        max_length=4
    )

    def __init__(self, time_roles):
        super().__init__()
        self.time_roles = time_roles

    async def on_submit(self, interaction: discord.Interaction):
        try:
            days = int(self.dias.value)
            if days <= 0:
                await interaction.response.send_message("❌ Dias deve ser maior que 0.", ephemeral=True)
                return

            # Cria select para escolher o cargo
            guild = interaction.guild
            roles = [r for r in guild.roles if not r.managed and r != guild.default_role]
            options = [discord.SelectOption(label=r.name[:25], value=str(r.id)) for r in roles[:25]]

            if not options:
                await interaction.response.send_message("❌ Nenhum cargo disponível.", ephemeral=True)
                return

            view = TimeRoleSelectView(self.time_roles, days, options)
            embed = discord.Embed(
                title=f"🎯 Selecionar Cargo para {days} dias+",
                description="Escolha o cargo que será atribuído aos apoiadores com pelo menos este tempo de apoio.",
                color=discord.Color.blue()
            )

            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        except ValueError:
            await interaction.response.send_message("❌ Valor inválido para dias.", ephemeral=True)


class TimeRoleSelectView(ui.View):
    """View para selecionar cargo específico para tempo"""
    def __init__(self, time_roles, days, options):
        super().__init__()
        self.time_roles = time_roles
        self.days = days

        self.select_menu = ui.Select(
            placeholder=f"Selecione cargo para {days} dias+",
            min_values=1,
            max_values=1,
            options=options
        )
        self.select_menu.callback = self.role_selected
        self.add_item(self.select_menu)

    async def role_selected(self, interaction: discord.Interaction):
        """Callback quando um role é selecionado"""
        try:
            role_id = self.select_menu.values[0]
            self.time_roles[str(self.days)] = role_id

            role = interaction.guild.get_role(int(role_id))
            role_name = role.name if role else f"ID: {role_id}"

            embed = discord.Embed(
                title="✅ Cargo Adicionado",
                color=discord.Color.green(),
                description=f"Cargo **{role_name}** configurado para apoiadores com **{self.days} dias+** de apoio"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)


class PIXConfigView(ui.View):
    def __init__(self):
        super().__init__()

    @ui.button(label="✏️ Editar", style=discord.ButtonStyle.primary)
    async def edit(self, interaction: discord.Interaction, button: ui.Button):
        modal = SetQRCodeModal()
        await interaction.response.send_modal(modal)

    @ui.button(label="❌ Limpar Config", style=discord.ButtonStyle.danger)
    async def clear_config(self, interaction: discord.Interaction, button: ui.Button):
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(select(PixConfig))
                config = result.scalars().first()
                if config:
                    await session.delete(config)
                    await session.commit()
                    await interaction.response.send_message("✅ Configuração PIX removida", ephemeral=True)
                else:
                    await interaction.response.send_message("⚠️ Nenhuma configuração para remover", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)
            logger.error(f"Erro ao limpar PIX config: {e}")


class RoleConfigView(ui.View):
    """View para gerenciar configuração de cargos de apoiador"""
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
            # Re-executar a visualização
            guild_id = str(self.guild.id)
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(GuildConfig).where(GuildConfig.guild_id == guild_id)
                )
                config = result.scalars().first()

            embed = discord.Embed(
                title="⭐ Configuração de Cargos de Apoiador",
                color=discord.Color.gold(),
                description=f"Configurações para **{self.guild.name}**"
            )

            if not config:
                embed.add_field(
                    name="⚠️ Nenhuma Configuração",
                    value="Nenhum cargo de apoiador configurado ainda.\nUse os botões abaixo para configurar.",
                    inline=False
                )
            else:
                # Cargo padrão
                if config.cargo_apoiador_default:
                    role = self.guild.get_role(int(config.cargo_apoiador_default))
                    if role:
                        embed.add_field(
                            name="⭐ Cargo Padrão",
                            value=f"{role.mention}\n*Atribuído automaticamente a todos os apoiadores*",
                            inline=False
                        )
                    else:
                        embed.add_field(
                            name="⭐ Cargo Padrão",
                            value=f"ID: {config.cargo_apoiador_default} (cargo não encontrado)",
                            inline=False
                        )
                else:
                    embed.add_field(
                        name="⭐ Cargo Padrão",
                        value="Não configurado",
                        inline=False
                    )

                # Cargos baseados no tempo
                if config.cargos_tempo and isinstance(config.cargos_tempo, dict):
                    time_roles = []
                    for days_str, role_id in sorted(config.cargos_tempo.items(), key=lambda x: int(x[0])):
                        days = int(days_str)
                        role = self.guild.get_role(int(role_id))
                        role_name = role.mention if role else f"ID: {role_id}"
                        time_roles.append(f"**{days} dias+**: {role_name}")

                    if time_roles:
                        embed.add_field(
                            name="⏳ Cargos por Tempo de Apoio",
                            value="\n".join(time_roles),
                            inline=False
                        )
                    else:
                        embed.add_field(
                            name="⏳ Cargos por Tempo de Apoio",
                            value="Nenhum configurado",
                            inline=False
                        )
                else:
                    embed.add_field(
                        name="⏳ Cargos por Tempo de Apoio",
                        value="Nenhum configurado",
                        inline=False
                    )

            view = RoleConfigView(self.bot, self.guild)
            await interaction.response.edit_message(embed=embed, view=view)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro ao atualizar: {str(e)}", ephemeral=True)


class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.role_manager = SupporterRoleManager(bot)

    @commands.hybrid_command(name="set_qrcode", description="[ADMIN] Atualiza a imagem do QR Code PIX e chave estática")
    async def set_qrcode(self, ctx: commands.Context):
        """Update the static QR code image URL and PIX key in database"""
        if not check_is_owner(ctx.interaction if hasattr(ctx, 'interaction') else ctx):
            await ctx.send("❌ Apenas admins podem usar esse comando!", ephemeral=True)
            return
        try:
            modal = SetQRCodeModal()
            await ctx.interaction.response.send_modal(modal)
            logger.info(f"Modal PIX aberto para {ctx.author}")
        except Exception as e:
            await ctx.send(f"❌ Erro ao abrir formulário: {str(e)}", ephemeral=True)
            logger.error(f"Erro ao abrir modal PIX: {e}")

    @commands.hybrid_command(name="dashboard", description="[ADMIN] Mostra o painel de controle com estatísticas dos apoiadores")
    async def dashboard(self, ctx: commands.Context):
        """Show dashboard with supporter statistics"""
        if not check_is_owner(ctx.interaction if hasattr(ctx, 'interaction') else ctx):
            await ctx.send("❌ Apenas admins podem usar esse comando!", ephemeral=True)
            return
        try:
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
                receita_total = result.scalar() or 0
                receita_total /= 100

                total_servidores = len(self.bot.guilds)

            embed = discord.Embed(
                title="📊 Painel de Controle - HugMe Bot",
                color=discord.Color.blue(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="👥 Apoiadores Ativos", value=f"{total_apoiadores}", inline=True)
            embed.add_field(name="🆕 Doações Recentes (30d)", value=f"{recentes}", inline=True)
            embed.add_field(name="💰 Receita Total", value=f"R$ {receita_total:.2f}", inline=True)
            embed.add_field(name="🏠 Servidores", value=f"{total_servidores}", inline=True)
            embed.set_footer(text=f"Clique nos botões abaixo para gerenciar tudo!")

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
        """List all servers the bot is in"""
        if not check_is_owner(ctx.interaction if hasattr(ctx, 'interaction') else ctx):
            await ctx.send("❌ Apenas admins podem usar esse comando!", ephemeral=True)
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

            if server_list:
                embed.description = "\n".join(server_list)
            else:
                embed.description = "Nenhum servidor encontrado."

            embed.set_footer(text=f"Total: {len(self.bot.guilds)} servidores")
            await ctx.send(embed=embed, ephemeral=True)
            logger.info(f"Lista de servidores exibida para {ctx.author}")
        except Exception as e:
            await ctx.send(f"❌ Erro ao listar servidores: {str(e)}", ephemeral=True)
            logger.error(f"Erro na listagem de servidores: {e}")

    @commands.hybrid_command(name="configure_role", description="[ADMIN] Configura cargos de apoiador para um servidor")
    async def configure_role(self, ctx: commands.Context):
        """Configure supporter role for a specific level in a guild - Use /set_supporter_role instead"""
        if not check_is_owner(ctx.interaction if hasattr(ctx, 'interaction') else ctx):
            await ctx.send("❌ Apenas admins podem usar esse comando!", ephemeral=True)
            return
        try:
            embed = discord.Embed(
                title="ℹ️ Comando Descontinuado",
                description="Use `/set_supporter_role` para configurar cargos de apoiador",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Erro: {e}")

    @commands.hybrid_command(name="set_default_supporter_role", description="[ADMIN] Define o cargo padrão que todos os apoiadores terão")
    async def set_default_supporter_role(self, ctx: commands.Context):
        """Set the default supporter role that all supporters will have"""
        if not check_is_owner(ctx.interaction if hasattr(ctx, 'interaction') else ctx):
            await ctx.send("❌ Apenas admins podem usar esse comando!", ephemeral=True)
            return
        try:
            if not ctx.guild:
                await ctx.send("❌ Este comando só funciona em um servidor.", ephemeral=True)
                return

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
        """Configure time-based roles for supporters"""
        if not check_is_owner(ctx.interaction if hasattr(ctx, 'interaction') else ctx):
            await ctx.send("❌ Apenas admins podem usar esse comando!", ephemeral=True)
            return
        try:
            if not ctx.guild:
                await ctx.send("❌ Este comando só funciona em um servidor.", ephemeral=True)
                return

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
        """Show current PIX configuration"""
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
                view = PIXConfigView()
                await ctx.send(embed=embed, view=view, ephemeral=True)
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

            view = PIXConfigView()
            await ctx.send(embed=embed, view=view, ephemeral=True)
            logger.info(f"PIX config mostrada para {ctx.author}")
        except Exception as e:
            await ctx.send(f"❌ Erro ao mostrar configuração PIX: {str(e)}", ephemeral=True)
            logger.error(f"Erro ao mostrar PIX config: {e}")


    @commands.hybrid_command(name="manage_supporter", description="[ADMIN] Gerencia apoiadores manualmente (adicionar, pausar, continuar, remover)")
    async def manage_supporter(self, ctx: commands.Context):
        """Manually manage supporters (add, pause, continue, remove)"""
        if not check_is_owner(ctx.interaction if hasattr(ctx, 'interaction') else ctx):
            await ctx.send("❌ Apenas admins podem usar esse comando!", ephemeral=True)
            return
        try:
            embed = discord.Embed(
                title="👤 Gerenciar Apoiador Manualmente",
                description="Use o botão abaixo para abrir o formulário de gerenciamento de apoiadores.\n\n**Ações disponíveis:**\n• **Adicionar**: Cria ou estende apoio manual\n• **Pausar**: Interrompe temporariamente o apoio\n• **Continuar**: Retoma apoio pausado\n• **Remover**: Remove completamente do sistema",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="📝 Como usar",
                value="1. Clique no botão\n2. Digite o ID do usuário ou @menção\n3. Escolha a ação\n4. Para 'adicionar', especifique os meses\n5. Opcional: tipo de apoio (padrão: manual)",
                inline=False
            )

            view = ManageSupporterView(self.bot, self.role_manager)
            await ctx.send(embed=embed, view=view, ephemeral=True)
            logger.info(f"Gerenciamento de apoiador aberto para {ctx.author}")
        except Exception as e:
            await ctx.send(f"❌ Erro ao abrir gerenciamento: {str(e)}", ephemeral=True)
            logger.error(f"Erro ao abrir gerenciamento de apoiador: {e}")


class ManageSupporterModal(ui.Modal, title="Gerenciar Apoiador Manualmente"):
    usuario = ui.TextInput(
        label="ID do Usuário ou @menção",
        placeholder="123456789 ou @usuario",
        required=True,
        max_length=50
    )
    acao = ui.TextInput(
        label="Ação",
        placeholder="adicionar, pausar, continuar, remover",
        required=True,
        max_length=20
    )
    meses = ui.TextInput(
        label="Meses (para adicionar)",
        placeholder="5",
        required=False,
        max_length=3
    )
    tipo = ui.TextInput(
        label="Tipo de Apoio",
        placeholder="apoia-se, pix, manual",
        default="manual",
        required=False,
        max_length=20
    )

    def __init__(self, role_manager):
        super().__init__()
        self.role_manager = role_manager

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Parse user ID
            user_input = str(self.usuario).strip()
            if user_input.startswith('<@') and user_input.endswith('>'):
                # Remove <@ and > and @! if present
                user_id = user_input.replace('<@', '').replace('>', '').replace('!', '')
            else:
                user_id = user_input

            try:
                discord_id = str(int(user_id))
            except ValueError:
                await interaction.response.send_message("❌ ID de usuário inválido.", ephemeral=True)
                return

            # Parse action
            action = str(self.acao).strip().lower()
            if action not in ['adicionar', 'add', 'pausar', 'pause', 'continuar', 'continue', 'remover', 'remove']:
                await interaction.response.send_message("❌ Ação inválida. Use: adicionar, pausar, continuar, remover", ephemeral=True)
                return

            # Parse months if adding
            months = None
            if action in ['adicionar', 'add']:
                if not self.meses.value:
                    await interaction.response.send_message("❌ Número de meses é obrigatório para adicionar.", ephemeral=True)
                    return
                try:
                    months = int(str(self.meses))
                    if months <= 0:
                        await interaction.response.send_message("❌ Meses deve ser maior que 0.", ephemeral=True)
                        return
                except ValueError:
                    await interaction.response.send_message("❌ Número de meses inválido.", ephemeral=True)
                    return

            tipo_apoio = str(self.tipo).strip() or "manual"
            guild_id = str(interaction.guild.id)

            # Get or create supporter record
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(Apoiador).where(
                        Apoiador.discord_id == discord_id,
                        Apoiador.guild_id == guild_id
                    )
                )
                apoiador = result.scalars().first()

                now = datetime.now(timezone.utc)

                if action in ['adicionar', 'add']:
                    if not apoiador:
                        # Create new supporter
                        data_expiracao = now + timedelta(days=months * 30)  # Approximate months to days
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
                            ja_pago=True  # Manual addition counts as paid
                        )
                        session.add(apoiador)
                        message = f"✅ Apoiador criado: {months} meses de {tipo_apoio}"
                    else:
                        # Extend existing supporter
                        if apoiador.ativo:
                            # Active supporter - extend expiration
                            if apoiador.data_expiracao:
                                apoiador.data_expiracao += timedelta(days=months * 30)
                            else:
                                apoiador.data_expiracao = now + timedelta(days=months * 30)
                            apoiador.duracao_meses = (apoiador.duracao_meses or 0) + months
                            apoiador.ultimo_pagamento = now
                            message = f"✅ Apoiador estendido: +{months} meses (total: {apoiador.duracao_meses} meses)"
                        else:
                            # Inactive supporter - reactivate and extend
                            apoiador.ativo = True
                            apoiador.data_expiracao = now + timedelta(days=months * 30)
                            apoiador.duracao_meses = months
                            apoiador.ultimo_pagamento = now
                            message = f"✅ Apoiador reativado: {months} meses de {tipo_apoio}"

                elif action in ['pausar', 'pause']:
                    if not apoiador or not apoiador.ativo:
                        await interaction.response.send_message("❌ Apoiador não encontrado ou já inativo.", ephemeral=True)
                        return
                    apoiador.ativo = False
                    message = "✅ Apoiador pausado (doações interrompidas)"

                elif action in ['continuar', 'continue']:
                    if not apoiador:
                        await interaction.response.send_message("❌ Apoiador não encontrado.", ephemeral=True)
                        return
                    if apoiador.ativo:
                        await interaction.response.send_message("❌ Apoiador já está ativo.", ephemeral=True)
                        return
                    apoiador.ativo = True
                    apoiador.ultimo_pagamento = now
                    message = "✅ Apoiador reativado (doações continuadas)"

                elif action in ['remover', 'remove']:
                    if not apoiador:
                        await interaction.response.send_message("❌ Apoiador não encontrado.", ephemeral=True)
                        return
                    await session.delete(apoiador)
                    message = "✅ Apoiador removido do sistema"

                await session.commit()

            # Try to assign/update roles
            try:
                member = interaction.guild.get_member(int(discord_id))
                if member:
                    if action in ['adicionar', 'add', 'continuar', 'continue']:
                        # Assign roles
                        await self.role_manager.assign_default_supporter_role(member)
                        await self.role_manager.update_member_time_based_roles(member)
                    elif action in ['pausar', 'pause', 'remover', 'remove']:
                        # Remove roles if pausing/removing
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

            await interaction.response.send_message(embed=embed, ephemeral=True)
            logger.info(f"Apoiador gerenciado por {interaction.user}: {discord_id} - {action}")

        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)
            logger.error(f"Erro ao gerenciar apoiador: {e}")


class ManageSupporterView(ui.View):
    """View for managing supporters manually"""
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
            modal = ManageSupporterModal(self.role_manager)
            await interaction.response.send_modal(modal)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(AdminCommands(bot))