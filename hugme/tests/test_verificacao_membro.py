import unittest
from typing import Optional
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
import discord
from bot.servicos.VerificacaoMembro import VerificacaoMembro

class TestVerificacaoMembro(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        """Configuração inicial para cada teste."""
        self.bot = MagicMock()  # Mock do bot
        self.verificador = VerificacaoMembro(self.bot)

    def criar_membro_mock(self, joined_at: Optional[datetime]) -> discord.Member:
        """Cria um mock de discord.Member com uma data de entrada específica."""
        member = MagicMock(spec=discord.Member)
        member.joined_at = joined_at
        member.display_name = "Membro Teste"
        return member

    async def test_tempo_servidor_menos_de_1_hora(self):
        """Testa o caso onde o membro está no servidor há menos de 1 hora."""
        agora = datetime.now(timezone.utc)
        entrada = agora - timedelta(minutes=30)  # 30 minutos atrás
        member = self.criar_membro_mock(entrada)

        resultado = await self.verificador.tempo_servidor(member)
        self.assertEqual(resultado, "menos de 1 hora")

    async def test_tempo_servidor_1_dia(self):
        """Testa o caso onde o membro está no servidor há 1 dia."""
        agora = datetime.now(timezone.utc)
        entrada = agora - timedelta(days=1)  # 1 dia atrás
        member = self.criar_membro_mock(entrada)

        resultado = await self.verificador.tempo_servidor(member)
        self.assertEqual(resultado, "1 dia")

    async def test_tempo_servidor_1_mes(self):
        """Testa o caso onde o membro está no servidor há 1 mês."""
        agora = datetime.now(timezone.utc)
        entrada = agora - timedelta(days=30)  # 30 dias atrás (~1 mês)
        member = self.criar_membro_mock(entrada)

        resultado = await self.verificador.tempo_servidor(member)
        self.assertEqual(resultado, "1 mes")

    async def test_tempo_servidor_1_ano(self):
        """Testa o caso onde o membro está no servidor há 1 ano."""
        agora = datetime.now(timezone.utc)
        entrada = agora - timedelta(days=365)  # 365 dias atrás (~1 ano)
        member = self.criar_membro_mock(entrada)

        resultado = await self.verificador.tempo_servidor(member)
        self.assertEqual(resultado, "1 ano")

    async def test_tempo_servidor_1_ano_2_meses_3_dias(self):
        """Testa o caso onde o membro está no servidor há 1 ano, 2 meses e 3 dias."""
        agora = datetime.now(timezone.utc)
        entrada = agora - timedelta(days=365 + 60 + 3)  # 1 ano, 2 meses e 3 dias atrás
        member = self.criar_membro_mock(entrada)

        resultado = await self.verificador.tempo_servidor(member)
        self.assertEqual(resultado, "1 ano, 2 meses, 3 dias")

    async def test_tempo_servidor_sem_joined_at(self):
        """Testa o caso onde joined_at é None."""
        member = self.criar_membro_mock(None)
        resultado = await self.verificador.tempo_servidor(member)
        self.assertEqual(resultado, "tempo desconhecido")

if __name__ == '__main__':
    unittest.main()