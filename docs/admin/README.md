# Pacote Admin - Documentação Técnica

## Visão Geral

O pacote `bot/commands/admin/` é responsável por toda a administração do bot, incluindo:
- Gerenciamento de PIX e QR Codes
- Sistema de cargos (padrão e baseado em tempo)
- Gerenciamento manual de apoiadores
- Dashboard e estatísticas
- Confirmações e validações

## Estrutura de Arquivos

```
bot/commands/admin/
├── __init__.py              # Exporta setup()
├── cog.py                   # Classe AdminCommands e comandos
├── utils.py                 # check_is_owner(), _build_role_config_embed()
├── modals_pix.py            # Modais para PIX e configuração
├── views_base.py            # Views base reutilizáveis
├── views_dashboard.py       # Dashboard e paginação
├── views_pix.py             # Configuração PIX
├── views_roles.py           # Sistema de cargos
└── views_supporter.py       # Gerenciamento de apoiadores
```

## Módulos

### `cog.py` - Cog Principal

Contém a classe `AdminCommands` com todos os comandos slash e hybrid.

**Classe**: `AdminCommands(commands.Cog)`
- `__init__(bot)` - Inicializa com `SupporterRoleManager`
- `_get_dashboard_stats()` - Calcula estatísticas em tempo real
- `_manage_supporter_action()` - Helper para ações de apoiador

**Comandos Slash**:
- `add_supporter(user, months, type)` - Adiciona/estende apoiador
- `pause_supporter(user)` - Pausa apoio
- `resume_supporter(user)` - Retoma apoio
- `remove_supporter(user)` - Remove apoiador

**Comandos Hybrid**:
- `dashboard()` - Exibe painel com estatísticas
- `servers()` - Lista servidores
- `pix_config()` - Gerencia configuração PIX
- `set_default_supporter_role()` - Define cargo padrão
- `configure_time_roles()` - Configura cargos por tempo
- `manage_supporter()` - Interface de gerenciamento

### `utils.py` - Utilitários

**Funções**:

```python
def check_is_owner(ctx_or_interaction) -> bool:
    """Verifica se usuário é owner/dev.
    
    Suporta tanto Context quanto Interaction.
    Lê variáveis: TRUSTED_MOD_ID, DEV_ID
    """

def _build_role_config_embed(guild, config) -> discord.Embed:
    """Constrói embed de visualização de cargos configurados.
    
    Mostra:
    - Cargo padrão (se configurado)
    - Cargos por tempo (dias/meses/anos)
    """
```

### `modals_pix.py` - Modais de Configuração

**Classes**:

1. **SetQRCodeModal**
   - Campos: `qr_url`, `pix_key`, `nome_titular`, `cidade`
   - Valida URL (http/https)
   - Salva em `PixConfig`
   - Usa `ConfirmationView` para dupla confirmação

2. **ConfigureRoleModal**
   - Configuração de cargo (não utilizado atualmente)

3. **ConfirmationModal**
   - Modal genérico de confirmação
   - Exige digitação de "CONFIRMAR"
   - Callbacks: `confirm_callback`, `cancel_callback`

### `views_base.py` - Views Base

**Classes**:

1. **ConfirmView**
   - Botões simples: Confirmar/Cancelar
   - Timeout: 180s
   - Seta `self.confirmed` (True/False)

2. **ConfirmationView**
   - Integrada com callbacks
   - Defer automático antes de executar callback
   - Suporta `ephemeral=True`
   - Melhor que `ConfirmView` para operações assíncronas

### `views_dashboard.py` - Dashboard

**Classes**:

1. **DashboardView(ui.View)**
   - Botões: Atualizar, Gerenciar Apoiadores, Apoiadores, Servidores, PIX Config, Cargos, Modal PIX
   - Timeout: `None` (permanente)
   - Validação: `check_owner()`
   - Integra com todas as outras views

2. **SupportersPaginationView**
   - Paginação de apoiadores (8 por página)
   - Botões: Anterior, Próximo, Info de página
   - Exibe: Nome, tipo, nível, datas de início/expiração

### `views_pix.py` - Configuração PIX

**Classes**:

1. **PIXConfigView**
   - Botões: Editar (abre `SetQRCodeModal`), Limpar Config
   - Dupla confirmação para limpeza
   - Salva em BD via `AsyncSessionLocal`

### `views_roles.py` - Sistema de Cargos

**Classes**:

1. **PaginatedRoleSelectView**
   - Base para seleção de cargos com paginação
   - Suporta 25 cargos por página
   - Filtro opcional de padrões de tempo (regex)
   - Botões: Anterior, Próximo, Página Info

2. **DefaultRoleSelectView(PaginatedRoleSelectView)**
   - Seleciona cargo padrão
   - Salva em `GuildConfig.cargo_apoiador_default`
   - Confirmação dupla antes de salvar

3. **TimeRoleConfigView**
   - Botões: Adicionar Cargo, Ver Configurados
   - Modal: `TimeRoleModal`
   - Carrega cargos existentes async

4. **TimeRoleModal**
   - Input: Valor mínimo de apoio (threshold)
   - Próximo passo: Seleciona unidade (dias/meses/anos)

5. **TimeUnitSelectView**
   - Botões: Dias, Meses, Anos
   - Próximo passo: Seleciona cargo via `TimeRoleSelectView`

6. **TimeRoleSelectView(PaginatedRoleSelectView)**
   - Seleciona cargo final
   - `_execute_add_role()` - Salva em `GuildConfig.cargos_tempo`
   - Formato: `[{threshold, unit, role_id}, ...]`

7. **RoleConfigView**
   - Botões: Definir Cargo Padrão, Cargos por Tempo, Atualizar
   - Menu principal para configuração de cargos

### `views_supporter.py` - Gerenciamento de Apoiadores

**Classes Modais**:

1. **SupporterActionModal** (Adicionar)
   - Campos: usuario, threshold, tipo, valor
   - Fluxo: tipo de período → unidade → confirmação

2. **SupporterPauseModal**
   - Campo: usuario
   - Seta `ativo = False`

3. **SupporterResumeModal**
   - Campo: usuario
   - Seta `ativo = True` e `ultimo_pagamento = now`

4. **SupporterRemoveModal**
   - Campo: usuario
   - Deleta record do BD
   - Aviso: Ação irreversível

**Classes Views**:

1. **SupporterTimeTypeSelectView**
   - Escolha: Retroativo ou Antecipado
   - Próximo: `SupporterUnitSelectView`

2. **SupporterUnitSelectView**
   - Botões: Dias, Meses, Anos
   - `_execute_add_action()` - Lógica principal de adição/extensão
   - Atualiza BD e cargos do member

3. **ManageSupporterActionView**
   - Botões: Adicionar, Pausar, Continuar, Remover
   - Abre modais correspondentes

4. **ManageSupporterView**
   - Botão: Gerenciar Apoiador
   - Abre `ManageSupporterActionView`

## Fluxos de Dados

### Adicionar Apoiador

```
/manage_supporter
  ↓ (clica "Gerenciar Apoiador")
ManageSupporterView
  ↓ (clica "Adicionar")
SupporterActionModal (ID, meses, tipo, valor)
  ↓ (confirma)
SupporterTimeTypeSelectView (Retroativo/Antecipado)
  ↓ (seleciona)
SupporterUnitSelectView (Dias/Meses/Anos)
  ↓ (seleciona)
ConfirmationView (dupla confirmação)
  ↓ (confirma)
_execute_add_action()
  ↓ Salva no BD
  ↓ Atribui cargo padrão
  ↓ Atualiza cargos por tempo
  ✓ Sucesso!
```

### Configurar Cargo Padrão

```
/set_default_supporter_role
  ↓
DefaultRoleSelectView (paginação de cargos)
  ↓ (seleciona cargo)
ConfirmationView (dupla confirmação)
  ↓ (confirma)
Salva em GuildConfig.cargo_apoiador_default
  ✓ Sucesso!
```

### Configurar Cargos por Tempo

```
/configure_time_roles
  ↓
RoleConfigView
  ↓ (clica "Adicionar Cargo")
TimeRoleModal (insere threshold)
  ↓
TimeUnitSelectView (Dias/Meses/Anos)
  ↓
TimeRoleSelectView (seleciona cargo)
  ↓
ConfirmationView (dupla confirmação)
  ↓
_execute_add_role()
  ↓ Salva em GuildConfig.cargos_tempo
  ✓ Sucesso!
```

## Validações e Segurança

- **Verificação de Owner**: Todos os comandos usam `check_is_owner()`
- **Validação de URLs**: PIX - `startswith('http://' ou 'https://')`
- **Validação de IDs**: Converte para `int` antes de usar
- **Validação de Valores**: Cálculos em centavos para evitar floats
- **Dupla Confirmação**: Críticas (remover, limpar, adicionar) requerem confirmação visual
- **Rate Limiting**: Views têm timeout para evitar spam

## Integração com BD

**Modelos Usados**:
- `Apoiador` - Apoiadores do bot (discord_id, ativo, data_expiracao, etc.)
- `GuildConfig` - Configuração por servidor (cargo_apoiador_default, cargos_tempo)
- `PixConfig` - Configuração PIX global (url_qr, chave, titular, cidade)

**Operações**:
```python
# Adicionar/atualizar
async with AsyncSessionLocal() as session:
    result = await session.execute(select(Model).where(...))
    obj = result.scalars().first()
    # ... modifica obj ...
    await session.commit()

# Deletar
await session.delete(obj)
await session.commit()
```

## Padrões de Código

### Handling de Interações

```python
# Defer primeiro se operação é longa
await interaction.response.defer(ephemeral=True)

# Depois use followup para respostas
await interaction.followup.send(embed=embed, ephemeral=True)
```

### Error Handling

```python
try:
    # operação
except (discord.NotFound, discord.HTTPException) as e:
    if hasattr(e, 'code') and e.code == 10062:  # Interaction expired
        # tratamento especial
    else:
        logger.error(f"Erro: {e}")
```

### Logging

```python
logger = logging.getLogger(__name__)
logger.info(f"Ação realizada: {interaction.user}")
logger.error(f"Erro ao processar: {e}")
```

## Extensões Futuras

- [ ] Auditoria de ações (log de quem fez o quê)
- [ ] Backup automático de configurações
- [ ] Sistema de permissões granulares (não só owner)
- [ ] Integração com mais métodos de pagamento
- [ ] Dashboard em tempo real via web (API)
- [ ] Sincronização de cargos com sistemas externos

## Troubleshooting

**Problema**: Comandos não aparecem  
**Solução**: Sincronizar árvore de comandos: `await bot.tree.sync()`

**Problema**: Cargo não é atribuído  
**Solução**: Verificar `SupporterRoleManager.assign_default_supporter_role()`

**Problema**: Modal é cortado  
**Solução**: Reduzir número de fields ou usar múltiplos modais

**Problema**: Interação expirada (10062)  
**Solução**: Usar `defer()` imediatamente no handler

