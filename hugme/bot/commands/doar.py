import discord
from discord.ext import commands
from discord.ui import Button, View

class DoarView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Pix", style=discord.ButtonStyle.primary, emoji="💰")
    async def pix_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message(
            "📌 **Doação via Pix**\n"
            "Você pode fazer uma doação única ou recorrente via Pix.\n"
            "Envie o comprovante para a moderação após realizar o pagamento.\n"
            "Use o comando `/enviar_pix` para continuar."
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
            view = DoarView()
            await ctx.author.send(embed=embed, view=view)  # Envia a mensagem direta
            await ctx.send("📩 Verifique sua mensagem direta (DM) para escolher a forma de doação!", ephemeral=True)
        except discord.Forbidden:
            await ctx.send("❌ Não foi possível enviar a mensagem direta. Verifique suas configurações de privacidade!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(DoarCommands(bot))