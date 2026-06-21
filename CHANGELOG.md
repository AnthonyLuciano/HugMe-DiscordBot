# Changelog

Todas as mudanças importantes no HugMe serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere à [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [1.13] - 2026-06-20

### Adicionado / Alterado

- **Remoção completa de cargos de apoiador**: Ao confirmar a remoção de um apoiador via modal administrativo, o sistema agora remove também o cargo padrão de apoiador e todos os cargos por tempo (30d/90d/...) que o usuário possua. Arquivo afetado: `bot/commands/admin/views_supporter.py`.

- **Pergunta de atividade e ajuste de expiração**: Antes da confirmação final ao adicionar/estender apoio, o administrador é perguntado se o apoiador ainda está ativamente apoiando. Se a resposta for "Sim", a `data_expiracao` será incrementada em +1 mês (comportamento aplicado tanto para entradas antecipadas quanto para reativações). Arquivo afetado: `bot/commands/admin/views_supporter.py`.

- **Semântica de apoio retroativo corrigida**: Adições retroativas agora registram `data_inicio` no passado e não aplicam padding automático futuro na `data_expiracao` (ou seja, conta apenas o período efetivamente decorrido). A exceção é quando o administrador indica que o apoiador está ativo — aí a expiração recebe +1 mês conforme acima. Arquivo(s) afetado(s): `bot/commands/admin/views_supporter.py`.

### Notas

- Estas mudanças visam alinhar a atribuição de cargos por tempo com o comportamento esperado: retroativos contam somente o tempo já transcorrido, enquanto antecipados e apoiadores ativos garantem a atribuição imediata do cargo correspondente.
- Recomenda-se rodar os testes de `tests/test_supporter_roles.py` após aplicar alterações envolvendo regras de tempo/expiração.


## [1.12.9.1] - 2026-05-07

### Correções

- Corrigido bug de indentação em `bot/commands/admin.py` no fluxo de criação/estensão de apoiadores manuais, restaurando a atualização de cargos após o commit.

## [1.12.9] - 2026-05-06

### Melhorias

- **Sistema de Modais de Apoiadores**:
  - Refatorado sistema de modais para usar classes específicas por ação
  - Criados `SupporterPauseModal`, `SupporterResumeModal`, `SupporterRemoveModal` para melhor UX
  - Modal de adicionar mantido como `SupporterActionModal` (único que requer campos adicionais)
  - Campos obrigatórios reduzidos por modal - apenas o necessário para cada ação
  - Confirmação visual aprimorada com cores específicas por tipo de ação
  - Mensagens de erro mais específicas por operação

- **Interface de Administração**:
  - Fluxo simplificado para configuração de cargos por tempo
  - **Listagem de Apoiadores**: Implementada paginação para visualizar todos os apoiadores ativos (removido limite de 10)
  - Confirmação imediata de alterações salvas
  - Lista de apoiadores mostra corretamente entradas manuais

### Correções

- **Interface de Administração**:
  - Corrigido limite de 10 apoiadores no botão do dashboard (implementada paginação)
  - `SupportersPaginationView` adicionada para navegação completa de apoiadores
  - Timeout desabilitado em views administrativas para uso prolongado

### Correções

- **Painel de Administração**:
  - Corrigido falha de interação após expiração da sessão (15 minutos)
  - Tratamento de interações expiradas com notificação via DM
  - Views com timeout desabilitado para uso prolongado

- **Configuração de Ambiente**:
  - Corrigido erro de inicialização `ValueError: Missing BASE_URL configuration`
  - `BASE_URL` agora usa `REDIRECT_URL` (produção) ou `NGROK_URL` (desenvolvimento)
  - Mensagem de erro aprimorada para indicar `REDIRECT_URL/NGROK_URL`

- **Gerenciamento Manual de Apoiadores**:
  - Corrigido cálculo de tempo de apoio para apoiadores adicionados manualmente
  - `data_inicio` agora definido no passado baseado nos meses informados
  - Suporte histórico correto para roles baseadas em tempo de apoio

- **Configuração de Cargos por Tempo**:
  - Salvamento automático ao confirmar adição de cargo (removido botão separado 💾)
  - Carregamento de configurações existentes antes de adicionar novas regras
  - Texto de confirmação atualizado para informar salvamento automático


## [1.12.8] - 2026-05-02

### Correções

- **Configuração de Cargos por Tempo**:
  - Corrigido erro `'TimeUnitSelectView' object has no attribute 'bot'` ao selecionar unidade de tempo
  - Passagem correta do objeto `bot` através da cadeia `TimeRoleConfigView` → `TimeRoleModal` → `TimeUnitSelectView`
  - Removida filtragem restritiva de padrões de tempo - agora permite selecionar qualquer cargo do servidor
  - Corrigido cálculo de páginas para evitar exibir "Página 1/0" quando não há cargos

## [1.12.7] - 2026-04-24

### Adicionado

- **Paginação de Cargos na Configuração**:
  - Suporte a servidores com 100+ cargos (paginação com botões ⬅️ / ➡️)
  - Filtro inteligente de padrões de tempo ao configurar cargos (reconhece: números, "dia", "mês", "ano", "semana", etc)
  - Menu reutilizável `PaginatedRoleSelectView` para todas as seleções de cargo

### Correções

- **Suporte de timezone em cálculo de tempo de apoio**:
  - Normaliza `data_inicio` para UTC quando o valor do banco não possui timezone
  - Evita erro `can't subtract offset-naive and offset-aware datetimes` em `SupporterRoleManager`

## [1.12.6] - 2026-04-22

### Adicionado

- **Sistema de Safeguard Avançado para DeepSeek Chat**
  - Detecção de tópicos sensíveis (suicídio, automutilação, abuso, violência) em respostas da IA
  - Reset automático de contexto a cada 10 mensagens para evitar degradação do prompt e jailbreaks acidentais
  - Log crítico com menção direta a dev_id e mod_id quando a API tenta gerar conteúdo inadequado
  - Instrução explícita no prompt para proibir piadas sobre temas traumáticos

### Melhorias

- **Reforço do Sistema de Proteção**:
  - Filtragem dupla: entrada (usuário) + saída (API)
  - Contexto auto-limpante para manter integridade do sistema de instruções
  - Alertas prioritários (vermelho #FF0000) no canal de logs

## [1.12.5] - 2026-04-21

### Melhorias

- **Cobertura de Testes**: Aumentada de ~0% para 21%
  - Atualizado `tests/run_tests.sh` para executar todos os 3 arquivos de testes (`test_doacoes.py`, `test_doar.py`, `test_supporter_roles.py`)
  - Agora 32 testes passam no total (3 + 14 + 15)
  - Geração de relatório de cobertura mais preciso e completo
  - `SupporterRoleManager.py` com 51% de cobertura
  - `doar.py` com 63% de cobertura

## [1.12.4.1] - 2026-04-18

### Adicionado
- **Melhor documentação**

## [1.12.4] - 2026-04-18

### Adicionado

- **Sistema de Gerenciamento de Apoiadores aprimorado**
  - Modal de CRUD trocado por botões
- **Comando de Checagem de integridade de comandos com "/check_commands" ou !check_commands**

### Correções

- **problemas de inicialização do bot e servidor web**
  - Criado `bot/database/__init__.py` com configurações SQLAlchemy completas (síncrono e assíncrono)
  - Adicionadas `SessionLocal` e `get_db` para compatibilidade com FastAPI
  - Corrigido uso incorreto de `discord.select` para `sqlalchemy.select` em `main.py`
  - Corrigido caminho dos templates HTML de `bot/web/templates/` para `frontend/src/pages/`
  - Bot e servidor web agora inicializam sem erros de importação
- **Remoção de Emojis da documentação criado pelo assistente localhost**

---

## [1.12.2] - 2026-04-17

### Adicionado

- **Gerenciamento Manual de Apoiadores**: Sistema completo para admins gerenciarem doações externas
  - Comando `/manage_supporter` para adicionar/pausar/continuar/remover apoiadores
  - Suporte a doações via apoia-se e outras formas não-automáticas
  - Integração com sistema de cargos por tempo
  - Interface modal interativa no dashboard admin

### Documentação

- docs/commands.md: Atualizado com novo comando de administração

### Melhorias

- Sistema de administração expandido com controles manuais

---

## [1.0.0] - 2026-04-16 (inicio do changelog)

### Adicionado

- **Sistema de Doações PIX**: Integração completa com PagBank
  - Geração de QR Code dinâmico
  - Validação de pagamento via webhook
  - Atribuição automática de cargo
  
- **Sistema de Doações Ko-fi**: Assinaturas recorrentes
  - Tokenização de cartões
  - Webhook de renovação automática
  - Sistema de 3 camadas para garantir renovação perfeita
  
- **Sistema de Cargos por Tempo**: Baseado no tempo de apoio
  - Cargo padrão para todos os apoiadores
  - Cargos especiais por tempo (30d, 90d, 180d, 1ano+)
  - Checagem semanal automática
  
- **Sistema RPG por Texto**: Aventuras com DeepSeek AI
  - Criação de personagens com 6 atributos
  - Até 3 personagens por usuário
  - Histórico persistente de interações
  - Funciona em canais públicos ou DMs
  
- **Painel Web Administrativo**: Gerenciamento de dados
  - Autenticação via Discord OAuth2
  - Lista de apoiadores e métricas
  - Visualização de dados em tempo real
  
- **Webhooks**: Notificações e renovações automáticas
  - Ko-fi webhook para renovações
  - PagBank webhook para pagamentos PIX

### Documentação

- README.md: Documentação completa do projeto
- docs/INDEX.md: Índice da documentação
- docs/commands.md: Lista de comandos (atualizado com novos comandos admin)
- docs/config.md: Guia de configuração
- docs/database.md: Estrutura do banco de dados
- docs/servicos.md: Descrição dos serviços
- docs/sistema_renovacao.md: Sistema de renovação automática
- docs/time_based_roles.md: Cargos por tempo
- docs/web.md: Painel web
- docs/webhooks.md: Webhooks

### Melhorias

- Código reorganizado em módulos claros
- Sistema de comandos padronizado
- Modelos de banco de dados otimizados
- Documentação completa e organizada

### Correções

- Nenhuma correção nesta versão inicial

---

## [Unreleased] - Próximas Versões

### Planejado

- [ ] Notificação para usuário quando cargo for reaplicado
- [ ] Logs detalhados de renovação
- [ ] Painel para visualizar histórico de renovações
- [ ] Opção para usuário cancelar assinatura
- [ ] Relatórios de conversão de doações
- [ ] Sistema de exportação de dados

### Em Desenvolvimento

- [ ] Novos comandos de administração
- [ ] Melhorias no sistema de RPG
- [ ] Novos templates para painel web

---

**Nota**: Versões anteriores a 1.0.0 não são documentadas neste arquivo.
