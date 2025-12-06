import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import yt_dlp

TOKEN = os.getenv("BOT_TOKEN")  # use variável de ambiente no Render

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Envie um link de vídeo que eu baixo para você!")

async def baixar_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    await update.message.reply_text("⏳ Baixando vídeo...")

    output = "video.mp4"

    try:
        ydl_opts = {
            "outtmpl": output,
            "format": "mp4"
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        await update.message.reply_video(open(output, "rb"))
        os.remove(output)

    except Exception as e:
        await update.message.reply_text(f"Erro ao baixar: {e}")

def main():
    app = Application.builder().token(TOKEN).build()

    # comandos
    app.add_handler(CommandHandler("start", start))

    # quando usuário manda link
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, baixar_video))

    app.run_polling()

if __name__ == "__main__":
    main()