import discord
from discord.ext import commands
from discord import ui
from datetime import datetime, timedelta, timezone
from bot.database import SessionLocal, AsyncSessionLocal
from bot.database.models import Apoiador, GuildConfig
from bot.servicos.SupporterRoleManager import SupporterRoleManager
from bot.servicos.VerificacaoMembro import VerificacaoMembro
from sqlalchemy import select, update, delete
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class TestSupporterCommands(commands.Cog):
    """Comandos para testar funcionalidades de doação e cargos de apoiadores"""

    def __init__(self, bot):
        self.bot = bot
        self.role_manager = SupporterRoleManager(bot)
        self.verificador = VerificacaoMembro(bot)

    async def _is_admin(self, ctx: commands.Context) -> bool:
        """Verifica se o usuário é administrador"""
        if ctx.author.guild_permissions.administrator:
            return True

        # Verifica se tem cargo de admin configurado
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(GuildConfig).where(GuildConfig.guild_id == str(ctx.guild.id))
                )
                config = result.scalars().first()
                if config and config.cargo_apoiador_default:
                    admin_role = ctx.guild.get_role(int(config.cargo_apoiador_default))
                    if admin_role and admin_role in ctx.author.roles:
                        return True
        except Exception as e:
            logger.error(f"Erro ao verificar admin: {e}")

        return False

    @commands.hybrid_command(
        name='test_doacao',
        description="[ADMIN] Simula uma doação para testar atribuição de cargos"
    )
    @commands.guild_only()
    async def test_doacao(
        self,
        ctx: commands.Context,
        membro: discord.Member,
        valor: float = commands.parameter(description="Valor da doação em R$"),
        dias_apoio: int = commands.parameter(default=0, description="Dias de apoio a adicionar (0 para usar data atual)")
    ):
        """Simula uma doação para um membro e testa a atribuição de cargos"""

        if not await self._is_admin(ctx):
            await ctx.send("❌ Você não tem permissão para usar este comando.")
            return

        try:
            # Calcula data de início
            if dias_apoio > 0:
                data_inicio = datetime.now(timezone.utc) - timedelta(days=dias_apoio)
            else:
                data_inicio = datetime.now(timezone.utc)

            # Cria registro de doação simulada
            async with AsyncSessionLocal() as session:
                # Remove doações anteriores do mesmo usuário para teste limpo
                await session.execute(
                    delete(Apoiador).where(
                        Apoiador.discord_id == str(membro.id),
                        Apoiador.guild_id == str(ctx.guild.id)
                    )
                )

                apoiador = Apoiador(
                    discord_id=str(membro.id),
                    guild_id=str(ctx.guild.id),
                    tipo_apoio="pix_simulado",
                    valor_doacao=int(valor * 100),  # Converte para centavos
                    data_inicio=data_inicio,
                    ultimo_pagamento=datetime.now(timezone.utc),
                    ativo=True,
                    ja_pago=True
                )
                session.add(apoiador)
                await session.commit()

            # Atribui cargos
            default_assigned = await self.role_manager.assign_default_supporter_role(membro)
            time_updated = await self.role_manager.update_member_time_based_roles(membro)

            # Calcula tempo total de apoio
            total_days = await self.role_manager.calculate_total_support_time(str(membro.id), str(ctx.guild.id))

            embed = discord.Embed(
                title="🧪 Doação Simulada",
                description=f"Doação simulada criada para {membro.mention}",
                color=0x00FF00
            )
            embed.add_field(name="Valor", value=f"R$ {valor:.2f}", inline=True)
            embed.add_field(name="Dias de Apoio", value=f"{dias_apoio if dias_apoio > 0 else 'Novo'}", inline=True)
            embed.add_field(name="Tempo Total", value=f"{total_days} dias", inline=True)
            embed.add_field(name="Cargo Padrão", value="✅ Atribuído" if default_assigned else "❌ Não atribuído", inline=True)
            embed.add_field(name="Cargo por Tempo", value="✅ Atualizado" if time_updated else "❌ Não atualizado", inline=True)

            # Lista cargos atuais relacionados a apoiadores
            supporter_roles = []
            config = await self.role_manager.get_guild_config(str(ctx.guild.id))
            if config:
                if config.cargo_apoiador_default:
                    role = ctx.guild.get_role(int(config.cargo_apoiador_default))
                    if role and role in membro.roles:
                        supporter_roles.append(f"🏷️ {role.name}")

                if config.cargos_tempo:
                    for time_config in config.cargos_tempo:
                        role_id = time_config.get('role_id')
                        threshold = time_config.get('threshold', 0)
                        unit = time_config.get('unit', 'days')
                        if role_id:
                            role = ctx.guild.get_role(int(role_id))
                            if role and role in membro.roles:
                                unit_display = {"days": "dias", "months": "meses", "years": "anos"}.get(unit, unit)
                                supporter_roles.append(f"⏳ {role.name} ({threshold}+ {unit_display})")

            if supporter_roles:
                embed.add_field(name="Cargos Atuais", value="\n".join(supporter_roles), inline=False)
            else:
                embed.add_field(name="Cargos Atuais", value="Nenhum cargo de apoiador", inline=False)

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Erro no teste de doação: {e}")
            await ctx.send(f"❌ Erro ao simular doação: {str(e)}")

    @commands.hybrid_command(
        name='test_atualizar_cargos',
        description="[ADMIN] Força atualização de cargos para todos os apoiadores"
    )
    @commands.guild_only()
    async def test_atualizar_cargos(self, ctx: commands.Context):
        """Atualiza cargos de todos os apoiadores do servidor"""

        if not await self._is_admin(ctx):
            await ctx.send("❌ Você não tem permissão para usar este comando.")
            return

        try:
            await ctx.send("🔄 Iniciando atualização de cargos...")

            stats = await self.role_manager.update_all_supporters_roles(ctx.guild)

            if "error" in stats:
                await ctx.send(f"❌ Erro na atualização: {stats['error']}")
                return

            embed = discord.Embed(
                title="🔄 Atualização de Cargos Concluída",
                description=f"Servidor: {ctx.guild.name}",
                color=0x00FF00
            )
            embed.add_field(name="Total Processados", value=str(stats['total_processed']), inline=True)
            embed.add_field(name="Atualizados", value=str(stats['updated']), inline=True)
            embed.add_field(name="Servidor", value=str(stats['guild_name']), inline=True)

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Erro ao atualizar cargos: {e}")
            await ctx.send(f"❌ Erro ao atualizar cargos: {str(e)}")

    @commands.hybrid_command(
        name='test_verificar_apoiador',
        description="[ADMIN] Verifica status de apoiador de um membro"
    )
    @commands.guild_only()
    async def test_verificar_apoiador(
        self,
        ctx: commands.Context,
        membro: discord.Member = commands.parameter(default=None, description="Membro para verificar (padrão: você)")
    ):
        """Verifica o status completo de apoiador de um membro"""

        if not await self._is_admin(ctx):
            await ctx.send("❌ Você não tem permissão para usar este comando.")
            return

        membro = membro or ctx.author

        try:
            # Busca dados do apoiador
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(Apoiador).where(
                        Apoiador.discord_id == str(membro.id),
                        Apoiador.guild_id == str(ctx.guild.id)
                    )
                )
                apoiador = result.scalars().first()

            embed = discord.Embed(
                title=f"🔍 Status de Apoiador - {membro.display_name}",
                color=0x3498db
            )

            if apoiador:
                embed.add_field(name="ID Discord", value=apoiador.discord_id, inline=True)
                embed.add_field(name="Tipo de Apoio", value=apoiador.tipo_apoio, inline=True)
                embed.add_field(name="Ativo", value="✅ Sim" if apoiador.ativo else "❌ Não", inline=True)
                embed.add_field(name="Já Pagou", value="✅ Sim" if apoiador.ja_pago else "❌ Não", inline=True)

                if apoiador.valor_doacao:
                    embed.add_field(name="Valor Doação", value=f"R$ {apoiador.valor_doacao / 100:.2f}", inline=True)

                if apoiador.data_inicio:
                    embed.add_field(name="Data Início", value=apoiador.data_inicio.strftime("%d/%m/%Y"), inline=True)

                if apoiador.ultimo_pagamento:
                    embed.add_field(name="Último Pagamento", value=apoiador.ultimo_pagamento.strftime("%d/%m/%Y"), inline=True)

                # Calcula tempo total
                total_days = await self.role_manager.calculate_total_support_time(str(membro.id), str(ctx.guild.id))
                embed.add_field(name="Tempo Total de Apoio", value=f"{total_days} dias", inline=True)

                # Verifica cargo apropriado
                time_role = await self.role_manager.get_appropriate_time_role(ctx.guild, total_days)
                if time_role:
                    has_role = time_role in membro.roles
                    embed.add_field(name="Cargo por Tempo", value=f"{time_role.name} ({'✅' if has_role else '❌'})", inline=True)
                else:
                    embed.add_field(name="Cargo por Tempo", value="Nenhum disponível", inline=True)

            else:
                embed.add_field(name="Status", value="❌ Não é apoiador registrado", inline=False)

            # Lista todos os cargos de apoiador que o membro tem
            supporter_roles = []
            config = await self.role_manager.get_guild_config(str(ctx.guild.id))
            if config:
                if config.cargo_apoiador_default:
                    role = ctx.guild.get_role(int(config.cargo_apoiador_default))
                    if role and role in membro.roles:
                        supporter_roles.append(f"🏷️ {role.name} (Padrão)")

                if config.cargos_tempo:
                    for time_config in config.cargos_tempo:
                        role_id = time_config.get('role_id')
                        threshold = time_config.get('threshold', 0)
                        unit = time_config.get('unit', 'days')
                        if role_id:
                            role = ctx.guild.get_role(int(role_id))
                            if role and role in membro.roles:
                                unit_display = {"days": "dias", "months": "meses", "years": "anos"}.get(unit, unit)
                                supporter_roles.append(f"⏳ {role.name} ({threshold}+ {unit_display})")

            if supporter_roles:
                embed.add_field(name="Cargos Atuais", value="\n".join(supporter_roles), inline=False)
            else:
                embed.add_field(name="Cargos Atuais", value="Nenhum", inline=False)

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Erro ao verificar apoiador: {e}")
            await ctx.send(f"❌ Erro ao verificar status: {str(e)}")

    @commands.hybrid_command(
        name='test_limpar_apoiador',
        description="[ADMIN] Remove registro de apoiador para teste"
    )
    @commands.guild_only()
    async def test_limpar_apoiador(
        self,
        ctx: commands.Context,
        membro: discord.Member
    ):
        """Remove o registro de apoiador de um membro para limpeza de testes"""

        if not await self._is_admin(ctx):
            await ctx.send("❌ Você não tem permissão para usar este comando.")
            return

        try:
            # Remove do banco
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    delete(Apoiador).where(
                        Apoiador.discord_id == str(membro.id),
                        Apoiador.guild_id == str(ctx.guild.id)
                    )
                )
                deleted = result.rowcount
                await session.commit()

            # Remove cargos de apoiador
            config = await self.role_manager.get_guild_config(str(ctx.guild.id))
            roles_to_remove = []

            if config:
                if config.cargo_apoiador_default:
                    role = ctx.guild.get_role(int(config.cargo_apoiador_default))
                    if role and role in membro.roles:
                        roles_to_remove.append(role)

                if config.cargos_tempo:
                    for time_config in config.cargos_tempo:
                        role_id = time_config.get('role_id')
                        if role_id:
                            role = ctx.guild.get_role(int(role_id))
                            if role and role in membro.roles:
                                roles_to_remove.append(role)

            if roles_to_remove:
                await membro.remove_roles(*roles_to_remove)

            embed = discord.Embed(
                title="🧹 Limpeza Concluída",
                description=f"Registro removido para {membro.mention}",
                color=0xFFA500
            )
            embed.add_field(name="Registros Removidos", value=str(deleted), inline=True)
            embed.add_field(name="Cargos Removidos", value=str(len(roles_to_remove)), inline=True)

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Erro ao limpar apoiador: {e}")
            await ctx.send(f"❌ Erro ao limpar registro: {str(e)}")

    async def _process_test_donation(self, interaction: discord.Interaction, membro: discord.Member, valor: float, tempo: int, unidade: str):
        """Processa a doação de teste após confirmação do modal"""
        try:
            # Calcula data de início baseada na unidade
            if unidade == "days":
                data_inicio = datetime.now(timezone.utc) - timedelta(days=tempo)
            elif unidade == "weeks":
                data_inicio = datetime.now(timezone.utc) - timedelta(weeks=tempo)
            elif unidade == "months":
                data_inicio = datetime.now(timezone.utc) - timedelta(days=tempo * 30)  # Aproximação
            elif unidade == "years":
                data_inicio = datetime.now(timezone.utc) - timedelta(days=tempo * 365)  # Aproximação
            else:
                data_inicio = datetime.now(timezone.utc) - timedelta(days=tempo)

            # Cria registro de doação simulada
            async with AsyncSessionLocal() as session:
                # Remove doações anteriores do mesmo usuário para teste limpo
                await session.execute(
                    delete(Apoiador).where(
                        Apoiador.discord_id == str(membro.id),
                        Apoiador.guild_id == str(interaction.guild.id)
                    )
                )

                apoiador = Apoiador(
                    discord_id=str(membro.id),
                    guild_id=str(interaction.guild.id),
                    tipo_apoio="pix_simulado",
                    valor_doacao=int(valor * 100),  # Converte para centavos
                    data_inicio=data_inicio,
                    ultimo_pagamento=datetime.now(timezone.utc),
                    ativo=True,
                    ja_pago=True
                )
                session.add(apoiador)
                await session.commit()

            # Atribui cargos
            default_assigned = await self.role_manager.assign_default_supporter_role(membro)
            time_updated = await self.role_manager.update_member_time_based_roles(membro)

            # Calcula tempo total de apoio
            total_days = await self.role_manager.calculate_total_support_time(str(membro.id), str(interaction.guild.id))

            embed = discord.Embed(
                title="🧪 Doação Simulada",
                description=f"Doação simulada criada para {membro.mention}",
                color=0x00FF00
            )
            embed.add_field(name="Valor", value=f"R$ {valor:.2f}", inline=True)
            embed.add_field(name="Tempo Simulado", value=f"{tempo} {unidade}", inline=True)
            embed.add_field(name="Tempo Total", value=f"{total_days} dias", inline=True)
            embed.add_field(name="Cargo Padrão", value="✅ Atribuído" if default_assigned else "❌ Não atribuído", inline=True)
            embed.add_field(name="Cargo por Tempo", value="✅ Atualizado" if time_updated else "❌ Não atualizado", inline=True)

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            logger.error(f"Erro no processamento de doação teste: {e}")
            await interaction.response.send_message(f"❌ Erro ao processar doação: {str(e)}")


class TestDonationModal(ui.Modal, title="Configurar Doação de Teste"):
    """Modal para configurar parâmetros da doação de teste"""

    def __init__(self, cog, membro: discord.Member, valor: float):
        super().__init__(timeout=300.0)
        self.cog = cog
        self.membro = membro
        self.valor = valor

    tempo_apoio = ui.TextInput(
        label="Tempo de Apoio",
        placeholder="Ex: 30",
        required=True,
        max_length=3
    )

    unidade_select = ui.Select(
        placeholder="Escolha a unidade de tempo",
        options=[
            discord.SelectOption(label="Dias", value="days", description="Tempo em dias"),
            discord.SelectOption(label="Semanas", value="weeks", description="Tempo em semanas"),
            discord.SelectOption(label="Meses", value="months", description="Tempo em meses"),
            discord.SelectOption(label="Anos", value="years", description="Tempo em anos")
        ]
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            tempo = int(self.tempo_apoio.value)
            unidade = self.unidade_select.values[0] if self.unidade_select.values else "days"

            # Processa a doação
            await self.cog._process_test_donation(interaction, self.membro, self.valor, tempo, unidade)

        except ValueError:
            await interaction.response.send_message(
                "❌ Tempo deve ser um número válido."
            )
        except Exception as e:
            logger.error(f"Erro no modal de teste: {e}")
            await interaction.response.send_message(
                f"❌ Erro ao processar: {str(e)}"
            )


async def setup(bot):
    await bot.add_cog(TestSupporterCommands(bot))
