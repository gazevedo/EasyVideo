import os
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler

TOKEN = "8010976316:AAEpXdsLrbUUKqye66OI41LrQaTEc7RAuAk"
APP_URL = f"https://easyvideo.onrender.com"   # coloque seu domínio do Render

app_bot = ApplicationBuilder().token(TOKEN).build()

async def start(update: Update, context):
    await update.message.reply_text("Oi! Seu bot está funcionando via Webhook 😄")

app_bot.add_handler(CommandHandler("start", start))

flask_app = Flask(__name__)

@flask_app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(), app_bot.bot)
    app_bot.update_queue.put_nowait(update)
    return "ok", 200

@flask_app.route("/")
def home():
    return "Bot ativo!", 200

async def set_webhook():
    webhook_url = f"{APP_URL}/webhook"
    await app_bot.bot.set_webhook(webhook_url)
    print("Webhook configurado para:", webhook_url)

import asyncio
asyncio.get_event_loop().run_until_complete(set_webhook())

if __name__ == "__main__":
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))