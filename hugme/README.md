# Discord Donation Bot

Este projeto é um bot do Discord desenvolvido em Python, destinado a uma comunidade de 1400 pessoas autistas. O objetivo do bot é permitir que os membros façam doações mensais através da API do PagBank, e com isso, o bot atribui cargos especiais automaticamente no Discord com base no status de apoio.

## Estrutura do Projeto

A estrutura do projeto é a seguinte:

```
discord-donation-bot
├── bot
│   ├── __init__.py
│   ├── main.py
│   ├── commands
│   │   └── __init__.py
│   ├── pagbank
│   │   └── __init__.py
│   ├── db
│   │   ├── __init__.py
│   │   └── models.py
│   └── utils
│       └── __init__.py
├── requirements.txt
├── README.md
└── .env.example
```

## Tecnologias Utilizadas

- **Python**: Linguagem principal do projeto.
- **discord.py**: Biblioteca para integração com a API do Discord.
- **httpx** ou **aiohttp**: Bibliotecas para realizar requisições HTTP à API do PagBank.
- **PostgreSQL**: Banco de dados utilizado para armazenar informações dos apoiadores.
- **SQLAlchemy**: ORM para facilitar a interação com o banco de dados.
- **asyncio**: Biblioteca para execução assíncrona, permitindo que o bot responda a eventos de forma eficiente.

## Instalação

1. **Clone o repositório**:
   ```
   git clone https://github.com/seu_usuario/discord-donation-bot.git
   cd discord-donation-bot
   ```

2. **Crie um ambiente virtual** (opcional, mas recomendado):
   ```
   python -m venv venv
   source venv/bin/activate  # Para Linux/Mac
   venv\Scripts\activate  # Para Windows
   ```

3. **Instale as dependências**:
   ```
   pip install -r requirements.txt
   ```

4. **Configure as variáveis de ambiente**:
   Renomeie o arquivo `.env.example` para `.env` e preencha com suas credenciais da API do PagBank e informações do banco de dados.

## Uso

Para iniciar o bot, execute o seguinte comando:

```
python bot/main.py
```

## Contribuição

Contribuições são bem-vindas! Sinta-se à vontade para abrir issues ou pull requests.

## Licença

Este projeto está licenciado sob a MIT License - veja o arquivo [LICENSE](LICENSE) para mais detalhes.