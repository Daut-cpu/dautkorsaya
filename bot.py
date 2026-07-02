import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramNetworkError
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from handlers import router

logger = logging.getLogger(__name__)

STARTUP_RETRY_DELAY_SECONDS = 5


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    # aiogram's own retry loop only covers getUpdates once polling is
    # already running -- the very first call (get_me, done inside
    # start_polling before that loop starts) isn't covered, so a one-off
    # network blip right at launch would otherwise crash the process
    # instead of just being retried.
    while True:
        try:
            await dp.start_polling(bot)
            return
        except TelegramNetworkError:
            logger.warning(
                "Could not reach Telegram at startup, retrying in %ss...",
                STARTUP_RETRY_DELAY_SECONDS,
            )
            await asyncio.sleep(STARTUP_RETRY_DELAY_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())
