import discord
import logging
import os
from discord.ext import commands
from bot.database.models import PixConfig
from bot.database import SessionLocal

logger = logging.getLogger(__name__)

def is_owner():
    async def predicate(ctx):
        mod_id = os.getenv('TRUSTED_MOD_ID')
        dev_id = os.getenv('DEV_ID')
        if not dev_id:
            if not mod_id:
                raise ValueError("Both DEV_ID and MOD_ID must be set in environment variables")
        return ctx.author.id == int(dev_id) or ctx.author.id == int(mod_id)
    return commands.check(predicate)

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @is_owner()
    @commands.hybrid_command(name="set_qrcode", description="[ADMIN] Atualiza a imagem do QR Code PIX e chave estática")
    async def set_qrcode(self, ctx: commands.Context, image_url: str, chave: str = None, nome_titular: str = "HugMe Bot", cidade: str = "São Paulo"):
        """Update the static QR code image URL and PIX key in database"""
        try:
            if not image_url.startswith(('http://', 'https://')):
                raise ValueError("URL deve começar com http:// ou https://")

            with SessionLocal() as session:
                config = session.query(PixConfig).first()
                if not config:
                    config = PixConfig(
                        static_qr_url=image_url,
                        chave=chave if chave else "hugmebotdev@gmail.com",
                        nome_titular=nome_titular,
                        cidade=cidade,
                        atualizado_por=str(ctx.author.id)
                    )
                else:
                    config.static_qr_url = image_url
                    if chave:
                        config.chave = chave
                    config.nome_titular = nome_titular
                    config.cidade = cidade
                    config.atualizado_por = str(ctx.author.id)
                
                session.add(config)
                session.commit()

            await ctx.send(f"✅ QR Code atualizado para: {image_url}" + 
                         (f" e chave PIX para: {chave}" if chave else ""), 
                         ephemeral=True)
            logger.info(f"QR Code atualizado por {ctx.author} para {image_url}" + 
                       (f" e chave PIX para: {chave}" if chave else ""))
        except Exception as e:
            await ctx.send(f"❌ Erro ao atualizar QR Code: {str(e)}", ephemeral=True)
            logger.error(f"Erro ao atualizar QR Code: {e}")

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))