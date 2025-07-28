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
  - Validações:
    - URL deve começar com `http(s)://`
    - Acesso restrito a donos do bot (`@is_owner()`)