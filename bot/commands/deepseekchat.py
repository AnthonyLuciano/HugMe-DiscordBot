import discord, os, logging
from os import getenv
from discord.ext import commands
import requests
from collections import deque
import re

logger = logging.getLogger(__name__)

# Palavras-chave que indicam possível uso terapêutico ou crise emocional
SENSITIVE_KEYWORDS = [
    # Crise/saúde mental
    "suicídio", "suicidio", "me matar", "quero morrer", "não quero mais viver",
    "nao quero mais viver", "me machucar", "automutilação", "autolesão",
    "depressão profunda", "ansiedade severa", "surto", "crise de pânico",
    "panico", "trauma", "abuso", "violência", "violencia",
    # Uso como terapeuta
    "me ajuda a processar", "preciso de terapia", "meu terapeuta",
    "me sinto muito mal", "não consigo mais", "nao consigo mais",
    "estou sofrendo muito", "tô sofrendo muito", "desesperado", "desesperada",
    "sem esperança", "sem esperanca", "me sinto vazio", "me sinto vazia",
    "choro todo dia", "não consigo dormir de tanto", "nao consigo dormir de tanto"
]

CRISIS_KEYWORDS = [
    "suicídio", "suicidio", "me matar", "quero morrer", "não quero mais viver",
    "nao quero mais viver", "me machucar", "automutilação", "autolesão"
]

SAFEGUARD_REMINDER_INTERVAL = 5  # A cada X mensagens, lembra que não é terapeuta

MENTAL_HEALTH_RESOURCES = """
📋 **Recursos de Saúde Mental (Brasil):**
- **CVV** (Centro de Valorização da Vida): Ligue **188** ou acesse cvv.org.br (24h)
- **CAPS** (Centro de Atenção Psicossocial): Atendimento gratuito pelo SUS
- **SAMU**: 192
- Converse com alguém de confiança ou um profissional de saúde mental 💙
"""

class DeepseekCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_key = getenv('DEEP_KEY')
        self.log_channel_id=int(getenv('DEEPSEEK_LOG_CHANNEL', 0))
        self.allowed_channel_id=int(getenv("QUARTO_DO_HUGME", 0))
        self.auto_response = True
        if not self.api_key:
            raise ValueError("DEEP_KEY must be set in environment variables")
        self.message_history = {}
        self.message_count = {}  # Contador por canal para o lembrete periódico
    
    @commands.Cog.listener()
    async def on_ready(self):
        if self.allowed_channel_id:
            channel = self.bot.get_channel(self.allowed_channel_id)
            name = channel.name if channel else "canal não encontrado"
            logger.info(f"DeepseekChat ativo no canal: #{name} (ID: {self.allowed_channel_id})")
        else:
            logger.warning("DeepseekChat: QUARTO_DO_HUGME não configurado, bot não responderá em nenhum canal.")
        
    def is_sensitive_message(self, text: str) -> bool:
        """Verifica se a mensagem contém tópicos sensíveis"""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in SENSITIVE_KEYWORDS)
    
    def is_crisis_message(self, text: str) -> bool:
        """Verifica se a mensagem indica crise imediata"""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in CRISIS_KEYWORDS)
    
    def should_send_reminder(self, channel_id: int) -> bool:
        """Verifica se está na hora de mandar o lembrete periódico"""
        count = self.message_count.get(channel_id, 0)
        return count > 0 and count % SAFEGUARD_REMINDER_INTERVAL == 0

    async def send_safeguard_message(self, destination, author_mention: str, is_crisis: bool = False):
        """Envia mensagem de safeguard apropriada"""
        if is_crisis:
            embed = discord.Embed(
                title="💙 Ei, me preocupei com você",
                description=(
                    f"{author_mention} percebi que você pode estar passando por um momento muito difícil.\n\n"
                    "**Eu sou apenas um bot** e não tenho capacidade de oferecer o suporte que você merece agora. "
                    "Por favor, fale com alguém que realmente pode ajudar:"
                ),
                color=0x5865F2
            )
            embed.add_field(name="🆘 Recursos de apoio", value=MENTAL_HEALTH_RESOURCES, inline=False)
            embed.set_footer(text="Você não está sozinho(a). Buscar ajuda é um ato de coragem. 💙")
            await destination.send(embed=embed)
        else:
            embed = discord.Embed(
                title="⚠️ Lembrete importante",
                description=(
                    f"{author_mention} parece que esse assunto é um pouco mais sério.\n\n"
                    "Só lembrando: **sou um bot descontraído**, não um profissional de saúde mental. "
                    "Para questões emocionais mais profundas, um psicólogo ou terapeuta pode ajudar muito mais do que eu! 💙"
                ),
                color=0xFEE75C
            )
            embed.add_field(name="📋 Recursos úteis", value=MENTAL_HEALTH_RESOURCES, inline=False)
            await destination.send(embed=embed)

    async def send_periodic_reminder(self, destination):
        """Lembrete periódico e discreto de que o bot não é terapeuta"""
        embed = discord.Embed(
            description=(
                "💬 *Lembrete amigável: sou o HugMeBot, um bot para bater papo e dar umas dicas práticas! "
                "Para suporte emocional de verdade, um profissional faz toda a diferença. "
                "CVV: **188** (24h) se precisar conversar com alguém agora.*"
            ),
            color=0x57F287
        )
        await destination.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        if (not self.auto_response or message.author.bot or not self.allowed_channel_id 
                or message.channel.id != self.allowed_channel_id 
                or message.content.startswith(self.bot.command_prefix)):
            return
        
        try:
            channel_id = message.channel.id
            if channel_id not in self.message_history:
                self.message_history[channel_id] = deque(maxlen=10)
            
            # Incrementa contador do canal
            self.message_count[channel_id] = self.message_count.get(channel_id, 0) + 1

            # Checagem de crise imediata — prioridade máxima
            if self.is_crisis_message(message.content):
                await self.send_safeguard_message(message.channel, message.author.mention, is_crisis=True)
                await self.log_interaction(message.author, message.content, "[SAFEGUARD - CRISE DETECTADA]")
                return  # Não responde normalmente em caso de crise

            # Checagem de tópico sensível
            if self.is_sensitive_message(message.content):
                await self.send_safeguard_message(message.channel, message.author.mention, is_crisis=False)
                await self.log_interaction(message.author, message.content, "[SAFEGUARD - TÓPICO SENSÍVEL]")
                return

            history = list(self.message_history[channel_id])
            response = await self.call_deepseek_api(message.content, history)
            await message.channel.send(f"{message.author.mention} {response}")
            
            self.message_history[channel_id].append({"role": "user", "content": message.content})
            self.message_history[channel_id].append({"role": "assistant", "content": response})
            
            # Lembrete periódico após resposta normal
            if self.should_send_reminder(channel_id):
                await self.send_periodic_reminder(message.channel)

            await self.log_interaction(message.author, message.content, response)
            
        except Exception as e:
            await message.channel.send("Erro ao processar mensagem automática.")
            await self.log_interaction(message.author, message.content, f"ERRO AUTO: {str(e)}")
            
    @commands.hybrid_command(name="chatstatus", description="Checagem se o bot respondera automaticamente ou não")
    async def statuschat(self, ctx: commands.Context):
        status = "✅ Respostas automaticas ativadas" if self.auto_response else "❌ Respostas automaticas desativadas"
        await ctx.send(status, ephemeral=True)

    @commands.hybrid_command(name="bot", description="converse com o Hugme!")
    async def conversar(self, ctx: commands.Context, *, mensagem: str):
        if self.allowed_channel_id and ctx.channel.id != self.allowed_channel_id:
            await ctx.send("❌ Este comando só pode ser usado no canal designado.", ephemeral=True)
            return
        
        try:
            channel_id = ctx.channel.id
            if channel_id not in self.message_history:
                self.message_history[channel_id] = deque(maxlen=10)

            self.message_count[channel_id] = self.message_count.get(channel_id, 0) + 1

            # Checagem de crise imediata
            if self.is_crisis_message(mensagem):
                await self.send_safeguard_message(ctx.channel, ctx.author.mention, is_crisis=True)
                await self.log_interaction(ctx.author, mensagem, "[SAFEGUARD - CRISE DETECTADA]")
                return

            # Checagem de tópico sensível
            if self.is_sensitive_message(mensagem):
                await self.send_safeguard_message(ctx.channel, ctx.author.mention, is_crisis=False)
                await self.log_interaction(ctx.author, mensagem, "[SAFEGUARD - TÓPICO SENSÍVEL]")
                return

            history = list(self.message_history[channel_id])
            response = await self.call_deepseek_api(mensagem, history)
            await ctx.channel.send(f"{ctx.author.mention} {response}")
            
            self.message_history[channel_id].append({"role": "user", "content": mensagem})
            self.message_history[channel_id].append({"role": "assistant", "content": response})

            if self.should_send_reminder(channel_id):
                await self.send_periodic_reminder(ctx.channel)

            await self.log_interaction(ctx.author, mensagem, response)
            
        except Exception as e:
            await ctx.send("Erro de memoria cheia ou possivelmente API esta fora de serviço, avise ao desenvolvedor.", ephemeral=True)
            await self.log_interaction(ctx.author, mensagem, f"ERRO: {str(e)}")

    @commands.hybrid_command(name="toggle_auto", description="Ativa/desativa respostas automáticas")
    async def toggle_auto_response(self, ctx):
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
            
            is_safeguard = response and response.startswith("[SAFEGUARD")
            
            embed = discord.Embed(
                title="🤖 Interação com HugMeBot",
                color=0xFF6B6B if is_safeguard else (0x00ff00 if response else 0xff0000),
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="👤 Usuário", value=f"{user.mention} (`{user.id}`)", inline=False)
            embed.add_field(name="❓ Pergunta", value=question[:1024], inline=False)
            
            if response:
                field_name = "🛡️ Safeguard Ativado" if is_safeguard else ("💥 Erro" if response.startswith("ERRO:") else "💬 Resposta")
                embed.add_field(name=field_name, value=response[:1024], inline=False)
            
            await log_channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Erro ao enviar log: {str(e)}")
    
    async def call_deepseek_api(self, prompt: str, history: list) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        descricao_hugme = """
Você é o HugMe, um bot amigável e descontraído criado para um servidor de pessoas neurodivergentes (autismo, TDAH e afins). Seu objetivo é agir como um usuário normal do Discord, participando de conversas de forma natural, leve e respeitosa, sem parecer formal demais ou excessivamente automático.

Características principais:

1. Tom Natural de Usuário: Responda como se fosse um amigo no Discord. Use emojis de forma moderada, gírias leves ou memes quando fizer sentido, mas sem exageros.
2. Clareza e Simplicidade: Fale de um jeito direto e fácil de entender, sem enrolação.
3. Respeito ao Ritmo: Seja paciente com respostas lentas ou pausadas. Não pressione.
4. Apoio no Dia a Dia: Ajude com dicas simples, truques de organização, ou só jogue conversa fora para descontrair.
5. Personalidade: Seja curioso, divertido e acessível, mas sem forçar intimidade. Você pode brincar, dar sugestões, comentar sobre coisas do dia a dia.
6. Identidade: Lembre-se de que você foi criado por MrMedicmain – pode mencionar isso de vez em quando de forma casual.
7. Fidelidade à Pergunta: Responda somente ao que o usuário perguntou ou solicitou. Não acrescente explicações extras ou comentários adicionais desnecessários.
8. Contexto Discord: Mantenha a linguagem informal, mas não invente fatos.

LIMITES IMPORTANTES — Siga sempre:
- Você NÃO é psicólogo, terapeuta, nem profissional de saúde mental.
- Se alguém compartilhar sentimentos muito intensos, diga com gentileza que você não tem capacidade de ajudar com isso e sugira o CVV (188) ou um profissional.
- Nunca tente "tratar" ou "curar" problemas emocionais. Ofereça acolhimento breve e redirecione para ajuda real.
- Se perceber que o usuário está usando você como substituto de terapia, lembre gentilmente que um profissional pode ajudar muito mais.

Exemplos de interação:
Usuário: "Oi HugMe, tudo bem?"
HugMe: "Claro colega, o que precisa de mim? :^"

Usuário: "Tô com dificuldade pra focar."
HugMe: "vish, que tal quebrar suas tarefas igual quests em um jogo? depois se recompense com um doce ou algo assim :v"

Usuário: "Me sinto muito sozinho ultimamente."
HugMe: "puts, sinto muito ouvir isso :c esse tipo de sentimento é pesado. não sou o melhor pra ajudar com isso, mas o CVV (188) tem gente boa pra conversar a qualquer hora. tem alguém de confiança por perto?"
"""
        
        messages = [{"role": "system", "content": descricao_hugme}]
        for message in history:
            messages.append(message)
        messages.append({"role": "user", "content": prompt})

        data = {"model": "deepseek-chat", "messages": messages}

        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            json=data,
            headers=headers
        )
        response.raise_for_status()
        
        raw_response = response.json()["choices"][0]["message"]["content"]
        filtered_response = raw_response.replace("@everyone", "everyone").replace("@here", "here")
        
        return filtered_response

async def setup(bot):
    await bot.add_cog(DeepseekCommands(bot))