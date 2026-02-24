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