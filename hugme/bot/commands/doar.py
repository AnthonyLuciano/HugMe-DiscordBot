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
    email = TextInput(
        label="Seu Email",
        placeholder="email@exemplo.com",
        required=True
    )
    phone = TextInput(
        label="Teleone (Com DDD)",
        placeholder="11999999999",
        required=True,
        min_length=11,
        max_length=11,
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = float(self.amount.value)
            method = self.method.value.lower()
            phone = self.phone.value
            email = self.email.value

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
                    "email": email,
                    "tax_id": "12345678909",
                    "phones": [
                        {
                            "country": "55",
                            "area": phone[:2],
                            "number": phone[2:],
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


class DoarView(View):
    def __init__(self, bot):
        super().__init__(timeout=180)
        self.bot = bot
        self.ngrok_url = os.getenv('REDIRECT_URL')

    @discord.ui.button(label="Pix", style=discord.ButtonStyle.green, custom_id="doar_pix")
    async def doar_pix_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(DonationModal())

    @discord.ui.button(label="Cartão", style=discord.ButtonStyle.blurple, custom_id="doar_cartao", disabled=False)
    async def doar_cartao_button(self, interaction: discord.Interaction, button: Button):
        try:
            checkout_data = {
                "reference_id": f"card_checkout_{interaction.user.id}",
                "customer": {
                    "name": str(interaction.user),
                    "email": f"{interaction.user.id}@temp.com",
                    "tax_id": "12345678909"
                },
                "items": [{
                    "reference_id": "doacao_001",
                    "name": "Doação Discord",
                    "quantity": 1,
                    "unit_amount": 1000
                }],
                "payment_methods": [{
                    "type": "CREDIT_CARD",
                    "brands": ["VISA", "MASTERCARD"]
                }],
                "redirect_url": f"{self.ngrok_url}/obrigado",
                "notification_urls": [f"{self.ngrok_url}/webhook"]
            }

            headers = {
                "Authorization": f"Bearer {os.getenv('PAGBANK_API_KEY')}",
                "Content-Type": "application/json",
                "x-api-version": "4.0"
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{os.getenv('PAGBANK_ENDPOINT')}/checkouts",
                    json=checkout_data,
                    headers=headers
                )

                logger.info(f"Request: {checkout_data}")
                logger.info(f"Response: {response.text}")

                response.raise_for_status()
                checkout_info = response.json()

                payment_url = next(
                    (link['href'] for link in checkout_info['links'] if link['rel'] == 'PAY'),
                    None
                )

                if not payment_url:
                    raise ValueError("URL de pagamento não encontrada na resposta")

            embed = discord.Embed(
                title="💳 Doação com Cartão",
                description="Clique no botão abaixo para finalizar seu pagamento:",
                color=0x3498db
            )
            embed.set_footer(text="Você será redirecionado para o PagBank.")

            class PagamentoView(View):
                def __init__(self, url: str):
                    super().__init__(timeout=None)
                    self.add_item(Button(
                        label="Finalizar Pagamento",
                        style=discord.ButtonStyle.link,
                        url=url
                    ))

            view = PagamentoView(payment_url)

            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        except httpx.HTTPStatusError as e:
            logger.error(f"Erro HTTP: {e.response.text}")
            await interaction.response.send_message(
                f"❌ Erro no PagBank: {e.response.json().get('error_message', 'Verifique os logs')}",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Erro geral: {str(e)}", exc_info=True)
            await interaction.response.send_message(
                "❌ Erro interno ao processar pagamento",
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
            await ctx.send(embed=embed, view=view)
        except discord.Forbidden:
            await ctx.send("❌ Não foi possível exibir os botões. Verifique suas permissões!", ephemeral=True)

# --- Setup ---
async def setup(bot):
    await bot.add_cog(DoarCommands(bot))
