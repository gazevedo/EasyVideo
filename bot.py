import os
import re
import asyncio
import httpx
from typing import List, Optional
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# -------------------------
# CONFIG
# -------------------------
TOKEN = "8010976316:AAEpXdsLrbUUKqye66OI41LrQaTEc7RAuAk"
APP_URL = "https://easyvideo.onrender.com"  # seu URL público
DOWNLOAD_DIR = "/tmp"  # onde salvar arquivos temporários

# -------------------------
# APP GLOBAL
# -------------------------
app = FastAPI()
application = Application.builder().token(TOKEN).build()

# -------------------------
# UTIL: extrair urls
# -------------------------
URL_RE = re.compile(r"https?://[^\s<>\"\']+")

def extract_urls(text: str) -> List[str]:
    if not text:
        return []
    return URL_RE.findall(text)


# -------------------------
# DOWNLOAD HELPERS
# -------------------------
async def resolve_url_follow(url: str, client: httpx.AsyncClient, timeout=20) -> str:
    """ Resolve redirects and return final URL string """
    r = await client.get(url, follow_redirects=True, timeout=timeout)
    return str(r.url)


async def download_bytes(url: str, client: httpx.AsyncClient, timeout=30) -> Optional[bytes]:
    resp = await client.get(url, timeout=timeout)
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code} for {url}")
    return resp.content


# -------------------------
# TIKTOK (TIKWM) - já funcional
# -------------------------
async def baixar_tiktok_tikwm(url: str) -> Optional[str]:
    try:
        url = url.strip()
        print(">> TIKTOK: recebendo link:", url)
        async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
            resolved = await client.get(url)
            final_url = str(resolved.url)
        print(">> TIKTOK: url resolvida:", final_url)

        # chama tikwm
        api_url = "https://www.tikwm.com/api/"
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(api_url, data={"url": final_url})

        print(">> TIKWM raw:", resp.text[:400])
        data = resp.json()
        if data.get("code") != 0:
            print(">> TIKWM erro:", data)
            return None

        video_url = data["data"].get("play") or data["data"].get("wmplay") or data["data"].get("video")
        if not video_url:
            print(">> TIKWM não retornou vídeo")
            return None

        async with httpx.AsyncClient(timeout=60) as client:
            vb = await client.get(video_url)
        if vb.status_code != 200:
            print(">> TIKWM download err", vb.status_code)
            return None

        filename = os.path.join(DOWNLOAD_DIR, f"tiktok_{int(asyncio.time())}.mp4")
        with open(filename, "wb") as f:
            f.write(vb.content)
        print(">> TIKTOK salvo:", filename)
        return filename
    except Exception as e:
        print(">> ERRO TIKTOK:", e)
        return None


# -------------------------
# SHOPEE: rotina própria (várias tentativas)
# -------------------------
MP4_RE = re.compile(r"https?://[^\s\"']+?\.mp4[^\s\"']*", re.IGNORECASE)
CDN_RE = re.compile(r"https?://[^\s\"']+(?:cdn|shopeecdn|sv|v[0-9]+)\.[^\s\"']+\.mp4[^\s\"']*", re.IGNORECASE)

async def baixar_shopee(url: str) -> Optional[str]:
    """
    Tentativa robusta para Shopee:
    1) resolve redirecionamentos
    2) busca por mp4 direto no HTML
    3) detecta paths share-video e monta URL direto
    4) heurística final: busca por JSON embarcado com urls
    """
    try:
        url = url.strip()
        print(">> SHOPEE: recebendo link:", url)
        async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
            # 1) resolve redirecionamento - muitos links shp.ee redirecionam
            try:
                r = await client.get(url, follow_redirects=True, timeout=20)
                final_url = str(r.url)
            except Exception as e:
                print(">> SHOPEE: erro resolvendo link:", e)
                final_url = url

            print(">> SHOPEE: url final:", final_url)

            # 2) tenta obter a página final (share-video ou página do produto)
            try:
                page = await client.get(final_url, timeout=20)
                html = page.text
            except Exception as e:
                print(">> SHOPEE: erro GET final url:", e)
                html = ""

            # 3) procura direto por links mp4 (CDN)
            candidates = MP4_RE.findall(html)
            if candidates:
                video_url = candidates[0]
                print(">> SHOPEE: encontrou mp4 direto:", video_url)
                return await _save_remote_video(video_url, client)

            # 4) procura pelo padrão share-video/<id>
            m = re.search(r"share-video/([A-Za-z0-9_\-=%]+)", final_url)
            if m:
                share_id = m.group(1)
                sv_url = f"https://sv.shopee.com.br/share-video/{share_id}"
                print(">> SHOPEE: tentando sv URL:", sv_url)
                try:
                    svpage = await client.get(sv_url, timeout=20)
                    svhtml = svpage.text
                    cand = MP4_RE.findall(svhtml)
                    if cand:
                        print(">> SHOPEE: sv encontrou mp4:", cand[0])
                        return await _save_remote_video(cand[0], client)
                except Exception as e:
                    print(">> SHOPEE: erro acessando sv:", e)

            # 5) procura JSON dentro do HTML que contenha "video" ou "play"
            json_like = re.findall(r"\{(?:[^{}]|(?R))*\}", html, flags=re.DOTALL)[:50]  # heurística
            for j in json_like:
                if "video" in j or "play" in j or ".mp4" in j:
                    found = MP4_RE.findall(j)
                    if found:
                        print(">> SHOPEE: achou mp4 em JSON:", found[0])
                        return await _save_remote_video(found[0], client)

            # 6) heurística final: tentar endpoints conhecidos (sem depender de terceiros)
            # tenta acessar a url redirecionada direta para o share-video (se houver query redir)
            q = re.search(r"redir=(https%3A%2F%2F[^\&]+)", final_url)
            if q:
                decoded = httpx.utils.unquote(q.group(1))
                print(">> SHOPEE: tentando decoded redir:", decoded)
                try:
                    r2 = await client.get(decoded, timeout=20)
                    found = MP4_RE.findall(r2.text)
                    if found:
                        return await _save_remote_video(found[0], client)
                except Exception as e:
                    print(">> SHOPEE: erro decoded redir:", e)

            print(">> SHOPEE: não encontrou vídeo com heurísticas internas")
            return None

    except Exception as e:
        print(">> ERRO SHOPEE geral:", e)
        return None

async def _save_remote_video(video_url: str, client: httpx.AsyncClient) -> Optional[str]:
    try:
        print(">> Baixando video:", video_url)
        r = await client.get(video_url, timeout=60)
        if r.status_code != 200:
            raise RuntimeError(f"status {r.status_code}")
        fname = os.path.join(DOWNLOAD_DIR, f"shp_{abs(hash(video_url)) % (10**9)}.mp4")
        with open(fname, "wb") as f:
            f.write(r.content)
        print(">> Salvo em:", fname)
        return fname
    except Exception as e:
        print(">> ERRO download remote video:", e)
        return None


# -------------------------
# GENERIC: tentar vários provedores para um link
# -------------------------
async def try_download_for_url(url: str) -> Optional[str]:
    url = url.strip()
    # Detect providers
    if "tiktok.com" in url or "vt.tiktok.com" in url:
        f = await baixar_tiktok_tikwm(url)
        if f:
            return f

    if "shopee" in url or "shp.ee" in url:
        f = await baixar_shopee(url)
        if f:
            return f

    # fallback: tente baixar direto se for mp4 link
    if url.lower().endswith(".mp4"):
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                content = await download_bytes(url, client)
            fname = os.path.join(DOWNLOAD_DIR, f"file_{abs(hash(url))%10**9}.mp4")
            with open(fname, "wb") as f:
                f.write(content)
            return fname
        except Exception as e:
            print(">> fallback download falhou:", e)
            return None

    # se não reconheceu, retorne None
    return None


# -------------------------
# HANDLERS TELEGRAM
# -------------------------
async def start(update: Update, context):
    print(">> /start recebido em chat", update.effective_chat.id)
    await update.message.reply_text("Bot online! Envie um link (TikTok/Shopee/outro mp4). Vou tentar baixar.")

async def process_message(update: Update, context):
    text = update.message.text or ""
    chat_type = update.effective_chat.type
    user = update.effective_user

    print(f">> Mensagem recebida de {user.id} ({user.username}) no chat {update.effective_chat.id} [{chat_type}]: {text}")

    urls = extract_urls(text)
    if not urls:
        # só responde se houver link
        print(">> Nenhum link detectado; ignorando.")
        return

    # responde apenas quando houver link (em grupo também)
    await update.message.reply_text("🔎 Link detectado. Tentando baixar...")

    for url in urls:
        print(">> Processando URL:", url)
        # tenta provider-specific / heurísticas internas
        file_path = await try_download_for_url(url)
        if not file_path:
            print(">> Falha em baixar:", url)
            await update.message.reply_text(f"❌ Não consegui baixar: {url}")
            continue

        # envia vídeo
        try:
            print(">> Enviando vídeo para chat:", file_path)
            # usa reply_video (funciona em grupos e privados)
            with open(file_path, "rb") as fh:
                await update.message.reply_video(video=fh)
            os.remove(file_path)
            print(">> Enviado e removido:", file_path)
        except Exception as e:
            print(">> ERRO enviando arquivo:", e)
            await update.message.reply_text(f"❌ Erro ao enviar o arquivo: {e}")
            # tenta remover se existe
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass

# registrar handlers
application.add_handler(CommandHandler("start", start))
# filtra mensagens de texto (com links) - nosso handler checa se há link
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_message))


# -------------------------
# WEBHOOK
# -------------------------
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


# -------------------------
# STARTUP (ESSENCIAL PARA RENDER)
# -------------------------
@app.on_event("startup")
async def on_startup():
    print(">> Inicializando o bot...")
    await application.initialize()
    webhook_url = f"{APP_URL}/webhook"
    print(">> Configurando Webhook:", webhook_url)
    await application.bot.set_webhook(webhook_url)
    await application.start()
    print(">> Bot iniciado e webhook ativo!")