import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set. Copy .env.example to .env and fill it in.")

# Telegram Bot API refuses to download files larger than this via getFile.
MAX_DOWNLOAD_SIZE_BYTES = 20 * 1024 * 1024

# Telegram Bot API refuses to upload files larger than this via send* methods.
MAX_UPLOAD_SIZE_BYTES = 50 * 1024 * 1024

VIDEO_NOTE_SIZE = 480
FFMPEG_TIMEOUT_SECONDS = 120

# Cap resolution for link downloads so they don't drag in oversized files.
YTDLP_MAX_HEIGHT = 720
YTDLP_SOCKET_TIMEOUT_SECONDS = 20
YTDLP_RETRIES = 3
DOWNLOAD_TIMEOUT_SECONDS = 180
