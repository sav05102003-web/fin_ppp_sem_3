"""Кнопки и ползунок управления анимацией."""

from collections.abc import Callable
import tkinter as tk
from tkinter import ttk

from src.renderers.heart_renderer import BACKGROUND


class Controls(tk.Frame):
    """Разместить панель управления под холстом."""

    def __init__(
        self, parent: tk.Misc, on_pause: Callable[[], None],
        on_reset: Callable[[], None], on_mode: Callable[[], None],
        on_speed: Callable[[str], None], figures: tuple[str, ...],
        on_figure: Callable[[tk.Event], None],
    ) -> None:
        """Создать кнопки, переключатель режима и ползунок скорости."""
        super().__init__(parent, background=BACKGROUND)
        self.mode = tk.BooleanVar(value=False)
        self.speed = tk.DoubleVar(value=1.0)
        self.figure = tk.StringVar(value=figures[0])
        selector = ttk.Combobox(
            self, values=figures, textvariable=self.figure,
            state="readonly", width=24, font=("Segoe UI", 10),
        )
        selector.grid(row=0, column=0, columnspan=5, pady=(0, 16))
        selector.bind("<<ComboboxSelected>>", on_figure)
        self.pause_button = ttk.Button(self, text="Пауза", command=on_pause)
        self.pause_button.grid(row=1, column=0, padx=(0, 10))
        ttk.Button(self, text="Сначала", command=on_reset).grid(
            row=1, column=1, padx=(0, 20),
        )
        ttk.Checkbutton(
            self, text="Контур целиком", variable=self.mode, command=on_mode,
        ).grid(row=1, column=2, padx=(0, 20))
        self.speed_label = tk.Label(
            self, text="Скорость 1.00×", background=BACKGROUND,
            foreground="#e1d6e1", font=("Segoe UI", 10),
        )
        self.speed_label.grid(row=1, column=3, padx=(0, 10))
        ttk.Scale(
            self, from_=0.25, to=3.0, variable=self.speed,
            command=on_speed, length=180,
        ).grid(row=1, column=4, sticky="ew")
        self.columnconfigure(4, weight=1)

    def refresh(self, paused: bool) -> None:
        """Обновить подпись паузы и доступность кнопки для текущего режима."""
        self.pause_button.configure(text="Продолжить" if paused else "Пауза")
        state = ["disabled"] if self.mode.get() else ["!disabled"]
        self.pause_button.state(state)
