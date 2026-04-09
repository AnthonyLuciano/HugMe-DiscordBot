# 📚 Documentação do Sistema de Renovação Automática

## 📝 Resumo das Atualizações

### Arquivos Atualizados

| Arquivo | Descrição |
|---------|-----------|
| `bot/web/main.py` | Adicionado 3 funções de scheduler + detecção de renovação no webhook |
| `docs/webhooks.md` | Documentado webhook Ko-fi com renovação automática |
| `docs/database.md` | Documentado modelo Apoiador com todos os campos |
| `docs/servicos.md` | Documentado VerificacaoMembro com renovação |
| `docs/commands.md` | Atualizado com integração Ko-fi |
| `docs/config.md` | Adicionado variáveis de configuração |
| `docs/web.md` | Documentado scheduler e endpoints |
| `README.md` | Atualizado com sistema de renovação |
| `docs/sistema_renovacao.md` | **NOVO** - Documentação completa do sistema |

---

## 🔧 O Que Foi Implementado

### 1. Webhook Ko-fi (`bot/web/main.py`)
```python
# Detecta renovação de assinatura
if exists_dupped and data["type"] == "Subscription":
    apoiador.ativo = True
    apoiador.cargo_atribuido = False  # Reset para reaplicar cargo
    apoiador.data_expiracao = agora + 30 dias
    return {"status": "renovado"}
```

### 2. Scheduler de Renovação (`bot/web/main.py`)

#### `check_expirations()` - A cada 6 horas
- Busca: `data_expiracao < agora AND ativo = True`
- Marca: `ativo = False`

#### `renovar_apoiadores_expirados()` - A cada 12 horas
- Busca: `ativo = False AND tipo_apoio = "kofi"`
- Reativa: `ativo = True, data_expiracao += 30 dias`

#### `reativar_cargos_da_assinatura()` - A cada 2 horas
- Busca: `ativo = True AND cargo_atribuido = False AND tipo_apoio = "kofi"`
- Aplica: cargo no Discord
- Marca: `cargo_atribuido = True`

---

## 📊 Fluxo Completo

```
DIA 30 (Expiração):
├─ check_expirations() → ativo=False
└─ renovar_apoiadores_expirados() → ativo=True, data_expiracao=+30d

DIA 30 + 2h:
└─ reativar_cargos_da_assinatura() → cargo reaplicado no Discord

DIA 60 (Próxima expiração):
└─ Ciclo se repete automaticamente
```

---

## 🗄️ Novos Campos no Banco

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `cargo_atribuido` | BOOL | Cargo já aplicado neste ciclo? |
| `ultimo_pagamento` | DATETIME | Último pagamento da assinatura |
| `data_expiracao` | DATETIME | Quando a assinatura expira |

---

## 📖 Documentação Completa

### `docs/sistema_renovacao.md`
- Visão geral do sistema
- Fluxo de renovação
- Funções detalhadas
- Timeline de execução
- Caminhos de estados
- Checklist de implementação

---

## ✅ Resultado Final

**Apoiadores com assinatura Ko-fi agora:**
- ✅ Recebem renovação automática mensalmente
- ✅ Não precisam reconfirmar a doação
- ✅ Cargo volta automaticamente a cada renovação
- ✅ Sistema rastreia histórico completo
- ✅ Tudo funciona sem intervenção manual

---

## 🎯 Próximos Passos (Opcional)

- [ ] Adicionar notificação para usuário quando cargo for reaplicado
- [ ] Adicionar logs detalhados de renovação
- [ ] Adicionar painel para visualizar histórico de renovações
- [ ] Adicionar opção para usuário cancelar assinatura
- [ ] Adicionar relatórios de conversão de doações

---

## 📞 Suporte

Para dúvidas sobre o sistema de renovação, consulte:
- `docs/sistema_renovacao.md` - Documentação completa
- `docs/webhooks.md` - Webhooks Ko-fi
- `docs/database.md` - Modelos de dados
- `docs/servicos.md` - Serviços de verificação
