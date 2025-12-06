from telegram.ext import ApplicationBuilder, MessageHandler, filters

TOKEN = "8010976316:AAEpXdsLrbUUKqye66OI41LrQaTEc7RAuAk"

async def responder(update, context):
    texto = update.message.text.lower()
    if texto == "oi":
        await update.message.reply_text("Oi! Tudo funcionando 😄")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))

app.run_polling()