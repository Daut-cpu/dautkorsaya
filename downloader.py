import asyncio
import os
import re
import shutil
import signal

from config import (
    DOWNLOAD_TIMEOUT_SECONDS,
    MAX_UPLOAD_SIZE_BYTES,
    YTDLP_COOKIES_FILE,
    YTDLP_MAX_HEIGHT,
    YTDLP_RETRIES,
    YTDLP_SOCKET_TIMEOUT_SECONDS,
)

SUPPORTED_HOSTS = (
    "instagram.com",
    "instagr.am",
    "facebook.com",
    "fb.watch",
)

_URL_HOST_RE = re.compile(r"^https?://([^/]+)/?", re.IGNORECASE)
_SCHEME_RE = re.compile(r"^https?://", re.IGNORECASE)


class DownloadError(Exception):
    """Raised when a video can't be fetched from the given link."""


def normalize_url(url: str) -> str:
    url = url.strip()
    if not _SCHEME_RE.match(url):
        url = f"https://{url}"
    return url


def is_supported_link(url: str) -> bool:
    match = _URL_HOST_RE.match(normalize_url(url))
    if not match:
        return False
    host = match.group(1).lower()
    if host.startswith("www."):
        host = host[4:]
    elif host.startswith("m."):
        host = host[2:]
    return any(host == h or host.endswith("." + h) for h in SUPPORTED_HOSTS)


def yt_dlp_available() -> bool:
    return shutil.which("yt-dlp") is not None


async def _kill_process_group(process: asyncio.subprocess.Process) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    try:
        await asyncio.wait_for(process.wait(), timeout=5)
    except asyncio.TimeoutError:
        # The OS didn't report the reap in time; don't hang the caller over it.
        pass


async def download_video(url: str, work_dir: str) -> str:
    """Run yt-dlp as a subprocess so a stuck download can always be killed outright.

    (The in-process Python API would run inside a thread pool worker that
    Python cannot forcibly stop if it hangs, eventually starving the pool.)
    """
    height = YTDLP_MAX_HEIGHT
    fmt = (
        f"best[height<={height}][ext=mp4]/"
        f"bestvideo[height<={height}]+bestaudio/"
        f"best[height<={height}]/best"
    )

    args = [
        "yt-dlp",
        "--no-playlist",
        "--quiet",
        "--no-warnings",
        "--format", fmt,
        "--merge-output-format", "mp4",
        "--max-filesize", str(MAX_UPLOAD_SIZE_BYTES),
        "--socket-timeout", str(YTDLP_SOCKET_TIMEOUT_SECONDS),
        "--retries", str(YTDLP_RETRIES),
        "--fragment-retries", str(YTDLP_RETRIES),
        "--concurrent-fragments", "4",
        "--print", "after_move:filepath",
        "-o", os.path.join(work_dir, "%(id)s.%(ext)s"),
    ]
    if YTDLP_COOKIES_FILE and os.path.isfile(YTDLP_COOKIES_FILE):
        args += ["--cookies", YTDLP_COOKIES_FILE]
    args.append(url)

    process = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        # New session/process group so we can kill yt-dlp *and* any child it
        # spawns (e.g. ffmpeg for merging) instead of just the immediate PID.
        start_new_session=True,
    )

    try:
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=DOWNLOAD_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError as exc:
            await _kill_process_group(process)
            raise DownloadError("download timed out") from exc
    except asyncio.CancelledError:
        await _kill_process_group(process)
        raise

    if process.returncode != 0:
        raise DownloadError(stderr.decode(errors="ignore")[-2000:])

    lines = stdout.decode(errors="ignore").strip().splitlines()
    path = lines[-1] if lines else ""
    if not path or not os.path.exists(path):
        raise DownloadError("downloaded file not found on disk")
    return path
