import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler

TOKEN = "8010976316:AAEpXdsLrbUUKqye66OI41LrQaTEc7RAuAk"
APP_URL = "https://easyvideo.onrender.com"

app = Flask(__name__)

# Criar event loop global
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# Criar Application PTB
application = Application.builder().token(TOKEN).build()

# Handler
async def hello(update: Update, context):
    await update.message.reply_text("Hello World!")

application.add_handler(CommandHandler("start", hello))


# Rota do webhook
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    update = Update.de_json(data, application.bot)

    # PROCESSAMENTO CORRETO PARA PTB 21.6
    loop.create_task(application.process_update(update))

    return "ok", 200


@app.route("/")
def home():
    return "Bot funcionando!", 200


# Configurar webhook
async def set_webhook():
    await application.bot.delete_webhook()
    await application.bot.set_webhook(f"{APP_URL}/webhook")
    print("Webhook configurado!")


# Inicializar PTB
loop.run_until_complete(application.initialize())
loop.run_until_complete(application.start())
loop.run_until_complete(set_webhook())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))