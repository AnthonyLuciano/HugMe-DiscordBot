import json
import re, discord, logging, os, httpx
from bot.config import Config as app_config
from bot.database import SessionLocal
from bot.database.models import Apoiador, PixConfig
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta, timezone
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput

logger = logging.getLogger(__name__)

# --- Modal de Doação (Formulário Pix) ---
class DonationModal(Modal, title="Fazer Doação via Pix"):
    def __init__(self, bot):
        super().__init__(
            custom_id="pix_donation_modal",
            timeout=180.0
        )
        self.bot = bot
        self.redirect = os.getenv('REDIRECT_URL')
        
    amount = TextInput(
        label="Valor da Doação Esperada <3 (R$)",
        placeholder="Ex: 10.00",
        required=True
    )
   

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = float(self.amount.value)

            reference_id = f"doacao_discord_user_{interaction.user.id}"
            amount_cents = int(amount * 100)
            guild_id = str(interaction.guild.id) if interaction.guild else "0"
            
            with SessionLocal() as session:
                apoiador = Apoiador(
                    discord_id=str(interaction.user.id),
                    guild_id=guild_id,
                    id_pagamento=reference_id,
                    tipo_apoio="pix",
                    valor_doacao=amount_cents,
                    data_inicio=datetime.now(timezone.utc),
                    ja_pago=False
                )
                session.add(apoiador)
                try:
                    session.commit()
                except IntegrityError:
                    session.rollback()
                    apoiador = session.query(Apoiador).filter_by(
                        discord_id=str(interaction.user.id),
                        guild_id=guild_id
                    ).first()
                    if apoiador:
                        apoiador.id_pagamento = reference_id
                        session.commit()
            brasilia_offset = timedelta(hours=-3)
            brasilia_tz = timezone(brasilia_offset)
            expiration = (datetime.now(brasilia_tz) + timedelta(days=180)).isoformat()
            
            with SessionLocal() as session:
                config = session.query(PixConfig).first()
                if not config:
                    raise ValueError("Configuração PIX não encontrada no banco de dados.")
                chave = config.chave
                image_url = config.static_qr_url
                if not image_url:
                    raise ValueError("URL do QR Code PIX não configurada.")
                if not chave:
                    raise ValueError("Chave PIX não configurada.")

            embed = discord.Embed(
                title=f"💰 Doação de R${amount:.2f} via PIX",
                description="Escaneie o QR Code ou copie o código abaixo:",
                color=0x32CD32
            )
            embed.add_field(name="Valor", value=f"R$ {amount:.2f}", inline=True)
            embed.add_field(name="Copia e Cola", value=f"`{chave}`", inline=False)
            embed.set_image(url=image_url)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            await interaction.followup.send(
                "⏳ Atenção: sua doação pode levar alguns minutos para ser processada. "
                "Obrigado pelo apoio! 🤗",
                ephemeral=True
                )

            
            channel_id = app_config.DONO_LOG_CHANNEL
            donolog = await self.bot.fetch_channel(channel_id)
            
            if donolog:
                view = View(timeout=None)
                view.add_item(Button(
                    style=discord.ButtonStyle.success,
                    label="Sim (Confirmar Pagamento)",
                    custom_id=f"confirm_payment_{reference_id}"
                ))
                view.add_item(Button(
                    style=discord.ButtonStyle.danger,
                    label="Não",
                    custom_id=f"reject_payment_{reference_id}"
                ))
                
                notification_embed = discord.Embed(
                    title="📊 Nova Doação Recebida",
                    description=f"**Usuário:** {interaction.user.mention} (`{interaction.user.id}`)\n"
                    f"**Valor:** R${amount:.2f} \n\n",
                    color=0x00FF00
                )
                await donolog.send(
                    content="Nova doação registrada!",
                    embeds=[notification_embed],
                    view=view
                )
        except Exception as e:
            logger.error(f"Erro ao processar doação: {e}")
            await interaction.response.send_message(
                "❌ Ocorreu um erro ao processar sua doação. Tente novamente mais tarde.",
                ephemeral=True
            )

class DMConfirmationView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=180.0)
        self.bot = bot

    @discord.ui.button(label="Sim, Continuar", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Mostra o mesmo embed de opções que seria exibido em servidores
        embed = discord.Embed(
            title="💖 Apoie Nossa Comunidade!",
            description=(
                "Escolha a forma de doação:\n\n"
                "💰 **Pix**: Doação única ou recorrente.\n"
                "☕ **Ko-fi**: Doação mensal via cartão.\n\n"
                "Clique nos botões abaixo para mais informações."
            ),
            color=discord.Color.green()
        )
        view = DoarView(self.bot)  # View normal com botões PIX/Ko-fi
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="❌ Doação cancelada.",
            view=None,
            embed=None,
            ephemeral = True
        )
    
class DoarView(View):
    def __init__(self, bot):
        super().__init__(timeout=180)
        self.bot = bot
        self.ngrok_url = os.getenv('REDIRECT_URL')

    @discord.ui.button(label="Pix", style=discord.ButtonStyle.green, custom_id="doar_pix")
    async def doar_pix_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(DonationModal(bot=self.bot))

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

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.data or "custom_id" not in interaction.data:
            return
        custom_id = interaction.data["custom_id"]
        if custom_id.startswith("confirm_payment_"):
            reference_id = custom_id.replace("confirm_payment_", "")
            await interaction.response.send_message(
                f"✅ Pagamento confirmado para referência {reference_id}",
                ephemeral=True
                )
        elif custom_id.startswith("reject_payment_"):
            reference_id = custom_id.split("_")[2]
            await interaction.response.send_message(
                f"❌ Pagamento rejeitado para referência {reference_id}",
                ephemeral=True
            )
            
            
    @commands.hybrid_command(name="doar", description="Inicie o processo de doação para a comunidade")
    async def doar(self, ctx: commands.Context):
        try:
            if not ctx.author:
                raise ValueError("Contexto inválido - author ausente")
            
            if not ctx.guild:
                embed = discord.Embed(
                    title="⚠️ Doação via Mensagem Direta",
                    description=(
                        "Doações em DMs **não concedem recompensas** em servidores.\n"
                        "Caso deseje tais recompenças use o comando no servidor \n"
                        "Ou notifique um Admin ou o Desenvolvedor no servidor de sua doação\n -MrMedicMain(dev)\n\n"
                        "**Deseja continuar mesmo assim?**"
                    ),
                    color=discord.Color.orange()
                )
                view = DMConfirmationView(self.bot)
                await ctx.send(embed=embed, view=view, ephemeral = True)
                return


            embed = discord.Embed(
                title="💖 Apoie Nossa Comunidade!",
                description=(
                    "Escolha a forma de doação:\n\n"
                    "💰 **Pix**: Doação única ou recorrente.\n"
                    "☕ **Ko-fi**: Doação mensal via cartão.\n\n"
                    "Clique nos botões abaixo para mais informações."
                ),
                color=discord.Color.green()
            )
        
            view = DoarView(self.bot)
            await ctx.send(embed=embed, view=view, ephemeral = True)

        except discord.Forbidden:
            await ctx.send("❌ Sem permissões para enviar mensagens aqui!", ephemeral=True)
        except AttributeError as e:
            logger.error(f"Erro de atributo no comando doar: {str(e)}")
            await ctx.send("❌ Ocorreu um erro interno. Tente novamente mais tarde.", ephemeral=True)
        except Exception as e:
            logger.error(f"Erro inesperado em doar: {str(e)}", exc_info=True)
            await ctx.send("❌ Falha ao processar o comando. Notifique os administradores.", ephemeral=True)
# --- Setup ---
async def setup(bot):
    await bot.add_cog(DoarCommands(bot))