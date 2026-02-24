import discord
import os
import logging
import threading
import uvicorn
from bot.config import Config as app_config
from discord.ext import commands
from bot.database import Base, engine, AsyncSessionLocal
from bot.database.models import Apoiador
from bot.shared import set_bot_instance
from sqlalchemy import select

# Configuração básica de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Carrega variáveis do arquivo .env
# (engine and AsyncSessionLocal are imported from bot.database)

# Gerenciamento do banco de dados
class DatabaseManager:
    async def obter_apoiador(self, discord_id: str, guild_id: str) -> Apoiador | None:
        """Obtém um apoiador pelo Discord ID e Guild ID"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Apoiador).where(
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
            activity=discord.Game(name="Ajudando a comunidade"),
            allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=True)
        )
        self.db = DatabaseManager()
        self.web_thread = None

    def start_web_server(self):
        """Schedule the uvicorn server to run in the bot's asyncio loop."""
        # build absolute paths based on this source file so we don't depend on
        # the process working directory (which in some deployment setups
        # like Replit is `/home/container`).
        base_dir = os.path.abspath(os.path.dirname(__file__))

        # compute potential certificate directories. the project normally keeps
        # them under bot/certificates, but some hosting environments (e.g.
        # the Replit container) provide them at /home/container/certificates.
        # check each location and use the first that contains both files.
        candidate_dirs = [
            os.path.join(base_dir, "certificates"),
            "/home/container/certificates",
        ]

        ssl_certificate = None
        ssl_keyfile = None
        for d in candidate_dirs:
            cert_path = os.path.join(d, "hugmebot.online.pem")
            key_path = os.path.join(d, "hugmebot.online.key")
            if os.path.isfile(cert_path) and os.path.isfile(key_path):
                ssl_certificate = cert_path
                ssl_keyfile = key_path
                logger.info(f"Usando certificados em {d}")
                break

        # if we didn't find them in any known location, error out.
        if not ssl_certificate or not ssl_keyfile:
            # report the list of places we looked for easier debugging
            seen = ", ".join(candidate_dirs)
            raise FileNotFoundError(
                f"Certificado ou chave SSL não encontrados em nenhum dos diretórios: {seen}"
            )

        try:
            config = uvicorn.Config("bot.web.main:app",
                                    host="0.0.0.0",
                                    port=26173,
                                    loop="asyncio",
                                    lifespan="on",
                                    ssl_certfile=ssl_certificate,
                                    ssl_keyfile=ssl_keyfile
                                    )
            server = uvicorn.Server(config)
            # Run server.serve() as a background task in the bot's event loop
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(server.serve())
                logger.info("Servidor web agendado no loop asyncio atual na porta 26173")
            except RuntimeError:
                # No running loop; fallback to thread-based start
                def run_web():
                    uvicorn.run("bot.web.main:app",
                                host="0.0.0.0",
                                port=26173,
                                reload=False,
                                ssl_certfile=ssl_certificate,
                                ssl_keyfile=ssl_keyfile
                                )
                self.web_thread = threading.Thread(target=run_web, daemon=True)
                self.web_thread.start()
                logger.info("Servidor web iniciado em thread (fallback) na porta 26173")
        except Exception as e:
            logger.error(f"Falha ao iniciar servidor web: {e}")

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
