import asyncio
import json
import re, discord, logging, os, httpx
from bot.servicos.SupporterRoleManager import SupporterRoleManager
from bot.servicos.VerificacaoMembro import VerificacaoMembro
from bot.config import Config as app_config
from bot.database import SessionLocal
from bot.database.models import Apoiador, PixConfig
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta, timezone
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
from discord.utils import sleep_until

logger = logging.getLogger(__name__)

# --- Função utilitária para pegar hora de Brasília ---
def get_brasilia_time():
    brasilia_offset = timedelta(hours=-3)
    brasilia_tz = timezone(brasilia_offset)
    return datetime.now(brasilia_tz)

# --- Função para desabilitar botões de admin ---
async def disable_admin_buttons(message: discord.Message):
    if not message.components:
        return
    view = View(timeout=None)
    for row in message.components:
        for button in row.children:
            new_button = Button(
            style = button.style,
            label = button.label,
            custom_id=button.custom_id,
            disabled=True
            )
            view.add_item(new_button)
    await message.edit(view=view)

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
            # --- Validação do valor ---
            try:
                amount = float(self.amount.value)
            except ValueError:
                await interaction.response.send_message(
                    "❌ Valor inválido. Por favor, insira um número válido.",
                    ephemeral=True
                )
                return

            reference_id = f"doacao_discord_user_{interaction.user.id}"
            amount_cents = int(amount * 100)
            guild_id = str(interaction.guild.id) if interaction.guild else "0"

            # --- Salva ou atualiza no banco ---
            with SessionLocal() as session:
                try:
                    apoiador = session.query(Apoiador).filter_by(
                        discord_id=str(interaction.user.id),
                        guild_id=guild_id
                    ).first()
                    
                    if apoiador:
                        # Atualiza apenas o id_pagamento e dados
                        apoiador.id_pagamento = reference_id
                        apoiador.tipo_apoio = "pix"
                        apoiador.valor_doacao = amount_cents
                        apoiador.data_inicio = datetime.now(timezone.utc)
                        apoiador.ja_pago = False
                    else:
                        # Cria novo registro
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

                    session.commit()
                except Exception as e:
                    session.rollback()
                    logger.error(f"Erro ao salvar doação no banco: {e}")
                    await interaction.response.send_message(
                        "❌ Erro ao registrar a doação. Tente novamente mais tarde.",
                        ephemeral=True
                    )
                    return

            # --- Busca configuração PIX ---
            with SessionLocal() as session:
                config = session.query(PixConfig).first()
                if not config:
                    await interaction.response.send_message(
                        "❌ Configuração PIX não encontrada.",
                        ephemeral=True
                    )
                    return
                chave = config.chave
                image_url = config.static_qr_url

            # --- Envia embed pro usuário ---
            embed = discord.Embed(
                title=f"💰 Doação de R${amount:.2f} via PIX",
                description="Escaneie o QR Code ou copie o código abaixo:",
                color=0x32CD32
            )
            embed.add_field(name="Valor", value=f"R$ {amount:.2f}", inline=True)
            embed.add_field(name="Copia e Cola", value=f"`{chave}`", inline=False)
            embed.set_image(url=image_url)

            # Footer pro usuário e timer de auto rejeição
            timeout = get_brasilia_time() + timedelta(minutes=5)
            restante = timeout - get_brasilia_time()
            mins, segs = divmod(int(restante.total_seconds()), 60)
            embed.set_footer(text=f"⏳ Confirmação Manual pendente | Tempo restante: {mins}m {segs}s")

            user_view = View(timeout=None)
            user_view.add_item(Button(
                style=discord.ButtonStyle.success,
                label="já paguei",
                custom_id=f"user_paid_{reference_id}"))
            user_view.add_item(Button(
                style=discord.ButtonStyle.danger,
                label="Cancelar Doação",
                custom_id=f"user_cancel_{reference_id}"))

            try:
                dm_channel = await interaction.user.create_dm()
                bot_message = await dm_channel.send(embed=embed, view=user_view)
                user_message = None
                await interaction.response.send_message(
                    "✅ Verifique sua DM para completar a doação.", ephemeral=True
                )
            except discord.Forbidden:
                await interaction.response.send_message(embed=embed, view=user_view, ephemeral=True)
                bot_message = None
                user_message = await interaction.original_response()

            # --- Auto-delete das mensagens após X minutos ---
            async def autodelete(bot_msg: discord.Message, user_msg: discord.Message, delay_minutos: int = 10):
                delete_time = get_brasilia_time() + timedelta(minutes=delay_minutos)
                while True:
                    if get_brasilia_time() >= delete_time:
                        for msg in (bot_msg, user_msg):
                            if msg is None:
                                continue
                            try:
                                await msg.delete()
                            except (discord.NotFound, discord.Forbidden):
                                pass
                        break
                    await asyncio.sleep(5)
            asyncio.create_task(autodelete(user_message, bot_message))

            # --- Inicia timer de rejeição automática ---
            doar_cog = self.bot.get_cog("DoarCommands")
            msg_para_timer = bot_message or user_message
            if doar_cog:
                asyncio.create_task(doar_cog.update_timer_embed(
                    message=msg_para_timer,
                    reference_id=reference_id,
                    timeout=timeout
                ))

            # --- Notifica admins ---
            channel_id = app_config.DONO_LOG_CHANNEL
            donolog = await self.bot.fetch_channel(channel_id)
            if donolog:
                view = View(timeout=None)
                view.add_item(Button(
                    style=discord.ButtonStyle.success,
                    label="Confirmar Pagamento",
                    custom_id=f"confirm_payment_{reference_id}"
                ))
                view.add_item(Button(
                    style=discord.ButtonStyle.danger,
                    label="Rejeitar Pagamento",
                    custom_id=f"reject_payment_{reference_id}"
                ))

                notification_embed = discord.Embed(
                    title="📊 Nova Doação Recebida",
                    description=f"**Usuário:** {interaction.user.mention} (`{interaction.user.id}`)\n**Valor:** R${amount:.2f}\n\n",
                    color=0x00FF00
                )
                admin_msg = await donolog.send(
                    content="Nova doação registrada!",
                    embeds=[notification_embed],
                    view=view
                )
                if doar_cog:
                    # Salva a mensagem do admin para manipulação futura
                    doar_cog.admin_messages[reference_id] = admin_msg

        except Exception as e:
            logger.error(f"Erro ao processar doação: {e}")
            await interaction.response.send_message(
                "❌ Ocorreu um erro ao processar sua doação. Tente novamente mais tarde.",
                ephemeral=True
            )


# --- Views para DM ---
class DMConfirmationView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=180.0)
        self.bot = bot

    @discord.ui.button(label="Sim, Continuar", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
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
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="❌ Doação cancelada.",
            view=None,
            embed=None,
            ephemeral=True
        )


# --- View principal de doações ---
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
        embed = discord.Embed(
            title="☕ Doação via Ko-fi",
            description=(
                "Obrigado por considerar doar via Ko-fi!\n\n"
                "**⚠️Antes de prosseguir⚠️:**\n"
                "Quando for Doar, coloque o seu nome de usuário do Discord.\n"
                "Caso contrário, será feita verificação manual.\n"
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
        self.timer_tasks = {}
        self.admin_messages = {}
        self.verificador = VerificacaoMembro(bot)
        self.role_manager = SupporterRoleManager(bot)

    async def update_timer_embed(self, message: discord.Message, reference_id: str, timeout: datetime):
        try:
            if not message.embeds:
                return

            embed = message.embeds[0]
            
            async def timer_task():
                try:
                    while True:
                        remaining = timeout - get_brasilia_time()
                        total_secs = int(remaining.total_seconds())
                
                        if total_secs <= 0:
                            embed.set_footer(text="⌛ Pagamento não confirmado (expirado)")
                            await message.edit(embeds=[embed], view=None)
                            break
                
                        mins, secs = divmod(total_secs, 60)
                        embed.set_footer(text=f"⏳ Confirmação pendente | Tempo restante: {mins}m {secs}s")
                        await message.edit(embeds=[embed])
                        await asyncio.sleep(5)
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.info(f"erro no timer task: {e}")
                finally:
                    if reference_id in self.timer_tasks:
                        del self.timer_tasks[reference_id]
                        
            task = asyncio.create_task(timer_task())
            self.timer_tasks[reference_id] = task
                
        except Exception as e:
            logger.error(f"Erro no timer embed: {e}")
            if reference_id in self.timer_tasks:
                del self.timer_tasks[reference_id]

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.data or "custom_id" not in interaction.data:
            return

        custom_id = interaction.data["custom_id"]

        # --- Usuário já pagou ---
        if custom_id.startswith("user_paid_"):
            reference_id = custom_id.replace("user_paid_", "")
            await interaction.response.send_message(
                "✅ Obrigado pelo pagamento! Aguarde a confirmação dos administradores.",
                ephemeral=True
            )

        # --- Usuário cancelou ---
        elif custom_id.startswith("user_cancel_"):
            reference_id = custom_id.replace("user_cancel_", "")
            if reference_id in self.timer_tasks:
                self.timer_tasks[reference_id].cancel()
            
            await interaction.response.edit_message(
                content="❌ Doação cancelada pelo usuário.",
                view=None,
                embed=None
            )
            admin_msg = self.admin_messages.get(reference_id)
            if admin_msg:
                await disable_admin_buttons(admin_msg)

        # --- Admin confirma pagamento ---
        if custom_id.startswith("confirm_payment_"):
            reference_id = custom_id.replace("confirm_payment_", "")
            message = interaction.message
            if reference_id in self.timer_tasks:
                self.timer_tasks[reference_id].cancel()
            
            embed = message.embeds[0]
            embed.set_footer(text="✅ Pagamento confirmado")
            await message.edit(embeds=[embed], view=None)

            with SessionLocal() as session:
                apoiador = session.query(Apoiador).filter_by(id_pagamento=reference_id).first()
                if apoiador:
                    apoiador.ja_pago = True
                    apoiador.ultimo_pagamento = get_brasilia_time()
                    session.commit()

                    # Atribui cargo padrão de apoiador
                    logger.info(f"Atribuindo cargo padrão para {apoiador.discord_id} no servidor {apoiador.guild_id}")
                    guild = self.bot.get_guild(int(apoiador.guild_id))
                    if guild:
                        member = guild.get_member(int(apoiador.discord_id))
                        if member:
                            # Atribui cargo padrão
                            default_assigned = await self.role_manager.assign_default_supporter_role(member)
                            # Atualiza cargos baseados no tempo
                            time_updated = await self.role_manager.update_member_time_based_roles(member)

                            if default_assigned or time_updated:
                                logger.info(f"Cargos atribuídos/atualizados para {apoiador.discord_id}")
                            else:
                                logger.info(f"Nenhum cargo novo necessário para {apoiador.discord_id}")
                        else:
                            logger.error(f"Membro {apoiador.discord_id} não encontrado no servidor {apoiador.guild_id}")
                    else:
                        logger.error(f"Servidor {apoiador.guild_id} não encontrado")
            admin_msg = self.admin_messages.get(reference_id)
            if admin_msg:
                await disable_admin_buttons(admin_msg)

            await interaction.response.send_message(
                f"✅ Pagamento confirmado para referência {reference_id}",
                ephemeral=True
            )

        # --- Admin rejeita pagamento ---
        elif custom_id.startswith("reject_payment_"):
            reference_id = custom_id.replace("reject_payment_", "")
            embed = interaction.message.embeds[0]
            embed.set_footer(text="❌ Pagamento rejeitado")
            if reference_id in self.timer_tasks:
                self.timer_tasks[reference_id].cancel()
            await interaction.message.edit(embeds=[embed], view=None)

            admin_msg = self.admin_messages.get(reference_id)
            if admin_msg:
                await disable_admin_buttons(admin_msg)

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
                        "Caso deseje tais recompensas use o comando no servidor.\n"
                        "Ou notifique um Admin ou o Desenvolvedor no servidor de sua doação.\n\n"
                        "**Deseja continuar mesmo assim?**"
                    ),
                    color=discord.Color.orange()
                )
                view = DMConfirmationView(self.bot)
                await ctx.send(embed=embed, view=view, ephemeral=True)
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
            await ctx.send(embed=embed, view=view, ephemeral=True)

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