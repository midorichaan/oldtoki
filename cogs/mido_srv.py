import discord
from discord.ext import commands

from lib import util

class mido_srv(commands.Cog):
    
    def __init__(self, bot):
        self.bot = bot
    
def setup(bot):
    bot.add_cog(mido_srv(bot))
