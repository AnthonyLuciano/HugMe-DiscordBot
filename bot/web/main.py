import asyncio, hashlib, hmac, json, logging, os, re, threading
from datetime import datetime, timedelta, timezone
from queue import Queue

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Request
from contextlib import asynccontextmanager
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.middleware.cors import CORSMiddleware as middleware

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.config import Config
from starlette.middleware.sessions import SessionMiddleware

from bot.config import config as app_config
from bot.database import AsyncSessionLocal, get_db
from bot.database.models import Apoiador, GuildConfig
from bot.servicos.VerificacaoMembro import VerificacaoMembro
from bot.shared import get_bot_instance

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app):
    # Inicia o scheduler apenas quando o aplicativo realmente entra em execução (lifespan)
    try:
        try:
            # scheduler é definido abaixo; durante import ele não será iniciado
            if not scheduler.running:
                scheduler.start()
                logger.info("Scheduler iniciado via lifespan do FastAPI.")
        except Exception as e:
            logger.warning(f"Falha ao iniciar o scheduler via lifespan: {e}")
        yield
    finally:
        try:
            if scheduler.running:
                scheduler.shutdown(wait=False)
                logger.info("Scheduler finalizado via lifespan do FastAPI.")
        except Exception as e:
            logger.warning(f"Falha ao finalizar o scheduler via lifespan: {e}")

app = FastAPI(lifespan=lifespan)
app.add_middleware(middleware, allow_origins=["*"], allow_methods=["*"], allow_credentials=True, allow_headers=["*"])
router = APIRouter()
bot = get_bot_instance()

DISCORD_CLIENT_ID = os.getenv('DISCORD_CLIENT_ID')
DISCORD_CLIENT_SECRET = os.getenv('DISCORD_CLIENT_SECRET')
SESSION_SECRET = os.getenv('SESSION_SECRET')

if not DISCORD_CLIENT_ID or not DISCORD_CLIENT_SECRET:
    raise ValueError("As variáveis 'DISCORD_CLIENT_ID' e 'DISCORD_CLIENT_SECRET' não estão definidas no .env.")
if not SESSION_SECRET:
    raise ValueError("A variável 'SESSION_SECRET' não está definida no .env.")

config = Config('.env') if os.path.exists('.env') else Config()
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


async def _resolve_scalars(result):
    """Normalize different Result/Mock shapes and return a 'scalars' object.

    This function is defensive: tests may mock `session.execute` with AsyncMock
    objects that expose `scalars` differently (callable, attribute, returning
    coroutines). We try several shapes and await coroutines when needed.
    """
    # If the whole result is a coroutine, await it first
    if asyncio.iscoroutine(result):
        result = await result

    scalars_attr = getattr(result, "scalars", None)

    # Some tests set attributes directly on `result.scalars` (e.g. AsyncMock().scalars.first = ...)
    # If the attribute already exposes `first`/`all`, prefer using it as-is instead of calling it.
    if scalars_attr is None:
        return None

    if hasattr(scalars_attr, "first") or hasattr(scalars_attr, "all"):
        return scalars_attr

    # Otherwise, if scalars is callable (normal SQLAlchemy API), call it and await if needed
    if callable(scalars_attr):
        scalars = scalars_attr()
        if asyncio.iscoroutine(scalars):
            scalars = await scalars
        return scalars

    return scalars_attr


async def safe_first(result):
    scalars = await _resolve_scalars(result)
    if scalars is None:
        return None
    first_attr = getattr(scalars, "first", None)
    if callable(first_attr):
        maybe = first_attr()
        if asyncio.iscoroutine(maybe):
            return await maybe
        return maybe
    return first_attr


async def safe_all(result):
    scalars = await _resolve_scalars(result)
    if scalars is None:
        return []
    all_attr = getattr(scalars, "all", None)
    if callable(all_attr):
        maybe = all_attr()
        if asyncio.iscoroutine(maybe):
            return await maybe
        return maybe
    return all_attr or []

async def check_expirations():
    """
    FUNÇÃO: check_expirations
    FUNÇÃO: Verifica quais apoiadores tiveram sua assinatura expirada
    
    O QUE FAZ:
    1. Busca todos os apoiadores com data_expiracao < agora e status ativo=True
    2. Marca-os como ativo=False (desativa)
    3. Log no console para rastreamento
    
    ISSO DISPARA: Quando o cargo deve ser removido
    """
    async with AsyncSessionLocal() as session:
        now = datetime.now(timezone.utc)
        result = await session.execute(
            select(Apoiador).where(Apoiador.data_expiracao < now, Apoiador.ativo == True)
        )
        expired = await safe_all(result)
        if expired:
            for apoiador in expired:
                apoiador.ativo = False
                logger.info(f"Apoiador expirado: {apoiador.discord_id}")
            await session.commit()


async def renovar_apoiadores_expirados():
    """
    FUNÇÃO: renovar_apoiadores_expirados
    PROPÓSITO: Reativar automaticamente apoiadores com assinatura Ko-fi que expiraram
    
    O QUE FAZ:
    1. Procura apoiadores com:
       - ativo = False (estão desativados)
       - tipo_apoio = "kofi" (têm assinatura Ko-fi)
       - data_expiracao no passado (expirou o período anterior)
    
    2. Para cada um encontrado:
       - ativo = True (reativa)
       - data_expiracao = agora + 30 dias (estende por mais um mês)
       - Isso simula a renovação automática da assinatura Ko-fi
    
    3. Salva todas as mudanças no banco
    
    RESULTADO: Apoiadores com Ko-fi recebem renovação automática sem ter que reconfirmar
    """
    async with AsyncSessionLocal() as session:
        now = datetime.now(timezone.utc)
        
        # Busca apoiadores expirados com Ko-fi (assinatura recorrente)
        result = await session.execute(
            select(Apoiador).where(
                Apoiador.ativo == False,
                Apoiador.tipo_apoio == "kofi",
                Apoiador.data_expiracao != None
            )
        )
        expired_kofi = await safe_all(result)
        
        renovados = 0
        for apoiador in expired_kofi:
            # Reativa e estende para o próximo mês
            apoiador.ativo = True
            apoiador.data_expiracao = now + timedelta(days=30)
            renovados += 1
            logger.info(f"Apoiador Ko-fi renovado automaticamente: {apoiador.discord_id}")
        
        if renovados > 0:
            await session.commit()
            logger.info(f"Total de apoiadores renovados: {renovados}")


async def reativar_cargos_da_assinatura():
    """
    FUNÇÃO: reativar_cargos_da_assinatura
    PROPÓSITO: Reaplica cargos de Discord para apoiadores recentemente renovados
    
    O QUE FAZ:
    1. Procura apoiadores que foram recentemente reativados:
       - ativo = True
       - cargo_atribuido = False (ainda não têm o cargo aplicado neste ciclo)
       - tipo_apoio = "kofi" (assinatura automática)
    
    2. Para cada um:
       - Tenta atribuir o cargo no Discord
       - Se bem-sucedido, marca cargo_atribuido = True
    
    3. Salva tudo no banco
    
    RESULTADO: O usuário automaticamente recebe seu cargo de volta sem fazer nada
    
    NOTA: cargo_atribuido é um flag para não ficarmos tentando aplicar cargo
          infinitamente - serve como "já processamos este ciclo"
    """
    bot = get_bot_instance()
    if not bot:
        logger.warning("Bot instance indisponível para reativar cargos")
        return
    
    async with AsyncSessionLocal() as session:
        # Busca apoiadores recentemente reativados que precisam ter cargo reaplicado
        result = await session.execute(
            select(Apoiador).where(
                Apoiador.ativo == True,
                Apoiador.cargo_atribuido == False,
                Apoiador.tipo_apoio == "kofi"
            )
        )
        need_role = await safe_all(result)
        
        verificador = VerificacaoMembro(bot)
        cargo_apoiador = app_config.APOIADOR_ID2
        
        for apoiador in need_role:
            try:
                # Tenta encontrar o servidor do usuário (bot compartilha com o user)
                for guild in bot.guilds:
                    res = await verificador.atribuir_cargo_apos_pagamento(
                        apoiador.discord_id,
                        guild.id,
                        cargo_id=cargo_apoiador,
                        nivel=getattr(apoiador, 'nivel', None)
                    )
                    if res:
                        apoiador.cargo_atribuido = True
                        logger.info(f"Cargo reaplicado para: {apoiador.discord_id} no servidor {guild.id}")
                        break
            except Exception as e:
                logger.error(f"Erro ao reativar cargo para {apoiador.discord_id}: {e}")
        
        await session.commit()


# Use AsyncIOScheduler to run the async task periodically
scheduler = AsyncIOScheduler()

# A cada 6 horas, verifica expiração (desativa apoios vencidos)
scheduler.add_job(check_expirations, 'interval', hours=6)

# A cada 12 horas, renova apostadores Ko-fi expirados (reativa automaticamente)
scheduler.add_job(renovar_apoiadores_expirados, 'interval', hours=12)

# A cada 2 horas, reaplica cargos aos renovados (isso roda mais frequente porque é crítico)
scheduler.add_job(reativar_cargos_da_assinatura, 'interval', hours=2)


@app.get("/")
async def home(request: Request):
    user = request.session.get("user")
    return {"user": user, "message": "Bem-vindo à API do HugMe Bot"}

@app.get("/status")
async def status():
    return {"message": "Integração Ko-fi/Discord ativa!"}

@app.get("/test")
async def test_endpoint():
    return {"message": "Endpoint de teste funcionando!"}

@app.get("/login")
async def login(request: Request):
    # Build redirect_uri from the actual request to include port
    redirect_uri = f"{request.url.scheme}://{request.url.netloc}/auth"
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
    
@app.get("/dashboard")
async def dashboard(request: Request, db: AsyncSession = Depends(get_db)):
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

    result = await db.execute(select(Apoiador))
    apoiadores = await safe_all(result)
    
    # Retorne JSON em vez de template
    return {
        "user": user,
        "apoiadores": [apoiador.__dict__ for apoiador in apoiadores],  # Ou serialize adequadamente
        "now": datetime.now(timezone.utc).isoformat()
    }

@app.get("/servers")
async def servers(request: Request):
    user = request.session.get('user')
    if not user:
        raise HTTPException(status_code=401, detail="Não autenticado, se quer oque amigo?")

    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {user['access_token']}"}
        response = await client.get("https://discord.com/api/users/@me/guilds", headers=headers)
        guilds_raw = response.json()
        guilds = [guild for guild in guilds_raw if (guild.get('permissions', 0) & 0x8)]
        
    return {"user": user, "guilds": guilds}

@app.get("/admin")
async def admin_panel(request: Request, db: AsyncSession = Depends(get_db)):
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
    result = await db.execute(select(Apoiador))
    apoiadores = await safe_all(result)

    return {
        "user": user,
        "metricas": metricas,
        "apoiadores": [apoiador.__dict__ for apoiador in apoiadores],
        "now": datetime.now(timezone.utc).isoformat(),
        "app_config": {
            "admin_token": app_config.ADMIN_TOKEN,  # Cuidado: não expor senhas reais
            # Adicione outros campos necessários, mas filtre sensíveis
        }
    }

@app.get("/admin/metrics", dependencies=[Depends(get_current_admin)])
async def admin_metric():
    async with AsyncSessionLocal() as session:
        total_res = await session.execute(select(func.count()).select_from(Apoiador))
        total = total_res.scalar() or 0
        active_res = await session.execute(select(func.count()).select_from(Apoiador).where(Apoiador.ativo == True))
        active = active_res.scalar() or 0
        expired_res = await session.execute(select(func.count()).select_from(Apoiador).where(Apoiador.data_expiracao < datetime.now(timezone.utc)))
        expired = expired_res.scalar() or 0
        pending_res = await session.execute(select(func.count()).select_from(Apoiador).where(Apoiador.ativo == True, Apoiador.cargo_atribuido == False))
        pending_roles = pending_res.scalar() or 0
        webhook_res = await session.execute(select(func.sum(GuildConfig.webhook_failures)))
        webhook_failures = webhook_res.scalar() or 0

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
async def set_supporter_role(request: Request, db: AsyncSession = Depends(get_db)):
    data = await request.json()
    guild_id = data.get("guild_id")
    role_id = data.get("role_id")

    if not guild_id or not role_id:
        raise HTTPException(status_code=400, detail="guild_id ou role_id ausente, ai me quebra")
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(GuildConfig).filter_by(guild_id=guild_id))
        guild_config = await safe_first(result)
        if not guild_config:
            guild_config = GuildConfig(guild_id=guild_id, cargo_apoiador_id=role_id)
        else:
            guild_config.cargo_apoiador_id = role_id

        session.add(guild_config)
        await session.commit()
        logger.info(f"Cargo de apoiador atualizado para guild_id={guild_id}, role_id={role_id}")
    
    return {"status": "sucesso", "guild_id": guild_id, "role_id": role_id}


@app.post("/admin/set-supporter-roles", dependencies=[Depends(get_current_admin)])
async def set_supporter_roles(request: Request, db: AsyncSession = Depends(get_db)):
    """Recebe um JSON com 'guild_id' e 'supporter_roles' (dict nível->role_id) e salva em GuildConfig.supporter_roles."""
    data = await request.json()
    guild_id = data.get("guild_id")
    supporter_roles = data.get("supporter_roles")

    if not guild_id or not supporter_roles or not isinstance(supporter_roles, dict):
        raise HTTPException(status_code=400, detail="guild_id ausente ou supporter_roles inválido (esperado dict)")

    # Limitar até 9 níveis
    if len(supporter_roles) > 9:
        raise HTTPException(status_code=400, detail="Máximo de 9 níveis permitidos")

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(GuildConfig).filter_by(guild_id=guild_id))
        guild_config = await safe_first(result)
        if not guild_config:
            guild_config = GuildConfig(guild_id=guild_id, supporter_roles=supporter_roles)
        else:
            guild_config.supporter_roles = supporter_roles

        session.add(guild_config)
        await session.commit()
        logger.info(f"Supporter roles atualizados para guild_id={guild_id}: {supporter_roles}")

    return {"status": "sucesso", "guild_id": guild_id, "supporter_roles": supporter_roles}

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

        # Alguns drivers MySQL podem lançar 'Command out of sync' em condições de concorrência;
        # tente algumas vezes com uma nova sessão antes de falhar.
        db_attempts = 2
        for attempt in range(db_attempts):
            try:
                async with AsyncSessionLocal() as session:
                    result = await session.execute(select(Apoiador).filter_by(id_pagamento=transaction_id))
                    exists_dupped = await safe_first(result)
                    is_test = data.get("is_test") is True or data.get("is_test") == "True"
                    
                    # TRATAMENTO DE RENOVAÇÃO DE ASSINATURA
                    # Se o apoiador já existe E é uma assinatura, é uma RENOVAÇÃO
                    if exists_dupped and data["type"] == "Subscription" and not is_test:
                        # Reativa apoiador que tinha expirado
                        logger.info(f"🔄 RENOVAÇÃO de assinatura Ko-fi detectada: {discord_id}")
                        exists_dupped.ativo = True
                        exists_dupped.cargo_atribuido = False  # Reset para forçar reaplic do cargo
                        exists_dupped.data_expiracao = datetime.now(timezone.utc) + timedelta(days=30)
                        exists_dupped.ultimo_pagamento = datetime.now(timezone.utc)
                        session.add(exists_dupped)
                        await session.commit()
                        return {"status": "renovado"}
                    
                    # Duplicata de doação única (ignorar)
                    if exists_dupped and not is_test:
                        logger.warning(f"Transação Ko-fi duplicada detectada: {transaction_id}")
                        return {"status": "duplicado"}

                    if exists_dupped and is_test:
                        # Em teste, reutilize o registro existente em vez de inserir duplicado
                        apoiador = exists_dupped
                        logger.info(f"Usando registro existente para transação de teste: {transaction_id}")
                    else:
                        # NOVA DOAÇÃO (primeira vez)
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
                        await session.commit()
                    logger.info(f"Apoiador registrado: {discord_id}, tipo={data['type']}, valor={data['amount']}")
                break
            except OperationalError as oe:
                logger.warning(f"OperationalError ao gravar Apoiador (tentativa {attempt+1}/{db_attempts}): {oe}")
                if attempt + 1 >= db_attempts:
                    raise
                await asyncio.sleep(0.2)
        bot = get_bot_instance()
        sucesso = False
        if bot:
            verificador = VerificacaoMembro(bot)
            cargo_apoiador = app_config.APOIADOR_ID2

            # Tentar atribuir cargo em todos os casos (inclusive doadores anônimos).
            # Em ambientes reais a conversão do ID pode falhar e será capturada
            # pelas exceções internas — nos testes VerificacaoMembro é mockado.
            for guild in bot.guilds:
                try:
                    logger.info(f"Tentando atribuir cargo para {discord_id} no servidor {guild.id}")
                    res = await verificador.atribuir_cargo_apos_pagamento(
                        discord_id,
                        guild.id,
                        cargo_id=cargo_apoiador,
                        nivel=getattr(apoiador, 'nivel', None)
                    )
                    if res:
                        sucesso = True
                        logger.info(f"Cargo atribuído automaticamente para {discord_id} no servidor {guild.id}")
                        break
                except Exception as e:
                    logger.error(f"Erro ao tentar atribuir cargo no servidor {guild.id}: {e}")
            if not sucesso:
                logger.warning(f"Falha ao atribuir cargo para {discord_id} via Ko-fi em todos os servidores do bot")
        else:
            logger.warning("Bot instance não disponível para atribuir cargo via Ko-fi")



        donohook_url = app_config.DISCORD_DONOHOOK
        if donohook_url:
            currency = data.get('currency', '')
            embed = {
                "title": "📊 Nova Doação Ko-fi",
                "description": f"De: {data.get('from_name', 'Anônimo')}",
                "color": 0x29ABE2,
                "fields": [
                    {"name": "Valor", "value": f"{data.get('amount', '')} {currency}"},
                    {"name": "Discord ID", "value": discord_id or "Não informado"},
                    {"name": "Email", "value": data.get('email', 'Não informado')},
                    {"name": "Mensagem", "value": data.get('message', 'Nenhuma')[:1000]},
                    {"name": "Tipo", "value": "Assinatura" if data.get("type") == "Subscription" else "Doação Única"},
                    {"name": "Cargo Atribuído", "value": "✅ Sim" if sucesso else "❌ Falha" if discord_id and not discord_id.startswith("kofi_anon_") else "⏸️ Anônimo"}
                ]
            }
            logger.info(f"Enviando notificação para webhook: {donohook_url}")
            try:
                async with httpx.AsyncClient() as client:
                    payload = {"embeds": [embed]}
                    logger.info(f"Webhook payload: {json.dumps(payload, ensure_ascii=False)}")
                    resp = await client.post(donohook_url, json=payload)
                    logger.info(f"Resposta do webhook: {resp.status_code} - {resp.text}")
                    if resp.status_code == 400:
                        logger.warning("Embed inválido, tentando fallback com 'content' simples")
                        fallback = {"content": f"📢 Nova doação: {data.get('from_name', 'Anônimo')} — {data.get('amount', '')} {data.get('currency', '')}"}
                        resp2 = await client.post(donohook_url, json=fallback)
                        logger.info(f"Resposta fallback webhook: {resp2.status_code} - {resp2.text}")
                        if resp2.status_code >= 400:
                            logger.warning("Fallback com 'content' também falhou, tentando embed mínimo")
                            minimal = {"embeds": [{"title": "📊 Nova Doação Ko-fi", "description": f"De: {data.get('from_name', 'Anônimo')}\nValor: {data.get('amount', '')} {data.get('currency', '')}"}]}
                            resp3 = await client.post(donohook_url, json=minimal)
                            logger.info(f"Resposta minimal webhook: {resp3.status_code} - {resp3.text}")
                    elif resp.status_code >= 400:
                        logger.warning(f"Falha ao postar no webhook (status {resp.status_code})")
            except Exception as e:
                logger.error(f"Erro ao enviar notificação para Discord via webhook: {e}")

        cargo_status = "✅ Sim" if sucesso else ("❌ Falha" if discord_id and not discord_id.startswith("kofi_anon_") else "⏸️ Anônimo")
        return {"status": "sucesso", "cargo_atribuido": cargo_status}
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
