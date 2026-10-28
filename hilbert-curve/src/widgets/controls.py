"""Кнопки, выбор кривой и параметры анимации."""

import tkinter as tk
from tkinter import ttk

from src.models.curves import CURVES


class Controls(ttk.Frame):
    """Содержать элементы управления и передавать действия приложению."""

    def __init__(self, master, on_curve, on_order, on_speed, on_pause,
                 on_restart, on_show_all):
        """Создать панель и зарегистрировать обработчики событий."""
        super().__init__(master, padding=(24, 16))
        self.columnconfigure(7, weight=1)
        self.curve = tk.StringVar(value=next(iter(CURVES)))
        self.order = tk.IntVar(value=3)
        self.speed = tk.DoubleVar(value=1.0)
        self.speed_label = tk.StringVar(value="1.00×")
        ttk.Label(self, text="Кривая").grid(row=0, column=0, sticky="w")
        self.curve_box = ttk.Combobox(
            self, textvariable=self.curve, values=tuple(CURVES),
            state="readonly", width=22,
        )
        self.curve_box.grid(row=1, column=0, padx=(0, 20), sticky="w")
        self.curve_box.bind("<<ComboboxSelected>>", lambda _: on_curve())
        ttk.Label(self, text="Порядок").grid(row=0, column=1, sticky="w")
        self.order_box = ttk.Combobox(
            self, textvariable=self.order, values=tuple(range(1, 8)),
            state="readonly", width=5,
        )
        self.order_box.grid(row=1, column=1, padx=(0, 24), sticky="w")
        self.order_box.bind("<<ComboboxSelected>>", lambda _: on_order())
        ttk.Label(self, text="Скорость").grid(row=0, column=2, sticky="w")
        self.speed_scale = ttk.Scale(
            self, from_=0.25, to=4.0, variable=self.speed,
            command=lambda value: self._change_speed(value, on_speed),
            length=130,
        )
        self.speed_scale.grid(row=1, column=2, padx=(0, 8))
        ttk.Label(self, textvariable=self.speed_label, width=6).grid(
            row=1, column=3, padx=(0, 20)
        )
        self.pause_button = ttk.Button(self, text="Пауза", command=on_pause)
        self.pause_button.grid(row=1, column=4, padx=(0, 8))
        ttk.Button(self, text="Сначала", command=on_restart).grid(
            row=1, column=5, padx=(0, 8)
        )
        ttk.Button(self, text="Показать всё", command=on_show_all).grid(
            row=1, column=6
        )

    def set_order_limit(self, maximum):
        """Изменить список допустимых порядков для выбранной кривой."""
        self.order_box.configure(values=tuple(range(1, maximum + 1)))
        self.order.set(min(self.order.get(), maximum))

    def set_animation_state(self, paused, completed):
        """Обновить подпись и доступность кнопки паузы."""
        self.pause_button.configure(
            text="Продолжить" if paused else "Пауза",
            state="disabled" if completed else "normal",
        )

    def _change_speed(self, value, callback):
        self.speed_label.set(f"{float(value):.2f}×")
        callback(float(value))
