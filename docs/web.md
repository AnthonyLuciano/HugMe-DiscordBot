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
- O servidor web é iniciado via `uvicorn` e, por padrão, tenta carregar
  certificados localizados em `bot/certificates/hugmebot.online.pem` e
  `.../hugmebot.online.key`.
- Durante o deploy o processo pode ter um **cwd diferente** (por exemplo
  `/home/container`), então esses caminhos são agora resolvidos a partir
  do diretório do módulo (`bot/main.py`). Se os arquivos estiverem ausentes
  (comuns em repositórios, pois a pasta está em `.gitignore`), o servidor
  cairá para HTTP e logará um aviso.
- Para habilitar TLS em produção, copie seu PEM e chave para `bot/certificates`
  ou defina `SSL_CERTFILE`/`SSL_KEYFILE` no código antes de iniciar.

## Templates
- **Dashboard**:
  - Lista apoiadores (`apoiadores.ativo`)
  - Navegação para `/commands`
- **Servidores**:
  - Filtra guildas com permissão admin