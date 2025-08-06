import discord, os, logging, httpx, time
from sqlalchemy.orm import Session
from discord.ext import commands
from dotenv import load_dotenv
from bot.database import Base, engine
from bot.database.models import Apoiador, Base, PixConfig
from bot.shared import set_bot_instance

# Configuração básica de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Carrega variáveis do arquivo .env
load_dotenv()

class DatabaseManager:
    #json de testes pelamor de deus nao use no prod 🙏🙏🙏
    async def criar_qrcode_pix(self, valor: float, descricao: str):
        headers = {
            "Authorization": f"Bearer {os.getenv('PAGBANK_API_KEY')}",
            "Content-Type": "application/json",
            "x-api-version": "4.0"
        }
        payload = {
            "reference_id": f"doacao_{int(time.time())}",
            "customer":{
                "name": "Teste Sandbox",
                "email":"teste@sandbox.pagseguro.com.br",
                "tax_id": "12345678909",
            },
            "items": [{
                "reference_id": "item-1",
                "name": descricao[:100],
                "quantity": 1,
                "unit_amount": int(valor * 100)
            }],
            "qr_codes": [{
            "amount": {"value": int(valor * 100)},
            "expiration_date": "2025-08-31T23:59:59-03:00"
            }],
            "notification_urls": [
                "https://example.com/notifications"
            ]
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(
                    f"{os.getenv('PAGBANK_ENDPOINT')}/orders",
                    json=payload,
                    headers=headers
                )
                resp.raise_for_status()
            
                data = resp.json()
                # Busca o link de imagem PNG
                links = data["qr_codes"][0].get("links", [])
                for link in links:
                    if link.get("media") == "image/png":
                        return link["href"]
                # Fallback para primeiro link
                if links:
                    return links[0]["href"]
                raise RuntimeError("Nenhum link de QR Code encontrado na resposta")
            
            except httpx.HTTPStatusError as e:
                logger.error(f"Erro PagBank [{e.response.status_code}]: {e.response.text}")
                raise
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
        super().__init__(
            command_prefix='!',  # Mantém prefixo para comandos tradicionais
            intents=discord.Intents.all(),
            application_id=os.getenv('APPLICATION_ID'),
            help_command=None,
            activity=discord.Game(name="Ajudando a comunidade")
        )
        self.db = DatabaseManager()
        self._init_db()

    def _init_db(self):
        """Cria apenas as tabelas necessárias"""
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