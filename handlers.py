import logging
import os
import shutil
import tempfile
import uuid

from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile, Message

from config import MAX_DOWNLOAD_SIZE_BYTES
from converter import ConversionError, convert_to_video_note, ffmpeg_available

logger = logging.getLogger(__name__)

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "Пришли мне видео (или видеофайл) — верну его в виде кружочка."
    )


async def _process_video(message: Message, bot: Bot, file_id: str, file_size: int | None) -> None:
    if not ffmpeg_available():
        await message.reply("❌ FFmpeg не установлен на сервере, конвертация недоступна.")
        return

    if file_size and file_size > MAX_DOWNLOAD_SIZE_BYTES:
        await message.reply("❌ Файл слишком большой (лимит Telegram Bot API — 20 МБ).")
        return

    status = await message.reply("⏳ Конвертирую видео в кружочек...")

    work_dir = tempfile.mkdtemp(prefix="videonote_")
    input_path = os.path.join(work_dir, "input.mp4")
    output_path = os.path.join(work_dir, f"{uuid.uuid4().hex}.mp4")

    try:
        try:
            tg_file = await bot.get_file(file_id)
            await bot.download_file(tg_file.file_path, destination=input_path)
        except Exception:
            logger.exception("Failed to download file %s", file_id)
            await status.edit_text("❌ Не удалось скачать видео из Telegram.")
            return

        try:
            await convert_to_video_note(input_path, output_path)
        except ConversionError:
            logger.exception("ffmpeg failed to convert %s", file_id)
            await status.edit_text("❌ Не получилось сконвертировать это видео.")
            return

        try:
            await message.reply_video_note(FSInputFile(output_path))
        except Exception:
            logger.exception("Failed to send video note for %s", file_id)
            await status.edit_text("❌ Видео сконвертировано, но не отправилось.")
            return

        await status.delete()
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


@router.message(F.video)
async def handle_video(message: Message, bot: Bot) -> None:
    video = message.video
    await _process_video(message, bot, video.file_id, video.file_size)


@router.message(F.document)
async def handle_document(message: Message, bot: Bot) -> None:
    document = message.document
    if not document.mime_type or not document.mime_type.startswith("video/"):
        return
    await _process_video(message, bot, document.file_id, document.file_size)
