import discord
import logging
import asyncio
from discord.ext import commands, tasks
from datetime import datetime, time, timezone, timedelta
from bot.servicos.SupporterRoleManager import SupporterRoleManager

logger = logging.getLogger(__name__)

class WeeklyRoleCheck(commands.Cog):
    """Sistema de checagem semanal de cargos de apoiadores"""

    def __init__(self, bot):
        self.bot = bot
        self.role_manager = SupporterRoleManager(bot)
        self.weekly_check.start()

    def cog_unload(self):
        self.weekly_check.cancel()

    @tasks.loop(time=time(hour=9, minute=0, tzinfo=timezone.utc))  # Executa toda segunda-feira às 9:00 UTC
    async def weekly_check(self):
        """Executa checagem semanal de cargos de apoiadores"""
        logger.info("🔄 Iniciando checagem semanal de cargos de apoiadores...")

        total_guilds = 0
        total_processed = 0
        total_updated = 0

        for guild in self.bot.guilds:
            try:
                total_guilds += 1
                result = await self.role_manager.update_all_supporters_roles(guild)

                if "error" not in result:
                    total_processed += result.get("total_processed", 0)
                    total_updated += result.get("updated", 0)
                    logger.info(f"✅ {guild.name}: {result.get('updated', 0)}/{result.get('total_processed', 0)} atualizados")
                else:
                    logger.error(f"❌ Erro em {guild.name}: {result['error']}")

            except Exception as e:
                logger.error(f"Erro ao processar servidor {guild.name}: {e}")
                continue

        logger.info(f"🎯 Checagem semanal concluída: {total_updated}/{total_processed} membros atualizados em {total_guilds} servidores")

    @commands.hybrid_command(name="weekly_check_now", description="[ADMIN] Executa checagem semanal de cargos manualmente")
    @commands.has_permissions(administrator=True)
    async def manual_weekly_check(self, ctx: commands.Context):
        """Executa checagem semanal manualmente (apenas admin)"""
        await ctx.defer(ephemeral=True)

        try:
            embed = discord.Embed(
                title="🔄 Executando Checagem Semanal",
                description="Atualizando cargos de apoiadores...",
                color=discord.Color.blue(),
                timestamp=datetime.now(timezone.utc)
            )
            msg = await ctx.send(embed=embed, ephemeral=True)

            total_guilds = 0
            total_processed = 0
            total_updated = 0
            results = []

            for guild in self.bot.guilds:
                try:
                    total_guilds += 1
                    result = await self.role_manager.update_all_supporters_roles(guild)

                    if "error" not in result:
                        processed = result.get("total_processed", 0)
                        updated = result.get("updated", 0)
                        total_processed += processed
                        total_updated += updated
                        results.append(f"✅ **{guild.name}**: {updated}/{processed} atualizados")
                    else:
                        results.append(f"❌ **{guild.name}**: Erro - {result['error']}")

                except Exception as e:
                    results.append(f"❌ **{guild.name}**: Erro - {str(e)}")
                    continue

            embed.title = "✅ Checagem Semanal Concluída"
            embed.description = f"**Resultados:**\n" + "\n".join(results[:10])  # Limita a 10 resultados
            embed.add_field(
                name="📊 Totais",
                value=f"Servidores: {total_guilds}\nMembros processados: {total_processed}\nCargos atualizados: {total_updated}",
                inline=False
            )

            await msg.edit(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Erro na checagem manual: {str(e)}", ephemeral=True)
            logger.error(f"Erro na checagem manual: {e}")

    @commands.hybrid_command(name="supporter_stats", description="Mostra estatísticas dos apoiadores do servidor")
    async def supporter_stats(self, ctx: commands.Context):
        """Mostra estatísticas dos apoiadores"""
        try:
            stats = await self.role_manager.get_supporter_stats(ctx.guild)

            if "error" in stats:
                await ctx.send(f"❌ Erro ao obter estatísticas: {stats['error']}", ephemeral=True)
                return

            embed = discord.Embed(
                title=f"📊 Estatísticas de Apoiadores - {stats['guild_name']}",
                color=discord.Color.gold(),
                timestamp=datetime.now(timezone.utc)
            )

            embed.add_field(
                name="👥 Total de Apoiadores Ativos",
                value=str(stats['total_supporters']),
                inline=True
            )

            if stats['time_based_roles']:
                time_roles_text = ""
                for days, role_info in sorted(stats['time_based_roles'].items()):
                    time_roles_text += f"**{days} dias+**: {role_info['role_name']} ({role_info['member_count']} membros)\n"

                embed.add_field(
                    name="⏳ Cargos por Tempo de Apoio",
                    value=time_roles_text or "Nenhum configurado",
                    inline=False
                )
            else:
                embed.add_field(
                    name="⏳ Cargos por Tempo de Apoio",
                    value="Nenhum sistema de tempo configurado",
                    inline=False
                )

            await ctx.send(embed=embed, ephemeral=True)

        except Exception as e:
            await ctx.send(f"❌ Erro ao obter estatísticas: {str(e)}", ephemeral=True)
            logger.error(f"Erro nas estatísticas: {e}")

async def setup(bot):
    await bot.add_cog(WeeklyRoleCheck(bot))