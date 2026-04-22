# Comandos de Teste para Doações e Cargos

Este documento descreve os comandos de teste implementados para simular e validar as funcionalidades de doação e atribuição de cargos baseada em tempo.

## Visão Geral

Os comandos de teste foram criados para permitir que administradores testem as funcionalidades de doação e cargos sem precisar fazer doações reais ou esperar longos períodos de tempo. Todos os comandos são restritos a administradores do servidor.

## Comandos Disponíveis

### `/test_doacao`

Simula uma doação para um membro e testa automaticamente a atribuição de cargos.

**Parâmetros:**
- `membro` (obrigatório): Membro do Discord para simular a doação
- `valor` (obrigatório): Valor da doação em R$

**Exemplos:**
```
/test_doacao membro:@João valor:50
```

Após executar o comando, um modal aparecerá para você escolher:
- **Tempo de apoio**: Quantidade numérica (ex: 30)
- **Unidade**: Dias, semanas, meses ou anos

**O que faz:**
1. Remove qualquer registro anterior do membro para teste limpo
2. Cria um registro de doação simulada no banco de dados
3. Atribui cargo padrão de apoiador
4. Atribui cargo baseado no tempo de apoio (convertido automaticamente)
5. Mostra um relatório completo da operação

### `/test_atualizar_cargos`

Força a atualização de cargos para todos os apoiadores do servidor.

**Parâmetros:** Nenhum

**Exemplo:**
```
/test_atualizar_cargos
```

**O que faz:**
- Processa todos os apoiadores ativos do servidor
- Atualiza cargos padrão e baseados em tempo
- Mostra estatísticas da operação (total processado, atualizados)

### `/test_verificar_apoiador`

Verifica o status completo de apoiador de um membro.

**Parâmetros:**
- `membro` (opcional): Membro para verificar (padrão: você mesmo)

**Exemplos:**
```
/test_verificar_apoiador
/test_verificar_apoiador membro:@João
```

**O que mostra:**
- Dados do registro no banco (tipo de apoio, valor, datas)
- Tempo total de apoio calculado
- Cargo apropriado baseado no tempo
- Lista de todos os cargos de apoiador que o membro possui

### `/test_limpar_apoiador`

Remove o registro de apoiador de um membro para limpeza de testes.

**Parâmetros:**
- `membro` (obrigatório): Membro para limpar

**Exemplo:**
```
/test_limpar_apoiador membro:@João
```

**O que faz:**
- Remove registros do banco de dados
- Remove todos os cargos de apoiador do membro
- Mostra quantos registros e cargos foram removidos



## Configuração de Cargos por Tempo

### Formato Antigo (Dias apenas)
```json
{
  "cargos_tempo": {
    "30": "123456789",
    "90": "987654321"
  }
}
```

### Formato Novo (Múltiplas Unidades)
```json
{
  "cargos_tempo": [
    {
      "threshold": 30,
      "unit": "days",
      "role_id": "123456789"
    },
    {
      "threshold": 3,
      "unit": "months", 
      "role_id": "987654321"
    },
    {
      "threshold": 1,
      "unit": "years",
      "role_id": "456789123"
    }
  ]
}
```

### Unidades Suportadas
- `days` / `d` - Dias
- `weeks` / `w` - Semanas  
- `months` / `m` - Meses (30 dias)
- `years` / `y` - Anos (365 dias)

### Migração
Se você tinha configurações no formato antigo, execute o script de migração:
```bash
python migration_guild_config.py
```

Este script converterá automaticamente todas as configurações antigas para o novo formato, assumindo que os valores antigos eram em dias.
## Cenários de Teste Recomendados

### 1. Teste Básico de Doação
```
/test_doacao membro:@TestUser valor:10
```
Verifica se o cargo padrão é atribuído corretamente.

### 2. Teste de Cargo por Tempo
```
/test_doacao membro:@TestUser valor:25
```
No modal, selecione "2" e "months" para testar cargos de 2 meses.

### 3. Teste de Atualização em Massa
```
/test_atualizar_cargos
```
Atualiza todos os apoiadores após mudanças na configuração.

### 4. Verificação de Status
```
/test_verificar_apoiador membro:@TestUser
```
Verifica se tudo está funcionando corretamente.

### 5. Limpeza
```
/test_limpar_apoiador membro:@TestUser
```
Limpa dados de teste antes de novos testes.

## Segurança

- Todos os comandos são restritos a administradores do servidor
- As operações são logged para auditoria
- Dados simulados são claramente marcados como "pix_simulado"
- Não afeta doações reais

## Troubleshooting

### Comando não aparece
- Verifique se você é administrador do servidor
- Reinicie o bot para carregar novos comandos
- Use `/sync` se disponível para sincronizar comandos slash

### Cargos não são atribuídos
- Verifique se os cargos estão configurados em `GuildConfig`
- Confirme que os IDs dos cargos estão corretos
- Verifique logs do bot para erros

### Dados não aparecem
- Certifique-se de que o banco de dados está conectado
- Verifique se há erros nos logs do bot
- Teste com um membro diferente

## Arquivos Relacionados

- `bot/commands/test_supporter.py` - Implementação dos comandos
- `bot/servicos/SupporterRoleManager.py` - Lógica de atribuição de cargos
- `bot/database/models.py` - Modelos de dados
- `tests/test_supporter_roles.py` - Testes unitários
