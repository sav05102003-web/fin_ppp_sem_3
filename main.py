"""Точка входа: измените SPEED для настройки скорости и направления."""

import tkinter as tk

from src.app import App


SPEED = 1.0  # рад/с: плюс — по часовой, минус — против часовой


def main() -> None:
    """Открыть окно анимации с заданной начальной скоростью."""
    root = tk.Tk()
    App(root, speed=SPEED).run()


if __name__ == "__main__":
    main()
