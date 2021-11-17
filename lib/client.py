import asyncio

class Route:
  
    def __init__(self, method, path):
        self.method = method
        self.path = path

class Client:
    
    def __init__(self, bot):
        self.bot = bot
        self.session = bot.session
    
    async def request(self, route, *arg, **kwargs):
        async with self.session.request(route.method, route.path, *args, **kwargs) as r:
            await r.raise_for_status()
            return r
