import discord, os, logging
from os import getenv
from discord.ext import commands
import requests
logger = logging.getLogger(__name__)

class DeepseekCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_key = getenv('DEEP_KEY')
        self.log_channel_id=int(getenv('DEEPSEEK_LOG_CHANNEL', 0))
        self.allowed_channel_id=int(getenv("QUARTO_DO_HUGME", 0))
        if not self.api_key:
            raise ValueError("DEEP_KEY must be set in environment variables")
        
    @commands.hybrid_command(name="bot", description="converse com o Hugme!")
    async def conversar(self, ctx: commands.Context, *, mensagem:str):
        if self.allowed_channel_id and ctx.channel.id != self.allowed_channel_id:
            await ctx.send(f"❌ Este comando só pode ser usado no canal designado.", ephemeral=True)
            return
        
        try:
            response = await self.call_deepseek_api(mensagem)
            await ctx.channel.send(f"{ctx.author.mention}{response}")
            
            await self.log_interaction(ctx.author, mensagem, response)
            
        except Exception as e:
            error_msg = f"❌ Erro ao chamar a API Deepseek: {str(e)}"
            await ctx.send(f"{error_msg}, avise ao desenvolvedor.", ephemeral=True)
            await self.log_interaction(ctx.author, mensagem, f"ERRO: {str(e)}")

    async def log_interaction(self, user: discord.User, question: str, response: str | None):
        if not self.log_channel_id:
            return
        try:
            log_channel = self.bot.get_channel(self.log_channel_id)
            if not log_channel:
                logger.warning(f"Canal de logs ({self.log_channel_id}) não encontrado")
                return
            
            embed = discord.Embed(
                title="🤖 Interação com HugMeBot",
                color=0x00ff00 if response else 0xff0000,
                timestamp=discord.utils.utcnow()
            )
            
            embed.add_field(
                name="👤 Usuário",
                value=f"{user.mention} (`{user.id}`)",
                inline=False
            )
            
            embed.add_field(
                name="❓ Pergunta",
                value=question[:1024],
                inline=False
            )
            
            if response:
                if response.startswith("ERRO:"):
                    embed.color = 0xff0000
                    embed.add_field(
                        name="💥 Erro",
                        value=response[:1024],
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="💬 Resposta",
                        value=response[:1024] if len(response) <= 1024 else f"{response[:1020]}...",
                        inline=False
                    )
            
            await log_channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Erro ao enviar log: {str(e)}")
    
    async def call_deepseek_api(self, prompt: str) -> str:
        """Implementação real da chamada à API do DeepSeek"""
        # Substitua por sua chave de API real
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Descrição do HugMe e o prompt com a interação do usuário
        descricao_hugme = """
        Você é o HugMe, um bot amigável e descontraído criado para um servidor de pessoas neurodivergentes, como pessoas com autismo, TDAH, entre outras. Seu papel é oferecer interações informais, apoiando os membros da comunidade de maneira leve e respeitosa.

        Características principais:
        1. Conversas Descontraídas: Você responde de forma amigável, mas sem ser excessivamente emocional. Mantenha o tom leve e natural.
        2. Respostas Claras e Diretas: Use uma linguagem simples e objetiva. Evite complicações ou termos que possam ser confusos.
        3. Respeito ao Ritmo do Usuário: Entenda que algumas pessoas podem precisar de mais tempo para interagir ou formular respostas, e você deve ser paciente e respeitar isso.
        4. Apoio no Dia a Dia: Ofereça ajuda em questões práticas, como organizar tarefas, dicas rápidas, ou simplesmente estar disponível para uma conversa descontraída.

        Exemplo de Resposta do HugMeBot:
        - Usuário: "Oi HugMe, como vai?"
        - HugMeBot: "Oi! Tudo tranquilo por aqui! Como posso te ajudar hoje? 😊"

        - Usuário: "Estou com dificuldade para me concentrar."
        - HugMeBot: "Entendo! Às vezes isso acontece, né? Tente dividir as tarefas em etapas menores, isso pode ajudar a focar. Precisa de algo específico?"

        - Usuário: "Estou sem ideias para um projeto."
        - HugMeBot: "Eu posso ajudar! Você já pensou em tentar algo criativo ou mudar um pouco o foco? Às vezes uma pausa também ajuda a clarear a mente. Se precisar de mais sugestões, só avisar!"

        - Usuário: "Me sinto um pouco desorganizado."
        - HugMeBot: "Isso é super normal, acontece com todo mundo. Que tal tentar fazer uma lista de coisas para fazer? Às vezes isso ajuda a ter uma visão mais clara das tarefas."

        Nota: Lembre-se de que você não é um psicólogo e sua missão não é lidar com questões emocionais profundas. Apenas seja um bot amigável, que oferece ajuda prática e mantém a conversa fluida e divertida. A ideia é ser acessível, sem ser intrusivo, e garantir que os membros se sintam confortáveis em interagir com você.
        """
        
        data = {
            "model": "deepseek-chat",
            "messages": [{
                "role": "system",
                "content": descricao_hugme
            },
            {
                "role": "user",
                "content": f"{prompt}"
            }]
        }

        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            json=data,
            headers=headers
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

async def setup(bot):
    await bot.add_cog(DeepseekCommands(bot))
