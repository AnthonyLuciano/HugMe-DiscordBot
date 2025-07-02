import discord
from datetime import datetime, timezone

class VerificacaoMembro:
    """Apenas calcula tempo de servidor - SEM níveis, SEM banco de dados"""
    
    def __init__(self, bot):
        self.bot = bot

    async def tempo_servidor(self, member: discord.Member) -> str:
        agora = datetime.now(timezone.utc)
        entrada = member.joined_at or agora  # Fallback caso joined_at seja None
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
