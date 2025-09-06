import discord, os, logging
from os import getenv
from discord.ext import commands
import requests
from collections import deque
from bot.commands.admin import is_owner
logger = logging.getLogger(__name__)

class DeepseekCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_key = getenv('DEEP_KEY')
        self.log_channel_id=int(getenv('DEEPSEEK_LOG_CHANNEL', 0))
        self.allowed_channel_id=int(getenv("QUARTO_DO_HUGME", 0))
        self.auto_response = True #caso true, bot responde sozinho
        if not self.api_key:
            raise ValueError("DEEP_KEY must be set in environment variables")
        self.message_history = {}
        
    @commands.Cog.listener()
    async def on_message(self, message):
        if (not self.auto_response or message.author.bot or not self.allowed_channel_id or message.channel.id != self.allowed_channel_id or message.content.startswith(self.bot.command_prefix)):
            return
        
        try:
            channel_id = message.channel.id
            if channel_id not in self.message_history:
                self.message_history[channel_id] = deque(maxlen=10)
            
            history = list(self.message_history[channel_id])
                
            response = await self.call_deepseek_api(message.content, history)
            await message.channel.send(f"{message.author.mention}{response}")
            
            self.message_history[channel_id].append({
                "role": "user",
                "content": message.content
            })
            self.message_history[channel_id].append({
                "role": "assistant",
                "content": response
            })
            
            await self.log_interaction(message.author, message.content, response)
            
        except Exception as e:
            error_msg = f"❌ Erro ao responder automaticamente: {str(e)}"
            await message.channel.send("Erro ao processar mensagem automática.", ephemeral=True)
            await self.log_interaction(message.author, message.content, f"ERRO AUTO: {str(e)}")

        
    @commands.hybrid_command(name="bot", description="converse com o Hugme!")
    async def conversar(self, ctx: commands.Context, *, mensagem:str):
        if self.allowed_channel_id and ctx.channel.id != self.allowed_channel_id:
            await ctx.send(f"❌ Este comando só pode ser usado no canal designado.", ephemeral=True)
            return
        
        try:
            channel_id = ctx.channel.id
            if channel_id not in self.message_history:
                self.message_history[channel_id] = deque(maxlen=10)
            
            history = list(self.message_history[channel_id])
                
            response = await self.call_deepseek_api(mensagem, history)
            await ctx.channel.send(f"{ctx.author.mention}{response}")
            
            self.message_history[channel_id].append({
                "role": "user",
                "content": mensagem
            })
            self.message_history[channel_id].append({
                "role": "assistant",
                "content": response
            })
            
            await self.log_interaction(ctx.author, mensagem, response)
            
        except Exception as e:
            error_msg = f"❌ Erro ao chamar a API Deepseek: {str(e)}"
            await ctx.send("Erro de memoria cheia ou posivelmente API esta fora de serviço, avise ao desenvolvedor.", ephemeral=True)
            await self.log_interaction(ctx.author, mensagem, f"ERRO: {str(e)}")

    @is_owner()
    @commands.hybrid_command(name="toggle_auto", description="Ativa/desativa respostas automáticas")
    @commands.has_permissions(administrator=True)
    async def toggle_auto_response(self, ctx):
        """Toggle automatic responses"""
        self.auto_response = not self.auto_response
        status = "✅ **LIGADO**" if self.auto_response else "❌ **DESLIGADO**"
        await ctx.send(f"Respostas automáticas: {status}", ephemeral=True)


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
    
    async def call_deepseek_api(self, prompt: str, history: list) -> str:
        """Implementação real da chamada à API do DeepSeek"""
        # Substitua por sua chave de API real
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Descrição do HugMe e o prompt com a interação do usuário
        descricao_hugme = """
        Você é o HugMe, um bot amigável e descontraído criado para um servidor de pessoas neurodivergentes (autismo, TDAH e afins). Seu objetivo é agir como um usuário normal do Discord, participando de conversas de forma natural, leve e respeitosa, sem parecer formal demais ou excessivamente automático.

        Características principais:

        1. Tom Natural de Usuário: Responda como se fosse um amigo no Discord. Use emojis de forma moderada, gírias leves ou memes quando fizer sentido, mas sem exageros.
        2. Clareza e Simplicidade: Fale de um jeito direto e fácil de entender, sem enrolação.
        3. Respeito ao Ritmo: Seja paciente com respostas lentas ou pausadas. Não pressione.
        4. Apoio no Dia a Dia: Ajude com dicas simples, truques de organização, ou só jogue conversa fora para descontrair.
        5. Personalidade: Seja curioso, divertido e acessível, mas sem forçar intimidade. Você pode brincar, dar sugestões, comentar sobre coisas do dia a dia.
        6. Identidade: Lembre-se de que você foi criado por MrMedicmain – pode mencionar isso de vez em quando de forma casual, como um usuário falando do dev.

        Exemplos de interação:
        Usuário: "Oi HugMe, tudo bem?"
        HugMe: "Claro colega, o que precisa de mim? :^"

        Usuário: "Tô com dificuldade pra focar."
        HugMe: "vish, que tal quebrar suas tarefas igual quests em um jogo? depois se recompense com um doçe ou algo assim :v"

        Usuário: "Tô sem ideia de projeto."
        HugMe: "quem nunca, tenta pegar inspiração de algo, ou criar um problema ficticio pra resolver, quem sabe ate um problema pequeno real? :p."

        Usuário: "Me sinto meio bagunçado."
        HugMe: "Relaxa, todo mundo passa por isso. Já tentou fazer uma listinha rápida do que precisa fazer hoje? Ajuda a clarear a mente."

        Nota: Você não é psicólogo. Sua missão não é lidar com questões emocionais profundas. Apenas seja um bot amigável que oferece ajuda prática e mantém a conversa fluida e divertida. A ideia é ser acessível, sem ser intrusivo, garantindo que os membros se sintam confortáveis em interagir com você.

        """
        
        messages = [{
            "role": "system",
            "content": descricao_hugme
        }]
        
        # Add message history if available
        for message in history:
            messages.append(message)
        
        # Add current user message
        messages.append({
            "role": "user",
            "content": prompt
        })

        data = {
            "model": "deepseek-chat",
            "messages": messages
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
