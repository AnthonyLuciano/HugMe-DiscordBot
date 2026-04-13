# Sistema de Cargos Baseados no Tempo de Apoio

## 🎯 Visão Geral

O novo sistema permite configurar **cargos automáticos baseados no tempo de apoio** dos membros, com checagem semanal automática.

## 🏗️ Componentes

### 1. **Cargo Padrão de Apoiador**
- Cargo básico que **todos os apoiadores** recebem automaticamente
- Configurado via `/set_default_supporter_role`

### 2. **Cargos por Tempo de Apoio**
- Cargos especiais baseados no tempo total de apoio
- Exemplos: 30 dias, 90 dias, 180 dias, 1 ano
- Configurado via `/configure_time_roles`

### 3. **Checagem Semanal Automática**
- Executa toda segunda-feira às 9:00 UTC
- Atualiza cargos de todos os apoiadores ativos
- Comando manual: `/weekly_check_now` (apenas admin)

## ⚙️ Configuração

### Passo 1: Executar Migração do Banco
```sql
-- Execute o arquivo migration_time_roles.sql no seu MySQL
source migration_time_roles.sql;
```

### Passo 2: Configurar Cargo Padrão
```
/set_default_supporter_role
```
- Selecione o cargo que todos os apoiadores terão

### Passo 3: Configurar Cargos por Tempo
```
/configure_time_roles
```
- Clique em "➕ Adicionar Cargo"
- Digite os dias mínimos (ex: 30, 90, 180)
- Selecione o cargo correspondente
- Clique em "💾 Salvar Configuração"

### Passo 4: Verificar Estatísticas
```
/supporter_stats
```
- Mostra total de apoiadores
- Lista cargos por tempo configurados
- Conta membros em cada nível

## 🔄 Como Funciona

### Quando Alguém Doa:
1. **Pagamento confirmado** → Recebe cargo padrão automaticamente
2. **Sistema calcula tempo total** de apoio (soma todas as doações)
3. **Atribui cargo de tempo** apropriado baseado nos dias

### Checagem Semanal:
- Executa automaticamente toda segunda-feira
- Recalcula tempo de apoio para todos os membros
- Atualiza cargos conforme necessário
- Remove cargos antigos e atribui novos

## 📊 Exemplo de Configuração

```
Cargo Padrão: "Apoiador" (todos recebem)

Cargos por Tempo:
├── 30 dias+: "Apoiador Ativo"
├── 90 dias+: "Apoiador Veterano"
├── 180 dias+: "Apoiador Elite"
└── 365 dias+: "Apoiador Lendário"
```

## 📋 Comandos Disponíveis

### Para Admins:
- `/set_default_supporter_role` - Define cargo padrão
- `/configure_time_roles` - Configura cargos por tempo
- `/weekly_check_now` - Executa checagem manual
- `/supporter_stats` - Estatísticas dos apoiadores

### Para Todos:
- `/supporter_stats` - Ver estatísticas (modo leitura)

## 🔧 Personalização

### Tempos Sugeridos:
- **30 dias**: Apoiador Ativo
- **90 dias**: Apoiador Veterano
- **180 dias**: Apoiador Elite
- **365 dias**: Apoiador Lendário

### Cálculo de Tempo:
- Conta apenas doações **confirmadas** (`ja_pago = True`)
- Soma todos os períodos de apoio ativo
- Não remove tempo se doação expirar

## 🚨 Notas Importantes

1. **Banco de dados**: Execute a migração antes de usar
2. **Permissões**: Bot precisa de permissões para gerenciar cargos
3. **Hierarquia**: Bot deve estar acima dos cargos que gerencia
4. **Checagem**: Sistema roda automaticamente, mas pode ser manual

## 📈 Benefícios

- ✅ **Automação completa** de cargos
- ✅ **Escalabilidade** ilimitada
- ✅ **Flexibilidade** de configuração por servidor
- ✅ **Manutenção mínima** (checagem semanal automática)
- ✅ **Reconhecimento** do tempo de apoio dos membros