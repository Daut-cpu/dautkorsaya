import asyncio
import logging
import os
import shutil
import tempfile
import time
import uuid

from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, Message

from config import MAX_DOWNLOAD_SIZE_BYTES
from converter import ConversionError, convert_to_video_note, ffmpeg_available
from downloader import (
    DownloadError,
    download_video,
    is_supported_link,
    normalize_url,
    yt_dlp_available,
)
from keyboards import BTN_CANCEL, BTN_DOWNLOAD_LINK, BTN_VIDEO_NOTE, cancel_menu, main_menu
from states import DownloadLink

logger = logging.getLogger(__name__)

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "Привет! Выбери, что нужно сделать:\n\n"
        f"{BTN_VIDEO_NOTE} — превратить видео в кружочек\n"
        f"{BTN_DOWNLOAD_LINK} — скачать видео по ссылке из Instagram или Facebook",
        reply_markup=main_menu(),
    )


@router.message(F.text == BTN_VIDEO_NOTE)
async def prompt_video_note(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "Пришли видео или видеофайл — верну его в виде кружочка.",
        reply_markup=main_menu(),
    )


@router.message(F.text == BTN_DOWNLOAD_LINK)
async def prompt_download_link(message: Message, state: FSMContext) -> None:
    await state.set_state(DownloadLink.waiting_for_url)
    await message.answer(
        "Пришли ссылку на видео из Instagram или Facebook.",
        reply_markup=cancel_menu(),
    )


@router.message(F.text == BTN_CANCEL)
async def cancel_action(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Отменено.", reply_markup=main_menu())


async def _download_with_progress(url: str, work_dir: str, status: Message) -> str:
    """Await the download while periodically reassuring the user it's still running.

    download_video() guarantees termination (success or DownloadError) within
    DOWNLOAD_TIMEOUT_SECONDS, since it kills the yt-dlp subprocess on timeout
    instead of relying on cooperative cancellation.
    """
    task = asyncio.ensure_future(download_video(url, work_dir))
    started = time.monotonic()

    while True:
        try:
            return await asyncio.wait_for(asyncio.shield(task), timeout=7)
        except asyncio.TimeoutError:
            elapsed = int(time.monotonic() - started)
            try:
                await status.edit_text(f"⏳ Скачиваю видео по ссылке... ({elapsed}с)")
            except Exception:
                pass


@router.message(DownloadLink.waiting_for_url, F.text)
async def handle_link(message: Message, state: FSMContext) -> None:
    if not yt_dlp_available():
        await message.reply("❌ yt-dlp не установлен на сервере, скачивание недоступно.")
        return

    url = normalize_url(message.text)
    if not is_supported_link(url):
        await message.reply(
            "Это не похоже на ссылку из Instagram или Facebook. "
            "Пришли корректную ссылку или нажми «Отмена»."
        )
        return

    await state.clear()
    status = await message.reply("⏳ Скачиваю видео по ссылке...", reply_markup=main_menu())

    work_dir = tempfile.mkdtemp(prefix="linkdownload_")
    try:
        try:
            video_path = await _download_with_progress(url, work_dir, status)
        except DownloadError:
            logger.exception("Failed to download video from %s", url)
            await status.edit_text("❌ Не удалось скачать видео по этой ссылке.")
            return

        try:
            await message.reply_video(FSInputFile(video_path))
        except Exception:
            logger.exception("Failed to send downloaded video from %s", url)
            await status.edit_text("❌ Видео скачано, но не отправилось (возможно, слишком большое).")
            return

        await status.delete()
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


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
