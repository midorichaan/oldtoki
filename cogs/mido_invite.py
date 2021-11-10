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
    
    

def setup(bot):
    bot.add_cog(mido_invite(bot))
