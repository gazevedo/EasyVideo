import httpx
import re

# ----------------------------------------------------------
# EXTRAI O LINK DO TIKTOK DA MENSAGEM (mesmo se vier texto)
# ----------------------------------------------------------
def extrair_url(texto):
    match = re.search(r'(https?://[^\s]+)', texto)
    return match.group(1) if match else None


# ==========================================================
# 1️⃣ API TIKWM
# ==========================================================
async def api_tikwm(url):
    try:
        print(">> [API TIKWM] Tentando...")

        async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
            resolved = await client.get(url)
            final_url = str(resolved.url)

        payload = {"url": final_url}

        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post("https://www.tikwm.com/api/", data=payload)

        data = r.json()
        if data["code"] != 0:
            print(">> [TIKWM] Falha:", data)
            return None

        video_url = "https://www.tikwm.com" + data["data"]["play"]

        async with httpx.AsyncClient(timeout=20) as client:
            v = await client.get(video_url)

        filename = "video_tikwm.mp4"
        with open(filename, "wb") as f:
            f.write(v.content)

        print(">> [TIKWM] Sucesso!")
        return filename

    except Exception as e:
        print(">> [TIKWM] Erro:", e)
        return None


# ==========================================================
# 2️⃣ API TIKMATE
# ==========================================================
async def api_tikmate(url):
    try:
        print(">> [API TIKMATE] Tentando...")

        async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
            resolved = await client.get(url)
            final_url = str(resolved.url)

        api = f"https://api.tikmate.app/api/lookup?url={final_url}"

        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(api)

        data = r.json()

        if "video_url" not in data:
            print(">> [TIKMATE] Falha:", data)
            return None

        video_url = f"https://tikmate.app/download/{data['token']}/{data['video_id']}.mp4"

        async with httpx.AsyncClient(timeout=20) as client:
            v = await client.get(video_url)

        filename = "video_tikmate.mp4"
        with open(filename, "wb") as f:
            f.write(v.content)

        print(">> [TIKMATE] Sucesso!")
        return filename

    except Exception as e:
        print(">> [TIKMATE] Erro:", e)
        return None


# ==========================================================
# 3️⃣ API TTSAVE
# (funciona via POST e retorna JSON com URL final)
# ==========================================================
async def api_ttsave(url):
    try:
        print(">> [API TTSAVE] Tentando...")

        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post("https://ttsave.app/download", data={"url": url})

        data = r.json()

        if "videourl" not in data:
            print(">> [TTSAVE] Falha:", data)
            return None

        video_url = data["videourl"]

        async with httpx.AsyncClient(timeout=20) as client:
            v = await client.get(video_url)

        filename = "video_ttsave.mp4"
        with open(filename, "wb") as f:
            f.write(v.content)

        print(">> [TTSAVE] Sucesso!")
        return filename

    except Exception as e:
        print(">> [TTSAVE] Erro:", e)