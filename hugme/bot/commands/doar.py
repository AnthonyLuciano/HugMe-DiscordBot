import re, discord, logging, os, httpx
from bot.database import SessionLocal
from bot.database.models import Apoiador
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta, timezone
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput

logger = logging.getLogger(__name__)

# --- Modal de Doação (Formulário Pix) ---
class DonationModal(Modal, title="Fazer Doação via Pix"):
    def __init__(self):
        super().__init__(
            custom_id="pix_donation_modal",
            timeout=30.0
        )
        self.ngrok_url = os.getenv('REDIRECT_URL')
        
    amount = TextInput(
        label="Valor da Doação (R$)",
        placeholder="Ex: 10.00",
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
    cpf = TextInput(
        label="CPF",
        placeholder="12345678909",
        required=True,
        min_length=11,
        max_length=11
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = float(self.amount.value)
            phone = self.phone.value
            email = self.email.value
            cpf = self.cpf.value

            reference_id = f"doacao_discord_user_{interaction.user.id}"
            amount_cents = int(amount * 100)
            guild_id = str(interaction.guild.id) if interaction.guild else "0"
            
            with SessionLocal() as session:
                apoiador = Apoiador(
                    discord_id=str(interaction.user.id),
                    guild_id=guild_id,
                    id_pagamento=reference_id,
                    tipo_apoio="pix",
                    email_doador=email,
                    cpf_doador=cpf,
                    telefone_doador=phone,
                    valor_doacao=amount_cents,
                    data_inicio=datetime.now(timezone.utc)
                )
                session.add(apoiador)
                try:
                    session.commit()
                except IntegrityError:
                    session.rollback()
                    apoiador = session.query(Apoiador).filter_by(
                        discord_id=str(interaction.user.id),
                        guild_id=str(interaction.guild.id)
                    ).first
                    if apoiador:
                        apoiador.id_pagamento = reference_id
                        session.commit()
            brasilia_offset = timedelta(hours=-3)
            brasilia_tz = timezone(brasilia_offset)
            expiration = (datetime.now(brasilia_tz) + timedelta(days=180)).isoformat()
            
            payment_data = {
                "reference_id": reference_id,
                "description": "Apoio Voluntário à Comunidade",
                "qr_codes": [{
                    "amount": {
                        "value": amount_cents,
                        "currency": "BRL"
                    },
                    "expiration_date": expiration
                }],
                "notification_urls": [f"{self.ngrok_url}/pagbank-webhook"],
                "customer": {
                    "name": str(interaction.user),
                    "email": email,
                    "tax_id": cpf,
                    "phones": [{
                        "country": "55",
                        "area": phone[:2],
                        "number": phone[2:],
                        "type": "MOBILE"
                    }]
                },
                "metadata": {
                    "transaction_type": "donation",
                    "platform": "discord_community"
                }
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

    @discord.ui.button(label="☕ Doar via Ko-fi", style=discord.ButtonStyle.secondary, custom_id="doar_kofi")
    async def doar_kofi_button(self, interaction: discord.Interaction, button: Button):
        # Embed de aviso antes de redirecionar
        embed = discord.Embed(
            title="☕ Doação via Ko-fi",
            description=(
                "Obrigado por considerar doar via Ko-fi!\n\n"
                "**⚠️Antes de prosseguir⚠️:**\n"
                "Quando for Doar, Coloque o seu nome de usuario do discord\n"   
                "Caso contrario tera que ser feito verificação manual\n"
                "- Visite o link abaixo para continuar.\n\n"
                "[Clique aqui para doar no Ko-fi](https://ko-fi.com/W7W81J60WA)"
            ),
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)



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
                    "☕ **kofi**: Doação mensal unica ou recorrente via Ko-fi.\n\n"
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
