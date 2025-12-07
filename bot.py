import httpx
import re


def extrair_url(texto):
    match = re.search(r"(https?://[^\s]+)", texto)
    return match.group(1) if match else None


async def download_tikwm(url_original):
    print(">> TIKWM: iniciando download para:", url_original)

    # Primeiro vamos resolver possíveis links curtos
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
            req = await client.get(url_original)
            url_final = str(req.url)
            print(">> URL FINAL:", url_final)
    except Exception as e:
        print(">> ERRO ao resolver URL:", e)
        return None, "Erro ao resolver URL"

    # Agora vamos chamar a API do TIKWM
    api_url = "https://www.tikwm.com/api/"

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(api_url, data={"url": url_final})

        data = r.json()
        print(">> RESPOSTA API TIKWM:", data)

    except Exception as e:
        print(">> ERRO chamada API TIKWM:", e)
        return None, "Erro ao consultar API TIKWM"

    # Verificar se a API retornou OK
    if data.get("code") != 0:
        return None, f"Erro da API TIKWM: {data.get('msg')}"

    try:
        video_path = data["data"]["play"]
        video_url = "https://www.tikwm.com" + video_path
        print(">> URL DO VÍDEO:", video_url)
    except Exception as e:
        print(">> ERRO ao extrair link do vídeo:", e)
        return None, "Erro ao extrair link do vídeo"

    # Baixar arquivo
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            vid = await client.get(video_url)

        filename = "video_tikwm.mp4"
        with open(filename, "wb") as f:
            f.write(vid.content)

        print(">> VÍDEO BAIXADO:", filename)
        return filename, None

    except Exception as e:
        print(">> ERRO ao baixar vídeo:", e)
        return None, "Erro ao baixar vídeo"