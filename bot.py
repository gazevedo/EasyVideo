from aiogram import Bot, Dispatcher, types
from aiogram import F
import asyncio

TOKEN = "8010976316:AAEpXdsLrbUUKqye66OI41LrQaTEc7RAuAk"

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(F.text.lower() == "oi")
async def responder_oi(message: types.Message):
    await message.answer("oi")

async def main():
    print("Bot iniciado e rodando!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())