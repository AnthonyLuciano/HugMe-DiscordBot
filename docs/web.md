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

## Templates
- **Dashboard**:
  - Lista apoiadores (`apoiadores.ativo`)
  - Navegação para `/commands`
- **Servidores**:
  - Filtra guildas com permissão admin