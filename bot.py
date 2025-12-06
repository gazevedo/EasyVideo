import asyncio
from aiogram import Bot, Dispatcher, executor, types
from aiohttp import web

TOKEN = "COLOQUE_SEU_TOKEN_AQUI"

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# --- BOT ---
@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    await msg.answer("Bot iniciado!")

@dp.message_handler(lambda msg: msg.text.lower() == "oi")
async def oi(msg: types.Message):
    await msg.answer("oi!")

# --- SERVIDOR WEB PARA O RENDER ---
async def render_healthcheck(request):
    return web.Response(text="Bot rodando!")

async def start_web_app():
    app = web.Application()
    app.router.add_get("/", render_healthcheck)
    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT")))
    await site.start()

# --- MAIN ---
async def main():
    asyncio.create_task(start_web_app())
    executor.start_polling(dp)

if __name__ == "__main__":
    import os
    asyncio.run(main())