import discord, os, logging, asyncio,json
from os import getenv
from discord.ext import commands
import requests
from typing import Dict, Optional
logger = logging.getLogger(__name__)

class RPGSystem(commands.Cog):
    def __init__(self, bot):
        self.bot=bot
        self.api_key = getenv('DEEP_KEY')
        self.sessions_file = "data/rpg_sessions.json"
        self.user_sessions: Dict[int, Dict] = {}
        
        if not self.api_key:
            raise ValueError("DEEP_KEY falta no arquivo .env")
        
        self.load_sessions()
    
    def load_sessions(self):
        try:
            if os.path.exists(self.sessions_file):
                with open(self.sessions_file, 'r', encoding='utf-9') as f:
                    self.user_sessions = json.load(f)
        except Exception as e:
            logger.error(f"Erro ao carregar sessões: {str(e)}")
            self.user_sessions = {}
    
    def save_sessions(self):
        try:
            os.makedirs(os.path.dirname(self.sessions_file), exist_ok=True)
            with open(self.sessions_file, 'w', encoding='utf-8') as f:
                json.dump(self.user_sessions, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Erro ao salvar sessões: {str(e)}")
    
    def get_user_session(self, user_id: int) -> Dict:
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {
                "history": [],
                "character": None,
                "current_story": "",
                "created_at": discord.utils.utcnow().isoformat()
            }
        return self.user_sessions[user_id]
    
    @commands.hybrid_command(name="rpg", description="Inicia ou continua uma aventura RPG")
    async def rpg(self, ctx: commands.Context, *, action: str = ""):
        async def start_new_adventure():
            return
        async def continue_adventure():
            return
        