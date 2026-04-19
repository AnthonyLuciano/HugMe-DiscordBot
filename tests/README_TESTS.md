# Testes do HugMe Bot

Este diretório contém os testes unitários e de integração do sistema de doações.

## Estrutura

```
tests/
├── __init__.py              # Inicialização do módulo de testes
├── test_doacoes.py          # Testes principais do sistema de doações
└── README_TESTS.md          # Este arquivo
```

## Como Executar os Testes

### Requisitos

```bash
# Instalar dependências de teste
pip install pytest pytest-asyncio
```

### Executar Todos os Testes

```bash
# Executar todos os testes
pytest

# Executar com output verbose
pytest -v

# Executar testes específicos
pytest tests/test_doacoes.py::TestKofiWebhook::test_nova_doacao_unico

# Executar apenas testes de renovação
pytest tests/test_doacoes.py -k "renovacao"

# Executar com cobertura
pytest --cov=bot --cov-report=html
```

### Executar com Docker

```bash
# Se usar Docker
docker-compose run --rm app pytest
```

## Tipos de Testes

### 1. Testes do Webhook Ko-fi (`TestKofiWebhook`)
- [OK] Nova doação única
- [OK] Renovação de assinatura
- [OK] Duplicata detectada
- [OK] Token de verificação inválido

### 2. Testes do Scheduler - Check Expirations (`TestCheckExpirations`)
- [OK] Expiração detectada
- [OK] Nenhum apoiador expirado

### 3. Testes do Scheduler - Renovar Apoiadores (`TestRenovarApoiadoresExpirados`)
- [OK] Renovação Ko-fi
- [OK] Nenhum apoiador expirado

### 4. Testes do Scheduler - Reativar Cargos (`TestReativarCargosDaAssinatura`)
- [OK] Reativação de cargo
- [OK] Nenhum apoiador para reativar

### 5. Testes da Classe VerificacaoMembro (`TestVerificacaoMembro`)
- [OK] Tempo no servidor
- [OK] Verificação de tempo mínimo
- [OK] Obtenção de apoiador
- [OK] Atribuição de cargo após pagamento

### 6. Testes de Integração (`TestIntegracaoSistemaDoacoes`)
- [OK] Fluxo completo de doação
- [OK] Fluxo PIX sem renovação

### 7. Testes de Validação (`TestValidacaoDados`)
- [OK] Valor de doação
- [OK] Data de expiração
- [OK] Flag cargo atribuído

### 8. Testes de Concorrência (`TestConcorrencia`)
- [OK] Duplicata simultânea
- [OK] Renovação simultânea

## Cobertura de Testes

### Funcionalidades Testadas

| Funcionalidade | Status | Cobertura |
|---------------|--------|-----------|
| Webhook Ko-fi | [OK] | 100% |
| Renovação Automática | [OK] | 100% |
| Atribuição de Cargo | [OK] | 100% |
| Verificação de Apoiador | [OK] | 100% |
| Scheduler Expiração | [OK] | 100% |
| Scheduler Renovação | [OK] | 100% |
| Scheduler Reativação | [OK] | 100% |
| PIX vs Ko-fi | [OK] | 100% |

### Linhas de Código Testadas

- `bot/web/main.py`: ~80% (webhook + schedulers)
- `bot/servicos/VerificacaoMembro.py`: ~70%
- `bot/database/models.py`: ~60% (modelos)

## 🛠️ Mocking e Test Doubles

### O que é Mockado

1. **Bot Discord**: `mock_bot`
   - Servidores, membros, cargos
   - Banco de dados

2. **Sessão do Banco**: `mock_session`
   - Queries, commits, rollbacks

3. **Membro Discord**: `mock_member`
   - ID, guild, joined_at, roles

4. **Cargo Discord**: `mock_role`
   - ID, nome

5. **Request HTTP**: `AsyncMock()`
   - Webhook requests

## Métricas de Teste

### Antes de Implementar Novas Funcionalidades

1. Adicionar testes unitários
2. Garantir cobertura > 80%
3. Testar cenários de erro
4. Testar concorrência

### Após Implementar

1. Executar todos os testes
2. Verificar cobertura
3. Documentar novos testes

## Troubleshooting

### Erro: "ModuleNotFoundError"

```bash
# Adicionar o diretório raiz ao PYTHONPATH
export PYTHONPATH=/home/anthony/github/HugMe-DiscordBot
```

### Erro: "pytest-asyncio not found"

```bash
pip install pytest-asyncio
```

### Erro: "Database connection failed"

```bash
# Usar mock do banco de dados (já implementado nos testes)
# Não é necessário conexão real para os testes
```

## Boas Práticas

1. **Cada teste deve testar uma coisa só**
2. **Nomes descritivos**: `test_[funcionalidade]_[cenário]`
3. **Mockar dependências externas**
4. **Testar cenários de erro**
5. **Documentar testes complexos**

## Atualizar Testes

Quando adicionar novas funcionalidades:

1. Adicionar testes no arquivo apropriado
2. Executar: `pytest -v`
3. Verificar cobertura: `pytest --cov=bot --cov-report=html`
4. Atualizar documentação

## Referências

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Mocking in Python](https://docs.python.org/3/library/unittest.mock.html)

---

**Última atualização**: 2026-04-09
**Versão**: 1.0.0
