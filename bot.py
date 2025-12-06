import os
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler
import asyncio

TOKEN = "8010976316:AAEpXdsLrbUUKqye66OI41LrQaTEc7RAuAk"
APP_URL = "https://easyvideo.onrender.com"

app = Flask(__name__)
bot_app = ApplicationBuilder().token(TOKEN).build()

async def hello(update: Update, context):
    await update.message.reply_text("Hello World!")

bot_app.add_handler(CommandHandler("start", hello))

@app.route("/webhook", methods=["POST"])
def webhook():
    print("WEBHOOK RECEBIDO!")
    print(request.get_json())
    update = Update.de_json(request.get_json(), bot_app.bot)
    asyncio.create_task(bot_app.process_update(update))
    return "ok"

@app.route("/")
def home():
    return "Bot funcionando", 200

async def set_webhook():
    url = f"{APP_URL}/webhook"
    await bot_app.bot.set_webhook(url)
    print("Webhook configurado:", url)

asyncio.get_event_loop().run_until_complete(set_webhook())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))