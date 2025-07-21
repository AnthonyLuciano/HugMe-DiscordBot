import discord, logging
from discord.ext import commands
from discord.ui import Button, View

logger = logging.getLogger(__name__)

class DoarView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Pix", style=discord.ButtonStyle.primary, emoji="💰")
    async def pix_button(self, interaction: discord.Interaction, button: Button):
        try:
            qrcode_url = await self.bot.db.criar_qrcode_pix(
                valor=10.00,
                descricao="Doação para comunidade"
            )

            embed = discord.Embed(
                title="📌 Doação via PIX",
                description="Escaneie o QR Code abaixo ou use a chave PIX cadastrada",
                color=0x32CD32
            )
            embed.set_image(url=qrcode_url)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Erro ao gerar QR Code: {e}")
            await interaction.response.send_message(
                "❌ Erro ao gerar QR Code. Tente novamente mais tarde.",
                ephemeral=True
            )
    @discord.ui.button(label="Cartão", style=discord.ButtonStyle.primary, emoji="💳")
    async def cartao_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message(
            "📌 **Doação via Cartão (PayPal)**\n"
            "Você pode fazer uma doação recorrente mensal com cartão de crédito.\n"
            "Acesse o link abaixo para assinar:\n"
            "[Link do PayPal](https://www.paypal.com/assinatura)\n"
            "Após a confirmação, seu cargo será atribuído automaticamente."
        )


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
                    "💳 **Cartão**: Doação mensal recorrente via PayPal.\n\n"
                    "Clique nos botões abaixo para mais informações."
                ),
                color=discord.Color.green()
            )
            view = DoarView(self.bot)
            await ctx.author.send(embed=embed, view=view)
            await ctx.send("📩 Verifique sua mensagem direta (DM) para escolher a forma de doação!", ephemeral=True)
        except discord.Forbidden:
            await ctx.send("❌ Não foi possível enviar a mensagem direta. Verifique suas configurações de privacidade!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(DoarCommands(bot))