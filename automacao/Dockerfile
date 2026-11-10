# Imagem única do editor + automação. Contexto de build: a raiz do repositório.
FROM python:3.12-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 \
    HF_HOME=/app/dados/cache/hf EDITOR_VIDEO_HOME=/app/dados/editor-video

# ffmpeg, Node (Remotion), bibliotecas do Chrome headless e fontes de emoji
RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg nodejs npm ca-certificates tzdata fonts-noto-color-emoji fonts-dejavu-core \
      libnss3 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 libgbm1 libasound2 libxrandr2 libxkbcommon0 \
      libxfixes3 libxcomposite1 libxdamage1 libpango-1.0-0 libcairo2 libcups2 libdrm2 \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 editor
WORKDIR /app

COPY requirements.txt automacao/requirements.txt /tmp/req/
RUN pip install --no-cache-dir -r /tmp/req/requirements.txt -r /tmp/req/automacao/requirements.txt ai-edge-litert

COPY --chown=editor:editor . /app
USER editor
RUN cd render && npm ci --no-audit --no-fund && node gen-icons.mjs && npx remotion browser ensure

CMD ["python", "-m", "automacao"]
