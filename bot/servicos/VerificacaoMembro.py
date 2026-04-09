import discord, logging
from datetime import datetime, timezone
from bot.database import engine, AsyncSessionLocal
from bot.database.models import Apoiador, GuildConfig
from sqlalchemy import select, update

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

        Parâmetros:
            member (discord.Member): O membro do Discord a ser verificado.

        Retorno:
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

        Parâmetros:
            member (discord.Member): O membro do Discord.

        Retorno:
            int: ID do servidor.
        """
        return member.guild.id
    
    async def verificar_tempo_minimo(self, member: discord.Member, tempo_minimo_dias: int) -> bool:
        """Verifica se o membro tem o tempo mínimo necessário no servidor.
        
        Parâmetros:
            member: O membro a verificar
            tempo_minimo_dias: Tempo mínimo em dias
            
        Retorno:
            bool: True se atender ao requisito
        """
        if member.joined_at is None:
            return False

        diferenca = datetime.now(timezone.utc) - member.joined_at
        return diferenca.days >= tempo_minimo_dias
    
    async def obter_apoiador(self, discord_id: str, guild_id: str) -> Apoiador | None:
        """Obtém um apoiador pelo Discord ID e Guild ID"""
        return await self.db.obter_apoiador(discord_id, guild_id)

    async def obter_role_por_nivel(self, guild_id: str, nivel: int) -> int | None:
        """Retorna o role_id configurado para um determinado nível no GuildConfig."""
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(select(GuildConfig).filter_by(guild_id=str(guild_id)))
                cfg = result.scalars().first()
                if not cfg or not cfg.supporter_roles:
                    return None
                key = str(nivel)
                role_id = cfg.supporter_roles.get(key)
                if role_id:
                    try:
                        return int(role_id)
                    except Exception:
                        return None
                return None
        except Exception as e:
            logger.error(f"Erro ao obter role por nível: {e}")
            return None


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

    async def atribuir_cargo_apos_pagamento(self, discord_id: str, guild_id: int, cargo_id: int | None = None, nivel: int | None = None) -> bool:
        try:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                logger.error(f"Servidor {guild_id} não encontrado")
                return False
        
        # Recarregar o servidor para garantir que temos os dados mais recentes
            await guild.chunk()
        
            member = guild.get_member(int(discord_id))
            if not member:
                logger.error(f"Membro {discord_id} não encontrado no servidor {guild_id}")
            # Tentar buscar o membro via API
                try:
                    member = await guild.fetch_member(int(discord_id))
                except discord.NotFound:
                    logger.error(f"Membro {discord_id} realmente não existe no servidor")
                    return False
                except discord.HTTPException as e:
                    logger.error(f"Erro ao buscar membro: {e}")
                    return False  
        # Determinar o cargo a aplicar: prioridade -> nivel (se fornecido) -> cargo_id -> GuildConfig.cargo_apoiador_id
            cargo = None
            chosen_role_id = None

            if nivel is not None:
                chosen_role_id = await self.obter_role_por_nivel(str(guild_id), nivel)

            if chosen_role_id is None and cargo_id is not None:
                chosen_role_id = int(cargo_id)

            if chosen_role_id is None:
                # tentar obter o cargo padrão em GuildConfig
                try:
                    async with AsyncSessionLocal() as session:
                        result = await session.execute(select(GuildConfig).filter_by(guild_id=str(guild_id)))
                        cfg = result.scalars().first()
                        if cfg and cfg.cargo_apoiador_id:
                            try:
                                chosen_role_id = int(cfg.cargo_apoiador_id)
                            except Exception:
                                chosen_role_id = None
                except Exception as e:
                    logger.error(f"Erro ao carregar GuildConfig: {e}")

            if chosen_role_id is None:
                logger.error(f"Nenhum cargo configurado para atribuir no servidor {guild_id}")
                return False

            try:
                cargo = guild.get_role(int(chosen_role_id))
                if not cargo:
                    # Listar todos os cargos para debugging
                    all_roles = [f"{r.name} ({r.id})" for r in guild.roles]
                    logger.info(f"Cargos disponíveis no servidor: {', '.join(all_roles)}")
                    logger.error(f"Cargo ID {chosen_role_id} não encontrado entre {len(guild.roles)} cargos")
                    return False
            except Exception as e:
                logger.error(f"Erro ao buscar cargo: {e}")
                return False
        
        # Verificar permissões do bot
            if not guild.me.guild_permissions.manage_roles:
                logger.error(f"Bot sem permissão para gerenciar cargos no servidor {guild_id}")
                return False
        
            if guild.me.top_role.position <= cargo.position:
                logger.error(f"Cargo do bot ({guild.me.top_role.position}) não é superior ao cargo {cargo.name} ({cargo.position})")
                return False
        
        # Verificar se o membro já tem o cargo
            if cargo in member.roles:
                logger.info(f"Membro {member.display_name} já tem o cargo {cargo.name}")
                return True
        
            await member.add_roles(cargo)
            logger.info(f"Cargo {cargo.name} atribuído para {member.display_name}")
        
        # Atualiza o status no banco de dados
            apoiador = await self.obter_apoiador(discord_id, str(guild_id))
            if apoiador:
                try:
                    async with AsyncSessionLocal() as session:
                        await session.execute(
                            update(Apoiador)
                            .where(Apoiador.discord_id == str(discord_id), Apoiador.guild_id == str(guild_id))
                            .values(cargo_atribuido=True)
                        )
                        await session.commit()
                except Exception as e:
                    logger.error(f"Erro ao atualizar apoiador no DB: {e}")
        
            return True
        
        except discord.Forbidden:
            logger.error(f"Permissão negada para atribuir cargo no servidor {guild_id}")
            return False
        except discord.HTTPException as e:
            logger.error(f"Erro HTTP ao atribuir cargo: {e}")
            return False
        except Exception as e:
            logger.error(f"Erro inesperado ao atribuir cargo: {e}")
            return False