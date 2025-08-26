# ⚙️ Serviços do Bot

## PagBank (`servicos/__init__.py`)
- **Funções**:
  - `create_transaction()`: Inicia transação
  - `verify_transaction()`: Verifica status
- **Fluxo**:
  1. Gera QR Code via API
  2. Registra no banco
  3. Aguarda webhook de confirmação

## Verificação de Membros (`VerificacaoMembro.py`)
- **Métodos**:
  ```python
  async def tempo_servidor(member) -> str
  async def verificar_tempo_minimo(member, dias) -> bool
  ```
- **Uso**:
  - Comando `/tempo`
  - Verificação de cargos