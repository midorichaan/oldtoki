import discord
from discord.ext import commands

import asyncio
from lib import util

class mido_invite(commands.Cog):
    
    def __init__(self, bot):
        self.bot = bot
        asyncio.gather(self.setup_db())
    
    #setup_db
    async def setup_db(self):
        await self.bot.wait_until_ready()
        tables = [i.values() for i in await self.bot.db.fetchall("SHOW TABLES")]
        
        if not "invites" in tables:
            await self.bot.db.execute("CREATE TABLE IF NOT EXISTS invites(user_id BIGINT, code TEXT, used INT)")
        if not "invitecache" in tables:
            await self.bot.db.execute("CREATE TABLE IF NOT EXISTS invitecache(guild_id BIGINT, code TEXT, used INT)")
    
    #create_invite
    async def create_invite(self, ctx, *, channel=None):
        if ctx.guild.me.guild_permissions.create_instant_invite:
            if channel:
                return await channel.create_invite()
            else:
                return await ctx.guild.system_channel.create_invite()
        else:
            return None
    
    #invite
    @commands.command(name="invite", description="招待を作成します", usage="invite")
    async def invite(self, ctx):
        m = await util.reply_or_send(ctx, content="> 処理中...")
        
        if isinstance(ctx.channel, discord.DMChannel):
            return await m.edit(content="> DMでは使えないよ！")
        
        db = await self.bot.db.fetchone("SELECT * FROM invites WHERE user_id=%s", (ctx.author.id,))
        if db:
            return await m.edit(content=f"> すでに招待URLがあるよ！ \n→ discord.gg/{db['code']} (使用回数: {db['used']})")
        
        await m.edit(content="> 招待URLを作成しますか？")
        try:
            r = await util.wait_for_check(ctx, message=m, timeout=15.0, type="reaction")
        except Exception as exc:
            return await m.edit(content=f"> エラー \n```py\n{exc}\n```")
        else:
            if r == False:
                return await m.edit(content="> キャンセルしたよ！")
                
            invite = await self.create_invite(ctx)
            if not invite:
                return await m.edit(content=f"> コードの作成ができなかったよ...")
        
            await self.bot.db.execute("INSERT INTO invites VALUES(%s, %s, %s)", (ctx.author.id, invite.code, 0))
            return await m.edit(content=f"> 招待URLを作成したよ！ \n→ discord.gg/{invite.code}")
    
    #on_invite_delete
    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        await self.bot.db.execute("DELETE FROM invites WHERE code=%s", (invite.code,))
        await self.bot.db.execute("DELETE FROM invitecache WHERE code=%s", (invite.code,))
    
    #on_invite_create
    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        await self.bot.db.execute("INSERT INTO invitecache VALUES(%s, %s, %s)", (invite.guild.id, invite.code, 0))
    
    #on_member_join
    @commands.Cog.listener()
    async def on_member_join(self, member):
        try:
            invite = await member.guild.invites()
        except Exception as exc:
            e = discord.Embed(title="Exception Info", description=f"```py\n{exc}\n```", color=self.bot.color, timestamp=datetime.datetime.now())
            return await self.bot.get_channel(self.bot.config.LOG_CHANNEL).send(embed=e)
        else:
            db = await self.bot.db.fetchall("SELECT * FROM invitecache")
            d = {}
            for i in db:
                d[i["code"]] = i["used"]
            
            for i in invite:
                if i.uses > d[i.code]:
                    await self.bot.db.execute("UPDATE invites SET used=%s WHERE code=%s", (i.uses, i.code))
                    await self.bot.db.execute("UPDATE invitecache SET used=%s WHERE code=%s", (i.uses, i.code))
                    break
        
def setup(bot):
    bot.add_cog(mido_invite(bot))
