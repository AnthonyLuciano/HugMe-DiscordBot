# 🤗 HugMe - Gerenciador de Apoios via PIX para Discord (Em Desenvolvimento)
**HugMe** é um projeto em desenvolvimento que visa integrar o sistema de doações mensais via **PIX** a um servidor Discord da comunidade autista. Através de um bot, o sistema atribui automaticamente cargos especiais no Discord aos apoiadores com base em seu status de contribuição \:D.

## 📌 Descrição
O HugMe é uma aplicação backend escrita em **Python**, que oferece:
- Integração com comprovantes de doação via **PIX** para gerenciamento de apoios.
- Persistência das informações de apoiadores e doações em um banco **PostgreSQL**.
- Automatização da atribuição de cargos no Discord com base no tempo e nível de apoio.
- Painel web administrativo (futuramente) para gerenciamento e visualização dos dados.

## 🚧 Status do Projeto
**Este projeto está em desenvolvimento ativo.**

### Funcionalidades concluídas:
- [X] Configuração inicial do ambiente Python com virtualenv.
- [X] Conexão com PostgreSQL configurada (após resolver problemas de permissão).
- [X] Instalação e configuração do SQLAlchemy ORM.
- [X] Configuração básica do discord.py (comandos híbridos e eventos).
- [X] Modelo de banco de dados para apoiadores (`Apoiador`).

### Funcionalidades em andamento:
- [ ] Sistema de doações via PIX (envio e validação de comprovantes).
- [ ] Comandos básicos no Discord (`!ajuda`, `!status`, `!iniciar_apoio`).
- [ ] Atribuição automática de cargos baseada no tempo de apoio.
- [ ] Tarefas agendadas para verificação de expiração de apoios.

### Funcionalidades futuras:
- [ ] Painel web administrativo (Flask ou FastAPI + frontend opcional).
- [ ] Logs e alertas de falhas em operações críticas.
- [ ] Configurar deploy contínuo (CI/CD).

## 🛠 Tecnologias Utilizadas
- [Python 3.12+](https://www.python.org/)
- [discord.py](https://github.com/Rapptz/discord.py)
- [SQLAlchemy ORM](https://www.sqlalchemy.org/)
- [PostgreSQL](https://www.postgresql.org/)
- [asyncio](https://docs.python.org/3/library/asyncio.html)
- [Railway.app](https://railway.app/) para banco(futuramente)
- [Render](https://render.com/) hospedagem do bot (futuramente)

## 🧭 Próximos Passos
- [ ] Finalizar comandos básicos no Discord.
- [ ] Implementar sistema de envio e validação de comprovantes PIX.
- [ ] Criar tarefa agendada para atualização de cargos.
- [ ] Desenvolver sistema de logs e alertas.
- [ ] Iniciar desenvolvimento do painel administrativo web.

## 📬 Contato
Para dúvidas, sugestões ou feedbacks, entre em contato:
📧 **[hugmebotdev@gmail.com](mailto:hugmebotdev@gmail.com)**

---
> Projeto pessoal desenvolvido com fins de aprendizado e apoio à comunidade autista. 💙

## 🧱 Arquitetura do Projeto
![Diagrama de arquitetura](docs/casodeuso.png)
