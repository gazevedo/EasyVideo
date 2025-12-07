import os
import re
import httpx
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters


TOKEN = "8010976316:AAEpXdsLrbUUKqye66OI41LrQaTEc7RAuAk"
APP_URL = "https://easyvideo.onrender.com"


# ======================================================
# FASTAPI APP (ISTO PRECISA EXISTIR)
# ======================================================
app = FastAPI()


# ======================================================
# TELEGRAM APPLICATION
# ======================================================
application = Application.builder().token(TOKEN).build()


# ======================================================
# Funções auxiliares
# ======================================================
def extrair_url(texto):
    match = re.search(r"(https?://[^\s]+)", texto)
    return match.group(1) if match else None


# ======================================================
# 1️⃣ API TIKWM
# ======================================================
async def api_tikwm(url):
    try:
        print(">> [API TIKWM] Tentando...")

        async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
            r = await client.get("https://www.tikwm.com/api/", params={"url": url})

        data = r.json()
        if data["code"] != 0:
            return None

        video_url = "https://www.tikwm.com" + data["data"]["play"]

        async with httpx.AsyncClient(timeout=20) as client:
            vid = await client.get(video_url)

        filename = "video_tikwm.mp4"
        with open(filename, "wb") as f:
            f.write(vid.content)

        return filename

    except:
        return None


# ======================================================
# 2️⃣ API TIKMATE
# ======================================================
async def api_tikmate(url):
    try:
        print(">> [API TIKMATE] Tentando...")

        api = f"https://api.tikmate.app/api/lookup?url={url}"

        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(api)

        data = r.json()
        if "video_id" not in data:
            return None

        video_url = f"https://tikmate.app/download/{data['token']}/{data['video_id']}.mp4"

        async with httpx.AsyncClient(timeout=20) as client:
            vid = await client.get(video_url)

        filename = "video_tikmate.mp4"
        with open(filename, "wb") as f:
            f.write(vid.content)

        return filename

    except:
        return None


# ======================================================
# TRY ALL APIs
# ======================================================
async def baixar_video_tiktok(texto):
    url = extrair_url(texto)
    if not url:
        return None, "Nenhum link encontrado."

    APIS = [api_tikwm, api_tikmate]

    for api in APIS:
        arquivo = await api(url)
        if arquivo:
            return arquivo, None

    return None, "Nenhuma API funcionou."


# ======================================================
# Handlers do bot
# ======================================================
async def