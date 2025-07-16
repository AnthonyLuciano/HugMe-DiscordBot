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
    
    async def aplicar_cargo_se_qualificado(self, member: discord.Member, cargo_id: int, tempo_minimo_dias: int) -> str:
        """Tenta aplicar um cargo se o membro atender ao tempo mínimo.
        
        Args:
            member: Membro a verificar
            cargo_id: ID do cargo a aplicar
            tempo_minimo_dias: Tempo mínimo em dias
            
        Returns:
            str: Mensagem com o resultado
        """
        cargo = member.guild.get_role(cargo_id)
        if not cargo:
            return "Cargo não encontrado!"
        #^^pegador de excessoes    
        if await self.verificar_tempo_minimo(member, tempo_minimo_dias):
            await member.add_roles(cargo)
            return f"Cargo {cargo.name} aplicado com sucesso!"
        #^^adiciona cargo quando verificado
        else:
            tempo_atual = await self.tempo_servidor(member)
            return f"Você precisa de {tempo_minimo_dias} dias no servidor (atual: {tempo_atual})"
        #^^se nao poder ser verificado, avisa quando pode