import discord
from discord.ext import commands

import asyncio
import datetime
import random
import string
from lib import util

class mido_srv(commands.Cog):
    
    def __init__(self, bot):
        self.bot = bot
        self.guild = self.bot.get_guild(891255334109323275)
        self.verify_role = self.guild.get_role(907664018444001340)
        
        self.verify_key_log_id = 907640515200163870
        
        asyncio.gather(self.setup_db())
    
    #setup_db
    async def setup_db(self):
        await self.bot.wait_until_ready()
        tables = [i.values() for i in await self.bot.db.fetchall("SHOW TABLES")]
        
        if not "verifyqueue" in tables:
            await self.bot.db.execute("CREATE TABLE IF NOT EXISTS verifyqueue(user_id BIGINT, verifykey TEXT)")
    
    #generate_verifykey
    def generate_verifykey(self, length: int, type: str="string"):
        if type == "string":
            return "".join(random.choices(string.ascii_letters, k=length))
        elif type == "code":
            return "".join(random.choices(string.digits, k=length))
        else:
            return "".join(random.choices(string.ascii_letters + string.digits, k=length))
    
    #check verifykey
    async def check_verifykey(self, key: str):
        db = await self.bot.db.fetchone("SELECT * FROM verifyqueue WHERE verifykey=%s", (key,))
        
        if db:
            return False
        return True
    
    #get_verify_key
    async def get_verify_key(self):
        while True:
            key = self.generate_verifykey(4, "string")
            ret = await self.check_verifykey(key)
            
            if ret:
                break
    
    #on_member_join
    @commands.Cog.listener()
    async def on_member_join(self, member):
        try:
            key = await self.get_verify_key()
        except Exception as exc:
            e = discord.Embed(title="Exception Info", description=f"```py{exc}\n```", color=self.bot.color, timestamp=datetime.datetime.now())
            return await self.bot.get_channel(self.bot.config.LOG_CHANNEL).send(embed=e)
        else:
            await self.bot.db.execute("INSERT INTO verifyqueue VALUES(%s, %s)", (member.id, str(key)))
            await self.bot.get_channel(self.verify_key_log_id).send(f"> {member} ({member.id})の認証コード \n**{key}**")
    
    #on_message
    @commands.Cog.listener()
    async def on_message(self, msg):
        if isinstance(msg.channel, discord.DMChannel):
            if msg.author.id == self.bot.user.id:
                return
            
            db = await self.bot.db.fetchone("SELECT * FROM verifyqueue WHERE user_id=%s", (msg.author.id,))
            if not db:
                return
            
            config = await self.bot.db.fetchone("SELECT * FROM config WHERE guild_id=891255334109323275")
            ctx = await self.bot.get_context(msg)
            if secrets.compare_digest(str(db["verifykey"]), msg.content):
                await util.reply_or_send(ctx, content=config["verify_message"] or "認証に成功しました！")
                await guild.get_member(msg.author.id).add_roles(self.verify_role, reason="complete verification")
                return await self.bot.db.execute("DELETE FROM verifyqueue WHERE user_id=%s", (msg.author.id,))
            else:
                return await util.reply_or_send(ctx, content=config["verify_failed_message"] or "認証に失敗しました")
    
    #on_member_remove
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        db = await self.bot.db.fetchone("SELECT * FROM verifyqueue WHERE user_id=%s", (member.id,))
        
        if db:
            await self.bot.db.execute("DELETE FROM verifyqueue WHERE user_id=%s", (member.id,))
    
def setup(bot):
    bot.add_cog(mido_srv(bot))
