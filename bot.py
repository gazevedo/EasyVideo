import os
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler

TOKEN = "8010976316:AAEpXdsLrbUUKqye66OI41LrQaTEc7RAuAk"
WEBHOOK_URL = "https://easyvideo.onrender.com/webhook"

app = Flask(__name__)

application = ApplicationBuilder().token(TOKEN).build()

async def start(update: Update, context):
    await update.message.reply_text("Hello World!")

application.add_handler(CommandHandler("start", start))

@app.post("/webhook")
async def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    await application.process_update(update)   # <-- ESSENCIAL
    return "OK"

@app.get("/")
def home():
    return "Bot funcionando!"

async def set_webhook():
    await application.bot.set_webhook(WEBHOOK_URL)
    print("Webhook configurado!")

import asyncio
asyncio.run(set_webhook())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))