import discord
from discord.ext import commands

class CheckCommands(commands.Cog):
    """Comandos básicos do bot."""

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name='check', description="Verifica se o bot está online")
    async def check(self, ctx: commands.Context):
        """Responde com 'bot esta online! pronto para ajudar :D'."""
        await ctx.defer()  # Garante os 15 min de janela para responder
        await ctx.send('Bot está online! Pronto para ajudar :D')

    @commands.hybrid_command(name='ajuda', description="Mostra os comandos disponíveis")
    async def help(self, ctx: commands.Context):
        """Mostra uma lista de comandos disponíveis."""
        await ctx.defer()  # Idem

        embed = discord.Embed(
            title="📚 Comandos do Bot",
            description="Aqui estão todos os comandos disponíveis:",
            color=discord.Color.blue()
        )

        for cog_name, cog in self.bot.cogs.items():
            cog_commands = []
            for command in cog.get_commands():
                if not command.hidden:
                    cog_commands.append(f"`/{command.name}` - {command.description or 'Sem descrição'}")
            if cog_commands:
                embed.add_field(
                    name=f"🔧 {cog_name}",
                    value="\n".join(cog_commands),
                    inline=False
                )

        uncategorized_commands = []
        for command in self.bot.commands:
            if not command.cog and not command.hidden:
                uncategorized_commands.append(f"`/{command.name}` - {command.description or 'Sem descrição'}")
        if uncategorized_commands:
            embed.add_field(
                name="🔧 Comandos Gerais",
                value="\n".join(uncategorized_commands),
                inline=False
            )

        await ctx.send(embed=embed)

    @commands.hybrid_command(name='check_commands', description="Verifica integridade de todos os comandos do bot")
    async def check_commands(self, ctx: commands.Context):
        """Gera um relatório de integridade dos comandos registrados."""
        await ctx.defer(ephemeral=True)

        total_commands = len(self.bot.commands)
        tree_commands = {cmd.name for cmd in self.bot.tree.get_commands()}
        problems = []
        duplicate_names = []
        seen_names = {}

        for command in self.bot.commands:
            if command.name in seen_names:
                duplicate_names.append(command.name)
            else:
                seen_names[command.name] = command

            if command.callback is None:
                problems.append(f"`{command.name}` não tem callback definido")

            if not command.enabled:
                problems.append(f"`{command.name}` está desabilitado")

            if isinstance(command, commands.HybridCommand) and command.name not in tree_commands:
                problems.append(f"`{command.name}` parece ser híbrido, mas não está no tree de comandos slash")

            if isinstance(command, commands.Group) and not command.commands:
                problems.append(f"`{command.name}` é um grupo sem subcomandos")

            try:
                await command.can_run(ctx)
            except commands.CommandError as error:
                problems.append(f"`{command.name}` falha em can_run(): {type(error).__name__}")
            except Exception as error:
                problems.append(f"`{command.name}` falha em can_run(): {type(error).__name__} - {str(error)}")

        if duplicate_names:
            problems.append(f"Nomes de comando duplicados: {', '.join(sorted(set(duplicate_names)))}")

        embed = discord.Embed(
            title="🛠️ Verificação de Integridade dos Comandos",
            color=discord.Color.gold(),
            description=(
                f"Total de comandos registrados: **{total_commands}**\n"
                f"Comandos slash no tree: **{len(tree_commands)}**\n"
                f"Problemas detectados: **{len(problems)}**"
            )
        )

        if problems:
            report = "\n".join(problems[:8])
            if len(problems) > 8:
                report += f"\n... e mais {len(problems) - 8} itens."
            embed.add_field(name="⚠️ Problemas encontrados", value=report, inline=False)
        else:
            embed.add_field(
                name="✅ Integridade OK",
                value="Todos os comandos registrados passaram na verificação básica.",
                inline=False
            )

        await ctx.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(CheckCommands(bot))