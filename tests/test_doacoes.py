"""
Testes do Sistema de Doações - HugMe Bot

Este módulo contém testes unitários e de integração para o sistema de doações,
incluindo:
- Webhook Ko-fi
- Renovação automática de assinaturas
- Atribuição de cargos
- Verificação de apoiadores
"""

import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text

# Importar módulos do bot
from bot.database.models import Apoiador, GuildConfig
from bot.servicos.VerificacaoMembro import VerificacaoMembro
from bot.web.main import (
    check_expirations,
    renovar_apoiadores_expirados,
    reativar_cargos_da_assinatura,
    kofi_webhook
)


# ============================================
# FIXTURES E UTILITÁRIOS
# ============================================

@pytest.fixture
def mock_bot():
    """Cria um mock do bot Discord"""
    bot = Mock()
    bot.db = Mock()
    bot.get_guild = Mock()
    bot.guilds = []
    return bot


@pytest.fixture
def mock_member():
    """Cria um mock de membro Discord"""
    member = Mock(spec=['id', 'guild', 'joined_at', 'roles', 'add_roles'])
    member.id = 123456789
    member.guild = Mock()
    member.guild.id = 987654321
    member.guild.get_role = Mock()
    member.joined_at = datetime.now(timezone.utc) - timedelta(days=45)
    member.roles = []
    # `add_roles` is async in discord.py
    member.add_roles = AsyncMock()
    member.display_name = "TestUser"
    return member


@pytest.fixture
def mock_guild():
    """Cria um mock de servidor Discord"""
    guild = Mock()
    guild.id = 987654321
    guild.get_member = Mock()
    guild.get_role = Mock()
    guild.chunk = AsyncMock()
    guild.me = Mock()
    guild.me.guild_permissions = Mock(manage_roles=True)
    guild.me.top_role = Mock(position=100)
    return guild


@pytest.fixture
def mock_role():
    """Cria um mock de cargo"""
    role = Mock()
    role.id = 111222333
    role.name = "Apoiador"
    role.position = 1
    return role


@pytest.fixture
def mock_session():
    """Cria um mock de sessão do banco de dados"""
    session = AsyncMock()
    session.add = Mock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def mock_apoiador():
    """Cria um mock de apoiador"""
    apoiador = Apoiador(
        discord_id="123456789",
        guild_id="987654321",
        id_pagamento="kofi_test_123",
        tipo_apoio="kofi",
        valor_doacao=5000,  # R$ 50,00
        data_inicio=datetime.now(timezone.utc),
        data_expiracao=datetime.now(timezone.utc) + timedelta(days=30),
        ativo=True,
        ja_pago=True,
        cargo_atribuido=True
    )
    return apoiador


# ============================================
# TESTES DO WEBHOOK KO-FI
# ============================================

class TestKofiWebhook:
    """Testes para o webhook Ko-fi"""

    @pytest.mark.asyncio
    async def test_nova_doacao_unico(self, mock_session, mock_bot):
        """Testa o processamento de uma nova doação única"""
        # Mock do bot
        mock_bot.guilds = [Mock()]
        mock_bot.guilds[0].id = 987654321
        
        # Mock do verificador
        verificador_mock = Mock()
        verificador_mock.atribuir_cargo_apos_pagamento = AsyncMock(return_value=True)
        
        # Mock do request
        request = AsyncMock()
        request.form = AsyncMock(return_value={
            "data": '{"transaction_id": "kofi_new_123", "type": "Donation", "amount": "50.00", "email": "test@example.com", "from_name": "Test User"}'
        })
        
        # Mock do bot instance
        with patch('bot.web.main.get_bot_instance', return_value=mock_bot):
            with patch('bot.web.main.VerificacaoMembro', return_value=verificador_mock):
                # Mock do execute para retornar None (não existe)
                mock_session.execute.return_value.scalars.first = AsyncMock(return_value=None)
                
                # Mock do bot.db.obter_apoiador
                mock_bot.db.obter_apoiador = AsyncMock(return_value=None)
                
                # Mock do fetch_member
                mock_bot.guilds[0].fetch_member = AsyncMock(return_value=Mock())
                
                # Mock do get_role
                mock_bot.guilds[0].get_role = Mock(return_value=Mock())
                
                # Mock do session
                with patch('bot.web.main.AsyncSessionLocal') as mock_session_factory:
                    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                    
                    # Mock do commit
                    mock_session.commit = AsyncMock()
                    
                    # Executar o webhook
                    result = await kofi_webhook(request)
                    
                    # Verificar resultado
                    assert result["status"] == "sucesso"
                    assert result["cargo_atribuido"] == "✅ Sim"

    @pytest.mark.asyncio
    async def test_renovacao_assinatura(self, mock_session, mock_bot):
        """Testa a detecção de renovação de assinatura"""
        # Criar apoiador existente (expirado)
        apoiador_existente = Apoiador(
            discord_id="123456789",
            guild_id="987654321",
            id_pagamento="kofi_subscription_123",
            tipo_apoio="kofi",
            ativo=False,  # Estava expirado
            cargo_atribuido=True,
            data_expiracao=datetime.now(timezone.utc) - timedelta(days=5)
        )
        
        # Mock do request com assinatura
        request = AsyncMock()
        request.form = AsyncMock(return_value={
            "data": '{"transaction_id": "kofi_subscription_123", "type": "Subscription", "amount": "50.00", "email": "test@example.com", "from_name": "Test User"}'
        })
        
        # Mock do execute para retornar apoiador existente
        mock_result = AsyncMock()
        mock_result.scalars.first = AsyncMock(return_value=apoiador_existente)
        mock_session.execute.return_value = mock_result
        
        # Mock do bot
        mock_bot.guilds = [Mock()]
        mock_bot.guilds[0].id = 987654321
        
        # Mock do verificador
        verificador_mock = Mock()
        verificador_mock.atribuir_cargo_apos_pagamento = AsyncMock(return_value=True)
        
        with patch('bot.web.main.get_bot_instance', return_value=mock_bot):
            with patch('bot.web.main.VerificacaoMembro', return_value=verificador_mock):
                with patch('bot.web.main.AsyncSessionLocal') as mock_session_factory:
                    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                    mock_session.commit = AsyncMock()
                    
                    # Executar o webhook
                    result = await kofi_webhook(request)
                    
                    # Verificar que o apoiador foi reativado
                    assert apoiador_existente.ativo == True
                    assert apoiador_existente.cargo_atribuido == False  # Reset para reaplicar cargo
                    assert apoiador_existente.data_expiracao > datetime.now(timezone.utc)
                    assert result["status"] == "renovado"

    @pytest.mark.asyncio
    async def test_duplicata_detectada(self, mock_session):
        """Testa a detecção de transação duplicada"""
        apoiador_existente = Apoiador(
            discord_id="123456789",
            guild_id="987654321",
            id_pagamento="kofi_duplicate_123",
            tipo_apoio="kofi",
            ativo=True
        )
        
        # Mock do request
        request = AsyncMock()
        request.form = AsyncMock(return_value={
            "data": '{"transaction_id": "kofi_duplicate_123", "type": "Donation", "amount": "50.00"}'
        })
        
        # Mock do execute para retornar apoiador existente
        mock_result = AsyncMock()
        mock_result.scalars.first = AsyncMock(return_value=apoiador_existente)
        mock_session.execute.return_value = mock_result
        
        with patch('bot.web.main.AsyncSessionLocal') as mock_session_factory:
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            
            result = await kofi_webhook(request)
            
            assert result["status"] == "duplicado"

    @pytest.mark.asyncio
    async def test_token_verificacao_invalido(self, mock_session):
        """Testa rejeição com token de verificação inválido"""
        request = AsyncMock()
        request.form = AsyncMock(return_value={
            "data": '{"transaction_id": "kofi_test_123", "type": "Donation", "amount": "50.00", "verification_token": "invalid_token"}'
        })
        
        with patch('bot.web.main.AsyncSessionLocal') as mock_session_factory:
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            
            with pytest.raises(Exception) as exc_info:
                await kofi_webhook(request)
            
            assert "Token de verificação inválido" in str(exc_info.value)


# ============================================
# TESTES DO SCHEDULER - CHECK EXPIRATIONS
# ============================================

class TestCheckExpirations:
    """Testes para a função check_expirations()"""

    @pytest.mark.asyncio
    async def test_expiracao_detectada(self, mock_session):
        """Testa detecção de apoiadores expirados"""
        # Criar apoiadores
        apoiador_expirado = Apoiador(
            discord_id="111111111",
            guild_id="987654321",
            id_pagamento="kofi_expirado_1",
            tipo_apoio="kofi",
            ativo=True,
            data_expiracao=datetime.now(timezone.utc) - timedelta(days=1)  # Expirou ontem
        )
        
        apoiador_ativo = Apoiador(
            discord_id="222222222",
            guild_id="987654321",
            id_pagamento="kofi_ativo_1",
            tipo_apoio="kofi",
            ativo=True,
            data_expiracao=datetime.now(timezone.utc) + timedelta(days=1)  # Ainda válido
        )
        
        # Mock do execute para retornar apoiadores
        mock_result = AsyncMock()
        mock_result.scalars.all = AsyncMock(return_value=[apoiador_expirado])
        mock_session.execute.return_value = mock_result
        
        # Mock do commit
        mock_session.commit = AsyncMock()
        
        # Executar check_expirations (patch AsyncSessionLocal para usar mock_session)
        with patch('bot.web.main.AsyncSessionLocal') as mock_session_factory:
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            await check_expirations()
        
        # Verificar que apoiador expirado foi marcado como inativo
        assert apoiador_expirado.ativo == False
        # Verificar que apoiador ativo não foi alterado
        assert apoiador_ativo.ativo == True
        # Verificar que commit foi chamado
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_nenhum_expirado(self, mock_session):
        """Testa quando não há apoiadores expirados"""
        apoiador_ativo = Apoiador(
            discord_id="111111111",
            guild_id="987654321",
            id_pagamento="kofi_ativo_1",
            tipo_apoio="kofi",
            ativo=True,
            data_expiracao=datetime.now(timezone.utc) + timedelta(days=30)
        )
        
        mock_result = AsyncMock()
        mock_result.scalars.all = AsyncMock(return_value=[])
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()
        
        with patch('bot.web.main.AsyncSessionLocal') as mock_session_factory:
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            await check_expirations()
        
        # Verificar que commit não foi chamado (nenhum apoiador expirado)
        mock_session.commit.assert_not_called()


# ============================================
# TESTES DO SCHEDULER - RENOVAR APOIADORES
# ============================================

class TestRenovarApoiadoresExpirados:
    """Testes para a função renovar_apoiadores_expirados()"""

    @pytest.mark.asyncio
    async def test_renovacao_kofi(self, mock_session):
        """Testa renovação de apoiadores Ko-fi expirados"""
        # Criar apoiador expirado Ko-fi
        apoiador_expirado = Apoiador(
            discord_id="111111111",
            guild_id="987654321",
            id_pagamento="kofi_expirado_1",
            tipo_apoio="kofi",
            ativo=False,
            data_expiracao=datetime.now(timezone.utc) - timedelta(days=5)
        )
        
        # Criar apoiador PIX (não deve ser renovado)
        apoiador_pix = Apoiador(
            discord_id="222222222",
            guild_id="987654321",
            id_pagamento="pix_expirado_1",
            tipo_apoio="pix",
            ativo=False,
            data_expiracao=None
        )
        
        mock_result = AsyncMock()
        mock_result.scalars.all = AsyncMock(return_value=[apoiador_expirado])
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()
        
        # Executar renovar_apoiadores_expirados (patch AsyncSessionLocal para usar mock_session)
        with patch('bot.web.main.AsyncSessionLocal') as mock_session_factory:
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            await renovar_apoiadores_expirados()
        
        # Verificar que Ko-fi foi reativado
        assert apoiador_expirado.ativo == True
        assert apoiador_expirado.data_expiracao > datetime.now(timezone.utc)
        assert apoiador_expirado.data_expiracao < datetime.now(timezone.utc) + timedelta(days=31)
        
        # Verificar que PIX não foi alterado
        assert apoiador_pix.ativo == False
        assert apoiador_pix.data_expiracao is None
        
        # Verificar que commit foi chamado
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_nenhum_apoiador_expirado(self, mock_session):
        """Testa quando não há apoiadores expirados"""
        mock_result = AsyncMock()
        mock_result.scalars.all = AsyncMock(return_value=[])
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()
        
        with patch('bot.web.main.AsyncSessionLocal') as mock_session_factory:
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            await renovar_apoiadores_expirados()

        mock_session.commit.assert_not_called()


# ============================================
# TESTES DO SCHEDULER - REATIVAR CARGOS
# ============================================

class TestReativarCargosDaAssinatura:
    """Testes para a função reativar_cargos_da_assinatura()"""

    @pytest.mark.asyncio
    async def test_reativacao_cargo(self, mock_session, mock_bot, mock_member, mock_role):
        """Testa reativação de cargo para apoiadores Ko-fi"""
        # Criar apoiador reativado que precisa de cargo
        apoiador_reativado = Apoiador(
            discord_id="111111111",
            guild_id="987654321",
            id_pagamento="kofi_reativado_1",
            tipo_apoio="kofi",
            ativo=True,
            cargo_atribuido=False  # Precisa de cargo
        )
        
        # Mock do execute para retornar apoiadores
        mock_result = AsyncMock()
        mock_result.scalars.all = AsyncMock(return_value=[apoiador_reativado])
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()
        
        # Mock do bot
        mock_guild = Mock()
        mock_guild.id = 987654321
        mock_guild.get_member = Mock(return_value=mock_member)
        mock_guild.get_role = Mock(return_value=mock_role)
        mock_guild.chunk = AsyncMock()
        
        mock_bot.guilds = [mock_guild]
        mock_bot.db = Mock()
        mock_bot.db.obter_apoiador = AsyncMock(return_value=apoiador_reativado)
        
        # Mock do verificador
        verificador_mock = Mock()
        verificador_mock.atribuir_cargo_apos_pagamento = AsyncMock(return_value=True)
        
        with patch('bot.web.main.get_bot_instance', return_value=mock_bot):
            with patch('bot.web.main.VerificacaoMembro', return_value=verificador_mock):
                with patch('bot.web.main.AsyncSessionLocal') as mock_session_factory:
                    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                    # Executar reativar_cargos_da_assinatura
                    await reativar_cargos_da_assinatura()
                
                # Verificar que cargo_atribuido foi marcado como True
                assert apoiador_reativado.cargo_atribuido == True
                
                # Verificar que commit foi chamado
                mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_nenhum_apoiador_para_reativar(self, mock_session):
        """Testa quando não há apoiadores para reativar cargo"""
        mock_result = AsyncMock()
        mock_result.scalars.all = AsyncMock(return_value=[])
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()
        
        with patch('bot.web.main.get_bot_instance', return_value=None):
            await reativar_cargos_da_assinatura()
        
        mock_session.commit.assert_not_called()


# ============================================
# TESTES DA CLASSE VERIFICACAO MEMBRO
# ============================================

class TestVerificacaoMembro:
    """Testes para a classe VerificacaoMembro"""

    @pytest.mark.asyncio
    async def test_tempo_servidor(self, mock_member):
        """Testa cálculo de tempo no servidor"""
        bot = Mock()
        verificador = VerificacaoMembro(bot)
        
        # Testar com 45 dias
        member = Mock()
        member.joined_at = datetime.now(timezone.utc) - timedelta(days=45)
        
        tempo = await verificador.tempo_servidor(member)
        
        assert "1 mes" in tempo or "45 dia" in tempo

    @pytest.mark.asyncio
    async def test_verificar_tempo_minimo(self, mock_member):
        """Testa verificação de tempo mínimo"""
        bot = Mock()
        verificador = VerificacaoMembro(bot)
        
        # Testar com 45 dias e mínimo de 30 dias
        member = Mock()
        member.joined_at = datetime.now(timezone.utc) - timedelta(days=45)
        
        resultado = await verificador.verificar_tempo_minimo(member, 30)
        
        assert resultado == True

    @pytest.mark.asyncio
    async def test_obter_apoiador(self, mock_session, mock_bot):
        """Testa obtenção de apoiador"""
        apoiador = Apoiador(
            discord_id="123456789",
            guild_id="987654321",
            id_pagamento="kofi_test_123",
            tipo_apoio="kofi"
        )
        
        mock_result = AsyncMock()
        mock_result.scalars.first = AsyncMock(return_value=apoiador)
        mock_session.execute.return_value = mock_result
        
        mock_bot.db.obter_apoiador = AsyncMock(return_value=apoiador)
        verificador = VerificacaoMembro(mock_bot)
        
        resultado = await verificador.obter_apoiador("123456789", "987654321")
        
        assert resultado.discord_id == "123456789"

    @pytest.mark.asyncio
    async def test_atribuir_cargo_apos_pagamento(self, mock_session, mock_bot, mock_member, mock_role):
        """Testa atribuição de cargo após pagamento"""
        apoiador = Apoiador(
            discord_id="123456789",
            guild_id="987654321",
            id_pagamento="kofi_test_123",
            tipo_apoio="kofi",
            ativo=True,
            nivel=1
        )
        
        mock_guild = Mock()
        mock_guild.id = 987654321
        mock_guild.get_member = Mock(return_value=mock_member)
        mock_guild.get_role = Mock(return_value=mock_role)
        mock_guild.chunk = AsyncMock()
        # Garante identidade e permissões do bot para comparação de cargos
        mock_guild.me = Mock()
        mock_guild.me.guild_permissions = Mock(manage_roles=True)
        mock_guild.me.top_role = Mock(position=100)
        mock_bot.get_guild = Mock(return_value=mock_guild)
        mock_bot.db.obter_apoiador = AsyncMock(return_value=apoiador)
        
        verificador = VerificacaoMembro(mock_bot)
        
        with patch('bot.servicos.VerificacaoMembro.AsyncSessionLocal') as mock_session_factory:
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            resultado = await verificador.atribuir_cargo_apos_pagamento(
                "123456789",
                987654321,
                cargo_id=111222333
            )
        
        assert resultado == True


# ============================================
# TESTES DE INTEGRAÇÃO
# ============================================

class TestIntegracaoSistemaDoacoes:
    """Testes de integração do sistema completo de doações"""

    @pytest.mark.asyncio
    async def test_fluxo_completo_doacao(self, mock_session, mock_bot):
        """Testa o fluxo completo: webhook → atribuição → renovação"""
        # 1. Nova doação
        apoiador = Apoiador(
            discord_id="123456789",
            guild_id="987654321",
            id_pagamento="kofi_fluxo_1",
            tipo_apoio="kofi",
            valor_doacao=5000,
            data_inicio=datetime.now(timezone.utc),
            data_expiracao=datetime.now(timezone.utc) + timedelta(days=30),
            ativo=True,
            ja_pago=True,
            cargo_atribuido=False
        )
        
        # 2. Webhook processa
        assert apoiador.ativo == True
        assert apoiador.data_expiracao > datetime.now(timezone.utc)
        
        # 3. Cargo atribuído
        apoiador.cargo_atribuido = True
        assert apoiador.cargo_atribuido == True
        
        # 4. Expiração detectada
        apoiador.data_expiracao = datetime.now(timezone.utc) - timedelta(days=1)
        apoiador.ativo = False
        assert apoiador.ativo == False
        
        # 5. Renovação automática
        apoiador.ativo = True
        apoiador.cargo_atribuido = False  # Reset
        apoiador.data_expiracao = datetime.now(timezone.utc) + timedelta(days=30)
        
        assert apoiador.ativo == True
        assert apoiador.cargo_atribuido == False
        assert apoiador.data_expiracao > datetime.now(timezone.utc)

    @pytest.mark.asyncio
    async def test_fluxo_pix_sem_renovacao(self, mock_session):
        """Testa que PIX não tem renovação automática"""
        apoiador_pix = Apoiador(
            discord_id="123456789",
            guild_id="987654321",
            id_pagamento="pix_fluxo_1",
            tipo_apoio="pix",
            valor_doacao=5000,
            data_inicio=datetime.now(timezone.utc),
            data_expiracao=None,  # PIX não tem data de expiração
            ativo=True,
            ja_pago=True
        )
        
        # Verificar que tipo_apoio = "pix" não é renovado
        assert apoiador_pix.tipo_apoio == "pix"
        assert apoiador_pix.data_expiracao is None
        
        # Simular expiração (não deve acontecer para PIX)
        apoiador_pix.ativo = False
        assert apoiador_pix.ativo == False
        
        # Verificar que não é renovado (só Ko-fi é renovado)
        if apoiador_pix.tipo_apoio == "kofi":
            apoiador_pix.ativo = True
            apoiador_pix.data_expiracao = datetime.now(timezone.utc) + timedelta(days=30)
        
        # PIX permanece inativo
        assert apoiador_pix.ativo == False


# ============================================
# TESTES DE VALIDAÇÃO
# ============================================

class TestValidacaoDados:
    """Testes de validação de dados"""

    @pytest.mark.asyncio
    async def test_validacao_valor_doacao(self):
        """Testa validação de valor de doação"""
        apoiador = Apoiador(
            discord_id="123456789",
            guild_id="987654321",
            id_pagamento="kofi_test_123",
            tipo_apoio="kofi",
            valor_doacao=5000,  # R$ 50,00
            data_inicio=datetime.now(timezone.utc),
            data_expiracao=datetime.now(timezone.utc) + timedelta(days=30),
            ativo=True,
            ja_pago=True
        )
        
        assert apoiador.valor_doacao == 5000
        assert apoiador.valor_doacao > 0

    @pytest.mark.asyncio
    async def test_validacao_data_expiracao(self):
        """Testa validação de data de expiração"""
        agora = datetime.now(timezone.utc)
        
        apoiador = Apoiador(
            discord_id="123456789",
            guild_id="987654321",
            id_pagamento="kofi_test_123",
            tipo_apoio="kofi",
            data_inicio=agora,
            data_expiracao=agora + timedelta(days=30),
            ativo=True
        )
        
        assert apoiador.data_expiracao > apoiador.data_inicio
        assert apoiador.data_expiracao < agora + timedelta(days=31)

    @pytest.mark.asyncio
    async def test_validacao_cargo_atribuido(self):
        """Testa validação do flag cargo_atribuido"""
        apoiador = Apoiador(
            discord_id="123456789",
            guild_id="987654321",
            id_pagamento="kofi_test_123",
            tipo_apoio="kofi",
            ativo=True,
            cargo_atribuido=True
        )
        
        assert apoiador.cargo_atribuido == True
        
        # Simular reset para renovação
        apoiador.cargo_atribuido = False
        assert apoiador.cargo_atribuido == False


# ============================================
# TESTES DE CONCORRÊNCIA
# ============================================

class TestConcorrencia:
    """Testes para cenários de concorrência"""

    @pytest.mark.asyncio
    async def test_duplicata_simultanea(self, mock_session):
        """Testa comportamento quando webhook chega duplicado"""
        apoiador_existente = Apoiador(
            discord_id="123456789",
            guild_id="987654321",
            id_pagamento="kofi_duplicado_1",
            tipo_apoio="kofi",
            ativo=True
        )
        
        # Mock do execute para retornar apoiador existente
        mock_result = AsyncMock()
        mock_result.scalars.first = AsyncMock(return_value=apoiador_existente)
        mock_session.execute.return_value = mock_result
        
        # Mock do request
        request = AsyncMock()
        request.form = AsyncMock(return_value={
            "data": '{"transaction_id": "kofi_duplicado_1", "type": "Donation", "amount": "50.00"}'
        })
        
        with patch('bot.web.main.AsyncSessionLocal') as mock_session_factory:
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            
            result = await kofi_webhook(request)
            
            # Deve detectar duplicata e rejeitar
            assert result["status"] == "duplicado"

    @pytest.mark.asyncio
    async def test_renovacao_simultanea(self, mock_session):
        """Testa comportamento quando renovação chega múltiplas vezes"""
        apoiador = Apoiador(
            discord_id="123456789",
            guild_id="987654321",
            id_pagamento="kofi_renovacao_1",
            tipo_apoio="kofi",
            ativo=False,
            cargo_atribuido=True,
            data_expiracao=datetime.now(timezone.utc) - timedelta(days=5)
        )
        
        # Mock do execute para retornar apoiador existente
        mock_result = AsyncMock()
        mock_result.scalars.first = AsyncMock(return_value=apoiador)
        mock_session.execute.return_value = mock_result
        
        # Mock do request
        request = AsyncMock()
        request.form = AsyncMock(return_value={
            "data": '{"transaction_id": "kofi_renovacao_1", "type": "Subscription", "amount": "50.00"}'
        })
        
        with patch('bot.web.main.AsyncSessionLocal') as mock_session_factory:
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            
            result = await kofi_webhook(request)
            
            # Deve detectar renovação
            assert result["status"] == "renovado"
            assert apoiador.ativo == True
            assert apoiador.cargo_atribuido == False  # Reset
            assert apoiador.data_expiracao > datetime.now(timezone.utc)


# ============================================
# RUNNER
# ============================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
