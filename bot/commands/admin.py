import discord
import logging
import os
from discord.ext import commands
from discord import ui
from bot.database.models import PixConfig, Apoiador, GuildConfig
from bot.database import AsyncSessionLocal
from sqlalchemy import select, func
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

    @ui.button(label="🎯 Configurar Cargo", style=discord.ButtonStyle.secondary)
    async def configure_role_button(self, interaction: discord.Interaction, button: ui.Button):
        if not await self.check_owner(interaction):
            return
        if not interaction.guild:
            await interaction.response.send_message("❌ Este comando só funciona em um servidor.", ephemeral=True)
            return
        try:
            view = RoleSelectView(self.bot, interaction.guild)

            embed = discord.Embed(
                title="🎯 Selecione o Cargo de Apoiador",
                description="Escolha o cargo que será atribuído aos apoiadores",
                color=discord.Color.blue()
            )

            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            logger.info(f"Select de cargo aberto para {interaction.user}")
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)
            logger.error(f"Erro ao abrir seletor de cargo: {e}")

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

    @ui.button(label="❌ Fechar", style=discord.ButtonStyle.danger)
    async def close_dashboard(self, interaction: discord.Interaction, button: ui.Button):
        if not await self.check_owner(interaction):
            return
        try:
            # Tenta deletar a mensagem original
            await interaction.message.delete()
            logger.info(f"Dashboard fechado (deletado) por {interaction.user}")
        except Exception as e:
            logger.error(f"Erro ao fechar dashboard: {e}")


class RoleSelectView(ui.View):
    """View com select dinâmico de roles"""
    def __init__(self, bot, guild: discord.Guild):
        super().__init__()
        self.bot = bot
        self.guild = guild
        
        # Obtém os roles e cria as opções
        roles = [r for r in guild.roles if not r.managed and r != guild.default_role]
        options = [discord.SelectOption(label=r.name[:25], value=str(r.id)) for r in roles[:25]]
        
        # Cria o select com as opções
        if options:
            self.select_menu = ui.Select(
                placeholder="Selecione um cargo de apoiador",
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

                config.cargo_apoiador_id = str(role.id)
                await session.commit()

            embed = discord.Embed(
                title="✅ Cargo Configurado",
                color=discord.Color.green(),
                description=f"Cargo base de apoiador definido para: {role.mention}"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            logger.info(f"Cargo definido por {interaction.user}: {role.id} em {guild_id}")
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)
            logger.error(f"Erro ao configurar cargo: {e}")


class PIXConfigView(ui.View):
    """View para configuração de PIX"""
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


# ============== COG ==============
class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

    @commands.hybrid_command(name="set_supporter_role", description="[ADMIN] Define o cargo base de apoiador para um servidor")
    async def set_supporter_role(self, ctx: commands.Context):
        """Set the base supporter role for the current guild"""
        if not check_is_owner(ctx.interaction if hasattr(ctx, 'interaction') else ctx):
            await ctx.send("❌ Apenas admins podem usar esse comando!", ephemeral=True)
            return
        try:
            if not ctx.guild:
                await ctx.send("❌ Este comando só funciona em um servidor.", ephemeral=True)
                return

            view = RoleSelectView(self.bot, ctx.guild)

            embed = discord.Embed(
                title="🎯 Selecione o Cargo de Apoiador",
                description="Escolha o cargo que será atribuído aos apoiadores",
                color=discord.Color.blue()
            )

            await ctx.send(embed=embed, view=view, ephemeral=True)
            logger.info(f"Select de cargo aberto para {ctx.author}")
        except Exception as e:
            await ctx.send(f"❌ Erro ao abrir seletor: {str(e)}", ephemeral=True)
            logger.error(f"Erro ao abrir seletor de cargo: {e}")

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


async def setup(bot):
    await bot.add_cog(AdminCommands(bot))