import discord, os, logging, httpx, time, threading, uvicorn
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import create_async_engine
from discord.ext import commands
from dotenv import load_dotenv
from bot.database import Base, engine
from bot.database.models import Apoiador, Base, PixConfig
from bot.shared import set_bot_instance
from bot.config import config as app_config

# Configuração básica de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Carrega variáveis do arquivo .env
load_dotenv()

class DatabaseManager:
    def obter_apoiador(self, discord_id: str, guild_id: str) -> Apoiador | None:
        """Obtém um apoiador pelo Discord ID e Guild ID"""
        with Session(engine) as session:
            return session.query(Apoiador).filter(
                Apoiador.discord_id == discord_id,
                Apoiador.guild_id == guild_id
            ).first()

class HugMeBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        self.db = DatabaseManager()
        self.web_thread = None
        self.config = app_config
        super().__init__(
            command_prefix='!',  # Mantém prefixo para comandos tradicionais
            intents=discord.Intents.all(),
            application_id=os.getenv('APPLICATION_ID'),
            help_command=None,
            activity=discord.Game(name="Ajudando a comunidade")
        )
        self.db = DatabaseManager()
        
    def start_web_server(self):
        """Inicia o servidor web em uma thread separada"""
        def run_web():
            uvicorn.run("bot.web.main:app", host="0.0.0.0", port=26173, reload=False)
            
        self.web_thread = threading.Thread(target=run_web, daemon=True)
        self.web_thread.start()
        logger.info("Servidor web iniciado na porta 26173")

    async def _init_db(self):
        """Inicialização assíncrona do banco de dados"""
        try:
            # Use create_async_engine para operações async
            async_engine = create_async_engine(self.config.DATABASE_URL)
            async with async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            await async_engine.dispose()
            logger.info("✅ Banco de dados inicializado com sucesso")
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar banco de dados: {e}")
            raise
        
    async def on_member_join(self, member):
        """Apenas loga, sem verificação no banco"""
        logger.info(f"Novo membro: {member.display_name}")
    
    async def setup_hook(self):
        """Configurações iniciais quando o bot está inicializando"""
        try:
            # Primeiro carrega todos os cogs tradicionais
            for filename in os.listdir('./bot/commands'):
                if filename.endswith('.py') and not filename.startswith('_'):
                    try:
                        await self._init_db()  # Inicializa o DB antes de carregar cogs
                        logger.info(f"Banco de dados incializado antes dos cogs")
                        await self.load_extension(f'bot.commands.{filename[:-3]}')
                        logger.info(f"Extensão '{filename}' carregada com sucesso")
                    except Exception as e:
                        logger.error(f"Erro ao carregar cog {filename}: {e}")
            self.start_web_server()
            # Sincroniza comandos slash
            await self.tree.sync()
            logger.info("Comandos slash sincronizados")
            
        except Exception as e:
            logger.error(f"Erro ao carregar extensões: {e}")

    async def on_command_error(self, ctx, error):
        """Tratamento global de erros"""
        if isinstance(error, commands.CommandNotFound):
            return
        logger.error(f"Erro no comando {ctx.command}: {error}")
        await ctx.send(f"⚠️ Ocorreu um erro: {str(error)}")
    
# Cria e executa o bot
if __name__ == '__main__':
    bot = HugMeBot()
    set_bot_instance(bot)
    
    @bot.event
    async def on_ready():
        logger.info(f'Bot conectado como {bot.user}')
        logger.info(f'Comandos disponíveis: {[cmd.name for cmd in bot.commands]}')

    try:
        TOKEN = os.getenv('DISCORD_BOT_TOKEN')
        if not TOKEN:
            raise ValueError("Token do Discord não encontrado no .env")
        bot.run(TOKEN)
    except Exception as e:
        logger.critical(f"Falha ao iniciar o bot: {e}")