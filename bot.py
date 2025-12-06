import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler

TOKEN = "8010976316:AAEpXdsLrbUUKqye66OI41LrQaTEc7RAuAk"
APP_URL = "https://easyvideo.onrender.com"

app = Flask(__name__)

# Criar event loop MANUAL porque Flask não cria um
event_loop = asyncio.new_event_loop()
asyncio.set_event_loop(event_loop)

# Iniciar aplicação PTB dentro do loop
bot_app = ApplicationBuilder().token(TOKEN).build()
event_loop.run_until_complete(bot_app.initialize())
event_loop.run_until_complete(bot_app.start())

# --- HANDLER ---
async def hello(update: Update, context):
    await update.message.reply_text("Hello World!")

bot_app.add_handler(CommandHandler("start", hello))


# --- WEBHOOK ---
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    update = Update.de_json(data, bot_app.bot)

    # Processar update dentro do loop
    event_loop.create_task(bot_app.process_update(update))

    return "ok"


# --- HOME ---
@app.route("/")
def home():
    return "Bot funcionando", 200


# --- SET WEBHOOK ---
async def set_webhook():
    await bot_app.bot.set_webhook(f"{APP_URL}/webhook")
    print("Webhook configurado!")

event_loop.run_until_complete(set_webhook())


# --- START FLASK ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))