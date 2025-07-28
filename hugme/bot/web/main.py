from datetime import datetime, timedelta, timezone

from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from bot.config import config as app_config
from fastapi import FastAPI, Header, Request, Depends, HTTPException, APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from bot.database import SessionLocal
from bot.database import get_db
from bot.database.models import Apoiador
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from starlette.middleware.sessions import SessionMiddleware
import httpx, os, logging, asyncio, hmac, hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
router = APIRouter()


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
    if oauth.discord is None:
        raise RuntimeError("O Cliente OAuth do Discord não foi encontrado Episodio I: The Phantom Error")
    return await oauth.discord.authorize_redirect(request, redirect_uri)

async def fetch_with_retry(client,url,headers,max_retries=5, delay=5):
    for attempt in range(max_retries):
        try:
            response = await client.get(url,headers=headers)
            response.raise_for_status()
            return response
        except httpx.ConnectTimeout as e:
            if attempt < max_retries - 1:
                logger.warning(f"Tentativa {attempt + 1} falhou. Tentando novamente em {delay} segundos...")
                await asyncio.sleep(delay)
            else:
                raise e
    raise httpx.ConnectTimeout("Todas as tentativas falharam.")

@app.get("/auth")
async def auth(request: Request):
    try:
        logger.info("Iniciando processo de autenticação.")
        if oauth.discord is None:
            raise RuntimeError("o Cliente OAuth do Discord não foi encontrado, Episodio II: Queda do Access_Token")
        token = await oauth.discord.authorize_access_token(request)
        if not token:
            raise ValueError("Token de acesso não retornado pelo Discord.")
        logger.info(f"Token de acesso obtido: {token}")

        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {token['access_token']}"}
            response = await client.get("https://discord.com/api/users/@me", headers=headers)
            response.raise_for_status()
            user = response.json()

        request.session['user'] = {**user,
        'access_token': token['access_token'],
        'refresh_token': token.get('refresh_token')                           
        }
        logger.info("Autenticação concluída com sucesso.")
        return RedirectResponse(url='/dashboard')

    except httpx.HTTPStatusError as e:
        logger.error(f"Erro na requisição à API do Discord: {e.response.status_code} - {e.response.text}")
        raise HTTPException(status_code=500, detail="Falha na comunicação com o Discord.")
    except Exception as e:
        logger.error(f"Erro durante a autenticação: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")
    
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    user = request.session.get('user')
    if not user:
        raise HTTPException(status_code=401, detail="Não autenticado")

    # Verificar permissões de admin
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {user['access_token']}"}
        try:
            response = await client.get(
                "https://discord.com/api/users/@me/guilds",
                headers=headers
            )
            guilds = response.json()
            user['admin'] = any(guild.get('permissions', 0) & 0x8 for guild in guilds)
        except Exception:
            user['admin'] = False

    apoiadores = db.query(Apoiador).all()
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "apoiadores": apoiadores,
        "now": datetime.now(timezone.utc)
    })

@app.get("/servers", response_class=HTMLResponse)
async def servers(request: Request):
    user = request.session.get('user')
    if not user:
        raise HTTPException(status_code=401, detail="Não autenticado")

    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {user['access_token']}"}
        try:
            response = await client.get(
                "https://discord.com/api/users/@me/guilds",
                headers=headers
            )
            response.raise_for_status()

            # Forçar a codificação UTF-8
            response_text = response.text.encode('utf-8').decode('utf-8')

            guilds_raw=response.json()

            guilds = [guild for guild in guilds_raw 
                if (guild.get('permissions', 0) & 0x8)
            ]
            
            for guild in guilds:
                guild['is_admin'] = True

            return templates.TemplateResponse("servers.html", {
                "request": request,
                "user": user,
                "guilds": guilds
            })

        except httpx.HTTPStatusError as e:
            logger.error(f"Erro na requisição à API do Discord: {e.response.status_code} - {e.response.text}")
            raise HTTPException(
                status_code=503,
                detail="Falha na comunicação com o Discord."
            )
        except ValueError as e:
            logger.error(f"Erro ao decodificar JSON: {e}. Resposta: {response.text}")  # type: ignore
            raise HTTPException(
                status_code=500,
                detail="Resposta inválida da API do Discord."
            )
        except Exception as e:
            logger.error(f"Erro ao obter servidores: {e}")
            raise HTTPException(
                status_code=500,
                detail="Erro interno ao carregar servidores."
            )
    
@app.get("/commands", response_class=HTMLResponse)
async def commands(request: Request):
    user = request.session.get('user')
    if not user:
        raise HTTPException(status_code=401, detail="Não autenticado")

async def verify_webhook_signature(request: Request, body: bytes) -> bool:
    if not app_config.WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")
    
    signature = request.headers.get("x-pagbank-signature")
    if not signature:
        return False
        
    digest = hmac.new(
        app_config.WEBHOOK_SECRET.encode(), 
        body, 
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(digest, signature)
async def pagbank_webhook(request: Request):
    try:
        # Get raw body for HMAC verification
        body = await request.body()
        
        # Verify signature
        if not await verify_webhook_signature(request, body):
            raise HTTPException(status_code=403, detail="Invalid signature")

        data = await request.json()
        reference_id = data.get("reference_id")
        
        with SessionLocal() as session:
            apoiador = session.query(Apoiador).filter_by(id_pagamento=reference_id).first()
            if not apoiador:
                raise HTTPException(status_code=404, detail="Apoiador not found")

            # Update supporter status
            apoiador.ultimo_pagamento = datetime.now(timezone.utc)
            apoiador.data_expiracao = datetime.now(timezone.utc) + timedelta(days=30)
            apoiador.ativo = True
            session.commit()

        return {"status": "success"}
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
security = HTTPBearer()

async def get_current_admin(credentals: HTTPAuthorizationCredentials = Depends(security)):
    if credentals.credentials != app_config.ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="invalid perimieter")
    return True

@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(
    request: Request,
    db: Session = Depends(get_db)
):
    user = request.session.get('user')
    if not user:
        raise HTTPException(status_code=401, detail="Não autenticado")

    # Verificar permissões de admin
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {user['access_token']}"}
        try:
            response = await client.get(
                "https://discord.com/api/users/@me/guilds",
                headers=headers
            )
            guilds = response.json()
            if not any(guild.get('permissions', 0) & 0x8 for guild in guilds):
                raise HTTPException(status_code=403, detail="Acesso negado")
        except Exception as e:
            raise HTTPException(status_code=403, detail="Falha ao verificar permissões")

    metricas = await admin_metric()
    apoiadores = db.query(Apoiador).all()

    return templates.TemplateResponse("admin.html", {
        "request": request,
        "metricas": metricas,
        "apoiadores": apoiadores,
        "now": datetime.now(timezone.utc)
    })

@app.get("/admin/metrics", dependencies=[Depends(get_current_admin)])
async def admin_metric():
    with SessionLocal() as session:
        total = session.query(Apoiador).count()
        active = session.query(Apoiador).filter_by(ativo=True).count()
        expired = session.query(Apoiador).filter(
            Apoiador.data_expiracao < datetime.now(timezone.utc)
        ).count()
        return {
            "total_donations": total,
            "active_supporters": active,
            "expired_supporters": expired,
            "renewal_rate": round((active / total) * 100, 2) if total else 0
        }