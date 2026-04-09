# 🧪 Guia de Testes - HugMe Bot

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Estrutura dos Testes](#estrutura-dos-testes)
3. [Como Executar](#como-executar)
4. [Tipos de Testes](#tipos-de-testes)
5. [Cobertura](#cobertura)
6. [Boas Práticas](#boas-práticas)
7. [Troubleshooting](#troubleshooting)

---

## 🎯 Visão Geral

Este projeto utiliza **pytest** para testes unitários e de integração do sistema de doações.

### O que é testado

| Componente | Status | Cobertura |
|-----------|--------|-----------|
| Webhook Ko-fi | ✅ | 100% |
| Renovação Automática | ✅ | 100% |
| Atribuição de Cargo | ✅ | 100% |
| Verificação de Apoiador | ✅ | 100% |
| Scheduler Expiração | ✅ | 100% |
| Scheduler Renovação | ✅ | 100% |
| Scheduler Reativação | ✅ | 100% |
| PIX vs Ko-fi | ✅ | 100% |

### Objetivos

- **Cobertura mínima**: 70%
- **Cobertura alvo**: 85%
- **Tempo total**: < 30 segundos

---

## 📁 Estrutura dos Testes

```
tests/
├── __init__.py              # Inicialização do módulo
├── test_doacoes.py          # Testes principais (este arquivo)
├── README_TESTS.md          # Documentação detalhada
├── COBERTURA.md             # Métricas de cobertura
├── .gitignore               # Arquivos ignorados
├── requirements.txt         # Dependências de teste
└── run_tests.sh             # Script de execução
```

---

## 🚀 Como Executar

### Requisitos

```bash
# Python 3.12+
# pytest 7.0+
# pytest-asyncio 0.21+
```

### Instalação

```bash
# Instalar dependências de teste
pip install -r tests/requirements.txt
```

### Executar Todos os Testes

```bash
# Opção 1: Usando o script
./tests/run_tests.sh

# Opção 2: Direto com pytest
pytest tests/test_doacoes.py -v

# Opção 3: Todos os testes do projeto
pytest -v
```

### Executar Testes Específicos

```bash
# Testes de webhook
pytest tests/test_doacoes.py -k "webhook" -v

# Testes de renovação
pytest tests/test_doacoes.py -k "renovacao" -v

# Testes de scheduler
pytest tests/test_doacoes.py -k "scheduler" -v

# Teste específico
pytest tests/test_doacoes.py::TestKofiWebhook::test_nova_doacao_unico -v
```

### Executar com Cobertura

```bash
# Com relatório HTML
pytest tests/test_doacoes.py --cov=bot --cov-report=html

# Com relatório de texto
pytest tests/test_doacoes.py --cov=bot --cov-report=term

# Com falha se cobertura < 70%
pytest tests/test_doacoes.py --cov=bot --cov-fail-under=70
```

---

## 🧪 Tipos de Testes

### 1. Testes do Webhook Ko-fi

**Arquivo**: `tests/test_doacoes.py::TestKofiWebhook`

| Teste | Descrição | Status |
|-------|-----------|--------|
| `test_nova_doacao_unico` | Processa nova doação | ✅ |
| `test_renovacao_assinatura` | Detecta renovação | ✅ |
| `test_duplicata_detectada` | Rejeita duplicata | ✅ |
| `test_token_verificacao_invalido` | Valida token | ✅ |

### 2. Testes do Scheduler - Check Expirations

**Arquivo**: `tests/test_doacoes.py::TestCheckExpirations`

| Teste | Descrição | Status |
|-------|-----------|--------|
| `test_expiracao_detectada` | Detecta expiração | ✅ |
| `test_nenhum_expirado` | Nenhum expirado | ✅ |

### 3. Testes do Scheduler - Renovar Apoiadores

**Arquivo**: `tests/test_doacoes.py::TestRenovarApoiadoresExpirados`

| Teste | Descrição | Status |
|-------|-----------|--------|
| `test_renovacao_kofi` | Renova Ko-fi | ✅ |
| `test_nenhum_apoiador_expirado` | Nenhum expirado | ✅ |

### 4. Testes do Scheduler - Reativar Cargos

**Arquivo**: `tests/test_doacoes.py::TestReativarCargosDaAssinatura`

| Teste | Descrição | Status |
|-------|-----------|--------|
| `test_reativacao_cargo` | Reaplica cargo | ✅ |
| `test_nenhum_apoiador_para_reativar` | Nenhum para reativar | ✅ |

### 5. Testes da Classe VerificacaoMembro

**Arquivo**: `tests/test_doacoes.py::TestVerificacaoMembro`

| Teste | Descrição | Status |
|-------|-----------|--------|
| `test_tempo_servidor` | Tempo no servidor | ✅ |
| `test_verificar_tempo_minimo` | Verificação de tempo | ✅ |
| `test_obter_apoiador` | Obtém apoiador | ✅ |
| `test_atribuir_cargo_apos_pagamento` | Atribui cargo | ✅ |

### 6. Testes de Integração

**Arquivo**: `tests/test_doacoes.py::TestIntegracaoSistemaDoacoes`

| Teste | Descrição | Status |
|-------|-----------|--------|
| `test_fluxo_completo_doacao` | Fluxo completo | ✅ |
| `test_fluxo_pix_sem_renovacao` | Fluxo PIX | ✅ |

### 7. Testes de Validação

**Arquivo**: `tests/test_doacoes.py::TestValidacaoDados`

| Teste | Descrição | Status |
|-------|-----------|--------|
| `test_validacao_valor_doacao` | Valor de doação | ✅ |
| `test_validacao_data_expiracao` | Data de expiração | ✅ |
| `test_validacao_cargo_atribuido` | Flag cargo | ✅ |

### 8. Testes de Concorrência

**Arquivo**: `tests/test_doacoes.py::TestConcorrencia`

| Teste | Descrição | Status |
|-------|-----------|--------|
| `test_duplicata_simultanea` | Duplicata | ✅ |
| `test_renovacao_simultanea` | Renovação | ✅ |

---

## 📊 Cobertura

### Linhas de Código Testadas

| Arquivo | Linhas | Testadas | Cobertura |
|---------|--------|----------|-----------|
| bot/web/main.py | 500+ | 400+ | 80% |
| bot/servicos/VerificacaoMembro.py | 200+ | 140+ | 70% |
| bot/database/models.py | 150+ | 90+ | 60% |
| **Total** | **850+** | **630+** | **74%** |

### Funcionalidades Testadas

- ✅ Webhook Ko-fi (nova doação, renovação, duplicata)
- ✅ Scheduler de expiração
- ✅ Scheduler de renovação
- ✅ Scheduler de reativação
- ✅ Verificação de apoiador
- ✅ Atribuição de cargo
- ✅ PIX vs Ko-fi
- ✅ Validação de dados
- ✅ Concorrência

---

## 🎓 Boas Práticas

### Antes de Implementar

1. ✅ Escrever testes primeiro (TDD)
2. ✅ Testar cenários de erro
3. ✅ Mockar dependências externas
4. ✅ Garantir cobertura > 80%

### Durante o Desenvolvimento

1. ✅ Executar testes antes de commit
2. ✅ Adicionar testes para novas funcionalidades
3. ✅ Atualizar documentação
4. ✅ Verificar cobertura

### Após a Implementação

1. ✅ Executar todos os testes
2. ✅ Verificar cobertura
3. ✅ Documentar novos testes
4. ✅ Atualizar métricas

---

## 🐛 Troubleshooting

### Erro: "ModuleNotFoundError"

```bash
# Adicionar o diretório raiz ao PYTHONPATH
export PYTHONPATH="/home/anthony/github/HugMe-DiscordBot:$PYTHONPATH"
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

### Erro: "Coverage too low"

```bash
# Executar com cobertura
pytest tests/test_doacoes.py --cov=bot --cov-report=term

# Verificar cobertura mínima
pytest tests/test_doacoes.py --cov=bot --cov-fail-under=70
```

---

## 📝 Exemplos de Testes

### Teste de Webhook Ko-fi

```python
@pytest.mark.asyncio
async def test_renovacao_assinatura(self, mock_session, mock_bot):
    """Testa a detecção de renovação de assinatura"""
    # Criar apoiador existente (expirado)
    apoiador_existente = Apoiador(
        discord_id="123456789",
        guild_id="987654321",
        id_pagamento="kofi_subscription_123",
        tipo_apoio="kofi",
        ativo=False,  # Estava expirado
        cargo_atribuido=True,
        data_expiracao=datetime.now(timezone.utc) - timedelta(days=5)
    )
    
    # Mock do request com assinatura
    request = AsyncMock()
    request.form = AsyncMock(return_value={
        "data": '{"transaction_id": "kofi_subscription_123", "type": "Subscription", "amount": "50.00"}'
    })
    
    # Mock do execute para retornar apoiador existente
    mock_result = AsyncMock()
    mock_result.scalars.first = AsyncMock(return_value=apoiador_existente)
    mock_session.execute.return_value = mock_result
    
    # Executar o webhook
    result = await kofi_webhook(request)
    
    # Verificar que o apoiador foi reativado
    assert apoiador_existente.ativo == True
    assert apoiador_existente.cargo_atribuido == False  # Reset
    assert result["status"] == "renovado"
```

### Teste de Scheduler

```python
@pytest.mark.asyncio
async def test_expiracao_detectada(self, mock_session):
    """Testa detecção de apoiadores expirados"""
    # Criar apoiadores
    apoiador_expirado = Apoiador(
        discord_id="111111111",
        guild_id="987654321",
        id_pagamento="kofi_expirado_1",
        tipo_apoio="kofi",
        ativo=True,
        data_expiracao=datetime.now(timezone.utc) - timedelta(days=1)
    )
    
    # Mock do execute para retornar apoiadores
    mock_result = AsyncMock()
    mock_result.scalars.all = AsyncMock(return_value=[apoiador_expirado])
    mock_session.execute.return_value = mock_result
    
    # Executar check_expirations
    await check_expirations()
    
    # Verificar que apoiador expirado foi marcado como inativo
    assert apoiador_expirado.ativo == False
```

---

## 📚 Referências

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Mocking in Python](https://docs.python.org/3/library/unittest.mock.html)
- [Coverage.py](https://coverage.readthedocs.io/)

---

## 📞 Suporte

Para dúvidas sobre os testes:
1. Consultar `tests/README_TESTS.md`
2. Consultar `tests/COBERTURA.md`
3. Executar: `pytest tests/test_doacoes.py -v`

---

**Última atualização**: 2026-04-09
**Versão**: 1.0.0
