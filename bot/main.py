import discord
import os
import logging
import threading
import uvicorn
from bot.config import Config as app_config
from discord.ext import commands
from bot.database import Base
from bot.database.models import Apoiador
from bot.shared import set_bot_instance
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Configuração básica de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Carrega variáveis do arquivo .env


DATABASE_URL = app_config.DATABASE_URL
# Engine async
engine = create_async_engine(DATABASE_URL, echo=True, future=True)
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


# Gerenciamento do banco de dados
class DatabaseManager:
    async def obter_apoiador(self, discord_id: str, guild_id: str) -> Apoiador | None:
        """Obtém um apoiador pelo Discord ID e Guild ID"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                discord.select(Apoiador).where(
                    Apoiador.discord_id == discord_id,
                    Apoiador.guild_id == guild_id
                )
            )
            return result.scalars().first()


# Função async para criar as tabelas
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Tabelas do banco inicializadas")


class HugMeBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(
            command_prefix='!',
            intents=intents,
            application_id=os.getenv('APPLICATION_ID'),
            help_command=None,
            activity=discord.Game(name="Ajudando a comunidade")
        )
        self.db = DatabaseManager()
        self.web_thread = None

    def start_web_server(self):
        """Inicia o servidor web em uma thread separada"""
        def run_web():
            uvicorn.run("bot.web.main:app", host="0.0.0.0", port=26173, reload=False)

        self.web_thread = threading.Thread(target=run_web, daemon=True)
        self.web_thread.start()
        logger.info("Servidor web iniciado na porta 26173")

    async def setup_hook(self):
        """Configurações iniciais quando o bot está inicializando"""
        try:
            # Inicializa o banco de dados async
            await init_db()

            # Carrega todos os cogs
            for filename in os.listdir('./bot/commands'):
                if filename.endswith('.py') and not filename.startswith('_'):
                    try:
                        await self.load_extension(f'bot.commands.{filename[:-3]}')
                        logger.info(f"Extensão '{filename}' carregada com sucesso")
                    except Exception as e:
                        logger.error(f"Erro ao carregar cog {filename}: {e}")

            self.start_web_server()
            # Sincroniza comandos slash
            await self.tree.sync()
            logger.info("Comandos slash sincronizados")
        except Exception as e:
            logger.error(f"Erro ao carregar extensões/setup_hook: {e}")

    async def on_ready(self):
        logger.info(f'Bot conectado como {self.user}')
        logger.info(f'Comandos disponíveis: {[cmd.name for cmd in self.commands]}')

    async def on_member_join(self, member):
        logger.info(f"Novo membro: {member.display_name}")

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        logger.error(f"Erro no comando {ctx.command}: {error}")
        await ctx.send(f"⚠️ Ocorreu um erro: {str(error)}")


if __name__ == '__main__':
    bot = HugMeBot()
    set_bot_instance(bot)

    try:
        TOKEN = os.getenv('DISCORD_BOT_TOKEN')
        if not TOKEN:
            raise ValueError("Token do Discord não encontrado no .env")
        bot.run(TOKEN)
    except Exception as e:
        logger.critical(f"Falha ao iniciar o bot: {e}")
