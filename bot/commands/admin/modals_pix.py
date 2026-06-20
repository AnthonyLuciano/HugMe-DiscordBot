import logging
import discord
from discord import ui
from sqlalchemy import select

from bot.database import AsyncSessionLocal
from bot.database.models import PixConfig
from .views_base import ConfirmationView

logger = logging.getLogger(__name__)


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
