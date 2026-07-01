# dautkorsaya — Telegram video note bot

Telegram-бот на aiogram, который принимает видео и возвращает его в виде
video note (кружочка).

## Возможности

* Принимает видео (`video`) и видеофайлы, отправленные как документ (`document`)
* Конвертирует через FFmpeg в квадрат 480×480 с обрезкой по центру
* Отправляет результат через `sendVideoNote`
* Удаляет временные файлы после обработки
* Обрабатывает ошибки скачивания/конвертации/отправки, не роняя бота

## Требования

* Python 3.10+
* Установленный в системе `ffmpeg`

## Установка и запуск

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# впишите в .env токен бота, полученный у @BotFather

python bot.py
```

## Структура

* `bot.py` — точка входа, запуск polling
* `config.py` — конфигурация (токен, лимиты)
* `handlers.py` — обработчики сообщений (скачивание, конвертация, отправка)
* `converter.py` — обёртка над FFmpeg (crop + scale в квадрат)
