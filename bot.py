import os
import re
import httpx
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

TOKEN = "8010976316:AAEpXdsLrbUUKqye66OI41LrQaTEc7RAuAk"
APP_URL = "https://easyvideo.onrender.com"

app = FastAPI()

# ============================
# APPLICATION GLOBAL
# ============================
application = Application.builder().token(TOKEN).build()

# Regex universal para detectar links
URL_REGEX = r"(https?://[^\s]+)"


# ============================
# FUNÇÃO: Baixar TikTok (TIKWM)
# ============================
async def baixar_tiktok(url: str):
    try:
        url = url.strip()
        print(">> Link recebido:", url)

        # Resolver link encurtado
        async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
            resolved = await client.get(url)
            final_url = str(resolved.url)

        print(">> URL resolvida:", final_url)

        # Consultar API TIKWM
        api_url = "https://www.tikwm.com/api/"
        print(">> Enviando para API:", api_url)

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(api_url, data={"url": final_url})

        print(">> RAW API RESPONSE:", resp.text)

        data = resp.json()

        if data.get("code") != 0:
            print(">> API retornou erro:", data)
            return None

        video_url = data["data"]["play"]
        print(">> URL final do vídeo:", video_url)

        # Baixar vídeo
        async with httpx.AsyncClient(timeout=30) as client:
            video_bytes = await client.get(video_url)

        filename = "video_tiktok.mp4"
        with open(filename, "wb") as f:
            f.write(video_bytes.content)

        print(">> Arquivo salvo:", filename)
        return filename

    except Exception as e:
        print(">> ERRO NO DOWNLOAD:", e)
        return None


# ============================
# HANDLERS TELEGRAM
# ============================
async def start(update: Update, context):
    print(">> /start recebido")
    await update.message.reply_text("Bot online! Envie qualquer link.")


async def process_message(update: Update, context):
    text = update.message.text.strip()
    print(">> Mensagem recebida:", text)

    # ---------- Só responde se houver link ----------
    match = re.search(URL_REGEX, text)
    if not match:
        print(">> Mensagem ignorada (não contém link)")
        return  # <-- IGNORA SEM RESPONDER

    link = match.group(1)
    print(">> Link detectado:", link)

    # Se for link do TikTok → baixa vídeo
    if "tiktok.com" in link or "vt.tiktok.com" in link:
        await update.message.reply_text("⏳ Baixando vídeo do TikTok...")

        arquivo = await baixar_tiktok(link)
        if not arquivo:
            await update.message.reply_text("❌ Erro ao baixar o vídeo.")
            return

        await update.message.reply_video(video=open(arquivo, "rb"))
        os.remove(arquivo)
        return

    # Se for qualquer outro link → responde normal
    await update.message.reply_text(f"🔗 Link recebido:\n{link}")


# Registrar handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_message))


# ============================
# WEBHOOK
# ============================
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


# ============================
# STARTUP RENDER
# ============================
@app.on_event("startup")
async def on_startup():
    print(">> Inicializando o bot...")

    await application.initialize()

    webhook_url = f"{APP_URL}/webhook"
    print(">> Configurando webhook:", webhook_url)

    await application.bot.set_webhook(webhook_url)
    await application.start()

    print(">> Bot iniciado e webhook ativo!")