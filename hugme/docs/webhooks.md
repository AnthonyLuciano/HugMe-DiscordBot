# 🌐 Webhooks

## PagBank
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