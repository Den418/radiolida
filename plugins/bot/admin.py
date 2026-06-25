"""
Плагин: административные команды

Все команды здесь доступны только:
• Администраторам чата
• Пользователям из AUTH_USERS в конфиге
"""
import os
import shutil

from pyrogram import filters
from pyrogram.types import Message

from bot_client import bot
from config import Config
from utils import ADMINS, CHAT_ID, call, mp, playlist, msg, ADMIN_LIST


def admin_only():
    """Фильтр: только администраторы."""
    return filters.user(ADMINS)


# ══════════════════════════════════════════════════════════════════════════════
#  Голосовой чат
# ══════════════════════════════════════════════════════════════════════════════

@bot.on_message(filters.command(["join"]) & admin_only())
async def cmd_join(_, message: Message):
    """/join — войти в голосовой чат и запустить радио."""
    k = await message.reply_text("🔊 Вхожу в голосовой чат...")
    try:
        await mp.start_radio()
        await k.edit(f"✅ Вошёл в голосовой чат!\n📻 Радио: `{Config.STREAM_URL}`")
    except Exception as e:
        await k.edit(f"❌ Ошибка: `{e}`")


@bot.on_message(filters.command(["leave"]) & admin_only())
async def cmd_leave(_, message: Message):
    """/leave — покинуть голосовой чат."""
    await mp.stop_radio()
    await message.reply_text("👋 Вышел из голосового чата.")


# ══════════════════════════════════════════════════════════════════════════════
#  Управление воспроизведением
# ══════════════════════════════════════════════════════════════════════════════

@bot.on_message(filters.command(["radio"]) & admin_only())
async def cmd_radio(_, message: Message):
    """/radio — включить радио (остановить очередь и запустить радио-поток)."""
    k = await message.reply_text("📻 Включаю радио...")
    try:
        await mp.start_radio()
        await k.edit(f"📻 **Радио включено!**\n`{Config.STREAM_URL}`")
    except Exception as e:
        await k.edit(f"❌ Ошибка: `{e}`")


@bot.on_message(filters.command(["stop", "stopradio"]) & admin_only())
async def cmd_stop(_, message: Message):
    """/stop, /stopradio — остановить воспроизведение и выйти из голосового чата."""
    await mp.stop_radio()
    await message.reply_text("⏹ Воспроизведение остановлено.")


@bot.on_message(filters.command(["skip"]) & admin_only())
async def cmd_skip(_, message: Message):
    """/skip — пропустить текущий трек."""
    if not playlist:
        await message.reply_text("📭 Очередь пуста — играет радио, нечего пропускать.")
        return
    current = playlist[0][1]
    await message.reply_text(f"⏭ Пропускаю: **{current}**")
    await mp.skip_current_playing()


@bot.on_message(filters.command(["pause"]) & admin_only())
async def cmd_pause(_, message: Message):
    """/pause — поставить воспроизведение на паузу."""
    try:
        await call.pause_stream(CHAT_ID)
        await message.reply_text("⏸ Пауза.")
    except Exception as e:
        await message.reply_text(f"❌ Не удалось поставить на паузу: `{e}`")


@bot.on_message(filters.command(["resume"]) & admin_only())
async def cmd_resume(_, message: Message):
    """/resume — продолжить воспроизведение после паузы."""
    try:
        await call.resume_stream(CHAT_ID)
        await message.reply_text("▶️ Воспроизведение продолжено.")
    except Exception as e:
        await message.reply_text(f"❌ Не удалось продолжить: `{e}`")


@bot.on_message(filters.command(["replay"]) & admin_only())
async def cmd_replay(_, message: Message):
    """/replay — повторить текущий трек с начала."""
    if not playlist:
        await message.reply_text("📭 Очередь пуста. Перезапускаю радио.")
        await mp.start_radio()
        return
    song = playlist[0]
    await message.reply_text(f"🔁 Повторяю: **{song[1]}**")
    await mp.play_song(song)


# ══════════════════════════════════════════════════════════════════════════════
#  Информация о воспроизведении (доступно всем)
# ══════════════════════════════════════════════════════════════════════════════

@bot.on_message(filters.command(["current", "playing", "now"]))
async def cmd_current(_, message: Message):
    """/current — показать что сейчас играет."""
    if not playlist:
        await message.reply_text(
            f"📻 **Сейчас играет: Радио**\n"
            f"`{Config.STREAM_URL}`"
        )
    else:
        song = playlist[0]
        rest = len(playlist) - 1
        text = (
            f"🎵 **Сейчас играет:**\n"
            f"**{song[1]}**\n\n"
            f"└ Запросил: {song[4]}"
        )
        if rest > 0:
            text += f"\n\n📋 В очереди ещё: **{rest}** {'трек' if rest == 1 else 'треков'}"
        await message.reply_text(text)


@bot.on_message(filters.command(["playlist", "queue", "list"]))
async def cmd_playlist(_, message: Message):
    """/playlist — показать всю очередь треков."""
    if not playlist:
        await message.reply_text("📭 Очередь пуста. Играет радио.")
        return

    lines = [
        f"`{i}.` **{x[1]}**\n     └ {x[4]}"
        for i, x in enumerate(playlist, 1)
    ]
    await message.reply_text(
        "🎶 **Очередь треков:**\n\n" + "\n\n".join(lines),
        disable_web_page_preview=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  Голос и громкость
# ══════════════════════════════════════════════════════════════════════════════

@bot.on_message(filters.command(["mute"]) & admin_only())
async def cmd_mute(_, message: Message):
    """/mute — заглушить юзербота в голосовом чате."""
    try:
        await call.mute_stream(CHAT_ID)
        await message.reply_text("🔇 Юзербот заглушён.")
    except Exception as e:
        await message.reply_text(f"❌ Ошибка: `{e}`")


@bot.on_message(filters.command(["unmute"]) & admin_only())
async def cmd_unmute(_, message: Message):
    """/unmute — включить звук юзербота."""
    try:
        await call.unmute_stream(CHAT_ID)
        await message.reply_text("🔔 Звук включён.")
    except Exception as e:
        await message.reply_text(f"❌ Ошибка: `{e}`")


@bot.on_message(filters.command(["volume", "vol"]) & admin_only())
async def cmd_volume(_, message: Message):
    """
    /volume [0-200] — установить громкость.
    100 = стандартная, 200 = максимальная.
    Пример: /volume 150
    """
    args = message.command[1:]
    if not args or not args[0].isdigit():
        await message.reply_text(
            "❌ Укажи уровень громкости от 0 до 200.\n"
            "**Пример:** `/volume 100`\n\n"
            "• 0 = без звука\n• 100 = стандартная\n• 200 = максимальная"
        )
        return

    volume = int(args[0])
    if not 0 <= volume <= 200:
        await message.reply_text("❌ Громкость должна быть от **0** до **200**.")
        return

    try:
        await call.change_volume_call(CHAT_ID, volume)
        bar = "▓" * (volume // 10) + "░" * (20 - volume // 10)
        await message.reply_text(f"🔊 Громкость: **{volume}%**\n`{bar}`")
    except Exception as e:
        await message.reply_text(f"❌ Ошибка: `{e}`")


# ══════════════════════════════════════════════════════════════════════════════
#  Обслуживание
# ══════════════════════════════════════════════════════════════════════════════

@bot.on_message(filters.command(["clean"]) & admin_only())
async def cmd_clean(_, message: Message):
    """/clean — удалить скачанные файлы из папки downloads."""
    k = await message.reply_text("🗑 Очищаю папку загрузок...")
    try:
        if os.path.isdir("downloads"):
            shutil.rmtree("downloads")
        os.makedirs("downloads", exist_ok=True)
        await k.edit("✅ Папка загрузок очищена.")
    except Exception as e:
        await k.edit(f"❌ Ошибка: `{e}`")


@bot.on_message(filters.command(["setvar"]) & admin_only())
async def cmd_setvar(_, message: Message):
    """
    /setvar КЛЮЧ ЗНАЧЕНИЕ — изменить переменную окружения на Heroku.
    После изменения перезапусти бота: /restart

    Пример:
      /setvar STREAM_URL http://my-radio.com/stream
      /setvar DURATION_LIMIT 30
    """
    if not Config.HEROKU_APP:
        await message.reply_text(
            "❌ Heroku не настроен.\n\n"
            "Задай в переменных окружения:\n"
            "• `HEROKU_API_KEY` — ключ API (Heroku → Account settings → API Key)\n"
            "• `HEROKU_APP_NAME` — имя твоего приложения"
        )
        return

    parts = message.text.split(None, 2)
    if len(parts) < 3:
        await message.reply_text(
            "❌ Неправильный формат.\n\n"
            "**Использование:** `/setvar КЛЮЧ ЗНАЧЕНИЕ`\n\n"
            "**Примеры:**\n"
            "• `/setvar STREAM_URL http://radio.example.com/stream`\n"
            "• `/setvar DURATION_LIMIT 30`\n"
            "• `/setvar RADIO_TITLE 🎵 МОЁ РАДИО`"
        )
        return

    key, value = parts[1], parts[2]
    try:
        Config.HEROKU_APP.config()[key] = value
        await message.reply_text(
            f"✅ **{key}** обновлено!\n\n"
            f"Новое значение: `{value}`\n\n"
            f"_Перезапусти бота командой /restart, чтобы изменение вступило в силу._"
        )
    except Exception as e:
        await message.reply_text(f"❌ Ошибка при обновлении: `{e}`")


@bot.on_message(filters.command(["authusers", "admins"]) & admin_only())
async def cmd_authusers(_, message: Message):
    """/admins — показать список администраторов бота."""
    from utils import ADMINS as _ADMINS
    if not _ADMINS:
        await message.reply_text(
            "ℹ️ Дополнительных администраторов нет.\n"
            "_Команды доступны только администраторам чата._"
        )
        return

    lines = [f"• `{a}`" for a in _ADMINS]
    await message.reply_text(
        "👮 **Администраторы бота (AUTH_USERS):**\n\n" + "\n".join(lines)
    )
