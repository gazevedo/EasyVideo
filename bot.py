import os
import asyncio
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

TOKEN = "8010976316:AAEpXdsLrbUUKqye66OI41LrQaTEc7RAuAk"
APP_URL = "https://easyvideo.onrender.com"

app = FastAPI()

# --- cria a aplicação do Telegram
application = Application.builder().token(TOKEN).build()

# --- handler do /start
async def start(update: Update, context):
    print("Recebi /start de:", update.effective_user.id)
    await update.message.reply_text("Hello World!")

# --- handler para qualquer mensagem
async def echo(update: Update, context):
    print("Mensagem recebida:", update.message.text)
    await update.message.reply_text("Recebido!")

application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

# --- ROUTE DO WEBHOOK
@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    print("Webhook recebeu:", data)

    update = Update.de_json(data, application.bot)
    await application.process_update(update)

    return {"status": "ok"}

@app.get("/")
async def home():
    return {"status": "running"}

# --- CONFIGURA O WEBHOOK AO INICIAR ---
async def set_webhook():
    url = f"{APP_URL}/webhook"
    print("Configurando webhook:", url)
    await application.bot.set_webhook(url)

@app.on_event("startup")
async def startup_event():
    await set_webhook()