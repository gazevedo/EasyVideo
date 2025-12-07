import os
import asyncio
from fastapi import FastAPI, Request
import uvicorn
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

TOKEN = "8010976316:AAEpXdsLrbUUKqye66OI41LrQaTEc7RAuAk"
APP_URL = "https://easyvideo.onrender.com"

app = FastAPI()

# --- Criar Application ---
application = ApplicationBuilder().token(TOKEN).build()

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(">>> RECEBIDO /start DE:", update.message.from_user.id)
    print(">>> TEXTO:", update.message.text)

    await update.message.reply_text("Hello World!")

    print(">>> RESPOSTA ENVIADA: Hello World!")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user.id
    msg = update.message.text

    print(">>> MENSAGEM RECEBIDA:")
    print("    Usuário:", user)
    print("    Texto:", msg)

    resposta = f"Você disse: {msg}"
    await update.message.reply_text(resposta)

    print(">>> RESPOSTA ENVIADA:", resposta)


# Registrar handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))


# --- Webhook ---
@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()

    print(">>> PACOTE JSON RECEBIDO NO WEBHOOK:")
    print(data)

    update = Update.de_json(data, application.bot)
    await application.process_update(update)

    return {"ok": True}


@app.get("/")
async def root():
    return {"status": "ok"}


# --- Configurar webhook no início ---
async def set_webhook():
    url = f"{APP_URL}/webhook"
    await application.bot.set_webhook(url)
    print(">>> WEBHOOK DEFINIDO PARA:", url)


asyncio.get