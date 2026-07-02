from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

BTN_VIDEO_NOTE = "🔵 Видео в кружок"
BTN_DOWNLOAD_LINK = "⬇️ Скачать по ссылке"
BTN_CANCEL = "✖️ Отмена"


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_VIDEO_NOTE)],
            [KeyboardButton(text=BTN_DOWNLOAD_LINK)],
        ],
        resize_keyboard=True,
    )


def cancel_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_CANCEL)]],
        resize_keyboard=True,
    )
