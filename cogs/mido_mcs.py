import discord
from discord.ext import commands

from lib import util

class mido_mcs(commands.Cog):
    
    def __init__(self, bot):
        self.bot = bot
    
    #reward
    @commands.command(name="reward", aliases=["rewards"], description="ログイン報酬を受け取ります(MCID登録必須)", usage="reward")
    async def reward(self, ctx):
        m = await util.reply_or_send(ctx, content="> 処理中...")
        
        db = await self.bot.db.fetchone("SELECT * FROM mcids WHERE user_id=%s", (ctx.author.id,))
        if not db:
            return await m.edit(content="> MCIDが登録されていないよ！")
        
        return await m.edit(content="> 準備ちう...><")
        
def setup(bot):
    bot.add_cog(mido_mcs(bot))
