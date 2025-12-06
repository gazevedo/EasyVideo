from aiogram import Bot, Dispatcher, executor, types

TOKEN = "COLOQUE_SEU_TOKEN_AQUI"

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=['start'])
async def start(msg: types.Message):
    await msg.answer("Bot iniciado!")

@dp.message_handler(lambda msg: msg.text.lower() == "oi")
async def responder(msg: types.Message):
    await msg.answer("oi")

if __name__ == "__main__":
    executor.start_polling(dp)