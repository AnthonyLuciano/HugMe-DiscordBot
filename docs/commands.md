# 📜 Comandos do Bot

## Estrutura de Comandos
- **Localização**: `bot/commands/`
- **Registro**: Todos os comandos são registrados via `setup_all()` em `bot/commands/__init__.py`

## Categorias

### 🔍 Básicos (`botcheck.py`)
- **Comandos**:
  - `/check`: Verificação simples de status
  - `/ajuda`: Exibe lista de comandos via Embed
- **Features**:
  ```python
  embed = discord.Embed(
      title="📚 Comandos",
      fields=[{
          "name": "🛠️ Básicos",
          "value": "Lista de comandos..."
      }]
  )
  ```

### 💰 Doações (`doar.py`)
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

### ⏳ Tempo no Servidor (`tempo.py`)
- **Funcionalidade**:
  - Calcula tempo de membro via `VerificacaoMembro`
  - Sintaxe: `/tempo [@membro]`
- **Dependências**:
  ```python
  self.verificador = VerificacaoMembro(bot)
  await self.verificador.tempo_servidor(member)
  ```

### 🔐 Admin (`admin.py`)
- **Comandos Privilegiados**:
  - `/set_qrcode [url]`: Atualiza QR Code PIX
  - `/verificarcargo [cargo_id] [dias]`: Cria botão de verificação
  - Validações:
    - URL deve começar com `http(s)://`
    - Acesso restrito a donos do bot (`@is_owner()`)

### 🎮 RPG (`rpg_system.py`)
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

### 📤 Envio de Mensagens (`sendmsg.py`)
- **Comandos**:
  - `/sendmsg [canal] [mensagem]`: Envia mensagem programada
- **Features**:
  - Suporte a embeds
  - Agendamento via APScheduler

### ⏱️ Tempo de Voz (`tempvoice.py`)
- **Comandos**:
  - `/tempo_voz [@membro]`: Tempo em voice channels
- **Features**:
  - Rastreamento de tempo em voice
  - Estatísticas por servidor

### 🎭 Verificação de Cargo (`verificarcargo.py`)
- **Comandos**:
  - `/verificarcargo [cargo_id] [dias]`: Cria botão de verificação
- **Features**:
  - Botão interativo para verificação
  - Verifica tempo mínimo no servidor
  - Aplica cargo automaticamente se qualificado

### 🤖 Bot Check (`botcheck.py`)
- **Comandos**:
  - `/check`: Status do bot
  - `/ajuda`: Lista de comandos
- **Features**:
  - Embed formatado
  - Informações de uptime

### 🧠 DeepSeek Chat (`deepseekchat.py`)
- **Comandos**:
  - `/deepseek [prompt]`: Chat com DeepSeek
- **Features**:
  - API integration
  - Contexto persistente

### 😂 Autismo (`autism.py`)
- **Comandos**:
  - `/autismo`: Comandos de diversão
- **Features**:
  - Comandos leves para entretenimento

### 🤗 Hug (`hug.py`)
- **Comandos**:
  - `/hug [@membro]`: Abraça alguém
- **Features**:
  - Comandos de interação social

### 🙏 Doar (`doar.py`)
- **Comandos**:
  - `/doar`: Inicia processo de doação
- **Features**:
  - Modal de valor
  - QR Code PIX
  - Integração Ko-fi
  - Renovação automática para assinaturas