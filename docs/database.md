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
  - `SessionLocal`: Factory pattern para sessões
  - `get_db()`: Gerador para FastAPI

## Modelos Principais

### PixConfig (`models.py`)
- **Campos**:
  ```python
  chave: str           # Chave PIX (email/CPF)
  static_qr_url: str   # URL da imagem do QR Code
  atualizado_em: datetime  # Timestamp automático
  ```

### Apoiador (parcial)
- **Relacionamentos**:
  - Vincula usuários Discord a doações
- **Status**:
  - `ativo`: Boolean
  - `data_expiracao`: Controle de benefícios