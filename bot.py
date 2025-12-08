import os
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


# =============================================
#  TIKTOK — API TIKWM (FUNCIONA 100%)
# =============================================
async def baixar_tiktok(url: str):
    try:
        print(">> TIKTOK link recebido:", url)

        # 1) Resolvendo link encurtado
        async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
            resolved = await client.get(url)
            final_url = str(resolved.url)

        print(">> TIKTOK URL resolvida:", final_url)

        # 2) API
        api_url = "https://www.tikwm.com/api/"
        print(">> Enviando para API TIKWM")

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(api_url, data={"url": final_url})

        print(">> RAW TIKWM RESPONSE:", resp.text)

        data = resp.json()

        if data.get("code") != 0:
            return None

        video_url = data["data"]["play"]

        print(">> Vídeo final do TikTok:", video_url)

        async with httpx.AsyncClient(timeout=30) as client:
            video_bytes = await client.get(video_url)

        filename = "video_tiktok.mp4"
        with open(filename, "wb") as f:
            f.write(video_bytes.content)

        return filename

    except Exception as e:
        print(">> ERRO TIKTOK:", e)
        return None


# =============================================
# LISTA DE APIs GRATUITAS SHOPEE (tentativa múltipla)
# =============================================
async def baixar_shopee(url: str):
    print(">> SHOPEE: resolvendo link:", url)

    # 1) Resolver URL encurtada
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
            resolved = await client.get(url)
            final_url = str(resolved.url)
        print(">> SHOPEE URL final:", final_url)
    except:
        print(">> Não consegui resolver o link da Shopee.")
        final_url = url

    # ============================
    # TENTATIVA 1 — SaveShopee API
    # ============================
    try:
        api1 = f"https://api.saveshopee.com/v1/info?url={final_url}"
        print(">> Consultando API SHOPEE #1:", api1)

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(api1)

        data = resp.json()
        if "video_url" in data:
            video = data["video_url"]

            print(">> SHOPEE #1 OK — baixando vídeo:", video)

            async with httpx.AsyncClient(timeout=30) as client:
                video_bytes = await client.get(video)

            filename = "shopee_video.mp4"
            with open(filename, "wb") as f:
                f.write(video_bytes.content)

            return filename
    except Exception as e:
        print(">> ERRO SHOPEE #1:", e)

    # ============================
    # TENTATIVA 2 — vercel.app API
    # ============================
    try:
        api2 = f"https://shopee-video-api.vercel.app/api?url={final_url}"
        print(">> Consultando API SHOPEE #2:", api2)

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(api2)

        data = resp.json()
        if "url" in data:
            video = data["url"]

            print(">> SHOPEE #2 OK — baixando vídeo:", video)

            async with httpx.AsyncClient(timeout=30) as client:
                video_bytes = await client.get(video)

            filename = "shopee_video.mp4"
            with open(filename, "wb") as f:
                f.write(video_bytes.content)

            return filename
    except Exception as e:
        print(">> ERRO SHOPEE #2:", e)

    # ============================
    # TENTATIVA 3 — Railway API
    # ============================
    try:
        api3 = f"https://shopeeapi.up.railway.app/download?url={final_url}"
        print(">> Consultando API SHOPEE #3:", api3)

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(api3)

        data = resp.json()
        if data.get("success") and "file" in data:
            video = data["file"]

            print(">> SHOPEE #3 OK:", video)

            async with httpx.AsyncClient(timeout=30) as client:
                video_bytes = await client.get(video)

            filename = "shopee_video.mp4"
            with open(filename, "wb") as f:
                f.write(video_bytes.content)

            return filename
    except Exception as e:
        print(">> ERRO SHOPEE #3:", e)

    return None


# =============================================
# HANDLER PRINCIPAL — detecta qualquer link
# =============================================
async def process_link(update: Update, context):
    text = update.message.text
    print(">> Mensagem recebida:", text)

    # Filtrar URL
    if not text.startswith("http"):
        return

    await update.message.reply_text("🔍 Processando link...")

    # TIKTOK
    if "tiktok.com" in text:
        arquivo = await baixar_tiktok(text)
        if arquivo:
            await update.message.reply_video(video=open(arquivo, "rb"))
            os.remove(arquivo)
            return
        else:
            await update.message.reply_text("❌ Erro ao baixar vídeo do TikTok.")
            return

    # SHOPEE
    if "shopee" in text or "shp.ee" in text:
        arquivo = await baixar_shopee(text)
        if arquivo:
            await update.message.reply_video(video=open(arquivo, "rb"))
            os.remove(arquivo)
            return
        else:
            await update.message.reply_text("❌ Não consegui baixar o vídeo da Shopee.")
            return

    await update.message.reply_text("Não reconheço este tipo de link.")


# Registrar handlers
application.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("Bot ativo!")))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_link))


# =============================================
# WEBHOOK
# =============================================
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


# =============================================
# STARTUP
# =============================================
@app.on_event("startup")
async def on_startup():
    print(">> Inicializando o bot...")

    await application.initialize()
    webhook_url = f"{APP_URL}/webhook"
    print(">> Configurando Webhook:", webhook_url)
    await application.bot.set_webhook(webhook_url)
    await application.start()

    print(">> Bot iniciado e webhook ativo!")