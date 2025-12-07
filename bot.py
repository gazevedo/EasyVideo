import os
import httpx
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

TOKEN = "8010976316:AAEpXdsLrbUUKqye66OI41LrQaTEc7RAuAk"
APP_URL = "https://easyvideo.onrender.com"

app = FastAPI()

# =====================================================================
# APPLICATION GLOBAL
# =====================================================================
application = Application.builder().token(TOKEN).build()


# =====================================================================
# DOWNLOAD TIKTOK - API TIKWM
# =====================================================================
async def baixar_tiktok(url: str):
    try:
        url = url.strip()

        print(">> TIKTOK link recebido:", url)

        # Resolver URL encurtada
        async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
            r = await client.get(url)
            final_url = str(r.url)

        print(">> TIKTOK URL resolvida:", final_url)

        api = "https://www.tikwm.com/api/"

        print(">> Enviando para API TIKWM")
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(api, data={"url": final_url})

        print(">> RAW TIKWM RESPONSE:", resp.text)

        data = resp.json()

        if data.get("code") != 0:
            print(">> Erro TIKWM:", data)
            return None

        video_url = data["data"]["play"]
        print(">> Vídeo final do TikTok:", video_url)

        # Baixar vídeo
        async with httpx.AsyncClient(timeout=30) as client:
            video_data = await client.get(video_url)

        filename = "video_tiktok.mp4"
        with open(filename, "wb") as f:
            f.write(video_data.content)

        return filename

    except Exception as e:
        print(">> ERRO NO TIKTOK:", e)
        return None


# =====================================================================
# DOWNLOAD SHOPEE (FUNCIONA)
# Snaptik API — https://api.snaptik.app/api/v1/shopee
# =====================================================================
async def baixar_shopee(url: str):
    try:
        print(">> SHOPEE: resolvendo link:", url)

        async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
            r = await client.get(url)
            final_url = str(r.url)

        print(">> SHOPEE URL final:", final_url)

        api = f"https://api.snaptik.app/api/v1/shopee?url={final_url}"
        print(">> Consultando API SHOPEE:", api)

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(api)

        print(">> RAW RESP SHOPEE:", resp.text)

        data = resp.json()

        if data.get("status") != "success":
            print(">> API Shopee retornou erro:", data)
            return None

        info = data.get("data", {})

        video = info.get("video")
        images = info.get("images", [])

        return {
            "video": video,
            "images": images
        }

    except Exception as e:
        print(">> ERRO SHOPEE:", e)
        return None


# =====================================================================
# HANDLERS DO TELEGRAM
# =====================================================================
async def start(update: Update, context):
    await update.message.reply_text("Bot online! Envie link do TikTok ou Shopee.")


async def process_message(update: Update, context):
    text = update.message.text
    print(">> Mensagem recebida:", text)

    # Detectar link
    import re
    urls = re.findall(r'(https?://\S+)', text)

    if not urls:
        return  # ignora mensagens sem links

    url = urls[0]
    print(">> Link detectado:", url)

    # ============================
    # PROCESSAR SHOPEE
    # ============================
    if "shp.ee" in url or "shopee.com" in url:
        await update.message.reply_text("⏳ Processando link da Shopee...")
        resultado = await baixar_shopee(url)

        if not resultado:
            await update.message.reply_text("❌ Não consegui baixar conteúdo da Shopee.")
            return

        # Se tiver vídeo
        if resultado["video"]:
            async with httpx.AsyncClient() as client:
                v = await client.get(resultado["video"])
            filename = "shopee_video.mp4"
            with open(filename, "wb") as f:
                f.write(v.content)

            await update.message.reply_video(video=open(filename, "rb"))
            os.remove(filename)
            return

        # Apenas imagens
        if resultado["images"]:
            for img in resultado["images"]:
                await update.message.reply_photo(photo=img)
            return

        await update.message.reply_text("Não encontrei vídeo ou imagens.")
        return

    # ============================
    # PROCESSAR TIKTOK
    # ============================
    if "tiktok.com" in url:
        await update.message.reply_text("⏳ Baixando vídeo do TikTok...")
        arquivo = await baixar_tiktok(url)

        if not arquivo:
            await update.message.reply_text("❌ Erro ao baixar vídeo do TikTok.")
            return

        await update.message.reply_video(video=open(arquivo, "rb"))
        os.remove(arquivo)
        return


# Registrar handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_message))


# =====================================================================
# WEBHOOK
# =====================================================================
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


# =====================================================================
# STARTUP DO RENDER
# =====================================================================
@app.on_event("startup")
async def on_startup():
    print(">> Inicializando o bot...")

    await application.initialize()

    webhook_url = f"{APP_URL}/webhook"
    print(">> Configurando Webhook:", webhook_url)
    await application.bot.set_webhook(webhook_url)

    await application.start()

    print(">> Bot iniciado e webhook ativo!")