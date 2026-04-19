# Sistema de Renovação Automática de Apoios

## Índice
1. [Visão Geral](#visão-geral)
2. [Fluxo de Renovação](#fluxo-de-renovação)
3. [Funções Detalhadas](#funções-detalhadas)
4. [Timeline de Execução](#timeline-de-execução)
5. [Campos do Banco de Dados](#campos-do-banco-de-dados)

---

## Visão Geral

O sistema agora funciona em **3 camadas** para garantir que apoiadores com assinatura Ko-fi recebam renovação automática:

```
┌─────────────────────────────────────────────────────────┐
│         APOIADOR COM ASSINATURA KO-FI                  │
│            Mês 1: Doa R$50/mês                          │
└─────────────────────────────────────────────────────────┘
                          ↓
        ┌─────────────────────────────────────┐
        │ Ko-fi envia webhook "Subscription"  │
        │ (mensalmente, automaticamente)      │
        └─────────────────────────────────────┘
                          ↓
        ┌─────────────────────────────────────┐
        │ 1️⃣ WEBHOOK DETECTA RENOVAÇÃO       │
        │ (kofi_webhook function)            │
        │ - Se é assinatura = RENOVADO [OK]    │
        │ - Reativa: ativo=True              │
        │ - Estende: data_expiracao += 30d   │
        └─────────────────────────────────────┘
                          ↓
        ┌─────────────────────────────────────┐
        │ 2️⃣ SCHEDULER REAPLICA CARGO        │
        │ (reativar_cargos_da_assinatura)    │
        │ - A cada 2 horas                   │
        │ - Busca: ativo=True, cargo_atrib=F │
        │ - Aplica: discord_role              │
        │ - Marca: cargo_atribuido=True       │
        └─────────────────────────────────────┘
                          ↓
        ┌─────────────────────────────────────┐
        │ ✨ APOIADOR RECEBE CARGO DE VOLTA  │
        │    Sem fazer nada!                 │
        └─────────────────────────────────────┘
```

---

## Fluxo de Renovação

### Cenário 1: Assinatura Ko-fi Renovando

```
DIA 30 (Expiração do mês anterior):
├─ Ko-fi envia webhook com mismo transaction_id
├─ Sistema DETECTA que já existe (renovação)
│  └─ Em vez de IGNORAR, REATIVA!
│     ├─ ativo = True
│     ├─ cargo_atribuido = False (reset)
│     └─ data_expiracao = agora + 30 dias
└─ Webhook responde: {"status": "renovado"}

DIA 30 + 2h (Scheduler executando a cada 2h):
├─ reativar_cargos_da_assinatura() busca:
│  ├─ ativo = True
│  ├─ cargo_atribuido = False
│  └─ tipo_apoio = "kofi"
├─ Para cada apoiador encontrado:
│  ├─ Busca membro no Discord
│  ├─ Aplica role
│  └─ Marca: cargo_atribuido = True
└─ [OK] Apoiador tem cargo novamente!

DIA 60 (Próxima expiração):
├─ Scheduler check_expirations() a cada 6h
├─ Se data_expiracao < agora e ativo=True
│  └─ Marca: ativo = False (desativa)
└─ Scheduler renovar_apoiadores_expirados() a cada 12h
   ├─ Busca: ativo=False, tipo_apoio="kofi"
   ├─ Se encontrar: reativa novamente!
   │  ├─ ativo = True
   │  └─ data_expiracao = agora + 30 dias
   └─ Próximo ciclo: cargo reaplicado em 2h ```

### Cenário 2: PIX (Sem Renovação Automática)

```
DIA 1: Usuário doa via PIX
├─ Cria: Apoiador com tipo_apoio="pix"
├─ data_expiracao = NULL (não tem)
└─ Cargo é atribuído manualmente

DIA X (Sem renovação):
├─ O apoio NÃO expira (data_expiracao é NULL)
├─ Usuário mantém cargo indefinidamente
└─ (Comportamento esperado para doação única)
```

---

## Funções Detalhadas

### [1] `check_expirations()` - Detecta Expiração

```python
async def check_expirations():
```

**Quando executa?** A cada 6 horas (scheduler)

**O que faz:**
1. Busca apoiadores onde:
   - `data_expiracao < agora` (data passou)
   - `ativo = True` (estão ativos)
2. Para cada um:
   - Marca: `ativo = False`
   - Log: "Apoiador expirado"
3. Salva no banco

**Exemplo:**
```
Entrada: Apoiador A com data_expiracao = 2026-04-08 23:59:59
Agora:   2026-04-09 00:00:00
Resultado: ativo = False ❌
```

**Propósito:** Marcar quem precisa renovar

---

### [2] `renovar_apoiadores_expirados()` - Reativa Assinatura

```python
async def renovar_apoiadores_expirados():
```

**Quando executa?** A cada 12 horas (scheduler)

**O que faz:**
1. Busca apoiadores onde:
   - `ativo = False` (foram desativados)
   - `tipo_apoio = "kofi"` (têm assinatura automática)
   - `data_expiracao != None` (tinham data, não é PIX)
2. Para cada um encontrado:
   - Marca: `ativo = True` (reativa!)
   - Atualiza: `data_expiracao = agora + 30 dias`
   - Log: "Apoiador Ko-fi renovado automaticamente"
3. Salva no banco

**Exemplo:**
```
ANTES:
  ativo = False ❌
  data_expiracao = 2026-04-08 23:59:59 (passou)
  tipo_apoio = "kofi"

DEPOIS (após renovar_apoiadores_expirados):
  ativo = True ✅
  data_expiracao = 2026-05-09 23:59:59 (já estendido!)
  tipo_apoio = "kofi"
```

**Propósito:** Reativar automaticamente quem tem assinatura

---

### [3] `reativar_cargos_da_assinatura()` - Reaplica Role

```python
async def reativar_cargos_da_assinatura():
```

**Quando executa?** A cada 2 horas (scheduler - mais frequente!)

**O que faz:**
1. Busca apoiadores onde:
   - `ativo = True` (estão ativos)
   - `cargo_atribuido = False` (cargo foi reset)
   - `tipo_apoio = "kofi"` (assinatura automática)
2. Para cada um:
   - Pega instância do bot
   - Tenta encontrar membro em cada servidor
   - Se encontrar: `await member.add_roles(role)`
   - Marca: `cargo_atribuido = True` (já processado)
   - Log: "Cargo reaplicado para: {user}"
3. Salva no banco

**Exemplo:**
```
ANTES:
  ativo = True ✅
  cargo_atribuido = False [NAO] (precisa reaplicar)
  tipo_apoio = "kofi"

DEPOIS (após reativar_cargos):
  ativo = True ✅
  cargo_atribuido = True [OK] (cargo já aplicado!)
  discord: user recebeu role

Discord: @User agora tem role "Apoiador" novamente! ```

**Propósito:** Colocar o cargo de volta no Discord

---

### [4] `kofi_webhook()` - Detecta Renovação no Webhook

**Adição ao webhook existente:**

```python
# TRATAMENTO DE RENOVAÇÃO DE ASSINATURA
if exists_dupped and data["type"] == "Subscription" and not is_test:
    logger.info(f"🔄 RENOVAÇÃO de assinatura Ko-fi detectada")
    exists_dupped.ativo = True
    exists_dupped.cargo_atribuido = False  # Reset cargo
    exists_dupped.data_expiracao = datetime.now(timezone.utc) + timedelta(days=30)
    exists_dupped.ultimo_pagamento = datetime.now(timezone.utc)
    session.add(exists_dupped)
    await session.commit()
    return {"status": "renovado"}
```

**Quando executa?** Quando Ko-fi envia webhook (mensalmente para assinatura)

**O que faz:**
1. Recebe webhook do Ko-fi
2. Verifica se `id_pagamento` já existe (renewal)
3. Se for assinatura (`data["type"] == "Subscription"`):
   - Reativa: `ativo = True`
   - Reset cargo: `cargo_atribuido = False`
   - Estende: `data_expiracao += 30 dias`
   - Atualiza: `ultimo_pagamento = agora`
4. Responde: `{"status": "renovado"}`

**Exemplo:**
```
Ko-fi envia: 
{
  "transaction_id": "12345",
  "type": "Subscription",
  "from_name": "João",
  "amount": "50.00"
}

Sistema detecta:
- transaction_id já existe (= renovação!)
- type = Subscription (= assinatura recorrente)

Sistema faz:
- ativo = True
- cargo_atribuido = False
- data_expiracao += 30 dias
- return {"status": "renovado"}

Próximo passo: reativar_cargos_da_assinatura() vai rodar e aplicar cargo!
```

**Propósito:** Capturar renovações mensais direto do Ko-fi

---

## Timeline de Execução

```
┌─ MÊS 1 ─────────────────────────────────────────┐
│ DIA 1:                                           │
│ ├─ Usuário doa via Ko-fi (assinatura R$50/mês) │
│ ├─ Webhook envia dados                          │
│ ├─ Sistema cria Apoiador:                       │
│ │  ├─ id_pagamento = "kofi_123"                │
│ │  ├─ tipo_apoio = "kofi"                      │
│ │  ├─ ativo = True                             │
│ │  ├─ data_expiracao = 2026-05-01 (30 dias)   │
│ │  └─ ja_pago = True                           │
│ ├─ Cargo é aplicado imediatamente              │
│ │  └─ User recebe: @Apoiador                   │
│ └─ [OK] Pronto!                                   │
│                                                 │
│ DIA 2-30: User tem cargo                       │
└─────────────────────────────────────────────────┘

        ↓ (28 dias depois...)

┌─ MÊS 2 - DIA 30 ────────────────────────────────┐
│ check_expirations() roda a cada 6h:            │
│ ├─ data_expiracao (2026-05-01) < agora ✓      │
│ ├─ ativo = True ✓                              │
│ └─ Marca: ativo = False                        │
│                                                │
│ renovar_apoiadores_expirados() roda a cada 12h:
│ ├─ Busca: ativo=False, tipo_apoio="kofi"      │
│ ├─ Encontra nosso Apoiador                    │
│ └─ Reativa:                                    │
│    ├─ ativo = True                            │
│    ├─ cargo_atribuido = False (reset!)        │
│    └─ data_expiracao = 2026-06-01 (novo +30d) │
│                                                │
│ reativar_cargos_da_assinatura() roda em 2h:   │
│ ├─ Busca: ativo=True, cargo_atribuido=False   │
│ ├─ Encontra nosso Apoiador                    │
│ ├─ Aplica role no Discord: @Apoiador          │
│ └─ Marca: cargo_atribuido = True               │
│                                                │
│ ✨ User tem cargo de novo! Sem fazer nada!    │
└─────────────────────────────────────────────────┘

        ↓ (30 dias depois...)

┌─ MÊS 3 - DIA 60 ────────────────────────────────┐
│ Mesmo ciclo se repete...                       │
│ [OK] Renovação automática funciona indefinidly! │
└─────────────────────────────────────────────────┘
```

---

## Campos do Banco de Dados

### Tabela `apoiadores` - Campos Importantes

| Campo | Tipo | Propósito | Exemplo |
|-------|------|----------|---------|
| `id` | INT | ID único | 1 |
| `discord_id` | VARCHAR(20) | ID do usuário | "123456789" |
| `id_pagamento` | VARCHAR(50) | ID da transação (único) | "kofi_123" |
| **`tipo_apoio`** | VARCHAR(20) | "pix" ou "kofi" | "kofi" |
| **`ativo`** | BOOL | Se suporte está ativo? | True/False |
| **`data_inicio`** | DATETIME | Quando começou | 2026-04-01 |
| **`data_expiracao`** | DATETIME | Quando expira | 2026-05-01 |
| **`ultimo_pagamento`** | DATETIME | Último pagamento | 2026-04-30 |
| **`cargo_atribuido`** | BOOL | Cargo já aplicado? | True/False |
| **`duracao_meses`** | INT | Duração em meses | 12 |
| **`ja_pago`** | BOOL | Pagamento confirmado? | True/False |
| `nivel` | INT | Nível de apoio | 1, 2, 3... |

### Fluxo de Estados

```
┌─────────────────────────────────────────────────────┐
│                     NOVO APOIADOR                   │
│  (webhook Ko-fi recebido, primeira doação)          │
│                                                     │
│  [OK] ativo = True                                    │
│  [OK] data_expiracao = agora + 30 dias               │
│  [NAO] cargo_atribuido = False                         │
│  [OK] ja_pago = True                                  │
└─────────────────────────────────────────────────────┘

                      ↓ (reativar_cargos roda)

┌─────────────────────────────────────────────────────┐
│              CARGO APLICADO (ATIVO)                 │
│  (User tem @Apoiador role no Discord)               │
│                                                     │
│  [OK] ativo = True                                    │
│  [OK] data_expiracao = agora + 30 dias               │
│  [OK] cargo_atribuido = True                          │
│  [OK] ja_pago = True                                  │
└─────────────────────────────────────────────────────┘

                 ↓ (30 dias passam...)
             ↓ (check_expirations roda)

┌─────────────────────────────────────────────────────┐
│              EXPIRADO (INATIVO)                      │
│  (Cargo removido do user, mas dados mantidos)       │
│                                                     │
│  [NAO] ativo = False                                   │
│ data_expiracao = 2026-05-01 (passou!)          │
│  [OK] cargo_atribuido = True (antigo)                │
│  [OK] ja_pago = True (antigo)                         │
└─────────────────────────────────────────────────────┘

         ↓ (renovar_apoiadores_expirados roda)
         [apenas para tipo_apoio="kofi"]

┌───────────────────────────────────────────────────────┐
│              RENOVADO (REATIVADO)                     │
│  (Sistema detectou renovação de assinatura)           │
│                                                       │
│  [OK] ativo = True (reativado!)                       │
│  [OK] data_expiracao = agora + 30 dias (estendido!)   │
│  [NAO] cargo_atribuido = False (reset para reaplicar!)│
│  [OK] ja_pago = True                                  │
└───────────────────────────────────────────────────────┘

             ↓ (reativar_cargos roda novamente)

┌─────────────────────────────────────────────────────┐
│          CARGO REAPLICADO (2º CICLO)                │
│  (User tem @Apoiador role novamente!)               │
│                                                     │
│  [OK] ativo = True                                  │
│  [OK] data_expiracao = agora + 30 dias              │
│  [OK] cargo_atribuido = True (reaplicado!)          │
│  [OK] ja_pago = True                                │
└─────────────────────────────────────────────────────┘ Ciclo continua infinitamente...
```

---

## Resumo Rápido

| Evento | O que acontece | Quando |
|--------|---------------|--------|
| Usuário doa via Ko-fi (assinatura) | Webhook cria Apoiador, aplic cargo | Imediato |
| Passa data_expiracao | check_expirations marca ativo=False | A cada 6h |
| Apoiador é expirado + Ko-fi | renovar_apoio reativa (ativo=True) | A cada 12h |
| Cargo_atribuido = False + ativo=True | reativar_cargos reaplica role | A cada 2h |
| Ko-fi envia renovação (subscription) | kofi_webhook detecta e reativa | Mensal (do Ko-fi) |

---

## Checklist de Implementação

- [x] `check_expirations()` - Marcar como expirado
- [x] `renovar_apoiadores_expirados()` - Reativar expirados Ko-fi
- [x] `reativar_cargos_da_assinatura()` - Reaplicar roles
- [x] `kofi_webhook()` - Detectar renovação de assinatura
- [x] Scheduler para 3 funções nas frequências corretas
- [x] Campos no BD para rastrear tudo

---

## Resultado Final

```
┌─────────────────────────────────────────────────────┐
│  APOIADORES COM ASSINATURA KO-FI AGORA:             │
│                                                     │
│  [OK] Recebem renovação AUTOMÁTICA mensalmente      │
│  [OK] Não precisam reconfirmar a doação             │
│  [OK] Cargo volta automaticamente a cada renovação  │
│  [OK] Sistema rastreia histórico completo           │
│  [OK] Tudo funciona sem intervenção manual          │
└─────────────────────────────────────────────────────┘
```
