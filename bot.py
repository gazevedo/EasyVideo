import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiohttp import web

TOKEN = "8010976316:AAEpXdsLrbUUKqye66OI41LrQaTEc7RAuAk"

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# --- BOT ---
@dp.message_handler()
async def responder(msg: types.Message):
    if msg.text.lower() == "oi":
        await msg.answer("oi")

# --- SERVIDOR WEB PARA O RENDER ---
async def handle(request):
    return web.Response(text="Bot ativo!")

async def start_web_app():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()


async def main():
    # inicia o mini servidor para o Render
    asyncio.create_task(start_web_app())

    # inicia o bot Telegram
    executor.start_polling(dp, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())