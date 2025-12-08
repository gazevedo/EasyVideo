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

MP4_RE = re.compile(r"https?://[^\s\"']+\.mp4")


# ============================================================
# FUNÇÃO TIKTOK — 100% FUNCIONAL (TIKWM)
# ============================================================
async def baixar_tiktok(url: str):
    try:
        url = url.strip()
        print(">> TIKTOK link recebido:", url)

        async with httpx.AsyncClient(follow_redirects=True, timeout=20) as c:
            resolved = await c.get(url)
        final_url = str(resolved.url)
        print(">> TIKTOK URL resolvida:", final_url)

        api = "https://www.tikwm.com/api/"
        print(">> Enviando para API TIKWM")

        async with httpx.AsyncClient(timeout=20) as c:
            resp = await c.post(api, data={"url": final_url})

        print(">> RAW TIKWM RESPONSE:", resp.text)

        data = resp.json()
        if data.get("code") != 0:
            print(">> ERRO TIKWM:", data)
            return None

        video_url = data["data"]["play"]
        print(">> Vídeo final do TikTok:", video_url)

        async with httpx.AsyncClient(timeout=30) as c:
            video_bytes = await c.get(video_url)

        fname = "tiktok_video.mp4"
        with open(fname, "wb") as f:
            f.write(video_bytes.content)

        return fname

    except Exception as e:
        print(">> ERRO TIKTOK:", e)
        return None


# ============================================================
# FUNÇÃO SHOPEE — VERSÃO CORRIGIDA (SEM ?R)
# ============================================================
async def baixar_shopee(url: str):
    try:
        url = url.strip()
        print(">> SHOPEE: recebendo link:", url)

        # 1) Resolver redirecionamento
        async with httpx.AsyncClient(follow_redirects=True, timeout=20) as c:
            r = await c.get(url)
        final = str(r.url)
        print(">> SHOPEE URL final resolvida:", final)

        # 2) Tenta baixar a página
        async with httpx.AsyncClient(timeout=20) as c:
            page = await c.get(final)

        html = page.text
        print(">> SHOPEE: HTML recebido, tamanho:", len(html))

        # 3) Procurar mp4 direto no HTML
        direct = MP4_RE.findall(html)
        if direct:
            print(">> SHOPEE: achou mp4 direto no HTML:", direct[0])
            return await _save_remote_video(direct[0])

        # 4) Procurar mp4 em scripts e atributos (NOVA FUNÇÃO SEM ?R)
        script_blocks = re.findall(r"<script[^>]*>(.*?)</script>", html, flags=re.DOTALL)
        data_attrs = re.findall(r"data-[a-zA-Z0-9_-]+=\"(.*?)\"", html)

        for block in script_blocks + data_attrs:
            if ".mp4" in block:
                found = MP4_RE.findall(block)
                if found:
                    print(">> SHOPEE: achou mp4 em script/data:", found[0])
                    return await _save_remote_video(found[0])

        print(">> SHOPEE: nenhum mp4 encontrado")
        return None

    except Exception as e:
        print(">> ERRO SHOPEE geral:", e)
        return None


# Função auxiliar para salvar vídeo
async def _save_remote_video(url):
    try:
        print(">> Baixando vídeo remoto:", url)
        async with httpx.AsyncClient(timeout=30) as c:
            vid = await c.get(url)

        fname = "shopee_video.mp4"
        with open(fname, "wb") as f:
            f.write(vid.content)

        print(">> Vídeo salvo:", fname)
        return fname

    except Exception as e:
        print(">> ERRO AO SALVAR VÍDEO:", e)
        return None


# ============================================================
# PROCESSADOR ÚNICO DE LINKS
# ============================================================
async def processar_link(update: Update, context):
    msg = update.message.text
    print(f">> Mensagem recebida de {update.effective_user.id}: {msg}")

    # Detecta link
    urls = re.findall(r"https?://\S+", msg)
    if not urls:
        await update.message.reply_text("Nenhum link detectado.")
        return

    url = urls[0]
    print(">> Processando URL:", url)

    await update.message.reply_text("⏳ Processando link...")

    # Decide TikTok x Shopee
    if "tiktok.com" in url or "vt.tiktok.com" in url:
        arquivo = await baixar_tiktok(url)

    elif "shp.ee" in url or "shopee.com" in url:
        arquivo = await baixar_shopee(url)

    else:
        await update.message.reply_text("Link não suportado ainda.")
        return

    # Se falhou
    if not arquivo:
        await update.message.reply_text("❌ Não consegui baixar o vídeo deste link.")
        return

    # Envia vídeo
    await update.message.reply_video(video=open(arquivo, "rb"))
    os.remove(arquivo)


# ============================================================
# HANDLERS TELEGRAM
# ============================================================
async def start(update: Update, context):
    await update.message.reply_text("Bot online! Envie links de TikTok ou Shopee.")


application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, processar_link))


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
# STARTUP (REQUIRED BY RENDER)
# ============================================================
@app.on_event("startup")
async def on_startup():
    print(">> Inicializando o bot...")
    await application.initialize()
    url = f"{APP_URL}/webhook"
    print(">> Configurando Webhook:", url)
    await application.bot.set_webhook(url)
    await application.start()
    print(">> Bot iniciado e webhook ativo!")