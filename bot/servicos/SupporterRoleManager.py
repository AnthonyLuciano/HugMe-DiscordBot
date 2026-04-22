import discord
import logging
from datetime import datetime, timedelta, timezone
from bot.database import AsyncSessionLocal
from bot.database.models import Apoiador, GuildConfig
from sqlalchemy import select, func
from typing import Dict, List

logger = logging.getLogger(__name__)

class SupporterRoleManager:
    """Gerencia cargos de apoiadores baseado no tempo de apoio"""

    def __init__(self, bot):
        self.bot = bot

    async def get_guild_config(self, guild_id: str) -> GuildConfig | None:
        """Obtém configuração do servidor"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(GuildConfig).where(GuildConfig.guild_id == guild_id)
            )
            return result.scalars().first()

    async def assign_default_supporter_role(self, member: discord.Member) -> bool:
        """Atribui cargo padrão de apoiador"""
        try:
            config = await self.get_guild_config(str(member.guild.id))
            if not config or not config.cargo_apoiador_default:
                return False

            role = member.guild.get_role(int(config.cargo_apoiador_default))
            if not role:
                logger.error(f"Cargo padrão {config.cargo_apoiador_default} não encontrado")
                return False

            if role not in member.roles:
                await member.add_roles(role)
                logger.info(f"Cargo padrão {role.name} atribuído a {member.display_name}")
                return True

            return True
        except Exception as e:
            logger.error(f"Erro ao atribuir cargo padrão: {e}")
            return False

    async def calculate_total_support_time(self, discord_id: str, guild_id: str) -> int:
        """Calcula tempo total de apoio em dias"""
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(Apoiador).where(
                        Apoiador.discord_id == discord_id,
                        Apoiador.guild_id == guild_id,
                        Apoiador.ativo == True
                    )
                )
                apoiadores = result.scalars().all()

                if not apoiadores:
                    return 0

                total_days = 0
                now = datetime.now(timezone.utc)

                for apo in apoiadores:
                    if apo.data_inicio:
                        # Calcula dias desde o início do apoio
                        days_supported = (now - apo.data_inicio).days
                        total_days += max(0, days_supported)

                return total_days
        except Exception as e:
            logger.error(f"Erro ao calcular tempo de apoio: {e}")
            return 0

    async def get_appropriate_time_role(self, guild: discord.Guild, total_days: int) -> discord.Role | None:
        """Retorna o cargo apropriado baseado no tempo total de apoio"""
        try:
            config = await self.get_guild_config(str(guild.id))
            if not config or not config.cargos_tempo:
                return None

            # Converte total_days para diferentes unidades e encontra o melhor match
            best_role = None
            best_threshold_days = -1

            for time_config in config.cargos_tempo:
                threshold = time_config.get('threshold', 0)
                unit = time_config.get('unit', 'days')
                role_id = time_config.get('role_id')

                # Converte threshold para dias
                threshold_days = self._convert_to_days(threshold, unit)

                # Se o membro qualifica para este threshold E é melhor que o anterior
                if total_days >= threshold_days and threshold_days > best_threshold_days:
                    role = guild.get_role(int(role_id))
                    if role:
                        best_role = role
                        best_threshold_days = threshold_days

            return best_role
        except Exception as e:
            logger.error(f"Erro ao obter cargo de tempo: {e}")
            return None

    def _convert_to_days(self, threshold: int, unit: str) -> int:
        """Converte um threshold para dias baseado na unidade"""
        if unit == 'days' or unit == 'd':
            return threshold
        elif unit == 'weeks' or unit == 'w':
            return threshold * 7
        elif unit == 'months' or unit == 'm':
            return threshold * 30  # Aproximação
        elif unit == 'years' or unit == 'y':
            return threshold * 365  # Aproximação
        else:
            logger.warning(f"Unidade de tempo desconhecida: {unit}, assumindo dias")
            return threshold

    def _format_time_threshold(self, threshold: int, unit: str) -> str:
        """Formata um threshold de tempo para exibição"""
        unit_names = {
            'days': 'dias', 'd': 'dias',
            'weeks': 'semanas', 'w': 'semanas', 
            'months': 'meses', 'm': 'meses',
            'years': 'anos', 'y': 'anos'
        }
        unit_name = unit_names.get(unit, unit)
        return f"{threshold} {unit_name}"

    async def update_member_time_based_roles(self, member: discord.Member) -> bool:
        """Atualiza cargos baseados no tempo de apoio do membro"""
        try:
            total_days = await self.calculate_total_support_time(str(member.id), str(member.guild.id))

            if total_days == 0:
                return False

            # Obtém cargo apropriado para o tempo
            time_role = await self.get_appropriate_time_role(member.guild, total_days)

            if not time_role:
                return False

            # Remove cargos de tempo antigos
            config = await self.get_guild_config(str(member.guild.id))
            if config and config.cargos_tempo:
                old_roles = []
                for time_config in config.cargos_tempo:
                    role_id = time_config.get('role_id')
                    role = member.guild.get_role(int(role_id))
                    if role and role in member.roles and role != time_role:
                        old_roles.append(role)

                if old_roles:
                    await member.remove_roles(*old_roles)
                    logger.info(f"Removidos cargos antigos de {member.display_name}: {[r.name for r in old_roles]}")

            # Atribui novo cargo de tempo se não tiver
            if time_role not in member.roles:
                await member.add_roles(time_role)
                logger.info(f"Cargo de tempo {time_role.name} atribuído a {member.display_name} ({total_days} dias)")
                return True

            return True
        except Exception as e:
            logger.error(f"Erro ao atualizar cargos de tempo: {e}")
            return False

    async def update_all_supporters_roles(self, guild: discord.Guild) -> Dict[str, int]:
        """Atualiza cargos de todos os apoiadores ativos do servidor (execução semanal)"""
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(Apoiador).where(
                        Apoiador.guild_id == str(guild.id),
                        Apoiador.ativo == True
                    )
                )
                apoiadores = result.scalars().all()

            updated_count = 0
            total_processed = 0

            for apo in apoiadores:
                try:
                    member = guild.get_member(int(apo.discord_id))
                    if not member:
                        continue

                    total_processed += 1

                    # Atribui cargo padrão se necessário
                    default_assigned = await self.assign_default_supporter_role(member)

                    # Atualiza cargo baseado no tempo
                    time_updated = await self.update_member_time_based_roles(member)

                    if default_assigned or time_updated:
                        updated_count += 1

                except Exception as e:
                    logger.error(f"Erro ao processar apoiador {apo.discord_id}: {e}")
                    continue

            logger.info(f"Atualização semanal concluída: {updated_count}/{total_processed} membros atualizados em {guild.name}")
            return {
                "total_processed": total_processed,
                "updated": updated_count,
                "guild_name": guild.name
            }

        except Exception as e:
            logger.error(f"Erro na atualização semanal de {guild.name}: {e}")
            return {"error": str(e)}

    async def get_supporter_stats(self, guild: discord.Guild) -> Dict:
        """Retorna estatísticas dos apoiadores do servidor"""
        try:
            async with AsyncSessionLocal() as session:
                # Total de apoiadores ativos
                result = await session.execute(
                    select(func.count(Apoiador.id)).where(
                        Apoiador.guild_id == str(guild.id),
                        Apoiador.ativo == True
                    )
                )
                total_supporters = result.scalar() or 0

                # Estatísticas por tempo
                time_stats = {}
                config = await self.get_guild_config(str(guild.id))

                if config and config.cargos_tempo:
                    for time_config in config.cargos_tempo:
                        role_id = time_config.get('role_id')
                        if role_id:
                            days = time_config.get('threshold', 0)
                            role = guild.get_role(int(role_id))
                            if role:
                                member_count = len([m for m in guild.members if role in m.roles])
                                time_stats[days] = {
                                    "role_name": role.name,
                                    "member_count": member_count
                                }

                return {
                    "total_supporters": total_supporters,
                    "time_based_roles": time_stats,
                    "guild_name": guild.name
                }

        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
            return {"error": str(e)}