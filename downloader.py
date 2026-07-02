import asyncio
import os
import re

import yt_dlp

from config import MAX_UPLOAD_SIZE_BYTES

SUPPORTED_HOSTS = (
    "instagram.com",
    "instagr.am",
    "facebook.com",
    "fb.watch",
)

_URL_HOST_RE = re.compile(r"^https?://([^/]+)/?", re.IGNORECASE)


class DownloadError(Exception):
    """Raised when a video can't be fetched from the given link."""


def is_supported_link(url: str) -> bool:
    match = _URL_HOST_RE.match(url.strip())
    if not match:
        return False
    host = match.group(1).lower()
    if host.startswith("www."):
        host = host[4:]
    elif host.startswith("m."):
        host = host[2:]
    return any(host == h or host.endswith("." + h) for h in SUPPORTED_HOSTS)


def _download(url: str, work_dir: str) -> str:
    ydl_opts = {
        "outtmpl": os.path.join(work_dir, "%(id)s.%(ext)s"),
        "format": "mp4/bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "max_filesize": MAX_UPLOAD_SIZE_BYTES,
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        path = ydl.prepare_filename(info)
        if not os.path.exists(path):
            raise DownloadError("downloaded file not found on disk")
        return path


async def download_video(url: str, work_dir: str) -> str:
    try:
        return await asyncio.to_thread(_download, url, work_dir)
    except DownloadError:
        raise
    except yt_dlp.utils.DownloadError as exc:
        raise DownloadError(str(exc)) from exc
