# File: /discord-donation-bot/discord-donation-bot/bot/main.py

import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env (como o token do bot)
load_dotenv()

#define os intents necessarios
intents = discord.Intents.default()
intents.message_content = True # Necessário para ler o conteúdo das mensagens

class HugMeBot(commands.Bot):
    async def setup_hook(self):
        await self.load_extension('hugme.bot.commands')

# Cria o bot com prefixo '!' e intents
bot = HugMeBot(command_prefix='!', intents=intents)

# Evento chamado quando o bot está pronto
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} - {bot.user.id}')
    print('------')

# Inicia o bot usando o token do arquivo .env
if __name__ == '__main__':
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    bot.run(TOKEN)