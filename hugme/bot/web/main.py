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
"""
ola, quem estiver vendo esse codigo, se voce notar que tem comandos em ingles e logs em portugues
é porque o ADM coringou, necessito de ajuda seria :,D
codigo ta mais bagunçado que um quarto de criança, por favor nao notem a bagunça
"""

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

async def _extract_order_id(payload: dict, headers) -> str | None:
    # Checar header primeiro (vem em muitos webhooks do PagBank)
    order_id = headers.get("x-product-id") or headers.get("X-Product-Id")
    if order_id:
        return order_id

    # Checar campos comuns no body
    for key in ("id", "order_id", "reference_id"):
        if payload.get(key):
            return payload.get(key)

    # Checar charges -> reference_id
    charges = payload.get("charges") or []
    if isinstance(charges, list) and charges:
        first = charges[0]
        if isinstance(first, dict):
            return first.get("reference_id") or first.get("id")

    # resource.order_id (caso exista)
    resource = payload.get("resource") or {}
    if isinstance(resource, dict):
        return resource.get("order_id") or resource.get("id")

    return None

async def verify_webhook_signature(request: Request, body: bytes) -> bool:
    if not app_config.PAGBANK_API_KEY:
        raise HTTPException(status_code=500, detail="PagBank token not configured")

    headers = request.headers

    # 1) Se header de autenticidade existir, validar por SHA256(token + "-" + payload_cru)
    authenticity = headers.get("x-authenticity-token") or headers.get("X-Authenticity-Token")
    if authenticity:
        try:
            raw_payload = body.decode("utf-8")
        except UnicodeDecodeError:
            logger.warning("Cannot decode payload as utf-8 for signature check")
            return False

        expected = hashlib.sha256(f"{app_config.PAGBANK_API_KEY}-{raw_payload}".encode("utf-8")).hexdigest()
        return hmac.compare_digest(expected, authenticity)

    # 2) Fallback: validação ativa (consulta na API do PagBank)
    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        logger.warning("Webhook payload is not valid JSON")
        return False

    order_id = await _extract_order_id(payload, headers)
    if not order_id:
        logger.warning("No order_id found in webhook payload or headers")
        return False

    # Confirmar com a API do PagBank
    endpoint = app_config.PAGBANK_ENDPOINT.rstrip("/")  # ex: https://sandbox.api.pagseguro.com
    url = f"{endpoint}/orders/{order_id}"

    headers_out = {
        "Authorization": f"Bearer {app_config.PAGBANK_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        timeout = httpx.Timeout(5.0, connect=3.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url, headers=headers_out)
        if resp.status_code != 200:
            logger.error(f"PagBank order lookup failed ({resp.status_code}): {resp.text}")
            return False

        order_data = resp.json()
        # Verifique status de ordem ou charges
        if order_data.get("status") == "PAID":
            return True

        for ch in order_data.get("charges", []) or []:
            if ch.get("status") == "PAID":
                return True

        logger.info(f"Order {order_id} not PAID (order_status={order_data.get('status')})")
        return False

    except httpx.RequestError as e:
        logger.error(f"HTTP error when confirming order {order_id}: {e}")
        return False
    except Exception as e:
        logger.exception(f"Unexpected error verifying webhook for order {order_id}: {e}")
        return False

@app.post("/pagbank-webhook")
async def pagbank_webhook(request: Request):
    try:
        body = await request.body()
        if not await verify_webhook_signature(request, body):
            raise HTTPException(status_code=403, detail="invalid signature")
        
        data = json.loads(body)
        
        logger.info(f"Full webhook data: {data}")  # Log full payload
        
        charges = data.get("charges", [])
        
        # Get first charge's status if available
        charge_status = charges[0].get("status", "").upper() if charges else ""

        # Debug logging with more details
        logger.info(f"status: {charge_status}")
        logger.info(f"Reference ID: {charges[0].get('reference_id') if charges else 'N/A'}")

        # More flexible status check
        if charge_status != "PAID":
            logger.warning(f"Ignorando webhook - status não é PAID: {charge_status}")
            return {"status": "ignored"}
        
        reference_id = charges[0].get("reference_id") if charges else None
        if not reference_id:
            raise HTTPException(status_code=400, detail="Missing reference_id")
        
        with SessionLocal() as session:
            apoiador = session.query(Apoiador).filter_by(id_pagamento=reference_id).first()
            if not apoiador:
                logger.warning(f"Pagamento não vinculado: {reference_id}")
                return {"status": "apoiador_not_found"}
            
             # Atualizar informações do pagamento
            apoiador.valor_doacao = charges[0].get("amount", {}).get("value") if charges else None
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
            donohook_url= app_config.DISCORD_DONOHOOK
            if donohook_url and charges:
                charge = charges[0]
                customer = charge.get("customer", {})
                
                embed = {
                    "title": "💰 Nova Doação via PIX",
                    "color": 0x32CD32,
                    "fields": [
                        {"name": "Valor", "value": f"R$ {float(charge.get('amount', {}).get('value', 0)) / 100:.2f}"},
                        {"name": "Discord ID", "value": apoiador.discord_id if apoiador else "Não vinculado"},
                        {"name": "Email", "value": customer.get('email', 'Não informado')},
                        {"name": "Status", "value": charge_status},
                        {"name": "ID Transação", "value": charge.get('id', 'N/A')}
                    ]
                }
                async with httpx.AsyncClient() as client:
                    await client.post(donohook_url, json={"embeds": [embed]})
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

@app.get("/")
async def post_root():
    return {"error": "Use specific endpoints like /pagbank-webhook or /kofi-webhook"}

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
    raise httpx.ConnectTimeout("Todas as tentativas falharam, é foda hora do debugging.")

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
        raise HTTPException(status_code=401, detail="Não autenticado, ai você me quebra usuario ('-')")

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
        form_data = await request.form()
        if "data" not in form_data:
            raise HTTPException(status_code=400, detail="Missing data field")
        
        data = json.loads(form_data["data"])
        transaction_id = data.get("transaction_id", f"kofi_{int(datetime.now(timezone.utc).timestamp())}")


        # Token verification
        if "verification_token" in data and app_config.KOFI_TOKEN:
            if data["verification_token"] != app_config.KOFI_TOKEN:
                raise HTTPException(status_code=403, detail="Invalid verification token")

        if data["type"] not in ["Donation", "Subscription"]:
            return {"status": "ignored"}

        # Extract Discord ID
        for source in [data.get("from_name"), data.get("message")]:
            if source and (match := re.search(r"(?:discord\.com/users/)?(\d{17,19})", str(source))):
                discord_id = match.group(1)
                break
        else:
            discord_id = "kofi_anon_" + str(int(datetime.now(timezone.utc).timestamp()))  # Valor alternativo

        # Database operations
        with SessionLocal() as session:
            exists_dupped = session.query(Apoiador).filter_by(
                id_pagamento=transaction_id
            ).first()
            if exists_dupped:
                logger.warning(f"Duplicate Ko-fi transaction detected: {transaction_id}")
                return {"status": "duplicate"}
            apoiador = Apoiador(
                discord_id=discord_id,
                guild_id="0",  # Global donation
                id_pagamento=data.get("transaction_id", f"kofi_{int(datetime.now(timezone.utc).timestamp())}"),
                tipo_apoio="kofi",
                email_doador=data.get("email"),
                valor_doacao=int(float(data["amount"]) * 100),  # Convert to cents
                data_inicio=datetime.now(timezone.utc),
                data_expiracao=datetime.now(timezone.utc) + timedelta(days=30) if data["type"] == "Subscription" else None,
                ativo=True
            )
            session.add(apoiador)
            session.commit()

        # Discord notification
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
                    {"name": "Tipo", "value": "Assinatura" if data["type"] == "Subscription" else "Doação Única"}
                ]
            }
            async with httpx.AsyncClient() as client:
                await client.post(donohook_url, json={"embeds": [embed]})

        return {"status": "success"}
    except Exception as e:
        logger.error(f"Ko-fi webhook error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def verify_kofi_webhook_signature(request: Request, body: bytes) -> bool:
    if not app_config.WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")
    
    signature = request.headers.get("x-ko-signature")
    
    if not signature:
        return False
    
    expected_signature = hmac.new(
        app_config.WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256,
        ).hexdigest()
    return hmac.compare_digest(expected_signature, signature)
