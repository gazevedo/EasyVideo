import os
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message
import yt_dlp
import asyncio

TOKEN = "COLOQUE_SEU_TOKEN_AQUI"

bot = Bot(token=TOKEN)
dp = Dispatcher()

def baixar_video(url):
    ydl_opts = {"outtmpl": "video.mp4"}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return "video.mp4"

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer("Envie o link do vídeo que deseja baixar!")

@dp.message()
async def baixar(message: Message):
    url = message.text

    await message.answer("⏳ Baixando vídeo...")

    try:
        arquivo = baixar_video(url)
        await message.answer_video(open(arquivo, "rb"))
        os.remove(arquivo)
    except Exception as e:
        await message.answer(f"❌ Erro ao baixar: {e}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
