# 📝 Changelog

Todas as mudanças importantes no HugMe serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere à [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [1.12.3] - 2026-04-17

### 🎉 Adicionado
- **Sistema de Safeguard Aprimorado**: Detecção expandida de crises emocionais
  - Adicionadas variações de "tortura" na lista de palavras-chave de crise
  - Melhor proteção contra conteúdo sensível no chat DeepSeek

### 🐛 Correções
- **Erro Crítico de Importação**: Resolvidos problemas de inicialização do bot e servidor web
  - Criado `bot/database/__init__.py` com configurações SQLAlchemy completas (síncrono e assíncrono)
  - Adicionadas `SessionLocal` e `get_db` para compatibilidade com FastAPI
  - Corrigido uso incorreto de `discord.select` para `sqlalchemy.select` em `main.py`
  - Bot e servidor web agora inicializam sem erros de importação

---

## [1.12.2] - 2026-04-17

### 🎉 Adicionado
- **Gerenciamento Manual de Apoiadores**: Sistema completo para admins gerenciarem doações externas
  - Comando `/manage_supporter` para adicionar/pausar/continuar/remover apoiadores
  - Suporte a doações via apoia-se e outras formas não-automáticas
  - Integração com sistema de cargos por tempo
  - Interface modal interativa no dashboard admin

### 📚 Documentação
- docs/commands.md: Atualizado com novo comando de administração

### 🔧 Melhorias
- Sistema de administração expandido com controles manuais

---

## [1.0.0] - 2026-04-16 (inicio do changelog)

### 🎉 Adicionado
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

### 📚 Documentação
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

### 🔧 Melhorias
- Código reorganizado em módulos claros
- Sistema de comandos padronizado
- Modelos de banco de dados otimizados
- Documentação completa e organizada

### 🐛 Correções
- Nenhuma correção nesta versão inicial

---

## [Unreleased] - Próximas Versões

### 🎯 Planejado
- [ ] Notificação para usuário quando cargo for reaplicado
- [ ] Logs detalhados de renovação
- [ ] Painel para visualizar histórico de renovações
- [ ] Opção para usuário cancelar assinatura
- [ ] Relatórios de conversão de doações
- [ ] Sistema de exportação de dados

### 🚧 Em Desenvolvimento
- [ ] Novos comandos de administração
- [ ] Melhorias no sistema de RPG
- [ ] Novos templates para painel web

---

**Nota**: Versões anteriores a 1.0.0 não são documentadas neste arquivo.
