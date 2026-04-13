# 🧪 Testes Unitários - HugMe Discord Bot

Este diretório contém os testes unitários para o sistema de cargos baseados no tempo de apoio.

## 📋 Pré-requisitos

### 1. Instalar dependências de teste
```bash
pip install -r requirements-test.txt
```

### 2. Ambiente de desenvolvimento
- Python 3.8+
- Virtual environment ativado
- Todas as dependências do bot instaladas

## 🚀 Executando os Testes

### Testes básicos
```bash
# Executar todos os testes
python run_tests.py

# Ou diretamente com pytest
pytest tests/ -v
```

### Testes com coverage
```bash
# Executar com relatório de cobertura
python run_tests.py --coverage

# Ou diretamente
pytest tests/ --cov=bot --cov-report=html
```

### Testes específicos
```bash
# Executar apenas uma classe
pytest tests/test_supporter_roles.py::TestSupporterRoleManager -v

# Executar apenas um teste
pytest tests/test_supporter_roles.py::TestSupporterRoleManager::test_get_guild_config_success -v

# Executar apenas testes de integração
pytest tests/ -m integration -v

# Executar apenas testes unitários (excluindo integração)
pytest tests/ -m "not integration" -v
```

## 📁 Estrutura dos Testes

```
tests/
├── test_supporter_roles.py    # Testes principais do sistema
│   ├── TestSupporterRoleManager    # Testes da classe principal
│   ├── TestWeeklyRoleCheck         # Testes do sistema semanal
│   └── TestIntegration            # Testes de integração
```

## 🎯 Cobertura de Testes

### SupporterRoleManager
- ✅ `get_guild_config()` - Obtenção de configuração
- ✅ `assign_default_supporter_role()` - Atribuição de cargo padrão
- ✅ `calculate_total_support_time()` - Cálculo de tempo de apoio
- ✅ `get_appropriate_time_role()` - Seleção de cargo por tempo
- ✅ `update_member_time_based_roles()` - Atualização de cargos
- ✅ `update_all_supporters_roles()` - Atualização em lote
- ✅ `get_supporter_stats()` - Estatísticas dos apoiadores

### WeeklyRoleCheck
- ✅ `weekly_check()` - Tarefa semanal automática
- ✅ `manual_weekly_check()` - Execução manual

## 🧩 Mocks Utilizados

### Discord.py Mocks
- `discord.Member` - Membro do servidor
- `discord.Guild` - Servidor Discord
- `discord.Role` - Cargo do Discord
- `discord.Bot` - Instância do bot

### SQLAlchemy Mocks
- `AsyncSessionLocal` - Sessão assíncrona do banco
- `GuildConfig` - Configuração do servidor
- `Apoiador` - Registro de apoiador

## 📊 Relatórios

### Coverage HTML
Após executar com `--coverage`, acesse:
```
htmlcov/index.html
```

### Métricas de Cobertura
- **Statements**: Cobertura de linhas de código
- **Branches**: Cobertura de branches condicionais
- **Functions**: Cobertura de funções
- **Classes**: Cobertura de classes

## 🔧 Debugging

### Ver logs detalhados
```bash
pytest tests/ -v -s --log-cli-level=INFO
```

### Executar com debugger
```bash
pytest tests/ --pdb
```

### Parar no primeiro erro
```bash
pytest tests/ -x
```

## 📈 Melhorando a Cobertura

### Áreas para expandir:
1. **Testes de erro** - Cenários de falha (permissões, rede, etc.)
2. **Testes de performance** - Benchmarks para operações em lote
3. **Testes de integração** - Com banco real (usando SQLite em memória)
4. **Testes end-to-end** - Fluxo completo com bot real

### Adicionando novos testes:
```python
@pytest.mark.asyncio
async def test_nome_do_teste(self, fixture):
    """Descrição do que o teste verifica"""
    # Arrange
    # Act
    # Assert
```

## 🚨 Boas Práticas

### ✅ FAZER
- Usar mocks para dependências externas
- Testar casos de sucesso E erro
- Manter testes independentes
- Usar nomes descritivos
- Documentar cenários complexos

### ❌ NÃO FAZER
- Testar código de terceiros
- Dependências entre testes
- Testes que requerem internet
- Testes que modificam estado global
- Testes muito lentos

## 🔄 CI/CD

Para integração contínua, adicionar ao pipeline:

```yaml
- name: Run Tests
  run: |
    pip install -r requirements-test.txt
    python run_tests.py --coverage
```

## 📞 Suporte

Para dúvidas sobre os testes:
1. Verificar logs de erro
2. Consultar documentação do pytest
3. Revisar código dos testes existentes
4. Abrir issue no repositório