"""
╔══════════════════════════════════════════════════════════╗
║              RadioPlayerV3 — Ядро (utils.py)            ║
║                                                          ║
║  Здесь живут:                                            ║
║  • MusicPlayer — управление воспроизведением            ║
║  • call         — PyTgCalls клиент                      ║
║  • Обработчики событий голосового чата                   ║
╚══════════════════════════════════════════════════════════╝

Формат элемента плейлиста (Config.playlist):
  [0] msg_id   — ID сообщения с запросом
  [1] title    — Название трека
  [2] source   — URL или file_id Telegram-файла
  [3] src_type — "youtube" | "telegram" | "direct"
  [4] by       — Кто запросил (mention пользователя)
"""
import asyncio
import logging
import os
from asyncio import sleep
from random import randint

from pyrogram.errors import FloodWait
from pyrogram.raw.functions.phone import CreateGroupCall, EditGroupCallTitle
from pyrogram.raw.functions.channels import GetFullChannel
from pyrogram.raw.types import InputGroupCall

# ─── PyTgCalls ────────────────────────────────────────────────────────────────
# Совместимость с pytgcalls >= 0.9
# Убедись что версия обновлена: pip install -U pytgcalls
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream, AudioParameters, AudioQuality

# ─── yt-dlp ───────────────────────────────────────────────────────────────────
from yt_dlp import YoutubeDL

from config import Config
from user import USER
from bot_client import bot

log = logging.getLogger(__name__)

# ─── Копируем настройки из конфига в локальные переменные ────────────────────
CHAT_ID        = Config.CHAT_ID
STREAM_URL     = Config.STREAM_URL
DURATION_LIMIT = Config.DURATION_LIMIT
LOG_GROUP      = Config.LOG_GROUP
DELAY          = Config.DELAY
EDIT_TITLE     = Config.EDIT_TITLE
RADIO_TITLE    = Config.RADIO_TITLE
ADMINS         = Config.ADMINS

# ─── Общее изменяемое состояние (ссылки на Config, изменения видны везде) ────
playlist = Config.playlist   # Очередь треков
msg      = Config.msg        # Служебные сообщения

# ─── Кэш администраторов (заполняется по запросу) ─────────────────────────────
ADMIN_LIST: dict = {}

# ─── Username бота — устанавливается в main.py после старта ──────────────────
USERNAME = ""

# ─── Настройки yt-dlp (не скачиваем файл, только получаем прямую ссылку) ─────
_YDL_OPTS = {
    "format": "bestaudio[ext=m4a]/bestaudio/best",
    "default_search": "ytsearch1",
    "geo-bypass": True,
    "nocheckcertificate": True,
    "quiet": True,
    "no_warnings": True,
}

# ─── Главный объект PyTgCalls (работает поверх юзербота USER) ─────────────────
call = PyTgCalls(USER)


# ══════════════════════════════════════════════════════════════════════════════
#  MusicPlayer — всё управление воспроизведением
# ══════════════════════════════════════════════════════════════════════════════
class MusicPlayer:

    # ── Плейлист ──────────────────────────────────────────────────────────────

    async def send_playlist(self):
        """Обновить сообщение с очередью треков в лог-группе."""
        if not LOG_GROUP:
            return  # Лог-группа не задана — молчим

        if not playlist:
            text = "📭 **Очередь пуста.** Играет радио."
        else:
            lines = [
                f"`{i}.` **{x[1]}**\n     └ запросил: {x[4]}"
                for i, x in enumerate(playlist, 1)
            ]
            text = "🎶 **Очередь треков:**\n\n" + "\n".join(lines)

        # Удаляем старое сообщение с плейлистом, если было
        if msg.get("playlist"):
            try:
                await msg["playlist"].delete()
            except Exception:
                pass
            msg["playlist"] = None

        try:
            msg["playlist"] = await bot.send_message(
                LOG_GROUP, text,
                disable_web_page_preview=True,
                disable_notification=True,
            )
        except FloodWait as e:
            # FloodWait.value (не .x) — исправлен баг оригинала
            await sleep(e.value)
        except Exception as e:
            log.warning("send_playlist: %s", e)

    # ── Управление воспроизведением ────────────────────────────────────────────

    async def start_radio(self):
        """Запустить радио-поток из STREAM_URL."""
        playlist.clear()
        log.info("📻 Запускаем радио: %s", STREAM_URL)

        stream = MediaStream(
            STREAM_URL,
            audio_parameters=AudioParameters(
                bitrate=128_000,       # 128 kbps — хорошее качество
            ),
        )

        joined = False
        # Пробуем сменить поток (если уже в голосовом чате)
        try:
            await call.change_stream(CHAT_ID, stream)
            joined = True
        except Exception:
            pass

        if not joined:
            # Пробуем вступить в голосовой чат
            try:
                await call.join_group_call(CHAT_ID, stream)
            except Exception as e:
                log.error("Не удалось войти в голосовой чат: %s", e)
                # Голосового чата нет — создаём его
                await self._create_voice_chat()
                await call.join_group_call(CHAT_ID, stream)

        if EDIT_TITLE and RADIO_TITLE:
            await self.edit_title(RADIO_TITLE)

        log.info("✅ Радио запущено")

    async def stop_radio(self):
        """Остановить воспроизведение и покинуть голосовой чат."""
        playlist.clear()
        try:
            await call.leave_group_call(CHAT_ID)
            log.info("⏹ Воспроизведение остановлено")
        except Exception as e:
            log.warning("stop_radio — leave_group_call: %s", e)

    async def play_song(self, song: list):
        """
        Начать воспроизведение трека.
        song — элемент плейлиста: [msg_id, title, src, src_type, by]
        """
        url = await self._resolve_url(song)

        if not url:
            log.warning("⚠️ Нет URL для '%s' — пропускаем", song[1])
            if playlist:
                playlist.pop(0)
            if playlist:
                await self.play_song(playlist[0])
            else:
                await self.start_radio()
            return

        stream = MediaStream(url)

        try:
            await call.change_stream(CHAT_ID, stream)
        except Exception:
            try:
                await call.join_group_call(CHAT_ID, stream)
            except Exception as e:
                log.error("play_song — join_group_call: %s", e)
                return

        if EDIT_TITLE:
            await self.edit_title(f"🎵 {song[1]}")

        await self.send_playlist()
        log.info("▶️ Играет: %s (запросил: %s)", song[1], song[4])

    async def skip_current_playing(self):
        """Пропустить текущий трек и перейти к следующему (или к радио)."""
        if not playlist:
            await self.start_radio()
            return

        skipped = playlist.pop(0)
        log.info("⏭ Пропущен трек: %s", skipped[1])

        # Удаляем временный файл, если трек был из Telegram
        if skipped[3] == "telegram":
            tmp = f"downloads/{skipped[0]}.m4a"
            try:
                if os.path.isfile(tmp):
                    os.remove(tmp)
            except Exception:
                pass

        if playlist:
            await self.play_song(playlist[0])
        else:
            await self.start_radio()

    # ── Вспомогательные методы ────────────────────────────────────────────────

    async def _resolve_url(self, song: list) -> str | None:
        """
        Превратить запись из плейлиста в прямую ссылку на аудио.

        YouTube  → прямой URL от yt-dlp (файл не скачиваем)
        Telegram → скачиваем файл и возвращаем путь
        direct   → возвращаем URL как есть
        """
        src_type: str = song[3]
        src: str      = song[2]

        try:
            if src_type == "youtube":
                with YoutubeDL(_YDL_OPTS) as ydl:
                    info = ydl.extract_info(src, download=False)
                    # Берём прямой URL лучшего аудио-формата
                    if "url" in info:
                        return info["url"]
                    # Если есть список форматов — берём последний (обычно лучший)
                    for fmt in reversed(info.get("formats", [])):
                        if fmt.get("acodec") not in (None, "none"):
                            return fmt.get("url")
                return None

            elif src_type == "telegram":
                os.makedirs("downloads", exist_ok=True)
                path = await bot.download_media(
                    src,
                    file_name=f"downloads/{song[0]}.m4a",
                )
                return path

            else:
                # Прямая ссылка (direct URL, другой сайт)
                return src

        except Exception as e:
            log.error("_resolve_url для '%s': %s", song[1], e)
            return None

    async def _create_voice_chat(self):
        """Создать голосовой чат в канале/группе, если его нет."""
        try:
            peer = await USER.resolve_peer(CHAT_ID)
            await USER.invoke(
                CreateGroupCall(peer=peer, random_id=randint(10_000, 999_999_999))
            )
            await sleep(2)  # Telegram нужно немного времени
            log.info("✅ Голосовой чат создан в чате %s", CHAT_ID)
        except Exception as e:
            log.error("Не удалось создать голосовой чат: %s", e)

    async def edit_title(self, title: str):
        """Изменить заголовок текущего голосового чата."""
        if not EDIT_TITLE:
            return
        try:
            peer = await USER.resolve_peer(CHAT_ID)
            full = await USER.invoke(GetFullChannel(channel=peer))
            gc = full.full_chat.call
            if gc:
                await USER.invoke(EditGroupCallTitle(
                    call=InputGroupCall(id=gc.id, access_hash=gc.access_hash),
                    title=title,
                ))
        except Exception as e:
            log.debug("edit_title: %s", e)

    async def get_admins(self, chat_id: int) -> list:
        """
        Вернуть список ID администраторов чата.
        Результат кэшируется в ADMIN_LIST — не долбим API каждый раз.
        """
        if chat_id in ADMIN_LIST:
            return ADMIN_LIST[chat_id]

        admins = list(ADMINS)  # Начинаем с тех, кто задан в AUTH_USERS
        try:
            async for member in bot.get_chat_members(chat_id, filter="administrators"):
                if member.user:
                    admins.append(member.user.id)
        except Exception as e:
            log.warning("get_admins для %s: %s", chat_id, e)

        ADMIN_LIST[chat_id] = admins
        return admins

    async def delete_after_delay(self, message):
        """
        Удалить сообщение бота через DELAY секунд.
        Работает только в группах и каналах (в личке незачем).
        """
        if DELAY <= 0:
            return
        if getattr(message.chat, "type", "") in ("supergroup", "channel", "group"):
            await sleep(DELAY)
            try:
                await message.delete()
            except Exception:
                pass


# ─── Единственный экземпляр плеера (все плагины импортируют именно его) ───────
mp = MusicPlayer()


# ══════════════════════════════════════════════════════════════════════════════
#  Обработчики событий PyTgCalls
# ══════════════════════════════════════════════════════════════════════════════

@call.on_stream_end()
async def _on_stream_end(_, update):
    """
    Автоматически вызывается, когда поток заканчивается:
    • Трек из очереди завершился → играем следующий (или возвращаемся к радио)
    • Радиопоток оборвался → перезапускаем
    """
    chat_id = getattr(update, "chat_id", CHAT_ID)
    if chat_id != CHAT_ID:
        return

    log.info("⏹ Поток завершился в чате %s", chat_id)

    if playlist:
        await mp.skip_current_playing()
    else:
        # Небольшая задержка перед перезапуском радио
        await sleep(1)
        await mp.start_radio()
