from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx
from sqlalchemy.orm import Session
from bot.database import get_db
from bot.database.models import Apoiador
import os
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from starlette.middleware.sessions import SessionMiddleware
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

DISCORD_CLIENT_ID = os.getenv('DISCORD_CLIENT_ID')
DISCORD_CLIENT_SECRET = os.getenv('DISCORD_CLIENT_SECRET')
SESSION_SECRET = os.getenv('SESSION_SECRET')

if not DISCORD_CLIENT_ID or not DISCORD_CLIENT_SECRET:
    raise ValueError("As variáveis 'DISCORD_CLIENT_ID' e 'DISCORD_CLIENT_SECRET' não estão definidas no .env.")
if not SESSION_SECRET:
    raise ValueError("A variável 'SESSION_SECRET' não está definida no .env.")

config = Config('.env')
oauth = OAuth(config)

try:
    oauth.register(
        name='discord',
        client_id=DISCORD_CLIENT_ID,
        client_secret=DISCORD_CLIENT_SECRET,
        authorize_url='https://discord.com/api/oauth2/authorize',
        access_token_url='https://discord.com/api/oauth2/token',
        client_kwargs={'scope': 'identify guilds'},
    )
    logger.info("OAuth Discord registrado com sucesso.")
except Exception as e:
    logger.error(f"Erro ao registrar OAuth Discord: {e}")
    raise

app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)

static_dir = os.path.join(os.path.dirname(__file__), "static")
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/login")
async def login(request: Request):
    redirect_uri = request.url_for('auth')
    return await oauth.discord.authorize_redirect(request, redirect_uri) # type: ignore #funiona normalmente, gloria a deus fiquei umas duas horas arrumando isso 1/2

@app.get("/auth")
async def auth(request: Request):
    try:
        # Verificar o estado (state) para prevenir CSRF
        token = await oauth.discord.authorize_access_token(request) # type: ignore #e isso... 2/2

        # Obter os dados do usuário diretamente da API do Discord
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {token['access_token']}"}
            response = await client.get("https://discord.com/api/users/@me", headers=headers)
            response.raise_for_status()
            user = response.json()

        # Armazenar os dados do usuário na sessão
        request.session['user'] = user
        return RedirectResponse(url='/dashboard')

    except Exception as e:
        logger.error(f"Erro durante a autenticação: {e}")
        raise HTTPException(status_code=500, detail="Erro interno durante a autenticação.")

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    user = request.session.get('user')
    if not user:
        raise HTTPException(status_code=401, detail="Não autenticado")
    
    apoiadores = db.query(Apoiador).all()
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "apoiadores": apoiadores
    })

@app.get("/servers", response_class=HTMLResponse)
async def servers(request: Request):
    user = request.session.get('user')
    if not user:
        raise HTTPException(status_code=401, detail="Não autenticado")
    
    return templates.TemplateResponse("servers.html", {"request": request, "user": user})

@app.get("/commands", response_class=HTMLResponse)
async def commands(request: Request):
    user = request.session.get('user')
    if not user:
        raise HTTPException(status_code=401, detail="Não autenticado")
    
    return templates.TemplateResponse("commands.html", {"request": request, "user": user})