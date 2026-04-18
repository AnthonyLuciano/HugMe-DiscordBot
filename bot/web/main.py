import asyncio, hashlib, hmac, json, logging, os, re
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import FastAPI, HTTPException, Request

from bot.config import config as app_config
from bot.database import SessionLocal
from bot.database.models import Apoiador
from bot.servicos.VerificacaoMembro import VerificacaoMembro
from bot.shared import get_bot_instance

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="HugMe Webhooks", description="Serviço de webhooks para doações")

@app.get("/status")
async def status():
    """Endpoint de status para verificar se o serviço está ativo"""
    return {"message": "Serviço de webhooks ativo!", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.post("/webhook")
async def legacy_webhook(request: Request):
    """Endpoint legado - redireciona para kofi-webhook"""
    logger.warning("Endpoint legacy webhook chamado, redirecionando para /kofi-webhook")
    return await kofi_webhook(request)

@app.post("/kofi-webhook")
async def kofi_webhook(request: Request):
    """Webhook principal para processar doações do Ko-fi"""
    try:
        form_data = await request.form()
        if "data" not in form_data:
            raise HTTPException(status_code=400, detail="Campo 'data' ausente")

        data = json.loads(form_data["data"])
        transaction_id = data.get("transaction_id", f"kofi_{int(datetime.now(timezone.utc).timestamp())}")

        # Verificação de token se configurado
        if "verification_token" in data and app_config.KOFI_TOKEN:
            if data["verification_token"] != app_config.KOFI_TOKEN:
                raise HTTPException(status_code=403, detail="Token de verificação inválido")

        # Ignorar tipos não suportados
        if data["type"] not in ["Donation", "Subscription"]:
            return {"status": "ignorado", "type": data["type"]}

        # Extrair Discord ID da mensagem ou nome
        discord_id = None
        for source in [data.get("from_name"), data.get("message")]:
            if source and (match := re.search(r"(?:discord\.com/users/)?(\d{17,19})", str(source))):
                discord_id = match.group(1)
                break

        if not discord_id:
            discord_id = f"kofi_anon_{int(datetime.now(timezone.utc).timestamp())}"

        # Processar doação no banco de dados
        with SessionLocal() as session:
            # Verificar duplicatas
            exists_dupped = session.query(Apoiador).filter_by(id_pagamento=transaction_id).first()
            if exists_dupped:
                logger.warning(f"Transação Ko-fi duplicada detectada: {transaction_id}")
                return {"status": "duplicado"}

            # Criar registro do apoiador
            apoiador = Apoiador(
                discord_id=discord_id,
                guild_id="0",  # Será atualizado quando o usuário usar o bot
                id_pagamento=transaction_id,
                tipo_apoio="kofi",
                email_doador=data.get("email"),
                valor_doacao=int(float(data["amount"]) * 100),  # Em centavos
                data_inicio=datetime.now(timezone.utc),
                data_expiracao=datetime.now(timezone.utc) + timedelta(days=30) if data["type"] == "Subscription" else None,
                ativo=True,
                ja_pago=True,
            )
            session.add(apoiador)
            session.commit()
            logger.info(f"Apoiador registrado via Ko-fi: {discord_id}, tipo={data['type']}, valor={data['amount']}")

        # Atribuir cargo automaticamente se possível
        sucesso = False
        if discord_id and not discord_id.startswith("kofi_anon_"):
            bot = get_bot_instance()
            if bot:
                verificador = VerificacaoMembro(bot)
                cargo_apoiador = app_config.APOIADOR_ID2

                sucesso = await verificador.atribuir_cargo_apos_pagamento(
                    discord_id,
                    0,  # guild_id será determinado pelo bot
                    cargo_apoiador
                )

                if sucesso:
                    logger.info(f"Cargo atribuído automaticamente para {discord_id} via Ko-fi")
                else:
                    logger.warning(f"Falha ao atribuir cargo para {discord_id} via Ko-fi")

        # Enviar notificação para Discord se configurado
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
                ],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            async with httpx.AsyncClient() as client:
                await client.post(donohook_url, json={"embeds": [embed]})
                logger.info("Notificação de doação enviada para Discord via webhook")

        return {"status": "sucesso", "discord_id": discord_id, "cargo_atribuido": sucesso}

    except Exception as e:
        logger.error(f"Erro no webhook do Ko-fi: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")