"""Настройки из переменных окружения и локального файла .env."""

import os
import re
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent


def load_settings() -> tuple[str, Path]:
    """Прочитать токен и путь базы, не записывая секреты в журнал."""
    values = {}
    env_path = PROJECT_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, separator, value = line.partition("=")
            allowed = {"BOT_TOKEN", "BOT_DB_PATH"}
            if not separator or key.strip() not in allowed:
                raise ValueError(
                    "В .env допустимы строки BOT_TOKEN= и BOT_DB_PATH=.")
            value = value.strip()
            if value.startswith(("'", '"')):
                if len(value) < 2 or value[-1] != value[0]:
                    raise ValueError("В .env не закрыты кавычки.")
                value = value[1:-1]
            values[key.strip()] = value
    token = os.environ.get("BOT_TOKEN", values.get("BOT_TOKEN", "")).strip()
    if not re.fullmatch(r"\d+:[A-Za-z0-9_-]{30,}", token):
        raise ValueError(
            "Укажите токен от @BotFather в BOT_TOKEN или файле .env. "
            "Пример настройки находится в .env.example."
        )
    db_value = os.environ.get(
        "BOT_DB_PATH", values.get("BOT_DB_PATH", "data/users.sqlite3"),
    ).strip()
    if not db_value:
        raise ValueError("BOT_DB_PATH не должен быть пустым.")
    db_path = Path(db_value).expanduser()
    if not db_path.is_absolute():
        db_path = PROJECT_DIR / db_path
    return token, db_path
