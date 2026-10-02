# tg-ypl-bot

A Telegram bot that takes an Instagram reel or YouTube Shorts link and replies
with the video.

It is one Python file built on [yt-dlp](https://github.com/yt-dlp/yt-dlp) and
[aiogram](https://github.com/aiogram/aiogram). It uses long polling, so it needs
no public port, domain or database.

## Run

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy its token.
2. Get your Telegram user ID from [@userinfobot](https://t.me/userinfobot).
3. Start the bot:

```sh
cp .env.example .env   # fill in BOT_TOKEN and ALLOWED_USERS
docker compose up -d --build
docker compose logs -f
```

Send the bot a link in a private chat. Only the user IDs in `ALLOWED_USERS` get
an answer. Everyone else is ignored.

## How it works

1. `download` fetches the video with yt-dlp, preferring H.264 in mp4.
2. `probe` reads the codec, size and duration with `ffprobe`.
3. If the codec is not H.264, `to_h264` re-encodes it so Telegram plays it inline.
4. The bot replies with the video and deletes the temporary files.

## Troubleshooting

**Downloads start failing.** The sites change often and yt-dlp follows. Rebuild
to pick up the latest release:

```sh
docker compose build --no-cache && docker compose up -d
```

**"Sign in to confirm you're not a bot".** YouTube and Instagram sometimes demand
a login, mostly on server IPs. Export a Netscape-format cookies file from a
logged-in browser, mount it into the container and set `COOKIES_FILE` to its
path.

**Video is too large.** Telegram's cloud Bot API rejects uploads above 50 MB.

## Development

```sh
ruff format . && ruff check .
```
