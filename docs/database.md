# 🗃️ Sistema de Banco de Dados

## Conexão (`bot/database/__init__.py`)
- **Config**:
  ```python
  engine = create_engine(
      config.DATABASE_URL,
      pool_pre_ping=True,
      echo=False
  )
  ```
- **Sessões**:
  - `AsyncSessionLocal`: Factory pattern para sessões assíncronas
  - `get_db()`: Gerador para FastAPI

## Modelos Principais

### PixConfig (`models.py`)
- **Campos**:
  ```python
  id: int
  chave: str           # Chave PIX (email/CPF)
  static_qr_url: str   # URL da imagem do QR Code
  nome_titular: str    # Nome do titular da conta
  cidade: str          # Cidade do titular
  atualizado_em: datetime  # Timestamp automático
  atualizado_por: str  # Discord ID do atualizador
  ```

### Apoiador (`models.py`)
- **Relacionamentos**:
  - Vincula usuários Discord a doações
  - Rastreia histórico de pagamentos

- **Campos Principais**:
  ```python
  id: int                              # ID único
  discord_id: str                      # ID do usuário Discord
  guild_id: str                        # ID do servidor (para multi-server)
  id_pagamento: str                    # ID da transação (único)
  tipo_apoio: str                      # "pix" ou "kofi"
  duracao_meses: int                   # Duração em meses (opcional)
  comprovante_url: str                 # URL do comprovante (opcional)
  
  # Status de apoio
  data_inicio: datetime                # Quando começou
  ultimo_pagamento: datetime           # Último pagamento
  data_expiracao: datetime             # Quando expira (para Ko-fi)
  ativo: bool                          # Status atual (ativo/inativo)
  cargo_atribuido: bool                # Cargo já aplicado?
  ja_pago: bool                        # Pagamento confirmado?
  
  # Dados financeiros
  valor_doacao: int                    # Valor em centavos
  data_pagamento: datetime             # Data do pagamento específico
  metodo_pagamento: str                # "pix" ou "kofi"
  email_doador: str                    # Email do doador
  nivel: int                           # Nível de apoio (1, 2, 3...)
  ```

- **Fluxo de Estados**:
  ```
  NOVO → Webhook Ko-fi → ativo=True, data_expiracao=+30d
  ↓
  CARGO APLICADO → cargo_atribuido=True
  ↓
  EXPIRADO → check_expirations() → ativo=False
  ↓
  RENOVAÇÃO → renovar_apoiadores_expirados() → ativo=True, cargo_atribuido=False
  ↓
  CARGO REAPLICADO → reativar_cargos_da_assinatura() → cargo_atribuido=True
  ```

### RPGCharacter (`models.py`)
- **Campos**:
  ```python
  id: int
  user_id: str
  name: str
  class_name: str
  race: str
  strength, dexterity, constitution, intelligence, wisdom, charisma: int
  is_active: bool
  created_at, updated_at: datetime
  ```

### RPGSession (`models.py`)
- **Campos**:
  ```python
  id: int
  user_id: str
  history: JSON                        # Histórico de interações
  character_data: JSON                 # Dados do personagem
  current_story: Text                  # História atual
  has_seen_tutorial: bool
  adventure_started_at: datetime
  summary_count: int
  active_character_id: int
  created_at, updated_at: datetime
  ```

### GuildConfig (`models.py`)
- **Campos**:
  ```python
  guild_id: str                        # ID do servidor (PK)
  role_prefix: str                     # Prefixo para roles (ex: "Apoia")
  cargo_apoiador_id: str               # ID do cargo padrão
  webhook_failures: int                # Contador de falhas
  supporter_roles: dict                # Mapeamento nível → role_id
  ```

## Scheduler de Renovação (`bot/web/main.py`)
- **check_expirations()**: A cada 6h
  - Busca: `data_expiracao < agora AND ativo = True`
  - Marca: `ativo = False`
  
- **renovar_apoiadores_expirados()**: A cada 12h
  - Busca: `ativo = False AND tipo_apoio = "kofi"`
  - Reativa: `ativo = True, data_expiracao += 30d`
  
- **reativar_cargos_da_assinatura()**: A cada 2h
  - Busca: `ativo = True AND cargo_atribuido = False AND tipo_apoio = "kofi"`
  - Aplica: cargo no Discord
  - Marca: `cargo_atribuido = True`