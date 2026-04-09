# 🌐 Painel Web

## Autenticação (`web/main.py`)
- **Fluxo OAuth2**:
  1. Redireciona para Discord
  2. Captura token
  3. Armazena em sessão:
     ```python
     request.session['user'] = {
         **user_data,
         'access_token': token
     }
     ```

## SSL / HTTPS
- O servidor web é iniciado via `uvicorn` e carrega certificados a partir de
  `bot/certificates/hugmebot.online.pem` e
  `bot/certificates/hugmebot.online.key`.
- Como alternativa, quando o primeiro diretório não existe o código também
  verifica `/home/container/certificates`, que é onde algumas plataformas
  montam chaves TLS fora do repositório. Isso permite que o bot funcione mesmo
  se os arquivos não fizerem parte do clone.
- Os caminhos são resolvidos a partir do diretório do módulo (`bot/main.py`)
  em vez do cwd atual para evitar erros quando o processo é iniciado com outro
  diretório de trabalho.
- Se nenhuma das localizações contiver ambos os arquivos, o bot lança
  `FileNotFoundError` citando todos os diretórios pesquisados, facilitando o
  diagnóstico.
- Para habilitar TLS em produção, copie ou monte os arquivos em uma dessas
  pastas; não há necessidade de editar configurações ou variáveis de ambiente.

## Templates
- **Dashboard**:
  - Lista apoiadores (`apoiadores.ativo`)
  - Navegação para `/commands`
- **Servidores**:
  - Filtra guildas com permissão admin

## Endpoints da API (`bot/web/main.py`)

### Webhooks
- **`POST /kofi-webhook`**: Webhook principal para Ko-fi
  - Detecta novas doações
  - Detecta renovações de assinatura
  - Atribui cargo automaticamente
  - Responde: `{"status": "renovado"}` ou `{"status": "sucesso"}`

- **`POST /webhook`**: Webhook legacy (redireciona para Ko-fi)

### Admin
- **`GET /admin`**: Painel administrativo
  - Requer autenticação OAuth2
  - Lista apoiadores
  - Métricas de doação

- **`GET /admin/metrics`**: Métricas em JSON
  - Total de apoiadores
  - Ativos
  - Expirados
  - Taxa de renovação

### Dashboard
- **`GET /dashboard`**: Lista apoiadores em JSON
- **`GET /servers`**: Lista guildas do usuário

### OAuth2
- **`GET /login`**: Redireciona para Discord OAuth
- **`GET /callback`**: Callback do OAuth
- **`GET /logout`**: Logout do usuário

## Scheduler de Renovação Automática

### `check_expirations()` - A cada 6 horas
```python
# Busca apoiadores expirados
select(Apoiador).where(
    Apoiador.data_expiracao < agora,
    Apoiador.ativo == True
)

# Marca como inativo
apoiador.ativo = False
```
**Propósito**: Identificar quem precisa renovar

---

### `renovar_apoiadores_expirados()` - A cada 12 horas
```python
# Busca apoiadores Ko-fi expirados
select(Apoiador).where(
    Apoiador.ativo == False,
    Apoiador.tipo_apoio == "kofi",
    Apoiador.data_expiracao != None
)

# Reativa e estende
apoiador.ativo = True
apoiador.data_expiracao = agora + 30 dias
```
**Propósito**: Reativar automaticamente assinaturas Ko-fi

---

### `reativar_cargos_da_assinatura()` - A cada 2 horas
```python
# Busca apoiadores reativados que precisam de cargo
select(Apoiador).where(
    Apoiador.ativo == True,
    Apoiador.cargo_atribuido == False,
    Apoiador.tipo_apoio == "kofi"
)

# Aplica cargo no Discord
await member.add_roles(role)
apoiador.cargo_atribuido = True
```
**Propósito**: Reaplicar cargo no Discord após renovação

---

### Fluxo Completo de Renovação
```
DIA 30 (Expiração):
├─ check_expirations() → ativo=False
└─ renovar_apoiadores_expirados() → ativo=True, data_expiracao=+30d

DIA 30 + 2h:
└─ reativar_cargos_da_assinatura() → cargo reaplicado no Discord

DIA 60 (Próxima expiração):
└─ Ciclo se repete automaticamente
```

## Integração com Webhooks

### Ko-fi Webhook (Assinatura)
```python
# Detecta renovação
if exists_dupped and data["type"] == "Subscription":
    apoiador.ativo = True
    apoiador.cargo_atribuido = False  # Reset
    apoiador.data_expiracao = agora + 30 dias
    return {"status": "renovado"}
```

### Webhook de Notificação
- Envia embed para canal configurado
- Mostra: valor, Discord ID, email, mensagem, tipo
- Indica se cargo foi atribuído

## Segurança
- Token de admin no `.env`
- OAuth2 para autenticação
- Webhook secret para validação
- Verificação de permissões de admin