"""
╔══════════════════════════════════════════════════════════╗
║           RadioPlayerV3 — Конфигурация                  ║
║   Все настройки берутся из переменных окружения         ║
║   (.env файл локально, или Config Vars на Heroku)       ║
╚══════════════════════════════════════════════════════════╝
"""
import os
from dotenv import load_dotenv

# Загружаем .env файл, если запускаем локально
load_dotenv()


class Config:

    # ══════════════════════════════════════════════════════════════
    # ОБЯЗАТЕЛЬНЫЕ — без них бот не запустится
    # ══════════════════════════════════════════════════════════════

    # Получить на https://my.telegram.org → "API development tools"
    API_ID   = int(os.getenv("API_ID", 0))
    API_HASH = os.getenv("API_HASH", "")

    # Токен бота — создать через @BotFather → /newbot
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")

    # Строка сессии юзербота — получить запустив: python3 gen_session.py
    # Юзербот нужен потому, что обычные боты не умеют входить в голосовые чаты
    SESSION = os.getenv("SESSION_STRING", "")

    # ID чата/канала, где будет играть музыка
    # Для групп/каналов — отрицательное число, например: -1001234567890
    # Узнать ID можно пересланным постом через @username_to_id_bot
    CHAT_ID = int(os.getenv("CHAT_ID", 0))

    # ══════════════════════════════════════════════════════════════
    # НЕОБЯЗАТЕЛЬНЫЕ — разумные значения по умолчанию
    # ══════════════════════════════════════════════════════════════

    # Дополнительные администраторы бота (через пробел, ID или @username)
    # Пример: AUTH_USERS="123456789 987654321 @myusername"
    # (Администраторы чата добавляются автоматически)
    ADMINS: list = [
        int(a) if a.lstrip("-").isdigit() else a
        for a in os.getenv("AUTH_USERS", "").split()
        if a
    ]

    # Ссылка на радиопоток (по умолчанию — индийское радио Mirchi для теста)
    # Поменяй на свою: например http://icecast.example.com:8000/stream.mp3
    STREAM_URL = os.getenv("STREAM_URL", "http://peridot.streamguys.com:7150/Mirchi")

    # ID группы/канала для логов (статус бота, текущий трек и т.д.)
    # Оставь пустым, если логи не нужны
    LOG_GROUP = int(os.getenv("LOG_GROUP") or 0) or None

    # Если True — /play и /song доступны ТОЛЬКО администраторам
    # Если False — любой участник чата может добавить трек
    ADMIN_ONLY = os.getenv("ADMIN_ONLY", "False").lower() == "true"

    # Ответ на личные сообщения от незнакомцев (None = не отвечать)
    REPLY_MESSAGE = os.getenv("REPLY_MESSAGE") or None

    # Через сколько секунд удалять служебные сообщения бота (0 = не удалять)
    DELAY = int(os.getenv("DELAY") or 10)

    # Если True — заголовок голосового чата меняется на название трека
    EDIT_TITLE = os.getenv("EDIT_TITLE", "True").lower() != "false"

    # Заголовок голосового чата во время работы радио
    RADIO_TITLE = os.getenv("RADIO_TITLE", "📻 РАДИО 24/7 | ПРЯМОЙ ЭФИР") or None

    # Максимальная длина трека в МИНУТАХ для команды /play
    # Треки длиннее этого лимита будут отклонены
    DURATION_LIMIT = int(os.getenv("MAXIMUM_DURATION") or 15)

    # ══════════════════════════════════════════════════════════════
    # HEROKU — нужно только при деплое на Heroku
    # ══════════════════════════════════════════════════════════════

    HEROKU_API_KEY  = os.getenv("HEROKU_API_KEY")   # Account → API Key
    HEROKU_APP_NAME = os.getenv("HEROKU_APP_NAME")   # Имя твоего Heroku-приложения
    HEROKU_APP      = None                            # Заполняется ниже

    # ══════════════════════════════════════════════════════════════
    # РАБОЧЕЕ СОСТОЯНИЕ — меняется в процессе работы бота
    # ══════════════════════════════════════════════════════════════

    msg:      dict = {}   # Ссылки на служебные сообщения (для редактирования/удаления)
    playlist: list = []   # Очередь треков — список списков [id, title, src, type, by]


# ─── Подключение к Heroku (только если оба ключа заданы) ─────────────────────
if Config.HEROKU_API_KEY and Config.HEROKU_APP_NAME:
    try:
        import heroku3
        Config.HEROKU_APP = heroku3.from_key(Config.HEROKU_API_KEY).apps()[Config.HEROKU_APP_NAME]
        print("[Heroku] ✅ Подключение успешно")
    except Exception as _err:
        print(f"[Heroku] ⚠️  Не удалось подключиться: {_err}")
