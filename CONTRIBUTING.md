# 🤝 Guia de Contribuição

Agradecemos seu interesse em contribuir para o HugMe! Este documento explica como você pode ajudar a melhorar o bot.

## 📋 Índice

- [Como contribuir](#-como-contribuir)
- [Tipos de contribuições](#-tipos-de-contribuições)
- [Primeiros passos](#-primeiros-passos)
- [Processo de desenvolvimento](#-processo-de-desenvolvimento)
- [Padrões de código](#-padrões-de-código)
- [Envio de pull requests](#-envio-de-pull-requests)
- [Revisão e aprovação](#-revisão-e-aprovação)

---

## 💡 Como contribuir

Existem várias maneiras de contribuir com o HugMe:

1. **Código**: Adicionar novas funcionalidades, corrigir bugs, melhorar performance
2. **Documentação**: Melhorar guias, tutoriais e exemplos
3. **Testes**: Escrever novos testes ou melhorar os existentes
4. **Design**: Melhorar a interface do painel web ou UX do bot
5. **Traduções**: Traduzir documentação para outros idiomas
6. **Feedback**: Relatar bugs, sugerir melhorias, dar feedback

---

## 🎯 Tipos de contribuições

### Novas Funcionalidades
- Adicionar novos comandos ao bot
- Criar novos sistemas (ex: novos tipos de doação)
- Melhorar sistemas existentes (ex: melhorar o RPG)

### Correções de Bugs
- Relatar bugs (antes de corrigir, deixe um issue aberto)
- Corrigir bugs reportados por outros usuários
- Melhorar tratamento de erros

### Melhorias de Código
- Refatorar código para melhor legibilidade
- Melhorar performance
- Adicionar comentários e documentação
- Melhorar nomes de variáveis e funções

### Melhorias de Testes
- Aumentar cobertura de testes
- Adicionar testes para novas funcionalidades
- Melhorar testes existentes

---

## 🚀 Primeiros passos

### 1. Fork o repositório
1. Acesse [https://github.com/AnthonyLuciano/HugMe-DiscordBot](https://github.com/AnthonyLuciano/HugMe-DiscordBot)
2. Clique no botão "Fork" no topo direito
3. Clone seu fork localmente:
   ```bash
   git clone https://github.com/seu-usuario/HugMe-DiscordBot.git
   cd HugMe-DiscordBot
   ```

### 2. Crie uma branch
Crie uma branch para sua contribuição:
```bash
git checkout -b feature/nome-da-feature
# ou
git checkout -b fix/nome-do-bug
```

### 3. Configure o ambiente
```bash
# Crie e ative o ambiente virtual
python -m venv .venv
source .venv/bin/activate

# Instale as dependências
pip install -r requirements.txt
pip install -r requirements-test.txt

# Configure o arquivo .env (copie de .env.example)
cp .env.example .env
# Edite .env com suas configurações
```

### 4. Faça suas alterações
- Escreva código limpo e bem documentado
- Adicione testes para novas funcionalidades
- Atualize a documentação se necessário

### 5. Teste suas alterações
```bash
# Execute os testes
pytest

# Execute com cobertura
pytest --cov=bot --cov-report=html
```

---

## 🛠️ Processo de desenvolvimento

### Antes de começar
1. **Verifique se já existe uma issue** para o que você quer fazer
2. **Crie uma issue** se não existir (explique sua proposta)
3. **Aguarde feedback** da equipe antes de começar a codar

### Durante o desenvolvimento
1. **Faça commits pequenos e frequentes**
2. **Escreva mensagens de commit claras**
3. **Teste a cada etapa**
4. **Mantenha o código limpo**

### Exemplo de fluxo de trabalho:
```bash
# 1. Crie uma branch
git checkout -b feature/nova-funcionalidade

# 2. Faça suas alterações
# ... código ...

# 3. Adicione os arquivos
git add nome-do-arquivo.py

# 4. Faça commit
git commit -m "Adiciona nova funcionalidade X"

# 5. Repita até estar pronto

# 6. Atualize seu fork
git push origin feature/nova-funcionalidade
```

---

## 📝 Padrões de código

### Python
- Siga o [PEP 8](https://peps.python.org/pep-0008/) para estilo de código
- Use type hints quando possível
- Escreva docstrings para funções e classes
- Mantenha funções pequenas e focadas

### Exemplo de código bom:
```python
async def processar_doacao(usuario: str, valor: int, metodo: str) -> bool:
    """
    Processa uma doação e atribui cargo ao usuário.
    
    Args:
        usuario: ID do usuário Discord
        valor: Valor da doação em centavos
        metodo: Método de pagamento (pix ou kofi)
        
    Returns:
        bool: True se sucesso, False caso contrário
    """
    try:
        # Processa a doação
        await banco.salvar_doacao(usuario, valor, metodo)
        await bot.atribuir_cargo(usuario)
        return True
    except Exception as e:
        logger.error(f"Erro ao processar doação: {e}")
        return False
```

### Comentários e documentação
- Use comentários para explicar **por que**, não **o que**
- Escreva docstrings em português para funções internas
- Use docstrings em português para funções públicas

---

## 📤 Envio de pull requests

### O que incluir
1. **Descrição clara** do que foi mudado
2. **Motivação** para a mudança
3. **Como testar** a nova funcionalidade
4. **Issues relacionadas** (se aplicável)

### Template de pull request:
```
## O que foi mudado?
[Descreva suas mudanças]

## Por que isso é necessário?
[Explique o problema que resolve]

## Como testar?
[Instruções para testar]

## Issues relacionadas?
[Cita issues com #numero]
```

### Antes de enviar
- [ ] Testes passando
- [ ] Documentação atualizada
- [ ] Código limpo e bem formatado
- [ ] Commit messages claras
- [ ] Branch atualizada com main

---

## 👀 Revisão e aprovação

### O que esperar
1. **Revisão rápida** (1-2 dias): Feedback inicial
2. **Revisão técnica** (3-5 dias): Análise de código
3. **Aprovação**: Merge para main

### Possíveis feedbacks
- **Sugestões de melhoria**: Código pode ser melhorado
- **Pedidos de testes**: Adicionar mais cobertura
- **Pedidos de documentação**: Adicionar docstrings
- **Pedidos de alterações**: Mudanças necessárias

### Se seu PR for aprovado
1. O PR será mergeado para main
2. Será incluído na próxima versão
3. Você será listado como contribuidor

---

## 🐛 Relatando bugs

### O que incluir
1. **Descrição clara** do problema
2. **Passos para reproduzir**
3. **Comportamento esperado**
4. **Comportamento real**
5. **Ambiente** (versão, sistema operacional)

### Exemplo:
```
## Descrição
O comando /doar não está funcionando.

## Passos para reproduzir
1. Digite /doar
2. Escolha PIX
3. Clique em "já paguei"
4. O bot não responde

## Comportamento esperado
O bot deveria processar o pagamento.

## Comportamento real
O bot não responde e não dá cargo.

## Ambiente
- Versão: 1.0.0
- Sistema: Ubuntu 22.04
- Python: 3.10
```

---

## 💬 Perguntas?

Se tiver dúvidas:
1. Abra uma issue com a tag "pergunta"
2. Entre no servidor da comunidade
3. Envie um email (se disponível)

---

## 🙏 Agradecimentos

Agradecemos todas as contribuições! Cada ajuda conta para tornar o HugMe melhor.