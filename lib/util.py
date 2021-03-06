import asyncio
import subprocess
import uuid

from discord.ext import commands
from . import mido_util

class MemberConverter(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            return await mido_util.FetchUserConverter().convert(ctx, argument)
        except:
            return None

#MinecraftConverter
class MinecraftConverter:
    async def convert(self, ctx, value):
        try:
            id = uuid.UUID(value)
        except:
            async with ctx.bot.session.get(f"https://api.mojang.com/users/profiles/minecraft/{value}") as resp:
                if resp.status == 204:
                    raise ValueError("ユーザーが見つかりません")
                elif resp.status == 200:
                    return await resp.json()
                else:
                    raise ValueError("ユーザー名の検証中にエラーが発生しました")
        else:
            async with ctx.bot.session.get(f"https://api.mojang.com/user/profile/{id.hex}") as resp:
                if resp.status == 204:
                    raise ValueError("UUIDが見つかりません")
                elif resp.status == 200:
                    return await resp.json()
                else:
                    raise ValueError("UUIDの検証中にエラーが発生しました")

#clear_reactions
async def clear_reactions(message):
    try:
        await message.clear_reactions()
    except:
        pass

#wait_for_check
async def wait_for_check(ctx, *, message=None, timeout: float=30.0, type: str="reaction"):
    if not message:
        message = ctx.message
    
    if type == "reaction":
        await message.add_reaction("✅")
        await message.add_reaction("❌")
        
        try:
            r, u = await ctx.bot.wait_for("reaction_add", check=lambda r, u: u.id == ctx.author.id and r.message.id == message.id, timeout=timeout)
        except Exception as exc:
            await clear_reactions(message) 
            raise exc
        else:
            if r.emoji == "✅":
                await clear_reactions(message)
                return True
            elif r.emoji == "❌":
                await clear_reactions(message)
                return False
    else:
        try:
            m = await ctx.bot.wait_for("message", check=lambda m: m.author.id == ctx.author.id and m.id == message.id, timeout=timeout)
        except Exception as exc:
            raise exc
        else:
            if m.content in ["yes", "y", "はい", "true", "on", "True"]:
                return True
            elif m.content in ["no", "n", "いいえ", "false", "off", "False"]:
                return False
                    
#resolve_mcid
async def resolve_mcid(ctx, *, mcid):
    cls = MinecraftConverter()
    return await cls.convert(ctx, mcid)

#reply_or_send
async def reply_or_send(ctx, *args, **kwargs):
    try:
        return await ctx.reply(*args, **kwargs)
    except:
        try:
            return await ctx.send(*args, **kwargs)
        except:
            try:
                return await ctx.author.send(*args, **kwargs)
            except:
                return None

#remove ```
def cleanup_code(content):
    if content.startswith('```') and content.endswith('```'):
        return '\n'.join(content.split('\n')[1:-1])

    return content.strip('` \n')

#create shell process
async def run_process(ctx, command):
    try:
        process = await asyncio.create_subprocess_shell(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        result = await process.communicate()
    except NotImplementedError:
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        result = await ctx.bot.loop.run_in_executor(None, process.communicate)

    return [output.decode() for output in result]

#is_staff
async def is_staff(ctx):
    guild = ctx.bot.get_guild(891255334109323275)
    if not ctx.guild:
        return False
    if not guild.get_member(ctx.author.id):
        return False
    return guild.get_role(891967518762237963) in ctx.author.roles
