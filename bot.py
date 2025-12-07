import os
import asyncio
import threading
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters
)

TOKEN = "8010976316:AAEpXdsLrbUUKqye66OI41LrQaTEc7RAuAk"
APP_URL = "https://easyvideo.onrender.com"

app = Flask(__name__)

# ============================================
# LOOP ASSÍNCRONO EM THREAD SEPARADA
# ============================================
loop = asyncio.new_event_loop()

def start_loop():
    asyncio.set_event_loop(loop)
    loop.run_forever()

threading.Thread(target=start_loop, daemon=True).start()

# ============================================
# CRIA APPLICATION DO TELEGRAM
# ============================================
application = ApplicationBuilder().token(TOKEN).build()

# ============================================
# HANDLER /start
# ============================================
async def start(update: Update, context):
    await update.message.reply_text("Bot ONLINE!")

application.add_handler(CommandHandler("start", start))

# ============================================
# HANDLER PARA QUALQUER TEXTO
# ============================================
async def eco(update: Update, context):
    await update.message.reply_text(f"Você disse: {update.message.text}")

application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, eco))

# ============================================
# FLASK WEBHOOK
# ============================================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)

    # ESSA LINHA É A MAIS IMPORTANTE DO ARQUIVO TODO
    asyncio.run_coroutine_threadsafe(application.process_update(update), loop)

    return "OK", 200

@app.route("/", methods=["GET"])
def home():
    return "Bot funcionando!", 200

# ============================================
# CONFIGURA O WEBHOOK AO INICIAR
# ============================================
async def set_webhook():
    await application.bot.set_webhook(f"{APP_URL}/webhook")
    print("Webhook configurado!")

asyncio.run_coroutine_threadsafe(set_webhook(), loop)

# ============================================
# INICIA FLASK
# ============================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)