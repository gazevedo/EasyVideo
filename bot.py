from aiogram import Bot, Dispatcher, executor, types
import yt_dlp, os

TOKEN = "8010976316:AAEpXdsLrbUUKqye66OI41LrQaTEc7RAuAk"

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

def baixar_video(url):
    ydl_opts = {
        "outtmpl": "video.mp4",
        "format": "mp4/bestaudio/best"
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return "video.mp4"

@dp.message_handler()
async def processar(message: types.Message):
    url = message.text.strip()

    await message.reply("⏳ Baixando vídeo, aguarde...")

    try:
        video = baixar_video(url)
        await message.reply_video(open(video, "rb"), caption="Vídeo baixado!")
        os.remove(video)
    except Exception as e:
        await message.reply(f"❌ Erro: ao baixar: {e}")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
