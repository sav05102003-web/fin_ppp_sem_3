"""Хранение профилей, недельных меню, покупок и таймеров в SQLite."""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


SCHEMA = """
CREATE TABLE IF NOT EXISTS profiles (
    user_id INTEGER PRIMARY KEY,
    diet TEXT NOT NULL DEFAULT 'обычное',
    excluded TEXT NOT NULL DEFAULT '[]',
    pantry TEXT NOT NULL DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS menu (
    user_id INTEGER NOT NULL,
    week TEXT NOT NULL,
    day INTEGER NOT NULL CHECK(day BETWEEN 0 AND 6),
    meal TEXT NOT NULL,
    recipe_id INTEGER NOT NULL,
    portions INTEGER NOT NULL CHECK(portions BETWEEN 1 AND 12),
    PRIMARY KEY (user_id, week, day, meal)
);
CREATE TABLE IF NOT EXISTS purchases (
    user_id INTEGER NOT NULL,
    week TEXT NOT NULL,
    name TEXT NOT NULL,
    unit TEXT NOT NULL,
    PRIMARY KEY (user_id, week, name, unit)
);
CREATE TABLE IF NOT EXISTS timers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    chat_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    due REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    next_attempt REAL NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS timers_due ON timers(status, due, next_attempt);
"""


class Storage:
    """Открывать короткие транзакции без общего соединения между потоками."""

    def __init__(self, path: Path) -> None:
        """Создать каталог и таблицы, если база ещё не существует."""
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(SCHEMA)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """Открыть соединение, зафиксировать изменения и закрыть его."""
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def profile(self, user_id: int) -> dict:
        """Получить профиль пользователя, при необходимости создав его."""
        with self.connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO profiles(user_id) VALUES (?)",
                (user_id,),
            )
            row = connection.execute(
                "SELECT * FROM profiles WHERE user_id = ?", (user_id,),
            ).fetchone()
        return {
            "diet": row["diet"],
            "excluded": tuple(json.loads(row["excluded"])),
            "pantry": tuple(json.loads(row["pantry"])),
        }

    def set_profile(self, user_id: int, field: str, value: object) -> None:
        """Изменить только разрешённое поле профиля."""
        if field not in {"diet", "excluded", "pantry"}:
            raise ValueError("Неизвестное поле профиля.")
        self.profile(user_id)
        stored = value if field == "diet" else json.dumps(
            value, ensure_ascii=False)
        with self.connect() as connection:
            connection.execute(
                f"UPDATE profiles SET {field} = ? WHERE user_id = ?",
                (stored, user_id),
            )
            if field in {"diet", "excluded"}:
                connection.execute(
                    "DELETE FROM menu WHERE user_id = ?", (user_id,))
                connection.execute(
                    "DELETE FROM purchases WHERE user_id = ?", (user_id,),
                )

    def menu(self, user_id: int, week: str) -> list[dict]:
        """Получить блюда недели только для указанного пользователя."""
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM menu WHERE user_id = ? AND week = ? "
                "ORDER BY day, CASE meal WHEN 'завтрак' THEN 0 "
                "WHEN 'обед' THEN 1 ELSE 2 END", (user_id, week),
            ).fetchall()
        return [dict(row) for row in rows]

    def save_menu(
        self, user_id: int, week: str, entries: list[tuple], replace: bool,
    ) -> None:
        """Атомарно записать меню и сбросить отметки изменившихся покупок."""
        with self.connect() as connection:
            if replace:
                connection.execute(
                    "DELETE FROM menu WHERE user_id = ? AND week = ?",
                    (user_id, week),
                )
            connection.executemany(
                "INSERT OR REPLACE INTO menu VALUES (?, ?, ?, ?, ?, ?)",
                [(user_id, week, *entry) for entry in entries],
            )
            connection.execute(
                "DELETE FROM purchases WHERE user_id = ? AND week = ?",
                (user_id, week),
            )

    def purchased(self, user_id: int, week: str) -> set[tuple[str, str]]:
        """Получить названия и единицы уже купленных продуктов."""
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT name, unit FROM purchases "
                "WHERE user_id = ? AND week = ?",
                (user_id, week),
            ).fetchall()
        return {(row["name"], row["unit"]) for row in rows}

    def toggle_purchase(
        self, user_id: int, week: str, name: str, unit: str,
    ) -> None:
        """Переключить отметку покупки в одной транзакции."""
        with self.connect() as connection:
            result = connection.execute(
                "DELETE FROM purchases WHERE user_id = ? AND week = ? "
                "AND name = ? AND unit = ?", (user_id, week, name, unit),
            )
            if not result.rowcount:
                connection.execute(
                    "INSERT INTO purchases VALUES (?, ?, ?, ?)",
                    (user_id, week, name, unit),
                )

    def add_timer(
        self, user_id: int, chat_id: int, title: str, due: float,
    ) -> int:
        """Сохранить таймер с ограничением десять активных на пользователя."""
        with self.connect() as connection:
            # Ранняя блокировка не позволяет двум созданиям обойти лимит.
            connection.execute("BEGIN IMMEDIATE")
            count = connection.execute(
                "SELECT COUNT(*) FROM timers WHERE user_id = ? "
                "AND status = 'pending'", (user_id,),
            ).fetchone()[0]
            if count >= 10:
                raise ValueError(
                    "Можно создать не более 10 активных таймеров.")
            cursor = connection.execute(
                "INSERT INTO timers(user_id, chat_id, title, due) "
                "VALUES (?, ?, ?, ?)", (user_id, chat_id, title, due),
            )
            return cursor.lastrowid

    def timers(self, user_id: int) -> list[dict]:
        """Вернуть активные таймеры пользователя."""
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM timers "
                "WHERE user_id = ? AND status = 'pending' "
                "ORDER BY due, id", (user_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def due_timers(self, now: float) -> list[dict]:
        """Получить готовые к отправке таймеры, включая просроченные."""
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM timers WHERE status = 'pending' AND due <= ? "
                "AND next_attempt <= ? ORDER BY due, id", (now, now),
            ).fetchall()
        return [dict(row) for row in rows]

    def cancel_timer(self, user_id: int, timer_id: int) -> bool:
        """Отменить только собственный активный таймер."""
        with self.connect() as connection:
            cursor = connection.execute(
                "UPDATE timers SET status = 'cancelled' WHERE id = ? "
                "AND user_id = ? AND status = 'pending'", (timer_id, user_id),
            )
        return bool(cursor.rowcount)

    def finish_timer(self, timer_id: int, status: str) -> None:
        """Завершить таймер после доставки или постоянной ошибки."""
        if status not in {"sent", "failed"}:
            raise ValueError("Недопустимый статус таймера.")
        with self.connect() as connection:
            connection.execute(
                "UPDATE timers SET status = ? "
                "WHERE id = ? AND status = 'pending'",
                (status, timer_id),
            )

    def retry_timer(self, timer_id: int, now: float) -> None:
        """Отложить уведомление, максимум пять попыток доставки."""
        with self.connect() as connection:
            connection.execute(
                "UPDATE timers SET attempts = attempts + 1, next_attempt = ?, "
                "status = CASE WHEN attempts >= 4 THEN 'failed' "
                "ELSE 'pending' END WHERE id = ? AND status = 'pending'",
                (now + 30, timer_id),
            )
