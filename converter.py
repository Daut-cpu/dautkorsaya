import asyncio
import shutil

from config import FFMPEG_TIMEOUT_SECONDS, VIDEO_NOTE_SIZE


class ConversionError(Exception):
    """Raised when ffmpeg fails to convert a video into a square video note."""


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


async def convert_to_video_note(input_path: str, output_path: str) -> None:
    """Crop the source video to a centered square and scale it for sendVideoNote."""
    size = VIDEO_NOTE_SIZE
    crop_filter = f"crop='min(iw,ih)':'min(iw,ih)',scale={size}:{size},setsar=1"

    process = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-y",
        "-i", input_path,
        "-vf", crop_filter,
        "-c:v", "libx264",
        "-preset", "fast",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        output_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        _, stderr = await asyncio.wait_for(process.communicate(), timeout=FFMPEG_TIMEOUT_SECONDS)
    except asyncio.TimeoutError as exc:
        process.kill()
        await process.wait()
        raise ConversionError("ffmpeg timed out while converting the video") from exc

    if process.returncode != 0:
        raise ConversionError(stderr.decode(errors="ignore")[-2000:])
