import discord
import logging
import os
from discord.ext import commands
from bot.database.models import PixConfig
from bot.database import SessionLocal

logger = logging.getLogger(__name__)

def is_owner():
    async def predicate(ctx):
        dev_id = os.getenv('DEV_ID')
        if not dev_id:
            raise commands.CheckFailure("Variável DEV_ID não configurada")
        return ctx.author.id == int(dev_id)
    return commands.check(predicate)

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @is_owner()
    @commands.hybrid_command(name="set_qrcode", description="[ADMIN] Atualiza a imagem do QR Code PIX")
    async def set_qrcode(self, ctx: commands.Context, image_url: str):
        """Update the static QR code image URL in database"""
        try:
            if not image_url.startswith(('http://', 'https://')):
                raise ValueError("URL deve começar com http:// ou https://")

            with SessionLocal() as session:
                config = session.query(PixConfig).first()
                if not config:
                    config = PixConfig(
                        static_qr_url=image_url,  # Correto: atribuição no construtor
                        chave="hugmebotdev@gmail.com"
                    )
                else:
                    setattr(config, 'static_qr_url', image_url)
                session.add(config)
                session.commit()

            await ctx.send(f"✅ QR Code atualizado para: {image_url}", ephemeral=True)
            logger.info(f"QR Code atualizado por {ctx.author} para {image_url}")
        except Exception as e:
            await ctx.send(f"❌ Erro ao atualizar QR Code: {str(e)}", ephemeral=True)
            logger.error(f"Erro ao atualizar QR Code: {e}")

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))