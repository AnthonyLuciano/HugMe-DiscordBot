# Changelog

Todas as mudanças importantes no HugMe serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere à [Semantic Versioning](https://semver.org/lang/pt-BR/).

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
