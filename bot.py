import os
import httpx
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

TOKEN = "8010976316:AAEpXdsLrbUUKqye66OI41LrQaTEc7RAuAk"
APP_URL = "https://easyvideo.onrender.com"

app = FastAPI()

# ============================
# APPLICATION GLOBAL (OBRIGATÓRIO)
# ============================
application = Application.builder().token(TOKEN).build()


# ============================
# FUNÇÃO DE DOWNLOAD TIKTOK
# ============================
async def baixar_tiktok(url: str):
    """
    Baixa vídeo do TikTok usando API SnapTik, compatível com Render.
    """

    try:
        url = url.strip()  # remove \n e espaços

        print(">> Link recebido:", url)

        # 1) Resolver link encurtado
        async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
            resolved = await client.get(url)
            final_url = str(resolved.url)

        print(">> URL resolvida:", final_url)

        # 2) Consultar API SnapTik
        api_url = f"https://api.snaptik.app/v1/tiktok/video?url={final_url}"
        print(">> Consultando API:", api_url)

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(api_url)

        if resp.status_code != 200:
            print(">> ERRO API:", resp.text)
            return None

        data = resp.json()
        print(">> Resposta API:", data)

        video_url = data.get("video", {}).get("no_watermark")

        if not video_url:
            print(">> API não retornou vídeo válido")
            return None

        print(">> URL do vídeo:", video_url)

        # 3) Baixar o vídeo final
        async with httpx.AsyncClient(timeout=20) as client:
            video_bytes = await client.get(video_url)

        filename = "video_tiktok.mp4"
        with open(filename, "wb") as f:
            f.write(video_bytes.content)

        print(">> Vídeo salvo:", filename)
        return filename

    except Exception as e:
        print(">> ERRO NO DOWNLOAD:", e)
        return None


# ============================
# HANDLERS DO TELEGRAM
# ============================
async def start(update: Update, context):
    print(">> /start recebido")
    await update.message.reply_text("Bot online! Envie um link do TikTok.")


async def process_link(update: Update, context):
    text = update.message.text
    print(">> Mensagem recebida:", text)

    if "tiktok.com" not in text:
        await update.message.reply_text("Envie um link válido do TikTok.")
        return

    await update.message.reply_text("⏳ Baixando vídeo...")

    arquivo = await baixar_tiktok(text)

    if not arquivo:
        await update.message.reply_text("❌ Erro ao baixar o vídeo.")
        return

    await update.message.reply_video(video=open(arquivo, "rb"))
    os.remove(arquivo)


# Registrar handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_link))


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
# STARTUP ESSENCIAL NO RENDER
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