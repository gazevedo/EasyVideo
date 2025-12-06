from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import yt_dlp
import os

TOKEN = "COLOQUE_SEU_TOKEN_AQUI"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Envie um link de vídeo que eu baixo pra você!")

async def baixar_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text

    await update.message.reply_text("⏳ Baixando vídeo...")

    try:
        ydl_opts = {
            "outtmpl": "video.mp4",
            "format": "mp4"
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        await update.message.reply_video("video.mp4")

        os.remove("video.mp4")

    except Exception as e:
        await update.message.reply_text(f"Erro ao baixar: {e}")

async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, baixar_video))

    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())