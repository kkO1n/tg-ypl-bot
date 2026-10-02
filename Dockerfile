FROM python:3.13-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# yt-dlp needs a JavaScript runtime for YouTube.
COPY --from=denoland/deno:bin /deno /usr/local/bin/deno

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -U -r requirements.txt

COPY bot.py .

# Every start pulls the latest yt-dlp, so a restart is all an update takes.
CMD ["sh", "-c", "pip install -q --no-cache-dir --root-user-action=ignore -U 'yt-dlp[default]'; exec python bot.py"]
