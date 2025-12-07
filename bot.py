import os
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

TOKEN = "8010976316:AAEpXdsLrbUUKqye66OI41LrQaTEc7RAuAk"
APP_URL = "https://easyvideo.onrender.com"

app = FastAPI()

# Criar Application global
application = Application.builder().token(TOKEN).build()


# ---------------------- HANDLERS --------------------------
async def start(update: Update, context):
    print(">> START recebido de:", update.effective_user.id)
    await update.message.reply_text("Bot online! Pode enviar mensagens.")


async def echo(update: Update, context):
    print(">> Mensagem recebida:", update.message.text)
    await update.message.reply_text("Recebido: " + update.message.text)


application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))


# ---------------------- WEBHOOK ----------------------------
@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    print(">> RAW UPDATE:", data)

    update = Update.de_json(data, application.bot)
    await application.process_update(update)

    return {"status": "ok"}


@app.get("/")
async def home():
    return {"status": "running"}


# ---------------------- STARTUP (ESSENCIAL!) ----------------
@app.on_event("startup")
async def on_startup():
    print(">> Inicializando o bot...")

    # Inicializa as tarefas internas do PTB (necessário para webhook)
    await application.initialize()

    # Configura webhook
    webhook_url = f"{APP_URL}/webhook"
    print(">> Configurando webhook para:", webhook_url)
    await application.bot.set_webhook(webhook_url)

    # Inicia o Application (necessário para process_update funcionar)
    await application.start()

    print(">> Bot iniciado e webhook ativo!")