from aiogram.fsm.state import State, StatesGroup


class DownloadLink(StatesGroup):
    waiting_for_url = State()
