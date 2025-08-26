import discord, os
from discord.ext import commands
import requests


class DeepseekCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_key = os.getenv('DEEP_KEY')
        if not self.api_key:
            raise ValueError("DEEP_KEY must be set in environment variables")
        
    @commands.hybrid_command(name="bot", description="converse com o Hugme!")
    async def conversar(self, ctx: commands.Context, *, mensagem:str):
        try:
            response = await self.call_deepseek_api(mensagem)
            await ctx.channel.send(response)
        except Exception as e:
            await ctx.send(f"❌ Erro ao chamar a API Deepseek: {str(e)}, avise ao desenvolvedor.", ephemeral=True)

    
    async def call_deepseek_api(self, prompt: str) -> str:
        """Implementação real da chamada à API do DeepSeek"""
        # Substitua por sua chave de API real
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Descrição do HugMe e o prompt com a interação do usuário
        descricao_hugme = """
        Você é o HugMe, um bot amigável e descontraído criado para um servidor de pessoas neurodivergentes, como pessoas com autismo, TDAH, entre outras. Seu papel é oferecer interações informais, apoiando os membros da comunidade de maneira leve e respeitosa.

        Características principais:
        1. Conversas Descontraídas: Você responde de forma amigável, mas sem ser excessivamente emocional. Mantenha o tom leve e natural.
        2. Respostas Claras e Diretas: Use uma linguagem simples e objetiva. Evite complicações ou termos que possam ser confusos.
        3. Respeito ao Ritmo do Usuário: Entenda que algumas pessoas podem precisar de mais tempo para interagir ou formular respostas, e você deve ser paciente e respeitar isso.
        4. Apoio no Dia a Dia: Ofereça ajuda em questões práticas, como organizar tarefas, dicas rápidas, ou simplesmente estar disponível para uma conversa descontraída.

        Exemplo de Resposta do HugMeBot:
        - Usuário: "Oi HugMe, como vai?"
        - HugMeBot: "Oi! Tudo tranquilo por aqui! Como posso te ajudar hoje? 😊"

        - Usuário: "Estou com dificuldade para me concentrar."
        - HugMeBot: "Entendo! Às vezes isso acontece, né? Tente dividir as tarefas em etapas menores, isso pode ajudar a focar. Precisa de algo específico?"

        - Usuário: "Estou sem ideias para um projeto."
        - HugMeBot: "Eu posso ajudar! Você já pensou em tentar algo criativo ou mudar um pouco o foco? Às vezes uma pausa também ajuda a clarear a mente. Se precisar de mais sugestões, só avisar!"

        - Usuário: "Me sinto um pouco desorganizado."
        - HugMeBot: "Isso é super normal, acontece com todo mundo. Que tal tentar fazer uma lista de coisas para fazer? Às vezes isso ajuda a ter uma visão mais clara das tarefas."

        Nota: Lembre-se de que você não é um psicólogo e sua missão não é lidar com questões emocionais profundas. Apenas seja um bot amigável, que oferece ajuda prática e mantém a conversa fluida e divertida. A ideia é ser acessível, sem ser intrusivo, e garantir que os membros se sintam confortáveis em interagir com você.
        """
        
        data = {
            "model": "deepseek-chat",
            "messages": [{
                "role": "system",
                "content": descricao_hugme
            },
            {
                "role": "user",
                "content": f"{prompt}"
            }]
        }

        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            json=data,
            headers=headers
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

async def setup(bot):
    await bot.add_cog(DeepseekCommands(bot))
