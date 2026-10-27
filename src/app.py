"""Главное окно приложения."""

import tkinter as tk

from src.models.heart import heart_radius
from src.renderers.heart_renderer import BACKGROUND, HeartRenderer


class App:
    """Создать окно для визуализации полярного сердца."""

    def __init__(self) -> None:
        """Подготовить окно и холст."""
        self.root = tk.Tk()
        self.root.title("Сердце в полярных координатах")
        self.root.geometry("1000x760")
        self.root.minsize(720, 600)
        self.root.configure(background=BACKGROUND)
        tk.Label(
            self.root, text="Сердце", font=("Segoe UI", 26, "bold"),
            foreground="#ffe4ec", background=BACKGROUND,
        ).pack(pady=(20, 0))
        tk.Label(
            self.root, text="Простая анимация · Полярные координаты",
            font=("Segoe UI", 11), foreground="#a1a6bc",
            background=BACKGROUND,
        ).pack(pady=(4, 0))
        self.canvas = tk.Canvas(
            self.root, background=BACKGROUND, highlightthickness=0,
        )
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        self.renderer = HeartRenderer(self.canvas, heart_radius)
        self.canvas.bind("<Configure>", self._resize)

    def _resize(self, _event: tk.Event) -> None:
        self.renderer.resize()
        self.renderer.draw()

    def run(self) -> None:
        """Запустить главный цикл обработки событий."""
        self.root.mainloop()
