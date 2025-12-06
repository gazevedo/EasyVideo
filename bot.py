from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from flask import Flask, request

TOKEN = "8010976316:AAEpXdsLrbUUKqye66OI41LrQaTEc7RAuAk"

app = Flask(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello World!")

@app.post("/webhook")
def webhook():
    application = app.config.get("application")
    if application:
        application.process_update(Update.de_json(request.json, application.bot))
    return "OK", 200

def main():
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))

    # Salvar aplicação Flask
    app.config["application"] = application

    # Iniciar polling em background para evitar timeout do Render
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()