import os
import re
import httpx
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

TOKEN = "8010976316:AAEpXdsLrbUUKqye66OI41LrQaTEc7RAuAk"
APP_URL = "https://easyvideo.onrender.com"

app = FastAPI()

application = Application.builder().token(TOKEN).build()

URL_REGEX = r"(https?://[^\s]+)"


# ============================
# SHOPEE DOWNLOADER
# ============================
async def baixar_shopee(url: str):
    try:
        api = f"https://shopee-api.naikmimpi.my.id/?url={url}"
        print(">> Consultando API SHOPEE:", api)

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(api)

        print(">> RAW SHOPEE RESPONSE:", resp.text)

        if resp.status_code != 200:
            return None

        data = resp.json()
        if data.get("status") != "success":
            return None

        result = data.get("result", {})

        # Coleta imagens e vídeo
        images = result.get("images", [])
        video = result.get("video_url")

        return {"images": images, "video": video}

    except Exception as e:
        print(">> ERRO SHOPEE:", e)
        return None


# ============================
# TIKTOK DOWNLOADER (TIKWM)
# ============================
async def baixar_tiktok(url: str):
    try:
        url = url.strip()
        print(">> Link recebido:", url)

        async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
            resolved = await client.get(url)
            final_url = str(resolved.url)

        print(">> URL resolvida:", final_url)

        api_url = "https://www.tikwm.com/api/"

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(api_url, data={"url": final_url})

        print(">> RAW API RESPONSE:", resp.text)

        data = resp.json()
        if data.get("code") != 0:
            return None

        video_url = data["data"]["play"]

        async with httpx.AsyncClient(timeout=30) as client:
            video_bytes = await client.get(video_url)

        filename = "video_tiktok.mp4"
        with open(filename, "wb") as f:
            f.write(video_bytes.content)

        return filename

    except Exception as e:
        print(">> ERRO NO DOWNLOAD:", e)
        return None


# ============================
# PROCESSADOR DE MENSAGEM
# ============================
async def process_message(update: Update, context):
    text = update.message.text.strip()
    print(">> Mensagem recebida:", text)

    match = re.search(URL_REGEX, text)
    if not match:
        return

    link = match.group(1)
    print(">> Link detectado:", link)

    # ---------- SHOPEE ----------
    if "shopee.com" in link:
        await update.message.reply_text("🛒 Baixando mídia da Shopee...")

        data = await baixar_shopee(link)
        if not data:
            await update.message.reply_text("❌ Não consegui baixar mídia da Shopee.")
            return

        # Vídeo
        if data.get("video"):
            async with httpx.AsyncClient() as client:
                video_bytes = await client.get(data["video"])
            with open("shopee_video.mp4", "wb") as f:
                f.write(video_bytes.content)

            await update.message.reply_video(video=open("shopee_video.mp4", "rb"))
            os.remove("shopee_video.mp4")

        # Imagens
        for i, img in enumerate(data.get("images", [])):
            async with httpx.AsyncClient() as client:
                img_bytes = await client.get(img)

            filename = f"shopee_img_{i}.jpg"
            with open(filename, "wb") as f:
                f.write(img_bytes.content)

            await update.message.reply_photo(photo=open(filename, "rb"))
            os.remove(filename)

        return

    # ---------- TIKTOK ----------
    if "tiktok.com" in link or "vt.tiktok.com" in link:
        await update.message.reply_text("🎥 Baixando vídeo do TikTok...")

        arquivo = await baixar_tiktok(link)
        if not arquivo:
            await update.message.reply_text("❌ Erro ao baixar o vídeo.")
            return

        await update.message.reply_video(video=open(arquivo, "rb"))
        os.remove(arquivo)
        return

    # ---------- QUALQUER OUTRO LINK ----------
    await update.message.reply_text(f"🔗 Link recebido:\n{link}")


# Registrar handlers
application.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("Bot online!")))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_message))


# ============================
# WEBHOOK
# ============================
@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"status": "ok"}


@app.get("/")
async def home():
    return {"status": "running"}


@app.on_event("startup")
async def on_startup():
    print(">> Inicializando bot...")
    await application.initialize()
    await application.bot.set_webhook(f"{APP_URL}/webhook")
    await application.start()
    print(">> Bot ativo!")