import logging
import discord
from discord import ui

logger = logging.getLogger(__name__)


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
