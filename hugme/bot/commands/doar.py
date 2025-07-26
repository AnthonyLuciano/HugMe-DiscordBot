import discord
import logging
import os
import httpx
from datetime import datetime, timedelta, timezone
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput

logger = logging.getLogger(__name__)

# --- Modal de Doação (Formulário Pix) ---
class DonationModal(Modal, title="Fazer Doação via Pix"):
    amount = TextInput(
        label="Valor da Doação (R$)",
        placeholder="Ex: 10.00",
        required=True
    )
    method = TextInput(
        label="Método de Pagamento (Digite 'Pix')",
        placeholder="Pix",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = float(self.amount.value)
            method = self.method.value.lower()

            if method != "pix":
                await interaction.response.send_message(
                    "⚠️ Atualmente só aceitamos doações via **Pix**.",
                    ephemeral=True
                )
                return

            reference_id = f"doacao_discord_user_{interaction.user.id}"
            amount_cents = int(amount * 100)
            brasilia_offset = timedelta(hours=-3)
            brasilia_tz = timezone(brasilia_offset)
            expiration = (datetime.now(brasilia_tz) + timedelta(days=180)).isoformat()


            payment_data = {
                "reference_id": reference_id,
                "customer": {
                    "name": str(interaction.user),
                    "email": f"{interaction.user.id}@example.com",
                    "tax_id": "12345678909",
                    "phones": [
                        {
                            "country": "55",
                            "area": "11",
                            "number": "999999999",
                            "type": "MOBILE"
                        }
                    ]
                },
                "items": [
                    {
                        "reference_id": "doacao_item_001",
                        "name": "Doação Discord",
                        "quantity": 1,
                        "unit_amount": amount_cents
                    }
                ],
                "qr_codes": [
                    {
                        "amount": {
                            "value": amount_cents
                        },
                        "expiration_date": expiration
                    }
                ],
                "notification_urls": [
                    "https://seusite.com/pagbank-webhook"
                ]
            }

            headers = {
                "Authorization": f"Bearer {os.getenv('PAGBANK_API_KEY')}",
                "Content-Type": "application/json"
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{os.getenv('PAGBANK_ENDPOINT')}/orders",
                    json=payment_data,
                    headers=headers
                )
                response.raise_for_status()
                payment_info = response.json()

            # Pega o QR Code
            qr_code_url = payment_info["qr_codes"][0]["links"][0]["href"]
            text_key = payment_info["qr_codes"][0]["text"]

            embed = discord.Embed(
                title=f"💰 Doação de R${amount:.2f} via PIX",
                description="Escaneie o QR Code ou copie o código abaixo:",
                color=0x32CD32
            )
            embed.add_field(name="Valor", value=f"R$ {amount:.2f}", inline=True)
            embed.add_field(name="Copia e Cola", value=f"`{text_key}`", inline=False)
            embed.set_image(url=qr_code_url)

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Erro ao processar doação: {e}")
            await interaction.response.send_message(
                "❌ Ocorreu um erro ao processar sua doação. Tente novamente mais tarde.",
                ephemeral=True
            )


# --- View com Botões ---
class DoarView(View):
    def __init__(self, bot):
        super().__init__(timeout=180)
        self.bot = bot

    @discord.ui.button(label="Pix", style=discord.ButtonStyle.green, custom_id="doar_pix")
    async def doar_pix_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(DonationModal())

    @discord.ui.button(label="Cartão (em breve)", style=discord.ButtonStyle.gray, custom_id="doar_cartao", disabled=True)
    async def doar_cartao_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message(
            "💳 Doações com cartão estarão disponíveis em breve!",
            ephemeral=True
        )

# --- Comando /doar ---
class DoarCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="doar", description="Inicie o processo de doação para a comunidade")
    async def doar(self, ctx: commands.Context):
        try:
            embed = discord.Embed(
                title="💖 Apoie Nossa Comunidade!",
                description=(
                    "Escolha a forma de doação:\n\n"
                    "💰 **Pix**: Doação única ou recorrente.\n"
                    "💳 **Cartão**: Doação mensal recorrente via PagBank.\n\n"
                    "Clique nos botões abaixo para mais informações."
                ),
                color=discord.Color.green()
            )
            view = DoarView(self.bot)
            await ctx.send(embed=embed, view=view, ephemeral=True)
        except discord.Forbidden:
            await ctx.send("❌ Não foi possível exibir os botões. Verifique suas permissões!", ephemeral=True)

# --- Setup ---
async def setup(bot):
    await bot.add_cog(DoarCommands(bot))
