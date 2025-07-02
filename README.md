# 🤗 HugMe - Gerenciador de Apoios via PagBank para Discord (Em Desenvolvimento)

**HugMe** é um projeto em desenvolvimento que visa integrar o sistema de doações mensais via **PagBank** a um servidor Discord da comunidade autista. Através de um bot, o sistema atribui automaticamente cargos especiais no Discord aos apoiadores com base em seu status de contribuição \:D.

## 📌 Descrição

O HugMe é uma aplicação backend escrita em **Python**, que oferece:

* Integração segura com a API do PagBank para gerenciamento de doações.
* Persistência das informações de apoiadores e doações em um banco PostgreSQL.
* Automatização da atribuição de cargos no Discord com base nas assinaturas.
* Painel web administrativo (futuramente) para gerenciamento e visualização dos dados.

## 🚧 Status do Projeto

**Este projeto está em desenvolvimento ativo.**

Funcionalidades previstas:

* [X] Configuração inicial do ambiente Python com virtualenv
* [X] Conexão com PostgreSQL configurada (após resolver problemas de permissão)
* [X] Instalação e configuração do SQLAlchemy ORM
* [ ] Integração segura com a API do PagBank (cliente, token e transações)
* [ ] Persistência de usuários e doações no PostgreSQL
* [ ] Validação periódica do status dos apoiadores
* [X] Configuração básica do discord.py (após resolver importação)
* [ ] Atribuição automática de cargos no Discord
* [ ] Painel web administrativo (Flask ou FastAPI + frontend opcional)
* [ ] Logs e alertas de falhas em operações críticas

## 🛠 Tecnologias Utilizadas

* [Python 3.12+](https://www.python.org/)
* [discord.py](https://github.com/Rapptz/discord.py)
* [httpx](https://www.python-httpx.org/) ou [aiohttp](https://docs.aiohttp.org/)
* [PostgreSQL](https://www.postgresql.org/)
* [SQLAlchemy ORM](https://www.sqlalchemy.org/)
* [asyncio](https://docs.python.org/3/library/asyncio.html)
* [Railway.app](https://railway.app/) para banco e hospedagem (futuramente)

## 🧭 Próximos Passos

* [X] Resolver problemas de importação do módulo bot
* [X] Instalar e configurar psycopg2 para conexão com PostgreSQL
* [X] Corrigir permissões do usuário PostgreSQL para criação de tabelas
* [ ] Finalizar comandos básicos no Discord
* [ ] Implementar integração com PagBank
* [ ] Armazenar e consultar doações com SQLAlchemy
* [ ] Tarefa agendada para atualizar cargos de acordo com o tempo de apoio
* [ ] Criar sistema de logs e alertas para falhas de sincronização
* [ ] Desenvolver painel administrativo web (opcional)
* [ ] Configurar deploy contínuo (CI/CD)

## 📬 Contato

Para dúvidas, sugestões ou feedbacks, entre em contato:

📧 **[hugmebotdev@gmail.com](mailto:hugmebotdev@gmail.com)**

---

> Projeto pessoal desenvolvido com fins de aprendizado e apoio à comunidade autista. 💙

## 🧱 Arquitetura do Projeto

![Diagrama de arquitetura](docs/casodeuso.png)
