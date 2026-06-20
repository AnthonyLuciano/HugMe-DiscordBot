import os
import discord

from sqlalchemy import select

from bot.database import AsyncSessionLocal
from bot.database.models import GuildConfig


def check_is_owner(ctx_or_interaction) -> bool:
    """Verifica se o usuário é owner - funciona com Context ou Interaction"""
    mod_id = os.getenv('TRUSTED_MOD_ID')
    dev_id = os.getenv('DEV_ID')

    if hasattr(ctx_or_interaction, 'user'):
        user_id = ctx_or_interaction.user.id
    elif hasattr(ctx_or_interaction, 'author'):
        user_id = ctx_or_interaction.author.id
    else:
        return False

    allowed_ids = []
    if dev_id:
        allowed_ids.append(int(dev_id))
    if mod_id:
        allowed_ids.append(int(mod_id))
    return user_id in allowed_ids


def _build_role_config_embed(guild: discord.Guild, config) -> discord.Embed:
    """Constrói o embed de configuração de cargos (reutilizável)."""
    embed = discord.Embed(
        title="⭐ Configuração de Cargos de Apoiador",
        color=discord.Color.gold(),
        description=f"Configurações para **{guild.name}**"
    )

    if not config:
        embed.add_field(
            name="⚠️ Nenhuma Configuração",
            value="Nenhum cargo de apoiador configurado ainda.\nUse os botões abaixo para configurar.",
            inline=False
        )
        return embed

    if config.cargo_apoiador_default:
        role = guild.get_role(int(config.cargo_apoiador_default))
        value = role.mention if role else f"ID: {config.cargo_apoiador_default} (cargo não encontrado)"
        embed.add_field(
            name="⭐ Cargo Padrão",
            value=f"{value}\n*Atribuído automaticamente a todos os apoiadores*",
            inline=False
        )
    else:
        embed.add_field(name="⭐ Cargo Padrão", value="Não configurado", inline=False)

    if config.cargos_tempo and isinstance(config.cargos_tempo, list):
        unit_map = {"days": "dias", "months": "meses", "years": "anos"}
        time_roles = []
        for item in sorted(config.cargos_tempo, key=lambda x: (x.get('unit', 'days'), x.get('threshold', 0))):
            threshold = item.get('threshold', 0)
            unit = item.get('unit', 'days')
            role_id = item.get('role_id')
            role = guild.get_role(int(role_id)) if role_id else None
            role_name = role.mention if role else f"ID: {role_id}"
            time_roles.append(f"**{threshold} {unit_map.get(unit, unit)}+**: {role_name}")

        embed.add_field(
            name="⏳ Cargos por Tempo de Apoio",
            value="\n".join(time_roles) if time_roles else "Nenhum configurado",
            inline=False
        )
    else:
        embed.add_field(name="⏳ Cargos por Tempo de Apoio", value="Nenhum configurado", inline=False)

    return embed
