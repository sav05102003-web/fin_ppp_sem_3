"""Окно Tkinter, таймер анимации и управление с клавиатуры."""

import time
import tkinter as tk
from tkinter import messagebox

from src.models.animation_model import AnimationModel
from src.renderers.renderer import Renderer


class App:
    """Связать модель движения и Canvas через событийный цикл Tkinter."""

    FRAME_INTERVAL_MS = 16
    SPEED_STEP = 0.25

    def __init__(self, root: tk.Tk, speed: float = 1.0) -> None:
        """Создать окно 600×600 и запланировать первый кадр."""
        self.root = root
        self.model = AnimationModel(speed=speed)
        self.paused = False
        self._closed = False
        self._after_id: str | None = None
        self._last_tick = time.perf_counter()
        self._direction = -1 if speed < 0 else 1

        root.geometry("600x600")
        root.resizable(False, False)
        self.canvas = tk.Canvas(
            root, width=600, height=600, bg="white",
            highlightthickness=0, borderwidth=0,
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.renderer = Renderer(self.canvas, self.model)
        root.bind("<KeyPress>", self._on_key)
        root.protocol("WM_DELETE_WINDOW", self.close)
        self._update_title()
        self._schedule_frame()

    def run(self) -> None:
        """Запустить обработку событий окна."""
        self.root.mainloop()

    def toggle_pause(self) -> None:
        """Переключить паузу, не включая время простоя в движение."""
        self._advance_to_now()
        self.paused = not self.paused
        self._update_title()

    def reset(self) -> None:
        """Вернуть точку в начало, сохранив скорость и состояние паузы."""
        self.model.reset()
        self._last_tick = time.perf_counter()
        self.renderer.draw(self.model)

    def change_speed(self, delta: float) -> None:
        """Изменить модуль скорости, сохранив направление движения."""
        self._advance_to_now()
        magnitude = max(0.0, abs(self.model.speed) + delta)
        self.model.set_speed(self._direction * magnitude)
        self._update_title()

    def set_direction(self, clockwise: bool) -> None:
        """Выбрать направление; при нулевой скорости возобновить движение."""
        self._advance_to_now()
        self._direction = 1 if clockwise else -1
        magnitude = abs(self.model.speed) or self.SPEED_STEP
        self.model.set_speed(self._direction * magnitude)
        self._update_title()

    def show_help(self) -> None:
        """Показать назначение клавиш в отдельном диалоге."""
        was_paused = self.paused
        if not was_paused:
            self.toggle_pause()
        try:
            messagebox.showinfo(
                "Управление",
                "Пробел — пауза / продолжение\n"
                "↑ / ↓ — быстрее / медленнее\n"
                "→ — по часовой, ← — против часовой\n"
                "R / К — вернуть точку наверх\n"
                "Esc — закрыть окно\n\n"
                "Скорость указана в радианах в секунду.",
                parent=self.root,
            )
        finally:
            if not was_paused and not self._closed:
                self.toggle_pause()

    def close(self) -> None:
        """Отменить таймер и закрыть окно без фоновых обработчиков."""
        if self._closed:
            return
        self._closed = True
        if self._after_id is not None:
            self.root.after_cancel(self._after_id)
            self._after_id = None
        self.root.destroy()

    def _advance_to_now(self) -> None:
        now = time.perf_counter()
        if not self.paused:
            self.model.advance(now - self._last_tick)
        self._last_tick = now
        self.renderer.draw(self.model)

    def _schedule_frame(self) -> None:
        self._after_id = self.root.after(self.FRAME_INTERVAL_MS, self._tick)

    def _tick(self) -> None:
        if self._closed:
            return
        self._after_id = None
        self._advance_to_now()
        self._schedule_frame()

    def _update_title(self) -> None:
        state = "пауза" if self.paused else "движение"
        self.root.title(
            f"Точка по окружности | {self.model.speed:+.2f} рад/с"
            f" | {state} | F1 — справка"
        )

    def _on_key(self, event: tk.Event) -> str | None:
        actions = {
            "space": self.toggle_pause,
            "Up": lambda: self.change_speed(self.SPEED_STEP),
            "Down": lambda: self.change_speed(-self.SPEED_STEP),
            "Right": lambda: self.set_direction(True),
            "Left": lambda: self.set_direction(False),
            "r": self.reset,
            "R": self.reset,
            "Cyrillic_ka": self.reset,
            "Cyrillic_KA": self.reset,
            "F1": self.show_help,
            "Escape": self.close,
        }
        action = actions.get(event.keysym)
        if action is not None:
            action()
            return "break"
        return None
