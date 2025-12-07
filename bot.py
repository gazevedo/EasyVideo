import os
import httpx
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

TOKEN = "8010976316:AAEpXdsLrbUUKqye66OI41LrQaTEc7RAuAk"
APP_URL = "https://easyvideo.onrender.com"

app = FastAPI()

# ============================================================
# APPLICATION GLOBAL (OBRIGATÓRIO)
# ============================================================
application = Application.builder().token(TOKEN).build()


# ============================================================
# FUNÇÃO TIKTOK — VIA TIKWM (FUNCIONANDO)
# ============================================================
async def baixar_tiktok(url: str):
    try:
        url = url.strip()
        print(">> TIKTOK link recebido:", url)

        # Resolver link encurtado
        async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
            r = await client.get(url)
            final_url = str(r.url)

        print(">> TIKTOK URL resolvida:", final_url)

        # API TIKWM
        api = "https://www.tikwm.com/api/"
        print(">> Enviando para API TIKWM")

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(api, data={"url": final_url})

        print(">> RAW TIKWM RESPONSE:", resp.text)

        data = resp.json()

        if data.get("code") != 0:
            print(">> TIKWM erro:", data)
            return None

        video_url = data["data"]["play"]
        print(">> Vídeo final do TikTok:", video_url)

        # Baixar vídeo
        async with httpx.AsyncClient(timeout=30) as client:
            video_bytes = await client.get(video_url)

        filename = "video_tiktok.mp4"
        with open(filename, "wb") as f:
            f.write(video_bytes.content)

        return filename

    except Exception as e:
        print(">> ERRO TIKTOK:", e)
        return None


# ============================================================
# FUNÇÃO SHOPEE — 100% FUNCIONAL (VÍDEO SEM MARCA D’ÁGUA)
# ============================================================
async def baixar_shopee(url: str):
    try:
        print(">> SHOPEE: resolvendo link:", url)

        # Resolver redirecionamentos (shp.ee, encurtados etc)
        async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
            r = await client.get(url)
            final_url = str(r.url)

        print(">> SHOPEE URL final:", final_url)

        # API SaveShopee
        api = f"https://api.saveshopee.com/v1/info?url={final_url}"
        print(">> Consultando API SHOPEE:", api)

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(api)

        print(">> RAW SHOPEE API:", resp.text)

        data = resp.json()

        if data.get("status") != "success":
            print(">> Erro na API Shopee:", data)
            return None

        product = data.get("result", {})

        return {
            "video": product.get("video_url"),
            "images": product.get("images", [])
        }

    except Exception as e:
        print(">> ERRO SHOPEE:", e)
        return None


# ============================================================
# HANDLERS TELEGRAM
# ============================================================
async def start(update: Update, context):
    await update.message.reply_text("Bot online! Envie links do TikTok ou Shopee.")


async def process_link(update: Update, context):
    text = update.message.text.strip()
    print(">> Mensagem recebida:", text)

    # --------------------------------------------
    # SHOPEE
    # --------------------------------------------
    if any(x in text for x in ["shopee", "shp.ee", "shp.com"]):
        await update.message.reply_text("🛒 Baixando mídia da Shopee...")

        data = await baixar_shopee(text)
        if not data:
            await update.message.reply_text("❌ Não consegui baixar da Shopee.")
            return

        # vídeo primeiro
        if data.get("video"):
            async with httpx.AsyncClient() as client:
                r = await client.get(data["video"])
            with open("shopee_video.mp4", "wb") as f:
                f.write(r.content)

            await update.message.reply_video(video=open("shopee_video.mp4", "rb"))
            os.remove("shopee_video.mp4")

        # imagens
        for i, img in enumerate(data.get("images", [])):
            async with httpx.AsyncClient() as client:
                r = await client.get(img)
            name = f"shopee_img_{i}.jpg"
            with open(name, "wb") as f:
                f.write(r.content)
            await update.message.reply_photo(photo=open(name, "rb"))
            os.remove(name)

        return

    # --------------------------------------------
    # TIKTOK
    # --------------------------------------------
    if "tiktok.com" in text or "vt.tiktok.com" in text:
        await update.message.reply_text("🎥 Baixando vídeo do TikTok...")

        arquivo = await baixar_tiktok(text)
        if not arquivo:
            await update.message.reply_text("❌ Não consegui baixar o vídeo do TikTok.")
            return

        await update.message.reply_video(video=open(arquivo, "rb"))
        os.remove(arquivo)
        return

    # Se for link mas não TikTok ou Shopee
    if text.startswith("http"):
        await update.message.reply_text("🔗 Link recebido, mas não reconheço a plataforma.")
        return


# Registrar handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_link))


# ============================================================
# WEBHOOK
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
# STARTUP RENDER
# ============================================================
@app.on_event("startup")
async def on_startup():
    print(">> Inicializando o bot...")

    await application.initialize()

    webhook_url = f"{APP_URL}/webhook"
    print(">> Configurando Webhook:", webhook_url)

    await application.bot.set_webhook(webhook_url)
    await application.start()

    print(">> Bot iniciado e webhook ativo!")