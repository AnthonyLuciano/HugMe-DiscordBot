# 🌐 Webhooks

## Ko-fi Webhook (`/kofi-webhook`)
- **Arquivo**: `bot/web/main.py`
- **Endpoint**: `POST /kofi-webhook`
- **Fluxo**:
  1. Recebe POST com dados da transação
  2. Valida token de verificação
  3. Processa transação:
  ```python
  # NOVA DOAÇÃO
  apoiador = Apoiador(
      tipo_apoio="kofi",
      data_expiracao=datetime.now() + timedelta(days=30),
      ativo=True,
      ja_pago=True
  )
  
  # RENOVAÇÃO (detectada automaticamente)
  if exists_dupped and data["type"] == "Subscription":
      apoiador.ativo = True
      apoiador.cargo_atribuido = False  # Reset para reaplicar cargo
      apoiador.data_expiracao = agora + 30 dias
      return {"status": "renovado"}
  ```
  4. Atribui cargo no Discord
  5. Notifica webhook do dono

- **Detecção de Renovação**:
  - Se `transaction_id` já existe E `type == "Subscription"`:
    - Sistema detecta renovação automática
    - Reativa: `ativo = True`
    - Reset cargo: `cargo_atribuido = False`
    - Estende: `data_expiracao += 30 dias`

- **Segurança**:
  - Token de verificação no `.env`
  - Validação de assinatura HMAC (opcional)

---

## PagBank Webhook
- **Arquivo**: `bot/web/main.py`
- **Fluxo**:
  1. Recebe POST com payload
  2. Valida assinatura HMAC-SHA256
  3. Atualiza status no banco:
  ```python
  apoiador.ultimo_pagamento = now
  apoiador.ativo = True
  ```
- **Segurança**:
  - Verificação de IP (opcional)
  - Token secreto no `.env`