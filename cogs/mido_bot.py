import discord
from discord.ext import commands

import platform
import psutil

from lib import util

class mido_bot(commands.Cog):
    
    def __init__(self, bot):
        self.bot = bot
    
    #ping
    @commands.command(name="ping", description="Pingを実行します", usage="ping")
    async def ping(self, ctx):
        st = time.time()
        m = await util.reply_or_send(ctx, content="> pinging...")
        ping = str(round(time.time()-st, 3) * 1000)
        ws = round(self.bot.latency * 1000, 2)
        
        await m.edit(content=f"ぽんぐっ！🏓 \nPing: {ping}ms \nWebSocket: {ws}ms")
        return await msg.edit(embed=e)
    
    #debug
    @commands.command(name="debug", aliases=["dbg"], description="Botのデバッグ情報を表示します。", usage="debug")
    async def debug(self, ctx):
        e = discord.Embed(title="Debug Information", description="処理中...", color=self.bot.color, timestamp=ctx.message.created_at)
        msg = await util.reply_or_send(ctx, embed=e)

        mem = psutil.virtual_memory()
        allmem = str(mem.total/1000000000)[0:3]
        used = str(mem.used/1000000000)[0:3]
        ava = str(mem.available/1000000000)[0:3]
        memparcent = mem.percent
        cpu = psutil.cpu_percent(interval=1)
        core_a = psutil.cpu_count()
        core_b = psutil.cpu_count(logical=False)
        f = 100-memparcent

        dsk = psutil.disk_usage("/")
        d_used = str(dsk.used/100000000)[0:3]
        d_free = str(dsk.free/1000000000)[0:3]

        e.description = None
        e.add_field(name="OS", value=f"{platform.platform(aliased=True)} ({platform.machine()})")
        e.add_field(name="OS Version", value=platform.release())
        e.add_field(name="CPU Information", value=f"Usage: {cpu}% \nCore: {core_a}/{core_b}")
        e.add_field(name="Memory Information", value=f"Total: {allmem}GB \nUsed: {used}GB ({memparcent}%) \nFree: {ava}GB ({f}%)")
        e.add_field(name="Disk Information", value=f"Total: {d_used}GB \nFree: {d_free}GB \nUsage: {dsk.percent}%")
        e.add_field(name="Last Started Date", value=self.bot.uptime.strftime('%Y/%m/%d %H:%M:%S'))
        e.add_field(name="Bot Information", value=f"discord.py v{discord.__version__} \nPython v{platform.python_version()}")

        await msg.edit(embed=e)

def setup(bot):
    bot.add_cog(mido_bot(bot))
