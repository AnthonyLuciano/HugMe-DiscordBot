# ⚙️ Configuração

## Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto baseando-se no `.env.example`. Abaixo está a descrição de cada variável.

### Discord
```ini
APPLICATION_ID=          # Application ID do bot (Discord Developer Portal)
DISCORD_CLIENT_ID=      # Client ID OAuth2 do bot
DISCORD_CLIENT_SECRET=  # Client Secret OAuth2 do bot
DISCORD_BOT_TOKEN=      # Token do bot Discord
DEV_ID=                 # ID do desenvolvedor (acesso owner)
TRUSTED_MOD_ID=         # ID do moderador confiável
GUILD_ID=               # ID do servidor principal
APOIADOR_CARGO_ID=      # ID do cargo de apoiador
VERIFIED_ROLE_ID=       # ID do cargo de membro verificado
DISCORD_DONOHOOK_URL=   # URL do webhook para notificações de doação
```

### Banco de Dados
```ini
DATABASE_URL=            # URL de conexão (ex: postgresql://user:pass@host:5432/dbname)
```

### Ko-fi (Doações)
```ini
KOFI_LOG_CHANNEL_ID=    # ID do canal de logs de doação
KOFI_TOKEN=             # Token de verificação do webhook Ko-fi
```

### DeepSeek (RPG e Chat)
```ini
DEEPSEEK_LOG_CHANNEL=   # ID do canal de logs do DeepSeek
DEEPSEEK_API_KEY=       # API Key do DeepSeek
QUARTO_DO_HUGME=        # ID do canal "Quarto do HugMe"
```

### Produção e Desenvolvimento
```ini
REDIRECT_URL=           # URL de redirect OAuth2 (produção)
NGROK_URL=              # URL do Ngrok (desenvolvimento local)
```

### Segurança
```ini
SESSION_SECRET=         # Segredo para sessões do painel web
ADMIN_TOKEN=            # Token de acesso admin ao painel web
WEBHOOK_SECRET=         # Segredo para validação de webhooks
```

---

## Ambientes

### Desenvolvimento
```ini
NGROK_URL=https://xxx.ngrok-free.app
DATABASE_URL=sqlite:///./dev.db
```
- Use Ngrok para expor o servidor local e receber webhooks
- Banco SQLite local para testes rápidos

### Produção
```ini
REDIRECT_URL=https://seu-dominio.com/callback
DATABASE_URL=postgresql://user:pass@host:5432/dbname
DISCORD_DONOHOOK_URL=https://discord.com/api/webhooks/...
```
- Domínio próprio com HTTPS
- Banco PostgreSQL para dados persistentes
- Webhooks configurados nos painéis Ko-fi e PagBank

---

## Configuração de Webhooks

### Ko-fi Webhook
No painel do Ko-fi, configure a URL:
```
https://seu-dominio.com/kofi-webhook
```

### PagBank Webhook
No painel do PagBank, configure a URL:
```
https://seu-dominio.com/webhook
```

---

## Cargos por Nível

Os cargos por nível de apoio são configurados no banco de dados (campo `GuildConfig.supporter_roles` em JSON):
```json
{
  "1": "cargo_id_nivel_1",
  "2": "cargo_id_nivel_2",
  "3": "cargo_id_nivel_3"
}
```
Use o comando `/configure_time_roles` no Discord para configurar visualmente.