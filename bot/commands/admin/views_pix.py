import logging
import discord
from discord import ui
from sqlalchemy import select

from bot.database import AsyncSessionLocal
from bot.database.models import PixConfig
from .modals_pix import SetQRCodeModal
from .views_base import ConfirmationView

logger = logging.getLogger(__name__)


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
