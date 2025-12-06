from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler
import asyncio

TOKEN = "8010976316:AAEpXdsLrbUUKqye66OI41LrQaTEc7RAuAk"
WEBHOOK_URL = "https://easyvideo.onrender.com/webhook"

app = Flask(__name__)
bot = Bot(token=TOKEN)

# Application (handler engine)
application = Application.builder().token(TOKEN).build()

# Comando /start
async def start(update: Update, context):
    await update.message.reply_text("Hello World!")

application.add_handler(CommandHandler("start", start))

# Rota do webhook (Render chama aqui)
@app.post("/webhook")
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, bot)
    asyncio.run(application.process_update(update))
    return "OK", 200

# Rota inicial (Render verifica vivo)
@app.get("/")
def index():
    return "Bot running (Hello World)!", 200

# Seta o webhook na inicialização
async def set_webhook():
    await bot.delete_webhook()
    await bot.set_webhook(url=WEBHOOK_URL)

@app.before_first_request
def activate_webhook():
    asyncio.run(set_webhook())