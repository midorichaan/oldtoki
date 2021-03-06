import discord
from discord.ext import commands

import asyncio

from lib import util

class mido_mcids(commands.Cog):
    
    def __init__(self, bot):
        self.bot = bot
        asyncio.gather(self.setup_db())
    
    async def setup_db(self):
        await self.bot.wait_until_ready()
        tables = [i.values() for i in await self.bot.db.fetchall("SHOW TABLES")]
        
        if not "mcids" in tables:
            await self.bot.db.execute("CREATE TABLE IF NOT EXISTS mcids(user_id BIGINT, mcid TEXT, uuid TEXT)")

    #mcid
    @commands.command(name="mcid", description="MCIDとDiscordを紐づけます", usage="mcid <mcid>")
    async def mcid(self, ctx, mcid: str=None):
        m = await util.reply_or_send(ctx, content="> 処理中...")
        
        if not mcid:
            return await m.edit(content="> MCIDを入力してね！")
        
        d = await self.bot.db.fetchone("SELECT * FROM mcids WHERE user_id=%s", (ctx.author.id,))
        if d:
            try:
                data = await util.resolve_mcid(ctx, mcid=mcid)
            except Exception as exc:
                return await m.edit(content=f"> エラー \n```py\n{exc}\n```")
            else:
                await self.bot.db.execute("UPDATE mcids SET mcid=%s, uuid=%s WHERE user_id=%s", (data["name"], data["id"], ctx.author.id))
                return await m.edit(content=f"> あなたのMCIDを`{mcid}`で再登録したよ！")
        else:
            try:
                data = await util.resolve_mcid(ctx, mcid=mcid)
            except Exception as exc:
                return await m.edit(content=f"> エラー \n```py\n{exc}\n```")
            else:
                await self.bot.db.execute("INSERT INTO mcids VALUES(%s, %s, %s)", (ctx.author.id, data["name"], data["id"]))
                return await m.edit(content=f"> あなたのMCIDを`{mcid}`で登録したよ！")
    
    #show
    @commands.command(name="show", description="登録しているMCIDを表示します", usage="show [Member/User]")
    async def show(self, ctx, target: util.MemberConverter=None):
        m = await util.reply_or_send(ctx, content="> 処理中...")
        
        if not target:
            target = ctx.author
        
        db = await self.bot.db.fetchone("SELECT * FROM mcids WHERE user_id=%s", (target.id,))
        if not db:
            return await m.edit(content=f"> {target}のMCIDは登録されてないよ！")
        else:
            return await m.edit(content=f"> {target} のMCID登録情報 \nMCID: {db['mcid']} \nUUID: {db['uuid']}")

def setup(bot):
    bot.add_cog(mido_mcids(bot))
