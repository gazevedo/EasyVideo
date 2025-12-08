# bot.py
import os
import re
import json
import httpx
import asyncio
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

TOKEN = "8010976316:AAEpXdsLrbUUKqye66OI41LrQaTEc7RAuAk"
APP_URL = "https://easyvideo.onrender.com"

app = FastAPI()
application = Application.builder().token(TOKEN).build()

# -------------------------
# Helpers: salvar arquivo
# -------------------------
def save_bytes_to_file(bytes_data: bytes, filename: str = "video.mp4") -> str:
    with open(filename, "wb") as f:
        f.write(bytes_data)
    return filename

# -------------------------
# SHOPEE DOWNLOADER (multi-strategy)
# -------------------------
async def baixar_shopee(original_url: str) -> str | None:
    """
    Tenta várias estratégias para obter o vídeo da Shopee:
     1) Resolver redirecionamento e buscar mp4 direto no HTML
     2) Procurar JSON em <script> que contenha URLs
     3) Testar várias APIs públicas (quando disponíveis)
     4) Retorna o caminho do arquivo salvo ou None
    """

    try:
        url = original_url.strip()
        print(">> SHOPEE: link recebido:", url)

        async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
            # Resolve final URL (br.shp.ee -> shopee.com.br/universal-link... -> possivelmente página com embed)
            resolved_resp = await client.get(url)
            final_url = str(resolved_resp.url)
            print(">> SHOPEE: URL final resolvida:", final_url)

            # 1) Buscar HTML e procurar mp4
            html = resolved_resp.text
            print(">> SHOPEE: HTML recebido, tamanho:", len(html))

            # Regex simples para mp4
            mp4s = re.findall(r'https?://[^"\'>\s]+\.mp4[^"\'>\s]*', html)
            if mp4s:
                print(">> SHOPEE: mp4s encontrados no HTML:", mp4s[:5])
                # pega o primeiro válido
                video_url = mp4s[0]
                print(">> SHOPEE: baixando mp4:", video_url)
                async with httpx.AsyncClient(timeout=60) as dlc:
                    r = await dlc.get(video_url)
                if r.status_code == 200 and len(r.content) > 1000:
                    return save_bytes_to_file(r.content, "shopee_video.mp4")
                print(">> SHOPEE: falha ao baixar mp4 direto (status/size).")

            # 2) Procurar JSON embutido em <script> tags
            # Extrai blocos <script> ... </script> e procura por objetos JSON que contenham 'video' 'play' 'play_url' 'mp4'
            scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, flags=re.S | re.I)
            candidate_urls = []
            for s in scripts:
                # tenta achar JSONs
                for js in re.findall(r'({.*?})', s, flags=re.S):
                    try:
                        obj = json.loads(js)
                        # varre dict por chaves com urls
                        def walk(o):
                            if isinstance(o, dict):
                                for k, v in o.items():
                                    if isinstance(v, str) and ("http" in v and (".mp4" in v or "sv.shopee" in v or "play" in k.lower() or "video" in k.lower())):
                                        candidate_urls.append(v)
                                    else:
                                        walk(v)
                            elif isinstance(o, list):
                                for i in o:
                                    walk(i)
                        walk(obj)
                    except Exception:
                        continue
            if candidate_urls:
                print(">> SHOPEE: candidate URLs extraídas de scripts:", candidate_urls[:5])
                # tenta baixar a primeira que pareça um mp4
                for cu in candidate_urls:
                    if ".mp4" in cu or "play" in cu or "sv.shopee" in cu:
                        try:
                            async with httpx.AsyncClient(timeout=60) as dlc:
                                r = await dlc.get(cu)
                            if r.status_code == 200 and len(r.content) > 1000:
                                return save_bytes_to_file(r.content, "shopee_video.mp4")
                        except Exception as e:
                            print(">> SHOPEE: erro ao tentar baixar candidate url:", cu, e)

            # 3) Consultar várias APIs públicas/externas conhecidas (tentativas):
            shopee_apis = [
                # Observação: alguns desses endpoints podem não responder; tentamos em sequência
                "https://api.saveshopee.com/v1/info?url={url}",
                "https://shopee-video-api.vercel.app/api?url={url}",
                "https://shopeeapi.up.railway.app/download?url={url}",
                # adicione aqui outros endpoints públicos que você já conhece
            ]

            for idx, api_template in enumerate(shopee_apis, start=1):
                api_call = api_template.format(url=final_url)
                print(f">> Consultando API SHOPEE #{idx}:", api_call)
                try:
                    async with httpx.AsyncClient(timeout=20) as client2:
                        resp = await client2.get(api_call)
                    if resp.status_code != 200:
                        print(">> SHOPEE API", idx, "status:", resp.status_code)
                        continue

                    # tenta interpretar como JSON
                    try:
                        j = resp.json()
                    except Exception:
                        # às vezes a api retorna um HTML com link
                        txt = resp.text
                        mp4s_api = re.findall(r'https?://[^"\'>\s]+\.mp4[^"\'>\s]*', txt)
                        if mp4s_api:
                            print(">> SHOPEE API returned mp4 in body:", mp4s_api[0])
                            async with httpx.AsyncClient(timeout=60) as dlc:
                                r = await dlc.get(mp4s_api[0])
                            if r.status_code == 200 and len(r.content) > 1000:
                                return save_bytes_to_file(r.content, "shopee_video.mp4")
                        print(">> SHOPEE API", idx, "did not return JSON or mp4.")
                        continue

                    # Procura por campos comuns com URLs
                    def find_video_in_obj(o):
                        if isinstance(o, dict):
                            for k, v in o.items():
                                if isinstance(v, str) and (v.startswith("http") and (".mp4" in v or "play" in k.lower() or "video" in k.lower())):
                                    return v
                                else:
                                    res = find_video_in_obj(v)
                                    if res:
                                        return res
                        elif isinstance(o, list):
                            for i in o:
                                res = find_video_in_obj(i)
                                if res:
                                    return res
                        return None

                    candidate = find_video_in_obj(j)
                    if candidate:
                        print(">> SHOPEE API #{} candidate: {}".format(idx, candidate))
                        async with httpx.AsyncClient(timeout=60) as dlc:
                            r = await dlc.get(candidate)
                        if r.status_code == 200 and len(r.content) > 1000:
                            return save_bytes_to_file(r.content, "shopee_video.mp4")
                        else:
                            print(">> SHOPEE API #{} candidate returned non-ok/downsize".format(idx))
                    else:
                        print(">> SHOPEE API #{} returned JSON but no video found".format(idx))

                except Exception as e:
                    print(">> ERRO SHOPEE #{}:".format(idx), e)
                    continue

            # 4) Como fallback: tenta abrir final_url com headers imitando app (User-Agent + headers comuns)
            try:
                app_headers = {
                    "User-Agent": "Mozilla/5.0 (Linux; Android 13; Shopee) AppleWebKit/537.36 (KHTML, like Gecko) Mobile Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                }
                async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client3:
                    r = await client3.get(final_url, headers=app_headers)
                extra_mp4s = re.findall(r'https?://[^"\'>\s]+\.mp4[^"\'>\s]*', r.text)
                if extra_mp4s:
                    print(">> SHOPEE fallback mp4s:", extra_mp4s[:3])
                    async with httpx.AsyncClient(timeout=60) as dlc:
                        rr = await dlc.get(extra_mp4s[0])
                    if rr.status_code == 200 and len(rr.content) > 1000:
                        return save_bytes_to_file(rr.content, "shopee_video.mp4")
            except Exception as e:
                print(">> SHOPEE fallback erro:", e)

        print(">> SHOPEE: nenhuma estratégia obteve o vídeo.")
        return None

    except Exception as e:
        print(">> ERRO NO BAIXAR SHOPEE:", e)
        return None

# -------------------------
# TIKTOK (mantém seu método tikwm/tikmate/snaptik etc)
# -------------------------
async def baixar_tiktok(url: str) -> str | None:
    try:
        url = url.strip()
        print(">> TIKTOK: Link recebido:", url)

        async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
            resolved = await client.get(url)
            final_url = str(resolved.url)
        print(">> TIKTOK URL resolvida:", final_url)

        # Exemplo usando Tikwm
        api_url = "https://www.tikwm.com/api/"
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(api_url, data={"url": final_url})
        if resp.status_code != 200:
            print(">> TIKWM status !=200", resp.status_code, resp.text[:200])
            return None
        data = resp.json()
        if data.get("code") != 0:
            print(">> TIKWM erro payload:", data)
            return None
        video_url = data["data"].get("play") or data["data"].get("url") or data["data"].get("video")
        if not video_url:
            print(">> TIKWM não retornou vídeo")
            return None
        async with httpx.AsyncClient(timeout=60) as dlc:
            r = await dlc.get(video_url)
        if r.status_code == 200 and len(r.content) > 1000:
            return save_bytes_to_file(r.content, "tiktok_video.mp4")
        return None
    except Exception as e:
        print(">> ERRO NO TIKTOK:", e)
        return None

# -------------------------
# TELEGRAM HANDLERS
# -------------------------
async def start(update: Update, context):
    print(">> /start recebido")
    await update.message.reply_text("Bot online! Envie qualquer link (TikTok, Shopee, etc).")

async def process_link(update: Update, context):
    text = update.message.text or ""
    print(">> Mensagem recebida:", text)

    # pega a primeira URL simples na mensagem
    m = re.search(r'(https?://[^\s]+)', text)
    if not m:
        await update.message.reply_text("Envie um link (ex: tiktok/shopee).")
        return
    link = m.group(1).strip()
    await update.message.reply_text("⏳ Detectado link, vou tentar baixar...")

    # decidir qual downloader chamar
    if "shopee" in link or "shp.ee" in link:
        print(">> SHOPEE link detectado:", link)
        arquivo = await baixar_shopee(link)
    elif "tiktok" in link or "vt.tiktok" in link:
        print(">> TIKTOK link detectado:", link)
        arquivo = await baixar_tiktok(link)
    else:
        # tenta TikTok first (muitos encurtadores tiktok) and then generic approach
        arquivo = None
        if "tiktok" in link or "vt.tiktok" in link:
            arquivo = await baixar_tiktok(link)
        # se quiser: adicionar suporte para youtube, instagram, etc.
    if not arquivo:
        await update.message.reply_text("❌ Não consegui baixar o vídeo com as estratégias tentadas. Veja logs.")
        return

    # envia arquivo
    try:
        await update.message.reply_video(video=open(arquivo, "rb"))
    except Exception as e:
        print(">> ERRO ao enviar video:", e)
        await update.message.reply_text("❌ Erro ao enviar o vídeo (tamanho/formato?).")
    finally:
        try:
            os.remove(arquivo)
        except Exception:
            pass

application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_link))

# -------------------------
# WEBHOOK + STARTUP (Render)
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

@app.on_event("startup")
async def on_startup():
    print(">> Inicializando o bot...")
    await application.initialize()
    webhook_url = f"{APP_URL}/webhook"
    print(">> Configurando Webhook:", webhook_url)
    await application.bot.set_webhook(webhook_url)
    await application.start()
    print(">> Bot iniciado e webhook ativo!")