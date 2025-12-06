import os
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler

TOKEN = "8010976316:AAEpXdsLrbUUKqye66OI41LrQaTEc7RAuAk"
APP_URL = "https://easyvideo.onrender.com"  # Seu domínio Render

app = Flask(__name__)

# Criar aplicação do Telegram
application = Application.builder().token(TOKEN).build()

# ---- HANDLERS ----
def start(update: Update, context):
    context.bot.send_message(chat_id=update.message.chat_id, text="Hello World!")

application.add_handler(CommandHandler("start", start))

# ---- WEBHOOK RECEBE UPDATE ----
@app.route("/webhook", methods=["POST"])
def webhook():
    json_data = request.get_json()
    update = Update.de_json(json_data, application.bot)

    # Processa o update (modo síncrono)
    application.process_update(update)

    return "ok", 200

# ---- HOME ----
@app.route("/")
def home():
    return "Bot funcionando!", 200

# ---- SET WEBHOOK AUTOMÁTICO ----
if __name__ == "__main__":
    import asyncio

    async def setup():
        url = f"{APP_URL}/webhook"
        await application.bot.set_webhook(url)
        print("Webhook configurado:", url)

    asyncio.run(setup())

    # Iniciar Flask
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)