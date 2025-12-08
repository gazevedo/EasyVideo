import os
import httpx
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# ============================
# VARIÁVEIS DE AMBIENTE
# ============================
TOKEN = os.getenv("TOKEN")
APP_URL = os.getenv("APP_URL")

USE_PLAYWRIGHT = int(os.getenv("USE_PLAYWRIGHT", "0"))
SHOPEE_USERNAME = os.getenv("SHOPEE_USERNAME")
SHOPEE_PASSWORD = os.getenv("SHOPEE_PASSWORD")

app = FastAPI()

# Application global obrigatório
application = Application.builder().token(TOKEN).build()

# ============================
# 1) TIKTOK - API TIKWM
# ============================
async def baixar_tiktok(url: str):
    try:
        print(">> TIKTOK recebido:", url)

        async with httpx.AsyncClient(follow_redirects=True) as client:
            resolved = await client.get(url)
            final_url = str(resolved.url)

        print(">> TIKTOK URL resolvida:", final_url)

        api_url = "https://www.tikwm.com/api/"

        async with httpx.AsyncClient() as client:
            resp = await client.post(api_url, data={"url": final_url})

        print(">> RAW TIKWM RESPONSE:", resp.text)

        data = resp.json()

        if data.get("code") != 0:
            return None

        video_url = data["data"]["play"]

        async with httpx.AsyncClient(timeout=60) as client:
            video_bytes = await client.get(video_url)

        filename = "tiktok.mp4"
        with open(filename, "wb") as f:
            f.write(video_bytes.content)

        return filename

    except Exception as e:
        print(">> ERRO TIKTOK:", e)
        return None


# ============================
# 2) SHOPEE - APIs GRATUITAS
# ============================
async def tentar_shopee_api(url: str):
    api_list = [
        "https://api.saveshopee.com/v1/info?url=",
        "https://shopee-video-api.vercel.app/api?url=",
        "https://shopeeapi.up.railway.app/download?url=",
    ]

    async with httpx.AsyncClient(timeout=15) as client:
        for api in api_list:
            try:
                print(f">> Testando API SHOPEE: {api}")

                resp = await client.get(api + url)

                if resp.status_code != 200:
                    continue

                data = resp.json()

                mp4 = data.get("video_url") or data.get("url")

                if mp4:
                    print(">> SHOPEE vídeo encontrado:", mp4)

                    video_bytes = await client.get(mp4)
                    filename = "shopee.mp4"
                    with open(filename, "wb") as f:
                        f.write(video_bytes.content)
                    return filename

            except Exception as e:
                print(">> Erro API Shopee:", e)

    return None


# ============================
# 3) SHOPEE - PLAYWRIGHT
# ============================
async def baixar_shopee_playwright(url: str):
    print(">> SHOPEE usando Playwright")

    from playwright.async_api import async_playwright

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()

            page = await context.new_page()

            # Login
            await page.goto("https://shopee.com.br/buyer/login")

            await page.fill('input[name="loginKey"]', SHOPEE_USERNAME)
            await page.fill('input[name="password"]', SHOPEE_PASSWORD)

            await page.click('button[type="submit"]')
            await page.wait_for_timeout(3000)

            # Abre o link do vídeo
            await page.goto(url, wait_until="networkidle")

            video_url = await page.get_attribute("video", "src")

            if not video_url:
                print(">> Não encontrou o <video>")
                return None

            print(">> Vídeo Shopee encontrado:", video_url)

            async with httpx.AsyncClient() as client:
                bytes_video = await client.get(video_url)

            filename = "shopee.mp4"
            with open(filename, "wb") as f:
                f.write(bytes_video.content)

            return filename

    except Exception as e:
        print(">> ERRO PLAYWRIGHT SHOPEE:", e)
        return None


# ============================
# DECISÃO: QUAL DOWNLOAD USAR?
# ============================
async def processar_download(url: str):
    print(">> Processando URL:", url)

    # TIKTOK
    if "tiktok.com" in url:
        return await baixar_tiktok(url)

    # SHOPEE
    if "shp.ee" in url or "shopee.com" in url:
        print(">> SHOPEE detectado. Tentando APIs...")

        arquivo = await tentar_shopee_api(url)

        if arquivo:
            return arquivo

        print(">> APIs falharam. PLAYWRIGHT =", USE_PLAYWRIGHT)

        if USE_PLAYWRIGHT == 1:
            return await baixar_shopee_playwright(url)

        return None

    return None


# ============================
# HANDLERS TELEGRAM
# ============================
async def start(update: Update, context):
    await update.message.reply_text("Bot ativo! Envie um link TikTok ou Shopee.")


async def receber(update: Update, context):
    url = update.message.text

    if "http" not in url:
        return

    await update.message.reply_text("⏳ Baixando... aguarde...")

    arquivo = await processar_download(url)

    if not arquivo:
        await update.message.reply_text("❌ Não consegui baixar esse link.")
        return

    await update.message.reply_video(video=open(arquivo, "rb"))
    os.remove(arquivo)


application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT, receber))


# ============================
# WEBHOOK
# ============================
@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"ok": True}


# ============================
# STARTUP RENDER
# ============================
@app.on_event("startup")
async def on_startup():
    print(">> Inicializando o bot...")

    await application.initialize()

    webhook_url = f"{APP_URL}/webhook"
    print(">> Configurando Webhook:", webhook_url)

    await application.bot.set_webhook(webhook_url)
    await application.start()

    print(">> Bot iniciado e webhook ativo!")