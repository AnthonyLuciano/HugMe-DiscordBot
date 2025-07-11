import discord
from datetime import datetime, timezone

class VerificacaoMembro:
    """Classe para calcular o tempo de permanência de um membro no servidor."""

    def __init__(self, bot):
        self.bot = bot

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