from datetime import datetime
import discord,logging,aiohttp
from discord.ext import commands
from typing import Dict
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select
from bot.database.models import RPGSession, RPGCharacter, Base
from bot.config import Config as app_config

logger = logging.getLogger(__name__)

class SistemaRPG(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.api_key = app_config.DEEP_KEY
        self.log_channel_id = int(app_config.DONO_LOG_CHANNEL) if app_config.DONO_LOG_CHANNEL else None
        self.allowed_channel_id = int(app_config.QUARTO_DO_HUGME) if app_config.QUARTO_DO_HUGME else None
        
        # Configuração do banco de dados
        self.engine = create_async_engine(app_config.DATABASE_URL)
        self.async_session = async_sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )
        
        if not self.api_key:
            raise ValueError("DEEP_KEY precisa estar configurada no environment variables")

    # ---------------- SESSÕES ----------------
    async def pegar_sessao_usuario(self, user_id: int) -> Dict:
        """Busca ou cria sessão do usuário no banco de dados"""
        async with self.async_session() as session:
            result = await session.execute(
                select(RPGSession).where(RPGSession.user_id == str(user_id))
                )
            db_session = result.scalar_one_or_none()
            
            if not db_session:
                # Cria nova sessão
                db_session = RPGSession(
                    user_id=str(user_id),
                    history=[],
                    character_data={},
                    current_story="",
                    has_seen_tutorial=False,
                    adventure_started_at=None
                )
                session.add(db_session)
                await session.commit()
                await session.refresh(db_session)
            
            return self._db_session_to_dict(db_session)
    
    def _db_session_to_dict(self, db_session: RPGSession) -> Dict:
        """Converte objeto SQLAlchemy para dicionário"""
        return {
            "history": db_session.history,
            "character": db_session.character_data,
            "current_story": db_session.current_story,
            "created_at": db_session.created_at,
            "has_seen_tutorial": db_session.has_seen_tutorial,
            "adventure_started_at": db_session.adventure_started_at if db_session.adventure_started_at else None
        }
    
    async def atualizar_sessao_usuario(self, user_id: int, data: Dict):
        """Atualiza sessão do usuário no banco de dados"""
        async with self.async_session() as session:
            result = await session.execute(
                select(RPGSession).where(RPGSession.user_id == str(user_id))
                )
            db_session = result.scalar_one_or_none()
            
            if db_session:
                db_session.history = data.get("history", [])
                character_data = data.get("character", {})
                if character_data and 'created_at' in character_data and isinstance(character_data['created_at'], datetime):
                    character_data['created_at'] = character_data['created_at'].isoformat()
                db_session.character_data = character_data
                db_session.current_story = data.get("current_story", "")
                db_session.has_seen_tutorial = data.get("has_seen_tutorial", False)
                db_session.adventure_started_at = data.get("adventure_started_at")
                db_session.updated_at = discord.utils.utcnow()
                
                await session.commit()

    # ---------------- COMANDO RPG ----------------
    @commands.hybrid_command(name="rpg", description="Inicia ou continua sua aventura de RPG!")
    async def rpg(self, ctx: commands.Context, *, acao: str = ""):
        await ctx.defer(ephemeral=False)

        if self.allowed_channel_id and ctx.channel.id != self.allowed_channel_id:
            if ctx.interaction:
                await ctx.send("❌ Este comando só pode ser usado no canal designado.", ephemeral=True)
            else:
                await ctx.send("❌ Este comando só pode ser usado no canal designado.", delete_after=10)
            return

        try:
            sessao = await self.pegar_sessao_usuario(ctx.author.id)

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
• Use `/rpg_personagem` para criar seu personagem, atributos devem ser entre 1 e 10
• Use `/rpg [sua ação]` para interagir com o mundo
• Use `/rpg_status` para ver seu progresso
"""
        await ctx.send(tutorial)
        sessao["has_seen_tutorial"] = True
        await self.atualizar_sessao_usuario(ctx.author.id, sessao)

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
            sessao = await self.pegar_sessao_usuario(ctx.author.id)
            
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

            # Criar personagem no banco de dados
            async with self.async_session() as session:
                character = RPGCharacter(
                    user_id=str(ctx.author.id),
                    name=nome,
                    class_name=classe,
                    race=raca,
                    strength=forca,
                    dexterity=destreza,
                    constitution=constituicao,
                    intelligence=inteligencia,
                    wisdom=sabedoria,
                    charisma=carisma
                )
                session.add(character)
                await session.commit()
                await session.refresh(character)

            # Atualizar sessão
            sessao["character"] = {
                "name": nome,
                "class": classe,
                "race": raca,
                "attributes": atributos,
                "created_at": discord.utils.utcnow().isoformat()
            }
            await self.atualizar_sessao_usuario(ctx.author.id, sessao)

            await ctx.send(
                f"🎉 Personagem **{nome}** criado com sucesso!\n"
                f"**Classe:** {classe}\n"
                f"**Raça:** {raca}\n"
                f"**Atributos:**\n"
                f"• Força: {forca}\n• Destreza: {destreza}\n• Constituição: {constituicao}\n"
                f"• Inteligência: {inteligencia}\n• Sabedoria: {sabedoria}\n• Carisma: {carisma}\n\n"
                f"Use `/rpg iniciar` para começar sua aventura!"
            )

        except Exception as e:
            logger.error(f"Erro no comando rpg_personagem: {e}")
            await ctx.send(f"❌ Erro ao criar personagem: {str(e)}")

    # ---------------- COMANDO RPG_STATUS ----------------
    @commands.hybrid_command(name="rpg_status", description="Mostra o status atual da sua aventura")
    async def rpg_status(self, ctx: commands.Context):
        """Mostra o status da aventura atual"""
        await ctx.defer(ephemeral=False)
        
        sessao = await self.pegar_sessao_usuario(ctx.author.id)
        
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
            value=data_inicio.strftime("%Y-%m-%d") if data_inicio else "Não iniciada",
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
        sessao["adventure_started_at"] = discord.utils.utcnow()

        char = sessao["character"]
        prompt_inicial = f"""
Você é um mestre de RPG de texto. Crie uma aventura épica e imersiva para {char['name']}, um {char['race']} {char['class']} com os seguintes atributos: {char['attributes']}.
Descreva o cenário, NPCs e conflitos de forma vívida, usando detalhes sensoriais e emoção. Inclua elementos de surpresa e desafios que incentivem decisões estratégicas.
No final, apresente 2 a 3 opções de ação concretas para o jogador escolher, **e uma quarta opção indicando que ele pode fazer algo diferente, sugerindo sua própria ação**. 
A resposta deve ter no máximo 3 parágrafos e ser coerente com a personalidade e habilidades do personagem.
"""

        resposta = await self.chamar_api_rpg(prompt_inicial, sessao["history"])
        sessao["history"].extend([
            {"role": "system", "content": prompt_inicial},
            {"role": "assistant", "content": resposta}
        ])

        await self.atualizar_sessao_usuario(ctx.author.id, sessao)
        await ctx.send(f"🎮 **Aventura iniciada com {char['name']}!**\n\n{resposta}")

    async def continuar_historia(self, ctx: commands.Context, sessao: Dict, acao_jogador: str):
        if not sessao["history"]:
            await ctx.send("❌ Use `/rpg iniciar` antes de continuar a aventura!")
            return

        sessao["history"].append({"role": "user", "content": acao_jogador})
        contexto = [sessao["history"][0]] + sessao["history"][-8:]

        resposta = await self.chamar_api_rpg("Continue a história com base na ação do jogador:", contexto)
        sessao["history"].append({"role": "assistant", "content": resposta})

        await self.atualizar_sessao_usuario(ctx.author.id, sessao)
        await ctx.send(f"🎭 **Continuação da aventura**\n\n{resposta}")

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

    # ---------------- COG CLEANUP ----------------
    async def cog_unload(self):
        """Fecha a conexão com o banco de dados quando o cog é descarregado"""
        await self.engine.dispose()

# ---------------- SETUP ----------------
async def setup(bot: commands.Bot):
    await bot.add_cog(SistemaRPG(bot))