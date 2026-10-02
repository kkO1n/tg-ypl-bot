import asyncio
import json
import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.types import FSInputFile, Message
from aiogram.utils.chat_action import ChatActionSender
from yt_dlp import YoutubeDL

BOT_TOKEN = os.environ["BOT_TOKEN"]
ALLOWED_USERS = {int(x) for x in os.environ["ALLOWED_USERS"].split(",") if x.strip()}
COOKIES_FILE = os.environ.get("COOKIES_FILE")

TELEGRAM_UPLOAD_LIMIT = 50 * 1024 * 1024
URL_RE = re.compile(
    r"https?://(?:[\w-]+\.)?(?:instagram\.com|youtube\.com|youtu\.be)/\S+"
)

log = logging.getLogger("bot")
dp = Dispatcher()


def download(url: str, workdir: str) -> Path:
    options = {
        "outtmpl": f"{workdir}/%(id)s.%(ext)s",
        "format_sort": ["vcodec:h264", "res:1080", "acodec:m4a"],
        "merge_output_format": "mp4",
        "noplaylist": True,
        "socket_timeout": 30,
        "quiet": True,
        "noprogress": True,
    }
    if COOKIES_FILE:
        options["cookiefile"] = COOKIES_FILE
    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
    return Path(info["requested_downloads"][0]["filepath"])


def probe(path: Path) -> dict:
    result = subprocess.run(
        [
            *("ffprobe", "-v", "error", "-of", "json"),
            *("-select_streams", "v:0"),
            *("-show_entries", "stream=codec_name,width,height:format=duration"),
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(result.stdout)
    return {
        **data["streams"][0],
        "duration": round(float(data["format"]["duration"])),
    }


def to_h264(path: Path) -> Path:
    output = path.with_name(f"{path.stem}.h264.mp4")
    subprocess.run(
        [
            *("ffmpeg", "-v", "error", "-y", "-i", str(path)),
            *("-c:v", "libx264", "-preset", "veryfast", "-crf", "23"),
            *("-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart"),
            str(output),
        ],
        check=True,
    )
    return output


def fetch(url: str, workdir: str) -> tuple[Path, dict]:
    path = download(url, workdir)
    meta = probe(path)
    # Telegram only plays H.264 inline on every client.
    if meta["codec_name"] != "h264":
        path = to_h264(path)
        meta = probe(path)
    return path, meta


@dp.message(F.from_user.id.in_(ALLOWED_USERS), F.text.regexp(URL_RE).as_("match"))
async def handle_link(message: Message, match: re.Match) -> None:
    url = match.group(0)
    log.info("download %s", url)
    with tempfile.TemporaryDirectory() as workdir:
        async with ChatActionSender.upload_video(
            bot=message.bot, chat_id=message.chat.id
        ):
            try:
                path, meta = await asyncio.to_thread(fetch, url, workdir)
            except Exception as error:
                log.exception("download failed: %s", url)
                await message.reply(f"Download failed: {str(error)[-300:]}")
                return

            size = path.stat().st_size
            if size > TELEGRAM_UPLOAD_LIMIT:
                await message.reply(
                    f"Video is {size / 1024 / 1024:.0f} MB, Telegram's limit is 50 MB."
                )
                return

            await message.reply_video(
                FSInputFile(path),
                width=meta["width"],
                height=meta["height"],
                duration=meta["duration"],
                supports_streaming=True,
            )


@dp.message(F.from_user.id.in_(ALLOWED_USERS))
async def handle_other(message: Message) -> None:
    await message.reply("Send me an Instagram reel or YouTube Shorts link.")


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(Bot(BOT_TOKEN))


if __name__ == "__main__":
    asyncio.run(main())
