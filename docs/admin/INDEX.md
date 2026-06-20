# Documentação - Admin Package

## Índice

Esta pasta contém documentação completa sobre o pacote `bot/commands/admin/`.

### Para Usuários

- **[GUIDE.md](GUIDE.md)** ⭐ *Recomendado para começar*
  - Guia prático passo-a-passo
  - Exemplos de cada comando
  - Troubleshooting comum
  - Dicas e atalhos

### Para Desenvolvedores

- **[README.md](README.md)** 🔧 *Documentação técnica*
  - Estrutura de arquivos
  - Descrição de cada módulo
  - Fluxos de dados
  - Integração com BD
  - Padrões de código
  - Troubleshooting técnico

## Estrutura Rápida

```
bot/commands/admin/
├── __init__.py              # Setup function
├── cog.py                   # 400+ lines - Todos os comandos
├── utils.py                 # Funções auxiliares
├── modals_pix.py            # PIX configuration
├── views_base.py            # Base views
├── views_dashboard.py       # Dashboard & stats
├── views_pix.py             # PIX UI
├── views_roles.py           # Role system
└── views_supporter.py       # Supporter management
```

**9 arquivos** organizados por funcionalidade:
- **1 cog** = lógica de comandos
- **4 modais** = UI input
- **5 views** = UI buttons/interactions

## Comandos Principais

| Tipo | Comando | Descrição |
|------|---------|-----------|
| Slash | `/add_supporter` | Adiciona apoiador |
| Slash | `/pause_supporter` | Pausa apoio |
| Slash | `/resume_supporter` | Retoma apoio |
| Slash | `/remove_supporter` | Remove apoiador |
| Hybrid | `/dashboard` | Painel de controle |
| Hybrid | `/manage_supporter` | Interface integrada |
| Hybrid | `/pix_config` | Configuração PIX |
| Hybrid | `/set_default_supporter_role` | Cargo padrão |
| Hybrid | `/configure_time_roles` | Cargos por tempo |
| Hybrid | `/servers` | Lista servidores |

## Fluxos Populares

1. **Novo Apoiador**: `/manage_supporter` → Adicionar → Modal → Tipo → Unidade → Confirmar
2. **Configurar Servidor**: `/set_default_supporter_role` + `/configure_time_roles`
3. **Gerenciar PIX**: `/pix_config` → Editar → Modal → Confirmar

## Validações

- ✅ Acesso restrito a admins (TRUSTED_MOD_ID, DEV_ID)
- ✅ Dupla confirmação em operações críticas
- ✅ Validação de URLs (http/https)
- ✅ Timeout de 180-3600s para evitar spam
- ✅ Trata erros Discord (expired interactions, invalid roles, etc)

## Contribuindo

Ao modificar o pacote admin:

1. **Adicione testes** em `tests/` antes de mudar cog.py
2. **Mantenha README.md atualizado** com nova estrutura
3. **Atualize GUIDE.md** se adiciona novo comando/feature
4. **Sincronize árvore de comandos**: `await bot.tree.sync()`

Exemplo de adição:
```python
# Em cog.py
@app_commands.command(name="seu_comando")
async def seu_comando(self, interaction: discord.Interaction):
    """Descrição do seu comando."""
    await interaction.response.defer()
    # ... sua lógica ...
    await interaction.followup.send("Sucesso!")
```

Depois atualize:
- GUIDE.md (adicione novo item em "Sumário Rápido")
- README.md (adicione fluxo se for feature complexa)
- docs/commands/commands.md (sincronize lista)

## Status de Implementação

| Feature | Status | Arquivo |
|---------|--------|---------|
| Gerenciamento de PIX | ✅ Completo | modals_pix.py, views_pix.py |
| Cargo padrão | ✅ Completo | views_roles.py |
| Cargos por tempo | ✅ Completo | views_roles.py |
| Gerenciamento manual de apoiadores | ✅ Completo | views_supporter.py |
| Dashboard com paginação | ✅ Completo | views_dashboard.py |
| Dupla confirmação | ✅ Completo | views_base.py |
| Auditoria de ações | ⏳ TODO | - |
| Backup automático | ⏳ TODO | - |
| Permissões granulares | ⏳ TODO | - |

## Links Úteis

- [Documentação completa de comandos](../commands/commands.md)
- [Modelos do BD](../database/database.md) - Apoiador, GuildConfig, PixConfig
- [Sistema de doações](../donations/renewal.md)
- [Configuração inicial](../setup/config.md)

## FAQ

**P: Como adiciono um novo comando?**  
R: Edite `cog.py`, adicione método com `@app_commands.command()` ou `@commands.hybrid_command()`, sincronize com `bot.tree.sync()`.

**P: Por que há tantos arquivos?**  
R: Cada arquivo tem responsabilidade única (single responsibility principle), facilitando manutenção.

**P: Como testo mudanças?**  
R: Use servidor de teste, execute `tests/run_tests.sh`, verifique permissões de cargo.

**P: Posso mover módulos?**  
R: Sim, mas atualize imports em `__init__.py` e docs depois.

---

**Última atualização**: 2026-06-20  
**Versão**: 2.0 (refatorado em módulos)  
**Mantido por**: @bot-dev

