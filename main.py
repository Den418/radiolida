"""
╔══════════════════════════════════════════════════════════╗
║           RadioPlayerV3 — Точка входа (main.py)         ║
╠══════════════════════════════════════════════════════════╣
║  Порядок запуска:                                        ║
║  1. USER  — юзербот (войдёт в голосовой чат)            ║
║  2. call  — PyTgCalls поверх USER                       ║
║  3. bot   — Pyrogram-бот (принимает команды)            ║
║  4. Радио — сразу после старта                          ║
╚══════════════════════════════════════════════════════════╝

Запуск:
    python3 main.py
"""
import asyncio
import logging
import os
import sys
from threading import Thread
from time import sleep as time_sleep

from pyrogram import filters, idle
from pyrogram.errors import UserAlreadyParticipant
from pyrogram.raw.functions.bots import SetBotCommands
from pyrogram.raw.types import BotCommand, BotCommandScopeDefault

from bot_client import bot
from config import Config
from utils import CHAT_ID, LOG_GROUP, ADMINS, call, mp
import utils  # нужен для записи USERNAME после старта

# ─── Настройка логирования ─────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("RadioPlayerV3")

# Убираем лишний шум от сторонних библиотек
for _lib in ("pyrogram", "pytgcalls", "asyncio"):
    logging.getLogger(_lib).setLevel(logging.WARNING)


# ══════════════════════════════════════════════════════════════════════════════
#  Список команд для меню бота в Telegram (кнопка "/" рядом с вводом)
# ══════════════════════════════════════════════════════════════════════════════
BOT_COMMANDS = [
    ("start",     "🚀 Запустить бота / информация"),
    ("help",      "❓ Справка по командам"),
    ("play",      "🎵 Воспроизвести трек с YouTube"),
    ("song",      "📥 Скачать аудио с YouTube"),
    ("skip",      "⏭ Пропустить текущий трек"),
    ("pause",     "⏸ Пауза"),
    ("resume",    "▶️ Продолжить воспроизведение"),
    ("radio",     "📻 Включить радио"),
    ("stopradio", "⏹ Остановить радио"),
    ("current",   "🎶 Текущий трек"),
    ("playlist",  "📋 Очередь треков"),
    ("join",      "🔊 Войти в голосовой чат"),
    ("leave",     "🔇 Выйти из голосового чата"),
    ("mute",      "🔕 Заглушить юзербота"),
    ("unmute",    "🔔 Включить звук юзербота"),
    ("volume",    "🔊 Установить громкость (0-200)"),
    ("replay",    "🔁 Повторить трек сначала"),
    ("clean",     "🗑 Удалить загруженные файлы"),
    ("restart",   "🔄 Обновить и перезапустить бота"),
    ("setvar",    "⚙️ Изменить Config Var (Heroku)"),
]


# ══════════════════════════════════════════════════════════════════════════════
#  Команда /restart — здесь (а не в плагине), чтобы корректно остановить
#  PyTgCalls до выхода из процесса
# ══════════════════════════════════════════════════════════════════════════════
def _do_restart():
    """
    Синхронная функция перезапуска.
    Запускается в отдельном потоке, чтобы не блокировать event loop.

    ИСПРАВЛЕНbug оригинала:
      Было:  Thread(target=stop_and_restart())  ← вызывает функцию сразу!
      Стало: Thread(target=_do_restart)         ← передаёт функцию, без ()
    """
    time_sleep(2)       # Даём боту время отправить ответное сообщение
    os.system("git pull && pip install -r requirements.txt -q")
    os.execl(sys.executable, sys.executable, *sys.argv)   # Перезапускаем процесс


@bot.on_message(
    filters.command(["restart"])
    & filters.user(ADMINS)
)
async def cmd_restart(client, message):
    """/restart — обновить код и перезапустить бота."""
    k = await message.reply("🔄 **Перезапуск...**")

    # На Heroku — перезапустить дино
    if Config.HEROKU_APP:
        await k.edit(
            "♻️ **Перезапускаю дино на Heroku...**\n"
            "_Бот вернётся через ~30 секунд._"
        )
        Config.HEROKU_APP.restart()
        return

    # Локальный запуск — git pull → exec
    await k.edit(
        "⬇️ **Обновляю код и перезапускаю...**\n"
        "_Подождите ~15 секунд._"
    )

    # Выходим из голосового чата перед перезапуском
    try:
        await call.leave_group_call(CHAT_ID)
    except Exception:
        pass

    # Запускаем перезапуск в фоновом потоке (без скобок — передаём функцию!)
    Thread(target=_do_restart, daemon=True).start()


# ══════════════════════════════════════════════════════════════════════════════
#  Главная асинхронная функция
#
#  ИСПРАВЛЕН bug оригинала:
#    Было: bot.run(main())   ← блокирует процесс навсегда
#          bot.start()        ← никогда не выполняется
#          bot.send_message() ← никогда не выполняется
#
#    Стало: всё внутри одной async-функции, запускаемой через asyncio.run()
# ══════════════════════════════════════════════════════════════════════════════
async def main():

    # ── Шаг 1: Запускаем юзербота ──────────────────────────────────────────────
    from user import USER
    log.info("Запускаем юзербота...")
    await USER.start()
    user_me = await USER.get_me()
    log.info("✅ Юзербот: %s (%s)", user_me.first_name, user_me.id)

    # ── Шаг 2: Запускаем PyTgCalls (поверх юзербота) ──────────────────────────
    log.info("Запускаем PyTgCalls...")
    await call.start()
    log.info("✅ PyTgCalls запущен")

    # ── Шаг 3: Запускаем бота и регистрируем меню команд ─────────────────────
    log.info("Запускаем бота...")
    await bot.start()
    bot_me = await bot.get_me()

    # Сохраняем username для использования в плагинах
    utils.USERNAME = bot_me.username

    log.info("✅ Бот запущен: @%s", bot_me.username)

    # Устанавливаем список команд в меню Telegram
    try:
        await bot.invoke(SetBotCommands(
            scope=BotCommandScopeDefault(),
            lang_code="ru",
            commands=[BotCommand(command=c, description=d) for c, d in BOT_COMMANDS],
        ))
    except Exception as e:
        log.warning("Не удалось обновить меню команд: %s", e)

    # ── Шаг 4: Уведомляем лог-группу ─────────────────────────────────────────
    if LOG_GROUP:
        try:
            await bot.send_message(
                LOG_GROUP,
                f"✅ **RadioPlayerV3 запущен**\n\n"
                f"├ Бот: @{bot_me.username}\n"
                f"├ Юзербот: {user_me.first_name} (`{user_me.id}`)\n"
                f"├ Чат: `{CHAT_ID}`\n"
                f"└ Радио: `{Config.STREAM_URL}`",
                disable_web_page_preview=True,
            )
        except Exception as e:
            log.warning("Не удалось отправить стартовое сообщение в лог: %s", e)

    # ── Шаг 5: Запускаем радио ─────────────────────────────────────────────────
    log.info("Запускаем радио...")
    try:
        await mp.start_radio()
    except Exception as e:
        log.error("Не удалось запустить радио: %s", e)
        log.error("Проверь CHAT_ID и убедись, что юзербот — участник чата")

    # ── Готово ─────────────────────────────────────────────────────────────────
    print("\n" + "═" * 50)
    print(f"  RadioPlayerV3 работает!")
    print(f"  Бот: @{bot_me.username}")
    print(f"  Чат: {CHAT_ID}")
    print(f"  Нажми Ctrl+C для остановки")
    print("═" * 50 + "\n")

    # Держим процесс живым — ждём Ctrl+C или сигнала остановки
    await idle()

    # ── Завершение ─────────────────────────────────────────────────────────────
    log.info("Останавливаем бота...")
    try:
        await mp.stop_radio()
    except Exception:
        pass
    try:
        await call.stop()
    except Exception:
        pass
    await bot.stop()
    await USER.stop()
    log.info("Бот остановлен. До свидания!")


if __name__ == "__main__":
    asyncio.run(main())
