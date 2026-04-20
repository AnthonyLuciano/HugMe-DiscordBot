"""
Testes unitários para o comando /doar - HugMe Bot

Este módulo contém testes para o sistema de doações via Pix e Ko-fi,
simulando interações completas do usuário ao admin.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta, timezone

# Importar classes do comando doar
from bot.commands.doar import (
    DoarCommands, DonationModal, DoarView, DMConfirmationView,
    get_brasilia_time, disable_admin_buttons
)


class TestDoarCommands:
    """Testes para a classe DoarCommands"""

    @pytest.fixture
    def mock_bot(self):
        """Fixture para mock do bot"""
        bot = AsyncMock()
        bot.get_cog.return_value = None  # Por padrão, sem cog
        return bot

    @pytest.fixture
    def mock_session(self):
        """Fixture para mock da sessão do banco"""
        session = MagicMock()
        return session

    @pytest.fixture
    def cog(self, mock_bot):
        """Fixture para a cog DoarCommands"""
        return DoarCommands(mock_bot)

    @pytest.mark.asyncio
    async def test_doar_command_success(self, cog, mock_bot):
        """Testa o comando /doar com sucesso"""
        # Mock do contexto
        ctx = AsyncMock()
        ctx.author = AsyncMock()
        ctx.author.id = 12345
        ctx.guild = AsyncMock()
        ctx.guild.id = 67890
        ctx.send = AsyncMock()

        # Executa o comando via callback
        await cog.doar.callback(cog, ctx)

        # Verifica se send foi chamado com embed e view
        assert ctx.send.called
        call_args = ctx.send.call_args
        embed = call_args[1]['embed']
        view = call_args[1]['view']

        assert embed.title == "💖 Apoie Nossa Comunidade!"
        assert isinstance(view, DoarView)

    @pytest.mark.asyncio
    async def test_doar_command_dm_warning(self, cog, mock_bot):
        """Testa o comando /doar em DM (sem guild)"""
        ctx = AsyncMock()
        ctx.author = AsyncMock()
        ctx.guild = None
        ctx.send = AsyncMock()

        await cog.doar.callback(cog, ctx)

        call_args = ctx.send.call_args
        embed = call_args[1]['embed']
        view = call_args[1]['view']

        assert "Doação via Mensagem Direta" in embed.title
        assert isinstance(view, DMConfirmationView)

    @pytest.mark.asyncio
    async def test_doar_command_forbidden_error(self, cog, mock_bot):
        """Testa erro de Forbidden no comando /doar"""
        ctx = AsyncMock()
        ctx.author = AsyncMock()
        ctx.guild = AsyncMock()
        # Falha na primeira chamada (embed), sucesso na segunda (erro)
        ctx.send = AsyncMock(side_effect=[Exception("Forbidden"), None])

        await cog.doar.callback(cog, ctx)

        # Verifica se tentou enviar mensagem de erro
        assert ctx.send.call_count == 2


class TestDonationModal:
    """Testes para o modal DonationModal"""

    @pytest.fixture
    def mock_bot(self):
        """Fixture para mock do bot"""
        bot = AsyncMock()
        cog = AsyncMock()
        bot.get_cog.return_value = cog
        return bot

    @pytest.fixture
    def modal(self, mock_bot):
        """Fixture para o modal"""
        return DonationModal(mock_bot)

    @pytest.mark.asyncio
    async def test_modal_submit_valid_amount(self, modal, mock_bot):
        """Testa submissão do modal com valor válido"""
        # Mock da interação
        interaction = AsyncMock()
        interaction.user = AsyncMock()
        interaction.user.id = 12345
        interaction.user.mention = "@user"
        interaction.guild = AsyncMock()
        interaction.guild.id = 67890
        interaction.response = AsyncMock()
        interaction.response.send_message = AsyncMock()

        # Mock DM channel
        mock_dm_channel = AsyncMock()
        mock_dm_channel.send = AsyncMock(return_value=AsyncMock())  # bot_message
        interaction.user.create_dm = AsyncMock(return_value=mock_dm_channel)

        # Mock original_response for ephemeral
        mock_user_message = AsyncMock()
        interaction.original_response = AsyncMock(return_value=mock_user_message)

        # Mock do valor
        modal.amount = MagicMock()
        modal.amount.value = "10.00"

        # Mock do banco
        with patch('bot.commands.doar.SessionLocal') as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_session_cls.return_value.__exit__ = MagicMock(return_value=None)

            # Mock query para Apoiador
            mock_apoiador = None
            # Mock query para PixConfig
            mock_config = MagicMock()
            mock_config.chave = "pix_key_123"
            mock_config.static_qr_url = "http://qr.url"

            # Configurar query para retornar objetos diferentes
            def mock_query(model):
                if model.__name__ == 'Apoiador':
                    mock_q = MagicMock()
                    mock_q.filter_by.return_value.first.return_value = mock_apoiador
                    return mock_q
                elif model.__name__ == 'PixConfig':
                    mock_q = MagicMock()
                    mock_q.first.return_value = mock_config
                    return mock_q
                return MagicMock()

            mock_session.query = mock_query

            # Mock fetch_channel
            mock_channel = AsyncMock()
            mock_admin_msg = AsyncMock()
            mock_channel.send = AsyncMock(return_value=mock_admin_msg)
            mock_bot.fetch_channel = AsyncMock(return_value=mock_channel)

            # Executa on_submit
            await modal.on_submit(interaction)

            # Verifica se response.send_message foi chamado
            assert interaction.response.send_message.called

            # Verifica se DM foi criada e send chamado
            assert interaction.user.create_dm.called
            assert mock_dm_channel.send.called

    @pytest.mark.asyncio
    async def test_modal_submit_invalid_amount(self, modal):
        """Testa submissão com valor inválido"""
        interaction = AsyncMock()
        interaction.response = AsyncMock()
        interaction.response.send_message = AsyncMock()

        modal.amount = MagicMock()
        modal.amount.value = "invalid"

        await modal.on_submit(interaction)

        # Verifica mensagem de erro
        call_args = interaction.response.send_message.call_args
        assert "Valor inválido" in call_args[0][0]


class TestDoarView:
    """Testes para DoarView"""

    @pytest.fixture
    def mock_bot(self):
        """Fixture para mock do bot"""
        return AsyncMock()

    @pytest.fixture
    def view(self, mock_bot):
        """Fixture para DoarView"""
        return DoarView(mock_bot)

    @pytest.mark.asyncio
    async def test_pix_button(self, view, mock_bot):
        """Testa botão Pix"""
        interaction = AsyncMock()
        interaction.response = AsyncMock()
        interaction.response.send_modal = AsyncMock()

        button = view.children[0]  # Botão Pix
        await button.callback(interaction)

        # Verifica se send_modal foi chamado com DonationModal
        assert interaction.response.send_modal.called
        modal = interaction.response.send_modal.call_args[0][0]
        assert isinstance(modal, DonationModal)

    @pytest.mark.asyncio
    async def test_kofi_button(self, view):
        """Testa botão Ko-fi"""
        interaction = AsyncMock()
        interaction.response = AsyncMock()
        interaction.response.send_message = AsyncMock()

        button = view.children[1]  # Botão Ko-fi
        await button.callback(interaction)

        # Verifica embed Ko-fi
        call_args = interaction.response.send_message.call_args
        embed = call_args[1]['embed']
        assert "Doação via Ko-fi" in embed.title


class TestDMConfirmationView:
    """Testes para DMConfirmationView"""

    @pytest.fixture
    def mock_bot(self):
        """Fixture para mock do bot"""
        return AsyncMock()

    @pytest.fixture
    def view(self, mock_bot):
        """Fixture para DMConfirmationView"""
        return DMConfirmationView(mock_bot)

    @pytest.mark.asyncio
    async def test_confirm_button(self, view, mock_bot):
        """Testa botão de confirmação"""
        interaction = AsyncMock()
        interaction.response = AsyncMock()
        interaction.response.edit_message = AsyncMock()

        button = view.children[0]  # Botão Sim
        await button.callback(interaction)

        # Verifica se edit_message foi chamado com novo embed e view
        assert interaction.response.edit_message.called
        call_args = interaction.response.edit_message.call_args
        embed = call_args[1]['embed']
        new_view = call_args[1]['view']
        assert embed.title == "💖 Apoie Nossa Comunidade!"
        assert isinstance(new_view, DoarView)

    @pytest.mark.asyncio
    async def test_cancel_button(self, view):
        """Testa botão de cancelamento"""
        interaction = AsyncMock()
        interaction.response = AsyncMock()
        interaction.response.edit_message = AsyncMock()

        button = view.children[1]  # Botão Cancelar
        await button.callback(interaction)

        # Verifica mensagem de cancelamento
        call_args = interaction.response.edit_message.call_args
        assert "Doação cancelada" in call_args[1]['content']


class TestInteractionListener:
    """Testes para o listener on_interaction"""

    @pytest.fixture
    def mock_bot(self):
        """Fixture para mock do bot"""
        bot = AsyncMock()
        cog = AsyncMock()
        bot.get_cog.return_value = cog
        return bot

    @pytest.fixture
    def cog(self, mock_bot):
        """Fixture para a cog"""
        return DoarCommands(mock_bot)

    @pytest.mark.asyncio
    async def test_user_paid_button(self, cog):
        """Testa botão 'já paguei'"""
        interaction = AsyncMock()
        interaction.data = {"custom_id": "user_paid_ref123"}
        interaction.response = AsyncMock()
        interaction.response.send_message = AsyncMock()

        await cog.on_interaction(interaction)

        # Verifica resposta de confirmação
        call_args = interaction.response.send_message.call_args
        assert "Obrigado pelo pagamento" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_confirm_payment_button(self, cog, mock_bot):
        """Testa botão de confirmação de pagamento pelo admin"""
        interaction = AsyncMock()
        interaction.data = {"custom_id": "confirm_payment_ref123"}
        interaction.message = AsyncMock()
        interaction.message.embeds = [MagicMock()]
        interaction.response = AsyncMock()
        interaction.response.send_message = AsyncMock()

        # Mock do banco
        with patch('bot.commands.doar.SessionLocal') as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_session_cls.return_value.__exit__ = MagicMock(return_value=None)

            mock_apoiador = MagicMock()
            mock_apoiador.discord_id = "12345"
            mock_apoiador.guild_id = "67890"

            def mock_query(model):
                if model.__name__ == 'Apoiador':
                    mock_q = MagicMock()
                    mock_q.filter_by.return_value.first.return_value = mock_apoiador
                    return mock_q
                return MagicMock()

            mock_session.query = mock_query

            # Mock guild e member
            mock_guild = AsyncMock()
            mock_member = AsyncMock()
            mock_guild.get_member = MagicMock(return_value=mock_member)  # get_member é síncrono
            mock_bot.get_guild = MagicMock(return_value=mock_guild)  # get_guild é síncrono

            # Mock role manager
            cog.role_manager = AsyncMock()
            cog.role_manager.assign_default_supporter_role = AsyncMock(return_value=True)
            cog.role_manager.update_member_time_based_roles = AsyncMock(return_value=True)

            await cog.on_interaction(interaction)

            # Verifica se apoiador.ja_pago foi setado
            assert mock_apoiador.ja_pago == True
            # Verifica resposta
            assert interaction.response.send_message.called

    @pytest.mark.asyncio
    async def test_reject_payment_button(self, cog):
        """Testa botão de rejeição de pagamento"""
        interaction = AsyncMock()
        interaction.data = {"custom_id": "reject_payment_ref123"}
        interaction.message = AsyncMock()
        interaction.message.embeds = [MagicMock()]
        interaction.response = AsyncMock()
        interaction.response.send_message = AsyncMock()

        await cog.on_interaction(interaction)

        # Verifica se embed foi editado com rejeição
        assert interaction.message.edit.called
        # Verifica resposta
        assert interaction.response.send_message.called


class TestUtilityFunctions:
    """Testes para funções utilitárias"""

    def test_get_brasilia_time(self):
        """Testa função get_brasilia_time"""
        time = get_brasilia_time()
        assert isinstance(time, datetime)
        # Verifica se está no timezone correto (UTC-3)
        assert time.tzinfo == timezone(timedelta(hours=-3))

    @pytest.mark.asyncio
    async def test_disable_admin_buttons(self):
        """Testa função disable_admin_buttons"""
        message = AsyncMock()
        message.components = [
            MagicMock(children=[MagicMock(style=1, label="Test", custom_id="test")])
        ]
        message.edit = AsyncMock()

        await disable_admin_buttons(message)

        # Verifica se edit foi chamado
        assert message.edit.called


# Para executar os testes: pytest tests/test_doar.py -v