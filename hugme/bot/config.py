from os import getenv
from dotenv import load_dotenv

load_dotenv()

class Config:
    DISCORD_TOKEN = getenv('DISCORD_BOT_TOKEN')
    PAGBANK_API_KEY = getenv('API_KEY')
    DATABASE_URL = getenv('DATABASE_URL')

    if not all([DISCORD_TOKEN, PAGBANK_API_KEY, DATABASE_URL]):
        raise ValueError("Variaveis do ambiente faltando! Verifique o seu .env")

config = Config()