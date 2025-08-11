from os import getenv
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Required core settings
    DISCORD_TOKEN = getenv('DISCORD_BOT_TOKEN')
    PAGBANK_API_KEY = getenv('PAGBANK_API_KEY')
    DATABASE_URL = getenv('DATABASE_URL')
    APPLICATION_ID = getenv('APPLICATION_ID')
    PAGBANK_EMAIL = getenv('PAGBANK_EMAIL')
    KOFI_API_KEY = getenv('KOFI_API_KEY')
    KOFI_ENDPOINT = getenv('KOFI_ENDPOINT')

    # Webhook and security settings
    WEBHOOK_SECRET = getenv('WEBHOOK_SECRET')
    ADMIN_TOKEN = getenv('ADMIN_TOKEN', '')

    # Environment detection
    USE_NGROK = getenv('USE_NGROK', 'false').lower() == 'true'
    NGROK_URL = getenv('NGROK_URL', '')
    FLY_URL = getenv('FLY_URL', '')
    BASE_URL = NGROK_URL if USE_NGROK else FLY_URL

    def __init__(self):
        if not all([self.DISCORD_TOKEN, self.PAGBANK_API_KEY, self.DATABASE_URL]):
            raise ValueError("Missing required environment variables")
        if not self.BASE_URL:
            raise ValueError("Missing BASE_URL configuration")

config = Config()