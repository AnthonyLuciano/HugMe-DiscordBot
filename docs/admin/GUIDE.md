# Guia de Uso - Comandos Admin

Este guia prático mostra como usar cada recurso do painel admin.

## Sumário Rápido

| Tarefa | Comando | Passos |
|--------|---------|--------|
| Visualizar painel | `/dashboard` | 1 |
| Adicionar apoiador | `/manage_supporter` | 5 |
| Pausar apoio | `/manage_supporter` | 3 |
| Retomar apoio | `/manage_supporter` | 3 |
| Remover apoiador | `/manage_supporter` | 3 |
| Configurar PIX | `/pix_config` | 2 |
| Definir cargo padrão | `/set_default_supporter_role` | 3 |
| Configurar cargos por tempo | `/configure_time_roles` | 5 |
| Listar servidores | `/servers` | 1 |

## Comandos Detalhados

### 1. Dashboard - `/dashboard`

**Objetivo**: Ver estatísticas e acessar todas as funções

**Como usar**:
1. Digite `/dashboard` no chat
2. Clique nos botões:
   - 🔄 **Atualizar** - Recarrega estatísticas
   - 👤 **Gerenciar Apoiadores** - Abre interface de gerenciamento
   - 📋 **Apoiadores** - Lista todos os apoiadores ativos (com paginação)
   - 🏠 **Servidores** - Mostra todos os servidores do bot
   - 💳 **PIX Config** - Gerencia QR Code e dados
   - ⭐ **Ver Cargos Configurados** - Visualiza configuração de cargos
   - ✏️ **PIX Modal** - Edita configuração PIX

**Exemplo**:
```
Você vê:
📊 Painel de Controle - HugMe Bot
👥 Apoiadores Ativos: 42
🆕 Doações Recentes (30d): 12
💰 Receita Total: R$ 450.50
🏠 Servidores: 8
```

---

### 2. Gerenciar Apoiador - `/manage_supporter`

Acesso rápido a todas as ações de apoiador em um único lugar.

#### 2.1. Adicionar Apoiador

**Quando usar**: Novo apoiador ou extensão de apoio manual

**Passos**:
1. Digite `/manage_supporter`
2. Clique em **➕ Adicionar**
3. Preencha o modal:
   - **ID do Usuário ou @menção**: `123456789` ou `@usuario`
   - **Duração**: `3` (número)
   - **Tipo de Apoio** (opcional): `manual`, `pix`, `apoia-se` (padrão: `manual`)
   - **Valor** (opcional): `12.50` ou deixe em branco
4. Clique em **Enviar**
5. Escolha tipo de período:
   - **⏮️ Retroativo**: O tempo contar como se o apoio já estivesse ativo desde dias/meses/anos atrás
   - **⏭️ Antecipado**: Estender o apoio para o futuro (próxima renovação)
6. Escolha unidade: **📅 Dias**, **📆 Meses**, ou **📈 Anos**
7. Clique em **✅ CONFIRMAR** para finalizar

**Exemplo de Retroativo** (6 meses):
- Hoje: 20/06/2026
- Data início: 20/12/2025 (6 meses no passado)
- Expira: 20/07/2026
- Cargo é atribuído imediatamente

**Exemplo de Antecipado** (3 meses):
- Hoje: 20/06/2026
- Data início: hoje
- Expira: 20/09/2026 (3 meses no futuro)

#### 2.2. Pausar Apoiador

**Quando usar**: Apoiador solicitou pausa, quer testar sem cargos, etc.

**Passos**:
1. Digite `/manage_supporter`
2. Clique em **⏸️ Pausar**
3. Insira ID/menção do usuário
4. Clique em **✅ CONFIRMAR**

**Resultado**: Apoio fica inativo, cargos são removidos

#### 2.3. Retomar Apoio

**Quando usar**: Apoiador voltou, pausa terminou

**Passos**:
1. Digite `/manage_supporter`
2. Clique em **▶️ Continuar**
3. Insira ID/menção do usuário
4. Clique em **✅ CONFIRMAR**

**Resultado**: Apoio fica ativo novamente, cargos restaurados

#### 2.4. Remover Apoiador

**Quando usar**: Fim de parceria, dados errados, etc.

**Passos**:
1. Digite `/manage_supporter`
2. Clique em **🗑️ Remover**
3. Insira ID/menção do usuário
4. Leia o aviso: **⚠️ Esta ação não pode ser desfeita!**
5. Clique em **✅ CONFIRMAR**

**Resultado**: Registro completamente deletado do BD, cargos removidos

---

### 3. PIX - `/pix_config`

**Objetivo**: Gerenciar QR Code e dados para cobranças

**Passos para Configurar PIX**:
1. Digite `/pix_config`
2. Clique em **✏️ Editar**
3. Preencha o modal:
   - **URL do QR Code**: `https://exemplo.com/qrcode.png` (obrigatório)
   - **Chave PIX** (opcional): Email, CPF, Telefone ou Chave Aleatória
   - **Nome do Titular** (padrão: "HugMe Bot"): Seu nome ou empresa
   - **Cidade** (padrão: "São Paulo"): Cidade do titular
4. Clique em **Enviar**
5. Clique em **✅ CONFIRMAR**

**Validações**:
- URL deve começar com `http://` ou `https://`
- Nenhum campo é deletado, todos são atualizados

**Limpar Configuração**:
1. Digite `/pix_config`
2. Clique em **❌ Limpar Config**
3. Clique em **✅ CONFIRMAR**

---

### 4. Cargos - Sistema de Roles

#### 4.1. Definir Cargo Padrão

**Objetivo**: Todo apoiador recebe automaticamente este cargo

**Passos**:
1. Digite `/set_default_supporter_role`
2. Navegue pelos cargos disponíveis (páginas de 25 cargos)
3. Clique em um cargo
4. Clique em **✅ CONFIRMAR**

**Resultado**: Novo apoiador recebe este cargo ao ser criado

**Exemplo**:
- Defini `@Apoiador` como cargo padrão
- Quando adiciono `@usuario`, ele recebe `@Apoiador` automaticamente

#### 4.2. Configurar Cargos por Tempo

**Objetivo**: Cargos automáticos baseados em quanto tempo apoiou (ex: Bronze, Prata, Ouro)

**Passos**:
1. Digite `/configure_time_roles`
2. Clique em **➕ Adicionar Cargo**
3. Insira **Valor mínimo de apoio**: `3` (número)
4. Escolha unidade: **📅 Dias**, **📆 Meses**, ou **📈 Anos**
5. Selecione o cargo (com paginação)
6. Clique em **✅ CONFIRMAR**

**Exemplo de Configuração**:
```
1 mês+ → @Apoiador Bronze
3 meses+ → @Apoiador Prata
6 meses+ → @Apoiador Ouro
1 ano+ → @Apoiador Platina
```

Quando um apoiador atinge o tempo, o cargo é atribuído automaticamente!

**Para Ver Cargos Configurados**:
1. Digite `/configure_time_roles`
2. Clique em **📋 Ver Configurados**

---

### 5. Listar Servidores - `/servers`

**Objetivo**: Ver todos os servidores onde o bot está presente

**Como usar**:
1. Digite `/servers`
2. Veja a lista com nome, ID e número de membros

**Exemplo**:
```
🏠 Servidores do Bot

**HugMe Community** (ID: 123456789) - 1250 membros
**Dev Server** (ID: 987654321) - 45 membros
**Tests** (ID: 111222333) - 12 membros

Total: 3 servidores
```

---

## Troubleshooting

### "❌ Apenas admins podem usar esse comando!"

**Problema**: Você não é reconhecido como admin

**Solução**: 
- Verificar variáveis de ambiente:
  - `DEV_ID` - ID do desenvolvedor principal
  - `TRUSTED_MOD_ID` - ID do moderador confiável
- Pedir ao admin para adicionar seu ID

### "❌ Este comando só funciona em um servidor"

**Problema**: Usou comando em DM ou contexto inválido

**Solução**: Use o comando em um servidor (canal de texto)

### "❌ URL deve começar com http:// ou https://"

**Problema**: URL do PIX inválida

**Solução**: Copie novamente a URL, certificando-se que começa com `https://`

### "Cargo não é atribuído"

**Problema**: Cargo foi adicionado mas member não o recebeu

**Causas possíveis**:
1. Bot não tem permissão para atribuir cargo
2. Cargo é superior ao do bot (Discord bloqueia)
3. Bot não tinha role_manager configurado

**Solução**: Verifique permissões do bot no servidor e posição dos cargos

### Modal é cortado ou truncado

**Problema**: Campos de texto não cabem

**Solução**: Use valores mais curtos ou em passo anterior, divida em dois modais

---

## Dicas Práticas

✅ **Sempre confirme as ações** - Dupla confirmação protege contra erros

✅ **Use retroativo para backfill** - Se apoiador estava ativo antes, marque como retroativo

✅ **Categorize com cargos por tempo** - Bronze/Prata/Ouro motiva renovações

✅ **Revise configuração de PIX regularmente** - QR Codes expiram

✅ **Mantenha lista atualizada** - Remova apoiadores inativos para não pagar taxa

✅ **Teste em dev server primeiro** - Não teste cargos em servidor principal

---

## Atalhos Úteis

| Ação Rápida | Comando |
|-------------|---------|
| Dashboard completo | `/dashboard` |
| Tudo de apoiador em um lugar | `/manage_supporter` |
| Só configurar PIX | `/pix_config` → ✏️ Editar |
| Só cargos padrão | `/set_default_supporter_role` |
| Só cargos por tempo | `/configure_time_roles` |
| Listar em outro servidor | `/servers` |

---

## Contato & Suporte

Se encontrar bugs ou tiver dúvidas:
1. Abra uma issue no GitHub
2. Verifique o CHANGELOG.md para versão atual
3. Consulte README.md para instruções de instalação

Bom uso! 🚀

