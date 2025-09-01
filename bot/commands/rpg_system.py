import discord, os, logging, json, asyncio, aiohttp
from discord.ext import commands
from typing import Dict
from datetime import datetime
from bot.config import Config as app_config

logger = logging.getLogger(__name__)

class SistemaRPG(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.api_key = app_config.DEEP_KEY
        self.log_channel_id = int(app_config.DONO_LOG_CHANNEL) if app_config.DONO_LOG_CHANNEL else None
        self.allowed_channel_id = int(app_config.QUARTO_DO_HUGME) if app_config.QUARTO_DO_HUGME else None
        self.sessions_file = "data/rpg_sessions.json"
        self.user_sessions: Dict[int, Dict] = {}
        self.save_lock = asyncio.Lock()

        if not self.api_key:
            raise ValueError("DEEP_KEY precisa estar configurada no environment variables")

        self.carregar_sessoes()

    # ---------------- SESSÕES ----------------
    def carregar_sessoes(self):
        try:
            if os.path.exists(self.sessions_file):
                with open(self.sessions_file, 'r', encoding='utf-8') as f:
                    self.user_sessions = json.load(f)
        except Exception as e:
            logger.error(f"Erro ao carregar sessões: {str(e)}")
            self.user_sessions = {}

    async def salvar_sessoes(self):
        async with self.save_lock:
            try:
                os.makedirs(os.path.dirname(self.sessions_file), exist_ok=True)
                with open(self.sessions_file, 'w', encoding='utf-8') as f:
                    json.dump(self.user_sessions, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"Erro ao salvar sessões: {str(e)}")

    def pegar_sessao_usuario(self, user_id: int) -> Dict:
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {
                "history": [],
                "character": {},
                "current_story": "",
                "created_at": discord.utils.utcnow().isoformat(),
                "has_seen_tutorial": False,
                "adventure_started_at": None
            }
        return self.user_sessions[user_id]

    # ---------------- COMANDO RPG ----------------
    @commands.hybrid_command(name="rpg", description="Inicia ou continua sua aventura de RPG!")
    async def rpg(self, ctx: commands.Context, *, acao: str = ""):
        await ctx.defer(ephemeral=False)

        if ctx.guild.id != app_config.TEST_SERVER_ID:
            if ctx.interaction:
                await ctx.send("❌ Este comando só pode ser usado no servidor de testes.", ephemeral=True)
            else:
                await ctx.send("❌ Este comando só pode ser usado no servidor de testes.", delete_after=10)
            return

        if self.allowed_channel_id and ctx.channel.id != self.allowed_channel_id:
            if ctx.interaction:
                await ctx.send("❌ Este comando só pode ser usado no canal designado.", ephemeral=True)
            else:
                await ctx.send("❌ Este comando só pode ser usado no canal designado.", delete_after=10)
            return

        try:
            sessao = self.pegar_sessao_usuario(ctx.author.id)

            if not sessao["has_seen_tutorial"]:
                await self.mostrar_tutorial(ctx, sessao)
                return

            if acao.lower().startswith(("personagem", "character", "criar personagem")):
                await ctx.send("❌ Agora use o comando `/rpg_personagem`!")
                return

            if acao.lower() in ["iniciar", "start", "novo"]:
                await self.iniciar_aventura(ctx, sessao)
            elif acao:
                await self.continuar_historia(ctx, sessao, acao)
            else:
                await ctx.send("❌ Você precisa especificar uma ação! Use `/rpg iniciar` ou `/rpg [ação]`.")

            await self.salvar_sessoes()

        except Exception as e:
            logger.error(f"Erro no comando rpg: {e}")
            try:
                await ctx.send(f"⚠️ Ocorreu um erro: {str(e)}")
            except Exception as e2:
                logger.error(f"Erro ao enviar mensagem de erro: {e2}")

    # ---------------- TUTORIAL ----------------
    async def mostrar_tutorial(self, ctx: commands.Context, sessao: Dict):
        tutorial = """
🎮 **Bem-vindo ao Sistema de RPG!** 🎮

**Como jogar:**
• Use `/rpg iniciar` para começar uma nova aventura
• Use `/rpg_personagem` para criar seu personagem
• Use `/rpg [sua ação]` para interagir com o mundo
• Use `/rpg_status` para ver seu progresso
"""
        await ctx.send(tutorial)
        sessao["has_seen_tutorial"] = True
        await self.salvar_sessoes()

    # ---------------- COMANDO RPG_PERSONAGEM ----------------
    @commands.hybrid_command(
        name="rpg_personagem",
        description="Crie seu personagem de RPG com atributos separados"
    )
    async def rpg_personagem_cmd(
        self,
        ctx: commands.Context,
        nome: str,
        classe: str,
        raca: str,
        forca: int,
        destreza: int,
        constituicao: int,
        inteligencia: int,
        sabedoria: int,
        carisma: int
    ):
        """Cria um personagem com atributos separados"""
        await ctx.defer(ephemeral=False)

        try:
            sessao = self.pegar_sessao_usuario(ctx.author.id)
            
            if sessao.get("character"):
                await ctx.send("❌ Você já tem um personagem criado! Use `/rpg iniciar`.")
                return

            # Validar atributos
            atributos = {
                "for": forca,
                "des": destreza,
                "con": constituicao,
                "int": inteligencia,
                "sab": sabedoria,
                "car": carisma
            }
            
            for nome_attr, valor in atributos.items():
                if valor < 1 or valor > 10:
                    await ctx.send(f"❌ O atributo {nome_attr} deve estar entre 1 e 10.")
                    return
                
            sessao = self.pegar_sessao_usuario(ctx.author.id)
            
            if sessao.get("character"):
                await ctx.send("❌ Você já tem um personagem criado! Use `/rpg iniciar`.")
                return

            # Criar personagem
            sessao["character"] = {
                "name": nome,
                "class": classe,
                "race": raca,
                "attributes": atributos,
                "created_at": discord.utils.utcnow().isoformat()
            }

            await ctx.send(
                f"🎉 Personagem **{nome}** criado com sucesso!\n"
                f"**Classe:** {classe}\n"
                f"**Raça:** {raca}\n"
                f"**Atributos:**\n"
                f"• Força: {forca}\n• Destreza: {destreza}\n• Constituição: {constituicao}\n"
                f"• Inteligência: {inteligencia}\n• Sabedoria: {sabedoria}\n• Carisma: {carisma}\n\n"
                f"Use `/rpg iniciar` para começar sua aventura!"
            )
            await self.salvar_sessoes()

        except Exception as e:
            logger.error(f"Erro no comando rpg_personagem: {e}")
            await ctx.send(f"❌ Erro ao criar personagem: {str(e)}")

    # ---------------- COMANDO RPG_STATUS ----------------
    @commands.hybrid_command(name="rpg_status", description="Mostra o status atual da sua aventura")
    async def rpg_status(self, ctx: commands.Context):
        """Mostra o status da aventura atual"""
        await ctx.defer(ephemeral=False)
        
        sessao = self.pegar_sessao_usuario(ctx.author.id)
        
        if not sessao["history"]:
            await ctx.send("❌ Você ainda não iniciou uma aventura! Use `/rpg iniciar`")
            return

        # Usa a data de início da aventura se disponível, senão usa a data de criação da sessão
        data_inicio = sessao.get("adventure_started_at", sessao["created_at"])
        
        embed = discord.Embed(
            title="🎮 Status da Aventura",
            color=0x00ff00,
            timestamp=discord.utils.utcnow()
        )
        
        if sessao.get("character"):
            embed.add_field(
                name="👤 Personagem",
                value=f"{sessao['character']['name']} - {sessao['character']['class']} {sessao['character']['race']}",
                inline=False
            )
        
        embed.add_field(
            name="📅 Iniciada em",
            value=data_inicio[:10],
            inline=True
        )
        
        embed.add_field(
            name="📊 Progresso",
            value=f"{len(sessao['history'])} interações",
            inline=True
        )
        
        # Mostra um preview da última mensagem
        ultima_mensagem = sessao["history"][-1]["content"]
        preview = ultima_mensagem[:100] + "..." if len(ultima_mensagem) > 100 else ultima_mensagem
        embed.add_field(
            name="📖 Última cena",
            value=preview,
            inline=False
        )
        
        await ctx.send(embed=embed)

    # ---------------- AVENTURA ----------------
    async def iniciar_aventura(self, ctx: commands.Context, sessao: Dict):
        if not sessao.get("character"):
            await ctx.send("❌ Crie um personagem primeiro com `/rpg_personagem`")
            return

        sessao["history"] = []
        sessao["adventure_started_at"] = discord.utils.utcnow().isoformat()

        char = sessao["character"]
        prompt_inicial = f"""
Você é um mestre de RPG de texto. Crie uma aventura para {char['name']}, {char['race']} {char['class']} com atributos {char['attributes']}.
Dê 2-3 opções de ação no final. Máximo 3 parágrafos.
"""
        resposta = await self.chamar_api_rpg(prompt_inicial, sessao["history"])
        sessao["history"].extend([
            {"role": "system", "content": prompt_inicial},
            {"role": "assistant", "content": resposta}
        ])

        await ctx.send(f"🎮 **Aventura iniciada com {char['name']}!**\n\n{resposta}")
        await self.salvar_sessoes()

    async def continuar_historia(self, ctx: commands.Context, sessao: Dict, acao_jogador: str):
        if not sessao["history"]:
            await ctx.send("❌ Use `/rpg iniciar` antes de continuar a aventura!")
            return

        sessao["history"].append({"role": "user", "content": acao_jogador})
        contexto = [sessao["history"][0]] + sessao["history"][-8:]

        resposta = await self.chamar_api_rpg("Continue a história com base na ação do jogador:", contexto)
        sessao["history"].append({"role": "assistant", "content": resposta})

        await ctx.send(f"🎭 **Continuação da aventura**\n\n{resposta}")
        await self.salvar_sessoes()

    # ---------------- API ----------------
    async def chamar_api_rpg(self, prompt: str, history: list) -> str:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        system_prompt = "Você é um mestre de RPG de texto. Crie aventuras coerentes e ofereça opções. Máximo 3 parágrafos."
        mensagens = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": prompt}]
        data = {"model": "deepseek-chat", "messages": mensagens, "max_tokens": 500, "temperature": 0.8}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post("https://api.deepseek.com/v1/chat/completions",
                                        json=data, headers=headers,
                                        timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    resp.raise_for_status()
                    resultado = await resp.json()
                    if ("choices" in resultado and len(resultado["choices"]) > 0 and
                        "message" in resultado["choices"][0] and "content" in resultado["choices"][0]["message"]):
                        return resultado["choices"][0]["message"]["content"]
                    else:
                        logger.warning(f"Resposta inesperada da API: {resultado}")
                        return "⚠️ O mestre ficou em silêncio. Tente novamente!"
        except Exception as e:
            logger.error(f"Erro na API: {str(e)}")
            return "⚠️ O mestre não está respondendo. Tente novamente mais tarde."


# ---------------- SETUP ----------------
async def setup(bot: commands.Bot):
    await bot.add_cog(SistemaRPG(bot))