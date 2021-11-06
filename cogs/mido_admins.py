import discord
from discord.ext import commands

import asyncio
import io
import textwrap
import traceback
from contextlib import redirect_stdout
from lib import util

class mido_admins(commands.Cog):
    
    def __init__(self, bot):
        self.bot = bot
        self._ = None
        self.success = "✅"
        self.failed = "❌"
    
    #eval
    @commands.is_owner()
    @commands.command(name="eval", description="[運営用]Pythonのコードを評価します", usage="eval <code>")
    async def _eval(self, ctx, *, code: str=None):
        if not code:
            return await util.reply_or_send(ctx, content="> 評価するコードを入力してね！")
        
        env = {
            'bot': self.bot,
            'ctx': ctx,
            'self': self,
            '_': self._
        }
        
        env.update(globals())
        
        code = util.cleanup_code(code)
        stdout = io.StringIO()

        to_compile = f'async def func():\n{textwrap.indent(code, "  ")}'
        
        try:
            exec(to_compile, env)
        except Exception as exc:
            await ctx.message.add_reaction(self.failed)
            return await util.reply_or_send(ctx, content=f"```py\n{exc.__class__.__name__}: {exc}\n```")
        
        func = env['func']
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as exc:
            await ctx.message.add_reaction(self.failed)
            value = stdout.getvalue()
            return await util.reply_or_send(ctx, content=f'```py\n{value}{traceback.format_exc()}\n```')
        else:
            value = stdout.getvalue()
            await ctx.message.add_reaction(self.success)

            if ret is None:
                if value:
                    await util.reply_or_send(ctx, content=f'```py\n{value}\n```')
            else:
                self._ = ret
                await util.reply_or_send(ctx, content=f'```py\n{value}{ret}\n```')
    
    #shell
    @commands.is_owner()
    @commands.command(name="shell", aliases=["sh"], description="[運営用]シェルコマンドを実行します", usage="shell <command>")
    async def shell(self, ctx, *, command=None):
        if not command:
            await ctx.message.add_reaction(self.failed)
            return await util.reply_or_send(ctx, content="> 実行するコマンドを入力してね！")
       
        stdout, stderr = await util.run_process(ctx, command)
        
        if stderr:
            text = f"```\nstdout: \n{stdout} \n\nstderr: \n{stderr}\n```"
        else:
            text = f"```\nstdout: \n{stdout} \n\nstderr: \nnone\n```"
        
        try:
            await ctx.message.add_reaction(self.success)
            return await util.reply_or_send(ctx, content=text)   
        except Exception as exc:
            await ctx.message.add_reaction(self.failed)
            return await util.reply_or_send(ctx, content=f"```py\n{exc}\n```")
    
    #system
    @commands.group(name="system", description="[運営用]Botのシステムコマンドです", usage="system [args]", invoke_without_command=True)
    @commands.is_owner()
    async def system(self, ctx):
        pass
    
    #help
    @commands.is_owner()
    @system.command(name="help", description="[運営用]ヘルプを表示します。", usage="help [cmd]")
    async def help(self, ctx, cmd=None):
        e = discord.Embed(title="System - system", color=self.bot.color, timestamp=ctx.message.created_at)
        
        if cmd:
            c = self.bot.get_command("system").get_command(cmd)
            
            if c:
                e.title = f"System - {c.name}"
                e.add_field(name="使用例", value=c.usage)
                e.add_field(name="説明", value=c.description)
                e.add_field(name="エイリアス", value=", ".join([f"`{row}`" for row in c.aliases]))
                e.add_field(name="権限", value=c.brief)
               
                try:
                   return await util.reply_or_send(ctx, embed=e)
                except Exception as exc:
                    return await util.reply_or_send(ctx, content=f"> エラー\n```py\n{exc}\n```")
            else:
                for i in self.bot.get_command("system").commands:
                    e.add_field(name=i.usage, value=i.description)
            
                try:
                    return await util.reply_or_send(ctx, embed=e)
                except Exception as exc:
                    return await util.reply_or_send(ctx, content=f"> エラー \n```py\n{exc}\n```")
        else:
            for i in self.bot.get_command("system").commands:
                e.add_field(name=i.usage, value=i.description)
            
            try:
                return await util.reply_or_send(ctx, embed=e)
            except Exception as exc:
                return await util.reply_or_send(ctx, content=f"> エラー \n```py\n{exc}\n```")

    #load
    @commands.is_owner()
    @system.command(name="load", description="[運営用]ファイルをロードします。", usage="load <file>")
    async def load(self, ctx, *, module=None):
        if not module:
            await ctx.message.add_reaction(self.failed)
            return await ctx.send("> 読み込むファイルを指定してね！")

        try:
            self.bot.load_extension(module)
        except Exception as exc:
            await ctx.message.add_reaction(self.failed)
            return await util.reply_or_send(ctx, content=f"> エラー \n```py\n{exc.__class__.__name__}: {exc}\n```")
        else:
            await ctx.message.add_reaction(self.success)
    
    #unload
    @commands.is_owner()
    @system.command(name="unload", description="[運営用]ファイルをunloadします。", usage="unload <file>")
    async def unload(self, ctx, *, module=None):
        if not module:
            await ctx.message.add_reaction(self.failed)
            return await util.reply_or_send(ctx, content="> unloadするファイルを指定してね！")
            
        try:
            self.bot.unload_extension(module)
        except Exception as exc:
            await ctx.message.remove_reaction(self.loading, self.bot.user)
            await ctx.message.add_reaction(self.failed)
            return await util.reply_or_send(ctx, content=f"> エラー \n```py\n{exc.__class__.__name__}: {exc}\n```")
        else:
            await ctx.message.add_reaction(self.success)
    
    #reload
    @commands.is_owner()
    @system.command(name="reload", aliases=["rl"], description="[運営用]ファイルを再読み込みします。", usage="reload <file>")
    async def reload(self, ctx, *, module=None):
        if not module:
            cogs = self.bot._ext
            excs = ""
            
            for cog in cogs:
                try:
                    self.bot.reload_extension(cog)
                except Exception as exc:
                    excs += f"{cog} → {exc}\n"

            await ctx.message.add_reaction(self.success)
            
            if execs != "":
                await util.reply_or_send(ctx, content=f"> Failed to reload(s) \n```\n{excs}\n```")
            return
        else:
            try:
                self.bot.reload_extension(module)
            except Exception as exc:
                await ctx.message.add_reaction(self.failed)
                return await util.reply_or_send(ctx, content=f"> エラー \n```py\n{exc.__class__.__name__}: {exc}\n```")
            else:
                await ctx.message.add_reaction(self.success)
    
    #restart
    @commands.is_owner()
    @system.command(name="restart", aliases=["reboot"], description="[運営用]Botを再起動します。", usage="restart")
    async def reboot(self, ctx):
        await util.reply_or_send(ctx, content="> Botを再起動します...しばらくお待ちください...")
        await self.bot.change_presence(activity=discord.Game(name=f'disabling tokibot... Please Wait...'))
        await asyncio.sleep(3)
        await self.bot.close()
    
    #toggle
    @commands.is_owner()
    @system.command(name="toggle", description="[運営用]指定コマンドの有効/無効を切り替えます。", usage="toggle <command>")
    async def toggle(self, ctx, command=None):
        if not command:
            await ctx.message.add_reaction(self.failed)
            return await util.reply_or_send(ctx, content="> コマンドを入力してね！")
        
        cmd = self.bot.get_command(command)
        if not cmd:
            await ctx.message.add_reaction(self.failed)
            return await util.reply_or_send(ctx, content="> そのコマンドは存在しないよ！")
        
        if cmd.enabled:
            cmd.enabled = False
        else:
            cmd.enabled = True
        await ctx.message.add_reaction(self.success)
    
    #get_log
    @commands.is_owner()
    @system.command(name="get_log", description="[運営用]エラーログを取得します", usage="get_log <error_id>")
    async def get_log(self, ctx, exc_id: int=None):
        if not exc_id:
            await ctx.message.add_reaction(self.failed)
            return await util.reply_or_send(ctx, content="> IDを入力してね！")
        
        try:
            log = await self.bot.get_channel(self.bot.config.LOG_CHANNEL).fetch_message(exc_id)
        except Exception as exc:
            await util.reply_or_send(ctx, content=f"```py\n{exc}\n```")
            return await ctx.message.add_reaction(self.failed)
        else:
            await ctx.message.add_reaction(self.success)
            await util.reply_or_send(ctx, embed=log.embeds[0])

def setup(bot):
    bot.add_cog(mido_admins(bot))
