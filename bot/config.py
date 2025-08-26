from os import getenv
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Required core settings
    DISCORD_TOKEN = getenv('DISCORD_BOT_TOKEN')
    DATABASE_URL = getenv('DATABASE_URL')
    APPLICATION_ID = getenv('APPLICATION_ID')
    KOFI_TOKEN = getenv('KOFI_TOKEN')
    KOFI_ENDPOINT = getenv('KOFI_ENDPOINT')
    DISCORD_DONOHOOK = getenv('DISCORD_DONOHOOK_URL')
    DONO_LOG_CHANNEL = getenv('KOFI_LOG_CHANNEL_ID')
    DEEP_API = getenv('DEEP_API')
    DEEP_KEY = getenv('DEEP_KEY')
    
    #Discord
    APOIADOR_ID = getenv('APOIADOR_CARGO_ID')
    APOIADOR_ID2 = getenv('APOIADOR_CARGO_ID2')

    # Webhook and security settings
    WEBHOOK_SECRET = getenv('WEBHOOK_SECRET')
    ADMIN_TOKEN = getenv('ADMIN_TOKEN', '')

    # Environment detection
    USE_NGROK = getenv('USE_NGROK', 'false').lower() == 'true'
    NGROK_URL = getenv('NGROK_URL', '')
    FLY_URL = getenv('FLY_URL', '')
    BASE_URL = NGROK_URL if USE_NGROK else FLY_URL

    def __init__(self):
        if not all([self.DISCORD_TOKEN, self.DEEP_KEY, self.DATABASE_URL]):
            raise ValueError("Missing required environment variables")
        if not self.BASE_URL:
            raise ValueError("Missing BASE_URL configuration")

config = Config()