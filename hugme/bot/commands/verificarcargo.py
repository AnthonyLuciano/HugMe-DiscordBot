import discord
from discord.ui import Button, View
from bot.servicos.VerificacaoMembro import VerificacaoMembro

class VerificarCargoView(View):
    def __init__(self, verificador: VerificacaoMembro, cargo_id: int, tempo_minimo_dias: int):
        super().__init__(timeout=120)
        self.verificador = verificador
        self.cargo_id = cargo_id
        self.tempo_minimo_dias = tempo_minimo_dias

    @discord.ui.button(label="Verificar Cargo", style=discord.ButtonStyle.primary)
    async def verificar_cargo(self, interaction: discord.Interaction, button: Button):
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "Você precisa estar no servidor para usar este comando",
                ephemeral=True
            )
            return

        resultado = await self.verificador.aplicar_cargo_se_qualificado(
            interaction.user,
            self.cargo_id,
            self.tempo_minimo_dias
        )
        await interaction.response.send_message(resultado, ephemeral=True)

async def setup(bot):
    verificador = VerificacaoMembro(bot)
    
    @bot.tree.command(name="verificar_cargo", description="Cria verificação de cargo (apenas staff)")
    @discord.app_commands.checks.has_permissions(administrator=True)
    async def verificar_cargo(interaction: discord.Interaction, cargo_id: str, tempo_minimo_dias: int = 30):
        """Comando restrito para staff criar verificação de cargo"""
        try:
            if not isinstance(interaction.channel, discord.TextChannel):
                await interaction.response.send_message(
                    "❌ Este comando só pode ser usado em canais de texto normais",
                ephemeral=True
            )
                return

            view = VerificarCargoView(verificador, int(cargo_id), tempo_minimo_dias)
            await interaction.response.send_message(
                "✅ Botão de verificação criado!",
                ephemeral=True
            )
            await interaction.channel.send(
                f"Clique para verificar e receber o cargo (mínimo {tempo_minimo_dias} dias)",
                view=view
            )
        except Exception as e:
            await interaction.response.send_message(f"Erro: {str(e)}", ephemeral=True)