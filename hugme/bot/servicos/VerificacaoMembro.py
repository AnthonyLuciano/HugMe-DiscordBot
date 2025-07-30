import discord, logging
from datetime import datetime, timezone
from bot.database import engine
from bot.database.models import Apoiador
from sqlalchemy.orm import Session

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VerificacaoMembro:
    """Classe para calcular o tempo de permanência de um membro no servidor."""

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    async def tempo_servidor(self, member: discord.Member) -> str:
        """Calcula o tempo de permanência de um membro no servidor e retorna uma string formatada.

        Args:
            member (discord.Member): O membro do Discord a ser verificado.

        Returns:
            str: String formatada com o tempo de permanência (ex: "1 ano, 2 meses, 3 dias").
        """
        agora = datetime.now(timezone.utc)
        entrada = member.joined_at

        if entrada is None:
            return "tempo desconhecido"

        diferenca = agora - entrada

        # Calcula os componentes de tempo
        anos = diferenca.days // 365
        meses = (diferenca.days % 365) // 30
        dias = (diferenca.days % 365) % 30
        horas = diferenca.seconds // 3600

        # Constrói a string de retorno de forma dinâmica
        partes = []

        if anos > 0:
            partes.append(f"{anos} ano{'s' if anos != 1 else ''}")
        if meses > 0:
            partes.append(f"{meses} mes{'es' if meses != 1 else ''}")
        if dias > 0 and anos < 2:  # Mostra dias apenas se for menos de 2 anos
            partes.append(f"{dias} dia{'s' if dias != 1 else ''}")
        if horas > 0 and anos == 0 and meses == 0:  # Mostra horas apenas se for menos de 1 mês
            partes.append(f"{horas} hora{'s' if horas != 1 else ''}")

        # Se for menos de 1 hora, mostra "menos de 1 hora"
        if not partes:
            return "menos de 1 hora"
            
        return ', '.join(partes)

    async def obter_guild_id(self, member: discord.Member) -> int:
        """Obtém o ID do servidor (guild) a partir do objeto member.

        Args:
            member (discord.Member): O membro do Discord.

        Returns:
            int: ID do servidor.
        """
        return member.guild.id
    
    async def verificar_tempo_minimo(self, member: discord.Member, tempo_minimo_dias: int) -> bool:
        """Verifica se o membro tem o tempo mínimo necessário no servidor.
        
        Args:
            member: O membro a verificar
            tempo_minimo_dias: Tempo mínimo em dias
            
        Returns:
            bool: True se atender ao requisito
        """
        if member.joined_at is None:
            return False

        diferenca = datetime.now(timezone.utc) - member.joined_at
        return diferenca.days >= tempo_minimo_dias
    
    async def obter_apoiador(self, discord_id: str, guild_id: str) -> Apoiador | None:
        """Obtém um apoiador pelo Discord ID e Guild ID"""
        return self.db.obter_apoiador(discord_id, guild_id)


    async def aplicar_cargo_se_qualificado(self, member: discord.Member, cargo_id: int, tempo_minimo_dias: int, nivel_apoio: int | None = None) -> str:
        cargo = member.guild.get_role(cargo_id)
        if not cargo:
            return "Cargo não encontrado!"
        
        try:
            apoiador = await self.obter_apoiador(str(member.id), str(member.guild.id))
            
            if nivel_apoio is not None:
                if apoiador and apoiador.ativo and apoiador.nivel >= nivel_apoio:
                    await member.add_roles(cargo)
                    return f"Cargo de apoiador {cargo.name} aplicado!"
                return "Você não é um apoiador qualificado"
            
            if await self.verificar_tempo_minimo(member, tempo_minimo_dias):
                await member.add_roles(cargo)
                tempo_atual = await self.tempo_servidor(member)
                return f"Cargo {cargo.name} aplicado com sucesso! (Tempo: {tempo_atual})"
            else:    
                tempo_atual = await self.tempo_servidor(member)
                return f"Precisa de {tempo_minimo_dias} dias (atual: {tempo_atual})"
        except Exception as e:
            logger.error(f"Erro ao verificar apoiador: {e}")
            return "Erro ao verificar status"

    async def atribuir_cargo_apos_pagamento(self, discord_id: str, guild_id: int, cargo_id: int) -> bool:
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return False
        
        member = guild.get_member(int(discord_id))
        if not member:
            return False
        
        cargo = guild.get_role(cargo_id)
        if not cargo:
            return False
        
        try:
            await member.add_roles(cargo)
        
        # Atualiza o status no banco de dados
            apoiador = await self.obter_apoiador(discord_id, str(guild_id))
            if apoiador:
                apoiador.cargo_atribuido = True
                with Session(engine) as session:
                    session.add(apoiador)
                    session.commit()
        
            return True
        except Exception as e:
            logger.error(f"Erro ao atribuir cargo: {e}")
            return False