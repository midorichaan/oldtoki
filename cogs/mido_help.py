import discord
from discord.ext import commands

from lib import util, paginator

class mido_help(commands.Cog):
    
    def __init__(self, bot):
        self.bot = bot
        
        if isinstance(bot.get_command("help"), commands.help._HelpCommandImpl):
            self.bot.remove_command("help")
    
    #generate_help
    def generate_help(self, ctx):
        e = discord.Embed(title="Help Menu", description="", color=self.bot.color, timestamp=ctx.message.created_at)
        e.description = """
        HelpMenuはリアクションで進行します。
            
        ⏮ - 最初のに戻る
        ◀ - 前のページに戻る
        ⏹️ - HelpMenuを停止
        ▶ - 次のページへ進む
        ⏭️ - 最後のページに進む
        🔢 - 指定ページに進む
        """
        e.set_footer(text=f"Page 1 / 4")
        
        e1 = discord.Embed(title="Help Menu - Bot Commands", description="", color=self.bot.color, timestamp=ctx.message.created_at)
        cmd = self.bot.cogs["mido_bot"].get_commands()
        cmd.extend(self.bot.cogs["mido_help"].get_commands())
        e1.description = f"".join([f"`{c.name}`, " for c in cmd])
        e1.set_footer(text=f"Page 2 / 4")
        
        e2 = discord.Embed(title="Help Menu - Minecraft Commands", description="", color=self.bot.color, timestamp=ctx.message.created_at)
        cmd = self.bot.cogs["mido_mcids"].get_commands()
        cmd.extend(self.bot.cogs["mido_mcs"].get_commands())
        e2.description = f"".join([f"`{c.name}`, " for c in cmd])
        e2.set_footer(text=f"Page 3 / 4")
        
        e3 = discord.Embed(title="Help Menu - Admin Commands", description="", color=self.bot.color, timestamp=ctx.message.created_at)
        cmd = self.bot.cogs["mido_admins"].get_commands()
        cmd.extend(self.bot.get_command("jishaku"))
        e3.description = f"".join([f"`{c.name}`, " for c in cmd])
        e3.set_footer(text=f"Page 4 / 4")
        
        return [e, e1, e2, e3]

    #help
    @commands.command(name="help", description="ヘルプを表示します", usage="help [command]")
    async def _help(self, ctx, *, command: str=None):
        m = await util.reply_or_send(ctx, content="> 処理中...")
        
        if not command:
            embeds = self.generate_help(ctx)
            page = paginator.EmbedPaginator(ctx, entries=embeds, timeout=30.0)
            await m.delete()
            return await page.paginate()
        else:
            c = self.bot.get_command(command)
            
            if not c:
                embeds = self.generate_help(ctx)
                page = paginator.EmbedPaginator(ctx, entries=embeds, timeout=30.0)
                await m.delete()
                return await page.paginate()
            else:
                e = discord.Embed(title=f"Help - {c.name}", color=self.bot.color, timestamp=ctx.message.created_at)
                e.add_field(name="説明", value=c.description or "なし。")
                e.add_field(name="使用例", value=c.usage or "なし。")
                e.add_field(name="エイリアス", value=", ".join([f"`{row}`" for row in c.aliases]) or "なし。")
                return await m.edit(content=None, embed=e)
        
def setup(bot):
    bot.add_cog(mido_help(bot))
