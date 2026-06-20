import logging
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta

import discord
from discord import ui
from sqlalchemy import select

from bot.database import AsyncSessionLocal
from bot.database.models import Apoiador, GuildConfig
from .utils import check_is_owner
from .views_base import ConfirmationView

logger = logging.getLogger(__name__)


# ==================== MODALS ====================

class SupporterActionModal(ui.Modal):
    usuario = ui.TextInput(
        label="ID do Usuário ou @menção",
        placeholder="123456789 ou @usuario",
        required=True,
        max_length=50
    )
    threshold = ui.TextInput(
        label="Duração do apoio",
        placeholder="Ex: 1, 3, 6, 12",
        required=True,
        min_length=1,
        max_length=4
    )
    tipo = ui.TextInput(
        label="Tipo de Apoio (opcional)",
        placeholder="apoia-se, pix, manual",
        default="manual",
        required=False,
        max_length=20
    )
    valor = ui.TextInput(
        label="Valor do apoio (R$)",
        placeholder="Ex: 12.50",
        required=False,
        max_length=20
    )

    def __init__(self, role_manager):
        self.role_manager = role_manager
        super().__init__(title="Adicionar Apoiador")

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

            try:
                threshold = int(str(self.threshold).strip())
                if threshold <= 0:
                    await interaction.response.send_message("❌ Duração deve ser maior que 0.", ephemeral=True)
                    return
            except ValueError:
                await interaction.response.send_message("❌ Duração inválida.", ephemeral=True)
                return

            tipo_apoio = str(self.tipo).strip() or "manual"

            valor_text = str(self.valor).strip()
            amount_cents = None
            if valor_text:
                valor_text = valor_text.replace(',', '.')
                try:
                    amount = float(valor_text)
                    if amount < 0:
                        raise ValueError("Valor negativo")
                    amount_cents = int(round(amount * 100))
                except ValueError:
                    await interaction.response.send_message("❌ Valor inválido. Use um número como 12.50", ephemeral=True)
                    return

            view = SupporterTimeTypeSelectView(self.role_manager, threshold, tipo_apoio, discord_id, amount_cents)
            embed = discord.Embed(
                title="⏰ Tipo de Período de Apoio",
                description="Escolha se o tempo sendo adicionado é:\n"
                           "• **Retroativo**: Contabiliza como se já estivesse em vigor (data de início no passado)\n"
                           "• **Antecipado**: Estende o apoio futuro (próxima data de vencimento)",
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)
            logger.error(f"Erro ao processar ação de apoiador: {e}")


class SupporterPauseModal(ui.Modal, title="Pausar Apoiador"):
    usuario = ui.TextInput(
        label="ID do Usuário ou @menção",
        placeholder="123456789 ou @usuario",
        required=True,
        max_length=50
    )

    def __init__(self, role_manager):
        self.role_manager = role_manager
        super().__init__()

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

            description = f"Pausar apoio de <@{discord_id}> (interromper doações)"
            view = ConfirmationView(
                action_description=description,
                confirm_callback=lambda i: self._execute_pause_action(i, discord_id),
            )
            embed = discord.Embed(
                title="⚠️ Confirmar Ação",
                description=f"**Ação:** {description}\n\nClique em **CONFIRMAR** para prosseguir.",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)
            logger.error(f"Erro ao processar pausa de apoiador: {e}")

    async def _execute_pause_action(self, interaction: discord.Interaction, discord_id: str):
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

                if not apoiador or not apoiador.ativo:
                    await interaction.followup.send("❌ Apoiador não encontrado ou já está pausado.", ephemeral=True)
                    return

                apoiador.ativo = False
                await session.commit()

            try:
                member = interaction.guild.get_member(int(discord_id))
                if member:
                    config = await self.role_manager.get_guild_config(guild_id)
                    if config and config.cargo_apoiador_default:
                        role = interaction.guild.get_role(int(config.cargo_apoiador_default))
                        if role and role in member.roles:
                            await member.remove_roles(role)
            except Exception as e:
                logger.error(f"Erro ao remover cargo: {e}")

            embed = discord.Embed(
                title="✅ Apoiador Pausado",
                color=discord.Color.green(),
                description="✅ Apoiador pausado (doações interrompidas)"
            )
            embed.add_field(name="Usuário", value=f"<@{discord_id}>", inline=True)
            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"Apoiador pausado por {interaction.user}: {discord_id}")

        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao executar pausa: {str(e)}", ephemeral=True)
            logger.error(f"Erro ao executar pausa de apoiador: {e}")


class SupporterResumeModal(ui.Modal, title="Continuar Apoiador"):
    usuario = ui.TextInput(
        label="ID do Usuário ou @menção",
        placeholder="123456789 ou @usuario",
        required=True,
        max_length=50
    )

    def __init__(self, role_manager):
        self.role_manager = role_manager
        super().__init__()

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

            description = f"Continuar apoio de <@{discord_id}> (retomar doações)"
            view = ConfirmationView(
                action_description=description,
                confirm_callback=lambda i: self._execute_resume_action(i, discord_id),
            )
            embed = discord.Embed(
                title="⚠️ Confirmar Ação",
                description=f"**Ação:** {description}\n\nClique em **CONFIRMAR** para prosseguir.",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)
            logger.error(f"Erro ao processar continuação de apoiador: {e}")

    async def _execute_resume_action(self, interaction: discord.Interaction, discord_id: str):
        try:
            guild_id = str(interaction.guild.id)
            now = datetime.now(timezone.utc)

            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(Apoiador).where(
                        Apoiador.discord_id == discord_id,
                        Apoiador.guild_id == guild_id
                    )
                )
                apoiador = result.scalars().first()

                if not apoiador:
                    await interaction.followup.send("❌ Apoiador não encontrado.", ephemeral=True)
                    return
                if apoiador.ativo:
                    await interaction.followup.send("❌ Apoiador já está ativo.", ephemeral=True)
                    return

                apoiador.ativo = True
                apoiador.ultimo_pagamento = now
                await session.commit()

            try:
                member = interaction.guild.get_member(int(discord_id))
                if member:
                    await self.role_manager.assign_default_supporter_role(member)
                    await self.role_manager.update_member_time_based_roles(member)
            except Exception as e:
                logger.error(f"Erro ao atualizar cargos: {e}")

            embed = discord.Embed(
                title="✅ Apoiador Reativado",
                color=discord.Color.green(),
                description="✅ Apoiador reativado (doações continuadas)"
            )
            embed.add_field(name="Usuário", value=f"<@{discord_id}>", inline=True)
            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"Apoiador reativado por {interaction.user}: {discord_id}")

        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao executar continuação: {str(e)}", ephemeral=True)
            logger.error(f"Erro ao executar continuação de apoiador: {e}")


class SupporterRemoveModal(ui.Modal, title="Remover Apoiador"):
    usuario = ui.TextInput(
        label="ID do Usuário ou @menção",
        placeholder="123456789 ou @usuario",
        required=True,
        max_length=50
    )

    def __init__(self, role_manager):
        self.role_manager = role_manager
        super().__init__()

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

            description = f"REMOVER COMPLETAMENTE o apoio de <@{discord_id}> do sistema"
            view = ConfirmationView(
                action_description=description,
                confirm_callback=lambda i: self._execute_remove_action(i, discord_id),
            )
            embed = discord.Embed(
                title="⚠️ Confirmar Ação",
                description=f"**Ação:** {description}\n\n**⚠️ ATENÇÃO:** Esta ação não pode ser desfeita!\n\nClique em **CONFIRMAR** para prosseguir.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)
            logger.error(f"Erro ao processar remoção de apoiador: {e}")

    async def _execute_remove_action(self, interaction: discord.Interaction, discord_id: str):
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

                if not apoiador:
                    await interaction.followup.send("❌ Apoiador não encontrado.", ephemeral=True)
                    return

                await session.delete(apoiador)
                await session.commit()

            try:
                member = interaction.guild.get_member(int(discord_id))
                if member:
                    config = await self.role_manager.get_guild_config(guild_id)
                    if config and config.cargo_apoiador_default:
                        role = interaction.guild.get_role(int(config.cargo_apoiador_default))
                        if role and role in member.roles:
                            await member.remove_roles(role)
            except Exception as e:
                logger.error(f"Erro ao remover cargo: {e}")

            embed = discord.Embed(
                title="✅ Apoiador Removido",
                color=discord.Color.green(),
                description="✅ Apoiador removido do sistema"
            )
            embed.add_field(name="Usuário", value=f"<@{discord_id}>", inline=True)
            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"Apoiador removido por {interaction.user}: {discord_id}")

        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao executar remoção: {str(e)}", ephemeral=True)
            logger.error(f"Erro ao executar remoção de apoiador: {e}")


# ==================== VIEWS ====================

class SupporterTimeTypeSelectView(ui.View):
    """View para selecionar se o tempo é retroativo ou antecipado"""
    def __init__(self, role_manager, threshold, tipo_apoio, discord_id, amount_cents=None):
        super().__init__()
        self.role_manager = role_manager
        self.threshold = threshold
        self.tipo_apoio = tipo_apoio
        self.discord_id = discord_id
        self.amount_cents = amount_cents

    @ui.button(label="⏮️ Retroativo", style=discord.ButtonStyle.primary)
    async def select_retroactive(self, interaction: discord.Interaction, button: ui.Button):
        view = SupporterUnitSelectView(
            self.role_manager, self.threshold, self.tipo_apoio,
            self.discord_id, self.amount_cents, time_type="retroative"
        )
        embed = discord.Embed(
            title=f"⏱️ Selecionar Unidade para {self.threshold}+",
            description="Escolha a unidade de tempo para a duração do apoio retroativo.",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @ui.button(label="⏭️ Antecipado", style=discord.ButtonStyle.primary)
    async def select_anticipated(self, interaction: discord.Interaction, button: ui.Button):
        view = SupporterUnitSelectView(
            self.role_manager, self.threshold, self.tipo_apoio,
            self.discord_id, self.amount_cents, time_type="anticipated"
        )
        embed = discord.Embed(
            title=f"⏱️ Selecionar Unidade para {self.threshold}+",
            description="Escolha a unidade de tempo para estender o apoio para o futuro.",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class SupporterUnitSelectView(ui.View):
    def __init__(self, role_manager, threshold, tipo_apoio, discord_id, amount_cents=None, time_type="retroative"):
        super().__init__()
        self.role_manager = role_manager
        self.threshold = threshold
        self.tipo_apoio = tipo_apoio
        self.discord_id = discord_id
        self.amount_cents = amount_cents
        self.time_type = time_type

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
            time_type_display = "retroativo" if self.time_type == "retroative" else "antecipado"
            description = f"Adicionar/estender apoio de <@{self.discord_id}> por {self.threshold} {unit} ({time_type_display}, tipo: {self.tipo_apoio})"

            view = ConfirmationView(
                action_description=description,
                confirm_callback=lambda i: self._execute_add_action(i, self.discord_id, self.threshold, unit, self.tipo_apoio, self.amount_cents, self.time_type),
            )
            embed = discord.Embed(
                title="⚠️ Confirmar Ação",
                description=f"**Ação:** {description}\n\nClique em **CONFIRMAR** para prosseguir.",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)
            logger.error(f"Erro ao selecionar unidade: {e}")

    async def _execute_add_action(self, interaction: discord.Interaction, discord_id: str, threshold: int, unit: str, tipo_apoio: str, amount_cents: int | None = None, time_type: str = "retroative"):
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

                if not apoiador:
                    if time_type == "retroative":
                        data_inicio = now - relativedelta(**{unit: threshold})
                        data_expiracao = now
                        type_display = "retroativo"
                    else:
                        data_inicio = now
                        data_expiracao = now + relativedelta(**{unit: threshold})
                        type_display = "antecipado"

                    apoiador = Apoiador(
                        discord_id=discord_id,
                        guild_id=guild_id,
                        data_inicio=data_inicio,
                        data_expiracao=data_expiracao,
                        valor_doacao=amount_cents or 0,
                        data_pagamento=now if amount_cents is not None else None,
                        tipo_apoio=tipo_apoio,
                        ativo=True,
                        ultimo_pagamento=now,
                        nivel=1
                    )
                    session.add(apoiador)
                    message = f"✅ Novo apoiador adicionado com {threshold} {unit} de apoio {type_display}"
                    if amount_cents is not None:
                        message += f" | Valor informado: R$ {amount_cents / 100:.2f}"
                else:
                    if apoiador.ativo:
                        if time_type == "retroative":
                            if apoiador.data_inicio:
                                apoiador.data_inicio -= relativedelta(**{unit: threshold})
                            type_display = "retroativo"
                        else:
                            if apoiador.data_expiracao:
                                apoiador.data_expiracao += relativedelta(**{unit: threshold})
                            else:
                                apoiador.data_expiracao = now + relativedelta(**{unit: threshold})
                            type_display = "antecipado"

                        if amount_cents is not None:
                            apoiador.valor_doacao = (apoiador.valor_doacao or 0) + amount_cents
                            apoiador.data_pagamento = now
                        message = f"✅ Apoio estendido por mais {threshold} {unit} ({type_display})"
                        if amount_cents is not None:
                            message += f" | Valor informado: R$ {amount_cents / 100:.2f}"
                    else:
                        apoiador.ativo = True
                        if time_type == "retroative":
                            apoiador.data_inicio = now - relativedelta(**{unit: threshold})
                            apoiador.data_expiracao = now
                            type_display = "retroativo"
                        else:
                            apoiador.data_inicio = now
                            apoiador.data_expiracao = now + relativedelta(**{unit: threshold})
                            type_display = "antecipado"

                        apoiador.duracao_meses = threshold
                        apoiador.ultimo_pagamento = now
                        if amount_cents is not None:
                            apoiador.valor_doacao = (apoiador.valor_doacao or 0) + amount_cents
                            apoiador.data_pagamento = now
                        message = f"✅ Apoiador reativado e apoio estendido por {threshold} {unit} ({type_display})"
                        if amount_cents is not None:
                            message += f" | Valor informado: R$ {amount_cents / 100:.2f}"

                await session.commit()

            try:
                member = interaction.guild.get_member(int(discord_id))
                if member:
                    await self.role_manager.assign_default_supporter_role(member)
                    await self.role_manager.update_member_time_based_roles(member)
            except Exception as e:
                logger.error(f"Erro ao atualizar cargos: {e}")

            embed = discord.Embed(
                title="✅ Apoiador Adicionado/Estendido",
                color=discord.Color.green(),
                description=message
            )
            embed.add_field(name="Usuário", value=f"<@{discord_id}>", inline=True)
            embed.add_field(name="Duração Adicionada", value=f"{threshold} {unit}", inline=True)
            embed.add_field(name="Tipo de Tempo", value="⏮️ Retroativo" if time_type == "retroative" else "⏭️ Antecipado", inline=True)
            embed.add_field(name="Tipo de Apoio", value=tipo_apoio, inline=True)
            if amount_cents is not None:
                embed.add_field(name="Valor Informado", value=f"R$ {amount_cents / 100:.2f}", inline=True)

            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"Apoiador adicionado/estendido por {interaction.user}: {discord_id} - {threshold} {unit} ({time_type})")

        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao executar ação: {str(e)}", ephemeral=True)
            logger.error(f"Erro ao executar ação de apoiador: {e}")


class ManageSupporterActionView(ui.View):
    def __init__(self, role_manager):
        super().__init__()
        self.role_manager = role_manager

    @ui.button(label="➕ Adicionar", style=discord.ButtonStyle.success)
    async def add_supporter(self, interaction: discord.Interaction, button: ui.Button):
        if not check_is_owner(interaction):
            await interaction.response.send_message("❌ Apenas admins podem usar essa função!", ephemeral=True)
            return
        await interaction.response.send_modal(SupporterActionModal(self.role_manager))

    @ui.button(label="⏸️ Pausar", style=discord.ButtonStyle.secondary)
    async def pause_supporter(self, interaction: discord.Interaction, button: ui.Button):
        if not check_is_owner(interaction):
            await interaction.response.send_message("❌ Apenas admins podem usar essa função!", ephemeral=True)
            return
        await interaction.response.send_modal(SupporterPauseModal(self.role_manager))

    @ui.button(label="▶️ Continuar", style=discord.ButtonStyle.primary)
    async def continue_supporter(self, interaction: discord.Interaction, button: ui.Button):
        if not check_is_owner(interaction):
            await interaction.response.send_message("❌ Apenas admins podem usar essa função!", ephemeral=True)
            return
        await interaction.response.send_modal(SupporterResumeModal(self.role_manager))

    @ui.button(label="🗑️ Remover", style=discord.ButtonStyle.danger)
    async def remove_supporter(self, interaction: discord.Interaction, button: ui.Button):
        if not check_is_owner(interaction):
            await interaction.response.send_message("❌ Apenas admins podem usar essa função!", ephemeral=True)
            return
        await interaction.response.send_modal(SupporterRemoveModal(self.role_manager))


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
