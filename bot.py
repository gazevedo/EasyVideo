import os
import httpx
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# ==========================================
# VARIÁVEIS DE AMBIENTE
# ==========================================
TOKEN = os.getenv("TOKEN")
APP_URL = os.getenv("APP_URL")
USE_PLAYWRIGHT = int(os.getenv("USE_PLAYWRIGHT", "1"))  # 1 = usar Playwright se APIs falharem

app = FastAPI()

# ==========================================
# TELEGRAM APPLICATION GLOBAL
# ==========================================
application = Application.builder().token(TOKEN).build()

# ==========================================
# 1) TIKTOK via API TIKWM
# ==========================================
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


# ==========================================
# 2) SHOPEE — TENTAR VÁRIAS APIS
# ==========================================
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
                    print(">> SHOPEE vídeo encontrado via API:", mp4)

                    video_bytes = await client.get(mp4)
                    filename = "shopee.mp4"
                    with open(filename, "wb") as f:
                        f.write(video_bytes.content)
                    return filename

            except Exception as e:
                print(">> Erro API Shopee:", e)

    return None


# ==========================================
# 3) SHOPEE — PLAYWRIGHT (SEM LOGIN)
# ==========================================
async def baixar_shopee_playwright(url: str):
    print(">> SHOPEE usando Playwright (modo sem login)")

    from playwright.async_api import async_playwright

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            # abre o link
            await page.goto(url, wait_until="networkidle")

            # procura o player
            video_elem = page.locator("video")

            if await video_elem.count() == 0:
                print(">> Nenhum <video> encontrado na página Shopee")
                return None

            video_url = await video_elem.get_attribute("src")

            if not video_url:
                print(">> O <video> existe, mas não possui SRC")
                return None

            print(">> Vídeo encontrado via Playwright:", video_url)

            async with httpx.AsyncClient() as client:
                video_bytes = await client.get(video_url)

            filename = "shopee.mp4"
            with open(filename, "wb") as f:
                f.write(video_bytes.content)

            return filename

    except Exception as e:
        print(">> ERRO PLAYWRIGHT SHOPEE:", e)
        return None


# ==========================================
# 4) DECISÃO DE DOWNLOAD
# ==========================================
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


# ==========================================
# 5) HANDLERS TELEGRAM
# ==========================================
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


# ==========================================
# 6) WEBHOOK
# ==========================================
@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"ok": True}


# ==========================================
# 7) STARTUP NO RENDER
# ==========================================
@app.on_event("startup")
async def on_startup():
    print(">> Inicializando o bot...")

    await application.initialize()

    webhook_url = f"{APP_URL}/webhook"
    print(">> Configurando Webhook:", webhook_url)

    await application.bot.set_webhook(webhook_url)
    await application.start()

    print(">> Bot iniciado e webhook ativo!")