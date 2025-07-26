# 🤗 HugMe - Gerenciador de Apoios via PIX para Discord (Em Desenvolvimento)

**HugMe** é um projeto em desenvolvimento que visa integrar o sistema de doações mensais via **PIX** a um servidor Discord da comunidade autista. Através de um bot, o sistema atribui automaticamente cargos especiais no Discord aos apoiadores com base em seu status de contribuição \:D.

## 📌 Descrição
O HugMe é uma aplicação backend escrita em **Python**, que oferece:
- Integração com comprovantes de doação via **PIX** (PagBank) para gerenciamento de apoios.
- Persistência das informações de apoiadores e doações em um banco **PostgreSQL**.
- Automatização da atribuição de cargos no Discord com base no tempo e nível de apoio.
- Painel web administrativo (futuramente) para gerenciamento e visualização dos dados.

## 🚧 Status do Projeto
**Este projeto está em desenvolvimento ativo.**

### Funcionalidades concluídas:
- [x] Configuração inicial do ambiente Python com virtualenv.
- [x] Conexão com PostgreSQL configurada.
- [x] Configuração do SQLAlchemy ORM.
- [x] Sistema básico do discord.py (comandos/eventos).
- [x] Modelo de banco de dados para apoiadores.
- [x] Comando `/doar` com interface interativa via botão e modal.
- [x] Envio de pedidos Pix com QR Code via API PagBank.
- Integração com PIX: [███████░░░] **70%**
  - [x] Envio do pedido via API
  - [x] Geração do QR Code e chave Pix no Discord
  - [ ] Validação de pagamento via webhook
  - [ ] Atribuição automática de cargo

### Funcionalidades em andamento:
- [ ] Webhook de notificação de pagamento
- [ ] Tarefas agendadas para expiração de apoios
- [ ] Refinamento do painel administrativo

### Funcionalidades futuras:
- [ ] Sistema avançado de logs/alertas
- [ ] Configuração de CI/CD
- [ ] Dashboard de métricas para apoiadores
- [ ] Sistema de notificações via webhook
- [ ] Integração com Cartão de Crédito

## 🧭 Próximos Passos
- [ ] Finalizar webhook de confirmação de pagamento Pix
- [ ] Implementar agendamentos para:
  - [ ] Verificação de expiração
  - [ ] Atualização de cargos automaticamente
- [ ] Adicionar painel com histórico e logs
- [ ] Documentar API para integrações externas

## 🏁 Etapa Final
- [ ] Homologar integração com o PagBank (testes completos no ambiente real)
- [ ] Migrar o bot para ambiente de produção com chave oficial


## 🛠 Tecnologias Utilizadas
- [Python 3.12+](https://www.python.org/)
- [discord.py](https://github.com/Rapptz/discord.py)
- [SQLAlchemy ORM](https://www.sqlalchemy.org/)
- [PostgreSQL](https://www.postgresql.org/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [httpx](https://www.python-httpx.org/)
- [asyncio](https://docs.python.org/3/library/asyncio.html)
- [Railway](https://railway.app/) *(planejado para banco de dados)*
- [Render](https://render.com/) *(planejado para hospedagem do bot)*
- [PagSeguro / PagBank](https://pagseguro.uol.com.br/) *(integração em andamento)*

## 📬 Contato
📧 **[hugmebotdev@gmail.com](mailto:hugmebotdev@gmail.com)**

---
> Projeto pessoal desenvolvido com fins de aprendizado e apoio à comunidade autista. 💙

## 🧱 Arquitetura do Projeto
![Diagrama de arquitetura](docs/casodeuso.png)

### Diagramas de Fluxo
![pix](docs/fluxopix.png)
