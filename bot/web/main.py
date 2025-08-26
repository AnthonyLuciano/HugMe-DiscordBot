import asyncio, hashlib, hmac, json, logging, os, re, threading
from datetime import datetime, timedelta, timezone
from queue import Queue

import httpx
from apscheduler.schedulers.background import BackgroundScheduler
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.config import Config
from starlette.middleware.sessions import SessionMiddleware

from bot.config import config as app_config
from bot.database import SessionLocal, get_db
from bot.database.models import Apoiador, GuildConfig
from bot.servicos.VerificacaoMembro import VerificacaoMembro
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
    logger.info("OAuth do Discord registrado com sucesso.")
except Exception as e:
    logger.error(f"Erro ao registrar OAuth do Discord: {e}")
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
            for attempt in range(3):
                try:
                    task()
                    break
                except Exception as e:
                    if attempt == 2:
                        logger.error(f"Falha na execução da tarefa após 3 tentativas: {str(e)}")
        finally:
            retry_queue.task_done()

worker_thread = threading.Thread(target=retry_worker)
worker_thread.daemon = True
worker_thread.start()
    
security = HTTPBearer()

async def get_current_admin(credentals: HTTPAuthorizationCredentials = Depends(security)):
    if credentals.credentials != app_config.ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Permissão inválida")
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

scheduler = BackgroundScheduler()
scheduler.add_job(check_expirations, 'interval', hours=6)
scheduler.start()

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    user = request.session.get("user")
    return templates.TemplateResponse("home.html", {"request": request, "user": user})

@app.get("/status")
async def status():
    return {"message": "Integração Ko-fi/Discord ativa!"}

@app.get("/login")
async def login(request: Request):
    redirect_uri = request.url_for('auth')
    if oauth.discord is None:
        raise RuntimeError("Cliente OAuth do Discord não encontrado (Episódio I - O Erro Fantasma)")
    return await oauth.discord.authorize_redirect(request, redirect_uri)

async def fetch_with_retry(client,url,headers,max_retries=5, delay=5):
    for attempt in range(max_retries):
        try:
            response = await client.get(url,headers=headers)
            response.raise_for_status()
            return response
        except httpx.ConnectTimeout as e:
            if attempt < max_retries - 1:
                logger.warning(f"Tentativa {attempt + 1} falhou, sacanagem. Tentando novamente em {delay} segundos...")
                await asyncio.sleep(delay)
            else:
                raise e
    raise httpx.ConnectTimeout("Todas as tentativas falharam, hora do debugging.")

@app.get("/auth")
async def auth(request: Request):
    try:
        logger.info("Iniciando autenticação do usuário.")
        if oauth.discord is None:
            raise RuntimeError("Cliente OAuth do Discord não encontrado (Episódio II - Ataque do Auth-Token)")
        token = await oauth.discord.authorize_access_token(request)
        if not token:
            raise ValueError("Token de acesso não retornado pelo Discord. ai lasca tambem.")
        logger.info(f"Token de acesso obtido com sucesso: {token}")

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
        logger.error(f"Erro na API do Discord: {e.response.status_code} - {e.response.text}")
        raise HTTPException(status_code=500, detail="Falha na comunicação com o Discord, ai complica.")
    except Exception as e:
        logger.error(f"Erro durante a autenticação: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")
    
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    user = request.session.get('user')
    if not user:
        raise HTTPException(status_code=401, detail="Não autenticado.")

    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {user['access_token']}"}
        try:
            response = await client.get("https://discord.com/api/users/@me/guilds", headers=headers)
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
        raise HTTPException(status_code=401, detail="Não autenticado, se quer oque amigo?")

    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {user['access_token']}"}
        try:
            response = await client.get("https://discord.com/api/users/@me/guilds", headers=headers)
            response.raise_for_status()

            response_text = response.text.encode('utf-8').decode('utf-8')
            guilds_raw = response.json()
            guilds = [guild for guild in guilds_raw if (guild.get('permissions', 0) & 0x8)]
            
            for guild in guilds:
                guild['is_admin'] = True

            return templates.TemplateResponse("servers.html", {
                "request": request,
                "user": user,
                "guilds": guilds
            })

        except httpx.HTTPStatusError as e:
            logger.error(f"Erro na API do Discord: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=503, detail="Falha na comunicação com o Discord.")
        except ValueError as e:
            logger.error(f"Erro ao decodificar JSON: {e}. Resposta: {response.text}")  # type: ignore
            raise HTTPException(status_code=500, detail="Resposta inválida da API do Discord.")
        except Exception as e:
            logger.error(f"Erro ao obter servidores: {e}")
            raise HTTPException(status_code=500, detail="Erro interno ao carregar servidores.")

@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request, db: Session = Depends(get_db)):
    user = request.session.get('user')
    if not user:
        raise HTTPException(status_code=401, detail="Não autenticado")

    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {user['access_token']}"}
        try:
            response = await client.get("https://discord.com/api/users/@me/guilds", headers=headers)
            guilds = response.json()
            if not any(guild.get('permissions', 0) & 0x8 for guild in guilds):
                raise HTTPException(status_code=403, detail="Acesso negado")
        except Exception as e:
            logger.error(f"Falha ao verificar permissões de admin: {e}")
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
        expired = session.query(Apoiador).filter(Apoiador.data_expiracao < datetime.now(timezone.utc)).count()
        pending_roles = session.query(Apoiador).filter_by(ativo=True, cargo_atribuido=False).count()
        webhook_failures = session.query(func.sum(GuildConfig.webhook_failures)).scalar() or 0
        
        logger.info(f"Métricas carregadas: total={total}, ativos={active}, expirados={expired}, roles pendentes={pending_roles}, falhas webhook={webhook_failures}")

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
        raise HTTPException(status_code=400, detail="guild_id ou role_id ausente, ai me quebra")
    with SessionLocal() as session:
        guild_config = session.query(GuildConfig).filter_by(guild_id=guild_id).first()
        if not guild_config:
            guild_config = GuildConfig(guild_id=guild_id, cargo_apoiador_id=role_id)
        else:
            guild_config.cargo_apoiador_id = role_id
        
        session.add(guild_config)
        session.commit()
        logger.info(f"Cargo de apoiador atualizado para guild_id={guild_id}, role_id={role_id}")
    
    return {"status": "sucesso", "guild_id": guild_id, "role_id": role_id}

@app.post("/webhook")
async def legacy_webhook(request: Request):
    logger.warning("Endpoint legacy webhook chamado, redirecionando para /kofi-webhook")
    return await kofi_webhook(request)

@app.post("/kofi-webhook")
async def kofi_webhook(request: Request):
    try:
        form_data = await request.form()
        if "data" not in form_data:
            raise HTTPException(status_code=400, detail="Campo 'data' ausente")
        
        data = json.loads(form_data["data"])
        transaction_id = data.get("transaction_id", f"kofi_{int(datetime.now(timezone.utc).timestamp())}")

        if "verification_token" in data and app_config.KOFI_TOKEN:
            if data["verification_token"] != app_config.KOFI_TOKEN:
                raise HTTPException(status_code=403, detail="Token de verificação inválido")

        if data["type"] not in ["Donation", "Subscription"]:
            return {"status": "ignorado"}

        for source in [data.get("from_name"), data.get("message")]:
            if source and (match := re.search(r"(?:discord\.com/users/)?(\d{17,19})", str(source))):
                discord_id = match.group(1)
                break
        else:
            discord_id = "kofi_anon_" + str(int(datetime.now(timezone.utc).timestamp()))

        with SessionLocal() as session:
            exists_dupped = session.query(Apoiador).filter_by(id_pagamento=transaction_id).first()
            if exists_dupped:
                logger.warning(f"Transação Ko-fi duplicada detectada: {transaction_id}")
                return {"status": "duplicado"}
            
            apoiador = Apoiador(
                discord_id=discord_id,
                guild_id="0",
                id_pagamento=transaction_id,
                tipo_apoio="kofi",
                email_doador=data.get("email"),
                valor_doacao=int(float(data["amount"]) * 100),
                data_inicio=datetime.now(timezone.utc),
                data_expiracao=datetime.now(timezone.utc) + timedelta(days=30) if data["type"] == "Subscription" else None,
                ativo=True,
                ja_pago=True,
            )
            session.add(apoiador)
            session.commit()
            logger.info(f"Apoiador registrado: {discord_id}, tipo={data['type']}, valor={data['amount']}")
        bot = get_bot_instance()
        if bot:
            verificador = VerificacaoMembro(bot)
            cargo_apoiador = app_config.APOIADOR_ID2
        
            if discord_id and not discord_id.startswith("kofi_anon_"):
                sucesso = await verificador.atribuir_cargo_apos_pagamento(
                    discord_id,
                    0,
                    cargo_apoiador
                )
                if sucesso:
                    logger.info(f"Cargo atribuído automaticamente para {discord_id} via Ko-fi")
                else:
                    logger.warning(f"Falha ao atribuir cargo para {discord_id} via Ko-fi")
        else:
            logger.warning("Bot instance não disponível para atribuir cargo via Ko-fi")



        donohook_url = app_config.DISCORD_DONOHOOK
        if donohook_url:
            embed = {
                "title": "📊 Nova Doação Ko-fi",
                "description": f"De: {data.get('from_name', 'Anônimo')}",
                "color": 0x29ABE2,
                "fields": [
                    {"name": "Valor", "value": f"{data['amount']} {data['currency']}"},
                    {"name": "Discord ID", "value": discord_id or "Não informado"},
                    {"name": "Email", "value": data.get('email', 'Não informado')},
                    {"name": "Mensagem", "value": data.get('message', 'Nenhuma')[:1000]},
                    {"name": "Tipo", "value": "Assinatura" if data["type"] == "Subscription" else "Doação Única"},
                    {"name": "Cargo Atribuído", "value": "✅ Sim" if sucesso else "❌ Falha" if discord_id and not discord_id.startswith("kofi_anon_") else "⏸️ Anônimo"}
                ]
            }
            async with httpx.AsyncClient() as client:
                await client.post(donohook_url, json={"embeds": [embed]})
                logger.info(f"Notificação enviada para Discord via webhook: {donohook_url}")

        return {"status": "sucesso"}
    except Exception as e:
        logger.error(f"Erro no webhook do Ko-fi: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def verify_kofi_webhook_signature(request: Request, body: bytes) -> bool:
    if not app_config.WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="Webhook secret não configurado, porque não em ou dev?")
    
    signature = request.headers.get("x-ko-signature")
    
    if not signature:
        return False
    
    expected_signature = hmac.new(
        app_config.WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected_signature, signature)
