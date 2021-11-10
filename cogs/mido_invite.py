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
            await self.bot.db.execute("CREATE TABBLE IF NOT EXISTS invitecache(guild_id BIGINT, code TEXT, used INT)")
    
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
        
        invite = await self.create_invite()
        if not invite:
            return await m.edit(content=f"> コードの作成ができなかったよ...")
        
        await self.bot.db.execute("INSERT INTO invites VALUES(%s, %s, %s)", (ctx.author.id, invite.code, 0))
        return await m.edit(content=f"> 招待URLを作成したよ！ \n→ discord.gg/{invite.code}")
    
    #on_invite_delete
    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        db = await self.bot.db.fetchone("SELECT * FROM invites WHERE code=%s", (invite.code,))
        cache = await self.bot.db.fetchone("SELECT * FROM invitecache WHERE code=%s", (invite.code,))
        
        if db:
            await self.bot.db.execute("DELETE FROM invites WHERE code=%s", (invite.code,))
        
        if cache:
            await self.bot.db.execute("DELETE FROM invitecache WHERE code=%s", (invite.code,))
    
    #on_invite_create
    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        await self.bot.db.execute("INSERT INTO invitecache VALUES(%s, %s, %s)", (invite.guild.id, invite.code, 0))
        
def setup(bot):
    bot.add_cog(mido_invite(bot))
