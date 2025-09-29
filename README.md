# 🤗 HugMe - Gerenciador de Apoios via PIX e Cartão para Discord (Em Desenvolvimento)

**HugMe** é um projeto em desenvolvimento que visa integrar o sistema de doações mensais via **PIX** e **Cartão de crédito/débito** a um servidor Discord da comunidade autista. Através de um bot, o sistema atribui automaticamente cargos especiais no Discord aos apoiadores com base em seu status de contribuição \:D.

## 📌 Descrição
O HugMe é uma aplicação backend escrita em **Python**, que oferece:
- Integração com comprovantes de doação via **PIX** e **cartão de crédito** para gerenciamento de apoios
- Persistência das informações de apoiadores e doações em um banco **PostgreSQL**
- Automatização da atribuição de cargos no Discord com base no tempo e nível de apoio
- Painel web administrativo (futuramente) para gerenciamento e visualização dos dados
- Suporte a pagamentos únicos e assinaturas recorrentes

## 🚧 Status do Projeto
**Este projeto está em Desenvolvimento Ativo**

#### PIX via Pagbank: Integração [██████████] **100%**

#### Cartão de Crédito: Integração [██████████] **100%**

#### Funcionalidades prontas antigas:
![Funcionalidades(old)](https://github.com/AnthonyLuciano/HugMe-DiscordBot/blob/test/oldREADME.md)

### Funcionalidades Gerais em andamento:

- [ ] Implementar agendamentos para:
  - [x] Verificação de expiração
  - [ ] Atualização de cargos automaticamente

## 🎮 Sistema de RPG por Texto

### Funcionalidades Concluídas:
- [x] **Sistema de Personagens**: Criação com 6 atributos (1-20) via `/rpg_personagem`
- [x] **Múltiplos Personagens**: Até 3 personagens por usuário com gerenciamento completo
- [x] **Histórico Persistente**: Sessões salvas em banco MariaDB com SQLAlchemy async
- [x] **Comandos Híbridos**: `/rpg`, `/rpg_personagem`, `/rpg_status`, etc (slash e prefixo)
- [x] **Integração DeepSeek**: API para geração de aventuras com contexto histórico
- [x] **Sistema de Tutorial**: Guia interativo para novos jogadores
- [x] **Status Embed**: Visualização elegante do progresso da aventura
- [x] **Gestão de Sessões**: Histórico mantém últimas 8 interações por desempenho
- [x] **Sistema de Resumo**: Resumos automáticos para histórias longas
- [x] **Suporte a DMs**: Jogável tanto em canal designado quanto por mensagem privada
- [x] **Comandos de Gerenciamento**:
  - `/rpg_personagens` - Lista todos os personagens
  - `/rpg_usar_personagem [ID]` - Seleciona personagem ativo
  - `/rpg_deletar_personagem [ID]` - Remove personagem
  - `/rpg_ajuda` - Tutorial manual

### Funcionalidades em Andamento:
🦗🦗🦗🦗 nao tem nada mais por enquanto...

### Tecnologias Utilizadas:
- **Database**: MariaDB com SQLAlchemy ORM async
- **API**: DeepSeek Chat para geração de conteúdo
- **Framework**: discord.py com comandos híbridos
- **Armazenamento**: JSON em campos SQL para flexibilidade

### Arquitetura:
- **Modelos**: `RPGSession` (sessões), `RPGCharacter` (personagens)
- **Engine Async**: Operações não-bloqueantes para melhor performance
- **Cache Inteligente**: Histórico mantido em memória com persistência automática
- **Tratamento de Erros**: Sistema robusto com fallbacks amigáveis

### Exemplo de Uso:
1. `/rpg_personagem João Mago Humano 3 5 4 10 10 5`
2. `/rpg iniciar` - Começa uma aventura épica
3. `/rpg Atacar o dragão com magia` - Interage com o mundo
4. `/rpg_status` - Verifica progresso e atributos

## 🧭 Próximos Passos

- [ ] Adicionar painel com histórico e logs
- [ ] Documentar API para integrações externas

## 🏁 Etapa Final
- [x] Testes completos no ambiente real
- [x] Migrar o bot para ambiente de produção

## 🛠 Tecnologias Utilizadas
- [Python 3.12+](https://www.python.org/)
- [discord.py](https://github.com/Rapptz/discord.py)
- [SQLAlchemy ORM](https://www.sqlalchemy.org/)
- [PostgreSQL](https://www.postgresql.org/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [httpx](https://www.python-httpx.org/)
- [asyncio](https://docs.python.org/3/library/asyncio.html)
- [BlazeHosting](https://blazehosting.com.br/bots) *(hospedagem do bot e painel, bem recomendado)*

## 📬 Contato
📧 **[hugmebotdev@gmail.com](mailto:hugmebotdev@gmail.com)**

---
> Projeto pessoal desenvolvido com fins de aprendizado e apoio à comunidade autista. 💙
---
## 🧱 Arquitetura do Projeto
![Diagrama de Caso de Uso](https://www.plantuml.com/plantuml/dsvg/TPFDRXCn4CVlVefHJo2K0qq_Q0-e8UKZGaYXLH7NgJr9hEnwLcDlE23UXOe3Jy0JvCKOiywo2ULc__tpU3x-lee99RLrPIfQ94WCufUh1CuBsUGvcBZseK716ceER5V2DK6Iben1crZWBhRR1_5SjXDN--1Z4dGiHJkwLO5gXFSyMlWZmAYhDtvtEfdFu9gekILQvyD-OqpE0iEo8dZ52RuQW3QInKXmD0lUUXHmZDkVsn-SRyBTzFcGUHqjLokIIvZFFWEtVGAPF1wIRqbGuECDJDbHfWiq7a9pOKinAjZW4ciAYVSYdWpXJoH-uUs_6PuUl4jXKCSlYWKx6s9J3XkI_BBb6cOJUFAkNNuWRShJWfyFyKaIVzzwfL6M707Rn3KcpIOdJUNAYxtQq0Ug0Fln9RzX-4Bt1RumtupPpHf6evUvruV2yQ5mRbGiwp7y6SD0EO7BhdychxEMRQ6YEiBevIprPYXo9WRNjJ4BBtNNODEpvNK5RYWs71CQi-VCGfm-gfuzgbwOFatjdOQ-BdC5Mv9mgCHuGCnxcsoA6nmRFUeAyz6oE2rAoJAnRc3614vKlY8lkiy2iBFVN_T54D8OeckAIcmyvWWf9_Ki3s_5lEwcltr8thAXu207FtoY_t80EI57O3lBbH8R5DIps3OiYM3xFHkn3TwXe_y5BHOhdt-OXiOlrjJp71eSvqvJp2Labm0LP_InhtJLrjLl)
> por algum motivo o diagrama não quer atualizar, ignore

![Fluxo Geral](https://www.plantuml.com/plantuml/dsvg/ZLJFRZir4BxlKmova1n2xr5LDMrQgQ8L9LKBDpIn9wdfshFOtb1ucue3we4ZJx0lXhtnxhB4vTT3bFNucp_VvvavTnwjhtLPLE5V2LMXyV3ewkRDAXuPBzYFpsW4hr2o6vadFz06bb8hCm5q44xZw-Nz3QoK4snb2qZVmNoC-vRdMnLHuUjQPI4hekg1w2MY-aDHV0tNPVtA80bMZCsVpHyCUuLmV_DZqR63-LaajO0JoMYBy1ajtUq2xjXvYo3OR9NLASXqTNUP35wnULBqw-muOWS1cP9tqGVH5h2cdMepX9znANuiiCNcIlb-7I9B0dA-UGiwyCT4M-bW6kH_PdwP5Kd0M4EmBI1T1BynmI9SV5Xen-OGlOT6nWzSAg4y0dghDhLgSMrqjBkU_l3O2rWUW0S0OEqvIYfGa_6Kq-iEhS045wmvfMh-acCTWlXxiadGY8IRPURHD-pXD2Hpk2DzbXBsBRI0AnDrh2phoXUT6UQT_veyMuDWoLNiF6OefX0T0a8oeTYWaGnrgYT7z9Pt815KqC6sBCRydiYghHBOItmP9Samt2UWFMWsTHwtMs1J_ZRBLTl5XOgiLiurVvC3Z9DS332O7_Lu2paUdqkh48B8gSZzlwlEJ4pPPaQBFTActiaer9VgILSCXi6HtIl9zekTDaZPBwfH8oy5EOTmabXzJgPF2pIcyTt6D-yQTFFkROZeW00hLk7IaZiuTFEw9YF9gjzJj6-UlIx_q_KwDfQ3Y-RDAS4kqn3YcSHBPhrCegbTAh4xbA6l9aN67N-k9NwydKXlIBRp9b8jumAZ7BiwTNI_owRj4ymowHpvdtwn8e9EQrkUvHHS-XhBgChZ-XPa7pLJP7gDOMemkHuFsDLhfReobt4ljSiM_xSHuxkn0ugkyGgcmdAWDO27nhXLpYD86j2vFbkJvdtQd-uOcbN1-S3A7SP86VHgpyKv6LdhyXy0)
