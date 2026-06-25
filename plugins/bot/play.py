"""
Плагин: /play и /song — добавление треков в очередь

/play ссылка_или_название  → находит трек на YouTube, добавляет в очередь (файл не скачивается)
/song ссылка_или_название  → скачивает аудио как mp3 и отправляет файлом в чат
"""
import os

from pyrogram import filters
from pyrogram.types import Message
from yt_dlp import YoutubeDL

from bot_client import bot
from config import Config
from utils import ADMINS, CHAT_ID, DURATION_LIMIT, LOG_GROUP, playlist, mp


def _play_filter():
    """Фильтр для /play и /song с учётом ADMIN_ONLY."""
    base = filters.command(["play", "song"])
    if Config.ADMIN_ONLY:
        return base & filters.user(ADMINS)
    return base


async def _youtube_info(query: str, download: bool = False, out_dir: str = "downloads") -> dict | None:
    """
    Получить информацию о треке с YouTube (или найти по названию).
    Если download=True — скачивает файл в out_dir.
    """
    opts = {
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "default_search": "ytsearch1",   # Если дали название — ищем на YouTube
        "geo-bypass": True,
        "nocheckcertificate": True,
        "quiet": True,
        "no_warnings": True,
    }
    if download:
        opts.update({
            "outtmpl": f"{out_dir}/%(title)s.%(ext)s",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        })
    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(query, download=download)
            # Если поиск вернул несколько результатов — берём первый
            if "entries" in info:
                info = info["entries"][0]
            return info
    except Exception as e:
        return None


@bot.on_message(_play_filter())
async def cmd_play(client, message: Message):
    """
    /play [ссылка или название] — добавить трек в очередь.

    Примеры:
      /play https://youtu.be/dQw4w9WgXcQ
      /play Linkin Park Numb
    """
    command = message.command[0]   # "play" или "song"
    query   = " ".join(message.command[1:]).strip()

    # ── Обработка ответа на аудио-сообщение ──────────────────────────────────
    reply = message.reply_to_message
    if reply and (reply.audio or reply.voice or reply.document):
        media   = reply.audio or reply.voice or reply.document
        title   = getattr(media, "title", None) or getattr(media, "file_name", "Без названия")
        song    = [message.id, title, media.file_id, "telegram", message.from_user.mention]

        playlist.append(song)
        k = await message.reply_text(
            f"✅ Добавлено в очередь: **{title}**\n"
            f"📋 Позиция: **{len(playlist)}**"
        )
        if len(playlist) == 1:
            await mp.play_song(playlist[0])
        return

    # ── Нет ни запроса, ни ответного сообщения ───────────────────────────────
    if not query:
        await message.reply_text(
            "❌ Укажи название трека или ссылку.\n\n"
            "**Примеры:**\n"
            "• `/play Imagine Dragons Believer`\n"
            "• `/play https://youtu.be/...`"
        )
        return

    # ── Скачивание файла (/song) ──────────────────────────────────────────────
    if command == "song":
        k = await message.reply_text("🔍 Ищу и скачиваю...")
        os.makedirs("downloads", exist_ok=True)

        info = await _youtube_info(query, download=True)
        if not info:
            await k.edit("❌ Не удалось найти трек. Попробуй другой запрос.")
            return

        title = info.get("title", "Без названия")

        # Ищем скачанный файл
        fname = None
        for f in os.listdir("downloads"):
            if f.endswith(".mp3") and title[:20].lower() in f.lower():
                fname = os.path.join("downloads", f)
                break

        if not fname or not os.path.isfile(fname):
            await k.edit("❌ Файл не найден после скачивания.")
            return

        await k.delete()
        sent = await message.reply_audio(
            fname,
            title=title,
            performer=info.get("uploader", ""),
            caption=f"🎵 **{title}**",
        )
        try:
            os.remove(fname)
        except Exception:
            pass
        return

    # ── Поиск и добавление в очередь (/play) ──────────────────────────────────
    k = await message.reply_text("🔍 Ищу трек...")

    info = await _youtube_info(query)
    if not info:
        await k.edit("❌ Трек не найден. Попробуй другое название или ссылку.")
        return

    title    = info.get("title", "Без названия")
    duration = info.get("duration") or 0
    url      = info.get("webpage_url") or info.get("original_url") or info.get("url", "")
    thumb    = info.get("thumbnail")

    # Проверяем лимит длительности
    if duration and duration > DURATION_LIMIT * 60:
        mins = duration // 60
        await k.edit(
            f"❌ **Трек слишком длинный!**\n\n"
            f"├ Длительность: **{mins} мин**\n"
            f"└ Лимит: **{DURATION_LIMIT} мин**\n\n"
            f"_Измени `MAXIMUM_DURATION` в настройках для увеличения лимита._"
        )
        return

    # Добавляем в очередь
    song = [message.id, title, url, "youtube", message.from_user.mention]
    playlist.append(song)

    mins, secs = divmod(duration, 60)
    pos = len(playlist)

    await k.edit(
        f"✅ Добавлено в очередь:\n\n"
        f"🎵 **{title}**\n"
        f"├ Длительность: `{mins}:{secs:02d}`\n"
        f"├ Запросил: {message.from_user.mention}\n"
        f"└ Позиция в очереди: **{pos}**"
    )

    # Если это единственный трек — начинаем воспроизведение сразу
    if pos == 1:
        await mp.play_song(playlist[0])
