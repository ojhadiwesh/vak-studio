# Vāk Studio for Railway (or any Docker host). Built from the GitHub repo: code, knowledge layer and the small library
# recordings. The film library, art pieces and studio films come from the seed archive in Supabase Storage on the first
# boot (web/start.sh → python -m web.seed pull) onto a volume, so they survive redeploys. Railway sets $PORT.
FROM python:3.12-slim

ENV PYTHONUTF8=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg build-essential curl ca-certificates fonts-noto-core \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

# Node assets (captions, title cards, code-animation renderer) + headless Chromium
COPY vak/assets/package.json vak/assets/package-lock.json vak/assets/
RUN cd vak/assets && npm ci --omit=dev && npx playwright install --with-deps chromium

COPY . .
RUN sed -i 's/\r$//' web/start.sh && chmod +x web/start.sh && mkdir -p web/data/uploads web/data/thumbs chants/studio

CMD ["sh", "web/start.sh"]
