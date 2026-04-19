# Serviços do Bot

## PagBank (`servicos/__init__.py`)
- **Funções**:
  - `create_transaction()`: Inicia transação
  - `verify_transaction()`: Verifica status
- **Fluxo**:
  1. Gera QR Code via API
  2. Registra no banco
  3. Aguarda webhook de confirmação

## Verificação de Membros (`VerificacaoMembro.py`)
- **Métodos**:
  ```python
  async def tempo_servidor(member) -> str
  async def verificar_tempo_minimo(member, dias) -> bool
  async def obter_apoiador(discord_id, guild_id) -> Apoiador
  async def obter_role_por_nivel(guild_id, nivel) -> int
  async def aplicar_cargo_se_qualificado(member, cargo_id, dias, nivel) -> str
  async def atribuir_cargo_apos_pagamento(discord_id, guild_id, cargo_id, nivel) -> bool
  ```
- **Uso**:
  - Comando `/tempo`
  - Verificação de cargos
  - Atribuição automática após doação
  - Reaplicação de cargo após renovação de assinatura

- **Fluxo de Atribuição**:
  ```
  1. Webhook Ko-fi recebe transação
  2. Cria/Atualiza Apoiador no banco
  3. Chama atribuir_cargo_apos_pagamento()
  4. Busca membro no servidor
  5. Aplica role
  6. Marca cargo_atribuido = True
  ```

- **Fluxo de Renovação** (automático):
  ```
  1. check_expirations() detecta expiração (a cada 6h)
  2. renovar_apoiadores_expirados() reativa (a cada 12h)
  3. reativar_cargos_da_assinatura() reaplica cargo (a cada 2h)
  ```

## Configuração (`config.py`)
- **Variáveis de Doação**:
  ```python
  KOFI_TOKEN = getenv('KOFI_TOKEN')           # Token de verificação
  KOFI_ENDPOINT = getenv('KOFI_ENDPOINT')     # Endpoint webhook
  DISCORD_DONOHOOK = getenv('DISCORD_DONOHOOK_URL')  # Webhook de notificação
  DONO_LOG_CHANNEL = getenv('KOFI_LOG_CHANNEL_ID')   # Canal de logs
  ```

- **Variáveis de Cargo**:
  ```python
  APOIADOR_ID = getenv('APOIADOR_CARGO_ID')   # Cargo nível 1
  APOIADOR_ID2 = getenv('APOIADOR_CARGO_ID2') # Cargo nível 2 (padrão)
  ```

- **Variáveis de Webhook**:
  ```python
  WEBHOOK_SECRET = getenv('WEBHOOK_SECRET')     # Segurança de webhook
  ADMIN_TOKEN = getenv('ADMIN_TOKEN')           # Token de admin
  ```

- **Variáveis de Ambiente**:
  ```python
  USE_NGROK = getenv('USE_NGROK')              # Usar Ngrok para testes
  NGROK_URL = getenv('NGROK_URL')              # URL do Ngrok
  ```