from os import getenv
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Required core settings
    DISCORD_TOKEN = getenv('DISCORD_BOT_TOKEN')
    DATABASE_URL = getenv('DATABASE_URL')
    APPLICATION_ID = getenv('APPLICATION_ID')
    
    # Ko-fi
    KOFI_LOG_CHANNEL_ID = getenv('KOFI_LOG_CHANNEL_ID')
    KOFI_VERIFICATION_TOKEN = getenv('KOFI_TOKEN')
    # Webhook and security settings
    WEBHOOK_SECRET = getenv('WEBHOOK_SECRET')
    ADMIN_TOKEN = getenv('ADMIN_TOKEN', '')
    DISCORD_DONOHOOK = getenv('DISCORD_WEBHOOK_URL')
    

    # Environment detection
    USE_NGROK = getenv('USE_NGROK', 'false').lower() == 'true'
    NGROK_URL = getenv('NGROK_URL', '')
    FLY_URL = getenv('FLY_URL', '')
    BASE_URL = NGROK_URL if USE_NGROK else FLY_URL

    def __init__(self):
        if not all([self.DISCORD_TOKEN, self.DATABASE_URL]):
            raise ValueError("Missing required environment variables")
        if not self.BASE_URL:
            raise ValueError("Missing BASE_URL configuration")