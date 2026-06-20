# Comandos do Bot

## Estrutura de Comandos

- **Localização**: `bot/commands/`
- **Registro**: Todos os comandos são registrados via `setup_all()` em `bot/commands/__init__.py`

## Categorias

### [BASICO] Básicos (`botcheck.py`)

- **Comandos**:
  - `/check`: Verificação simples de status
  - `/ajuda`: Exibe lista de comandos via Embed
- **Features**:

  ```python
  embed = discord.Embed(
      title="Comandos",
      fields=[{
          "name": "Basicos",
          "value": "Lista de comandos..."
      }]
  )
  ```

### [DOACOES] Doações (`doar.py`)

- **Fluxo**:
  1. Usuário executa `/doar`
  2. Bot exibe modal com campos:
     - Valor (R$)
     - Método (Pix)
     - Email
     - Telefone
  3. Salva no banco com `ja_pago = False`
  4. Envia QR Code via DM
  5. Botão "já paguei" envia notificação para admins
  6. Admin confirma/rejeita via webhook
  7. Se confirmado: atribui cargo automaticamente

- **Integração Ko-fi**:
  - Webhook `/kofi-webhook` detecta renovação automática
  - Assinaturas Ko-fi são reativadas sem intervenção
  - Cargo volta automaticamente após renovação

- **Dados**: Armazenados no modelo `Apoiador`

### [TEMPO] Tempo no Servidor (`tempo.py`)

- **Funcionalidade**:
  - Calcula tempo de membro via `VerificacaoMembro`
  - Sintaxe: `/tempo [@membro]`
- **Dependências**:

  ```python
  self.verificador = VerificacaoMembro(bot)
  await self.verificador.tempo_servidor(member)
  ```

### [ADMIN] Admin (`bot/commands/admin/`)

Pacote modularizado para gerenciamento administrativo do bot com suporte completo a PIX, cargos e apoiadores.

**Estrutura**:
- `cog.py` - Classe principal `AdminCommands` e comandos slash/hybrid
- `utils.py` - Funções auxiliares (`check_is_owner`, `_build_role_config_embed`)
- `modals_pix.py` - Modais para configuração PIX (`SetQRCodeModal`, `ConfigureRoleModal`, `ConfirmationModal`)
- `views_base.py` - Views base (`ConfirmView`, `ConfirmationView`)
- `views_dashboard.py` - Dashboard (`DashboardView`, `SupportersPaginationView`)
- `views_pix.py` - Configuração PIX (`PIXConfigView`)
- `views_roles.py` - Sistema de cargos (`PaginatedRoleSelectView`, `DefaultRoleSelectView`, `TimeRoleConfigView`, `RoleConfigView`, etc.)
- `views_supporter.py` - Gerenciamento de apoiadores (Modais, Views e ações)

**Comandos Principais**:

1. **PIX & Configuração**:
   - `/pix_config` - Exibe/edita configuração PIX (QR Code, chave, dados)
   - Modal: `SetQRCodeModal` para atualizar QR Code e dados do titular

2. **Cargos e Apoiadores**:
   - `/set_default_supporter_role` - Define cargo padrão para todos os apoiadores
   - `/configure_time_roles` - Configura cargos baseados no tempo de apoio (dias/meses/anos)
   - `/view_role_config` - Visualiza configurações de cargos do servidor

3. **Gerenciamento de Apoiadores**:
   - `/add_supporter @usuario [meses] [tipo]` - Adiciona/estende apoio manual
   - `/pause_supporter @usuario` - Pausa apoio temporariamente
   - `/resume_supporter @usuario` - Retoma apoio pausado
   - `/remove_supporter @usuario` - Remove apoiador completamente
   - `/manage_supporter` - Interface interativa com 4 opções de ação

4. **Dashboard & Informações**:
   - `/dashboard` - Painel com estatísticas (apoiadores ativos, doações recentes, receita, servidores)
   - `/servers` - Lista todos os servidores onde o bot está presente

**Features**:
- Suporte a apoio retroativo (no passado) e antecipado (no futuro)
- Paginação para cargos (suporta 100+ cargos)
- Confirmação dupla com `ConfirmationView`
- Sistema de Time-based roles (automático após confirmação)
- Dashboard atualiza em tempo real
- Integração com `SupporterRoleManager` para atribuição automática
- Acesso restrito a donos do bot (`@check_is_owner()`)
- Validações de URLs, valores monetários, IDs de usuário

**Fluxo Típico de Apoiador**:
1. Admin executa `/manage_supporter`
2. Seleciona ação (Adicionar, Pausar, Continuar ou Remover)
3. Preenche modal com ID/menção do usuário
4. Escolhe tipo de período (retroativo ou antecipado)
5. Seleciona unidade (dias, meses, anos)
6. Confirma a ação
7. Sistema atualiza BD e atribui cargos automaticamente

### RPG (`rpg_system.py`)

- **Comandos**:
  - `/rpg_personagem [nome] [classe] [raça] [stats...]`: Cria personagem
  - `/rpg [ação]`: Interage com aventura
  - `/rpg_status`: Verifica progresso
  - `/rpg_personagens`: Lista personagens
  - `/rpg_usar_personagem [id]`: Seleciona personagem
  - `/rpg_deletar_personagem [id]`: Remove personagem
  - `/rpg_ajuda`: Tutorial
- **Features**:
  - Até 3 personagens por usuário
  - Histórico persistente (últimas 8 interações)
  - Integração DeepSeek para geração de aventuras
  - Funciona em canais públicos ou DMs

### Envio de Mensagens (`sendmsg.py`)

- **Comandos**:
  - `/sendmsg [canal] [mensagem]`: Envia mensagem programada
- **Features**:
  - Suporte a embeds
  - Agendamento via APScheduler

### [TEMPORIZADA] Tempo de Voz (`tempvoice.py`)

- **Comandos**:
  - `/tempo_voz [@membro]`: Tempo em voice channels
- **Features**:
  - Rastreamento de tempo em voice
  - Estatísticas por servidor

### Verificação de Cargo (`verificarcargo.py`)

- **Comandos**:
  - `/verificarcargo [cargo_id] [dias]`: Cria botão de verificação
- **Features**:
  - Botão interativo para verificação
  - Verifica tempo mínimo no servidor
  - Aplica cargo automaticamente se qualificado

### Bot Check (`botcheck.py`)

- **Comandos**:
  - `/check`: Status do bot
  - `/ajuda`: Lista de comandos
- **Features**:
  - Embed formatado
  - Informações de uptime

### DeepSeek Chat (`deepseekchat.py`)

- **Comandos**:
  - `/deepseek [prompt]`: Chat com DeepSeek
- **Features**:
  - API integration
  - Contexto persistente

### Autismo (`autism.py`)

- **Comandos**:
  - `/autismo`: Comandos de diversão
- **Features**:
  - Comandos leves para entretenimento

### Hug (`hug.py`)

- **Comandos**:
  - `/hug [@membro]`: Abraça alguém
- **Features**:
  - Comandos de interação social

### Doar (`doar.py`)

- **Comandos**:
  - `/doar`: Inicia processo de doação
- **Features**:
  - Modal de valor
  - QR Code PIX
  - Integração Ko-fi
  - Renovação automática para assinaturas
