import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application

TOKEN = "8010976316:AAEpXdsLrbUUKqye66OI41LrQaTEc7RAuAk"
APP_URL = "https://easyvideo.onrender.com"

# Flask
app = Flask(__name__)

# Criar event loop global
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# Criar Application
application = Application.builder().token(TOKEN).build()

# Handler
async def hello(update: Update, context):
    await update.message.reply_text("Hello World!")

application.add_handler(CommandHandler("start", hello))


@app.post("/webhook")
def webhook():
    data = request.get_json()
    update = Update.de_json(data, application.bot)

    # Processar update NO EVENT LOOP CORRETO
    loop.create_task(application.process_update(update))

    return "ok", 200


@app.get("/")
def home():
    return "Bot funcionando!", 200


# Configure webhook e inicie Application corretamente
async def setup():
    await application.initialize()
    await application.start()
    await application.bot.set_webhook(f"{APP_URL}/webhook")
    print("Webhook configurado!")


# Executar setup
loop.run_until_complete(setup())


# Rodar servidor Flask
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))