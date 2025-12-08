#!/bin/bash
set -e

echo ">> Instalando Chromium..."
python3 -m playwright install chromium

echo ">> Iniciando servidor..."
exec uvicorn bot:app --host 0.0.0.0 --port $PORT