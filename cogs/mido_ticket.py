import discord
from discord.ext import commands

import asyncio
import json
import os

from lib import util

class ticket_log():
    
    def __init__(self, msg):
        self.author_id = msg.author.id
        self.message_id = msg.id
        self.channel_id = msg.channel.id
        self.message_content = msg.content
        self.created_at = msg.created_at
        self.embeds = [e.to_dict() for e in msg.embeds if msg.embeds]
        self.attachments = [a.proxy_url for a in msg.attachments if msg.attachments]
        self.message_raw = msg

class mido_ticket(commands.Cog):
    
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        
        if hasattr(bot, "ticket_log") and isinstance(bot.ticket_log, dict):
            self.ticket_log = bot.ticket_log
        else:
            bot.ticket_log = dict()
            self.ticket_log = bot.ticket_log
        
        asyncio.gather(self.db.execute("CREATE TABLE IF NOT EXISTS ticket_config(guild BIGINT PRIMARY KEY NOT NULL, category BIGINT, mention INTEGER, role BIGINT, deleteafter INTEGER, moveclosed INTEGER, movecat BIGINT, log BIGINT)"))
        asyncio.gather(self.db.execute("CREATE TABLE IF NOT EXISTS tickets(id BIGINT PRIMARY KEY NOT NULL, panel BIGINT, author BIGINT, category BIGINT, status INTEGER)"))
        asyncio.gather(self.db.execute("CREATE TABLE IF NOT EXISTS ticket_panel(id BIGINT PRIMARY KEY NOT NULL, channel BIGINT, guild BIGINT)"))
        asyncio.gather(self.db.execute("CREATE TABLE IF NOT EXISTS ticket_log(id BIGINT PRIMARY KEY NOT NULL, channel BIGINT, author BIGINT, content TEXT)"))
    
    #create_ticket
    async def create_ticket(self, guild, member, *, reason, config=None):
        if config is None:
            config = await self.db.fetchone("SELECT * FROM ticket_config WHERE guild=%s", (guild.id,))

        chs = [c for c in guild.channels if str(member.id) in str(c.name)]

        ch = await guild.get_channel(config["category"]).create_text_channel(name=f"ticket-{member.id}-{len(chs)+1}")

        overwrite = discord.PermissionOverwrite()
        overwrite.send_messages = True
        overwrite.read_messages = True
        overwrite.add_reactions = True
        overwrite.embed_links = True
        overwrite.read_message_history = True
        overwrite.external_emojis = True
        overwrite.attach_files = True

        await ch.set_permissions(member, overwrite=overwrite)
        panel = await self.create_panel(guild, member, ch, reason=reason)
        await ch.send(f"> お問い合わせ内容を送信してください。")

        return ch, panel
    
    #create panel
    async def create_panel(self, guild, author, channel, *, reason):
        e = discord.Embed(title=f"Support Ticket - {author}", color=self.bot.color)
        e.add_field(name="チケット作成理由 / Reason", value=f"```\n{reason}\n```", inline=False)
        e.add_field(name="ステータス / Ticket Status", value="```\nwait for reason\n```", inline=False)
        
        db = await self.db.fetchone("SELECT * FROM ticket_config WHERE guild=%s", (guild.id,))
        
        if db and db["mention"] == 1:
            msg = await channel.send(content=f"{guild.get_role(db['role']).mention} {author.mention} →", embed=e)
        else:
            msg = await channel.send(content=f"{author.mention} →", embed=e)
        
        await msg.pin()
        await self.db.execute(f"INSERT INTO tickets VALUES(%s, %s, %s, %s, %s)", (channel.id, msg.id, author.id, channel.category.id, 2))
        await msg.add_reaction("🔐")
        
        return msg
    
    #log_ticket
    async def log_ticket(self, msg):
        if not os.path.exists(f"./logs/ticket-{msg.channel.id}.json"):
            with open(f"./logs/ticket-{msg.channel.id}.json", "x", encoding="utf-8") as f:
                json.dump({}, f)
            
            with open(f"./logs/ticket-{msg.channel.id}.json", "r", encoding="utf-8") as f:
                file = json.load(f)
                
                if msg.content:
                    await self.db.execute(f"INSERT INTO ticket_log VALUES(%s, %s, %s, %s)", (int(msg.id), int(msg.channel.id), int(msg.author.id), str(msg.content)))
                    self.ticket_log[msg.id] = ticket_log(msg)
                    
                    file[msg.id] = {
                        "message_id":msg.id, 
                        "channel_id":msg.channel.id, 
                        "author_id":msg.author.id, 
                        "embeds":[e.to_dict() for e in msg.embeds if msg.embeds],
                        "attachments":[a.proxy_url for a in msg.attachments if msg.attachments],
                        "content":msg.content,
                        "created_at":str(msg.created_at)
                    }
                    
                else:
                    await self.db.execute(f"INSERT INTO ticket_log VALUES(%s, %s, %s, %s)", (int(msg.id), int(msg.channel.id), int(msg.author.id), None))
                    self.ticket_log[msg.id] = ticket_log(msg)
                    
                    file[msg.id] = {
                        "message_id":msg.id, 
                        "channel_id":msg.channel.id, 
                        "author_id":msg.author.id, 
                        "embeds":[e.to_dict() for e in msg.embeds if msg.embeds],
                        "attachments":[a.proxy_url for a in msg.attachments if msg.attachments],
                        "content":msg.content,
                        "created_at":str(msg.created_at)
                    }
                
                with open(f"./logs/ticket-{msg.channel.id}.json", "w", encoding="utf-8") as f:
                    json.dump(file, f, indent=4)
                    
    
    #on_msg log
    @commands.Cog.listener()
    async def on_message(self, msg):
        if isinstance(msg.channel, discord.DMChannel):
            return                    
                                
        db = await self.db.fetchone("SELECT * FROM tickets WHERE id=%s", (msg.channel.id,))
        if not db:
            return
        
        if db["status"] == 1:
            try:
                await self.log_ticket(msg)
            except Exception as exc:
                await self.bot.get_user(546682137240403984).send(f"> Ticket Log Exc \n```py\n{exc}\n```")
        
        if db["status"] == 2:
            if not msg.author.id == db["author"]:
                return

            panel = await msg.channel.fetch_message(db["panel"])
            embed = panel.embeds[0]
            embed.set_field_at(0, name="チケット作成理由 / Reason", value=f"```\n{msg.content}\n```", inline=False)
            embed.set_field_at(1, name="ステータス / Ticket Status", value="```\nOpen\n```", inline=False)
            await panel.edit(embed=embed)
            await self.db.execute("UPDATE tickets SET status=1 WHERE id=%s", (msg.channel.id,))
                                
    #detect reaction
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        db = await self.db.fetchone("SELECT * FROM tickets WHERE panel=%s", (payload.message_id,))
        panel = await self.db.fetchone("SELECT * FROM ticket_panel WHERE id=%s", (payload.message_id,))
        config = await self.db.fetchone("SELECT * FROM ticket_config WHERE guild=%s", (payload.guild_id,))

        if db and str(payload.event_type) == "REACTION_ADD" and payload.user_id != self.bot.user.id and str(payload.emoji) == "🔐":
            try:
                msg = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
                await msg.remove_reaction("🔐", payload.member)
            except:
                pass

            if db["status"] == 0:
                return

            if not (db["author"] == payload.member.id or payload.member.id in [m.id for m in self.bot.get_guild(payload.guild_id).get_role(config["role"]).members]):
                return

            ch = self.bot.get_channel(payload.channel_id)

            check = await ch.send("> Closeしますか？ (open/close)")

            wait = await self.bot.wait_for("message", check=lambda m: m.author.id == payload.user_id and m.channel.id == payload.channel_id)

            if str(wait.content) != "close":
                await check.edit(content=f"> キャンセルしました！")
                return
            else:
                overwrite = discord.PermissionOverwrite()
                overwrite.send_messages = False
                overwrite.add_reactions = False
                overwrite.external_emojis = False

                await self.db.execute("UPDATE tickets SET status=%s WHERE panel=%s", (0, payload.message_id))
                await ch.edit(name=ch.name.replace("ticket", "close"))
                await ch.set_permissions(self.bot.get_guild(payload.guild_id).get_member(db["author"]), overwrite=overwrite)
                await ch.send("> サポートチケットをcloseしました！")
                await ch.send(content="> Support Ticket Logs (json)", file=discord.File(f"./logs/ticket-{ch.id}.json"))

                if config["log"]:
                    embed = discord.Embed(title=f"Ticket Logs {self.bot.get_user(db['author'])} ({db['author']})", color=self.bot.color)

                    await self.bot.get_channel(config["log"]).send(embed=embed, file=discord.File(f"./logs/ticket-{ch.id}.json"))

                if config["deleteafter"] == 1:
                    await asyncio.sleep(10)
                    await ch.delete()

                if config["moveclosed"] == 1:
                    await ch.edit(category=self.bot.get_channel(int(config["movecat"])))
                                
        if panel and str(payload.event_type) == "REACTION_ADD" and payload.user_id != self.bot.user.id and payload.message_id == panel["id"] and str(payload.emoji) == "📩":
            msg = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
            await msg.remove_reaction("📩", payload.member)
            await self.create_ticket(self.bot.get_guild(payload.guild_id), payload.member, reason=None)
            
    #ticket
    @commands.group(invoke_without_command=True, name="ticket", description="チケット関連のコマンドです。", usage="ticket <arg1> [arg2]")
    async def ticket(self, ctx):
        pass
    
    #ticket help
    @ticket.command(name="help", description="チケットのヘルプを表示します。", usage="ticket help")
    async def help(self, ctx):
        e = discord.Embed(title="Support - ticket", color=self.bot.color, timestamp=ctx.message.created_at)
        e.add_field(name="help", value="チケットシステムのヘルプを表示します。")
        e.add_field(name="create [reason]", value="サポートチケットを作成します。")
        e.add_field(name="reopen <channel>", value="サポートチケットを再度オープンします。")
        e.add_field(name="close", value="サポートチケットをクローズします。")
        e.add_field(name="adduser <member> [channel]", value="[運営用]指定メンバーをチケットに追加します。")
        e.add_field(name="removeuser <member> [channel] | deluser <member> [channel]", value="[運営用]指定メンバーをチケットから削除します。")
        e.add_field(name="panel [channel]", value="[運営用]サポートチケットを発行するためのパネルを作成します。")
        e.add_field(name="deletepanel <panel_id>", value="[運営用]サポートチケットを発行するためのパネルを削除します。")
        e.add_field(name="config <args>", value="[運営用]TicketSystemの設定を変更します。")
        e.add_field(name="register [channel]", value="[運営用]指定チャンネルをチケットチャンネル扱いにします。")
                                
        await ctx.send(embed=e)

    #ticket adduser
    @ticket.command(name="adduser", description="チケットにユーザーを追加します。", usage="ticket adduser <member> [channel]")
    @commands.check(util.is_staff)
    async def adduser(self, ctx, member:commands.MemberConverter=None, channel:commands.TextChannelConverter=None):
        e = discord.Embed(title="Ticket - adduser", description="処理中....", color=self.bot.color, timestamp=ctx.message.created_at)
        msg = await ctx.send(embed=e)
                                
        if isinstance(ctx.channel, discord.DMChannel):
            e.description = None
            e.add_field(name="エラー", value="DMでは使えないよ！")
            return await msg.edit(embed=e)

        if member is None:
            e.description = None
            e.add_field(name="エラー", value="メンバーを指定してね！")
            return await msg.edit(embed=e)

        if channel is None:
            ch = ctx.channel
        else:
            ch = channel

        db = await self.db.fetchone("SELECT * FROM tickets WHERE id=%s", (ch.id,))

        if db:                   
            overwrite = discord.PermissionOverwrite()
            overwrite.send_messages = True
            overwrite.read_messages = True
            overwrite.add_reactions = True
            overwrite.embed_links = True
            overwrite.read_message_history = True
            overwrite.external_emojis = True
            overwrite.attach_files = True
            
            await ch.set_permissions(member, overwrite=overwrite)
                                
            e.description = None
            e.add_field(name="成功", value=f"{member} ({member.id}) さんを{ch}に追加したよ！")
            return await msg.edit(embed=e)
        else:
            e.description = None
            e.add_field(name="エラー", value="そのチャンネルはチケットチャンネルじゃないよ！")
            return await msg.edit(embed=e)
                               
    #ticket removeuser
    @ticket.command(name="removeuser", aliases=["deluser"], description="チケットからユーザーを削除します。", usage="ticket removeuser <member> [channel] | ticket deluser <member> [channel]")
    @commands.check(util.is_staff)
    async def removeuser(self, ctx, member:commands.MemberConverter=None, channel:commands.TextChannelConverter=None):
        e = discord.Embed(title="Ticket - removeuser", description="処理中....", color=self.bot.color, timestamp=ctx.message.created_at)
        msg = await ctx.send(embed=e)

        if isinstance(ctx.channel, discord.DMChannel):
            e.description = None
            e.add_field(name="エラー", value="DMでは使えないよ！")
            return await msg.edit(embed=e)

        if member is None:
            e.description = None
            e.add_field(name="エラー", value="メンバーを指定してね！")
            return await msg.edit(embed=e)

        if channel is None:
            ch = ctx.channel
        else:
            ch = channel

        db = await self.db.fetchone("SELECT * FROM tickets WHERE id=%s", (ch.id,))

        if db:                   
            await ch.set_permissions(member, overwrite=None)
                                
            e.description = None
            e.add_field(name="成功", value=f"{member} ({member.id}) さんを{ch}から削除したよ！")
            return await msg.edit(embed=e)
        else:
            e.description = None
            e.add_field(name="エラー", value="そのチャンネルはチケットチャンネルじゃないよ！")
            return await msg.edit(embed=e)

    #ticket deletepanel
    @ticket.command(name="deletepanel", aliases=["delpanel"], description="チケットパネルを削除します。", usage="ticket deletepanel <panel_id> | ticket delpanel <panel_id>")
    @commands.check(util.is_staff)
    async def deletepanel(self, ctx, panel_id:int=None):
        e = discord.Embed(title="Ticket - deletepanel", description="処理中...", color=self.bot.color, timestamp=ctx.message.created_at)
        msg = await ctx.send(embed=e)
        
        if isinstance(ctx.channel, discord.DMChannel):
            e.description = None
            e.add_field(name="エラー", value="DMでは使えないよ！")
            return await msg.edit(embed=e)

        if panel_id is None:
            e.description = None
            e.add_field(name="エラー", value="パネルIDを入力してね！")
            return await msg.edit(embed=e)
         
        check = await self.db.fetchone("SELECT * FROM ticket_panel WHERE id=%s", (panel_id,))
        
        if check:
            ch = self.bot.get_channel(check["channel"])
            panel = await ch.fetch_message(panel_id)
            
            await self.db.execute("DELETE FROM ticket_panel WHERE id=%s", (panel_id,))
            await panel.delete()
                                
            e.description = None
            e.add_field(name="成功", value="パネルを削除しました！")
            return await msg.edit(embed=e)
        else:
            e.description = None
            e.add_field(name="エラー", value=f"そのIDのパネルは存在しません。")
            return await msg.edit(embed=e)
    
    #ticket panel
    @ticket.command(name="panel", aliases=["addpanel"], description="チケットパネルを作成します。", usage="ticket panel [channel] | ticket addpanel [channel]")
    @commands.check(util.is_staff)
    async def panel(self, ctx, channel:commands.TextChannelConverter=None):
        e = discord.Embed(title="Ticket - panel", description="処理中...", color=self.bot.color, timestamp=ctx.message.created_at)
        msg = await ctx.send(embed=e)
        
        if isinstance(ctx.channel, discord.DMChannel):
            e.description = None
            e.add_field(name="エラー", value="DMでは使えないよ！")
            return await msg.edit(embed=e)

        if channel is None:
            channel = ctx.channel
        else:
            channel = channel
        
        db = await self.db.fetchone("SELECT * FROM ticket_config WHERE guild=%s", (ctx.guild.id,))
        if not db:
            e.description = None
            e.add_field(name="エラー", value="Configがないのでパネルを作成できません。")
            return await msg.edit(embed=e)
         
        check = await self.db.fetchone("SELECT * FROM ticket_panel WHERE channel=%s", (channel.id,))
        
        if check:
            e.description = None
            e.add_field(name="エラー", value="すでにパネルが存在するよ！")
            return await msg.edit(embed=e)
        else:
            panel = discord.Embed(title="Support Ticket Panel", description="📩 をクリックすることでサポートチケットを発行します。", color=self.bot.color)
            m = await channel.send(embed=panel)
            await m.add_reaction("📩")

            await self.db.execute(f"INSERT INTO ticket_panel VALUES({m.id}, {channel.id}, {ctx.guild.id})")

            e.description = None
            e.add_field(name="成功", value=f"{channel} ({channel.id})にサポートパネルを作成しました！")
            return await msg.edit(embed=e)
    
    #ticket config
    @ticket.group(name="config", description="チケットの設定を変更します。", usage="ticket config <arg1> [arg2]")
    @commands.check(util.is_staff)
    async def config(self, ctx):
        e = discord.Embed(title="Ticket - config", color=self.bot.color, timestamp=ctx.message.created_at)
        
        if ctx.invoked_subcommand is None:
            e.add_field(name="config category <category>", value="サポートチケットのカテゴリを変更します。")
            e.add_field(name="config role <role>", value="チケット作成時にメンションする役職を変更します。")
            e.add_field(name="config mention <True/False>", value="運営チームにメンションするかを変更します。")
            e.add_field(name="config delafter <True/False>", value="チケットクローズ後チャンネルを削除するかを変更します。")
            e.add_field(name="config moveclosed <True/False>", value="チケットクローズ後にアーカイブするかを変更します。")
            e.add_field(name="config moveto <category>", value="チケットクローズ後にアーカイブするカテゴリを変更します。")
            e.add_field(name="config log <channel>", value="チケットクローズ後にjsonログを送信するチャンネルを変更します。")
            await ctx.send(embed=e)
    
    #ticket config moveto
    @config.command(name="moveto", description="チケットをクローズ後に移動するカテゴリを設定します。", usage="ticket config moveto <category>")
    @commands.check(util.is_staff)
    async def moveto(self, ctx, category:commands.CategoryChannelConverter=None):
        e = discord.Embed(title="Config - moveto", description="処理中...", color=self.bot.color, timestamp=ctx.message.created_at)
        msg = await ctx.send(embed=e)

        if isinstance(ctx.channel, discord.DMChannel):
            e.description = None
            e.add_field(name="エラー", value="DMでは使えないよ！")
            return await msg.edit(embed=e)
        
        if category is None:
            e.description = None
            e.add_field(name="エラー", value="カテゴリを入力してね！")
            return await msg.edit(embed=e)
         
        check = await self.db.fetchone("SELECT * FROM ticket_config WHERE guild=%s", (ctx.guild.id,))
        
        if check:
            await self.db.execute(f"UPDATE ticket_config SET movecat={category.id} WHERE guild={ctx.guild.id}")
            e.description = None
            e.add_field(name="成功", value=f"アーカイブ先のカテゴリを{category} ({category.id})に設定したよ！")
            return await msg.edit(embed=e)
        else:
            e.description = None
            e.add_field(name="エラー", value="データが存在しません。")
            return await msg.edit(embed=e)

    #ticket config moveclosed
    @config.command(name="moveclosed", description="チケットをクローズ後にカテゴリを移動するか設定します。", usage="ticket config moveclosed <True/False>")
    @commands.check(util.is_staff)
    async def moveclosed(self, ctx, value:bool=None):
        e = discord.Embed(title="Config - moveclosed", description="処理中...", color=self.bot.color, timestamp=ctx.message.created_at)
        msg = await ctx.send(embed=e)

        if isinstance(ctx.channel, discord.DMChannel):
            e.description = None
            e.add_field(name="エラー", value="DMでは使えないよ！")
            return await msg.edit(embed=e)
        
        if value is None:
            e.description = None
            e.add_field(name="エラー", value="TrueかFalseを入力してね！")
            return await msg.edit(embed=e)
         
        check = await self.db.fetchone("SELECT * FROM ticket_config WHERE guild=%s", (ctx.guild.id,))
        
        if check:
            await self.db.execute(f"UPDATE ticket_config SET moveclosed={int(value)} WHERE guild={ctx.guild.id}")
            e.description = None
            e.add_field(name="成功", value=f"チケットの移動を{value}に設定したよ！")
            return await msg.edit(embed=e)
        else:
            e.description = None
            e.add_field(name="エラー", value="データが存在しません。")
            return await msg.edit(embed=e)
                                
    #ticket config mention
    @config.command(name="mention", description="チケット作成時に指定ロールにメンションするかを設定します。", usage="ticket config mention <on/off>")
    @commands.check(util.is_staff)
    async def mention(self, ctx, mention:bool=None):
        e = discord.Embed(title="Config - mention", description="処理中...", color=self.bot.color, timestamp=ctx.message.created_at)
        msg = await ctx.send(embed=e)

        if isinstance(ctx.channel, discord.DMChannel):
            e.description = None
            e.add_field(name="エラー", value="DMでは使えないよ！")
            return await msg.edit(embed=e)
        
        if mention is None:
            e.description = None
            e.add_field(name="エラー", value="onかoffを入力してね！")
            return await msg.edit(embed=e)
         
        check = await self.db.fetchone("SELECT * FROM ticket_config WHERE guild=%s", (ctx.guild.id,))
        
        if check:
            await self.db.execute(f"UPDATE ticket_config SET mention={int(mention)} WHERE guild={ctx.guild.id}")
            e.description = None
            e.add_field(name="成功", value=f"メンションを{mention}に設定したよ！")
            return await msg.edit(embed=e)
        else:
            e.description = None
            e.add_field(name="エラー", value="データが存在しません。")
            return await msg.edit(embed=e)

    #ticket config role
    @config.command(name="role", description="チケット発行時にメンションする役職を設定します。", usage="ticket config role <role>")
    @commands.check(util.is_staff)
    async def role(self, ctx, role:commands.RoleConverter=None):
        e = discord.Embed(title="Config - role", description="処理中...", color=self.bot.color, timestamp=ctx.message.created_at)
        msg = await ctx.send(embed=e)

        if isinstance(ctx.channel, discord.DMChannel):
            e.description = None
            e.add_field(name="エラー", value="DMでは使えないよ！")
            return await msg.edit(embed=e)
        
        if role is None:
            e.description = None
            e.add_field(name="エラー", value="ロールを入力してね！")
            return await msg.edit(embed=e)
         
        check = await self.db.fetchone("SELECT * FROM ticket_config WHERE guild=%s", (ctx.guild.id,))
        
        if check:
            await self.db.execute(f"UPDATE ticket_config SET role={role.id} WHERE guild={ctx.guild.id}")
            e.description = None
            e.add_field(name="成功", value=f"メンションする役職を{role} ({role.id})に設定したよ！")
            return await msg.edit(embed=e)
        else:
            e.description = None
            e.add_field(name="エラー", value="データが存在しません。")
            return await msg.edit(embed=e)
    
    #ticket config category
    @config.command(name="category", description="チケット発行時にどのカテゴリにチャンネルを作成するかを設定します。", usage="ticket config category <category>")
    @commands.check(util.is_staff)
    async def category(self, ctx, category:commands.CategoryChannelConverter=None):
        e = discord.Embed(title="Config - category", description="処理中...", color=self.bot.color, timestamp=ctx.message.created_at)
        msg = await ctx.send(embed=e)

        if isinstance(ctx.channel, discord.DMChannel):
            e.description = None
            e.add_field(name="エラー", value="DMでは使えないよ！")
            return await msg.edit(embed=e)
        
        if category is None:
            e.description = None
            e.add_field(name="エラー", value="カテゴリを入力してね！")
            return await msg.edit(embed=e)
         
        check = await self.db.fetchone("SELECT * FROM ticket_config WHERE guild=%s", (ctx.guild.id,))
        
        if check:
            await self.db.execute(f"UPDATE ticket_config SET category={category.id} WHERE guild={ctx.guild.id}")
            e.description = None
            e.add_field(name="成功", value=f"チケットのカテゴリを{category} ({category.id})に設定したよ！")
            return await msg.edit(embed=e)
        else:
            e.description = None
            e.add_field(name="エラー", value="データが存在しません。")
            return await msg.edit(embed=e)
                                                      
    #ticket config channel
    @config.command(name="log", description="チケットクローズ後にjsonのログを送信するチャンネルを設定します。", usage="ticket config log <channel>")
    @commands.check(util.is_staff)
    async def log(self, ctx, channel:commands.TextChannelConverter=None):
        e = discord.Embed(title="Config - log", description="処理中...", color=self.bot.color, timestamp=ctx.message.created_at)
        msg = await ctx.send(embed=e)

        if isinstance(ctx.channel, discord.DMChannel):
            e.description = None
            e.add_field(name="エラー", value="DMでは使えないよ！")
            return await msg.edit(embed=e)
        
        if channel is None:
            e.description = None
            e.add_field(name="エラー", value="チャンネルを入力してね！")
            return await msg.edit(embed=e)
         
        check = await self.db.fetchone("SELECT * FROM ticket_config WHERE guild=%s", (ctx.guild.id,))
        
        if check:
            await self.db.execute(f"UPDATE ticket_config SET log={channel.id} WHERE guild={ctx.guild.id}")
            e.description = None
            e.add_field(name="成功", value=f"ログチャンネルを{channel} ({channel.id})に設定したよ！")
            return await msg.edit(embed=e)
        else:
            e.description = None
            e.add_field(name="エラー", value="データが存在しません。")
            return await msg.edit(embed=e)
                           
    #ticket config delafter
    @config.command(name="delafter", description="チケットクローズ後にチケットを削除するかを設定します。", usage="ticket config delafter <True/False>")
    @commands.check(util.is_staff)
    async def delafter(self, ctx, bool:bool=None):
        e = discord.Embed(title="Config - delafter", description="処理中...", color=self.bot.color, timestamp=ctx.message.created_at)
        msg = await ctx.send(embed=e)

        if isinstance(ctx.channel, discord.DMChannel):
            e.description = None
            e.add_field(name="エラー", value="DMでは使えないよ！")
            return await msg.edit(embed=e)
        
        if bool is None:
            e.description = None
            e.add_field(name="エラー", value="TrueかFalseを入力してね！")
            return await msg.edit(embed=e)
         
        check = await self.db.fetchone("SELECT * FROM ticket_config WHERE guild=%s", (ctx.guild.id,))
        
        if check:
            await self.db.execute(f"UPDATE ticket_config SET deleteafter={int(bool)} WHERE guild={ctx.guild.id}")
            e.description = None
            e.add_field(name="成功", value=f"{bool}に設定したよ！")
            return await msg.edit(embed=e)
        else:
            e.description = None
            e.add_field(name="エラー", value="データが存在しません。")
            return await msg.edit(embed=e)
    
    #ticket close
    @ticket.command(name="close", description="チケットをクローズします。", usage="ticket close")
    async def _close(self, ctx):
        msg = await ctx.send("> 処理中...")
        
        if isinstance(ctx.channel, discord.DMChannel):
            return await msg.edit(content="> エラー\nDMでは使えないよ！")
                                
        db = await self.db.fetchone("SELECT * FROM tickets WHERE id=%s", (ctx.channel.id,))
        config = await self.db.fetchone("SELECT * FROM ticket_config WHERE guild=%s", (ctx.guild.id,))
                        
        if not (db["author"] == ctx.author.id or ctx.author.id in [m.id for m in ctx.guild.get_role(config["role"]).members]):
            return await msg.edit(content=f"> エラー\nチケットの作成者または運営のみがcloseできます。")
        
        if db:
            if db["status"] == 1:
                await msg.edit(content=f"> Closeしますか？ (close/open)")
                
                wait = await self.bot.wait_for("message", check=lambda m: m.author.id == ctx.author.id and m.channel.id == ctx.channel.id)
                        
                if str(wait.content) != "close":
                    await msg.edit(content=f"> キャンセルしました！")
                    return
                else:
                    overwrite = discord.PermissionOverwrite()
                    overwrite.send_messages = False
                    overwrite.add_reactions = False
                    overwrite.external_emojis = False
                        
                    await ctx.channel.edit(name=ctx.channel.name.replace("ticket", "close"))
                    await ctx.channel.set_permissions(self.bot.get_user(db["author"]), overwrite=overwrite)
                    await self.db.execute("UPDATE tickets SET status=%s WHERE id=%s", (1, ctx.channel.id))
                    await msg.edit(content="> サポートチケットをcloseしました！")
                    await ctx.send(content="> Support Ticket Logs (json)", file=discord.File(f"/home/midorichan/TokiServerBot/logs/ticket-{ctx.channel.id}.json"))
                    
                    if config["log"]:
                        embed = discord.Embed(title=f"Ticket Logs {self.bot.get_user(db['author'])} ({db['author']})", color=0x36b8fa)
                                
                        await self.bot.get_channel(config["log"]).send(embed=embed, file=discord.File(f"/home/midorichan/TokiServerBot/logs/ticket-{ctx.channel.id}.json"))
                                              
                    if config["deleteafter"] == 1:
                        await asyncio.sleep(10)
                        await ctx.channel.delete()
                    
                    if config["moveclosed"] == 1:
                        await ctx.channel.edit(category=ctx.guild.get_channel(config["movecat"]))
            else:
                await msg.edit(content=f"> エラー\nこのチャンネルはすでにcloseされてるよ！")
        else:
            await msg.edit(content=f"> エラー\nこのチャンネルはサポートチケットじゃないよ！")
    
    #ticket reopen
    @ticket.command(name="reopen", description="クローズ済みのチケットを再度オープンします。", usage="ticket reopen <channel>")
    async def reopen(self, ctx, channel:commands.TextChannelConverter=None):
        msg = await ctx.send("> 処理中...")
                                
        if isinstance(ctx.channel, discord.DMChannel):
            return await msg.edit(content="> エラー \nDMでは使えないよ！")
                                
        if channel is None:
            return await msg.edit(content="> エラー \n再オープンするチケットチャンネルを入力してね！")

        db = await self.db.fetchone("SELECT * FROM tickets WHERE id=%s", (channel.id,))
        config = await self.db.fetchone("SELECT * FROM ticket_config WHERE guild=%s", (ctx.guild.id,))
                                
        if not db:
            return await msg.edit(content="> エラー \nそのチャンネルはチケットチャンネルではありません。")
       
        if db["status"] != 0:
            return await msg.edit(content="> エラー \nそのチケットチャンネルはcloseされていません。")
                                
        if db["author"] == ctx.author.id or ctx.author.id in [m.id for m in ctx.guild.get_role(config["role"]).members]:
            await self.db.execute(f"UPDATE tickets SET status=1 WHERE id={channel.id}")
                                
            overwrite = discord.PermissionOverwrite()
            overwrite.send_messages = True
            overwrite.read_messages = True
            overwrite.add_reactions = True
            overwrite.embed_links = True
            overwrite.read_message_history = True
            overwrite.external_emojis = True
            overwrite.attach_files = True

            if channel.category_id == int(config["movecat"]):
                await channel.edit(name=channel.name.replace("close", "ticket"), category=ctx.guild.get_channel(int(config["category"])))
            elif channel.category_id != int(config["category"]):
                await channel.edit(name=channel.name.replace("close", "ticket"), category=ctx.guild.get_channel(int(config["category"])))
            else:
                await channel.edit(name=channel.name.replace("close", "ticket"))
                                
            await channel.set_permissions(ctx.guild.get_member(db["author"]), overwrite=overwrite)
            
            return await msg.edit(content="> チケットを再オープンしました！")
        else:
            return await msg.edit(content="> エラー \nそのチケットチャンネルは作成者または、運営のみが再オープンできます。")
                                  
    #ticket create
    @ticket.command(name="create", description="チケットを発行します。", usage="ticket create [reason]")
    async def create(self, ctx, *, reason:str=None):
        msg = await ctx.send("> 処理中...")
        
        if isinstance(ctx.channel, discord.DMChannel):
            return await msg.edit(content="> エラー\nDMでは使えないよ！")
        
        if reason is None:
            reason = "なし"
        
        if len(reason) >= 1024:
            return await msg.edit(content="> エラー\n理由は1024文字以下にしてね！")
        
        db = await self.db.fetchone("SELECT * FROM ticket_config WHERE guild=%s", (ctx.guild.id,))

        if not db:
            return await msg.edit(content=f"> エラー \nデータが存在しません。")
                               
        channel, message = await self.create_ticket(ctx.guild, ctx.author, reason="unknown")
        
        await msg.edit(content=f"> チケットを作成しました！ \n→ {channel.mention}")
        
    #ticket create
    @ticket.command(name="register", description="チャンネルをチケット扱いにします。", usage="ticket register [channel]")
    @commands.check(util.is_staff)
    async def register(self, ctx, *, channel:commands.TextChannelConverter=None):
        msg = await ctx.send("> 処理中...")
        
        if isinstance(ctx.channel, discord.DMChannel):
            return await msg.edit(content="> エラー\nDMでは使えないよ！")
        
        if channel is None:
            channel = ctx.channel
        
        await self.create_panel(ctx.guild, ctx.author, channel, reason="unknown")
        
        overwrite = discord.PermissionOverwrite()
        overwrite.send_messages = True
        overwrite.read_messages = True
        overwrite.add_reactions = True
        overwrite.embed_links = True
        overwrite.read_message_history = True
        overwrite.external_emojis = True
        overwrite.attach_files = True
        await channel.set_permissions(ctx.author, overwrite=overwrite)
        
        await msg.edit(content=f"> チケット登録しました！")
        
def setup(bot):
    bot.add_cog(mido_ticket(bot))
