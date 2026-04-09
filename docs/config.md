# ⚙️ Configuração

## Variáveis Essenciais
```ini
# Discord
DISCORD_BOT_TOKEN=                    # Token do bot Discord
APPLICATION_ID=                       # Application ID do bot

# Banco de Dados
DATABASE_URL=                         # URL de conexão PostgreSQL/MariaDB

# Ko-fi (Doações)
KOFI_TOKEN=                           # Token de verificação webhook
KOFI_ENDPOINT=                        # Endpoint webhook Ko-fi
DISCORD_DONOHOOK_URL=                 # Webhook para notificações de doação
KOFI_LOG_CHANNEL_ID=                  # Canal de logs de doação

# API DeepSeek (RPG)
DEEP_API=                             # URL da API DeepSeek
DEEP_KEY=                             # API Key DeepSeek

# Webhook e Segurança
WEBHOOK_SECRET=                       # Segurança de webhook
ADMIN_TOKEN=                          # Token de admin para painel web

# Discord (Cargos)
QUARTO_DO_HUGME=                      # ID do canal "Quarto do HugMe"
APOIADOR_CARGO_ID=                    # ID do cargo nível 1
APOIADOR_CARGO_ID2=                   # ID do cargo nível 2 (padrão)
TEST_SERVER_ID=                       # ID do servidor de testes

# Ambiente
USE_NGROK=true                        # Usar Ngrok para testes (dev)
NGROK_URL=                            # URL do Ngrok (dev)
```

## Ambientes
- **Desenvolvimento**:
  ```ini
  USE_NGROK=true
  NGROK_URL=https://xxx.ngrok-free.app
  DATABASE_URL=sqlite:///./dev.db     # Banco local
  ```

- **Produção**:
  ```ini
  USE_NGROK=false
  DATABASE_URL=postgresql://user:pass@host:5432/dbname
  DISCORD_DONOHOOK_URL=https://discord.com/webhook/...
  ```

## Variáveis de Cargo por Nível
```ini
# No banco (GuildConfig.supporter_roles JSON):
{
  "1": "cargo_id_nivel_1",
  "2": "cargo_id_nivel_2",
  "3": "cargo_id_nivel_3"
}
```

## Variáveis de Webhook
```ini
# Ko-fi Webhook (configurado no painel Ko-fi):
https://seu-domínio.com/kofi-webhook

# PagBank Webhook (configurado no painel PagBank):
https://seu-domínio.com/webhook
```