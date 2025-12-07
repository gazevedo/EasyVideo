import os
import httpx
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

TOKEN = "8010976316:AAEpXdsLrbUUKqye66OI41LrQaTEc7RAuAk"
APP_URL = "https://easyvideo.onrender.com"

app = FastAPI()

# Criar Application global
application = Application.builder().token(TOKEN).build()


# ============================================================
# ---------------------- HANDLERS -----------------------------
# ============================================================

async def start(update: Update, context):
    print(">> START recebido de:", update.effective_user.id)
    await update.message.reply_text("Bot online! Envie qualquer texto ou link do TikTok.")


async def echo(update: Update, context):
    msg = update.message.text
    print(">> Mensagem recebida:", msg)

    # --- Detecta se é link TikTok ---
    if "tiktok.com" in msg:
        await update.message.reply_text("⏳ Baixando vídeo do TikTok...")

        video_path = await baixar_tiktok(msg)

        if video_path:
            print(">> Enviando vídeo baixado:", video_path)
            await update.message.reply_video(video=open(video_path, "rb"))
            os.remove(video_path)
        else:
            await update.message.reply_text("❌ Erro ao baixar o vídeo.")

        return

    # Se não for TikTok → resposta normal
    await update.message.reply_text("Recebido: " + msg)


application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))


# ============================================================
# ------------------ FUNÇÃO DOWNLOAD TIKTOK ------------------
# ============================================================

async def baixar_tiktok(url: str):
    """
    Faz download de vídeo TikTok sem marca d’água.
    Usa API estável: https://api.tikmate.app
    """

    try:
        # 1) Resolve a URL final (short links dai / vt)
        async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
            final_url = (await client.get(url)).url.__str__()
            print(">> URL resolvida:", final_url)

        # 2) Pega ID do vídeo
        video_id = final_url.split("/video/")[1].split("?")[0]

        api_url = f"https://api.tikmate.app/api/lookup?url={final_url}"
        print(">> Consultando API:", api_url)

        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(api_url)
            info = r.json()

        if "token" not in info:
            print(">> Erro API Tikmate:", info)
            return None

        token = info["token"]
        download_url = f"https://tikmate.app/download/{token}/{video_id}.mp4"
        print(">> URL de download:", download_url)

        # 3) Baixar arquivo
        async with httpx.AsyncClient(timeout=20) as client:
            video_bytes = await client.get(download_url)

        filename = f"tiktok_{video_id}.mp4"
        with open(filename, "wb") as f:
            f.write(video_bytes.content)

        print(">> Vídeo salvo:", filename)
        return filename

    except Exception as e:
        print(">> ERRO NO DOWNLOAD:", e)
        return None


# ============================================================
# ---------------------- WEBHOOK ------------------------------
# ============================================================

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


# ============================================================
# ---------------------- STARTUP ------------------------------
# ============================================================

@app.on_event("startup")
async def on_startup():
    print(">> Inicializando o bot...")

    await application.initialize()

    webhook_url = f"{APP_URL}/webhook"
    print(">> Configurando webhook para:", webhook_url)
    await application.bot.set_webhook(webhook_url)

    await application.start()

    print(">> Bot iniciado e webhook ativo!")