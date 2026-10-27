"""Главное окно приложения."""

import tkinter as tk
from tkinter import ttk
from time import perf_counter

from src.models.animation import AnimationModel
from src.models.heart import heart_radius
from src.renderers.heart_renderer import BACKGROUND, HeartRenderer
from src.widgets.controls import Controls


class App:
    """Создать окно для визуализации полярного сердца."""

    def __init__(self) -> None:
        """Подготовить окно, модель, отрисовку и элементы управления."""
        self.root = tk.Tk()
        self.root.title("Сердце в полярных координатах")
        self.root.geometry("1000x760")
        self.root.minsize(720, 600)
        self.root.configure(background=BACKGROUND)
        self.model = AnimationModel()
        self._after_id: str | None = None
        self._last_time = perf_counter()
        self._configure_style()
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
        self.controls = Controls(
            self.root, self.toggle_pause, self.reset, self.change_mode,
            self.change_speed,
        )
        self.controls.pack(fill=tk.X, padx=28, pady=(4, 14))
        self.status = tk.StringVar()
        tk.Label(
            self.root, textvariable=self.status, font=("Consolas", 10),
            foreground="#c2a9bd", background=BACKGROUND,
        ).pack(pady=(0, 8))
        tk.Label(
            self.root, text="Пробел — пауза    R — сначала    Esc — выход",
            font=("Segoe UI", 10), foreground="#8b91a8",
            background=BACKGROUND,
        ).pack(pady=(0, 18))
        self.canvas.bind("<Configure>", self._resize)
        # Обрабатываем горячие клавиши один раз на уровне окна.
        self.root.bind("<space>", self.toggle_pause)
        self.root.bind("<KeyPress>", self._on_key)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self._render()

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(
            "TButton", font=("Segoe UI", 10), padding=(14, 8),
            background="#342538", foreground="#ffe4ec", borderwidth=0,
        )
        style.map("TButton", background=[("active", "#61374d")])
        style.configure(
            "TCheckbutton", background=BACKGROUND, foreground="#e1d6e1",
            font=("Segoe UI", 10),
        )
        style.map("TCheckbutton", background=[("active", BACKGROUND)])
        style.configure("Horizontal.TScale", background=BACKGROUND)

    def toggle_pause(self, _event: tk.Event | None = None) -> str:
        """Приостановить или продолжить анимацию."""
        if not self.controls.mode.get():
            self.model.toggle_pause()
            self.controls.refresh(self.model.paused)
            self._render()
        return "break"

    def reset(self) -> None:
        """Вернуться в анимацию и сбросить угол, сохранив паузу и скорость."""
        self.controls.mode.set(False)
        self.model.reset()
        self._last_time = perf_counter()
        self.controls.refresh(self.model.paused)
        self._render()

    def change_mode(self) -> None:
        """Переключить полный контур и анимацию с сохранением ее позиции."""
        self.controls.refresh(self.model.paused)
        self._last_time = perf_counter()
        self._render()

    def change_speed(self, value: str) -> None:
        """Применить значение ползунка к скорости модели."""
        self.model.set_speed(float(value))
        self.controls.speed_label.configure(
            text=f"Скорость {self.model.speed:.2f}×",
        )

    def close(self) -> None:
        """Отменить отложенный кадр и закрыть окно."""
        if self._after_id is not None:
            self.root.after_cancel(self._after_id)
            self._after_id = None
        self.root.destroy()

    def _on_key(self, event: tk.Event) -> str | None:
        if event.keysym.lower() in ("r", "cyrillic_ka"):
            self.reset()
            return "break"
        if event.keysym == "Escape":
            self.close()
            return "break"
        return None

    def _resize(self, _event: tk.Event) -> None:
        self.renderer.resize()
        self._render()

    def _render(self) -> None:
        full = self.controls.mode.get()
        self.renderer.draw(1.0 if full else self.model.progress)
        state = "Контур целиком" if full else (
            "Пауза" if self.model.paused else "Отрисовка"
        )
        self.status.set(
            f"{state}   |   θ = {self.model.angle:.2f} рад"
            f"   |   Δθ = {self.model.last_step:.4f}"
            f"   |   Проход {self.model.cycles + 1}"
        )

    def _tick(self) -> None:
        now = perf_counter()
        # После перемещения окна не пытаемся мгновенно догнать все кадры.
        elapsed = min(now - self._last_time, 0.1)
        self._last_time = now
        if not self.controls.mode.get():
            self.model.advance(elapsed)
        self._render()
        self._after_id = self.root.after(16, self._tick)

    def run(self) -> None:
        """Запустить главный цикл обработки событий."""
        self._last_time = perf_counter()
        self._tick()
        self.root.mainloop()
