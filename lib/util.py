import asyncio
import subprocess
import uuid

from discord.ext import commands
from . import mido_util

class MemberConverter(commands.Converter):
    async def convert(ctx, argument):
        return await mido_util.FetchUserConverter().convert(ctx, argument)

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
