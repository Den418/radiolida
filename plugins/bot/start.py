"""
Плагин: /start и /help
"""
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message

from bot_client import bot
from config import Config

HELP_TEXT = """
📖 **Справка по командам RadioPlayerV3**

**🎵 Музыка:**
• /play `[ссылка или название]` — добавить трек с YouTube
• /song `[ссылка или название]` — скачать аудио и добавить
• /skip — пропустить текущий трек
• /pause — поставить на паузу
• /resume — продолжить воспроизведение
• /replay — повторить трек сначала
• /current — что сейчас играет
• /playlist — список очереди

**📻 Радио:**
• /radio — включить радио-поток
• /stopradio — выключить радио

**🔊 Голосовой чат:**
• /join — войти в голосовой чат
• /leave — выйти из голосового чата
• /mute — заглушить юзербота
• /unmute — включить звук
• /volume `[0-200]` — громкость (100 = стандарт)

**🛠 Для администраторов:**
• /clean — удалить загруженные файлы
• /restart — обновить бота с GitHub
• /setvar `КЛЮЧ ЗНАЧЕНИЕ` — изменить Config Var (Heroku)

ℹ️ _Команды /skip, /pause, /resume, /radio, /join, /leave, /mute,_
_/unmute, /volume, /clean, /restart доступны только администраторам_
"""


@bot.on_message(filters.command(["start"]))
async def cmd_start(_, message: Message):
    """Приветственное сообщение."""
    name = message.from_user.mention if message.from_user else "пользователь"
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("❓ Помощь", callback_data="show_help"),
            InlineKeyboardButton("📻 GitHub", url="https://github.com/AsmSafone/RadioPlayerV3"),
        ],
    ])
    await message.reply_text(
        f"👋 Привет, {name}!\n\n"
        f"Я **RadioPlayerV3** — бот для воспроизведения музыки "
        f"и интернет-радио в голосовых чатах Telegram.\n\n"
        f"🎵 Добавь меня в группу и дай права администратора.\n"
        f"📻 Юзербот автоматически войдёт в голосовой чат и начнёт вещание.\n\n"
        f"Нажми **Помощь**, чтобы увидеть все команды.",
        reply_markup=keyboard,
    )


@bot.on_message(filters.command(["help"]))
async def cmd_help(_, message: Message):
    """Справка по всем командам."""
    await message.reply_text(HELP_TEXT, disable_web_page_preview=True)


@bot.on_callback_query(filters.regex("^show_help$"))
async def cb_show_help(_, query):
    """Кнопка «Помощь» в стартовом сообщении."""
    await query.message.edit_text(HELP_TEXT, disable_web_page_preview=True)
    await query.answer()
