"""Точка входа: запуск Telegram-бота, проверка или локальная демонстрация."""

import argparse
import logging
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from config import load_settings
from src.assistant import CookingAssistant
from src.storage import Storage


def main() -> int:
    """Разобрать аргументы и запустить выбранный режим работы."""
    parser = argparse.ArgumentParser(description="Кулинарный помощник, тема 4")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--demo", action="store_true",
                       help="Демонстрация без токена")
    modes.add_argument("--check", action="store_true",
                       help="Проверка каталога и SQLite")
    args = parser.parse_args()
    if args.demo:
        from src.demo import run_demo

        run_demo()
        return 0
    if args.check:
        with TemporaryDirectory() as directory:
            assistant = CookingAssistant(
                Storage(Path(directory) / "check.sqlite3"))
            print(f"Каталог: {len(assistant.recipes)} рецептов. SQLite: OK.")
        return 0
    try:
        token, db_path = load_settings()
        from src.bot import build_application

        assistant = CookingAssistant(Storage(db_path))
        application = build_application(token, assistant)
    except (ValueError, ImportError, RuntimeError, OSError) as error:
        if isinstance(error, ImportError):
            print("Установите зависимости: "
                  "python -m pip install -r requirements.txt")
        else:
            print(str(error))
        return 1
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        level=logging.INFO,
    )
    # HTTP-клиенты могут журналировать URL с токеном; оставляем только ошибки.
    logging.getLogger("httpx").setLevel(logging.CRITICAL)
    logging.getLogger("httpcore").setLevel(logging.CRITICAL)
    print("Бот запущен. Откройте его в Telegram и отправьте /start. "
          "Выход: Ctrl+C.")
    try:
        application.run_polling(allowed_updates=["message"])
    except Exception as error:
        # Текст сетевого исключения может содержать URL с токеном.
        logging.getLogger(__name__).error(
            "Остановка бота: %s. Проверьте сеть и настройки.", type(
                error).__name__,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
