from queue import Queue
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi import FastAPI, Header, Request, Depends, HTTPException, APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session
from bot.config import config as app_config
from bot.database import SessionLocal
from bot.database import get_db
from bot.database.models import Apoiador, GuildConfig
from bot.servicos.VerificacaoMembro import VerificacaoMembro
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from starlette.middleware.sessions import SessionMiddleware
import httpx, os, logging, asyncio, hmac, hashlib, threading

from bot.shared import get_bot_instance

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
router = APIRouter()
bot = get_bot_instance()

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

retry_queue = Queue()

def retry_worker():
    while True:
        task = retry_queue.get()
        if task is None:
            break
        try:
            # Execute the task with retry logic
            for attempt in range(3):
                try:
                    task()
                    break
                except Exception as e:
                    if attempt == 2:
                        logger.error(f"Retry failed: {str(e)}")
        finally:
            retry_queue.task_done()

# Start worker thread when module loads
worker_thread = threading.Thread(target=retry_worker)
worker_thread.daemon = True
worker_thread.start()

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
        body = await request.body()
        if not await verify_webhook_signature(request, body):
            raise HTTPException(status_code=403, detail="invalid signature")
        
        data = await request.json()
        logger.info(f"Full webhook data: {data}")  # Log full payload
        
        event_type = data.get("event")
        charge = data.get("charge", {})
        charge_status = charge.get("status", "").upper() if charge else ""

        # Debug logging with more details
        logger.info(f"Received event: {event_type}, status: {charge_status}")
        logger.info(f"Reference ID: {charge.get('reference_id')}")

        # More flexible status check
        if event_type != "PAYMENT_RECEIVED" or charge_status != "PAID":
            logger.warning(f"Ignoring event - reason: "
                           f"event_type_match={event_type == 'PAYMENT_RECEIVED'}, "
                           f"status_match={charge_status == 'PAID'}")
            return {"status": "ignored"}
        
        # ... rest of the function remains the same ...
        
        reference_id = charge.get("reference_id")
        if not reference_id:
            raise HTTPException(status_code=400, detail="Missing reference_id")
        
        with SessionLocal() as session:
            apoiador = session.query(Apoiador).filter_by(id_pagamento=reference_id).first()
            if not apoiador:
                logger.warning(f"Pagamento não vinculado: {reference_id}")
                return {"status": "apoiador_not_found"}
            
             # Atualizar informações do pagamento
            apoiador.valor_doacao = charge.get("amount", {}).get("value")
            apoiador.metodo_pagamento = "pix"
            apoiador.data_pagamento = datetime.now(timezone.utc)
            apoiador.ultimo_pagamento = datetime.now(timezone.utc)
            apoiador.data_expiracao = datetime.now(timezone.utc) + timedelta(days=30)
            apoiador.ativo = True
            
            # Get guild config
            guild_config = session.query(GuildConfig).filter_by(guild_id=apoiador.guild_id).first()
            if guild_config and guild_config.cargo_apoiador_id:
                try:
                    verificador = VerificacaoMembro(bot)
                    success = await verificador.atribuir_cargo_apos_pagamento(
                        apoiador.discord_id,
                        int(apoiador.guild_id),
                        int(guild_config.cargo_apoiador_id)
                    )
                    if success:
                        apoiador.cargo_atribuido = True
                        logger.info(f"Cargo atribuído: {apoiador.discord_id}")
                except Exception as e:
                    logger.error(f"Erro ao atribuir cargo: {str(e)}")
                    # Increment failure counter
                    if guild_config:
                        guild_config.webhook_failures += 1
            
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

def check_expirations():
    with SessionLocal() as session:
        now = datetime.now(timezone.utc)
        expired = session.query(Apoiador).filter(
            Apoiador.data_expiracao < now,
            Apoiador.ativo == True
        ).all()
        for apoiador in expired:
            apoiador.ativo = False
            logger.info(f"Apoiador expirado: {apoiador.discord_id}")
        
        session.commit()

#inicia schedule quando começa o app
scheduler = BackgroundScheduler()
scheduler.add_job(check_expirations, 'interval', hours=6)
scheduler.start()

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
        "now": datetime.now(timezone.utc),
        "app_config": app_config
    })

@app.get("/admin/metrics", dependencies=[Depends(get_current_admin)])
async def admin_metric():
    with SessionLocal() as session:
        total = session.query(Apoiador).count()
        active = session.query(Apoiador).filter_by(ativo=True).count()
        expired = session.query(Apoiador).filter(
            Apoiador.data_expiracao < datetime.now(timezone.utc)
        ).count()
        pending_roles = session.query(Apoiador).filter_by(
            ativo=True, cargo_atribuido=False
        ).count()
        
        webhook_failures = session.query(func.sum(GuildConfig.webhook_failures)).scalar() or 0
        
        return {
            "total_donations": total,
            "active_supporters": active,
            "expired_supporters": expired,
            "pending_role_assignments": pending_roles,
            "webhook_failure_count": webhook_failures,
            "renewal_rate": round((active / total) * 100, 2) if total else 0
        }

@app.post("/admin/set-role", dependencies=[Depends(get_current_admin)])
async def set_supporter_role(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    guild_id = data.get("guild_id")
    role_id = data.get("role_id")

    if not guild_id or not role_id:
        raise HTTPException(status_code=400, detail="Missing guild_id or role_id")
    with SessionLocal() as session:
        guild_config = session.query(GuildConfig).filter_by(guild_id=guild_id).first()
        if not guild_config:
            guild_config = GuildConfig(guild_id=guild_id, cargo_apoiador_id=role_id)
        else:
            guild_config.cargo_apoiador_id = role_id
        
        session.add(guild_config)
        session.commit()
    
    return {"status": "success", "guild_id": guild_id, "role_id": role_id}
    

@app.post("/pagbank-webhook")
async def handle_pagbank_webhook(request: Request):
    return await pagbank_webhook(request)

# Adicionar esta rota para compatibilidade com notificações antigas

@app.post("/webhook")
async def legacy_webhook(request: Request):
    logger.warning("Legacy webhook endpoint called, redirecting to pagbank-webhook")
    return await pagbank_webhook(request)

from fastapi import Request, HTTPException
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger(__name__)

@app.post("/kofi-webhook")
async def handle_kofi_webhook(request: Request):
    try:
        body = await request.body()
        if not await verify_webhook_signature(request, body):
            raise HTTPException(status_code=403, detail="Invalid signature")
        
        data = await request.json()
        logger.info(f"Received Ko-fi webhook: {data}")
        
        # Lógica para processar a notificação do Ko-fi
        reference_id = data.get("kofi_transaction_id")
        if not reference_id:
            raise HTTPException(status_code=400, detail="Missing kofi_transaction_id")
        
        with SessionLocal() as session:
            apoiador = session.query(Apoiador).filter_by(id_pagamento=reference_id).first()
            if not apoiador:
                logger.warning(f"Payment not linked: {reference_id}")
                return {"status": "apoiador_not_found"}
            
            apoiador.ultimo_pagamento = datetime.now(timezone.utc)
            apoiador.data_expiracao = datetime.now(timezone.utc) + timedelta(days=30)
            apoiador.ativo = True
            
            guild_config = session.query(GuildConfig).filter_by(guild_id=apoiador.guild_id).first()
            if guild_config and guild_config.cargo_apoiador_id:
                try:
                    verificador = VerificacaoMembro(bot)
                    success = await verificador.atribuir_cargo_apos_pagamento(
                        apoiador.discord_id,
                        int(apoiador.guild_id),
                        int(guild_config.cargo_apoiador_id)
                    )
                    if success:
                        apoiador.cargo_atribuido = True
                        logger.info(f"Cargo assigned: {apoiador.discord_id}")
                except Exception as e:
                    logger.error(f"Error assigning role: {str(e)}")
                    if guild_config:
                        guild_config.webhook_failures += 1
            
            session.commit()
            return {"status": "success"}

    except Exception as e:
        logger.error(f"Ko-fi webhook error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def verify_kofi_webhook_signature(request: Request, body: bytes) -> bool:
    if not app_config.WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")
    
    signature = request.headers.get("x-ko-signature")
