import discord, os, logging
from discord.ext import commands
from dotenv import load_dotenv
from bot.database import Base, engine

# Configuração básica de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Carrega variáveis do arquivo .env
load_dotenv()

class HugMeBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(
            command_prefix='!',  # Mantém prefixo para comandos tradicionais
            intents=discord.Intents.all(),
            application_id=os.getenv('APPLICATION_ID'),
            help_command=None,
            activity=discord.Game(name="Ajudando a comunidade")
        )
        self._init_db()

    def _init_db(self):
        """Cria apenas as tabelas necessárias"""
        from bot.database.models import Base
        Base.metadata.create_all(bind=engine)

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
                        await self.load_extension(f'bot.commands.{filename[:-3]}')
                        logger.info(f"Extensão '{filename}' carregada com sucesso")
                    except Exception as e:
                        logger.error(f"Erro ao carregar cog {filename}: {e}")
            
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