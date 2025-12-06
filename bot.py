import os
import asyncio
import threading
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

TOKEN = "8010976316:AAEpXdsLrbUUKqye66OI41LrQaTEc7RAuAk"
APP_URL = "https://easyvideo.onrender.com"

app = Flask(__name__)

# --- Cria loop asyncio em thread separada ---
loop = asyncio.new_event_loop()

def start_loop():
    asyncio.set_event_loop(loop)
    loop.run_forever()

threading.Thread(target=start_loop, daemon=True).start()

# --- Cria a Application (seu objeto principal) ---
application = ApplicationBuilder().token(TOKEN).build()

# --- Handler /start ---
async def hello(update: Update, context):
    await update.message.reply_text("Hello World!")

application.add_handler(CommandHandler("start", hello))

# --- Handler para responder qualquer mensagem ---
async def reply_any(update: Update, context):
    texto = update.message.text
    await update.message.reply_text(f"Você disse: {texto}")

application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply_any))

# --- Webhook (rota síncrona do Flask) ---
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)

    asyncio.run_coroutine_threadsafe(application.process_update(update), loop)
    return "OK", 200

@app.route("/", methods=["GET"])
def index():
    return "Bot funcionando!", 200

# --- Configura webhook no Telegram ---
async def _set_webhook():
    await application.bot.set_webhook(f"{APP_URL}/webhook")
    print("Webhook configurado:", f"{APP_URL}/webhook")

asyncio.run_coroutine_threadsafe(_set_webhook(), loop)

# --- Start Flask ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)