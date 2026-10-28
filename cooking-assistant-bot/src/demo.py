"""Воспроизводимая демонстрация сценариев без токена и Telegram."""

from pathlib import Path
from tempfile import TemporaryDirectory

from src.assistant import CookingAssistant
from src.storage import Storage


def run_demo() -> None:
    """Выполнить пользовательский сценарий во временной базе."""
    with TemporaryDirectory(prefix="cooking-bot-demo-") as directory:
        assistant = CookingAssistant(Storage(Path(directory) / "demo.sqlite3"))
        commands = [
            "/find рис, морковь, перец", "/recipe 3",
            "/diet веганское", "/exclude тофу", "/tips",
            "/plan авто 2", "/shopping", "/buy 1",
            "/timer 10с рис", "/timers", "/cancel_timer 1",
        ]
        for command in commands:
            print(f"\n>>> {command}\n{assistant.execute(1, 1, command)}")
        print("\nДемонстрация завершена; "
              "временная база удаляется автоматически.")
