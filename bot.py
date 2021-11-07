import discord
from discord.ext import commands

import aiohttp
import config
import datetime
import logging
import traceback
from lib import util, database

bot = commands.Bot(command_prefix=config.PREFIX, intents=discord.Intents.all(), status=discord.Status.idle)

bot.config = __import__("config")
bot.color = config.COLOR
bot.db = database.Database()
bot._ext = ["cogs.mido_admins", "jishaku"]
bot.session = aiohttp.ClientSession()
bot.uptime = datetime.datetime.now()
bot.logger = logging.getLogger("discord")
logging.basicConfig(level=logging.WARNING, format="[DebugLog] %(levelname)-8s: %(message)s")
bot._default_close = bot.close

#close_handler
async def close_handler():
    try:
        await bot.session.close()
        print("[System] HTTPSession closed")
    except:
        pass
    
    await bot.change_presence(activity=None, status=discord.Status.offline)
    await bot._default_close()
    
bot.close = close_handler

#on_ready
@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="enabling... please wait..."))
    print("[System] Startup...")
    
    for name in bot._ext:
        try:
            bot.load_extension(name)
        except Exception as exc:
            print(f"[System] {name} load failed → {exc}")
        else:
            print(f"[System] {name} load")
    
    await bot.change_presence(activity=discord.Game(name="Toki DiscordServer Bot | ©Midorichan"))
    print("[System] on_ready!")

#command_log
@bot.event
async def on_command(ctx):
    if isinstance(ctx.channel, discord.DMChannel):
        print(f"[Log] {ctx.author} ({ctx.author.id}) → {ctx.message.content} @DM")
    else:
        print(f"[Log] {ctx.author} ({ctx.author.id}) → {ctx.message.content} @{ctx.guild} ({ctx.guild.id}) - {ctx.channel} ({ctx.channel.id})")
    
#error_handler
@bot.event
async def on_command_error(ctx, exc):
    traceback_error = f"```{''.join(traceback.TracebackException.from_exception(exc).format())}```"
    if len(str(traceback_error)) >= 1024:
        error = f"```py\n{exc}\n```"
    else:
        error = traceback_error
    
    e = discord.Embed(title="Exception Info", description=error, color=bot.color, timestamp=ctx.message.created_at)
    e.set_author(name=f"{ctx.author} ({ctx.author.id})", icon_url=ctx.author.avatar_url_as(static_format="png"))
    
    if isinstance(ctx.channel, discord.DMChannel):
        e.set_footer(text=f"@{ctx.author} ({ctx.author.id})")
        print(f"[Error] {ctx.author} ({ctx.author.id}) -> {exc} @DM")
    else:
        e.set_footer(text=f"{ctx.guild} ({ctx.guild.id}) - {ctx.channel} ({ctx.channel.id})", icon_url=ctx.guild.icon_url_as(static_format="png"))
        print(f"[Error] {ctx.guild.name} ({ctx.guild.id}) -> {exc} @{ctx.channel} ({ctx.channel.id})")
    
    msg = await bot.get_channel(config.LOG_CHANNEL).send(embed=e)
    
    if isinstance(exc, commands.NotOwner):
        await util.reply_or_send(ctx, content=f"このコマンドは使えないよ！ \nエラーID: {msg.id}")
    elif isinstance(exc, commands.CommandNotFound):
        await util.reply_or_send(ctx, content=f"そのコマンドは存在しないよ！ \nエラーID: {msg.id}")
    elif isinstance(exc, commands.DisabledCommand):
        await util.reply_or_send(ctx, content=f"このコマンドは使えないよ！ \nエラーID: {msg.id}")
    elif isinstance(exc, commands.CheckFailure):
        await util.reply_or_send(ctx, content=f"このコマンドは使えないよ！ \nエラーID: {msg.id}")
    else:
        await util.reply_or_send(ctx, content=f"エラーが発生したよ！運営さんに報告してね！ \nエラーID: {msg.id}")

print(f"[System] enabling toki server bot")
bot.run(config.BOT_TOKEN)
